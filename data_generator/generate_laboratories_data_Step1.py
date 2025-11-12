"""
生成实验室数据，
要求真实自然，
使用AI辅助生成，
然后插入数据库


CREATE TABLE laboratories (
    lab_id SERIAL PRIMARY KEY,                         -- 实验室ID，主键，自动递增
    lab_code VARCHAR(50) UNIQUE NOT NULL,              -- 实验室代码，唯一且不可为空
    lab_name VARCHAR(200) NOT NULL,                    -- 实验室名称，不能为空
    location VARCHAR(200),                             -- 实验室地址，可为空
    certification VARCHAR(100),                        -- 认证类型，可为空
    equipment_level VARCHAR(50),                       -- 设备等级，可为空
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP     -- 创建时间，默认为当前时间
);


### 3. 实验室表 (laboratories)

**目标数量**：约 30 条

**数据要求**：

- **实验室代码格式**：`LAB{序号}`，如 LAB001、LAB002，序号3位数字
- **实验室名称**：格式为"{城市}{实验室类型}"
  - 城市：从15个城市中随机选择（北京、上海、广州、深圳、杭州等）
  - 实验室类型：从12种类型中随机选择
    - 物理特性检验室、化学成分分析室、药理活性检测室、微生物检验室
    - 稳定性研究室、制剂工艺研究室、分子生物实验室、色谱分析实验室
    - 光谱分析实验室、生物分析实验室、理化检测实验室、药物代谢研究室
- **地址格式**："{城市}市科技园区{1-20}号楼"
- **认证类型**：从8种认证中随机选择
  - ISO 17025、ISO 9001、GLP、CNAS、CMA、CAP
  - 国家药典委员会认证、药品检验机构资格认证
- **设备等级**：从5个等级中随机选择（基础级、标准级、先进级、研发级、国际领先级）

**字段存储格式详细说明**：

| 字段名              | SQL类型      | 是否必填 | 存储格式                                     | 示例值                                        | 说明                              |
| ------------------- | ------------ | -------- | -------------------------------------------- | --------------------------------------------- | --------------------------------- |
| `lab_id`          | SERIAL       | 自动生成 | 整数，自动递增                               | 1, 2, 3...                                    | 主键，插入时不需要提供            |
| `lab_code`        | VARCHAR(50)  | 必填     | 字符串，格式：LAB{3位序号}                   | "LAB001", "LAB002"                            | 实验室代码，必须唯一，最大50字符  |
| `lab_name`        | VARCHAR(200) | 必填     | 中文字符串，格式：{城市}{类型}               | "北京物理特性检验室", "上海化学成分分析室"    | 实验室名称，不能为空，最大200字符 |
| `location`        | VARCHAR(200) | 可选     | 中文字符串，格式：{城市}市科技园区{楼号}号楼 | "北京市科技园区5号楼", "上海市科技园区12号楼" | 地址，可为NULL，最大200字符       |
| `certification`   | VARCHAR(100) | 可选     | 字符串                                       | "ISO 17025", "CNAS", "GLP"                    | 认证类型，可为NULL，最大100字符   |
| `equipment_level` | VARCHAR(50)  | 可选     | 中文字符串                                   | "基础级", "标准级", "先进级"                  | 设备等级，可为NULL，最大50字符    |
| `created_at`      | TIMESTAMP    | 自动生成 | 时间戳格式：YYYY-MM-DD HH:MM:SS              | "2025-01-15 10:30:00"                         | 创建时间，默认当前时间            |

**SQL插入示例**：

```sql
INSERT INTO laboratories (lab_code, lab_name, location, certification, equipment_level)
VALUES ('LAB001', '北京物理特性检验室', '北京市科技园区5号楼', 'ISO 17025', '标准级');
```

**注意事项**：

- `lab_code` 必须唯一，插入前需检查
- `lab_id` 和 `created_at` 由数据库自动生成，无需手动设置
- 这些实验室将用于后续生成实验记录和权限关系


"""

import os
import sys
import random
import json
from pathlib import Path
from typing import Dict

# 添加项目根目录到路径
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from openai import OpenAI
from database.connection import get_connection_pool, get_connection
from dao.base_dao import BaseDAO
from utils.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)

# 常量定义
CITIES = [
    '北京', '上海', '广州', '深圳', '杭州', '南京', '成都', '武汉', '西安', '重庆',
    '天津', '苏州', '长沙', '郑州', '济南'
]

LAB_TYPES = [
    '物理特性检验室', '化学成分分析室', '药理活性检测室', '微生物检验室',
    '稳定性研究室', '制剂工艺研究室', '分子生物实验室', '色谱分析实验室',
    '光谱分析实验室', '生物分析实验室', '理化检测实验室', '药物代谢研究室'
]

CERTIFICATIONS = [
    'ISO 17025', 'ISO 9001', 'GLP', 'CNAS', 'CMA', 'CAP',
    '国家药典委员会认证', '药品检验机构资格认证'
]

EQUIPMENT_LEVELS = ['基础级', '标准级', '先进级', '研发级', '国际领先级']


def init_openai_client():
    """
    初始化OpenAI客户端（使用阿里云DashScope）
    
    返回:
        OpenAI客户端实例
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        # 如果环境变量中没有，尝试使用硬编码的密钥（仅用于开发测试）
        api_key = "你自己的API密钥"
        logger.warning("使用硬编码的API密钥，建议使用环境变量DASHSCOPE_API_KEY")
    
    client = OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    return client


def generate_lab_code(sequence: int) -> str:
    """
    生成实验室代码
    
    参数:
        sequence: 序号（3位数字）
        
    返回:
        str: 实验室代码，格式LAB{3位序号}
    """
    return f"LAB{sequence:03d}"


def generate_location(city: str) -> str:
    """
    生成实验室地址（代码生成）
    
    参数:
        city: 城市名称
        
    返回:
        str: 地址字符串，格式：{城市}市科技园区{楼号}号楼
    """
    building_no = random.randint(1, 20)
    return f"{city}市科技园区{building_no}号楼"


def generate_lab_name_and_location_with_ai(client: OpenAI, city: str, lab_type: str,
                                            certification: str, equipment_level: str) -> Dict[str, str]:
    """
    使用AI生成实验室名称和地址，要求真实自然
    
    参数:
        client: OpenAI客户端
        city: 城市（由代码随机生成）
        lab_type: 实验室类型（由代码随机生成）
        certification: 认证类型（由代码随机生成）
        equipment_level: 设备等级（由代码随机生成）
        
    返回:
        dict: 包含lab_name和location的字典
    """
    try:
        prompt = f"""请为以下实验室生成名称和地址，要求真实自然：

1. 城市：{city}（已确定，不需要生成）
2. 实验室类型：{lab_type}（已确定，不需要生成）
3. 认证类型：{certification}
4. 设备等级：{equipment_level}

请生成以下信息（JSON格式）：
- lab_name: 实验室名称，格式为"{city}{lab_type}"，要求：
  * 名称要真实自然，符合中国药品检验实验室的命名习惯
  * 可以适当添加修饰词，如"国家"、"省级"、"市级"、"重点"、"中心"等，但不要过度
  * 示例："{city}国家{lab_type}"、"{city}省级{lab_type}"、"{city}{lab_type}"等
  * 确保名称长度不超过200字符
  
- location: 实验室地址，要求：
  * 地址要真实自然，符合中国科技园区或产业园区的地址格式
  * 可以是科技园区、产业园区、高新技术开发区等
  * 地址格式可以多样化，如：
    * "{city}市[区名]科技园区[楼号]号楼"（例如：北京市海淀区科技园区8号楼）
    * "{city}市[区名]高新技术开发区[路名][楼号]号"（例如：上海市浦东新区高新技术开发区生物路15号）
    * "{city}市[区名]产业园区[楼号]栋"（例如：广州市天河区产业园区3栋）
  * 区名可以是：海淀区、朝阳区、浦东新区、天河区、南山区、西湖区、鼓楼区等真实区名
  * 路名可以是：科技路、创新路、研发路、生物路等
  * 楼号可以是1-20之间的数字
  * 确保地址长度不超过200字符
  * 让地址看起来真实自然，不要过于简单

只返回JSON格式，不要其他文字说明。示例格式：
{{
    "lab_name": "{city}国家{lab_type}",
    "location": "{city}市海淀区科技园区8号楼"
}}
或
{{
    "lab_name": "{city}省级{lab_type}",
    "location": "{city}市浦东新区高新技术开发区生物路15号"
}}
或
{{
    "lab_name": "{city}{lab_type}",
    "location": "{city}市天河区产业园区3栋"
}}"""

        completion = client.chat.completions.create(
            model="qwen-flash",
            messages=[
                {'role': 'system', 'content': '你是一个数据生成助手，只返回JSON格式的数据，不要其他说明文字。'},
                {'role': 'user', 'content': prompt}
            ],
            temperature=0.7
        )
        
        response_text = completion.choices[0].message.content.strip()
        
        # 打印AI生成的内容
        logger.info(f"AI生成内容（城市：{city}，类型：{lab_type}）：\n{response_text}")
        
        # 尝试解析JSON（可能包含markdown代码块）
        if response_text.startswith('```'):
            # 移除markdown代码块标记
            lines = response_text.split('\n')
            json_text = '\n'.join([line for line in lines if not line.strip().startswith('```')])
        else:
            json_text = response_text
        
        ai_data = json.loads(json_text)
        
        # 获取AI生成的实验室名称和地址
        lab_name = ai_data.get('lab_name', '')
        location = ai_data.get('location', '')
        
        # 如果AI没有生成，使用代码生成
        if not lab_name:
            lab_name = f"{city}{lab_type}"
        
        if not location:
            location = generate_location(city)
        
        logger.info(f"生成的实验室名称：{lab_name}，地址：{location}")
        
        return {
            'lab_name': lab_name,
            'location': location
        }
        
    except Exception as e:
        logger.warning(f"AI生成实验室名称和地址失败，使用代码生成: {e}")
        # AI生成失败时，使用代码生成
        lab_name = f"{city}{lab_type}"
        location = generate_location(city)
        return {
            'lab_name': lab_name,
            'location': location
        }


def clear_laboratories_table() -> int:
    """
    清空laboratories表的所有数据
    
    返回:
        int: 删除的记录数量
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM laboratories")
                count_before = cursor.fetchone()[0]
                
                cursor.execute("DELETE FROM laboratories")
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"已删除 {deleted_count} 条实验室数据（删除前共有 {count_before} 条）")
                return deleted_count
    except Exception as e:
        logger.error(f"清空laboratories表失败: {str(e)}")
        raise


def generate_laboratories_data(count: int = 30, use_ai: bool = True, clear_existing: bool = True) -> int:
    """
    生成实验室数据并插入数据库
    
    参数:
        count: 要生成的实验室数量，默认30
        use_ai: 是否使用AI辅助生成，默认True
        clear_existing: 是否在生成前清空现有数据，默认True
        
    返回:
        int: 实际插入的记录数量
    """
    logger.info(f"开始生成实验室数据，目标数量：{count}个，使用AI：{use_ai}")
    
    # 如果指定清空现有数据，先删除所有记录
    if clear_existing:
        try:
            clear_laboratories_table()
        except Exception as e:
            logger.warning(f"清空现有数据失败，继续生成: {e}")
    
    # 初始化AI客户端（如果需要）
    client = None
    if use_ai:
        try:
            client = init_openai_client()
            logger.info("AI客户端初始化成功")
        except Exception as e:
            logger.warning(f"AI客户端初始化失败，将使用代码生成: {e}")
            use_ai = False
    
    laboratories = []
    
    # 检查数据库中已存在的实验室代码
    existing_lab_codes = set()
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT lab_code FROM laboratories")
                existing_lab_codes = {row[0] for row in cursor.fetchall()}
        logger.info(f"数据库中已存在 {len(existing_lab_codes)} 个实验室代码")
    except Exception as e:
        logger.warning(f"查询已存在实验室代码失败: {e}")
    
    # 生成实验室数据
    generated_count = 0
    sequence = 1
    
    for i in range(count):
        # 生成实验室代码
        lab_code = generate_lab_code(sequence)
        
        # 检查代码是否已存在
        while lab_code in existing_lab_codes:
            sequence += 1
            lab_code = generate_lab_code(sequence)
        
        # 随机选择城市、类型、认证和设备等级
        city = random.choice(CITIES)
        lab_type = random.choice(LAB_TYPES)
        certification = random.choice(CERTIFICATIONS)
        equipment_level = random.choice(EQUIPMENT_LEVELS)
        
        # 使用AI生成实验室名称和地址，其他字段用代码随机生成
        if use_ai and client:
            ai_data = generate_lab_name_and_location_with_ai(
                client, city, lab_type, certification, equipment_level
            )
            lab_name = ai_data['lab_name']
            location = ai_data['location']
        else:
            # 使用代码生成
            lab_name = f"{city}{lab_type}"
            location = generate_location(city)
        
        laboratory = {
            'lab_code': lab_code,
            'lab_name': lab_name,
            'location': location,
            'certification': certification,
            'equipment_level': equipment_level
        }
        
        laboratories.append(laboratory)
        existing_lab_codes.add(lab_code)
        generated_count += 1
        sequence += 1
        
        if (i + 1) % 5 == 0:
            logger.info(f"已生成 {i + 1}/{count} 条实验室数据")
    
    if not laboratories:
        logger.warning("没有生成任何实验室数据")
        return 0
    
    # 批量插入数据库
    try:
        connection_pool = get_connection_pool()
        dao = BaseDAO(connection_pool, 'laboratories', 'lab_id')
        
        inserted_count = dao.batch_insert(
            laboratories,
            batch_size=50,
            on_conflict="(lab_code) DO NOTHING"
        )
        
        logger.info(f"成功插入 {inserted_count} 条实验室数据")
        return inserted_count
        
    except Exception as e:
        logger.error(f"插入实验室数据失败: {str(e)}")
        raise


if __name__ == "__main__":
    # 生成30条实验室数据
    generate_laboratories_data(count=30, use_ai=True)
