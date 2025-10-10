"""
SQLite数据处理器

负责处理CLIP文件中的SQLite数据库。
"""

import os
import sqlite3
import tempfile
from typing import List, Dict, Any, Optional
from loguru import logger

from .exceptions import SqliteError, DataProcessingError


class SqliteHandler:
    """SQLite数据处理器"""
    
    def __init__(self, sqlite_binary_data: bytes):
        """
        初始化SQLite处理器
        
        Args:
            sqlite_binary_data: SQLite二进制数据
        """
        self.sqlite_binary_data = sqlite_binary_data
        self.temp_db_file: Optional[str] = None
        
        # 解析数据
        self._parse_sqlite_data()
    
    def _parse_sqlite_data(self) -> None:
        """解析SQLite数据"""
        logger.debug("开始解析SQLite数据")
        
        try:
            # 创建临时数据库文件
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
                self.temp_db_file = f.name
                f.write(self.sqlite_binary_data)
            
            # 连接数据库并读取数据
            with sqlite3.connect(self.temp_db_file) as conn:
                self.canvas_preview_list = self._read_canvas_preview(conn)
                self.layer_list = self._read_layers(conn)
                self.layer_thumbnail_list = self._read_layer_thumbnails(conn)
                self.offscreen_list = self._read_offscreen(conn)
                self.mipmap_list = self._read_mipmap(conn)
                self.mipmap_info_list = self._read_mipmap_info(conn)
            
            logger.info(f"成功解析SQLite数据: {len(self.layer_list)} 个图层")
            
        except Exception as e:
            raise SqliteError(f"解析SQLite数据失败: {str(e)}")
    
    def _execute_query(self, conn: sqlite3.Connection, query: str) -> List[tuple]:
        """执行SQLite查询"""
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            raise SqliteError(f"执行查询失败: {query} - {str(e)}")
    
    def _read_canvas_preview(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """读取画布预览数据"""
        logger.debug("读取画布预览数据")
        
        canvas_preview_list = []
        query = "SELECT MainId, CanvasId, ImageData, ImageWidth, ImageHeight FROM CanvasPreview;"
        
        try:
            results = self._execute_query(conn, query)
            for result in results:
                canvas_preview_data = {
                    'main_id': result[0],
                    'canvas_id': result[1],
                    'image_data': result[2],
                    'image_width': result[3],
                    'image_height': result[4],
                }
                canvas_preview_list.append(canvas_preview_data)
                
                logger.debug(f"画布预览: ID={result[0]}, 尺寸={result[3]}x{result[4]}")
                
        except Exception as e:
            logger.warning(f"读取画布预览数据失败: {str(e)}")
        
        return canvas_preview_list
    
    def _read_layers(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """读取图层数据"""
        logger.debug("读取图层数据")
        
        layer_list = []
        # 先尝试获取所有可能的字段，如果失败则使用基本字段
        try:
            query = """
            SELECT MainId, CanvasId, LayerName, LayerUuid, LayerRenderMipmap,
                   LayerRenderThumbnail, LayerNextIndex, LayerFirstChildIndex, LayerType,
                   LayerVisible, LayerOpacity, LayerBlendMode, LayerIndex
            FROM Layer
            ORDER BY CASE WHEN LayerIndex IS NOT NULL THEN LayerIndex ELSE MainId END ASC;
            """
            results = self._execute_query(conn, query)
        except:
            # 如果扩展字段不存在，使用基本查询
            logger.debug("使用基本图层查询（扩展字段不可用）")
            query = """
            SELECT MainId, CanvasId, LayerName, LayerUuid, LayerRenderMipmap,
                   LayerRenderThumbnail, LayerNextIndex, LayerFirstChildIndex, LayerType
            FROM Layer
            ORDER BY MainId ASC;
            """
            results = self._execute_query(conn, query)
        
        try:
            for result in results:
                layer_data = {
                    'main_id': result[0],
                    'canvas_id': result[1],
                    'layer_name': result[2],
                    'layer_uuid': result[3],
                    'layer_render_mipmap': result[4],
                    'layer_render_thumbnail': result[5],
                    'layer_next_index': result[6],
                    'layer_first_child_index': result[7],
                    'layer_type': result[8],
                    'layer_visible': result[9] if len(result) > 9 else 1,  # 默认可见
                    'layer_opacity': result[10] if len(result) > 10 else 255,  # 默认不透明
                    'layer_blend_mode': result[11] if len(result) > 11 else 0,  # 默认正常混合
                    'layer_index': result[12] if len(result) > 12 else 0,  # 默认索引
                }
                layer_list.append(layer_data)
                
                logger.debug(f"图层: {result[2]} (ID={result[0]}, Type={result[8]})")
                
        except Exception as e:
            raise SqliteError(f"读取图层数据失败: {str(e)}")
        
        return layer_list
    
    def _read_layer_thumbnails(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """读取图层缩略图数据"""
        logger.debug("读取图层缩略图数据")
        
        layer_thumbnail_list = []
        query = """
        SELECT MainId, CanvasId, LayerId, ThumbnailCanvasWidth, 
               ThumbnailCanvasHeight, ThumbnailOffscreen 
        FROM LayerThumbnail;
        """
        
        try:
            results = self._execute_query(conn, query)
            for result in results:
                layer_thumbnail_data = {
                    'main_id': result[0],
                    'canvas_id': result[1],
                    'layer_id': result[2],
                    'thumbnail_canvas_width': result[3],
                    'thumbnail_canvas_height': result[4],
                    'thumbnail_offscreen': result[5],
                }
                layer_thumbnail_list.append(layer_thumbnail_data)
                
        except Exception as e:
            logger.warning(f"读取图层缩略图数据失败: {str(e)}")
        
        return layer_thumbnail_list
    
    def _read_offscreen(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """读取离屏数据"""
        logger.debug("读取离屏数据")
        
        offscreen_list = []
        query = "SELECT MainId, CanvasId, LayerId, BlockData FROM Offscreen;"
        
        try:
            results = self._execute_query(conn, query)
            for result in results:
                offscreen_data = {
                    'main_id': result[0],
                    'canvas_id': result[1],
                    'layer_id': result[2],
                    'block_data': result[3].decode() if result[3] else '',
                }
                offscreen_list.append(offscreen_data)
                
        except Exception as e:
            logger.warning(f"读取离屏数据失败: {str(e)}")
        
        return offscreen_list
    
    def _read_mipmap(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """读取Mipmap数据"""
        logger.debug("读取Mipmap数据")
        
        mipmap_list = []
        query = "SELECT MainId, CanvasId, LayerId, MipmapCount, BaseMipmapInfo FROM Mipmap;"
        
        try:
            results = self._execute_query(conn, query)
            for result in results:
                mipmap_data = {
                    'main_id': result[0],
                    'canvas_id': result[1],
                    'layer_id': result[2],
                    'mipmap_count': result[3],
                    'base_mipmap_info': result[4],
                }
                mipmap_list.append(mipmap_data)
                
        except Exception as e:
            logger.warning(f"读取Mipmap数据失败: {str(e)}")
        
        return mipmap_list
    
    def _read_mipmap_info(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """读取MipmapInfo数据"""
        logger.debug("读取MipmapInfo数据")
        
        mipmap_info_list = []
        query = "SELECT MainId, CanvasId, LayerId, ThisScale, Offscreen, NextIndex FROM MipmapInfo;"
        
        try:
            results = self._execute_query(conn, query)
            for result in results:
                mipmap_info_data = {
                    'main_id': result[0],
                    'canvas_id': result[1],
                    'layer_id': result[2],
                    'this_scale': result[3],
                    'offscreen': result[4],
                    'next_index': result[5],
                }
                mipmap_info_list.append(mipmap_info_data)
                
        except Exception as e:
            logger.warning(f"读取MipmapInfo数据失败: {str(e)}")
        
        return mipmap_info_list
    
    def cleanup(self) -> None:
        """清理临时文件"""
        if self.temp_db_file and os.path.exists(self.temp_db_file):
            try:
                # 强制关闭可能的数据库连接
                import gc
                gc.collect()

                # 尝试删除文件
                os.remove(self.temp_db_file)
                logger.debug(f"已删除临时数据库文件: {self.temp_db_file}")
            except PermissionError:
                # Windows上可能出现文件被占用的情况，延迟删除
                logger.debug(f"临时数据库文件被占用，将在程序退出时删除: {self.temp_db_file}")
                import atexit
                atexit.register(lambda: self._force_delete(self.temp_db_file))
            except Exception as e:
                logger.warning(f"删除临时数据库文件失败: {str(e)}")

    def _force_delete(self, filepath: str) -> None:
        """强制删除文件"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except:
            pass  # 静默忽略删除失败
    
    def __del__(self):
        """析构函数，确保清理临时文件"""
        self.cleanup()
