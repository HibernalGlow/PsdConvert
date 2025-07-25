"""
CSPNG主转换器

整合所有模块，提供统一的转换接口。
"""

import time
from typing import Optional, Tuple, List, Dict, Any
import numpy as np
from loguru import logger

from .file_parser import ClipFileParser
from .sqlite_handler import SqliteHandler
from .image_processor import ImageProcessor
from .exceptions import CspngError, DataProcessingError, ImageProcessingError


class CspConverter:
    """CLIP到PNG转换器"""
    
    def __init__(self, filepath: str):
        """
        初始化转换器
        
        Args:
            filepath: CLIP文件路径
        """
        self.filepath = filepath
        self.file_parser: Optional[ClipFileParser] = None
        self.sqlite_handler: Optional[SqliteHandler] = None
        
        # 解析文件
        self._initialize()
    
    def _initialize(self) -> None:
        """初始化解析器"""
        logger.info(f"初始化CLIP文件转换器: {self.filepath}")
        
        try:
            # 解析文件结构
            self.file_parser = ClipFileParser(self.filepath)
            
            # 处理SQLite数据
            self.sqlite_handler = SqliteHandler(self.file_parser.sqlite_binary_data)
            
            logger.info("转换器初始化完成")
            
        except Exception as e:
            raise CspngError(f"初始化转换器失败: {str(e)}")
    
    def get_canvas_info(self) -> Dict[str, Any]:
        """获取画布信息"""
        if not self.sqlite_handler or not self.sqlite_handler.canvas_preview_list:
            raise DataProcessingError("画布信息不可用")
        
        canvas_info = self.sqlite_handler.canvas_preview_list[0]
        return {
            'width': canvas_info['image_width'],
            'height': canvas_info['image_height'],
            'canvas_id': canvas_info['canvas_id']
        }
    
    def get_layer_list(self) -> List[Dict[str, Any]]:
        """获取图层列表"""
        if not self.sqlite_handler:
            raise DataProcessingError("SQLite处理器未初始化")
        
        return self.sqlite_handler.layer_list
    
    def get_layer_data(self, canvas_id: int, layer_id: int) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
        """
        获取图层数据
        
        Args:
            canvas_id: 画布ID
            layer_id: 图层ID
            
        Returns:
            Tuple[BGR图像, Alpha图像, BGRA图像]
        """
        start_time = time.time()
        
        try:
            # 获取外部ID
            external_id = self._get_external_id(canvas_id, layer_id)
            if external_id is None:
                logger.warning(f"无法获取外部ID (Canvas: {canvas_id}, Layer: {layer_id})")
                return None, None, None
            
            # 获取图层缩略图信息
            layer_thumbnail = self._get_layer_thumbnail(canvas_id, layer_id)
            if layer_thumbnail is None:
                logger.warning(f"无法获取图层缩略图 (Canvas: {canvas_id}, Layer: {layer_id})")
                return None, None, None
            
            # 获取外部数据
            external_data = self._get_external_data(external_id)
            if external_data is None:
                logger.warning(f"无法获取外部数据 (External ID: {external_id})")
                return None, None, None
            
            # 转换为图像
            image_width = layer_thumbnail['thumbnail_canvas_width']
            image_height = layer_thumbnail['thumbnail_canvas_height']
            
            bgr_image, alpha_image = ImageProcessor.convert_external_data_to_image(
                external_data, image_width, image_height
            )
            
            # 合并BGR和Alpha
            bgra_image = None
            if bgr_image is not None and alpha_image is not None:
                temp_alpha = alpha_image.reshape([*alpha_image.shape, 1])
                bgra_image = np.concatenate([bgr_image, temp_alpha], 2)
            
            elapsed_time = (time.time() - start_time) * 1000
            logger.debug(f"获取图层数据耗时: {elapsed_time:.2f}ms")
            
            return bgr_image, alpha_image, bgra_image
            
        except Exception as e:
            logger.error(f"获取图层数据失败: {str(e)}")
            return None, None, None
    
    def _get_external_id(self, canvas_id: int, layer_id: int) -> Optional[str]:
        """获取外部ID"""
        if not self.sqlite_handler:
            return None
        
        try:
            # 查找图层
            layer_data = None
            for layer in self.sqlite_handler.layer_list:
                if layer['main_id'] == layer_id and layer['canvas_id'] == canvas_id:
                    layer_data = layer
                    break
            
            if layer_data is None:
                logger.warning(f"未找到图层 (Canvas: {canvas_id}, Layer: {layer_id})")
                return None
            
            # 查找Mipmap
            mipmap_data = None
            mipmap_id = layer_data['layer_render_mipmap']
            for mipmap in self.sqlite_handler.mipmap_list:
                if mipmap['main_id'] == mipmap_id:
                    mipmap_data = mipmap
                    break
            
            if mipmap_data is None:
                logger.warning(f"未找到Mipmap数据 (Mipmap ID: {mipmap_id})")
                return None
            
            # 查找MipmapInfo
            mipmap_info_data = None
            mipmap_info_id = mipmap_data['base_mipmap_info']
            for mipmap_info in self.sqlite_handler.mipmap_info_list:
                if mipmap_info['main_id'] == mipmap_info_id:
                    mipmap_info_data = mipmap_info
                    break
            
            if mipmap_info_data is None:
                logger.warning(f"未找到MipmapInfo数据 (MipmapInfo ID: {mipmap_info_id})")
                return None
            
            # 查找Offscreen
            offscreen_data = None
            offscreen_id = mipmap_info_data['offscreen']
            for offscreen in self.sqlite_handler.offscreen_list:
                if offscreen['main_id'] == offscreen_id:
                    offscreen_data = offscreen
                    break
            
            if offscreen_data is None:
                logger.warning(f"未找到Offscreen数据 (Offscreen ID: {offscreen_id})")
                return None
            
            return offscreen_data['block_data']
            
        except Exception as e:
            logger.error(f"获取外部ID失败: {str(e)}")
            return None
    
    def _get_layer_thumbnail(self, canvas_id: int, layer_id: int) -> Optional[Dict[str, Any]]:
        """获取图层缩略图信息"""
        if not self.sqlite_handler:
            return None
        
        for thumbnail in self.sqlite_handler.layer_thumbnail_list:
            if thumbnail['main_id'] == layer_id and thumbnail['canvas_id'] == canvas_id:
                return thumbnail
        
        return None
    
    def _get_external_data(self, external_id: str) -> Optional[bytes]:
        """获取外部数据"""
        if not self.file_parser:
            return None
        
        try:
            # 查找对应的块
            target_chunk = None
            for chunk in self.file_parser.chunk_external_list:
                if chunk['type'] != 'CHNKExta':
                    continue
                
                chunk_external_id = self.file_parser.get_external_id_from_chunk(chunk)
                if chunk_external_id == external_id:
                    target_chunk = chunk
                    break
            
            if target_chunk is None:
                logger.warning(f"未找到外部数据块 (External ID: {external_id})")
                return None
            
            # 获取外部数据
            external_data = ImageProcessor.get_external_data_from_chunk(
                target_chunk, self.file_parser.binary_data
            )
            
            return external_data
            
        except Exception as e:
            logger.error(f"获取外部数据失败: {str(e)}")
            return None
    
    def convert_to_png(self, output_path: str, merge_layers: bool = True) -> bool:
        """
        转换为PNG文件
        
        Args:
            output_path: 输出文件路径
            merge_layers: 是否合并所有图层
            
        Returns:
            转换是否成功
        """
        try:
            logger.info(f"开始转换为PNG: {output_path}")
            
            if merge_layers:
                return self._convert_merged_layers(output_path)
            else:
                return self._convert_single_layer(output_path)
                
        except Exception as e:
            logger.error(f"转换PNG失败: {str(e)}")
            return False
    
    def _convert_merged_layers(self, output_path: str) -> bool:
        """转换合并的图层"""
        try:
            # 获取画布信息
            canvas_info = self.get_canvas_info()
            canvas_width = canvas_info['width']
            canvas_height = canvas_info['height']
            
            # 获取所有图层数据
            layers_data = []
            layer_list = self.get_layer_list()

            # 过滤可见图层并按正确顺序排序
            visible_layers = []
            logger.info("分析图层信息:")

            for layer in layer_list:
                # 检查图层是否可见
                is_visible = layer.get('layer_visible', 1) != 0
                layer_type = layer.get('layer_type', 0)
                layer_opacity = layer.get('layer_opacity', 255)
                layer_index = layer.get('layer_index', layer.get('main_id', 0))

                logger.info(f"  图层: {layer['layer_name']} | 可见: {is_visible} | 类型: {layer_type} | 透明度: {layer_opacity} | 索引: {layer_index}")

                # 跳过隐藏图层和某些特殊类型的图层
                if not is_visible:
                    logger.debug(f"跳过隐藏图层: {layer['layer_name']}")
                    continue

                # 跳过文件夹图层等特殊类型
                if layer_type in [1, 2]:  # 1=文件夹, 2=参考图层等
                    logger.debug(f"跳过特殊类型图层: {layer['layer_name']} (type={layer_type})")
                    continue

                visible_layers.append(layer)

            # 按图层索引排序（从底层到顶层）
            visible_layers.sort(key=lambda x: x.get('layer_index', x.get('main_id', 0)))

            logger.info(f"处理 {len(visible_layers)}/{len(layer_list)} 个可见图层")

            for layer in visible_layers:
                canvas_id = layer['canvas_id']
                layer_id = layer['main_id']
                layer_name = layer['layer_name']
                layer_opacity = layer.get('layer_opacity', 255)

                logger.debug(f"处理图层: {layer_name} (透明度: {layer_opacity})")

                _, _, bgra_image = self.get_layer_data(canvas_id, layer_id)

                # 应用图层透明度
                if bgra_image is not None and layer_opacity < 255:
                    opacity_factor = layer_opacity / 255.0
                    bgra_image[:, :, 3] = (bgra_image[:, :, 3] * opacity_factor).astype(np.uint8)

                layers_data.append((layer_name, bgra_image))
            
            # 合并图层
            merged_image = ImageProcessor.merge_layers_to_canvas(
                layers_data, canvas_width, canvas_height
            )
            
            if merged_image is None:
                logger.error("图层合并失败")
                return False
            
            # 保存图像
            return ImageProcessor.save_image_as_png(merged_image, output_path)
            
        except Exception as e:
            logger.error(f"合并图层转换失败: {str(e)}")
            return False
    
    def _convert_single_layer(self, output_path: str) -> bool:
        """转换单个图层（暂未实现）"""
        logger.warning("单图层转换功能暂未实现")
        return False
    
    def cleanup(self) -> None:
        """清理资源"""
        if self.sqlite_handler:
            self.sqlite_handler.cleanup()
    
    def __del__(self):
        """析构函数"""
        self.cleanup()
