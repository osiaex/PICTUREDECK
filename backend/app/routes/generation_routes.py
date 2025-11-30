# app/routes/generation_routes.py

from flask import Blueprint, request, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Generation
from .. import db
import threading
from ..utils.helpers import api_response
# 引入新写的两个函数
from ..services.ai_service import generate_image_with_jimeng, generate_video_with_jimeng

generation_blueprint = Blueprint('generation', __name__)

def process_generation_task(generation_id):
    """
    后台任务：根据类型调用不同的AI能力
    """
    from app import create_app
    app = create_app()
    with app.app_context():
        generation = Generation.query.get(generation_id)
        if not generation: return

        prompt = generation.prompt
        gen_type = generation.generation_type
        
        # 决定文件后缀
        ext = 'mp4' if gen_type in ['t2v', 'i2v'] else 'jpg'
        output_filename = f"{generation.uuid}.{ext}"
        
        print(f"开始处理任务 {generation_id} [{gen_type}]: {prompt}")

        saved_path = None
        
        # ⭐️ 分流逻辑
        if gen_type == 't2i':
            saved_path = generate_image_with_jimeng(prompt, output_filename)
        elif gen_type == 't2v':
            # 调用新写的视频生成函数
            saved_path = generate_video_with_jimeng(prompt, output_filename)
        else:
            print(f"未实现的生成类型: {gen_type}")

        # --- 后续处理保持不变 ---
        current_params = generation.parameters or {}
        
        if saved_path:
            review_passed = True
            review_msg = "Success"
        else:
            review_passed = False
            review_msg = "Generation failed."
        
        current_params['review'] = {
            "status": "approved" if review_passed else "rejected",
            "message": review_msg if not review_passed else None
        }
        generation.parameters = current_params

        if saved_path:
            generation.status = 'completed'
            # 这里的 URL 指向本地静态文件
            generation.result_url = url_for('static_files.get_output_file', filename=output_filename, _external=True)
            generation.physical_path = saved_path
        else:
            generation.status = 'failed'
            
        generation.completed_at = db.func.current_timestamp()
        db.session.commit()
        print(f"任务 {generation_id} 结束，状态: {generation.status}")


@generation_blueprint.route('', methods=['POST'])
@jwt_required()
def create_generation_task():
    """发起任务接口 (适配文档 #11)"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data or 'prompt' not in data or 'type' not in data:
        return api_response(code=400, message="请求参数不完整")
    
    gen_type = data['type'] # t2i, t2v 等

    try:
        new_generation = Generation(
            user_id=current_user_id,
            prompt=data['prompt'],
            generation_type=gen_type,
            status='processing' # 初始状态
        )
        db.session.add(new_generation)
        db.session.commit()
        
        # 启动线程
        thread = threading.Thread(target=process_generation_task, args=(new_generation.id,))
        thread.start()

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
        print(f"Task create error: {e}")
        return api_response(code=500, message="服务器内部错误")

@generation_blueprint.route('/<string:taskId>', methods=['GET'])
@jwt_required()
def get_generation_status(taskId):
    """查询结果接口 (适配文档 #13)"""
    current_user_id = int(get_jwt_identity())
    generation = Generation.query.filter_by(uuid=taskId).first()
    
    if not generation:
        return api_response(code=404, message="任务不存在")
    if generation.user_id != current_user_id:
        return api_response(code=403, message="无权访问")
        
    return api_response(code=200, message="任务状态获取成功", data=generation.to_dict())