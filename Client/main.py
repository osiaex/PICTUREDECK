# This Python file uses the following encoding: utf-8
import sys

from PySide6.QtWidgets import QApplication, QWidget

# Important:
# You need to run the following command to generate the ui_form.py file
#     pyside6-uic form.ui -o ui_form.py, or
#     pyside2-uic form.ui -o ui_form.py

from controllers.main_controller import MainController

# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     widget = ForgotPasswordWindow(lambda :42)
#     widget.show()
#     sys.exit(app.exec())

if __name__ == "__main__":
    controller = MainController()
    controller.run()

