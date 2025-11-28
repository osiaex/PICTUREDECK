# app/routes/auth_routes.py

from flask import Blueprint, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta # 用于计算token过期时间
from ..models import User
from .. import db
from ..utils.helpers import api_response # 导入我们的统一响应工具

auth_blueprint = Blueprint('auth', __name__)
user_blueprint = Blueprint('user', __name__) # 为 /api/v1/user/ 下的接口创建一个新蓝图

# --- 1. /api/v1/auth/ 下的接口 ---

@auth_blueprint.route('/register', methods=['POST'])
def register():
    """注册接口"""
    data = request.get_json()
    if not data or 'account' not in data or 'password' not in data or 'email' not in data:
        return api_response(code=400, message="请求参数不完整")

    # 检查账号或邮箱是否已存在
    if User.query.filter_by(username=data['account']).first():
        return api_response(code=401, message="账号已存在")
    if User.query.filter_by(email=data['email']).first():
        return api_response(code=402, message="邮箱已被注册")

    try:
        new_user = User(
            username=data['account'], # 数据库中仍存储为 username
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
        print(f"注册时发生数据库错误: {e}")
        return api_response(code=500, message="服务器内部错误")


@auth_blueprint.route('/login', methods=['POST'])
def login():
    """登录接口"""
    data = request.get_json()
    if not data or 'account' not in data or 'password' not in data:
        return api_response(code=400, message="请求参数不完整")

    user = User.query.filter_by(username=data['account']).first()

    if not user or not user.check_password(data['password']):
        return api_response(code=401, message="账号或密码错误")

    if user.status == 'banned':
        return api_response(code=403, message="账户已被封禁") # 假设403为封禁

    try:
        # 创建Token，可以设置过期时间
        expires = timedelta(hours=24)
        access_token = create_access_token(identity=str(user.id), expires_delta=expires)
        
        response_data = {
            "account": user.username,
            "email": user.email,
            "token": access_token,
            # "token_expire_at": (datetime.utcnow() + expires).isoformat() + "Z" # 如果需要返回过期时间
        }
        return api_response(code=200, message="登录成功", data=response_data)
    except Exception as e:
        print(f"登录时创建Token失败: {e}")
        return api_response(code=500, message="服务器内部错误")

@auth_blueprint.route('/forgot-password', methods=['POST'])
def forgot_password():
    """忘记密码，请求发送邮件接口 (框架)"""
    # 此处需要实现发送邮件的逻辑，例如使用 Flask-Mail 插件
    # 1. 获取 email
    # 2. 生成验证码或重置链接
    # 3. 将验证码存入Redis或数据库，并设置过期时间
    # 4. 发送邮件
    return api_response(code=501, message="此功能尚未实现")

@auth_blueprint.route('/reset-password', methods=['POST'])
def reset_password_with_code():
    """忘记密码，重置密码接口 (框架)"""
    # 1. 获取 email, verification_code, new_password
    # 2. 校验验证码的正确性和时效性
    # 3. 更新用户密码
    return api_response(code=501, message="此功能尚未实现")

# --- 2. /api/v1/user/ 下的接口 (需要登录) ---

@user_blueprint.route('/reset-password', methods=['POST'])
@jwt_required()
def reset_password_loggedin():
    """修改密码接口 (登录状态)"""
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    data = request.get_json()

    if not data or 'old_password' not in data or 'new_password' not in data:
        return api_response(code=400, message="请求参数不完整")

    if not user.check_password(data['old_password']):
        return api_response(code=401, message="旧密码不正确")

    try:
        user.set_password(data['new_password'])
        db.session.commit()
        return api_response(code=200, message="成功修改密码")
    except Exception as e:
        db.session.rollback()
        return api_response(code=500, message="服务器内部错误")


@user_blueprint.route('/reset-email', methods=['POST'])
@jwt_required()
def reset_email():
    """修改邮箱接口 (登录状态)"""
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    data = request.get_json()

    if not data or 'new_email' not in data:
        return api_response(code=400, message="请求参数不完整")

    new_email = data['new_email']
    if User.query.filter_by(email=new_email).first():
        return api_response(code=401, message="该邮箱已被注册")

    try:
        user.email = new_email
        db.session.commit()
        response_data = {"email": user.email}
        return api_response(code=200, message="成功修改邮箱", data=response_data)
    except Exception as e:
        db.session.rollback()
        return api_response(code=500, message="服务器内部错误")

# (之前的 /profile 测试接口可以删掉或保留)
@user_blueprint.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """获取当前用户信息 (测试接口)"""
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    if not user:
        return api_response(code=404, message="用户不存在")
    return api_response(code=200, message="获取成功", data=user.to_dict())