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
    VOLC_ACCESS_KEY_ID = "AKLTZGM1MTMxY2Q5ODg2NDFkMWE3ODI2MGYwODQ2NmUwNDQ"
    VOLC_SECRET_ACCESS_KEY = "TUdZMk56RTJORFZrT1RNd05ETTVZams0WXpFNVlqUmtaREZrWXpFNU16WQ=="
    # 图片保存的根目录
    OUTPUTS_DIR = os.path.join(os.path.abspath(os.path.dirname(__name__)), 'generated_outputs')

    # 参考图片保存目录
    REF_DIR = os.path.join(os.path.abspath(os.path.dirname(__name__)), 'reference_images')
    
    SERVER_NAME = "127.0.0.1:5000"
    
    # (可选，但推荐) 明确指定 URL 方案
    PREFERRED_URL_SCHEME = "http"


    #下面是NFT的内容。定义好NFT的合约地址和客户端ID。
    THIRDWEB_CLIENT_ID="d7d937da8bccd8f51d1a02ade326f652"
    
    THIRDWEB_NFT_CONTRACT="0xcD7B1852A152DCC1199840aC59Fb9fcb5E9bDcA1"
    #合约地址如上,这是我第一次mint的nft,名为CAT0,有20份.

    THIRDWEB_CLIENT_ID = os.getenv("THIRDWEB_CLIENT_ID", "")
    THIRDWEB_NFT_CONTRACT = os.getenv("THIRDWEB_NFT_CONTRACT", "")


    # ⭐️⭐️⭐️ 新增邮件配置 (以QQ邮箱为例) ⭐️⭐️⭐️
    MAIL_SERVER = 'smtp.qq.com'          # QQ邮箱服务器
    MAIL_PORT = 465                      # SSL端口
    MAIL_USE_SSL = True                  # 开启SSL
    MAIL_USERNAME = '1402175551@qq.com'     # 发送方邮箱
    MAIL_PASSWORD = 'hukxgvcnjaobghad'       # ⚠️ 注意：这里填SMTP授权码，不是QQ密码！
    MAIL_DEFAULT_SENDER = '1402175551@qq.com' # 默认发送者