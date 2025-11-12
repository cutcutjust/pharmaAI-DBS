"""
数据库连接诊断脚本
用于测试和诊断数据库连接问题
"""

import psycopg2
import os
import sys

# 尝试从config.database导入配置
try:
    from config.database import DB_CONFIG as CONFIG_DB_CONFIG
    print("✓ 找到 config/database.py 配置文件")
    config_from_file = True
except ImportError:
    print("⚠ 未找到 config/database.py，使用默认配置")
    CONFIG_DB_CONFIG = None
    config_from_file = False

# 数据库连接参数（优先使用环境变量，其次使用config文件，最后使用默认值）
if config_from_file:
    DB_CONFIG = {
        'host': os.environ.get('DB_HOST', CONFIG_DB_CONFIG.get('host', 'localhost')),
        'port': os.environ.get('DB_PORT', str(CONFIG_DB_CONFIG.get('port', '5432'))),
        'database': os.environ.get('DB_NAME', CONFIG_DB_CONFIG.get('database', 'pharmacopoeia_db')),
        'user': os.environ.get('DB_USER', CONFIG_DB_CONFIG.get('user', 'postgres')),
        'password': os.environ.get('DB_PASSWORD', CONFIG_DB_CONFIG.get('password', 'postgres'))
    }
else:
    DB_CONFIG = {
        'host': os.environ.get('DB_HOST', 'localhost'),
        'port': os.environ.get('DB_PORT', '5432'),
        'database': os.environ.get('DB_NAME', 'pharmacopoeia_db'),
        'user': os.environ.get('DB_USER', 'postgres'),
        'password': os.environ.get('DB_PASSWORD', 'postgres')
    }

def test_connection():
    """测试数据库连接"""
    print("=" * 60)
    print("数据库连接诊断")
    print("=" * 60)
    print("连接配置:")
    print(f"  Host: {DB_CONFIG['host']}")
    print(f"  Port: {DB_CONFIG['port']}")
    print(f"  Database: {DB_CONFIG['database']}")
    print(f"  User: {DB_CONFIG['user']}")
    print(f"  Password: {'*' * len(DB_CONFIG['password']) if DB_CONFIG['password'] else '(未设置)'}")
    print("=" * 60)
    
    # 测试1: 尝试连接到 postgres 数据库（默认数据库）
    print("\n测试1: 连接到默认数据库 'postgres'...")
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database='postgres',
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        print("✓ 成功连接到 'postgres' 数据库")
        
        # 检查目标数据库是否存在
        with conn.cursor() as cur:
            cur.execute("""
                SELECT datname FROM pg_database 
                WHERE datname = %s
            """, (DB_CONFIG['database'],))
            result = cur.fetchone()
            
            if result:
                print(f"✓ 数据库 '{DB_CONFIG['database']}' 存在")
            else:
                print(f"✗ 数据库 '{DB_CONFIG['database']}' 不存在")
                print(f"\n需要创建数据库 '{DB_CONFIG['database']}'")
                print("可以使用以下SQL命令创建:")
                print(f"  CREATE DATABASE {DB_CONFIG['database']};")
        
        conn.close()
    except psycopg2.OperationalError as e:
        error_msg = str(e) if e else "未知错误"
        print(f"✗ 连接失败: {error_msg}")
        
        # 尝试其他常见端口
        print("\n尝试其他端口...")
        test_ports = ['5433', '5434']
        if DB_CONFIG['port'] == '5432':
            test_ports = ['5433', '5434']
        elif DB_CONFIG['port'] == '5433':
            test_ports = ['5432', '5434']
        
        found_port = False
        for port in test_ports:
            try:
                test_conn = psycopg2.connect(
                    host=DB_CONFIG['host'],
                    port=port,
                    database='postgres',
                    user=DB_CONFIG['user'],
                    password=DB_CONFIG['password'],
                    connect_timeout=3
                )
                print(f"✓ 端口 {port} 可以连接！")
                test_conn.close()
                found_port = True
                print(f"\n建议: 设置环境变量 DB_PORT={port} 或修改配置文件中的端口号")
                break
            except Exception:
                pass
        
        if not found_port:
            print("\n可能的原因:")
            print("  1. PostgreSQL 服务未运行")
            print("  2. 端口号不正确")
            print("  3. 用户名或密码不正确")
            print("  4. 防火墙阻止连接")
            print("  5. PostgreSQL 配置不允许本地连接")
        
        return False
    except Exception as e:
        error_msg = str(e) if e else "未知错误"
        error_type = type(e).__name__
        print(f"✗ 发生错误 ({error_type}): {error_msg}")
        import traceback
        print("\n详细错误信息:")
        traceback.print_exc()
        return False
    
    # 测试2: 尝试连接到目标数据库
    print(f"\n测试2: 连接到目标数据库 '{DB_CONFIG['database']}'...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print(f"✓ 成功连接到 '{DB_CONFIG['database']}' 数据库")
        
        # 检查表是否存在
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = cur.fetchall()
            
            if tables:
                print(f"\n数据库中的表 ({len(tables)} 个):")
                for table in tables:
                    print(f"  - {table[0]}")
            else:
                print("\n数据库中没有表（可能需要运行 schema.sql 创建表结构）")
        
        conn.close()
        print("\n✓ 所有连接测试通过！")
        return True
    except psycopg2.OperationalError as e:
        error_msg = str(e) if e else "未知错误"
        print(f"✗ 连接失败: {error_msg}")
        if "does not exist" in error_msg:
            print(f"\n数据库 '{DB_CONFIG['database']}' 不存在，需要先创建")
        return False
    except Exception as e:
        error_msg = str(e) if e else "未知错误"
        error_type = type(e).__name__
        print(f"✗ 发生错误 ({error_type}): {error_msg}")
        import traceback
        print("\n详细错误信息:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

