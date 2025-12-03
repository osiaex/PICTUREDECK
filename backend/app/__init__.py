# app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from flask_jwt_extended import JWTManager 

db = SQLAlchemy()
jwt = JWTManager()

def create_app():
    """创建并配置Flask应用"""
    app = Flask(__name__)
    
    # 从config.py加载配置
    app.config.from_object(Config)
    jwt.init_app(app)
    db.init_app(app)
    
    # 注册蓝图
    from .routes.auth_routes import auth_blueprint 
    app.register_blueprint(auth_blueprint, url_prefix='/api/v1/auth')

    # 2. User 模块 (改为从新的 user_routes 文件导入)
    from .routes.user_routes import user_blueprint
    app.register_blueprint(user_blueprint, url_prefix='/api/v1/user')
    
    from .routes.generation_routes import generation_blueprint
    app.register_blueprint(generation_blueprint, url_prefix='/api/v1/generation')
    
    # ⭐️ 关键修改：把这里的 url_prefix 改成了 /api/v1/user
    # 这样你的接口地址就是 /api/v1/user/favorite_list，完全符合文档
    from .routes.collection_routes import collection_blueprint
    app.register_blueprint(collection_blueprint, url_prefix='/api/v1/user')
    
    from .routes.static_routes import static_files_blueprint
    app.register_blueprint(static_files_blueprint)
    
    return app