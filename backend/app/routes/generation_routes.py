# app/routes/generation_routes.py

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Generation, User
from .. import db
import threading
import time
# 创建一个新的蓝图
generation_blueprint = Blueprint('generation', __name__)


def simulate_ai_processing(generation_id):
    """一个模拟AI处理的后台任务"""
    from app import create_app
    app = create_app()
    with app.app_context():
        # 模拟耗时5秒
        print(f"开始处理任务 {generation_id}...")
        time.sleep(5)
        
        # 任务处理完成，更新数据库
        generation = Generation.query.get(generation_id)
        if generation:
            generation.status = 'completed'
            generation.result_url = f"https://example.com/images/{generation.uuid}.png" # 假的URL
            generation.completed_at = db.func.current_timestamp()
            db.session.commit()
            print(f"任务 {generation_id} 处理完成！")

@generation_blueprint.route('', methods=['POST'])
@jwt_required()
def create_generation_task():
    """发起一个新的生成任务"""
    current_user_id = get_jwt_identity()
    data = request.get_json()

    if not data or 'prompt' not in data or 'generation_type' not in data:
        return jsonify({"message": "请求参数不完整(需要prompt和generation_type)"}), 400

    # 创建一个新的Generation记录
    new_generation = Generation(
        user_id=int(current_user_id),
        prompt=data['prompt'],
        generation_type=data['generation_type'],
        status='processing' # 直接设置为处理中
    )
    db.session.add(new_generation)
    db.session.commit()
    
    # 启动一个后台线程来模拟处理，避免阻塞主线程
    # new_generation.id 是在 commit 后才有的
    thread = threading.Thread(target=simulate_ai_processing, args=(new_generation.id,))
    thread.start()

    return jsonify({
        "message": "任务已提交，正在处理中...",
        "task": new_generation.to_dict()
    }), 202 # 202 Accepted 表示服务器已接受请求，但尚未完成处理

@generation_blueprint.route('/<string:task_uuid>', methods=['GET'])
@jwt_required()
def get_generation_status(task_uuid):
    """根据UUID查询任务状态"""
    current_user_id = int(get_jwt_identity())
    
    generation = Generation.query.filter_by(uuid=task_uuid).first()
    
    if not generation:
        return jsonify({"message": "任务不存在"}), 404
        
    # 安全检查：确保用户只能查询自己的任务
    if generation.user_id != current_user_id:
        return jsonify({"message": "无权访问此任务"}), 403
        
    return jsonify(generation.to_dict()), 200
