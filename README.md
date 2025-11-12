# 智药AI (PharmaAI-DBS)

智药AI是一个基于AI对话和关系型数据库的智能药典平台，通过10万+条对话数据驱动的智能问答系统，结合实验记录管理和药品信息检索，为药检员提供智能化的药品检验和数据管理服务。本项目是数据库系统原理课程的实践项目。

## 项目概述

本系统实现了三个主要功能模块：

1. **实验记录管理** - 提供实验记录的创建、查询、修改和删除功能，支持实验数据点的详细记录
2. **对话查询** - 提供药检员与系统的对话历史查询功能，支持按药检员、时间范围、关键词等条件查询
3. **系统配置** - 提供系统配置参数的管理功能，展示1-1关系设计（config_key作为主键）

## 系统架构

系统采用经典的三层架构：

- **表示层** - 基于Flask的Web应用，提供用户界面
- **业务逻辑层** - 实现服务和业务逻辑处理
- **数据访问层** - 提供数据库操作接口

## 技术栈

- **后端**：Python 3.8+
- **Web框架**：Flask
- **数据库**：PostgreSQL
- **前端**：HTML5, CSS3, JavaScript, Bootstrap 5
- **其他**：Jinja2模板引擎, SQLAlchemy ORM

## 安装指南

### 环境要求

- Python 3.8 或更高版本
- pip 包管理器

### 安装步骤

1. 克隆仓库

```bash
git clone https://github.com/yourusername/pharmaAI-DBS.git
cd pharmaAI-DBS
```

2. 创建并激活虚拟环境

```bash
# 使用venv
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

3. 安装依赖

```bash
pip install -r requirements.txt
```

4. 初始化数据库

```bash
python main.py --init-db
```

## 使用方法

### 启动系统

```bash
python main.py
```

或者指定主机和端口:

```bash
python main.py --host 127.0.0.1 --port 8080
```

### 命令行参数

- `--init-db`: 初始化数据库(创建表和索引)
- `--run-web`: 仅运行Web应用
- `--run-tests`: 运行系统测试
- `--host HOST`: Web应用主机地址，默认0.0.0.0
- `--port PORT`: Web应用端口号，默认5000
- `--debug`: 启用Web应用调试模式

### 访问Web界面

启动系统后，通过浏览器访问:

- 首页: http://localhost:5000/
- 实验管理: http://localhost:5000/experiments
- 对话查询: http://localhost:5000/conversations
- 系统配置: http://localhost:5000/settings

## 项目结构

```
pharmaAI-DBS/
│
├── main.py                   # 主入口点
├── requirements.txt          # 项目依赖
├── pharmacopoeia.db          # SQLite数据库文件
│
├── config/                   # 配置模块
│   ├── __init__.py
│   ├── database.py           # 数据库连接配置
│   └── settings.py           # 系统配置参数
│
├── database/                 # 数据库脚本
│   ├── __init__.py
│   ├── schema.sql            # 建表SQL脚本
│   ├── indexes.sql           # 索引创建脚本
│   ├── connection.py         # 连接池管理
│   └── test_db_connection.py # 数据库连接测试
│
├── models/                   # 数据模型
│   ├── __init__.py
│   ├── base.py               # 基础模型和数据库连接
│   ├── inspector.py          # 药检员模型
│   ├── pharmacopoeia.py      # 药典条目模型
│   ├── conversation.py       # 对话模型
│   ├── message.py            # 消息模型
│   └── experiment.py         # 实验记录模型
│
├── dao/                      # 数据访问层
│   ├── __init__.py
│   ├── base_dao.py           # 基础DAO（通用CRUD）
│   ├── inspector_dao.py      # 药检员数据访问
│   ├── conversation_dao.py   # 对话数据访问
│   ├── message_dao.py        # 消息数据访问
│   └── experiment_dao.py     # 实验数据访问
│
├── services/                 # 业务服务层
│   ├── __init__.py
│   ├── query_service.py      # 查询服务
│   ├── transaction_service.py # 事务服务
│   ├── data_generator.py     # 测试数据生成服务
│   └── performance_monitor.py # 性能监控服务
│
├── data_generator/           # 数据生成模块
│   ├── __init__.py
│   ├── generate_inspectors_data_Step1.py      # 生成药检员数据
│   ├── generate_laboratories_data_Step1.py    # 生成实验室数据
│   ├── generate_phamarcopoeia_data_Step1.py   # 生成药典数据
│   ├── generate_lab_access_Step2.py           # 生成实验室权限数据
│   ├── generate_conversation_data_Step3.py    # 生成对话数据
│   ├── generate_message_data_Step3.py         # 生成消息数据
│   ├── generate_experiment_records_Step3.py   # 生成实验记录
│   ├── generate_experiment_data_points_Step3.py # 生成实验数据点
│   ├── generate_config_data_Step4.py          # 生成系统配置
│   ├── data/                 # 生成的CSV数据文件
│   └── 中华人民共和国药典2025版全四部文本/  # 药典原始数据
│
├── web/                      # Web应用
│   ├── __init__.py
│   ├── app.py                # Flask应用创建
│   ├── routes/               # 路由处理
│   │   ├── __init__.py
│   │   ├── conversation_routes.py  # 对话查询路由
│   │   ├── experiment_routes.py    # 实验管理路由
│   │   └── settings_routes.py      # 系统配置路由
│   ├── templates/            # 页面模板
│   │   ├── base.html         # 基础模板
│   │   ├── index.html        # 首页
│   │   ├── experiment_manage.html    # 实验管理页面
│   │   ├── conversation_search.html  # 对话查询页面
│   │   ├── settings.html     # 系统配置页面
│   │   └── readme.html       # 说明文档页面
│   ├── static/               # 静态资源
│   │   ├── css/
│   │   │   └── style.css     # 样式文件
│   │   ├── js/
│   │   │   └── main.js       # JavaScript文件
│   │   └── pic/              # 截图图片
│   └── doc/                  # Web模块文档
│
├── tests/                    # 测试代码
│   ├── __init__.py
│   ├── setup_test_db.py      # 测试数据库设置
│   ├── test_crud.py          # CRUD测试
│   ├── test_transaction.py   # 事务测试
│   ├── test_concurrent.py    # 并发测试
│   ├── test_extreme.py       # 极端情况测试
│   └── doc/                  # 测试报告和日志
│
└── utils/                    # 工具函数
    ├── __init__.py
    ├── logger.py             # 日志工具
    ├── performance_logger.py # 性能日志
    └── db_statistics.py      # 数据库统计工具
```

## 数据库设计

系统实现了一个关系型数据库，采用标准的ER建模方法，包含9个核心表和2个辅助表。

### 核心数据表

1. **pharmacopoeia_items** (药典条目) - **6,283条**

   - 存储2025版中国药典的药品信息
   - 包括中文名、英文名、拼音名、分类、详细内容等
2. **inspectors** (药检员) - **301条**

   - 药检员基本信息
   - 包括工号、姓名、部门、职称、资质等级等
3. **laboratories** (实验室) - **30条**

   - 实验室基本信息
   - 包括实验室代码、名称、地址、认证、设备等级等
4. **conversations** (对话会话) - **7,931条**

   - 药检员与系统的对话会话记录
   - 包括会话ID、开始时间、结束时间、消息总数等
5. **messages** (对话消息) - **103,794条** ⭐主要数据源

   - 详细的对话消息内容
   - 包括消息文本、意图分类、置信度、响应时间等
6. **experiments** (实验记录) - **15,000条** ⭐次要数据源

   - 实验检测记录
   - 包括实验编号、类型、日期、状态、结果等
7. **experiment_data** (实验数据点) - **52,499条**

   - 实验的具体测量数据点
   - 包括测量类型、测量值、单位、标准范围等
8. **lab_access** (实验室权限) - **800条**

   - 药检员与实验室的多对多关系
   - 包括访问权限级别、授权日期等
9. **system_config** (系统配置) - **28条** ⭐1-1关系表

   - 系统配置参数管理
   - 使用config_key作为主键，实现1-1关系设计
   - 包括系统、显示、安全、业务、数据库、性能6类配置

### 实体关系(ER)图

系统设计包含以下关系类型：

- **1:1关系**: SystemConfig (config_key作为主键，每个配置项唯一)
- **1:N关系**: Inspector → Conversation → Message (8个以上1:N关系)
- **1:N关系**: Inspector → Experiment → ExperimentData
- **N:M关系**: Inspector ↔ Laboratory (通过lab_access中间表)

```
Inspector (药检员)
    ├─1:N→ Conversation (对话会话)
    │      └─1:N→ Message (对话消息)
    ├─1:N→ Experiment (实验记录)
    │      └─1:N→ ExperimentData (实验数据点)
    └─N:M→ Laboratory (实验室) [通过LabAccess]

Item (药品条目)
    ├─1:N→ Experiment (实验记录)
    └─1:N→ Message (引用)

Laboratory (实验室)
    ├─N:M→ Inspector (药检员) [通过LabAccess]
    └─1:N→ Experiment (实验记录)
```

### 数据量统计

总数据量约 **186,666条记录**，远超课程要求的10万条（达到187%）：

- 主要数据源：message表 (103,794条)
- 次要数据源：experiment表 (15,000条) + experiment_data表 (52,499条)
- 基础数据：item (6,283条) + inspector (301条) + laboratory (30条) + conversation (7,931条) + lab_access (800条) + system_config (28条)

### 数据库特性

- ✅ **完整的外键约束** - 保证数据完整性
- ✅ **15+个索引** - 优化查询性能
- ✅ **ACID事务支持** - 保证数据一致性
- ✅ **并发控制** - 连接池管理，支持多用户访问
- ✅ **符合3NF** - 规范的数据库设计

## 功能截图

### 智药AI首页

![智药AI首页](web/static/pic/首页.png)

![智药AI首页](web/static/pic/首页2.png)

### 实验管理界面

![实验管理界面](web/static/pic/实验管理.png)

### 对话查询界面

![对话查询界面](web/static/pic/对话查询.png)

### 系统配置页面

![系统配置页面](web/static/pic/系统配置.png)

## 性能优化

系统在数据库层面实现了多种优化:

- 合适的索引设计
- 查询优化
- 事务处理
- 并发控制

## 开发者

- 项目名称: 智药AI (PharmaAI)
- 开发者: J

## 许可证

本项目采用 **GNU Affero General Public License v3.0 (AGPL-3.0)** 开源许可证。

### 许可证核心要求

#### ✅ 您可以：

1. **自由使用** - 可以自由运行本程序用于任何目的
2. **修改权利** - 可以修改程序的源代码以满足您的需求
3. **分发自由** - 可以将程序的副本分发给他人
4. **商业使用** - 可以将本程序用于商业目的

#### ⚠️ 您必须：

1. **开源要求** - 如果您修改并分发本程序，必须以 AGPL-3.0 许可证公开完整源代码
2. **网络使用开源** - **重要**: 如果您在网络服务器上运行修改版本（如提供 Web 服务），必须向用户提供修改后的源代码访问途径
3. **保留声明** - 必须保留原始版权声明、许可证声明和免责声明
4. **声明修改** - 如果修改了源代码，必须明确标注修改内容和日期
5. **相同许可** - 衍生作品必须使用相同的 AGPL-3.0 许可证

#### 🔴 您不可以：

1. **闭源使用** - 不能将本程序或其衍生作品闭源发布
2. **许可证变更** - 不能更改许可证类型（必须保持 AGPL-3.0）
3. **移除版权** - 不能移除或修改原始版权和许可证声明

### 为什么选择 AGPL-3.0？

本项目选择 AGPL-3.0 是为了：

1. **保护开源精神** - 确保所有改进和修改都回馈给开源社区
2. **防止闭源SaaS** - 防止他人将项目改造成闭源的云服务
3. **促进协作** - 鼓励开发者公开分享改进，形成良性生态

### 许可证文本

完整许可证文本请查看: [LICENCE](LICENCE)

### 免责声明

本程序按"原样"提供，不提供任何明示或暗示的担保。详细免责声明请参阅许可证第15条和第16条。
