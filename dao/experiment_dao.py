"""
实验记录数据访问对象(Experiment DAO)模块

本模块提供对experiment_records表和experiment_data_points表的数据访问功能，
用于管理药检员的实验记录和实验数据点信息，是系统中第二主要的数据源。

使用方法:
    from dao.experiment_dao import ExperimentDAO
    from database.connection import get_connection_pool
    
    # 创建DAO实例
    conn_pool = get_connection_pool()
    experiment_dao = ExperimentDAO(conn_pool)
    
    # 创建新实验记录（事务操作）
    experiment_data = {
        'experiment': {
            'experiment_no': 'EXP2025001',
            'inspector_id': 1,
            'lab_id': 2,
            'item_id': 100,
            'experiment_type': '含量测定',
            'batch_no': 'B20250101',
            'experiment_date': '2025-01-15'
        },
        'data_points': [
            {
                'measurement_type': 'pH值',
                'measurement_value': 6.8,
                'measurement_unit': 'pH',
                'standard_min': 6.0,
                'standard_max': 7.5,
                'is_qualified': True
            },
            {
                'measurement_type': '含量',
                'measurement_value': 98.5,
                'measurement_unit': '%',
                'standard_min': 95.0,
                'standard_max': 105.0,
                'is_qualified': True
            }
        ]
    }
    experiment_id = experiment_dao.create_experiment_with_data(experiment_data)
    
    # 查询药检员的所有实验
    experiments = experiment_dao.get_by_inspector(inspector_id=1)
    
    # 获取实验的所有数据点
    data_points = experiment_dao.get_experiment_data_points(experiment_id=1)

主要功能:
    - ExperimentDAO: 实验记录数据访问对象类
        - create_experiment(): 创建新实验记录
        - create_experiment_with_data(): 在事务中创建实验记录及其数据点（原子操作）
        - add_data_point(): 添加实验数据点
        - get_by_inspector(): 获取指定药检员的实验记录
        - get_by_item(): 获取指定药典条目的实验记录
        - find_by_date_range(): 按日期范围查询实验记录
        - find_by_status(): 按状态查询实验记录
        - update_experiment_status(): 更新实验状态和结果
        - get_experiment_data_points(): 获取实验的所有数据点
        - get_experiment_with_details(): 获取实验详情（含药检员、实验室、药典条目信息）
"""

from .base_dao import BaseDAO
from utils.performance_logger import log_execution_time
from datetime import datetime
import uuid


class ExperimentDAO(BaseDAO):
    """实验记录数据访问对象类"""

    def __init__(self, connection_pool):
        """初始化实验DAO"""
        super().__init__(connection_pool, 'experiment_records', 'experiment_id')
        self.data_points_dao = DataPointsDAO(connection_pool)

    @log_execution_time
    def create_experiment(self, experiment_data):
        """
        创建新实验记录
        
        参数:
            experiment_data: 实验数据字典
            
        返回:
            新创建的实验ID
        """
        # 确保有实验编号
        if 'experiment_no' not in experiment_data:
            experiment_data['experiment_no'] = f"EXP{uuid.uuid4().hex[:10].upper()}"
            
        # 确保有实验日期
        if 'experiment_date' not in experiment_data:
            experiment_data['experiment_date'] = datetime.now().strftime('%Y-%m-%d')
            
        # 默认状态为进行中
        if 'status' not in experiment_data:
            experiment_data['status'] = '进行中'
            
        return self.insert(experiment_data)

    @log_execution_time
    def create_experiment_with_data(self, data):
        """
        在事务中创建实验记录及其数据点（原子操作）
        
        参数:
            data: 包含'experiment'和'data_points'的字典
            
        返回:
            新创建的实验ID
        """
        # 使用事务确保原子性
        def transaction_callback(cursor):
            # 1. 插入实验记录
            experiment_data = data['experiment']
            
            # 确保有实验编号
            if 'experiment_no' not in experiment_data:
                experiment_data['experiment_no'] = f"EXP{uuid.uuid4().hex[:10].upper()}"
                
            # 确保有实验日期
            if 'experiment_date' not in experiment_data:
                experiment_data['experiment_date'] = datetime.now().strftime('%Y-%m-%d')
                
            # 默认状态为进行中
            if 'status' not in experiment_data:
                experiment_data['status'] = '进行中'
                
            columns = list(experiment_data.keys())
            values = list(experiment_data.values())
            placeholders = ["%s"] * len(columns)
            
            query = f"""
                INSERT INTO experiment_records ({", ".join(columns)})
                VALUES ({", ".join(placeholders)})
                RETURNING experiment_id
            """
            
            cursor.execute(query, values)
            experiment_id = cursor.fetchone()[0]
            
            # 2. 插入数据点
            if 'data_points' in data and data['data_points']:
                data_points = data['data_points']
                for point in data_points:
                    point['experiment_id'] = experiment_id
                    
                    if 'measurement_time' not in point:
                        point['measurement_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    point_columns = list(point.keys())
                    point_values = list(point.values())
                    point_placeholders = ["%s"] * len(point_columns)
                    
                    point_query = f"""
                        INSERT INTO experiment_data_points ({", ".join(point_columns)})
                        VALUES ({", ".join(point_placeholders)})
                    """
                    
                    cursor.execute(point_query, point_values)
            
            return experiment_id
            
        return self.execute_transaction(transaction_callback)

    @log_execution_time
    def add_data_point(self, data_point):
        """
        添加实验数据点
        
        参数:
            data_point: 数据点字典，必须包含experiment_id和measurement_type
            
        返回:
            新添加的数据点ID
        """
        if 'measurement_time' not in data_point:
            data_point['measurement_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
        return self.data_points_dao.insert(data_point)

    @log_execution_time
    def get_by_inspector(self, inspector_id, limit=100, offset=0):
        """
        获取指定药检员的实验记录
        
        参数:
            inspector_id: 药检员ID
            limit: 限制返回的记录数
            offset: 跳过的记录数
            
        返回:
            实验记录列表
        """
        return self.find_by({'inspector_id': inspector_id}, limit, offset, order_by="experiment_date DESC")

    @log_execution_time
    def get_by_item(self, item_id, limit=100, offset=0):
        """
        获取指定药典条目的实验记录
        
        参数:
            item_id: 药典条目ID
            limit: 限制返回的记录数
            offset: 跳过的记录数
            
        返回:
            实验记录列表
        """
        return self.find_by({'item_id': item_id}, limit, offset, order_by="experiment_date DESC")

    @log_execution_time
    def find_by_date_range(self, start_date, end_date, inspector_id=None, lab_id=None, limit=100, offset=0):
        """
        按日期范围查询实验记录
        
        参数:
            start_date: 开始日期（'YYYY-MM-DD'格式）
            end_date: 结束日期（'YYYY-MM-DD'格式）
            inspector_id: 可选的药检员ID筛选
            lab_id: 可选的实验室ID筛选
            limit: 限制返回的记录数
            offset: 跳过的记录数
            
        返回:
            匹配的实验记录列表
        """
        params = [start_date, end_date]
        where_clauses = ["experiment_date BETWEEN %s AND %s"]
        
        if inspector_id:
            where_clauses.append("inspector_id = %s")
            params.append(inspector_id)
            
        if lab_id:
            where_clauses.append("lab_id = %s")
            params.append(lab_id)
            
        params.extend([limit, offset])
        
        query = f"""
            SELECT * FROM experiment_records
            WHERE {' AND '.join(where_clauses)}
            ORDER BY experiment_date DESC
            LIMIT %s OFFSET %s
        """
        
        return self.execute_query(query, params)

    @log_execution_time
    def find_by_status(self, status, limit=50, offset=0):
        """
        按状态查询实验记录
        
        参数:
            status: 实验状态（'进行中'/'已完成'/'异常'）
            limit: 限制返回的记录数
            offset: 跳过的记录数
            
        返回:
            匹配的实验记录列表
        """
        return self.find_by({'status': status}, limit, offset, order_by="experiment_date DESC")

    @log_execution_time
    def update_experiment_status(self, experiment_id, status, result=None, conclusion=None):
        """
        更新实验状态和结果
        
        参数:
            experiment_id: 实验ID
            status: 新状态
            result: 可选的结果
            conclusion: 可选的结论
            
        返回:
            更新成功返回True，否则返回False
        """
        update_data = {'status': status}
        
        if result:
            update_data['result'] = result
            
        if conclusion:
            update_data['conclusion'] = conclusion
            
        if status == '已完成' and 'end_time' not in update_data:
            update_data['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
        return self.update(experiment_id, update_data)

    @log_execution_time
    def get_experiment_data_points(self, experiment_id):
        """
        获取实验的所有数据点
        
        参数:
            experiment_id: 实验ID
            
        返回:
            数据点记录列表
        """
        return self.data_points_dao.find_by({'experiment_id': experiment_id}, order_by="measurement_time ASC")

    @log_execution_time
    def get_experiment_with_details(self, experiment_id):
        """
        获取实验详情（含药检员、实验室、药典条目信息）
        
        参数:
            experiment_id: 实验ID
            
        返回:
            包含详细信息的实验记录字典
        """
        query = """
            SELECT e.*, i.name as inspector_name, i.employee_no, 
                   l.lab_name, l.lab_code, 
                   p.name_cn as item_name, p.name_pinyin, p.category
            FROM experiment_records e
            JOIN inspectors i ON e.inspector_id = i.inspector_id
            JOIN laboratories l ON e.lab_id = l.lab_id
            JOIN pharmacopoeia_items p ON e.item_id = p.item_id
            WHERE e.experiment_id = %s
        """
        
        result = self.execute_query(query, [experiment_id])
        if not result:
            return None
            
        experiment = result[0]
        
        # 获取数据点
        experiment['data_points'] = self.get_experiment_data_points(experiment_id)
        
        return experiment


class DataPointsDAO(BaseDAO):
    """实验数据点数据访问对象类"""

    def __init__(self, connection_pool):
        """初始化数据点DAO"""
        super().__init__(connection_pool, 'experiment_data_points', 'data_id')
