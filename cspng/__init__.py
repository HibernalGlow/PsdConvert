"""
CSPNG - Clip Studio Paint to PNG Converter

一个用于将Clip Studio Paint (.clip) 文件转换为PNG格式的Python包。
支持图层合并、批量处理等功能。
"""

__version__ = "1.0.0"
__author__ = "CSPNG Team"
__description__ = "Clip Studio Paint to PNG Converter"

try:
    from .core.converter import CspConverter
    from .core.exceptions import CspngError, FileNotFoundError, InvalidFileError
except ImportError:
    # 如果导入失败，至少保证版本信息可用
    CspConverter = None
    CspngError = None
    FileNotFoundError = None
    InvalidFileError = None

__all__ = [
    "CspConverter",
    "CspngError",
    "FileNotFoundError",
    "InvalidFileError",
    "__version__",
]
