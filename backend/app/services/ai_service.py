# app/services/ai_service.py

import json
import requests
import os
import time
from flask import current_app
from volcengine.visual.VisualService import VisualService

# --- 1. 填坑用的伪造对象 (保持不变，用于解决 AttributeError) ---
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

# --- 2. 强力解析函数 (新增，解决 TypeError) ---
def parse_sdk_response(resp):
    """
    不管 SDK 返回什么鬼东西 (字典、JSON字符串、字节流)，都强行转成字典
    """
    if resp is None:
        return {}
    
    # 如果已经是字典，直接返回
    if isinstance(resp, dict):
        return resp
    
    # 如果是字节流，解码成字符串
    if isinstance(resp, bytes):
        try:
            resp = resp.decode('utf-8')
        except:
            print(f"[SDK Parse] 无法解码字节流: {resp}")
            return {}

    # 如果是字符串，尝试转换 JSON
    if isinstance(resp, str):
        try:
            return json.loads(resp)
        except:
            print(f"[SDK Parse] 响应不是有效的 JSON: {resp}")
            return {}
            
    return {}

# --- 文生图服务 (保持不变) ---
def generate_image_with_jimeng(prompt, output_filename):
    ak = current_app.config.get('VOLC_ACCESS_KEY_ID')
    sk = current_app.config.get('VOLC_SECRET_ACCESS_KEY')
    if not ak or not sk: return None
    visual_service = VisualService()
    visual_service.set_ak(ak)
    visual_service.set_sk(sk)
    form_data = {"req_key": "jimeng_high_aes_general_v21_L", "prompt": prompt, "return_url": True}
    try:
        res = visual_service.cv_process(form_data)
        if 'data' not in res: return None
        return download_file(res['data']['image_urls'][0], output_filename)
    except: return None

# --- 核心逻辑: 视频生成 ---

def generate_video_with_jimeng(prompt, output_filename):
    """
    ⭐️ 文生视频：终极容错版
    """
    ak = current_app.config.get('VOLC_ACCESS_KEY_ID')
    sk = current_app.config.get('VOLC_SECRET_ACCESS_KEY')
    if not ak or not sk:
        print("[Video] 缺少 AK/SK 配置")
        return None

    # 1. 初始化
    video_service = VisualService()
    video_service.set_ak(ak)
    video_service.set_sk(sk)

    # 2. 修改配置
    video_service.service_info.host = 'visual.volcengineapi.com'
    video_service.service_info.socket_timeout = 30
    video_service.service_info.connection_timeout = 30

    # 3. 注册 API (骗过 SDK)
    video_service.api_info['SubmitTask'] = ApiInfoStruct(
        method='POST', path='/', 
        query={'Action': 'CVSync2AsyncSubmitTask', 'Version': '2022-08-31'}
    )
    video_service.api_info['GetResult'] = ApiInfoStruct(
        method='POST', path='/', 
        query={'Action': 'CVSync2AsyncGetResult', 'Version': '2022-08-31'}
    )

    # 4. 准备参数 (使用文档要求的 key)
    submit_body = {
        "req_key": "jimeng_t2v_v30_1080p", 
        "prompt": prompt,
        "frames": 121, 
        "aspect_ratio": "16:9"
    }

    try:
        print(f">>> [Video] 提交任务...")
        
        # 5. 发送请求
        raw_resp = video_service.json('SubmitTask', {}, json.dumps(submit_body))
        
        # ⭐️⭐️⭐️ 强力解析 (防止 string indices 报错) ⭐️⭐️⭐️
        resp = parse_sdk_response(raw_resp)
        
        # 打印出来看看，死也要死得明白
        # print(f"[Debug] Submit Resp: {resp}")

        # 错误检查
        if 'ResponseMetadata' in resp and 'Error' in resp['ResponseMetadata']:
            err = resp['ResponseMetadata']['Error']
            print(f"[Video] API报错: Code={err.get('Code')}, Message={err.get('Message')}")
            return None

        if 'data' not in resp or 'task_id' not in resp['data']:
            print(f"[Video] 响应异常或解析失败: {resp}")
            return None

        task_id = resp['data']['task_id']
        print(f">>> [Video] 任务已提交，TaskID: {task_id}")

        # 6. 轮询结果
        max_retries = 60
        for i in range(max_retries):
            time.sleep(5)
            
            query_body = {"req_key": "jimeng_t2v_v30_1080p", "task_id": task_id}
            
            raw_get_resp = video_service.json('GetResult', {}, json.dumps(query_body))
            
            # ⭐️⭐️⭐️ 强力解析 ⭐️⭐️⭐️
            get_resp = parse_sdk_response(raw_get_resp)
            
            data = get_resp.get('data', {})
            status = data.get('status')
            
            if status == 'done':
                video_url = data.get('video_url')
                if video_url:
                    print(f">>> [Video] 生成成功！URL: {video_url}")
                    return download_file(video_url, output_filename)
                else:
                    print(f"[Video] 完成但无URL: {get_resp}")
                    return None
            
            elif status in ['failed', 'not_found', 'expired']:
                print(f"[Video] 失败状态: {status}")
                return None
            
            print(f"    ... [{i+1}/{max_retries}] 状态: {status}")

        print("[Video] 超时")
        return None

    except Exception as e:
        # 打印详细堆栈，防止不明不白的错误
        import traceback
        traceback.print_exc()
        return None

def download_file(url, filename):
    """通用下载"""
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