# app/routes/user_routes.py

from typing import Collection
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

@user_blueprint.route('/generation_list', methods=['POST'])
@jwt_required()
def delete_generation_record():
    """
    接口 15: 删除生成记录
    注意：文档要求是 POST 方法，且通过 result_url 定位
    """
    current_user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data or 'result_url' not in data:
        return api_response(code=400, message="缺少 result_url 参数")

    result_url = data['result_url']

    # 查找记录
    gen_record = Generation.query.filter_by(result_url=result_url, user_id=current_user_id).first()

    if not gen_record:
        # 为了幂等性，找不到也可以算成功，或者返回 404，这里按文档风格返回 400 或忽略
        return api_response(code=400, message="未找到对应的生成记录")

    try:
        # 1. 删除关联的收藏夹条目 (如果有)
        # 你的 Collection 模型有 generation_id 外键，如果是级联删除可以省去这一步
        # 但显式删除更安全
        Collection.query.filter_by(generation_id=gen_record.id).delete()

        # 2. 删除生成记录本身
        db.session.delete(gen_record)
        
        # 注意：这里我们只删除了数据库记录，物理文件 (gen_record.physical_path) 通常保留或由定期脚本清理
        
        db.session.commit()
        return api_response(code=200, message="生成记录删除成功", data={"result_url": result_url})
    
    except Exception as e:
        db.session.rollback()
        return api_response(code=500, message="服务器内部错误")