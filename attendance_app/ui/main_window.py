"""Main window for the camera preview demo."""
from PyQt6.QtWidgets import QMainWindow, QStackedWidget
from recognition.recognition_service import RecognitionService
from registration.registration_service import RegistrationService
from storage.vector_store import FaissVectorStore
from ui.pages.recognition_page import RecognitionPage
from ui.pages.registration_page import RegistrationPage

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Face Attendance · Device Preview")
        self.resize(1360, 820)
        self.setMinimumSize(1100, 700)
        self.vector_store = FaissVectorStore()
        self.recognition_page = RecognitionPage(
            RecognitionService(self.vector_store), self
        )
        self.registration_page = RegistrationPage(
            RegistrationService(self.vector_store), self
        )
        self.pages = QStackedWidget(self)
        self.pages.addWidget(self.recognition_page)
        self.pages.addWidget(self.registration_page)
        self.setCentralWidget(self.pages)
        self.recognition_page.register_requested.connect(self.show_registration)
        self.registration_page.back_requested.connect(self.show_recognition)
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #10151d; color: #edf2f7; font-family: Segoe UI, sans-serif; }
            QLabel#pageTitle { font-size: 25px; font-weight: 700; }
            QLabel#mutedText { color: #9aa8b8; font-size: 13px; }
            QLabel#faceGuidance { color: #c6dbff; font-size: 17px; font-weight: 600; }
            QLabel#statusPill { color: #81e6b0; background: #183329; border-radius: 12px; padding: 8px 12px; }
            QLabel#statusPill[state="error"] { color: #feb2b2; background: #452626; }
            QLabel#cameraView { background: #080b10; border: 1px solid #2c3745; border-radius: 12px; }
            QPushButton#primaryButton { background: #3978f6; color: white; border: 0; border-radius: 8px; padding: 12px 20px; font-weight: 600; }
            QPushButton#primaryButton:hover { background: #548bff; }
            QPushButton#primaryButton:disabled { background: #485365; color: #aab3bf; }
        """)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self.pages.currentWidget() is self.recognition_page:
            self.recognition_page.start_camera()

    def show_registration(self) -> None:
        self.recognition_page.stop_camera()
        self.pages.setCurrentWidget(self.registration_page)
        self.registration_page.start_camera()

    def show_recognition(self) -> None:
        self.registration_page.stop_camera()
        self.pages.setCurrentWidget(self.recognition_page)
        self.recognition_page.start_camera()

    def closeEvent(self, event) -> None:
        self.recognition_page.stop_camera()
        self.registration_page.stop_camera()
        super().closeEvent(event)
