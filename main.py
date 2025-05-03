import os
import shutil
import subprocess
from PIL import Image
from tqdm import tqdm
import send2trash
from pathlib import Path
import logging
import pyperclip
import argparse
import zipfile
import psutil
import json
from multiprocessing import Pool, cpu_count

# 导入自定义模块
from src.archive_processor import extract_all_archives_recursive, ARCHIVE_EXTENSIONS
from src.format_converter import convert_psd_files, convert_pdf_files, convert_clip_files, TARGET_FORMATS

from loguru import logger
import os
import sys
from pathlib import Path
from datetime import datetime

def setup_logger(app_name="app", project_root=None):
    """配置 Loguru 日志系统
    
    Args:
        app_name: 应用名称，用于日志目录
        project_root: 项目根目录，默认为当前文件所在目录
        
    Returns:
        tuple: (logger, config_info)
            - logger: 配置好的 logger 实例
            - config_info: 包含日志配置信息的字典
    """
    # 获取项目根目录
    if project_root is None:
        project_root = Path(__file__).parent.resolve()
    
    # 清除默认处理器
    logger.remove()
    
    # 添加控制台处理器（简洁版格式）
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <blue>{elapsed}</blue> | <level>{level.icon} {level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
    )
    
    # 使用 datetime 构建日志路径
    current_time = datetime.now()
    date_str = current_time.strftime("%Y-%m-%d")
    hour_str = current_time.strftime("%H")
    minute_str = current_time.strftime("%M%S")
    
    # 构建日志目录和文件路径
    log_dir = os.path.join(project_root, "logs", app_name, date_str, hour_str)
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{minute_str}.log")
    
    # 添加文件处理器
    logger.add(
        log_file,
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {elapsed} | {level.icon} {level: <8} | {name}:{function}:{line} - {message}",
    )
    
    # 创建配置信息字典
    config_info = {
        'log_file': log_file,
    }
    
    logger.info(f"日志系统已初始化，应用名称: {app_name}")
    return logger, config_info

logger, config_info = setup_logger(app_name="psd_convert")

def delete_files_by_extensions(directory, extensions):
    """
    删除指定目录下具有指定扩展名的所有文件。

    参数:
    directory -- 目标目录路径
    extensions -- 文件扩展名列表
    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    logger.info(f"已删除文件: {file_path}")
                except Exception as e:
                    logger.error(f"删除文件出错 {file_path}: {e}")

def delete_empty_folders(directory):
    """
    删除指定目录下的所有空文件夹。

    参数:
    directory -- 目标目录路径
    """
    for root, dirs, files in os.walk(directory, topdown=False):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            if not os.listdir(dir_path):
                try:
                    os.rmdir(dir_path)
                    logger.info(f"已删除空目录: {dir_path}")
                except Exception as e:
                    logger.error(f"删除目录出错 {dir_path}: {e}")

def delete_folders_by_keywords(directory, keywords):
    """
    删除指定目录下包含特定关键字的文件夹。

    参数:
    directory -- 目标目录路径
    keywords -- 关键字列表
    """
    for root, dirs, files in os.walk(directory, topdown=False):
        for dir in dirs:
            if any(keyword in dir for keyword in keywords):
                dir_path = os.path.join(root, dir)
                try:
                    shutil.rmtree(dir_path)
                    logger.info(f"已删除包含关键词的目录: {dir_path}")
                except Exception as e:
                    logger.error(f"删除目录出错 {dir_path}: {e}")

def organize_media_files(source_path, target_base_path):
    """
    整理媒体文件，保持原有文件夹结构，使用剪切操作，清理空文件夹
    
    参数:
    source_path (str): 源路径
    target_base_path (str): 目标基础路径
    """
    # 定义文件类型
    media_types = {
        '[01视频]': ['.mp4', '.avi', '.webm', '.rmvb', '.mov', '.mkv','.flv','.wmv'],
        # '[02动图]': ['.gif'],
        # '[03压缩]': ['.zip', '.7z', '.rar'],
        '[04cbz]': ['.cbz']  # 新增cbz文件类型
    }
    
    # 遍历源路径
    for root, _, files in os.walk(source_path):
        # 检查当前文件夹是否包含需要处理的媒体文件
        media_files = {}
        for file in files:
            for media_type, extensions in media_types.items():
                if any(file.endswith(ext.lower()) for ext in extensions):
                    if media_type not in media_files:
                        media_files[media_type] = []
                    media_files[media_type].append(file)
        
        # 如果文件夹包含媒体文件，移动文件
        if media_files:
            relative_path = os.path.relpath(root, source_path)
            for media_type, file_list in media_files.items():
                target_dir = os.path.join(target_base_path, media_type, relative_path)
                
                # 创建目标文件夹
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)
                
                # 移动文件
                for file in file_list:
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(target_dir, file)
                    try:
                        shutil.move(src_file, dst_file)
                        logger.info(f"已移动 {src_file} 到 {dst_file}")
                    except Exception as e:
                        logger.error(f"移动文件时出错 {src_file}: {e}")

    # 处理完文件后，删除空文件夹
    logger.info("开始清理空文件夹...")
    for root, dirs, files in os.walk(source_path, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                if not os.listdir(dir_path):  # 检查文件夹是否为空
                    os.rmdir(dir_path)
                    logger.info(f"已删除空文件夹: {dir_path}")
            except Exception as e:
                logger.error(f"删除空文件夹时出错 {dir_path}: {e}")

def load_config(config_path='config.json'):
    """
    加载配置文件
    
    参数:
    config_path -- 配置文件路径
    
    返回:
    配置字典
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"配置文件加载成功: {config_path}")
        return config
    except Exception as e:
        logger.error(f"加载配置文件出错: {e}")
        logger.info("使用默认配置")
        return {
            "execution": {
                "delete": True,
                "organize": False,
                "extract": False
            },
            "files": {
                "psd_handling": "convert",
                "pdf_handling": "convert",
                "clip_handling": "convert",
                "use_recycle_bin": False,
                "delete_archives": True
            },
            "delete_config": {
                "extensions": ["txt", "js", "url", "htm", "html", "docx"],
                "keywords": ["進捗", "宣伝", "同人誌", "予告", "新刊"]
            }
        }

def process_directory(directory, config, custom_target_formats):
    """
    处理单个目录的所有操作
    
    参数:
    directory -- 目标目录路径
    config -- 配置字典
    custom_target_formats -- 自定义目标格式列表
    """
    logger.info(f"正在处理目录: {directory}")
    try:
        # 执行解压操作
        if config["execution"]["extract"]:
            logger.info("=== 检查是否需要递归解压所有压缩文件 ===")
            # 询问用户是否需要递归解压
            print(f"\n是否要递归解压目录 '{directory}' 中的所有压缩文件?")
            print("1. 是")
            print("2. 否")
            while True:
                choice = input("请选择 (1/2): ").strip()
                if choice == '1':
                    logger.info("=== 开始递归解压所有压缩文件 ===")
                    extract_all_archives_recursive(
                        directory, 
                        delete_original=config["files"]["delete_archives"], 
                        target_formats=custom_target_formats
                    )
                    break
                elif choice == '2':
                    logger.info("=== 跳过递归解压操作 ===")
                    break
                else:
                    print("无效的选项，请重新输入")
        
        # 处理PSD文件
        if config["files"]["psd_handling"] == 'convert':
            logger.info("=== 开始转换PSD文件 ===")
            convert_psd_files(directory, config["files"]["use_recycle_bin"])
        
        # 处理PDF文件
        if config["files"]["pdf_handling"] == 'convert':
            logger.info("=== 开始转换PDF文件 ===")
            convert_pdf_files(directory)
        
        # 处理CLIP文件
        if config["files"]["clip_handling"] == 'convert':
            logger.info("=== 开始转换CLIP文件 ===")
            convert_clip_files(directory, config["files"]["use_recycle_bin"])
        
        # 构建需要删除的文件扩展名列表
        delete_extensions = config["delete_config"]["extensions"].copy()
        if config["files"]["psd_handling"] == 'delete':
            delete_extensions.append('psd')
        if config["files"]["pdf_handling"] == 'delete':
            delete_extensions.append('pdf')
        if config["files"]["clip_handling"] == 'delete':
            delete_extensions.append('clip')
            
        # 执行删除操作
        if config["execution"]["delete"]:
            logger.info("=== 开始删除不需要的文件和文件夹 ===")
            delete_files_by_extensions(directory, delete_extensions)
            delete_empty_folders(directory)
            delete_folders_by_keywords(directory, config["delete_config"]["keywords"])
        
        # 执行整理操作
        if config["execution"]["organize"]:
            logger.info("=== 开始整理媒体文件 ===")
            organize_media_files(directory, directory)
        
        logger.info(f"目录 {directory} 处理完成")
    except Exception as e:
        logger.error(f"处理目录 {directory} 时出错: {str(e)}")
        logger.error(f"处理目录 {directory} 时发生错误，继续处理下一个目录")

def main():
    """主函数：处理用户输入和配置，调用其他函数执行实际操作"""
    # 添加命令行参数解析
    parser = argparse.ArgumentParser(description='文件处理工具')
    parser.add_argument('--clipboard', action='store_true', help='从剪贴板读取路径')
    parser.add_argument('--keep-archives', action='store_true', help='保留原始压缩文件不删除')
    parser.add_argument('--config', default='config.json', help='指定配置文件路径')
    parser.add_argument('--formats', default=','.join(TARGET_FORMATS), 
                       help=f'待处理的目标文件格式，逗号分隔，例如: {",".join(TARGET_FORMATS)}')
    args = parser.parse_args()
    
    # 获取目录路径
    if args.clipboard:
        input_text = pyperclip.paste()
    else:
        print("请一次性粘贴所有目录路径（每行一个路径，最后输入空行结束）:")
        input_text = ""
        while True:
            line = input()
            if not line:
                break
            input_text += line + "\n"

    # 处理输入的路径
    directories = []
    for path in input_text.strip().split('\n'):
        # 去除可能存在的引号和空白字符
        clean_path = path.strip().strip('"').strip("'").strip()
        if os.path.exists(clean_path):
            directories.append(clean_path)
        else:
            logger.warning(f"警告：路径不存在 - {clean_path}")
    
    if not directories:
        logger.warning("未输入有效路径，程序退出")
        return
    
    # 加载配置文件
    config = load_config(args.config)
    
    # 如果命令行指定了保留压缩文件，覆盖配置文件中的设置
    if args.keep_archives:
        config["files"]["delete_archives"] = False
    
    # 解析目标文件格式
    custom_target_formats = [f.strip() for f in args.formats.split(',')]
    
    # 为每个目录执行处理操作
    for directory in directories:
        process_directory(directory, config, custom_target_formats)
    
    logger.info("所有操作已完成")

if __name__ == "__main__":
    main()