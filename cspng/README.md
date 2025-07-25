# CSPNG - Clip Studio Paint to PNG Converter

🎨 一个用于将Clip Studio Paint (.clip) 文件转换为PNG格式的Python包。

## 特性

- ✅ **完整的图层合并**: 将所有图层合并为单个PNG文件
- ✅ **分模块架构**: 清晰的代码结构，易于维护和扩展
- ✅ **现代命令行界面**: 基于typer和rich的美观CLI
- ✅ **详细的日志记录**: 使用loguru提供丰富的日志信息
- ✅ **批量处理**: 支持批量转换多个文件
- ✅ **文件信息查看**: 分析并显示CLIP文件详细信息
- ✅ **错误处理**: 完善的异常处理和用户友好的错误信息

## 安装

### 从源码安装

```bash
# 克隆仓库
git clone https://github.com/your-username/cspng.git
cd cspng

# 安装依赖
pip install -e .

# 或者安装开发依赖
pip install -e ".[dev]"
```

### 使用pip安装（如果发布到PyPI）

```bash
pip install cspng
```

## 使用方法

### 命令行使用

#### 基本转换

```bash
# 转换单个文件
cspng convert artwork.clip

# 指定输出文件名
cspng convert artwork.clip -o result.png

# 强制覆盖已存在的文件
cspng convert artwork.clip -f

# 显示详细日志
cspng convert artwork.clip -v

# 静默模式
cspng convert artwork.clip -q
```

#### 查看文件信息

```bash
# 显示基本信息
cspng info artwork.clip

# 显示详细信息
cspng info artwork.clip -v
```

#### 批量转换

```bash
# 转换目录中的所有CLIP文件
cspng batch /path/to/clip/files

# 递归处理子目录
cspng batch /path/to/clip/files -r

# 指定输出目录
cspng batch /path/to/clip/files -o /path/to/output

# 强制覆盖已存在的文件
cspng batch /path/to/clip/files -f
```

#### 其他命令

```bash
# 显示版本信息
cspng version

# 显示帮助
cspng --help
cspng convert --help
```

### Python API使用

```python
from cspng import CspConverter

# 创建转换器
converter = CspConverter("artwork.clip")

# 获取文件信息
canvas_info = converter.get_canvas_info()
print(f"画布尺寸: {canvas_info['width']}x{canvas_info['height']}")

layer_list = converter.get_layer_list()
print(f"图层数量: {len(layer_list)}")

# 转换为PNG
success = converter.convert_to_png("output.png", merge_layers=True)
if success:
    print("转换成功!")

# 清理资源
converter.cleanup()
```

## 架构设计

```
cspng/
├── __init__.py          # 包初始化
├── __main__.py          # 主入口点
├── core/                # 核心模块
│   ├── __init__.py
│   ├── converter.py     # 主转换器
│   ├── file_parser.py   # CLIP文件解析器
│   ├── sqlite_handler.py # SQLite数据处理器
│   ├── image_processor.py # 图像处理器
│   └── exceptions.py    # 异常定义
└── cli/                 # 命令行接口
    ├── __init__.py
    └── main.py          # CLI主程序
```

### 核心组件

- **CspConverter**: 主转换器，整合所有功能
- **ClipFileParser**: 解析CLIP文件的二进制结构
- **SqliteHandler**: 处理CLIP文件中的SQLite数据库
- **ImageProcessor**: 处理图像数据的提取和合并
- **CLI**: 基于typer的现代命令行界面

## 依赖项

- **numpy**: 数组和数值计算
- **opencv-python**: 图像处理
- **typer**: 现代CLI框架
- **rich**: 美观的终端输出
- **loguru**: 现代日志记录

## 开发

### 设置开发环境

```bash
# 克隆仓库
git clone https://github.com/your-username/cspng.git
cd cspng

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装开发依赖
pip install -e ".[dev]"
```

### 代码质量

```bash
# 代码格式化
black cspng/
isort cspng/

# 代码检查
flake8 cspng/
mypy cspng/

# 运行测试
pytest
```

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件。

## 贡献

欢迎贡献代码！请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 更新日志

### v1.0.0
- 初始版本
- 支持CLIP到PNG转换
- 图层合并功能
- 现代CLI界面
- 批量处理支持

## 支持

如果遇到问题，请在 [GitHub Issues](https://github.com/your-username/cspng/issues) 中报告。
