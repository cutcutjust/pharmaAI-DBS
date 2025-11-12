"""
对话查询路由模块(Conversation Routes Module)

本模块提供对话查询相关的Web路由处理功能，负责处理对话历史查询请求，
连接前端页面和后端查询服务，实现按药检员、时间范围、关键词等条件查询对话历史。

使用方法:
    from web.routes.conversation_routes import register_conversation_routes
    from flask import Flask
    
    app = Flask(__name__)
    
    # 注册对话查询相关路由
    register_conversation_routes(app)
    
    if __name__ == '__main__':
        app.run(debug=True)
    
    # 注册后可通过以下URL访问对话查询功能
    # /conversations - 显示对话查询页面
    # /conversations/search - 执行对话查询操作
    # /conversations/<conversation_id> - 查看指定对话详情
    # /conversations/export - 导出对话查询结果

主要功能:
    - register_conversation_routes(app): 
        注册所有对话查询相关的路由到Flask应用
        
    - conversation_search_page(): 
        渲染对话查询页面，处理GET请求
        
    - search_conversations(): 
        处理对话查询表单提交，执行查询并返回结果，处理POST请求
        
    - get_conversation_details(conversation_id): 
        获取指定对话会话的详细信息，包括所有消息
        
    - export_conversations(): 
        导出对话查询结果为CSV或Excel格式
        
    - _get_query_service(): 
        获取查询服务实例（内部函数）
        
    - _format_conversation_data(conversations): 
        格式化对话数据以适应前端展示（内部函数）
"""

import csv
import io
import datetime
import pandas as pd
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, session
from psycopg2.extras import RealDictCursor
from utils.logger import get_logger
from utils.performance_logger import log_performance

logger = get_logger(__name__)

def register_conversation_routes(app):
    """
    注册所有对话查询相关的路由到Flask应用
    
    Args:
        app: Flask应用实例
    """
    app.route('/conversations', methods=['GET'])(conversation_search_page)
    app.route('/conversations/search', methods=['POST'])(search_conversations)
    app.route('/conversations/<int:conversation_id>', methods=['GET'])(get_conversation_details)
    app.route('/conversations/export', methods=['POST'])(export_conversations)

@log_performance
def conversation_search_page():
    """
    渲染对话查询页面，处理GET请求
    
    Returns:
        str: 渲染后的对话查询页面HTML
    """
    try:
        from database.connection import get_connection_pool
        
        pool = get_connection_pool()
        conn = pool.getconn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 获取药检员列表
        cursor.execute("SELECT inspector_id as id, name FROM inspectors ORDER BY name")
        inspectors = cursor.fetchall()
        
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        offset = (page - 1) * per_page
        
        # 获取总记录数
        cursor.execute("SELECT COUNT(*) as total FROM conversations")
        total_count = cursor.fetchone()['total']
        
        # 获取对话记录（分页）
        cursor.execute("""
            SELECT 
                c.conversation_id as id,
                c.session_id,
                c.start_time,
                c.end_time,
                c.total_messages as message_count,
                c.context_topic as main_keywords,
                i.inspector_id as inspector_id,
                i.name as inspector_name
            FROM conversations c
            JOIN inspectors i ON c.inspector_id = i.inspector_id
            ORDER BY c.start_time DESC
            LIMIT %s OFFSET %s
        """, (per_page, offset))
        conversations = cursor.fetchall()
        
        # 格式化日期时间
        for conv in conversations:
            if conv['start_time']:
                conv['start_time'] = str(conv['start_time'])
            if conv['end_time']:
                conv['end_time'] = str(conv['end_time'])
        
        cursor.close()
        pool.putconn(conn)
        
        # 计算总页数
        total_pages = (total_count + per_page - 1) // per_page
        
        # 构建分页信息
        pagination = {
            'page': page,
            'per_page': per_page,
            'total_count': total_count,
            'total_pages': total_pages
        }
        
        return render_template('conversation_search.html', 
                             inspectors=inspectors, 
                             conversations=conversations,
                             pagination=pagination)
    except Exception as e:
        logger.error(f"加载对话查询页面失败: {str(e)}")
        import traceback
        traceback.print_exc()
        flash('加载对话查询页面失败，请稍后再试', 'error')
        return render_template('conversation_search.html', inspectors=[], conversations=[])

@log_performance
def search_conversations():
    """
    处理对话查询表单提交，执行查询并返回结果，处理POST请求
    
    Returns:
        str: 渲染后的对话查询结果页面HTML
    """
    try:
        # 从表单获取查询条件
        inspector_id = request.form.get('inspector_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        keywords = request.form.get('keywords')
        page = int(request.form.get('page', 1))
        per_page = int(request.form.get('per_page', 20))
        
        # 构建查询条件
        query_params = {}
        if inspector_id:
            query_params['inspector_id'] = int(inspector_id)
        if start_date:
            query_params['start_date'] = start_date
        if end_date:
            query_params['end_date'] = end_date
        if keywords:
            query_params['keywords'] = keywords.strip()
        
        query_service = _get_query_service()
        conversations, total_count = query_service.search_conversations(
            query_params, page=page, per_page=per_page
        )
        
        # 将查询结果存储在会话中，以便导出功能使用
        session['last_conversation_search'] = {
            'query_params': query_params,
            'total_count': total_count
        }
        
        # 计算分页信息
        total_pages = max(1, (total_count + per_page - 1) // per_page)
        
        # 构建分页信息
        pagination = {
            'page': page,
            'per_page': per_page,
            'total_count': total_count,
            'total_pages': total_pages
        }
        
        # 获取药检员列表（用于表单回显）
        from database.connection import get_connection_pool
        pool = get_connection_pool()
        conn = pool.getconn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT inspector_id as id, name FROM inspectors ORDER BY name")
        inspectors = cursor.fetchall()
        cursor.close()
        pool.putconn(conn)
        
        # 显示查询成功的消息
        if total_count > 0:
            flash(f'查询成功！共找到 {total_count} 条对话记录', 'success')
        else:
            flash('未找到符合条件的对话记录，请尝试修改查询条件', 'info')
        
        # 渲染同一个页面，显示查询结果
        return render_template(
            'conversation_search.html',
            conversations=conversations,
            inspectors=inspectors,
            pagination=pagination,
            query_params=query_params
        )
    except Exception as e:
        logger.error(f"对话查询失败: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'对话查询失败: {str(e)}', 'error')
        return redirect(url_for('conversation_search_page'))

@log_performance
def get_conversation_details(conversation_id):
    """
    获取指定对话会话的详细信息，包括所有消息
    
    Args:
        conversation_id (int): 对话会话ID
        
    Returns:
        Response: JSON格式的对话详情
    """
    try:
        from database.connection import get_connection_pool
        
        pool = get_connection_pool()
        conn = pool.getconn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 获取对话会话信息
        cursor.execute("""
            SELECT 
                c.conversation_id as id,
                c.session_id,
                c.start_time,
                c.end_time,
                c.total_messages,
                c.context_topic,
                i.inspector_id as inspector_id,
                i.name as inspector_name
            FROM conversations c
            JOIN inspectors i ON c.inspector_id = i.inspector_id
            WHERE c.conversation_id = %s
        """, (conversation_id,))
        
        conversation = cursor.fetchone()
        
        if not conversation:
            return jsonify({'error': '对话会话不存在'}), 404
        
        # 格式化日期时间
        if conversation['start_time']:
            conversation['start_time'] = str(conversation['start_time'])
        if conversation['end_time']:
            conversation['end_time'] = str(conversation['end_time'])
        
        # 获取消息记录
        cursor.execute("""
            SELECT 
                m.message_id as id,
                m.message_seq,
                m.sender_type as role,
                m.message_text as content,
                m.timestamp,
                m.referenced_item_id,
                pi.name_cn as referenced_item_name
            FROM messages m
            LEFT JOIN pharmacopoeia_items pi ON m.referenced_item_id = pi.item_id
            WHERE m.conversation_id = %s
            ORDER BY m.message_seq
        """, (conversation_id,))
        
        messages = cursor.fetchall()
        
        # 格式化消息时间戳
        for msg in messages:
            if msg['timestamp']:
                msg['timestamp'] = str(msg['timestamp'])
        
        cursor.close()
        pool.putconn(conn)
        
        return jsonify({
            'conversation': conversation,
            'messages': messages
        })
    except Exception as e:
        logger.error(f"获取对话详情失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@log_performance
def export_conversations():
    """
    导出对话查询结果为CSV或Excel格式
    
    Returns:
        Response: 文件下载响应
    """
    try:
        # 获取上次查询的参数
        last_search = session.get('last_conversation_search')
        if not last_search:
            flash('没有可导出的查询结果，请先进行查询', 'error')
            return redirect(url_for('conversation_search_page'))
            
        query_params = last_search.get('query_params', {})
        
        # 获取导出格式
        export_format = request.form.get('export_format', 'csv')
        
        # 获取所有结果（不分页）
        query_service = _get_query_service()
        conversations, _ = query_service.search_conversations(
            query_params, page=1, per_page=10000  # 设置较大的每页数量以获取全部结果
        )
        
        # 格式化对话数据
        formatted_conversations = _format_conversation_data(conversations)
        
        # 准备导出数据
        export_data = []
        for conv in formatted_conversations:
            # 格式化药检员显示：ID - 姓名
            inspector_display = conv.get('inspector_name', '未知')
            if conv.get('inspector_id'):
                inspector_display = f"{conv['inspector_id']} - {inspector_display}"
            export_data.append({
                '会话ID': conv['id'],
                '药检员': inspector_display,
                '开始时间': conv['start_time'],
                '结束时间': conv['end_time'],
                '消息数量': conv['message_count'],
                '主要关键词': conv['main_keywords']
            })
        
        # 生成文件名
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        
        if export_format == 'excel':
            # 导出为Excel
            output = io.BytesIO()
            df = pd.DataFrame(export_data)
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='对话查询结果', index=False)
            
            output.seek(0)
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                attachment_filename=f'conversation_export_{timestamp}.xlsx'
            )
        else:
            # 导出为CSV
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
            writer.writeheader()
            writer.writerows(export_data)
            
            output_str = output.getvalue()
            output_bytes = io.BytesIO(output_str.encode('utf-8-sig'))  # 使用UTF-8 with BOM以支持中文
            
            return send_file(
                output_bytes,
                mimetype='text/csv',
                as_attachment=True,
                attachment_filename=f'conversation_export_{timestamp}.csv'
            )
    except Exception as e:
        logger.error(f"导出对话查询结果失败: {str(e)}")
        flash('导出对话查询结果失败，请稍后再试', 'error')
        return redirect(url_for('conversation_search_page'))

def _get_query_service():
    """
    获取查询服务实例（内部函数）
    
    Returns:
        QueryService: 查询服务实例
    """
    from flask import current_app
    return current_app.query_service

def _format_conversation_data(conversations):
    """
    格式化对话数据以适应前端展示（内部函数）
    
    Args:
        conversations (list): 原始对话数据列表
        
    Returns:
        list: 格式化后的对话数据列表
    """
    formatted_data = []
    for conv in conversations:
        # 提取主要关键词（如果有的话）
        main_keywords = conv.get('keywords', '无关键词')
        if isinstance(main_keywords, list) and main_keywords:
            main_keywords = ', '.join(main_keywords[:5])  # 仅显示前5个关键词
            
        formatted_conv = {
            'id': conv.get('id'),
            'inspector_id': conv.get('inspector_id'),
            'inspector_name': conv.get('inspector_name', '未知'),
            'start_time': conv.get('start_time'),
            'end_time': conv.get('end_time'),
            'message_count': conv.get('message_count', 0),
            'main_keywords': main_keywords
        }
        formatted_data.append(formatted_conv)
        
    return formatted_data