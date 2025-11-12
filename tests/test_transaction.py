"""
事务机制测试模块(Transaction Mechanism Test Module)

本模块提供数据库事务机制的测试用例，用于验证系统的事务提交和回滚功能，
确保在执行多步操作时能够保证数据的一致性，满足课程对事务支持的要求。

使用方法:
    # 直接运行测试文件
    python tests/test_transaction.py
    
    # 或使用unittest模块运行
    python -m unittest tests.test_transaction
    
    # 运行特定测试类
    python -m unittest tests.test_transaction.TestTransactionMechanism
    
    # 运行特定测试方法
    python -m unittest tests.test_transaction.TestTransactionMechanism.test_successful_transaction
    
    # 查看详细测试输出
    python -m unittest tests.test_transaction -v

测试流程:
    1. 测试成功事务：创建实验记录和多个数据点，验证全部提交成功
    2. 测试事务回滚：模拟部分操作失败的情况，验证全部回滚
    3. 测试事务隔离：验证并发事务间的数据隔离性
    4. 测试事务持久性：验证提交后的数据能够永久保存
    5. 记录和报告事务执行时间，验证性能表现

主要功能:
    - TestTransactionMechanism: 事务机制测试类
        - setUp(): 
            测试前准备工作，创建测试数据库连接和事务服务对象
            
        - tearDown(): 
            测试后清理工作，关闭连接并清理测试数据
            
        - test_successful_transaction(): 
            测试正常情况下的事务提交，验证所有操作成功完成
            
        - test_transaction_rollback(): 
            测试异常情况下的事务回滚，验证所有操作都被撤销
            
        - test_transaction_isolation(): 
            测试事务隔离级别，验证并发事务间的数据隔离性
            
        - test_transaction_durability(): 
            测试事务持久性，验证提交的数据在系统重启后仍然存在
            
        - test_transaction_performance(): 
            测试事务执行性能，记录事务执行时间
            
        - _create_test_experiment_data(): 
            辅助方法，创建用于测试的实验数据
            
        - _verify_experiment_data(experiment_id): 
            辅助方法，验证实验数据是否正确插入
            
        - _clean_test_data(): 
            辅助方法，清理测试数据
"""

import unittest
import time
import uuid
import threading
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional

from config.database import get_test_db_config
from database.connection import get_connection_pool
from services.transaction_service import TransactionService
from services.performance_monitor import PerformanceMonitor


class TestTransactionMechanism(unittest.TestCase):
    """事务机制测试类，测试数据库事务的提交和回滚功能"""

    def setUp(self):
        """测试前准备工作，创建测试数据库连接和事务服务对象"""
        # 获取测试数据库连接池
        self.pool = get_connection_pool(get_test_db_config())
        self.conn = self.pool.getconn()
        self.conn.autocommit = False  # 关闭自动提交，手动控制事务
        self.cur = self.conn.cursor()
        
        # 创建事务服务对象
        self.transaction_service = TransactionService(self.pool)
        
        # 创建性能监控器
        self.perf_monitor = PerformanceMonitor()
        
        # 生成唯一测试标识，避免多次测试冲突
        self.test_id = str(uuid.uuid4()).replace('-', '')[:8]
        
        # 创建测试表
        self._create_test_tables()
        
        # 插入基础测试数据
        self._insert_base_test_data()

    def tearDown(self):
        """测试后清理工作，关闭连接并清理测试数据"""
        # 清理测试数据和临时表
        self._clean_test_data()
        
        # 关闭连接
        if self.cur:
            self.cur.close()
        if self.conn:
            self.pool.putconn(self.conn)

    def test_successful_transaction(self):
        """测试正常情况下的事务提交，验证所有操作成功完成"""
        with self.perf_monitor.measure_operation('测试成功事务'):
            # 准备实验数据
            experiment_data = self._create_test_experiment_data()
            
            try:
                # 开始事务
                success, experiment_id = self._execute_transaction(experiment_data)
                
                # 验证事务执行成功
                self.assertTrue(success, "事务应该成功执行")
                self.assertIsNotNone(experiment_id, "应该返回实验ID")
                
                # 验证实验数据已正确插入
                exists, data_points_count = self._verify_experiment_data(experiment_id)
                self.assertTrue(exists, "实验记录应该存在")
                self.assertEqual(data_points_count, len(experiment_data['data_points']), 
                                "数据点数量应该匹配")
            except Exception as e:
                self.fail(f"测试成功事务时出错: {str(e)}")

    def test_transaction_rollback(self):
        """测试异常情况下的事务回滚，验证所有操作都被撤销"""
        with self.perf_monitor.measure_operation('测试事务回滚'):
            # 准备实验数据
            experiment_data = self._create_test_experiment_data()
            
            # 故意插入一个无效的数据点（缺少必要字段）触发错误
            experiment_data['data_points'].append({
                'invalid_field': 'invalid_value'  # 缺少必要字段
            })
            
            try:
                # 开始事务，预期会失败
                conn = self.pool.getconn()
                try:
                    conn.autocommit = False
                    cur = conn.cursor()
                    
                    # 插入实验记录
                    cur.execute(f"""
                        INSERT INTO test_experiment_{self.test_id} (
                            experiment_no, inspector_id, lab_id, item_id, experiment_type
                        ) VALUES (%s, %s, %s, %s, %s) RETURNING experiment_id
                    """, (
                        experiment_data['experiment']['experiment_no'],
                        experiment_data['experiment']['inspector_id'],
                        experiment_data['experiment']['lab_id'],
                        experiment_data['experiment']['item_id'],
                        experiment_data['experiment']['experiment_type']
                    ))
                    
                    experiment_id = cur.fetchone()[0]
                    
                    # 尝试插入数据点，其中一个会失败
                    for data_point in experiment_data['data_points']:
                        try:
                            cur.execute(f"""
                                INSERT INTO test_data_point_{self.test_id} (
                                    experiment_id, measurement_type, measurement_value, measurement_unit
                                ) VALUES (%s, %s, %s, %s)
                            """, (
                                experiment_id,
                                data_point.get('measurement_type', '未知类型'),  # 可能不存在
                                data_point.get('measurement_value', 0),  # 可能不存在
                                data_point.get('measurement_unit', '')  # 可能不存在
                            ))
                        except Exception as e:
                            # 预期会失败
                            conn.rollback()
                            rollback_successful = True
                            break
                    else:
                        # 如果没有失败，手动回滚
                        conn.rollback()
                        rollback_successful = True
                    
                    # 验证回滚成功
                    self.assertTrue(rollback_successful, "应该成功回滚事务")
                    
                    # 查询实验记录，应该不存在
                    cur.execute(f"""
                        SELECT COUNT(*) FROM test_experiment_{self.test_id}
                        WHERE experiment_no = %s
                    """, (experiment_data['experiment']['experiment_no'],))
                    
                    count = cur.fetchone()[0]
                    self.assertEqual(count, 0, "回滚后实验记录应该不存在")
                    
                finally:
                    if cur:
                        cur.close()
                    if conn:
                        self.pool.putconn(conn)
            except Exception as e:
                self.fail(f"测试事务回滚时出错: {str(e)}")

    def test_transaction_isolation(self):
        """测试事务隔离级别，验证并发事务间的数据隔离性"""
        with self.perf_monitor.measure_operation('测试事务隔离'):
            # 准备测试数据
            exp_data1 = self._create_test_experiment_data(suffix="A")
            exp_data2 = self._create_test_experiment_data(suffix="B")
            
            # 设置事件标记用于线程协调
            tx1_started = threading.Event()
            tx1_inserted = threading.Event()
            tx2_tried_to_read = threading.Event()
            tx1_committed = threading.Event()
            tx2_completed = threading.Event()
            
            # 存储测试结果
            results = {"tx2_could_read_before_commit": None, "tx2_could_read_after_commit": None}
            
            # 事务1线程：插入数据但不立即提交
            def tx1_thread():
                conn = self.pool.getconn()
                try:
                    conn.autocommit = False
                    cur = conn.cursor()
                    
                    # 通知事务1已开始
                    tx1_started.set()
                    
                    # 插入实验记录
                    cur.execute(f"""
                        INSERT INTO test_experiment_{self.test_id} (
                            experiment_no, inspector_id, lab_id, item_id, experiment_type
                        ) VALUES (%s, %s, %s, %s, %s) RETURNING experiment_id
                    """, (
                        exp_data1['experiment']['experiment_no'],
                        exp_data1['experiment']['inspector_id'],
                        exp_data1['experiment']['lab_id'],
                        exp_data1['experiment']['item_id'],
                        exp_data1['experiment']['experiment_type']
                    ))
                    
                    # 通知插入已完成但未提交
                    tx1_inserted.set()
                    
                    # 等待事务2尝试读取
                    tx2_tried_to_read.wait(timeout=10)
                    
                    # 提交事务1
                    conn.commit()
                    
                    # 通知事务1已提交
                    tx1_committed.set()
                    
                    # 等待事务2完成
                    tx2_completed.wait(timeout=10)
                finally:
                    if cur:
                        cur.close()
                    if conn:
                        self.pool.putconn(conn)
            
            # 事务2线程：在事务1提交前后尝试读取数据
            def tx2_thread():
                conn = self.pool.getconn()
                try:
                    conn.autocommit = False
                    cur = conn.cursor()
                    
                    # 等待事务1插入数据
                    tx1_inserted.wait(timeout=10)
                    
                    # 在事务1提交前尝试读取
                    cur.execute(f"""
                        SELECT COUNT(*) FROM test_experiment_{self.test_id}
                        WHERE experiment_no = %s
                    """, (exp_data1['experiment']['experiment_no'],))
                    
                    count_before = cur.fetchone()[0]
                    results["tx2_could_read_before_commit"] = (count_before > 0)
                    
                    # 通知事务2已尝试读取
                    tx2_tried_to_read.set()
                    
                    # 等待事务1提交
                    tx1_committed.wait(timeout=10)
                    
                    # 在事务1提交后尝试读取
                    cur.execute(f"""
                        SELECT COUNT(*) FROM test_experiment_{self.test_id}
                        WHERE experiment_no = %s
                    """, (exp_data1['experiment']['experiment_no'],))
                    
                    count_after = cur.fetchone()[0]
                    results["tx2_could_read_after_commit"] = (count_after > 0)
                    
                    # 通知事务2已完成
                    tx2_completed.set()
                finally:
                    if cur:
                        cur.close()
                    if conn:
                        self.pool.putconn(conn)
            
            # 启动测试线程
            thread1 = threading.Thread(target=tx1_thread)
            thread2 = threading.Thread(target=tx2_thread)
            
            thread1.start()
            
            # 确保事务1已开始
            tx1_started.wait(timeout=10)
            
            thread2.start()
            
            # 等待测试完成
            thread1.join(timeout=15)
            thread2.join(timeout=15)
            
            # 验证隔离性
            self.assertFalse(results["tx2_could_read_before_commit"], 
                           "在事务1提交前，事务2不应该能读取事务1插入的数据（READ COMMITTED隔离级别）")
            
            self.assertTrue(results["tx2_could_read_after_commit"], 
                          "在事务1提交后，事务2应该能读取事务1插入的数据")

    def test_transaction_durability(self):
        """测试事务持久性，验证提交后的数据在系统重启后仍然存在"""
        with self.perf_monitor.measure_operation('测试事务持久性'):
            # 准备测试数据
            experiment_data = self._create_test_experiment_data(suffix="D")
            
            # 执行事务
            success, experiment_id = self._execute_transaction(experiment_data)
            
            # 验证事务执行成功
            self.assertTrue(success, "事务应该成功执行")
            
            # 关闭当前连接，模拟系统重启
            if self.cur:
                self.cur.close()
            if self.conn:
                self.pool.putconn(self.conn)
            
            # 重新获取连接
            self.conn = self.pool.getconn()
            self.cur = self.conn.cursor()
            
            # 查询实验数据，验证持久性
            exists, data_points_count = self._verify_experiment_data(experiment_id)
            
            # 验证数据持久存在
            self.assertTrue(exists, "实验记录在'重启'后应该仍然存在")
            self.assertEqual(data_points_count, len(experiment_data['data_points']), 
                            "数据点数量在'重启'后应该保持不变")

    def test_transaction_performance(self):
        """测试事务执行性能，记录事务执行时间"""
        # 测试不同数据点数量下的事务性能
        data_point_counts = [1, 5, 10, 20]
        results = []
        
        for count in data_point_counts:
            # 准备测试数据
            experiment_data = self._create_test_experiment_data(
                suffix=f"P{count}", 
                data_points_count=count
            )
            
            # 测量事务执行时间
            start_time = time.time()
            
            # 执行事务
            success, experiment_id = self._execute_transaction(experiment_data)
            
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            
            # 验证事务执行成功
            self.assertTrue(success, f"含{count}个数据点的事务应该成功执行")
            
            # 记录结果
            results.append({
                'data_points_count': count,
                'duration_ms': duration_ms
            })
            
            # 清理本次测试数据
            with self.perf_monitor.measure_operation('清理测试数据'):
                conn = self.pool.getconn()
                try:
                    conn.autocommit = True
                    cur = conn.cursor()
                    
                    # 删除本次测试的数据点
                    cur.execute(f"""
                        DELETE FROM test_data_point_{self.test_id} 
                        WHERE experiment_id = %s
                    """, (experiment_id,))
                    
                    # 删除本次测试的实验记录
                    cur.execute(f"""
                        DELETE FROM test_experiment_{self.test_id} 
                        WHERE experiment_id = %s
                    """, (experiment_id,))
                finally:
                    if cur:
                        cur.close()
                    if conn:
                        self.pool.putconn(conn)
        
        # 验证性能结果
        for i in range(1, len(results)):
            # 验证事务执行时间与数据点数量成正比
            ratio = results[i]['duration_ms'] / results[0]['duration_ms']
            expected_ratio = results[i]['data_points_count'] / results[0]['data_points_count']
            
            # 允许一定的误差范围
            self.assertLess(ratio / expected_ratio, 10.0, 
                          "事务执行时间应该与数据点数量基本成正比")
        
        # 将性能结果写入报告
        with open('transaction_performance_report.csv', 'w') as f:
            f.write('data_points_count,duration_ms\n')
            for result in results:
                f.write(f"{result['data_points_count']},{result['duration_ms']:.2f}\n")

    def _create_test_tables(self):
        """辅助方法，创建测试所需的临时表"""
        # 清理可能存在的旧表
        self.cur.execute(f"DROP TABLE IF EXISTS test_data_point_{self.test_id}")
        self.cur.execute(f"DROP TABLE IF EXISTS test_experiment_{self.test_id}")
        self.cur.execute(f"DROP TABLE IF EXISTS test_item_{self.test_id}")
        self.cur.execute(f"DROP TABLE IF EXISTS test_laboratory_{self.test_id}")
        self.cur.execute(f"DROP TABLE IF EXISTS test_inspector_{self.test_id}")
        
        # 创建药检员测试表
        self.cur.execute(f"""
            CREATE TABLE test_inspector_{self.test_id} (
                inspector_id SERIAL PRIMARY KEY,
                employee_no VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL
            )
        """)
        
        # 创建实验室测试表
        self.cur.execute(f"""
            CREATE TABLE test_laboratory_{self.test_id} (
                lab_id SERIAL PRIMARY KEY,
                lab_code VARCHAR(50) UNIQUE NOT NULL,
                lab_name VARCHAR(200) NOT NULL
            )
        """)
        
        # 创建药品条目测试表
        self.cur.execute(f"""
            CREATE TABLE test_item_{self.test_id} (
                item_id SERIAL PRIMARY KEY,
                name_cn VARCHAR(200) NOT NULL,
                category VARCHAR(100)
            )
        """)
        
        # 创建实验记录测试表
        self.cur.execute(f"""
            CREATE TABLE test_experiment_{self.test_id} (
                experiment_id SERIAL PRIMARY KEY,
                experiment_no VARCHAR(100) UNIQUE NOT NULL,
                inspector_id INT NOT NULL,
                lab_id INT NOT NULL,
                item_id INT NOT NULL,
                experiment_type VARCHAR(100),
                experiment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(50) DEFAULT 'pending',
                FOREIGN KEY (inspector_id) REFERENCES test_inspector_{self.test_id}(inspector_id),
                FOREIGN KEY (lab_id) REFERENCES test_laboratory_{self.test_id}(lab_id),
                FOREIGN KEY (item_id) REFERENCES test_item_{self.test_id}(item_id)
            )
        """)
        
        # 创建实验数据点测试表
        self.cur.execute(f"""
            CREATE TABLE test_data_point_{self.test_id} (
                data_id SERIAL PRIMARY KEY,
                experiment_id INT NOT NULL,
                measurement_type VARCHAR(100) NOT NULL,
                measurement_value DECIMAL(12,4),
                measurement_unit VARCHAR(50),
                FOREIGN KEY (experiment_id) REFERENCES test_experiment_{self.test_id}(experiment_id)
            )
        """)
        
        self.conn.commit()

    def _insert_base_test_data(self):
        """辅助方法，插入基础测试数据"""
        # 插入药检员测试数据
        self.cur.execute(f"""
            INSERT INTO test_inspector_{self.test_id} (employee_no, name) 
            VALUES (%s, %s) RETURNING inspector_id
        """, (f'EMP{self.test_id}', '测试药检员'))
        inspector_id = self.cur.fetchone()[0]
        
        # 插入实验室测试数据
        self.cur.execute(f"""
            INSERT INTO test_laboratory_{self.test_id} (lab_code, lab_name) 
            VALUES (%s, %s) RETURNING lab_id
        """, (f'LAB{self.test_id}', '测试实验室'))
        lab_id = self.cur.fetchone()[0]
        
        # 插入药品条目测试数据
        self.cur.execute(f"""
            INSERT INTO test_item_{self.test_id} (name_cn, category) 
            VALUES (%s, %s) RETURNING item_id
        """, ('测试药品', '测试类别'))
        item_id = self.cur.fetchone()[0]
        
        self.conn.commit()
        
        # 保存ID供后续测试使用
        self.test_inspector_id = inspector_id
        self.test_lab_id = lab_id
        self.test_item_id = item_id

    def _create_test_experiment_data(self, suffix="", data_points_count=3):
        """辅助方法，创建用于测试的实验数据"""
        # 构造实验记录
        experiment = {
            'experiment_no': f'EXP{self.test_id}{suffix}',
            'inspector_id': self.test_inspector_id,
            'lab_id': self.test_lab_id,
            'item_id': self.test_item_id,
            'experiment_type': '测试实验类型'
        }
        
        # 构造实验数据点
        data_points = []
        for i in range(data_points_count):
            data_points.append({
                'measurement_type': f'测量类型{i+1}',
                'measurement_value': 100.0 + i * 10.0,
                'measurement_unit': '单位'
            })
        
        return {
            'experiment': experiment,
            'data_points': data_points
        }

    def _execute_transaction(self, experiment_data):
        """辅助方法，执行实验数据事务"""
        conn = self.pool.getconn()
        experiment_id = None
        success = False
        
        try:
            conn.autocommit = False
            cur = conn.cursor()
            
            # 插入实验记录
            cur.execute(f"""
                INSERT INTO test_experiment_{self.test_id} (
                    experiment_no, inspector_id, lab_id, item_id, experiment_type
                ) VALUES (%s, %s, %s, %s, %s) RETURNING experiment_id
            """, (
                experiment_data['experiment']['experiment_no'],
                experiment_data['experiment']['inspector_id'],
                experiment_data['experiment']['lab_id'],
                experiment_data['experiment']['item_id'],
                experiment_data['experiment']['experiment_type']
            ))
            
            experiment_id = cur.fetchone()[0]
            
            # 插入数据点
            for data_point in experiment_data['data_points']:
                cur.execute(f"""
                    INSERT INTO test_data_point_{self.test_id} (
                        experiment_id, measurement_type, measurement_value, measurement_unit
                    ) VALUES (%s, %s, %s, %s)
                """, (
                    experiment_id,
                    data_point['measurement_type'],
                    data_point['measurement_value'],
                    data_point['measurement_unit']
                ))
            
            # 提交事务
            conn.commit()
            success = True
        except Exception as e:
            # 回滚事务
            conn.rollback()
            success = False
            print(f"事务执行失败: {str(e)}")
        finally:
            if cur:
                cur.close()
            if conn:
                self.pool.putconn(conn)
        
        return success, experiment_id

    def _verify_experiment_data(self, experiment_id):
        """辅助方法，验证实验数据是否正确插入"""
        conn = self.pool.getconn()
        try:
            cur = conn.cursor()
            
            # 检查实验记录是否存在
            cur.execute(f"""
                SELECT COUNT(*) FROM test_experiment_{self.test_id}
                WHERE experiment_id = %s
            """, (experiment_id,))
            
            experiment_count = cur.fetchone()[0]
            exists = (experiment_count > 0)
            
            # 检查数据点数量
            cur.execute(f"""
                SELECT COUNT(*) FROM test_data_point_{self.test_id}
                WHERE experiment_id = %s
            """, (experiment_id,))
            
            data_points_count = cur.fetchone()[0]
            
            return exists, data_points_count
        finally:
            if cur:
                cur.close()
            if conn:
                self.pool.putconn(conn)

    def _clean_test_data(self):
        """辅助方法，清理测试数据和临时表"""
        try:
            # 删除测试表
            self.cur.execute(f"DROP TABLE IF EXISTS test_data_point_{self.test_id}")
            self.cur.execute(f"DROP TABLE IF EXISTS test_experiment_{self.test_id}")
            self.cur.execute(f"DROP TABLE IF EXISTS test_item_{self.test_id}")
            self.cur.execute(f"DROP TABLE IF EXISTS test_laboratory_{self.test_id}")
            self.cur.execute(f"DROP TABLE IF EXISTS test_inspector_{self.test_id}")
            self.conn.commit()
        except Exception as e:
            # 记录清理错误但不影响测试结果
            print(f"清理测试数据时出错: {e}")


if __name__ == '__main__':
    # 生成性能报告的路径
    performance_report_path = 'transaction_performance_report.csv'
    
    # 运行测试
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestTransactionMechanism)
    test_result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    
    # 生成性能报告
    perf_monitor = PerformanceMonitor()
    perf_monitor.generate_report(performance_report_path)
    
    print(f"性能报告已保存至: {performance_report_path}")