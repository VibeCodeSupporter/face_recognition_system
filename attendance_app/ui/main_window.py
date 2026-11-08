"""Main window for the camera preview demo."""
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QFrame, QMainWindow, QScrollArea, QStackedWidget
from recognition.recognition_service import RecognitionService
from registration.registration_service import RegistrationService
from storage.vector_store import FaissVectorStore
from ui.pages.recognition_page import RecognitionPage
from ui.pages.registration_page import RegistrationPage

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Face Attendance · Device Preview")
        self.resize(1200, 760)
        self.setMinimumSize(320, 240)
        self._screen_signal_connected = False
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
        self.page_scroll = QScrollArea(self)
        self.page_scroll.setWidgetResizable(True)
        self.page_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.page_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.page_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.page_scroll.setStyleSheet(
            "QScrollBar:vertical { background: #151d28; width: 24px; "
            "margin: 2px; border-radius: 10px; }"
            "QScrollBar::handle:vertical { background: #52647a; "
            "min-height: 56px; border: 4px solid #151d28; border-radius: 9px; }"
            "QScrollBar::handle:vertical:hover { background: #7890aa; }"
            "QScrollBar::handle:vertical:pressed { background: #3978f6; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { "
            "background: transparent; }"
        )
        self.page_scroll.setWidget(self.pages)
        self.setCentralWidget(self.page_scroll)
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
        if not self._screen_signal_connected and self.windowHandle() is not None:
            self.windowHandle().screenChanged.connect(self._adapt_to_screen)
            self._screen_signal_connected = True
            QTimer.singleShot(0, lambda: self._fit_to_screen(self.screen()))
        if self.pages.currentWidget() is self.recognition_page:
            self.recognition_page.start_camera()

    def _fit_to_screen(self, screen) -> None:
        """Center the initial window within the active screen work area."""
        if screen is None:
            return
        area = screen.availableGeometry()
        minimum_width = min(480, area.width())
        minimum_height = min(320, area.height())
        self.setMinimumSize(minimum_width, minimum_height)
        width = min(1360, max(minimum_width, int(area.width() * 0.94)))
        height = min(820, max(minimum_height, int(area.height() * 0.92)))
        self.setGeometry(
            area.x() + (area.width() - width) // 2,
            area.y() + (area.height() - height) // 2,
            width,
            height,
        )

    def _adapt_to_screen(self, screen) -> None:
        """Keep the current window position when it fits the newly selected screen."""
        if screen is None:
            return
        area = screen.availableGeometry()
        minimum_width = min(480, area.width())
        minimum_height = min(320, area.height())
        self.setMinimumSize(minimum_width, minimum_height)
        current = self.geometry()
        width = min(current.width(), area.width())
        height = min(current.height(), area.height())
        x = min(max(current.x(), area.left()), area.right() - width + 1)
        y = min(max(current.y(), area.top()), area.bottom() - height + 1)
        if (x, y, width, height) != (
            current.x(), current.y(), current.width(), current.height()
        ):
            self.setGeometry(x, y, width, height)

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
