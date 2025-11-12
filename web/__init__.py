"""
Web应用包(Web Application Package)

本包提供智药AI系统的Web应用功能，实现前端页面展示和用户交互，
满足课程要求的"前端页面只要一到两个具体的业务实现即可"。

使用方法:
    # 导入并创建Flask应用
    from web.app import create_app
    
    app = create_app()
    
    # 或在主模块中运行
    if __name__ == '__main__':
        app.run(host='0.0.0.0', port=5000, debug=True)
    
    # 访问应用
    # 对话查询: http://localhost:5000/conversations
    # 实验管理: http://localhost:5000/experiments

包含模块:
    - app.py: Flask应用创建和配置
    - routes/: 路由处理模块目录
      - conversation_routes.py: 对话查询路由
      - experiment_routes.py: 实验管理路由
    - templates/: 模板文件目录
      - base.html: 基础模板
      - conversation_search.html: 对话查询页面
      - experiment_manage.html: 实验管理页面
"""

from utils.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)

# 版本信息
__version__ = '1.0.0'

# 包含子模块
__all__ = ['app', 'routes', 'templates']

# 初始化日志
logger.info(f"加载Web应用包 (版本: {__version__})")

# 导入主要组件方便直接从包中导入
from web.app import create_app