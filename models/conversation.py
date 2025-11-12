"""
对话会话模型模块(Conversation Model Module)

本模块提供对话会话相关的模型类，对应数据库中的conversations表，
用于表示药检员与系统之间的对话会话数据。

使用方法:
    from models.conversation import Conversation
    from datetime import datetime
    
    # 创建新的对话会话
    conversation = Conversation(
        inspector_id=1,
        session_id="sess_12345",
        start_time=datetime.now(),
        session_type="查询",
        context_topic="药品含量测定方法"
    )
    
    # 访问对话会话属性
    print(f"会话ID: {conversation.session_id}")
    print(f"开始时间: {conversation.start_time}")
    
    # 更新会话结束信息
    conversation.end_conversation(datetime.now(), 15)
    
    # 转换为字典用于数据库操作
    conversation_dict = conversation.to_dict()
    
    # 从数据库记录创建实例
    db_record = (1, 2, "sess_67890", "2025-01-15 10:30:00", 
                 "2025-01-15 10:45:00", 12, "咨询", "药品稳定性")
    conversation = Conversation.from_db_record(db_record)

主要功能:
    - Conversation: 对话会话模型类
        - __init__(inspector_id, session_id, start_time, session_type=None, 
                  context_topic=None, end_time=None, total_messages=0, id=None): 
            初始化会话对象
            
        - end_conversation(end_time, total_messages): 
            结束会话，设置结束时间和消息总数
            
        - get_duration(): 
            计算会话持续时间（分钟）
            
        - is_active(): 
            检查会话是否处于活动状态（未结束）
            
        - to_dict(): 
            将会话对象转换为字典
            
        - from_dict(data): 
            从字典创建会话对象(类方法)
            
        - from_db_record(record): 
            从数据库记录创建会话对象(类方法)
"""

from models.base import BaseModel
from datetime import datetime

class Conversation(BaseModel):
    """
    对话会话模型类，对应数据库中的conversations表。
    """
    
    def __init__(self, inspector_id, session_id, start_time, session_type=None, 
                 context_topic=None, end_time=None, total_messages=0, id=None):
        """
        初始化对话会话对象。
        
        Args:
            inspector_id: 药检员ID，外键
            session_id: 会话唯一标识
            start_time: 会话开始时间，datetime类型
            session_type: 会话类型（查询/咨询/实验指导等），可选
            context_topic: 会话主题，可选
            end_time: 会话结束时间，可选，datetime类型
            total_messages: 消息总数，默认为0
            id: 数据库记录ID，可选
        """
        super().__init__(id)
        self.inspector_id = inspector_id
        self.session_id = session_id
        self.start_time = start_time
        self.session_type = session_type
        self.context_topic = context_topic
        self.end_time = end_time
        self.total_messages = total_messages
    
    def end_conversation(self, end_time, total_messages=None):
        """
        结束会话，设置结束时间和消息总数。
        
        Args:
            end_time: 会话结束时间，datetime类型
            total_messages: 会话的消息总数，如果为None则保持当前值不变
            
        Returns:
            Conversation: 返回自身，支持链式调用
        """
        self.end_time = end_time
        if total_messages is not None:
            self.total_messages = total_messages
        return self
    
    def get_duration(self):
        """
        计算会话持续时间（分钟）。
        
        Returns:
            float: 会话持续的分钟数，如果会话未结束则返回None
        """
        if self.end_time is None or self.start_time is None:
            return None
            
        duration = self.end_time - self.start_time
        # 转换为分钟，并保留1位小数
        minutes = duration.total_seconds() / 60.0
        return round(minutes, 1)
    
    def is_active(self):
        """
        检查会话是否处于活动状态（未结束）。
        
        Returns:
            bool: 如果会话未结束返回True，否则返回False
        """
        return self.end_time is None
    
    @classmethod
    def from_db_record(cls, record):
        """
        从数据库记录创建对话会话对象。
        
        数据库记录格式:
        (conversation_id, inspector_id, session_id, start_time, end_time, 
         total_messages, session_type, context_topic)
        
        Args:
            record: 数据库查询结果元组
            
        Returns:
            Conversation: 新创建的对话会话对象实例
        """
        if record is None or len(record) < 8:
            raise ValueError("无效的数据库记录格式")
        
        # 解析datetime字符串为datetime对象
        start_time_str = record[3]
        start_time = None
        if start_time_str:
            if isinstance(start_time_str, str):
                try:
                    start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass
            elif isinstance(start_time_str, datetime):
                start_time = start_time_str
        
        end_time_str = record[4]
        end_time = None
        if end_time_str:
            if isinstance(end_time_str, str):
                try:
                    end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass
            elif isinstance(end_time_str, datetime):
                end_time = end_time_str
        
        # 创建Conversation实例
        return cls(
            id=record[0],
            inspector_id=record[1],
            session_id=record[2],
            start_time=start_time,
            end_time=end_time,
            total_messages=record[5],
            session_type=record[6],
            context_topic=record[7]
        )