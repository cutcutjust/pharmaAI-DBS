"""
基础数据访问对象(Base DAO)模块

本模块提供通用的数据库CRUD(创建、读取、更新、删除)操作，作为其他所有DAO类的基类。

使用方法:
    1. 继承BaseDAO类并指定表名和主键
       class MyEntityDAO(BaseDAO):
           def __init__(self, connection_pool):
               super().__init__(connection_pool, 'table_name', 'id_column')
       
    2. 直接使用基础CRUD方法
       dao = MyEntityDAO(connection_pool)
       # 插入数据
       entity_id = dao.insert({'field1': 'value1', 'field2': 'value2'})
       # 查询数据
       entity = dao.get_by_id(entity_id)
       # 更新数据
       dao.update(entity_id, {'field1': 'new_value'})
       # 删除数据
       dao.delete(entity_id)

主要功能:
    - BaseDAO: 基础数据访问对象类，提供通用CRUD操作
        - insert(): 插入单条记录并返回ID
        - batch_insert(): 批量插入多条记录
        - get_by_id(): 根据ID获取单条记录
        - get_all(): 获取所有记录
        - find_by(): 根据条件查询记录
        - update(): 更新单条记录
        - delete(): 删除单条记录
        - execute_query(): 执行自定义SQL查询
        - execute_transaction(): 在事务中执行操作
"""

from utils.performance_logger import log_execution_time
from utils.logger import get_logger
import psycopg2
import psycopg2.extras


class BaseDAO:
    """基础数据访问对象类，提供通用的CRUD操作"""

    def __init__(self, connection_pool, table_name, id_column):
        """
        初始化基础DAO
        
        参数:
            connection_pool: 数据库连接池
            table_name: 表名
            id_column: ID列名
        """
        self.connection_pool = connection_pool
        self.table_name = table_name
        self.id_column = id_column
        self.logger = get_logger(__name__)

    @log_execution_time
    def insert(self, data):
        """
        插入单条记录
        
        参数:
            data: 包含列名和值的字典
            
        返回:
            新插入记录的ID
        """
        columns = list(data.keys())
        values = list(data.values())
        placeholders = ["%s"] * len(columns)
        
        query = f"""
            INSERT INTO {self.table_name} ({", ".join(columns)})
            VALUES ({", ".join(placeholders)})
            RETURNING {self.id_column}
        """
        
        with self.connection_pool.getconn() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, values)
                    result = cursor.fetchone()
                    conn.commit()
                    return result[0] if result else None
            except Exception as e:
                conn.rollback()
                self.logger.error(f"Error inserting data into {self.table_name}: {str(e)}")
                raise
            finally:
                self.connection_pool.putconn(conn)

    @log_execution_time
    def batch_insert(self, data_list, batch_size=1000, on_conflict=None):
        """
        批量插入多条记录
        
        参数:
            data_list: 包含多个数据字典的列表
            batch_size: 每批插入的记录数量，默认1000
            on_conflict: 冲突处理方式，如 "DO NOTHING" 或 "DO UPDATE SET ..."
            
        返回:
            插入成功的记录数量
        """
        if not data_list:
            return 0
        
        # 确保所有数据具有相同的列
        columns = list(data_list[0].keys())
        values_list = []
        for data in data_list:
            values_list.append([data.get(col) for col in columns])
        
        placeholders = ["%s"] * len(columns)
        
        # 构建基础插入语句
        base_query = f"""
            INSERT INTO {self.table_name} ({", ".join(columns)})
            VALUES ({", ".join(placeholders)})
        """
        
        # 如果有冲突处理，添加到查询中
        if on_conflict:
            query = f"{base_query} ON CONFLICT {on_conflict}"
        else:
            query = base_query
        
        total_inserted = 0
        batch_count = (len(values_list) + batch_size - 1) // batch_size
        
        self.logger.info(f"开始批量插入 {len(values_list)} 条记录，分 {batch_count} 批处理（每批 {batch_size} 条）")
        
        # 分批处理
        for i in range(0, len(values_list), batch_size):
            batch = values_list[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            with self.connection_pool.getconn() as conn:
                try:
                    with conn.cursor() as cursor:
                        # 使用 execute_batch 执行批量插入
                        psycopg2.extras.execute_batch(cursor, query, batch, page_size=batch_size)
                        conn.commit()
                        # execute_batch 的 rowcount 应该准确反映实际插入的行数
                        # 对于 ON CONFLICT DO NOTHING，rowcount 只计算实际插入的行数
                        inserted = cursor.rowcount
                        total_inserted += inserted
                        if inserted != len(batch):
                            self.logger.debug(f"第 {batch_num}/{batch_count} 批插入完成，本批插入 {inserted}/{len(batch)} 条记录（可能有重复或冲突）")
                        else:
                            self.logger.debug(f"第 {batch_num}/{batch_count} 批插入完成，本批插入 {inserted} 条记录")
                except Exception as e:
                    conn.rollback()
                    self.logger.error(f"批量插入第 {batch_num} 批时出错: {str(e)}")
                    self.logger.error(f"错误详情: {type(e).__name__}: {e}")
                    # 如果批量插入失败，尝试逐条插入以找出问题记录
                    if len(batch) > 1:
                        self.logger.warning(f"批量插入失败，尝试逐条插入第 {batch_num} 批...")
                        for idx, values in enumerate(batch):
                            conn2 = self.connection_pool.getconn()
                            try:
                                with conn2.cursor() as cursor2:
                                    cursor2.execute(query, values)
                                    conn2.commit()
                                    total_inserted += 1
                            except Exception as e2:
                                conn2.rollback()
                                self.logger.error(f"插入第 {batch_num} 批第 {idx + 1} 条记录失败: {str(e2)}")
                                self.logger.debug(f"失败记录的值: {values[:5]}...")  # 只显示前5个值
                                # 继续处理下一条记录
                            finally:
                                self.connection_pool.putconn(conn2)
                    else:
                        raise
                finally:
                    self.connection_pool.putconn(conn)
        
        self.logger.info(f"批量插入完成，共插入 {total_inserted} 条记录（共 {len(values_list)} 条）")
        return total_inserted

    @log_execution_time
    def get_by_id(self, id_value):
        """
        根据ID获取单条记录
        
        参数:
            id_value: ID值
            
        返回:
            匹配的记录字典，未找到则返回None
        """
        query = f"""
            SELECT * FROM {self.table_name}
            WHERE {self.id_column} = %s
        """
        
        with self.connection_pool.getconn() as conn:
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute(query, [id_value])
                    result = cursor.fetchone()
                    return dict(result) if result else None
            except Exception as e:
                self.logger.error(f"Error getting record from {self.table_name}: {str(e)}")
                raise
            finally:
                self.connection_pool.putconn(conn)

    @log_execution_time
    def get_all(self, limit=None, offset=None, order_by=None):
        """
        获取所有记录
        
        参数:
            limit: 限制返回的记录数量
            offset: 跳过的记录数量
            order_by: 排序字段和顺序，如"id ASC"
            
        返回:
            记录字典的列表
        """
        query = f"SELECT * FROM {self.table_name}"
        
        params = []
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        if offset:
            query += " OFFSET %s"
            params.append(offset)
        
        with self.connection_pool.getconn() as conn:
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
            except Exception as e:
                self.logger.error(f"Error getting all records from {self.table_name}: {str(e)}")
                raise
            finally:
                self.connection_pool.putconn(conn)

    @log_execution_time
    def find_by(self, criteria, limit=None, offset=None, order_by=None):
        """
        根据条件查询记录
        
        参数:
            criteria: 条件字典，如{'field1': 'value1', 'field2': 'value2'}
            limit: 限制返回的记录数量
            offset: 跳过的记录数量
            order_by: 排序字段和顺序，如"id ASC"
            
        返回:
            匹配的记录字典列表
        """
        if not criteria:
            return self.get_all(limit, offset, order_by)
        
        conditions = []
        params = []
        for column, value in criteria.items():
            conditions.append(f"{column} = %s")
            params.append(value)
        
        query = f"""
            SELECT * FROM {self.table_name}
            WHERE {' AND '.join(conditions)}
        """
        
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        if offset:
            query += " OFFSET %s"
            params.append(offset)
        
        with self.connection_pool.getconn() as conn:
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
            except Exception as e:
                self.logger.error(f"Error finding records in {self.table_name}: {str(e)}")
                raise
            finally:
                self.connection_pool.putconn(conn)

    @log_execution_time
    def update(self, id_value, data):
        """
        更新单条记录
        
        参数:
            id_value: 要更新记录的ID
            data: 要更新的数据字典
            
        返回:
            更新成功返回True，否则返回False
        """
        if not data:
            return False
        
        set_clauses = []
        params = []
        for column, value in data.items():
            set_clauses.append(f"{column} = %s")
            params.append(value)
        
        params.append(id_value)
        
        query = f"""
            UPDATE {self.table_name}
            SET {', '.join(set_clauses)}
            WHERE {self.id_column} = %s
        """
        
        with self.connection_pool.getconn() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    conn.commit()
                    return cursor.rowcount > 0
            except Exception as e:
                conn.rollback()
                self.logger.error(f"Error updating record in {self.table_name}: {str(e)}")
                raise
            finally:
                self.connection_pool.putconn(conn)

    @log_execution_time
    def delete(self, id_value):
        """
        删除单条记录
        
        参数:
            id_value: 要删除记录的ID
            
        返回:
            删除成功返回True，否则返回False
        """
        query = f"""
            DELETE FROM {self.table_name}
            WHERE {self.id_column} = %s
        """
        
        with self.connection_pool.getconn() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, [id_value])
                    conn.commit()
                    return cursor.rowcount > 0
            except Exception as e:
                conn.rollback()
                self.logger.error(f"Error deleting record from {self.table_name}: {str(e)}")
                raise
            finally:
                self.connection_pool.putconn(conn)

    @log_execution_time
    def execute_query(self, query, params=None):
        """
        执行自定义SQL查询
        
        参数:
            query: SQL查询语句
            params: 查询参数列表
            
        返回:
            执行结果列表
        """
        with self.connection_pool.getconn() as conn:
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute(query, params or [])
                    if query.upper().startswith(("SELECT", "WITH")):
                        results = cursor.fetchall()
                        return [dict(row) for row in results]
                    else:
                        conn.commit()
                        return cursor.rowcount
            except Exception as e:
                if not query.upper().startswith(("SELECT", "WITH")):
                    conn.rollback()
                self.logger.error(f"Error executing query: {str(e)}")
                raise
            finally:
                self.connection_pool.putconn(conn)

    @log_execution_time
    def execute_transaction(self, callback):
        """
        在事务中执行操作
        
        参数:
            callback: 回调函数，接收一个游标作为参数
            
        返回:
            回调函数的返回值
        """
        with self.connection_pool.getconn() as conn:
            try:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    result = callback(cursor)
                    conn.commit()
                    return result
            except Exception as e:
                conn.rollback()
                self.logger.error(f"Error executing transaction: {str(e)}")
                raise
            finally:
                self.connection_pool.putconn(conn)
