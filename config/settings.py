# -*- coding: utf-8 -*-
"""
系统全局配置参数

本模块包含智药AI系统的全局配置参数，用于系统各个组件间共享配置信息。

项目: 智药AI (PharmaAI-DBS)
作用:
    1. 定义系统运行参数
    2. 配置日志记录设置
    3. 设置性能监控参数
    4. 配置Web应用参数

功能配置:
    - 数据生成: 控制生成数据的数量和特性
    - 事务支持: 配置事务隔离级别和超时时间
    - 索引支持: 配置索引刷新间隔
    - 多用户访问: 配置最大并发连接数和会话超时时间
    - 性能监控: 配置性能日志记录级别和输出位置

使用方式:
    from config.settings import SETTINGS, LOG_CONFIG
"""

# 系统全局设置
SETTINGS = {
    # Web应用设置
    'web': {
        'host': '0.0.0.0',
        'port': 5000,
        'debug': True,
        'template_folder': 'web/templates',
    },
    
    # 性能监控设置
    'performance': {
        'log_queries': True,        # 是否记录SQL查询
        'log_threshold_ms': 100,    # 记录执行时间超过此阈值的查询(毫秒)
        'monitor_interval': 5,      # 性能采样间隔(秒)
    },
    
    # 数据生成设置
    'data_generation': {
        'conversation_count': 8000,     # 生成对话会话数量
        'messages_per_conversation': 15, # 每个会话平均消息数
        'experiment_count': 15000,      # 实验记录数量
        'datapoints_per_experiment': 3, # 每个实验的数据点数量
    },
    
    # 并发测试设置
    'concurrent_test': {
        'user_count': 10,           # 模拟用户数
        'requests_per_user': 100,   # 每个用户的请求数
        'request_interval': 0.5,    # 请求间隔(秒)
    }
}

# 日志配置
LOG_CONFIG = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'pharmacopoeia.log',
            'level': 'DEBUG',
        },
        'performance_file': {
            'class': 'logging.FileHandler',
            'filename': 'performance.log',
            'level': 'INFO',
        }
    },
    'loggers': {
        'app': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'performance': {
            'handlers': ['console', 'performance_file'],
            'level': 'INFO',
        },
    }
}
