"""Create and run the PyQt device application."""
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Face Attendance Device")
    window = MainWindow()
    window.show()
    return app.exec()
