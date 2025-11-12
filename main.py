"""
智药AI主入口模块(Main Entry Module)

本模块是智药AI系统的主入口点，负责系统初始化、启动Web应用、
创建数据库表，提供系统演示功能。

使用方法:
    # 运行系统演示
    python main.py
    
    # 带命令行参数运行
    python main.py --init-db     # 初始化数据库（创建表和索引）
    python main.py --run-web     # 仅运行Web应用
    python main.py --run-tests   # 运行系统测试
    
    # 示例：初始化并启动
    python main.py --init-db --run-web

主要功能:
    - main(): 
        主函数，根据命令行参数执行相应操作
        
    - initialize_database(): 
        初始化数据库，创建表结构和索引
        
    - run_web_application(): 
        启动Web应用
        
    - run_tests(): 
        运行系统测试
        
    - parse_arguments(): 
        解析命令行参数
        
    - setup_logging(): 
        设置日志系统
        
    - print_system_info(): 
        打印系统信息和统计数据
"""

import argparse
import sys
import os
from datetime import datetime

# 导入自定义模块
from utils.logger import get_logger
from models.base import initialize_database as init_db
from models.base import create_indices
from web.app import create_app
import unittest
from utils.performance_logger import log_execution_time

# 创建日志记录器
logger = get_logger(__name__)

@log_execution_time
def main():
    """主函数，根据命令行参数执行相应操作"""
    # 设置日志系统
    setup_logging()
    
    # 解析命令行参数
    args = parse_arguments()
    
    # 打印启动信息
    print_startup_banner()
    
    try:
        # 根据命令行参数执行操作
        if args.init_db:
            initialize_database()
        
        if args.run_tests:
            success = run_tests()
            if not success and not args.run_web:
                logger.error("测试失败，终止运行")
                sys.exit(1)
        
        if args.run_web or (not any([args.init_db, args.run_tests])):
            # 如果没有指定任何参数，默认运行Web应用
            run_web_application(host=args.host, port=args.port, debug=args.debug)
        
        # 如果只执行了数据库初始化，打印系统信息
        if args.init_db:
            if not args.run_web and not args.run_tests:
                print_system_info()
    
    except Exception as e:
        logger.error(f"系统运行出错: {str(e)}")
        raise

@log_execution_time
def initialize_database():
    """初始化数据库，创建表结构和索引"""
    logger.info("开始初始化数据库...")
    
    try:
        # 调用模型基础模块的初始化函数
        init_db()
        
        # 创建索引
        create_indices()
        
        logger.info("数据库初始化完成")
        return True
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        raise

@log_execution_time
def run_web_application(host='0.0.0.0', port=5000, debug=False):
    """启动Web应用
    
    Args:
        host (str): 主机地址，默认为0.0.0.0
        port (int): 端口号，默认为5000
        debug (bool): 是否启用调试模式，默认为False
    """
    logger.info(f"启动Web应用 (host={host}, port={port}, debug={debug})...")
    
    try:
        # 创建Flask应用
        app = create_app()
        
        # 启动应用
        app.run(host=host, port=port, debug=debug)
    except Exception as e:
        logger.error(f"Web应用启动失败: {str(e)}")
        raise

@log_execution_time
def run_tests():
    """运行系统测试
    
    Returns:
        bool: 测试是否全部通过
    """
    logger.info("开始运行系统测试...")
    try:
        suite = unittest.defaultTestLoader.discover('tests')
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        if result.wasSuccessful():
            logger.info("所有测试通过")
        else:
            logger.warning("部分测试未通过")
        return result.wasSuccessful()
    except Exception as e:
        logger.error(f"系统测试运行失败: {str(e)}")
        return False

def parse_arguments():
    """解析命令行参数
    
    Returns:
        argparse.Namespace: 包含命令行参数的命名空间对象
    """
    parser = argparse.ArgumentParser(description="智药AI (PharmaAI)")
    
    parser.add_argument("--init-db", action="store_true", help="初始化数据库（创建表和索引）")
    parser.add_argument("--run-web", action="store_true", help="运行Web应用")
    parser.add_argument("--run-tests", action="store_true", help="运行系统测试")
    
    # Web应用参数
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Web应用主机地址（默认0.0.0.0）")
    parser.add_argument("--port", type=int, default=5000, help="Web应用端口号（默认5000）")
    parser.add_argument("--debug", action="store_true", help="启用Web应用调试模式")
    
    return parser.parse_args()

def setup_logging():
    """设置日志系统"""
    # 日志已经在导入时设置，此处可以进行额外配置
    pass

def print_system_info():
    """打印系统信息和统计数据"""
    from models.base import get_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM inspectors")
        inspector_count = cursor.fetchone()[0]
    except Exception:
        inspector_count = 0
    
    try:
        cursor.execute("SELECT COUNT(*) FROM pharmacopoeia_items")
        item_count = cursor.fetchone()[0]
    except Exception:
        item_count = 0
    
    try:
        cursor.execute("SELECT COUNT(*) FROM conversations")
        conversation_count = cursor.fetchone()[0]
    except Exception:
        conversation_count = 0
    
    try:
        cursor.execute("SELECT COUNT(*) FROM experiments")
        experiment_count = cursor.fetchone()[0]
    except Exception:
        experiment_count = 0
    
    print("\n" + "=" * 50)
    print(" 智药AI (PharmaAI) - 系统信息")
    print("=" * 50)
    print(f" 药检员数量: {inspector_count}")
    print(f" 药典条目数量: {item_count}")
    print(f" 对话记录数量: {conversation_count}")
    print(f" 实验记录数量: {experiment_count}")
    print("=" * 50)
    print(" 系统就绪，可以通过Web界面进行访问")
    print(" Web地址: http://localhost:5000")
    print("=" * 50 + "\n")

def print_startup_banner():
    """打印启动标语"""
    banner = """
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║            智 药 AI (PharmaAI)                        ║
    ║                                                       ║
    ║  PharmaAI - AI-Powered Pharmacopoeia System           ║
    ║                                                       ║
    ║  数据库系统原理课程项目                                 ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """
    print(banner)
    print(f"  系统启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  运行环境: {sys.platform} {os.name}\n")

# 当作为脚本直接运行时执行
if __name__ == "__main__":
    main()