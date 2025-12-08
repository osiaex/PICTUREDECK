# app/services/ai_service.py

import json
import requests
import os
import time
from flask import current_app
from volcengine.visual.VisualService import VisualService
import base64

# --- 1. 填坑用的伪造对象 (保持不变) ---
class ApiInfoStruct:
    def __init__(self, method, path, query, header=None):
        self.method = method
        self.path = path
        self.url = path
        self.query = query
        self.header = header or {}
        self.body_format = 'json' 
        self.socket_timeout = 30
        self.connection_timeout = 30

# --- 2. 强力解析函数 (保持不变) ---
def parse_sdk_response(resp):
    if resp is None: return {}
    if isinstance(resp, dict): return resp
    if isinstance(resp, bytes):
        try: resp = resp.decode('utf-8')
        except: return {}
    if isinstance(resp, str):
        try: return json.loads(resp)
        except: return {}
    return {}

# --- 3. 辅助函数：图片转Base64 ---
def encode_image_to_base64(file_path):
    if not file_path or not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"[Base64] 编码失败: {e}")
        return None

# --- 4. 文生图 / 图生图服务 (已修复参数缺失问题) ---
# ⚠️ 修复点：添加了 ref_image_path=None 参数
def generate_image_with_jimeng(prompt, output_filename, ref_image_path=None):
    ak = current_app.config.get('VOLC_ACCESS_KEY_ID')
    sk = current_app.config.get('VOLC_SECRET_ACCESS_KEY')
    if not ak or not sk: return None
    
    visual_service = VisualService()
    visual_service.set_ak(ak)
    visual_service.set_sk(sk)
    
    form_data = {"req_key": "jimeng_high_aes_general_v21_L", "prompt": prompt, "return_url": True}
    
    # 逻辑：如果有参考图，处理 i2i 逻辑
    if ref_image_path:
        print(f">>> [i2i] 正在处理参考图: {ref_image_path}")
        base64_str = encode_image_to_base64(ref_image_path)
        if base64_str:
            form_data["init_image"] = base64_str
            form_data["strength"] = 0.6 
        else:
            print(">>> [i2i] 参考图编码失败，将降级为文生图")

    try:
        res = visual_service.cv_process(form_data)
        if 'data' not in res: return None
        return download_file(res['data']['image_urls'][0], output_filename)
    except Exception as e:
        print(f"Image Gen Error: {e}")
        return None

# --- 5. 文生视频 / 图生视频服务 (已修复参数缺失 + req_key一致性问题) ---
# ⚠️ 修复点：添加了 ref_image_path=None 参数
def generate_video_with_jimeng(prompt, output_filename, ref_image_path=None):
    ak = current_app.config.get('VOLC_ACCESS_KEY_ID')
    sk = current_app.config.get('VOLC_SECRET_ACCESS_KEY')
    if not ak or not sk:
        print("❌ [Error] AK 或 SK 未配置！")
        return None

    video_service = VisualService()
    video_service.set_ak(ak)
    video_service.set_sk(sk)
    video_service.service_info.host = 'visual.volcengineapi.com'
    video_service.service_info.socket_timeout = 30
    video_service.service_info.connection_timeout = 30
    video_service.api_info['SubmitTask'] = ApiInfoStruct('POST', '/', {'Action': 'CVSync2AsyncSubmitTask', 'Version': '2022-08-31'})
    video_service.api_info['GetResult'] = ApiInfoStruct('POST', '/', {'Action': 'CVSync2AsyncGetResult', 'Version': '2022-08-31'})

    # 1. 默认参数 (文生视频)
    submit_body = {
        "req_key": "jimeng_t2v_v30_1080p", 
        "prompt": prompt,
        "frames": 121, 
        "aspect_ratio": "16:9"
    }

    # 2. 如果有参考图 (图生视频)，切换 Key 和 参数
    if ref_image_path:
        print(f">>> [i2v] 正在处理参考图: {ref_image_path}")
        base64_str = encode_image_to_base64(ref_image_path)
        if base64_str:
            # ⭐️ 核心修正：使用文档指定的最新 Key
            submit_body["req_key"] = "jimeng_i2v_first_v30_1080"
            
            # ⭐️ 核心修正：使用 binary_data_base64 数组格式
            submit_body["binary_data_base64"] = [base64_str]
            
            # ⭐️ 核心修正：清理文生视频特有的参数 (避免参数冲突)
            # 根据文档，i2v 似乎不需要 aspect_ratio，我们这里为了安全保留 frames 和 prompt
            # 如果报错参数多余，可以尝试 del submit_body["aspect_ratio"]
        else:
            print(">>> [i2v] 参考图编码失败，降级为文生视频")

    try:
        print(f">>> [Video] 提交任务 (Key: {submit_body['req_key']})...")
        raw_resp = video_service.json('SubmitTask', {}, json.dumps(submit_body))
        resp = parse_sdk_response(raw_resp)

        if 'data' not in resp or 'task_id' not in resp['data']:
            print(f"❌ [Error] 视频任务提交失败: {resp}")
            return None

        task_id = resp['data']['task_id']
        print(f">>> [Video] 任务ID: {task_id}")

        for i in range(60):
            time.sleep(5)
            # ⭐️ 查询时使用相同的 req_key
            query_body = {"req_key": submit_body["req_key"], "task_id": task_id}
            
            raw_get_resp = video_service.json('GetResult', {}, json.dumps(query_body))
            get_resp = parse_sdk_response(raw_get_resp)
            
            data = get_resp.get('data', {})
            status = data.get('status')
            
            if status == 'done':
                video_url = data.get('video_url')
                return download_file(video_url, output_filename)
            elif status in ['failed', 'not_found', 'expired']:
                print(f"❌ [Error] 视频生成失败: {status}, Msg: {get_resp.get('message')}")
                return None
            print(f"    ... [{i+1}/60] {status}")

        return None
    except Exception as e:
        print(f"❌ [Error] generate_video 异常: {e}")
        return None

# --- 下载函数 (保持不变) ---
def download_file(url, filename):
    try:
        print(f">>> 下载文件: {url}")
        resp = requests.get(url, stream=True, timeout=120, verify=False)
        resp.raise_for_status()
        output_dir = current_app.config['OUTPUTS_DIR']
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)
        with open(output_path, 'wb') as f:
            for chunk in resp.iter_content(4096):
                f.write(chunk)
        print(f"<<< 已保存: {output_path}")
        return output_path
    except Exception as e:
        print(f"下载失败: {e}")
        return None