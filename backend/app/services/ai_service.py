# app/services/ai_service.py

import requests
from flask import current_app
import base64
import os

def generate_image_with_stability(prompt, output_filename):
    """
    调用 Stability AI (SD3) API 生成图片并保存。
    
    :param prompt: 文本提示词
    :param output_filename: 不带路径的文件名, e.g., 'some_uuid.png'
    :return: 成功时返回保存的完整物理路径，失败时返回 None
    """
    api_key = current_app.config['STABILITY_API_KEY']
    api_host = 'https://api.stability.ai'
    engine_id = "stable-diffusion-3" # 使用 SD3 模型

    if not api_key:
        print("错误：未配置 Stability AI API Key。")
        return None

    response = requests.post(
        f"{api_host}/v1/generation/{engine_id}/text-to-image",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        json={
            "text_prompts": [
                {
                    "text": prompt
                }
            ],
            "cfg_scale": 7,
            "height": 1024,
            "width": 1024,
            "samples": 1,
            "steps": 30,
        },
    )

    if response.status_code != 200:
        print(f"Stability AI API 请求失败: {response.text}")
        return None

    data = response.json()

    # 确保保存图片的目录存在
    output_dir = current_app.config['OUTPUTS_DIR']
    os.makedirs(output_dir, exist_ok=True)
    
    # 拼接完整的保存路径
    output_path = os.path.join(output_dir, output_filename)

    # API 返回的是 base64 编码的图片数据
    for i, image in enumerate(data["artifacts"]):
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(image["base64"]))
        # 我们只生成一张图，所以直接返回
        print(f"图片成功保存到: {output_path}")
        return output_path

    return None