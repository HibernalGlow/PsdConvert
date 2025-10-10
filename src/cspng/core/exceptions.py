"""
CSPNG异常类定义

定义了包中使用的所有自定义异常类。
"""


class CspngError(Exception):
    """CSPNG包的基础异常类"""
    pass


class FileNotFoundError(CspngError):
    """文件未找到异常"""
    def __init__(self, filepath: str):
        self.filepath = filepath
        super().__init__(f"文件未找到: {filepath}")


class InvalidFileError(CspngError):
    """无效文件异常"""
    def __init__(self, filepath: str, reason: str = ""):
        self.filepath = filepath
        self.reason = reason
        message = f"无效的文件: {filepath}"
        if reason:
            message += f" - {reason}"
        super().__init__(message)


class DataProcessingError(CspngError):
    """数据处理异常"""
    def __init__(self, message: str, layer_name: str = None):
        self.layer_name = layer_name
        if layer_name:
            message = f"处理图层 '{layer_name}' 时发生错误: {message}"
        super().__init__(message)


class SqliteError(CspngError):
    """SQLite数据库操作异常"""
    pass


class ImageProcessingError(CspngError):
    """图像处理异常"""
    pass
