# app/routes/user_routes.py

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import User, Generation
from .. import db
from ..utils.helpers import api_response

user_blueprint = Blueprint('user', __name__)

# --- API 5: 修改密码接口 ---
@user_blueprint.route('/reset-password', methods=['POST'])
@jwt_required()
def reset_password():
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    data = request.get_json()

    if not data or 'old_password' not in data or 'new_password' not in data:
        return api_response(code=400, message="请求参数不完整")

    # 验证旧密码
    if not user.check_password(data['old_password']):
        return api_response(code=401, message="旧密码不正确")

    try:
        user.set_password(data['new_password'])
        db.session.commit()
        return api_response(code=200, message="成功修改密码")
    except Exception as e:
        db.session.rollback()
        return api_response(code=500, message="服务器内部错误")


# --- API 6: 修改邮箱接口 ---
@user_blueprint.route('/reset-email', methods=['POST'])
@jwt_required()
def reset_email():
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)
    data = request.get_json()

    if not data or 'new_email' not in data:
        return api_response(code=400, message="请求参数不完整")
    
    new_email = data['new_email']

    # 检查新邮箱是否已被其他用户注册
    if User.query.filter_by(email=new_email).first():
        return api_response(code=401, message="该邮箱已被注册")

    try:
        user.email = new_email
        db.session.commit()
        return api_response(code=200, message="成功修改邮箱", data={"email": user.email})
    except Exception as e:
        db.session.rollback()
        return api_response(code=500, message="服务器内部错误")


# --- API 7: 获取历史生成记录接口 ---
@user_blueprint.route('/generation_list', methods=['GET'])
@jwt_required()
def get_generation_list():
    current_user_id = int(get_jwt_identity())
    
    try:
        # 文档要求：记录应该按照时间升序排列 (asc)
        generations = Generation.query.filter_by(user_id=current_user_id)\
            .order_by(Generation.created_at.asc()).all()
        
        # 你的 Generation 模型中 to_dict 已经适配了 task_id 等字段
        data_list = [gen.to_dict() for gen in generations]
        
        return api_response(code=200, message="成功", data=data_list)
    except Exception as e:
        print(f"Fetch list error: {e}")
        return api_response(code=500, message="服务器内部错误")