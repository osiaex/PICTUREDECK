import mimetypes
import os
from PySide6.QtCore import QIODevice, QObject, Signal, QTimer, QByteArray, QUrl, QFile,qDebug
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply, QHttpMultiPart, QHttpPart
import json
from services.config import app_config
from services.mock_reply import MockReply, mock_reply_manager

SPECIAL_PREFIXES = {
    "outputs"
}
class HttpClient(QObject):
    BASE_URL = app_config.get_base_url()
    """注释:
              ┌──────────────────────────────┐
              │      BASE_URL = 主地址        │
              │  https://api.xxx.com/api/v1  │
              └──────────────────────────────┘
                            │
                ┌───────────┴───────────┐
        正常接口 endpoint              静态资源 endpoint
        "user/login"                   "generated_outputs/1.png"
                │                               │
                ▼                               ▼
        正常加前缀（包括 /api/v1）      去掉 /api/v1（图片直链）
                │                               │
                ▼                               ▼
        https://api.xxx.com/api/v1/…     https://api.xxx.com/generated_outputs/…
    """
    
    def __init__(self):
        super().__init__()
        self.manager = QNetworkAccessManager()

    # ------------------------------
    # 发起 HTTP 请求
    # endpoint_url: 相对于 BASE_URL 的路径，如 "auth/login"，前导斜杠可有可无，不含主机名、api/v1等
    # 若content_type为None或空字符串，则不设置Content-Type头
    # 若content_type为"image/png"等，data应为文件路径字符串
    # 若content_type为"application/json"，data应为字典
    # ------------------------------
    def request(self, method, endpoint_url, content_type="application/json", data=None, token=None):

        remove_api = any(endpoint_url.lstrip('/').startswith(prefix) for prefix in SPECIAL_PREFIXES)

        if remove_api:
            final_url = f"{self.BASE_URL.rsplit('/api/v1', 1)[0]}/{endpoint_url.lstrip('/')}"
        else:
            final_url = f"{self.BASE_URL}/{endpoint_url.lstrip('/')}"
            
        url = QUrl(final_url)
        request = QNetworkRequest(url)

        if isinstance(content_type, str) and content_type.strip() and content_type.lower() != "multipart/form-data":
            request.setHeader(QNetworkRequest.ContentTypeHeader, content_type)

        if token:
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode())

        if app_config.is_debug():
            # 打印 QNetworkRequest 的信息
            print(f"[{app_config.get_env().capitalize()} Mode] Request info:")
            print("URL:", request.url().toString())
            print("Method:", method)
            # 打印 Header
            for header in request.rawHeaderList():
                print(f"{header.data().decode()}: {request.rawHeader(header.data().decode()).data().decode()}")
            # 打印 body（data）
            if data is not None and content_type == "application/json":
                print("Body:", json.dumps(data, ensure_ascii=False))
            print('\n')
        if app_config.get_env() == "offline":
            # 返回 MockReply
            return mock_reply_manager.get_reply(endpoint_url, method=method)

        # 根据 method 发起请求
        if method.upper() == "GET":
            reply = self.manager.get(request)
        elif method.upper() == "DELETE":
            reply = self.manager.deleteResource(request)
        else:
            if content_type.startswith("multipart/") and isinstance(data, str):
                # 使用multipart/form-data携带文件
                file_path = data
                multi_part = QHttpMultiPart(QHttpMultiPart.FormDataType)

                # 创建文件 form-data 部分
                file_part = QHttpPart()
                file_part.setHeader(QNetworkRequest.ContentDispositionHeader,
                                    f'form-data; name="file"; filename="{os.path.basename(file_path)}"')

                # 自动猜测 MIME 类型
                mime, _ = mimetypes.guess_type(file_path)
                if mime:
                    file_part.setHeader(QNetworkRequest.ContentTypeHeader, mime)
                else:
                    file_part.setHeader(QNetworkRequest.ContentTypeHeader, "application/octet-stream")

                file_device = QFile(file_path)
                file_device.open(QIODevice.ReadOnly)
                file_part.setBodyDevice(file_device)
                file_device.setParent(multi_part)  # 生命周期绑定

                multi_part.append(file_part)
                payload = multi_part
            elif content_type == "application/json":
                payload = QByteArray(json.dumps(data or {}).encode("utf-8"))
            else:
                payload = data
            if method.upper() == "POST":
                reply = self.manager.post(request, payload)
                if content_type.startswith("multipart/"):
                    # multipart 需要特殊处理
                    payload.setParent(reply)  # 生命周期绑定
                    file_device.setParent(multi_part)  # 生命周期绑定
            elif method.upper() == "PUT":
                reply = self.manager.put(request, payload)
            else:
                raise ValueError("Unsupported HTTP method")

        return reply

http_client = HttpClient()


