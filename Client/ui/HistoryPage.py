from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from PySide6.QtCore import Qt
from services.local_store import LocalDB, save_pixmap_from_url
from services.request_service import async_request
from services.session import session
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel
from enum import Enum

class GenerationType(Enum):
    T2I = "t2i"
    I2I = "i2i"
    T2V = "t2v"
    I2V = "i2v"

GEN_TYPE_DESC = {
    GenerationType.T2I: "文生图",
    GenerationType.I2I: "参考图生图",
    GenerationType.T2V: "文生视频",
    GenerationType.I2V: "关键帧生视频",
}

DESC_TO_GEN_TYPE = {v: k for k, v in GEN_TYPE_DESC.items()}
STR_TO_DESC = {t.value: desc for t, desc in GEN_TYPE_DESC.items()}


class RecordWidget(QWidget):
    """单条记录展示组件"""
    """
record: dict
    一条 AI 生成内容或收藏项的记录，JSON 格式如下：

    {
        "type": str,   # 生成类型，如 "文生图"、"文生视频"、"图生图" 等
        "prompt": str,            # 用户输入的提示词，用于生成内容
        "parameters": dict,       # 生成时使用的参数，可包含 size、model、seed 等
        "result_url": str         # 生成结果的图片或封面图的网络地址（HTTP/HTTPS）
    }

字段说明：
    - type：用于在 UI 中展示记录属于哪种生成任务。
    - prompt：记录主要描述文本，是最主要的内容展示来源。
    - parameters：存放所有附加参数，通常不直接展示，但可用于 debug 或详情页。
    - result_url：必须是有效 URL，界面将通过网络异步请求加载该图片。

示例：
    {
        "type": "t2i",
        "prompt": "一只站在月光下的狐狸",
        "parameters": {"size": "512x512", "model": "SDXL"},
        "result_url": "result/generated_image_001.png"
    }
"""
    url_record_map = {}  # 类变量，缓存 URL 到 RecordWidget 实例的映射
    def __init__(self, record):
        super().__init__()
        layout = QVBoxLayout()
        self.image_size = 250

        self.type=STR_TO_DESC.get(record.get("type", "未知类型"), "未知类型")
        self.prompt=record.get("prompt", "")
        self.parameters=record.get("parameters", {})
        self.result_url=record.get("result_url", "")
        self.local_path=None
        if self.result_url and not RecordWidget.url_record_map.get(self.result_url):
            RecordWidget.url_record_map[self.result_url] = self  # 缓存 URL 到实例的映射

        # 显示文字信息
        title_label = QLabel(f"{self.type}\n {self.prompt}")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        
        # 图片
        self.img_label = QLabel("图片加载中...")
        layout.addWidget(self.img_label)
        
        self.setLayout(layout)

    def serach_image_in_local(self, image_url):
        db = LocalDB.instance()
        record = db.get_record_by_url(image_url)
        if record:
            self.local_path = record.get("local_path")
            if self.local_path:
                pixmap = QPixmap(self.local_path)
                if not pixmap.isNull():
                    self.img_label.setPixmap(pixmap.scaledToWidth(self.image_size, Qt.TransformationMode.SmoothTransformation))
                    return True
        return False
    
    def request_image(self, image_url):
        self.result_url=image_url
        try:
            # 异步请求图片数据
            async_request(
                sender=self,
                method="GET",
                url=image_url,
                data=None,
                handle_response=self.__update_image
            )

        except Exception as e:
            self.img_label.setText("图片加载失败")

    def getpixmap(self):
        return self.img_label.pixmap()

    
    def get_record_dict(self):
        return {
            "type": DESC_TO_GEN_TYPE[self.type].value,
            "prompt": self.prompt,
            "parameters": self.parameters,
            "result_url": self.result_url
        }
    
    def __update_image(self, reply):
        img_data = reply.readAll()
        pixmap = QPixmap()
        success = pixmap.loadFromData(img_data)

        if pixmap.isNull():
            self.img_label.setText("图片加载失败（格式错误）")
            print("loadFromData success:", success)
            print("img_data size:\n", len(img_data))
            print(bytes(img_data[:20]).hex(" "))
            from PySide6.QtGui import QImageReader
            print(QImageReader.supportedImageFormats())

            with open("debug_image.bin", "wb") as f:
                f.write(img_data)
        else:
            self.img_label.setPixmap(pixmap.scaledToWidth(self.image_size, Qt.TransformationMode.SmoothTransformation))

            # 缓存 URL 到实例的映射
            RecordWidget.url_record_map[self.result_url] = self
            # 保存图片到本地
            self.local_path = save_pixmap_from_url(self.result_url, pixmap)
            # 存储到本地数据库
            db = LocalDB.instance()
            db.insert_record(
                username=session.get_user().get("account"),
                local_path=self.local_path,
                url=self.result_url,
                generation_type=self.type,
                prompt=self.prompt,
                parameters=self.parameters,
            )

class HistoryPage(QWidget):
    """
    可用于 QStackedWidget 的历史记录页面容器，
    内部垂直排列 RecordWidget，每条记录之间保持间距，
    内容溢出时显示滚动条。
    """
    def __init__(self, parent=None, spacing=10, margin=10):
        super().__init__(parent)

        # 主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)  # 主布局无边距

        # 滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.main_layout.addWidget(self.scroll_area)

        # 内容容器
        self.container = QWidget()
        self.scroll_area.setWidget(self.container)

        # 垂直布局
        self.layout = QVBoxLayout(self.container)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # 顶部对齐
        self.layout.setSpacing(spacing)                      # 控制 RecordWidget 间距
        self.layout.setContentsMargins(margin, margin, margin, margin)  # 内边距

    def addWidget(self, widget: QWidget):
        """
        向历史记录页添加一个 RecordWidget。
        """
        self.layout.insertWidget(0, widget)
