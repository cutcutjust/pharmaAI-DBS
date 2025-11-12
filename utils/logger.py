"""
通用日志模块(General Logger Module)

本模块提供智药AI系统的通用日志功能，用于记录系统运行中的各种信息、
警告和错误，便于系统运行状态监控和调试。

使用方法:
    from utils.logger import setup_logger, get_logger
    
    # 方式1: 在应用启动时设置日志配置
    setup_logger(
        log_file='app.log',        # 日志文件路径
        console_level='INFO',      # 控制台输出级别
        file_level='DEBUG',        # 文件记录级别
        max_file_size=10*1024*1024 # 日志文件最大大小（10MB）
    )
    
    # 方式2: 在各个模块中获取日志记录器
    logger = get_logger(__name__)  # 使用模块名作为日志记录器名称
    
    # 记录不同级别的日志
    logger.debug("详细调试信息")
    logger.info("一般信息")
    logger.warning("警告信息")
    logger.error("错误信息")
    logger.critical("致命错误信息")
    
    # 记录异常信息
    try:
        # 执行可能出错的操作
        result = 10 / 0
    except Exception as e:
        logger.exception("发生异常: %s", str(e))  # 自动记录异常堆栈
    
    # 记录带有上下文的信息
    user_id = 123
    operation = "查询药典条目"
    logger.info("用户 %s 执行操作: %s", user_id, operation)

主要功能:
    - setup_logger(log_file=None, console_level='INFO', file_level='DEBUG', max_file_size=10*1024*1024): 
        设置全局日志配置，包括日志文件路径、日志级别和文件大小限制
        
    - get_logger(name=None): 
        获取指定名称的日志记录器实例，如果不指定名称则返回根日志记录器
        
    - LoggerFormatter: 
        自定义日志格式化器类，用于格式化日志消息，添加时间戳、日志级别和模块名
        
    - configure_logger(logger_instance, console_level='INFO', file_level='DEBUG'): 
        配置指定日志记录器的级别和处理器
        
    - _get_console_handler(level='INFO'): 
        创建控制台日志处理器（内部函数）
        
    - _get_file_handler(log_file, level='DEBUG', max_size=10*1024*1024): 
        创建文件日志处理器（内部函数）
"""

import os
import logging
from logging.handlers import RotatingFileHandler
import sys

# 日志级别映射字典
_LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

class LoggerFormatter(logging.Formatter):
    """自定义日志格式化器类，用于格式化日志消息
    
    提供了更加结构化和易于阅读的日志格式。
    """
    
    def __init__(self):
        """初始化日志格式化器
        
        设置默认的日志格式，包括时间、日志级别、模块名和消息内容
        """
        # 设置格式: 时间 - 日志级别 - 模块名 - 消息内容
        fmt = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        datefmt = '%Y-%m-%d %H:%M:%S'
        super().__init__(fmt=fmt, datefmt=datefmt)

def _get_console_handler(level='INFO'):
    """创建控制台日志处理器

    Args:
        level (str, optional): 日志级别. Defaults to 'INFO'.

    Returns:
        logging.StreamHandler: 配置好的控制台日志处理器
    """
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    # 设置日志级别
    console_handler.setLevel(_LOG_LEVELS.get(level, logging.INFO))
    # 设置日志格式
    console_handler.setFormatter(LoggerFormatter())
    return console_handler

def _get_file_handler(log_file, level='DEBUG', max_size=10*1024*1024):
    """创建文件日志处理器

    Args:
        log_file (str): 日志文件路径
        level (str, optional): 日志级别. Defaults to 'DEBUG'.
        max_size (int, optional): 日志文件最大大小(字节). Defaults to 10MB.

    Returns:
        logging.FileHandler: 配置好的文件日志处理器
    """
    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 创建轮转文件处理器，默认保留5个备份
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=max_size, 
        backupCount=5,
        encoding='utf-8'
    )
    # 设置日志级别
    file_handler.setLevel(_LOG_LEVELS.get(level, logging.DEBUG))
    # 设置日志格式
    file_handler.setFormatter(LoggerFormatter())
    return file_handler

def configure_logger(logger_instance, console_level='INFO', file_level='DEBUG'):
    """配置指定日志记录器的级别和处理器

    Args:
        logger_instance (logging.Logger): 日志记录器实例
        console_level (str, optional): 控制台日志级别. Defaults to 'INFO'.
        file_level (str, optional): 文件日志级别. Defaults to 'DEBUG'.
    """
    # 移除现有的处理器，防止重复添加
    for handler in logger_instance.handlers[:]:
        logger_instance.removeHandler(handler)
    
    # 设置日志级别为最低级别，以便处理所有日志
    logger_instance.setLevel(logging.DEBUG)
    
    # 阻止日志传播到父记录器
    logger_instance.propagate = False

def setup_logger(log_file=None, console_level='INFO', file_level='DEBUG', max_file_size=10*1024*1024):
    """设置全局日志配置

    Args:
        log_file (str, optional): 日志文件路径. Defaults to None.
        console_level (str, optional): 控制台日志级别. Defaults to 'INFO'.
        file_level (str, optional): 文件日志级别. Defaults to 'DEBUG'.
        max_file_size (int, optional): 日志文件最大大小(字节). Defaults to 10MB.

    Returns:
        logging.Logger: 配置好的根日志记录器
    """
    # 获取根日志记录器
    root_logger = logging.getLogger()
    
    # 配置根日志记录器
    configure_logger(root_logger, console_level, file_level)
    
    # 添加控制台处理器
    root_logger.addHandler(_get_console_handler(console_level))
    
    # 如果指定了日志文件，则添加文件处理器
    if log_file:
        root_logger.addHandler(_get_file_handler(log_file, file_level, max_file_size))
    
    return root_logger

def get_logger(name=None):
    """获取指定名称的日志记录器实例

    Args:
        name (str, optional): 日志记录器名称. Defaults to None.

    Returns:
        logging.Logger: 日志记录器实例
    """
    # 获取指定名称的日志记录器
    logger = logging.getLogger(name)
    
    # 如果没有处理器，则添加一个控制台处理器
    if not logger.handlers:
        # 设置日志级别
        logger.setLevel(logging.DEBUG)
        # 添加控制台处理器
        logger.addHandler(_get_console_handler())
    
    return logger
    