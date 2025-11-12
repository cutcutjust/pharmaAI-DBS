"""
测试包(Tests Package)

本包提供智药AI系统的各种测试用例，用于验证系统的功能正确性和性能表现，
包括基本CRUD操作、事务机制、并发访问性能测试和极端条件压力测试，
确保系统满足课程要求。

使用方法:
    # 通过main.py运行常规测试（推荐）
    python main.py --run-tests
    
    # 通过main.py运行极端测试（单独运行）
    python main.py --run-extreme-tests
    
    # 单独运行CRUD操作测试
    python -m unittest tests.test_crud
    
    # 单独运行事务机制测试
    python -m unittest tests.test_transaction
    
    # 单独运行并发性能测试
    python -m unittest tests.test_concurrent
    
    # 单独运行极端条件测试
    python -m unittest tests.test_extreme
    
    # 也可以直接运行具体的测试文件
    python tests/test_crud.py
    python tests/test_transaction.py
    python tests/test_concurrent.py
    python tests/test_extreme.py
    
    # 在测试前确保数据库已正确配置
    # 测试会在测试数据库中创建和操作表，不会影响生产数据

包含模块:
    常规测试（--run-tests）:
        - test_crud.py: 测试基本的CRUD（创建、读取、更新、删除）操作
        - test_transaction.py: 测试数据库事务提交和回滚机制
        - test_concurrent.py: 测试多用户并发访问性能和数据一致性
    
    极端测试（--run-extreme-tests）:
        - test_extreme.py: 测试系统在极端条件下的性能表现和稳定性
"""

# 导入测试模块，方便从包中直接导入测试类
from tests.test_crud import TestCRUDOperations
from tests.test_transaction import TestTransactionMechanism
from tests.test_concurrent import TestConcurrentAccess

# 导出所有测试类，方便直接从tests包导入
__all__ = [
    'TestCRUDOperations',
    'TestTransactionMechanism',
    'TestConcurrentAccess'
]