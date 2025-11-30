import sys
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QApplication

from ui.LoginWindow import LoginWindow
from ui.RegisterWindow import RegisterWindow
from ui.ForgotPasswordWindow import ForgotPasswordWindow
from ui.MainWindow import MainWindow
from ui.ProfileWindow import ProfileWindow
from services.session import session
from services.global_signals import global_signals

class MainController:
    def __init__(self):
        self.app = QApplication(sys.argv)

        self.login_window = None
        self.register_window = None
        self.main_window = None
        self.profile_window = None
        self.forget_password_window = None
        
        global_signals.unauthorized.connect(self.show_login)
        if session.is_logged_in():
            self.show_main()
        else:
            self.show_login()

    # ------------------------- 窗口切换功能 -------------------------

    def show_login(self):
        if self.register_window:
            self.register_window.close()
            self.register_window = None
        if self.main_window:
            self.main_window.close()
            self.main_window = None

        self.login_window = LoginWindow(
            switch_to_register=self.show_register,
            switch_to_main=self.show_main,
            switch_to_forgot_password_window = self.show_forget_password_window
        )
        self.login_window.show()

    def success_register_callback(self):
        self.register_window.close()
        self.register_window = None
        self.login_window.activateWindow()
        return

    def show_register(self):
        self.register_window = RegisterWindow(switch_to_login=self.success_register_callback)
        original_close_event = self.login_window.closeEvent
        def new_close_event(event):
            if self.register_window:
                self.register_window.close()
            original_close_event(event)
        self.login_window.closeEvent = new_close_event
        self.register_window.show()

    def show_forget_password_window(self):
        self.forget_password_window = ForgotPasswordWindow()
        original_close_event = self.login_window.closeEvent
        def new_close_event(event):
            if self.forget_password_window:
                self.forget_password_window = None
                self.forget_password_window.close()
            # self.forget_password_window.close()
            original_close_event(event)
        self.login_window.closeEvent = new_close_event

        forget_password_original_close_event = self.forget_password_window.closeEvent
        def forget_password_new_close_event(event):
            self.forget_password_window = None
            forget_password_original_close_event(event)
        self.forget_password_window.closeEvent = forget_password_new_close_event
        self.forget_password_window.show()

    def show_main(self):
        if self.login_window:
            self.login_window.close()
        if self.register_window:
            self.register_window.close()
        self.main_window = MainWindow(switch_to_profile=self.show_profile, logout=self.show_login)
        self.main_window.show()

    def show_profile(self):
        self.profile_window = ProfileWindow()
        self.profile_window.show()

    def run(self):
        sys.exit(self.app.exec())