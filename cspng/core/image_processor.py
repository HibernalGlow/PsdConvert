"""
图像处理器

负责处理图像数据的提取、解压缩和合并。
"""

import struct
import zlib
from typing import Optional, Tuple, Dict, Any, List
import numpy as np
import cv2
from loguru import logger

from .exceptions import ImageProcessingError, DataProcessingError


class ImageProcessor:
    """图像处理器"""
    
    @staticmethod
    def get_external_data_from_chunk(
        chunk_data: Dict[str, Any], 
        binary_data: bytes
    ) -> Optional[bytes]:
        """从块中获取外部数据"""
        try:
            offset = chunk_data['chunk_start_position']
            
            # 16字节：跳过
            offset += 16
            
            # 大端序8字节：块大小
            chunk_size = struct.unpack_from('>Q', binary_data, offset)[0]
            offset += 8
            
            # 读取External ID
            external_id = struct.unpack_from(
                str(chunk_size) + 's', binary_data, offset)[0]
            external_id = external_id.decode()
            offset += chunk_size
            
            # 大端序8字节：External数据大小（跳过）
            offset += 8
            
            external_data = bytes([])
            while offset < chunk_data['chunk_end_position']:
                block_start_position = offset
                
                # 大端序4字节：大小01
                size_01 = struct.unpack_from('>L', binary_data, offset)[0]
                offset += 4
                
                # 大端序4字节：大小02
                size_02 = struct.unpack_from('>L', binary_data, offset)[0]
                offset += 4
                
                # 设置数据块名称和大小
                if size_02 == 0x0042006C:  # "Bl"
                    block_name_len = size_01
                    block_data_len = 0
                    offset = block_start_position + 4
                else:
                    block_name_len = size_02
                    block_data_len = size_01
                
                # 获取数据块名称
                block_name = '<toobig>'
                if block_name_len < 256:
                    block_name = struct.unpack_from(
                        str(block_name_len * 2) + 's', binary_data, offset)[0]
                    block_name = block_name.decode('utf-16-be')
                    offset += block_name_len * 2
                else:
                    offset += block_name_len * 2
                
                # 数据块处理
                block_start_position = offset
                block_end_position = block_start_position + block_data_len
                
                if block_name == 'BlockDataBeginChunk':
                    external_data += ImageProcessor._process_block_data_chunk(
                        binary_data, offset, block_start_position
                    )
                    block_end_position = ImageProcessor._get_block_end_position(
                        binary_data, offset, block_start_position
                    )
                elif block_name in ['BlockStatus', 'BlockCheckSum']:
                    # 跳过状态和校验和块
                    offset += 4  # i0
                    offset += 4  # 块大小
                    offset += 4  # 块宽度
                    offset += 4  # 块高度
                    offset += 4  # i4
                    offset += 4  # i5
                    block_end_position = block_start_position + 24
                
                offset = block_end_position
            
            return external_data
            
        except Exception as e:
            logger.error(f"获取外部数据失败: {str(e)}")
            return None
    
    @staticmethod
    def _process_block_data_chunk(
        binary_data: bytes, 
        offset: int, 
        block_start_position: int
    ) -> bytes:
        """处理块数据"""
        try:
            # 跳过块索引
            offset += 4
            
            # 大端序4字节：块大小（非压缩）
            block_uncompressed_size = struct.unpack_from('>L', binary_data, offset)[0]
            offset += 4
            
            # 跳过块宽度和高度
            offset += 8
            
            # 大端序4字节：块存在标志
            exist_flag = struct.unpack_from('>L', binary_data, offset)[0]
            offset += 4
            
            if exist_flag > 0:
                # 大端序4字节：块长度
                block_len = struct.unpack_from('>L', binary_data, offset)[0]
                offset += 4
                
                # 小端序4字节：块长度2
                block_len_2 = struct.unpack_from('<L', binary_data, offset)[0]
                offset += 4
                
                if block_len_2 < block_len - 4:
                    logger.warning("块长度不匹配")
                
                # 解压缩块数据
                block_zlib_data = binary_data[offset:offset + block_len_2]
                block_data = zlib.decompress(block_zlib_data)
                
                if len(block_data) != block_uncompressed_size:
                    logger.warning("解压缩大小不匹配")
                
                return block_data
            else:
                # 返回空数据
                return bytes(block_uncompressed_size)
                
        except Exception as e:
            logger.error(f"处理块数据失败: {str(e)}")
            return bytes()
    
    @staticmethod
    def _get_block_end_position(
        binary_data: bytes, 
        offset: int, 
        block_start_position: int
    ) -> int:
        """获取块结束位置"""
        try:
            # 跳过到存在标志
            temp_offset = offset + 16
            exist_flag = struct.unpack_from('>L', binary_data, temp_offset)[0]
            
            if exist_flag > 0:
                temp_offset += 4
                block_len = struct.unpack_from('>L', binary_data, temp_offset)[0]
                return block_start_position + 24 + block_len
            else:
                return block_start_position + 20
                
        except Exception as e:
            logger.error(f"获取块结束位置失败: {str(e)}")
            return block_start_position
    
    @staticmethod
    def convert_external_data_to_image(
        external_data: bytes,
        image_width: int,
        image_height: int
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """将外部数据转换为图像"""
        try:
            logger.debug(f"转换外部数据为图像: {image_width}x{image_height}")
            
            # 各种常数值
            pixel_size = 4
            bgr_composite_block_size = 256 * 320 * pixel_size
            block_size = 256 * 256
            blocks_per_row = int((image_height + 255) / 256)
            blocks_per_column = int((image_width + 255) / 256)
            padded_width = blocks_per_column * 256
            padded_height = blocks_per_row * 256
            
            grayscale_expected_size = padded_width * padded_height
            bgr_expected_size = padded_width * padded_height * (pixel_size + 1)
            
            # 检查数据大小
            if len(external_data) == grayscale_expected_size:
                raise ImageProcessingError("暂不支持灰度图像")
            elif len(external_data) != bgr_expected_size:
                logger.warning(f"数据大小不匹配: 期望 {bgr_expected_size}, 实际 {len(external_data)}")
                return None, None
            
            # 转换为图像
            bgr_image, alpha_image = ImageProcessor._external_data_to_image(
                external_data,
                block_size,
                blocks_per_row,
                blocks_per_column,
                bgr_composite_block_size,
            )
            
            # 移除填充
            if bgr_image is not None:
                bgr_image = bgr_image[:image_height, :image_width]
            if alpha_image is not None:
                alpha_image = alpha_image[:image_height, :image_width]
            
            return bgr_image, alpha_image
            
        except Exception as e:
            raise ImageProcessingError(f"转换图像失败: {str(e)}")
    
    @staticmethod
    def _external_data_to_image(
        external_data: bytes,
        block_size: int,
        blocks_per_row: int,
        blocks_per_column: int,
        bgr_composite_block_size: int,
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """将外部数据转换为图像数组"""
        try:
            # 创建块列表
            bgra_block_list = [[None] * blocks_per_column for _ in range(blocks_per_row)]
            alpha_block_list = [[None] * blocks_per_column for _ in range(blocks_per_row)]
            
            # 转换为numpy数组
            external_data_array = np.frombuffer(external_data, dtype=np.uint8)
            
            for block_index in range(blocks_per_row * blocks_per_column):
                # 计算块位置
                block_address = block_index * bgr_composite_block_size
                block_x = int(block_index % blocks_per_column)
                block_y = int(block_index / blocks_per_column)
                
                # 获取块数据
                block = external_data_array[block_address:block_address + bgr_composite_block_size]
                alpha_block = block[0:block_size]
                bgra_block = block[block_size:]
                
                # 重塑并添加到列表
                alpha_block = alpha_block.reshape(256, 256)
                alpha_block_list[block_y][block_x] = alpha_block
                
                bgra_block = bgra_block.reshape(256, 256, 4)
                bgra_block_list[block_y][block_x] = bgra_block
            
            # 合并Alpha图像
            alpha_image = ImageProcessor._merge_blocks(alpha_block_list, blocks_per_row, blocks_per_column)
            
            # 合并BGRA图像并提取BGR
            bgra_image = ImageProcessor._merge_blocks(bgra_block_list, blocks_per_row, blocks_per_column)
            bgr_image = np.delete(bgra_image, 3, 2) if bgra_image is not None else None
            
            return bgr_image, alpha_image
            
        except Exception as e:
            logger.error(f"转换图像数组失败: {str(e)}")
            return None, None
    
    @staticmethod
    def _merge_blocks(block_list: List[List], blocks_per_row: int, blocks_per_column: int) -> Optional[np.ndarray]:
        """合并块为完整图像"""
        try:
            merged_image = None
            for block_y in range(blocks_per_row):
                temp_row = None
                for block_x in range(blocks_per_column):
                    if temp_row is None:
                        temp_row = block_list[block_y][block_x]
                    else:
                        temp_row = np.hstack([temp_row, block_list[block_y][block_x]])
                
                if merged_image is None:
                    merged_image = temp_row
                else:
                    merged_image = np.vstack([merged_image, temp_row])
            
            return merged_image

        except Exception as e:
            logger.error(f"合并块失败: {str(e)}")
            return None

    @staticmethod
    def merge_layers_to_canvas(
        layers_data: List[Tuple[str, Optional[np.ndarray]]],
        canvas_width: int,
        canvas_height: int
    ) -> Optional[np.ndarray]:
        """将多个图层合并到画布上"""
        try:
            logger.info(f"开始合并 {len(layers_data)} 个图层到 {canvas_width}x{canvas_height} 画布")

            # 创建空白画布（BGRA格式）
            merged_canvas = np.zeros((canvas_height, canvas_width, 4), dtype=np.uint8)
            processed_count = 0

            for layer_name, bgra_image in layers_data:
                if bgra_image is None:
                    logger.warning(f"跳过空图层: {layer_name}")
                    continue

                try:
                    # 获取图层尺寸
                    layer_height, layer_width = bgra_image.shape[:2]

                    # 计算放置位置（居中）
                    start_y = max(0, (canvas_height - layer_height) // 2)
                    start_x = max(0, (canvas_width - layer_width) // 2)
                    end_y = min(canvas_height, start_y + layer_height)
                    end_x = min(canvas_width, start_x + layer_width)

                    # 计算实际复制区域
                    copy_height = end_y - start_y
                    copy_width = end_x - start_x

                    # 获取要复制的图层区域
                    layer_region = bgra_image[:copy_height, :copy_width]
                    canvas_region = merged_canvas[start_y:end_y, start_x:end_x]

                    # Alpha混合
                    alpha = layer_region[:, :, 3:4] / 255.0

                    # 混合颜色通道
                    for c in range(3):  # BGR通道
                        canvas_region[:, :, c] = (
                            alpha[:, :, 0] * layer_region[:, :, c] +
                            (1 - alpha[:, :, 0]) * canvas_region[:, :, c]
                        )

                    # 更新Alpha通道
                    canvas_region[:, :, 3] = np.maximum(
                        canvas_region[:, :, 3],
                        layer_region[:, :, 3]
                    )

                    processed_count += 1
                    logger.debug(f"成功合并图层: {layer_name}")

                except Exception as e:
                    logger.error(f"合并图层 '{layer_name}' 时发生错误: {str(e)}")
                    continue

            logger.info(f"成功合并 {processed_count}/{len(layers_data)} 个图层")

            # 返回RGB格式（移除Alpha通道）
            return merged_canvas[:, :, :3]

        except Exception as e:
            raise ImageProcessingError(f"合并图层失败: {str(e)}")

    @staticmethod
    def save_image_as_png(image: np.ndarray, output_path: str) -> bool:
        """保存图像为PNG格式"""
        try:
            success = cv2.imwrite(output_path, image)
            if success:
                logger.info(f"成功保存图像到: {output_path}")
                return True
            else:
                logger.error(f"保存图像失败: {output_path}")
                return False

        except Exception as e:
            logger.error(f"保存图像时发生错误: {str(e)}")
            return False
