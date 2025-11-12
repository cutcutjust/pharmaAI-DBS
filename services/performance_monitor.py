"""
性能监控服务模块(Performance Monitor Service)

本模块提供数据库操作性能监控和统计功能，用于记录各种操作的执行时间、
统计并发用户数、响应时间和吞吐量，并生成性能报告，满足课程对多用户访问性能记录的要求。

使用方法:
    from services.performance_monitor import PerformanceMonitor, performance_log
    
    # 方式1：使用性能监控对象
    monitor = PerformanceMonitor()
    
    # 使用上下文管理器测量操作执行时间
    with monitor.measure_operation('查询药品信息'):
        # 执行需要监控的操作
        results = dao.find_by({'name_cn': '人参'})
    
    # 手动开始和结束测量
    monitor.start_measurement('复杂查询')
    # 执行复杂查询...
    monitor.end_measurement()
    
    # 获取统计信息
    stats = monitor.get_statistics()
    print(f"平均响应时间: {stats['avg_response_time_ms']}毫秒")
    print(f"最大响应时间: {stats['max_response_time_ms']}毫秒")
    
    # 方式2：使用装饰器记录函数执行时间
    @performance_log
    def query_experiment_data(experiment_id):
        # 函数执行时间会被自动记录
        return dao.get_experiment_data_points(experiment_id)
    
    # 方式3：记录并发用户操作
    monitor = PerformanceMonitor()
    monitor.register_user('user1')  # 注册用户会话
    
    with monitor.track_user_operation('user1', 'query'):
        # 用户操作代码
        pass
    
    # 生成性能报告
    monitor.generate_report('performance_report.csv')

主要功能:
    - PerformanceMonitor: 性能监控类
        - __init__(): 初始化监控器
        
        - measure_operation(operation_name): 
            创建用于测量操作执行时间的上下文管理器
            
        - start_measurement(operation_name): 
            手动开始测量操作执行时间
            
        - end_measurement(): 
            手动结束测量并记录执行时间
            
        - register_user(user_id): 
            注册用户会话，用于并发监控
            
        - track_user_operation(user_id, operation_type): 
            跟踪用户操作的上下文管理器
            
        - get_statistics(): 
            获取性能统计信息（平均响应时间、最大响应时间、操作次数等）
            
        - get_concurrent_users_count(): 
            获取当前并发用户数
            
        - get_throughput(time_window_seconds=60): 
            获取指定时间窗口内的吞吐量（每秒操作数）
            
        - generate_report(file_path): 
            生成性能报告CSV文件
            
    - performance_log: 性能日志装饰器
        用于装饰函数并自动记录其执行时间
        
    - OperationContext: 操作上下文管理器类
        实现上下文管理协议，用于自动测量操作执行时间
"""

import time
import csv
import functools
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Callable, Optional, ContextManager
from contextlib import contextmanager

from utils.logger import get_logger

logger = get_logger(__name__)

class OperationContext:
    """
    操作上下文管理器类，用于自动测量操作执行时间
    """
    
    def __init__(self, monitor, operation_name: str):
        """
        初始化操作上下文
        
        Args:
            monitor: PerformanceMonitor实例
            operation_name: 操作名称
        """
        self.monitor = monitor
        self.operation_name = operation_name
    
    def __enter__(self):
        """
        进入上下文，开始计时
        """
        self.monitor.start_measurement(self.operation_name)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        退出上下文，结束计时并记录
        """
        self.monitor.end_measurement()
        if exc_type:
            logger.error(f"操作 {self.operation_name} 执行出错: {exc_val}")


class PerformanceMonitor:
    """
    性能监控类，提供数据库操作性能监控和统计功能
    """
    
    def __init__(self):
        """
        初始化性能监控器
        """
        self.operations = []  # 存储所有操作记录
        self._current_operation = None  # 当前正在测量的操作
        self._start_time = None  # 当前操作开始时间
        self._active_users = {}  # 活跃用户字典 {user_id: last_activity_time}
        self._user_operations = []  # 用户操作记录
        self._lock = threading.RLock()  # 线程锁，用于并发安全
    
    @contextmanager
    def measure_operation(self, operation_name: str) -> ContextManager:
        """
        创建用于测量操作执行时间的上下文管理器
        
        Args:
            operation_name: 操作名称
            
        Yields:
            OperationContext: 操作上下文管理器
        """
        try:
            self.start_measurement(operation_name)
            yield self
        finally:
            self.end_measurement()
    
    def start_measurement(self, operation_name: str) -> None:
        """
        手动开始测量操作执行时间
        
        Args:
            operation_name: 操作名称
        """
        with self._lock:
            if self._current_operation:
                logger.warning(f"上一个操作 {self._current_operation} 尚未结束就开始了新操作 {operation_name}")
                self.end_measurement()  # 自动结束上一个操作
            
            self._current_operation = operation_name
            self._start_time = time.time()
    
    def end_measurement(self) -> Optional[Dict[str, Any]]:
        """
        手动结束测量并记录执行时间
        
        Returns:
            Optional[Dict[str, Any]]: 操作记录，如果没有正在进行的操作则返回None
        """
        with self._lock:
            if not self._current_operation or not self._start_time:
                logger.warning("没有正在进行的操作测量")
                return None
            
            end_time = time.time()
            duration_ms = (end_time - self._start_time) * 1000  # 转换为毫秒
            timestamp = datetime.now()
            
            operation_record = {
                'operation_name': self._current_operation,
                'start_time': self._start_time,
                'end_time': end_time,
                'duration_ms': duration_ms,
                'timestamp': timestamp
            }
            
            self.operations.append(operation_record)
            
            logger.debug(f"操作 {self._current_operation} 执行耗时: {duration_ms:.2f}ms")
            
            self._current_operation = None
            self._start_time = None
            
            return operation_record
    
    def register_user(self, user_id: str) -> None:
        """
        注册用户会话，用于并发监控
        
        Args:
            user_id: 用户标识
        """
        with self._lock:
            current_time = datetime.now()
            self._active_users[user_id] = current_time
            logger.debug(f"用户 {user_id} 已注册")
    
    def unregister_user(self, user_id: str) -> None:
        """
        注销用户会话
        
        Args:
            user_id: 用户标识
        """
        with self._lock:
            if user_id in self._active_users:
                del self._active_users[user_id]
                logger.debug(f"用户 {user_id} 已注销")
    
    @contextmanager
    def track_user_operation(self, user_id: str, operation_type: str) -> ContextManager:
        """
        跟踪用户操作的上下文管理器
        
        Args:
            user_id: 用户标识
            operation_type: 操作类型
            
        Yields:
            ContextManager: 上下文管理器
        """
        start_time = time.time()
        try:
            # 更新用户活跃时间
            with self._lock:
                self._active_users[user_id] = datetime.now()
            
            yield
        finally:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            with self._lock:
                self._user_operations.append({
                    'user_id': user_id,
                    'operation_type': operation_type,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_ms': duration_ms,
                    'timestamp': datetime.now()
                })
                
                # 更新用户活跃时间
                self._active_users[user_id] = datetime.now()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取性能统计信息
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        with self._lock:
            # 合并所有操作记录（包括普通操作和用户操作）
            all_operations = self.operations.copy()
            
            # 将用户操作也添加到统计中
            for user_op in self._user_operations:
                all_operations.append({
                    'operation_name': user_op['operation_type'],
                    'start_time': user_op['start_time'],
                    'end_time': user_op['end_time'],
                    'duration_ms': user_op['duration_ms'],
                    'timestamp': user_op['timestamp']
                })
            
            if not all_operations:
                return {
                    'total_operations': 0,
                    'avg_response_time_ms': 0,
                    'max_response_time_ms': 0,
                    'min_response_time_ms': 0,
                    'operation_counts': {},
                    'current_active_users': len(self._active_users)
                }
            
            # 计算响应时间统计
            durations = [op['duration_ms'] for op in all_operations]
            avg_response_time = sum(durations) / len(durations)
            max_response_time = max(durations)
            min_response_time = min(durations)
            
            # 统计各类操作次数
            operation_counts = {}
            for op in all_operations:
                op_name = op['operation_name']
                operation_counts[op_name] = operation_counts.get(op_name, 0) + 1
            
            return {
                'total_operations': len(all_operations),
                'avg_response_time_ms': avg_response_time,
                'max_response_time_ms': max_response_time,
                'min_response_time_ms': min_response_time,
                'operation_counts': operation_counts,
                'current_active_users': len(self._active_users)
            }
    
    def get_concurrent_users_count(self, active_threshold_minutes: int = 5) -> int:
        """
        获取当前并发用户数
        
        Args:
            active_threshold_minutes: 用户活跃阈值（分钟），超过此时间未活动视为非活跃
            
        Returns:
            int: 当前并发用户数
        """
        with self._lock:
            current_time = datetime.now()
            threshold_time = current_time - timedelta(minutes=active_threshold_minutes)
            
            # 清理非活跃用户
            inactive_users = []
            for user_id, last_time in self._active_users.items():
                if last_time < threshold_time:
                    inactive_users.append(user_id)
            
            for user_id in inactive_users:
                del self._active_users[user_id]
            
            return len(self._active_users)
    
    def get_throughput(self, time_window_seconds: int = 60) -> float:
        """
        获取指定时间窗口内的吞吐量（每秒操作数）
        
        Args:
            time_window_seconds: 时间窗口大小（秒）
            
        Returns:
            float: 每秒操作数
        """
        with self._lock:
            if not self.operations:
                return 0.0
            
            current_time = time.time()
            window_start = current_time - time_window_seconds
            
            # 统计时间窗口内的操作数量
            recent_operations = [
                op for op in self.operations 
                if op['end_time'] >= window_start
            ]
            
            if not recent_operations:
                return 0.0
            
            return len(recent_operations) / time_window_seconds
    
    def generate_report(self, file_path: str) -> bool:
        """
        生成性能报告CSV文件
        
        Args:
            file_path: 报告文件路径
            
        Returns:
            bool: 是否成功生成报告
        """
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                # 中文表头字段名
                fieldnames = [
                    '操作名称', '开始时间', '结束时间', 
                    '耗时(毫秒)', '时间戳'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for op in self.operations:
                    writer.writerow({
                        '操作名称': op['operation_name'],
                        '开始时间': datetime.fromtimestamp(op['start_time']).strftime('%Y-%m-%d %H:%M:%S.%f'),
                        '结束时间': datetime.fromtimestamp(op['end_time']).strftime('%Y-%m-%d %H:%M:%S.%f'),
                        '耗时(毫秒)': f"{op['duration_ms']:.2f}",
                        '时间戳': op['timestamp'].strftime('%Y-%m-%d %H:%M:%S.%f')
                    })
            
            logger.info(f"性能报告已生成: {file_path}")
            return True
        except Exception as e:
            logger.error(f"生成性能报告失败: {str(e)}")
            return False
    
    def clear_data(self) -> None:
        """
        清除收集的数据
        """
        with self._lock:
            self.operations = []
            self._user_operations = []
            # 不清除活跃用户信息


def performance_log(func: Callable) -> Callable:
    """
    性能日志装饰器，用于自动记录函数执行时间
    
    Args:
        func: 需要监控的函数
        
    Returns:
        Callable: 装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 创建一个临时的监控器
        monitor = PerformanceMonitor()
        operation_name = f"{func.__module__}.{func.__name__}"
        
        try:
            monitor.start_measurement(operation_name)
            result = func(*args, **kwargs)
            return result
        finally:
            duration = monitor.end_measurement()
            logger.info(f"函数 {operation_name} 执行耗时: {duration['duration_ms']:.2f}ms")
    
    return wrapper