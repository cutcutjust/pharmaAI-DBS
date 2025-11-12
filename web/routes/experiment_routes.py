"""
实验管理路由模块(Experiment Routes Module)

本模块提供实验记录管理相关的Web路由处理功能，负责处理实验记录的创建、查询、
修改和删除请求，连接前端页面和后端实验服务，实现实验记录的完整管理功能。

使用方法:
    from web.routes.experiment_routes import register_experiment_routes
    from flask import Flask
    
    app = Flask(__name__)
    
    # 注册实验管理相关路由
    register_experiment_routes(app)
    
    if __name__ == '__main__':
        app.run(debug=True)
    
    # 注册后可通过以下URL访问实验管理功能
    # /experiments - 显示实验记录列表页面
    # /experiments/new - 新建实验记录页面
    # /experiments/<experiment_id> - 查看实验详情
    # /experiments/<experiment_id>/edit - 编辑实验记录
    # /experiments/<experiment_id>/delete - 删除实验记录

主要功能:
    - register_experiment_routes(app): 
        注册所有实验管理相关的路由到Flask应用
        
    - experiment_list_page(): 
        渲染实验记录列表页面，处理GET请求
        
    - new_experiment_page(): 
        渲染新建实验记录页面，处理GET请求
        
    - create_experiment(): 
        处理新建实验记录表单提交，执行创建操作，处理POST请求
        
    - experiment_details(experiment_id): 
        查看指定实验记录的详细信息，包括数据点
        
    - edit_experiment_page(experiment_id): 
        渲染编辑实验记录页面，处理GET请求
        
    - update_experiment(experiment_id): 
        处理编辑实验记录表单提交，执行更新操作，处理POST请求
        
    - delete_experiment(experiment_id): 
        删除指定的实验记录，处理POST请求
        
    - _get_transaction_service(): 
        获取事务服务实例（内部函数）
        
    - _get_query_service(): 
        获取查询服务实例（内部函数）
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from psycopg2.extras import RealDictCursor
from utils.logger import get_logger
from utils.performance_logger import log_performance

logger = get_logger(__name__)

def register_experiment_routes(app):
    """
    注册所有实验管理相关的路由到Flask应用
    
    Args:
        app: Flask应用实例
    """
    app.route('/experiments', methods=['GET'])(experiment_list_page)
    app.route('/experiments/new', methods=['GET'])(new_experiment_page)
    app.route('/experiments', methods=['POST'])(create_experiment)
    app.route('/experiments/<int:experiment_id>', methods=['GET'])(experiment_details)
    app.route('/experiments/<int:experiment_id>/json', methods=['GET'])(experiment_details_json)
    app.route('/experiments/<int:experiment_id>/edit', methods=['GET'])(edit_experiment_page)
    app.route('/experiments/<int:experiment_id>', methods=['POST'])(update_experiment)
    app.route('/experiments/<int:experiment_id>/delete', methods=['POST'])(delete_experiment)

@log_performance
def experiment_list_page():
    """
    渲染实验记录列表页面，处理GET请求
    
    Returns:
        str: 渲染后的实验记录列表页面HTML
    """
    try:
        from database.connection import get_connection_pool
        
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # 获取筛选参数
        inspector_id = request.args.get('inspector_id', type=int)
        lab_id = request.args.get('laboratory_id', type=int)
        item_id = request.args.get('item_id', type=int)
        status = request.args.get('status')
        date_start = request.args.get('date_start')
        date_end = request.args.get('date_end')
        keyword = request.args.get('keyword')
        
        pool = get_connection_pool()
        conn = pool.getconn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 构建查询条件
        where_conditions = []
        params = []
        
        if inspector_id:
            where_conditions.append("er.inspector_id = %s")
            params.append(inspector_id)
        if lab_id:
            where_conditions.append("er.lab_id = %s")
            params.append(lab_id)
        if item_id:
            where_conditions.append("er.item_id = %s")
            params.append(item_id)
        if status:
            where_conditions.append("er.status = %s")
            params.append(status)
        if date_start:
            where_conditions.append("er.experiment_date >= %s")
            params.append(date_start)
        if date_end:
            where_conditions.append("er.experiment_date <= %s")
            params.append(date_end)
        if keyword:
            where_conditions.append("(er.experiment_no LIKE %s OR er.experiment_type LIKE %s OR er.conclusion LIKE %s)")
            keyword_pattern = f"%{keyword}%"
            params.extend([keyword_pattern, keyword_pattern, keyword_pattern])
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # 查询实验记录
        query = f"""
            SELECT 
                er.experiment_id as id,
                er.experiment_no,
                er.experiment_type as title,
                er.experiment_date as date,
                er.status,
                er.result,
                er.created_at,
                i.inspector_id,
                i.name as inspector_name,
                pi.name_cn as item_name,
                l.lab_name as laboratory_name
            FROM experiment_records er
            JOIN inspectors i ON er.inspector_id = i.inspector_id
            JOIN pharmacopoeia_items pi ON er.item_id = pi.item_id
            LEFT JOIN laboratories l ON er.lab_id = l.lab_id
            WHERE {where_clause}
            ORDER BY er.created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([per_page, (page - 1) * per_page])
        
        cursor.execute(query, params)
        experiments = cursor.fetchall()
        
        # 获取总数用于分页
        count_query = f"""
            SELECT COUNT(*) as total
            FROM experiment_records er
            WHERE {where_clause}
        """
        cursor.execute(count_query, params[:-2])  # 不包括LIMIT和OFFSET参数
        total_count = cursor.fetchone()['total']
        
        # 获取药检员列表
        cursor.execute("SELECT inspector_id as id, name FROM inspectors ORDER BY name")
        inspectors = cursor.fetchall()
        
        # 获取实验室列表
        cursor.execute("SELECT lab_id as id, lab_name as name FROM laboratories ORDER BY lab_name")
        laboratories = cursor.fetchall()
        
        # 获取药品列表（限制数量以避免过多）
        cursor.execute("SELECT item_id as id, name_cn as name FROM pharmacopoeia_items ORDER BY name_cn LIMIT 1000")
        items = cursor.fetchall()
        
        cursor.close()
        pool.putconn(conn)
        
        # 计算分页信息
        total_pages = (total_count + per_page - 1) // per_page
        pagination = {
            'page': page,
            'pages': total_pages,
            'total_count': total_count,
            'per_page': per_page
        }
        
        return render_template(
            'experiment_manage.html',
            experiments=experiments,
            inspectors=inspectors,
            laboratories=laboratories,
            items=items,
            pagination=pagination
        )
    except Exception as e:
        logger.error(f"获取实验记录列表失败: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'获取实验记录列表失败: {str(e)}', 'error')
        return render_template('experiment_manage.html', experiments=[], inspectors=[], laboratories=[], items=[])

@log_performance
def new_experiment_page():
    """
    渲染新建实验记录页面，处理GET请求
    
    Returns:
        str: 渲染后的新建实验记录页面HTML
    """
    return render_template('experiments/new.html')

@log_performance
def create_experiment():
    """
    处理新建实验记录表单提交，执行创建操作，处理POST请求
    
    Returns:
        Response: 重定向到实验记录列表页面
    """
    try:
        transaction_service = _get_transaction_service()
        
        experiment_data = {
            'title': request.form.get('title'),
            'description': request.form.get('description'),
            'researcher': request.form.get('researcher'),
            'date': request.form.get('date'),
            'status': request.form.get('status'),
            'results': request.form.get('results')
        }
        
        # 处理数据点信息，如果有的话
        data_points = []
        data_point_values = request.form.getlist('data_point_value')
        data_point_units = request.form.getlist('data_point_unit')
        data_point_timestamps = request.form.getlist('data_point_timestamp')
        
        for i in range(len(data_point_values)):
            data_points.append({
                'value': data_point_values[i],
                'unit': data_point_units[i],
                'timestamp': data_point_timestamps[i]
            })
        
        experiment_data['data_points'] = data_points
        
        experiment_id = transaction_service.create_experiment(experiment_data)
        
        flash('实验记录创建成功！', 'success')
        return redirect(url_for('experiment_details', experiment_id=experiment_id))
    except Exception as e:
        logger.error(f"创建实验记录失败: {str(e)}")
        flash('创建实验记录失败，请检查输入并重试', 'error')
        return redirect(url_for('new_experiment_page'))

@log_performance
def experiment_details(experiment_id):
    """
    查看指定实验记录的详细信息，包括数据点
    
    Args:
        experiment_id (int): 实验记录ID
        
    Returns:
        str: 渲染后的实验详情页面HTML
    """
    try:
        from database.connection import get_connection_pool
        
        pool = get_connection_pool()
        conn = pool.getconn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 获取实验详情
        cursor.execute("""
            SELECT 
                er.experiment_id as id,
                er.experiment_no,
                er.experiment_type as title,
                er.experiment_date as date,
                er.status,
                er.result,
                er.conclusion as description,
                er.conclusion as results,
                er.created_at,
                er.inspector_id,
                er.lab_id,
                er.item_id,
                i.inspector_id as inspector_id_display,
                i.name as inspector_name,
                pi.name_cn as item_name,
                l.lab_name as laboratory_name
            FROM experiment_records er
            JOIN inspectors i ON er.inspector_id = i.inspector_id
            JOIN pharmacopoeia_items pi ON er.item_id = pi.item_id
            LEFT JOIN laboratories l ON er.lab_id = l.lab_id
            WHERE er.experiment_id = %s
        """, (experiment_id,))
        
        experiment = cursor.fetchone()
        
        if not experiment:
            cursor.close()
            pool.putconn(conn)
            flash('实验记录不存在', 'error')
            return redirect(url_for('experiment_list_page'))
        
        # 获取数据点
        cursor.execute("""
            SELECT 
                data_id as id,
                measurement_type,
                measurement_value as value,
                measurement_unit as unit,
                measurement_time as timestamp
            FROM experiment_data_points
            WHERE experiment_id = %s
            ORDER BY data_id
        """, (experiment_id,))
        
        data_points = cursor.fetchall()
        experiment['data_points'] = data_points
        
        cursor.close()
        pool.putconn(conn)
        
        return jsonify(experiment)
    except Exception as e:
        logger.error(f"获取实验记录详情失败: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('获取实验记录详情失败，请稍后再试', 'error')
        return redirect(url_for('experiment_list_page'))

@log_performance
def experiment_details_json(experiment_id):
    """
    获取指定实验记录的JSON数据（用于AJAX请求）
    
    Args:
        experiment_id (int): 实验记录ID
        
    Returns:
        Response: JSON格式的实验详情
    """
    try:
        from database.connection import get_connection_pool
        
        pool = get_connection_pool()
        conn = pool.getconn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 获取实验详情
        cursor.execute("""
            SELECT 
                er.experiment_id as id,
                er.experiment_no,
                er.experiment_type as title,
                er.experiment_date as date,
                er.status,
                er.result,
                er.conclusion as description,
                er.conclusion as results,
                er.created_at,
                er.inspector_id,
                er.lab_id,
                er.item_id,
                i.inspector_id as inspector_id_display,
                i.name as inspector_name,
                pi.name_cn as item_name,
                l.lab_name as laboratory_name
            FROM experiment_records er
            JOIN inspectors i ON er.inspector_id = i.inspector_id
            JOIN pharmacopoeia_items pi ON er.item_id = pi.item_id
            LEFT JOIN laboratories l ON er.lab_id = l.lab_id
            WHERE er.experiment_id = %s
        """, (experiment_id,))
        
        experiment = cursor.fetchone()
        
        if not experiment:
            cursor.close()
            pool.putconn(conn)
            return jsonify({'error': '实验记录不存在'}), 404
        
        # 获取数据点
        cursor.execute("""
            SELECT 
                data_id as id,
                measurement_type,
                measurement_value as value,
                measurement_unit as unit,
                measurement_time as timestamp
            FROM experiment_data_points
            WHERE experiment_id = %s
            ORDER BY data_id
        """, (experiment_id,))
        
        data_points = cursor.fetchall()
        
        # 格式化日期时间
        if experiment['date']:
            experiment['date'] = str(experiment['date'])
        if experiment['created_at']:
            experiment['created_at'] = str(experiment['created_at'])
        
        for dp in data_points:
            if dp['timestamp']:
                dp['timestamp'] = str(dp['timestamp'])
        
        experiment['data_points'] = data_points
        
        cursor.close()
        pool.putconn(conn)
        
        return jsonify(experiment)
    except Exception as e:
        logger.error(f"获取实验记录JSON失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@log_performance
def edit_experiment_page(experiment_id):
    """
    渲染编辑实验记录页面，处理GET请求
    
    Args:
        experiment_id (int): 实验记录ID
        
    Returns:
        str: 渲染后的编辑实验记录页面HTML
    """
    try:
        query_service = _get_query_service()
        experiment = query_service.get_experiment_by_id(experiment_id)
        
        if not experiment:
            flash('实验记录不存在', 'error')
            return redirect(url_for('experiment_list_page'))
            
        return render_template('experiments/edit.html', experiment=experiment)
    except Exception as e:
        logger.error(f"获取实验记录编辑信息失败: {str(e)}")
        flash('获取实验记录编辑信息失败，请稍后再试', 'error')
        return redirect(url_for('experiment_list_page'))

@log_performance
def update_experiment(experiment_id):
    """
    处理编辑实验记录表单提交，执行更新操作，处理POST请求
    
    Args:
        experiment_id (int): 实验记录ID
        
    Returns:
        Response: 重定向到实验记录详情页面
    """
    try:
        transaction_service = _get_transaction_service()
        
        experiment_data = {
            'id': experiment_id,
            'title': request.form.get('title'),
            'description': request.form.get('description'),
            'researcher': request.form.get('researcher'),
            'date': request.form.get('date'),
            'status': request.form.get('status'),
            'results': request.form.get('results')
        }
        
        # 处理数据点信息，如果有的话
        data_points = []
        data_point_ids = request.form.getlist('data_point_id')
        data_point_values = request.form.getlist('data_point_value')
        data_point_units = request.form.getlist('data_point_unit')
        data_point_timestamps = request.form.getlist('data_point_timestamp')
        
        for i in range(len(data_point_values)):
            data_point = {
                'value': data_point_values[i],
                'unit': data_point_units[i],
                'timestamp': data_point_timestamps[i]
            }
            
            if i < len(data_point_ids) and data_point_ids[i]:
                data_point['id'] = data_point_ids[i]
                
            data_points.append(data_point)
        
        experiment_data['data_points'] = data_points
        
        transaction_service.update_experiment(experiment_data)
        
        flash('实验记录更新成功！', 'success')
        return redirect(url_for('experiment_details', experiment_id=experiment_id))
    except Exception as e:
        logger.error(f"更新实验记录失败: {str(e)}")
        flash('更新实验记录失败，请检查输入并重试', 'error')
        return redirect(url_for('edit_experiment_page', experiment_id=experiment_id))

@log_performance
def delete_experiment(experiment_id):
    """
    删除指定的实验记录，处理POST请求
    
    Args:
        experiment_id (int): 实验记录ID
        
    Returns:
        Response: 重定向到实验记录列表页面
    """
    try:
        transaction_service = _get_transaction_service()
        transaction_service.delete_experiment(experiment_id)
        
        flash('实验记录已成功删除！', 'success')
        return redirect(url_for('experiment_list_page'))
    except Exception as e:
        logger.error(f"删除实验记录失败: {str(e)}")
        flash('删除实验记录失败，请稍后再试', 'error')
        return redirect(url_for('experiment_details', experiment_id=experiment_id))

def _get_transaction_service():
    """
    获取事务服务实例（内部函数）
    
    Returns:
        TransactionService: 事务服务实例
    """
    from flask import current_app
    return current_app.transaction_service

def _get_query_service():
    """
    获取查询服务实例（内部函数）
    
    Returns:
        QueryService: 查询服务实例
    """
    from flask import current_app
    return current_app.query_service