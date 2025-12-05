# app/routes/collection_routes.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Collection, Generation, User
from .. import db
from ..utils.helpers import api_response 
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

@collection_blueprint.route('/favorite_list', methods=['GET'])
@jwt_required()
def get_favorite_list():
    current_user_id = int(get_jwt_identity())
    
    # 查询该用户的所有收藏节点
    collections = Collection.query.filter_by(user_id=current_user_id).all()
    
    data_list = []
    for node in collections:
        item = {
            "id": node.id,
            "parent_id": node.parent_id,
            "name": node.name,
            "node_type": node.node_type
        }
        # 如果是文件类型，尝试获取 refer_url
        if node.node_type == 'file' and node.generation:
            # 你的 Generation 模型里有 result_url
            item['refer_url'] = node.generation.result_url
        elif node.node_type == 'file':
             # 容错处理：有节点但没关联生成记录
             item['refer_url'] = "" 
             
        data_list.append(item)

    return api_response(code=200, message="成功获取收藏夹列表", data=data_list)


# --- 对应文档 API 9: 新增收藏夹内容 ---
@collection_blueprint.route('/favorite_list', methods=['POST'])
@jwt_required()
def add_favorite_item():
    current_user_id = int(get_jwt_identity())
    data = request.get_json()

    # 文档参数: parent_id, name, node_type, refer_url(可选)
    if not data or 'name' not in data or 'node_type' not in data:
        return api_response(code=400, message="参数不合规")
    
    parent_id = data.get('parent_id')
    node_type = data['node_type']
    refer_url = data.get('refer_url')
    
    generation_id = None
    
    # 如果是文件，文档传的是 refer_url，但我们要存 generation_id
    if node_type == 'file' and refer_url:
        # 尝试通过 refer_url 反查 Generation
        # 这里做一个简单的模糊匹配，或者你可以要求前端传 id，但为了适配文档：
        gen = Generation.query.filter(
            Generation.result_url == refer_url, 
            Generation.user_id == current_user_id
        ).first()
        
        if gen:
            generation_id = gen.id
        else:
            # 如果找不到对应的生成记录，这里需要决定是报错还是允许存空
            # 根据小组作业特性，建议先放行，或者只存名字
            pass

    try:
        new_node = Collection(
            user_id=current_user_id,
            parent_id=parent_id,
            name=data['name'],
            node_type=node_type,
            generation_id=generation_id
        )
        db.session.add(new_node)
        db.session.commit()
        
        return api_response(code=200, message="成功创建新收藏内容", data={"id": new_node.id})
        
    except Exception as e:
        db.session.rollback()
        # 打印错误方便调试
        print(f"创建收藏失败: {e}")
        return api_response(code=500, message="服务器内部错误")


# --- 对应文档 API 10: 删除收藏夹内容 ---
# 文档 URI: /api/v1/user/favorite_list/{collectionid}
@collection_blueprint.route('/favorite_list/<int:collection_id>', methods=['DELETE'])
@jwt_required()
def delete_favorite_item(collection_id):
    current_user_id = int(get_jwt_identity())
    
    # 查找要删除的节点
    node = Collection.query.filter_by(id=collection_id, user_id=current_user_id).first()
    
    if not node:
        # 为了幂等性，不存在也可以返回成功，或者返回404
        return api_response(code=400, message="节点不存在或无权删除")

    try:
        # 你的 Collection 模型定义了 children 关系
        # 如果需要级联删除，需要递归逻辑或者依赖数据库的 CASCADE
        # 这里为了简单，先做手动删除子节点（如果是文件夹）
        
        deleted_items = []
        
        def delete_recursive(current_node):
            # 记录被删除的信息用于返回
            deleted_items.append({"id": current_node.id, "name": current_node.name})
            
            # 查找子节点
            children = Collection.query.filter_by(parent_id=current_node.id).all()
            for child in children:
                delete_recursive(child)
            
            db.session.delete(current_node)

        delete_recursive(node)
        db.session.commit()

        return api_response(code=200, message="删除收藏夹内容成功", data=deleted_items)
        
    except Exception as e:
        db.session.rollback()
        print(f"删除失败: {e}")
        return api_response(code=500, message="服务器内部错误")

@collection_blueprint.route('/favorite_list/batch', methods=['POST'])
@jwt_required()
def batch_add_favorite_items():
    """
    接口 16: 批量新增收藏夹内容
    难点：处理 temp_id 和 parent_temp_id 的依赖关系
    """
    current_user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data or 'items' not in data:
        return api_response(code=400, message="参数 items 缺失")
    
    items = data['items'] # 这是一个列表
    if not items:
        return api_response(code=200, message="没有需要创建的项", data={"mapping": {}})

    # 临时ID 到 真实数据库ID 的映射
    # 格式: { 1: 32, 2: 33 }
    temp_id_map = {} 
    
    # 待处理队列 (为了防止无限循环，通常限制最大轮数，这里简化处理)
    pending_items = items[:] 
    
    # 用于记录本轮是否有进展，防止死循环（比如父节点不存在）
    processed_count = 0
    
    # 最多循环 len(items) 次，防止死锁
    max_loops = len(items) + 2 
    loop_counter = 0

    while pending_items and loop_counter < max_loops:
        loop_counter += 1
        next_round_items = []
        progress_made = False

        for item in pending_items:
            temp_id = item.get('temp_id')
            parent_id = item.get('parent_id')           # 真实父ID
            parent_temp_id = item.get('parent_temp_id') # 临时父ID
            name = item.get('name')
            node_type = item.get('node_type')
            refer_url = item.get('refer_url')

            real_parent_id = None

            # 情况A: 指定了真实的 parent_id (挂在已存在的文件夹下)
            if parent_id is not None:
                real_parent_id = parent_id
            
            # 情况B: 指定了 parent_temp_id (挂在本次批量创建的新文件夹下)
            elif parent_temp_id is not None:
                if parent_temp_id in temp_id_map:
                    real_parent_id = temp_id_map[parent_temp_id]
                else:
                    # 父节点还没创建，留到下一轮
                    next_round_items.append(item)
                    continue
            
            # 情况C: 根节点 (既没 parent_id 也没 parent_temp_id)
            else:
                real_parent_id = None

            # --- 执行插入 ---
            generation_id = None
            if node_type == 'file' and refer_url:
                # 尝试查找关联的 generation
                gen = Generation.query.filter_by(result_url=refer_url, user_id=current_user_id).first()
                if gen:
                    generation_id = gen.id

            try:
                new_node = Collection(
                    user_id=current_user_id,
                    parent_id=real_parent_id,
                    name=name,
                    node_type=node_type,
                    generation_id=generation_id
                )
                db.session.add(new_node)
                
                # 必须 flush 以获取 id，但先不 commit 以保持事务原子性
                db.session.flush() 
                
                # 记录映射关系
                if temp_id is not None:
                    temp_id_map[temp_id] = new_node.id
                
                progress_made = True
                
            except Exception as e:
                print(f"Batch Create Error Item {temp_id}: {e}")
                db.session.rollback()
                return api_response(code=500, message="批量创建内部错误")

        pending_items = next_round_items
        
        if not progress_made and pending_items:
            # 如果还有剩余项，但这一轮没有任何进展，说明存在无法解析的依赖（比如parent_temp_id指向不存在的ID）
            db.session.rollback()
            return api_response(code=400, message="批量创建失败：存在无法解析的父子依赖关系")

    try:
        db.session.commit()
        # 将 key 转为字符串返回，保证 JSON 兼容性
        str_map = {str(k): v for k, v in temp_id_map.items()}
        return api_response(code=200, message="批量创建成功", data={"mapping": str_map})
    except Exception as e:
        db.session.rollback()
        return api_response(code=500, message="数据库提交失败")