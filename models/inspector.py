"""
药检员模型模块(Inspector Model Module)

本模块提供药检员相关的模型类，对应数据库中的inspectors表，
用于表示药检员的基本信息及其在系统中的角色。

使用方法:
    from models.inspector import Inspector
    from datetime import date
    
    # 创建药检员对象
    inspector = Inspector(
        employee_no="YJ2025001",
        name="张三",
        phone="13800138000",
        email="zhangsan@example.com",
        department="药品检测部",
        title="高级药师",
        certification_level="A级",
        join_date=date(2020, 1, 15)
    )
    
    # 访问药检员属性
    print(f"姓名: {inspector.name}")
    print(f"部门: {inspector.department}")
    
    # 修改药检员信息
    inspector.update_contact("13900139000", "zhangsan_new@example.com")
    inspector.promote("主任药师", "S级")
    
    # 检查药检员状态
    if inspector.is_active:
        print("在岗状态")
    
    # 转换为字典用于数据库操作
    inspector_dict = inspector.to_dict()
    
    # 从数据库记录创建实例
    db_record = (1, "YJ2025002", "李四", "13811138111", "lisi@example.com", 
                 "质量控制部", "药师", "B级", "2022-03-01", True, "2022-03-01 00:00:00")
    inspector = Inspector.from_db_record(db_record)

主要功能:
    - Inspector: 药检员模型类
        - __init__(employee_no, name, phone=None, email=None, department=None, 
                  title=None, certification_level=None, join_date=None, 
                  is_active=True, id=None):
            初始化药检员对象
            
        - update_contact(phone=None, email=None): 
            更新联系信息
            
        - promote(new_title=None, new_certification=None): 
            晋升职称或资质等级
            
        - set_active_status(is_active): 
            设置在岗状态
            
        - get_work_years(): 
            计算工作年限
            
        - to_dict(): 
            将药检员对象转换为字典
            
        - from_dict(data): 
            从字典创建药检员对象(类方法)
            
        - from_db_record(record): 
            从数据库记录创建药检员对象(类方法)
"""

from models.base import BaseModel
from datetime import date, datetime

class Inspector(BaseModel):
    """
    药检员模型类，对应数据库中的inspectors表。
    """
    
    def __init__(self, employee_no, name, phone=None, email=None, department=None, 
                 title=None, certification_level=None, join_date=None, 
                 is_active=True, id=None):
        """
        初始化药检员对象。
        
        Args:
            employee_no: 工号，唯一标识符
            name: 姓名
            phone: 电话号码，可选
            email: 电子邮箱，可选
            department: 所属部门，可选
            title: 职称，可选
            certification_level: 资质等级，可选
            join_date: 入职日期，可选，date类型
            is_active: 是否在岗状态，默认为True
            id: 数据库记录ID，可选
        """
        super().__init__(id)
        self.employee_no = employee_no
        self.name = name
        self.phone = phone
        self.email = email
        self.department = department
        self.title = title
        self.certification_level = certification_level
        self.join_date = join_date
        self.is_active = is_active
    
    def update_contact(self, phone=None, email=None):
        """
        更新药检员联系信息。
        
        Args:
            phone: 新的电话号码，如果为None则不更新
            email: 新的电子邮箱，如果为None则不更新
            
        Returns:
            Inspector: 返回自身，支持链式调用
        """
        if phone is not None:
            self.phone = phone
        if email is not None:
            self.email = email
        return self
    
    def promote(self, new_title=None, new_certification=None):
        """
        晋升药检员职称或资质等级。
        
        Args:
            new_title: 新的职称，如果为None则不更新
            new_certification: 新的资质等级，如果为None则不更新
            
        Returns:
            Inspector: 返回自身，支持链式调用
        """
        if new_title is not None:
            self.title = new_title
        if new_certification is not None:
            self.certification_level = new_certification
        return self
    
    def set_active_status(self, is_active):
        """
        设置药检员在岗状态。
        
        Args:
            is_active: 是否在岗，布尔值
            
        Returns:
            Inspector: 返回自身，支持链式调用
        """
        self.is_active = is_active
        return self
    
    def get_work_years(self):
        """
        计算药检员的工作年限（入职至今）。
        
        Returns:
            float: 工作年数，保留1位小数
        """
        if self.join_date is None:
            return 0.0
        
        today = date.today()
        years = today.year - self.join_date.year
        months = today.month - self.join_date.month
        
        # 调整不足一年的情况
        if months < 0:
            years -= 1
            months += 12
            
        # 计算年份，包含小数部分表示月份
        work_years = years + (months / 12.0)
        return round(work_years, 1)
    
    @classmethod
    def from_db_record(cls, record):
        """
        从数据库记录创建药检员对象。
        
        数据库记录格式:
        (inspector_id, employee_no, name, phone, email, department, title, 
         certification_level, join_date, is_active, created_at)
        
        Args:
            record: 数据库查询结果元组
            
        Returns:
            Inspector: 新创建的药检员对象实例
        """
        if record is None or len(record) < 10:
            raise ValueError("无效的数据库记录格式")
        
        # 解析join_date字符串为date对象（如果不为None）
        join_date_str = record[8]
        join_date = None
        if join_date_str:
            if isinstance(join_date_str, str):
                try:
                    join_date = datetime.strptime(join_date_str, "%Y-%m-%d").date()
                except ValueError:
                    # 尝试其他可能的日期格式
                    try:
                        join_date = datetime.strptime(join_date_str, "%Y-%m-%d %H:%M:%S").date()
                    except ValueError:
                        pass
            elif isinstance(join_date_str, date):
                join_date = join_date_str
        
        # 创建Inspector实例
        return cls(
            id=record[0],
            employee_no=record[1],
            name=record[2],
            phone=record[3],
            email=record[4],
            department=record[5],
            title=record[6],
            certification_level=record[7],
            join_date=join_date,
            is_active=record[9]
        )