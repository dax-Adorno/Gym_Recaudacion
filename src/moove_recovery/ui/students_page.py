from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from moove_recovery.application.service import GymService
from moove_recovery.domain.errors import DomainError
from moove_recovery.domain.models import Actor, Role
from moove_recovery.ui.common import format_money, make_label
from moove_recovery.ui.dialogs import PaymentDialog, StudentDialog

STATE_COLORS = {
    "inactivo": ("#f0f1f1", "#58615c"),
    "deudor": ("#f9e5e1", "#a14436"),
    "por_vencer": ("#fff2d8", "#876314"),
    "pendiente": ("#f3f4f2", "#647069"),
    "al_dia": ("#e6f2e9", "#34734e"),
    "sin_cuota": ("#f7eada", "#89612a"),
}


class StudentsPage(QWidget):
    changed = Signal()

    def __init__(self, service: GymService, actor: Actor) -> None:
        super().__init__()
        self.service = service
        self.actor = actor
        self.students: dict[int, dict[str, object]] = {}
        self.selected_id: int | None = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 19, 22, 18)
        root.setSpacing(12)
        heading = QHBoxLayout()
        title_stack = QVBoxLayout()
        title = make_label("Alumnos", "pageTitle")
        subtitle = make_label("Gestión de cuotas y cobranzas", "muted")
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)
        heading.addLayout(title_stack)
        heading.addStretch(1)
        self.add_button = QPushButton("＋  Nuevo alumno")
        self.add_button.setObjectName("primaryButton")
        self.add_button.clicked.connect(self.add_student)
        heading.addWidget(self.add_button)
        root.addLayout(heading)

        tools = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setClearButtonEnabled(True)
        self.search.setPlaceholderText("Buscar por nombre, apellido o DNI")
        self.search.textChanged.connect(self.refresh)
        tools.addWidget(self.search, 1)
        self.filter = QComboBox()
        self.filter.addItems(
            ["Todos", "Al día", "Próximos a vencer", "Deudores", "Inactivos", "Pendientes"]
        )
        self.filter.currentTextChanged.connect(self.refresh)
        tools.addWidget(self.filter)
        clear = QPushButton("Limpiar")
        clear.setObjectName("secondaryButton")
        clear.clicked.connect(self.clear_filters)
        tools.addWidget(clear)
        root.addLayout(tools)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["ALUMNO", "DNI", "ACTIVIDAD", "PLAN", "ESTADO", "CUOTA ACTUAL"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 170)
        self.table.setColumnWidth(1, 95)
        self.table.setColumnWidth(2, 105)
        self.table.setColumnWidth(3, 75)
        self.table.setColumnWidth(4, 120)
        self.table.itemSelectionChanged.connect(self.show_selected)
        splitter.addWidget(self.table)

        self.detail = QFrame()
        self.detail.setObjectName("detailPanel")
        self.detail.setMinimumWidth(280)
        self.detail.setMaximumWidth(390)
        details_layout = QVBoxLayout(self.detail)
        details_layout.setContentsMargins(16, 15, 16, 15)
        details_layout.setSpacing(9)
        self.detail_name = make_label("Selecciona un alumno", "detailTitle")
        self.detail_state = make_label("", "muted")
        details_layout.addWidget(self.detail_name)
        details_layout.addWidget(self.detail_state)
        self.detail_form = QFormLayout()
        self.detail_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.name_value = make_label("—")
        self.dni_value = make_label("—")
        self.phone_value = make_label("—")
        self.activity_value = make_label("—")
        self.plan_value = make_label("—")
        self.enrolled_value = make_label("—")
        self.detail_form.addRow("Nombre", self.name_value)
        self.detail_form.addRow("DNI", self.dni_value)
        self.detail_form.addRow("Teléfono", self.phone_value)
        self.detail_form.addRow("Actividad", self.activity_value)
        self.detail_form.addRow("Plan", self.plan_value)
        self.detail_form.addRow("Alta", self.enrolled_value)
        details_layout.addLayout(self.detail_form)
        self.detail_tabs = QTabWidget()
        fee_page = QWidget()
        fee_layout = QVBoxLayout(fee_page)
        fee_layout.setContentsMargins(0, 5, 0, 0)
        self.fee_table = QTableWidget(0, 3)
        self.fee_table.setHorizontalHeaderLabels(["PERÍODO", "VENCE", "SALDO"])
        self.fee_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.fee_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.fee_table.verticalHeader().setVisible(False)
        self.fee_table.horizontalHeader().setStretchLastSection(True)
        fee_layout.addWidget(self.fee_table)
        history_page = QWidget()
        history_layout = QVBoxLayout(history_page)
        history_layout.setContentsMargins(0, 5, 0, 0)
        self.history_table = QTableWidget(0, 4)
        self.history_table.setHorizontalHeaderLabels(["FECHA", "MOVIMIENTO", "DETALLE", "IMPORTE"])
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        history_layout.addWidget(self.history_table)
        self.detail_tabs.addTab(fee_page, "Cuotas")
        self.detail_tabs.addTab(history_page, "Historial")
        details_layout.addWidget(self.detail_tabs, 1)
        self.notes = make_label("", "muted")
        self.notes.setWordWrap(True)
        details_layout.addWidget(self.notes)
        details_layout.addStretch(1)
        actions = QHBoxLayout()
        self.pay_button = QPushButton("Registrar cobro")
        self.pay_button.setObjectName("primaryButton")
        self.pay_button.clicked.connect(self.take_payment)
        actions.addWidget(self.pay_button)
        self.edit_button = QPushButton("Editar")
        self.edit_button.setObjectName("secondaryButton")
        self.edit_button.clicked.connect(self.edit_student)
        actions.addWidget(self.edit_button)
        details_layout.addLayout(actions)
        owner_actions = QHBoxLayout()
        self.deactivate_button = QPushButton("Dar de baja")
        self.deactivate_button.setObjectName("textButton")
        self.deactivate_button.clicked.connect(self.deactivate)
        self.reactivate_button = QPushButton("Reactivar")
        self.reactivate_button.setObjectName("textButton")
        self.reactivate_button.setToolTip(
            "Pendiente acordar vencimiento e importe de reactivación."
        )
        self.reactivate_button.clicked.connect(self.reactivate)
        owner_actions.addWidget(self.deactivate_button)
        owner_actions.addWidget(self.reactivate_button)
        details_layout.addLayout(owner_actions)
        splitter.addWidget(self.detail)
        splitter.setSizes([650, 330])
        root.addWidget(splitter, 1)

        if self.actor.role != Role.OWNER:
            self.edit_button.hide()
            self.deactivate_button.hide()
            self.reactivate_button.hide()
        self.show_selected()

    def clear_filters(self) -> None:
        self.search.clear()
        self.filter.setCurrentText("Todos")

    def refresh(self) -> None:
        previous = self.selected_id
        try:
            self.service.generate_missing_dues()
            items = self.service.list_students(
                self.actor,
                query=self.search.text() if hasattr(self, "search") else "",
                filter_name=self.filter.currentText() if hasattr(self, "filter") else "Todos",
            )
        except DomainError as error:
            QMessageBox.warning(self, "No se pudieron cargar los alumnos", str(error))
            return
        self.students = {int(student["id"]): student for student in items}
        self.table.setRowCount(len(items))
        selected_row = -1
        for row_number, student in enumerate(items):
            student_id = int(student["id"])
            if student_id == previous:
                selected_row = row_number
            state = str(student["state"])
            background, foreground = STATE_COLORS[state]
            fees = student["fees"]
            current = next(
                (fee for fee in fees if fee["period"] == self.service.today().strftime("%Y-%m")),
                None,
            )
            outstanding = int(current["outstanding_cents"]) if current else 0
            values = [
                str(student["full_name"]),
                str(student["dni"]),
                str(student["activity"]),
                f"{student['sessions_per_week']} veces",
                str(student["state_label"]),
                format_money(outstanding) if current else "—",
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.ItemDataRole.UserRole, student_id)
                cell.setBackground(QColor(background))
                cell.setForeground(QColor(foreground if column == 4 else "#29332d"))
                if column == 4:
                    cell.setToolTip(str(student["state_detail"]))
                self.table.setItem(row_number, column, cell)
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        elif items:
            self.table.selectRow(0)
        else:
            self.selected_id = None
            self._clear_detail()
        self.show_selected()

    def show_selected(self) -> None:
        selected_items = self.table.selectedItems() if hasattr(self, "table") else []
        if not selected_items:
            self._clear_detail()
            return
        student_id = int(selected_items[0].data(Qt.ItemDataRole.UserRole))
        student = self.students.get(student_id)
        if student is None:
            return
        self.selected_id = student_id
        self.detail_name.setText(str(student["full_name"]))
        self.detail_state.setText(f"{student['state_label']} · {student['state_detail']}")
        self.name_value.setText(str(student["full_name"]))
        self.dni_value.setText(str(student["dni"]))
        self.phone_value.setText(str(student["phone"]))
        self.activity_value.setText(str(student["activity"]))
        self.plan_value.setText(f"{student['sessions_per_week']} veces por semana")
        self.enrolled_value.setText(
            date.fromisoformat(str(student["enrolled_on"])).strftime("%d/%m/%Y")
        )
        fees = list(student["fees"])
        self.fee_table.setRowCount(len(fees))
        for row, fee in enumerate(fees):
            values = [
                str(fee["period"]),
                date.fromisoformat(str(fee["due_date"])).strftime("%d/%m/%Y"),
                format_money(int(fee["outstanding_cents"]))
                if int(fee["outstanding_cents"])
                else "Cubierta",
            ]
            for column, value in enumerate(values):
                self.fee_table.setItem(row, column, QTableWidgetItem(value))
        history = self.service.list_student_history(self.actor, student_id)
        self.history_table.setRowCount(len(history))
        for row, movement in enumerate(history):
            kind = str(movement["kind"])
            if kind == "cuota":
                period = str(movement["date"])
                shown_date = f"{period[5:7]}/{period[:4]}"
                description = "Cuota"
                due_text = date.fromisoformat(str(movement["detail"])).strftime("%d/%m/%Y")
                status_text = (
                    "Cubierta"
                    if int(movement["paid_cents"]) >= int(movement["amount_cents"])
                    else "Pendiente"
                )
                detail = f"Vence {due_text} · {status_text}"
                if movement["extra"] == "alta_50":
                    detail += " · Descuento de ingreso 50 %"
                amount = format_money(int(movement["amount_cents"]))
            elif kind == "pago":
                shown_date = str(movement["date"])[:10]
                description = "Cobro"
                detail = f"{movement['detail']} · {movement['extra']}"
                amount = format_money(int(movement["amount_cents"]))
            else:
                shown_date = date.fromisoformat(str(movement["date"])).strftime("%d/%m/%Y")
                description = str(movement["detail"]).replace("_", " ").capitalize()
                detail = "Movimiento de cuenta"
                amount = "—"
            for column, value in enumerate((shown_date, description, detail, amount)):
                self.history_table.setItem(row, column, QTableWidgetItem(value))
        self.notes.setText(
            f"Observaciones: {student['notes']}" if student["notes"] else "Sin observaciones"
        )
        has_open_fees = any(int(fee["outstanding_cents"]) > 0 for fee in fees)
        self.pay_button.setEnabled(has_open_fees)
        self.edit_button.setEnabled(self.actor.role == Role.OWNER)
        self.deactivate_button.setVisible(self.actor.role == Role.OWNER and bool(student["active"]))
        self.reactivate_button.setVisible(
            self.actor.role == Role.OWNER and not bool(student["active"])
        )
        self.reactivate_button.setEnabled(False)

    def _clear_detail(self) -> None:
        if not hasattr(self, "detail_name"):
            return
        self.selected_id = None
        self.detail_name.setText("Selecciona un alumno")
        self.detail_state.setText("")
        for label in (
            self.name_value,
            self.dni_value,
            self.phone_value,
            self.activity_value,
            self.plan_value,
            self.enrolled_value,
        ):
            label.setText("—")
        self.fee_table.setRowCount(0)
        self.history_table.setRowCount(0)
        self.notes.setText("")
        self.pay_button.setEnabled(False)
        self.edit_button.setEnabled(False)
        self.deactivate_button.setVisible(False)
        self.reactivate_button.setVisible(False)

    def add_student(self) -> None:
        dialog = StudentDialog(self.service, self.actor)
        if dialog.exec():
            self.changed.emit()
            self.refresh()

    def edit_student(self) -> None:
        student = self.students.get(self.selected_id or -1)
        if not student or self.actor.role != Role.OWNER:
            return
        dialog = StudentDialog(self.service, self.actor, student=student)
        if dialog.exec():
            self.changed.emit()
            self.refresh()

    def take_payment(self) -> None:
        student = self.students.get(self.selected_id or -1)
        if not student:
            return
        dialog = PaymentDialog(self.service, self.actor, student)
        if dialog.exec():
            self.changed.emit()
            self.refresh()

    def deactivate(self) -> None:
        if self.selected_id is None:
            return
        answer = QMessageBox.question(
            self,
            "Dar de baja",
            "El alumno quedará inactivo. Las cuotas y cobros anteriores se conservarán. ¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.deactivate_student(self.actor, self.selected_id)
        except DomainError as error:
            QMessageBox.warning(self, "No se pudo dar de baja", str(error))
            return
        self.filter.setCurrentText("Todos")
        self.changed.emit()
        self.refresh()

    def reactivate(self) -> None:
        if self.selected_id is None:
            return
        try:
            self.service.reactivate_student(self.actor, self.selected_id)
        except DomainError as error:
            QMessageBox.information(self, "Decisión pendiente", str(error))
