# app/routes/collection_routes.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Collection, Generation, User
from .. import db

collection_blueprint = Blueprint('collection', __name__)

# ⭐️⭐️⭐️ --- 新增代码开始 --- ⭐️⭐️⭐️
@collection_blueprint.route('', methods=['POST'])
@jwt_required()
def create_folder():
    """创建一个新的文件夹"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data or 'name' not in data:
        return jsonify({"message": "需要文件夹名称(name)"}), 400

    parent_id = data.get('parent_id') # 可以指定父文件夹，默认为根目录

    # 安全检查：如果指定了parent_id，要确保父文件夹存在且属于当前用户
    if parent_id:
        parent_folder = Collection.query.filter_by(id=parent_id, user_id=current_user_id, node_type='folder').first()
        if not parent_folder:
            return jsonify({"message": "指定的父文件夹不存在或无权访问"}), 404

    new_folder = Collection(
        user_id=current_user_id,
        parent_id=parent_id,
        name=data['name'],
        node_type='folder'
    )
    db.session.add(new_folder)
    db.session.commit()

    return jsonify(new_folder.to_dict()), 201

@collection_blueprint.route('', methods=['GET'])
@jwt_required()
def get_collections_tree():
    """获取用户的整个文件/文件夹树"""
    current_user_id = int(get_jwt_identity())
    
    # 找到用户的所有根节点 (通常只有一个)
    root_nodes = Collection.query.filter_by(user_id=current_user_id, parent_id=None).all()
    
    # 将整个树结构序列化
    tree = [node.to_dict(include_children=True) for node in root_nodes]
    
    return jsonify(tree), 200

@collection_blueprint.route('/items', methods=['POST'])
@jwt_required()
def add_generation_to_collection():
    """将一个已生成的作品添加为一个收藏'文件'"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data or 'generation_uuid' not in data:
        return jsonify({"message": "需要提供 generation_uuid"}), 400
        
    generation_uuid = data.get('generation_uuid')
    parent_id = data.get('parent_id') # 目标文件夹ID, 可选

    # 查找作品
    generation = Generation.query.filter_by(uuid=generation_uuid, user_id=current_user_id).first()
    if not generation:
        return jsonify({"message": "作品不存在或无权访问"}), 404
    
    # 检查是否已在收藏中
    if Collection.query.filter_by(generation_id=generation.id).first():
        return jsonify({"message": "该作品已在收藏中"}), 409

    # 创建新的'file'节点
    new_file_node = Collection(
        user_id=current_user_id,
        parent_id=parent_id,
        name=f"作品_{generation.id}.png", # 默认文件名，可以前端传入
        node_type='file',
        generation_id=generation.id
    )
    db.session.add(new_file_node)
    db.session.commit()

    return jsonify(new_file_node.to_dict()), 201
# ⭐️⭐️⭐️ --- 新增代码结束 --- ⭐️⭐️⭐️