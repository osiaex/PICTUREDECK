# app/routes/auth_routes.py

import random
import time
from flask import Blueprint, request
from flask_jwt_extended import create_access_token
from datetime import timedelta, datetime, timezone
from flask_mail import Message

from ..models import User
from .. import db, mail
from ..utils.helpers import api_response

auth_blueprint = Blueprint('auth', __name__)

# 内存存储验证码 { "email": {"code": "123456", "expire_at": timestamp} }
VERIFICATION_CODES = {}

def generate_code():
    """生成6位数字验证码"""
    return str(random.randint(100000, 999999))

# --- API 1: 注册 ---
@auth_blueprint.route('/register', methods=['POST'])
def register():
    """注册接口"""
    data = request.get_json()
    if not data or 'account' not in data or 'password' not in data or 'email' not in data:
        return api_response(code=400, message="请求参数不完整")

    if User.query.filter_by(username=data['account']).first():
        return api_response(code=401, message="账号已存在")
    if User.query.filter_by(email=data['email']).first():
        return api_response(code=402, message="邮箱已被注册")

    try:
        new_user = User(
            username=data['account'],
            email=data['email']
        )
        new_user.set_password(data['password'])
        db.session.add(new_user)
        db.session.commit()
        
        response_data = {
            "account": new_user.username,
            "email": new_user.email,
            "created_at": new_user.created_at.isoformat() + "Z"
        }
        return api_response(code=200, message="注册成功", data=response_data)
    except Exception as e:
        db.session.rollback()
        print(f"注册错误: {e}")
        return api_response(code=500, message="服务器内部错误")

# --- API 2: 登录 ---
@auth_blueprint.route('/login', methods=['POST'])
def login():
    """登录接口"""
    data = request.get_json()
    if not data or 'account' not in data or 'password' not in data:
        return api_response(code=400, message="请求参数不完整")

    user = User.query.filter_by(username=data['account']).first()

    if not user or not user.check_password(data['password']):
        return api_response(code=401, message="账号或密码错误")

    if hasattr(user, 'status') and user.status == 'banned':
        return api_response(code=403, message="账户已被封禁")

    try:
        expires = timedelta(hours=24)
        access_token = create_access_token(identity=str(user.id), expires_delta=expires)
        expire_time = datetime.now(timezone.utc) + expires
        
        response_data = {
            "account": user.username,
            "email": user.email,
            "token": access_token,
            "token_expire_at": expire_time.isoformat().replace("+00:00", "Z")
        }
        return api_response(code=200, message="登录成功", data=response_data)
    except Exception as e:
        print(f"登录错误: {e}")
        return api_response(code=500, message="服务器内部错误")

# --- API 3: 忘记密码，请求发送邮件 ---
@auth_blueprint.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    if not data or 'email' not in data:
         return api_response(code=400, message="参数不合规")
    
    email = data['email']
    
    # 1. 检查邮箱是否存在
    user = User.query.filter_by(email=email).first()
    if not user:
        # 为了安全也可以返回成功，但作业里直接提示
        return api_response(code=401, message="该邮箱未注册")

    # 2. 生成验证码
    code = generate_code()
    
    # 3. 存入内存 (有效期 5 分钟)
    VERIFICATION_CODES[email] = {
        "code": code,
        "expire_at": time.time() + 300
    }

    # 4. 发送邮件
    try:
        msg = Message("【AI创作平台】重置密码验证码", recipients=[email])
        msg.body = f"您好，您的重置密码验证码是：{code}。\n有效期5分钟，请勿泄露给他人。"
        mail.send(msg)
        print(f"验证码 {code} 已发送至 {email}") # 后台打印，方便没配好邮箱时调试
        return api_response(code=200, message="邮件已发送")
    except Exception as e:
        print(f"发送邮件失败: {e}")
        # 如果邮箱配置没填对，这里会报错，但在控制台能看到验证码，依然可以测试流程
        return api_response(code=500, message="发送邮件失败(请检查Config配置)")

# --- API 4: 忘记密码，重置密码 ---
@auth_blueprint.route('/reset-password', methods=['POST'])
def reset_password_verify():
    data = request.get_json()
    required = ['email', 'verification_code', 'new_password']
    if not data or not all(k in data for k in required):
        return api_response(code=400, message="参数不合规")

    email = data['email']
    code = data['verification_code']
    new_password = data['new_password']

    # 1. 校验验证码
    record = VERIFICATION_CODES.get(email)
    if not record:
        return api_response(code=401, message="验证码不存在或已过期")
    
    if time.time() > record['expire_at']:
        del VERIFICATION_CODES[email]
        return api_response(code=401, message="验证码已过期")
    
    if record['code'] != code:
        return api_response(code=401, message="验证码错误")

    # 2. 查找用户并重置密码
    user = User.query.filter_by(email=email).first()
    if not user:
        return api_response(code=401, message="用户不存在")

    try:
        user.set_password(new_password)
        db.session.commit()
        
        # 成功后清除验证码
        if email in VERIFICATION_CODES:
            del VERIFICATION_CODES[email]
        
        return api_response(code=200, message="成功重置密码")
    except Exception as e:
        db.session.rollback()
        return api_response(code=500, message="服务器内部错误")