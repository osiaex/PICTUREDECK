from PySide6.QtCore import QObject, Signal, Slot, QThread, Qt
from PySide6.QtGui import QImage, QPixmap
import ffmpeg
import tempfile
import os
from services.config import app_config

class FirstFrameWorker(QObject):
    """子线程 Worker：执行 ffmpeg 解码"""
    finished = Signal(QPixmap)
    error = Signal(str)

    def __init__(self, path: str, width: int):
        super().__init__()
        self.path = path
        self.target_width = width

    @Slot()
    def process(self):
        """子线程执行：抽取第一帧"""
        try:
            # 读取视频信息
            probe = ffmpeg.probe(self.path)
            video_stream = next(
                s for s in probe["streams"] if s["codec_type"] == "video"
            )
            w = int(video_stream["width"])
            h = int(video_stream["height"])

            # 抽取第一帧 (raw rgb24)
            out, _ = (
                ffmpeg.input(self.path, ss=0)
                .output("pipe:", vframes=1, format="rawvideo", pix_fmt="rgb24")
                .run(capture_stdout=True, capture_stderr=True)
            )

            # 转换为 QImage
            image = QImage(out, w, h, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(image)
            pixmap = pixmap.scaledToWidth(self.target_width, Qt.SmoothTransformation)
            if app_config.is_debug():
                print(f"[Debug] Extracted first frame size: {pixmap.size()}")
            self.finished.emit(pixmap)

        except ffmpeg.Error as e:
            msg = e.stderr.decode("utf-8", errors="ignore")
            self.error.emit(msg)
        except Exception as e:
            self.error.emit(str(e))


class FirstFrameExtractor(QObject):
    """主线程对象：异步提取视频首帧"""
    frame_extracted = Signal(QPixmap)
    extraction_failed = Signal(str)

    def __init__(self, width=250, parent=None):
        super().__init__(parent)
        self.target_width = width
        self._temp_path = None

    def _run_async(self, video_path: str):
        """启动子线程执行 ffmpeg"""
        if app_config.is_debug():
            print(f"[Debug] Extracting first frame from: {video_path}")
        self.thread = QThread()
        self.worker = FirstFrameWorker(video_path, self.target_width)
        self.worker.moveToThread(self.thread)

        # 信号连接
        self.thread.started.connect(self.worker.process)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)

        # 清理
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.worker.error.connect(self.thread.quit)
        self.worker.error.connect(self.worker.deleteLater)

        self.thread.start()
        if app_config.is_debug():
            print("[Debug] First frame extraction thread started.")

    def load_from_file(self, path: str):
        """文件路径异步处理"""
        self._run_async(path)

    def load_from_bytes(self, data: bytes):
        """内存 bytes：使用临时文件过渡"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
            f.write(data)
            self._temp_path = f.name

        self._run_async(self._temp_path)

    @Slot(QPixmap)
    def _on_finished(self, pixmap: QPixmap):
        """子线程结束后，拿到首帧"""
        self.frame_extracted.emit(pixmap)

        if self._temp_path and os.path.exists(self._temp_path):
            os.remove(self._temp_path)
            self._temp_path = None

    @Slot(str)
    def _on_error(self, msg: str):
        """错误输出"""
        self.extraction_failed.emit(msg)

        if self._temp_path and os.path.exists(self._temp_path):
            os.remove(self._temp_path)
            self._temp_path = None
