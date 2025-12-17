import json
from PySide6.QtCore import QTimer
from PySide6.QtNetwork import QNetworkReply, QNetworkRequest
import os
import mimetypes
from services.global_signals import global_signals
from services.session import session
from services.http_client import http_client
from services.config import app_config

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
    - str -> 文件路径，根据后缀判断是否应使用 multipart
    """

    if isinstance(data, dict):
        return "application/json"
    # 处理字符串类型
    if isinstance(data, str):
        # 不是文件 → 判断是否 JSON 可序列化
        if not os.path.isfile(data):
            if is_json_serializable(data):
                return "application/json"
            return None

        # 是文件 → 猜测 MIME
        mime_type, _ = mimetypes.guess_type(data)

        # 如果是图片，强制走 multipart 上传
        if mime_type and mime_type.startswith("image/"):
            # 需求：把 image/* 改成 multipart/form-data
            return "multipart/form-data"

        # 文件存在但不是图片
        print(f"警告: 文件不是已知图片类型 -> {data}")
        return "multipart/form-data"   # 或 None

    return None


def check_if_unauthorized(reply: QNetworkReply):
    """检查响应是否为未授权（HTTP 401或422）"""
    if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 401 or reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 422:
        return True
    return False

def async_request(sender,method, url, data, handle_response=None, timeout=3000):
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
                if sender.enable_ui:
                    sender.enable_ui()
            cleanup()

    def on_finished():
        nonlocal is_timeout
        if is_timeout:
            return

        timer.stop()
        if sender and hasattr(sender, "enable_ui"):
            sender.enable_ui()
            
        if app_config.is_debug():
            print("\n响应状态码:", reply.attribute(QNetworkRequest.HttpStatusCodeAttribute))
            print("响应url:", reply.url().toString())

            # 获取 Content-Type
            ctype = reply.header(QNetworkRequest.ContentTypeHeader)
            ctype_str = str(ctype) if ctype else ""

            # 仅文本/JSON/XML/HTML 才打印内容
            text_like = (
                "text/" in ctype_str.lower()
                or "json" in ctype_str.lower()
                or "xml" in ctype_str.lower()
                or "html" in ctype_str.lower()
            )

            if text_like:
                body = reply.peek(reply.bytesAvailable()).data().decode(errors="replace")
                print("响应内容:", body)
            else:
                print(f"响应内容未显示（Content-Type: {ctype_str}）")

            print("\n--- 请求结束 ---\n")


        if check_if_unauthorized(reply):
            session.clear_session()
            global_signals.unauthorized.emit()
            cleanup()
            return
        
        if reply.error() != QNetworkReply.NoError:
            if sender:
                sender.show_error(f"网络错误: {reply.errorString()}")
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