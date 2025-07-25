"""
CLIP文件解析器

负责解析Clip Studio Paint文件的二进制结构。
"""

import os
import struct
import copy
from typing import List, Dict, Any, Tuple, Optional
from loguru import logger

from .exceptions import InvalidFileError, DataProcessingError


class ClipFileParser:
    """CLIP文件解析器"""
    
    def __init__(self, filepath: str):
        """
        初始化文件解析器
        
        Args:
            filepath: CLIP文件路径
        """
        self.filepath = filepath
        self.chunk_external_list: List[Dict[str, Any]] = []
        self.binary_data: Optional[bytes] = None
        self.sqlite_binary_data: Optional[bytes] = None
        
        # 验证文件
        self._validate_file()
        
        # 解析文件
        self._parse_file()
    
    def _validate_file(self) -> None:
        """验证文件是否为有效的CLIP文件"""
        if not os.path.exists(self.filepath):
            raise InvalidFileError(self.filepath, "文件不存在")
        
        extension = os.path.splitext(self.filepath)[1].lower()
        if extension != '.clip':
            raise InvalidFileError(self.filepath, f"不是CLIP文件，扩展名为: {extension}")
    
    def _parse_file(self) -> None:
        """解析CLIP文件"""
        logger.debug(f"开始解析CLIP文件: {self.filepath}")
        
        try:
            # 读取块数据和二进制数据
            chunk_data_info = self._read_chunk_data()
            chunk_data_list = chunk_data_info[0]
            self.binary_data = chunk_data_info[1]
            self.sqlite_binary_data = chunk_data_info[2]
            
            # 提取外部块列表
            self.chunk_external_list = chunk_data_list[1:-2]
            
            logger.info(f"成功解析CLIP文件，找到 {len(self.chunk_external_list)} 个外部块")
            
        except Exception as e:
            raise DataProcessingError(f"解析CLIP文件失败: {str(e)}")
    
    def _read_chunk_data(self) -> Tuple[List[Dict[str, Any]], bytes, bytes]:
        """读取块数据"""
        chunk_data_list = []
        binary_data = None
        sqlite_binary_data = None
        
        logger.debug(f"读取块数据: {self.filepath}")
        
        try:
            with open(self.filepath, mode='rb') as binary_file:
                binary_data = binary_file.read()
                data_size = len(binary_data)
                
                offset = 0
                
                # 8字节：魔术数字
                csf_magic_number = struct.unpack_from('8s', binary_data, offset)[0]
                csf_magic_number = csf_magic_number.decode()
                offset += 8
                logger.debug(f"CSF魔术数字: {csf_magic_number}")
                
                if not csf_magic_number.startswith('CSFCHUNK'):
                    raise InvalidFileError(self.filepath, f"无效的魔术数字: {csf_magic_number}")
                
                # 16字节：跳过
                offset += 16
                
                while offset < data_size:
                    # 块开始位置
                    chunk_start_position = offset
                    
                    # 8字节：块类型
                    chunk_type = struct.unpack_from('8s', binary_data, offset)[0]
                    chunk_type = chunk_type.decode()
                    offset += 8
                    
                    # 大端序8字节：块大小
                    chunk_size = struct.unpack_from('>Q', binary_data, offset)[0]
                    offset += 8
                    
                    # 跳过块大小
                    offset += chunk_size
                    
                    # 块结束位置
                    chunk_end_position = offset
                    
                    chunk_data = {
                        'type': chunk_type,
                        'size': chunk_size,
                        'chunk_start_position': chunk_start_position,
                        'chunk_end_position': chunk_end_position,
                    }
                    chunk_data_list.append(chunk_data)
                    
                    logger.debug(f"找到块: {chunk_data}")
                
                # 确认SQLite块开始位置
                sqlite_chunk_start_position = 0
                for chunk_info in chunk_data_list:
                    if chunk_info['type'] == 'CHNKSQLi':
                        sqlite_chunk_start_position = chunk_info['chunk_start_position']
                        break
                
                if sqlite_chunk_start_position == 0:
                    raise DataProcessingError("未找到SQLite块")
                
                sqlite_offset = sqlite_chunk_start_position + 16
                
                # 保存SQLite文件
                sqlite_binary_data = copy.deepcopy(binary_data[sqlite_offset:])
                
        except (struct.error, UnicodeDecodeError) as e:
            raise InvalidFileError(self.filepath, f"文件格式错误: {str(e)}")
        except Exception as e:
            raise DataProcessingError(f"读取块数据失败: {str(e)}")
        
        return chunk_data_list, binary_data, sqlite_binary_data
    
    def get_external_id_from_chunk(self, chunk_data: Dict[str, Any]) -> str:
        """从块中获取外部ID"""
        if not self.binary_data:
            raise DataProcessingError("二进制数据未初始化")
        
        try:
            offset = chunk_data['chunk_start_position']
            
            # 16字节：跳过
            offset += 16
            
            # 大端序8字节：块大小
            chunk_size = struct.unpack_from('>Q', self.binary_data, offset)[0]
            offset += 8
            
            # 读取External ID
            external_id = struct.unpack_from(
                str(chunk_size) + 's', self.binary_data, offset)[0]
            external_id = external_id.decode()
            
            return external_id
            
        except Exception as e:
            raise DataProcessingError(f"获取外部ID失败: {str(e)}")
