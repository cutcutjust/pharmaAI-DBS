"""
对话消息数据访问对象(Message DAO)模块

本模块提供对messages表的数据访问功能，用于管理对话消息数据，是系统中最主要的数据源之一，预计有10万+条记录。

使用方法:
    from dao.message_dao import MessageDAO
    from database.connection import get_connection_pool
    
    # 创建DAO实例
    conn_pool = get_connection_pool()
    message_dao = MessageDAO(conn_pool)
    
    # 添加新消息
    message_id = message_dao.add_message({
        'conversation_id': 1,
        'message_seq': 1,
        'sender_type': 'inspector',
        'message_text': '请查询二甲双胍的含量测定方法',
        'intent': '查询药典方法',
        'confidence_score': 0.95
    })
    
    # 获取会话的所有消息
    messages = message_dao.get_by_conversation(conversation_id=1)
    
    # 按关键词搜索消息
    results = message_dao.search_by_text('二甲双胍')

主要功能:
    - MessageDAO: 对话消息数据访问对象类
        - add_message(): 添加新消息并返回ID
        - get_by_conversation(): 获取指定会话的所有消息
        - get_latest_messages(): 获取最近的消息列表
        - search_by_text(): 按消息内容关键词搜索
        - get_by_intent(): 按意图类型查询消息
        - get_message_with_reference(): 获取消息及关联的药典条目信息
        - get_message_stats(): 获取消息统计数据
        - batch_insert_messages(): 批量插入多条消息记录（提高性能）
"""

from .base_dao import BaseDAO
from utils.performance_logger import log_execution_time
from datetime import datetime


class MessageDAO(BaseDAO):
    """对话消息数据访问对象类"""

    def __init__(self, connection_pool):
        """初始化消息DAO"""
        super().__init__(connection_pool, 'messages', 'message_id')

    @log_execution_time
    def add_message(self, data):
        """
        添加新消息并返回ID
        
        参数:
            data: 消息数据字典，必须包含conversation_id、message_seq、sender_type和message_text
            
        返回:
            新添加消息的ID
        """
        # 确保有时间戳
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
        return self.insert(data)

    @log_execution_time
    def get_by_conversation(self, conversation_id, order_by_seq=True):
        """
        获取指定会话的所有消息
        
        参数:
            conversation_id: 会话ID
            order_by_seq: 是否按消息序号排序，默认为True
            
        返回:
            消息记录列表
        """
        order_by = "message_seq ASC" if order_by_seq else "timestamp ASC"
        return self.find_by({'conversation_id': conversation_id}, order_by=order_by)

    @log_execution_time
    def get_latest_messages(self, limit=100):
        """
        获取最近的消息列表
        
        参数:
            limit: 限制返回的记录数
            
        返回:
            最近的消息记录列表
        """
        return self.get_all(limit=limit, order_by="timestamp DESC")

    @log_execution_time
    def search_by_text(self, keyword, limit=50, offset=0):
        """
        按消息内容关键词搜索
        
        参数:
            keyword: 搜索关键词
            limit: 限制返回的记录数
            offset: 跳过的记录数
            
        返回:
            匹配的消息记录列表
        """
        query = """
            SELECT m.*, c.inspector_id, c.context_topic
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.conversation_id
            WHERE m.message_text LIKE %s
            ORDER BY m.timestamp DESC
            LIMIT %s OFFSET %s
        """
        return self.execute_query(query, [f"%{keyword}%", limit, offset])

    @log_execution_time
    def get_by_intent(self, intent, limit=50, offset=0):
        """
        按意图类型查询消息
        
        参数:
            intent: 意图类型
            limit: 限制返回的记录数
            offset: 跳过的记录数
            
        返回:
            匹配的消息记录列表
        """
        return self.find_by({'intent': intent}, limit, offset, order_by="timestamp DESC")

    @log_execution_time
    def get_message_with_reference(self, message_id):
        """
        获取消息及关联的药典条目信息
        
        参数:
            message_id: 消息ID
            
        返回:
            包含消息和关联药典条目信息的字典
        """
        query = """
            SELECT m.*, p.name_cn, p.name_pinyin, p.name_en, p.category
            FROM messages m
            LEFT JOIN pharmacopoeia_items p ON m.referenced_item_id = p.item_id
            WHERE m.message_id = %s
        """
        results = self.execute_query(query, [message_id])
        return results[0] if results else None

    @log_execution_time
    def get_message_stats(self, conversation_id=None, inspector_id=None):
        """
        获取消息统计数据
        
        参数:
            conversation_id: 可选的会话ID筛选
            inspector_id: 可选的药检员ID筛选
            
        返回:
            包含统计信息的字典
        """
        params = []
        joins = ["FROM messages m"]
        where_clauses = []
        
        if conversation_id:
            where_clauses.append("m.conversation_id = %s")
            params.append(conversation_id)
            
        if inspector_id:
            joins.append("JOIN conversations c ON m.conversation_id = c.conversation_id")
            where_clauses.append("c.inspector_id = %s")
            params.append(inspector_id)
            
        where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        query = f"""
            SELECT 
                COUNT(*) as total_messages,
                COUNT(CASE WHEN sender_type = 'inspector' THEN 1 END) as inspector_messages,
                COUNT(CASE WHEN sender_type = 'system' THEN 1 END) as system_messages,
                AVG(response_time_ms) as avg_response_time_ms,
                AVG(confidence_score) as avg_confidence_score,
                COUNT(DISTINCT conversation_id) as conversation_count
            {' '.join(joins)}
            {where_clause}
        """
        
        result = self.execute_query(query, params)
        return result[0] if result else None

    @log_execution_time
    def batch_insert_messages(self, messages_data):
        """
        批量插入多条消息记录（提高性能）
        
        参数:
            messages_data: 消息数据字典的列表
            
        返回:
            插入成功的记录数量
        """
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 确保所有消息都有时间戳
        for message in messages_data:
            if 'timestamp' not in message:
                message['timestamp'] = current_time
                
        return self.batch_insert(messages_data)
