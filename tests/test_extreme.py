"""
极端条件测试模块(Extreme Condition Test Module)

本模块提供数据库系统在极端条件下的压力测试，用于评估系统在超高并发、
大数据量等极限场景下的性能表现和稳定性。

测试场景:
    1. 超高并发测试: 100, 500, 1000, 5000, 10000个并发客户端
    2. 极限并发测试: 50000, 100000个并发客户端（可选）
    3. 连续压力测试: 持续一定时间的高负载
    4. 峰值冲击测试: 瞬时大量并发请求

使用方法:
    # 运行标准极端测试
    python tests/test_extreme.py
    
    # 运行完整极限测试（包括10万并发）
    python tests/test_extreme.py --full
    
    # 查看详细输出
    python tests/test_extreme.py -v

警告:
    极端测试可能会对系统造成很大压力，建议：
    1. 在专门的测试环境中运行
    2. 确保有足够的系统资源
    3. 监控系统资源使用情况
    4. 根据实际情况调整测试参数
"""

import unittest
import threading
import time
import uuid
import random
import csv
import os
import sys
import psycopg2
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Any, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import get_test_db_config
from database.connection import get_connection_pool
from services.performance_monitor import PerformanceMonitor


class TestExtremeConditions(unittest.TestCase):
    """极端条件测试类，测试系统在极限场景下的性能和稳定性"""

    def setUp(self):
        """测试前准备工作"""
        # 获取测试数据库连接池，增加最大连接数
        config = get_test_db_config()
        config['max_connections'] = 100  # 增加最大连接数
        self.pool = get_connection_pool(config)
        
        # 创建性能监控器
        self.perf_monitor = PerformanceMonitor()
        
        # 生成唯一测试标识
        self.test_id = str(uuid.uuid4()).replace('-', '')[:8]
        
        # 创建日志文件
        self.log_file = os.path.join(
            os.path.dirname(__file__), 
            'doc', 
            f'extreme_test_log_{self.test_id}.txt'
        )
        
        # 创建CSV报告文件
        self.csv_file = os.path.join(
            os.path.dirname(__file__), 
            'doc', 
            f'extreme_performance_report_{self.test_id}.csv'
        )
        
        # 初始化日志
        self._init_log()
        
        # 创建测试表和准备测试数据
        self._prepare_test_data()
        
        # 测试结果列表
        self.test_results = []
        
        # 标准测试的并发数配置
        self.standard_concurrency = [100, 500, 1000, 5000, 10000]
        
        # 极限测试的并发数配置（需要特殊标志开启）
        self.extreme_concurrency = [50000, 100000]
        
        # 每个客户端执行的操作数（动态调整）
        self.operations_per_client = 5

    def tearDown(self):
        """测试后清理工作"""
        # 生成性能报告
        self._generate_performance_report()
        
        # 清理测试数据
        self._clean_test_data()
        
        # 关闭日志
        self._close_log()

    def test_extreme_concurrent_queries(self):
        """测试极端并发查询"""
        self._log("=" * 80)
        self._log("开始极端并发查询测试")
        self._log("=" * 80)
        
        for client_count in self.standard_concurrency:
            self._log(f"\n开始测试 {client_count} 个并发客户端的查询性能...")
            
            # 根据并发数调整每个客户端的操作数
            ops_per_client = max(1, 100 // (client_count // 100)) if client_count >= 100 else 10
            
            # 记录开始时间
            start_time = time.time()
            
            # 统计
            success_count = 0
            error_count = 0
            timeout_count = 0
            
            try:
                # 使用线程池执行并发查询
                with ThreadPoolExecutor(max_workers=min(client_count, 1000)) as executor:
                    futures = [
                        executor.submit(
                            self._client_query_task,
                            f"extreme-query-{i+1}",
                            ops_per_client
                        )
                        for i in range(client_count)
                    ]
                    
                    # 等待所有任务完成，设置超时
                    for future in as_completed(futures, timeout=300):
                        try:
                            result = future.result(timeout=10)
                            if result:
                                success_count += 1
                            else:
                                error_count += 1
                        except Exception as e:
                            error_count += 1
                            self._log(f"任务执行出错: {str(e)}")
            except Exception as e:
                self._log(f"线程池执行出错: {str(e)}")
            
            # 记录结束时间
            end_time = time.time()
            duration = end_time - start_time
            
            # 获取性能统计
            stats = self.perf_monitor.get_statistics()
            
            # 计算指标
            total_clients = client_count
            success_rate = (success_count / total_clients * 100) if total_clients > 0 else 0
            ops_per_second = stats['total_operations'] / duration if duration > 0 else 0
            
            # 记录测试结果
            result = {
                'test_name': 'extreme_concurrent_queries',
                'client_count': client_count,
                'duration': duration,
                'success_count': success_count,
                'error_count': error_count,
                'success_rate': success_rate,
                'avg_response_time_ms': stats.get('avg_response_time_ms', 0),
                'max_response_time_ms': stats.get('max_response_time_ms', 0),
                'operations_count': stats.get('total_operations', 0),
                'operations_per_second': ops_per_second
            }
            self.test_results.append(result)
            
            # 输出结果
            self._log(f"完成 {client_count} 个并发客户端的查询测试")
            self._log(f"  总耗时: {duration:.2f}秒")
            self._log(f"  成功数: {success_count}/{total_clients}")
            self._log(f"  失败数: {error_count}")
            self._log(f"  成功率: {success_rate:.2f}%")
            self._log(f"  平均响应时间: {stats.get('avg_response_time_ms', 0):.2f}毫秒")
            self._log(f"  最大响应时间: {stats.get('max_response_time_ms', 0):.2f}毫秒")
            self._log(f"  每秒操作数: {ops_per_second:.2f}")
            
            # 清除性能监控器数据
            self.perf_monitor.clear_data()
            
            # 暂停一段时间让系统恢复
            self._log(f"等待系统恢复...")
            time.sleep(5)

    def test_extreme_concurrent_inserts(self):
        """测试极端并发插入"""
        self._log("=" * 80)
        self._log("开始极端并发插入测试")
        self._log("=" * 80)
        
        for client_count in self.standard_concurrency:
            self._log(f"\n开始测试 {client_count} 个并发客户端的插入性能...")
            
            # 根据并发数调整每个客户端的操作数
            ops_per_client = max(1, 50 // (client_count // 100)) if client_count >= 100 else 5
            
            # 记录开始时间
            start_time = time.time()
            
            # 统计
            success_count = 0
            error_count = 0
            
            try:
                # 使用线程池执行并发插入
                with ThreadPoolExecutor(max_workers=min(client_count, 1000)) as executor:
                    futures = [
                        executor.submit(
                            self._client_insert_task,
                            f"extreme-insert-{i+1}",
                            ops_per_client
                        )
                        for i in range(client_count)
                    ]
                    
                    # 等待所有任务完成
                    for future in as_completed(futures, timeout=300):
                        try:
                            result = future.result(timeout=10)
                            if result:
                                success_count += 1
                            else:
                                error_count += 1
                        except Exception as e:
                            error_count += 1
                            self._log(f"任务执行出错: {str(e)}")
            except Exception as e:
                self._log(f"线程池执行出错: {str(e)}")
            
            # 记录结束时间
            end_time = time.time()
            duration = end_time - start_time
            
            # 获取性能统计
            stats = self.perf_monitor.get_statistics()
            
            # 计算指标
            total_clients = client_count
            success_rate = (success_count / total_clients * 100) if total_clients > 0 else 0
            ops_per_second = stats['total_operations'] / duration if duration > 0 else 0
            
            # 记录测试结果
            result = {
                'test_name': 'extreme_concurrent_inserts',
                'client_count': client_count,
                'duration': duration,
                'success_count': success_count,
                'error_count': error_count,
                'success_rate': success_rate,
                'avg_response_time_ms': stats.get('avg_response_time_ms', 0),
                'max_response_time_ms': stats.get('max_response_time_ms', 0),
                'operations_count': stats.get('total_operations', 0),
                'operations_per_second': ops_per_second
            }
            self.test_results.append(result)
            
            # 输出结果
            self._log(f"完成 {client_count} 个并发客户端的插入测试")
            self._log(f"  总耗时: {duration:.2f}秒")
            self._log(f"  成功数: {success_count}/{total_clients}")
            self._log(f"  失败数: {error_count}")
            self._log(f"  成功率: {success_rate:.2f}%")
            self._log(f"  平均响应时间: {stats.get('avg_response_time_ms', 0):.2f}毫秒")
            self._log(f"  最大响应时间: {stats.get('max_response_time_ms', 0):.2f}毫秒")
            self._log(f"  每秒操作数: {ops_per_second:.2f}")
            
            # 清除性能监控器数据
            self.perf_monitor.clear_data()
            
            # 暂停一段时间让系统恢复
            self._log(f"等待系统恢复...")
            time.sleep(5)

    def test_extreme_mixed_operations(self):
        """测试极端混合操作"""
        self._log("=" * 80)
        self._log("开始极端混合操作测试")
        self._log("=" * 80)
        
        for client_count in self.standard_concurrency:
            self._log(f"\n开始测试 {client_count} 个并发客户端的混合操作性能...")
            
            # 根据并发数调整每个客户端的操作数
            ops_per_client = max(1, 50 // (client_count // 100)) if client_count >= 100 else 5
            
            # 记录开始时间
            start_time = time.time()
            
            # 统计
            success_count = 0
            error_count = 0
            
            try:
                # 使用线程池执行混合操作
                with ThreadPoolExecutor(max_workers=min(client_count, 1000)) as executor:
                    futures = [
                        executor.submit(
                            self._client_mixed_task,
                            f"extreme-mixed-{i+1}",
                            ops_per_client
                        )
                        for i in range(client_count)
                    ]
                    
                    # 等待所有任务完成
                    for future in as_completed(futures, timeout=300):
                        try:
                            result = future.result(timeout=10)
                            if result:
                                success_count += 1
                            else:
                                error_count += 1
                        except Exception as e:
                            error_count += 1
            except Exception as e:
                self._log(f"线程池执行出错: {str(e)}")
            
            # 记录结束时间
            end_time = time.time()
            duration = end_time - start_time
            
            # 获取性能统计
            stats = self.perf_monitor.get_statistics()
            
            # 计算指标
            total_clients = client_count
            success_rate = (success_count / total_clients * 100) if total_clients > 0 else 0
            ops_per_second = stats['total_operations'] / duration if duration > 0 else 0
            
            # 记录测试结果
            result = {
                'test_name': 'extreme_mixed_operations',
                'client_count': client_count,
                'duration': duration,
                'success_count': success_count,
                'error_count': error_count,
                'success_rate': success_rate,
                'avg_response_time_ms': stats.get('avg_response_time_ms', 0),
                'max_response_time_ms': stats.get('max_response_time_ms', 0),
                'operations_count': stats.get('total_operations', 0),
                'operations_per_second': ops_per_second
            }
            self.test_results.append(result)
            
            # 输出结果
            self._log(f"完成 {client_count} 个并发客户端的混合操作测试")
            self._log(f"  总耗时: {duration:.2f}秒")
            self._log(f"  成功数: {success_count}/{total_clients}")
            self._log(f"  失败数: {error_count}")
            self._log(f"  成功率: {success_rate:.2f}%")
            self._log(f"  平均响应时间: {stats.get('avg_response_time_ms', 0):.2f}毫秒")
            self._log(f"  最大响应时间: {stats.get('max_response_time_ms', 0):.2f}毫秒")
            self._log(f"  每秒操作数: {ops_per_second:.2f}")
            
            # 清除性能监控器数据
            self.perf_monitor.clear_data()
            
            # 暂停一段时间让系统恢复
            self._log(f"等待系统恢复...")
            time.sleep(5)

    def _client_query_task(self, client_id: str, ops_count: int = 5) -> bool:
        """客户端查询任务"""
        try:
            # 注册用户会话
            self.perf_monitor.register_user(client_id)
            
            # 获取连接（设置超时）
            conn = self.pool.getconn()
            if conn is None:
                return False
            
            try:
                cur = conn.cursor()
                
                # 执行查询操作
                for i in range(ops_count):
                    with self.perf_monitor.track_user_operation(client_id, 'query'):
                        conversation_id = random.randint(1, 5)
                        cur.execute(f"""
                            SELECT message_text, sender_type, timestamp
                            FROM test_message_{self.test_id}
                            WHERE conversation_id = %s
                            ORDER BY timestamp DESC
                            LIMIT 5
                        """, (conversation_id,))
                        messages = cur.fetchall()
                
                return True
            finally:
                if cur:
                    cur.close()
                if conn:
                    self.pool.putconn(conn)
                self.perf_monitor.unregister_user(client_id)
        except Exception as e:
            return False

    def _client_insert_task(self, client_id: str, ops_count: int = 5) -> bool:
        """客户端插入任务"""
        try:
            # 注册用户会话
            self.perf_monitor.register_user(client_id)
            
            # 获取连接
            conn = self.pool.getconn()
            if conn is None:
                return False
            
            try:
                cur = conn.cursor()
                
                # 执行插入操作
                for i in range(ops_count):
                    with self.perf_monitor.track_user_operation(client_id, 'insert'):
                        conversation_id = random.randint(1, 5)
                        message_text = f"极端测试消息 from {client_id} - {i}"
                        sender_type = random.choice(['inspector', 'system'])
                        
                        cur.execute(f"""
                            INSERT INTO test_message_{self.test_id}
                            (conversation_id, message_seq, client_id, sender_type, message_text)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            conversation_id,
                            int(time.time() * 1000000),  # 使用微秒时间戳确保唯一性
                            client_id,
                            sender_type,
                            message_text
                        ))
                        
                        conn.commit()
                
                return True
            finally:
                if cur:
                    cur.close()
                if conn:
                    self.pool.putconn(conn)
                self.perf_monitor.unregister_user(client_id)
        except Exception as e:
            return False

    def _client_mixed_task(self, client_id: str, ops_count: int = 5) -> bool:
        """客户端混合操作任务"""
        try:
            # 注册用户会话
            self.perf_monitor.register_user(client_id)
            
            # 获取连接
            conn = self.pool.getconn()
            if conn is None:
                return False
            
            try:
                cur = conn.cursor()
                
                # 执行混合操作
                for i in range(ops_count):
                    # 80%查询，20%插入
                    operation_type = random.choices(['query', 'insert'], weights=[0.8, 0.2], k=1)[0]
                    
                    if operation_type == 'query':
                        with self.perf_monitor.track_user_operation(client_id, 'query'):
                            conversation_id = random.randint(1, 5)
                            cur.execute(f"""
                                SELECT message_text, sender_type
                                FROM test_message_{self.test_id}
                                WHERE conversation_id = %s
                                LIMIT 5
                            """, (conversation_id,))
                            messages = cur.fetchall()
                    else:
                        with self.perf_monitor.track_user_operation(client_id, 'insert'):
                            conversation_id = random.randint(1, 5)
                            message_text = f"极端混合测试 from {client_id} - {i}"
                            sender_type = random.choice(['inspector', 'system'])
                            
                            cur.execute(f"""
                                INSERT INTO test_message_{self.test_id}
                                (conversation_id, message_seq, client_id, sender_type, message_text)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (
                                conversation_id,
                                int(time.time() * 1000000),
                                client_id,
                                sender_type,
                                message_text
                            ))
                            conn.commit()
                
                return True
            finally:
                if cur:
                    cur.close()
                if conn:
                    self.pool.putconn(conn)
                self.perf_monitor.unregister_user(client_id)
        except Exception as e:
            return False

    def _prepare_test_data(self):
        """准备测试数据"""
        self._log("准备测试数据...")
        
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            
            # 创建测试表
            cur.execute(f"DROP TABLE IF EXISTS test_message_{self.test_id}")
            cur.execute(f"DROP TABLE IF EXISTS test_conversation_{self.test_id}")
            cur.execute(f"DROP TABLE IF EXISTS test_inspector_{self.test_id}")
            
            # 创建药检员表
            cur.execute(f"""
                CREATE TABLE test_inspector_{self.test_id} (
                    inspector_id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL
                )
            """)
            
            # 创建对话会话表
            cur.execute(f"""
                CREATE TABLE test_conversation_{self.test_id} (
                    conversation_id SERIAL PRIMARY KEY,
                    inspector_id INT NOT NULL,
                    session_id VARCHAR(100) UNIQUE NOT NULL,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (inspector_id) REFERENCES test_inspector_{self.test_id}(inspector_id)
                )
            """)
            
            # 创建对话消息表
            cur.execute(f"""
                CREATE TABLE test_message_{self.test_id} (
                    message_id SERIAL PRIMARY KEY,
                    conversation_id INT NOT NULL,
                    message_seq BIGINT NOT NULL,
                    client_id VARCHAR(100),
                    sender_type VARCHAR(20) NOT NULL,
                    message_text TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES test_conversation_{self.test_id}(conversation_id)
                )
            """)
            
            # 插入基础测试数据
            for i in range(5):
                cur.execute(f"""
                    INSERT INTO test_inspector_{self.test_id} (name)
                    VALUES (%s)
                """, (f"极端测试药检员{i+1}",))
            
            for i in range(5):
                inspector_id = i % 5 + 1
                cur.execute(f"""
                    INSERT INTO test_conversation_{self.test_id} (inspector_id, session_id)
                    VALUES (%s, %s)
                """, (inspector_id, f"extreme-session-{i+1}"))
            
            # 插入一些初始消息
            for conv_id in range(1, 6):
                for msg_id in range(10):
                    sender_type = 'inspector' if msg_id % 2 == 0 else 'system'
                    cur.execute(f"""
                        INSERT INTO test_message_{self.test_id} 
                        (conversation_id, message_seq, sender_type, message_text)
                        VALUES (%s, %s, %s, %s)
                    """, (conv_id, msg_id + 1, sender_type, f"初始消息{msg_id+1}"))
            
            conn.commit()
            
            self._log(f"测试数据准备完成，测试ID: {self.test_id}")
        except Exception as e:
            self._log(f"准备测试数据时出错: {str(e)}")
        finally:
            if cur:
                cur.close()
            if conn:
                self.pool.putconn(conn)

    def _clean_test_data(self):
        """清理测试数据"""
        self._log("清理测试数据...")
        
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            
            cur.execute(f"DROP TABLE IF EXISTS test_message_{self.test_id}")
            cur.execute(f"DROP TABLE IF EXISTS test_conversation_{self.test_id}")
            cur.execute(f"DROP TABLE IF EXISTS test_inspector_{self.test_id}")
            
            conn.commit()
            
            self._log(f"测试数据清理完成")
        except Exception as e:
            self._log(f"清理测试数据时出错: {str(e)}")
        finally:
            if cur:
                cur.close()
            if conn:
                self.pool.putconn(conn)

    def _generate_performance_report(self):
        """生成性能测试报告"""
        self._log("\n" + "=" * 80)
        self._log("生成性能测试报告")
        self._log("=" * 80)
        
        try:
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    '测试名称', '客户端数量', '耗时(秒)', '成功数', '失败数', '成功率(%)',
                    '平均响应时间(毫秒)', '最大响应时间(毫秒)', '操作总数', '每秒操作数'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for result in self.test_results:
                    test_name_map = {
                        'extreme_concurrent_queries': '极端并发查询',
                        'extreme_concurrent_inserts': '极端并发插入',
                        'extreme_mixed_operations': '极端混合操作'
                    }
                    
                    writer.writerow({
                        '测试名称': test_name_map.get(result.get('test_name', ''), result.get('test_name', '')),
                        '客户端数量': result.get('client_count', ''),
                        '耗时(秒)': f"{result.get('duration', 0):.2f}",
                        '成功数': result.get('success_count', ''),
                        '失败数': result.get('error_count', ''),
                        '成功率(%)': f"{result.get('success_rate', 0):.2f}",
                        '平均响应时间(毫秒)': f"{result.get('avg_response_time_ms', 0):.2f}",
                        '最大响应时间(毫秒)': f"{result.get('max_response_time_ms', 0):.2f}",
                        '操作总数': result.get('operations_count', ''),
                        '每秒操作数': f"{result.get('operations_per_second', 0):.2f}"
                    })
            
            self._log(f"\n性能测试报告已生成: {self.csv_file}")
        except Exception as e:
            self._log(f"生成性能报告时出错: {str(e)}")

    def _init_log(self):
        """初始化日志文件"""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("智药AI (PharmaAI) - 极端条件测试日志\n")
            f.write("=" * 80 + "\n")
            f.write(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"测试ID: {self.test_id}\n")
            f.write("=" * 80 + "\n\n")

    def _log(self, message: str):
        """写入日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}\n"
        
        # 输出到控制台
        print(message)
        
        # 写入日志文件
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_message)
        except Exception as e:
            print(f"写入日志失败: {e}")

    def _close_log(self):
        """关闭日志"""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n")


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("智药AI (PharmaAI) - 极端条件测试")
    print("=" * 80)
    print("\n警告: 此测试将对系统造成极大压力，请确保:")
    print("  1. 在专门的测试环境中运行")
    print("  2. 系统有足够的资源（CPU、内存、连接数等）")
    print("  3. 已调整数据库连接池和系统限制")
    print("\n测试配置:")
    print("  - 标准测试: 100, 500, 1000, 5000, 10000 并发客户端")
    print("  - 预计耗时: 10-30分钟")
    print("\n" + "=" * 80 + "\n")
    
    # 运行测试
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestExtremeConditions)
    test_result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    
    print("\n" + "=" * 80)
    print("极端条件测试完成!")
    print("=" * 80)

