import json
import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QStackedWidget,
    QListWidget, QListWidgetItem, QMessageBox
)
from PySide6.QtCore import Qt
from services.session import session
from services.request_service import async_request

class ProfileWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.account_info = session.get_user()
        self.setWindowTitle("个人资料")
        self.setFixedSize(500, 360)
        self.setup_ui()

    def show_info(self, message):
        QMessageBox.information(self, "信息", message)

    def show_error(self, message):
        QMessageBox.critical(self, "错误", message)

    def __switch_page(self, index):
        self.stack.setCurrentIndex(index)

    def __handle_update_email_response(self, reply):
        response_data = reply.readAll().data().decode("utf-8")
        result = json.loads(response_data)
        if result.get("code") == 200:
            new_email = result.get("data", {}).get("email", "")
            self.account_info['email'] = new_email
            session.update_user(self.account_info)

            # 更新显示
            self.stack.widget(0).layout().itemAt(1).widget().setText(f"邮箱: {new_email}")
            self.show_info(result.get("message", "邮箱更新成功"))
        else:
            self.show_error(result.get("message", "邮箱更新失败"))


    def update_email(self):
        new_email = self.new_email_input.text().strip()
        if not new_email:
            self.show_error("邮箱不能为空！")
            return
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", new_email):
            self.show_error("邮箱格式不正确！")
            return

        async_request(
            sender=self,
            method="POST",
            url="/user/reset-email",
            data={"new_email": new_email},
            handle_response=self.__handle_update_email_response
        )


    def update_password(self):
        old_pwd = self.old_password_input.text().strip()
        new_pwd = self.new_password_input.text().strip()
        confirm_pwd = self.confirm_password_input.text().strip()

        if not old_pwd or not new_pwd or not confirm_pwd:
            self.show_error("请填写完整密码信息！")
            return
        if new_pwd != confirm_pwd:
            self.show_error("两次输入的新密码不一致！")
            return
        
        async_request(
            sender=self,
            method="POST", 
            url="/user/reset-password",
            data={
                "old_password": old_pwd,
                "new_password": new_pwd
            },
            handle_response=self.__handle_update_password_response
        )

        # self.switch_page(0)
        # self.list_widget.setCurrentRow(0)

    def __handle_update_password_response(self, reply):
        response_data = reply.readAll().data().decode("utf-8")
        result = json.loads(response_data)
        if result.get("code") == 200:
            self.show_info(result.get("message", "密码更新成功"))
        else:
            self.show_error(result.get("message", "密码更新失败"))



    def setup_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---- 左侧侧边栏 ----
        sidebar = QFrame()
        sidebar.setFixedWidth(140)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border-right: 1px solid #ddd;
            }
        """)
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 10px 15px;
            }

        """)
        for name in ["账号信息", "修改邮箱", "修改密码"]:
            item = QListWidgetItem(name)
            self.list_widget.addItem(item)

        self.list_widget.setCurrentRow(0)
        self.list_widget.currentRowChanged.connect(self.__switch_page)

        sidebar_layout.addWidget(self.list_widget)
        sidebar_layout.addStretch()
        sidebar.setLayout(sidebar_layout)

        # ---- 中心区域 ----
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("QWidget { background-color: white; }")

        # --- 页面 0: 账号信息 ---
        info_page = QWidget()
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(30, 20, 30, 20)
        info_layout.setSpacing(12)

        account_label = QLabel(f"账号: {self.account_info.get('account', '')}")
        email_label = QLabel(f"邮箱: {self.account_info.get('email', '')}")
        for lbl in [account_label, email_label]:
            lbl.setStyleSheet("font-size: 16px;")

        info_layout.addWidget(account_label)
        info_layout.addWidget(email_label)
        info_layout.addStretch()
        info_page.setLayout(info_layout)

        # --- 页面 1: 修改邮箱 ---
        email_page = QWidget()
        email_layout = QVBoxLayout()
        email_layout.setContentsMargins(30, 20, 30, 20)
        email_layout.setSpacing(12)

        self.new_email_input = QLineEdit()
        self.new_email_input.setPlaceholderText("输入新邮箱")
        self.new_email_input.setFixedHeight(36)
        self.new_email_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #aaa;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #409EFF;
            }
        """)

        email_submit = QPushButton("更新邮箱")
        email_submit.setCursor(Qt.PointingHandCursor)
        email_submit.setFixedHeight(38)
        email_submit.setStyleSheet("""
            QPushButton {
                background-color: #409EFF;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
            QPushButton:pressed {
                background-color: #3a8ee6;
            }
        """)
        email_submit.clicked.connect(self.update_email)

        email_layout.addWidget(QLabel("修改邮箱:"))
        email_layout.addWidget(self.new_email_input)
        email_layout.addWidget(email_submit)
        email_layout.addStretch()
        email_page.setLayout(email_layout)

        # --- 页面 2: 修改密码 ---
        # --- 页面 2: 修改密码 ---
        password_page = QWidget()
        password_layout = QVBoxLayout()
        password_layout.setContentsMargins(30, 20, 30, 20)
        password_layout.setSpacing(12)

        self.old_password_input = QLineEdit()
        self.old_password_input.setPlaceholderText("旧密码")
        self.old_password_input.setEchoMode(QLineEdit.Password)
        self.old_password_input.setFixedHeight(36)
        self.old_password_input.setStyleSheet(self.new_email_input.styleSheet())

        self.new_password_input = QLineEdit()
        self.new_password_input.setPlaceholderText("新密码")
        self.new_password_input.setEchoMode(QLineEdit.Password)
        self.new_password_input.setFixedHeight(36)
        self.new_password_input.setStyleSheet(self.new_email_input.styleSheet())

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("确认新密码")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setFixedHeight(36)
        self.confirm_password_input.setStyleSheet(self.new_email_input.styleSheet())

        password_submit = QPushButton("更新密码")
        password_submit.setCursor(Qt.PointingHandCursor)
        password_submit.setFixedHeight(38)
        password_submit.setStyleSheet(email_submit.styleSheet())
        password_submit.clicked.connect(self.update_password)

        password_layout.addWidget(QLabel("修改密码:"))
        password_layout.addWidget(self.old_password_input)
        password_layout.addWidget(self.new_password_input)
        password_layout.addWidget(self.confirm_password_input)
        password_layout.addWidget(password_submit)
        password_layout.addStretch()
        password_page.setLayout(password_layout)

        # ---- 添加页面到stack ----
        self.stack.addWidget(info_page)
        self.stack.addWidget(email_page)
        self.stack.addWidget(password_page)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)
