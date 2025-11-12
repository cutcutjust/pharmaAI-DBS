"""
复杂查询服务模块(Query Service)

本模块提供跨表JOIN查询功能，用于执行涉及多表关联的复杂查询操作，
满足课程对跨数据库表操作的要求，支持对话历史和实验数据的复杂查询场景。

使用方法:
    from services.query_service import QueryService
    from database.connection import get_connection_pool
    
    # 创建查询服务实例
    pool = get_connection_pool()
    query_service = QueryService(pool)
    
    # 示例1：查询药检员的对话历史及关联的药典条目（3表JOIN）
    conversations = query_service.get_inspector_conversations_with_items(
        inspector_id=1, 
        start_date='2025-01-01',
        end_date='2025-01-31'
    )
    
    for conv in conversations:
        print(f"会话ID: {conv['conversation_id']}")
        print(f"主题: {conv['context_topic']}")
        print(f"消息数: {conv['total_messages']}")
        print(f"关联药品: {conv['referenced_items']}")
    
    # 示例2：获取实验记录详情（包含药检员、实验室和药典条目信息）
    experiment_details = query_service.get_experiment_with_details(experiment_id=123)
    print(f"实验编号: {experiment_details['experiment_no']}")
    print(f"药检员: {experiment_details['inspector_name']}")
    print(f"实验室: {experiment_details['lab_name']}")
    print(f"检测药品: {experiment_details['item_name']}")
    
    # 示例3：统计各实验室的实验完成情况（多表JOIN+聚合）
    lab_stats = query_service.get_laboratory_experiment_stats()
    for stat in lab_stats:
        print(f"实验室: {stat['lab_name']}")
        print(f"实验总数: {stat['total_experiments']}")
        print(f"合格率: {stat['pass_rate']}%")
    
    # 示例4：搜索消息内容（全文搜索）
    messages = query_service.search_messages_by_content("二甲双胍", limit=10)
    for msg in messages:
        print(f"消息ID: {msg['message_id']}")
        print(f"内容: {msg['message_text']}")
        print(f"发送者: {msg['sender_type']}")

主要功能:
    - QueryService: 复杂查询服务类
        - __init__(connection_pool): 
            初始化查询服务，接收数据库连接池
            
        - get_inspector_conversations_with_items(inspector_id, start_date=None, end_date=None): 
            获取药检员的对话会话及关联的药典条目信息（JOIN conversations, messages, pharmacopoeia_items）
            
        - get_experiment_with_details(experiment_id): 
            获取实验记录详情，包含药检员、实验室和药典条目信息
            （JOIN experiment_records, inspectors, laboratories, pharmacopoeia_items）
            
        - get_laboratory_experiment_stats(): 
            获取各实验室的实验统计信息，包括实验总数、合格率等
            （JOIN laboratories, experiment_records + GROUP BY）
            
        - search_messages_by_content(search_text, limit=100): 
            根据内容关键词搜索消息记录
            （JOIN messages, conversations, inspectors）
            
        - get_inspector_experiment_history(inspector_id): 
            获取药检员的实验历史记录
            （JOIN experiment_records, pharmacopoeia_items, experiment_data_points）
            
        - get_item_experiments_summary(item_id): 
            获取指定药典条目的实验情况汇总
            （JOIN experiment_records, experiment_data_points + GROUP BY）
            
        - execute_custom_query(query, params=None): 
            执行自定义复杂查询（高级用法）
"""

from typing import List, Dict, Any, Optional, Union
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor

from utils.logger import get_logger

logger = get_logger(__name__)

class QueryService:
    """
    复杂查询服务类，提供跨表JOIN查询功能
    """
    
    def __init__(self, connection_pool: ThreadedConnectionPool):
        """
        初始化查询服务
        
        Args:
            connection_pool: 数据库连接池（PostgreSQL）
        """
        self.connection_pool = connection_pool
    
    def execute_query(self, query: str, params: Optional[Union[tuple, dict]] = None) -> List[Dict[str, Any]]:
        """
        执行SQL查询
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            List[Dict[str, Any]]: 查询结果列表
        """
        connection = self.connection_pool.getconn()
        try:
            cursor = connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"执行查询失败: {str(e)}")
            logger.error(f"查询语句: {query}")
            logger.error(f"查询参数: {params}")
            raise
        finally:
            self.connection_pool.putconn(connection)
    
    def get_inspector_conversations_with_items(
        self, inspector_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取药检员的对话会话及关联的药典条目信息
        
        Args:
            inspector_id: 药检员ID
            start_date: 开始日期，格式为YYYY-MM-DD
            end_date: 结束日期，格式为YYYY-MM-DD
            
        Returns:
            List[Dict[str, Any]]: 会话记录列表
        """
        query = """
            SELECT 
                c.conversation_id,
                c.context_topic,
                c.start_time as created_at,
                c.end_time as last_message_at,
                c.total_messages,
                i.name AS inspector_name,
                STRING_AGG(DISTINCT pi.name_cn, ', ') AS referenced_items,
                STRING_AGG(DISTINCT CAST(pi.item_id AS TEXT), ',') AS item_ids
            FROM conversations c
            JOIN inspectors i ON c.inspector_id = i.inspector_id
            LEFT JOIN messages m ON c.conversation_id = m.conversation_id
            LEFT JOIN pharmacopoeia_items pi ON m.referenced_item_id = pi.item_id
            WHERE c.inspector_id = %s
        """
        
        params = [inspector_id]
        
        if start_date:
            query += " AND c.created_at >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND c.created_at <= %s"
            params.append(end_date)
        
        query += " GROUP BY c.conversation_id, c.context_topic, c.start_time, c.end_time, c.total_messages, i.name ORDER BY c.end_time DESC"
        
        result = self.execute_query(query, tuple(params))
        
        # 处理空结果
        for row in result:
            if row['item_ids'] is None:
                row['item_ids'] = []
            else:
                row['item_ids'] = [int(id_) for id_ in row['item_ids'].split(',')]
                
            if row['referenced_items'] is None:
                row['referenced_items'] = ''
        
        return result
    
    def get_experiment_with_details(self, experiment_id: int) -> Dict[str, Any]:
        """
        获取实验记录详情，包含药检员、实验室和药典条目信息
        
        Args:
            experiment_id: 实验记录ID
            
        Returns:
            Dict[str, Any]: 实验详情
        """
        query = """
            SELECT 
                er.experiment_id,
                er.experiment_no,
                er.experiment_type,
                er.batch_no,
                er.experiment_date,
                er.created_at,
                er.status,
                i.inspector_id,
                i.name AS inspector_name,
                i.title AS inspector_title,
                l.lab_id,
                l.lab_code,
                l.lab_name,
                l.location as lab_location,
                pi.item_id,
                pi.name_cn AS item_name,
                pi.volume as standard_code,
                pi.category
            FROM experiment_records er
            JOIN inspectors i ON er.inspector_id = i.inspector_id
            JOIN laboratories l ON er.lab_id = l.lab_id
            JOIN pharmacopoeia_items pi ON er.item_id = pi.item_id
            WHERE er.experiment_id = %s
        """
        
        result = self.execute_query(query, (experiment_id,))
        
        if not result:
            return {}
        
        experiment_details = result[0]
        
        # 获取实验数据点
        data_points_query = """
            SELECT 
                data_id AS data_point_id,
                measurement_type,
                measurement_value,
                measurement_unit,
                standard_min,
                standard_max,
                is_qualified
            FROM experiment_data_points
            WHERE experiment_id = %s
            ORDER BY data_id
        """
        
        data_points = self.execute_query(data_points_query, (experiment_id,))
        experiment_details['data_points'] = data_points
        
        # 计算实验合格率
        qualified_count = sum(1 for point in data_points if point['is_qualified'])
        if data_points:
            experiment_details['qualification_rate'] = (qualified_count / len(data_points)) * 100
        else:
            experiment_details['qualification_rate'] = 0
        
        return experiment_details
    
    def get_laboratory_experiment_stats(self) -> List[Dict[str, Any]]:
        """
        获取各实验室的实验统计信息，包括实验总数、合格率等
        
        Returns:
            List[Dict[str, Any]]: 实验室统计信息列表
        """
        query = """
            SELECT 
                l.lab_id,
                l.lab_name,
                l.lab_code,
                COUNT(er.experiment_id) AS total_experiments,
                SUM(CASE WHEN er.status = 'completed' THEN 1 ELSE 0 END) AS completed_experiments,
                AVG(
                    (SELECT 
                        COUNT(edp.data_id) * 100.0 / NULLIF(
                            (SELECT COUNT(*) FROM experiment_data_points WHERE experiment_id = er.experiment_id), 
                            0
                        )
                    FROM experiment_data_points edp 
                    WHERE edp.experiment_id = er.experiment_id AND edp.is_qualified = TRUE)
                ) AS avg_qualification_rate
            FROM laboratories l
            LEFT JOIN experiment_records er ON l.lab_id = er.lab_id
            GROUP BY l.lab_id, l.lab_name, l.lab_code
            ORDER BY total_experiments DESC
        """
        
        result = self.execute_query(query)
        
        # 处理数据
        for row in result:
            # 计算实验合格率
            if row['avg_qualification_rate'] is None:
                row['pass_rate'] = 0
            else:
                row['pass_rate'] = round(row['avg_qualification_rate'], 2)
            
            # 计算实验完成率
            if row['total_experiments'] > 0:
                row['completion_rate'] = round((row['completed_experiments'] / row['total_experiments']) * 100, 2)
            else:
                row['completion_rate'] = 0
        
        return result
    
    def search_messages_by_content(self, search_text: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        根据内容关键词搜索消息记录
        
        Args:
            search_text: 搜索关键词
            limit: 结果数量限制
            
        Returns:
            List[Dict[str, Any]]: 消息记录列表
        """
        query = """
            SELECT 
                m.message_id,
                m.conversation_id,
                m.message_seq,
                m.sender_type,
                m.message_text,
                m.timestamp as created_at,
                m.referenced_item_id,
                c.context_topic AS conversation_topic,
                i.name AS inspector_name,
                pi.name_cn AS referenced_item_name
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.conversation_id
            JOIN inspectors i ON c.inspector_id = i.inspector_id
            LEFT JOIN pharmacopoeia_items pi ON m.referenced_item_id = pi.item_id
            WHERE m.message_text LIKE %s
            ORDER BY m.timestamp DESC
            LIMIT %s
        """
        
        search_pattern = f"%{search_text}%"
        result = self.execute_query(query, (search_pattern, limit))
        
        return result
    
    def get_inspector_experiment_history(self, inspector_id: int) -> List[Dict[str, Any]]:
        """
        获取药检员的实验历史记录
        
        Args:
            inspector_id: 药检员ID
            
        Returns:
            List[Dict[str, Any]]: 实验历史记录列表
        """
        query = """
            SELECT 
                er.experiment_id,
                er.experiment_no,
                er.experiment_type,
                er.batch_no,
                er.experiment_date,
                er.status,
                pi.item_id,
                pi.name_cn AS item_name,
                l.lab_name,
                (
                    SELECT COUNT(*) FROM experiment_data_points edp 
                    WHERE edp.experiment_id = er.experiment_id AND edp.is_qualified = TRUE
                ) AS qualified_points_count,
                (
                    SELECT COUNT(*) FROM experiment_data_points edp 
                    WHERE edp.experiment_id = er.experiment_id
                ) AS total_points_count
            FROM experiment_records er
            JOIN pharmacopoeia_items pi ON er.item_id = pi.item_id
            JOIN laboratories l ON er.lab_id = l.lab_id
            WHERE er.inspector_id = %s
            ORDER BY er.experiment_date DESC
        """
        
        result = self.execute_query(query, (inspector_id,))
        
        # 计算实验合格率
        for row in result:
            if row['total_points_count'] > 0:
                row['qualification_rate'] = round((row['qualified_points_count'] / row['total_points_count']) * 100, 2)
            else:
                row['qualification_rate'] = 0
        
        return result
    
    def get_item_experiments_summary(self, item_id: int) -> Dict[str, Any]:
        """
        获取指定药典条目的实验情况汇总
        
        Args:
            item_id: 药典条目ID
            
        Returns:
            Dict[str, Any]: 实验情况汇总
        """
        # 获取药典条目信息
        item_query = """
            SELECT 
                item_id, 
                name_cn, 
                name_en, 
                volume as standard_code, 
                category
            FROM pharmacopoeia_items
            WHERE item_id = %s
        """
        
        item_result = self.execute_query(item_query, (item_id,))
        if not item_result:
            return {}
        
        summary = item_result[0]
        
        # 获取实验统计信息
        stats_query = """
            SELECT 
                COUNT(er.experiment_id) AS total_experiments,
                SUM(CASE WHEN er.status = 'completed' THEN 1 ELSE 0 END) AS completed_experiments,
                COUNT(DISTINCT er.inspector_id) AS inspector_count,
                COUNT(DISTINCT er.lab_id) AS lab_count,
                MIN(er.experiment_date) AS first_experiment_date,
                MAX(er.experiment_date) AS last_experiment_date
            FROM experiment_records er
            WHERE er.item_id = %s
        """
        
        stats_result = self.execute_query(stats_query, (item_id,))
        if stats_result:
            summary.update(stats_result[0])
        
        # 获取测量类型统计
        measurements_query = """
            SELECT 
                edp.measurement_type,
                COUNT(edp.data_id) AS measurement_count,
                AVG(edp.measurement_value) AS average_value,
                MIN(edp.measurement_value) AS min_value,
                MAX(edp.measurement_value) AS max_value,
                SUM(CASE WHEN edp.is_qualified THEN 1 ELSE 0 END) AS qualified_count
            FROM experiment_data_points edp
            JOIN experiment_records er ON edp.experiment_id = er.experiment_id
            WHERE er.item_id = %s
            GROUP BY edp.measurement_type
        """
        
        measurements_result = self.execute_query(measurements_query, (item_id,))
        
        # 计算各测量类型合格率
        for row in measurements_result:
            if row['measurement_count'] > 0:
                row['qualification_rate'] = round((row['qualified_count'] / row['measurement_count']) * 100, 2)
            else:
                row['qualification_rate'] = 0
        
        summary['measurements'] = measurements_result
        
        # 获取最近实验记录
        recent_experiments_query = """
            SELECT 
                er.experiment_id,
                er.experiment_no,
                er.experiment_date,
                er.status,
                i.name AS inspector_name,
                l.lab_name
            FROM experiment_records er
            JOIN inspectors i ON er.inspector_id = i.inspector_id
            JOIN laboratories l ON er.lab_id = l.lab_id
            WHERE er.item_id = %s
            ORDER BY er.experiment_date DESC
            LIMIT 5
        """
        
        recent_experiments = self.execute_query(recent_experiments_query, (item_id,))
        summary['recent_experiments'] = recent_experiments
        
        return summary
    
    def search_conversations(
        self, 
        query_params: Dict[str, Any], 
        page: int = 1, 
        per_page: int = 10
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        搜索对话会话记录
        
        Args:
            query_params: 查询参数字典，可包含 inspector_id, start_date, end_date, keywords
            page: 页码（从1开始）
            per_page: 每页记录数
            
        Returns:
            tuple: (对话列表, 总记录数)
        """
        # 构建查询条件
        where_conditions = []
        params = []
        
        if query_params.get('inspector_id'):
            where_conditions.append("c.inspector_id = %s")
            params.append(query_params['inspector_id'])
        
        if query_params.get('start_date'):
            where_conditions.append("DATE(c.start_time) >= %s")
            params.append(query_params['start_date'])
        
        if query_params.get('end_date'):
            # 包含结束日期的整天（到23:59:59）
            where_conditions.append("DATE(c.start_time) <= %s")
            params.append(query_params['end_date'])
        
        # 根据是否有关键词来决定是否需要JOIN messages表
        has_keywords = bool(query_params.get('keywords'))
        
        if has_keywords:
            where_conditions.append(
                "(c.context_topic LIKE %s OR m.message_text LIKE %s)"
            )
            keyword_pattern = f"%{query_params['keywords']}%"
            params.extend([keyword_pattern, keyword_pattern])
        
        # 构建WHERE子句
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # 获取总记录数 - 如果有关键词才JOIN messages表
        if has_keywords:
            count_query = f"""
                SELECT COUNT(DISTINCT c.conversation_id) as total
                FROM conversations c
                JOIN inspectors i ON c.inspector_id = i.inspector_id
                LEFT JOIN messages m ON c.conversation_id = m.conversation_id
                WHERE {where_clause}
            """
        else:
            count_query = f"""
                SELECT COUNT(DISTINCT c.conversation_id) as total
                FROM conversations c
                JOIN inspectors i ON c.inspector_id = i.inspector_id
                WHERE {where_clause}
            """
        
        count_result = self.execute_query(count_query, tuple(params))
        total_count = count_result[0]['total'] if count_result else 0
        
        # 计算偏移量
        offset = (page - 1) * per_page
        
        # 获取分页数据 - 如果有关键词才JOIN messages表
        if has_keywords:
            data_query = f"""
                SELECT 
                    c.conversation_id as id,
                    c.context_topic,
                    c.start_time,
                    c.end_time,
                    c.total_messages as message_count,
                    i.inspector_id as inspector_id,
                    i.name as inspector_name,
                    STRING_AGG(DISTINCT pi.name_cn, ', ') as keywords
                FROM conversations c
                JOIN inspectors i ON c.inspector_id = i.inspector_id
                LEFT JOIN messages m ON c.conversation_id = m.conversation_id
                LEFT JOIN pharmacopoeia_items pi ON m.referenced_item_id = pi.item_id
                WHERE {where_clause}
                GROUP BY c.conversation_id, c.context_topic, c.start_time, c.end_time, c.total_messages, i.inspector_id, i.name
                ORDER BY c.start_time DESC NULLS LAST
                LIMIT %s OFFSET %s
            """
        else:
            data_query = f"""
                SELECT 
                    c.conversation_id as id,
                    c.context_topic,
                    c.start_time,
                    c.end_time,
                    c.total_messages as message_count,
                    i.inspector_id as inspector_id,
                    i.name as inspector_name,
                    c.context_topic as keywords
                FROM conversations c
                JOIN inspectors i ON c.inspector_id = i.inspector_id
                WHERE {where_clause}
                ORDER BY c.start_time DESC NULLS LAST
                LIMIT %s OFFSET %s
            """
        
        # 添加分页参数
        data_params = list(params) + [per_page, offset]
        conversations = self.execute_query(data_query, tuple(data_params))
        
        # 格式化日期时间
        for conv in conversations:
            if conv.get('start_time'):
                conv['start_time'] = str(conv['start_time'])
            if conv.get('end_time'):
                conv['end_time'] = str(conv['end_time'])
        
        return conversations, total_count
    
    def execute_custom_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        执行自定义复杂查询（高级用法）
        
        Args:
            query: SQL查询语句
            params: 查询参数元组
            
        Returns:
            List[Dict[str, Any]]: 查询结果列表
        """
        logger.warning(f"执行自定义查询: {query}")
        return self.execute_query(query, params)