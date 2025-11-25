import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, Signal
import re
from services.request_service import async_request

class RegisterWindow(QWidget):

    def __init__(self, switch_to_login=None):
        super().__init__()
        self.switch_to_login = switch_to_login
        self.setWindowTitle("AIGC客户端注册")
        self.setFixedSize(380, 360)
        self.setup_ui()

    def __handle_register_response(self, reply):
        self.register_button.setEnabled(True)
        response_data = reply.readAll().data().decode("utf-8")
        result = json.loads(response_data)
        if result.get("code") == 200:
            self.show_info(result.get("message", "注册成功"))
            if self.switch_to_login:
                self.switch_to_login()
        else:
            self.show_error(result.get("message", "注册失败"))


    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(12)

        # ---- 标题 ----
        title = QLabel("注册新用户")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:24px; font-weight:bold; margin:0; padding:0;")

        # ---- 输入框 ----
        self.account_input = QLineEdit()
        self.account_input.setPlaceholderText("账号")
        self.account_input.setFixedHeight(36)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("邮箱")
        self.email_input.setFixedHeight(36)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(36)

        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("确认密码")
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setFixedHeight(36)

        common_style = """
            QLineEdit {
                border: 1px solid #aaa;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 14px;
                height: 36px;
            }
            QLineEdit:focus {
                border-color: #409EFF;
            }
        """
        for widget in (self.account_input, self.email_input, self.password_input, self.confirm_input):
            widget.setStyleSheet(common_style)

        # ---- 注册按钮 ----
        self.register_button = QPushButton("注册")
        self.register_button.setCursor(Qt.PointingHandCursor)
        self.register_button.setFixedHeight(38)
        self.register_button.setDefault(True)
        self.register_button.clicked.connect(self.handle_register)

        button_style = """
            QPushButton {
                background-color: #409EFF;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                height: 38px;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
            QPushButton:pressed {
                background-color: #3a8ee6;
            }
        """
        self.register_button.setStyleSheet(button_style)

        # ---- 返回登录 ----
        bottom_layout = QHBoxLayout()
        back_button = QPushButton("返回登录")
        back_button.setCursor(Qt.PointingHandCursor)
        back_button.setFixedHeight(30)
        back_button.setStyleSheet("""
            QPushButton {
                color: #409EFF;
                background-color: transparent;
                border: none;
                font-size: 13px;
                padding: 2px 6px;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        back_button.clicked.connect(self.close)
        bottom_layout.addStretch()
        bottom_layout.addWidget(back_button)

        # ---- 组装布局 ----
        layout.addWidget(title)
        layout.addWidget(self.account_input)
        layout.addWidget(self.email_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.confirm_input)
        layout.addWidget(self.register_button)
        layout.addLayout(bottom_layout)
        layout.addStretch()

        self.setLayout(layout)


    # ---- 注册逻辑 ----
    def handle_register(self):
        account = self.account_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        confirm = self.confirm_input.text().strip()

        # 1. 基本校验
        if not all([account, email, password, confirm]):
            QMessageBox.warning(self, "错误", "请填写所有字段！")
            return

        # 2. 邮箱格式验证
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
            QMessageBox.warning(self, "错误", "邮箱格式不正确！")
            return

        # 3. 两次密码一致性
        if password != confirm:
            QMessageBox.warning(self, "错误", "两次输入的密码不一致！")
            return

        self.register_button.setEnabled(False)
        async_request(
            sender=self,
            method="POST",
            url="/auth/register",
            data={"account": account, "email": email, "password": password},
            handle_response=self.__handle_register_response,
        )

    def show_error(self, message):
        QMessageBox.warning(self, "错误", message)

    def show_info(self, message):
        QMessageBox.information(self, "消息", message)
