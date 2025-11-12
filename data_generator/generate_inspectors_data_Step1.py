"""
生成药检员数据,使用AI辅助生成，然后插入数据库

CREATE TABLE inspectors (
    inspector_id SERIAL PRIMARY KEY,                  -- 药检员ID，主键，自动递增
    employee_no VARCHAR(50) UNIQUE NOT NULL,          -- 工号，唯一且不可为空
    name VARCHAR(100) NOT NULL,                       -- 姓名，不能为空
    phone VARCHAR(20),                                -- 电话
    email VARCHAR(100),                               -- 邮箱
    department VARCHAR(100),                          -- 所属部门
    title VARCHAR(50),                                -- 职称
    certification_level VARCHAR(50),                  -- 资质等级
    join_date DATE,                                   -- 入职日期
    is_active BOOLEAN DEFAULT TRUE,                   -- 是否在岗，默认为在岗
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP    -- 创建时间，默认为当前时间
);
CREATE INDEX idx_inspector_dept ON inspectors(department); -- 部门字段索引，加速按部门查询


### 2. 药检员表 (inspectors)

**目标数量**：约 150 条

**数据要求**：

- **工号格式**：`YJ{年份}{序号}`，如 YJ2025001、YJ2024002
  - 年份范围：2020-2025
  - 序号：4位数字，从0001开始递增
- **姓名生成**：
  - 姓氏：从常见姓氏列表中随机选择（李、王、张、刘、陈等30个常见姓）
  - 名字：从常见名字列表中随机选择（伟、芳、娜、秀英、敏等50个常见名）
  - 组合成2-3字的中文姓名
- **部门分配**：从10个部门中随机分配
  - 质量控制部、药品检验科、中药鉴定室、药物分析室、微生物检验科
  - 仪器分析室、临床药理科、药品稳定性研究室、中成药检测科、特殊药品检验科
- **职称分配**：从10个职称中随机分配
  - 助理药师、药师、主管药师、副主任药师、主任药师
  - 检验员、高级检验员、检验师、高级检验师、首席检验师
- **资质等级**：从4个等级中随机分配（初级资质、中级资质、高级资质、专家级资质）
- **其他字段**：
  - `phone`：11位手机号，以1开头，第二位为3/5/7/8/9
  - `email`：格式为"{姓名}{数字}@yaodian.com"
  - `join_date`：入职日期，范围2015-2025年，随机生成
  - `is_active`：95%概率为在岗（TRUE），5%概率为非在岗（FALSE）

**字段存储格式详细说明**：

| 字段名                  | SQL类型      | 是否必填 | 存储格式                        | 示例值                       | 说明                           |
| ----------------------- | ------------ | -------- | ------------------------------- | ---------------------------- | ------------------------------ |
| `inspector_id`        | SERIAL       | 自动生成 | 整数，自动递增                  | 1, 2, 3...                   | 主键，插入时不需要提供         |
| `employee_no`         | VARCHAR(50)  | 必填     | 字符串，格式：YJ{年份}{4位序号} | "YJ2025001", "YJ2024002"     | 工号，必须唯一，最大50字符     |
| `name`                | VARCHAR(100) | 必填     | 中文字符串，2-3字姓名           | "张三", "李四", "王五"       | 姓名，不能为空，最大100字符    |
| `phone`               | VARCHAR(20)  | 可选     | 字符串，11位手机号              | "13812345678", "15987654321" | 电话，可为NULL，最大20字符     |
| `email`               | VARCHAR(100) | 可选     | 字符串，邮箱格式                | "zhangsan123@yaodian.com"    | 邮箱，可为NULL，最大100字符    |
| `department`          | VARCHAR(100) | 可选     | 中文字符串                      | "质量控制部", "药品检验科"   | 部门，可为NULL，最大100字符    |
| `title`               | VARCHAR(50)  | 可选     | 中文字符串                      | "药师", "主管药师", "检验师" | 职称，可为NULL，最大50字符     |
| `certification_level` | VARCHAR(50)  | 可选     | 中文字符串                      | "初级资质", "高级资质"       | 资质等级，可为NULL，最大50字符 |
| `join_date`           | DATE         | 可选     | 日期格式：YYYY-MM-DD            | "2020-03-15", "2023-07-20"   | 入职日期，可为NULL             |
| `is_active`           | BOOLEAN      | 可选     | 布尔值：TRUE/FALSE              | TRUE, FALSE                  | 是否在岗，默认TRUE             |
| `created_at`          | TIMESTAMP    | 自动生成 | 时间戳格式：YYYY-MM-DD HH:MM:SS | "2025-01-15 10:30:00"        | 创建时间，默认当前时间         |

**SQL插入示例**：

```sql
INSERT INTO inspectors (employee_no, name, phone, email, department, title, certification_level, join_date, is_active)
VALUES ('YJ2025001', '张三', '13812345678', 'zhangsan123@yaodian.com', '质量控制部', '药师', '中级资质', '2020-03-15', TRUE);
```

**注意事项**：

- `employee_no` 必须唯一，插入前需检查
- `inspector_id` 和 `created_at` 由数据库自动生成，无需手动设置
- 这些药检员将用于后续生成对话和实验数据
"""

import os
import sys
import random
import datetime
import json
from pathlib import Path
from typing import List, Dict, Optional

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
SURNAMES = [
    '李', '王', '张', '刘', '陈', '杨', '黄', '赵', '周', '吴', 
    '徐', '孙', '朱', '马', '胡', '郭', '林', '何', '高', '梁', 
    '郑', '罗', '宋', '谢', '唐', '韩', '曹', '许', '邓', '萧'
]

NAMES = [
    '伟', '芳', '娜', '秀英', '敏', '静', '丽', '强', '磊', '军', 
    '洋', '勇', '艳', '杰', '娟', '涛', '明', '超', '秀兰', '霞', 
    '平', '刚', '桂英', '博', '志强', '建华', '兰英', '文', '玉兰', '力',
    '丹', '萍', '鹏', '华', '红', '琴', '飞', '桂兰', '建国', '荣',
    '佳', '亮', '欣', '璐', '雯', '宇', '浩', '凯', '慧', '哲',
    '晨', '瑞', '婷', '榕', '禾', '兴', '炎', '雪', '子轩', '子涵'
]

DEPARTMENTS = [
    '质量控制部', '药品检验科', '中药鉴定室', '药物分析室', '微生物检验科', 
    '仪器分析室', '临床药理科', '药品稳定性研究室', '中成药检测科', '特殊药品检验科'
]

TITLES = [
    '助理药师', '药师', '主管药师', '副主任药师', '主任药师', 
    '检验员', '高级检验员', '检验师', '高级检验师', '首席检验师'
]

CERTIFICATION_LEVELS = ['初级资质', '中级资质', '高级资质', '专家级资质']


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


def generate_random_name() -> str:
    """
    生成随机中文姓名
    
    返回:
        str: 随机生成的中文姓名（2-3字）
    """
    surname = random.choice(SURNAMES)
    # 随机选择1-2个字的名字
    if random.random() < 0.7:  # 70%概率单字名
        name = random.choice(NAMES)
        return f"{surname}{name}"
    else:  # 30%概率双字名
        name1 = random.choice(NAMES)
        name2 = random.choice(NAMES)
        return f"{surname}{name1}{name2}"


def generate_phone() -> str:
    """
    生成11位手机号
    
    返回:
        str: 11位手机号
    """
    second_digit = random.choice(['3', '5', '7', '8', '9'])
    remaining = ''.join([str(random.randint(0, 9)) for _ in range(9)])
    return f"1{second_digit}{remaining}"


def generate_email(name: str) -> str:
    """
    生成邮箱地址（随机格式和域名）
    
    参数:
        name: 姓名
        
    返回:
        str: 邮箱地址
    """
    # 常用邮箱域名
    email_domains = [
        'qq.com', 'gmail.com', '126.com', '163.com', 'sina.com', 
        'sohu.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 
        'foxmail.com', '139.com', '189.cn', 'aliyun.com', 'yaodian.com'
    ]
    
    # 将中文姓名转换为拼音（简化处理）
    pinyin_map = {
        '李': 'li', '王': 'wang', '张': 'zhang', '刘': 'liu', '陈': 'chen',
        '杨': 'yang', '黄': 'huang', '赵': 'zhao', '周': 'zhou', '吴': 'wu',
        '徐': 'xu', '孙': 'sun', '朱': 'zhu', '马': 'ma', '胡': 'hu',
        '郭': 'guo', '林': 'lin', '何': 'he', '高': 'gao', '梁': 'liang',
        '郑': 'zheng', '罗': 'luo', '宋': 'song', '谢': 'xie', '唐': 'tang',
        '韩': 'han', '曹': 'cao', '许': 'xu', '邓': 'deng', '萧': 'xiao'
    }
    
    surname = name[0]
    pinyin = pinyin_map.get(surname, 'user')
    
    # 随机选择域名
    domain = random.choice(email_domains)
    
    # 随机选择邮箱格式
    format_type = random.choice(['pinyin_number', 'pinyin_underscore', 'pinyin_dot', 'abbrev_number', 'pinyin_year'])
    number = random.randint(1, 9999)
    year = random.randint(2020, 2025)
    
    if format_type == 'pinyin_number':
        # 格式：zhangsan123
        email_local = f"{pinyin}{number}"
    elif format_type == 'pinyin_underscore':
        # 格式：zhangsan_123
        email_local = f"{pinyin}_{number}"
    elif format_type == 'pinyin_dot':
        # 格式：zhang.san123
        if len(pinyin) > 2:
            email_local = f"{pinyin[:len(pinyin)//2]}.{pinyin[len(pinyin)//2:]}{number}"
        else:
            email_local = f"{pinyin}.{number}"
    elif format_type == 'abbrev_number':
        # 格式：zs123
        abbrev = pinyin[0] + (pinyin[1] if len(pinyin) > 1 else '')
        email_local = f"{abbrev}{number}"
    else:  # pinyin_year
        # 格式：zhangsan2024
        email_local = f"{pinyin}{year}"
    
    return f"{email_local}@{domain}"


def generate_join_date() -> str:
    """
    生成随机入职日期（2015-2025年）
    
    返回:
        str: 日期字符串，格式YYYY-MM-DD
    """
    year = random.randint(2015, 2025)
    month = random.randint(1, 12)
    day = random.randint(1, 28)  # 使用28避免月份天数问题
    return datetime.date(year, month, day).isoformat()


def generate_employee_no(year: int, sequence: int) -> str:
    """
    生成工号
    
    参数:
        year: 年份（2020-2025）
        sequence: 序号（4位数字）
        
    返回:
        str: 工号，格式YJ{年份}{4位序号}
    """
    return f"YJ{year}{sequence:04d}"


def generate_name_and_email_with_ai(client: OpenAI, surname: str, name_length: int,
                                     department: str, title: str, 
                                     certification_level: str) -> Dict[str, str]:
    """
    使用AI生成药检员名字和邮箱（姓氏已由代码随机生成）
    
    参数:
        client: OpenAI客户端
        surname: 姓氏（由代码随机生成）
        name_length: 名字部分的长度（1或2，确保总长度为2-3字）
        department: 部门
        title: 职称
        certification_level: 资质等级
        
    返回:
        dict: 包含name和email的字典
    """
    try:
        name_length_desc = "1个字" if name_length == 1 else "2个字"
        prompt = f"""请为以下药检员生成名字和邮箱，要求：
1. 姓氏：{surname}（已确定，不需要生成）
2. 名字部分：需要生成{name_length_desc}，要符合中国人的常见姓名习惯
3. 部门：{department}
4. 职称：{title}
5. 资质等级：{certification_level}

请生成以下信息（JSON格式）：
- given_name: 名字部分（{name_length_desc}），不包含姓氏
- email: 邮箱地址，要求：
  * 邮箱格式可以多样化，不限于"姓名拼音+数字"格式
  * 可以是：姓名拼音+数字、姓名缩写+数字、姓名+下划线+数字、姓名+点+数字等任意格式
  * 邮箱域名可以从以下常用域名中随机选择：qq.com, gmail.com, 126.com, 163.com, sina.com, sohu.com, yahoo.com, hotmail.com, outlook.com, foxmail.com, 139.com, 189.cn, aliyun.com, yaodian.com等
  * 让邮箱看起来真实自然，格式可以灵活变化

只返回JSON格式，不要其他文字说明。示例格式（格式可以多样化）：
{{
    "given_name": "三",
    "email": "zhangsan_2023@qq.com"
}}
或
{{
    "given_name": "志强",
    "email": "zq.zhang123@gmail.com"
}}
或
{{
    "given_name": "明",
    "email": "sjiodnfsonklasdn2024@126.com"
}}
或
{{
    "given_name": "建华",
    "email": "zhangjh_88@163.com"
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
        logger.info(f"AI生成内容（姓氏：{surname}，名字长度：{name_length}）：\n{response_text}")
        
        # 尝试解析JSON（可能包含markdown代码块）
        if response_text.startswith('```'):
            # 移除markdown代码块标记
            lines = response_text.split('\n')
            json_text = '\n'.join([line for line in lines if not line.strip().startswith('```')])
        else:
            json_text = response_text
        
        ai_data = json.loads(json_text)
        
        # 获取AI生成的名字部分
        given_name = ai_data.get('given_name', '')
        if not given_name:
            # 如果AI没有生成名字，使用随机生成
            if name_length == 1:
                given_name = random.choice(NAMES)
            else:
                given_name = random.choice(NAMES) + random.choice(NAMES)
        
        # 组合完整姓名
        full_name = surname + given_name
        
        # 获取AI生成的邮箱，如果不存在则根据完整姓名生成
        ai_email = ai_data.get('email')
        if not ai_email:
            ai_email = generate_email(full_name)
        
        logger.info(f"生成的完整姓名：{full_name}，邮箱：{ai_email}")
        
        return {
            'name': full_name,
            'email': ai_email
        }
        
    except Exception as e:
        logger.warning(f"AI生成名字和邮箱失败，使用随机生成: {e}")
        # AI生成失败时，使用随机生成
        if name_length == 1:
            given_name = random.choice(NAMES)
        else:
            given_name = random.choice(NAMES) + random.choice(NAMES)
        full_name = surname + given_name
        return {
            'name': full_name,
            'email': generate_email(full_name)
        }


def clear_inspectors_table() -> int:
    """
    清空inspectors表的所有数据
    
    返回:
        int: 删除的记录数量
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM inspectors")
                count_before = cursor.fetchone()[0]
                
                cursor.execute("DELETE FROM inspectors")
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"已删除 {deleted_count} 条药检员数据（删除前共有 {count_before} 条）")
                return deleted_count
    except Exception as e:
        logger.error(f"清空inspectors表失败: {str(e)}")
        raise


def generate_inspectors_data(count: int = 150, use_ai: bool = True, clear_existing: bool = True) -> int:
    """
    生成药检员数据并插入数据库
    
    参数:
        count: 要生成的药检员数量，默认150
        use_ai: 是否使用AI辅助生成，默认True
        clear_existing: 是否在生成前清空现有数据，默认True
        
    返回:
        int: 实际插入的记录数量
    """
    logger.info(f"开始生成药检员数据，目标数量：{count}名，使用AI：{use_ai}")
    
    # 如果指定清空现有数据，先删除所有记录
    if clear_existing:
        try:
            clear_inspectors_table()
        except Exception as e:
            logger.warning(f"清空现有数据失败，继续生成: {e}")
    
    # 初始化AI客户端（如果需要）
    client = None
    if use_ai:
        try:
            client = init_openai_client()
            logger.info("AI客户端初始化成功")
        except Exception as e:
            logger.warning(f"AI客户端初始化失败，将使用随机生成: {e}")
            use_ai = False
    
    # 生成工号年份分布（2020-2025）
    year_weights = {2020: 0.15, 2021: 0.15, 2022: 0.20, 2023: 0.20, 2024: 0.20, 2025: 0.10}
    years = []
    for year, weight in year_weights.items():
        years.extend([year] * int(count * weight))
    # 补充到目标数量
    while len(years) < count:
        years.append(random.choice(list(year_weights.keys())))
    random.shuffle(years)
    
    # 为每个年份分配序号
    year_sequences = {}
    for year in set(years):
        year_sequences[year] = 1
    
    inspectors = []
    
    # 检查数据库中已存在的工号
    existing_employee_nos = set()
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT employee_no FROM inspectors")
                existing_employee_nos = {row[0] for row in cursor.fetchall()}
        logger.info(f"数据库中已存在 {len(existing_employee_nos)} 个工号")
    except Exception as e:
        logger.warning(f"查询已存在工号失败: {e}")
    
    # 生成药检员数据
    generated_count = 0
    for i in range(count):
        year = years[i]
        sequence = year_sequences[year]
        year_sequences[year] += 1
        
        employee_no = generate_employee_no(year, sequence)
        
        # 检查工号是否已存在
        if employee_no in existing_employee_nos:
            logger.warning(f"工号 {employee_no} 已存在，跳过")
            continue
        
        department = random.choice(DEPARTMENTS)
        title = random.choice(TITLES)
        certification_level = random.choice(CERTIFICATION_LEVELS)
        
        # 随机生成姓氏（代码生成）
        surname = random.choice(SURNAMES)
        # 随机决定名字长度：70%概率单字名（总长度3字），30%概率双字名（总长度2字）
        name_length = 2 if random.random() < 0.7 else 1
        
        # 使用AI生成名字和邮箱，其他字段用代码随机生成
        if use_ai and client:
            ai_data = generate_name_and_email_with_ai(
                client, surname, name_length, department, title, certification_level
            )
            name = ai_data['name']
            email = ai_data['email']
        else:
            # 使用随机生成（也使用姓氏+名字的方式）
            if name_length == 1:
                given_name = random.choice(NAMES)
            else:
                given_name = random.choice(NAMES) + random.choice(NAMES)
            name = surname + given_name
            email = generate_email(name)
        
        # 其他字段用代码随机生成
        inspector = {
            'employee_no': employee_no,
            'name': name,
            'phone': generate_phone(),
            'email': email,
            'department': department,
            'title': title,
            'certification_level': certification_level,
            'join_date': generate_join_date(),
            'is_active': random.random() > 0.05  # 95%概率在岗
        }
        
        inspectors.append(inspector)
        existing_employee_nos.add(employee_no)
        generated_count += 1
        
        if (i + 1) % 10 == 0:
            logger.info(f"已生成 {i + 1}/{count} 条药检员数据")
    
    if not inspectors:
        logger.warning("没有生成任何药检员数据")
        return 0
    
    # 批量插入数据库
    try:
        connection_pool = get_connection_pool()
        dao = BaseDAO(connection_pool, 'inspectors', 'inspector_id')
        
        inserted_count = dao.batch_insert(
            inspectors,
            batch_size=100,
            on_conflict="(employee_no) DO NOTHING"
        )
        
        logger.info(f"成功插入 {inserted_count} 名药检员数据")
        return inserted_count
        
    except Exception as e:
        logger.error(f"插入药检员数据失败: {str(e)}")
        raise


if __name__ == "__main__":
    # 生成150名药检员数据
    generate_inspectors_data(count=150, use_ai=True)
