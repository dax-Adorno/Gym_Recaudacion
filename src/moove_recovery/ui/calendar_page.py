from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from moove_recovery.application.service import GymService
from moove_recovery.domain.errors import DomainError
from moove_recovery.domain.models import Actor
from moove_recovery.ui.common import format_money, make_label

MONTHS = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
EVENT_CATEGORIES = {
    "Vencimientos": "vencimientos",
    "Cobros": "cobros",
    "Movimientos": "movimientos",
}


class CalendarPage(QWidget):
    def __init__(self, service: GymService, actor: Actor) -> None:
        super().__init__()
        self.service = service
        self.actor = actor
        self.selected_date = service.today()
        self.category = "vencimientos"
        self.events_by_date: dict[date, list[dict[str, object]]] = {}
        self.day_buttons: dict[date, QPushButton] = {}
        self.day_button_list: list[QPushButton] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(14)
        layout.addWidget(make_label("Calendario", "pageTitle"))

        toolbar = QHBoxLayout()
        self.previous_month = QPushButton("‹")
        self.previous_month.setAccessibleName("Mes anterior")
        self.previous_month.setToolTip("Mes anterior")
        self.previous_month.clicked.connect(lambda: self.shift_month(-1))
        self.month_title = make_label("", "sectionTitle")
        self.month_title.setMinimumWidth(150)
        self.month_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.today_button = QPushButton("Hoy")
        self.today_button.setObjectName("secondaryButton")
        self.today_button.clicked.connect(self.go_to_today)
        self.next_month = QPushButton("›")
        self.next_month.setAccessibleName("Mes siguiente")
        self.next_month.setToolTip("Mes siguiente")
        self.next_month.clicked.connect(lambda: self.shift_month(1))
        toolbar.addWidget(self.previous_month)
        toolbar.addWidget(self.month_title)
        toolbar.addWidget(self.next_month)
        toolbar.addWidget(self.today_button)
        toolbar.addStretch(1)

        self.category_group = QButtonGroup(self)
        self.category_group.setExclusive(True)
        self.category_buttons: dict[str, QPushButton] = {}
        category_tooltips = {
            "vencimientos": "Ver vencimientos de cuotas y su estado",
            "cobros": "Ver cobros registrados, incluidos los anulados",
            "movimientos": "Ver altas, bajas y reactivaciones de alumnos",
        }
        for label, category in EVENT_CATEGORIES.items():
            button = QPushButton(label)
            button.setObjectName("calendarActionButton")
            button.setToolTip(category_tooltips[category])
            button.setStyleSheet(
                "QPushButton#calendarActionButton { background: #ffffff; color: #405147; "
                "border: 1px solid #dce4de; border-radius: 4px; padding: 6px 9px; }"
                "QPushButton#calendarActionButton:checked { background: #254e3d; "
                "color: #ffffff; border-color: #254e3d; font-weight: 600; }"
            )
            button.setCheckable(True)
            button.clicked.connect(lambda checked, value=category: self.select_category(value))
            self.category_group.addButton(button)
            self.category_buttons[category] = button
            toolbar.addWidget(button)
        self.category_buttons[self.category].setChecked(True)
        layout.addLayout(toolbar)

        self.calendar_grid = QGridLayout()
        self.calendar_grid.setSpacing(4)
        for column, weekday in enumerate(("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")):
            label = QLabel(weekday)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setObjectName("muted")
            self.calendar_grid.addWidget(label, 0, column)
        self.day_group = QButtonGroup(self)
        self.day_group.setExclusive(True)
        for index in range(42):
            button = QPushButton()
            button.setObjectName("calendarDay")
            button.setStyleSheet(
                "QPushButton#calendarDay { text-align: left; padding: 5px; "
                "background: #f6f8f6; border: 1px solid #dbe2dd; border-radius: 3px; }"
                "QPushButton#calendarDay:checked { background: #e3f1e9; "
                "border: 2px solid #3a7959; }"
                "QPushButton#calendarDay:disabled { color: #a0a8a3; }"
            )
            button.setCheckable(True)
            button.setMinimumHeight(58)
            button.clicked.connect(lambda checked, item=index: self.select_day(item))
            self.day_group.addButton(button)
            self.day_button_list.append(button)
            self.calendar_grid.addWidget(button, index // 7 + 1, index % 7)
        layout.addLayout(self.calendar_grid)

        self.selected_day_label = make_label("", "sectionTitle")
        layout.addWidget(self.selected_day_label)
        self.empty_events = make_label("Sin eventos para esta fecha.", "muted")
        layout.addWidget(self.empty_events)
        self.events_table = QTableWidget(0, 3)
        self.events_table.setHorizontalHeaderLabels(["ALUMNO / CONCEPTO", "DETALLE", "IMPORTE"])
        self.events_table.verticalHeader().setVisible(False)
        self.events_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.events_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.events_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.events_table, 1)
        self.refresh()

    def refresh(self) -> None:
        first = self.selected_date.replace(day=1)
        grid_start = first - timedelta(days=first.weekday())
        grid_end = grid_start + timedelta(days=41)
        self.month_title.setText(f"{MONTHS[first.month - 1].capitalize()} {first.year}")
        try:
            events = self.service.list_calendar_events(
                self.actor, grid_start, grid_end, self.category
            )
        except DomainError:
            events = []
        self.events_by_date = {}
        self.day_buttons.clear()
        for event in events:
            event_date = event["date"]
            if isinstance(event_date, date):
                self.events_by_date.setdefault(event_date, []).append(event)
        for index in range(42):
            day = grid_start + timedelta(days=index)
            button = self.day_button_list[index]
            self.day_buttons[day] = button
            day_events = self.events_by_date.get(day, [])
            event_count = len(day_events)
            event_label = "evento" if event_count == 1 else "eventos"
            button.setText(
                f"{day.day}\n{event_count} {event_label}" if event_count else str(day.day)
            )
            button.setAccessibleName(f"{day.day} de {MONTHS[day.month - 1]}, {event_count} eventos")
            button.setToolTip("\n".join(str(event["title"]) for event in day_events))
            button.setProperty("outsideMonth", day.month != first.month)
            button.setChecked(day == self.selected_date)
            button.setEnabled(day.month == first.month)
        self.select_day_events()

    def select_category(self, category: str) -> None:
        if category not in EVENT_CATEGORIES.values():
            return
        self.category = category
        self.refresh()

    def select_day(self, index: int) -> None:
        first = self.selected_date.replace(day=1)
        grid_start = first - timedelta(days=first.weekday())
        self.selected_date = grid_start + timedelta(days=index)
        self.refresh()

    def select_day_events(self) -> None:
        self.selected_day_label.setText(
            f"{self.selected_date.day} de {MONTHS[self.selected_date.month - 1]}"
        )
        events = self.events_by_date.get(self.selected_date, [])
        self.empty_events.setVisible(not events)
        self.events_table.setRowCount(len(events))
        for row, event in enumerate(events):
            amount = event["amount_cents"]
            values = (
                str(event["title"]),
                str(event["details"]),
                format_money(int(amount)) if isinstance(amount, int) else "—",
            )
            for column, value in enumerate(values):
                self.events_table.setItem(row, column, QTableWidgetItem(value))

    def shift_month(self, delta: int) -> None:
        month_index = self.selected_date.year * 12 + self.selected_date.month - 1 + delta
        year, month_zero = divmod(month_index, 12)
        self.selected_date = date(year, month_zero + 1, 1)
        self.refresh()

    def go_to_today(self) -> None:
        self.selected_date = self.service.today()
        self.refresh()
