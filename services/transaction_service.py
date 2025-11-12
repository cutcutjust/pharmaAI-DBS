"""
事务服务模块(Transaction Service)

本模块提供数据库事务支持，用于确保复杂的数据操作的原子性，
满足课程对事务支持的要求，特别适用于需要保证数据一致性的场景，
如批量创建实验记录及其数据点、批量消息处理等。

使用方法:
    from services.transaction_service import TransactionService
    from database.connection import get_connection_pool
    
    # 创建事务服务实例
    pool = get_connection_pool()
    transaction_service = TransactionService(pool)
    
    # 示例1：在事务中创建实验记录和多个数据点
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
    
    success, result = transaction_service.create_experiment_with_data_points(experiment_data)
    if success:
        print(f"实验创建成功，ID：{result}")
    else:
        print(f"实验创建失败：{result}")
    
    # 示例2：批量处理对话消息
    messages_data = [
        {
            'conversation_id': 1,
            'message_seq': 1,
            'sender_type': 'inspector',
            'message_text': '请查询人参的功效'
        },
        {
            'conversation_id': 1,
            'message_seq': 2,
            'sender_type': 'system',
            'message_text': '人参具有补气固脱，益脾养胃，安神益智的功效。',
            'referenced_item_id': 100
        }
    ]
    
    success, result = transaction_service.batch_process_messages(messages_data, conversation_id=1)
    
    # 示例3：自定义事务操作
    def my_transaction_operations(cursor):
        # 执行多条SQL语句
        cursor.execute("INSERT INTO laboratories (lab_code, lab_name) VALUES (%s, %s)", 
                     ("LAB001", "中心实验室"))
        cursor.execute("INSERT INTO inspector_lab_access (inspector_id, lab_id) VALUES (%s, %s)",
                     (1, cursor.lastrowid))
        # 返回结果
        return cursor.lastrowid
    
    success, result = transaction_service.execute_in_transaction(my_transaction_operations)

主要功能:
    - TransactionService: 事务服务类
        - __init__(connection_pool): 
            初始化事务服务，接收数据库连接池
            
        - create_experiment_with_data_points(data): 
            在事务中创建实验记录及其数据点，保证原子性
            
        - batch_process_messages(messages, conversation_id): 
            在事务中批量处理对话消息
            
        - update_conversation_with_messages(conversation_data, messages): 
            在事务中更新对话会话及其消息
            
        - transfer_lab_access(from_inspector_id, to_inspector_id, lab_ids): 
            在事务中转移实验室访问权限
            
        - execute_in_transaction(operation_callback): 
            执行自定义事务操作回调函数
            
        - _begin_transaction(connection): 
            开始事务（内部方法）
            
        - _commit_transaction(connection): 
            提交事务（内部方法）
            
        - _rollback_transaction(connection): 
            回滚事务（内部方法）
"""

import logging
from contextlib import contextmanager
from typing import Callable, List, Dict, Tuple, Any, Optional, Union
from mysql.connector.pooling import MySQLConnectionPool
from mysql.connector import Error

from dao.experiment_dao import ExperimentDAO
from dao.message_dao import MessageDAO
from dao.conversation_dao import ConversationDAO
from dao.inspector_dao import InspectorDAO
from utils.logger import get_logger

logger = get_logger(__name__)

class TransactionService:
    """
    事务服务类，提供数据库事务支持，用于确保复杂的数据操作的原子性
    """
    
    def __init__(self, connection_pool: MySQLConnectionPool):
        """
        初始化事务服务
        
        Args:
            connection_pool: 数据库连接池
        """
        self.connection_pool = connection_pool
        self.experiment_dao = ExperimentDAO(connection_pool)
        self.message_dao = MessageDAO(connection_pool)
        self.conversation_dao = ConversationDAO(connection_pool)
        self.inspector_dao = InspectorDAO(connection_pool)
    
    @contextmanager
    def transaction(self):
        """
        事务上下文管理器
        
        Yields:
            connection: 数据库连接对象，已开启事务
        """
        connection = self.connection_pool.get_connection()
        try:
            self._begin_transaction(connection)
            yield connection
            self._commit_transaction(connection)
        except Exception as e:
            self._rollback_transaction(connection)
            logger.error(f"事务执行失败: {str(e)}")
            raise
        finally:
            connection.close()
    
    def execute_in_transaction(self, operation_callback: Callable) -> Tuple[bool, Any]:
        """
        在事务中执行自定义操作
        
        Args:
            operation_callback: 回调函数，接受cursor参数，返回操作结果
            
        Returns:
            Tuple[bool, Any]: (是否成功, 操作结果或错误信息)
        """
        connection = self.connection_pool.get_connection()
        try:
            self._begin_transaction(connection)
            cursor = connection.cursor(dictionary=True)
            result = operation_callback(cursor)
            self._commit_transaction(connection)
            return True, result
        except Exception as e:
            self._rollback_transaction(connection)
            logger.error(f"事务执行失败: {str(e)}")
            return False, str(e)
        finally:
            connection.close()
    
    def create_experiment_with_data_points(self, data: Dict) -> Tuple[bool, Union[int, str]]:
        """
        在事务中创建实验记录及其数据点
        
        Args:
            data: 包含experiment和data_points的字典
            
        Returns:
            Tuple[bool, Union[int, str]]: (是否成功, 实验ID或错误信息)
        """
        def operation(cursor):
            # 创建实验记录
            experiment_data = data['experiment']
            cursor.execute("""
                INSERT INTO experiment_records (
                    experiment_no, inspector_id, lab_id, item_id, 
                    experiment_type, batch_no, experiment_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                experiment_data['experiment_no'],
                experiment_data['inspector_id'],
                experiment_data['lab_id'],
                experiment_data['item_id'],
                experiment_data['experiment_type'],
                experiment_data['batch_no'],
                experiment_data['experiment_date']
            ))
            experiment_id = cursor.lastrowid
            
            # 创建数据点
            for point in data['data_points']:
                cursor.execute("""
                    INSERT INTO experiment_data_points (
                        experiment_id, measurement_type, measurement_value,
                        measurement_unit, standard_min, standard_max, is_qualified
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    experiment_id,
                    point['measurement_type'],
                    point['measurement_value'],
                    point['measurement_unit'],
                    point['standard_min'],
                    point['standard_max'],
                    point['is_qualified']
                ))
            
            return experiment_id
        
        return self.execute_in_transaction(operation)
    
    def batch_process_messages(self, messages: List[Dict], conversation_id: int) -> Tuple[bool, Union[List[int], str]]:
        """
        在事务中批量处理对话消息
        
        Args:
            messages: 消息列表
            conversation_id: 对话ID
            
        Returns:
            Tuple[bool, Union[List[int], str]]: (是否成功, 消息ID列表或错误信息)
        """
        def operation(cursor):
            message_ids = []
            
            # 验证会话存在
            cursor.execute("SELECT id FROM conversations WHERE id = %s", (conversation_id,))
            if not cursor.fetchone():
                raise ValueError(f"会话ID {conversation_id} 不存在")
            
            # 批量插入消息
            for message in messages:
                cursor.execute("""
                    INSERT INTO messages (
                        conversation_id, message_seq, sender_type, message_text, 
                        referenced_item_id, created_at
                    ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    message['conversation_id'],
                    message['message_seq'],
                    message['sender_type'],
                    message['message_text'],
                    message.get('referenced_item_id')  # 可选字段
                ))
                message_ids.append(cursor.lastrowid)
            
            # 更新会话的消息计数
            cursor.execute("""
                UPDATE conversations 
                SET total_messages = (
                    SELECT COUNT(*) FROM messages WHERE conversation_id = %s
                ),
                last_message_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (conversation_id, conversation_id))
            
            return message_ids
        
        return self.execute_in_transaction(operation)
    
    def update_conversation_with_messages(self, conversation_data: Dict, messages: List[Dict]) -> Tuple[bool, Union[Dict, str]]:
        """
        在事务中更新对话会话及其消息
        
        Args:
            conversation_data: 对话会话数据
            messages: 消息列表
            
        Returns:
            Tuple[bool, Union[Dict, str]]: (是否成功, 更新结果或错误信息)
        """
        def operation(cursor):
            # 更新对话会话
            cursor.execute("""
                UPDATE conversations
                SET context_topic = %s, last_message_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (
                conversation_data['context_topic'],
                conversation_data['id']
            ))
            
            # 批量插入或更新消息
            message_ids = []
            for message in messages:
                if 'id' in message and message['id']:  # 更新现有消息
                    cursor.execute("""
                        UPDATE messages
                        SET message_text = %s, referenced_item_id = %s
                        WHERE id = %s AND conversation_id = %s
                    """, (
                        message['message_text'],
                        message.get('referenced_item_id'),
                        message['id'],
                        conversation_data['id']
                    ))
                    message_ids.append(message['id'])
                else:  # 插入新消息
                    cursor.execute("""
                        INSERT INTO messages (
                            conversation_id, message_seq, sender_type, message_text, 
                            referenced_item_id, created_at
                        ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """, (
                        conversation_data['id'],
                        message['message_seq'],
                        message['sender_type'],
                        message['message_text'],
                        message.get('referenced_item_id')
                    ))
                    message_ids.append(cursor.lastrowid)
            
            # 更新会话的消息计数
            cursor.execute("""
                UPDATE conversations 
                SET total_messages = (
                    SELECT COUNT(*) FROM messages WHERE conversation_id = %s
                )
                WHERE id = %s
            """, (conversation_data['id'], conversation_data['id']))
            
            return {
                'conversation_id': conversation_data['id'],
                'message_ids': message_ids
            }
        
        return self.execute_in_transaction(operation)
    
    def transfer_lab_access(self, from_inspector_id: int, to_inspector_id: int, lab_ids: List[int]) -> Tuple[bool, Union[Dict, str]]:
        """
        在事务中转移实验室访问权限
        
        Args:
            from_inspector_id: 源药检员ID
            to_inspector_id: 目标药检员ID
            lab_ids: 实验室ID列表
            
        Returns:
            Tuple[bool, Union[Dict, str]]: (是否成功, 转移结果或错误信息)
        """
        def operation(cursor):
            # 验证药检员存在
            cursor.execute("SELECT id FROM inspectors WHERE id IN (%s, %s)", (from_inspector_id, to_inspector_id))
            inspectors = cursor.fetchall()
            if len(inspectors) != 2:
                raise ValueError("药检员ID不存在")
            
            # 验证实验室存在
            placeholders = ", ".join(["%s"] * len(lab_ids))
            cursor.execute(f"SELECT id FROM laboratories WHERE id IN ({placeholders})", tuple(lab_ids))
            labs = cursor.fetchall()
            if len(labs) != len(lab_ids):
                raise ValueError("部分实验室ID不存在")
            
            # 验证源药检员拥有这些权限
            cursor.execute(f"""
                SELECT lab_id FROM inspector_lab_access 
                WHERE inspector_id = %s AND lab_id IN ({placeholders})
            """, (from_inspector_id, *lab_ids))
            existing_access = [row['lab_id'] for row in cursor.fetchall()]
            if len(existing_access) != len(lab_ids):
                missing = set(lab_ids) - set(existing_access)
                raise ValueError(f"源药检员没有以下实验室的访问权限: {missing}")
            
            # 删除目标药检员可能已有的重复权限
            cursor.execute(f"""
                DELETE FROM inspector_lab_access 
                WHERE inspector_id = %s AND lab_id IN ({placeholders})
            """, (to_inspector_id, *lab_ids))
            
            # 转移权限
            for lab_id in lab_ids:
                cursor.execute("""
                    INSERT INTO inspector_lab_access (inspector_id, lab_id)
                    VALUES (%s, %s)
                """, (to_inspector_id, lab_id))
            
            # 删除源药检员的权限
            cursor.execute(f"""
                DELETE FROM inspector_lab_access 
                WHERE inspector_id = %s AND lab_id IN ({placeholders})
            """, (from_inspector_id, *lab_ids))
            
            return {
                'from_inspector_id': from_inspector_id,
                'to_inspector_id': to_inspector_id,
                'transferred_lab_ids': lab_ids
            }
        
        return self.execute_in_transaction(operation)
    
    def _begin_transaction(self, connection) -> None:
        """
        开始事务
        
        Args:
            connection: 数据库连接
        """
        connection.start_transaction()
    
    def _commit_transaction(self, connection) -> None:
        """
        提交事务
        
        Args:
            connection: 数据库连接
        """
        connection.commit()
    
    def _rollback_transaction(self, connection) -> None:
        """
        回滚事务
        
        Args:
            connection: 数据库连接
        """
        connection.rollback()