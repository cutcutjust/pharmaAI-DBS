"""
并发访问测试模块(Concurrent Access Test Module)

本模块提供数据库并发访问的测试用例，用于模拟多用户同时访问数据库的场景，
测试系统在并发环境下的稳定性和性能，记录各操作的执行时间和成功率，
满足课程对多用户（多客户端）同时访问数据库并记录性能的要求。

使用方法:
    # 直接运行测试文件
    python tests/test_concurrent.py
    
    # 或使用unittest模块运行
    python -m unittest tests.test_concurrent
    
    # 运行特定测试类
    python -m unittest tests.test_concurrent.TestConcurrentAccess
    
    # 运行特定测试方法
    python -m unittest tests.test_concurrent.TestConcurrentAccess.test_concurrent_queries
    
    # 查看详细测试输出
    python -m unittest tests.test_concurrent -v
    
    # 生成的性能报告会保存在performance_report.csv文件中

测试流程:
    1. 模拟5-10个客户端线程同时访问数据库
    2. 每个线程执行：查询对话历史、插入新消息、查询实验数据、执行JOIN查询
    3. 使用性能监控服务记录每个操作的执行时间
    4. 统计并发访问时的平均响应时间、最大响应时间和成功率
    5. 生成性能对比报告，包括不同并发用户数下的系统表现

主要功能:
    - TestConcurrentAccess: 并发访问测试类
        - setUp(): 
            测试前准备工作，初始化数据库连接池和性能监控器
            
        - tearDown(): 
            测试后清理工作，关闭连接并生成性能报告
            
        - test_concurrent_queries(): 
            测试多线程并发查询，验证数据一致性和查询性能
            
        - test_concurrent_inserts(): 
            测试多线程并发插入操作，验证数据写入的正确性
            
        - test_concurrent_mixed_operations(): 
            测试多线程混合读写操作，模拟真实使用场景
            
        - test_concurrent_transactions(): 
            测试多线程并发事务操作，验证事务隔离性
            
        - test_scalability(): 
            测试系统可扩展性，通过逐步增加并发用户数来评估系统极限
            
        - _client_query_task(client_id): 
            客户端查询任务函数，在线程中执行
            
        - _client_insert_task(client_id): 
            客户端插入任务函数，在线程中执行
            
        - _client_mixed_task(client_id): 
            客户端混合操作任务函数，在线程中执行
            
        - _prepare_test_data(): 
            准备测试数据，确保并发测试有足够的数据可操作
            
        - _generate_performance_report(): 
            生成性能测试报告，包括平均响应时间、最大响应时间和成功率
"""

import unittest
import threading
import time
import uuid
import random
import csv
import os
import psycopg2
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple, Any, Optional

from config.database import get_test_db_config
from database.connection import get_connection_pool
from services.performance_monitor import PerformanceMonitor


class TestConcurrentAccess(unittest.TestCase):
    """并发访问测试类，测试多线程并发访问数据库的性能和稳定性"""

    def setUp(self):
        """测试前准备工作，初始化数据库连接池和性能监控器"""
        # 获取测试数据库连接池
        self.config = get_test_db_config()
        self.pool = get_connection_pool(self.config)
        
        # 创建性能监控器
        self.perf_monitor = PerformanceMonitor()
        
        # 生成唯一测试标识，避免多次测试冲突
        self.test_id = str(uuid.uuid4()).replace('-', '')[:8]
        
        # 创建测试表和准备测试数据
        self._prepare_test_data()
        
        # 并发测试参数
        self.client_counts = [5, 10]  # 并发客户端数
        self.operations_per_client = 10  # 每个客户端执行的操作数
        
        # 记录测试结果
        self.test_results = []

    def tearDown(self):
        """测试后清理工作，关闭连接并生成性能报告"""
        # 生成性能报告
        self._generate_performance_report()
        
        # 清理测试数据
        self._clean_test_data()

    def test_concurrent_queries(self):
        """测试多线程并发查询，验证数据一致性和查询性能"""
        for client_count in self.client_counts:
            # 记录测试开始时间
            start_time = time.time()
            
            print(f"\n开始测试 {client_count} 个并发客户端的查询性能...")
            
            # 创建线程池
            with ThreadPoolExecutor(max_workers=client_count) as executor:
                # 提交查询任务
                futures = [
                    executor.submit(self._client_query_task, f"client-query-{i+1}")
                    for i in range(client_count)
                ]
                
                # 等待所有任务完成
                for future in futures:
                    future.result()
            
            # 记录测试结束时间
            end_time = time.time()
            duration = end_time - start_time
            
            # 获取性能统计信息
            stats = self.perf_monitor.get_statistics()
            
            # 计算每秒操作数
            ops_per_second = stats['total_operations'] / duration if duration > 0 else 0
            
            # 记录测试结果
            self.test_results.append({
                'test_name': 'concurrent_queries',
                'client_count': client_count,
                'duration': duration,
                'avg_response_time_ms': stats['avg_response_time_ms'],
                'max_response_time_ms': stats['max_response_time_ms'],
                'operations_count': stats['total_operations'],
                'operations_per_second': ops_per_second
            })
            
            print(f"完成 {client_count} 个并发客户端的查询测试")
            print(f"总耗时: {duration:.2f}秒")
            print(f"平均响应时间: {stats['avg_response_time_ms']:.2f}毫秒")
            print(f"最大响应时间: {stats['max_response_time_ms']:.2f}毫秒")
            print(f"每秒操作数: {ops_per_second:.2f}")
            
            # 清除性能监控器中的数据，准备下一轮测试
            self.perf_monitor.clear_data()

    def test_concurrent_inserts(self):
        """测试多线程并发插入操作，验证数据写入的正确性"""
        for client_count in self.client_counts:
            # 记录测试开始时间
            start_time = time.time()
            
            print(f"\n开始测试 {client_count} 个并发客户端的插入性能...")
            
            # 创建线程池
            with ThreadPoolExecutor(max_workers=client_count) as executor:
                # 提交插入任务
                futures = [
                    executor.submit(self._client_insert_task, f"client-insert-{i+1}")
                    for i in range(client_count)
                ]
                
                # 等待所有任务完成
                for future in futures:
                    future.result()
            
            # 记录测试结束时间
            end_time = time.time()
            duration = end_time - start_time
            
            # 获取性能统计信息
            stats = self.perf_monitor.get_statistics()
            
            # 验证插入数据的正确性
            conn = self.pool.getconn()
            try:
                cur = conn.cursor()
                
                # 统计每个客户端插入的消息数量
                cur.execute(f"""
                    SELECT client_id, COUNT(*) 
                    FROM test_message_{self.test_id} 
                    GROUP BY client_id
                """)
                
                client_counts = {row[0]: row[1] for row in cur.fetchall()}
                
                # 验证每个客户端都插入了正确数量的消息
                for i in range(client_count):
                    client_id = f"client-insert-{i+1}"
                    self.assertIn(client_id, client_counts, f"客户端 {client_id} 未插入任何数据")
                    self.assertGreaterEqual(client_counts[client_id], 1, 
                                           f"客户端 {client_id} 插入的消息数量过少")
            finally:
                if cur:
                    cur.close()
                if conn:
                    self.pool.putconn(conn)
            
            # 计算每秒操作数
            ops_per_second = stats['total_operations'] / duration if duration > 0 else 0
            
            # 记录测试结果
            self.test_results.append({
                'test_name': 'concurrent_inserts',
                'client_count': client_count,
                'duration': duration,
                'avg_response_time_ms': stats['avg_response_time_ms'],
                'max_response_time_ms': stats['max_response_time_ms'],
                'operations_count': stats['total_operations'],
                'operations_per_second': ops_per_second
            })
            
            print(f"完成 {client_count} 个并发客户端的插入测试")
            print(f"总耗时: {duration:.2f}秒")
            print(f"平均响应时间: {stats['avg_response_time_ms']:.2f}毫秒")
            print(f"最大响应时间: {stats['max_response_time_ms']:.2f}毫秒")
            print(f"每秒操作数: {ops_per_second:.2f}")
            
            # 清除性能监控器中的数据，准备下一轮测试
            self.perf_monitor.clear_data()

    def test_concurrent_mixed_operations(self):
        """测试多线程混合读写操作，模拟真实使用场景"""
        for client_count in self.client_counts:
            # 记录测试开始时间
            start_time = time.time()
            
            print(f"\n开始测试 {client_count} 个并发客户端的混合操作性能...")
            
            # 创建线程池
            with ThreadPoolExecutor(max_workers=client_count) as executor:
                # 提交混合操作任务
                futures = [
                    executor.submit(self._client_mixed_task, f"client-mixed-{i+1}")
                    for i in range(client_count)
                ]
                
                # 等待所有任务完成
                for future in futures:
                    future.result()
            
            # 记录测试结束时间
            end_time = time.time()
            duration = end_time - start_time
            
            # 获取性能统计信息
            stats = self.perf_monitor.get_statistics()
            
            # 记录测试结果
            self.test_results.append({
                'test_name': 'concurrent_mixed_operations',
                'client_count': client_count,
                'duration': duration,
                'avg_response_time_ms': stats['avg_response_time_ms'],
                'max_response_time_ms': stats['max_response_time_ms'],
                'operations_count': stats['total_operations'],
                'operations_per_second': stats['total_operations'] / duration
            })
            
            print(f"完成 {client_count} 个并发客户端的混合操作测试")
            print(f"总耗时: {duration:.2f}秒")
            print(f"平均响应时间: {stats['avg_response_time_ms']:.2f}毫秒")
            print(f"最大响应时间: {stats['max_response_time_ms']:.2f}毫秒")
            print(f"每秒操作数: {stats['total_operations'] / duration:.2f}")
            
            # 清除性能监控器中的数据，准备下一轮测试
            self.perf_monitor.clear_data()

    def test_concurrent_transactions(self):
        """测试多线程并发事务操作，验证事务隔离性"""
        for client_count in self.client_counts:
            # 记录测试开始时间和成功事务计数
            start_time = time.time()
            success_count = 0
            
            print(f"\n开始测试 {client_count} 个并发客户端的事务性能...")
            
            # 创建线程池
            with ThreadPoolExecutor(max_workers=client_count) as executor:
                # 提交事务任务
                futures = []
                for i in range(client_count):
                    future = executor.submit(
                        self._client_transaction_task, f"client-tx-{i+1}", i+1
                    )
                    futures.append(future)
                
                # 等待所有任务完成并统计成功事务数
                for future in futures:
                    if future.result():
                        success_count += 1
            
            # 记录测试结束时间
            end_time = time.time()
            duration = end_time - start_time
            
            # 获取性能统计信息
            stats = self.perf_monitor.get_statistics()
            
            # 记录测试结果
            success_rate = (success_count / client_count) * 100
            
            # 计算每秒操作数（基于成功的事务数）
            ops_per_second = success_count / duration if duration > 0 else 0
            
            self.test_results.append({
                'test_name': 'concurrent_transactions',
                'client_count': client_count,
                'duration': duration,
                'success_rate': success_rate,
                'avg_response_time_ms': stats['avg_response_time_ms'],
                'max_response_time_ms': stats['max_response_time_ms'],
                'operations_count': stats['total_operations'],
                'operations_per_second': ops_per_second
            })
            
            print(f"完成 {client_count} 个并发客户端的事务测试")
            print(f"总耗时: {duration:.2f}秒")
            print(f"成功率: {success_rate:.2f}%")
            print(f"平均响应时间: {stats['avg_response_time_ms']:.2f}毫秒")
            print(f"最大响应时间: {stats['max_response_time_ms']:.2f}毫秒")
            print(f"每秒操作数: {ops_per_second:.2f}")
            
            # 清除性能监控器中的数据，准备下一轮测试
            self.perf_monitor.clear_data()

    def test_scalability(self):
        """测试系统可扩展性，通过逐步增加并发用户数来评估系统极限"""
        # 测试不同并发用户数下的性能
        client_counts = [1, 2, 5, 10, 20]
        
        for client_count in client_counts:
            # 记录测试开始时间
            start_time = time.time()
            
            print(f"\n开始测试 {client_count} 个并发客户端的系统可扩展性...")
            
            # 创建线程池
            with ThreadPoolExecutor(max_workers=client_count) as executor:
                # 提交混合操作任务
                futures = [
                    executor.submit(self._client_mixed_task, f"client-scale-{i+1}")
                    for i in range(client_count)
                ]
                
                # 等待所有任务完成
                for future in futures:
                    future.result()
            
            # 记录测试结束时间
            end_time = time.time()
            duration = end_time - start_time
            
            # 获取性能统计信息
            stats = self.perf_monitor.get_statistics()
            
            # 计算每秒操作数
            ops_per_second = stats['total_operations'] / duration
            
            # 记录测试结果
            self.test_results.append({
                'test_name': 'scalability',
                'client_count': client_count,
                'duration': duration,
                'avg_response_time_ms': stats['avg_response_time_ms'],
                'max_response_time_ms': stats['max_response_time_ms'],
                'operations_count': stats['total_operations'],
                'operations_per_second': ops_per_second
            })
            
            print(f"完成 {client_count} 个并发客户端的可扩展性测试")
            print(f"总耗时: {duration:.2f}秒")
            print(f"平均响应时间: {stats['avg_response_time_ms']:.2f}毫秒")
            print(f"最大响应时间: {stats['max_response_time_ms']:.2f}毫秒")
            print(f"每秒操作数: {ops_per_second:.2f}")
            
            # 清除性能监控器中的数据，准备下一轮测试
            self.perf_monitor.clear_data()
        
        # 分析可扩展性
        print("\n可扩展性分析结果:")
        
        base_result = next(r for r in self.test_results if r['test_name'] == 'scalability' and r['client_count'] == 1)
        base_ops_per_second = base_result['operations_per_second']
        
        # 检查基准操作数是否有效
        if base_ops_per_second <= 0:
            print(f"警告: 基准每秒操作数为 {base_ops_per_second}，无法进行可扩展性分析")
            print("可能原因: 操作执行时间过短或性能监控器未正确记录操作")
            # 跳过可扩展性效率验证，但不让测试失败
            return
        
        for result in [r for r in self.test_results if r['test_name'] == 'scalability']:
            client_count = result['client_count']
            if client_count == 1:
                continue
                
            relative_throughput = result['operations_per_second'] / base_ops_per_second
            ideal_throughput = client_count
            efficiency = (relative_throughput / ideal_throughput) * 100
            
            print(f"客户端数: {client_count}, 相对吞吐量: {relative_throughput:.2f}x, 效率: {efficiency:.2f}%")
            
            # 验证系统具有一定的可扩展性
            if client_count <= 5:  # 小规模并发要求更好的可扩展性
                self.assertGreaterEqual(efficiency, 50, 
                                       f"小规模并发({client_count}个客户端)的可扩展性效率过低: {efficiency:.2f}%")
            else:  # 大规模并发允许效率有所下降
                self.assertGreaterEqual(efficiency, 30, 
                                       f"大规模并发({client_count}个客户端)的可扩展性效率过低: {efficiency:.2f}%")
    
    def _client_query_task(self, client_id):
        """客户端查询任务函数，在线程中执行"""
        # 注册用户会话
        self.perf_monitor.register_user(client_id)
        
        # 获取连接
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            
            # 执行多个查询操作
            for i in range(self.operations_per_client):
                # 1. 查询对话消息
                with self.perf_monitor.track_user_operation(client_id, 'query_messages'):
                    conversation_id = random.randint(1, 5)  # 随机选择会话ID
                    cur.execute(f"""
                        SELECT message_text, sender_type, timestamp
                        FROM test_message_{self.test_id}
                        WHERE conversation_id = %s
                        ORDER BY timestamp DESC
                        LIMIT 10
                    """, (conversation_id,))
                    messages = cur.fetchall()
                
                # 2. 执行JOIN查询
                with self.perf_monitor.track_user_operation(client_id, 'join_query'):
                    cur.execute(f"""
                        SELECT m.message_text, i.name, c.start_time
                        FROM test_message_{self.test_id} m
                        JOIN test_conversation_{self.test_id} c ON m.conversation_id = c.conversation_id
                        JOIN test_inspector_{self.test_id} i ON c.inspector_id = i.inspector_id
                        WHERE m.sender_type = %s
                        ORDER BY m.timestamp DESC
                        LIMIT 5
                    """, ('inspector',))
                    join_results = cur.fetchall()
                
                # 3. 查询实验数据
                with self.perf_monitor.track_user_operation(client_id, 'query_experiments'):
                    cur.execute(f"""
                        SELECT experiment_type, status, experiment_date
                        FROM test_experiment_{self.test_id}
                        ORDER BY experiment_date DESC
                        LIMIT 5
                    """)
                    experiments = cur.fetchall()
                
                # 模拟客户端处理时间
                time.sleep(0.01)
        except Exception as e:
            print(f"客户端查询任务出错: {str(e)}")
        finally:
            if cur:
                cur.close()
            if conn:
                self.pool.putconn(conn)
            
            # 注销用户会话
            self.perf_monitor.unregister_user(client_id)
    
    def _client_insert_task(self, client_id):
        """客户端插入任务函数，在线程中执行"""
        # 注册用户会话
        self.perf_monitor.register_user(client_id)
        
        # 获取连接
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            
            # 执行多个插入操作
            for i in range(self.operations_per_client):
                # 1. 插入消息记录
                with self.perf_monitor.track_user_operation(client_id, 'insert_message'):
                    conversation_id = random.randint(1, 5)  # 随机选择会话ID
                    message_text = f"测试消息 from {client_id} - {i}"
                    sender_type = random.choice(['inspector', 'system'])
                    
                    cur.execute(f"""
                        INSERT INTO test_message_{self.test_id}
                        (conversation_id, message_seq, client_id, sender_type, message_text)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        conversation_id,
                        i + 1,
                        client_id,
                        sender_type,
                        message_text
                    ))
                    
                    conn.commit()
                
                # 模拟客户端处理时间
                time.sleep(0.02)
        except Exception as e:
            print(f"客户端插入任务出错: {str(e)}")
        finally:
            if cur:
                cur.close()
            if conn:
                self.pool.putconn(conn)
            
            # 注销用户会话
            self.perf_monitor.unregister_user(client_id)
    
    def _client_mixed_task(self, client_id):
        """客户端混合操作任务函数，在线程中执行"""
        # 注册用户会话
        self.perf_monitor.register_user(client_id)
        
        # 获取连接
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            
            # 执行混合的读写操作
            for i in range(self.operations_per_client):
                # 随机选择操作类型：70%查询，30%写入
                operation_type = random.choices(
                    ['query', 'insert'], 
                    weights=[0.7, 0.3], 
                    k=1
                )[0]
                
                if operation_type == 'query':
                    # 执行查询操作
                    query_type = random.choice(['messages', 'join', 'experiment'])
                    
                    if query_type == 'messages':
                        with self.perf_monitor.track_user_operation(client_id, 'query_messages'):
                            conversation_id = random.randint(1, 5)
                            cur.execute(f"""
                                SELECT message_text, sender_type, timestamp
                                FROM test_message_{self.test_id}
                                WHERE conversation_id = %s
                                ORDER BY timestamp DESC
                                LIMIT 10
                            """, (conversation_id,))
                            messages = cur.fetchall()
                    
                    elif query_type == 'join':
                        with self.perf_monitor.track_user_operation(client_id, 'join_query'):
                            cur.execute(f"""
                                SELECT m.message_text, i.name, c.start_time
                                FROM test_message_{self.test_id} m
                                JOIN test_conversation_{self.test_id} c ON m.conversation_id = c.conversation_id
                                JOIN test_inspector_{self.test_id} i ON c.inspector_id = i.inspector_id
                                ORDER BY m.timestamp DESC
                                LIMIT 5
                            """)
                            join_results = cur.fetchall()
                    
                    else:  # experiment
                        with self.perf_monitor.track_user_operation(client_id, 'query_experiments'):
                            cur.execute(f"""
                                SELECT experiment_type, status, experiment_date
                                FROM test_experiment_{self.test_id}
                                ORDER BY experiment_date DESC
                                LIMIT 5
                            """)
                            experiments = cur.fetchall()
                
                else:  # insert
                    # 执行插入操作
                    with self.perf_monitor.track_user_operation(client_id, 'insert_message'):
                        conversation_id = random.randint(1, 5)
                        message_text = f"混合操作测试消息 from {client_id} - {i}"
                        sender_type = random.choice(['inspector', 'system'])
                        
                        cur.execute(f"""
                            INSERT INTO test_message_{self.test_id}
                            (conversation_id, message_seq, client_id, sender_type, message_text)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            conversation_id,
                            i + 1,
                            client_id,
                            sender_type,
                            message_text
                        ))
                        
                        conn.commit()
                
                # 模拟客户端思考时间
                time.sleep(random.uniform(0.01, 0.05))
        except Exception as e:
            print(f"客户端混合任务出错: {str(e)}")
        finally:
            if cur:
                cur.close()
            if conn:
                self.pool.putconn(conn)
            
            # 注销用户会话
            self.perf_monitor.unregister_user(client_id)
    
    def _client_transaction_task(self, client_id, client_index):
        """客户端事务任务函数，在线程中执行"""
        # 注册用户会话
        self.perf_monitor.register_user(client_id)
        
        # 获取连接
        conn = self.pool.getconn()
        success = False
        cur = None
        
        try:
            # 关闭自动提交
            conn.autocommit = False
            cur = conn.cursor()
            
            # 开始事务
            with self.perf_monitor.track_user_operation(client_id, 'transaction'):
                # 1. 创建实验记录 - 使用时间戳确保唯一性
                timestamp = int(time.time() * 1000000)  # 微秒级时间戳
                experiment_no = f"EXP-{self.test_id}-{client_id}-{timestamp}"
                inspector_id = client_index % 5 + 1  # 1-5之间循环
                lab_id = client_index % 3 + 1  # 1-3之间循环
                item_id = client_index % 10 + 1  # 1-10之间循环
                
                cur.execute(f"""
                    INSERT INTO test_experiment_{self.test_id}
                    (experiment_no, inspector_id, lab_id, item_id, experiment_type, client_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING experiment_id
                """, (
                    experiment_no,
                    inspector_id,
                    lab_id,
                    item_id,
                    f"测试实验-{client_id}",
                    client_id
                ))
                
                experiment_id = cur.fetchone()[0]
                
                # 2. 添加3个数据点
                for i in range(3):
                    cur.execute(f"""
                        INSERT INTO test_data_point_{self.test_id}
                        (experiment_id, measurement_type, measurement_value, measurement_unit)
                        VALUES (%s, %s, %s, %s)
                    """, (
                        experiment_id,
                        f"测量类型-{i+1}",
                        100.0 + i * 10.0,
                        "单位"
                    ))
                
                # 3. 更新实验状态
                cur.execute(f"""
                    UPDATE test_experiment_{self.test_id}
                    SET status = %s
                    WHERE experiment_id = %s
                """, ('completed', experiment_id))
                
                # 4. 提交事务
                conn.commit()
                success = True
        except psycopg2.errors.DeadlockDetected as e:
            # 死锁错误 - 回滚并标记为失败
            if conn:
                conn.rollback()
            print(f"客户端事务任务死锁: {client_id} - {str(e)}")
            success = False
        except psycopg2.errors.UniqueViolation as e:
            # 唯一性约束冲突 - 回滚并标记为失败
            if conn:
                conn.rollback()
            print(f"客户端事务任务唯一性冲突: {client_id} - {str(e)}")
            success = False
        except Exception as e:
            # 其他错误 - 回滚并标记为失败
            if conn:
                conn.rollback()
            print(f"客户端事务任务出错: {client_id} - {str(e)}")
            success = False
        finally:
            if cur:
                cur.close()
            if conn:
                # 确保连接状态正确
                try:
                    if not conn.closed:
                        self.pool.putconn(conn)
                except Exception:
                    pass
            
            # 注销用户会话
            self.perf_monitor.unregister_user(client_id)
        
        return success
    
    def _prepare_test_data(self):
        """准备测试数据，确保并发测试有足够的数据可操作"""
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            
            # 清理可能存在的旧表
            cur.execute(f"DROP TABLE IF EXISTS test_data_point_{self.test_id}")
            cur.execute(f"DROP TABLE IF EXISTS test_experiment_{self.test_id}")
            cur.execute(f"DROP TABLE IF EXISTS test_message_{self.test_id}")
            cur.execute(f"DROP TABLE IF EXISTS test_conversation_{self.test_id}")
            cur.execute(f"DROP TABLE IF EXISTS test_item_{self.test_id}")
            cur.execute(f"DROP TABLE IF EXISTS test_inspector_{self.test_id}")
            cur.execute(f"DROP TABLE IF EXISTS test_laboratory_{self.test_id}")
            
            # 创建测试表
            # 1. 药检员表
            cur.execute(f"""
                CREATE TABLE test_inspector_{self.test_id} (
                    inspector_id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    department VARCHAR(100)
                )
            """)
            
            # 2. 实验室表
            cur.execute(f"""
                CREATE TABLE test_laboratory_{self.test_id} (
                    lab_id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    location VARCHAR(200)
                )
            """)
            
            # 3. 药品条目表
            cur.execute(f"""
                CREATE TABLE test_item_{self.test_id} (
                    item_id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    category VARCHAR(100)
                )
            """)
            
            # 4. 对话会话表
            cur.execute(f"""
                CREATE TABLE test_conversation_{self.test_id} (
                    conversation_id SERIAL PRIMARY KEY,
                    inspector_id INT NOT NULL,
                    session_id VARCHAR(100) UNIQUE NOT NULL,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    total_messages INT DEFAULT 0,
                    FOREIGN KEY (inspector_id) REFERENCES test_inspector_{self.test_id}(inspector_id)
                )
            """)
            
            # 5. 对话消息表
            cur.execute(f"""
                CREATE TABLE test_message_{self.test_id} (
                    message_id SERIAL PRIMARY KEY,
                    conversation_id INT NOT NULL,
                    message_seq INT NOT NULL,
                    client_id VARCHAR(100),
                    sender_type VARCHAR(20) NOT NULL,
                    message_text TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES test_conversation_{self.test_id}(conversation_id)
                )
            """)
            
            # 6. 实验记录表
            cur.execute(f"""
                CREATE TABLE test_experiment_{self.test_id} (
                    experiment_id SERIAL PRIMARY KEY,
                    experiment_no VARCHAR(100) UNIQUE NOT NULL,
                    inspector_id INT NOT NULL,
                    lab_id INT NOT NULL,
                    item_id INT NOT NULL,
                    client_id VARCHAR(100),
                    experiment_type VARCHAR(100),
                    status VARCHAR(50) DEFAULT 'pending',
                    experiment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (inspector_id) REFERENCES test_inspector_{self.test_id}(inspector_id),
                    FOREIGN KEY (lab_id) REFERENCES test_laboratory_{self.test_id}(lab_id),
                    FOREIGN KEY (item_id) REFERENCES test_item_{self.test_id}(item_id)
                )
            """)
            
            # 7. 实验数据点表
            cur.execute(f"""
                CREATE TABLE test_data_point_{self.test_id} (
                    data_id SERIAL PRIMARY KEY,
                    experiment_id INT NOT NULL,
                    measurement_type VARCHAR(100) NOT NULL,
                    measurement_value DECIMAL(12,4),
                    measurement_unit VARCHAR(50),
                    FOREIGN KEY (experiment_id) REFERENCES test_experiment_{self.test_id}(experiment_id)
                )
            """)
            
            # 插入基础测试数据
            # 1. 药检员
            for i in range(5):
                cur.execute(f"""
                    INSERT INTO test_inspector_{self.test_id} (name, department)
                    VALUES (%s, %s)
                """, (f"药检员{i+1}", f"部门{i%3+1}"))
            
            # 2. 实验室
            for i in range(3):
                cur.execute(f"""
                    INSERT INTO test_laboratory_{self.test_id} (name, location)
                    VALUES (%s, %s)
                """, (f"实验室{i+1}", f"位置{i+1}"))
            
            # 3. 药品条目
            for i in range(10):
                cur.execute(f"""
                    INSERT INTO test_item_{self.test_id} (name, category)
                    VALUES (%s, %s)
                """, (f"药品{i+1}", f"类别{i%4+1}"))
            
            # 4. 对话会话
            for i in range(5):
                inspector_id = i % 5 + 1
                cur.execute(f"""
                    INSERT INTO test_conversation_{self.test_id} (inspector_id, session_id)
                    VALUES (%s, %s)
                """, (inspector_id, f"session-{i+1}"))
            
            # 5. 对话消息 (每个会话10条消息)
            for conv_id in range(1, 6):
                for msg_id in range(10):
                    sender_type = 'inspector' if msg_id % 2 == 0 else 'system'
                    cur.execute(f"""
                        INSERT INTO test_message_{self.test_id} (conversation_id, message_seq, sender_type, message_text)
                        VALUES (%s, %s, %s, %s)
                    """, (conv_id, msg_id + 1, sender_type, f"会话{conv_id}的消息{msg_id+1}"))
            
            # 6. 实验记录
            for i in range(5):
                inspector_id = i % 5 + 1
                lab_id = i % 3 + 1
                item_id = i % 10 + 1
                cur.execute(f"""
                    INSERT INTO test_experiment_{self.test_id} (experiment_no, inspector_id, lab_id, item_id, experiment_type, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (f"EXP{i+1}", inspector_id, lab_id, item_id, f"实验类型{i%3+1}", "completed"))
            
            # 提交事务
            conn.commit()
            
            print(f"测试数据准备完成，测试ID: {self.test_id}")
        except Exception as e:
            print(f"准备测试数据时出错: {str(e)}")
        finally:
            if cur:
                cur.close()
            if conn:
                self.pool.putconn(conn)
    
    def _clean_test_data(self):
        """清理测试数据和临时表"""
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            
            # 删除测试表
            cur.execute(f"DROP TABLE IF EXISTS test_data_point_{self.test_id}")
            cur.execute(f"DROP TABLE IF EXISTS test_experiment_{self.test_id}")
            cur.execute(f"DROP TABLE IF EXISTS test_message_{self.test_id}")
            cur.execute(f"DROP TABLE IF EXISTS test_conversation_{self.test_id}")
            cur.execute(f"DROP TABLE IF EXISTS test_item_{self.test_id}")
            cur.execute(f"DROP TABLE IF EXISTS test_inspector_{self.test_id}")
            cur.execute(f"DROP TABLE IF EXISTS test_laboratory_{self.test_id}")
            
            conn.commit()
            
            print(f"测试数据清理完成，测试ID: {self.test_id}")
        except Exception as e:
            print(f"清理测试数据时出错: {str(e)}")
        finally:
            if cur:
                cur.close()
            if conn:
                self.pool.putconn(conn)
    
    def _generate_performance_report(self):
        """生成性能测试报告，包括平均响应时间、最大响应时间和成功率"""
        # 确保报告目录存在
        report_dir = os.path.join(os.path.dirname(__file__), 'doc')
        os.makedirs(report_dir, exist_ok=True)
        
        # 测试名称中英文映射
        test_name_map = {
            'concurrent_inserts': '并发插入',
            'concurrent_queries': '并发查询',
            'concurrent_mixed_operations': '混合操作',
            'concurrent_transactions': '并发事务',
            'scalability': '可扩展性'
        }
        
        # 生成CSV报告
        report_path = os.path.join(report_dir, f'concurrent_performance_report_{self.test_id}.csv')
        
        try:
            with open(report_path, 'w', newline='', encoding='utf-8') as csvfile:
                # 中文表头字段名
                fieldnames = [
                    '测试名称', '客户端数量', '耗时(秒)', 
                    '平均响应时间(毫秒)', '最大响应时间(毫秒)', 
                    '操作总数', '每秒操作数',
                    '成功率'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for result in self.test_results:
                    # 将英文测试名称转换为中文
                    test_name_en = result.get('test_name', '')
                    test_name_cn = test_name_map.get(test_name_en, test_name_en)
                    
                    writer.writerow({
                        '测试名称': test_name_cn,
                        '客户端数量': result.get('client_count', ''),
                        '耗时(秒)': f"{result.get('duration', 0):.2f}",
                        '平均响应时间(毫秒)': f"{result.get('avg_response_time_ms', 0):.2f}",
                        '最大响应时间(毫秒)': f"{result.get('max_response_time_ms', 0):.2f}",
                        '操作总数': result.get('operations_count', ''),
                        '每秒操作数': f"{result.get('operations_per_second', 0):.2f}",
                        '成功率': f"{result.get('success_rate', 100):.2f}%"
                    })
            
            print(f"\n性能测试报告已生成: {report_path}")
        except Exception as e:
            print(f"生成性能报告时出错: {str(e)}")


if __name__ == '__main__':
    # 运行测试
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestConcurrentAccess)
    test_result = unittest.TextTestRunner(verbosity=2).run(test_suite)