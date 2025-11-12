"""
业务服务层包(Services Package)

本包提供智药AI系统的核心业务服务，包括事务处理、复杂查询和性能监控等功能，
是系统业务逻辑的重要组成部分，连接数据访问层和应用层。

使用方法:
    from services.transaction_service import TransactionService
    from services.query_service import QueryService
    from services.performance_monitor import PerformanceMonitor
    from services.data_generator import generate_sample_data
    from database.connection import get_connection_pool
    
    # 创建连接池
    pool = get_connection_pool()
    
    # 使用事务服务创建实验记录和数据点
    transaction_service = TransactionService(pool)
    experiment_data = {
        'experiment': {...},  # 实验记录数据
        'data_points': [...]  # 实验数据点列表
    }
    success, result = transaction_service.create_experiment_with_data_points(experiment_data)
    
    # 使用查询服务执行复杂联合查询
    query_service = QueryService(pool)
    conversations = query_service.get_inspector_conversations_with_items(inspector_id=1)
    
    # 使用性能监控服务记录操作性能
    perf_monitor = PerformanceMonitor()
    with perf_monitor.measure_operation('查询药检员对话'):
        results = query_service.get_inspector_conversations_with_items(inspector_id=1)
    perf_stats = perf_monitor.get_statistics()
    
    # 生成测试数据
    generate_sample_data(sample_size=1000)

包含模块:
    - transaction_service.py: 提供事务支持，确保数据操作的原子性
    - query_service.py: 提供复杂的跨表JOIN查询功能
    - performance_monitor.py: 提供性能监控和统计功能，记录操作执行时间
    - data_generator.py: 提供测试数据生成功能
"""

# 导入服务模块，方便从包中直接导入
from .transaction_service import TransactionService
from .query_service import QueryService
from .performance_monitor import PerformanceMonitor
from .data_generator import generate_sample_data

__all__ = [
    'TransactionService', 
    'QueryService', 
    'PerformanceMonitor',
    'generate_sample_data'
]