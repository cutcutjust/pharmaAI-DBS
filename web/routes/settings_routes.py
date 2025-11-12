"""
系统设置路由模块(Settings Routes)

本模块提供系统设置相关的路由处理，包括系统配置的查询、更新等功能，
展示1-1关系的实现（config_key作为主键，每个配置项唯一）。

主要功能:
    - 系统配置查询
    - 系统配置更新
    - 配置分类管理
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from database.connection import get_connection_pool
from utils.logger import get_logger
from utils.performance_logger import log_execution_time
from datetime import datetime

# 获取日志记录器
logger = get_logger(__name__)

# 获取数据库连接池
pool = get_connection_pool()


@log_execution_time
def settings_page():
    """系统设置页面
    
    Returns:
        Response: 渲染系统设置页面
    """
    try:
        conn = pool.getconn()
        cur = conn.cursor()
        
        # 获取配置分类
        category = request.args.get('category', 'all')
        
        # 查询系统配置
        if category == 'all':
            cur.execute("""
                SELECT config_key, config_value, config_type, description, 
                       category, is_editable, updated_by, updated_at
                FROM system_config
                ORDER BY category, config_key
            """)
        else:
            cur.execute("""
                SELECT config_key, config_value, config_type, description, 
                       category, is_editable, updated_by, updated_at
                FROM system_config
                WHERE category = %s
                ORDER BY config_key
            """, (category,))
        
        configs = []
        for row in cur.fetchall():
            configs.append({
                'config_key': row[0],
                'config_value': row[1],
                'config_type': row[2],
                'description': row[3],
                'category': row[4],
                'is_editable': row[5],
                'updated_by': row[6],
                'updated_at': row[7]
            })
        
        # 获取所有配置分类
        cur.execute("""
            SELECT DISTINCT category 
            FROM system_config 
            ORDER BY category
        """)
        categories = [row[0] for row in cur.fetchall()]
        
        pool.putconn(conn)
        
        logger.info(f"系统设置页面加载成功，当前分类: {category}，配置数量: {len(configs)}")
        
        return render_template('settings.html', 
                             configs=configs, 
                             categories=categories,
                             current_category=category)
    
    except Exception as e:
        logger.error(f"系统设置页面加载失败: {str(e)}")
        if 'conn' in locals():
            pool.putconn(conn)
        flash(f'加载系统设置失败: {str(e)}', 'error')
        return redirect(url_for('index'))


@log_execution_time
def update_config():
    """更新系统配置
    
    Returns:
        JSON: 更新结果
    """
    try:
        data = request.get_json()
        config_key = data.get('config_key')
        config_value = data.get('config_value')
        updated_by = data.get('updated_by', '系统管理员')
        
        if not config_key:
            return jsonify({
                'success': False,
                'message': '配置键不能为空'
            }), 400
        
        conn = pool.getconn()
        cur = conn.cursor()
        
        # 检查配置是否可编辑
        cur.execute("""
            SELECT is_editable FROM system_config WHERE config_key = %s
        """, (config_key,))
        
        result = cur.fetchone()
        if not result:
            pool.putconn(conn)
            return jsonify({
                'success': False,
                'message': '配置项不存在'
            }), 404
        
        if not result[0]:
            pool.putconn(conn)
            return jsonify({
                'success': False,
                'message': '该配置项不可编辑'
            }), 403
        
        # 更新配置
        cur.execute("""
            UPDATE system_config 
            SET config_value = %s, 
                updated_by = %s, 
                updated_at = %s
            WHERE config_key = %s
        """, (config_value, updated_by, datetime.now(), config_key))
        
        conn.commit()
        pool.putconn(conn)
        
        logger.info(f"配置更新成功: {config_key} = {config_value}, 操作者: {updated_by}")
        
        return jsonify({
            'success': True,
            'message': '配置更新成功'
        })
    
    except Exception as e:
        logger.error(f"配置更新失败: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            pool.putconn(conn)
        return jsonify({
            'success': False,
            'message': f'配置更新失败: {str(e)}'
        }), 500


@log_execution_time
def get_config_detail(config_key):
    """获取配置详情
    
    Args:
        config_key: 配置键
        
    Returns:
        JSON: 配置详情
    """
    try:
        conn = pool.getconn()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT config_key, config_value, config_type, description, 
                   category, is_editable, updated_by, updated_at, created_at
            FROM system_config
            WHERE config_key = %s
        """, (config_key,))
        
        row = cur.fetchone()
        pool.putconn(conn)
        
        if not row:
            return jsonify({
                'success': False,
                'message': '配置项不存在'
            }), 404
        
        config = {
            'config_key': row[0],
            'config_value': row[1],
            'config_type': row[2],
            'description': row[3],
            'category': row[4],
            'is_editable': row[5],
            'updated_by': row[6],
            'updated_at': row[7].strftime('%Y-%m-%d %H:%M:%S') if row[7] else None,
            'created_at': row[8].strftime('%Y-%m-%d %H:%M:%S') if row[8] else None
        }
        
        return jsonify({
            'success': True,
            'data': config
        })
    
    except Exception as e:
        logger.error(f"获取配置详情失败: {str(e)}")
        if 'conn' in locals():
            pool.putconn(conn)
        return jsonify({
            'success': False,
            'message': f'获取配置详情失败: {str(e)}'
        }), 500


def register_settings_routes(app):
    """注册系统设置路由
    
    Args:
        app: Flask应用实例
    """
    app.add_url_rule('/settings', 'settings_page', settings_page, methods=['GET'])
    app.add_url_rule('/api/config/update', 'update_config', update_config, methods=['POST'])
    app.add_url_rule('/api/config/<config_key>', 'get_config_detail', get_config_detail, methods=['GET'])
    
    logger.info("系统设置路由注册完成")

