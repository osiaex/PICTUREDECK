import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, Signal

from services.session import session
from services.request_service import async_request

class LoginWindow(QWidget):

    def __init__(self, switch_to_register, switch_to_main, switch_to_forgot_password_window):
        super().__init__()
        self.switch_to_register = switch_to_register
        self.switch_to_main = switch_to_main
        self.switch_to_forgot_password_window = switch_to_forgot_password_window
        self.setWindowTitle("AIGC客户端登录")
        self.setFixedSize(350, 280)
        self.__setup_ui()

    def __handle_login_response(self, reply):
        self.login_button.setEnabled(True)
        response_data = reply.readAll().data().decode("utf-8")
        result = json.loads(response_data)
        if result.get("code") == 200:
            user_data = result.get("data", {})
            session.set_session(
                token=user_data.get("token"),
                account=user_data.get("account"),
                email=user_data.get("email")
            )
            self.show_info(result.get("message", "登录成功"))
            self.switch_to_main()
        else:
            self.show_error(result.get("message", "登录失败"))

    def __setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 20, 30, 20)   # 四周留白适度
        # layout.setSpacing(15)                      # 控制控件间距

        # ---- 标题 ----
        title = QLabel("AIGC客户端")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:24px; font-weight:bold; margin:0; padding:0;")

        # ---- 顶部提示信息 ----
        self.message_label = QLabel()
        self.message_label.setText("")
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignLeft)
        self.message_label.setStyleSheet("font-size: 13px; margin-bottom: 6px;")

        # ---- 输入框 ----
        self.account_input = QLineEdit()
        self.account_input.setPlaceholderText("账号")
        self.account_input.setFixedHeight(36)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(36)

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
        self.account_input.setStyleSheet(common_style)
        self.password_input.setStyleSheet(common_style)

        # ---- 登录按钮 ----
        self.login_button = QPushButton("登录")
        self.login_button.clicked.connect(self.on_login)
        self.login_button.setDefault(True)
        self.login_button.setFixedHeight(38)
        self.login_button.setCursor(Qt.PointingHandCursor)

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
            QPushButton:disabled {
                background-color: #c0c4cc;
                color: #f0f0f0;
            }
        """
        self.login_button.setStyleSheet(button_style)

        # ---- 底部区域 ----
        bottom_layout = QHBoxLayout()

        # 注册部分
        register_label = QLabel("还没有账号？")
        register_button = QPushButton("去注册")
        register_button.setCursor(Qt.PointingHandCursor)
        register_button.setFixedHeight(30)
        register_button.setStyleSheet("""
            QPushButton {
                color: #409EFF;
                background-color: transparent;
                border: none;
                font-size: 13px;
                font-weight: 500;
                padding: 2px 6px;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        register_button.clicked.connect(self.switch_to_register)

        # 忘记密码部分
        forgot_button = QPushButton("忘记密码？")
        forgot_button.setCursor(Qt.PointingHandCursor)
        forgot_button.setFixedHeight(30)
        forgot_button.setStyleSheet("""
            QPushButton {
                color: #999;
                background-color: transparent;
                border: none;
                font-size: 13px;
                padding: 2px 6px;
            }
            QPushButton:hover {
                color: #409EFF;
                text-decoration: underline;
            }
        """)
        forgot_button.clicked.connect(self.switch_to_forgot_password_window)

        # 排列：左侧注册、右侧忘记密码
        bottom_layout.addWidget(register_label)
        bottom_layout.addWidget(register_button)
        bottom_layout.addStretch()
        bottom_layout.addWidget(forgot_button)

        # ---- 组装布局 ----
        layout.addWidget(title)
        layout.addWidget(self.message_label)
        layout.addWidget(self.account_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.login_button)
        layout.addLayout(bottom_layout)
        layout.addStretch()  # 让底部留出空间，视觉居中

        self.setLayout(layout)

    def show_error(self, message):
        self.message_label.setText(message)
        self.message_label.setStyleSheet("""
            color: #ff4d4f;
            font-size: 13px;
            font-weight: bold;
            margin-bottom: 6px;
        """)
        self.message_label.setVisible(True)

    def show_info(self, message):
        self.message_label.setText(message)
        self.message_label.setStyleSheet("""
            color: #409EFF;
            font-size: 13px;
            font-weight: bold;
            margin-bottom: 6px;
        """)
        self.message_label.setVisible(True)

    def on_login(self):
        account = self.account_input.text().strip()
        password = self.password_input.text().strip()
        if not account or not password:
            self.show_error("账号和密码不能为空")
            return
        self.login_button.setEnabled(False)
        async_request(
            sender=self,
            method="POST",
            url="/auth/login",
            data={"account": account, "password": password},
            handle_response=self.__handle_login_response,
        )


