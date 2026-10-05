from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from moove_recovery.application.service import GymService
from moove_recovery.domain.errors import DomainError
from moove_recovery.domain.models import Actor
from moove_recovery.ui.common import format_money, parse_money


def _gym_logo() -> QLabel:
    logo = QLabel()
    logo.setObjectName("gymLogo")
    logo.setAccessibleName("Logo de MOOVE RECOVERY")
    logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
    path = Path(__file__).resolve().parents[3] / "assets" / "branding" / "moove_recovery.png"
    pixmap = QPixmap(str(path))
    if not pixmap.isNull():
        logo.setPixmap(
            pixmap.scaled(
                260,
                190,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
    return logo


class InitialSetupDialog(QDialog):
    def __init__(self, service: GymService) -> None:
        super().__init__()
        self.service = service
        self.setWindowTitle("Configuración inicial · MOOVE RECOVERY")
        self.setMinimumWidth(430)
        layout = QVBoxLayout(self)
        self.gym_logo = _gym_logo()
        layout.addWidget(self.gym_logo)
        layout.addWidget(QLabel("Crea la cuenta del dueño e ingresa los precios vigentes reales."))
        self.full_name = QLineEdit()
        self.full_name.setPlaceholderText("Nombre y apellido")
        self.username = QLineEdit()
        self.username.setPlaceholderText("Usuario")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Mínimo 12 caracteres")
        form = QFormLayout()
        form.addRow("Dueño", self.full_name)
        form.addRow("Usuario", self.username)
        form.addRow("Contraseña", self.password)
        layout.addLayout(form)
        layout.addWidget(QLabel("Precios mensuales (ARS)"), 0, Qt.AlignmentFlag.AlignLeft)
        self.price_fields: dict[int, QLineEdit] = {}
        price_form = QFormLayout()
        for sessions in (2, 3, 4):
            field = QLineEdit()
            field.setPlaceholderText("Ej.: 30000,00")
            self.price_fields[sessions] = field
            price_form.addRow(f"Plan {sessions} veces por semana", field)
        layout.addLayout(price_form)
        hint = QLabel("Los importes se guardan en centavos. No se cargan precios de ejemplo.")
        hint.setObjectName("muted")
        layout.addWidget(hint)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Crear configuración")
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save(self) -> None:
        try:
            prices = {
                sessions: parse_money(field.text()) for sessions, field in self.price_fields.items()
            }
            self.service.setup_owner(
                full_name=self.full_name.text(),
                username=self.username.text(),
                password=self.password.text(),
                prices_cents=prices,
            )
        except (ValueError, DomainError) as error:
            QMessageBox.warning(self, "No se pudo guardar", str(error))
            return
        self.accept()


class LoginDialog(QDialog):
    def __init__(self, service: GymService) -> None:
        super().__init__()
        self.service = service
        self.actor: Actor | None = None
        self.setWindowTitle("Iniciar sesión · MOOVE RECOVERY")
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        self.gym_logo = _gym_logo()
        layout.addWidget(self.gym_logo)
        layout.addWidget(QLabel("Gestión de cuotas"))
        self.username = QLineEdit()
        self.username.setPlaceholderText("Usuario")
        self.password = QLineEdit()
        self.password.setPlaceholderText("Contraseña")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        form = QFormLayout()
        form.addRow("Usuario", self.username)
        form.addRow("Contraseña", self.password)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Ingresar")
        buttons.accepted.connect(self.authenticate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.password.returnPressed.connect(self.authenticate)

    def authenticate(self) -> None:
        self.actor = self.service.login(self.username.text(), self.password.text())
        if self.actor is None:
            QMessageBox.warning(self, "Acceso rechazado", "Usuario o contraseña incorrectos.")
            self.password.clear()
            self.password.setFocus()
            return
        self.accept()


class StudentDialog(QDialog):
    def __init__(self, service: GymService, actor: Actor, *, student: dict | None = None) -> None:
        super().__init__()
        self.service = service
        self.actor = actor
        self.student = student
        self.setWindowTitle("Editar alumno" if student else "Nuevo alumno")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.first_name = QLineEdit(student["first_name"] if student else "")
        self.last_name = QLineEdit(student["last_name"] if student else "")
        self.dni = QLineEdit(student["dni"] if student else "")
        self.phone = QLineEdit(student["phone"] if student else "")
        self.activity = QLineEdit(student["activity"] if student else "")
        self.enrolled_on = QDateEdit()
        self.enrolled_on.setCalendarPopup(True)
        self.enrolled_on.setDisplayFormat("dd/MM/yyyy")
        self.enrolled_on.setDate(
            QDate.fromString(student["enrolled_on"], "yyyy-MM-dd")
            if student
            else QDate.currentDate()
        )
        self.enrolled_on.setMaximumDate(QDate.currentDate())
        self.plan = QComboBox()
        for plan in service.available_plans():
            self.plan.addItem(f"{plan['sessions_per_week']} veces por semana", plan["id"])
            if student and plan["id"] == student["plan_id"]:
                self.plan.setCurrentIndex(self.plan.count() - 1)
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(76)
        if student:
            self.notes.setPlainText(student["notes"])
            self.enrolled_on.setEnabled(False)
            self.plan.setEnabled(False)
        form.addRow("Nombre", self.first_name)
        form.addRow("Apellido", self.last_name)
        form.addRow("DNI", self.dni)
        form.addRow("Teléfono", self.phone)
        form.addRow("Actividad", self.activity)
        form.addRow("Fecha de alta", self.enrolled_on)
        form.addRow("Plan", self.plan)
        form.addRow("Observaciones", self.notes)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save(self) -> None:
        try:
            if self.student:
                self.service.update_student_details(
                    self.actor,
                    int(self.student["id"]),
                    first_name=self.first_name.text(),
                    last_name=self.last_name.text(),
                    dni=self.dni.text(),
                    phone=self.phone.text(),
                    activity=self.activity.text(),
                    notes=self.notes.toPlainText(),
                )
            else:
                self.service.create_student(
                    self.actor,
                    first_name=self.first_name.text(),
                    last_name=self.last_name.text(),
                    dni=self.dni.text(),
                    phone=self.phone.text(),
                    activity=self.activity.text(),
                    enrolled_on=self.enrolled_on.date().toPython(),
                    plan_id=int(self.plan.currentData()),
                    notes=self.notes.toPlainText(),
                )
        except (DomainError, ValueError) as error:
            if hasattr(error, "student_id"):
                status = "activo" if error.active else "inactivo"
                QMessageBox.warning(
                    self,
                    "DNI existente",
                    f"Ya existe un alumno {status} con ese DNI. Busca la coincidencia antes de "
                    "continuar; si está inactivo, puedes reactivarlo desde su ficha.",
                )
            else:
                QMessageBox.warning(self, "No se pudo guardar", str(error))
            return
        self.accept()


class PaymentDialog(QDialog):
    def __init__(self, service: GymService, actor: Actor, student: dict) -> None:
        super().__init__()
        self.service = service
        self.actor = actor
        self.student = student
        self.payment_id: int | None = None
        self.idempotency_key = str(uuid4())
        self.setWindowTitle("Registrar cobro")
        self.setMinimumWidth(470)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Cobrar a {student['full_name']}"))
        period_controls = QHBoxLayout()
        period_controls.addWidget(QLabel("Incluir cuotas hasta (mes)"))
        self.through_month = QDateEdit()
        self.through_month.setCalendarPopup(True)
        self.through_month.setDisplayFormat("MM/yyyy")
        today = service.today()
        self.through_month.setMinimumDate(QDate(today.year, today.month, 1))
        self.through_month.setDate(QDate(today.year, today.month, 1))
        period_controls.addWidget(self.through_month)
        self.load_dues_button = QPushButton("Cargar cuotas")
        self.load_dues_button.clicked.connect(self.load_dues_through_period)
        period_controls.addWidget(self.load_dues_button)
        layout.addLayout(period_controls)
        self.dues = QListWidget()
        self.dues.itemChanged.connect(self.update_total)
        layout.addWidget(self.dues)
        form = QFormLayout()
        self.method = QComboBox()
        for value, label in (
            ("efectivo", "Efectivo"),
            ("transferencia", "Transferencia"),
            ("debito", "Débito"),
            ("credito", "Crédito"),
            ("otro", "Otro"),
        ):
            self.method.addItem(label, value)
        self.reference = QLineEdit()
        self.reference.setPlaceholderText("Opcional")
        self.total = QLabel(format_money(0))
        self.total.setObjectName("paymentTotal")
        form.addRow("Medio de pago", self.method)
        form.addRow("Referencia", self.reference)
        form.addRow("Total", self.total)
        layout.addLayout(form)
        note = QLabel(
            "Solo se cobran cuotas completas. Los adelantos quedan asociados a sus períodos."
        )
        note.setObjectName("muted")
        layout.addWidget(note)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save
        )
        self.submit = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        self.submit.setText("Confirmar cobro")
        self.submit.setEnabled(False)
        self.buttons.accepted.connect(self.confirm)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self._populate_dues()

    def _populate_dues(self, selected_periods: set[str] | None = None) -> None:
        self.dues.clear()
        self.dues.setEnabled(True)
        for fee in self.student["fees"]:
            if int(fee["outstanding_cents"]) <= 0:
                continue
            item = QListWidgetItem(
                f"{fee['period']}  ·  Vence {date.fromisoformat(fee['due_date']).strftime('%d/%m/%Y')}  ·  "
                f"{format_money(int(fee['amount_cents']))}"
            )
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            period = str(fee["period"])
            item.setCheckState(
                Qt.CheckState.Checked
                if selected_periods is not None and period in selected_periods
                else Qt.CheckState.Unchecked
            )
            item.setData(Qt.ItemDataRole.UserRole, int(fee["id"]))
            item.setData(Qt.ItemDataRole.UserRole + 1, int(fee["amount_cents"]))
            item.setData(Qt.ItemDataRole.UserRole + 2, period)
            self.dues.addItem(item)
        if self.dues.count() == 0:
            self.dues.addItem("No hay cuotas pendientes para cobrar.")
            self.dues.setEnabled(False)
        self.update_total()

    def load_dues_through_period(self) -> None:
        selected_periods = {
            str(self.dues.item(index).data(Qt.ItemDataRole.UserRole + 2))
            for index in range(self.dues.count())
            if self.dues.item(index).checkState() == Qt.CheckState.Checked
            and self.dues.item(index).data(Qt.ItemDataRole.UserRole + 2) is not None
        }
        through = self.through_month.date().toPython()
        try:
            counts = self.service.prepare_future_dues(self.actor, int(self.student["id"]), through)
            self.student = next(
                student
                for student in self.service.list_students(self.actor)
                if student["id"] == self.student["id"]
            )
            self._populate_dues(selected_periods)
        except DomainError as error:
            QMessageBox.warning(self, "No se pudieron cargar las cuotas", str(error))
            return
        if counts["without_price"]:
            QMessageBox.warning(
                self,
                "Faltan precios",
                f"No se generaron {counts['without_price']} cuota(s) porque falta configurar "
                "el precio del plan para esos períodos.",
            )

    def selected(self) -> tuple[list[int], int]:
        due_ids: list[int] = []
        total = 0
        for index in range(self.dues.count()):
            item = self.dues.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                due_ids.append(int(item.data(Qt.ItemDataRole.UserRole)))
                total += int(item.data(Qt.ItemDataRole.UserRole + 1))
        return due_ids, total

    def update_total(self) -> None:
        _, total = self.selected()
        self.total.setText(format_money(total))
        self.submit.setEnabled(total > 0)

    def confirm(self) -> None:
        due_ids, total = self.selected()
        answer = QMessageBox.question(
            self,
            "Confirmar cobro",
            f"Registrar {format_money(total)} para {len(due_ids)} cuota(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.submit.setEnabled(False)
        try:
            self.payment_id = self.service.record_payment(
                self.actor,
                student_id=int(self.student["id"]),
                due_ids=due_ids,
                total_cents=total,
                method=str(self.method.currentData()),
                reference=self.reference.text(),
                idempotency_key=self.idempotency_key,
            )
        except DomainError as error:
            QMessageBox.critical(self, "Cobro no registrado", str(error))
            self.submit.setEnabled(True)
            return
        except Exception as error:
            QMessageBox.critical(
                self,
                "Error de guardado",
                f"No se confirmó el cobro. La operación se revirtió.\n\n{error}",
            )
            self.submit.setEnabled(True)
            return
        self.accept()
