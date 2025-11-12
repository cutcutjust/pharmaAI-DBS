/*
药典数据库表结构定义脚本(Database Schema)

本脚本定义药典数据库系统的8个核心表结构，包括主键、外键、约束条件等，
创建了药典条目、药检员、实验室、对话会话等相关表，用于系统数据存储。

使用方法:
    1. 在PostgreSQL或MySQL数据库中执行本脚本创建表结构
    2. 可以通过以下方式执行:
    
       -- 方式1: 使用数据库客户端工具
       psql -h hostname -d dbname -U username -f schema.sql
       或
       mysql -h hostname -u username -p dbname < schema.sql
    
       -- 方式2: 使用代码执行
       from database.connection import execute_script_file
       execute_script_file('database/schema.sql')

主要表结构:
    1. pharmacopoeia_items: 药典条目表，存储药典中的药品、制剂、辅料等信息
    2. inspectors: 药检员表，存储药检员的基本信息
    3. laboratories: 实验室表，存储实验室相关信息
    4. inspector_lab_access: 药检员-实验室关系表，表示N-M的访问权限关系
    5. conversations: 对话会话表，存储药检员与系统的对话会话
    6. messages: 对话消息表，存储对话中的详细消息，系统主要数据源
    7. experiment_records: 实验记录表，存储药检员进行的实验信息
    8. experiment_data_points: 实验数据点表，存储实验中的测量数据
*/

-- 1. 药典条目表
CREATE TABLE pharmacopoeia_items (
    item_id SERIAL PRIMARY KEY,
    volume INT NOT NULL,                    -- 药典卷号 (1/2/3/4)
    doc_id INT NOT NULL,                    -- 文档ID
    name_cn VARCHAR(200) NOT NULL,          -- 中文名
    name_pinyin VARCHAR(200),               -- 拼音名
    name_en VARCHAR(200),                   -- 英文名
    category VARCHAR(100),                  -- 分类（药材/制剂/辅料等）
    content TEXT,                           -- 详细内容
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(volume, doc_id)
);

-- 2. 药检员表
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

-- 3. 实验室表
CREATE TABLE laboratories (
    lab_id SERIAL PRIMARY KEY,                         -- 实验室ID，主键，自动递增
    lab_code VARCHAR(50) UNIQUE NOT NULL,              -- 实验室代码，唯一且不可为空
    lab_name VARCHAR(200) NOT NULL,                    -- 实验室名称，不能为空
    location VARCHAR(200),                             -- 实验室地址，可为空
    certification VARCHAR(100),                        -- 认证类型，可为空
    equipment_level VARCHAR(50),                       -- 设备等级，可为空
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP     -- 创建时间，默认为当前时间
);

-- 4. 药检员-实验室关系表（N-M关系）
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

-- 5. 对话会话表
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

-- 6. 对话消息表（主要数据源，约10万条）
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

-- 7. 实验记录表（第二数据源）
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

-- 8. 实验数据点表
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

-- 9. 系统配置表（1-1关系示例）
CREATE TABLE system_config (
    config_key VARCHAR(100) PRIMARY KEY,                           -- 配置键，主键，每个配置项唯一
    config_value TEXT,                                             -- 配置值
    config_type VARCHAR(50) DEFAULT 'string',                      -- 配置类型（string/number/boolean/json）
    description TEXT,                                              -- 配置项描述
    category VARCHAR(50),                                          -- 配置分类（system/display/security等）
    is_editable BOOLEAN DEFAULT TRUE,                              -- 是否可编辑
    updated_by VARCHAR(100),                                       -- 最后更新者
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,                -- 最后更新时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP                 -- 创建时间
);