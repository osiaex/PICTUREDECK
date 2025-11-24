# app/services/ai_service.py

import json
import requests
import os
from flask import current_app
from volcengine.visual.VisualService import VisualService

def generate_image_with_jimeng(prompt, output_filename):
    """
    调用即梦 AI API 生成图片，并从返回的URL下载保存。
    """
    ak = current_app.config['VOLC_ACCESS_KEY_ID']
    sk = current_app.config['VOLC_SECRET_ACCESS_KEY']
    
    if not ak or not sk:
        print("错误：未配置火山引擎的 Access Key。")
        return None

    # 1. 初始化 VisualService
    visual_service = VisualService()
    visual_service.set_ak(ak)
    visual_service.set_sk(sk)
    
    # 2. 准备 Body 参数
    form_data = {
        "req_key": "jimeng_high_aes_general_v21_L",
        "prompt": prompt,
        "return_url": True,
    }

    try:
        print(">>> 准备向即梦AI发送请求 (使用 cv_process)...")
        
        # 3. 使用官方推荐的 cv_process 方法
        res_json = visual_service.cv_process(form_data)
        
        print("<<< 已收到即梦AI的响应！")
        print("原始响应内容:", res_json)

        # 检查业务错误码 (SDK 可能在失败时直接抛异常，也可能返回错误信息)
        # 我们先检查 ResponseMetadata，这是 SDK 的标准错误结构
        if 'ResponseMetadata' in res_json and 'Error' in res_json['ResponseMetadata']:
            error_info = res_json['ResponseMetadata']['Error']
            # 火山引擎的业务错误码在 CodeN 字段
            print(f"即梦 AI API 业务错误: Code: {error_info.get('CodeN')}, Message: {error_info.get('Message')}")
            return None

        # 如果没有 SDK 错误，再检查业务数据里的 image_urls
        image_urls = res_json.get("data", {}).get("image_urls", [])
        if not image_urls:
            print("即梦 AI API 成功，但未返回图片URL。")
            return None
            
        image_url = image_urls[0]
        print(f"获取到图片URL: {image_url}")
        
        # --- 后续的下载和保存逻辑完全不变 ---
        print(">>> 开始下载图片...")
        image_response = requests.get(image_url, stream=True, timeout=30)
        image_response.raise_for_status() 
        
        output_dir = current_app.config['OUTPUTS_DIR']
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'wb') as f:
            for chunk in image_response.iter_content(1024):
                f.write(chunk)
        
        print(f"<<< 图片成功保存到: {output_path}")
        return output_path

    except Exception as e:
        # SDK 的异常通常会包含更详细的信息
        print(f"[SDK或未知错误] 调用即梦 AI API 时发生异常: {e}")
        return None