"""
性能日志模块(Performance Logger Module)

本模块提供性能监控和日志记录功能，专门用于测量数据库操作和函数执行时间，
生成性能统计报告，满足课程对多用户访问性能记录的要求。

使用方法:
    from utils.performance_logger import PerformanceLogger, log_execution_time
    
    # 方式1：使用性能日志记录器类
    # 创建记录器实例
    perf_logger = PerformanceLogger(log_file='performance.log')
    
    # 记录单个操作执行时间
    perf_logger.start("数据库查询")
    # 执行数据库查询...
    perf_logger.end("数据库查询")
    
    # 使用上下文管理器记录代码块执行时间
    with perf_logger.measure("复杂计算"):
        # 执行复杂计算...
        pass
    
    # 获取性能统计信息
    stats = perf_logger.get_statistics()
    print(f"平均执行时间: {stats['avg_time_ms']}毫秒")
    print(f"最长执行时间: {stats['max_time_ms']}毫秒")
    print(f"总操作次数: {stats['operation_count']}")
    
    # 生成性能报告
    perf_logger.generate_report("performance_report.csv")
    
    # 方式2：使用装饰器记录函数执行时间
    @log_execution_time
    def complex_database_operation(param1, param2):
        # 函数执行时间会被自动记录
        return result
    
    # 方式3：记录并发用户操作性能
    # 在多线程或多进程环境中使用
    perf_logger = PerformanceLogger(log_file='concurrent_perf.log')
    
    # 在用户线程中使用
    def user_thread_function(user_id):
        logger = perf_logger.get_user_logger(user_id)
        logger.start("用户查询")
        # 执行用户操作...
        logger.end("用户查询")
    
    # 生成多用户性能对比报告
    perf_logger.generate_concurrent_report("users_performance.csv")

主要功能:
    - PerformanceLogger: 性能日志记录器类
        - __init__(log_file=None): 
            初始化记录器，可指定日志文件路径
            
        - start(operation_name): 
            开始记录操作执行时间
            
        - end(operation_name): 
            结束记录操作执行时间，计算执行时长
            
        - measure(operation_name): 
            返回上下文管理器，用于自动计算代码块执行时间
            
        - get_statistics(operation_name=None): 
            获取指定操作或所有操作的统计信息
            
        - log_operation(operation_name, execution_time_ms): 
            记录操作执行时间到日志
            
        - get_user_logger(user_id): 
            获取用户专用的性能记录器
            
        - generate_report(file_path): 
            生成性能报告CSV文件
            
        - generate_concurrent_report(file_path): 
            生成多用户并发性能对比报告
            
    - log_execution_time: 函数装饰器
        用于装饰函数并自动记录其执行时间
        
    - OperationMeasureContext: 操作测量上下文类
        实现上下文管理协议，用于自动记录代码块执行时间
        
    - _format_time(timestamp): 
        格式化时间戳为可读字符串（内部函数）
"""

import time
import csv
import os
import logging
import functools
import threading
import statistics
from datetime import datetime
from contextlib import contextmanager

# 获取logger
logger = logging.getLogger(__name__)

def _format_time(timestamp):
    """将时间戳格式化为可读字符串

    Args:
        timestamp (float): 时间戳

    Returns:
        str: 格式化后的时间字符串，格式为：YYYY-MM-DD HH:MM:SS.mmm
    """
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

class OperationMeasureContext:
    """操作测量上下文类，用于上下文管理器功能"""
    
    def __init__(self, logger, operation_name):
        """初始化上下文对象

        Args:
            logger (PerformanceLogger): 性能日志记录器实例
            operation_name (str): 操作名称
        """
        self.logger = logger
        self.operation_name = operation_name
        
    def __enter__(self):
        """进入上下文时开始计时"""
        self.logger.start(self.operation_name)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时结束计时

        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常跟踪信息
        """
        self.logger.end(self.operation_name)
        # 返回False表示不抑制异常
        return False

class PerformanceLogger:
    """性能日志记录器，用于记录和分析操作执行时间"""
    
    def __init__(self, log_file=None):
        """初始化性能日志记录器

        Args:
            log_file (str, optional): 日志文件路径。如果为None，则只在内存中记录不写入文件
        """
        # 操作开始时间记录
        self.start_times = {}
        # 操作执行时间记录
        self.execution_times = {}
        # 用户记录器字典
        self.user_loggers = {}
        # 记录器标识，用于区分不同实例
        self.logger_id = id(self)
        # 日志文件路径
        self.log_file = log_file
        # 线程锁，保证线程安全
        self.lock = threading.RLock()
        
        # 如果提供了日志文件，则创建目录
        if log_file:
            os.makedirs(os.path.dirname(log_file) if os.path.dirname(log_file) else '.', exist_ok=True)
    
    def start(self, operation_name):
        """开始记录操作执行时间

        Args:
            operation_name (str): 操作名称
        """
        with self.lock:
            self.start_times[operation_name] = time.time()
    
    def end(self, operation_name):
        """结束记录操作执行时间，计算执行时长

        Args:
            operation_name (str): 操作名称

        Returns:
            float: 操作执行时间（毫秒）
        
        Raises:
            KeyError: 如果未找到对应操作的开始时间
        """
        end_time = time.time()
        
        with self.lock:
            if operation_name not in self.start_times:
                raise KeyError(f"未找到操作'{operation_name}'的开始时间")
            
            start_time = self.start_times[operation_name]
            execution_time_ms = (end_time - start_time) * 1000
            
            # 记录执行时间
            self.log_operation(operation_name, execution_time_ms)
            
            # 清除开始时间
            del self.start_times[operation_name]
            
            return execution_time_ms
    
    def measure(self, operation_name):
        """创建一个上下文管理器来测量代码块执行时间

        Args:
            operation_name (str): 操作名称

        Returns:
            OperationMeasureContext: 上下文管理器对象
        """
        return OperationMeasureContext(self, operation_name)
    
    def log_operation(self, operation_name, execution_time_ms):
        """记录操作执行时间到内存和日志文件

        Args:
            operation_name (str): 操作名称
            execution_time_ms (float): 执行时间（毫秒）
        """
        timestamp = time.time()
        formatted_time = _format_time(timestamp)
        
        with self.lock:
            # 添加到内存记录
            if operation_name not in self.execution_times:
                self.execution_times[operation_name] = []
            
            self.execution_times[operation_name].append({
                'timestamp': timestamp,
                'execution_time_ms': execution_time_ms
            })
            
            # 写入日志文件
            if self.log_file:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(f"{formatted_time},{operation_name},{execution_time_ms:.2f}\n")
            
            # 输出到控制台日志
            logger.debug(f"操作 '{operation_name}' 执行时间: {execution_time_ms:.2f}ms")
    
    def get_statistics(self, operation_name=None):
        """获取操作的统计信息

        Args:
            operation_name (str, optional): 操作名称，如果为None则返回所有操作的汇总统计

        Returns:
            dict: 包含统计信息的字典：
                {
                    'operation_count': 操作次数,
                    'avg_time_ms': 平均执行时间(毫秒),
                    'min_time_ms': 最小执行时间(毫秒),
                    'max_time_ms': 最大执行时间(毫秒),
                    'total_time_ms': 总执行时间(毫秒),
                    'std_dev_ms': 标准差(毫秒)
                }
        """
        with self.lock:
            if operation_name:
                # 返回特定操作的统计信息
                if operation_name not in self.execution_times:
                    return {
                        'operation_count': 0,
                        'avg_time_ms': 0,
                        'min_time_ms': 0,
                        'max_time_ms': 0,
                        'total_time_ms': 0,
                        'std_dev_ms': 0
                    }
                
                times = [entry['execution_time_ms'] for entry in self.execution_times[operation_name]]
                return self._calculate_stats(times)
            else:
                # 返回所有操作的汇总统计信息
                all_times = []
                for op_times in self.execution_times.values():
                    all_times.extend([entry['execution_time_ms'] for entry in op_times])
                
                if not all_times:
                    return {
                        'operation_count': 0,
                        'avg_time_ms': 0,
                        'min_time_ms': 0,
                        'max_time_ms': 0,
                        'total_time_ms': 0,
                        'std_dev_ms': 0
                    }
                
                return self._calculate_stats(all_times)
    
    def _calculate_stats(self, times):
        """计算统计指标

        Args:
            times (list): 执行时间列表

        Returns:
            dict: 包含统计指标的字典
        """
        if not times:
            return {
                'operation_count': 0,
                'avg_time_ms': 0,
                'min_time_ms': 0,
                'max_time_ms': 0,
                'total_time_ms': 0,
                'std_dev_ms': 0
            }
        
        return {
            'operation_count': len(times),
            'avg_time_ms': sum(times) / len(times),
            'min_time_ms': min(times),
            'max_time_ms': max(times),
            'total_time_ms': sum(times),
            'std_dev_ms': statistics.stdev(times) if len(times) > 1 else 0
        }
    
    def get_user_logger(self, user_id):
        """获取用户专用的性能记录器

        Args:
            user_id: 用户标识（可以是ID或用户名）

        Returns:
            PerformanceLogger: 用户专用的性能记录器实例
        """
        with self.lock:
            if user_id not in self.user_loggers:
                # 如果有主日志文件，则为用户创建单独的日志文件
                user_log_file = None
                if self.log_file:
                    base_name, ext = os.path.splitext(self.log_file)
                    user_log_file = f"{base_name}_user_{user_id}{ext}"
                
                # 创建用户专用记录器
                self.user_loggers[user_id] = PerformanceLogger(log_file=user_log_file)
            
            return self.user_loggers[user_id]
    
    def generate_report(self, file_path):
        """生成性能报告CSV文件

        Args:
            file_path (str): 报告文件路径
        """
        with self.lock:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                # 中文表头字段名
                fieldnames = ['操作名称', '操作次数', '平均耗时(毫秒)', 
                             '最小耗时(毫秒)', '最大耗时(毫秒)', '总耗时(毫秒)', '标准差(毫秒)']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # 写入每个操作的统计信息
                for operation_name in self.execution_times.keys():
                    stats = self.get_statistics(operation_name)
                    writer.writerow({
                        '操作名称': operation_name,
                        '操作次数': stats['operation_count'],
                        '平均耗时(毫秒)': f"{stats['avg_time_ms']:.2f}",
                        '最小耗时(毫秒)': f"{stats['min_time_ms']:.2f}",
                        '最大耗时(毫秒)': f"{stats['max_time_ms']:.2f}",
                        '总耗时(毫秒)': f"{stats['total_time_ms']:.2f}",
                        '标准差(毫秒)': f"{stats['std_dev_ms']:.2f}"
                    })
                
                # 写入总计统计信息
                total_stats = self.get_statistics()
                writer.writerow({
                    '操作名称': '总计',
                    '操作次数': total_stats['operation_count'],
                    '平均耗时(毫秒)': f"{total_stats['avg_time_ms']:.2f}",
                    '最小耗时(毫秒)': f"{total_stats['min_time_ms']:.2f}",
                    '最大耗时(毫秒)': f"{total_stats['max_time_ms']:.2f}",
                    '总耗时(毫秒)': f"{total_stats['total_time_ms']:.2f}",
                    '标准差(毫秒)': f"{total_stats['std_dev_ms']:.2f}"
                })
    
    def generate_concurrent_report(self, file_path):
        """生成多用户并发性能对比报告

        Args:
            file_path (str): 报告文件路径
        """
        with self.lock:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                # 中文表头字段名
                fieldnames = ['用户ID', '操作名称', '操作次数', 
                             '平均耗时(毫秒)', '最大耗时(毫秒)', '总耗时(毫秒)']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # 写入每个用户的每个操作的统计信息
                for user_id, user_logger in self.user_loggers.items():
                    for operation_name in user_logger.execution_times.keys():
                        stats = user_logger.get_statistics(operation_name)
                        writer.writerow({
                            '用户ID': user_id,
                            '操作名称': operation_name,
                            '操作次数': stats['operation_count'],
                            '平均耗时(毫秒)': f"{stats['avg_time_ms']:.2f}",
                            '最大耗时(毫秒)': f"{stats['max_time_ms']:.2f}",
                            '总耗时(毫秒)': f"{stats['total_time_ms']:.2f}"
                        })
                    
                    # 写入用户总计
                    total_stats = user_logger.get_statistics()
                    writer.writerow({
                        '用户ID': user_id,
                        '操作名称': '用户总计',
                        '操作次数': total_stats['operation_count'],
                        '平均耗时(毫秒)': f"{total_stats['avg_time_ms']:.2f}",
                        '最大耗时(毫秒)': f"{total_stats['max_time_ms']:.2f}",
                        '总耗时(毫秒)': f"{total_stats['total_time_ms']:.2f}"
                    })
                
                # 写入所有用户的总计
                all_times = []
                total_operations = 0
                
                for user_logger in self.user_loggers.values():
                    for op_times in user_logger.execution_times.values():
                        all_times.extend([entry['execution_time_ms'] for entry in op_times])
                        total_operations += len(op_times)
                
                if all_times:
                    writer.writerow({
                        '用户ID': '所有用户',
                        '操作名称': '总计',
                        '操作次数': total_operations,
                        '平均耗时(毫秒)': f"{sum(all_times) / len(all_times):.2f}",
                        '最大耗时(毫秒)': f"{max(all_times):.2f}",
                        '总耗时(毫秒)': f"{sum(all_times):.2f}"
                    })

_global_performance_logger = None


def get_global_performance_logger():
    """获取全局性能记录器实例"""
    global _global_performance_logger
    if _global_performance_logger is None:
        _global_performance_logger = PerformanceLogger()
    return _global_performance_logger


def log_execution_time(func=None, logger=None, operation_name=None):
    """函数装饰器，用于记录函数执行时间

    可以直接作为装饰器使用，也可以带参数使用：
    
    @log_execution_time
    def my_function():
        pass
    
    # 或者
    @log_execution_time(logger=my_logger, operation_name="自定义操作")
    def my_function():
        pass

    Args:
        func: 被装饰的函数
        logger (PerformanceLogger, optional): 性能记录器实例，如果不提供则创建新实例
        operation_name (str, optional): 操作名称，如果不提供则使用函数名

    Returns:
        function: 包装后的函数
    """
    def decorator(_func):
        @functools.wraps(_func)
        def wrapper(*args, **kwargs):
            # 使用提供的记录器或创建新的
            _logger = logger or PerformanceLogger()
            # 使用提供的操作名称或函数名
            _operation_name = operation_name or f"{_func.__module__}.{_func.__name__}"
            
            # 记录开始时间
            _logger.start(_operation_name)
            
            try:
                # 执行原函数
                result = _func(*args, **kwargs)
                return result
            finally:
                # 记录结束时间
                _logger.end(_operation_name)
        
        return wrapper
    
    # 处理直接使用@log_execution_time的情况
    if func:
        return decorator(func)
    
    # 处理带参数使用@log_execution_time(...)的情况
    return decorator


def log_performance(func=None, operation_name=None, logger=None):
    """专用于Web路由/服务的性能装饰器，兼容旧接口"""
    _logger = logger or get_global_performance_logger()

    def decorator(_func):
        @functools.wraps(_func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{_func.__module__}.{_func.__name__}"
            _logger.start(op_name)
            try:
                return _func(*args, **kwargs)
            finally:
                execution_time = _logger.end(op_name)
                logger_obj = logging.getLogger(__name__)
                logger_obj.debug(f"性能记录：{op_name} 执行耗时 {execution_time:.2f}ms")

        return wrapper

    if func:
        return decorator(func)

    return decorator