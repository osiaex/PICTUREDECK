# app/routes/auth_routes.py

from flask import Blueprint, request, jsonify
from ..models import User
from .. import db  # <--- 修正点：从父包导入db

# 蓝图定义保持不变...
auth_blueprint = Blueprint('auth', __name__)

# 注册和登录的函数保持不变...
@auth_blueprint.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not 'username' in data or not 'password' in data or not 'email' in data:
        return jsonify({"message": "请求参数不完整"}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({"message": "用户名已存在"}), 409
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"message": "邮箱已被注册"}), 409

    new_user = User(
        username=data['username'],
        email=data['email']
    )
    new_user.set_password(data['password'])
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"message": "注册成功", "user": new_user.to_dict()}), 201


@auth_blueprint.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not 'username' in data or not 'password' in data:
        return jsonify({"message": "请求参数不完整"}), 400

    user = User.query.filter_by(username=data['username']).first()

    if not user or not user.check_password(data['password']):
        return jsonify({"message": "用户名或密码错误"}), 401

    if user.status == 'banned':
        return jsonify({"message": "账户已被封禁"}), 403

    return jsonify({"message": "登录成功", "user": user.to_dict()}), 200