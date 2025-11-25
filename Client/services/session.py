import json
import os

class Session:
    FILE_PATH = "user_session.json"

    def __init__(self):
        self.data = {
            "token": None,
            "account": None,
            "email": None
        }
        self.load()

    # -------------------- 基础读写 --------------------

    def load(self):
        """从本地 JSON 读取数据，没有文件就使用默认值"""
        if not os.path.exists(self.FILE_PATH):
            return

        try:
            with open(self.FILE_PATH, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception:
            # 文件坏了就重置
            self.data = {"token": None, "account": None, "email": None}

    def save(self):
        """写入 JSON"""
        with open(self.FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    # -------------------- 封装API --------------------

    def set_session(self, token, account, email):
        self.data["token"] = token
        self.data["account"] = account
        self.data["email"] = email
        self.save()

    def clear_session(self):
        self.data = {"token": None, "account": None, "email": None}
        self.save()

    def is_logged_in(self):
        return bool(self.data.get("token"))

    def get_token(self):
        return self.data.get("token")

    def get_user(self):
        return {
            "account": self.data.get("account"),
            "email": self.data.get("email")
        }
    
    def update_user(self, user_info):
        self.data["account"] = user_info.get("account", self.data["account"])
        self.data["email"] = user_info.get("email", self.data["email"])
        self.save()


# （供整个应用使用的实例）
session = Session()
