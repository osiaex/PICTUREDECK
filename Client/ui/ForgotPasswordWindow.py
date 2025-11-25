import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt
import re, random
from services.request_service import async_request

class ForgotPasswordWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.email = None
        self.switch_to_login = self.close
        self.setWindowTitle("找回密码")
        self.setFixedSize(380, 360)
        self.has_get_code = False
        self.__setup_ui()

    # ---- 获取验证码逻辑（模拟发送邮件） ----
    def handle_get_code(self):
        self.email = self.email_input.text().strip()
        if not self.email:
            QMessageBox.warning(self, "错误", "请输入邮箱地址！")
            return
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", self.email):
            QMessageBox.warning(self, "错误", "邮箱格式不正确！")
            return

        async_request(
            sender=self,
            url="/auth/forgot-password",
            method="POST",  
            data={"email": self.email},
            handle_response=self.__handle_get_code_response
        )

    def __handle_get_code_response(self, reply):
        response_data = reply.readAll().data().decode("utf-8")
        result = json.loads(response_data)
        if result.get("code") == 200:
            self.show_info(result.get("message", "邮件已发送"))
            self.has_get_code = True
        else:
            self.show_error(result.get("message", "获取验证码失败"))


    # ---- 提交新密码逻辑 ----
    def handle_submit(self):
        code = self.code_input.text().strip()
        new_password = self.new_password_input.text().strip()
        confirm = self.confirm_input.text().strip()

        if not all([code, new_password, confirm]):
            self.show_error("请填写所有字段！")
            return

        if not self.has_get_code:
            self.show_error("请先获取验证码！")
            return

        if new_password != confirm:
            self.show_error("两次输入的密码不一致！")
            return

        async_request(
            sender=self,
            url="/auth/reset-password",
            method="POST",
            data={
                "email": self.email,
                "verification_code": code,
                "new_password": new_password
            },
            handle_response=self.__handle_submit_response
        )
    def __handle_submit_response(self, reply):
        response_data = reply.readAll().data().decode("utf-8")
        result = json.loads(response_data)
        if result.get("code") == 200:
            self.show_info(result.get("message", "密码重置成功"))
            self.switch_to_login()
        else:
            self.show_error(result.get("message", "密码重置失败"))



    def show_error(self, message):
        QMessageBox.warning(self, "错误", message)

    def show_info(self, message):
        QMessageBox.information(self, "消息", message)

    def __setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(12)

        # ---- 标题 ----
        title = QLabel("找回密码")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:24px; font-weight:bold; margin:0; padding:0;")

        # ---- 邮箱 + 获取验证码布局 ----
        email_layout = QHBoxLayout()
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("请输入注册邮箱")
        self.email_input.setFixedHeight(36)

        self.get_code_button = QPushButton("获取验证码")
        self.get_code_button.setCursor(Qt.PointingHandCursor)
        self.get_code_button.setFixedHeight(36)
        self.get_code_button.setStyleSheet("""
            QPushButton {
                background-color: #409EFF;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
        """)
        self.get_code_button.clicked.connect(self.handle_get_code)

        email_layout.addWidget(self.email_input, 3)  # 占比 3
        email_layout.addWidget(self.get_code_button, 1)  # 占比 1

        # ---- 验证码输入框 ----
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("请输入邮箱验证码")
        self.code_input.setFixedHeight(36)

        # ---- 新密码输入框 ----
        self.new_password_input = QLineEdit()
        self.new_password_input.setPlaceholderText("新密码")
        self.new_password_input.setEchoMode(QLineEdit.Password)
        self.new_password_input.setFixedHeight(36)

        # ---- 确认新密码输入框 ----
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("确认新密码")
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setFixedHeight(36)

        # ---- 输入框样式 ----
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
        for widget in (self.email_input, self.code_input, self.new_password_input, self.confirm_input):
            widget.setStyleSheet(common_style)

        # ---- 提交新密码按钮 ----
        self.submit_button = QPushButton("提交")
        self.submit_button.setCursor(Qt.PointingHandCursor)
        self.submit_button.setFixedHeight(38)
        self.submit_button.setStyleSheet("""
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
        """)
        self.submit_button.clicked.connect(self.handle_submit)

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
        back_button.clicked.connect(self.switch_to_login)
        bottom_layout.addStretch()
        bottom_layout.addWidget(back_button)

        # ---- 组装布局 ----
        layout.addWidget(title)
        layout.addLayout(email_layout)
        layout.addWidget(self.code_input)
        layout.addWidget(self.new_password_input)
        layout.addWidget(self.confirm_input)
        layout.addWidget(self.submit_button)
        layout.addLayout(bottom_layout)
        layout.addStretch()

        self.setLayout(layout)
