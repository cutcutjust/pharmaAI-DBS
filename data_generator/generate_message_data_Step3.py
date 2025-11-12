"""
生成对话消息数据，
要求真实自然，
按概率随机生成+ai辅助生成，
然后插入数据库


CREATE TABLE messages ( 
    message_id SERIAL PRIMARY KEY,                                    -- 消息ID，主键，自增
    conversation_id INT NOT NULL,                                     -- 所属会话ID，外键，不能为空
    message_seq INT NOT NULL,                                         -- 消息序号
    sender_type VARCHAR(20) NOT NULL,                                 -- 发送者类型('inspector' / 'system')，不能为空
    message_text TEXT NOT NULL,                                       -- 消息内容，不能为空
    intent VARCHAR(100),                                              -- 意图分类，可为空
    confidence_score DECIMAL(5,4),                                    -- 识别置信度，可为空
    response_time_ms INT,                                             -- 响应时间(毫秒)，可为空
    referenced_item_id INT,                                           -- 关联的药典条目，可为空
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,                    -- 消息时间戳，默认为当前时间
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),      -- 外键，关联到conversations表
    FOREIGN KEY (referenced_item_id) REFERENCES pharmacopoeia_items(item_id)      -- 外键，关联到pharmacopoeia_items表
);
CREATE INDEX idx_msg_conversation ON messages(conversation_id);        -- 会话ID索引，加速按会话ID检索
CREATE INDEX idx_msg_timestamp ON messages(timestamp);                 -- 时间戳索引，加速按时间检索
CREATE INDEX idx_msg_intent ON messages(intent);                       -- 意图分类索引，加速相关检索


### 6. 对话消息表 (messages) ⭐ **主要数据源**

**目标数量**：约 100,000 条

**数据要求**：

- **消息分配策略**：
  - 为每个已生成的会话生成消息
  - 每个会话平均生成10-15条消息（范围可设置为8-18条）
  - 计算：8,000会话 × 12.5条消息 ≈ 100,000条消息
- **消息序号**：从1开始递增，每个会话独立编号
- **发送者类型**：
  - 奇数序号：`inspector`（药检员发送）
  - 偶数序号：`system`（系统回复）
  - 确保对话的交替模式
- **消息内容生成**：
  - **药检员消息（问题）**：
    - 根据会话主题生成相应的问题模板
    - 问题模板包含药品名称占位符，从药典条目中随机选择药品名称填充
    - 意图分类：从10种意图中随机选择（查询标准、获取信息、核实标准、提出问题等）
  - **系统消息（回答）**：
    - 根据会话主题和引用的药典条目生成回答
    - 回答模板包含药品名称、卷号、文档ID等信息
    - 意图固定为"提供信息"
    - 置信度：0.85-0.99之间随机生成（保留4位小数）
    - 响应时间：50-500毫秒之间随机生成
- **药典条目引用**：
  - 系统消息有70-80%的概率引用药典条目
  - 从已生成的药典条目中随机选择
  - 设置 `referenced_item_id` 字段
- **时间戳**：
  - 根据消息序号递增生成时间戳
  - 确保时间顺序合理

**字段存储格式详细说明**：

| 字段名                 | SQL类型      | 是否必填 | 存储格式                                | 示例值                             | 说明                                 |
| ---------------------- | ------------ | -------- | --------------------------------------- | ---------------------------------- | ------------------------------------ |
| `message_id`         | SERIAL       | 自动生成 | 整数，自动递增                          | 1, 2, 3...                         | 主键，插入时不需要提供               |
| `conversation_id`    | INT          | 必填     | 整数，引用conversations.conversation_id | 1, 2, 3...                         | 所属会话ID，外键，必须已存在         |
| `message_seq`        | INT          | 必填     | 整数，从1开始递增                       | 1, 2, 3, 4...                      | 消息序号，每个会话独立编号           |
| `sender_type`        | VARCHAR(20)  | 必填     | 字符串，固定值                          | "inspector", "system"              | 发送者类型，必须为这两个值之一       |
| `message_text`       | TEXT         | 必填     | 文本字符串，无长度限制                  | "请问人参的药典标准是什么？"       | 消息内容，不能为空                   |
| `intent`             | VARCHAR(100) | 可选     | 中文字符串                              | "查询标准", "获取信息", "提供信息" | 意图分类，可为NULL，最大100字符      |
| `confidence_score`   | DECIMAL(5,4) | 可选     | 小数，4位小数，范围0.0000-0.9999        | 0.8500, 0.9234, 0.9876             | 识别置信度，可为NULL，仅系统消息使用 |
| `response_time_ms`   | INT          | 可选     | 整数，单位毫秒                          | 50, 150, 300, 500                  | 响应时间，可为NULL，仅系统消息使用   |
| `referenced_item_id` | INT          | 可选     | 整数，引用pharmacopoeia_items.item_id   | 1, 2, 3...                         | 关联的药典条目ID，外键，可为NULL     |
| `timestamp`          | TIMESTAMP    | 自动生成 | 时间戳格式：YYYY-MM-DD HH:MM:SS         | "2023-05-15 14:30:15"              | 消息时间戳，默认当前时间             |

**SQL插入示例**：

```sql
-- 药检员消息
INSERT INTO messages (conversation_id, message_seq, sender_type, message_text, intent, timestamp)
VALUES (1, 1, 'inspector', '请问人参的药典标准是什么？', '查询标准', '2023-05-15 14:30:00');

-- 系统消息
INSERT INTO messages (conversation_id, message_seq, sender_type, message_text, intent, confidence_score, response_time_ms, referenced_item_id, timestamp)
VALUES (1, 2, 'system', '根据药典记录，人参的药典标准为...', '提供信息', 0.9234, 150, 1, '2023-05-15 14:30:15');
```

**注意事项**：

- 这是系统的**主要数据源**，必须达到10万条以上
- 外键 `conversation_id` 必须引用已存在的会话（先执行conversations的插入）
- 外键 `referenced_item_id` 可以为空（药检员消息通常不引用），如引用则必须已存在
- `message_id` 和 `timestamp` 由数据库自动生成，无需手动设置
- `sender_type` 必须为 "inspector" 或 "system"
- `confidence_score` 和 `response_time_ms` 通常仅系统消息使用
- 生成后需要更新对应会话的 `total_messages` 字段


"""

import sys
import random
import datetime
import time
from pathlib import Path
from typing import List, Dict, Tuple

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

# 常量定义 - 意图分类
INSPECTOR_INTENTS = [
    '查询标准', '获取信息', '核实标准', '提出问题', '请求建议',
    '确认信息', '表达疑虑', '寻求解释', '请求引用', '描述情况'
]

# 问题模板 - 根据会话主题生成问题
QUESTION_TEMPLATES = {
    '药材和饮片标准查询': [
        '请问{drug_name}的药典标准是什么？',
        '{drug_name}的含量测定方法是什么？',
        '{drug_name}的质量指标有哪些具体要求？',
        '药典中对{drug_name}的鉴别方法是如何规定的？',
        '{drug_name}的贮藏条件是什么？',
        '请问{drug_name}的性状描述是什么？'
    ],
    '植物油脂提取物标准': [
        '{drug_name}的提取工艺标准是什么？',
        '请问{drug_name}的提取物含量要求是多少？',
        '{drug_name}的提取方法有哪些规定？',
        '药典中对{drug_name}提取物的质量标准是什么？'
    ],
    '成方制剂标准查询': [
        '{drug_name}的制剂标准是什么？',
        '请问{drug_name}的处方组成有哪些要求？',
        '{drug_name}的制剂工艺标准是什么？',
        '药典中对{drug_name}的制剂质量要求是什么？'
    ],
    '单味制剂标准查询': [
        '{drug_name}单味制剂的制备方法是什么？',
        '请问{drug_name}单味制剂的质量标准是什么？',
        '{drug_name}单味制剂的检验方法有哪些？'
    ],
    '化学药品标准查询': [
        '{drug_name}的化学药品标准是什么？',
        '请问{drug_name}的含量测定方法是什么？',
        '{drug_name}的杂质检查标准是什么？',
        '药典中对{drug_name}的鉴别方法是如何规定的？'
    ],
    '抗生素标准查询': [
        '{drug_name}的抗生素标准是什么？',
        '请问{drug_name}的效价测定方法是什么？',
        '{drug_name}的微生物限度检查标准是什么？'
    ],
    '生化药品标准查询': [
        '{drug_name}的生化药品标准是什么？',
        '请问{drug_name}的生物活性测定方法是什么？',
        '{drug_name}的蛋白质含量测定标准是什么？'
    ],
    '放射性药品标准查询': [
        '{drug_name}的放射性药品标准是什么？',
        '请问{drug_name}的放射性活度测定方法是什么？',
        '{drug_name}的放射化学纯度检查标准是什么？'
    ],
    '生物制品标准查询': [
        '{drug_name}的生物制品标准是什么？',
        '请问{drug_name}的效价测定方法是什么？',
        '{drug_name}的无菌检查标准是什么？'
    ],
    '疫苗标准查询': [
        '{drug_name}的疫苗标准是什么？',
        '请问{drug_name}的效价测定方法是什么？',
        '{drug_name}的稳定性检查标准是什么？'
    ],
    '通则标准查询': [
        '请问关于{drug_name}的通则标准是什么？',
        '{drug_name}相关的通则要求是什么？',
        '药典通则中对{drug_name}的规定是什么？'
    ],
    '指导原则查询': [
        '请问关于{drug_name}的指导原则是什么？',
        '{drug_name}相关的指导原则有哪些？',
        '药典指导原则中对{drug_name}的要求是什么？'
    ],
    '通用技术要求查询': [
        '请问{drug_name}的通用技术要求是什么？',
        '{drug_name}相关的通用技术要求有哪些？',
        '药典中对{drug_name}的通用技术规定是什么？'
    ],
    '药用辅料标准查询': [
        '{drug_name}的药用辅料标准是什么？',
        '请问{drug_name}的辅料质量要求是什么？',
        '{drug_name}的辅料检验方法是什么？'
    ],
    '制剂通则查询': [
        '{drug_name}的制剂通则要求是什么？',
        '请问{drug_name}的制剂通则标准是什么？',
        '药典制剂通则中对{drug_name}的规定是什么？'
    ],
    '检验方法查询': [
        '{drug_name}的检验方法是什么？',
        '请问{drug_name}的检测方法有哪些？',
        '{drug_name}的检验操作步骤是什么？',
        '药典中对{drug_name}的检验方法是如何规定的？'
    ]
}

# 回答模板 - 根据会话主题和药典条目生成回答
ANSWER_TEMPLATES = {
    '药材和饮片标准查询': [
        '根据药典记录，{drug_name}的药典标准为：含量应为标示量的95.0%~105.0%，水分不得过0.5%。详细内容请参考药典第{volume}部{doc_id}号条目。',
        '{drug_name}的标准规定pH值应在6.0~8.0之间，重金属不得过百万分之十。其检验方法详见药典第{volume}部。',
        '药典规定{drug_name}的含量测定采用液相色谱法，鉴别采用红外光谱法。具体操作参数请查阅药典第{volume}部{doc_id}号条目。',
        '{drug_name}的质量标准包括性状、鉴别、检查、含量测定四部分内容，详细要求记录在药典第{volume}部{doc_id}号条目中。'
    ],
    '植物油脂提取物标准': [
        '{drug_name}的提取物标准规定含量应为标示量的90.0%~110.0%，详细要求请参考药典第{volume}部{doc_id}号条目。',
        '根据药典记载，{drug_name}提取物的质量标准包括性状、鉴别、检查、含量测定等内容，详见药典第{volume}部。'
    ],
    '成方制剂标准查询': [
        '{drug_name}的制剂标准规定含量应为标示量的95.0%~105.0%，详细内容请参考药典第{volume}部{doc_id}号条目。',
        '药典规定{drug_name}的制剂质量标准包括处方、制法、性状、鉴别、检查、含量测定等内容，详见药典第{volume}部。'
    ],
    '单味制剂标准查询': [
        '{drug_name}单味制剂的标准规定含量应为标示量的90.0%~110.0%，详细要求请参考药典第{volume}部{doc_id}号条目。',
        '根据药典记载，{drug_name}单味制剂的质量标准详见药典第{volume}部。'
    ],
    '化学药品标准查询': [
        '{drug_name}的化学药品标准规定含量应为标示量的95.0%~105.0%，有关物质不得过0.5%。详细内容请参考药典第{volume}部{doc_id}号条目。',
        '药典规定{drug_name}的含量测定采用HPLC法，杂质检查采用TLC法，具体操作参数请参考药典第{volume}部。'
    ],
    '抗生素标准查询': [
        '{drug_name}的抗生素标准规定效价应为标示量的90.0%~110.0%，详细内容请参考药典第{volume}部{doc_id}号条目。',
        '根据药典记载，{drug_name}的效价测定方法详见药典第{volume}部。'
    ],
    '生化药品标准查询': [
        '{drug_name}的生化药品标准规定生物活性应为标示量的80.0%~120.0%，详细内容请参考药典第{volume}部{doc_id}号条目。',
        '药典规定{drug_name}的生物活性测定方法详见药典第{volume}部。'
    ],
    '放射性药品标准查询': [
        '{drug_name}的放射性药品标准规定放射性活度应为标示量的90.0%~110.0%，详细内容请参考药典第{volume}部{doc_id}号条目。',
        '根据药典记载，{drug_name}的放射化学纯度检查方法详见药典第{volume}部。'
    ],
    '生物制品标准查询': [
        '{drug_name}的生物制品标准规定效价应为标示量的80.0%~120.0%，详细内容请参考药典第{volume}部{doc_id}号条目。',
        '药典规定{drug_name}的无菌检查方法详见药典第{volume}部。'
    ],
    '疫苗标准查询': [
        '{drug_name}的疫苗标准规定效价应为标示量的80.0%~120.0%，详细内容请参考药典第{volume}部{doc_id}号条目。',
        '根据药典记载，{drug_name}的稳定性检查方法详见药典第{volume}部。'
    ],
    '通则标准查询': [
        '关于{drug_name}的通则标准，请参考药典第{volume}部{doc_id}号条目。',
        '药典通则中对{drug_name}的相关规定详见药典第{volume}部。'
    ],
    '指导原则查询': [
        '关于{drug_name}的指导原则，请参考药典第{volume}部{doc_id}号条目。',
        '药典指导原则中对{drug_name}的相关要求详见药典第{volume}部。'
    ],
    '通用技术要求查询': [
        '{drug_name}的通用技术要求，请参考药典第{volume}部{doc_id}号条目。',
        '药典中对{drug_name}的通用技术规定详见药典第{volume}部。'
    ],
    '药用辅料标准查询': [
        '{drug_name}的药用辅料标准规定含量应为标示量的95.0%~105.0%，详细内容请参考药典第{volume}部{doc_id}号条目。',
        '根据药典记载，{drug_name}的辅料质量要求详见药典第{volume}部。'
    ],
    '制剂通则查询': [
        '{drug_name}的制剂通则要求，请参考药典第{volume}部{doc_id}号条目。',
        '药典制剂通则中对{drug_name}的相关规定详见药典第{volume}部。'
    ],
    '检验方法查询': [
        '{drug_name}的检验方法采用HPLC法，具体操作参数请参考药典第{volume}部{doc_id}号条目。',
        '根据药典记载，{drug_name}的检测方法详见药典第{volume}部。',
        '药典中对{drug_name}的检验方法规定详见药典第{volume}部{doc_id}号条目。'
    ]
}


def get_all_conversations() -> List[Dict]:
    """
    从数据库获取所有会话数据
    
    返回:
        List[Dict]: 会话记录列表
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT conversation_id, inspector_id, start_time, end_time, 
                           session_type, context_topic
                    FROM conversations
                    ORDER BY conversation_id
                """)
                columns = [desc[0] for desc in cursor.description]
                conversations = [dict(zip(columns, row)) for row in cursor.fetchall()]
                logger.info(f"从数据库获取到 {len(conversations)} 个会话")
                return conversations
    except Exception as e:
        logger.error(f"获取会话数据失败: {str(e)}")
        raise


def get_pharmacopoeia_items() -> List[Dict]:
    """
    从数据库获取药典条目数据（用于生成消息内容）
    
    返回:
        List[Dict]: 药典条目列表
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT item_id, volume, doc_id, name_cn, name_pinyin, name_en, category, content
                    FROM pharmacopoeia_items
                    ORDER BY item_id
                """)
                columns = [desc[0] for desc in cursor.description]
                items = [dict(zip(columns, row)) for row in cursor.fetchall()]
                logger.info(f"从数据库获取到 {len(items)} 个药典条目")
                return items
    except Exception as e:
        logger.error(f"获取药典条目数据失败: {str(e)}")
        raise


def generate_inspector_message(
    conversation_id: int,
    message_seq: int,
    context_topic: str,
    pharmacopoeia_items: List[Dict],
    start_time: datetime.datetime
) -> Dict:
    """
    生成药检员消息（问题）
    
    参数:
        conversation_id: 会话ID
        message_seq: 消息序号
        context_topic: 会话主题
        pharmacopoeia_items: 药典条目列表（用于选择药品名称）
        start_time: 会话开始时间
        
    返回:
        Dict: 消息记录字典
    """
    # 随机选择一个药典条目获取药品名称
    if pharmacopoeia_items:
        item = random.choice(pharmacopoeia_items)
        drug_name = item.get('name_cn', '某药品')
    else:
        drug_name = '某药品'
    
    # 根据会话主题选择问题模板
    templates = QUESTION_TEMPLATES.get(context_topic, [
        '请问关于{drug_name}的信息有哪些？',
        '{drug_name}的使用方法是什么？',
        '能告诉我{drug_name}的相关标准吗？',
        '{drug_name}有什么特殊要求吗？'
    ])
    
    # 随机选择一个模板并填充药品名称
    template = random.choice(templates)
    message_text = template.format(drug_name=drug_name)
    
    # 随机选择意图
    intent = random.choice(INSPECTOR_INTENTS)
    
    # 生成时间戳（基于会话开始时间和消息序号）
    # 每条消息间隔10-60秒
    time_offset = datetime.timedelta(seconds=message_seq * random.randint(10, 60))
    timestamp = start_time + time_offset
    
    return {
        'conversation_id': conversation_id,
        'message_seq': message_seq,
        'sender_type': 'inspector',
        'message_text': message_text,
        'intent': intent,
        'confidence_score': None,
        'response_time_ms': None,
        'referenced_item_id': None,
        'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S')
    }


def generate_system_message(
    conversation_id: int,
    message_seq: int,
    context_topic: str,
    pharmacopoeia_items: List[Dict],
    start_time: datetime.datetime
) -> Dict:
    """
    生成系统消息（回答）
    
    参数:
        conversation_id: 会话ID
        message_seq: 消息序号
        context_topic: 会话主题
        pharmacopoeia_items: 药典条目列表
        start_time: 会话开始时间
        
    返回:
        Dict: 消息记录字典
    """
    # 系统消息有70-80%的概率引用药典条目
    referenced_item = None
    referenced_item_id = None
    
    if pharmacopoeia_items and random.random() < 0.75:  # 75%概率引用
        referenced_item = random.choice(pharmacopoeia_items)
        referenced_item_id = referenced_item.get('item_id')
    
    # 根据会话主题选择回答模板
    templates = ANSWER_TEMPLATES.get(context_topic, [
        '根据药典记录，{drug_name}的详细信息如下：{content}。更多信息请参考药典第{volume}部{doc_id}号条目。',
        '{drug_name}的药典记载包括：{content}。详见药典第{volume}部{doc_id}号条目。',
        '查询到{drug_name}的相关信息：{content}。详情请查阅药典第{volume}部。',
        '药典第{volume}部{doc_id}号条目中关于{drug_name}的记载为：{content}。'
    ])
    
    # 随机选择一个模板
    template = random.choice(templates)
    
    # 如果有引用的药典条目，使用其信息填充模板
    if referenced_item:
        drug_name = referenced_item.get('name_cn', '某药品')
        volume = referenced_item.get('volume', '?')
        doc_id = referenced_item.get('doc_id', '?')
        content = referenced_item.get('content', '未找到详细内容')
        if not content or len(content) < 10:
            content = '该药品的药典标准包括性状、鉴别、检查、含量测定等内容'
        
        message_text = template.format(
            drug_name=drug_name,
            volume=volume,
            doc_id=doc_id,
            content=content[:100] if len(content) > 100 else content  # 限制内容长度
        )
    else:
        # 没有引用时使用通用回答
        message_text = "很抱歉，我无法找到相关的药典记录。请您提供更准确的药品名称或查询条件。"
    
    # 生成置信度（0.85-0.99，保留4位小数）
    confidence_score = round(random.uniform(0.85, 0.99), 4)
    
    # 生成响应时间（50-500毫秒）
    response_time_ms = random.randint(50, 500)
    
    # 生成时间戳（基于会话开始时间和消息序号）
    # 系统消息在药检员消息后5-30秒
    time_offset = datetime.timedelta(seconds=(message_seq - 1) * random.randint(10, 60) + random.randint(5, 30))
    timestamp = start_time + time_offset
    
    return {
        'conversation_id': conversation_id,
        'message_seq': message_seq,
        'sender_type': 'system',
        'message_text': message_text,
        'intent': '提供信息',
        'confidence_score': confidence_score,
        'response_time_ms': response_time_ms,
        'referenced_item_id': referenced_item_id,
        'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S')
    }


def clear_messages_table() -> int:
    """
    清空messages表的所有数据
    
    返回:
        int: 删除的记录数量
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM messages")
                count_before = cursor.fetchone()[0]
                
                cursor.execute("DELETE FROM messages")
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"已删除 {deleted_count} 条消息数据（删除前共有 {count_before} 条）")
                return deleted_count
    except Exception as e:
        logger.error(f"清空messages表失败: {str(e)}")
        raise


def update_conversation_total_messages(conversation_id: int, total_messages: int):
    """
    更新会话的total_messages字段
    
    参数:
        conversation_id: 会话ID
        total_messages: 消息总数
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE conversations 
                    SET total_messages = %s 
                    WHERE conversation_id = %s
                """, (total_messages, conversation_id))
                conn.commit()
    except Exception as e:
        logger.warning(f"更新会话 {conversation_id} 的消息总数失败: {str(e)}")


def generate_messages_data(
    messages_per_conversation_range: Tuple[int, int] = (8, 18),
    clear_existing: bool = True
) -> int:
    """
    生成对话消息数据并插入数据库
    
    参数:
        messages_per_conversation_range: 每个会话生成的消息数量范围，默认(8, 18)
        clear_existing: 是否在生成前清空现有数据，默认True
        
    返回:
        int: 实际插入的消息记录数量
    """
    start_time_total = time.time()
    logger.info(f"开始生成对话消息数据，每个会话生成 {messages_per_conversation_range[0]}-{messages_per_conversation_range[1]} 条消息")
    
    # 如果指定清空现有数据，先删除所有记录
    if clear_existing:
        try:
            clear_messages_table()
        except Exception as e:
            logger.warning(f"清空现有数据失败，继续生成: {e}")
    
    # 获取所有会话数据
    try:
        conversations = get_all_conversations()
        if not conversations:
            logger.error("没有找到会话数据，请先生成会话数据")
            return 0
        logger.info(f"获取到 {len(conversations)} 个会话")
    except Exception as e:
        logger.error(f"获取会话数据失败: {str(e)}")
        raise
    
    # 获取药典条目数据
    try:
        pharmacopoeia_items = get_pharmacopoeia_items()
        if not pharmacopoeia_items:
            logger.warning("没有找到药典条目数据，消息将不包含引用")
    except Exception as e:
        logger.warning(f"获取药典条目数据失败，消息将不包含引用: {e}")
        pharmacopoeia_items = []
    
    # 生成所有消息
    all_messages = []
    conversation_message_counts = {}  # 记录每个会话的消息数量
    
    # 使用进度条生成消息数据
    total_to_generate = 0
    for conv in conversations:
        # 每个会话随机生成8-18条消息
        message_count = random.randint(messages_per_conversation_range[0], messages_per_conversation_range[1])
        total_to_generate += message_count
        conversation_message_counts[conv['conversation_id']] = message_count
    
    logger.info(f"预计生成 {total_to_generate} 条消息数据...")
    
    with tqdm(total=total_to_generate, desc="生成消息", unit="条",
              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]') as pbar:
        
        for conv in conversations:
            conversation_id = conv['conversation_id']
            context_topic = conv.get('context_topic', '检验方法查询')  # 默认主题
            start_time_str = conv.get('start_time')
            
            # 解析开始时间
            if isinstance(start_time_str, str):
                try:
                    start_time = datetime.datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    start_time = datetime.datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S.%f')
            elif isinstance(start_time_str, datetime.datetime):
                start_time = start_time_str
            else:
                # 默认使用当前时间
                start_time = datetime.datetime.now() - datetime.timedelta(days=random.randint(1, 365))
            
            message_count = conversation_message_counts[conversation_id]
            
            # 为这个会话生成消息
            for seq in range(1, message_count + 1):
                if seq % 2 == 1:  # 奇数序号：药检员消息
                    message = generate_inspector_message(
                        conversation_id, seq, context_topic, pharmacopoeia_items, start_time
                    )
                else:  # 偶数序号：系统消息
                    message = generate_system_message(
                        conversation_id, seq, context_topic, pharmacopoeia_items, start_time
                    )
                
                all_messages.append(message)
                pbar.update(1)
    
    if not all_messages:
        logger.warning("没有生成任何消息数据")
        return 0
    
    logger.info(f"已生成 {len(all_messages)} 条消息数据，开始插入数据库")
    
    # 批量插入数据库
    try:
        connection_pool = get_connection_pool()
        dao = BaseDAO(connection_pool, 'messages', 'message_id')
        
        # 使用进度条显示插入进度
        print("\n开始插入数据库...")
        inserted_count = dao.batch_insert(
            all_messages,
            batch_size=1000,
            on_conflict=None  # messages表没有唯一约束，不需要冲突处理
        )
        
        # 更新会话的total_messages字段
        logger.info("开始更新会话的消息总数...")
        update_count = 0
        with tqdm(total=len(conversation_message_counts), desc="更新会话", unit="个") as pbar:
            for conversation_id, message_count in conversation_message_counts.items():
                update_conversation_total_messages(conversation_id, message_count)
                update_count += 1
                pbar.update(1)
        
        elapsed_time = time.time() - start_time_total
        elapsed_minutes = elapsed_time / 60
        
        logger.info(f"成功插入 {inserted_count} 条消息数据")
        logger.info(f"成功更新 {update_count} 个会话的消息总数")
        logger.info(f"总耗时: {elapsed_minutes:.2f} 分钟 ({elapsed_time:.2f} 秒)")
        print(f"\n✅ 数据生成完成！共插入 {inserted_count} 条记录，总耗时: {elapsed_minutes:.2f} 分钟")
        return inserted_count
        
    except Exception as e:
        logger.error(f"插入消息数据失败: {str(e)}")
        raise


if __name__ == "__main__":
    # 生成消息数据，每个会话生成8-18条消息
    generate_messages_data(messages_per_conversation_range=(8, 18), clear_existing=True)
