"""
配置加载器模块
"""
import json
import os
from pathlib import Path
from loguru import logger

def load_config(config_path=None):
    """
    加载配置文件
    
    参数:
    config_path -- 配置文件路径，如不指定则使用默认路径
    
    返回:
    配置字典
    """
    # 如果未指定配置路径，使用默认路径
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"配置文件加载成功: {config_path}")
        return config
    except Exception as e:
        logger.error(f"加载配置文件出错: {e}")
        logger.info("使用默认配置")
        return get_default_config()

def get_default_config():
    """
    获取默认配置
    
    返回:
    默认配置字典
    """
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
        },
        "multiprocessing": {
            "enabled": True,
            "auto_adjust": True,
            "max_processes": {
                "psd": 8,
                "pdf": 16,
                "clip": 8
            }
        }
    }