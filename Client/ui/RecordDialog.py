import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QScrollArea, QVBoxLayout, QPushButton
from PySide6.QtCore import QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget

from ui.VedioPlayerWidget import VideoPlayerWidget

class RecordDialog(QDialog):
    def __init__(self, detail, parent=None):
        super().__init__(parent)
        self.setWindowTitle("详情")

        # ============ 总布局 ============
        main_layout = QVBoxLayout(self)

        # ============ 文本信息部分 ============
        text_label = QLabel(
            f"类型: {detail.get('type', '')}\n"
            f"提示词: {detail.get('prompt', '')}\n"
            f"参数: {detail.get('parameters', '')}\n"
        )
        text_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                line-height: 1.4;
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 6px;
                background-color: #fafafa;
            }
        """)

        text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        main_layout.addWidget(text_label)

        path = detail.get("local_path", "")
        # ============ 图片部分（允许原尺寸） ============
        if detail.get("type", "") in ["t2i", "i2i"]:     
            if path and os.path.isfile(path):
                pix = QPixmap(path)
            else:
                pix = QPixmap(400, 400)
                pix.fill(Qt.lightGray)
            img_label = QLabel()
            img_label.setPixmap(pix)
            img_label.setAlignment(Qt.AlignCenter)

            # 如果图太大，使用 QScrollArea 避免窗口超屏
            scroll = QScrollArea()
            scroll.setWidget(img_label)
            scroll.setWidgetResizable(True)
            scroll.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(scroll)

        elif detail.get("type", "") in ["t2v", "i2v"]:
            video_player = VideoPlayerWidget(path)
            main_layout.addWidget(video_player, stretch=1)

        # ============ 关闭按钮 ============
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        main_layout.addWidget(close_btn)

        # self.resize(pix.width() + 80, pix.height() + 150)
        self.resize(600, 600)
        # 非模态方式打开
        self.setModal(False)

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    # 调用
    dlg = RecordDialog({
        "type": "文生图",
        "prompt": "一只站在月光下的狐狸",
        "parameters": {"size": "512x512", "model": "SDXL"},
        "local_path": "test.png"
    })
    dlg.show()
    sys.exit(app.exec())