from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from moove_recovery import __version__
from moove_recovery.application.service import GymService
from moove_recovery.domain.models import Actor, Role
from moove_recovery.ui.backups_page import BackupsPage
from moove_recovery.ui.calendar_page import CalendarPage
from moove_recovery.ui.dashboard_page import DashboardPage
from moove_recovery.ui.management_pages import PricesPage, UsersPage
from moove_recovery.ui.students_page import StudentsPage


class MainWindow(QMainWindow):
    def __init__(self, service: GymService, actor: Actor) -> None:
        super().__init__()
        self.service = service
        self.actor = actor
        self.last_business_day = service.today()
        self.setWindowTitle("MOOVE RECOVERY · Gestión de cuotas")
        self.setMinimumSize(1024, 650)
        self.resize(1220, 760)
        self.setFont(QFont("Segoe UI", 9))

        shell = QWidget()
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        self.setCentralWidget(shell)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(218)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(13, 18, 13, 13)
        side_layout.setSpacing(5)
        brand = QLabel("MOOVE RECOVERY")
        brand.setObjectName("brand")
        side_layout.addWidget(brand)
        side_layout.addWidget(QLabel("Gestión de cuotas"))
        side_layout.addSpacing(22)
        side_layout.addWidget(self._side_label("OPERACIÓN"))
        self.nav_buttons: dict[str, QPushButton] = {}
        self.page_widgets: dict[str, QWidget] = {}
        side_layout.addWidget(self._nav_button("Alumnos", "Alumnos"))
        if actor.role == Role.OWNER:
            side_layout.addSpacing(15)
            side_layout.addWidget(self._side_label("GESTIÓN"))
            side_layout.addWidget(self._nav_button("Panel", "Panel"))
            side_layout.addWidget(self._nav_button("Calendario", "Calendario"))
            side_layout.addWidget(self._side_label("ADMINISTRACIÓN"))
            side_layout.addWidget(self._nav_button("Planes y precios", "Planes y precios"))
            side_layout.addWidget(self._nav_button("Respaldos", "Respaldos"))
            side_layout.addWidget(self._nav_button("Usuarios", "Usuarios"))
        side_layout.addStretch(1)
        user = QLabel(f"{actor.full_name}\n{'Dueño' if actor.role == Role.OWNER else 'Empleado'}")
        user.setObjectName("userInfo")
        user.setWordWrap(True)
        side_layout.addWidget(user)
        self.creator_button = QPushButton("Creado por DAX")
        self.creator_button.setObjectName("creatorCredit")
        self.creator_button.setAccessibleName("Creado por DAX. Abrir Instagram")
        self.creator_button.setToolTip("Abrir Instagram de DAX")
        dax_logo = Path(__file__).resolve().parents[3] / "assets" / "branding" / "dax.png"
        self.creator_button.setIcon(QIcon(str(dax_logo)))
        self.creator_button.setIconSize(QSize(34, 34))
        self.creator_button.clicked.connect(self.open_creator_instagram)
        side_layout.addWidget(self.creator_button)
        version = QLabel(f"Versión {__version__}")
        version.setObjectName("muted")
        side_layout.addWidget(version)
        shell_layout.addWidget(sidebar)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        topbar = QFrame()
        topbar.setObjectName("topbar")
        top_layout = QHBoxLayout(topbar)
        top_layout.setContentsMargins(22, 0, 22, 0)
        top_layout.addWidget(QLabel("Centro de gestión"))
        top_layout.addStretch(1)
        top_layout.addWidget(QLabel(f"Sesión: {actor.username}"))
        right_layout.addWidget(topbar)
        self.pages = QStackedWidget()
        self.students_page = StudentsPage(service, actor)
        self.students_page.changed.connect(self.refresh_pages)
        self.pages.addWidget(self.students_page)
        self.page_widgets["Alumnos"] = self.students_page
        if actor.role == Role.OWNER:
            self.dashboard_page = DashboardPage(service, actor)
            self.calendar_page = CalendarPage(service, actor)
            self.backups_page = BackupsPage(service, actor)
            self.backups_page.restored.connect(self.close)
            self.prices_page = PricesPage(service, actor)
            self.users_page = UsersPage(service, actor)
            self.page_widgets["Panel"] = self.dashboard_page
            self.page_widgets["Calendario"] = self.calendar_page
            self.page_widgets["Planes y precios"] = self.prices_page
            self.page_widgets["Respaldos"] = self.backups_page
            self.page_widgets["Usuarios"] = self.users_page
            self.pages.addWidget(self.dashboard_page)
            self.pages.addWidget(self.calendar_page)
            self.pages.addWidget(self.prices_page)
            self.pages.addWidget(self.backups_page)
            self.pages.addWidget(self.users_page)
        right_layout.addWidget(self.pages, 1)
        shell_layout.addWidget(right, 1)
        self.setStyleSheet(APP_STYLES)
        self._select_page("Alumnos")

        self.day_timer = QTimer(self)
        self.day_timer.setInterval(60_000)
        self.day_timer.timeout.connect(self.refresh_if_day_changed)
        self.day_timer.start()

    @staticmethod
    def _side_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sideLabel")
        return label

    def _nav_button(self, text: str, page: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("navButton")
        button.setCheckable(True)
        button.clicked.connect(lambda: self._select_page(page))
        self.nav_buttons[page] = button
        return button

    def _select_page(self, page: str) -> None:
        self.pages.setCurrentWidget(self.page_widgets[page])
        for name, button in self.nav_buttons.items():
            button.setChecked(name == page)
        if page == "Alumnos":
            self.students_page.refresh()
        elif page == "Panel" and hasattr(self, "dashboard_page"):
            self.dashboard_page.refresh()
        elif page == "Calendario" and hasattr(self, "calendar_page"):
            self.calendar_page.refresh()
        elif page == "Respaldos" and hasattr(self, "backups_page"):
            self.backups_page.refresh()
        elif page == "Planes y precios" and hasattr(self, "prices_page"):
            self.pages.removeWidget(self.prices_page)
            self.prices_page = PricesPage(self.service, self.actor)
            self.page_widgets["Planes y precios"] = self.prices_page
            self.pages.addWidget(self.prices_page)
            self.pages.setCurrentWidget(self.prices_page)
        elif page == "Usuarios" and hasattr(self, "users_page"):
            self.pages.removeWidget(self.users_page)
            self.users_page = UsersPage(self.service, self.actor)
            self.page_widgets["Usuarios"] = self.users_page
            self.pages.addWidget(self.users_page)
            self.pages.setCurrentWidget(self.users_page)

    def refresh_pages(self) -> None:
        self.students_page.refresh()
        if hasattr(self, "dashboard_page"):
            self.dashboard_page.refresh()

    @staticmethod
    def open_creator_instagram() -> None:
        QDesktopServices.openUrl(QUrl("https://www.instagram.com/daxadorno/"))

    def refresh_if_day_changed(self) -> None:
        today = self.service.today()
        if today == self.last_business_day:
            return
        self.last_business_day = today
        result = self.service.generate_missing_dues()
        self.students_page.refresh()
        if result["without_price"]:
            QMessageBox.warning(
                self,
                "Falta configurar precios",
                f"Hay {result['without_price']} cuota(s) que no se generaron porque falta el precio del plan.",
            )


APP_STYLES = """
QMainWindow, QDialog { background: #ffffff; color: #26322b; }
QWidget { color: #26322b; }
QFrame#sidebar { background: #172f42; color: #edf3f5; }
QLabel#brand { color: #ffffff; font-size: 15px; font-weight: 800; }
QLabel#sideLabel { color: #9aadb8; font-size: 9px; font-weight: 700; padding-left: 7px; }
QFrame#sidebar QLabel { background: transparent; color: #e8eff1; }
QFrame#sidebar QLabel#muted { color: #b7c4ca; }
QFrame#topbar { background: #ffffff; border-bottom: 1px solid #e7ece8; min-height: 48px; }
QFrame#topbar QLabel { color: #65736a; font-size: 10px; }
QPushButton#navButton { background: transparent; color: #d4e0e3; border: 0; border-radius: 4px; padding: 8px 9px; text-align: left; }
QPushButton#navButton:hover { background: #254357; }
QPushButton#navButton:checked { background: #31546a; color: #ffffff; font-weight: 700; }
QLabel#userInfo { border-top: 1px solid #385063; padding: 11px 5px 5px; color: #ffffff; font-weight: 600; }
QLabel#muted { color: #85918a; font-size: 10px; }
QFrame#sidebar QLabel#muted { color: #b7c4ca; }
QPushButton#creatorCredit { background: transparent; border: 0; color: #e8eff1; padding: 6px 3px; text-align: left; }
QPushButton#creatorCredit:hover { background: #254357; border-radius: 3px; }
QLabel#pageTitle { color: #24332b; font-size: 20px; font-weight: 700; }
QLabel#detailTitle { color: #24332b; font-size: 15px; font-weight: 700; }
QLabel#sectionTitle { color: #31433a; font-size: 12px; font-weight: 700; }
QLabel#kpiValue { color: #19384a; font-size: 16px; font-weight: 700; }
QFrame#detailPanel { background: #fbfcfb; border: 1px solid #e5eae6; border-radius: 5px; }
QLineEdit, QComboBox, QDateEdit, QTextEdit, QListWidget { background: #ffffff; border: 1px solid #dfe6e1; border-radius: 4px; padding: 6px 8px; selection-background-color: #d9ebe0; }
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus { border: 1px solid #5a9876; }
QPushButton#primaryButton { background: #276b4c; color: #ffffff; border: 1px solid #276b4c; border-radius: 4px; padding: 7px 11px; font-weight: 600; }
QPushButton#primaryButton:hover { background: #1f583e; }
QPushButton#primaryButton:disabled { background: #a7b9ae; border-color: #a7b9ae; }
QPushButton#secondaryButton { background: #ffffff; color: #405147; border: 1px solid #dce4de; border-radius: 4px; padding: 6px 9px; }
QPushButton#secondaryButton:hover { background: #f3f7f4; }
QPushButton#textButton { background: transparent; border: 0; color: #66736b; padding: 5px; text-align: left; }
QPushButton#textButton:hover { color: #a24e42; }
QTableWidget { border: 1px solid #e4eae5; gridline-color: #edf0ed; selection-background-color: #e4efe7; selection-color: #27352d; alternate-background-color: #fafbfa; }
QHeaderView::section { background: #f5f7f5; border: 0; border-bottom: 1px solid #e5eae6; padding: 8px 6px; color: #77827b; font-size: 9px; font-weight: 700; }
QTableWidget::item { padding: 5px; }
QStatusBar { background: #ffffff; color: #78837c; border-top: 1px solid #e7ece8; }
QLabel#dialogTitle { color: #19384a; font-size: 17px; font-weight: 800; padding-bottom: 3px; }
QLabel#paymentTotal { color: #276b4c; font-size: 15px; font-weight: 700; }
QDialogButtonBox QPushButton { min-width: 82px; padding: 6px 9px; }
"""
