from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import QDesktopServices, QFont, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QToolButton,
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
    logout_requested = Signal()

    def __init__(self, service: GymService, actor: Actor) -> None:
        super().__init__()
        self.service = service
        self.actor = actor
        self.last_business_day = service.today()
        self.setWindowTitle("MOOVE RECOVERY · Gestión de cuotas")
        self.setMinimumSize(1024, 650)
        self.resize(1220, 760)
        self.setFont(QFont("Segoe UI", 10))

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
        self.nav_buttons: dict[str, QPushButton] = {}
        self.page_widgets: dict[str, QWidget] = {}
        self.nav_sections: dict[str, tuple[QToolButton, QWidget, QGraphicsOpacityEffect]] = {}
        self.section_animations: dict[str, QParallelAnimationGroup] = {}
        self.page_sections: dict[str, str] = {}
        self._add_nav_section(side_layout, "OPERACIÓN", [("Alumnos", "Alumnos")])
        if actor.role == Role.OWNER:
            self._add_nav_section(
                side_layout,
                "GESTIÓN",
                [("Panel", "Panel"), ("Calendario", "Calendario")],
            )
            self._add_nav_section(
                side_layout,
                "ADMINISTRACIÓN",
                [
                    ("Planes y precios", "Planes y precios"),
                    ("Respaldos", "Respaldos"),
                    ("Usuarios", "Usuarios"),
                ],
            )
        side_layout.addStretch(3)
        legend_index = side_layout.count()
        side_layout.addStretch(1)
        user = QLabel(f"{actor.full_name}\n{'Dueño' if actor.role == Role.OWNER else 'Empleado'}")
        user.setObjectName("userInfo")
        user.setWordWrap(True)
        side_layout.addWidget(user)
        self.logout_button = QPushButton("Cerrar sesión")
        self.logout_button.setObjectName("creatorCredit")
        self.logout_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        self.logout_button.setToolTip("Cerrar esta sesión e iniciar con otro usuario")
        self.logout_button.clicked.connect(lambda: self.logout_requested.emit())
        side_layout.addWidget(self.logout_button)
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
        side_layout.insertWidget(legend_index, self.students_page.status_legend)
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

    def _add_nav_section(
        self,
        layout: QVBoxLayout,
        title: str,
        pages: list[tuple[str, str]],
    ) -> None:
        if title != "OPERACIÓN":
            layout.addSpacing(9)
        toggle = QToolButton()
        toggle.setObjectName("sectionButton")
        toggle.setText(title)
        toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toggle.setArrowType(Qt.ArrowType.RightArrow)
        toggle.setCheckable(True)
        toggle.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        toggle.setMinimumHeight(32)

        content = QWidget()
        content.setObjectName("sectionContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(3)
        for label, page in pages:
            content_layout.addWidget(self._nav_button(label, page))
            self.page_sections[page] = title

        opacity = QGraphicsOpacityEffect(content)
        opacity.setOpacity(0)
        content.setGraphicsEffect(opacity)
        content.setMaximumHeight(0)
        toggle.clicked.connect(
            lambda _checked=False, section=title: self._toggle_nav_section(section)
        )
        layout.addWidget(toggle)
        layout.addWidget(content)
        self.nav_sections[title] = (toggle, content, opacity)

    def _toggle_nav_section(self, title: str) -> None:
        toggle, _, _ = self.nav_sections[title]
        self._set_nav_section_expanded(title, toggle.isChecked())

    def _set_nav_section_expanded(self, title: str, expanded: bool) -> None:
        toggle, content, opacity = self.nav_sections[title]
        toggle.setChecked(expanded)
        toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        if expanded:
            for other_title, (other_toggle, _, _) in self.nav_sections.items():
                if other_title != title and other_toggle.isChecked():
                    self._set_nav_section_expanded(other_title, False)

        previous = self.section_animations.get(title)
        if previous is not None:
            previous.stop()
            previous.deleteLater()

        start_height = min(content.maximumHeight(), content.sizeHint().height())
        end_height = content.sizeHint().height() if expanded else 0
        animation = QParallelAnimationGroup(self)
        height_animation = QPropertyAnimation(content, b"maximumHeight", animation)
        height_animation.setDuration(220)
        height_animation.setStartValue(start_height)
        height_animation.setEndValue(end_height)
        height_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        opacity_animation = QPropertyAnimation(opacity, b"opacity", animation)
        opacity_animation.setDuration(180)
        opacity_animation.setStartValue(opacity.opacity())
        opacity_animation.setEndValue(1.0 if expanded else 0.0)
        opacity_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        animation.addAnimation(height_animation)
        animation.addAnimation(opacity_animation)
        animation.finished.connect(
            lambda section=title, pane=content, opened=expanded: self._finish_section_animation(
                section, pane, opened
            )
        )
        self.section_animations[title] = animation
        animation.start()

    def _finish_section_animation(self, title: str, content: QWidget, expanded: bool) -> None:
        content.setMaximumHeight(content.sizeHint().height() if expanded else 0)
        animation = self.section_animations.pop(title, None)
        if animation is not None:
            animation.deleteLater()

    def _nav_button(self, text: str, page: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("navButton")
        button.setCheckable(True)
        button.clicked.connect(lambda: self._select_page(page))
        self.nav_buttons[page] = button
        return button

    def _select_page(self, page: str) -> None:
        self.pages.setCurrentWidget(self.page_widgets[page])
        self._set_nav_section_expanded(self.page_sections[page], True)
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
QLabel#brand { color: #ffffff; font-size: 16px; font-weight: 800; }
QLabel#sideLabel { color: #9aadb8; font-size: 10px; font-weight: 700; padding-left: 7px; }
QFrame#sidebar QLabel { background: transparent; color: #e8eff1; }
QFrame#sidebar QLabel#muted { color: #b7c4ca; }
QToolButton#sectionButton { background: transparent; color: #e8eff1; border: 0; padding: 7px 4px; text-align: left; font-weight: 700; }
QToolButton#sectionButton:hover, QToolButton#sectionButton:checked { color: #ffffff; }
QWidget#sectionContent { background: transparent; }
QFrame#topbar { background: #ffffff; border-bottom: 1px solid #e7ece8; min-height: 48px; }
QFrame#topbar QLabel { color: #65736a; font-size: 11px; }
QPushButton#navButton { background: transparent; color: #d4e0e3; border: 0; border-radius: 4px; padding: 8px 9px; text-align: left; }
QPushButton#navButton:hover { background: #254357; }
QPushButton#navButton:checked { background: #31546a; color: #ffffff; font-weight: 700; }
QLabel#userInfo { border-top: 1px solid #385063; padding: 11px 5px 5px; color: #ffffff; font-weight: 600; }
QLabel#muted { color: #85918a; font-size: 11px; }
QFrame#sidebar QLabel#muted { color: #b7c4ca; }
QPushButton#creatorCredit { background: transparent; border: 0; color: #e8eff1; padding: 6px 3px; text-align: left; }
QPushButton#creatorCredit:hover { background: #254357; border-radius: 3px; }
QLabel#pageTitle { color: #24332b; font-size: 21px; font-weight: 700; }
QLabel#detailTitle { color: #24332b; font-size: 16px; font-weight: 700; }
QLabel#sectionTitle { color: #31433a; font-size: 13px; font-weight: 700; }
QLabel#kpiValue { color: #19384a; font-size: 17px; font-weight: 700; }
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
QPushButton#dangerButton { background: #fff7f5; border: 1px solid #c98074; border-radius: 4px; color: #963c2f; padding: 7px 10px; }
QPushButton#dangerButton:hover { background: #f9e5e1; border-color: #963c2f; }
QPushButton#dangerButton:disabled { color: #8d9590; border-color: #dce4de; background: #f5f7f5; }
QTableWidget { border: 1px solid #aab9b0; gridline-color: #b9c7bf; selection-background-color: #e4efe7; selection-color: #27352d; alternate-background-color: #fafbfa; }
QHeaderView::section { background: #edf2ee; border: 0; border-right: 1px solid #aab9b0; border-bottom: 2px solid #94a89c; padding: 8px 6px; color: #4d6054; font-size: 10px; font-weight: 700; }
QHeaderView::section:hover { background: #d5e5db; color: #203a2b; border-right: 2px solid #547461; }
QSplitter#studentsSplitter::handle { background: #c0cdc5; border-left: 1px solid #94a89c; border-right: 1px solid #94a89c; }
QSplitter#studentsSplitter::handle:hover { background: #82a18e; }
QFrame#statusLegend { border-top: 1px solid #b9c7bf; border-bottom: 1px solid #b9c7bf; }
QFrame#sidebar QFrame#statusLegend { border-top: 1px solid #587080; border-bottom: 1px solid #587080; }
QTableWidget::item { padding: 5px; }
QStatusBar { background: #ffffff; color: #78837c; border-top: 1px solid #e7ece8; }
QLabel#dialogTitle { color: #19384a; font-size: 18px; font-weight: 800; padding-bottom: 3px; }
QLabel#paymentTotal { color: #276b4c; font-size: 16px; font-weight: 700; }
QDialogButtonBox QPushButton { min-width: 82px; padding: 6px 9px; }
"""
