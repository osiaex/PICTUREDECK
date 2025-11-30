from io import BytesIO
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFileDialog, QScrollArea, QFrame, QMessageBox
)
from PySide6.QtGui import QPixmap, QCursor
from PySide6.QtCore import Qt, QSize, Signal
import json
import sys
from enum import Enum
from ui.FavTreeView import FavTreeView
from services.request_service import async_request
from services.local_store import LocalDB, save_pixmap_from_url
from services.session import session
from ui.HistoryPage import DESC_TO_GEN_TYPE, GEN_TYPE_DESC, GenerationType, HistoryPage, RecordWidget
from ui.FavPathSelector import FavPathSelector

class UploadPreview(QWidget):
    imageRemoved = Signal()   # 发射信号，用于通知父组件图片被删除

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 140)  # 可修改大小

        # 主布局（叠加）
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # --- 图片显示区域 ---
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #EEE; border: 1px solid #CCC; border-radius: 8px;")
        self.main_layout.addWidget(self.image_label)

        # --- 左上角删除按钮 ---
        self.close_button = QPushButton("×", self)
        self.close_button.setFixedSize(24, 24)
        self.close_button.setStyleSheet("""
            QPushButton {
                background: rgba(0,0,0,0.6);
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(255,0,0,0.8);
            }
        """)
        self.close_button.move(5, 5)  # 绝对位置
        self.close_button.clicked.connect(self.removeImage)

        self.close_button.hide()  # 初始隐藏，没图不显示

        self.pixmap = None

    # ------------------------- 接口函数 --------------------------------
    def setImage(self, pixmap: QPixmap):
        """显示一张图片"""
        self.pixmap = pixmap
        self.image_label.setPixmap(pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))
        self.close_button.show()

    def clear(self):
        """清空图片"""
        self.pixmap = None
        self.image_label.clear()
        self.close_button.hide()

    def hasImage(self):
        return self.pixmap is not None

    def removeImage(self):
        """用户点击 × 按钮事件"""
        self.clear()
        self.imageRemoved.emit()

class MainWindow(QMainWindow):
    def __init__(self,switch_to_profile, logout):
        super().__init__()
        self.switch_to_profile = switch_to_profile
        self.logout = logout
        self.setWindowTitle("AIGC 内容生成客户端")
        self.setMinimumSize(800, 550)
        self.uploaded_image_path = None
        self.generation_list = []  # 生成记录列表数据初始化为空
        self.fav_list = []  # 收藏列表数据初始化为空
        self.__setup_ui()
        async_request(
            sender=self,
            method="GET",
            url="/user/generation_list",
            data=None,
            handle_response=self.__handle_get_generation_list_response,
        )


    def __handle_get_generation_list_response(self, reply):
        response_data = reply.readAll().data().decode("utf-8")
        result = json.loads(response_data)
        if result.get("code") == 200:
            self.generation_list = result.get("data", [])
            for record in self.generation_list:
                record_widget = RecordWidget(record)
                if not record_widget.serach_image_in_local(record.get("result_url", "")):
                    record_widget.request_image(record.get("result_url", ""))
                
                self.history_page.addWidget(record_widget)

            # 加载完成后再获取收藏列表
            async_request(
                sender=self,
                method="GET",
                url="/user/favorite_list",
                data=None,
                handle_response=self.__handle_get_favorite_list_response,
            )
        else:
            self.show_error(result.get("message", "获取生成列表失败"))

    def __handle_get_favorite_list_response(self, reply):
        response_data = reply.readAll().data().decode("utf-8")
        result = json.loads(response_data)
        if result.get("code") == 200:
            self.fav_list = result.get("data", [])
            self.fav_page.set_available_fav_items(RecordWidget.url_record_map)
            self.fav_page.set_json_tree(self.fav_list)
        else:
            self.show_error(result.get("message", "获取收藏列表失败"))
            
    def show_error(self, message):
        # 简单错误显示
        QMessageBox.critical(self, "错误", message)

    def show_info(self, message):
        # 简单信息显示
        QMessageBox.information(self, "信息", message)

    def __get_current_type(self) -> GenerationType | None:
        """
        从 mode_buttons 中找出被选中的按钮，并返回对应的枚举 GenerationType。
        如果无选中按钮，返回 None。
        """
        mode_text = next((btn.text() for btn in self.mode_buttons if btn.isChecked()), None)
        if not mode_text:
            return None
        
        return DESC_TO_GEN_TYPE.get(mode_text)

    # ===== 模式选择事件 =====
    def __on_mode_selected(self):
        sender = self.sender()
        for btn in self.mode_buttons:
            btn.setChecked(btn == sender)
        self.__update_upload_area_enabled()

    def __on_page_selected(self):
        sender = self.sender()
        for btn in (self.history_button, self.favorite_button):
            btn.setChecked(btn == sender)
        if sender == self.history_button:
            self.stack.setCurrentWidget(self.history_page)
        else:
            self.stack.setCurrentWidget(self.fav_page)

    # ===== 控制上传区可点击性 =====
    def __update_upload_area_enabled(self):
        mode_enum = self.__get_current_type()
        enable_upload = mode_enum in (GenerationType.I2I, GenerationType.I2V)

        if enable_upload:
            self.upload_area.setEnabled(True)
            self.upload_area.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.upload_area.setStyleSheet("""
                #uploadArea {
                    background-color: #F7F8FA;
                    border: 2px dashed #BBB;
                    border-radius: 10px;
                }
                #uploadArea:hover {
                    background-color: #F0F2F5;
                    border-color: #409EFF;
                }
            """)
        else:
            self.upload_area.setEnabled(False)
            self.upload_area.setCursor(QCursor(Qt.CursorShape.ForbiddenCursor))
            self.upload_area.setStyleSheet("""
                #uploadArea {
                    background-color: #EEE;
                    border: 2px dashed #CCC;
                    border-radius: 10px;
                }
            """)

    # ===== 上传图片逻辑（更新预览） =====
    def __upload_image(self, event=None):
        if not self.upload_area.isEnabled():
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg)"
        )
        if file_path:
            pixmap = QPixmap(file_path).scaled(
                QSize(140, 140), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.upload_preview.setImage(pixmap)
            self.upload_label.setText("已选择图片")
            self.upload_label.setStyleSheet("color: #409EFF; font-size: 14px;")
            self.uploaded_image_path = file_path



    # ===== 生成按钮点击事件 =====
    def handle_generate(self):
        gen_type = self.__get_current_type()
        if not gen_type:
            self.show_error("请选择生成类型")
            return
        text = self.text_input.toPlainText().strip()
        if not text:
            self.text_input.setFocus()
            return
        # 需要图片的生成需要待图片上传完成后再发起生成请求
        if gen_type in (GenerationType.I2I, GenerationType.I2V):
            if not self.uploaded_image_path:
                self.show_error("请上传参考图片")
                return
            # todo 多图的同步上传暂不支持，先只上传一张
            async_request(
                sender=self,
                method="POST",
                url="/upload",
                data=self.uploaded_image_path,
                handle_response=lambda reply: self.__handle_image_upload_response(reply, gen_type, text, parameters={}),
            )
        else:
            # 仅依赖文本的生成直接发起生成请求
            data = {"type": gen_type.value, "prompt": text, "parameters": {}}
            async_request(
                sender=self,
                method="POST",
                url="/generation",
                data=data,
                handle_response=self.__handle_generate_response,
            )


    def __handle_image_upload_response(self, reply, gen_type, prompt, parameters):
        response_data = reply.readAll().data().decode("utf-8")
        result = json.loads(response_data)
        if result.get("code") == 200:
            self.show_info("图片上传成功")
            # 上传成功后继续生成
            data = {"type": gen_type.value, "prompt": prompt, "parameters": parameters, "image": result.get("data", {}).get("file_id")}
            async_request(
                sender=self,
                method="POST",
                url="/generation",
                data=data,
                handle_response=self.__handle_generate_response,
            )
        else:
            self.show_error(result.get("message", "图片上传失败"))


    def __handle_generate_response(self, reply):
        response_data = reply.readAll().data().decode("utf-8")
        result = json.loads(response_data)
        if result.get("code") == 200:
            self.show_info("生成请求已提交，稍后请在历史记录中查看结果")
            record_widget = RecordWidget(result.get("data", {}))
            self.history_page.addWidget(record_widget)
            self.start_polling_generation(result.get("data").get("task_id"), record_widget)
        else:
            self.show_error(result.get("message", "生成请求失败"))

    def start_polling_generation(self, task_id, record_widget):
        from PySide6.QtCore import QTimer

        def poll():
            async_request(
                sender=self,
                method="GET",
                url=f"/generation/{task_id}",
                data=None,
                handle_response=lambda reply: self.__handle_poll_response(reply, task_id, record_widget, timer),
            )

        timer = QTimer(self)
        timer.timeout.connect(poll)
        timer.start(2000)  # 每2秒轮询一次
        poll()  # 立即执行一次

    def __handle_poll_response(self, reply, task_id, record_widget: RecordWidget, timer):
        response_data = reply.readAll().data().decode("utf-8")
        result = json.loads(response_data)
        if result.get("code") == 200:
            status = result.get("data", {}).get("status")
            if status == "completed":
                timer.stop()
                self.show_info("生成完成")
                record_widget.request_image(result.get("data", {}).get("result_url", ""))
            elif status == "failed":
                timer.stop()
                self.show_error("生成失败")
        else:
            self.show_error(result.get("message", "轮询生成状态失败"))

    def __on_log_out(self):
        session.clear_session()
        self.logout()

    def on_image_removed(self):
        self.uploaded_image_path = None
        self.upload_label.setText("+\n上传参考图\n支持 JPG/PNG")
        self.upload_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.upload_label.setStyleSheet("font-size: 14px; color: #666;")

    def __on_record_deleted(self, record_dict):
        # 当历史记录页面发出记录删除信号时，更新收藏夹中的对应记录
        record_url = record_dict.get("result_url")
        if not record_url:
            return
        # 从收藏列表中移除对应记录
        self.fav_list = self.fav_page.get_json_tree()
        self.fav_list = [fav for fav in self.fav_list if fav.get("refer_url") != record_url]
        self.fav_page.set_json_tree(self.fav_list)

    def __add_record_from_history_to_fav(self, record_dict):
        # 当历史记录页面发出添加到收藏夹信号时，更新收藏夹中的对应记录
        record_url = record_dict.get("result_url")
        if not record_url:
            return

        selector = FavPathSelector(self.fav_page.get_json_tree(), parent=self)
        selected_result = selector.get_result()
        if selected_result:
            self.fav_page.add_fav_directly(selected_result[1], selected_result[0], record_dict.get("result_url"))

    def __setup_ui(self):
        # 主容器
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # ===== 左侧输入区 =====
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(14)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_widget.setFixedWidth(420)
        left_widget.setStyleSheet("background-color: #f8f9fb; border-radius: 8px;")

        # 功能选择栏
        self.mode_selector = QHBoxLayout()
        self.mode_buttons = []
        for text in GEN_TYPE_DESC.values():
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedHeight(36)
            btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #ccc;
                    border-radius: 6px;
                    background-color: #fff;
                    font-size: 13px;
                    padding: 0 10px;
                }
                QPushButton:checked {
                    background-color: #409EFF;
                    color: white;
                    border: none;
                }
                QPushButton:hover {
                    border-color: #409EFF;
                }
            """)
            btn.clicked.connect(self.__on_mode_selected)
            self.mode_buttons.append(btn)
            self.mode_selector.addWidget(btn)

        self.mode_buttons[0].setChecked(True)  # 默认选中文本生图

        # 文本输入框（浅色背景）
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("请输入描述性文本，如：“一只戴眼镜的蓝色猫坐在草地上”")
        self.text_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 6px;
                font-size: 14px;
                padding: 6px;
                background-color: #fcfcfd;
            }
            QTextEdit:focus {
                border-color: #409EFF;
                background-color: #ffffff;
            }
        """)
        self.text_input.setFixedHeight(120)

        # ============ 上传区 ============ #
        upload_layout = QHBoxLayout()
        upload_layout.setSpacing(16)

        # 左：可点击上传区域
        self.upload_area = QFrame()
        self.upload_area.setObjectName("uploadArea")
        self.upload_area.setFixedHeight(140)

        area_layout = QVBoxLayout(self.upload_area)
        area_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.upload_label = QLabel("+\n上传参考图\n支持 JPG/PNG")
        self.upload_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.upload_label.setStyleSheet("font-size: 14px; color: #666;")
        area_layout.addWidget(self.upload_label)

        self.upload_area.mousePressEvent = self.__upload_image  # 点击整个区域上传

        # 右：预览图
        self.upload_preview = UploadPreview()
        self.upload_preview.imageRemoved.connect(self.on_image_removed)


        upload_layout.addWidget(self.upload_area, 1)
        upload_layout.addWidget(self.upload_preview)

        # 样式
        self.upload_area.setStyleSheet("""
            #uploadArea {
                background-color: #F7F8FA;
                border: 2px dashed #BBB;
                border-radius: 10px;
            }
            #uploadArea:hover {
                background-color: #F0F2F5;
                border-color: #409EFF;
            }
        """)

        # =================================== #

        # 生成按钮（靠下）
        self.generate_button = QPushButton("生成")
        self.generate_button.setFixedHeight(42)
        self.generate_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_button.setStyleSheet("""
            QPushButton {
                background-color: #67C23A;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #85ce61;
            }
        """)
        self.generate_button.clicked.connect(self.handle_generate)

        # 左侧布局装配
        left_layout.addLayout(self.mode_selector)
        left_layout.addWidget(self.text_input)
        left_layout.addLayout(upload_layout)
        left_layout.addStretch()
        left_layout.addWidget(self.generate_button)

        # ===== 右侧展示区 =====
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(12)
        right_widget.setStyleSheet("background-color: #ffffff; border-radius: 8px;")

        # 顶部导航栏（居右）
        nav_bar = QHBoxLayout()
        nav_bar.setSpacing(20)
        nav_bar.setContentsMargins(10, 0, 10, 0)
        nav_bar.addStretch()
        self.account_button = QPushButton("个人资料")
        self.logout_button = QPushButton("退出登录")
        self.favorite_button = QPushButton("收藏夹")
        self.history_button = QPushButton("历史记录")

        self.account_button.clicked.connect(self.switch_to_profile)
        self.logout_button.clicked.connect(self.__on_log_out)
        for btn in (self.account_button, self.logout_button):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    font-size: 14px;
                    color: #333;
                }
                QPushButton:hover {
                    color: #409EFF;
                    text-decoration: underline;
                }
            """)
            nav_bar.addWidget(btn)


        for btn in (self.history_button, self.favorite_button):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    font-size: 14px;
                    color: #333;
                }
                QPushButton:hover {
                    color: #409EFF;
                    text-decoration: underline;
                }
                QPushButton:checked {
                    color: #409EFF;
                    font-weight: bold;
                    text-decoration: underline;
                }
            """)
            nav_bar.addWidget(btn)
        self.history_button.setChecked(True)  # 默认选中历史记录




        self.history_page = HistoryPage(parent=self)

        self.fav_page = FavTreeView(json_data=self.fav_list, parent=self)
        self.history_page.record_deleted.connect(self.__on_record_deleted)
        self.history_page.add_record_to_fav.connect(self.__add_record_from_history_to_fav)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.history_page)
        self.stack.addWidget(self.fav_page)
        self.stack.setCurrentWidget(self.history_page)
        self.favorite_button.clicked.connect(
            self.__on_page_selected
        )
        self.history_button.clicked.connect(
            self.__on_page_selected
        )

        right_layout.addLayout(nav_bar)
        right_layout.addWidget(self.stack)

        # 合并左右
        main_layout.addWidget(left_widget)
        main_layout.addWidget(right_widget)
        self.setCentralWidget(central_widget)

        # 初始禁用上传
        self.__update_upload_area_enabled()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(switch_to_profile=lambda:42,  logout=lambda:42)
    window.show()
    sys.exit(app.exec())
