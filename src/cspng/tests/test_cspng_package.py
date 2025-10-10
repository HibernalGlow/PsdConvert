#!/usr/bin/env python
"""
CSPNG包测试脚本

验证新的独立包结构是否正常工作。
"""

import sys
import subprocess
from pathlib import Path

def test_package_import():
    """测试包导入"""
    print("🧪 测试包导入...")
    
    try:
        # 添加包路径
        sys.path.insert(0, str(Path("cspng")))
        
        # 测试基本导入
        import cspng
        print(f"✅ 成功导入cspng包，版本: {cspng.__version__}")
        
        # 测试核心组件导入
        from cspng.core.converter import CspConverter
        from cspng.core.exceptions import CspngError
        from cspng.core.file_parser import ClipFileParser
        from cspng.core.sqlite_handler import SqliteHandler
        from cspng.core.image_processor import ImageProcessor
        print("✅ 成功导入所有核心组件")
        
        # 测试CLI导入
        from cspng.cli.main import app
        print("✅ 成功导入CLI组件")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False


def test_cli_commands():
    """测试CLI命令"""
    print("\n🧪 测试CLI命令...")
    
    commands = [
        (["version"], "版本命令"),
        (["--help"], "帮助命令"),
        (["convert", "--help"], "转换命令帮助"),
        (["info", "--help"], "信息命令帮助"),
        (["batch", "--help"], "批量命令帮助"),
    ]
    
    success_count = 0
    
    for cmd_args, desc in commands:
        try:
            # 构建完整命令
            cmd_list = ', '.join([f'"{arg}"' for arg in cmd_args])
            full_cmd = f'python -c "import sys; sys.path.insert(0, \'cspng\'); from cspng.cli.main import app; app([{cmd_list}])"'

            result = subprocess.run(
                full_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(f"✅ {desc} - 成功")
                success_count += 1
            else:
                print(f"❌ {desc} - 失败")
                print(f"   错误: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"❌ {desc} - 超时")
        except Exception as e:
            print(f"❌ {desc} - 异常: {e}")
    
    print(f"CLI测试结果: {success_count}/{len(commands)} 成功")
    return success_count == len(commands)


def test_package_structure():
    """测试包结构"""
    print("\n🧪 测试包结构...")
    
    required_files = [
        "cspng/__init__.py",
        "cspng/__main__.py",
        "cspng/core/__init__.py",
        "cspng/core/converter.py",
        "cspng/core/file_parser.py",
        "cspng/core/sqlite_handler.py",
        "cspng/core/image_processor.py",
        "cspng/core/exceptions.py",
        "cspng/cli/__init__.py",
        "cspng/cli/main.py",
        "cspng/README.md",
        "cspng/tests/__init__.py",
        "cspng/tests/test_converter.py",
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ 缺少以下文件:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    else:
        print(f"✅ 所有 {len(required_files)} 个必需文件都存在")
        return True


def test_exception_hierarchy():
    """测试异常层次结构"""
    print("\n🧪 测试异常层次结构...")
    
    try:
        sys.path.insert(0, str(Path("cspng")))
        from cspng.core.exceptions import (
            CspngError, 
            FileNotFoundError, 
            InvalidFileError,
            DataProcessingError,
            SqliteError,
            ImageProcessingError
        )
        
        # 测试异常继承
        assert issubclass(FileNotFoundError, CspngError)
        assert issubclass(InvalidFileError, CspngError)
        assert issubclass(DataProcessingError, CspngError)
        assert issubclass(SqliteError, CspngError)
        assert issubclass(ImageProcessingError, CspngError)
        
        print("✅ 异常层次结构正确")
        return True
        
    except Exception as e:
        print(f"❌ 异常层次结构测试失败: {e}")
        return False


def test_module_independence():
    """测试模块独立性"""
    print("\n🧪 测试模块独立性...")
    
    try:
        sys.path.insert(0, str(Path("cspng")))
        
        # 测试各模块可以独立导入
        from cspng.core import exceptions
        from cspng.core import file_parser
        from cspng.core import sqlite_handler
        from cspng.core import image_processor
        
        print("✅ 所有核心模块可以独立导入")
        return True
        
    except Exception as e:
        print(f"❌ 模块独立性测试失败: {e}")
        return False


def main():
    """主函数"""
    print("🎨 CSPNG包测试")
    print("=" * 50)
    
    tests = [
        ("包结构", test_package_structure),
        ("包导入", test_package_import),
        ("CLI命令", test_cli_commands),
        ("异常层次", test_exception_hierarchy),
        ("模块独立性", test_module_independence),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed_tests += 1
        except Exception as e:
            print(f"❌ 测试 '{test_name}' 发生异常: {e}")
    
    print(f"\n{'='*50}")
    print(f"测试结果: {passed_tests}/{total_tests} 通过")
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过！CSPNG包已成功迁移为独立包")
        print("\n✨ 新包特性:")
        print("  ✅ 分模块架构 - 清晰的代码组织")
        print("  ✅ 现代CLI - 基于typer和rich")
        print("  ✅ 完善日志 - 使用loguru")
        print("  ✅ 异常处理 - 完整的异常体系")
        print("  ✅ 类型提示 - 更好的代码质量")
        print("  ✅ 测试支持 - 包含测试框架")
        
        print("\n🚀 使用方法:")
        print("  python -c \"import sys; sys.path.insert(0, 'cspng'); from cspng.cli.main import app; app(['convert', 'input.clip'])\"")
        print("  或者安装后: cspng convert input.clip")
        
    else:
        print("❌ 部分测试失败，请检查包结构")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
