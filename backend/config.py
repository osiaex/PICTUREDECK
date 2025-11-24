# config.py

import os

class Config:
    # 密钥，用于保护会话和CSRF等
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-hard-to-guess-string'

    # ⭐️ 新增JWT密钥配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'another-super-secret-key'
    # 数据库配置
    # 格式: mysql+pymysql://<user>:<password>@<host>/<dbname>
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:root@localhost/aigc'
    
    # 关闭Flask-SQLAlchemy的事件通知系统，节省资源
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 可选：打印执行的SQL语句，方便调试
    SQLALCHEMY_ECHO = True

    # 即梦 AI (火山引擎) 的密钥
    
    
    # 图片保存的根目录
    OUTPUTS_DIR = os.path.join(os.path.abspath(os.path.dirname(__name__)), 'generated_outputs')

    SERVER_NAME = "127.0.0.1:5000"
    
    # (可选，但推荐) 明确指定 URL 方案
    PREFERRED_URL_SCHEME = "http"