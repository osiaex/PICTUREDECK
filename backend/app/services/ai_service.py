# app/services/ai_service.py

import json
import requests
import os
import time
from flask import current_app
from volcengine.visual.VisualService import VisualService
import base64

# --- 1. 填坑用的伪造对象 ---
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

# --- 2. 解析响应函数 ---
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

# --- 4. 图片生成服务 (文生图 + 图生图) ---
def generate_image_with_jimeng(prompt, output_filename, ref_image_path=None):
    ak = current_app.config.get('VOLC_ACCESS_KEY_ID')
    sk = current_app.config.get('VOLC_SECRET_ACCESS_KEY')
    if not ak or not sk: return None, {"message": "AK/SK missing"}
    
    visual_service = VisualService()
    visual_service.set_ak(ak)
    visual_service.set_sk(sk)

    # ==========================================
    # 分支 A: 图生图 (i2i) - 使用 Jimeng 3.0 异步接口
    # ==========================================
    if ref_image_path:
        print(f">>> [Jimeng i2i v3.0] 启动异步图生图: {ref_image_path}")
        
        # 1. 初始化服务配置 (异步接口需要配置 Host 和 API Info)
        visual_service.service_info.host = 'visual.volcengineapi.com'
        visual_service.service_info.socket_timeout = 30
        visual_service.service_info.connection_timeout = 30
        
        if 'SubmitTask' not in visual_service.api_info:
            visual_service.api_info['SubmitTask'] = ApiInfoStruct('POST', '/', {'Action': 'CVSync2AsyncSubmitTask', 'Version': '2022-08-31'})
        if 'GetResult' not in visual_service.api_info:
            visual_service.api_info['GetResult'] = ApiInfoStruct('POST', '/', {'Action': 'CVSync2AsyncGetResult', 'Version': '2022-08-31'})

        # 2. 准备参数
        base64_str = encode_image_to_base64(ref_image_path)
        if not base64_str:
            return None, {"message": "Failed to encode reference image"}

        req_key = "jimeng_i2i_v30"
        submit_body = {
            "req_key": req_key,
            "binary_data_base64": [base64_str], # 数组格式
            "prompt": prompt,
            "scale": 0.5,  # 0.5 是官方推荐值，数值越大越像 Prompt，越小越像原图
            "seed": -1
        }

        try:
            # 3. 提交任务
            print(f">>> [i2i] 提交任务...")
            raw_resp = visual_service.json('SubmitTask', {}, json.dumps(submit_body))
            resp = parse_sdk_response(raw_resp)

            if 'data' not in resp or 'task_id' not in resp['data']:
                print(f"❌ [i2i] 提交失败: {resp}")
                return None, resp

            task_id = resp['data']['task_id']
            print(f">>> [i2i] 任务ID: {task_id}，开始轮询...")

            # 4. 轮询结果
            last_resp = {}
            for i in range(60):
                time.sleep(2) 
                # 查询时必须带上 return_url: true
                query_body = {
                    "req_key": req_key,
                    "task_id": task_id,
                    "req_json": json.dumps({"return_url": True}) 
                }
                
                raw_get_resp = visual_service.json('GetResult', {}, json.dumps(query_body))
                get_resp = parse_sdk_response(raw_get_resp)
                last_resp = get_resp
                
                status = get_resp.get('data', {}).get('status')
                
                if status == 'done':
                    image_urls = get_resp['data'].get('image_urls', [])
                    if image_urls:
                        saved_path = download_file(image_urls[0], output_filename)
                        return saved_path, get_resp
                    else:
                        return None, {"message": "Status done but no image_urls", "raw": get_resp}
                
                elif status in ['failed', 'not_found', 'expired']:
                    return None, get_resp
                
                print(f"    ... [i2i] {status}")
            
            return None, {"message": "Timeout", "last_response": last_resp}

        except Exception as e:
            print(f"❌ [i2i Error] {e}")
            return None, {"message": str(e)}

    # ==========================================
    # 分支 B: 文生图 (t2i) - 保持 V2.1 同步接口
    # ==========================================
    else:
        print(f">>> [Jimeng t2i v2.1] 文生图模式")
        form_data = {
            "req_key": "jimeng_high_aes_general_v21_L", 
            "prompt": prompt, 
            "return_url": True
        }
        try:
            res = visual_service.cv_process(form_data)
            if 'data' not in res: return None, res 
            saved_path = download_file(res['data']['image_urls'][0], output_filename)
            return saved_path, res
        except Exception as e:
            return None, {"message": str(e), "code": -1}


# --- 5. 视频生成服务 (文生视频 + 图生视频) ---
def generate_video_with_jimeng(prompt, output_filename, ref_image_path=None):
    ak = current_app.config.get('VOLC_ACCESS_KEY_ID')
    sk = current_app.config.get('VOLC_SECRET_ACCESS_KEY')
    if not ak or not sk:
        print("❌ [Error] AK 或 SK 未配置！")
        return None, {"message": "AK/SK missing"}

    video_service = VisualService()
    video_service.set_ak(ak)
    video_service.set_sk(sk)
    video_service.service_info.host = 'visual.volcengineapi.com'
    video_service.service_info.socket_timeout = 30
    video_service.service_info.connection_timeout = 30
    
    # 防止重复添加
    if 'SubmitTask' not in video_service.api_info:
        video_service.api_info['SubmitTask'] = ApiInfoStruct('POST', '/', {'Action': 'CVSync2AsyncSubmitTask', 'Version': '2022-08-31'})
    if 'GetResult' not in video_service.api_info:
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
            submit_body["req_key"] = "jimeng_i2v_first_v30_1080"
            submit_body["binary_data_base64"] = [base64_str]
            # 移除 aspect_ratio 防止冲突
            if "aspect_ratio" in submit_body:
                del submit_body["aspect_ratio"]
        else:
            print(">>> [i2v] 参考图编码失败，降级为文生视频")

    try:
        print(f">>> [Video] 提交任务 (Key: {submit_body['req_key']})...")
        raw_resp = video_service.json('SubmitTask', {}, json.dumps(submit_body))
        resp = parse_sdk_response(raw_resp)

        if 'data' not in resp or 'task_id' not in resp['data']:
            print(f"❌ [Error] 视频任务提交失败: {resp}")
            return None, resp

        task_id = resp['data']['task_id']
        print(f">>> [Video] 任务ID: {task_id}")

        last_resp = {}
        for i in range(60):
            time.sleep(5)
            query_body = {"req_key": submit_body["req_key"], "task_id": task_id}
            
            raw_get_resp = video_service.json('GetResult', {}, json.dumps(query_body))
            get_resp = parse_sdk_response(raw_get_resp)
            last_resp = get_resp 
            
            data = get_resp.get('data', {})
            status = data.get('status')
            
            if status == 'done':
                video_url = data.get('video_url')
                saved_path = download_file(video_url, output_filename)
                return saved_path, get_resp
            elif status in ['failed', 'not_found', 'expired']:
                print(f"❌ [Error] 视频生成失败: {status}")
                return None, get_resp
            print(f"    ... [{i+1}/60] {status}")

        return None, {"message": "Timeout polling video", "last_response": last_resp}
    except Exception as e:
        print(f"❌ [Error] generate_video 异常: {e}")
        return None, {"message": str(e), "code": -1}


# --- 6. 下载函数 ---
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