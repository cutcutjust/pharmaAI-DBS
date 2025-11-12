"""
数据访问对象(DAO)包

本包提供对智药AI系统各表的数据访问功能，遵循DAO设计模式分离业务逻辑和数据访问逻辑。

使用方法:
    from dao.base_dao import BaseDAO                # 导入基础DAO类
    from dao.inspector_dao import InspectorDAO      # 导入药检员DAO
    from dao.conversation_dao import ConversationDAO # 导入对话会话DAO
    from dao.message_dao import MessageDAO          # 导入消息DAO 
    from dao.experiment_dao import ExperimentDAO    # 导入实验记录DAO

模块组成:
    - base_dao.py: 提供通用CRUD操作的基础DAO类
    - inspector_dao.py: 药检员表数据访问对象
    - conversation_dao.py: 对话会话表数据访问对象
    - message_dao.py: 对话消息表数据访问对象
    - experiment_dao.py: 实验记录和实验数据点表数据访问对象
"""

from .base_dao import BaseDAO
from .inspector_dao import InspectorDAO
from .conversation_dao import ConversationDAO
from .message_dao import MessageDAO
from .experiment_dao import ExperimentDAO

__all__ = ['BaseDAO', 'InspectorDAO', 'ConversationDAO', 'MessageDAO', 'ExperimentDAO']
