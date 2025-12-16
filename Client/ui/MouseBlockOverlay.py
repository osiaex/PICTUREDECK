from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QMovie


class MouseBlockOverlay(QWidget):
    """
    激活态：
        - 显示
        - Z-order 置顶
        - 拦截所有鼠标事件

    非激活态：
        - 隐藏
        - 不参与事件
    """

    def __init__(self, parent: QWidget, use_gif: bool = True):
        super().__init__(parent)

        self._active = False
        self._use_gif = use_gif

        # —— 外观 —— #
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 80);")

        # —— 初始 geometry —— #
        self.setGeometry(parent.rect())

        # —— UI —— #
        self._init_ui()

        # 初始状态
        self.setActive(False)

    # =========================
    # UI 构建
    # =========================
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 上方弹性
        layout.addStretch(1)

        # 可选 GIF
        if self._use_gif:
            self.loading_label = QLabel(self)
            self.loading_label.setAlignment(Qt.AlignCenter)
            self.loading_label.setStyleSheet("background: transparent;")

            self.loading_movie = QMovie("ui/assets/loading.gif")
            self.loading_movie.setScaledSize(QSize(48, 48))
            self.loading_label.setMovie(self.loading_movie)

            layout.addWidget(self.loading_label)
        else:
            self.loading_label = None
            self.loading_movie = None

        # 文本（严格居中）
        self.text_label = QLabel("", self)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet(
            "background: transparent; color: #555; font-size: 15px;"
        )

        layout.addWidget(self.text_label)

        # 下方弹性
        layout.addStretch(1)

    # =========================
    # 对外唯一接口
    # =========================
    def setActive(self, active: bool, text: str = ""):
        self._active = active

        if active:
            self.text_label.setText(text)
            self.raise_()
            self.show()
            if self.loading_movie:
                self.loading_movie.start()
        else:
            if self.loading_movie:
                self.loading_movie.stop()
            self.hide()
            self.lower()

    # =========================
    # 父控件 resize 同步
    # =========================
    def syncGeometry(self):
        if self.parent():
            self.setGeometry(self.parent().rect())
                        
        if not self.loading_movie:
            return

        side = min(self.width(), self.height())
        side = int(side * 0.8) 

        if side > 0:
            self.loading_movie.setScaledSize(QSize(side, side))

    # =========================
    # 事件拦截
    # =========================
    def mousePressEvent(self, event):
        if self._active:
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        if self._active:
            event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if self._active:
            event.accept()
        else:
            event.ignore()

