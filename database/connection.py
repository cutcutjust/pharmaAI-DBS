"""
数据库连接管理模块(Database Connection Manager)

本模块提供数据库连接池管理功能，负责创建、维护和释放数据库连接，
支持多用户并发访问数据库，并提供连接资源的有效复用。

使用方法:
    from database.connection import get_connection_pool, get_connection
    
    # 方式1: 直接获取连接池实例
    pool = get_connection_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM pharmacopoeia_items LIMIT 5")
            items = cursor.fetchall()
            print(f"获取到 {len(items)} 条药典记录")
    finally:
        pool.putconn(conn)  # 归还连接到池
    
    # 方式2: 使用封装的get_connection函数和with语句（推荐）
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM messages")
            count = cursor.fetchone()[0]
            print(f"消息总数: {count}")
    
    # 执行SQL脚本文件
    execute_script_file('path/to/script.sql')
    
    # 在事务中执行多条SQL语句
    with get_transaction_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO inspectors (name, employee_no) VALUES (%s, %s)", 
                         ("张三", "YJ2025001"))
            cursor.execute("INSERT INTO laboratories (lab_code, lab_name) VALUES (%s, %s)",
                         ("LAB001", "中心实验室"))
            # 事务自动提交；如发生异常，自动回滚

主要功能:
    - init_connection_pool(max_connections=10, min_connections=1):
        初始化数据库连接池，设置最大和最小连接数。
        
    - get_connection_pool():
        获取已初始化的连接池单例实例。
        
    - get_connection():
        从连接池获取一个连接，可用于with语句的上下文管理器。
        
    - get_transaction_connection():
        获取一个事务连接，自动开启事务，用于with语句。
        
    - execute_script_file(script_path):
        执行指定路径的SQL脚本文件。
        
    - close_all_connections():
        关闭所有连接并清理连接池，通常在应用退出时调用。
        
    - ConnectionPoolManager类:
        管理连接池生命周期的类，实现了上下文管理器协议。
        
    - TransactionConnectionManager类:
        管理事务连接的类，实现了上下文管理器协议。
"""

import os
import re
import time
import logging
import psycopg2
from psycopg2 import pool
from typing import Optional, Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局连接池
_connection_pool = None

# 尝试从config.database导入配置
try:
    from config.database import DB_CONFIG as CONFIG_DB_CONFIG
    logger.debug("从 config.database 加载数据库配置")
    # 使用配置文件中的值作为默认值，但环境变量优先
    DB_CONFIG = {
        'host': os.environ.get('DB_HOST', CONFIG_DB_CONFIG.get('host', 'localhost')),
        'port': os.environ.get('DB_PORT', str(CONFIG_DB_CONFIG.get('port', '5432'))),
        'database': os.environ.get('DB_NAME', CONFIG_DB_CONFIG.get('database', 'pharmacopoeia_db')),
        'user': os.environ.get('DB_USER', CONFIG_DB_CONFIG.get('user', 'postgres')),
        'password': os.environ.get('DB_PASSWORD', CONFIG_DB_CONFIG.get('password', 'postgres'))
    }
except ImportError:
    logger.debug("未找到 config.database，使用默认配置")
    # 数据库连接参数（仅使用环境变量和默认值）
    DB_CONFIG = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': os.environ.get('DB_PORT', '5432'),
        'database': os.environ.get('DB_NAME', 'pharmacopoeia_db'),
        'user': os.environ.get('DB_USER', 'postgres'),
        'password': os.environ.get('DB_PASSWORD', 'postgres')
    }

def init_connection_pool(max_connections: int = 10, min_connections: int = 1, config: Optional[Dict[str, Any]] = None) -> None:
    """
    初始化数据库连接池。
    
    Args:
        max_connections: 最大连接数
        min_connections: 最小连接数
        config: 可选的数据库连接参数（host, port, database, user, password）
    """
    global _connection_pool, DB_CONFIG
    
    if _connection_pool is not None:
        logger.warning("连接池已经初始化，将重新初始化")
        close_all_connections()
    
    # 如果传入了配置，更新当前使用的连接参数
    if config is not None:
        for key in ('host', 'port', 'database', 'user', 'password'):
            if key in config:
                DB_CONFIG[key] = config[key]
    
    try:
        logger.info(f"初始化连接池: min={min_connections}, max={max_connections}")
        _connection_pool = pool.ThreadedConnectionPool(
            minconn=min_connections,
            maxconn=max_connections,
            **DB_CONFIG
        )
        logger.info("连接池初始化成功")
    except psycopg2.OperationalError as e:
        error_msg = str(e) if e else "未知错误"
        logger.error(f"连接池初始化失败: {error_msg}")
        logger.error(f"数据库配置: host={DB_CONFIG.get('host')}, port={DB_CONFIG.get('port')}, database={DB_CONFIG.get('database')}, user={DB_CONFIG.get('user')}")
        logger.error("=" * 60)
        logger.error("数据库连接失败，请检查以下事项：")
        logger.error("1. PostgreSQL服务是否正在运行？")
        logger.error("   Windows: 检查服务管理器或运行 'net start postgresql-x64-XX'")
        logger.error("2. 数据库配置是否正确？")
        logger.error("   可以通过环境变量设置: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD")
        logger.error("3. 数据库 'pharmacopoeia_db' 是否存在？")
        logger.error("   如果不存在，请先创建数据库")
        logger.error("4. 用户权限是否正确？")
        logger.error("   确保用户有访问数据库的权限")
        logger.error("=" * 60)
        raise
    except psycopg2.Error as e:
        error_msg = str(e) if e else "未知错误"
        logger.error(f"连接池初始化失败: {error_msg}")
        logger.error(f"数据库配置: host={DB_CONFIG.get('host')}, port={DB_CONFIG.get('port')}, database={DB_CONFIG.get('database')}, user={DB_CONFIG.get('user')}")
        raise

def get_connection_pool(config: Optional[Dict[str, Any]] = None):
    """
    获取已初始化的连接池单例实例。
    如果连接池尚未初始化，或需要使用传入的配置，则自动初始化。
    
    Args:
        config: 可选的数据库连接参数，如果包含 min_connections 和 max_connections，
                将用于设置连接池大小
    
    Returns:
        ThreadedConnectionPool: 连接池实例
    """
    global _connection_pool
    
    if _connection_pool is None or config is not None:
        logger.info("连接池尚未初始化或需要重置，自动初始化")
        # 从配置中提取连接池参数
        min_conn = config.get('min_connections', 1) if config else 1
        max_conn = config.get('max_connections', 10) if config else 10
        init_connection_pool(max_connections=max_conn, min_connections=min_conn, config=config)
    
    return _connection_pool

class ConnectionPoolManager:
    """
    连接池管理器，提供上下文管理器接口。
    
    使用方法:
        with ConnectionPoolManager() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM inspectors")
    """
    def __init__(self):
        self.pool = get_connection_pool()
        self.conn = None
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        try:
            self.conn = self.pool.getconn()
            return self.conn
        except Exception as e:
            logger.error(f"获取数据库连接失败: {e}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if self.conn is not None:
            if exc_type is not None:
                logger.warning(f"操作出现异常: {exc_type.__name__}: {exc_val}")
            
            logger.debug(f"操作完成，用时: {duration:.4f}秒")
            self.pool.putconn(self.conn)
            self.conn = None

def get_connection():
    """
    从连接池获取一个连接，可用于with语句的上下文管理器。
    
    Returns:
        ConnectionPoolManager: 连接管理器实例
    """
    return ConnectionPoolManager()

class TransactionConnectionManager:
    """
    事务连接管理器，提供上下文管理器接口。
    自动开启事务，退出时自动提交或回滚。
    
    使用方法:
        with TransactionConnectionManager() as conn:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO inspectors (...) VALUES (...)")
                cursor.execute("INSERT INTO inspector_lab_access (...) VALUES (...)")
                # 退出时自动提交事务；如有异常则自动回滚
    """
    def __init__(self):
        self.pool = get_connection_pool()
        self.conn = None
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        try:
            self.conn = self.pool.getconn()
            # 关闭自动提交，开启事务
            self.conn.autocommit = False
            return self.conn
        except Exception as e:
            logger.error(f"获取事务连接失败: {e}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if self.conn is not None:
            try:
                if exc_type is not None:
                    logger.warning(f"事务出现异常，执行回滚: {exc_type.__name__}: {exc_val}")
                    self.conn.rollback()
                else:
                    logger.debug("事务正常完成，执行提交")
                    self.conn.commit()
            except Exception as e:
                logger.error(f"事务提交/回滚失败: {e}")
                self.conn.rollback()
            finally:
                logger.debug(f"事务操作完成，用时: {duration:.4f}秒")
                # 恢复自动提交设置
                self.conn.autocommit = True
                self.pool.putconn(self.conn)
                self.conn = None

def get_transaction_connection():
    """
    获取一个事务连接，自动开启事务，用于with语句。
    
    Returns:
        TransactionConnectionManager: 事务连接管理器实例
    """
    return TransactionConnectionManager()

def execute_script_file(script_path: str) -> Dict[str, Any]:
    """
    执行指定路径的SQL脚本文件。
    
    Args:
        script_path: SQL脚本文件路径
        
    Returns:
        Dict: 包含执行结果的字典，如成功状态、用时等
    """
    start_time = time.time()
    result = {
        'success': False,
        'duration': 0,
        'error': None
    }
    
    try:
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"脚本文件不存在: {script_path}")
        
        with open(script_path, 'r', encoding='utf-8') as file:
            script_content = file.read()
        
        with get_connection() as conn:
            # 确保使用自动提交模式（PostgreSQL DDL需要立即提交）
            conn.autocommit = True
            with conn.cursor() as cursor:
                logger.info(f"开始执行SQL脚本: {script_path}")
                # 移除多行注释 /* ... */
                # 先移除多行注释
                script_content = re.sub(r'/\*.*?\*/', '', script_content, flags=re.DOTALL)
                
                # 分割SQL语句（按分号分割）
                lines = script_content.split('\n')
                cleaned_lines = []
                for line in lines:
                    # 移除单行注释（-- 后面的内容）
                    if '--' in line:
                        line = line[:line.index('--')]
                    cleaned_lines.append(line)
                
                cleaned_script = '\n'.join(cleaned_lines)
                
                # 按分号分割语句，过滤空语句
                statements = [s.strip() for s in cleaned_script.split(';') if s.strip()]
                
                for i, statement in enumerate(statements, 1):
                    if statement:
                        try:
                            cursor.execute(statement)
                            logger.debug(f"执行第 {i}/{len(statements)} 条SQL语句")
                        except Exception as e:
                            logger.error(f"执行第 {i} 条SQL语句时出错: {e}")
                            logger.error(f"语句内容: {statement[:200]}...")
                            raise
                
                logger.info(f"SQL脚本执行完成: {script_path}，共执行 {len(statements)} 条语句")
        
        result['success'] = True
    except Exception as e:
        logger.error(f"执行SQL脚本失败: {e}")
        result['error'] = str(e)
    finally:
        result['duration'] = time.time() - start_time
        logger.debug(f"脚本执行用时: {result['duration']:.4f}秒")
    
    return result

def close_all_connections():
    """
    关闭所有连接并清理连接池，通常在应用退出时调用。
    """
    global _connection_pool
    
    if _connection_pool is not None:
        logger.info("关闭所有数据库连接并清理连接池")
        _connection_pool.closeall()
        _connection_pool = None
        logger.info("连接池已清理")

# 在模块导入时自动初始化连接池
try:
    init_connection_pool()
except Exception as e:
    logger.warning(f"模块导入时自动初始化连接池失败: {e}")
    logger.warning("将在首次使用时尝试初始化连接池")