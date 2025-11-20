# app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from flask_jwt_extended import JWTManager 
# --- 关键点 1 ---
# 在这里，我们用 "图纸" (SQLAlchemy) 创建了全局的 "db" 对象实例
db = SQLAlchemy()
jwt = JWTManager()

def create_app():
    """创建并配置Flask应用"""
    app = Flask(__name__)
    
    # 从config.py加载配置
    app.config.from_object(Config)
    jwt.init_app(app) # ⭐️ 3. 将 JWTManager 与 app 关联
    # 将创建好的 db 对象与 app 关联
    db.init_app(app)
    
    # 注册蓝图 (我们的API接口)
    from .routes.auth_routes import auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/api/v1/auth')
    from .routes.generation_routes import generation_blueprint
    app.register_blueprint(generation_blueprint, url_prefix='/api/v1/generations')
    return app