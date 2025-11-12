"""
测试数据库设置脚本
自动创建测试数据库并初始化表结构和索引
"""

import os
import sys
import logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 将项目根目录添加到sys.path，以便导入config模块
# 当前文件在 tests/ 目录下，需要向上两级到项目根目录
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_test_db_config():
    """获取测试数据库配置"""
    try:
        from config.database import get_test_db_config as config_get_test_db_config
        return config_get_test_db_config()
    except ImportError:
        logger.warning("无法从 config.database 导入配置，使用默认配置")
        return {
            'host': os.environ.get('TEST_DB_HOST', 'localhost'),
            'port': os.environ.get('TEST_DB_PORT', '5433'),
            'user': os.environ.get('TEST_DB_USER', 'postgres'),
            'password': os.environ.get('TEST_DB_PASSWORD', 'postgresql'),
            'database': os.environ.get('TEST_DB_NAME', 'pharmacopoeia_test'),
        }

def create_test_database():
    """创建测试数据库"""
    config = get_test_db_config()
    test_db_name = config['database']
    
    # 获取项目根目录路径（从tests目录向上两级）
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    logger.info("=" * 60)
    logger.info("测试数据库设置")
    logger.info("=" * 60)
    logger.info(f"目标数据库: {test_db_name}")
    logger.info(f"主机: {config['host']}")
    logger.info(f"端口: {config['port']}")
    logger.info(f"用户: {config['user']}")
    logger.info("=" * 60)
    
    # 步骤1: 连接到postgres默认数据库
    logger.info("\n步骤1: 连接到默认数据库 'postgres'...")
    try:
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database='postgres',
            user=config['user'],
            password=config['password']
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        logger.info("✓ 成功连接到 'postgres' 数据库")
    except psycopg2.OperationalError as e:
        logger.error(f"✗ 连接失败: {e}")
        logger.error("\n请检查:")
        logger.error("1. PostgreSQL服务是否正在运行？")
        logger.error("2. 主机、端口、用户名和密码是否正确？")
        return False
    
    # 步骤2: 检查测试数据库是否存在
    logger.info(f"\n步骤2: 检查数据库 '{test_db_name}' 是否存在...")
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT datname FROM pg_database 
                WHERE datname = %s
            """, (test_db_name,))
            result = cur.fetchone()
            
            if result:
                logger.info(f"✓ 数据库 '{test_db_name}' 已存在")
                # 询问是否要删除并重建
                logger.info(f"将删除并重新创建数据库 '{test_db_name}'...")
                
                # 断开所有连接
                cur.execute(f"""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = '{test_db_name}'
                    AND pid <> pg_backend_pid();
                """)
                
                # 删除数据库
                cur.execute(f'DROP DATABASE {test_db_name}')
                logger.info(f"✓ 已删除数据库 '{test_db_name}'")
    except Exception as e:
        logger.error(f"✗ 检查数据库时出错: {e}")
        conn.close()
        return False
    
    # 步骤3: 创建测试数据库
    logger.info(f"\n步骤3: 创建数据库 '{test_db_name}'...")
    try:
        with conn.cursor() as cur:
            cur.execute(f'CREATE DATABASE {test_db_name}')
        logger.info(f"✓ 成功创建数据库 '{test_db_name}'")
    except Exception as e:
        logger.error(f"✗ 创建数据库失败: {e}")
        conn.close()
        return False
    
    conn.close()
    
    # 步骤4: 连接到新创建的测试数据库
    logger.info(f"\n步骤4: 连接到测试数据库 '{test_db_name}'...")
    try:
        test_conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=test_db_name,
            user=config['user'],
            password=config['password']
        )
        logger.info(f"✓ 成功连接到 '{test_db_name}' 数据库")
    except Exception as e:
        logger.error(f"✗ 连接失败: {e}")
        return False
    
    # 步骤5: 执行schema.sql创建表结构
    logger.info("\n步骤5: 创建表结构...")
    schema_path = os.path.join(project_root, 'database', 'schema.sql')
    if not os.path.exists(schema_path):
        logger.error(f"✗ schema.sql 文件不存在: {schema_path}")
        test_conn.close()
        return False
    
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        with test_conn.cursor() as cur:
            cur.execute(schema_sql)
            test_conn.commit()
        logger.info("✓ 表结构创建成功")
    except Exception as e:
        logger.error(f"✗ 创建表结构失败: {e}")
        test_conn.close()
        return False
    
    # 步骤6: 执行indexes.sql创建索引
    logger.info("\n步骤6: 创建索引...")
    indexes_path = os.path.join(project_root, 'database', 'indexes.sql')
    if not os.path.exists(indexes_path):
        logger.warning(f"⚠ indexes.sql 文件不存在: {indexes_path}")
        logger.warning("跳过索引创建步骤")
    else:
        try:
            with open(indexes_path, 'r', encoding='utf-8') as f:
                indexes_sql = f.read()
            
            with test_conn.cursor() as cur:
                cur.execute(indexes_sql)
                test_conn.commit()
            logger.info("✓ 索引创建成功")
        except Exception as e:
            logger.error(f"✗ 创建索引失败: {e}")
            test_conn.close()
            return False
    
    # 步骤7: 验证表是否创建成功
    logger.info("\n步骤7: 验证表是否创建成功...")
    try:
        with test_conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = cur.fetchall()
            
            if tables:
                logger.info(f"✓ 成功创建 {len(tables)} 个表:")
                for table in tables:
                    logger.info(f"  - {table[0]}")
            else:
                logger.warning("⚠ 数据库中没有表")
    except Exception as e:
        logger.error(f"✗ 验证表时出错: {e}")
        test_conn.close()
        return False
    
    test_conn.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ 测试数据库设置完成!")
    logger.info("=" * 60)
    logger.info("\n现在可以运行测试了:")
    logger.info("  python main.py --run-tests")
    logger.info("  或")
    logger.info("  python -m unittest discover -s tests")
    
    return True

def main():
    """主函数"""
    try:
        success = create_test_database()
        if success:
            sys.exit(0)
        else:
            logger.error("\n测试数据库设置失败!")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n操作已取消")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

