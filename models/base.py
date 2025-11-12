"""
基础模型类模块(Base Model Module)

本模块提供所有模型类的基础类，实现通用的数据转换、序列化等功能，
作为系统中所有数据模型的父类，提供统一的接口和行为。
同时提供数据库连接和初始化功能。

使用方法:
    from models.base import BaseModel, get_db_connection, initialize_database
    
    # 创建自定义模型类
    class MyModel(BaseModel):
        def __init__(self, field1=None, field2=None, id=None):
            super().__init__(id)
            self.field1 = field1
            self.field2 = field2
    
    # 创建实例
    model = MyModel(field1="value1", field2="value2")
    
    # 转换为字典
    model_dict = model.to_dict()
    print(model_dict)  # {'id': None, 'field1': 'value1', 'field2': 'value2'}
    
    # 从字典创建实例
    new_model = MyModel.from_dict({'field1': 'new_value', 'field2': 'value2', 'id': 1})
    
    # 从数据库记录创建实例
    db_record = (1, 'db_value1', 'db_value2')  # 模拟数据库记录
    model_from_db = MyModel.from_db_record(db_record)
    
    # 获取数据库连接
    conn = get_db_connection()
    
    # 初始化数据库
    initialize_database()

主要功能:
    - BaseModel: 所有模型类的基类
        - __init__(id=None): 初始化方法，可选地设置对象ID
        - to_dict(): 将对象转换为字典表示
        - from_dict(data): 从字典创建对象实例(类方法)
        - from_db_record(record): 从数据库记录创建对象实例(类方法)
        - get_id(): 获取对象ID
        - set_id(id): 设置对象ID
        - validate(): 验证对象数据有效性，子类可重写
        
    - get_db_connection(): 获取数据库连接
    
    - initialize_database(): 初始化数据库，创建表结构
    
    - create_indices(): 创建数据库索引
"""

import os
import sqlite3
import threading
from utils.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)

# 线程本地存储，用于保存数据库连接
_thread_local = threading.local()

# 数据库文件路径
DB_FILE = os.environ.get('DB_FILE', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'pharmacopoeia.db'))

def get_db_connection():
    """
    获取数据库连接，如果当前线程没有连接则创建一个新的连接
    
    Returns:
        sqlite3.Connection: 数据库连接对象
    """
    if not hasattr(_thread_local, 'connection'):
        # 创建数据库目录（如果不存在）
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        
        # 创建连接
        _thread_local.connection = sqlite3.connect(DB_FILE)
        _thread_local.connection.row_factory = sqlite3.Row  # 使查询结果可以通过列名访问
        
        # 启用外键约束
        _thread_local.connection.execute("PRAGMA foreign_keys = ON")
        
        logger.debug(f"创建新的数据库连接 (线程: {threading.current_thread().name})")
    
    return _thread_local.connection

def close_db_connection():
    """关闭当前线程的数据库连接"""
    if hasattr(_thread_local, 'connection'):
        _thread_local.connection.close()
        delattr(_thread_local, 'connection')
        logger.debug(f"关闭数据库连接 (线程: {threading.current_thread().name})")

def initialize_database():
    """
    初始化数据库，创建表结构
    
    Returns:
        bool: 初始化成功返回True，否则返回False
    """
    logger.info("开始初始化数据库表结构...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 创建药典条目表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pharmacopoeia_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            chemical_name TEXT,
            category TEXT,
            description TEXT,
            specification TEXT,
            usage_guide TEXT,
            storage_condition TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建药检员表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS inspectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_no TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            department TEXT,
            position TEXT,
            email TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建对话会话表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inspector_id INTEGER NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (inspector_id) REFERENCES inspectors (id)
        )
        ''')
        
        # 创建对话消息表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        )
        ''')
        
        # 创建实验记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            inspector_id INTEGER NOT NULL,
            item_id INTEGER,
            laboratory_id INTEGER,
            date DATE NOT NULL,
            status TEXT DEFAULT 'pending',
            results TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (inspector_id) REFERENCES inspectors (id),
            FOREIGN KEY (item_id) REFERENCES pharmacopoeia_items (id)
        )
        ''')
        
        # 创建数据点表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS data_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id INTEGER NOT NULL,
            value TEXT NOT NULL,
            unit TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (experiment_id) REFERENCES experiments (id)
        )
        ''')
        
        # 创建实验室表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS laboratories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT,
            capacity INTEGER,
            equipment_list TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        logger.info("数据库表结构初始化完成")
        return True
    
    except Exception as e:
        logger.error(f"初始化数据库表结构失败: {str(e)}")
        conn.rollback()
        return False

def create_indices():
    """
    创建数据库索引，提高查询性能
    
    Returns:
        bool: 创建成功返回True，否则返回False
    """
    logger.info("开始创建数据库索引...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 药典条目索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pharmacopoeia_name ON pharmacopoeia_items (name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pharmacopoeia_category ON pharmacopoeia_items (category)')
        
        # 药检员索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_inspector_employee_no ON inspectors (employee_no)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_inspector_name ON inspectors (name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_inspector_department ON inspectors (department)')
        
        # 对话会话索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_inspector ON conversations (inspector_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_start_time ON conversations (start_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversation_status ON conversations (status)')
        
        # 对话消息索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_conversation ON messages (conversation_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_timestamp ON messages (timestamp)')
        
        # 实验记录索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_experiment_inspector ON experiments (inspector_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_experiment_item ON experiments (item_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_experiment_date ON experiments (date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_experiment_status ON experiments (status)')
        
        # 数据点索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_data_point_experiment ON data_points (experiment_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_data_point_timestamp ON data_points (timestamp)')
        
        conn.commit()
        logger.info("数据库索引创建完成")
        return True
    
    except Exception as e:
        logger.error(f"创建数据库索引失败: {str(e)}")
        conn.rollback()
        return False

class BaseModel:
    """
    所有模型类的基础类，提供通用的数据转换和序列化功能。
    """
    
    def __init__(self, id=None):
        """
        初始化基础模型实例。
        
        Args:
            id: 对象的唯一标识符，默认为None
        """
        self._id = id
        
    def to_dict(self):
        """
        将模型对象转换为字典表示。
        
        Returns:
            dict: 包含对象所有属性的字典
        """
        # 获取所有非下划线开头的实例属性
        result = {}
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                # 将_id转换为id
                if key == '_id':
                    result['id'] = value
            else:
                result[key] = value
        return result
    
    @classmethod
    def from_dict(cls, data):
        """
        从字典创建模型对象的类方法。
        
        Args:
            data: 包含对象属性的字典
            
        Returns:
            BaseModel: 新创建的模型对象实例
        """
        # 提取id并创建基本实例
        id_value = data.get('id')
        instance = cls(id=id_value)
        
        # 填充其他属性
        for key, value in data.items():
            if key != 'id':
                setattr(instance, key, value)
                
        return instance
    
    @classmethod
    def from_db_record(cls, record):
        """
        从数据库记录创建模型对象的类方法。
        子类应该重写此方法以提供特定的实现。
        
        Args:
            record: 数据库查询结果记录（通常是元组）
            
        Returns:
            BaseModel: 新创建的模型对象实例
        """
        raise NotImplementedError("子类必须实现from_db_record方法")
    
    def get_id(self):
        """
        获取对象ID。
        
        Returns:
            任意类型: 对象的唯一标识符
        """
        return self._id
    
    def set_id(self, id):
        """
        设置对象ID。
        
        Args:
            id: 新的对象标识符
        """
        self._id = id
        
    def validate(self):
        """
        验证对象数据的有效性。
        子类可重写此方法以实现特定的验证逻辑。
        
        Returns:
            bool: 如果数据有效返回True，否则返回False
        """
        return True