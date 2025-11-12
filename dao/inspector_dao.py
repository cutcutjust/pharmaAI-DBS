"""
药检员数据访问对象(Inspector DAO)模块

本模块提供对inspectors表和inspector_lab_access表的数据访问功能，
用于管理药检员信息及其与实验室的访问权限关系(N-M关系)。

使用方法:
    from dao.inspector_dao import InspectorDAO
    from database.connection import get_connection_pool
    
    # 创建DAO实例
    conn_pool = get_connection_pool()
    inspector_dao = InspectorDAO(conn_pool)
    
    # 添加新药检员
    inspector_id = inspector_dao.add_inspector({
        'employee_no': 'YJ2025001',
        'name': '张三',
        'phone': '13800138000',
        'email': 'zhangsan@example.com',
        'department': '药品检测部',
        'title': '高级药师',
        'certification_level': 'A级'
    })
    
    # 授予实验室访问权限
    inspector_dao.grant_lab_access(inspector_id, lab_id=3, access_level='管理员')
    
    # 获取药检员详情
    inspector = inspector_dao.get_inspector_detail(inspector_id=1)
    
    # 获取药检员可访问的实验室
    labs = inspector_dao.get_accessible_labs(inspector_id=1)

主要功能:
    - InspectorDAO: 药检员数据访问对象类
        - add_inspector(): 添加新药检员
        - update_inspector(): 更新药检员信息
        - get_all_active_inspectors(): 获取所有在岗药检员
        - get_inspector_detail(): 获取药检员详情
        - find_by_department(): 按部门查询药检员
        - grant_lab_access(): 授予实验室访问权限
        - revoke_lab_access(): 撤销实验室访问权限
        - get_accessible_labs(): 获取药检员可访问的实验室列表
        - get_inspectors_by_lab(): 获取有权访问特定实验室的药检员
        - get_inspector_stats(): 获取药检员工作统计（对话数、实验数）
"""

from .base_dao import BaseDAO
from utils.performance_logger import log_execution_time
from datetime import datetime, date


class InspectorDAO(BaseDAO):
    """药检员数据访问对象类"""

    def __init__(self, connection_pool):
        """初始化药检员DAO"""
        super().__init__(connection_pool, 'inspectors', 'inspector_id')

    @log_execution_time
    def add_inspector(self, inspector_data):
        """
        添加新药检员
        
        参数:
            inspector_data: 药检员数据字典，必须包含employee_no和name
            
        返回:
            新添加药检员的ID
        """
        # 确保有入职日期
        if 'join_date' not in inspector_data:
            inspector_data['join_date'] = date.today().isoformat()
            
        # 默认在岗状态
        if 'is_active' not in inspector_data:
            inspector_data['is_active'] = True
            
        return self.insert(inspector_data)

    @log_execution_time
    def update_inspector(self, inspector_id, update_data):
        """
        更新药检员信息
        
        参数:
            inspector_id: 药检员ID
            update_data: 要更新的数据字典
            
        返回:
            更新成功返回True，否则返回False
        """
        return self.update(inspector_id, update_data)

    @log_execution_time
    def get_all_active_inspectors(self, limit=1000, offset=0):
        """
        获取所有在岗药检员
        
        参数:
            limit: 限制返回的记录数
            offset: 跳过的记录数
            
        返回:
            在岗药检员记录列表
        """
        return self.find_by({'is_active': True}, limit, offset, order_by="name ASC")

    @log_execution_time
    def get_inspector_detail(self, inspector_id):
        """
        获取药检员详情
        
        参数:
            inspector_id: 药检员ID
            
        返回:
            药检员详细信息字典，未找到则返回None
        """
        inspector = self.get_by_id(inspector_id)
        if not inspector:
            return None
            
        # 获取实验室访问权限
        query = """
            SELECT la.*, l.lab_name, l.lab_code
            FROM inspector_lab_access la
            JOIN laboratories l ON la.lab_id = l.lab_id
            WHERE la.inspector_id = %s
        """
        lab_access = self.execute_query(query, [inspector_id])
        
        # 添加到药检员信息中
        inspector['lab_access'] = lab_access
        
        # 获取统计信息
        stats = self.get_inspector_stats(inspector_id)
        if stats:
            inspector.update(stats)
            
        return inspector

    @log_execution_time
    def find_by_department(self, department, limit=100, offset=0):
        """
        按部门查询药检员
        
        参数:
            department: 部门名称
            limit: 限制返回的记录数
            offset: 跳过的记录数
            
        返回:
            匹配的药检员记录列表
        """
        return self.find_by({'department': department, 'is_active': True}, limit, offset, order_by="name ASC")

    @log_execution_time
    def grant_lab_access(self, inspector_id, lab_id, access_level='普通'):
        """
        授予实验室访问权限
        
        参数:
            inspector_id: 药检员ID
            lab_id: 实验室ID
            access_level: 访问权限级别，默认为'普通'
            
        返回:
            操作成功返回True，否则返回False
        """
        # 检查是否已存在权限记录
        query = """
            SELECT * FROM inspector_lab_access
            WHERE inspector_id = %s AND lab_id = %s
        """
        result = self.execute_query(query, [inspector_id, lab_id])
        
        if result:
            # 已存在，更新权限级别
            update_query = """
                UPDATE inspector_lab_access
                SET access_level = %s
                WHERE inspector_id = %s AND lab_id = %s
            """
            self.execute_query(update_query, [access_level, inspector_id, lab_id])
        else:
            # 不存在，创建新记录
            insert_query = """
                INSERT INTO inspector_lab_access (inspector_id, lab_id, access_level, granted_date)
                VALUES (%s, %s, %s, %s)
            """
            self.execute_query(insert_query, [inspector_id, lab_id, access_level, datetime.now().strftime('%Y-%m-%d')])
            
        return True

    @log_execution_time
    def revoke_lab_access(self, inspector_id, lab_id):
        """
        撤销实验室访问权限
        
        参数:
            inspector_id: 药检员ID
            lab_id: 实验室ID
            
        返回:
            操作成功返回True，否则返回False
        """
        query = """
            DELETE FROM inspector_lab_access
            WHERE inspector_id = %s AND lab_id = %s
        """
        result = self.execute_query(query, [inspector_id, lab_id])
        return result > 0

    @log_execution_time
    def get_accessible_labs(self, inspector_id):
        """
        获取药检员可访问的实验室列表
        
        参数:
            inspector_id: 药检员ID
            
        返回:
            实验室记录列表，每条包含访问权限级别
        """
        query = """
            SELECT l.*, la.access_level, la.granted_date
            FROM laboratories l
            JOIN inspector_lab_access la ON l.lab_id = la.lab_id
            WHERE la.inspector_id = %s
            ORDER BY l.lab_name
        """
        return self.execute_query(query, [inspector_id])

    @log_execution_time
    def get_inspectors_by_lab(self, lab_id, limit=100, offset=0):
        """
        获取有权访问特定实验室的药检员
        
        参数:
            lab_id: 实验室ID
            limit: 限制返回的记录数
            offset: 跳过的记录数
            
        返回:
            药检员记录列表，每条包含访问权限级别
        """
        query = """
            SELECT i.*, la.access_level, la.granted_date
            FROM inspectors i
            JOIN inspector_lab_access la ON i.inspector_id = la.inspector_id
            WHERE la.lab_id = %s AND i.is_active = TRUE
            ORDER BY i.name
            LIMIT %s OFFSET %s
        """
        return self.execute_query(query, [lab_id, limit, offset])

    @log_execution_time
    def get_inspector_stats(self, inspector_id):
        """
        获取药检员工作统计（对话数、实验数）
        
        参数:
            inspector_id: 药检员ID
            
        返回:
            包含统计信息的字典
        """
        # 获取对话统计
        conversation_query = """
            SELECT 
                COUNT(DISTINCT conversation_id) as conversation_count,
                SUM(total_messages) as total_messages,
                MAX(start_time) as last_conversation_time
            FROM conversations
            WHERE inspector_id = %s
        """
        conv_result = self.execute_query(conversation_query, [inspector_id])
        
        # 获取实验统计
        experiment_query = """
            SELECT 
                COUNT(*) as experiment_count,
                COUNT(CASE WHEN result = '合格' THEN 1 END) as passed_experiments,
                COUNT(CASE WHEN status = '进行中' THEN 1 END) as ongoing_experiments,
                MAX(experiment_date) as last_experiment_date
            FROM experiment_records
            WHERE inspector_id = %s
        """
        exp_result = self.execute_query(experiment_query, [inspector_id])
        
        stats = {}
        if conv_result and len(conv_result) > 0:
            stats.update(conv_result[0])
            
        if exp_result and len(exp_result) > 0:
            stats.update(exp_result[0])
            
        return stats
