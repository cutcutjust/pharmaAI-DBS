"""
数据库包(Database Package)

本包提供数据库连接管理、表结构定义和索引创建等基础功能，是系统与数据库交互的核心组件。

使用方法:
    from database.connection import get_connection_pool, get_connection
    
    # 获取连接池
    pool = get_connection_pool()
    
    # 获取单个连接
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM inspectors")
            results = cursor.fetchall()
    finally:
        conn.close()  # 确保连接归还到连接池
    
    # 或者使用with语句自动管理连接
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM messages LIMIT 10")
            messages = cursor.fetchall()
    
    # 执行SQL脚本
    from database.connection import execute_script_file
    execute_script_file('database/schema.sql')  # 创建表结构
    execute_script_file('database/indexes.sql') # 创建索引

包含模块:
    - connection.py: 提供数据库连接池管理，支持多用户并发访问
    - schema.sql: 定义8个核心表的DDL语句，用于创建数据库表结构
    - indexes.sql: 为高频查询字段创建索引，加速数据查询
"""

import os
import logging
from .connection import (
    get_connection_pool,
    get_connection,
    get_transaction_connection,
    execute_script_file,
    init_connection_pool,
    close_all_connections
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_database(drop_existing=False):
    """
    初始化数据库，创建表结构和索引。
    
    Args:
        drop_existing: 如果为True，将尝试先删除所有现有表（谨慎使用）
    
    Returns:
        bool: 初始化是否成功
    """
    try:
        logger.info("开始初始化数据库...")
        
        if drop_existing:
            logger.warning("准备删除所有现有表...")
            # 此处添加删除所有表的SQL
            drop_script = """
            DO $$ 
            DECLARE
                tables CURSOR FOR
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public';
            BEGIN
                FOR table_record IN tables LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || table_record.tablename || ' CASCADE';
                END LOOP;
            END $$;
            """
            
            with get_connection() as conn:
                with conn.cursor() as cursor:
                    logger.info("执行删除表操作...")
                    cursor.execute(drop_script)
            logger.info("所有现有表已删除")
        
        # 获取当前模块的目录路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 执行建表脚本
        schema_path = os.path.join(current_dir, 'schema.sql')
        logger.info(f"执行建表脚本: {schema_path}")
        schema_result = execute_script_file(schema_path)
        if not schema_result['success']:
            logger.error(f"建表失败: {schema_result['error']}")
            return False
        
        # 验证表是否创建成功（检查关键表是否存在）
        logger.info("验证表是否创建成功...")
        try:
            from .connection import get_connection
            with get_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查关键表是否存在
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'pharmacopoeia_items'
                        )
                    """)
                    table_exists = cursor.fetchone()[0]
                    if not table_exists:
                        logger.error("表创建验证失败: pharmacopoeia_items 表不存在")
                        return False
                    logger.info("表创建验证成功: pharmacopoeia_items 表已存在")
        except Exception as e:
            logger.error(f"验证表存在性时出错: {e}")
            return False
        
        # 执行索引创建脚本
        indexes_path = os.path.join(current_dir, 'indexes.sql')
        logger.info(f"执行索引创建脚本: {indexes_path}")
        indexes_result = execute_script_file(indexes_path)
        if not indexes_result['success']:
            logger.error(f"创建索引失败: {indexes_result['error']}")
            return False
        
        logger.info("数据库初始化完成!")
        return True
    
    except Exception as e:
        logger.error(f"数据库初始化过程中发生错误: {e}")
        return False

# 导出的函数和类
__all__ = [
    'get_connection_pool',
    'get_connection',
    'get_transaction_connection',
    'execute_script_file',
    'init_connection_pool',
    'close_all_connections',
    'init_database'
]