from PyQt5.QtCore import QObject, pyqtSignal


class Signals(QObject):
    status = pyqtSignal(list)
    message = pyqtSignal(dict)
    typing = pyqtSignal(str)
