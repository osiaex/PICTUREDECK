import json
import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QHBoxLayout, QLineEdit, QPushButton, QMenu, QMessageBox, QInputDialog, QCheckBox, QLabel
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from services.first_frame_extractor import FirstFrameExtractor
from services.local_store import LocalDB, save_data_from_url, save_pixmap_from_url
from services.request_service import async_request
from services.session import session
from PySide6.QtGui import QPixmap, QMovie
from PySide6.QtWidgets import QLabel
from enum import Enum
from ui.RecordDialog import RecordDialog
from ui.MouseBlockOverlay import MouseBlockOverlay
from services.config import app_config
from services.nft import mint_nft, transfer_nft

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



class RecordWidget(QWidget):
    """单条记录展示组件"""
    """
record: dict
    一条 AI 生成内容或收藏项的记录，JSON 格式如下：

    {
        "type": str,   # 生成类型，如 "文生图"、"文生视频"、"图生图" 等
        "prompt": str,            # 用户输入的提示词，用于生成内容
        "parameters": dict,       # 生成时使用的参数，可包含 size、model、seed 等
        "result_url": str,         # 生成结果的图片或封面图的网络地址（HTTP/HTTPS）
        "local_path": str,         # 本地保存的图片路径（可选）
        "task_id": str,          # 生成任务的唯一标识符
        "nft_token_id": str,     # 如果已上链为 NFT，则为 NFT 的 Token ID
        "is_on_chain": bool,     # 是否已上链为 NFT
        "is_transferred": bool   # NFT 是否已被转让
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
        self.image_size = 350
        self.type=STR_TO_DESC.get(record.get("type", "未知类型"), "未知类型")
        self.task_id=record.get("task_id","")
        self.nft_token_id=record.get("nft_token_id","")

        self.is_on_chain=record.get("is_on_chain", False)
        self.is_transferred=record.get("is_transferred", False)

        self.is_chain_pending= False
        self.is_transfer_pending= False

        self.status = record.get("status", "")
        self.review_status = record.get("review_status", "")
        self.review_message = record.get("review_message", "")

        self.prompt=record.get("prompt", "")
        self.parameters=record.get("parameters", {})
        self.result_url=record.get("result_url", "")
        self.local_path=None
        if self.result_url and not RecordWidget.url_record_map.get(self.result_url):
            RecordWidget.url_record_map[self.result_url] = self  # 缓存 URL 到实例的映射

        self.first_frame_extractor = None
        # 显示文字信息
        title_label = QLabel(f"{self.type}\n {self.prompt}")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        
        # 图片
        self.loading_movie = QMovie("ui/assets/loading_1.gif")
        self.loading_movie.setScaledSize(QSize(self.image_size, self.image_size))
        self.img_label = QLabel()
        self.img_label.setMovie(self.loading_movie)
        self.loading_movie.start()
        layout.addWidget(self.img_label)
        
        self.setLayout(layout)

        # --- 初始化NFT状态图标和动画 ---
        self.ICON_FONT_SIZE = 15

        # 确定图标尺寸 (GIF 和 QLabel 保持一致)
        icon_dim = QSize(self.ICON_FONT_SIZE, self.ICON_FONT_SIZE) # 稍微加一点边距

        # 样式 (用于 QLabel 静态图标)
        icon_style = f"""
            QLabel {{
                background-color: transparent;
                color: black;
                font-size: {self.ICON_FONT_SIZE}px; 
                font-weight: bold;
            }}
        """

        # --- A. 上链状态 (Chain Status) ---
        
        # 3.1. 完成图标 ⛓️
        self.icon_chain_done = QLabel("⛓️", self)
        self.icon_chain_done.setStyleSheet(icon_style)
        self.icon_chain_done.setToolTip(f"已上链 (Token ID: {self.nft_token_id})")
        
        # 3.2. 进行中动画
        self.movie_chain_pending = QMovie("ui/assets/loading_2.gif")
        self.movie_chain_pending.setScaledSize(icon_dim)
        
        # 3.3. 动画载体 (QLabel 用于显示 QMovie)
        self.icon_chain_pending_label = QLabel(self)
        self.icon_chain_pending_label.setMovie(self.movie_chain_pending)
        self.icon_chain_pending_label.setToolTip("正在上链中...")

        # --- B. 转让状态 (Transfer Status) ---
        
        # 3.4. 完成图标 📥
        self.icon_transfer_done = QLabel("📥", self)
        self.icon_transfer_done.setStyleSheet(icon_style)
        self.icon_transfer_done.setToolTip("NFT 已转让给用户")

        # 3.5. 进行中动画
        self.movie_transfer_pending = QMovie("ui/assets/loading_2.gif") 
        self.movie_transfer_pending.setScaledSize(icon_dim)
        
        # 3.6. 动画载体
        self.icon_transfer_pending_label = QLabel(self)
        self.icon_transfer_pending_label.setMovie(self.movie_transfer_pending)
        self.icon_transfer_pending_label.setToolTip("正在转让中...")

        # --- 4. 初始化遮罩组件 ---
        self.overlay = MouseBlockOverlay(self, use_gif=False)

        # 初始状态更新
        self._update_icon_visibility()
        
    def _update_icon_visibility(self):
        """根据布尔状态，控制显示完成图标还是进行中动画，并启动/停止动画"""
        
        # --- 1. 上链状态逻辑 ---
        if self.is_on_chain:
            # 已完成：显示静态图标
            self.icon_chain_done.setVisible(True)
            self.icon_chain_pending_label.setVisible(False)
            self.movie_chain_pending.stop()
        elif self.is_chain_pending:
            # 进行中：显示动画
            self.icon_chain_done.setVisible(False)
            self.icon_chain_pending_label.setVisible(True)
            self.movie_chain_pending.start()
        else:
            # 未开始或失败：都不显示
            self.icon_chain_done.setVisible(False)
            self.icon_chain_pending_label.setVisible(False)
            self.movie_chain_pending.stop()

        # --- 2. 转让状态逻辑 ---
        if self.is_transferred:
            # 已完成：显示静态图标
            self.icon_transfer_done.setVisible(True)
            self.icon_transfer_pending_label.setVisible(False)
            self.movie_transfer_pending.stop()
        elif self.is_transfer_pending:
            # 进行中：显示动画
            self.icon_transfer_done.setVisible(False)
            self.icon_transfer_pending_label.setVisible(True)
            self.movie_transfer_pending.start()
        else:
            # 未开始或失败：都不显示
            self.icon_transfer_done.setVisible(False)
            self.icon_transfer_pending_label.setVisible(False)
            self.movie_transfer_pending.stop()

        if self.is_chain_pending or self.is_transfer_pending or self.status == "queued" or self.status == "processing":
            # 显示遮罩
            self.overlay.setActive(True, "请稍候...")
        else:
            # 隐藏遮罩
            self.overlay.setActive(False)
        # 无论如何都要触发定位更新
        self.resizeEvent(None)


    def resizeEvent(self, event):
        """
        当组件大小改变时触发，用于将图标强制固定在右上角
        """
        super().resizeEvent(event)

        if self.status == "failed":
            detail = self.review_message or "未知原因"

            msg = f"""
            <div style="font-family: 'Microsoft YaHei';">
                <div style="
                    color: #d93026;
                    font-size: 18px;
                    font-weight: bold;
                    margin-bottom: 6px;
                ">
                    ❌ 生成失败
                </div>

                <div style="
                    color: #555555;
                    font-size: 13px;
                    line-height: 1.5;
                ">
                    <b>原因：</b>{detail}
                </div>
            </div>
            """

            self.img_label.setTextFormat(Qt.RichText)
            self.img_label.setText(msg)



        # 调整遮罩大小
        self.overlay.syncGeometry()

        # 调整NFT相关图标
        # 边距设置
        top_margin = 3
        right_margin = 3
        icon_spacing = 1
        
        current_x = self.width() - right_margin
        
        # 确定哪些图标当前可见，并获取它们的载体 (QLabel 或 动画载体)
        chain_icon_widget = None
        if self.is_on_chain:
            chain_icon_widget = self.icon_chain_done
        elif self.is_chain_pending:
            chain_icon_widget = self.icon_chain_pending_label
            
        transfer_icon_widget = None
        if self.is_transferred:
            transfer_icon_widget = self.icon_transfer_done
        elif self.is_transfer_pending:
            transfer_icon_widget = self.icon_transfer_pending_label


        # --- 布局逻辑：从右向左排列 ---
        
        # 1. 放置转让图标/动画 (右侧)
        if transfer_icon_widget and transfer_icon_widget.isVisible():
            trans_size = transfer_icon_widget.sizeHint()
            current_x -= trans_size.width()
            transfer_icon_widget.move(current_x, top_margin)
            current_x -= icon_spacing 
            
        # 2. 放置上链图标/动画 (左侧)
        if chain_icon_widget and chain_icon_widget.isVisible():
            chain_size = chain_icon_widget.sizeHint()
            current_x -= chain_size.width()
            chain_icon_widget.move(current_x, top_margin)

    def update_status(self, status=None, review_status=None, review_message=None, is_on_chain=None, is_transferred=None, is_chain_pending=None, is_transfer_pending=None):
        """
        用于外部更新 NFT 状态，并自动重新渲染图标。
        """

        if status is not None:
            self.status = status

        if review_status is not None:
            self.review_status = review_status

        if review_message is not None:
            self.review_message = review_message

        if is_on_chain is not None:
            self.is_on_chain = is_on_chain
            if is_on_chain:
                self.icon_chain_done.setToolTip(f"已上链 (Token ID: {self.nft_token_id})")

        if is_transferred is not None:
            self.is_transferred = is_transferred

        if is_chain_pending is not None:
            self.is_chain_pending = is_chain_pending
            
        if is_transfer_pending is not None:
            self.is_transfer_pending = is_transfer_pending
        
        self._update_icon_visibility()

    def show_error(self, message: str):
        QMessageBox.critical(self, "错误", message)

    def show_info(self, message: str):
        QMessageBox.information(self, "信息", message)

    def is_video_type(self):
        return self.type in ["文生视频", "首帧生视频"]

    def set_image(self, pixmap: QPixmap):
        self.loading_movie.stop()
        self.img_label.setMovie(None)
        self.img_label.setPixmap(pixmap.scaledToWidth(self.image_size, Qt.TransformationMode.SmoothTransformation))

    def serach_image_in_local(self, image_url):
        db = LocalDB.instance()
        record = db.get_record_by_url(image_url)
        if record:
            self.local_path = record.get("local_path")
            if app_config.is_debug():
                print(f"[Debug] Found local record for URL {image_url}: {self.local_path}")
            if self.local_path:
                if self.is_video_type():
                    if not self.first_frame_extractor:
                        self.first_frame_extractor = FirstFrameExtractor(width=self.image_size)
                        self.first_frame_extractor.frame_extracted.connect(lambda pm: self.set_image(pm))
                    self.first_frame_extractor.load_from_file(self.local_path)
                    return True
                pixmap = QPixmap(self.local_path)
                if not pixmap.isNull():
                    if app_config.is_debug():
                        print(f"[Debug] Loaded pixmap from local, size: {pixmap.size()}")
                    self.set_image(pixmap)
                    return True
        return False
    
    def remove_record(self):
        if self.result_url is None:
            return
        db = LocalDB.instance()
        db.delete_record_by_url(self.result_url)
        if self.result_url in RecordWidget.url_record_map:
            del RecordWidget.url_record_map[self.result_url]
        if os.path.exists(self.local_path):
            os.remove(self.local_path)
            
    
    def request_image(self, image_url):
        self.result_url=image_url
        if not image_url:
            return
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
            "status": self.status,
            "review_status": self.review_status,
            "review_message": self.review_message,
            "task_id": self.task_id,
            "nft_token_id": self.nft_token_id,
            "is_on_chain": self.is_on_chain,
            "is_transferred": self.is_transferred,
            "type": DESC_TO_GEN_TYPE[self.type].value,
            "prompt": self.prompt,
            "parameters": self.parameters,
            "result_url": self.result_url,
            "local_path": self.local_path
        }
    
    def __update_image(self, reply):
        data = reply.readAll()
        pixmap = QPixmap()
        if not self.is_video_type():
            success = pixmap.loadFromData(data)
            if success and not pixmap.isNull():
                self.set_image(pixmap)
            elif app_config.is_debug():
                self.img_label.setText("图片加载失败（格式错误）")
                print("loadFromData success:", success)
                print("img_data size:\n", len(data))
                print(bytes(data[:20]).hex(" "))
                from PySide6.QtGui import QImageReader
                print(QImageReader.supportedImageFormats())

                with open("debug_image.bin", "wb") as f:
                    f.write(data)

        # 缓存 URL 到实例的映射
        RecordWidget.url_record_map[self.result_url] = self
        # 保存图片到本地
        self.local_path = save_data_from_url(self.result_url, data)
        if self.is_video_type():
            if not self.first_frame_extractor:
                self.first_frame_extractor = FirstFrameExtractor(width=self.image_size)
                self.first_frame_extractor.frame_extracted.connect(lambda pm: self.set_image(pm))
            self.first_frame_extractor.load_from_file(self.local_path)
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

        # ========== 类型过滤区 ==========
        type_filter_container = QWidget()
        type_layout = QHBoxLayout(type_filter_container)
        type_layout.setContentsMargins(10, 0, 10, 0)
        type_layout.setSpacing(10)

        self.ALL_TYPES = [
            "文生图",
            "参考图生图",
            "文生视频",
            "首帧生视频",
        ]

        self.type_checkboxes = {}
        self.enabled_types = set(self.ALL_TYPES)

        # --- 全选 ---
        self.select_all_cb = QCheckBox("全选")
        self.select_all_cb.setChecked(True)
        self.select_all_cb.stateChanged.connect(self.onSelectAllClicked)
        type_layout.addWidget(self.select_all_cb)

        # --- 各类型 ---
        for t in self.ALL_TYPES:
            cb = QCheckBox(t)
            cb.setChecked(True)
            cb.stateChanged.connect(self.onTypeFilterChanged)
            self.type_checkboxes[t] = cb
            type_layout.addWidget(cb)

        type_layout.addStretch(1)
        self.main_layout.addWidget(type_filter_container)



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
        for record in self.all_records:
            # ===== 1. 提示词过滤 =====
            text = getattr(record, "prompt", "").lower()
            keyword_match = all(t.lower() in text for t in self.tags)

            # ===== 2. 类型过滤 =====
            record_type = getattr(record, "type", None)
            type_match = record_type in self.enabled_types

            record.setVisible(keyword_match and type_match)


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
        
        if not record_widget.is_video_type() and not record_widget.is_on_chain:
            menu.addAction("上链为NFT",
                lambda: mint_nft(self, record_widget)
            )

        if not record_widget.is_video_type() and record_widget.is_on_chain and not record_widget.is_transferred:
            menu.addAction("转让NFT",
                lambda: transfer_nft(self, record_widget)
            )

        menu.exec(global_pos)

    def enable_ui(self):
        return
    
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
                self.show_error(result.get("message", "删除失败"))
                return
            if widget in self.all_records:
                self.all_records.remove(widget)
                self.record_deleted.emit(widget.get_record_dict())
                widget.remove_record()
                widget.setParent(None)
                widget.deleteLater()
                
        async_request(
            sender=self,
            method="DELETE",
            url=f"/user/generation_list/{widget.task_id}",
            data=None,
            handle_response=lambda reply: __on_delete_response(self, reply, widget)
        )


    def onTypeFilterChanged(self):
        self.enabled_types.clear()

        for t, cb in self.type_checkboxes.items():
            if cb.isChecked():
                self.enabled_types.add(t)

        # 同步「全选」复选框状态
        all_checked = len(self.enabled_types) == len(self.ALL_TYPES)

        self.select_all_cb.blockSignals(True)
        self.select_all_cb.setChecked(all_checked)
        self.select_all_cb.blockSignals(False)

        self.filterRecords()


    def onSelectAllClicked(self):
        # 当前是否为“全选状态”
        all_checked = all(cb.isChecked() for cb in self.type_checkboxes.values())

        # 目标状态：反转
        target = not all_checked

        # 阻止信号递归触发
        for cb in self.type_checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(target)
            cb.blockSignals(False)

        # 同步 enabled_types
        self.enabled_types = set(self.ALL_TYPES) if target else set()

        # 同步全选自身状态
        self.select_all_cb.blockSignals(True)
        self.select_all_cb.setChecked(target)
        self.select_all_cb.blockSignals(False)

        self.filterRecords()


