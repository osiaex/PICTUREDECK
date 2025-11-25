import json
from PySide6.QtCore import QTimer
from PySide6.QtNetwork import QNetworkReply, QNetworkRequest
from services.session import session
from services.http_client import http_client
import os
import mimetypes
from services.global_signals import global_signals

def is_json_serializable(obj):
    """判断对象是否可被 JSON 序列化"""
    try:
        json.dumps(obj)
        return True
    except (TypeError, OverflowError):
        return False
    
def get_content_type(data):
    """
    根据 data 类型判断 Content-Type
    - dict -> application/json
    - str -> 文件路径，根据后缀返回 image/* MIME 类型
    - 否则返回 None
    """
    if is_json_serializable(data):
        return "application/json"

    elif isinstance(data, str):
        # 先确认是一个存在的文件
        if not os.path.isfile(data):
            print(f"警告: 文件不存在 -> {data}")
            return None
        
        # 根据文件后缀猜测 MIME 类型
        mime_type, _ = mimetypes.guess_type(data)
        
        if mime_type and mime_type.startswith("image/"):
            return mime_type
        
        # 如果文件存在但不是图片，可以选择返回默认 image/png 或 None
        print(f"警告: 文件不是已知图片类型 -> {data}")
        return None

    return None

def check_if_unauthorized(reply: QNetworkReply):
    """检查响应是否为未授权（HTTP 401）"""
    if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 401:
        return True
    return False

def async_request(sender,method, url, data, handle_response=None, timeout=3000):
    print(url)
    token = session.get_token()
    content_type = get_content_type(data)
    reply = http_client.request(method, url, content_type=content_type, data=data, token=token)
    timer = QTimer(sender)
    timer.setSingleShot(True)
    is_timeout = False

    def cleanup():
        timer.deleteLater()
        reply.deleteLater()

    def on_timeout():
        nonlocal is_timeout
        if reply.isRunning():
            is_timeout = True
            reply.abort()
            if sender:
                sender.show_error("请求超时")
            cleanup()

    def on_finished():
        nonlocal is_timeout
        if is_timeout:
            return

        timer.stop()
        if reply.error() != QNetworkReply.NoError:
            if sender:
                sender.show_error(f"网络错误: {reply.errorString()}")
            cleanup()
            return
        
        if check_if_unauthorized(reply):
            session.clear_session()
            global_signals.unauthorized.emit()
            cleanup()
            return
        
        # 业务处理部分交给外部回调
        if handle_response:
            try:
                handle_response(reply)
            except Exception as e:
                if sender:
                    sender.show_error(f"处理响应时发生错误: {str(e)}")
        cleanup()

    reply.finished.connect(on_finished)
    timer.timeout.connect(on_timeout)
    timer.start(timeout)