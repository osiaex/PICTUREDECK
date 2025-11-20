# app/models.py

# --- 关键点 2 ---
# 这里，我们从当前包 (app) 中，导入那个已经被创建好的 "db" 对象
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
import uuid # 导入uuid库来生成业务ID
# User类的定义不变...
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.BigInteger, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('user', 'admin'), nullable=False, default='user')
    status = db.Column(db.Enum('active', 'banned'), nullable=False, default='active')
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    updated_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return { "id": self.id, "username": self.username, "email": self.email }


class Generation(db.Model):
    __tablename__ = 'generations'

    id = db.Column(db.BigInteger, primary_key=True)
    # default=lambda: str(uuid.uuid4()) 让数据库在插入时自动生成一个UUID
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.Enum('queued', 'processing', 'completed', 'failed'), nullable=False, default='queued')
    generation_type = db.Column(db.Enum('t2i', 'i2i', 't2v', 'i2v'), nullable=False)
    prompt = db.Column(db.Text, nullable=True)
    parameters = db.Column(db.JSON, nullable=True)
    result_url = db.Column(db.String(512), nullable=True)
    physical_path = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())
    completed_at = db.Column(db.TIMESTAMP, nullable=True)
    
    # 关联到 User 模型
    user = db.relationship('User', backref=db.backref('generations', lazy=True))

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "user_id": self.user_id,
            "status": self.status,
            "generation_type": self.generation_type,
            "prompt": self.prompt,
            "result_url": self.result_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }