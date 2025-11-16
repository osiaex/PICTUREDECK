# run.py

# --- 关键点 3 ---
# 这里，我们从 app 包中，导入 create_app 函数和 db 对象
# 这能够成功的前提是：VS Code 的工作目录必须是 backend
from app import create_app, db
from app.models import User # 导入模型，确保 create_all 能找到它们

app = create_app()

if __name__ == '__main__':
    # 使用 app.app_context() 来确保应用上下文是活动的
    # 这样 SQLAlchemy 才能知道连接哪个数据库
    with app.app_context():
        db.create_all()
    
    # 启动Web服务器
    app.run(debug=True)