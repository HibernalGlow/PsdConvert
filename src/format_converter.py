import os
from pathlib import Path
import logging
from PIL import Image
from psd_tools import PSDImage
import send2trash
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
import subprocess
import psutil

# 支持的目标格式
TARGET_FORMATS = ['.psd', '.pdf', '.clip']

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
            logging.info(f"原始PSD信息：")
            logging.info(f"- 色深: {bit_depth}位/通道")
            logging.info(f"- 通道数: {channels}")
            
            # 根据色深决定转换策略
            if bit_depth > 16:
                logging.warning("警告：原始PSD色深超过16位/通道，转换为PNG可能会损失色彩信息")
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
                    new_filename = f"{filename}[PSD].png"
                    png_path = os.path.join(os.path.dirname(psd_path), new_filename)
                    img.save(filename=png_path)
                    success = True
            except Exception as e:
                error_messages.append(f"wand 打开失败: {e}")

        if success:
            # 如果使用psd-tools成功，需要保存文件
            if 'composed' in locals():
                filename = os.path.splitext(os.path.basename(psd_path))[0]
                new_filename = f"{filename}[PSD].png"
                png_path = os.path.join(os.path.dirname(psd_path), new_filename)
                composed.save(png_path, 
                    format='PNG',
                    optimize=True,
                    compress_level=6,  # 降低压缩级别以提高速度
                )

            # 转换成功后，根据设置决定删除方式
            if use_recycle_bin:
                send2trash.send2trash(psd_path)
                logging.info(f"成功转换并移至回收站: {psd_path}")
            else:
                os.remove(psd_path)
                logging.info(f"成功转换并直接删除: {psd_path}")
            return True
        else:
            # 记录所有尝试过的方法的错误信息
            for error in error_messages:
                logging.error(f"{psd_path}: {error}")
            return False

    except Exception as e:
        logging.error(f"处理文件时发生错误 {psd_path}: {str(e)}")
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
        logging.warning(f"内存使用率超过90%（当前：{memory_percent}%），切换到单线程模式")
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
            logging.error(f"PyMuPDF (fitz)库导入失败: {e}")
            logging.error("请安装PyMuPDF: pip install PyMuPDF")
            return False

        # 检查文件是否存在和可访问
        if not os.path.exists(pdf_path):
            logging.error(f"PDF文件不存在: {pdf_path}")
            return False

        # 创建输出目录
        output_dir = os.path.splitext(pdf_path)[0]
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            logging.error(f"创建输出目录失败: {e}")
            return False
        
        # 打开PDF文件
        try:
            doc = fitz.open(pdf_path)
            logging.info(f"PDF信息: 页数={doc.page_count}")
        except Exception as e:
            logging.error(f"打开PDF文件失败: {e}")
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
                logging.info(f"成功保存第 {page_num + 1} 页到 {image_path}")
            except Exception as e:
                logging.error(f"处理第 {page_num + 1} 页时出错: {e}")
                continue

        # 关闭PDF文档
        doc.close()
            
        # 转换完成后将PDF移到回收站
        try:
            send2trash.send2trash(pdf_path)
            logging.info(f"成功转换PDF并移除: {pdf_path}")
            return True
        except Exception as e:
            logging.error(f"移动PDF到回收站失败: {e}")
            return False
        
    except Exception as e:
        logging.error(f"处理PDF文件时出错 {pdf_path}: {e}")
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

def convert_clip_to_images(clip_path, use_recycle_bin=True):
    """
    转换CLIP文件为PNG图像
    
    参数:
    clip_path -- CLIP文件路径
    use_recycle_bin -- 是否使用回收站删除原文件
    
    返回:
    bool -- 转换是否成功
    """
    try:
        success = False
        error_messages = []
        
        # 获取临时文件路径
        clip_file_name = os.path.basename(clip_path)
        output_file_name = os.path.splitext(clip_file_name)[0] + "[CLIP].png"
        png_path = os.path.join(os.path.dirname(clip_path), output_file_name)
        
        # 方法1: 尝试使用wand/ImageMagick转换
        try:
            from wand.image import Image
            with Image(filename=clip_path) as img:
                # 设置格式和色彩空间
                img.format = 'png'
                img.colorspace = 'rgb'
                img.save(filename=png_path)
                success = True
                logging.info(f"使用Wand成功转换CLIP文件: {clip_path}")
        except Exception as e:
            error_messages.append(f"Wand转换失败: {e}")
            
        # 方法2: 尝试使用ImageMagick命令行工具转换 - 使用二进制模式避免编码问题
        if not success:
            try:
                cmd = [
                    'magick',
                    'convert',
                    clip_path,
                    '-quality', '100',
                    png_path
                ]
                
                # 使用subprocess时不捕获文本输出，避免编码问题
                result = subprocess.run(
                    cmd, 
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW,  # 防止命令窗口闪现
                    shell=False  # 避免使用shell，减少编码问题
                )
                
                if result.returncode == 0:
                    success = True
                    logging.info(f"使用ImageMagick命令行工具成功转换CLIP文件: {clip_path}")
                else:
                    # 尝试以二进制方式记录错误信息
                    try:
                        err_msg = result.stderr.decode('utf-8', errors='ignore')
                    except:
                        err_msg = "无法解码错误信息"
                    error_messages.append(f"ImageMagick命令行转换失败，返回码: {result.returncode}, 错误: {err_msg}")
            except Exception as e:
                error_messages.append(f"ImageMagick命令行处理失败: {e}")
                
        # 方法3: 尝试使用系统自带的clip viewer (如果可用)
        if not success:
            try:
                import tempfile
                # 创建临时批处理文件，避免路径中的特殊字符问题
                with tempfile.NamedTemporaryFile(suffix='.bat', delete=False, mode='w', encoding='utf-8') as bat_file:
                    bat_file.write(f'@echo off\ncd /d "{os.path.dirname(clip_path)}"\n')
                    bat_file.write(f'magick "{clip_file_name}" "{output_file_name}"\n')
                
                # 执行批处理文件
                result = subprocess.run(
                    bat_file.name, 
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                # 删除临时批处理文件
                try:
                    os.unlink(bat_file.name)
                except:
                    pass
                
                # 检查转换后文件是否存在
                if os.path.exists(png_path) and os.path.getsize(png_path) > 0:
                    success = True
                    logging.info(f"使用批处理文件成功转换CLIP文件: {clip_path}")
            except Exception as e:
                error_messages.append(f"批处理转换方法失败: {e}")
        
        # 如果转换成功，根据设置决定删除方式
        if success:
            if use_recycle_bin:
                send2trash.send2trash(clip_path)
                logging.info(f"成功转换并移至回收站: {clip_path}")
            else:
                os.remove(clip_path)
                logging.info(f"成功转换并直接删除: {clip_path}")
            return True
        else:
            for error in error_messages:
                logging.error(f"{clip_path}: {error}")
            logging.error(f"无法转换CLIP文件: {clip_path}")
            return False
            
    except Exception as e:
        logging.error(f"处理CLIP文件时出错 {clip_path}: {str(e)}")
        return False

def convert_clip_files(directory, use_recycle_bin=True):
    """转换目录中的所有CLIP文件"""
    directory = Path(directory)
    clip_files = list(directory.rglob('*.clip'))
    
    if not clip_files:
        logging.info(f"在 {directory} 中没有找到CLIP文件")
        return
    
    logging.info(f"找到 {len(clip_files)} 个CLIP文件准备转换")
    
    with tqdm(total=len(clip_files), desc="转换CLIP文件") as pbar:
        for clip_file in clip_files:
            success = convert_clip_to_images(str(clip_file), use_recycle_bin)
            pbar.update(1)
            if success:
                pbar.set_description(f"成功转换: {clip_file.name}")
            else:
                pbar.set_description(f"转换失败: {clip_file.name}")
    
    logging.info(f"CLIP文件转换完成")
