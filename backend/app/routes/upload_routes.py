# app/routes/upload_routes.py

import os
import uuid
from flask import Blueprint, request, current_app, url_for
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename
from ..utils.helpers import api_response

upload_blueprint = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

def allowed_file(filename):
    """检查文件扩展名是否合法"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_blueprint.route('', methods=['POST'])
@jwt_required()
def upload_image():
    """
    接口 12: 上传参考图片
    URI: /api/v1/upload (由 __init__.py 的 prefix 决定)
    """
    # 1. 检查请求中是否有文件
    if 'file' not in request.files:
        return api_response(code=400, message="请求中未包含文件(key应为'file')")
    
    file = request.files['file']
    
    # 2. 检查文件名是否为空
    if file.filename == '':
        return api_response(code=400, message="未选择文件")

    # 3. 检查格式并保存
    if file and allowed_file(file.filename):
        # 获取文件后缀
        ext = file.filename.rsplit('.', 1)[1].lower()
        
        # 生成唯一的 file_id，例如: ref_a1b2c3d4
        # 使用 UUID 防止文件名冲突
        random_id = uuid.uuid4().hex[:8]
        file_id = f"ref_{random_id}"
        new_filename = f"{file_id}.{ext}"
        
        # 获取保存目录 (复用 config.py 里的 OUTPUTS_DIR)
        save_dir = current_app.config['OUTPUTS_DIR']
        
        # 确保目录存在
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        # 保存文件
        save_path = os.path.join(save_dir, new_filename)
        try:
            file.save(save_path)
        except Exception as e:
            print(f"File save error: {e}")
            return api_response(code=500, message="文件保存失败")

        # 生成可访问的 URL
        # 这里的 'static_files.get_output_file' 对应你 static_routes.py 里的函数名
        # _external=True 会生成完整的 http://... 链接
        file_url = url_for('static_files.get_output_file', filename=new_filename, _external=True)

        return api_response(code=200, message="上传成功", data={
            "file_id": file_id,
            "file_url": file_url
        })
    else:
        return api_response(code=400, message="不支持的文件格式(仅支持图片)")