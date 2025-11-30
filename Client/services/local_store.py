from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtCore import QMutex, QMutexLocker
from PySide6.QtGui import QPixmap
import os
import re

def safe_filename_from_url(url: str) -> str:
    base = os.path.basename(url)
    name, ext = os.path.splitext(base)
    safe_name = re.sub(r'[^a-zA-Z0-9]+', '_', name).strip('_')

    if not safe_name:
        safe_name = "file"

    return safe_name + ext



def save_pixmap_from_url(url: str, pixmap: QPixmap, base_dir="local_result") -> str:
    """
    将 QPixmap 保存到 ./local_result 下（或指定路径）
    文件名根据 URL 生成安全格式并尽量保留扩展名
    返回最终保存的绝对路径
    """
    # 生成安全文件名
    filename = safe_filename_from_url(url)

    # 创建目录
    os.makedirs(base_dir, exist_ok=True)

    # 拼出完整路径
    full_path = os.path.join(base_dir, filename)

    # 保存 pixmap
    if not pixmap.save(full_path):
        raise RuntimeError(f"Failed to save pixmap to {full_path}")

    return full_path

class LocalDB:
    _instance = None
    _mutex = QMutex()

    @staticmethod
    def instance():
        """
        获取唯一数据库实例
        """
        with QMutexLocker(LocalDB._mutex):
            if LocalDB._instance is None:
                LocalDB._instance = LocalDB()
            return LocalDB._instance

    def __init__(self):
        """
        初始化数据库（只执行一次）
        """
        if hasattr(self, "_initialized"):
            return

        self.db = QSqlDatabase.addDatabase("QSQLITE")
        self.db.setDatabaseName("local_records.db")

        if not self.db.open():
            raise RuntimeError("Failed to open database")

        self._create_table()

        self._initialized = True

    def _create_table(self):
        """
        创建业务表结构
        """
        query = QSqlQuery(self.db)
        query.exec(
            """
            CREATE TABLE IF NOT EXISTS local_records(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                local_path TEXT NOT NULL,
                url TEXT UNIQUE,
                generation_type TEXT,
                prompt TEXT,
                parameters TEXT
            )
            """
        )

    # -------------------------------------------------------------
    # 业务方法（直接可用）
    # -------------------------------------------------------------

    def insert_record(self, username, local_path, url,
                      generation_type, prompt, parameters):
        """
        插入一条记录，URL 不重复（UNIQUE）时自动忽略
        """
        query = QSqlQuery(self.db)
        query.prepare(
            """
            INSERT OR IGNORE INTO local_records
            (username, local_path, url, generation_type, prompt, parameters)
            VALUES (?, ?, ?, ?, ?, ?)
            """
        )
        for v in (username, local_path, url,
                  generation_type, prompt, parameters):
            query.addBindValue(v)

        if not query.exec():
            print("Insert error:", query.lastError().text())

    def url_exists(self, url: str) -> bool:
        """
        判断 URL 是否存在
        """
        query = QSqlQuery(self.db)
        query.prepare(
            "SELECT 1 FROM local_records WHERE url = ? LIMIT 1"
        )
        query.addBindValue(url)
        query.exec()
        return query.next()

    def get_record_by_url(self, url: str):
        """
        根据 URL 获取整条记录，返回 dict 或 None
        """
        query = QSqlQuery(self.db)
        query.prepare(
            """
            SELECT id, username, local_path, url,
                   generation_type, prompt, parameters
            FROM local_records
            WHERE url = ? LIMIT 1
            """
        )
        query.addBindValue(url)
        query.exec()

        if query.next():
            return {
                "id": query.value(0),
                "username": query.value(1),
                "local_path": query.value(2),
                "url": query.value(3),
                "generation_type": query.value(4),
                "prompt": query.value(5),
                "parameters": query.value(6),
            }
        return None

    def get_value_by_url(self, url: str, field: str):
        """
        根据 URL 查找指定字段。例如：
            get_value_by_url(url, "local_path")
        """
        allowed = {
            "id", "username", "local_path",
            "url", "generation_type", "prompt",
            "parameters"
        }

        if field not in allowed:
            raise ValueError(f"Field not allowed: {field}")

        query = QSqlQuery(self.db)
        query.prepare(f"SELECT {field} FROM local_records WHERE url = ? LIMIT 1")
        query.addBindValue(url)
        query.exec()

        return query.value(0) if query.next() else None
    
    def delete_record_by_url(self, url: str):
        """
        根据 URL 删除对应记录
        """
        query = QSqlQuery(self.db)
        query.prepare("DELETE FROM local_records WHERE url = ?")
        query.addBindValue(url)
        if not query.exec():
            print("Delete error:", query.lastError().text())
