"""
生成实验记录数据，
要求真实自然，
按概率随机生成+AI辅助生成（非必须），
然后插入数据库。

CREATE TABLE experiment_records (
    experiment_id SERIAL PRIMARY KEY,                    -- 实验ID，主键，自增
    experiment_no VARCHAR(100) UNIQUE NOT NULL,          -- 实验编号，唯一且不可为空
    inspector_id INT NOT NULL,                           -- 药检员ID，外键，不可为空
    lab_id INT NOT NULL,                                 -- 实验室ID，外键，不可为空
    item_id INT NOT NULL,                                -- 检测的药品ID，外键，不可为空
    experiment_type VARCHAR(100),                        -- 实验类型
    batch_no VARCHAR(100),                               -- 批号
    sample_quantity DECIMAL(10,3),                       -- 样品量
    experiment_date DATE NOT NULL,                       -- 实验日期，不能为空
    start_time TIMESTAMP,                                -- 实验开始时间
    end_time TIMESTAMP,                                  -- 实验结束时间
    status VARCHAR(50),                                  -- 实验状态：进行中/已完成/异常
    result VARCHAR(50),                                  -- 实验结果：合格/不合格/待定
    conclusion TEXT,                                     -- 实验结论
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,       -- 创建时间，默认为当前时间
    FOREIGN KEY (inspector_id) REFERENCES inspectors(inspector_id),         -- 关联药检员表
    FOREIGN KEY (lab_id) REFERENCES laboratories(lab_id),                  -- 关联实验室表
    FOREIGN KEY (item_id) REFERENCES pharmacopoeia_items(item_id)          -- 关联药典条目表
);
CREATE INDEX idx_exp_inspector ON experiment_records(inspector_id);        -- 按药检员ID加速查询
CREATE INDEX idx_exp_date ON experiment_records(experiment_date);          -- 按实验日期加速查询
CREATE INDEX idx_exp_item ON experiment_records(item_id);                  -- 按药典条目ID加速查询


### 7. 实验记录表 (experiment_records)

**目标数量**：约 15,000 条

**数据要求**：

- **实验分配**：
  - 从已生成的150名药检员中随机分配
  - 从已生成的30个实验室中随机分配
  - 从已生成的6,000个药典条目中随机选择检测药品
  - 平均每个药检员约100个实验，每个实验室约500个实验
- **实验编号格式**：`EXP-{年份}{月份}-{字母}{序号}`
  - 年份：2023-2025
  - 月份：01-12
  - 字母：A-Z随机
  - 序号：001-999
  - 示例：EXP-202504-A001
- **实验类型**：从15种类型中随机选择
  - 含量测定、溶出度测定、水分测定、重金属检查、微生物限度检查
  - 无菌检查、浸出物测定、杂质检查、有关物质检查、残留溶剂测定
  - pH值测定、粒度分析、不溶性微粒检查、装量差异测定、热原检查
- **批号格式**：`B{年份}{月份}{日期}-{序号}`
  - 示例：B20250501-001
- **样品量**：0.5-100.0之间随机生成（保留3位小数）
- **实验日期**：2023-2025年，随机生成
- **实验时间**：
  - 开始时间：实验日期的8:00-17:00之间随机
  - 结束时间：开始后1-4小时随机生成
- **实验状态**：从3种状态中随机选择
  - 进行中：没有结束时间，结果为"待定"
  - 已完成：有结束时间，结果为"合格"/"不合格"/"待定"随机
  - 异常终止：有结束时间，结果为"待定"/"不合格"随机
- **实验结果**：根据状态决定
  - 进行中：固定为"待定"
  - 已完成：从"合格"、"不合格"、"待定"中随机
  - 异常终止：从"待定"、"不合格"中随机
- **实验结论**：
  - 合格：生成标准合格结论文本
  - 不合格：生成包含不合格原因（含量不足、溶出度不达标、杂质超标、微生物超标）的结论文本
  - 其他状态：可以为空
"""

import os
import sys
import random
import string
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from openai import OpenAI

# 添加项目根目录到路径
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import get_connection_pool, get_connection  # noqa: E402
from dao.base_dao import BaseDAO  # noqa: E402
from utils.logger import get_logger  # noqa: E402

# 日志记录器
logger = get_logger(__name__)

# 常量定义
EXPERIMENT_TYPES = [
    "含量测定", "溶出度测定", "水分测定", "重金属检查", "微生物限度检查",
    "无菌检查", "浸出物测定", "杂质检查", "有关物质检查", "残留溶剂测定",
    "pH值测定", "粒度分析", "不溶性微粒检查", "装量差异测定", "热原检查"
]

STATUS_OPTIONS = ["已完成", "进行中", "异常终止"]
STATUS_WEIGHTS = [0.72, 0.18, 0.10]

COMPLETED_RESULT_OPTIONS = ["合格", "不合格", "待定"]
COMPLETED_RESULT_WEIGHTS = [0.82, 0.12, 0.06]

ABNORMAL_RESULT_OPTIONS = ["待定", "不合格"]
ABNORMAL_RESULT_WEIGHTS = [0.35, 0.65]

UNQUALIFIED_REASONS = [
    "含量低于药典标准下限", "溶出度不达标", "杂质含量超标", "微生物限度超出要求",
    "残留溶剂超标", "有关物质检测异常", "pH值偏离标准范围", "热原检查未通过"
]

ABNORMAL_REASONS = [
    "实验过程中出现设备故障", "样品前处理异常终止", "实验条件波动超过允许范围",
    "系统检测到关键步骤数据缺失", "实验人员报告样品瓶破裂",
    "试剂批次出现异常，需要重新校验"
]

ONGOING_MESSAGES = [
    "实验仍在按照既定流程推进，关键检测尚未完成。",
    "当前实验数据已收集部分，后续步骤正在准备中。",
    "实验设备正在长时间运行中，预计稍后获得完整结果。",
    "本实验已完成前期准备，正在进行核心检测阶段。"
]

RESULT_IMPROVEMENT_SUGGESTIONS = [
    "建议对样品前处理流程进行复核，并核对标准品效价。",
    "推荐重新校准仪器，并对关键仪器参数进行验证。",
    "建议对操作批记录进行复查，排除人为操作误差。",
    "可考虑使用备用批次标准品进行复测，确认问题来源。",
    "建议联系仪器维护团队对设备性能进行全面检查。"
]

START_DATE = datetime.date(2023, 1, 1)
END_DATE = datetime.date(2025, 12, 31)


def init_openai_client() -> Optional[OpenAI]:
    """
    初始化OpenAI客户端（阿里云DashScope兼容模式），优先从环境变量读取密钥。
    如果未配置密钥或初始化失败，则返回None。
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        logger.info("未检测到环境变量 DASHSCOPE_API_KEY，实验结论将使用规则模板生成。")
        return None

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        logger.info("AI客户端初始化成功，可用于生成实验结论。")
        return client
    except Exception as exc:
        logger.warning(f"AI客户端初始化失败，将使用规则模板生成结论: {exc}")
        return None


def clear_experiment_records_table() -> int:
    """
    清空 experiment_records 表。
    返回删除的记录数量。
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM experiment_records")
                count_before = cursor.fetchone()[0]

                cursor.execute("DELETE FROM experiment_records")
                deleted = cursor.rowcount
                conn.commit()

                logger.info(f"已删除 {deleted} 条实验记录（删除前共有 {count_before} 条）。")
                return deleted
    except Exception as exc:
        logger.error(f"清空 experiment_records 表失败: {exc}")
        raise


def fetch_reference_data() -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    读取药检员、实验室、药典条目作为实验记录的外键来源。
    返回 (inspectors, laboratories, items) 三个列表。
    """
    inspectors: List[Dict] = []
    laboratories: List[Dict] = []
    items: List[Dict] = []

    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT inspector_id, name, department FROM inspectors")
                inspectors = [
                    {"inspector_id": row[0], "name": row[1], "department": row[2]}
                    for row in cursor.fetchall()
                ]

                cursor.execute("SELECT lab_id, lab_name, location FROM laboratories")
                laboratories = [
                    {"lab_id": row[0], "lab_name": row[1], "location": row[2]}
                    for row in cursor.fetchall()
                ]

                cursor.execute(
                    "SELECT item_id, name_cn, category, volume FROM pharmacopoeia_items"
                )
                items = [
                    {
                        "item_id": row[0],
                        "name_cn": row[1],
                        "category": row[2],
                        "volume": row[3],
                    }
                    for row in cursor.fetchall()
                ]
    except Exception as exc:
        logger.error(f"查询外键参考数据失败: {exc}")
        raise

    logger.info(
        "已加载参考数据：%d 名药检员，%d 个实验室，%d 条药典条目。",
        len(inspectors),
        len(laboratories),
        len(items),
    )
    return inspectors, laboratories, items


def load_existing_experiment_numbers() -> set:
    """
    读取数据库中已有的实验编号，避免重复。
    """
    existing_numbers = set()
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT experiment_no FROM experiment_records")
                existing_numbers = {row[0] for row in cursor.fetchall()}
    except Exception as exc:
        logger.warning(f"查询已有实验编号失败，将视为无记录: {exc}")
    return existing_numbers


def random_date_between(start: datetime.date, end: datetime.date) -> datetime.date:
    """在给定日期区间内随机选择一天。"""
    delta_days = (end - start).days
    random_day = random.randint(0, delta_days)
    return start + datetime.timedelta(days=random_day)


def random_start_time(experiment_date: datetime.date) -> datetime.datetime:
    """生成实验开始时间（当天 08:00-17:00 随机）。"""
    hour = random.randint(8, 16)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return datetime.datetime.combine(
        experiment_date,
        datetime.time(hour=hour, minute=minute, second=second),
    )


def calculate_end_time(
    start_time: datetime.datetime, status: str
) -> Optional[datetime.datetime]:
    """
    根据实验状态生成结束时间：
    - 已完成/异常终止：在开始后 1-4 小时随机；
    - 进行中：80% 概率无结束时间，20% 概率给出预计完成时间。
    """
    if status == "进行中":
        if random.random() < 0.2:
            duration = datetime.timedelta(
                hours=random.randint(2, 5), minutes=random.randint(0, 59)
            )
            return start_time + duration
        return None

    duration = datetime.timedelta(
        hours=random.randint(1, 4), minutes=random.randint(0, 59)
    )
    return start_time + duration


def generate_experiment_no(
    existing_numbers: set, sequence_map: Dict[Tuple[int, int, str], int], date_obj: datetime.date
) -> str:
    """
    按格式 EXP-YYYYMM-LNNN 生成唯一实验编号。
    使用年份、月份、随机字母与自增序号组合，确保唯一性。
    """
    year = date_obj.year
    month = date_obj.month

    for _ in range(500):
        letter = random.choice(string.ascii_uppercase)
        key = (year, month, letter)
        seq = sequence_map.get(key, 1)
        experiment_no = f"EXP-{year}{month:02d}-{letter}{seq:03d}"

        if experiment_no not in existing_numbers:
            existing_numbers.add(experiment_no)
            sequence_map[key] = seq + 1
            return experiment_no

        sequence_map[key] = seq + 1

    raise ValueError("无法生成唯一的实验编号，请检查编号生成逻辑。")


def generate_batch_no(experiment_date: datetime.date) -> str:
    """生成批号，格式 BYYYYMMDD-NNN。"""
    sequence = random.randint(1, 999)
    return f"B{experiment_date:%Y%m%d}-{sequence:03d}"


def generate_sample_quantity() -> float:
    """生成样品量，范围 0.500 - 100.000，保留三位小数。"""
    quantity = random.uniform(0.5, 100.0)
    return round(quantity, 3)


def choose_status_and_result() -> Tuple[str, str]:
    """根据预定义概率选择实验状态与结果。"""
    status = random.choices(STATUS_OPTIONS, weights=STATUS_WEIGHTS, k=1)[0]
    if status == "已完成":
        result = random.choices(
            COMPLETED_RESULT_OPTIONS, weights=COMPLETED_RESULT_WEIGHTS, k=1
        )[0]
    elif status == "异常终止":
        result = random.choices(
            ABNORMAL_RESULT_OPTIONS, weights=ABNORMAL_RESULT_WEIGHTS, k=1
        )[0]
    else:
        result = "待定"
    return status, result


def generate_conclusion_with_ai(
    client: Optional[OpenAI],
    inspector: Dict,
    lab: Dict,
    item: Dict,
    experiment_type: str,
    status: str,
    result: str,
    reason: Optional[str],
) -> Optional[str]:
    """
    使用AI生成实验结论，返回自然语言描述。若AI不可用或失败，返回None。
    """
    if client is None:
        return None

    try:
        reason_text = reason or "结果正在具体分析"
        prompt = f"""请根据以下实验信息生成一段50字以内的中文实验结论，语言自然且专业：
实验类型：{experiment_type}
实验状态：{status}
实验结果：{result}
药典条目：{item.get('name_cn', '未知条目')}（卷 {item.get('volume', '未知')}）
实验室：{lab.get('lab_name', '未知实验室')}
实验所在部门：{inspector.get('department', '未知部门')}
补充信息：{reason_text}

请直接输出结论内容，不要包含“结论：”等前缀。"""

        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的药品检验数据撰写助手，只输出简洁的实验结论。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        text = completion.choices[0].message.content.strip()
        if text:
            return text
    except Exception as exc:
        logger.warning(f"AI生成实验结论失败，改用规则模板: {exc}")
    return None


def build_template_conclusion(
    lab: Dict,
    item: Dict,
    experiment_type: str,
    status: str,
    result: str,
    reason: Optional[str],
) -> str:
    """
    根据规则生成默认实验结论文本。
    """
    lab_name = lab.get("lab_name") or "实验室"
    item_name = item.get("name_cn") or "样品"
    reason_text = reason or "后续将进一步分析验证。"

    if status == "进行中":
        progress_note = random.choice(ONGOING_MESSAGES)
        return (
            f"{lab_name}正在对《{item_name}》开展{experiment_type}，{progress_note}"
            "实验室将持续监控关键指标并在完成后更新结论。"
        )

    if status == "异常终止":
        return (
            f"{lab_name}在执行《{item_name}》的{experiment_type}时因{reason_text}，"
            "本次实验已中止，待排查原因并重新安排实验。"
        )

    # 已完成状态
    if result == "合格":
        return (
            f"{lab_name}完成《{item_name}》的{experiment_type}，检测数据符合药典标准，"
            "样品判定为合格。"
        )

    if result == "不合格":
        suggestion = random.choice(RESULT_IMPROVEMENT_SUGGESTIONS)
        return (
            f"{lab_name}完成《{item_name}》的{experiment_type}，结论为不合格，"
            f"主要问题：{reason_text}。{suggestion}"
        )

    # 已完成且结果待定
    return (
        f"{lab_name}完成《{item_name}》的{experiment_type}初步检测，部分数据仍在复核，"
        "实验结果暂定为待定，将在复核完成后确认。"
    )


def distribute_entities(target_count: int, entity_ids: List[int]) -> List[int]:
    """
    根据目标数量平均分配实体ID，以保证每个实体被引用次数较为均衡。
    """
    if not entity_ids:
        return []

    base_repeat = target_count // len(entity_ids)
    distributed = []
    for entity_id in entity_ids:
        distributed.extend([entity_id] * base_repeat)

    remainder = target_count - len(distributed)
    if remainder > 0:
        distributed.extend(random.choices(entity_ids, k=remainder))

    random.shuffle(distributed)
    return distributed


def generate_experiment_records(
    count: int = 15000,
    use_ai: bool = True,
    clear_existing: bool = False,
    batch_size: int = 500,
) -> int:
    """
    生成实验记录并写入数据库。
    参数：
        count: 生成记录数
        use_ai: 是否尝试使用AI生成结论（需要DASHSCOPE_API_KEY）
        clear_existing: 是否在生成前清空已有记录
        batch_size: 批量插入的批大小
    返回实际插入的记录数。
    """
    logger.info(
        "开始生成实验记录：目标数量=%d，使用AI=%s，清空旧数据=%s，批大小=%d",
        count,
        use_ai,
        clear_existing,
        batch_size,
    )

    if clear_existing:
        clear_experiment_records_table()

    inspectors, laboratories, items = fetch_reference_data()
    if not inspectors or not laboratories or not items:
        logger.error("缺少基础数据，无法生成实验记录，请先生成药检员、实验室和药典条目。")
        return 0

    inspector_ids = [ins["inspector_id"] for ins in inspectors]
    lab_ids = [lab["lab_id"] for lab in laboratories]
    item_ids = [item["item_id"] for item in items]

    inspector_map = {ins["inspector_id"]: ins for ins in inspectors}
    lab_map = {lab["lab_id"]: lab for lab in laboratories}
    item_map = {item["item_id"]: item for item in items}

    distributed_inspectors = distribute_entities(count, inspector_ids)
    distributed_labs = distribute_entities(count, lab_ids)

    existing_numbers = load_existing_experiment_numbers()
    sequence_map: Dict[Tuple[int, int, str], int] = {}

    ai_client = init_openai_client() if use_ai else None

    records: List[Dict] = []
    inserted_total = 0

    for idx in range(count):
        experiment_date = random_date_between(START_DATE, END_DATE)
        start_time = random_start_time(experiment_date)

        inspector_id = distributed_inspectors[idx % len(distributed_inspectors)]
        lab_id = distributed_labs[idx % len(distributed_labs)]
        item_id = random.choice(item_ids)

        inspector_info = inspector_map[inspector_id]
        lab_info = lab_map[lab_id]
        item_info = item_map[item_id]

        experiment_no = generate_experiment_no(existing_numbers, sequence_map, experiment_date)
        batch_no = generate_batch_no(experiment_date)
        sample_quantity = generate_sample_quantity()

        experiment_type = random.choice(EXPERIMENT_TYPES)
        status, result = choose_status_and_result()

        end_time = calculate_end_time(start_time, status)

        reason: Optional[str] = None
        if status == "异常终止":
            reason = random.choice(ABNORMAL_REASONS)
        elif result == "不合格":
            reason = random.choice(UNQUALIFIED_REASONS)

        # 以45%概率尝试调用AI生成结论
        conclusion: Optional[str] = None
        if ai_client is not None and random.random() < 0.45:
            conclusion = generate_conclusion_with_ai(
                ai_client,
                inspector_info,
                lab_info,
                item_info,
                experiment_type,
                status,
                result,
                reason,
            )

        if not conclusion:
            conclusion = build_template_conclusion(
                lab_info,
                item_info,
                experiment_type,
                status,
                result,
                reason,
            )

        record = {
            "experiment_no": experiment_no,
            "inspector_id": inspector_id,
            "lab_id": lab_id,
            "item_id": item_id,
            "experiment_type": experiment_type,
            "batch_no": batch_no,
            "sample_quantity": sample_quantity,
            "experiment_date": experiment_date,
            "start_time": start_time,
            "end_time": end_time,
            "status": status,
            "result": result,
            "conclusion": conclusion,
        }
        records.append(record)

        if len(records) >= batch_size or idx == count - 1:
            try:
                connection_pool = get_connection_pool()
                dao = BaseDAO(connection_pool, "experiment_records", "experiment_id")
                inserted = dao.batch_insert(
                    records,
                    batch_size=batch_size,
                    on_conflict="(experiment_no) DO NOTHING",
                )
                inserted_total += inserted
                logger.info("已插入 %d 条实验记录，累计插入 %d 条。", inserted, inserted_total)
            except Exception as exc:
                logger.error(f"批量插入实验记录失败: {exc}")
                raise
            finally:
                records.clear()

    logger.info("实验记录生成完成，共插入 %d 条记录。", inserted_total)
    return inserted_total


if __name__ == "__main__":
    generate_experiment_records(count=15000, use_ai=True, clear_existing=False)

