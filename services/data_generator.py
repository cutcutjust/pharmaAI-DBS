"""
数据生成模块(Data Generator Module)

本模块提供生成测试数据的功能，包括药典条目、药检员、对话和实验记录等，
用于系统初始化和测试。

使用方法:
    from services.data_generator import generate_sample_data
    
    # 生成100条样本数据
    generate_sample_data(sample_size=100)
    
    # 生成指定类型的数据
    generate_sample_data(sample_size=50, data_types=['inspectors', 'conversations'])

主要功能:
    - generate_sample_data(): 
        生成样本数据，包括药典条目、药检员、对话和实验记录
        
    - _generate_pharmacopoeia_items(): 
        生成药典条目数据
        
    - _generate_inspectors(): 
        生成药检员数据
        
    - _generate_laboratories(): 
        生成实验室数据
        
    - _generate_conversations(): 
        生成对话会话和消息数据
        
    - _generate_experiments(): 
        生成实验记录和数据点
"""

import random
import time
from datetime import datetime, timedelta
from utils.logger import get_logger
from models.base import get_db_connection
from utils.performance_logger import log_execution_time

# 获取日志记录器
logger = get_logger(__name__)

@log_execution_time
def generate_sample_data(sample_size=100, data_types=None):
    """
    生成样本数据，包括药典条目、药检员、对话和实验记录
    
    Args:
        sample_size (int): 生成的样本数量，默认为100
        data_types (list): 要生成的数据类型列表，可选值包括'pharmacopoeia', 'inspectors', 
                          'laboratories', 'conversations', 'experiments'
                          如果为None，则生成所有类型的数据
    
    Returns:
        dict: 包含生成的数据统计信息
    """
    logger.info(f"开始生成样本数据 (样本数量: {sample_size})...")
    
    # 默认生成所有类型的数据
    if data_types is None:
        data_types = ['pharmacopoeia', 'inspectors', 'laboratories', 'conversations', 'experiments']
    
    # 统计信息
    stats = {
        'pharmacopoeia_items': 0,
        'inspectors': 0,
        'laboratories': 0,
        'inspector_lab_access': 0,
        'conversations': 0,
        'messages': 0,
        'experiments': 0,
        'data_points': 0
    }
    
    try:
        # 获取数据库连接
        conn = get_db_connection()
        
        # 生成药典条目数据
        if 'pharmacopoeia' in data_types:
            pharmacopoeia_count = _generate_pharmacopoeia_items(conn, sample_size)
            stats['pharmacopoeia_items'] = pharmacopoeia_count
        
        # 生成药检员数据
        if 'inspectors' in data_types:
            inspector_count = _generate_inspectors(conn, sample_size // 20)  # 药检员数量约为样本数的1/20
            stats['inspectors'] = inspector_count
        
        # 生成实验室数据
        if 'laboratories' in data_types:
            lab_count, access_count = _generate_laboratories(conn, sample_size // 100)  # 实验室数量约为样本数的1/100
            stats['laboratories'] = lab_count
            stats['inspector_lab_access'] = access_count
        
        # 生成对话会话和消息数据
        if 'conversations' in data_types:
            conv_count, msg_count = _generate_conversations(conn, sample_size // 10)  # 会话数量约为样本数的1/10
            stats['conversations'] = conv_count
            stats['messages'] = msg_count
        
        # 生成实验记录和数据点
        if 'experiments' in data_types:
            exp_count, dp_count = _generate_experiments(conn, sample_size // 20)  # 实验记录数量约为样本数的1/20
            stats['experiments'] = exp_count
            stats['data_points'] = dp_count
        
        # 提交事务
        conn.commit()
        
        logger.info("样本数据生成完成")
        logger.info(f"生成统计: {stats}")
        
        return stats
    
    except Exception as e:
        logger.error(f"生成样本数据失败: {str(e)}")
        if conn:
            conn.rollback()
        raise

def _generate_pharmacopoeia_items(conn, count):
    """
    生成药典条目数据
    
    Args:
        conn: 数据库连接
        count: 生成的数据条数
        
    Returns:
        int: 实际生成的数据条数
    """
    logger.info(f"生成药典条目数据 ({count} 条)...")
    
    # 这里简化实现，实际项目中可以从文件导入真实药典数据
    items = []
    volumes = [1, 2, 3, 4]  # 药典卷号
    categories = ["药材", "制剂", "辅料", "中成药", "化学药品", "生物制品"]
    
    for i in range(count):
        item = {
            "volume": random.choice(volumes),
            "doc_id": 10000 + i,
            "name_cn": f"药品{i}",
            "name_pinyin": f"YaoPin{i}",
            "name_en": f"Medicine{i}",
            "category": random.choice(categories),
            "content": f"这是药品{i}的详细说明内容。"
        }
        items.append(item)
    
    # 插入数据库的代码（简化实现）
    cursor = conn.cursor()
    for item in items:
        cursor.execute(
            "INSERT INTO pharmacopoeia_items (volume, doc_id, name_cn, name_pinyin, name_en, category, content) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (item["volume"], item["doc_id"], item["name_cn"], item["name_pinyin"], 
             item["name_en"], item["category"], item["content"])
        )
    
    return len(items)

def _generate_inspectors(conn, count):
    """
    生成药检员数据
    
    Args:
        conn: 数据库连接
        count: 生成的数据条数
        
    Returns:
        int: 实际生成的数据条数
    """
    logger.info(f"生成药检员数据 ({count} 条)...")
    
    # 简化实现
    inspectors = []
    departments = ["质检部", "研发部", "生产部", "药检所"]
    titles = ["初级药检员", "中级药检员", "高级药检员", "药检主管"]
    
    for i in range(count):
        inspector = {
            "employee_no": f"YJ{2020 + i % 5}{i:03d}",
            "name": f"药检员{i}",
            "phone": f"1391234{i:04d}",
            "email": f"inspector{i}@pharma.com",
            "department": random.choice(departments),
            "title": random.choice(titles),
            "certification_level": f"Level {1 + i % 3}",
            "join_date": (datetime.now() - timedelta(days=random.randint(1, 3650))).strftime("%Y-%m-%d"),
            "is_active": True
        }
        inspectors.append(inspector)
    
    # 插入数据库（简化实现）
    cursor = conn.cursor()
    for inspector in inspectors:
        cursor.execute(
            "INSERT INTO inspectors (employee_no, name, phone, email, department, title, "
            "certification_level, join_date, is_active) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (inspector["employee_no"], inspector["name"], inspector["phone"], 
             inspector["email"], inspector["department"], inspector["title"],
             inspector["certification_level"], inspector["join_date"], inspector["is_active"])
        )
    
    return len(inspectors)

def _generate_laboratories(conn, count):
    """
    生成实验室数据和药检员-实验室关系数据
    
    Args:
        conn: 数据库连接
        count: 生成的数据条数
        
    Returns:
        tuple: (实验室数量, 药检员-实验室关系数量)
    """
    logger.info(f"生成实验室数据 ({count} 条)...")
    
    # 简化实现
    labs = []
    for i in range(count):
        lab = {
            "lab_code": f"LAB{i:03d}",
            "lab_name": f"实验室{i}",
            "location": f"位置{i}",
            "certification": f"认证类型{i % 3 + 1}",
            "equipment_level": f"Level {i % 5 + 1}"
        }
        labs.append(lab)
    
    # 插入数据库（简化实现）
    cursor = conn.cursor()
    for lab in labs:
        cursor.execute(
            "INSERT INTO laboratories (lab_code, lab_name, location, certification, equipment_level) "
            "VALUES (?, ?, ?, ?, ?)",
            (lab["lab_code"], lab["lab_name"], lab["location"], 
             lab["certification"], lab["equipment_level"])
        )
    
    # 生成药检员-实验室关系数据
    access_count = _generate_inspector_lab_access(conn, count * 4)  # 平均每个实验室4个药检员
    
    return len(labs), access_count

def _generate_inspector_lab_access(conn, count):
    """
    生成药检员-实验室关系数据
    
    Args:
        conn: 数据库连接
        count: 生成的数据条数
        
    Returns:
        int: 实际生成的数据条数
    """
    logger.info(f"生成药检员-实验室关系数据 ({count} 条)...")
    
    # 获取现有药检员和实验室ID
    cursor = conn.cursor()
    cursor.execute("SELECT inspector_id FROM inspectors")
    inspector_ids = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT lab_id FROM laboratories")
    lab_ids = [row[0] for row in cursor.fetchall()]
    
    if not inspector_ids or not lab_ids:
        logger.warning("没有药检员或实验室数据，跳过生成关系数据")
        return 0
    
    # 生成关系数据
    access_levels = ["操作员", "管理员", "只读", "超级管理员"]
    access_data = []
    
    # 避免重复的inspector_id-lab_id组合
    combinations = set()
    
    for _ in range(min(count, len(inspector_ids) * len(lab_ids))):
        inspector_id = random.choice(inspector_ids)
        lab_id = random.choice(lab_ids)
        
        # 跳过重复组合
        if (inspector_id, lab_id) in combinations:
            continue
        
        combinations.add((inspector_id, lab_id))
        
        access = {
            "inspector_id": inspector_id,
            "lab_id": lab_id,
            "access_level": random.choice(access_levels),
            "granted_date": (datetime.now() - timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d")
        }
        access_data.append(access)
    
    # 插入数据库（简化实现）
    for access in access_data:
        cursor.execute(
            "INSERT INTO inspector_lab_access (inspector_id, lab_id, access_level, granted_date) "
            "VALUES (?, ?, ?, ?)",
            (access["inspector_id"], access["lab_id"], access["access_level"], access["granted_date"])
        )
    
    return len(access_data)

def _generate_conversations(conn, count):
    """
    生成对话会话和消息数据
    
    Args:
        conn: 数据库连接
        count: 生成的会话数量
        
    Returns:
        tuple: (会话数量, 消息数量)
    """
    logger.info(f"生成对话会话数据 ({count} 条)...")
    
    # 获取现有药检员ID
    cursor = conn.cursor()
    cursor.execute("SELECT inspector_id FROM inspectors")
    inspector_ids = [row[0] for row in cursor.fetchall()]
    
    if not inspector_ids:
        logger.warning("没有药检员数据，跳过生成对话数据")
        return 0, 0
    
    # 生成会话数据
    session_types = ["查询", "咨询", "实验指导", "问题反馈"]
    topics = ["药品查询", "实验方法", "设备操作", "数据分析", "报告撰写"]
    
    total_messages = 0
    conversation_ids = []
    
    for i in range(count):
        # 生成会话基本信息
        start_time = datetime.now() - timedelta(days=random.randint(1, 90), 
                                               hours=random.randint(1, 24))
        end_time = start_time + timedelta(minutes=random.randint(5, 60))
        
        # 插入会话
        cursor.execute(
            "INSERT INTO conversations (inspector_id, session_id, start_time, end_time, "
            "session_type, context_topic) VALUES (?, ?, ?, ?, ?, ?)",
            (
                random.choice(inspector_ids),
                f"SESSION{int(time.time())}{i}",
                start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_time.strftime("%Y-%m-%d %H:%M:%S"),
                random.choice(session_types),
                random.choice(topics)
            )
        )
        
        conversation_id = cursor.lastrowid
        conversation_ids.append(conversation_id)
    
    # 生成消息数据
    logger.info(f"生成对话消息数据...")
    
    # 获取药典条目ID用于引用
    cursor.execute("SELECT item_id FROM pharmacopoeia_items")
    item_ids = [row[0] for row in cursor.fetchall()]
    
    for conversation_id in conversation_ids:
        # 每个会话生成8-15条消息
        message_count = random.randint(8, 15)
        
        for j in range(message_count):
            # 交替药检员和系统发送消息
            sender_type = "inspector" if j % 2 == 0 else "system"
            
            # 消息内容
            if sender_type == "inspector":
                message_text = f"这是药检员发送的第{j//2+1}条查询消息"
                intent = "查询"
                referenced_item_id = None
            else:
                message_text = f"这是系统回复的第{j//2+1}条消息"
                intent = "回答"
                referenced_item_id = random.choice(item_ids) if item_ids and random.random() > 0.5 else None
            
            # 插入消息
            cursor.execute(
                "INSERT INTO messages (conversation_id, message_seq, sender_type, message_text, "
                "intent, confidence_score, response_time_ms, referenced_item_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    conversation_id,
                    j + 1,  # 消息序号从1开始
                    sender_type,
                    message_text,
                    intent,
                    random.random() * 0.5 + 0.5,  # 0.5-1.0的随机置信度
                    random.randint(50, 2000),  # 50-2000ms的响应时间
                    referenced_item_id
                )
            )
            
            total_messages += 1
        
        # 更新会话的消息总数
        cursor.execute(
            "UPDATE conversations SET total_messages = ? WHERE conversation_id = ?",
            (message_count, conversation_id)
        )
    
    return count, total_messages

def _generate_experiments(conn, count):
    """
    生成实验记录和数据点
    
    Args:
        conn: 数据库连接
        count: 生成的实验记录数量
        
    Returns:
        tuple: (实验记录数量, 数据点数量)
    """
    logger.info(f"生成实验记录数据 ({count} 条)...")
    
    # 获取现有药检员、实验室和药品ID
    cursor = conn.cursor()
    
    cursor.execute("SELECT inspector_id FROM inspectors")
    inspector_ids = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT lab_id FROM laboratories")
    lab_ids = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT item_id FROM pharmacopoeia_items")
    item_ids = [row[0] for row in cursor.fetchall()]
    
    if not inspector_ids or not lab_ids or not item_ids:
        logger.warning("缺少必要的关联数据，跳过生成实验数据")
        return 0, 0
    
    # 生成实验记录数据
    experiment_types = ["含量测定", "鉴别", "纯度检查", "溶解度测定", "pH测定"]
    statuses = ["进行中", "已完成", "异常"]
    results = ["合格", "不合格", "待定"]
    
    total_data_points = 0
    experiment_ids = []
    
    for i in range(count):
        # 实验日期
        experiment_date = datetime.now() - timedelta(days=random.randint(1, 365))
        start_time = experiment_date + timedelta(hours=random.randint(8, 17))
        end_time = start_time + timedelta(hours=random.randint(1, 8))
        
        # 随机选择状态和结果
        status = random.choice(statuses)
        result = random.choice(results) if status == "已完成" else None
        
        # 插入实验记录
        cursor.execute(
            "INSERT INTO experiment_records (experiment_no, inspector_id, lab_id, item_id, "
            "experiment_type, batch_no, sample_quantity, experiment_date, "
            "start_time, end_time, status, result, conclusion) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f"EXP{int(time.time())}{i:04d}",
                random.choice(inspector_ids),
                random.choice(lab_ids),
                random.choice(item_ids),
                random.choice(experiment_types),
                f"BATCH{random.randint(1000, 9999)}",
                round(random.uniform(1, 100), 3),
                experiment_date.strftime("%Y-%m-%d"),
                start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_time.strftime("%Y-%m-%d %H:%M:%S") if status != "进行中" else None,
                status,
                result,
                f"实验结论：{'通过质量检验' if result == '合格' else '未通过质量检验'}" if result else None
            )
        )
        
        experiment_id = cursor.lastrowid
        experiment_ids.append(experiment_id)
    
    # 生成数据点数据
    logger.info(f"生成实验数据点...")
    
    measurement_types = ["含量", "纯度", "pH值", "溶解度", "熔点"]
    units = ["mg", "%", "pH", "g/L", "°C"]
    
    for experiment_id in experiment_ids:
        # 每个实验记录生成3-7个数据点
        data_point_count = random.randint(3, 7)
        
        for j in range(data_point_count):
            # 随机选择测量类型和单位
            measurement_type_idx = random.randint(0, len(measurement_types) - 1)
            measurement_type = measurement_types[measurement_type_idx]
            unit = units[measurement_type_idx]
            
            # 随机生成测量值和标准范围
            measurement_value = round(random.uniform(0, 100), 4)
            standard_min = round(measurement_value * 0.8, 4)
            standard_max = round(measurement_value * 1.2, 4)
            
            # 调整顺序，确保min小于max
            if standard_min > standard_max:
                standard_min, standard_max = standard_max, standard_min
            
            # 判断是否合格
            is_qualified = standard_min <= measurement_value <= standard_max
            
            # 插入数据点
            cursor.execute(
                "INSERT INTO experiment_data_points (experiment_id, measurement_type, "
                "measurement_value, measurement_unit, standard_min, standard_max, "
                "is_qualified, measurement_time, equipment_id, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    experiment_id,
                    measurement_type,
                    measurement_value,
                    unit,
                    standard_min,
                    standard_max,
                    is_qualified,
                    (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d %H:%M:%S"),
                    f"EQ{random.randint(1000, 9999)}",
                    f"数据点{j+1}的备注信息"
                )
            )
            
            total_data_points += 1
    
    return count, total_data_points
