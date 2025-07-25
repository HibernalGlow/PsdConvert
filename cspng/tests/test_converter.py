"""
转换器测试
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from cspng.core.converter import CspConverter
from cspng.core.exceptions import CspngError, InvalidFileError


class TestCspConverter:
    """CspConverter测试类"""
    
    def test_init_with_invalid_file(self):
        """测试无效文件初始化"""
        with pytest.raises(InvalidFileError):
            CspConverter("nonexistent.clip")
    
    def test_init_with_wrong_extension(self, tmp_path):
        """测试错误扩展名"""
        # 创建一个非CLIP文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        
        with pytest.raises(InvalidFileError):
            CspConverter(str(test_file))
    
    @patch('cspng.core.converter.ClipFileParser')
    @patch('cspng.core.converter.SqliteHandler')
    def test_successful_init(self, mock_sqlite, mock_parser, tmp_path):
        """测试成功初始化"""
        # 创建一个CLIP文件
        test_file = tmp_path / "test.clip"
        test_file.write_bytes(b"CSFCHUNK" + b"\x00" * 100)
        
        # 模拟解析器
        mock_parser_instance = Mock()
        mock_parser_instance.sqlite_binary_data = b"test_sqlite_data"
        mock_parser.return_value = mock_parser_instance
        
        # 模拟SQLite处理器
        mock_sqlite_instance = Mock()
        mock_sqlite.return_value = mock_sqlite_instance
        
        # 创建转换器
        converter = CspConverter(str(test_file))
        
        # 验证调用
        mock_parser.assert_called_once_with(str(test_file))
        mock_sqlite.assert_called_once_with(b"test_sqlite_data")
        
        assert converter.file_parser == mock_parser_instance
        assert converter.sqlite_handler == mock_sqlite_instance
    
    def test_get_canvas_info_no_handler(self):
        """测试没有SQLite处理器时获取画布信息"""
        with patch('cspng.core.converter.ClipFileParser'), \
             patch('cspng.core.converter.SqliteHandler'):
            
            converter = CspConverter.__new__(CspConverter)
            converter.sqlite_handler = None
            
            with pytest.raises(CspngError):
                converter.get_canvas_info()
    
    @patch('cspng.core.converter.ClipFileParser')
    @patch('cspng.core.converter.SqliteHandler')
    def test_get_canvas_info_success(self, mock_sqlite, mock_parser, tmp_path):
        """测试成功获取画布信息"""
        test_file = tmp_path / "test.clip"
        test_file.write_bytes(b"CSFCHUNK" + b"\x00" * 100)
        
        # 模拟SQLite处理器
        mock_sqlite_instance = Mock()
        mock_sqlite_instance.canvas_preview_list = [{
            'image_width': 1920,
            'image_height': 1080,
            'canvas_id': 1
        }]
        mock_sqlite.return_value = mock_sqlite_instance
        
        converter = CspConverter(str(test_file))
        canvas_info = converter.get_canvas_info()
        
        assert canvas_info['width'] == 1920
        assert canvas_info['height'] == 1080
        assert canvas_info['canvas_id'] == 1
    
    @patch('cspng.core.converter.ClipFileParser')
    @patch('cspng.core.converter.SqliteHandler')
    def test_get_layer_list(self, mock_sqlite, mock_parser, tmp_path):
        """测试获取图层列表"""
        test_file = tmp_path / "test.clip"
        test_file.write_bytes(b"CSFCHUNK" + b"\x00" * 100)
        
        # 模拟图层数据
        mock_layers = [
            {'main_id': 1, 'layer_name': 'Layer 1'},
            {'main_id': 2, 'layer_name': 'Layer 2'}
        ]
        
        mock_sqlite_instance = Mock()
        mock_sqlite_instance.layer_list = mock_layers
        mock_sqlite.return_value = mock_sqlite_instance
        
        converter = CspConverter(str(test_file))
        layers = converter.get_layer_list()
        
        assert len(layers) == 2
        assert layers[0]['layer_name'] == 'Layer 1'
        assert layers[1]['layer_name'] == 'Layer 2'


if __name__ == "__main__":
    pytest.main([__file__])
