import os
import sys # 添加 sys 模块导入
from pathlib import Path
from PIL import Image
from psd_tools import PSDImage
import send2trash
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
import subprocess
import psutil
import traceback
from loguru import logger
# 支持的目标格式
TARGET_FORMATS = ['.psd', '.pdf', '.clip']

# 不再需要导入clip_to_psd包
# 直接通过subprocess调用命令行程序

def process_single_psd(psd_path, out_path, use_recycle_bin=True):
    """
    处理单个PSD文件的转换
    
    参数:
    psd_path -- PSD文件路径
    out_path -- 输出路径
    use_recycle_bin -- 是否使用回收站删除文件，True则移至回收站，False则直接删除
    """
    try:
        success = False
        error_messages = []

        # 优先尝试使用 cp932 编码（日文 Windows 系统默认编码）
        try:
            psd = PSDImage.open(psd_path, encoding='cp932')
            # 检测并输出原始色深信息
            bit_depth = psd.depth
            channels = len(psd.channels)
            logger.info(f"原始PSD信息：")
            logger.info(f"- 色深: {bit_depth}位/通道")
            logger.info(f"- 通道数: {channels}")
            
            # 根据色深决定转换策略
            if bit_depth > 16:
                logger.warning("警告：原始PSD色深超过16位/通道，转换为PNG可能会损失色彩信息")
                # 这里可以添加是否继续的询问
                
            composed = psd.composite()
            success = True
        except Exception as e:
            error_messages.append(f"psd-tools (CP932) 打开失败: {e}")
            # 如果失败，依次尝试其他编码
            for encoding in ['utf-8', 'shift-jis', 'latin1']:
                try:
                    psd = PSDImage.open(psd_path, encoding=encoding)
                    composed = psd.composite()
                    success = True
                    break
                except Exception as e:
                    error_messages.append(f"psd-tools ({encoding}) 打开失败: {e}")

        # 方法2: 如果psd-tools失败，尝试使用wand
        if not success:
            try:
                from wand.image import Image
                with Image(filename=psd_path, format='psd') as img:
                    # 强制设置格式和色彩空间
                    img.format = 'png'
                    img.colorspace = 'rgb'
                    # 直接保存为PNG
                    filename = os.path.splitext(os.path.basename(psd_path))[0]
                    # Avoid adding [PSD] if it's already from a temp file
                    if not filename.endswith('.temp_intermediate'):
                        new_filename = f"{filename}[PSD].png"
                    else:
                        # Use the original base name for the final PNG
                        original_base_name = filename.replace('.temp_intermediate', '')
                        new_filename = f"{original_base_name}[CLIP].png"

                    png_path = os.path.join(os.path.dirname(psd_path), new_filename)
                    img.save(filename=png_path)
                    success = True
            except Exception as e:
                error_messages.append(f"wand 打开失败: {e}")

        if success:
            # 如果使用psd-tools成功，需要保存文件
            if 'composed' in locals():
                filename = os.path.splitext(os.path.basename(psd_path))[0]
                # Avoid adding [PSD] if it's already from a temp file
                if not filename.endswith('.temp_intermediate'):
                    new_filename = f"{filename}[PSD].png"
                else:
                    # Use the original base name for the final PNG
                    original_base_name = filename.replace('.temp_intermediate', '')
                    new_filename = f"{original_base_name}[CLIP].png"

                png_path = os.path.join(os.path.dirname(psd_path), new_filename)
                composed.save(png_path, 
                    format='PNG',
                    optimize=True,
                    compress_level=6,  # 降低压缩级别以提高速度
                )

            # 转换成功后，根据设置决定删除方式
            if use_recycle_bin:
                send2trash.send2trash(psd_path)
                logger.info(f"成功转换并移至回收站: {psd_path}")
            else:
                # Only remove if not specifically told to keep (e.g., temp files handled later)
                # This logic is now handled in convert_clip_via_psd for temp files
                if not psd_path.endswith('.temp_intermediate.psd'):
                    os.remove(psd_path)
                    logger.info(f"成功转换并直接删除: {psd_path}")
                else:
                    logger.info(f"成功转换临时PSD: {psd_path} (将在之后清理)")
            return True
        else:
            # 记录所有尝试过的方法的错误信息
            for error in error_messages:
                logger.error(f"{psd_path}: {error}")
            return False

    except Exception as e:
        logger.error(f"处理文件时发生错误 {psd_path}: {str(e)}")
        return False

def process_psd_wrapper(args):
    """
    包装函数用于多进程处理PSD文件
    """
    return process_single_psd(*args)

def convert_psd_files(directory, use_recycle_bin=True):
    """转换目录中的所有PSD文件"""
    directory = Path(directory)
    psd_files = list(directory.rglob('*.psd'))
    
    if not psd_files:
        print(f"在 {directory} 中没有找到PSD文件")
        return
    
    # 检查内存使用情况
    memory_percent = psutil.virtual_memory().percent
    if memory_percent > 90:
        logger.warning(f"内存使用率超过90%（当前：{memory_percent}%），切换到单线程模式")
        num_processes = 1
    else:
        num_processes = max(8, cpu_count() - 1)  # 保留一个CPU核心
    
    print(f"使用 {num_processes} 个进程进行转换")
    
    with Pool(num_processes) as pool:
        args = [(str(f), str(f.parent), use_recycle_bin) for f in psd_files]
        results = []
        
        # 使用process_psd_wrapper替代lambda函数
        for result in tqdm(
            pool.imap_unordered(process_psd_wrapper, args),
            total=len(psd_files),
            desc="转换PSD文件"
        ):
            results.append(result)
    
    success_count = sum(results)
    print(f"\n转换完成: 成功 {success_count}/{len(psd_files)} 个文件")

def convert_pdf_to_images(pdf_path):
    """
    使用PyMuPDF将PDF文件转换为PNG图片,每页保存为单独的文件
    
    参数:
    pdf_path -- PDF文件路径
    """
    try:
        # 检查fitz库是否可用
        try:
            import fitz
        except ImportError as e:
            logger.error(f"PyMuPDF (fitz)库导入失败: {e}")
            logger.error("请安装PyMuPDF: pip install PyMuPDF")
            return False

        # 检查文件是否存在和可访问
        if not os.path.exists(pdf_path):
            logger.error(f"PDF文件不存在: {pdf_path}")
            return False

        # 创建输出目录
        output_dir = os.path.splitext(pdf_path)[0]
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"创建输出目录失败: {e}")
            return False
        
        # 打开PDF文件
        try:
            doc = fitz.open(pdf_path)
            logger.info(f"PDF信息: 页数={doc.page_count}")
        except Exception as e:
            logger.error(f"打开PDF文件失败: {e}")
            return False

        # 转换每一页
        for page_num in range(doc.page_count):
            try:
                page = doc[page_num]
                # 设置更高的缩放因子以获得更好的图像质量
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                # 保存图像
                image_path = os.path.join(output_dir, f'page_{page_num + 1}.png')
                pix.save(image_path)
                logger.info(f"成功保存第 {page_num + 1} 页到 {image_path}")
            except Exception as e:
                logger.error(f"处理第 {page_num + 1} 页时出错: {e}")
                continue

        # 关闭PDF文档
        doc.close()
            
        # 转换完成后将PDF移到回收站
        try:
            send2trash.send2trash(pdf_path)
            logger.info(f"成功转换PDF并移除: {pdf_path}")
            return True
        except Exception as e:
            logger.error(f"移动PDF到回收站失败: {e}")
            return False
        
    except Exception as e:
        logger.error(f"处理PDF文件时出错 {pdf_path}: {e}")
        return False

def convert_pdf_files(directory):
    """转换目录中的所有PDF文件"""
    directory = Path(directory)
    pdf_files = list(directory.rglob('*.pdf'))
    
    if not pdf_files:
        print(f"在 {directory} 中没有找到PDF文件")
        return
    
    with tqdm(total=len(pdf_files), desc="转换PDF文件") as pbar:
        for pdf_file in pdf_files:
            success = convert_pdf_to_images(str(pdf_file))
            pbar.update(1)
            if success:
                pbar.set_description(f"成功转换并移除: {pdf_file.name}")
            else:
                pbar.set_description(f"转换失败: {pdf_file.name}")

def convert_clip_via_psd(clip_path, use_recycle_bin=True):
    """
    通过先转换为PSD，再将CLIP文件转换为PNG图像。

    参数:
    clip_path -- CLIP文件路径
    use_recycle_bin -- 是否使用回收站删除原文件

    返回:
    bool -- 转换是否成功
    """
    temp_psd_path = None # 初始化以用于错误处理
    try:
        clip_dir = os.path.dirname(clip_path)
        clip_filename_no_ext = os.path.splitext(os.path.basename(clip_path))[0]
        # 创建一个临时的PSD文件名
        temp_psd_filename = f"{clip_filename_no_ext}.temp_intermediate.psd"
        temp_psd_path = os.path.join(clip_dir, temp_psd_filename)

        logger.info(f"开始转换 CLIP -> PSD: {clip_path} -> {temp_psd_path}")
        
        # 使用子进程直接调用clip_to_psd命令行工具
        try:
            logger.debug(f"开始使用clip_to_psd命令转换: {clip_path} -> {temp_psd_path}")
            
            # 构建命令参数
            cmd = [
                "clip_to_psd",  # 直接使用包名作为命令
                f'"{clip_path}"',  # 使用引号包裹路径，防止路径中的空格等特殊字符
                "-o", f'"{temp_psd_path}"'  # 输出PSD文件
                # 可以根据需要添加其他参数，例如 --psd-version 1
            ]
            
            # 组合命令行参数为字符串
            cmd_str = " ".join(cmd)
            logger.debug(f"执行命令: {cmd_str}")
            
            # 执行命令
            result = subprocess.run(
                cmd_str,  # 使用字符串形式传递命令
                shell=True,  # 使用shell执行
                capture_output=True,  # 捕获输出
                text=True,  # 将输出作为文本返回
                check=False  # 不自动抛出异常
            )
            
            # 检查执行结果
            if result.returncode == 0:
                logger.debug("clip_to_psd命令执行成功")
                conversion_success = True
            else:
                logger.error(f"clip_to_psd命令执行失败: {clip_path}")
                logger.error(f"返回码: {result.returncode}")
                logger.error(f"错误输出: {result.stderr}")
                conversion_success = False
                
            if not conversion_success:
                # 如果转换失败，尝试删除可能已创建的临时PSD文件
                if os.path.exists(temp_psd_path):
                    try:
                        os.remove(temp_psd_path)
                    except Exception as e:
                        logger.warning(f"删除失败的临时PSD文件时出错 {temp_psd_path}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"调用clip_to_psd命令时出错: {str(e)}")
            # 如果出错，尝试删除可能已创建的临时PSD文件
            if os.path.exists(temp_psd_path):
                try:
                    os.remove(temp_psd_path)
                except Exception as cleanup_e:
                    logger.warning(f"删除失败的临时PSD文件时出错 {temp_psd_path}: {cleanup_e}")
            return False
              # 检查临时PSD文件是否真的被创建了
        if not os.path.exists(temp_psd_path):
            logger.error(f"clip_to_psd命令执行成功，但未找到输出文件: {temp_psd_path}")
            return False

        logger.info(f"成功转换 CLIP -> PSD: {temp_psd_path}")

        # --- PSD -> PNG 转换 ---
        logger.info(f"开始转换 PSD -> PNG: {temp_psd_path}")
        # 调用现有的 process_single_psd 函数处理临时PSD文件
        # 注意：这里将 use_recycle_bin 设置为 False，因为我们想手动删除临时PSD
        psd_to_png_success = process_single_psd(temp_psd_path, clip_dir, use_recycle_bin=False)

        # --- 清理 ---
        # 无论 PSD -> PNG 是否成功，都尝试删除临时的 PSD 文件
        try:
            os.remove(temp_psd_path)
            logger.info(f"已删除临时PSD文件: {temp_psd_path}")
        except Exception as e:
            # 如果删除失败，记录警告，但这不应阻止后续流程
            logger.warning(f"删除临时PSD文件失败 {temp_psd_path}: {e}")

        # 检查 PSD -> PNG 的转换结果
        if not psd_to_png_success:
            logger.error(f"从临时PSD转换到PNG失败: {temp_psd_path}")
            # 即使PNG转换失败，CLIP到PSD的步骤是成功的，但整体目标未达成
            return False

        # --- 处理原始 CLIP 文件 ---
        # 如果 PSD -> PNG 成功，处理原始的 CLIP 文件
        logger.info(f"成功完成 PSD -> PNG 转换，源文件: {clip_path}")
        try:
            if use_recycle_bin:
                send2trash.send2trash(clip_path)
                logger.info(f"原始CLIP文件已移至回收站: {clip_path}")
            else:
                os.remove(clip_path)
                logger.info(f"原始CLIP文件已删除: {clip_path}")
            return True # 整个流程成功
        except Exception as e:
            logger.error(f"处理原始CLIP文件失败 {clip_path}: {e}")
            return False # 清理原始文件失败

    except Exception as e:
        logger.error(f"处理CLIP文件时发生意外错误 {clip_path}: {e}", exc_info=True)
        # 发生意外时，也尝试清理临时PSD文件
        if temp_psd_path and os.path.exists(temp_psd_path):
             try:
                 os.remove(temp_psd_path)
                 logger.info(f"错误处理中：已删除临时PSD文件: {temp_psd_path}")
             except Exception as cleanup_e:
                 logger.warning(f"错误处理中：删除临时PSD文件失败 {temp_psd_path}: {cleanup_e}")
        return False

def process_clip_wrapper(args):
    """
    包装函数用于多进程处理CLIP文件
    """
    return convert_clip_via_psd(*args)

def convert_clip_files(directory, use_recycle_bin=True):
    """转换目录中的所有CLIP文件 (通过先转为PSD，使用多进程)"""
    directory = Path(directory)
    clip_files = list(directory.rglob('*.clip'))

    if not clip_files:
        logger.info(f"在 {directory} 中没有找到CLIP文件")
        return

    logger.info(f"找到 {len(clip_files)} 个CLIP文件准备转换 (via PSD)")

    # 检查内存使用情况，决定进程数
    memory_percent = psutil.virtual_memory().percent
    if memory_percent > 90:
        logger.warning(f"内存使用率超过90%（当前：{memory_percent}%），切换到单线程模式")
        num_processes = 1
    else:
        # CLIP转换比较耗资源，限制进程数
        num_processes = max(1, min(4, cpu_count() - 1))  # 保留一个CPU核心
    
    print(f"使用 {num_processes} 个进程进行CLIP文件转换")

    results = []
    with Pool(num_processes) as pool:
        args_list = [(str(f), use_recycle_bin) for f in clip_files]
        
        # 使用 tqdm 显示进度
        with tqdm(total=len(clip_files), desc="转换CLIP文件 (via PSD)") as pbar:
            for success in pool.imap_unordered(process_clip_wrapper, args_list):
                results.append(success)
                pbar.update(1) # 更新进度条
                # 更新进度条描述 (可选，可能因并发导致信息不准确)
                # pbar.set_description(f"{'成功' if success else '失败'}: ...") 

    success_count = sum(results)
    print(f"\nCLIP文件转换完成: 成功 {success_count}/{len(clip_files)} 个文件")
    if success_count == 0:
        logger.info("所有CLIP文件转换失败")
    else:
        logger.info(f"成功转换 {success_count} 个CLIP文件")