from PySide6.QtCore import QObject, Signal

class GlobalSignals(QObject):
    unauthorized = Signal()

global_signals = GlobalSignals()
