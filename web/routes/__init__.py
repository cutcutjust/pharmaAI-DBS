"""
Web路由包(Web Routes Package)

本包提供智药AI系统Web应用的路由处理功能，负责处理HTTP请求，
连接前端页面和后端服务，为用户提供对话查询和实验管理的Web界面。

使用方法:
    # 在Flask应用中注册路由
    from web.routes.conversation_routes import register_conversation_routes
    from web.routes.experiment_routes import register_experiment_routes
    
    def create_app():
        app = Flask(__name__)
        
        # 注册对话查询路由
        register_conversation_routes(app)
        
        # 注册实验管理路由
        register_experiment_routes(app)
        
        return app
    
    # 创建并运行应用
    app = create_app()
    app.run(debug=True)

包含模块:
    - conversation_routes.py: 提供对话查询相关的路由处理
    - experiment_routes.py: 提供实验记录管理相关的路由处理
"""

# 导入需要对外暴露的函数和类
from web.routes.conversation_routes import register_conversation_routes
from web.routes.experiment_routes import register_experiment_routes

__all__ = ['register_conversation_routes', 'register_experiment_routes']