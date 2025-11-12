"""
生成对话会话数据，
要求真实自然，
按概率随机生成，
然后插入数据库


CREATE TABLE conversations ( 
    conversation_id SERIAL PRIMARY KEY,                             -- 会话ID，主键，自动递增
    inspector_id INT NOT NULL,                                      -- 药检员ID，外键，不能为空
    session_id VARCHAR(100) UNIQUE NOT NULL,                        -- 会话唯一标识，唯一且不可为空
    start_time TIMESTAMP NOT NULL,                                  -- 会话开始时间，不能为空
    end_time TIMESTAMP,                                             -- 会话结束时间，可为空
    total_messages INT DEFAULT 0,                                   -- 消息总数，默认为0
    session_type VARCHAR(50),                                       -- 会话类型（查询/咨询/实验指导等）
    context_topic VARCHAR(200),                                     -- 会话主题
    FOREIGN KEY (inspector_id) REFERENCES inspectors(inspector_id)  -- 外键，关联inspector_id字段
);
CREATE INDEX idx_conv_inspector ON conversations(inspector_id);     -- 按药检员ID加速检索
CREATE INDEX idx_conv_time ON conversations(start_time);            -- 按会话开始时间加速检索
"""

import sys
import random
import datetime
import uuid
import time
from pathlib import Path
from typing import List, Optional, Tuple

# 添加项目根目录到路径
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import get_connection_pool, get_connection  # noqa: E402
from dao.base_dao import BaseDAO  # noqa: E402
from utils.logger import get_logger  # noqa: E402
from tqdm import tqdm  # noqa: E402

# 获取日志记录器
logger = get_logger(__name__)

# 常量定义 - 围绕药典内容设计
# 会话类型：基于药典四部的实际应用场景
SESSION_TYPES = [
    '药材鉴定查询', '饮片标准查询', '制剂标准查询', '化学药品标准查询',
    '生物制品查询', '药用辅料查询', '通则指导查询', '质量标准验证',
    '检测方法咨询', '标准解读咨询', '实验操作指导', '药典更新查询'
]

# 会话主题：基于2025药典四部的具体内容分类
CONTEXT_TOPICS = [
    # 第一部相关主题
    '药材和饮片标准查询', '植物油脂提取物标准', '成方制剂标准查询', '单味制剂标准查询',
    # 第二部相关主题
    '化学药品标准查询', '抗生素标准查询', '生化药品标准查询', '放射性药品标准查询',
    # 第三部相关主题
    '生物制品标准查询', '疫苗标准查询', '通则标准查询', '指导原则查询',
    # 第四部相关主题
    '通用技术要求查询', '药用辅料标准查询', '制剂通则查询', '检验方法查询'
]

# 会话类型和主题的关联映射（用于按概率生成更合理的组合）
# 格式：{session_type: [(topic, weight), ...]}
# weight越大，被选中的概率越高
SESSION_TOPIC_MAPPING = {
    '药材鉴定查询': [
        ('药材和饮片标准查询', 0.6), ('植物油脂提取物标准', 0.2), ('单味制剂标准查询', 0.2)
    ],
    '饮片标准查询': [
        ('药材和饮片标准查询', 0.7), ('成方制剂标准查询', 0.2), ('单味制剂标准查询', 0.1)
    ],
    '制剂标准查询': [
        ('成方制剂标准查询', 0.4), ('单味制剂标准查询', 0.3), ('制剂通则查询', 0.2), ('检验方法查询', 0.1)
    ],
    '化学药品标准查询': [
        ('化学药品标准查询', 0.5), ('抗生素标准查询', 0.2), ('生化药品标准查询', 0.2), ('检验方法查询', 0.1)
    ],
    '生物制品查询': [
        ('生物制品标准查询', 0.5), ('疫苗标准查询', 0.3), ('通则标准查询', 0.2)
    ],
    '药用辅料查询': [
        ('药用辅料标准查询', 0.6), ('通用技术要求查询', 0.3), ('制剂通则查询', 0.1)
    ],
    '通则指导查询': [
        ('通则标准查询', 0.4), ('指导原则查询', 0.3), ('通用技术要求查询', 0.2), ('检验方法查询', 0.1)
    ],
    '质量标准验证': [
        ('化学药品标准查询', 0.3), ('抗生素标准查询', 0.2), ('检验方法查询', 0.3), ('通则标准查询', 0.2)
    ],
    '检测方法咨询': [
        ('检验方法查询', 0.5), ('通则标准查询', 0.3), ('指导原则查询', 0.2)
    ],
    '标准解读咨询': [
        ('指导原则查询', 0.4), ('通则标准查询', 0.3), ('通用技术要求查询', 0.2), ('检验方法查询', 0.1)
    ],
    '实验操作指导': [
        ('检验方法查询', 0.4), ('指导原则查询', 0.3), ('通则标准查询', 0.2), ('通用技术要求查询', 0.1)
    ],
    '药典更新查询': [
        ('通则标准查询', 0.3), ('指导原则查询', 0.3), ('通用技术要求查询', 0.2), ('检验方法查询', 0.2)
    ]
}


def generate_session_type_and_topic() -> Tuple[str, str]:
    """
    按概率随机生成会话类型和主题，确保逻辑关联
    
    返回:
        Tuple[str, str]: (session_type, context_topic)
    """
    # 随机选择会话类型（均匀分布）
    session_type = random.choice(SESSION_TYPES)
    
    # 根据会话类型，按权重选择关联的主题
    if session_type in SESSION_TOPIC_MAPPING:
        # 从映射中按权重选择
        topic_weights = SESSION_TOPIC_MAPPING[session_type]
        topics = [topic for topic, _ in topic_weights]
        weights = [weight for _, weight in topic_weights]
        context_topic = random.choices(topics, weights=weights, k=1)[0]
    else:
        # 如果没有映射，随机选择（70%概率选择与类型相关的主题，30%完全随机）
        if random.random() < 0.7:
            # 尝试找到相关的主题
            related_topics = []
            for st, mappings in SESSION_TOPIC_MAPPING.items():
                if st == session_type or session_type in st or st in session_type:
                    related_topics.extend([topic for topic, _ in mappings])
            
            if related_topics:
                context_topic = random.choice(related_topics)
            else:
                context_topic = random.choice(CONTEXT_TOPICS)
        else:
            context_topic = random.choice(CONTEXT_TOPICS)
    
    return session_type, context_topic


def get_available_inspector_ids() -> List[int]:
    """
    从数据库获取所有可用的药检员ID列表
    
    返回:
        List[int]: 药检员ID列表
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT inspector_id FROM inspectors ORDER BY inspector_id")
                inspector_ids = [row[0] for row in cursor.fetchall()]
                logger.info(f"从数据库获取到 {len(inspector_ids)} 个药检员ID")
                return inspector_ids
    except Exception as e:
        logger.error(f"获取药检员ID列表失败: {str(e)}")
        raise


def generate_session_id() -> str:
    """
    生成唯一的会话ID（UUID格式）
    
    返回:
        str: UUID格式的会话ID
    """
    return str(uuid.uuid4())


def generate_start_time() -> datetime.datetime:
    """
    生成随机的会话开始时间（2023-2025年）
    
    返回:
        datetime.datetime: 会话开始时间
    """
    # 时间范围：2023-01-01 00:00:00 到 2025-12-31 23:59:59
    start_date = datetime.datetime(2023, 1, 1, 0, 0, 0)
    end_date = datetime.datetime(2025, 12, 31, 23, 59, 59)
    
    # 计算时间差（秒）
    time_delta = (end_date - start_date).total_seconds()
    
    # 随机生成秒数
    random_seconds = random.randint(0, int(time_delta))
    
    # 生成随机时间
    random_time = start_date + datetime.timedelta(seconds=random_seconds)
    
    return random_time


def generate_end_time(start_time: datetime.datetime) -> Optional[datetime.datetime]:
    """
    根据开始时间生成结束时间（开始后5-30分钟）
    
    参数:
        start_time: 会话开始时间
        
    返回:
        Optional[datetime.datetime]: 会话结束时间，可能为None
    """
    # 5-30分钟随机
    duration_minutes = random.randint(5, 30)
    end_time = start_time + datetime.timedelta(minutes=duration_minutes)
    
    # 确保结束时间不超过2025-12-31 23:59:59
    max_time = datetime.datetime(2025, 12, 31, 23, 59, 59)
    if end_time > max_time:
        return None
    
    return end_time


def clear_conversations_table() -> int:
    """
    清空conversations表的所有数据
    
    返回:
        int: 删除的记录数量
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM conversations")
                count_before = cursor.fetchone()[0]
                
                cursor.execute("DELETE FROM conversations")
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"已删除 {deleted_count} 条对话会话数据（删除前共有 {count_before} 条）")
                return deleted_count
    except Exception as e:
        logger.error(f"清空conversations表失败: {str(e)}")
        raise


def generate_conversations_data(count: int = 8000, clear_existing: bool = True) -> int:
    """
    生成对话会话数据并插入数据库
    
    参数:
        count: 要生成的会话数量，默认8000
        clear_existing: 是否在生成前清空现有数据，默认True
        
    返回:
        int: 实际插入的记录数量
    """
    start_time_total = time.time()
    logger.info(f"开始生成对话会话数据，目标数量：{count}条")
    
    # 如果指定清空现有数据，先删除所有记录
    if clear_existing:
        try:
            clear_conversations_table()
        except Exception as e:
            logger.warning(f"清空现有数据失败，继续生成: {e}")
    
    # 获取可用的药检员ID列表
    try:
        inspector_ids = get_available_inspector_ids()
        if not inspector_ids:
            logger.error("没有可用的药检员ID，请先生成药检员数据")
            return 0
        logger.info(f"获取到 {len(inspector_ids)} 个药检员ID")
    except Exception as e:
        logger.error(f"获取药检员ID失败: {str(e)}")
        raise
    
    # 检查数据库中已存在的session_id
    existing_session_ids = set()
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT session_id FROM conversations")
                existing_session_ids = {row[0] for row in cursor.fetchall()}
        logger.info(f"数据库中已存在 {len(existing_session_ids)} 个会话ID")
    except Exception as e:
        logger.warning(f"查询已存在会话ID失败: {e}")
    
    # 分配会话给药检员
    # 平均每个药检员约50-80个会话，确保所有药检员都有会话记录
    conversations = []
    sessions_per_inspector = count // len(inspector_ids)
    remaining_sessions = count % len(inspector_ids)
    
    # 计算每个药检员需要生成的会话数
    inspector_session_counts = []
    for inspector_id in inspector_ids:
        # 基础会话数 + 随机变化（±10）
        base_count = sessions_per_inspector
        variation = random.randint(-10, 10)
        inspector_session_count = max(1, base_count + variation)  # 至少1个会话
        
        # 如果还有剩余会话，随机分配给某些药检员
        if remaining_sessions > 0 and random.random() < 0.3:  # 30%概率获得额外会话
            inspector_session_count += 1
            remaining_sessions -= 1
        
        inspector_session_counts.append((inspector_id, inspector_session_count))
    
    # 如果还有剩余会话，随机分配给药检员
    while remaining_sessions > 0:
        idx = random.randint(0, len(inspector_session_counts) - 1)
        inspector_session_counts[idx] = (inspector_session_counts[idx][0], 
                                         inspector_session_counts[idx][1] + 1)
        remaining_sessions -= 1
    
    # 使用进度条生成会话数据
    total_to_generate = sum(count for _, count in inspector_session_counts)
    logger.info(f"开始生成 {total_to_generate} 条对话会话数据...")
    
    with tqdm(total=total_to_generate, desc="生成对话会话", unit="条", 
              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]') as pbar:
        
        for inspector_id, inspector_session_count in inspector_session_counts:
            # 为这个药检员生成会话
            for _ in range(inspector_session_count):
                session_id = generate_session_id()
                
                # 检查session_id是否已存在（极小概率，但需要处理）
                while session_id in existing_session_ids:
                    session_id = generate_session_id()
                existing_session_ids.add(session_id)
                
                start_time = generate_start_time()
                end_time = generate_end_time(start_time)
                
                # 按概率随机生成会话类型和主题
                session_type, context_topic = generate_session_type_and_topic()
                
                conversation = {
                    'inspector_id': inspector_id,
                    'session_id': session_id,
                    'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else None,
                    'total_messages': 0,  # 初始为0，生成消息后更新
                    'session_type': session_type,
                    'context_topic': context_topic
                }
                
                conversations.append(conversation)
                pbar.update(1)
    
    # 随机打乱顺序，使数据更自然
    random.shuffle(conversations)
    
    if not conversations:
        logger.warning("没有生成任何对话会话数据")
        return 0
    
    logger.info(f"已生成 {len(conversations)} 条对话会话数据，开始插入数据库")
    
    # 批量插入数据库
    try:
        connection_pool = get_connection_pool()
        dao = BaseDAO(connection_pool, 'conversations', 'conversation_id')
        
        # 使用进度条显示插入进度（batch_insert内部会分批处理）
        print("\n开始插入数据库...")
        inserted_count = dao.batch_insert(
            conversations,
            batch_size=500,
            on_conflict="(session_id) DO NOTHING"
        )
        
        elapsed_time = time.time() - start_time_total
        elapsed_minutes = elapsed_time / 60
        
        logger.info(f"成功插入 {inserted_count} 条对话会话数据")
        logger.info(f"总耗时: {elapsed_minutes:.2f} 分钟 ({elapsed_time:.2f} 秒)")
        print(f"\n✅ 数据生成完成！共插入 {inserted_count} 条记录，总耗时: {elapsed_minutes:.2f} 分钟")
        return inserted_count
        
    except Exception as e:
        logger.error(f"插入对话会话数据失败: {str(e)}")
        raise


if __name__ == "__main__":
    # 生成8000条对话会话数据
    generate_conversations_data(count=8000, clear_existing=True)