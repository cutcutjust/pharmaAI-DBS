# -*- coding: utf-8 -*-
"""
数据库连接配置

本模块包含连接到PostgreSQL/MySQL数据库所需的所有配置参数。
支持连接池管理，确保高效的数据库连接复用，适用于多用户并发访问场景。

项目: 智药AI (PharmaAI)
作用: 
    1. 提供数据库连接参数
    2. 配置连接池参数
    3. 支持不同环境的数据库配置切换（开发/测试/生产）

数据库设计:
    - 8个核心表: pharmacopoeia_items, inspectors, laboratories, 
                inspector_lab_access, conversations, messages, 
                experiment_records, experiment_data_points
    - 主要数据源: messages表(10万+记录)
    - 第二数据源: experiment_records和experiment_data_points表

使用方式:
    from config.database import DB_CONFIG
    conn = psycopg2.connect(**DB_CONFIG)

OID:16385
"""

import os

# 数据库连接参数
DB_CONFIG = {
    # 数据库连接信息
    'host': 'localhost',  # 数据库主机地址
    'port': 5433,         # 数据库端口号 (PostgreSQL默认5432，MySQL默认3306)
    'user': 'postgres',   # 数据库用户名
    'password': 'postgresql',       # 数据库密码
    'database': 'pharmacopoeia',  # 数据库名称
    
    # 连接池配置
    'min_connections': 5,     # 最小连接数
    'max_connections': 20,    # 最大连接数
    'connection_timeout': 30  # 连接超时时间(秒)
}

def get_test_db_config():
    """
    获取测试环境数据库连接配置。
    优先使用环境变量 TEST_DB_*，否则基于默认配置生成。
    返回的键与 psycopg2 连接参数一致。
    测试环境使用更大的连接池以支持并发测试。
    """
    return {
        'host': os.environ.get('TEST_DB_HOST', DB_CONFIG.get('host', 'localhost')),
        'port': os.environ.get('TEST_DB_PORT', str(DB_CONFIG.get('port', 5433))),
        'user': os.environ.get('TEST_DB_USER', DB_CONFIG.get('user', 'postgres')),
        'password': os.environ.get('TEST_DB_PASSWORD', DB_CONFIG.get('password', 'postgres')),
        'database': os.environ.get('TEST_DB_NAME', f"{DB_CONFIG.get('database', 'pharmacopoeia_db')}_test"),
        'min_connections': int(os.environ.get('TEST_DB_MIN_CONNECTIONS', '5')),
        'max_connections': int(os.environ.get('TEST_DB_MAX_CONNECTIONS', '30')),  # 测试环境需要更多连接
    }
