import json
import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QHBoxLayout, QLineEdit, QPushButton, QMenu, QMessageBox
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt, Signal
from services.local_store import LocalDB, save_pixmap_from_url
from services.request_service import async_request
from services.session import session
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel
from enum import Enum
from ui.RecordDialog import RecordDialog

class GenerationType(Enum):
    T2I = "t2i"
    I2I = "i2i"
    T2V = "t2v"
    I2V = "i2v"

GEN_TYPE_DESC = {
    GenerationType.T2I: "文生图",
    GenerationType.I2I: "参考图生图",
    GenerationType.T2V: "文生视频",
    GenerationType.I2V: "首帧生视频",
}

DESC_TO_GEN_TYPE = {v: k for k, v in GEN_TYPE_DESC.items()}
STR_TO_DESC = {t.value: desc for t, desc in GEN_TYPE_DESC.items()}


# todo 右键菜单删除历史记录，左键浏览详情
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
    def __init__(self, record, parent=None):
        super().__init__(parent)
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

    def show_error(self, message: str):
        QMessageBox.critical(self, "错误", message)

    def show_info(self, message: str):
        QMessageBox.information(self, "信息", message)

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
    
    def remove_record(self):
        db = LocalDB.instance()
        db.delete_record_by_url(self.result_url)
        if self.result_url in RecordWidget.url_record_map:
            del RecordWidget.url_record_map[self.result_url]
        if os.path.exists(self.local_path):
            os.remove(self.local_path)
            
    
    def request_image(self, image_url):
        self.result_url=image_url
        from urllib.parse import urlparse
        image_url = urlparse(image_url)
        try:
            # 异步请求图片数据
            async_request(
                sender=self,
                method="GET",
                url=image_url.path,
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
            "result_url": self.result_url,
            "local_path": self.local_path
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
    顶部带多标签搜索栏，可多关键词叠加过滤 RecordWidget。
    """
    record_deleted = Signal(dict)  # 当记录被删除时发出信号，传递被删除的记录字典
    add_record_to_fav = Signal(dict)  # 当记录被添加到收藏夹时发出信号，传递被添加的记录字典
    def __init__(self, parent=None, spacing=10, margin=10):
        super().__init__(parent)

        # 记录所有添加的 RecordWidgets
        self.all_records = []
        # 当前所有标签文本
        self.tags = []

        # 主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # ========== 搜索栏区域 ===========
        self.total_width = 0
        search_bar_container = QWidget()
        search_layout = QHBoxLayout(search_bar_container)
        search_layout.setContentsMargins(10, 10, 10, 10)
        search_layout.setSpacing(5)

        # --- 标签容器（多个 tag） ---
        self.tag_container = QWidget()
        self.tag_layout = QHBoxLayout(self.tag_container)
        self.tag_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_layout.setSpacing(4)
        self.tag_container.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)

        search_layout.addWidget(self.tag_container)

        # --- 输入框 ---
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("根据提示词过滤...")
        self.search_edit.returnPressed.connect(self.applySearch)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                border: none;
                padding: 4px 8px;
                font-size: 14px;
                background: transparent;
            }
        """)
        search_layout.addWidget(self.search_edit, 1)

        # --- 搜索按钮 ---
        self.search_btn = QPushButton()
        self.search_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
            }
        """)
        self.search_btn.setIcon(QIcon.fromTheme("system-search"))
        self.search_btn.setFixedSize(28, 28)
        self.search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_btn.clicked.connect(self.applySearch)
        search_layout.addWidget(self.search_btn)

        # 整体边框样式
        search_bar_container.setStyleSheet("""
            QWidget {
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 4px;
                background-color: white;
            }
        """)

        self.main_layout.addWidget(search_bar_container)

        # ========== 滚动区域 ===========
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.main_layout.addWidget(self.scroll_area)

        # 内容容器
        self.container = QWidget()
        self.scroll_area.setWidget(self.container)

        # 垂直布局
        self.layout = QVBoxLayout(self.container)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout.setSpacing(spacing)
        self.layout.setContentsMargins(margin, margin, margin, margin)



    # ===============================
    # 添加记录
    # ===============================
    def addWidget(self, widget: QWidget):
        self.layout.insertWidget(0, widget)
        self.all_records.append(widget)

    # ===============================
    # 搜索功能
    # ===============================
    def applySearch(self):
        keyword = self.search_edit.text().strip()
        if not keyword:
            self.search_edit.setFocus()
            return

        self.addTag(keyword)
        self.search_edit.clear()
        self.filterRecords()

    def filterRecords(self):
        """只有 RecordWidget.prompt 同时包含所有 tag 才显示"""
        for record in self.all_records:
            text = getattr(record, "prompt", "").lower()
            visible = all(t.lower() in text for t in self.tags)
            record.setVisible(visible)

    # ===============================
    # 标签（tag/chip） 功能
    # ===============================
    def addTag(self, keyword: str):
        if keyword in self.tags:
            return

        self.tags.append(keyword)

        tag_label = QLabel(f"{keyword}   ×")
        tag_label.setStyleSheet("""
            QLabel {
                border: none;
                background-color: #e0e0e0;
                border-radius: 8px;
                padding: 3px 6px;
                font-size: 12px;
            }
        """)
        # 点击删除
        tag_label.mousePressEvent = lambda e, t=keyword, w=tag_label: self.removeTag(t, w)

        self.tag_layout.addWidget(tag_label)

        self.adjustTagWidths()

    def removeTag(self, keyword, widget):
        if keyword in self.tags:
            self.tags.remove(keyword)

        widget.setParent(None)
        widget.deleteLater()

        self.adjustTagWidths()
        self.filterRecords()

    # ===============================
    # 标签压缩逻辑（最多占 70% 宽度）
    # ===============================
    def adjustTagWidths(self):
        if self.total_width == 0:
            self.total_width = self.search_edit.size().width()

        max_width = self.total_width * 0.7

        # 所有标签
        widgets = [self.tag_layout.itemAt(i).widget() for i in range(self.tag_layout.count())]
        widths = [w.sizeHint().width() for w in widgets]
        total = sum(widths)

        if total <= max_width:
            # 恢复原始宽度
            for w in widgets:
                w.setMaximumWidth(16777215)
            return

        # 等比例压缩
        ratio = max_width / total
        for i, w in enumerate(widgets):
            new_w = int(widths[i] * ratio)
            w.setMaximumWidth(new_w)
            w.setToolTip(self.tags[i])  # 悬停显示完整文本

    def mousePressEvent(self, event):
        # 获取点击位置相对于内容容器的位置
        content_pos = self.container.mapFrom(self, event.position().toPoint())

        # 找到被点击的 child
        clicked = self.container.childAt(content_pos)

        while clicked and not isinstance(clicked, RecordWidget):
            clicked = clicked.parent()

        # 不是 RecordWidget → 直接返回
        if not isinstance(clicked, RecordWidget):
            return super().mousePressEvent(event)

        if event.button() == Qt.MouseButton.LeftButton:
            self.openRecordDetail(clicked)

        elif event.button() == Qt.MouseButton.RightButton:
            self.openContextMenu(clicked, event.globalPos())

        return super().mousePressEvent(event)

    # 左键 → 打开详情
    def openRecordDetail(self, record_widget: "RecordWidget"):
        dlg = RecordDialog(record_widget.get_record_dict(), self)
        dlg.show()

    # 右键 → 弹出菜单
    def openContextMenu(self, record_widget: "RecordWidget", global_pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #f9f9f9;      /* 浅色背景 */
                color: #000000;                 /* 黑色文字 */
                border: 1px solid #ccc;         /* 边框颜色更浅 */
            }
            QMenu::item {
                padding: 5px 30px;              /* 上下左右内边距 */
            }
            QMenu::item:selected {
                background-color: #d0d0d0;      /* 悬停加深背景色 */
                color: #000000;                  /* 文字仍为黑色 */
            }
        """)

        delete_action = QAction("删除", self)
        menu.addAction(delete_action)
        menu.addAction("添加到收藏",
            lambda: self.add_record_to_fav.emit(record_widget.get_record_dict())
        )
        delete_action.triggered.connect(lambda: self.deleteRecordWidget(record_widget))

        menu.exec(global_pos)

    def show_error(self, message: str):
        QMessageBox.critical(self, "错误", message)

    def show_info(self, message: str):
        QMessageBox.information(self, "信息", message)

    # 删除
    def deleteRecordWidget(self, widget: "RecordWidget"):
        reply = QMessageBox.question(
            self, "确认删除",
            "删除记录将同时从本地与云端中删除生成结果与收藏夹中可能存在的对应记录，是否确认？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        
        def __on_delete_response(self:HistoryPage, reply, widget: RecordWidget):
            response_data = reply.readAll().data().decode("utf-8")
            result = json.loads(response_data)
            if result.get("code") != 200:
                self.show_error("记录删除失败，状态码：" + str(reply.status_code))
                return
            if widget in self.all_records:
                self.all_records.remove(widget)
                self.record_deleted.emit(widget.get_record_dict())
                widget.remove_record()
                widget.setParent(None)
                widget.deleteLater()
                
        async_request(
            sender=self,
            method="POST",
            url="/user/generation_list",
            data={"result_url": widget.result_url},
            handle_response=lambda reply: __on_delete_response(self, reply, widget)
        )

