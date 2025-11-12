"""
结合ai实现数据生成，生成药典条目表的数据，要求生成的数据符合药典条目表的格式要求，并符合药典条目表的约束条件。

pharmaAI-DBS\data_generator\中华人民共和国药典2025版全四部文本\第一部\docID49155_一枝黄花_第一部.txt文本内容如下：
一枝黄花
一枝黄花
Yizhihuɑnghuɑ
SOLIDAGINIS HERBA
本品为菊科植物一枝黄花
Solidago decurrens
Lour.的干燥全草。秋季花果期采挖，除去泥沙，晒干。
【性状】
......

pharmaAI-DBS\data_generator\中华人民共和国药典2025版全四部文本\第一部\1药典沿革.txt
......
pharmaAI-DBS\data_generator\中华人民共和国药典2025版全四部文本\第一部\docID49156_丁公藤_第一部.txt
......
pharmaAI-DBS\data_generator\中华人民共和国药典2025版全四部文本\第一部\docID51433_蠲哮片_第一部.txt




2025药典第一部：
药材和饮片:
id=1&docid=49155
...
id=1&docid=49770
植物油脂和提取物:
id=1&docid=49771
...
id=1&docid=49817
成方制剂和单味制剂:
id=1&docid=49818
...
id=1&docid=51433
一共2278个条目

2025药典第二部：
第一部分:
示例：二甲双胍格列本脲片（Ⅰ）
Erjiashuanggua Geliebenniao Pian（Ⅰ）
Metformin Hydrochloride and Glibenclamide Tablets（Ⅰ）
本品含盐酸二甲双胍（C4H11N5•HCl）应为标示量的95.0%~105.0%；含格列本脲（C23H28ClN3O5S）应为标示量的90.0%~110.0%。
【处方】【性状】【鉴别】【检查】【含量测定】【类别】【贮藏】等待
id=2&docid=51439
...
id=2&docid=54183

第二部分：
示例：锝［99mTc］双半胱乙酯注射液
De［99mTc］Shuangbanguangyizhi Zhusheye
Technetium［99mTc］Bicisate Injection
C12H21N2O5S299mTc　436.30
本品为锝［99mTc］标记的（2R）-2-［2-［［（2R）-1-乙氧基-1-氧代-3-巯基丙-2-基］氨基］乙氨基］-3-巯基丙酸乙酯的无菌溶液。
含锝［99mTc］的放射性活度，按其标签上记载的时间，应为标示量的90.0%~110.0%。
【制法】【性状】【鉴别】【检查】【放射化学纯度】【放射性活度】【类别】等待
id=2&docid=54184
...
id=2&docid=54215
一共2776个条目

2025药典第三部：
品种正文：
示例：冻干甲型肝炎减毒活疫苗
Donggan Jiaxing Ganyan Jiandu Huoyimiao
Hepatitis A（Live）Vaccine，Freeze-dried
本品系用甲型肝炎（简称甲肝）病毒减毒株接种人二倍体细胞，经培养、收获、提取病毒后，加入适宜稳定剂冻干制成。
用于预防甲型肝炎。
1　基本要求/2　制造/3　检定/4　疫苗稀释剂/5　保存、运输及有效期/6　使用说明/等待
id=3&docid=54231
......
id=3&docid=54383

通则与指导原则：
id=3&docid=54384
......
id=3&docid=54599
一共368个条目

2025药典第四部：
通用技术要求和指导原则：
id=4&docid=54610
...
id=4&docid=55082

药用辅料/品种正文:
示例：十二烷基硫酸钠
Shi’er Wanji Liusuanna
Sodium Lauryl Sulfate
[151-21-3]
本品为以十二烷基硫酸钠（C12H25NaO4S）为主的烷基硫酸钠混合物。
【性状】【鉴别】【检查】【类别】【贮藏】【标示】等
id=4&docid=55083
...
id=4&docid=55469
一共859个条目



### 1. 药典条目表 (pharmacopoeia_items)

**目标数量**：约 6,000 条

**数据要求**：

- **卷号分布**：
  - 第一部（volume=1）：约 2,280 条（38%），包含药材和饮片、植物油脂和提取物、成方制剂和单味制剂
  - 第二部（volume=2）：约 2,760 条（46%），包含化学药品、抗生素、生化药品等
  - 第三部（volume=3）：约 360 条（6%），包含生物制品、疫苗、通则和指导原则
  - 第四部（volume=4）：约 600 条（10%），包含药用辅料、通则、指导原则
- **文档ID范围**：
  - 第一部：doc_id 从 49155 到 51433
  - 第二部：doc_id 从 51439 到 54215
  - 第三部：doc_id 从 54231 到 54599
  - 第四部：doc_id 从 54610 到 55469
- **字段要求**：
  - `name_cn`：中文名称，格式如"药典条目{doc_id}"或实际药品名称
  - `name_pinyin`：拼音名称，格式如"Yaodian Tiaoyue {doc_id}"
  - `name_en`：英文名称，格式如"Pharmacopoeia Item {doc_id}"
  - `category`：根据卷号分配相应分类（药材和饮片、化学药品、生物制品、药用辅料等）
  - `content`：详细内容描述，包含卷号、文档ID和类别信息
  - `volume` 和 `doc_id` 组合必须唯一

**字段存储格式详细说明**：

| 字段名          | SQL类型      | 是否必填 | 存储格式                        | 示例值                                 | 说明                        |
| --------------- | ------------ | -------- | ------------------------------- | -------------------------------------- | --------------------------- |
| `item_id`     | SERIAL       | 自动生成 | 整数，自动递增                  | 1, 2, 3...                             | 主键，插入时不需要提供      |
| `volume`      | INT          | 必填     | 整数，范围1-4                   | 1, 2, 3, 4                             | 药典卷号，必须为1/2/3/4之一 |
| `doc_id`      | INT          | 必填     | 整数，根据卷号范围              | 49155, 51439, 54231, 54610             | 文档ID，与volume组合唯一    |
| `name_cn`     | VARCHAR(200) | 必填     | 中文字符串，最大200字符         | "药典条目49155", "人参"                | 中文名称，不能为空          |
| `name_pinyin` | VARCHAR(200) | 可选     | 拼音字符串，最大200字符         | "Yaodian Tiaomu 49155", "Renshen"     | 拼音名称，可为NULL          |
| `name_en`     | VARCHAR(200) | 可选     | 英文字符串，最大200字符         | "Pharmacopoeia Item 49155", "Ginseng"  | 英文名称，可为NULL          |
| `category`    | VARCHAR(100) | 可选     | 中文字符串，最大100字符         | "药材和饮片", "化学药品"               | 分类信息，可为NULL          |
| `content`     | TEXT         | 可选     | 文本字符串，无长度限制          | "药典第1部 文档ID 49155 的详细内容..." | 详细内容，可为NULL          |
| `created_at`  | TIMESTAMP    | 自动生成 | 时间戳格式：YYYY-MM-DD HH:MM:SS | "2025-01-15 10:30:00"                  | 创建时间，默认当前时间      |

**SQL插入示例**：

```sql
INSERT INTO pharmacopoeia_items (volume, doc_id, name_cn, name_pinyin, name_en, category, content)
VALUES (1, 49155, '药典条目49155', 'Yaodian Tiaoyue 49155', 'Pharmacopoeia Item 49155', '药材和饮片', '药典第1部 文档ID 49155 的详细内容...');
```

**注意事项**：

- 这是所有其他表的外键引用源，必须首先生成
- 数据应覆盖四部药典的所有主要类别
- `volume` 和 `doc_id` 组合必须唯一，插入前需检查
- `item_id` 和 `created_at` 由数据库自动生成，无需手动设置
"""
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import get_connection_pool, get_connection
from database import init_database
from dao.base_dao import BaseDAO
from utils.logger import get_logger
from utils.db_statistics import (
    log_pharmacopoeia_items_stats_from_records,
    log_pharmacopoeia_items_stats_from_db,
)

# 获取日志记录器
logger = get_logger(__name__)

# 药典文本文件根目录
PHARMACOPOEIA_TEXT_DIR = Path(__file__).parent / "中华人民共和国药典2025版全四部文本"
# 调试：验证基础目录是否存在
if not PHARMACOPOEIA_TEXT_DIR.exists():
    logger.warning(f"药典文本目录不存在: {PHARMACOPOEIA_TEXT_DIR}")
    logger.warning(f"请确认目录路径是否正确")

# 卷号到分类的映射
VOLUME_CATEGORIES = {
    1: ['药材和饮片', '植物油脂和提取物', '成方制剂和单味制剂'],
    2: ['化学药品', '放射性药品'],
    3: ['生物制品', '通则与指导原则'],
    4: ['通用技术要求和指导原则', '药用辅料']
}

# 根据注释定义的 doc_id 范围与对应分类
CATEGORY_RULES = [
    {'volume': 1, 'start': 49155, 'end': 49770, 'category': '药材和饮片'},
    {'volume': 1, 'start': 49771, 'end': 49817, 'category': '植物油脂和提取物'},
    {'volume': 1, 'start': 49818, 'end': 51433, 'category': '成方制剂和单味制剂'},
    {'volume': 2, 'start': 51439, 'end': 54183, 'category': '化学药品'},
    {'volume': 2, 'start': 54184, 'end': 54215, 'category': '放射性药品'},
    {'volume': 3, 'start': 54231, 'end': 54383, 'category': '生物制品'},
    {'volume': 3, 'start': 54384, 'end': 54599, 'category': '通则与指导原则'},
    {'volume': 4, 'start': 54610, 'end': 55082, 'category': '通用技术要求和指导原则'},
    {'volume': 4, 'start': 55083, 'end': 55469, 'category': '药用辅料'}
]

def parse_filename(filename: str) -> Optional[Dict[str, int]]:
    """
    从文件名解析 doc_id 和 volume
    
    文件名格式：docID{数字}_{名称}_{第X部}.txt
    
    参数:
        filename: 文件名
        
    返回:
        包含 doc_id 和 volume 的字典，如果解析失败返回 None
    """
    # 匹配 docID{数字} 的模式
    doc_id_match = re.search(r'docID(\d+)', filename)
    if not doc_id_match:
        return None
    
    doc_id = int(doc_id_match.group(1))
    
    # 从文件名或路径判断卷号
    volume = None
    if '第一部' in filename or '第1部' in filename:
        volume = 1
    elif '第二部' in filename or '第2部' in filename:
        volume = 2
    elif '第三部' in filename or '第3部' in filename:
        volume = 3
    elif '第四部' in filename or '第4部' in filename:
        volume = 4
    
    if volume is None:
        # 根据 doc_id 范围判断卷号
        if 49155 <= doc_id <= 51433:
            volume = 1
        elif 51439 <= doc_id <= 54215:
            volume = 2
        elif 54231 <= doc_id <= 54599:
            volume = 3
        elif 54610 <= doc_id <= 55469:
            volume = 4
    
    if volume is None:
        logger.warning(f"无法确定卷号，文件名: {filename}, doc_id: {doc_id}")
        return None
    
    return {'doc_id': doc_id, 'volume': volume}


def parse_file_content(file_path: Path) -> Dict[str, str]:
    """
    解析药典文本文件内容
    
    文件格式：
    第一行：中文名
    第二行：中文名（重复）
    第三行：拼音
    第四行：英文名
    第五行开始：详细内容
    
    参数:
        file_path: 文件路径
        
    返回:
        包含 name_cn, name_pinyin, name_en, content 的字典
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        
        if len(lines) < 1:
            return {
                'name_cn': '',
                'name_pinyin': None,
                'name_en': None,
                'content': ''
            }
        
        # 第一行是中文名
        name_cn = lines[0] if lines else ''
        
        # 第三行是拼音（索引2）
        name_pinyin = lines[2] if len(lines) > 2 else None
        
        # 第四行是英文名（索引3）
        name_en = lines[3] if len(lines) > 3 else None
        
        # 第五行开始是详细内容（索引4开始）
        content = '\n'.join(lines[4:]) if len(lines) > 4 else ''
        
        # 如果内容为空，使用前几行作为内容
        if not content and len(lines) > 1:
            content = '\n'.join(lines[1:])
        
        return {
            'name_cn': name_cn[:200],  # 限制长度
            'name_pinyin': name_pinyin[:200] if name_pinyin else None,
            'name_en': name_en[:200] if name_en else None,
            'content': content
        }
    except Exception as e:
        logger.error(f"解析文件失败 {file_path}: {e}")
        return {
            'name_cn': '',
            'name_pinyin': None,
            'name_en': None,
            'content': ''
        }


def determine_category(name_cn: str, content: str, volume: int, doc_id: int) -> Optional[str]:
    """
    根据 doc_id 范围及文本内容确定分类
    
    参数:
        name_cn: 中文名称
        content: 详细内容
        volume: 卷号
        doc_id: 文档ID
        
    返回:
        分类字符串
    """
    # 优先根据注释提供的 doc_id 范围确定分类
    for rule in CATEGORY_RULES:
        if rule['volume'] == volume and rule['start'] <= doc_id <= rule['end']:
            return rule['category']
    
    # 如果没有匹配到，根据卷号返回默认分类
    default_categories = {
        1: '药材和饮片',
        2: '化学药品',
        3: '生物制品',
        4: '通用技术要求和指导原则'
    }
    return default_categories.get(volume, None)


def load_pharmacopoeia_files(volume: Optional[int] = None) -> List[Dict]:
    """
    加载药典文本文件并解析为数据字典列表
    
    参数:
        volume: 可选的卷号，如果指定则只加载该卷的文件
        
    返回:
        药典条目数据列表
    """
    items = []
    
    # 确定要处理的卷号列表
    volumes = [volume] if volume else [1, 2, 3, 4]
    
    # 卷号到中文目录名的映射
    volume_names = {1: '第一部', 2: '第二部', 3: '第三部', 4: '第四部'}
    
    for vol in volumes:
        volume_dir = PHARMACOPOEIA_TEXT_DIR / volume_names[vol]
        
        # 调试信息：打印路径信息
        logger.debug(f"检查目录: {volume_dir}")
        logger.debug(f"目录绝对路径: {volume_dir.resolve()}")
        logger.debug(f"基础目录存在: {PHARMACOPOEIA_TEXT_DIR.exists()}")
        
        if not volume_dir.exists():
            logger.warning(f"目录不存在: {volume_dir}")
            logger.warning(f"请检查路径是否正确，期望的目录名应该是: {volume_names[vol]}")
            continue
        
        logger.info(f"开始处理第{vol}部药典文件，目录: {volume_dir}")
        
        # 遍历目录下的所有txt文件
        txt_files = list(volume_dir.glob("*.txt"))
        logger.info(f"找到 {len(txt_files)} 个文本文件")
        
        for file_path in txt_files:
            # 跳过目录文件
            if '目录' in file_path.name:
                continue
            
            # 若文件名中不含字符"doci"则跳过
            if 'doci' not in file_path.name.lower():
                continue
            
            # 解析文件名获取 doc_id 和 volume
            file_info = parse_filename(file_path.name)
            if not file_info:
                logger.warning(f"无法解析文件名: {file_path.name}")
                continue
            
            doc_id = file_info['doc_id']
            file_volume = file_info['volume']
            
            # 验证 doc_id 范围
            valid_ranges = {
                1: (49155, 51433),
                2: (51439, 54215),
                3: (54231, 54599),
                4: (54610, 55469)
            }
            min_id, max_id = valid_ranges.get(file_volume, (0, 0))
            if not (min_id <= doc_id <= max_id):
                logger.warning(f"doc_id {doc_id} 不在第{file_volume}部的有效范围内 ({min_id}-{max_id})")
                continue
            
            # 解析文件内容
            content_data = parse_file_content(file_path)
            
            # 确定分类
            category = determine_category(
                content_data['name_cn'],
                content_data['content'],
                file_volume,
                doc_id
            )
            
            # 构建数据字典
            item = {
                'volume': file_volume,
                'doc_id': doc_id,
                'name_cn': content_data['name_cn'] or f"药典条目{doc_id}",
                'name_pinyin': content_data['name_pinyin'],
                'name_en': content_data['name_en'],
                'category': category,
                'content': content_data['content']
            }
            
            items.append(item)
    
    logger.info(f"共加载 {len(items)} 条药典条目数据")
    return items


def generate_pharmacopoeia_items(volume: Optional[int] = None, batch_size: int = 1000) -> int:
    """
    生成药典条目数据并插入数据库
    
    参数:
        volume: 可选的卷号，如果指定则只生成该卷的数据
        batch_size: 批量插入的大小
        
    返回:
        实际插入的记录数量
    """
    logger.info("开始生成药典条目数据...")
    
    try:
        # 检查并初始化数据库表（如果不存在）
        try:
            with get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'pharmacopoeia_items'
                        )
                    """)
                    table_exists = cursor.fetchone()[0]
                    
                    if not table_exists:
                        logger.info("检测到 pharmacopoeia_items 表不存在，开始初始化数据库...")
                        if not init_database(drop_existing=False):
                            raise RuntimeError("数据库初始化失败，无法继续生成数据")
                        logger.info("数据库表初始化完成")
                    else:
                        logger.debug("pharmacopoeia_items 表已存在，跳过初始化")
        except Exception as e:
            logger.warning(f"检查表存在性时出错: {e}，尝试初始化数据库...")
            if not init_database(drop_existing=False):
                raise RuntimeError("数据库初始化失败，无法继续生成数据")
        
        # 再次验证表是否存在（确保初始化成功）
        try:
            with get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'pharmacopoeia_items'
                        )
                    """)
                    table_exists = cursor.fetchone()[0]
                    if not table_exists:
                        raise RuntimeError("pharmacopoeia_items 表不存在，无法继续生成数据")
        except Exception as e:
            logger.error(f"验证表存在性失败: {e}")
            raise
        
        # 加载药典文件数据
        items = load_pharmacopoeia_files(volume)
        
        if not items:
            logger.warning("没有加载到任何药典条目数据")
            return 0
        
        # 连接数据库并插入数据
        connection_pool = get_connection_pool()
        dao = BaseDAO(connection_pool, 'pharmacopoeia_items', 'item_id')
        
        # 检查已存在的记录，避免重复插入
        existing_items = dao.execute_query(
            "SELECT volume, doc_id FROM pharmacopoeia_items"
        )
        existing_set = {(item['volume'], item['doc_id']) for item in existing_items}

        # 统计并记录现有数据分布
        existing_total, _ = log_pharmacopoeia_items_stats_from_records(
            existing_items,
            logger=logger,
            header="数据库中现有记录统计:"
        )

        # 过滤掉已存在的记录
        new_items = [
            item for item in items
            if (item['volume'], item['doc_id']) not in existing_set
        ]

        if not new_items:
            logger.info(
                "所有药典条目数据已存在，无需插入（数据库中共有 %d 条记录，文件中共有 %d 条）",
                existing_total,
                len(items)
            )
            return 0

        logger.info(f"准备插入 {len(new_items)} 条新记录（共 {len(items)} 条，已存在 {len(items) - len(new_items)} 条）")

        # 批量插入，使用 ON CONFLICT 处理可能的重复（虽然已经过滤，但作为保险）
        # 注意：pharmacopoeia_items 表有 UNIQUE(volume, doc_id) 约束
        inserted_count = dao.batch_insert(
            new_items,
            batch_size=1000,
            on_conflict="(volume, doc_id) DO NOTHING"
        )

        logger.info(f"成功插入 {inserted_count} 条药典条目数据")

        # 显示最终统计信息
        if inserted_count > 0:
            log_pharmacopoeia_items_stats_from_db(
                dao,
                logger=logger,
                header="数据库最终记录统计:"
            )

        return inserted_count
            
    except Exception as e:
        logger.error(f"生成药典条目数据失败: {str(e)}")
        raise


if __name__ == "__main__":
    # 生成所有四部药典的数据
    generate_pharmacopoeia_items()
    
    # 或者只生成某一部
    # generate_pharmacopoeia_items(volume=1)  # 只生成第一部