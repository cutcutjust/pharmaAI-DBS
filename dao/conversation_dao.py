"""
对话会话数据访问对象(Conversation DAO)模块

本模块提供对conversations表的数据访问功能，用于管理药检员与系统的对话会话数据。

使用方法:
    from dao.conversation_dao import ConversationDAO
    from database.connection import get_connection_pool
    
    # 创建DAO实例
    conn_pool = get_connection_pool()
    conversation_dao = ConversationDAO(conn_pool)
    
    # 创建新会话
    conversation_id = conversation_dao.create_conversation({
        'inspector_id': 1,
        'session_id': 'sess_12345',
        'start_time': '2025-01-01 08:30:00',
        'session_type': '查询',
        'context_topic': '药品含量测定'
    })
    
    # 查询药检员的所有会话
    conversations = conversation_dao.get_by_inspector(inspector_id=1)
    
    # 更新会话结束时间和消息总数
    conversation_dao.update_session_end(conversation_id, '2025-01-01 09:15:00', 12)

主要功能:
    - ConversationDAO: 对话会话数据访问对象类
        - create_conversation(): 创建新的对话会话
        - get_by_inspector(): 获取指定药检员的所有会话
        - get_recent_conversations(): 获取最近的会话列表
        - find_by_topic(): 按主题关键词搜索会话
        - find_by_time_range(): 按时间范围查询会话
        - update_session_end(): 更新会话结束时间和消息总数
        - get_conversation_stats(): 获取会话统计信息
"""

from .base_dao import BaseDAO
from utils.performance_logger import log_execution_time
from datetime import datetime
import uuid


class ConversationDAO(BaseDAO):
    """对话会话数据访问对象类"""

    def __init__(self, connection_pool):
        """初始化对话会话DAO"""
        super().__init__(connection_pool, 'conversations', 'conversation_id')

    @log_execution_time
    def create_conversation(self, data):
        """
        创建新的对话会话
        
        参数:
            data: 会话数据字典，至少包含inspector_id和start_time
            
        返回:
            新创建的会话ID
        """
        # 确保有会话ID
        if 'session_id' not in data:
            data['session_id'] = f"sess_{uuid.uuid4().hex[:10]}"
            
        # 确保有开始时间
        if 'start_time' not in data:
            data['start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
        # 初始化消息数为0
        if 'total_messages' not in data:
            data['total_messages'] = 0
            
        return self.insert(data)

    @log_execution_time
    def get_by_inspector(self, inspector_id, limit=100, offset=0):
        """
        获取指定药检员的所有会话
        
        参数:
            inspector_id: 药检员ID
            limit: 限制返回的记录数
            offset: 跳过的记录数
            
        返回:
            会话记录列表
        """
        return self.find_by({'inspector_id': inspector_id}, limit, offset, order_by="start_time DESC")

    @log_execution_time
    def get_recent_conversations(self, limit=20):
        """
        获取最近的会话列表
        
        参数:
            limit: 限制返回的记录数
            
        返回:
            最近的会话记录列表
        """
        return self.get_all(limit=limit, order_by="start_time DESC")

    @log_execution_time
    def find_by_topic(self, keyword, limit=50, offset=0):
        """
        按主题关键词搜索会话
        
        参数:
            keyword: 主题关键词
            limit: 限制返回的记录数
            offset: 跳过的记录数
            
        返回:
            匹配的会话记录列表
        """
        query = """
            SELECT * FROM conversations
            WHERE context_topic LIKE %s
            ORDER BY start_time DESC
            LIMIT %s OFFSET %s
        """
        return self.execute_query(query, [f"%{keyword}%", limit, offset])

    @log_execution_time
    def find_by_time_range(self, start_date, end_date, inspector_id=None, limit=100, offset=0):
        """
        按时间范围查询会话
        
        参数:
            start_date: 开始日期（'YYYY-MM-DD'格式）
            end_date: 结束日期（'YYYY-MM-DD'格式）
            inspector_id: 可选的药检员ID筛选
            limit: 限制返回的记录数
            offset: 跳过的记录数
            
        返回:
            匹配的会话记录列表
        """
        if inspector_id:
            query = """
                SELECT * FROM conversations
                WHERE start_time BETWEEN %s AND %s
                AND inspector_id = %s
                ORDER BY start_time DESC
                LIMIT %s OFFSET %s
            """
            return self.execute_query(query, [start_date, end_date, inspector_id, limit, offset])
        else:
            query = """
                SELECT * FROM conversations
                WHERE start_time BETWEEN %s AND %s
                ORDER BY start_time DESC
                LIMIT %s OFFSET %s
            """
            return self.execute_query(query, [start_date, end_date, limit, offset])

    @log_execution_time
    def update_session_end(self, conversation_id, end_time, total_messages):
        """
        更新会话结束时间和消息总数
        
        参数:
            conversation_id: 会话ID
            end_time: 结束时间
            total_messages: 消息总数
            
        返回:
            更新成功返回True，否则返回False
        """
        update_data = {
            'end_time': end_time,
            'total_messages': total_messages
        }
        return self.update(conversation_id, update_data)

    @log_execution_time
    def get_conversation_stats(self, inspector_id=None, start_date=None, end_date=None):
        """
        获取会话统计信息
        
        参数:
            inspector_id: 可选的药检员ID筛选
            start_date: 可选的开始日期筛选
            end_date: 可选的结束日期筛选
            
        返回:
            包含统计信息的字典
        """
        params = []
        where_clauses = []
        
        if inspector_id:
            where_clauses.append("inspector_id = %s")
            params.append(inspector_id)
            
        if start_date:
            where_clauses.append("start_time >= %s")
            params.append(start_date)
            
        if end_date:
            where_clauses.append("end_time <= %s")
            params.append(end_date)
            
        where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        query = f"""
            SELECT 
                COUNT(*) as total_conversations,
                SUM(total_messages) as total_messages,
                AVG(total_messages) as avg_messages_per_conversation,
                MIN(start_time) as earliest_conversation,
                MAX(start_time) as latest_conversation,
                AVG(EXTRACT(EPOCH FROM (end_time - start_time))) as avg_duration_seconds
            FROM conversations
            {where_clause}
        """
        
        result = self.execute_query(query, params)
        return result[0] if result else None
