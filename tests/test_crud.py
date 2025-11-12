"""
CRUD操作测试模块(CRUD Operations Test Module)

本模块提供基本CRUD（创建、读取、更新、删除）操作的测试用例，
用于验证数据库表的创建、数据插入、查询、更新和删除功能，
确保系统满足课程要求的基本数据库操作功能。

使用方法:
    # 直接运行测试文件
    python tests/test_crud.py
    
    # 或使用unittest模块运行
    python -m unittest tests.test_crud
    
    # 运行特定测试类
    python -m unittest tests.test_crud.TestCRUDOperations
    
    # 运行特定测试方法
    python -m unittest tests.test_crud.TestCRUDOperations.test_create_table
    
    # 查看详细测试输出
    python -m unittest tests.test_crud -v

测试流程:
    1. 创建测试用的临时表
    2. 向表中插入数据并验证插入成功
    3. 查询数据并验证查询结果正确
    4. 更新数据并验证更新生效
    5. 执行跨表JOIN查询并验证结果
    6. 删除数据并验证删除成功
    7. 删除表并验证表已删除
    8. 所有测试自动清理临时数据

主要功能:
    - TestCRUDOperations: CRUD操作测试类
        - setUp(): 
            测试前准备工作，创建测试数据库连接
            
        - tearDown(): 
            测试后清理工作，关闭连接并清理临时数据
            
        - test_create_table(): 
            测试创建表功能
            
        - test_insert_data(): 
            测试数据插入功能
            
        - test_query_data(): 
            测试数据查询功能
            
        - test_update_data(): 
            测试数据更新功能
            
        - test_join_query(): 
            测试跨表JOIN查询功能
            
        - test_delete_data(): 
            测试数据删除功能
            
        - test_drop_table(): 
            测试删除表功能
            
        - _create_test_tables(): 
            辅助方法，创建测试所需的临时表
            
        - _insert_test_data(): 
            辅助方法，插入测试数据
            
        - _clean_test_data(): 
            辅助方法，清理测试数据和临时表
"""

import unittest
import time
import uuid
import psycopg2
from datetime import datetime, timedelta

from config.database import get_test_db_config
from database.connection import get_connection_pool
from services.performance_monitor import PerformanceMonitor


class TestCRUDOperations(unittest.TestCase):
    """CRUD操作测试类，测试基本的创建、读取、更新和删除操作"""

    def setUp(self):
        """测试前准备工作，创建测试数据库连接"""
        # 获取测试数据库连接池
        self.pool = get_connection_pool(get_test_db_config())
        self.conn = self.pool.getconn()
        self.cur = self.conn.cursor()
        
        # 创建性能监控器
        self.perf_monitor = PerformanceMonitor()
        
        # 生成唯一测试标识，避免多次测试冲突
        self.test_id = str(uuid.uuid4()).replace('-', '')[:8]
        
        # 创建测试表
        self._create_test_tables()

    def tearDown(self):
        """测试后清理工作，关闭连接并清理临时数据"""
        # 清理测试数据和临时表
        self._clean_test_data()
        
        # 关闭连接
        if self.cur:
            self.cur.close()
        if self.conn:
            self.pool.putconn(self.conn)

    def test_create_table(self):
        """测试创建表功能"""
        with self.perf_monitor.measure_operation('测试创建表'):
            # 检查测试表是否存在
            self.cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (f'test_inspector_{self.test_id}',))
            
            table_exists = self.cur.fetchone()[0]
            self.assertTrue(table_exists, "测试表应该成功创建")

    def test_insert_data(self):
        """测试数据插入功能"""
        with self.perf_monitor.measure_operation('测试数据插入'):
            # 插入测试数据
            self.cur.execute(f"""
                INSERT INTO test_inspector_{self.test_id} 
                (employee_no, name, department) 
                VALUES (%s, %s, %s) RETURNING inspector_id
            """, (f'EMP{self.test_id}', '测试药检员', '测试部门'))
            
            inspector_id = self.cur.fetchone()[0]
            self.conn.commit()
            
            # 验证插入成功
            self.assertIsNotNone(inspector_id, "插入操作应该返回ID")
            self.assertGreater(inspector_id, 0, "插入的ID应该大于0")

    def test_query_data(self):
        """测试数据查询功能"""
        # 先插入测试数据
        self._insert_test_data()
        
        with self.perf_monitor.measure_operation('测试数据查询'):
            # 查询数据
            self.cur.execute(f"""
                SELECT employee_no, name, department 
                FROM test_inspector_{self.test_id} 
                WHERE employee_no = %s
            """, (f'EMP{self.test_id}',))
            
            result = self.cur.fetchone()
            
            # 验证查询结果
            self.assertIsNotNone(result, "应该查询到插入的数据")
            self.assertEqual(result[0], f'EMP{self.test_id}', "工号应该匹配")
            self.assertEqual(result[1], '测试药检员', "姓名应该匹配")
            self.assertEqual(result[2], '测试部门', "部门应该匹配")

    def test_update_data(self):
        """测试数据更新功能"""
        # 先插入测试数据
        self._insert_test_data()
        
        with self.perf_monitor.measure_operation('测试数据更新'):
            # 更新数据
            self.cur.execute(f"""
                UPDATE test_inspector_{self.test_id} 
                SET name = %s, department = %s 
                WHERE employee_no = %s
            """, ('更新后的药检员', '更新后的部门', f'EMP{self.test_id}'))
            
            self.conn.commit()
            
            # 查询更新后的数据
            self.cur.execute(f"""
                SELECT name, department 
                FROM test_inspector_{self.test_id} 
                WHERE employee_no = %s
            """, (f'EMP{self.test_id}',))
            
            result = self.cur.fetchone()
            
            # 验证更新结果
            self.assertEqual(result[0], '更新后的药检员', "更新后姓名应该匹配")
            self.assertEqual(result[1], '更新后的部门', "更新后部门应该匹配")

    def test_join_query(self):
        """测试跨表JOIN查询功能"""
        # 先插入测试数据
        inspector_id = self._insert_test_data()
        
        # 插入实验室数据
        self.cur.execute(f"""
            INSERT INTO test_laboratory_{self.test_id} 
            (lab_code, lab_name) 
            VALUES (%s, %s) RETURNING lab_id
        """, (f'LAB{self.test_id}', '测试实验室'))
        
        lab_id = self.cur.fetchone()[0]
        
        # 插入关联数据
        self.cur.execute(f"""
            INSERT INTO test_access_{self.test_id} 
            (inspector_id, lab_id, access_level) 
            VALUES (%s, %s, %s)
        """, (inspector_id, lab_id, '测试权限'))
        
        self.conn.commit()
        
        with self.perf_monitor.measure_operation('测试JOIN查询'):
            # 执行JOIN查询
            self.cur.execute(f"""
                SELECT i.name, i.department, l.lab_name, a.access_level 
                FROM test_inspector_{self.test_id} i
                JOIN test_access_{self.test_id} a ON i.inspector_id = a.inspector_id
                JOIN test_laboratory_{self.test_id} l ON a.lab_id = l.lab_id
                WHERE i.employee_no = %s
            """, (f'EMP{self.test_id}',))
            
            result = self.cur.fetchone()
            
            # 验证JOIN查询结果
            self.assertIsNotNone(result, "JOIN查询应该返回结果")
            self.assertEqual(result[0], '测试药检员', "JOIN查询结果中的姓名应该匹配")
            self.assertEqual(result[1], '测试部门', "JOIN查询结果中的部门应该匹配")
            self.assertEqual(result[2], '测试实验室', "JOIN查询结果中的实验室名称应该匹配")
            self.assertEqual(result[3], '测试权限', "JOIN查询结果中的权限级别应该匹配")

    def test_delete_data(self):
        """测试数据删除功能"""
        # 先插入测试数据
        self._insert_test_data()
        
        with self.perf_monitor.measure_operation('测试数据删除'):
            # 删除数据
            self.cur.execute(f"""
                DELETE FROM test_inspector_{self.test_id} 
                WHERE employee_no = %s
            """, (f'EMP{self.test_id}',))
            
            self.conn.commit()
            
            # 验证删除成功
            self.cur.execute(f"""
                SELECT COUNT(*) FROM test_inspector_{self.test_id} 
                WHERE employee_no = %s
            """, (f'EMP{self.test_id}',))
            
            count = self.cur.fetchone()[0]
            self.assertEqual(count, 0, "删除后查询应该返回0条记录")

    def test_drop_table(self):
        """测试删除表功能"""
        with self.perf_monitor.measure_operation('测试删除表'):
            # 先删除依赖的表（外键约束）
            self.cur.execute(f"DROP TABLE IF EXISTS test_access_{self.test_id} CASCADE")
            # 删除临时表
            self.cur.execute(f"DROP TABLE IF EXISTS test_inspector_{self.test_id} CASCADE")
            self.cur.execute(f"DROP TABLE IF EXISTS test_laboratory_{self.test_id} CASCADE")
            self.conn.commit()
            
            # 检查表是否已删除
            self.cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (f'test_inspector_{self.test_id}',))
            
            table_exists = self.cur.fetchone()[0]
            self.assertFalse(table_exists, "测试表应该成功删除")

    def _create_test_tables(self):
        """辅助方法，创建测试所需的临时表"""
        # 清理可能存在的旧表
        self.cur.execute(f"DROP TABLE IF EXISTS test_access_{self.test_id}")
        self.cur.execute(f"DROP TABLE IF EXISTS test_inspector_{self.test_id}")
        self.cur.execute(f"DROP TABLE IF EXISTS test_laboratory_{self.test_id}")
        
        # 创建药检员测试表
        self.cur.execute(f"""
            CREATE TABLE test_inspector_{self.test_id} (
                inspector_id SERIAL PRIMARY KEY,
                employee_no VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                department VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建实验室测试表
        self.cur.execute(f"""
            CREATE TABLE test_laboratory_{self.test_id} (
                lab_id SERIAL PRIMARY KEY,
                lab_code VARCHAR(50) UNIQUE NOT NULL,
                lab_name VARCHAR(200) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建权限关系测试表
        self.cur.execute(f"""
            CREATE TABLE test_access_{self.test_id} (
                access_id SERIAL PRIMARY KEY,
                inspector_id INT NOT NULL,
                lab_id INT NOT NULL,
                access_level VARCHAR(50),
                granted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (inspector_id) REFERENCES test_inspector_{self.test_id}(inspector_id),
                FOREIGN KEY (lab_id) REFERENCES test_laboratory_{self.test_id}(lab_id),
                UNIQUE(inspector_id, lab_id)
            )
        """)
        
        self.conn.commit()

    def _insert_test_data(self):
        """辅助方法，插入测试数据"""
        # 插入药检员测试数据
        self.cur.execute(f"""
            INSERT INTO test_inspector_{self.test_id} 
            (employee_no, name, department) 
            VALUES (%s, %s, %s) RETURNING inspector_id
        """, (f'EMP{self.test_id}', '测试药检员', '测试部门'))
        
        inspector_id = self.cur.fetchone()[0]
        self.conn.commit()
        
        return inspector_id

    def _clean_test_data(self):
        """辅助方法，清理测试数据和临时表"""
        try:
            # 删除测试关系表
            self.cur.execute(f"DROP TABLE IF EXISTS test_access_{self.test_id}")
            # 删除测试药检员表
            self.cur.execute(f"DROP TABLE IF EXISTS test_inspector_{self.test_id}")
            # 删除测试实验室表
            self.cur.execute(f"DROP TABLE IF EXISTS test_laboratory_{self.test_id}")
            self.conn.commit()
        except Exception as e:
            # 记录清理错误但不影响测试结果
            print(f"清理测试数据时出错: {e}")


if __name__ == '__main__':
    # 生成性能报告的路径
    performance_report_path = 'crud_performance_report.csv'
    
    # 运行测试
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestCRUDOperations)
    test_result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    
    # 生成性能报告
    perf_monitor = PerformanceMonitor()
    perf_monitor.generate_report(performance_report_path)
    
    print(f"性能报告已保存至: {performance_report_path}")