# app/models.py

# --- 关键点 2 ---
# 这里，我们从当前包 (app) 中，导入那个已经被创建好的 "db" 对象
from . import db
from werkzeug.security import generate_password_hash, check_password_hash

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