import os
from PySide6.QtCore import Qt, QUrl, QTime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QLabel
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget


class VideoPlayerWidget(QWidget):
    """带播放控制条的视频播放器组件"""
    def __init__(self, video_path: str, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.video_widget = QVideoWidget(self)
        self.player.setVideoOutput(self.video_widget)
        self.player.setSource(QUrl.fromLocalFile(video_path))

        layout = QVBoxLayout(self)
        layout.addWidget(self.video_widget)

        # ===== 控制条 =====
        control_layout = QHBoxLayout()

        # 播放/暂停
        self.btn_play = QPushButton("▶")
        self.btn_play.clicked.connect(self.toggle_play)
        control_layout.addWidget(self.btn_play)

        # 时间显示
        self.label_time = QLabel("00:00 / 00:00")
        control_layout.addWidget(self.label_time)

        # 进度条
        self.slider_progress = QSlider(Qt.Horizontal)
        self.slider_progress.setRange(0, 0)
        self.slider_progress.sliderMoved.connect(self.seek_video)
        control_layout.addWidget(self.slider_progress)

        # 音量
        self.slider_volume = QSlider(Qt.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(50)
        self.slider_volume.valueChanged.connect(lambda value: self.audio_output.setVolume(value / 100))
        control_layout.addWidget(QLabel("音量"))
        control_layout.addWidget(self.slider_volume)

        layout.addLayout(control_layout)

        # 信号绑定
        self.player.durationChanged.connect(self.update_duration)
        self.player.positionChanged.connect(self.update_position)

        # self.player.play()

    # ===== 控制方法 =====
    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.btn_play.setText("▶")
        else:
            self.player.play()
            self.btn_play.setText("⏸")

    def seek_video(self, position):
        self.player.setPosition(position)

    def update_duration(self, duration):
        self.slider_progress.setRange(0, duration)
        self.update_time_label(self.player.position(), duration)

    def update_position(self, position):
        self.slider_progress.blockSignals(True)
        self.slider_progress.setValue(position)
        self.slider_progress.blockSignals(False)
        self.update_time_label(position, self.player.duration())

    def update_time_label(self, pos, dur):
        def ms_to_str(ms):
            t = QTime(0, 0, 0)
            t = t.addMSecs(ms)
            return t.toString("mm:ss")
        self.label_time.setText(f"{ms_to_str(pos)} / {ms_to_str(dur)}")
