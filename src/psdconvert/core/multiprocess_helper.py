"""
多进程处理辅助模块，提供通用的多进程处理工具和监控
"""
import os
import psutil
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
from loguru import logger

class MultiprocessExecutor:
    """多进程执行器，提供通用的多进程处理功能和动态调整"""
    
    def __init__(self, process_type="generic", config=None):
        """
        初始化多进程执行器
        
        参数:
        process_type -- 处理类型，可选值为"psd", "pdf", "clip", "generic"
        config -- 配置字典，如果为None则使用默认值
        """
        self.process_type = process_type
        self.config = config or {}
        # 从配置中获取多进程设置，如果不存在则使用默认值
        self.multiprocessing_config = self.config.get("multiprocessing", {
            "enabled": True,
            "auto_adjust": True,
            "max_processes": {
                "psd": 8,
                "pdf": 4,
                "clip": 4,
                "generic": 4
            }
        })
        
    def _get_optimal_process_count(self):
        """
        获取最优的进程数量，考虑系统资源和配置
        
        返回:
        int -- 最优的进程数量
        """
        # 如果多进程被禁用，返回1
        if not self.multiprocessing_config.get("enabled", True):
            logger.info("多进程处理已被禁用，使用单进程模式")
            return 1
            
        # 获取配置中指定的最大进程数
        max_processes_config = self.multiprocessing_config.get("max_processes", {})
        configured_max = max_processes_config.get(self.process_type, 4)
        
        # 如果启用了自动调整
        if self.multiprocessing_config.get("auto_adjust", True):
            # 检查系统资源
            memory_percent = psutil.virtual_memory().percent
            cpu_usage_percent = psutil.cpu_percent(interval=0.1)
            
            # 根据资源使用情况调整进程数
            if memory_percent > 90 or cpu_usage_percent > 95:
                logger.warning(f"系统资源紧张 (内存: {memory_percent}%, CPU: {cpu_usage_percent}%)，使用单进程模式")
                return 1
            elif memory_percent > 80 or cpu_usage_percent > 85:
                logger.warning(f"系统资源较紧张 (内存: {memory_percent}%, CPU: {cpu_usage_percent}%)，减少进程数")
                return max(1, min(2, configured_max, cpu_count() - 1))
            else:
                # 正常情况下，使用配置的进程数，但不超过CPU核心数减1
                return max(1, min(configured_max, cpu_count() - 1))
        else:
            # 不自动调整，直接使用配置的进程数
            return max(1, min(configured_max, cpu_count()))
    
    def execute(self, process_func, items, args_factory=None, desc="处理文件"):
        """
        执行多进程处理
        
        参数:
        process_func -- 处理函数，接收参数并返回处理结果
        items -- 要处理的项目列表
        args_factory -- 参数工厂函数，用于为每个项目生成参数元组，如果为None则直接使用项目作为参数
        desc -- 进度条描述
        
        返回:
        list -- 处理结果列表
        """
        if not items:
            logger.info(f"没有需要处理的项目")
            return []
            
        # 获取进程数
        num_processes = self._get_optimal_process_count()
        logger.info(f"使用 {num_processes} 个进程进行{desc}")
        
        # 准备参数
        if args_factory:
            args_list = [args_factory(item) for item in items]
        else:
            args_list = items
            
        # 执行多进程处理
        results = []
        if num_processes > 1:
            with Pool(num_processes) as pool:
                with tqdm(total=len(items), desc=desc) as pbar:
                    for result in pool.imap_unordered(process_func, args_list):
                        results.append(result)
                        pbar.update(1)
        else:
            # 单进程模式，直接使用tqdm
            with tqdm(total=len(items), desc=desc) as pbar:
                for args in args_list:
                    result = process_func(args)
                    results.append(result)
                    pbar.update(1)
                    
        # 统计结果
        if all(isinstance(r, bool) for r in results):
            success_count = sum(1 for r in results if r)
            logger.info(f"\n{desc}完成: 成功 {success_count}/{len(items)} 个项目")
            
        return results 