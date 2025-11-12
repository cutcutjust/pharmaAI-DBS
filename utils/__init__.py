"""
工具包(Utils Package)

本包提供智药AI系统的各种工具类和辅助功能，
主要用于日志记录和性能监控，支持系统运行中的调试和性能分析。

使用方法:
    from utils.logger import setup_logger, get_logger
    from utils.performance_logger import PerformanceLogger, log_execution_time
    
    # 使用系统日志记录器
    logger = get_logger(__name__)
    logger.info("系统正在启动...")
    logger.error("发生错误：数据库连接失败")
    
    # 使用性能日志记录器
    perf_logger = PerformanceLogger()
    perf_logger.start("查询操作")
    # 执行查询...
    perf_logger.end("查询操作")
    
    # 使用装饰器记录函数执行时间
    @log_execution_time
    def complex_query():
        # 函数执行时会自动记录执行时间
        pass

包含模块:
    - logger.py: 提供通用日志功能，用于记录系统运行信息和错误
    - performance_logger.py: 提供性能监控日志功能，用于记录操作执行时间和统计
"""

from utils.logger import setup_logger, get_logger
from utils.performance_logger import PerformanceLogger, log_execution_time
from utils.db_statistics import (
    summarize_volume_counts_from_records,
    log_pharmacopoeia_items_stats_from_records,
    log_pharmacopoeia_items_stats_from_db,
)

# 导出的公共接口
__all__ = [
    'setup_logger',
    'get_logger',
    'PerformanceLogger',
    'log_execution_time',
    'summarize_volume_counts_from_records',
    'log_pharmacopoeia_items_stats_from_records',
    'log_pharmacopoeia_items_stats_from_db',
]

# 初始化默认日志记录器
default_logger = get_logger("pharmaAI-DBS")