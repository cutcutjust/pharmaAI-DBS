"""
实验记录模型模块(Experiment Model Module)

本模块提供实验记录及实验数据点的模型类，对应数据库中的experiment_records和
experiment_data_points表，用于表示药检员进行的实验及测量数据。

使用方法:
    from models.experiment import ExperimentRecord, ExperimentDataPoint
    from datetime import date, datetime
    
    # 创建实验记录
    experiment = ExperimentRecord(
        experiment_no="EXP2025001",
        inspector_id=1,
        lab_id=2,
        item_id=100,
        experiment_type="含量测定",
        batch_no="B20250101",
        experiment_date=date(2025, 1, 15)
    )
    
    # 添加实验数据点
    data_point1 = ExperimentDataPoint(
        experiment_id=experiment.id,
        measurement_type="pH值",
        measurement_value=6.8,
        measurement_unit="pH",
        standard_min=6.0,
        standard_max=7.5,
        is_qualified=True
    )
    
    data_point2 = ExperimentDataPoint(
        experiment_id=experiment.id,
        measurement_type="含量",
        measurement_value=98.5,
        measurement_unit="%",
        standard_min=95.0,
        standard_max=105.0,
        is_qualified=True
    )
    
    # 更新实验状态和结果
    experiment.update_status("已完成", "合格")
    experiment.set_conclusion("该批次药品各项指标均符合要求")
    
    # 设置实验起止时间
    experiment.start(datetime.now())
    # ... 实验过程 ...
    experiment.end(datetime.now())
    
    # 转换为字典用于数据库操作
    experiment_dict = experiment.to_dict()
    data_point_dict = data_point1.to_dict()

主要功能:
    - ExperimentRecord: 实验记录模型类
        - __init__(experiment_no, inspector_id, lab_id, item_id, experiment_type=None,
                  batch_no=None, sample_quantity=None, experiment_date=None,
                  start_time=None, end_time=None, status="进行中", 
                  result=None, conclusion=None, id=None):
            初始化实验记录对象
            
        - start(start_time): 
            设置实验开始时间
            
        - end(end_time): 
            设置实验结束时间
            
        - update_status(status, result=None): 
            更新实验状态和结果
            
        - set_conclusion(conclusion): 
            设置实验结论
            
        - get_duration(): 
            计算实验持续时间（分钟）
            
        - is_completed(): 
            检查实验是否已完成
            
        - to_dict(): 
            将实验记录转换为字典
            
        - from_dict(data): 
            从字典创建实验记录对象(类方法)
            
        - from_db_record(record): 
            从数据库记录创建实验记录对象(类方法)
    
    - ExperimentDataPoint: 实验数据点模型类
        - __init__(experiment_id, measurement_type, measurement_value=None, 
                  measurement_unit=None, standard_min=None, standard_max=None,
                  is_qualified=None, measurement_time=None, equipment_id=None,
                  notes=None, id=None):
            初始化实验数据点对象
            
        - set_value(value, unit=None): 
            设置测量值和单位
            
        - set_standard_range(min_value, max_value): 
            设置标准范围
            
        - check_qualification(): 
            检查测量值是否合格（在标准范围内）
            
        - to_dict(): 
            将实验数据点转换为字典
            
        - from_dict(data): 
            从字典创建实验数据点对象(类方法)
            
        - from_db_record(record): 
            从数据库记录创建实验数据点对象(类方法)
"""

from models.base import BaseModel
from datetime import date, datetime

class ExperimentRecord(BaseModel):
    """
    实验记录模型类，对应数据库中的experiment_records表。
    """
    
    def __init__(self, experiment_no, inspector_id, lab_id, item_id, experiment_type=None,
                 batch_no=None, sample_quantity=None, experiment_date=None,
                 start_time=None, end_time=None, status="进行中", 
                 result=None, conclusion=None, id=None):
        """
        初始化实验记录对象。
        
        Args:
            experiment_no: 实验编号，唯一标识
            inspector_id: 药检员ID，外键
            lab_id: 实验室ID，外键
            item_id: 药典条目ID，外键
            experiment_type: 实验类型，可选
            batch_no: 批号，可选
            sample_quantity: 样品量，可选
            experiment_date: 实验日期，date类型，可选
            start_time: 实验开始时间，datetime类型，可选
            end_time: 实验结束时间，datetime类型，可选
            status: 实验状态，默认为"进行中"
            result: 实验结果，可选
            conclusion: 实验结论，可选
            id: 数据库记录ID，可选
        """
        super().__init__(id)
        self.experiment_no = experiment_no
        self.inspector_id = inspector_id
        self.lab_id = lab_id
        self.item_id = item_id
        self.experiment_type = experiment_type
        self.batch_no = batch_no
        self.sample_quantity = sample_quantity
        self.experiment_date = experiment_date if experiment_date else date.today()
        self.start_time = start_time
        self.end_time = end_time
        self.status = status
        self.result = result
        self.conclusion = conclusion
    
    def start(self, start_time):
        """
        设置实验开始时间。
        
        Args:
            start_time: 实验开始时间，datetime类型
            
        Returns:
            ExperimentRecord: 返回自身，支持链式调用
        """
        self.start_time = start_time
        return self
    
    def end(self, end_time):
        """
        设置实验结束时间。
        
        Args:
            end_time: 实验结束时间，datetime类型
            
        Returns:
            ExperimentRecord: 返回自身，支持链式调用
        """
        self.end_time = end_time
        # 如果状态仍为"进行中"，则自动更新为"已完成"
        if self.status == "进行中":
            self.status = "已完成"
        return self
    
    def update_status(self, status, result=None):
        """
        更新实验状态和结果。
        
        Args:
            status: 新的实验状态，如"进行中"、"已完成"、"异常"
            result: 实验结果，如"合格"、"不合格"、"待定"，可选
            
        Returns:
            ExperimentRecord: 返回自身，支持链式调用
        """
        self.status = status
        if result is not None:
            self.result = result
        return self
    
    def set_conclusion(self, conclusion):
        """
        设置实验结论。
        
        Args:
            conclusion: 实验结论文本
            
        Returns:
            ExperimentRecord: 返回自身，支持链式调用
        """
        self.conclusion = conclusion
        return self
    
    def get_duration(self):
        """
        计算实验持续时间（分钟）。
        
        Returns:
            float: 实验持续的分钟数，如果实验未结束则返回None
        """
        if self.end_time is None or self.start_time is None:
            return None
            
        duration = self.end_time - self.start_time
        # 转换为分钟，并保留1位小数
        minutes = duration.total_seconds() / 60.0
        return round(minutes, 1)
    
    def is_completed(self):
        """
        检查实验是否已完成。
        
        Returns:
            bool: 如果实验已完成返回True，否则返回False
        """
        return self.status == "已完成" or self.end_time is not None
    
    @classmethod
    def from_db_record(cls, record):
        """
        从数据库记录创建实验记录对象。
        
        数据库记录格式:
        (experiment_id, experiment_no, inspector_id, lab_id, item_id, experiment_type,
         batch_no, sample_quantity, experiment_date, start_time, end_time, 
         status, result, conclusion, created_at)
        
        Args:
            record: 数据库查询结果元组
            
        Returns:
            ExperimentRecord: 新创建的实验记录对象实例
        """
        if record is None or len(record) < 14:
            raise ValueError("无效的数据库记录格式")
        
        # 解析date和datetime字符串为相应对象
        experiment_date_str = record[8]
        experiment_date = None
        if experiment_date_str:
            if isinstance(experiment_date_str, str):
                try:
                    experiment_date = datetime.strptime(experiment_date_str, "%Y-%m-%d").date()
                except ValueError:
                    # 尝试其他可能的日期格式
                    try:
                        experiment_date = datetime.strptime(experiment_date_str, "%Y-%m-%d %H:%M:%S").date()
                    except ValueError:
                        pass
            elif isinstance(experiment_date_str, date):
                experiment_date = experiment_date_str
        
        start_time_str = record[9]
        start_time = None
        if start_time_str:
            if isinstance(start_time_str, str):
                try:
                    start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S.%f")
                    except ValueError:
                        pass
            elif isinstance(start_time_str, datetime):
                start_time = start_time_str
        
        end_time_str = record[10]
        end_time = None
        if end_time_str:
            if isinstance(end_time_str, str):
                try:
                    end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S.%f")
                    except ValueError:
                        pass
            elif isinstance(end_time_str, datetime):
                end_time = end_time_str
        
        # 创建ExperimentRecord实例
        return cls(
            id=record[0],
            experiment_no=record[1],
            inspector_id=record[2],
            lab_id=record[3],
            item_id=record[4],
            experiment_type=record[5],
            batch_no=record[6],
            sample_quantity=record[7],
            experiment_date=experiment_date,
            start_time=start_time,
            end_time=end_time,
            status=record[11],
            result=record[12],
            conclusion=record[13]
        )


class ExperimentDataPoint(BaseModel):
    """
    实验数据点模型类，对应数据库中的experiment_data_points表。
    """
    
    def __init__(self, experiment_id, measurement_type, measurement_value=None, 
                 measurement_unit=None, standard_min=None, standard_max=None,
                 is_qualified=None, measurement_time=None, equipment_id=None,
                 notes=None, id=None):
        """
        初始化实验数据点对象。
        
        Args:
            experiment_id: 所属实验ID，外键
            measurement_type: 测量类型（如pH值、含量等）
            measurement_value: 测量值，可选
            measurement_unit: 测量单位，可选
            standard_min: 标准下限，可选
            standard_max: 标准上限，可选
            is_qualified: 是否合格，可选
            measurement_time: 测量时间，datetime类型，可选，默认为当前时间
            equipment_id: 设备编号，可选
            notes: 备注，可选
            id: 数据库记录ID，可选
        """
        super().__init__(id)
        self.experiment_id = experiment_id
        self.measurement_type = measurement_type
        self.measurement_value = measurement_value
        self.measurement_unit = measurement_unit
        self.standard_min = standard_min
        self.standard_max = standard_max
        self.is_qualified = is_qualified
        self.measurement_time = measurement_time if measurement_time else datetime.now()
        self.equipment_id = equipment_id
        self.notes = notes
    
    def set_value(self, value, unit=None):
        """
        设置测量值和单位。
        
        Args:
            value: 测量值
            unit: 测量单位，可选
            
        Returns:
            ExperimentDataPoint: 返回自身，支持链式调用
        """
        self.measurement_value = value
        if unit is not None:
            self.measurement_unit = unit
        
        # 如果已设置标准范围，则自动检查是否合格
        if self.standard_min is not None and self.standard_max is not None:
            self.check_qualification()
            
        return self
    
    def set_standard_range(self, min_value, max_value):
        """
        设置标准范围。
        
        Args:
            min_value: 标准下限
            max_value: 标准上限
            
        Returns:
            ExperimentDataPoint: 返回自身，支持链式调用
        """
        self.standard_min = min_value
        self.standard_max = max_value
        
        # 如果已设置测量值，则自动检查是否合格
        if self.measurement_value is not None:
            self.check_qualification()
            
        return self
    
    def check_qualification(self):
        """
        检查测量值是否在标准范围内（是否合格）。
        如果测量值或标准范围未设置，则不会更新合格状态。
        
        Returns:
            bool: 如果合格返回True，否则返回False
        """
        if (self.measurement_value is not None and 
            self.standard_min is not None and 
            self.standard_max is not None):
            
            is_qualified = (self.standard_min <= self.measurement_value <= self.standard_max)
            self.is_qualified = is_qualified
            return is_qualified
            
        return None
    
    @classmethod
    def from_db_record(cls, record):
        """
        从数据库记录创建实验数据点对象。
        
        数据库记录格式:
        (data_id, experiment_id, measurement_type, measurement_value, measurement_unit,
         standard_min, standard_max, is_qualified, measurement_time, equipment_id, notes)
        
        Args:
            record: 数据库查询结果元组
            
        Returns:
            ExperimentDataPoint: 新创建的实验数据点对象实例
        """
        if record is None or len(record) < 11:
            raise ValueError("无效的数据库记录格式")
        
        # 解析datetime字符串为datetime对象
        measurement_time_str = record[8]
        measurement_time = None
        if measurement_time_str:
            if isinstance(measurement_time_str, str):
                try:
                    measurement_time = datetime.strptime(measurement_time_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        measurement_time = datetime.strptime(measurement_time_str, "%Y-%m-%d %H:%M:%S.%f")
                    except ValueError:
                        pass
            elif isinstance(measurement_time_str, datetime):
                measurement_time = measurement_time_str
        
        # 创建ExperimentDataPoint实例
        return cls(
            id=record[0],
            experiment_id=record[1],
            measurement_type=record[2],
            measurement_value=record[3],
            measurement_unit=record[4],
            standard_min=record[5],
            standard_max=record[6],
            is_qualified=record[7],
            measurement_time=measurement_time,
            equipment_id=record[9],
            notes=record[10]
        )