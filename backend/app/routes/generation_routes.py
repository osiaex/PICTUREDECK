# app/routes/generation_routes.py

import os
from flask import Blueprint, request, url_for, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Generation
from .. import db
import threading
from ..utils.helpers import api_response
# 确保引用了最新的服务函数
from ..services.ai_service import generate_image_with_jimeng, generate_video_with_jimeng

generation_blueprint = Blueprint('generation', __name__)

def find_file_path_by_id(file_id):
    """根据 file_id (如 ref_1234) 在输出目录找到真实文件路径"""
    if not file_id: return None
    output_dir = current_app.config['OUTPUTS_DIR']
    
    if os.path.exists(output_dir):
        for fname in os.listdir(output_dir):
            if fname.startswith(file_id):
                return os.path.join(output_dir, fname)
    return None

def process_generation_task(generation_id, ref_image_id=None):
    """
    后台任务：执行生成
    """
    from app import create_app
    app = create_app()
    with app.app_context():
        generation = Generation.query.get(generation_id)
        if not generation: return

        prompt = generation.prompt
        gen_type = generation.generation_type
        
        # 1. 解析参考图路径
        ref_image_path = find_file_path_by_id(ref_image_id)
        if ref_image_path:
            print(f"任务 {generation_id} 使用参考图: {ref_image_path}")
        
        ext = 'mp4' if gen_type in ['t2v', 'i2v'] else 'jpg'
        output_filename = f"{generation.uuid}.{ext}"
        
        print(f"开始处理任务 {generation_id} [{gen_type}]: {prompt}")

        saved_path = None
        
        # ⭐️⭐️⭐️ 核心修改在这里：把 i2i 和 i2v 加入判断逻辑 ⭐️⭐️⭐️
        if gen_type in ['t2i', 'i2i']:
            # 文生图 和 图生图 都走这里
            saved_path = generate_image_with_jimeng(prompt, output_filename, ref_image_path)
            
        elif gen_type in ['t2v', 'i2v']:
            # 文生视频 和 图生视频 都走这里
            saved_path = generate_video_with_jimeng(prompt, output_filename, ref_image_path)
            
        else:
            # 你的报错就是因为代码走到了这里
            print(f"未实现的生成类型: {gen_type}")

        # --- 后续状态更新 ---
        current_params = generation.parameters or {}
        
        if saved_path:
            generation.status = 'completed'
            generation.result_url = url_for('static_files.get_output_file', filename=output_filename, _external=True)
            generation.physical_path = saved_path
            msg = "Success"
        else:
            generation.status = 'failed'
            msg = "Failed"
            
        current_params['review'] = {
            "status": "approved" if saved_path else "rejected",
            "message": msg
        }
        generation.parameters = current_params
        generation.completed_at = db.func.current_timestamp()
        db.session.commit()
        print(f"任务 {generation_id} 结束，状态: {generation.status}")


@generation_blueprint.route('', methods=['POST'])
@jwt_required()
def create_generation_task():
    """发起任务接口"""
    current_user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data or 'prompt' not in data or 'type' not in data:
        return api_response(code=400, message="请求参数不完整")
    
    gen_type = data['type']
    
    # 获取前端传来的 image (file_id)
    ref_image_id = data.get('image')

    try:
        new_generation = Generation(
            user_id=current_user_id,
            prompt=data['prompt'],
            generation_type=gen_type,
            status='processing',
            parameters={"ref_image": ref_image_id} if ref_image_id else {}
        )
        db.session.add(new_generation)
        db.session.commit()
        
        # ⭐️ 启动线程时，传入 ref_image_id
        thread = threading.Thread(target=process_generation_task, args=(new_generation.id, ref_image_id))
        thread.start()

        response_data = {
            "task_id": new_generation.uuid,
            "created_at": new_generation.created_at.isoformat() + "Z",
            "type": new_generation.generation_type,
            "prompt": new_generation.prompt,
            "image": ref_image_id 
        }
        return api_response(code=200, message="生成任务已创建", data=response_data)
    except Exception as e:
        db.session.rollback()
        print(f"Task create error: {e}")
        return api_response(code=500, message="服务器内部错误")

@generation_blueprint.route('/<string:taskId>', methods=['GET'])
@jwt_required()
def get_generation_status(taskId):
    current_user_id = int(get_jwt_identity())
    generation = Generation.query.filter_by(uuid=taskId).first()
    
    if not generation:
        return api_response(code=404, message="任务不存在")
    if generation.user_id != current_user_id:
        return api_response(code=403, message="无权访问")
        
    return api_response(code=200, message="任务状态获取成功", data=generation.to_dict())