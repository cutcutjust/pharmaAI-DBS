"""
药典条目模型模块(Pharmacopoeia Item Model Module)

本模块提供药典条目相关的模型类，对应数据库中的pharmacopoeia_items表，
用于表示2025版中国药典中的药品、制剂、辅料等条目信息。

使用方法:
    from models.pharmacopoeia import PharmacopoeiaItem
    
    # 创建药典条目
    item = PharmacopoeiaItem(
        volume=1,
        doc_id=49350,
        name_cn="人参",
        name_pinyin="Renshen",
        name_en="Ginseng Radix et Rhizoma",
        category="药材和饮片",
        content="本品为五加科植物人参Panax ginseng C. A. Meyer的干燥根和根茎。春、秋二季采挖，除去须根及泥沙，晒干或低温干燥。"
    )
    
    # 访问条目属性
    print(f"药品名称: {item.name_cn}")
    print(f"拼音: {item.name_pinyin}")
    print(f"英文名: {item.name_en}")
    
    # 更新内容
    item.update_content("本品为五加科植物人参Panax ginseng C. A. Meyer的干燥根和根茎。春、秋二季采挖，除去须根及泥沙，晒干或低温干燥。具有补气固脱，益脾养胃，安神益智的功效。")
    
    # 获取药典卷号对应的文本描述
    volume_text = item.get_volume_text()  # 返回"第一部"
    
    # 转换为字典用于数据库操作
    item_dict = item.to_dict()
    
    # 从数据库记录创建实例
    db_record = (1, 2, 49771, "豆油", "Douyou", "Soya Oil", 
                 "植物油脂和提取物", "本品为豆科植物大豆的种子经压榨或浸提所得的脂肪油。", "2025-01-01 00:00:00")
    item = PharmacopoeiaItem.from_db_record(db_record)

主要功能:
    - PharmacopoeiaItem: 药典条目模型类
        - __init__(volume, doc_id, name_cn, name_pinyin=None, name_en=None, 
                  category=None, content=None, id=None):
            初始化药典条目对象
            
        - update_content(new_content): 
            更新条目内容文本
            
        - get_volume_text(): 
            获取药典卷号的文本描述（第一部/第二部/第三部/第四部）
            
        - get_doc_url(): 
            获取条目的文档URL链接
            
        - to_dict(): 
            将药典条目对象转换为字典
            
        - from_dict(data): 
            从字典创建药典条目对象(类方法)
            
        - from_db_record(record): 
            从数据库记录创建药典条目对象(类方法)
"""

from models.base import BaseModel
from datetime import datetime

class PharmacopoeiaItem(BaseModel):
    """
    药典条目模型类，对应数据库中的pharmacopoeia_items表。
    """
    
    def __init__(self, volume, doc_id, name_cn, name_pinyin=None, name_en=None, 
                 category=None, content=None, id=None):
        """
        初始化药典条目对象。
        
        Args:
            volume: 药典卷号（1/2/3/4）
            doc_id: 文档ID
            name_cn: 中文名称
            name_pinyin: 拼音名称，可选
            name_en: 英文名称，可选
            category: 分类（药材/制剂/辅料等），可选
            content: 详细内容，可选
            id: 数据库记录ID，可选
        """
        super().__init__(id)
        self.volume = volume
        self.doc_id = doc_id
        self.name_cn = name_cn
        self.name_pinyin = name_pinyin
        self.name_en = name_en
        self.category = category
        self.content = content
    
    def update_content(self, new_content):
        """
        更新条目内容文本。
        
        Args:
            new_content: 新的内容文本
            
        Returns:
            PharmacopoeiaItem: 返回自身，支持链式调用
        """
        self.content = new_content
        return self
    
    def get_volume_text(self):
        """
        获取药典卷号的文本描述。
        
        Returns:
            str: 卷号文本描述（第一部/第二部/第三部/第四部）
        """
        volume_texts = {
            1: "第一部",
            2: "第二部",
            3: "第三部",
            4: "第四部"
        }
        return volume_texts.get(self.volume, f"未知卷号({self.volume})")
    
    def get_doc_url(self):
        """
        获取条目的文档URL链接。
        
        Returns:
            str: 文档URL
        """
        return f"https://www.chp.org.cn/view?id={self.volume}&docid={self.doc_id}"
    
    @classmethod
    def from_db_record(cls, record):
        """
        从数据库记录创建药典条目对象。
        
        数据库记录格式:
        (item_id, volume, doc_id, name_cn, name_pinyin, name_en, category, content, created_at)
        
        Args:
            record: 数据库查询结果元组
            
        Returns:
            PharmacopoeiaItem: 新创建的药典条目对象实例
        """
        if record is None or len(record) < 8:
            raise ValueError("无效的数据库记录格式")
        
        # 创建PharmacopoeiaItem实例
        return cls(
            id=record[0],
            volume=record[1],
            doc_id=record[2],
            name_cn=record[3],
            name_pinyin=record[4],
            name_en=record[5],
            category=record[6],
            content=record[7]
        )