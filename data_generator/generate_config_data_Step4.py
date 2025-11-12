"""
系统配置数据生成脚本(Generate System Config Data - Step 4)

本脚本用于自动创建system_config表并生成初始配置数据，
展示1-1关系设计（config_key作为主键，每个配置项唯一）。

主要功能:
    - 自动检查并创建system_config表（如果不存在）
    - 生成系统基础配置数据（5项）
    - 生成显示相关配置数据（5项）
    - 生成安全相关配置数据（5项）
    - 生成业务相关配置数据（5项）
    - 生成数据库相关配置数据（4项）
    - 生成性能相关配置数据（4项）
    - 共计28条配置数据

1-1关系说明:
    使用config_key作为主键（PRIMARY KEY），确保每个配置键在表中唯一存在，
    实现了标准的1对1关系：一个配置键 ⟺ 唯一一条配置记录

使用方法:
    python data_generator/generate_config_data_Step4.py
    
    或者在其他模块中导入:
    from data_generator.generate_config_data_Step4 import generate_config_data
    generate_config_data()
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_connection_pool
from utils.logger import get_logger
from datetime import datetime

# 获取日志记录器
logger = get_logger(__name__)


def create_table_if_not_exists():
    """创建system_config表（如果不存在）
    
    Returns:
        bool: 创建/验证是否成功
    """
    # system_config表的创建SQL
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS system_config (
        config_key VARCHAR(100) PRIMARY KEY,
        config_value TEXT,
        config_type VARCHAR(50) DEFAULT 'string',
        description TEXT,
        category VARCHAR(50),
        is_editable BOOLEAN DEFAULT TRUE,
        updated_by VARCHAR(100),
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    pool = get_connection_pool()
    conn = pool.getconn()
    cur = conn.cursor()
    
    try:
        # 检查表是否存在
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'system_config'
            )
        """)
        exists = cur.fetchone()[0]
        
        if exists:
            logger.info("✓ system_config表已存在")
        else:
            logger.info("system_config表不存在，开始创建...")
            cur.execute(create_table_sql)
            conn.commit()
            logger.info("✓ system_config表创建成功！")
            logger.info("  说明：使用config_key作为主键，实现1-1关系设计")
        
        return True
    
    except Exception as e:
        logger.error(f"✗ 创建/检查表失败: {str(e)}")
        conn.rollback()
        return False
    
    finally:
        cur.close()
        pool.putconn(conn)


def generate_config_data():
    """生成系统配置数据
    
    Returns:
        tuple: (成功数量, 总数量)
    """
    logger.info("="*60)
    logger.info("开始生成系统配置数据 (Step 4)")
    logger.info("="*60)
    
    # 首先确保表存在
    if not create_table_if_not_exists():
        logger.error("无法创建system_config表，终止数据生成")
        return 0, 0
    
    # 系统配置数据列表
    config_data = [
        # 系统基础配置
        {
            'config_key': 'system.name',
            'config_value': '智药AI',
            'config_type': 'string',
            'description': '系统名称',
            'category': 'system',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'system.version',
            'config_value': 'v1.0.0',
            'config_type': 'string',
            'description': '系统版本号',
            'category': 'system',
            'is_editable': False,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'system.environment',
            'config_value': 'production',
            'config_type': 'string',
            'description': '运行环境（development/production）',
            'category': 'system',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'system.maintenance_mode',
            'config_value': 'false',
            'config_type': 'boolean',
            'description': '维护模式开关',
            'category': 'system',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'system.max_concurrent_users',
            'config_value': '100',
            'config_type': 'number',
            'description': '最大并发用户数',
            'category': 'system',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        
        # 显示相关配置
        {
            'config_key': 'display.page_size',
            'config_value': '20',
            'config_type': 'number',
            'description': '每页显示记录数',
            'category': 'display',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'display.date_format',
            'config_value': 'YYYY-MM-DD',
            'config_type': 'string',
            'description': '日期显示格式',
            'category': 'display',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'display.time_format',
            'config_value': 'HH:mm:ss',
            'config_type': 'string',
            'description': '时间显示格式',
            'category': 'display',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'display.language',
            'config_value': 'zh-CN',
            'config_type': 'string',
            'description': '系统默认语言',
            'category': 'display',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'display.theme',
            'config_value': 'default',
            'config_type': 'string',
            'description': '系统主题',
            'category': 'display',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        
        # 安全相关配置
        {
            'config_key': 'security.session_timeout',
            'config_value': '1800',
            'config_type': 'number',
            'description': '会话超时时间（秒）',
            'category': 'security',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'security.password_min_length',
            'config_value': '8',
            'config_type': 'number',
            'description': '密码最小长度',
            'category': 'security',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'security.max_login_attempts',
            'config_value': '5',
            'config_type': 'number',
            'description': '最大登录尝试次数',
            'category': 'security',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'security.enable_2fa',
            'config_value': 'false',
            'config_type': 'boolean',
            'description': '启用双因素认证',
            'category': 'security',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'security.ip_whitelist',
            'config_value': '[]',
            'config_type': 'json',
            'description': 'IP白名单（JSON数组）',
            'category': 'security',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        
        # 业务相关配置
        {
            'config_key': 'business.experiment_auto_approve',
            'config_value': 'false',
            'config_type': 'boolean',
            'description': '实验记录自动审批',
            'category': 'business',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'business.conversation_max_messages',
            'config_value': '100',
            'config_type': 'number',
            'description': '单个对话最大消息数',
            'category': 'business',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'business.data_retention_days',
            'config_value': '365',
            'config_type': 'number',
            'description': '数据保留天数',
            'category': 'business',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'business.enable_notifications',
            'config_value': 'true',
            'config_type': 'boolean',
            'description': '启用系统通知',
            'category': 'business',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'business.default_lab_code',
            'config_value': 'LAB001',
            'config_type': 'string',
            'description': '默认实验室代码',
            'category': 'business',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        
        # 数据库相关配置
        {
            'config_key': 'database.connection_pool_size',
            'config_value': '20',
            'config_type': 'number',
            'description': '数据库连接池大小',
            'category': 'database',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'database.query_timeout',
            'config_value': '30',
            'config_type': 'number',
            'description': '查询超时时间（秒）',
            'category': 'database',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'database.enable_query_log',
            'config_value': 'true',
            'config_type': 'boolean',
            'description': '启用查询日志',
            'category': 'database',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'database.backup_schedule',
            'config_value': '0 2 * * *',
            'config_type': 'string',
            'description': '数据库备份计划（Cron表达式）',
            'category': 'database',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        
        # 性能相关配置
        {
            'config_key': 'performance.enable_cache',
            'config_value': 'true',
            'config_type': 'boolean',
            'description': '启用缓存',
            'category': 'performance',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'performance.cache_ttl',
            'config_value': '300',
            'config_type': 'number',
            'description': '缓存过期时间（秒）',
            'category': 'performance',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'performance.enable_gzip',
            'config_value': 'true',
            'config_type': 'boolean',
            'description': '启用Gzip压缩',
            'category': 'performance',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
        {
            'config_key': 'performance.max_request_size',
            'config_value': '16777216',
            'config_type': 'number',
            'description': '最大请求大小（字节）',
            'category': 'performance',
            'is_editable': True,
            'updated_by': '系统初始化'
        },
    ]
    
    # 获取数据库连接
    pool = get_connection_pool()
    conn = pool.getconn()
    cur = conn.cursor()
    
    success_count = 0
    total_count = len(config_data)
    
    try:
        logger.info(f"准备插入 {total_count} 条系统配置数据...")
        
        for idx, config in enumerate(config_data, 1):
            try:
                # 插入配置数据
                cur.execute("""
                    INSERT INTO system_config 
                    (config_key, config_value, config_type, description, 
                     category, is_editable, updated_by, updated_at, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (config_key) DO UPDATE SET
                        config_value = EXCLUDED.config_value,
                        config_type = EXCLUDED.config_type,
                        description = EXCLUDED.description,
                        category = EXCLUDED.category,
                        is_editable = EXCLUDED.is_editable,
                        updated_by = EXCLUDED.updated_by,
                        updated_at = EXCLUDED.updated_at
                """, (
                    config['config_key'],
                    config['config_value'],
                    config['config_type'],
                    config['description'],
                    config['category'],
                    config['is_editable'],
                    config['updated_by'],
                    datetime.now(),
                    datetime.now()
                ))
                
                success_count += 1
                
                # 每10条显示一次进度
                if idx % 10 == 0 or idx == total_count:
                    logger.info(f"进度: {idx}/{total_count} ({success_count} 成功)")
            
            except Exception as e:
                logger.error(f"插入配置失败 [{config['config_key']}]: {str(e)}")
                continue
        
        # 提交事务
        conn.commit()
        
        logger.info("="*60)
        logger.info(f"系统配置数据生成完成!")
        logger.info(f"总数: {total_count}, 成功: {success_count}, 失败: {total_count - success_count}")
        logger.info("="*60)
        
        # 显示配置统计
        cur.execute("SELECT category, COUNT(*) FROM system_config GROUP BY category ORDER BY category")
        logger.info("\n配置分类统计:")
        for row in cur.fetchall():
            logger.info(f"  - {row[0]}: {row[1]} 项")
        
        # 显示1-1关系说明
        logger.info("\n" + "="*60)
        logger.info("1-1关系设计说明:")
        logger.info("  本表使用 config_key 作为主键（PRIMARY KEY），")
        logger.info("  确保每个配置键在表中唯一存在，实现了1对1关系。")
        logger.info("  即：一个配置键 <=> 唯一一条配置记录")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"生成配置数据失败: {str(e)}")
        conn.rollback()
        success_count = 0
    
    finally:
        cur.close()
        pool.putconn(conn)
    
    return success_count, total_count


def verify_config_data():
    """验证配置数据
    
    Returns:
        bool: 验证是否成功
    """
    logger.info("\n" + "="*60)
    logger.info("开始验证系统配置数据...")
    logger.info("="*60)
    
    pool = get_connection_pool()
    conn = pool.getconn()
    cur = conn.cursor()
    
    try:
        # 验证总数
        cur.execute("SELECT COUNT(*) FROM system_config")
        total_count = cur.fetchone()[0]
        logger.info(f"✓ 配置总数: {total_count}")
        
        # 验证主键唯一性（1-1关系）
        cur.execute("""
            SELECT config_key, COUNT(*) as cnt 
            FROM system_config 
            GROUP BY config_key 
            HAVING COUNT(*) > 1
        """)
        duplicates = cur.fetchall()
        if duplicates:
            logger.error(f"✗ 发现重复的配置键: {duplicates}")
            return False
        else:
            logger.info("✓ 所有配置键唯一（1-1关系验证通过）")
        
        # 验证各分类数据
        cur.execute("SELECT category, COUNT(*) FROM system_config GROUP BY category")
        categories = cur.fetchall()
        logger.info("\n各分类配置数量:")
        for cat, count in categories:
            logger.info(f"  - {cat}: {count} 项")
        
        # 验证可编辑配置
        cur.execute("SELECT COUNT(*) FROM system_config WHERE is_editable = TRUE")
        editable_count = cur.fetchone()[0]
        logger.info(f"\n可编辑配置: {editable_count} 项")
        
        cur.execute("SELECT COUNT(*) FROM system_config WHERE is_editable = FALSE")
        readonly_count = cur.fetchone()[0]
        logger.info(f"只读配置: {readonly_count} 项")
        
        logger.info("\n" + "="*60)
        logger.info("✓ 系统配置数据验证通过!")
        logger.info("="*60)
        
        return True
    
    except Exception as e:
        logger.error(f"验证配置数据失败: {str(e)}")
        return False
    
    finally:
        cur.close()
        pool.putconn(conn)


def main():
    """主函数"""
    print("\n" + "="*60)
    print("系统配置数据生成脚本 (Step 4)")
    print("  - 自动检查并创建system_config表")
    print("  - 生成28条系统配置数据")
    print("  - 展示1-1关系设计")
    print("="*60 + "\n")
    
    # 生成配置数据（自动创建表）
    success, total = generate_config_data()
    
    if success > 0:
        # 验证配置数据
        verify_config_data()
        
        print("\n✓ 配置数据生成和验证完成!")
        print(f"  成功生成: {success}/{total} 条配置")
    else:
        print("\n✗ 配置数据生成失败，请检查日志")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())

