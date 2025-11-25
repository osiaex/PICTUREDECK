import json
import os

class AppConfig:
    FILE_PATH = "config.json"

    DEFAULT_CONFIG = {
        "environment": "offline",     # offline / staging / production
        "debug": True,
        "api_base_urls": {
            "offline": "http://127.0.0.1:8000/api/v1",
            "staging": "https://127.0.0.1:5000/api/v1",
            "production": "https://prod-server.com/api/v1"
        }
    }

    def __init__(self):
        # 初始时加载配置
        self.data = {}
        self.load()

    def load(self):
        """从本地文件读取配置"""
        if not os.path.exists(self.FILE_PATH):
            self.data = self.DEFAULT_CONFIG.copy()
            self.save()
            return

        try:
            with open(self.FILE_PATH, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except:
            self.data = self.DEFAULT_CONFIG.copy()

    def save(self):
        with open(self.FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    # -------------------
    # 配置操作 API
    # -------------------

    def get_env(self):
        return self.data.get("environment")

    def set_env(self, env):
        assert env in ["offline", "staging", "production"]
        self.data["environment"] = env
        self.save()

    def get_base_url(self):
        env = self.get_env()
        return self.data["api_base_urls"][env]

    def is_debug(self):
        return self.data.get("debug", False)

    def set_debug(self, val: bool):
        self.data["debug"] = bool(val)
        self.save()


# 单例模式，全局唯一
app_config = AppConfig()
