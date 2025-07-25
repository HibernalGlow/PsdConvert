"""
CSPNG命令行主程序

使用typer构建的命令行接口。
"""

import os
import sys
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import print as rprint
from loguru import logger

from ..core.converter import CspConverter
from ..core.exceptions import CspngError
from .. import __version__

# 创建typer应用
app = typer.Typer(
    name="cspng",
    help="Clip Studio Paint to PNG Converter - 将CLIP文件转换为PNG格式",
    add_completion=False,
    rich_markup_mode="rich"
)

# 创建控制台对象
console = Console()


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """设置日志配置"""
    # 移除默认的logger
    logger.remove()
    
    if quiet:
        # 静默模式，只记录错误
        logger.add(sys.stderr, level="ERROR", format="<red>错误</red>: {message}")
    elif verbose:
        # 详细模式
        logger.add(
            sys.stderr, 
            level="DEBUG",
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"
        )
    else:
        # 正常模式
        logger.add(
            sys.stderr,
            level="INFO", 
            format="<level>{level}</level>: {message}"
        )


@app.command()
def convert(
    input_file: Path = typer.Argument(
        ...,
        help="输入的CLIP文件路径",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True
    ),
    output: Optional[Path] = typer.Option(
        None,
        "-o", "--output",
        help="输出PNG文件路径（默认为输入文件名.png）"
    ),
    merge_layers: bool = typer.Option(
        True,
        "--merge/--no-merge",
        help="是否合并所有图层（默认：合并）"
    ),
    verbose: bool = typer.Option(
        False,
        "-v", "--verbose",
        help="显示详细日志"
    ),
    quiet: bool = typer.Option(
        False,
        "-q", "--quiet", 
        help="静默模式，只显示错误"
    ),
    force: bool = typer.Option(
        False,
        "-f", "--force",
        help="强制覆盖已存在的输出文件"
    )
):
    """
    转换CLIP文件为PNG格式

    将Clip Studio Paint文件转换为PNG图像。默认会合并所有图层为单个PNG文件。

    示例:

        cspng convert artwork.clip                    # 转换为artwork.png
        cspng convert artwork.clip -o result.png     # 指定输出文件名
        cspng convert artwork.clip --no-merge        # 不合并图层（暂未实现）
    """
    # 设置日志
    setup_logging(verbose, quiet)
    
    # 验证输入文件
    if not input_file.suffix.lower() == '.clip':
        rprint(f"[red]错误[/red]: 输入文件必须是.clip格式，当前为: {input_file.suffix}")
        raise typer.Exit(1)
    
    # 确定输出文件路径
    if output is None:
        output = input_file.with_suffix('.png')
    
    # 检查输出文件是否存在
    if output.exists() and not force:
        rprint(f"[yellow]警告[/yellow]: 输出文件已存在: {output}")
        if not typer.confirm("是否覆盖？"):
            rprint("操作已取消")
            raise typer.Exit(0)
    
    # 显示转换信息
    if not quiet:
        rprint(f"[blue]输入文件[/blue]: {input_file}")
        rprint(f"[blue]输出文件[/blue]: {output}")
        rprint(f"[blue]合并图层[/blue]: {'是' if merge_layers else '否'}")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            disable=quiet
        ) as progress:
            # 初始化转换器
            task = progress.add_task("正在初始化转换器...", total=None)
            converter = CspConverter(str(input_file))
            
            # 获取文件信息
            progress.update(task, description="正在分析文件...")
            canvas_info = converter.get_canvas_info()
            layer_list = converter.get_layer_list()
            
            if not quiet:
                progress.update(task, description="显示文件信息...")
                rprint(f"[green]画布尺寸[/green]: {canvas_info['width']}x{canvas_info['height']}")
                rprint(f"[green]图层数量[/green]: {len(layer_list)}")
            
            # 执行转换
            progress.update(task, description="正在转换...")
            success = converter.convert_to_png(str(output), merge_layers)
            
            progress.update(task, description="转换完成", completed=True)
        
        if success:
            rprint(f"[green]✓ 转换成功[/green]: {output}")
            
            # 显示文件大小
            if output.exists():
                file_size = output.stat().st_size
                size_mb = file_size / (1024 * 1024)
                rprint(f"[dim]文件大小: {size_mb:.2f} MB[/dim]")
        else:
            rprint("[red]✗ 转换失败[/red]")
            raise typer.Exit(1)
            
    except CspngError as e:
        rprint(f"[red]转换错误[/red]: {e}")
        raise typer.Exit(1)
    except Exception as e:
        logger.error(f"未预期的错误: {e}")
        rprint(f"[red]未预期的错误[/red]: {e}")
        raise typer.Exit(1)


@app.command()
def info(
    input_file: Path = typer.Argument(
        ...,
        help="输入的CLIP文件路径",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True
    ),
    verbose: bool = typer.Option(
        False,
        "-v", "--verbose",
        help="显示详细信息"
    )
):
    """
    显示CLIP文件信息

    分析并显示CLIP文件的详细信息，包括画布尺寸、图层列表等。
    """
    # 设置日志
    setup_logging(verbose, False)
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("正在分析文件...", total=None)
            
            converter = CspConverter(str(input_file))
            canvas_info = converter.get_canvas_info()
            layer_list = converter.get_layer_list()
            
            progress.update(task, description="分析完成", completed=True)
        
        # 显示基本信息
        rprint(f"\n[bold blue]文件信息[/bold blue]: {input_file.name}")
        rprint(f"[green]文件路径[/green]: {input_file}")
        rprint(f"[green]文件大小[/green]: {input_file.stat().st_size / (1024*1024):.2f} MB")
        rprint(f"[green]画布尺寸[/green]: {canvas_info['width']} × {canvas_info['height']} 像素")
        rprint(f"[green]图层数量[/green]: {len(layer_list)}")
        
        # 显示图层列表
        if layer_list:
            rprint(f"\n[bold blue]图层列表[/bold blue]:")
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("ID", style="dim", width=6)
            table.add_column("名称", style="cyan")
            table.add_column("类型", style="green", width=8)
            table.add_column("画布ID", style="dim", width=8)
            
            for layer in layer_list:
                table.add_row(
                    str(layer['main_id']),
                    layer['layer_name'],
                    str(layer.get('layer_type', 'N/A')),
                    str(layer['canvas_id'])
                )
            
            console.print(table)
        
        if verbose:
            rprint(f"\n[dim]画布ID: {canvas_info['canvas_id']}[/dim]")
            
    except CspngError as e:
        rprint(f"[red]分析错误[/red]: {e}")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]未预期的错误[/red]: {e}")
        raise typer.Exit(1)


@app.command()
def batch(
    input_dir: Path = typer.Argument(
        ...,
        help="包含CLIP文件的输入目录",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "-o", "--output-dir",
        help="输出目录（默认为输入目录）"
    ),
    recursive: bool = typer.Option(
        False,
        "-r", "--recursive",
        help="递归处理子目录"
    ),
    force: bool = typer.Option(
        False,
        "-f", "--force",
        help="强制覆盖已存在的文件"
    ),
    verbose: bool = typer.Option(
        False,
        "-v", "--verbose",
        help="显示详细日志"
    )
):
    """
    批量转换CLIP文件

    批量处理目录中的所有CLIP文件，转换为PNG格式。
    """
    # 设置日志
    setup_logging(verbose, False)
    
    # 确定输出目录
    if output_dir is None:
        output_dir = input_dir
    
    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 查找CLIP文件
    pattern = "**/*.clip" if recursive else "*.clip"
    clip_files = list(input_dir.glob(pattern))
    
    if not clip_files:
        rprint(f"[yellow]警告[/yellow]: 在 {input_dir} 中未找到CLIP文件")
        return
    
    rprint(f"[blue]找到 {len(clip_files)} 个CLIP文件[/blue]")
    
    success_count = 0
    failed_files = []
    
    with Progress(console=console) as progress:
        task = progress.add_task("批量转换中...", total=len(clip_files))
        
        for clip_file in clip_files:
            try:
                # 计算相对路径以保持目录结构
                rel_path = clip_file.relative_to(input_dir)
                output_file = output_dir / rel_path.with_suffix('.png')
                
                # 创建输出目录
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                # 检查是否需要跳过
                if output_file.exists() and not force:
                    rprint(f"[yellow]跳过[/yellow]: {output_file} (已存在)")
                    progress.advance(task)
                    continue
                
                # 转换文件
                converter = CspConverter(str(clip_file))
                success = converter.convert_to_png(str(output_file), merge_layers=True)
                
                if success:
                    success_count += 1
                    if verbose:
                        rprint(f"[green]✓[/green] {clip_file.name} -> {output_file.name}")
                else:
                    failed_files.append(clip_file.name)
                    rprint(f"[red]✗[/red] {clip_file.name}")
                
            except Exception as e:
                failed_files.append(clip_file.name)
                rprint(f"[red]✗[/red] {clip_file.name}: {e}")
            
            progress.advance(task)
    
    # 显示结果
    rprint(f"\n[bold]批量转换完成[/bold]")
    rprint(f"[green]成功: {success_count}/{len(clip_files)}[/green]")
    
    if failed_files:
        rprint(f"[red]失败: {len(failed_files)}[/red]")
        if verbose:
            for failed_file in failed_files:
                rprint(f"  [red]•[/red] {failed_file}")


@app.command()
def version():
    """显示版本信息"""
    rprint(f"[bold blue]CSPNG[/bold blue] version [green]{__version__}[/green]")
    rprint("Clip Studio Paint to PNG Converter")


if __name__ == "__main__":
    app()
