# app/routes/generation_routes.py

from flask import Blueprint, request, jsonify, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Generation, User
from .. import db
import threading
from ..utils.helpers import api_response # 导入统一响应工具
from ..services.ai_service import generate_image_with_jimeng

# 创建蓝图
generation_blueprint = Blueprint('generation', __name__)


def process_generation_task(generation_id, prompt):
    """
    这是一个真实的后台任务，它会调用即梦AI的API，处理审核信息，并更新数据库。
    """
    from app import create_app
    app = create_app()
    with app.app_context():
        generation = Generation.query.get(generation_id)
        if not generation:
            print(f"任务 {generation_id} 在开始处理时已不存在。")
            return

        current_params = generation.parameters or {}
        output_filename = f"{generation.uuid}.jpg"
        
        print(f"开始调用即梦AI处理任务 {generation_id}，prompt: {prompt}")
        
        # ⭐️⭐️⭐️ --- 核心修正点：适配 ai_service 的返回值 --- ⭐️⭐️⭐️
        # 1. 只用一个变量来接收返回值
        saved_path = generate_image_with_jimeng(prompt, output_filename)
        
        # 2. 根据 saved_path 是否为 None 来自己判断成功与否
        if saved_path:
            review_passed = True
            review_msg = "Success"
        else:
            review_passed = False
            review_msg = "AI generation failed or returned an error." # 一个通用的失败信息
        # ⭐️⭐️⭐️ --- 修正结束 --- ⭐️⭐️⭐️
        
        # 构造 review 对象
        review_data = {
            "status": "approved" if review_passed else "rejected",
            "message": review_msg if not review_passed else None
        }
        # 更新到 parameters 中
        current_params['review'] = review_data
        generation.parameters = current_params

        if saved_path:
            # AI生成成功
            generation.status = 'completed'
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
    """发起一个新的生成任务 (对应文档 #11)"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()

    # 根据新文档，参数是 type, prompt, images (可选)
    if not data or 'prompt' not in data or 'type' not in data:
        return api_response(code=400, message="请求参数不完整 (需要 prompt 和 type)")

    try:
        new_generation = Generation(
            user_id=current_user_id,
            prompt=data['prompt'],
            generation_type=data['type'], # 使用新文档的 'type'
            status='processing'
        )
        db.session.add(new_generation)
        db.session.commit()
        
        thread = threading.Thread(target=process_generation_task, args=(new_generation.id, new_generation.prompt))
        thread.start()

        # 返回新文档要求的格式
        response_data = {
            "task_id": new_generation.uuid,
            "created_at": new_generation.created_at.isoformat() + "Z",
            "type": new_generation.generation_type,
            "prompt": new_generation.prompt,
            "parameters": new_generation.parameters,
        }
        return api_response(code=200, message="生成任务已创建", data=response_data)
    except Exception as e:
        db.session.rollback()
        print(f"创建生成任务时出错: {e}")
        return api_response(code=500, message="服务器内部错误")


@generation_blueprint.route('/<string:taskId>', methods=['GET'])
@jwt_required()
def get_generation_status(taskId):
    """根据任务 ID (taskId) 查询生成结果 (对应文档 #13)"""
    current_user_id = int(get_jwt_identity())
    
    # 使用 uuid (对应 taskId) 查询
    generation = Generation.query.filter_by(uuid=taskId).first()
    
    if not generation:
        return api_response(code=404, message="任务不存在")
        
    # 安全检查：确保用户只能查询自己的任务
    if generation.user_id != current_user_id:
        return api_response(code=403, message="无权访问此任务")
        
    # to_dict() 方法已经包含了所有需要的字段 (task_id, status, result_url etc.)
    return api_response(code=200, message="任务状态获取成功", data=generation.to_dict())