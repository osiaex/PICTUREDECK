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
    from app import create_app
    app = create_app()
    with app.app_context():
        generation = Generation.query.get(generation_id)
        if not generation: return

        prompt = generation.prompt
        gen_type = generation.generation_type
        ref_image_path = find_file_path_by_id(ref_image_id)
        
        ext = 'mp4' if gen_type in ['t2v', 'i2v'] else 'jpg'
        output_filename = f"{generation.uuid}.{ext}"
        
        print(f"开始处理任务 {generation_id} [{gen_type}]")

        saved_path = None
        api_response_data = {} # 新增：用于存 API 原始返回

        try:
            # ⭐️ 核心修改：接收两个返回值 (路径, 原始JSON)
            if gen_type in ['t2i', 'i2i']:
                saved_path, api_response_data = generate_image_with_jimeng(prompt, output_filename, ref_image_path)
            elif gen_type in ['t2v', 'i2v']:
                saved_path, api_response_data = generate_video_with_jimeng(prompt, output_filename, ref_image_path)
            else:
                api_response_data = {"message": f"Unknown type {gen_type}"}

        except Exception as e:
            print(f"Task Error: {e}")
            api_response_data = {"message": str(e)}

        # --- 解析 Review 信息 (完全匹配前端给你的 JSON 结构) ---
        
        # 1. 提取 Code (10000 是成功)
        code = api_response_data.get('code', -1)
        
        # 2. 提取 Message
        # 优先看 data.algorithm_base_resp.status_message (算法层的详细信息)
        # 其次看外层的 message
        msg = api_response_data.get('message', 'Unknown Error')
        if 'data' in api_response_data and isinstance(api_response_data['data'], dict):
            algo_resp = api_response_data['data'].get('algorithm_base_resp')
            if algo_resp and 'status_message' in algo_resp:
                msg = algo_resp['status_message']

        # 3. 决定 Status
        # 只有当路径存在 且 API code 为 10000 时，才算 approved
        if saved_path and code == 10000:
            review_status = "approved"
            final_status = 'completed'
            generation.result_url = url_for('static_files.get_output_file', filename=output_filename, _external=True)
            generation.physical_path = saved_path
        else:
            review_status = "rejected"
            final_status = 'failed'
            # 如果失败了，尽量让 msg 更有意义
            if msg == "Success": msg = "Generation failed despite API success code"

        # --- 更新数据库 ---
        generation.status = final_status
        current_params = generation.parameters or {}
        
        # 构造前端想要的 review 对象
        current_params['review'] = {
            "status": review_status,
            "message": msg,
            "api_code": code  # 把 code 也存进去，方便前端调试
        }
        
        # 可选：如果 API 返回了优化的 Prompt，也可以存下来
        if 'data' in api_response_data and isinstance(api_response_data['data'], dict):
             llm_result = api_response_data['data'].get('llm_result')
             if llm_result:
                 current_params['optimized_prompt'] = llm_result

        generation.parameters = current_params
        generation.completed_at = db.func.current_timestamp()
        db.session.commit()
        
        print(f"任务结束: {final_status}, Review: {review_status}, Msg: {msg}")


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