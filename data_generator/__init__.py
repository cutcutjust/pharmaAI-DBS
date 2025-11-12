"""
数据生成器包(Data Generator Package)

本包提供自动生成智药AI系统所需的大量样本数据功能，用于满足课程要求的10万+数据规模。

使用方法:
    from data_generator.generate_base_data import generate_all_base_data
    from data_generator.generate_conversations import generate_conversation_data
    from data_generator.generate_experiments import generate_experiment_data
    
    # 按顺序执行数据生成
    generate_all_base_data()        # 首先生成基础数据
    generate_conversation_data()    # 然后生成对话数据（主要数据源，10万+条）
    generate_experiment_data()      # 最后生成实验数据
    
    # 也可单独生成某类数据
    from data_generator.generate_base_data import generate_pharmacopoeia_items
    generate_pharmacopoeia_items()  # 仅生成药典条目数据

包含模块:
    - generate_base_data.py: 生成基础数据（药典条目、药检员、实验室、权限关系）
    - generate_conversations.py: 生成对话会话和消息数据（主要数据源，10万+条）
    - generate_experiments.py: 生成实验记录和实验数据点（第二数据源）
"""

# 导入基础数据生成模块的主要函数
from .generate_base_data import (
    generate_all_base_data,
    generate_pharmacopoeia_items,
    generate_inspectors,
    generate_laboratories,
    generate_lab_access
)

# 导入对话数据生成模块的主要函数
from .generate_conversations import (
    generate_conversation_data,
    generate_conversations_only,
    generate_messages_for_conversations
)

# 导入实验数据生成模块的主要函数
from .generate_experiments import (
    generate_experiment_data,
    generate_experiment_records_only,
    generate_data_points_for_experiments,
    generate_experiments_with_transaction
)

# 暴露给外部使用的函数
__all__ = [
    'generate_all_base_data',
    'generate_pharmacopoeia_items',
    'generate_inspectors',
    'generate_laboratories',
    'generate_lab_access',
    'generate_conversation_data',
    'generate_conversations_only',
    'generate_messages_for_conversations',
    'generate_experiment_data',
    'generate_experiment_records_only',
    'generate_data_points_for_experiments',
    'generate_experiments_with_transaction'
]