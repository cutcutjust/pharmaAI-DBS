"""
对话消息模型模块(Message Model Module)

本模块提供对话消息相关的模型类，对应数据库中的messages表，
用于表示药检员与系统交互过程中产生的对话消息，是系统中最主要的数据源之一。

使用方法:
    from models.message import Message
    from datetime import datetime
    
    # 创建药检员发送的消息
    inspector_message = Message(
        conversation_id=1,
        message_seq=1,
        sender_type="inspector",
        message_text="请查询二甲双胍的含量测定方法",
        intent="查询药典方法"
    )
    
    # 创建系统回复的消息
    system_message = Message(
        conversation_id=1,
        message_seq=2,
        sender_type="system",
        message_text="二甲双胍的含量测定方法如下：...",
        referenced_item_id=157,
        response_time_ms=320,
        confidence_score=0.95
    )
    
    # 访问消息属性
    print(f"消息内容: {inspector_message.message_text}")
    print(f"意图: {inspector_message.intent}")
    
    # 设置置信度
    inspector_message.set_confidence(0.87)
    
    # 关联到药典条目
    inspector_message.set_reference(157)
    
    # 转换为字典用于数据库操作
    message_dict = system_message.to_dict()
    
    # 从数据库记录创建实例
    db_record = (1, 2, 3, "system", "二甲双胍的含量测定方法如下：...", 
                 "回复查询", 0.95, 320, 157, "2025-01-15 10:30:15")
    message = Message.from_db_record(db_record)

主要功能:
    - Message: 对话消息模型类
        - __init__(conversation_id, message_seq, sender_type, message_text, 
                  intent=None, confidence_score=None, response_time_ms=None,
                  referenced_item_id=None, timestamp=None, id=None):
            初始化消息对象
            
        - is_from_inspector(): 
            检查消息是否来自药检员
            
        - is_from_system(): 
            检查消息是否来自系统
            
        - has_reference(): 
            检查消息是否关联药典条目
            
        - set_confidence(score): 
            设置置信度分数
            
        - set_response_time(milliseconds): 
            设置响应时间（毫秒）
            
        - set_reference(item_id): 
            设置关联的药典条目ID
            
        - to_dict(): 
            将消息对象转换为字典
            
        - from_dict(data): 
            从字典创建消息对象(类方法)
            
        - from_db_record(record): 
            从数据库记录创建消息对象(类方法)
"""

from models.base import BaseModel
from datetime import datetime

class Message(BaseModel):
    """
    对话消息模型类，对应数据库中的messages表。
    """
    
    def __init__(self, conversation_id, message_seq, sender_type, message_text, 
                 intent=None, confidence_score=None, response_time_ms=None,
                 referenced_item_id=None, timestamp=None, id=None):
        """
        初始化对话消息对象。
        
        Args:
            conversation_id: 所属会话ID，外键
            message_seq: 消息序号
            sender_type: 发送者类型，值为"inspector"或"system"
            message_text: 消息文本内容
            intent: 意图分类，可选
            confidence_score: 识别置信度（0-1），可选
            response_time_ms: 响应时间（毫秒），可选
            referenced_item_id: 关联的药典条目ID，可选
            timestamp: 消息时间戳，可选，默认为当前时间
            id: 数据库记录ID，可选
        """
        super().__init__(id)
        self.conversation_id = conversation_id
        self.message_seq = message_seq
        self.sender_type = sender_type
        self.message_text = message_text
        self.intent = intent
        self.confidence_score = confidence_score
        self.response_time_ms = response_time_ms
        self.referenced_item_id = referenced_item_id
        self.timestamp = timestamp if timestamp else datetime.now()
    
    def is_from_inspector(self):
        """
        检查消息是否来自药检员。
        
        Returns:
            bool: 如果消息来自药检员返回True，否则返回False
        """
        return self.sender_type.lower() == "inspector"
    
    def is_from_system(self):
        """
        检查消息是否来自系统。
        
        Returns:
            bool: 如果消息来自系统返回True，否则返回False
        """
        return self.sender_type.lower() == "system"
    
    def has_reference(self):
        """
        检查消息是否关联药典条目。
        
        Returns:
            bool: 如果消息关联了药典条目返回True，否则返回False
        """
        return self.referenced_item_id is not None
    
    def set_confidence(self, score):
        """
        设置识别置信度分数。
        
        Args:
            score: 置信度分数，范围0-1
            
        Returns:
            Message: 返回自身，支持链式调用
        """
        self.confidence_score = score
        return self
    
    def set_response_time(self, milliseconds):
        """
        设置响应时间（毫秒）。
        
        Args:
            milliseconds: 响应时间，整数，单位毫秒
            
        Returns:
            Message: 返回自身，支持链式调用
        """
        self.response_time_ms = milliseconds
        return self
    
    def set_reference(self, item_id):
        """
        设置关联的药典条目ID。
        
        Args:
            item_id: 药典条目ID
            
        Returns:
            Message: 返回自身，支持链式调用
        """
        self.referenced_item_id = item_id
        return self
    
    @classmethod
    def from_db_record(cls, record):
        """
        从数据库记录创建对话消息对象。
        
        数据库记录格式:
        (message_id, conversation_id, message_seq, sender_type, message_text,
         intent, confidence_score, response_time_ms, referenced_item_id, timestamp)
        
        Args:
            record: 数据库查询结果元组
            
        Returns:
            Message: 新创建的对话消息对象实例
        """
        if record is None or len(record) < 10:
            raise ValueError("无效的数据库记录格式")
        
        # 解析datetime字符串为datetime对象
        timestamp_str = record[9]
        timestamp = None
        if timestamp_str:
            if isinstance(timestamp_str, str):
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
                    except ValueError:
                        pass
            elif isinstance(timestamp_str, datetime):
                timestamp = timestamp_str
        
        # 创建Message实例
        return cls(
            id=record[0],
            conversation_id=record[1],
            message_seq=record[2],
            sender_type=record[3],
            message_text=record[4],
            intent=record[5],
            confidence_score=record[6],
            response_time_ms=record[7],
            referenced_item_id=record[8],
            timestamp=timestamp
        )