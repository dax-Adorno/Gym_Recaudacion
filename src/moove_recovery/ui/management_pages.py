from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from moove_recovery.application.service import GymService
from moove_recovery.domain.billing_rules import month_start
from moove_recovery.domain.billing_rules import next_month as next_period
from moove_recovery.domain.models import Actor
from moove_recovery.ui.common import format_money, make_label, parse_money


class PricesPage(QWidget):
    def __init__(self, service: GymService, actor: Actor) -> None:
        super().__init__()
        self.service = service
        self.actor = actor
        self.fields: dict[int, QLineEdit] = {}
        self.original_prices: dict[int, int | None] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        title = make_label("Planes y precios", "pageTitle")
        layout.addWidget(title)
        layout.addWidget(
            make_label(
                "Cada cambio se aplica desde el mes siguiente. Las cuotas ya generadas conservan su importe.",
                "muted",
            )
        )
        layout.addSpacing(12)
        form = QFormLayout()
        current = {int(row["id"]): row for row in service.list_plans(actor)}
        for plan_id, plan in current.items():
            sessions = int(plan["sessions_per_week"])
            field = QLineEdit()
            field.setPlaceholderText("ARS, por ejemplo 30000,00")
            if plan["amount_cents"] is not None:
                field.setText(format_money(int(plan["amount_cents"])).removeprefix("$ "))
                self.original_prices[plan_id] = int(plan["amount_cents"])
            else:
                self.original_prices[plan_id] = None
            self.fields[plan_id] = field
            form.addRow(f"{sessions} veces por semana", field)
        layout.addLayout(form)
        layout.addSpacing(8)
        save = QPushButton("Guardar precios")
        save.setObjectName("primaryButton")
        save.clicked.connect(self.save)
        layout.addWidget(save, 0)
        layout.addStretch(1)

    def save(self) -> None:
        starts_on = next_period(month_start(self.service.today()))
        try:
            for plan_id, field in self.fields.items():
                cents = parse_money(field.text())
                if cents != self.original_prices[plan_id]:
                    self.service.set_plan_price(self.actor, plan_id, cents, starts_on)
        except Exception as error:
            QMessageBox.warning(self, "No se pudieron guardar los precios", str(error))
            return
        QMessageBox.information(
            self, "Precios guardados", "Los cambios comenzarán a regir el mes próximo."
        )


class UsersPage(QWidget):
    def __init__(self, service: GymService, actor: Actor) -> None:
        super().__init__()
        self.service = service
        self.actor = actor
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.addWidget(make_label("Usuarios", "pageTitle"))
        layout.addWidget(
            make_label(
                "Solo se pueden crear cuentas de empleado. La cuenta del dueño no se duplica.",
                "muted",
            )
        )
        form = QFormLayout()
        self.full_name = QLineEdit()
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Mínimo 12 caracteres")
        form.addRow("Nombre y apellido", self.full_name)
        form.addRow("Usuario", self.username)
        form.addRow("Contraseña", self.password)
        layout.addLayout(form)
        create = QPushButton("Crear empleado")
        create.setObjectName("primaryButton")
        create.clicked.connect(self.create_user)
        layout.addWidget(create, 0)
        layout.addSpacing(18)
        layout.addWidget(make_label("Cuentas del sistema", "sectionTitle"))
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["NOMBRE", "USUARIO", "ROL"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        self.refresh()

    def create_user(self) -> None:
        try:
            self.service.create_employee(
                self.actor,
                full_name=self.full_name.text(),
                username=self.username.text(),
                password=self.password.text(),
            )
        except Exception as error:
            QMessageBox.warning(self, "No se pudo crear el usuario", str(error))
            return
        self.full_name.clear()
        self.username.clear()
        self.password.clear()
        self.refresh()

    def refresh(self) -> None:
        users = self.service.list_users(self.actor)
        self.table.setRowCount(len(users))
        for row, user in enumerate(users):
            for column, value in enumerate(
                (
                    user["full_name"],
                    user["username"],
                    "Dueño" if user["role"] == "owner" else "Empleado",
                )
            ):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
