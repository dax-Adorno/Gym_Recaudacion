from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from moove_recovery.application.service import GymService
from moove_recovery.domain.billing_rules import month_start
from moove_recovery.domain.billing_rules import next_month as next_period
from moove_recovery.domain.errors import DomainError
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


class UserEditDialog(QDialog):
    def __init__(
        self, service: GymService, actor: Actor, user: dict[str, object], parent=None
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.actor = actor
        self.user_id = int(user["id"])
        self.setWindowTitle("Editar usuario")
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.full_name = QLineEdit(str(user["full_name"]))
        self.username = QLineEdit(str(user["username"]))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Sin cambio si queda vacía")
        form.addRow("Nombre y apellido", self.full_name)
        form.addRow("Usuario", self.username)
        form.addRow("Nueva contraseña", self.password)
        layout.addLayout(form)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.save_user)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def save_user(self) -> None:
        try:
            self.service.update_user(
                self.actor,
                self.user_id,
                full_name=self.full_name.text(),
                username=self.username.text(),
                password=self.password.text() or None,
            )
        except DomainError as error:
            QMessageBox.warning(self, "No se pudo modificar el usuario", str(error))
            return
        self.password.clear()
        self.accept()


class UsersPage(QWidget):
    session_change_requested = Signal()

    def __init__(self, service: GymService, actor: Actor) -> None:
        super().__init__()
        self.service = service
        self.actor = actor
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.addWidget(make_label("Usuarios", "pageTitle"))
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
        self.show_deleted = QCheckBox("Mostrar eliminados")
        self.show_deleted.toggled.connect(self.refresh)
        layout.addWidget(self.show_deleted)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["NOMBRE", "USUARIO", "ROL", "ESTADO"])
        self.table.setColumnWidth(0, 250)
        self.table.setColumnWidth(1, 160)
        self.table.setColumnWidth(2, 110)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        actions = QHBoxLayout()
        self.edit_button = QPushButton("Editar usuario")
        self.edit_button.setObjectName("secondaryButton")
        self.edit_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        )
        self.edit_button.clicked.connect(self.edit_user)
        self.delete_button = QPushButton("Eliminar usuario")
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.delete_button.clicked.connect(self.delete_user)
        actions.addWidget(self.edit_button)
        actions.addWidget(self.delete_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        self.users: dict[int, dict[str, object]] = {}
        self.table.itemSelectionChanged.connect(self.sync_actions)
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
        users = self.service.list_users(self.actor, include_inactive=self.show_deleted.isChecked())
        self.users = {int(user["id"]): user for user in users}
        self.table.setRowCount(len(users))
        for row, user in enumerate(users):
            for column, value in enumerate(
                (
                    user["full_name"],
                    user["username"],
                    "Dueño" if user["role"] == "owner" else "Empleado",
                    "Activo" if user["active"] else "Eliminado",
                )
            ):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, int(user["id"]))
                self.table.setItem(row, column, item)
        self.table.clearSelection()
        self.sync_actions()

    def selected_user(self) -> dict[str, object] | None:
        items = self.table.selectedItems()
        return self.users.get(int(items[0].data(Qt.ItemDataRole.UserRole))) if items else None

    def sync_actions(self) -> None:
        user = self.selected_user()
        self.edit_button.setEnabled(bool(user and user["active"]))
        self.delete_button.setEnabled(bool(user and user["active"] and user["role"] != "owner"))

    def edit_user(self) -> None:
        user = self.selected_user()
        if user is None or not user["active"]:
            return
        dialog = UserEditDialog(self.service, self.actor, user, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            if int(user["id"]) == self.actor.id:
                self.session_change_requested.emit()

    def delete_user(self) -> None:
        user = self.selected_user()
        if user is None:
            return
        answer = QMessageBox.warning(
            self,
            "Eliminar usuario",
            f"¿Eliminar el acceso de {user['full_name']} ({user['username']})?\n\n"
            "No podrá ingresar ni seguir operando con una sesión existente. "
            "Su identificación se conservará en el historial de operaciones.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.delete_user(self.actor, int(user["id"]))
        except DomainError as error:
            QMessageBox.warning(self, "No se pudo eliminar el usuario", str(error))
            return
        self.refresh()
