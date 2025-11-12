"""
Web应用实现模块(Web Application Implementation)

本模块提供智药AI系统的Flask Web应用实现，包括应用创建、配置和初始化，
连接前端页面和后端服务，展示AI对话查询和实验管理两个主要功能。

使用方法:
    # 直接运行本模块启动Web应用
    python web/app.py
    
    # 或在其他模块中导入并使用
    from web.app import create_app
    
    app = create_app()
    app.run(debug=True)
    
    # 应用启动后可通过浏览器访问
    # http://localhost:5000/ - 首页
    # http://localhost:5000/conversations - 对话查询页面
    # http://localhost:5000/experiments - 实验管理页面

主要功能:
    - create_app(config=None): 
        创建并配置Flask应用实例
        
    - register_blueprints(app): 
        注册所有路由蓝图到应用
        
    - configure_app(app, config): 
        根据配置初始化应用
        
    - init_db_connection(app): 
        初始化数据库连接
        
    - init_services(app): 
        初始化服务组件
        
    - handle_404(error): 
        处理404错误的视图函数
        
    - handle_500(error): 
        处理500错误的视图函数
        
    - index(): 
        首页视图函数
"""

import os
from flask import Flask, render_template, redirect, url_for, request
from utils.logger import get_logger
from utils.performance_logger import log_execution_time
from services.query_service import QueryService
from services.transaction_service import TransactionService

# 获取日志记录器
logger = get_logger(__name__)

@log_execution_time
def index():
    """首页视图函数
    
    Returns:
        Response: 渲染首页模板
    """
    # 渲染首页
    return render_template('index.html')

@log_execution_time
def readme():
    """README文档页面视图函数
    
    Returns:
        Response: 渲染README内容页面
    """
    # README.md 文件路径（在项目根目录）
    readme_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'README.md')
    
    try:
        # 读取 README.md 文件
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        # 在Markdown转换前，先替换图片路径为Flask的static URL路径
        import re
        # 替换Markdown格式的图片路径: ![alt](web/static/path)
        readme_content = re.sub(r'!\[([^\]]*)\]\(web/static/([^\)]+)\)', r'![\1](/static/\2)', readme_content)
        # 替换Windows路径格式
        readme_content = re.sub(r'!\[([^\]]*)\]\(web\\static\\([^\)]+)\)', r'![\1](/static/\2)', readme_content)
        
        # 尝试使用 markdown 库转换，如果不可用则显示纯文本
        try:
            import markdown
            html_content = markdown.markdown(readme_content, extensions=['extra', 'codehilite', 'toc'])
        except ImportError:
            # 如果 markdown 库未安装，使用简单的 HTML 转换
            html_content = '<pre>' + readme_content.replace('<', '&lt;').replace('>', '&gt;') + '</pre>'
        
        # 再次处理HTML中的图片路径（双重保险）
        # 使用更通用的正则表达式，匹配所有可能的路径格式
        # 匹配 src="web/static/..." 或 src="/web/static/..." 或 src='web/static/...' 等
        html_content = re.sub(r'src=["\']/?web[/\\]static[/\\]([^"\']+)["\']', r'src="/static/\1"', html_content, flags=re.IGNORECASE)
        # 匹配 href 属性
        html_content = re.sub(r'href=["\']/?web[/\\]static[/\\]([^"\']+)["\']', r'href="/static/\1"', html_content, flags=re.IGNORECASE)
        # 也处理可能的其他属性
        html_content = re.sub(r'([a-z]+)=["\']/?web[/\\]static[/\\]([^"\']+)["\']', r'\1="/static/\2"', html_content, flags=re.IGNORECASE)
        
        # 渲染模板
        return render_template('readme.html', content=html_content)
    except FileNotFoundError:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>README - 智药AI</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
                h1 { color: #333; }
                .error { color: #dc3545; }
            </style>
        </head>
        <body>
            <h1>README</h1>
            <p class="error">README.md 文件未找到</p>
            <p><a href="/">返回首页</a></p>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"读取README文件失败: {str(e)}")
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>README - 智药AI</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
                h1 {{ color: #333; }}
                .error {{ color: #dc3545; }}
            </style>
        </head>
        <body>
            <h1>README</h1>
            <p class="error">读取README文件时出错: {str(e)}</p>
            <p><a href="/">返回首页</a></p>
        </body>
        </html>
        """

@log_execution_time
def create_app(config=None):
    """创建并配置Flask应用实例
    
    Args:
        config (dict, optional): 应用配置，默认为None
        
    Returns:
        Flask: 配置好的Flask应用实例
    """
    # 创建Flask应用
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
                static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    
    # 配置应用
    configure_app(app, config)
    
    # 初始化数据库连接
    init_db_connection(app)
    
    # 初始化服务
    init_services(app)
    
    # 注册蓝图
    register_blueprints(app)
    
    # 注册错误处理
    app.register_error_handler(404, handle_404)
    app.register_error_handler(500, handle_500)
    
    # 添加Python内置函数到Jinja2环境
    # 使分页等模板功能可以使用max和min函数
    app.jinja_env.globals.update(max=max, min=min)
    
    # 注册首页路由
    app.add_url_rule('/', 'index', index)
    # 注册README路由
    app.add_url_rule('/readme', 'readme', readme)
    
    logger.info("Flask应用创建完成")
    return app

def register_blueprints(app):
    """注册所有路由蓝图到应用
    
    Args:
        app (Flask): Flask应用实例
    """
    # 导入路由模块
    from web.routes.conversation_routes import register_conversation_routes
    from web.routes.experiment_routes import register_experiment_routes
    from web.routes.settings_routes import register_settings_routes
    
    # 注册路由
    register_conversation_routes(app)
    register_experiment_routes(app)
    register_settings_routes(app)
    
    logger.info("路由蓝图注册完成")

def configure_app(app, config):
    """根据配置初始化应用
    
    Args:
        app (Flask): Flask应用实例
        config (dict, optional): 应用配置，可以为None
    """
    # 加载默认配置
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key_for_pharmacopoeia_db'),
        SESSION_TYPE='filesystem',
        PERMANENT_SESSION_LIFETIME=1800,  # 会话有效期30分钟
        TEMPLATES_AUTO_RELOAD=True,
        JSON_AS_ASCII=False,  # 支持中文JSON
        MAX_CONTENT_LENGTH=16 * 1024 * 1024  # 最大上传限制16MB
    )
    
    # 更新用户配置
    if config:
        app.config.update(config)
    
    # 从环境变量加载配置
    if 'FLASK_ENV' in os.environ:
        app.config['ENV'] = os.environ['FLASK_ENV']
        app.config['DEBUG'] = os.environ['FLASK_ENV'] == 'development'
    
    logger.info(f"应用配置完成 (环境: {app.config['ENV'] if 'ENV' in app.config else 'production'})")

def init_db_connection(app):
    """初始化数据库连接
    
    Args:
        app (Flask): Flask应用实例
    """
    # 将在应用上下文中初始化数据库连接
    # 这通常在第一次请求时完成
    
    if hasattr(app, "before_serving"):
        @app.before_serving
        def before_serving():
            """在应用开始处理请求前初始化数据库连接"""
            from models.base import get_db_connection

            # 确保数据库连接可用
            get_db_connection()
            logger.info("数据库连接初始化完成")
    else:
        # 兼容性处理：旧版本Flask没有before_serving
        with app.app_context():
            from models.base import get_db_connection

            get_db_connection()
            logger.info("数据库连接初始化完成")

def init_services(app):
    """初始化服务组件
    
    Args:
        app (Flask): Flask应用实例
    """
    from database.connection import get_connection_pool

    connection_pool = get_connection_pool()
    
    # 创建服务实例
    query_service = QueryService(connection_pool)
    transaction_service = TransactionService(connection_pool)
    
    # 将服务添加到应用上下文
    app.query_service = query_service
    app.transaction_service = transaction_service
    
    logger.info("服务组件初始化完成")

def handle_404(error):
    """处理404错误的视图函数
    
    Args:
        error: 错误对象
        
    Returns:
        Response: 简单的404错误信息
    """
    logger.warning(f"404错误: {request.path}")
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>404 - 页面未找到</title>
        <style>
            body {
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .container {
                text-align: center;
                background: white;
                padding: 50px;
                border-radius: 10px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }
            h1 { color: #667eea; font-size: 72px; margin: 0; }
            p { color: #666; font-size: 18px; margin: 20px 0; }
            a { color: #667eea; text-decoration: none; font-weight: bold; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>404</h1>
            <p>抱歉，您访问的页面不存在</p>
            <a href="/">返回首页</a>
        </div>
    </body>
    </html>
    """, 404

def handle_500(error):
    """处理500错误的视图函数
    
    Args:
        error: 错误对象
        
    Returns:
        Response: 简单的500错误信息
    """
    logger.error(f"500错误: {str(error)}")
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>500 - 服务器错误</title>
        <style>
            body {
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            }
            .container {
                text-align: center;
                background: white;
                padding: 50px;
                border-radius: 10px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }
            h1 { color: #f5576c; font-size: 72px; margin: 0; }
            p { color: #666; font-size: 18px; margin: 20px 0; }
            a { color: #f5576c; text-decoration: none; font-weight: bold; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>500</h1>
            <p>抱歉，服务器遇到了问题</p>
            <p style="font-size: 14px; color: #999;">请稍后重试或联系管理员</p>
            <a href="/">返回首页</a>
        </div>
    </body>
    </html>
    """, 500

# 当作为脚本直接运行时执行
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)