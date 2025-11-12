# -*- coding: utf-8 -*-
"""
生成实验记录数据，
要求真实自然，
按概率随机生成+ai辅助生成（非必须），
然后插入数据库。


CREATE TABLE experiment_data_points (
    data_id SERIAL PRIMARY KEY,                                    -- 数据点ID，主键，自增
    experiment_id INT NOT NULL,                                    -- 所属实验ID，外键，不能为空
    measurement_type VARCHAR(100) NOT NULL,                        -- 测量类型（含量/纯度/pH等），不能为空
    measurement_value DECIMAL(12,4),                               -- 测量值
    measurement_unit VARCHAR(50),                                  -- 测量单位
    standard_min DECIMAL(12,4),                                    -- 标准下限
    standard_max DECIMAL(12,4),                                    -- 标准上限
    is_qualified BOOLEAN,                                          -- 是否合格
    measurement_time TIMESTAMP,                                    -- 测量时间
    equipment_id VARCHAR(100),                                     -- 设备编号
    notes TEXT,                                                    -- 备注
    FOREIGN KEY (experiment_id) REFERENCES experiment_records(experiment_id)  -- 外键，关联experiment_records表
);
CREATE INDEX idx_data_experiment ON experiment_data_points(experiment_id);     -- 按实验ID加速查询
CREATE INDEX idx_data_type ON experiment_data_points(measurement_type);        -- 按测量类型加速查询



### 8. 实验数据点表 (experiment_data_points)

**目标数量**：约 40,000 条

**数据要求**：

- **数据点分配**：
  - 为每个已生成的实验记录生成数据点
  - 每个实验记录平均生成2-5个数据点（范围可设置为2-5条）
  - 计算：15,000实验 × 2.67数据点 ≈ 40,000条数据点
- **测量类型选择**：
  - 根据实验类型选择相应的测量类型
  - 例如：含量测定实验 → 主成分含量、杂质含量、对照品含量对比等
  - 例如：溶出度测定实验 → 溶出度、释放度、累积溶出百分比等
  - 每个实验从对应的测量类型列表中随机选择2-5种
- **测量值生成**：
  - 根据测量类型设置合理的数值范围
  - **含量类**：88-112%，标准范围90-110%
  - **杂质类**：0-2.5%，标准范围0-2.0%
  - **水分类**：0-12%，标准范围0-10%
  - **重金属类**：0-15 ppm，标准范围0-10 ppm
  - **pH值**：3-11，标准范围4.0-9.0
  - **溶出度**：65-105%，标准范围75-100%
- **测量单位**：根据测量类型设置相应单位（%、ppm、mg/g、CFU/g等）
- **合格判定**：
  - 根据测量值是否在标准范围内（standard_min ≤ value ≤ standard_max）判定
  - 设置 `is_qualified` 字段
- **测量时间**：实验开始后1-48小时内随机生成
- **设备编号**：从15个设备ID中随机选择
  - HPLC-001、HPLC-002、GC-001、UV-001、IR-001等
- **备注信息**：
  - 不合格的数据点有概率生成备注，说明可能的原因
  - 备注内容：测量值超出标准范围、可能存在操作误差、仪器可能需要校准等

**字段存储格式详细说明**：

| 字段名                | SQL类型       | 是否必填 | 存储格式                                   | 示例值                           | 说明                                 |
| --------------------- | ------------- | -------- | ------------------------------------------ | -------------------------------- | ------------------------------------ |
| `data_id`           | SERIAL        | 自动生成 | 整数，自动递增                             | 1, 2, 3...                       | 主键，插入时不需要提供               |
| `experiment_id`     | INT           | 必填     | 整数，引用experiment_records.experiment_id | 1, 2, 3...                       | 所属实验ID，外键，必须已存在         |
| `measurement_type`  | VARCHAR(100)  | 必填     | 中文字符串                                 | "主成分含量", "溶出度", "pH值"   | 测量类型，不能为空，最大100字符      |
| `measurement_value` | DECIMAL(12,4) | 可选     | 小数，4位小数                              | 95.5000, 7.2500, 0.8500          | 测量值，可为NULL                     |
| `measurement_unit`  | VARCHAR(50)   | 可选     | 字符串                                     | "%", "ppm", "mg/g", ""           | 测量单位，可为NULL，最大50字符       |
| `standard_min`      | DECIMAL(12,4) | 可选     | 小数，4位小数                              | 90.0000, 0.0000, 4.0000          | 标准下限，可为NULL                   |
| `standard_max`      | DECIMAL(12,4) | 可选     | 小数，4位小数                              | 110.0000, 2.0000, 9.0000         | 标准上限，可为NULL                   |
| `is_qualified`      | BOOLEAN       | 可选     | 布尔值：TRUE/FALSE                         | TRUE, FALSE                      | 是否合格，根据值是否在标准范围内判定 |
| `measurement_time`  | TIMESTAMP     | 可选     | 时间戳格式：YYYY-MM-DD HH:MM:SS            | "2023-05-15 10:30:00"            | 测量时间，可为NULL                   |
| `equipment_id`      | VARCHAR(100)  | 可选     | 字符串                                     | "HPLC-001", "GC-001", "UV-001"   | 设备编号，可为NULL，最大100字符      |
| `notes`             | TEXT          | 可选     | 文本字符串，无长度限制                     | "测量值超出标准范围，需重新检测" | 备注，可为NULL                       |

**SQL插入示例**：

```sql
INSERT INTO experiment_data_points (experiment_id, measurement_type, measurement_value, measurement_unit, standard_min, standard_max, is_qualified, measurement_time, equipment_id, notes)
VALUES (1, '主成分含量', 95.5000, '%', 90.0000, 110.0000, TRUE, '2023-05-15 10:30:00', 'HPLC-001', NULL);
```

**注意事项**：

- 外键 `experiment_id` 必须引用已存在的实验记录（先执行experiment_records的插入）
- `data_id` 由数据库自动生成，无需手动设置
- 测量值应具有合理性，符合实际检测场景
- `is_qualified` 应根据 `measurement_value` 是否在 `standard_min` 和 `standard_max` 范围内判定
- 不合格数据点应占一定比例（约10-20%），模拟真实情况
- `measurement_unit` 根据测量类型设置：含量类用"%"，重金属用"ppm"，pH值用空字符串""
from openai import OpenAI

client = OpenAI(
    # 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    # 以下是北京地域base_url，如果使用新加坡地域的模型，需要将base_url替换为：https://dashscope-intl.aliyuncs.com/compatible-mode/v1
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

completion = client.chat.completions.create(
    # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    model="qwen-plus", 
    messages=[
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': '你是谁？'}
    ]
)
print(completion.choices[0].message.content)
api_key = "sk-f09ad7f79c3c47f29a6e95011d99255a"
"""


import os
import sys
import random
import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple
from pathlib import Path

from openai import OpenAI

# 添加项目根目录到路径
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import get_connection_pool, get_connection  # noqa: E402
from dao.base_dao import BaseDAO  # noqa: E402
from utils.logger import get_logger  # noqa: E402

logger = get_logger(__name__)

EQUIPMENT_IDS: Sequence[str] = (
    "HPLC-001",
    "HPLC-002",
    "GC-001",
    "UV-001",
    "IR-001",
    "LCMS-001",
    "LCMS-002",
    "ICPMS-001",
    "NMR-001",
    "TOC-001",
    "DLS-001",
    "XRD-001",
    "FTIR-001",
    "GCMS-001",
    "MS-001",
)

UNQUALIFIED_NOTE_TEMPLATES: Sequence[str] = (
    "测量值 {value}{unit} 超出标准范围 {min_bound}-{max_bound}{unit}，建议复测并校准设备。",
    "检测结果偏离药典标准（{min_bound}-{max_bound}{unit}），疑似样品或操作存在异常。",
    "该项检测未达标，建议复核前处理流程并检查 {equipment} 的状态。",
    "结果异常：测得 {value}{unit}，超出允许范围，需记录并启动纠正措施。",
    "数值不在标准区间内，考虑更换试剂或安排重复检测确认原因。",
)

@dataclass(frozen=True)
class MeasurementDefinition:
    measurement_type: str
    unit: str
    value_min: float
    value_max: float
    standard_min: Optional[float]
    standard_max: Optional[float]


CONTENT_MEASUREMENTS: Sequence[MeasurementDefinition] = (
    MeasurementDefinition("主成分含量", "%", 88.0, 112.0, 90.0, 110.0),
    MeasurementDefinition("杂质含量", "%", 0.0, 2.5, 0.0, 2.0),
    MeasurementDefinition("对照品含量对比", "%", 88.0, 112.0, 90.0, 110.0),
)

DISSOLUTION_MEASUREMENTS: Sequence[MeasurementDefinition] = (
    MeasurementDefinition("溶出度", "%", 65.0, 105.0, 75.0, 100.0),
    MeasurementDefinition("释放度", "%", 65.0, 105.0, 75.0, 100.0),
    MeasurementDefinition("累积溶出百分比", "%", 65.0, 105.0, 75.0, 100.0),
)

WATER_MEASUREMENTS: Sequence[MeasurementDefinition] = (
    MeasurementDefinition("水分含量", "%", 0.0, 12.0, 0.0, 10.0),
    MeasurementDefinition("干燥失重", "%", 0.0, 12.5, 0.0, 10.5),
)

HEAVY_METAL_MEASUREMENTS: Sequence[MeasurementDefinition] = (
    MeasurementDefinition("重金属含量", "ppm", 0.0, 15.0, 0.0, 10.0),
    MeasurementDefinition("铅含量", "ppm", 0.0, 10.0, 0.0, 5.0),
    MeasurementDefinition("镉含量", "ppm", 0.0, 5.0, 0.0, 2.0),
)

MICROBIO_MEASUREMENTS: Sequence[MeasurementDefinition] = (
    MeasurementDefinition("菌落总数", "CFU/g", 0.0, 150.0, 0.0, 100.0),
    MeasurementDefinition("霉菌和酵母计数", "CFU/g", 0.0, 60.0, 0.0, 40.0),
    MeasurementDefinition("大肠埃希氏菌检出", "", 0.0, 1.0, 0.0, 0.0),
)

PH_MEASUREMENTS: Sequence[MeasurementDefinition] = (
    MeasurementDefinition("pH值", "", 3.0, 11.0, 4.0, 9.0),
)

IMPURITY_MEASUREMENTS: Sequence[MeasurementDefinition] = (
    MeasurementDefinition("杂质总量", "%", 0.0, 2.5, 0.0, 2.0),
    MeasurementDefinition("单一杂质", "%", 0.0, 1.2, 0.0, 0.8),
    MeasurementDefinition("未知杂质峰面积比", "%", 0.0, 1.0, 0.0, 0.7),
)

SOLVENT_RESIDUE_MEASUREMENTS: Sequence[MeasurementDefinition] = (
    MeasurementDefinition("残留溶剂总量", "ppm", 0.0, 600.0, 0.0, 500.0),
    MeasurementDefinition("乙醇残留量", "ppm", 0.0, 800.0, 0.0, 500.0),
    MeasurementDefinition("丙酮残留量", "ppm", 0.0, 600.0, 0.0, 500.0),
)

PARTICLE_MEASUREMENTS: Sequence[MeasurementDefinition] = (
    MeasurementDefinition("粒径D90", "μm", 5.0, 120.0, 10.0, 100.0),
    MeasurementDefinition("粒径D50", "μm", 2.0, 80.0, 5.0, 60.0),
    MeasurementDefinition("不溶性微粒≥10μm数量", "个/瓶", 0.0, 15.0, 0.0, 12.0),
)

ENDOTOXIN_MEASUREMENTS: Sequence[MeasurementDefinition] = (
    MeasurementDefinition("热原单位", "EU/mL", 0.0, 0.8, 0.0, 0.5),
    MeasurementDefinition("内毒素水平", "EU/mL", 0.0, 1.0, 0.0, 0.5),
)

STERILITY_MEASUREMENTS: Sequence[MeasurementDefinition] = (
    MeasurementDefinition("无菌检出情况", "", 0.0, 1.0, 0.0, 0.0),
    MeasurementDefinition("阴性对照", "", 0.0, 1.0, 0.0, 0.0),
)

GENERAL_MEASUREMENTS: Sequence[MeasurementDefinition] = (
    MeasurementDefinition("实验信噪比", "", 5.0, 80.0, 10.0, 60.0),
    MeasurementDefinition("方法回收率", "%", 85.0, 110.0, 90.0, 105.0),
    MeasurementDefinition("系统适用性", "", 0.0, 1.0, 0.0, 0.0),
)

EXPERIMENT_TYPE_MEASUREMENTS: Dict[str, Sequence[MeasurementDefinition]] = {
    "含量测定": CONTENT_MEASUREMENTS,
    "溶出度测定": DISSOLUTION_MEASUREMENTS,
    "水分测定": WATER_MEASUREMENTS,
    "重金属检查": HEAVY_METAL_MEASUREMENTS,
    "微生物限度检查": MICROBIO_MEASUREMENTS,
    "无菌检查": STERILITY_MEASUREMENTS,
    "浸出物测定": SOLVENT_RESIDUE_MEASUREMENTS,
    "杂质检查": IMPURITY_MEASUREMENTS,
    "有关物质检查": IMPURITY_MEASUREMENTS,
    "残留溶剂测定": SOLVENT_RESIDUE_MEASUREMENTS,
    "pH值测定": PH_MEASUREMENTS,
    "粒度分析": PARTICLE_MEASUREMENTS,
    "不溶性微粒检查": PARTICLE_MEASUREMENTS,
    "装量差异测定": GENERAL_MEASUREMENTS,
    "热原检查": ENDOTOXIN_MEASUREMENTS,
}


def init_openai_client() -> Optional[OpenAI]:
    """
    初始化AI客户端（阿里云 DashScope 兼容模式）。
    未配置密钥时返回 None。
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        logger.info("未检测到环境变量 DASHSCOPE_API_KEY，备注将使用模板生成。")
        return None

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        logger.info("AI客户端初始化成功，可用于生成异常备注。")
        return client
    except Exception as exc:
        logger.warning("AI客户端初始化失败，将改用模板备注: %s", exc)
        return None


def clear_experiment_data_points() -> int:
    """
    清空 experiment_data_points 表。
    返回删除的记录数量。
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM experiment_data_points")
                count_before = cursor.fetchone()[0]
                cursor.execute("DELETE FROM experiment_data_points")
                deleted = cursor.rowcount
                conn.commit()
                logger.info("已删除 %d 条实验数据点（原有 %d 条）。", deleted, count_before)
                return deleted
    except Exception as exc:
        logger.error("清空 experiment_data_points 表失败: %s", exc)
        raise


def fetch_experiment_records(limit: Optional[int] = None) -> List[Dict]:
    """
    读取实验记录，作为数据点的外键来源。
    可通过 limit 限制记录数量，用于调试。
    """
    records: List[Dict] = []
    query = """
        SELECT experiment_id, experiment_type, start_time, end_time, experiment_date
        FROM experiment_records
        ORDER BY experiment_id
    """
    if limit is not None:
        query += " LIMIT %s"
        params: Tuple[int, ...] = (limit,)
    else:
        params = ()

    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                for row in cursor.fetchall():
                    records.append(
                        {
                            "experiment_id": row[0],
                            "experiment_type": row[1],
                            "start_time": row[2],
                            "end_time": row[3],
                            "experiment_date": row[4],
                        }
                    )
    except Exception as exc:
        logger.error("查询实验记录失败: %s", exc)
        raise

    logger.info("已载入 %d 条实验记录用于生成数据点。", len(records))
    return records


def choose_measurement_definitions(experiment_type: Optional[str]) -> Sequence[MeasurementDefinition]:
    """
    根据实验类型选择测量项，若类型未知则返回通用测量项。
    """
    if experiment_type and experiment_type in EXPERIMENT_TYPE_MEASUREMENTS:
        definitions = EXPERIMENT_TYPE_MEASUREMENTS[experiment_type]
        if definitions:
            return definitions
    return GENERAL_MEASUREMENTS


def random_measurements(definitions: Sequence[MeasurementDefinition], count: int) -> List[MeasurementDefinition]:
    """
    从定义列表中随机选择 count 个测量项，若定义数量不足则允许重复。
    """
    if len(definitions) >= count:
        return random.sample(list(definitions), count)
    result: List[MeasurementDefinition] = []
    for _ in range(count):
        result.append(random.choice(list(definitions)))
    return result


def generate_measurement_value(defn: MeasurementDefinition, fail_probability: float = 0.15) -> Tuple[float, bool]:
    """
    为给定测量定义生成测量值，并根据标准范围判定是否合格。
    返回 (measurement_value, is_qualified)。
    """
    standard_min = defn.standard_min
    standard_max = defn.standard_max

    # 若无标准范围，则视为合格
    if standard_min is None or standard_max is None:
        value = random.uniform(defn.value_min, defn.value_max)
        return round(value, 4), True

    is_fail = random.random() < fail_probability
    if is_fail:
        if random.random() < 0.5:
            lower_bound = max(defn.value_min, standard_min - (standard_max - standard_min) * 0.4)
            value = random.uniform(lower_bound, standard_min * 0.99)
        else:
            upper_bound = min(defn.value_max, standard_max + (standard_max - standard_min) * 0.4)
            value = random.uniform(standard_max * 1.01, upper_bound)
        value = max(defn.value_min, min(defn.value_max, value))
        qualified = standard_min <= value <= standard_max
        return round(value, 4), qualified

    center = (standard_min + standard_max) / 2
    deviation = (standard_max - standard_min) / 6
    value = random.gauss(center, deviation)
    value = max(defn.value_min, min(defn.value_max, value))
    qualified = standard_min <= value <= standard_max
    return round(value, 4), qualified


def generate_measurement_time(record: Dict) -> datetime.datetime:
    """
    在实验开始时间后 1-48 小时内生成测量时间。
    如果缺少开始时间，则使用实验日期 09:00 作为基准。
    """
    base_time: Optional[datetime.datetime] = record.get("start_time")
    experiment_date: Optional[datetime.date] = record.get("experiment_date")

    if base_time is None:
        if experiment_date is None:
            experiment_date = datetime.date.today()
        base_time = datetime.datetime.combine(
            experiment_date,
            datetime.time(
                hour=random.randint(8, 11),
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
            ),
        )

    offset_hours = random.uniform(1, 48)
    measurement_time = base_time + datetime.timedelta(hours=offset_hours)
    return measurement_time


def format_unit(unit: str) -> str:
    """统一处理空单位为 ''。"""
    return unit or ""


def generate_note_with_ai(
    client: Optional[OpenAI],
    experiment_type: Optional[str],
    measurement_type: str,
    measurement_value: float,
    standard_min: Optional[float],
    standard_max: Optional[float],
    equipment_id: str,
) -> Optional[str]:
    """
    使用AI生成异常备注。如AI不可用或失败，返回 None。
    """
    if client is None:
        return None

    try:
        min_text = f"{standard_min:.2f}" if standard_min is not None else "未知"
        max_text = f"{standard_max:.2f}" if standard_max is not None else "未知"
        prompt = f"""以下检测数据未能满足标准，请以药检实验室记录口吻生成一条不超过50字的中文备注：
实验类型：{experiment_type or '未知类型'}
测量项目：{measurement_type}
实测值：{measurement_value:.4f}
标准范围：{min_text} ~ {max_text}
使用设备：{equipment_id}
请直接给出备注内容，不要包含前缀。"""

        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {
                    "role": "system",
                    "content": "你是一名药品检验数据分析师，只输出简洁的异常备注。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
        )
        text = completion.choices[0].message.content.strip()
        return text or None
    except Exception as exc:
        logger.debug("AI生成备注失败，使用模板备注: %s", exc)
        return None


def build_template_note(
    measurement_value: float,
    unit: str,
    standard_min: Optional[float],
    standard_max: Optional[float],
    equipment_id: str,
) -> str:
    """
    使用预设模板生成异常备注。
    """
    min_text = f"{standard_min:.2f}" if standard_min is not None else "未知"
    max_text = f"{standard_max:.2f}" if standard_max is not None else "未知"
    unit_text = unit or ""
    template = random.choice(UNQUALIFIED_NOTE_TEMPLATES)
    return template.format(
        value=f"{measurement_value:.4f}",
        unit=unit_text,
        min_bound=min_text,
        max_bound=max_text,
        equipment=equipment_id,
    )


def generate_experiment_data_points(
    per_experiment_range: Tuple[int, int] = (2, 5),
    use_ai: bool = True,
    clear_existing: bool = True,
    limit_experiments: Optional[int] = None,
    batch_size: int = 1000,
    target_total_points: Optional[int] = 500000,
) -> int:
    """
    根据实验记录生成实验数据点，并插入数据库。

    参数:
        per_experiment_range: 每个实验生成的数据点数量范围（闭区间）。
        use_ai: 是否尝试使用AI生成异常备注。
        clear_existing: 是否在生成前清空表。
        limit_experiments: 限制处理的实验数量（调试用）。
        batch_size: 批量插入的数量。
        target_total_points: 目标生成的数据点总数（可选）。

    返回:
        实际插入的数据点数量。
    """
    if per_experiment_range[0] <= 0 or per_experiment_range[1] < per_experiment_range[0]:
        raise ValueError("per_experiment_range 参数不合法。")

    if target_total_points is not None and target_total_points <= 0:
        raise ValueError("target_total_points 必须为正整数。")

    if clear_existing:
        clear_experiment_data_points()

    experiment_records = fetch_experiment_records(limit=limit_experiments)
    if not experiment_records:
        logger.warning("未找到实验记录，无法生成实验数据点。")
        return 0

    client = init_openai_client() if use_ai else None
    connection_pool = get_connection_pool()
    data_point_dao = BaseDAO(connection_pool, "experiment_data_points", "data_id")

    total_inserted = 0
    buffer: List[Dict] = []

    stop_generation = False

    for idx, record in enumerate(experiment_records, start=1):
        if target_total_points is not None and (total_inserted + len(buffer)) >= target_total_points:
            stop_generation = True
            break

        experiment_id = record["experiment_id"]
        experiment_type = record.get("experiment_type")
        definitions = choose_measurement_definitions(experiment_type)
        point_count = random.randint(per_experiment_range[0], per_experiment_range[1])
        if target_total_points is not None:
            remaining = target_total_points - (total_inserted + len(buffer))
            if remaining <= 0:
                stop_generation = True
                break
            point_count = min(point_count, remaining)
            if point_count <= 0:
                continue
        selected_definitions = random_measurements(definitions, point_count)

        for defn in selected_definitions:
            value, qualified = generate_measurement_value(defn)
            measurement_time = generate_measurement_time(record)
            equipment_id = random.choice(EQUIPMENT_IDS)
            notes: Optional[str] = None

            if not qualified and random.random() < 0.7:
                note_text = generate_note_with_ai(
                    client=client,
                    experiment_type=experiment_type,
                    measurement_type=defn.measurement_type,
                    measurement_value=value,
                    standard_min=defn.standard_min,
                    standard_max=defn.standard_max,
                    equipment_id=equipment_id,
                )
                notes = note_text or build_template_note(
                    measurement_value=value,
                    unit=defn.unit,
                    standard_min=defn.standard_min,
                    standard_max=defn.standard_max,
                    equipment_id=equipment_id,
                )
            elif not qualified:
                notes = build_template_note(
                    measurement_value=value,
                    unit=defn.unit,
                    standard_min=defn.standard_min,
                    standard_max=defn.standard_max,
                    equipment_id=equipment_id,
                )
            elif random.random() < 0.05:
                notes = random.choice(
                    (
                        "结果稳定在标准范围内，仪器性能正常。",
                        "数值符合药典标准，记录用于趋势分析。",
                        "检测数据正常，维持现有操作流程。",
                    )
                )

            buffer.append(
                {
                    "experiment_id": experiment_id,
                    "measurement_type": defn.measurement_type,
                    "measurement_value": value,
                    "measurement_unit": format_unit(defn.unit),
                    "standard_min": defn.standard_min,
                    "standard_max": defn.standard_max,
                    "is_qualified": qualified,
                    "measurement_time": measurement_time,
                    "equipment_id": equipment_id,
                    "notes": notes,
                }
            )

        if buffer and len(buffer) >= batch_size:
            inserted = data_point_dao.batch_insert(buffer, batch_size=batch_size)
            total_inserted += inserted
            buffer.clear()

        if stop_generation:
            break

        if idx % 500 == 0:
            logger.info("已处理 %d/%d 条实验记录。", idx, len(experiment_records))

    if buffer:
        inserted = data_point_dao.batch_insert(buffer, batch_size=batch_size)
        total_inserted += inserted
        buffer.clear()

    logger.info("实验数据点生成完成，共插入 %d 条记录。", total_inserted)
    return total_inserted


if __name__ == "__main__":
    inserted_rows = generate_experiment_data_points(
        per_experiment_range=(2, 5),
        use_ai=True,
        clear_existing=True,
        limit_experiments=None,
        batch_size=1000,
    )
    logger.info("本次生成实验数据点条数：%d", inserted_rows)
