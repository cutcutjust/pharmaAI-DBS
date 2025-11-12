"""
生成药检员-实验室访问权限关系数据，
要求真实自然，
使用AI辅助生成，
然后插入数据库

CREATE TABLE inspector_lab_access (
    access_id SERIAL PRIMARY KEY,                       -- 访问ID，主键，自动递增
    inspector_id INT NOT NULL,                          -- 药检员ID，外键，不能为空
    lab_id INT NOT NULL,                                -- 实验室ID，外键，不能为空
    access_level VARCHAR(50),                           -- 权限级别
    granted_date DATE,                                  -- 授权日期
    FOREIGN KEY (inspector_id) REFERENCES inspectors(inspector_id),  -- 关联到inspectors表
    FOREIGN KEY (lab_id) REFERENCES laboratories(lab_id),            -- 关联到laboratories表
    UNIQUE(inspector_id, lab_id)                        -- 一个药检员和某实验室的对应关系唯一
);



## 🔗 第二阶段：关联基础数据生成

### 4. 药检员-实验室访问权限关系表 (inspector_lab_access)

**目标数量**：约 800 条

**数据要求**：

- **关系生成策略**：
  - 从已生成的药检员和实验室中随机组合
  - 确保每个组合唯一（一个药检员对一个实验室只有一条记录）
  - 一个药检员可以访问多个实验室（N-M关系）
  - 一个实验室可以被多个药检员访问
- **权限级别**：从4个级别中随机分配
  - 只读权限、操作权限、管理权限、完全权限
- **授权日期**：范围2018-2025年，随机生成

**字段存储格式详细说明**：

| 字段名           | SQL类型     | 是否必填 | 存储格式                          | 示例值                                         | 说明                           |
| ---------------- | ----------- | -------- | --------------------------------- | ---------------------------------------------- | ------------------------------ |
| `access_id`    | SERIAL      | 自动生成 | 整数，自动递增                    | 1, 2, 3...                                     | 主键，插入时不需要提供         |
| `inspector_id` | INT         | 必填     | 整数，引用inspectors.inspector_id | 1, 2, 3...                                     | 药检员ID，外键，必须已存在     |
| `lab_id`       | INT         | 必填     | 整数，引用laboratories.lab_id     | 1, 2, 3...                                     | 实验室ID，外键，必须已存在     |
| `access_level` | VARCHAR(50) | 可选     | 中文字符串                        | "只读权限", "操作权限", "管理权限", "完全权限" | 权限级别，可为NULL，最大50字符 |
| `granted_date` | DATE        | 可选     | 日期格式：YYYY-MM-DD              | "2018-05-10", "2023-12-20"                     | 授权日期，可为NULL             |

**SQL插入示例**：

```sql
INSERT INTO inspector_lab_access (inspector_id, lab_id, access_level, granted_date)
VALUES (1, 1, '操作权限', '2020-03-15');
```

**注意事项**：

- 必须确保 `inspector_id` 和 `lab_id` 的组合唯一，插入前需检查
- 外键必须引用已存在的药检员和实验室（先执行inspectors和laboratories的插入）
- `access_id` 由数据库自动生成，无需手动设置
- 关系数量应合理，平均每个药检员访问5-6个实验室，每个实验室被20-30个药检员访问

"""

import os
import sys
import random
import datetime
from pathlib import Path
from typing import Dict, Set, Tuple

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
ACCESS_LEVELS = ['只读权限', '操作权限', '管理权限', '完全权限']


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


def generate_granted_date() -> str:
    """
    生成随机授权日期（2018-2025年）
    
    返回:
        str: 日期字符串，格式YYYY-MM-DD
    """
    year = random.randint(2018, 2025)
    month = random.randint(1, 12)
    day = random.randint(1, 28)  # 使用28避免月份天数问题
    return datetime.date(year, month, day).isoformat()


def generate_access_level_with_ai(client: OpenAI, inspector_info: Dict, lab_info: Dict) -> str:
    """
    使用AI生成权限级别（根据药检员和实验室信息）
    
    参数:
        client: OpenAI客户端
        inspector_info: 药检员信息字典，包含department, title, certification_level等
        lab_info: 实验室信息字典，包含lab_name, certification, equipment_level等
        
    返回:
        str: 权限级别
    """
    try:
        prompt = f"""请为以下药检员和实验室的组合生成一个合理的权限级别，要求：
1. 药检员信息：
   - 部门：{inspector_info.get('department', '未知')}
   - 职称：{inspector_info.get('title', '未知')}
   - 资质等级：{inspector_info.get('certification_level', '未知')}
   
2. 实验室信息：
   - 实验室名称：{lab_info.get('lab_name', '未知')}
   - 认证类型：{lab_info.get('certification', '未知')}
   - 设备等级：{lab_info.get('equipment_level', '未知')}

请从以下4个权限级别中选择一个最合适的：
- 只读权限：只能查看实验室信息，不能进行操作
- 操作权限：可以进行常规实验操作
- 管理权限：可以管理实验室的日常运营
- 完全权限：拥有实验室的所有权限

只返回权限级别名称，不要其他说明文字。例如：操作权限"""

        completion = client.chat.completions.create(
            model="qwen-flash",
            messages=[
                {'role': 'system', 'content': '你是一个数据生成助手，只返回权限级别名称，不要其他说明文字。'},
                {'role': 'user', 'content': prompt}
            ],
            temperature=0.7
        )
        
        response_text = completion.choices[0].message.content.strip()
        
        # 打印AI生成的内容
        logger.info(f"AI生成权限级别：{response_text}")
        
        # 验证返回的权限级别是否有效
        if response_text in ACCESS_LEVELS:
            return response_text
        else:
            # 如果AI返回的不是有效值，使用随机生成
            logger.warning(f"AI返回的权限级别无效：{response_text}，使用随机生成")
            return random.choice(ACCESS_LEVELS)
        
    except Exception as e:
        logger.warning(f"AI生成权限级别失败，使用随机生成: {e}")
        return random.choice(ACCESS_LEVELS)


def clear_inspector_lab_access_table() -> int:
    """
    清空inspector_lab_access表的所有数据
    
    返回:
        int: 删除的记录数量
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM inspector_lab_access")
                count_before = cursor.fetchone()[0]
                
                cursor.execute("DELETE FROM inspector_lab_access")
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"已删除 {deleted_count} 条访问权限数据（删除前共有 {count_before} 条）")
                return deleted_count
    except Exception as e:
        logger.error(f"清空inspector_lab_access表失败: {str(e)}")
        raise


def generate_lab_access_data(count: int = 800, use_ai: bool = True, clear_existing: bool = True) -> int:
    """
    生成药检员-实验室访问权限关系数据并插入数据库
    
    参数:
        count: 要生成的权限关系数量，默认800
        use_ai: 是否使用AI辅助生成权限级别，默认True
        clear_existing: 是否在生成前清空现有数据，默认True
        
    返回:
        int: 实际插入的记录数量
    """
    logger.info(f"开始生成药检员-实验室访问权限关系数据，目标数量：{count}条，使用AI：{use_ai}")
    
    # 如果指定清空现有数据，先删除所有记录
    if clear_existing:
        try:
            clear_inspector_lab_access_table()
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
    
    # 查询现有药检员和实验室ID
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                # 查询所有药检员信息
                cursor.execute("""
                    SELECT inspector_id, department, title, certification_level 
                    FROM inspectors
                """)
                inspectors = []
                for row in cursor.fetchall():
                    inspectors.append({
                        'inspector_id': row[0],
                        'department': row[1],
                        'title': row[2],
                        'certification_level': row[3]
                    })
                
                # 查询所有实验室信息
                cursor.execute("""
                    SELECT lab_id, lab_name, certification, equipment_level 
                    FROM laboratories
                """)
                laboratories = []
                for row in cursor.fetchall():
                    laboratories.append({
                        'lab_id': row[0],
                        'lab_name': row[1],
                        'certification': row[2],
                        'equipment_level': row[3]
                    })
                
                if not inspectors or not laboratories:
                    logger.error("药检员或实验室数据不存在，请先生成基础数据")
                    return 0
                
                inspector_ids = [inspector['inspector_id'] for inspector in inspectors]
                lab_ids = [lab['lab_id'] for lab in laboratories]
                
                logger.info(f"找到 {len(inspector_ids)} 个药检员和 {len(lab_ids)} 个实验室")
                
                # 检查数据库中已存在的组合
                existing_combinations = set()
                try:
                    cursor.execute("SELECT inspector_id, lab_id FROM inspector_lab_access")
                    existing_combinations = {(row[0], row[1]) for row in cursor.fetchall()}
                    logger.info(f"数据库中已存在 {len(existing_combinations)} 个权限关系")
                except Exception as e:
                    logger.warning(f"查询已存在权限关系失败: {e}")
            
            # 计算最大可能的组合数
            max_combinations = len(inspector_ids) * len(lab_ids)
            target_count = min(count, max_combinations - len(existing_combinations))
            
            if target_count <= 0:
                logger.warning("已达到最大组合数，无法生成更多权限关系")
                return 0
            
            logger.info(f"目标生成 {target_count} 条新的权限关系")
            
            # 生成唯一的药检员-实验室组合
            access_relationships: Set[Tuple[int, int]] = set()
            attempts = 0
            max_attempts = target_count * 10  # 最多尝试次数
            
            while len(access_relationships) < target_count and attempts < max_attempts:
                inspector_id = random.choice(inspector_ids)
                lab_id = random.choice(lab_ids)
                combination = (inspector_id, lab_id)
                
                # 跳过已存在的组合
                if combination not in existing_combinations and combination not in access_relationships:
                    access_relationships.add(combination)
                
                attempts += 1
            
            if len(access_relationships) < target_count:
                logger.warning(f"只生成了 {len(access_relationships)} 个唯一组合，低于目标 {target_count}")
            
            # 创建药检员和实验室信息的映射（用于AI生成）
            inspector_map = {insp['inspector_id']: insp for insp in inspectors}
            lab_map = {lab['lab_id']: lab for lab in laboratories}
            
            # 生成权限数据
            lab_access_list = []
            generated_count = 0
            
            for inspector_id, lab_id in access_relationships:
                # 使用AI生成权限级别或随机生成
                if use_ai and client:
                    inspector_info = inspector_map.get(inspector_id, {})
                    lab_info = lab_map.get(lab_id, {})
                    access_level = generate_access_level_with_ai(client, inspector_info, lab_info)
                else:
                    access_level = random.choice(ACCESS_LEVELS)
                
                granted_date = generate_granted_date()
                
                lab_access = {
                    "inspector_id": inspector_id,
                    "lab_id": lab_id,
                    "access_level": access_level,
                    "granted_date": granted_date
                }
                lab_access_list.append(lab_access)
                generated_count += 1
                
                if generated_count % 50 == 0:
                    logger.info(f"已生成 {generated_count}/{len(access_relationships)} 条权限关系数据")
            
            if not lab_access_list:
                logger.warning("没有生成任何权限关系数据")
                return 0
            
            # 批量插入数据库
            try:
                connection_pool = get_connection_pool()
                access_dao = BaseDAO(connection_pool, 'inspector_lab_access', 'access_id')
                
                inserted_count = access_dao.batch_insert(
                    lab_access_list,
                    batch_size=100,
                    on_conflict="(inspector_id, lab_id) DO NOTHING"
                )
                
                logger.info(f"成功插入 {inserted_count} 条药检员-实验室访问权限关系数据")
                
                # 统计信息
                if inserted_count > 0:
                    avg_labs_per_inspector = inserted_count / len(inspector_ids) if inspector_ids else 0
                    avg_inspectors_per_lab = inserted_count / len(lab_ids) if lab_ids else 0
                    logger.info(f"统计信息：平均每个药检员访问 {avg_labs_per_inspector:.2f} 个实验室，"
                              f"平均每个实验室被 {avg_inspectors_per_lab:.2f} 个药检员访问")
                
                return inserted_count
                
            except Exception as e:
                logger.error(f"插入权限关系数据失败: {str(e)}")
                raise
                
    except Exception as e:
        logger.error(f"生成权限关系数据失败: {str(e)}")
        raise
    
    return 0


if __name__ == "__main__":
    # 生成800条药检员-实验室访问权限关系数据
    generate_lab_access_data(count=800, use_ai=True, clear_existing=True)
