"""
模型对象包(Model Objects Package)

本包提供智药AI系统的数据模型类，用于数据库表与Python对象之间的映射，
采用ORM思想，将数据库操作转换为对象操作，提高代码可读性和维护性。

使用方法:
    from models.inspector import Inspector
    from models.conversation import Conversation
    from models.message import Message
    from models.experiment import ExperimentRecord, ExperimentDataPoint
    from models.pharmacopoeia import PharmacopoeiaItem
    
    # 创建模型实例
    inspector = Inspector(
        employee_no="YJ2025001",
        name="张三",
        department="药品检测部"
    )
    
    # 从数据库记录创建模型实例
    message = Message.from_db_record(db_record)
    
    # 转换为字典表示
    message_dict = message.to_dict()
    
    # 保存到数据库（结合DAO层使用）
    inspector_dict = inspector.to_dict()
    inspector_dao.insert(inspector_dict)

包含模块:
    - base.py: 基础模型类，提供共享的模型功能
    - inspector.py: 药检员模型类
    - conversation.py: 对话会话模型类
    - message.py: 对话消息模型类
    - experiment.py: 实验记录和实验数据点模型类
    - pharmacopoeia.py: 药典条目模型类
"""

from models.base import BaseModel
from models.inspector import Inspector
from models.conversation import Conversation
from models.message import Message
from models.experiment import ExperimentRecord, ExperimentDataPoint
from models.pharmacopoeia import PharmacopoeiaItem

# 导出所有模型类，方便从models包直接导入
__all__ = [
    'BaseModel',
    'Inspector',
    'Conversation',
    'Message',
    'ExperimentRecord',
    'ExperimentDataPoint',
    'PharmacopoeiaItem'
]