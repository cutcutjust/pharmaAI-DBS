/*
数据库索引创建脚本(Database Indexes)

本脚本为药典数据库系统创建各种索引，用于优化数据库查询性能，
包括普通索引、唯一索引和复合索引，满足课程对索引支持的要求。

使用方法:
    1. 必须在执行schema.sql创建表之后执行本脚本
    2. 可以通过以下方式执行:
    
       -- 方式1: 使用数据库客户端工具
       psql -h hostname -d dbname -U username -f indexes.sql
       或
       mysql -h hostname -u username -p dbname < indexes.sql
       
       -- 方式2: 使用代码执行
       from database.connection import execute_script_file
       execute_script_file('database/indexes.sql')
       
       -- 方式3: 在数据库初始化时顺序执行
       execute_script_file('database/schema.sql')
       execute_script_file('database/indexes.sql')

主要索引:
    1. 药典条目表索引:
       - idx_item_category: 按分类快速查询药典条目
       - idx_item_name: 按中文名检索药品
       
    2. 药检员表索引:
       - idx_inspector_dept: 按部门查询药检员
       
    3. 对话会话表索引:
       - idx_conv_inspector: 按药检员ID检索会话
       - idx_conv_time: 按会话开始时间检索
       
    4. 消息表索引:
       - idx_msg_conversation: 按会话ID检索消息
       - idx_msg_timestamp: 按时间戳检索消息
       - idx_msg_intent: 按意图分类检索
       
    5. 实验记录表索引:
       - idx_exp_inspector: 按药检员ID查询实验
       - idx_exp_date: 按实验日期查询
       - idx_exp_item: 按药典条目ID查询
       
    6. 实验数据点表索引:
       - idx_data_experiment: 按实验ID查询数据点
       - idx_data_type: 按测量类型查询
*/

-- 1. 药典条目表索引
CREATE INDEX idx_item_category ON pharmacopoeia_items(category);
CREATE INDEX idx_item_name ON pharmacopoeia_items(name_cn);
CREATE INDEX idx_item_pinyin ON pharmacopoeia_items(name_pinyin);

-- 2. 药检员表索引
CREATE INDEX idx_inspector_dept ON inspectors(department);
CREATE INDEX idx_inspector_title ON inspectors(title);
CREATE INDEX idx_inspector_cert ON inspectors(certification_level);

-- 3. 实验室表索引
CREATE INDEX idx_lab_certification ON laboratories(certification);
CREATE INDEX idx_lab_equipment ON laboratories(equipment_level);

-- 4. 对话会话表索引
CREATE INDEX idx_conv_inspector ON conversations(inspector_id);
CREATE INDEX idx_conv_time ON conversations(start_time);
CREATE INDEX idx_conv_type ON conversations(session_type);
CREATE INDEX idx_conv_topic ON conversations(context_topic);

-- 5. 消息表索引 (主要数据源，优化查询性能很重要)
CREATE INDEX idx_msg_conversation ON messages(conversation_id);
CREATE INDEX idx_msg_timestamp ON messages(timestamp);
CREATE INDEX idx_msg_intent ON messages(intent);
CREATE INDEX idx_msg_referenced_item ON messages(referenced_item_id);
CREATE INDEX idx_msg_sender ON messages(sender_type);

-- 6. 实验记录表索引 (第二数据源)
CREATE INDEX idx_exp_inspector ON experiment_records(inspector_id);
CREATE INDEX idx_exp_date ON experiment_records(experiment_date);
CREATE INDEX idx_exp_item ON experiment_records(item_id);
CREATE INDEX idx_exp_lab ON experiment_records(lab_id);
CREATE INDEX idx_exp_status ON experiment_records(status);
CREATE INDEX idx_exp_result ON experiment_records(result);

-- 7. 实验数据点表索引
CREATE INDEX idx_data_experiment ON experiment_data_points(experiment_id);
CREATE INDEX idx_data_type ON experiment_data_points(measurement_type);
CREATE INDEX idx_data_qualified ON experiment_data_points(is_qualified);

-- 8. 复合索引 (提高多条件查询性能)
-- 按时间和药检员查询会话
CREATE INDEX idx_conv_inspector_time ON conversations(inspector_id, start_time);

-- 按实验室和日期查询实验
CREATE INDEX idx_exp_lab_date ON experiment_records(lab_id, experiment_date);

-- 按测量类型和合格状态查询数据点
CREATE INDEX idx_data_type_qualified ON experiment_data_points(measurement_type, is_qualified);
