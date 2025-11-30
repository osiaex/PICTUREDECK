import json
import os
import random
from PySide6.QtCore import QObject, Signal, QTimer, QByteArray
from PySide6.QtNetwork import QNetworkReply, QNetworkRequest


class MockReply(QObject):
    """
    模拟 QNetworkReply
    """
    finished = Signal()
    errorOccurred = Signal(int)

    def __init__(self, payload, delay=50, parent=None):
        super().__init__(parent)
        if isinstance(payload, dict):
            self._data = QByteArray(json.dumps(payload).encode("utf-8"))
        else:
            self._data = QByteArray(payload)
        self._aborted = False
        self.delay = delay

        QTimer.singleShot(self.delay, self._emit_signals)

    def _emit_signals(self):
        if self._aborted:
            self.errorOccurred.emit(QNetworkReply.NetworkError.OperationCanceledError)
        self.finished.emit()

    # 模拟 QNetworkReply 方法
    def readAll(self):
        return self._data

    def abort(self):
        self._aborted = True
        self.errorOccurred.emit(QNetworkReply.NetworkError.OperationCanceledError)
        self.finished.emit()

    def error(self):
        return QNetworkReply.NoError

    def isRunning(self):
        return not self._aborted

    def attribute(self, key):
        if key == QNetworkRequest.HttpStatusCodeAttribute:
            return 200
        return None


def match_dynamic(mock_key: str, endpoint_url: str):
    mock_fields = mock_key.split("/")
    url_fields = endpoint_url.split("/")

    # 字段数量必须一致
    if len(mock_fields) != len(url_fields):
        return False

    # 最后一项必须是动态字段，例如 `{id}`
    if not ("{" in mock_fields[-1] and "}" in mock_fields[-1]):
        return False

    # 比较除最后一个字段以外的所有字段
    for mk, uf in zip(mock_fields[:-1], url_fields[:-1]):
        if mk == "":      # 空字段不比较
            continue
        if mk != uf:
            return False

    return True

class MockReplyManager:
    """
    管理模拟 API 数据，提供生成 MockReply 的接口
    """
    def __init__(self, json_file="mock_data.json"):
        self.json_file = json_file
        self.mock_data = {}
        self.load_json(json_file)

    # -----------------------------
    # JSON 文件操作
    # -----------------------------
    def load_json(self, file_path=None):
        file_path = file_path or self.json_file
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.mock_data = json.load(f)
            # 将字符串形式的 lambda 转为 callable
            for key, responses in self.mock_data.items():
                for i, r in enumerate(responses):
                    if isinstance(r, str) and r.strip().startswith("lambda"):
                        self.mock_data[key][i] = eval(r)
        except FileNotFoundError:
            self.mock_data = {}

    def save_json(self, file_path=None):
        file_path = file_path or self.json_file
        # 保存前将 lambda 转为字符串
        data_to_save = {}
        for key, responses in self.mock_data.items():
            serialized = []
            for r in responses:
                if callable(r):
                    serialized.append(r.__code__.co_code)  # 可自定义序列化
                else:
                    serialized.append(r)
            data_to_save[key] = serialized
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)

    # -----------------------------
    # 动态管理 API
    # -----------------------------
    def add_mock(self, endpoint, response):
        """
        新增模拟接口或响应
        :param endpoint: API 路径，如 "/auth/login" 或 "user/{uid}"
        :param response: dict 或 lambda
        """
        if endpoint not in self.mock_data:
            self.mock_data[endpoint] = []
        self.mock_data[endpoint].append(response)

    # -----------------------------
    # 获取 MockReply 实例
    # -----------------------------
    def get_reply(self, endpoint_url: str, method="POST", delay=50) -> MockReply:
        payload = self._mock_response(endpoint_url, method=method)
        return MockReply(payload, delay=delay)

    def _mock_response(self, endpoint_url: str, method="POST"):

        if endpoint_url.startswith("/generated_outputs/") and method=="GET": 
            return self._load_image_payload(endpoint_url)
        
        if endpoint_url.startswith("/user/generation_list") and method=="POST":
            return {
                "code": 200,
                "message": "成功删除生成记录",
                "data": {
                    "result_url": "/generated_outputs/67890.txt"
                }
            }
        
        # 精确匹配
        if endpoint_url in self.mock_data:
            if endpoint_url == "/user/favorite_list" and method.upper() == "POST":
                import time
                import hashlib

                INT64_MAX = 2**63 - 1

                def gen_id():
                    now = str(time.time()).encode("utf-8")
                    digest = hashlib.md5(now).digest()
                    num = int.from_bytes(digest[:8], byteorder="big", signed=False)
                    return num & INT64_MAX        # 强制截成 int64 正数


                return {
                    "code": 200,
                    "message": "成功创建新收藏内容",
                    "data": {
                        "id": gen_id()
                    }
                }
            response = random.choice(self.mock_data[endpoint_url])
            return response() if callable(response) else response

        # 动态参数匹配，例如 user/{uid}
        for key, responses in self.mock_data.items():
            if match_dynamic(key, endpoint_url):
                uid = endpoint_url.split("/")[-1]
                response = random.choice(responses)
                return response(uid) if callable(response) else response

        print(f"警告: 未找到模拟接口数据 -> {endpoint_url}")
        return {"error": f"未模拟接口: {endpoint_url}"}
    
    def _load_image_payload(self, endpoint):
        filename = endpoint.split("/")[-1]
        path = os.path.join("mock_results", filename)

        if not os.path.exists(path):
            return {"error": f"未找到模拟图片: {path}"}

        try:
            with open(path, "rb") as f:
                data = f.read()
            return data  # 注意：返回的是二进制，不是 dict
        except Exception as e:
            return {"error": str(e)}
    
# 全局 MockReplyManager 实例
mock_reply_manager = MockReplyManager()
