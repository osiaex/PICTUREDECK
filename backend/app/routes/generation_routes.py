# app/routes/generation_routes.py

from flask import Blueprint, request, jsonify, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Generation, User
from .. import db
import threading

# 1. 导入我们新的、真实的 AI 服务函数
from ..services.ai_service import generate_image_with_jimeng

# 创建蓝图
generation_blueprint = Blueprint('generation', __name__)


def process_generation_task(generation_id, prompt):
    """
    这是一个真实的后台任务，它会调用即梦AI的API并更新数据库。
    之前的 simulate_ai_processing 函数已被此函数替换。
    """
    # 在新线程中，我们需要重新创建app上下文，以便访问数据库和配置
    from app import create_app
    app = create_app()
    with app.app_context():
        generation = Generation.query.get(generation_id)
        if not generation:
            print(f"任务 {generation_id} 在开始处理时已不存在。")
            return

        # 为生成的图片创建一个唯一的文件名
        output_filename = f"{generation.uuid}.jpg"  # 即梦AI返回的是jpeg格式
        
        # 2. 调用真实的AI服务函数
        print(f"开始调用即梦AI处理任务 {generation_id}，prompt: {prompt}")
        saved_path = generate_image_with_jimeng(prompt, output_filename)
        
        # 3. 根据AI服务返回的结果，更新数据库记录
        if saved_path:
            # AI生成成功
            generation.status = 'completed'
            # 创建一个可以通过浏览器访问的URL
            # 注意: 'static_files.get_output_file' 对应我们后面要创建的静态文件路由
            generation.result_url = url_for('static_files.get_output_file', filename=output_filename, _external=True)
            generation.physical_path = saved_path
            print(f"任务 {generation_id} 处理成功。")
        else:
            # AI生成失败
            generation.status = 'failed'
            print(f"任务 {generation_id} 处理失败。")
            
        generation.completed_at = db.func.current_timestamp()
        db.session.commit()


@generation_blueprint.route('', methods=['POST'])
@jwt_required()
def create_generation_task():
    """发起一个新的生成任务 (接口逻辑保持不变)"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data or 'prompt' not in data or 'generation_type' not in data:
        return jsonify({"message": "请求参数不完整 (需要 prompt 和 generation_type)"}), 400

    # 在数据库中创建一条新的任务记录
    new_generation = Generation(
        user_id=current_user_id,
        prompt=data['prompt'],
        generation_type=data['generation_type'],
        status='processing' # 初始状态设置为“处理中”
    )
    db.session.add(new_generation)
    db.session.commit()
    
    # 4. 启动新的、真实的后台处理线程
    # 我们把新创建任务的id和prompt传递给后台函数
    thread = threading.Thread(target=process_generation_task, args=(new_generation.id, new_generation.prompt))
    thread.start()

    return jsonify({
        "message": "任务已提交，正在处理中...",
        "task": new_generation.to_dict()
    }), 202


@generation_blueprint.route('/<string:task_uuid>', methods=['GET'])
@jwt_required()
def get_generation_status(task_uuid):
    """根据UUID查询任务状态 (接口逻辑保持不变)"""
    current_user_id = int(get_jwt_identity())
    
    generation = Generation.query.filter_by(uuid=task_uuid).first()
    
    if not generation:
        return jsonify({"message": "任务不存在"}), 404
        
    if generation.user_id != current_user_id:
        return jsonify({"message": "无权访问此任务"}), 403
        
    return jsonify(generation.to_dict()), 200