#!/usr/bin/env python
"""
CSPNG使用示例

演示如何使用CSPNG包进行CLIP文件转换。
"""

import sys
from pathlib import Path
from loguru import logger

# 添加cspng包路径
sys.path.insert(0, str(Path(__file__).parent / "cspng"))

try:
    from cspng import CspConverter
    from cspng.core.exceptions import CspngError
except ImportError as e:
    print(f"导入错误: {e}")
    print("请先运行 python install_cspng.py 安装包")
    sys.exit(1)


def example_basic_conversion():
    """基本转换示例"""
    print("📝 示例1: 基本转换")
    print("-" * 30)
    
    # 假设有一个CLIP文件
    clip_file = "example.clip"
    output_file = "output.png"
    
    try:
        # 创建转换器
        converter = CspConverter(clip_file)
        
        # 获取文件信息
        canvas_info = converter.get_canvas_info()
        layer_list = converter.get_layer_list()
        
        print(f"画布尺寸: {canvas_info['width']}x{canvas_info['height']}")
        print(f"图层数量: {len(layer_list)}")
        
        # 显示图层信息
        for i, layer in enumerate(layer_list, 1):
            print(f"  {i}. {layer['layer_name']} (ID: {layer['main_id']})")
        
        # 转换为PNG
        success = converter.convert_to_png(output_file, merge_layers=True)
        
        if success:
            print(f"✅ 转换成功: {output_file}")
        else:
            print("❌ 转换失败")
        
        # 清理资源
        converter.cleanup()
        
    except CspngError as e:
        print(f"转换错误: {e}")
    except FileNotFoundError:
        print(f"文件不存在: {clip_file}")
        print("请提供一个有效的CLIP文件路径")


def example_batch_processing():
    """批量处理示例"""
    print("\n📝 示例2: 批量处理")
    print("-" * 30)
    
    input_dir = Path("clip_files")
    output_dir = Path("png_output")
    
    # 创建输出目录
    output_dir.mkdir(exist_ok=True)
    
    # 查找所有CLIP文件
    clip_files = list(input_dir.glob("*.clip"))
    
    if not clip_files:
        print(f"在 {input_dir} 中未找到CLIP文件")
        return
    
    print(f"找到 {len(clip_files)} 个CLIP文件")
    
    success_count = 0
    
    for clip_file in clip_files:
        try:
            print(f"处理: {clip_file.name}")
            
            # 创建转换器
            converter = CspConverter(str(clip_file))
            
            # 生成输出文件名
            output_file = output_dir / clip_file.with_suffix('.png').name
            
            # 转换
            success = converter.convert_to_png(str(output_file))
            
            if success:
                success_count += 1
                print(f"  ✅ 成功")
            else:
                print(f"  ❌ 失败")
            
            # 清理
            converter.cleanup()
            
        except Exception as e:
            print(f"  ❌ 错误: {e}")
    
    print(f"\n批量处理完成: {success_count}/{len(clip_files)} 成功")


def example_layer_analysis():
    """图层分析示例"""
    print("\n📝 示例3: 图层分析")
    print("-" * 30)
    
    clip_file = "example.clip"
    
    try:
        converter = CspConverter(clip_file)
        
        # 获取图层列表
        layer_list = converter.get_layer_list()
        
        print("图层详细信息:")
        for layer in layer_list:
            print(f"  名称: {layer['layer_name']}")
            print(f"  ID: {layer['main_id']}")
            print(f"  类型: {layer.get('layer_type', 'N/A')}")
            print(f"  画布ID: {layer['canvas_id']}")
            
            # 尝试获取图层数据
            try:
                bgr, alpha, bgra = converter.get_layer_data(
                    layer['canvas_id'], 
                    layer['main_id']
                )
                
                if bgra is not None:
                    height, width = bgra.shape[:2]
                    print(f"  尺寸: {width}x{height}")
                else:
                    print(f"  尺寸: 无数据")
                    
            except Exception as e:
                print(f"  尺寸: 获取失败 ({e})")
            
            print()
        
        converter.cleanup()
        
    except Exception as e:
        print(f"分析失败: {e}")


def example_custom_logging():
    """自定义日志示例"""
    print("\n📝 示例4: 自定义日志")
    print("-" * 30)
    
    # 配置loguru日志
    logger.remove()  # 移除默认配置
    logger.add(
        sys.stderr,
        level="DEBUG",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"
    )
    logger.add(
        "cspng_conversion.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        rotation="10 MB"
    )
    
    print("已配置详细日志记录")
    print("日志将输出到控制台和 cspng_conversion.log 文件")


def main():
    """主函数"""
    print("🎨 CSPNG使用示例")
    print("=" * 50)
    
    # 运行示例
    example_basic_conversion()
    example_batch_processing()
    example_layer_analysis()
    example_custom_logging()
    
    print("\n💡 提示:")
    print("1. 确保有有效的CLIP文件进行测试")
    print("2. 使用 'cspng --help' 查看命令行选项")
    print("3. 查看 README.md 了解更多用法")


if __name__ == "__main__":
    main()
