from datetime import date

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from moove_recovery.application.service import GymService
from moove_recovery.domain.errors import DomainError
from moove_recovery.domain.models import Actor
from moove_recovery.ui.common import format_money, make_label, parse_money, plus_icon
from moove_recovery.ui.dashboard_page import MONTHS
from moove_recovery.ui.responsive_header import ResponsiveHeader

METHODS = [
    ("Efectivo", "efectivo"),
    ("Transferencia", "transferencia"),
    ("Debito", "debito"),
    ("Credito", "credito"),
    ("Otro", "otro"),
]


class ExpenseDialog(QDialog):
    def __init__(
        self, service: GymService, actor: Actor, expense=None, *, pending=False, pay_only=False
    ):
        super().__init__()
        self.service, self.actor, self.expense, self.pay_only = service, actor, expense, pay_only
        self.setWindowTitle(
            "Registrar pago de gasto" if pay_only else "Editar gasto" if expense else "Nuevo gasto"
        )
        self.setMinimumWidth(430)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.concept = QLineEdit(str(expense["concept"]) if expense else "")
        self.category = QComboBox()
        self.category.setEditable(True)
        self.category.addItems(
            ["Alquiler", "Servicios", "Sueldos", "Mantenimiento", "Insumos", "Otros"]
        )
        if expense:
            self.category.setCurrentText(str(expense["category"]))
        self.amount = QLineEdit()
        if expense:
            cents = int(expense["amount_cents"])
            self.amount.setText(f"{cents // 100},{cents % 100:02d}")
        self.status = QComboBox()
        self.status.addItems(["Pagado", "Pendiente"])
        self.status.setCurrentIndex(
            1 if (expense and expense["status"] == "pending") or pending else 0
        )
        self.status.setEnabled(not pay_only)
        self.scheduled = QDateEdit(
            QDate.fromString(str(expense["scheduled_on"]), Qt.DateFormat.ISODate)
            if expense
            else QDate(service.today().year, service.today().month, service.today().day)
        )
        self.scheduled.setCalendarPopup(True)
        self.scheduled.setDisplayFormat("dd/MM/yyyy")
        self.paid = QDateEdit(
            QDate.fromString(str(expense["paid_on"]), Qt.DateFormat.ISODate)
            if expense and expense["paid_on"]
            else self.scheduled.date()
        )
        self.paid.setCalendarPopup(True)
        self.paid.setDisplayFormat("dd/MM/yyyy")
        today = service.today()
        self.paid.setMaximumDate(QDate(today.year, today.month, today.day))
        self.method = QComboBox()
        for label, value in METHODS:
            self.method.addItem(label, value)
        if expense and expense["method"]:
            self.method.setCurrentIndex(self.method.findData(expense["method"]))
        self.notes = QTextEdit(str(expense["notes"]) if expense else "")
        self.notes.setMaximumHeight(85)
        for label, widget in [
            ("Concepto", self.concept),
            ("Categoria", self.category),
            ("Importe (ARS)", self.amount),
            ("Estado", self.status),
            ("Fecha prevista", self.scheduled),
            ("Fecha de pago", self.paid),
            ("Medio de pago", self.method),
            ("Observaciones", self.notes),
        ]:
            form.addRow(label, widget)
        root.addLayout(form)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setStyleSheet("color: #a33232")
        root.addWidget(self.error)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self.status.currentIndexChanged.connect(self.update_payment_fields)
        self.update_payment_fields()
        if pay_only:
            for widget in (
                self.concept,
                self.category,
                self.amount,
                self.status,
                self.scheduled,
                self.notes,
            ):
                widget.setEnabled(False)
            self.paid.setEnabled(True)
            self.method.setEnabled(True)

    def update_payment_fields(self):
        paid = self.status.currentIndex() == 0 or self.pay_only
        self.paid.setEnabled(paid)
        self.method.setEnabled(paid)

    def save(self):
        try:
            if self.pay_only:
                self.service.pay_expense(
                    self.actor,
                    int(self.expense["id"]),
                    paid_on=self.paid.date().toPython(),
                    method=self.method.currentData(),
                )
            else:
                paid = self.status.currentIndex() == 0
                if self.expense and self.expense["status"] == "paid" and not paid:
                    answer = QMessageBox.question(
                        self,
                        "Volver a pendiente",
                        "El gasto dejara de contar como pagado en el reporte. "
                        "Se quitaran su fecha y medio de pago, conservando la auditoria. "
                        "Esto corrige el registro; no devuelve dinero. ¿Continuar?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No,
                    )
                    if answer != QMessageBox.StandardButton.Yes:
                        return
                self.service.save_expense(
                    self.actor,
                    concept=self.concept.text(),
                    category=self.category.currentText(),
                    scheduled_on=self.scheduled.date().toPython(),
                    amount_cents=parse_money(self.amount.text()),
                    paid_on=self.paid.date().toPython() if paid else None,
                    method=self.method.currentData() if paid else None,
                    notes=self.notes.toPlainText(),
                    expense_id=int(self.expense["id"]) if self.expense else None,
                    expected_status=str(self.expense["status"]) if self.expense else None,
                )
        except (DomainError, ValueError) as error:
            self.error.setText(str(error))
            return
        self.accept()


class ExpensesPage(QWidget):
    changed = Signal()

    def __init__(self, service: GymService, actor: Actor):
        super().__init__()
        self.service, self.actor = service, actor
        service.list_expenses(actor, status="pending")
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 24)
        root.addWidget(make_label("Gastos", "pageTitle"))
        controls = QHBoxLayout()
        self.month = QComboBox()
        self.month.addItems(MONTHS)
        self.month.setCurrentIndex(service.today().month - 1)
        self.year = QSpinBox()
        self.year.setRange(1, 9999)
        self.year.setValue(service.today().year)
        controls.addWidget(self.month)
        controls.addWidget(self.year)
        controls.addStretch()
        add = QPushButton("Nuevo gasto")
        add.setObjectName("primaryButton")
        add.setIcon(plus_icon("#ffffff"))
        add.setToolTip("Registrar un nuevo gasto pagado o pendiente")
        add.clicked.connect(self.add_expense)
        controls.addWidget(add)
        root.addLayout(controls)
        self.total = make_label("", "sectionTitle")
        self.total.setWordWrap(True)
        root.addWidget(self.total)
        self.tabs = QTabWidget()
        self.tables = []
        self.rows = []
        for label in ("Pagados", "Pendientes", "Anulados"):
            table = QTableWidget(0, 6)
            table.setHorizontalHeader(ResponsiveHeader(table))
            table.setHorizontalHeaderLabels(
                ["FECHA", "CONCEPTO", "CATEGORIA", "IMPORTE", "MEDIO", "OBSERVACIONES"]
            )
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            table.horizontalHeader().setMinimumSectionSize(95)
            for column, width in enumerate((110, 230, 150, 135, 130, 240)):
                table.setColumnWidth(column, width)
            table.setWordWrap(True)
            table.setTextElideMode(Qt.TextElideMode.ElideNone)
            table.horizontalHeader().sectionResized.connect(table.resizeRowsToContents)
            table.verticalHeader().setMinimumSectionSize(36)
            table.verticalHeader().hide()
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setAlternatingRowColors(True)
            table.itemSelectionChanged.connect(self.update_buttons)
            self.tables.append(table)
            self.tabs.addTab(table, label)
        self.tabs.setTabToolTip(1, "Todos los pendientes actuales, sin limitar al mes seleccionado")
        root.addWidget(self.tabs, 1)
        actions = QHBoxLayout()
        self.edit = QPushButton("Editar")
        self.pay = QPushButton("Registrar pago")
        self.void = QPushButton("Anular")
        self.edit.setObjectName("secondaryButton")
        self.pay.setObjectName("primaryButton")
        self.void.setObjectName("dangerButton")
        for button, icon, handler in [
            (self.edit, QStyle.StandardPixmap.SP_FileDialogDetailedView, self.edit_expense),
            (self.pay, QStyle.StandardPixmap.SP_DialogApplyButton, self.pay_expense),
            (self.void, QStyle.StandardPixmap.SP_DialogCancelButton, self.void_expense),
        ]:
            button.setIcon(self.style().standardIcon(icon))
            button.clicked.connect(handler)
            actions.addWidget(button)
        root.addLayout(actions)
        self.month.currentIndexChanged.connect(self.refresh)
        self.year.valueChanged.connect(self.refresh)
        self.tabs.currentChanged.connect(self.update_buttons)
        self.refresh()

    def refresh(self, *_args):
        period = f"{self.year.value():04d}-{self.month.currentIndex() + 1:02d}"
        self.rows = [
            self.service.list_expenses(
                self.actor, status=status, period=None if status == "pending" else period
            )
            for status in ("paid", "pending", "voided")
        ]
        for table, rows in zip(self.tables, self.rows, strict=True):
            table.setRowCount(len(rows))
            for index, expense in enumerate(rows):
                values = [
                    date.fromisoformat(str(expense["paid_on"] or expense["scheduled_on"])).strftime(
                        "%d/%m/%Y"
                    ),
                    expense["concept"],
                    expense["category"],
                    format_money(int(expense["amount_cents"])),
                    dict((value, label) for label, value in METHODS).get(expense["method"], "-"),
                    expense["void_reason"] or expense["notes"],
                ]
                for column, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    item.setToolTip(str(value))
                    table.setItem(index, column, item)
            table.resizeRowsToContents()
        paid = sum(int(item["amount_cents"]) for item in self.rows[0])
        pending = sum(int(item["amount_cents"]) for item in self.rows[1])
        self.total.setText(
            f"Pagados en {period}: {format_money(paid)}    |    Pendientes actuales: {format_money(pending)}"
        )
        self.update_buttons()

    def selected(self):
        index = self.tabs.currentIndex()
        row = self.tables[index].currentRow()
        return self.rows[index][row] if 0 <= row < len(self.rows[index]) else None

    def update_buttons(self, *_args):
        expense = self.selected() if self.rows else None
        active = bool(expense and expense["status"] != "voided")
        self.edit.setEnabled(active)
        self.void.setEnabled(active)
        self.pay.setEnabled(bool(expense and expense["status"] == "pending"))

    def run_dialog(self, expense=None, *, pay_only=False):
        dialog = ExpenseDialog(
            self.service,
            self.actor,
            expense,
            pending=self.tabs.currentIndex() == 1,
            pay_only=pay_only,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            self.changed.emit()

    def add_expense(self):
        self.run_dialog()

    def edit_expense(self):
        if self.selected():
            self.run_dialog(self.selected())

    def pay_expense(self):
        if self.selected():
            self.run_dialog(self.selected(), pay_only=True)

    def void_expense(self):
        expense = self.selected()
        if not expense:
            return
        reason, accepted = QInputDialog.getText(self, "Anular gasto", "Motivo de anulacion:")
        if not accepted:
            return
        try:
            self.service.void_expense(self.actor, int(expense["id"]), reason)
        except DomainError as error:
            QMessageBox.warning(self, "No se pudo anular", str(error))
            return
        self.refresh()
        self.changed.emit()
