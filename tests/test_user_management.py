import pytest
from conftest import add_student
from PySide6.QtWidgets import QDialog, QMessageBox

from moove_recovery.domain.errors import PermissionDenied, ValidationError
from moove_recovery.ui.management_pages import UserEditDialog, UsersPage


def employee_account(environment):
    service = environment["service"]
    user_id = service.create_employee(
        environment["owner"],
        full_name="Empleado Ficticio",
        username="empleado",
        password="ClaveEmpleado-2026",
    )
    actor = service.login("empleado", "ClaveEmpleado-2026")
    assert actor is not None
    return user_id, actor


def test_update_preserves_password_unless_replaced_and_keeps_role(environment):
    service = environment["service"]
    user_id, _ = employee_account(environment)
    service.update_user(
        environment["owner"], user_id, full_name="  Nombre   Nuevo ", username="nuevo"
    )
    assert service.login("empleado", "ClaveEmpleado-2026") is None
    updated = service.login("NUEVO", "ClaveEmpleado-2026")
    assert updated.full_name == "Nombre Nuevo"
    assert updated.role.value == "employee"
    service.update_user(
        environment["owner"],
        user_id,
        full_name="Nombre Nuevo",
        username="nuevo",
        password="OtraClaveEmpleado-2026",
    )
    assert service.login("nuevo", "ClaveEmpleado-2026") is None
    assert service.login("nuevo", "OtraClaveEmpleado-2026") is not None
    audits = environment["db"].fetch_all(
        "SELECT details FROM audit_log WHERE action = 'usuario_edicion'"
    )
    assert all("OtraClaveEmpleado-2026" not in r["details"] for r in audits)


def test_owner_can_edit_own_account_but_cannot_be_deleted(environment):
    service = environment["service"]
    owner = environment["owner"]
    service.update_user(
        owner,
        owner.id,
        full_name="Nuevo Dueño",
        username="administrador",
        password="NuevaClaveDueno-2026",
    )
    assert service.login("administrador", "NuevaClaveDueno-2026").role.value == "owner"
    with pytest.raises(ValidationError, match="dueño"):
        service.delete_user(owner, owner.id)


@pytest.mark.parametrize(
    "values",
    [
        {"full_name": "Nombre", "username": "DUENO"},
        {"full_name": " ", "username": "empleado"},
        {"full_name": "Nombre", "username": " "},
        {"full_name": "Nombre", "username": "nuevo", "password": "corta"},
    ],
)
def test_invalid_updates_leave_user_unchanged(environment, values):
    service = environment["service"]
    user_id, _ = employee_account(environment)
    before = service.list_users(environment["owner"])
    with pytest.raises(ValidationError):
        service.update_user(environment["owner"], user_id, **values)
    assert service.list_users(environment["owner"]) == before
    assert service.login("empleado", "ClaveEmpleado-2026") is not None


def test_delete_user_preserves_financial_history_and_revokes_old_actor(environment):
    service = environment["service"]
    owner = environment["owner"]
    user_id, employee = employee_account(environment)
    student_id = add_student(environment)
    service.generate_missing_dues()
    fee = service.list_students(owner)[0]["fees"][0]
    service.record_payment(
        employee,
        student_id=student_id,
        due_ids=[fee["id"]],
        total_cents=fee["amount_cents"],
        method="efectivo",
    )
    before = service.get_monthly_report(owner, 2026, 10)
    service.delete_user(owner, user_id)
    assert service.login("empleado", "ClaveEmpleado-2026") is None
    assert all(u["id"] != user_id for u in service.list_users(owner))
    deleted = next(
        u for u in service.list_users(owner, include_inactive=True) if u["id"] == user_id
    )
    assert not deleted["active"]
    assert service.get_monthly_report(owner, 2026, 10) == before
    assert environment["db"].fetch_all("PRAGMA foreign_key_check") == []
    for operation in (
        lambda: service.list_students(employee),
        lambda: service.list_student_history(employee, student_id),
        lambda: service.prepare_future_dues(employee, student_id, service.today()),
        lambda: service.record_payment(
            employee,
            student_id=student_id,
            due_ids=[fee["id"]],
            total_cents=fee["amount_cents"],
            method="efectivo",
        ),
        lambda: service.create_student(
            employee,
            first_name="Otro",
            last_name="Alumno",
            dni="10000002",
            phone="",
            activity="Actividad",
            enrolled_on=service.today(),
            plan_id=environment["plans"][2],
        ),
    ):
        with pytest.raises(PermissionDenied):
            operation()
    with pytest.raises(ValidationError):
        service.update_user(owner, user_id, full_name="No", username="no")


def test_employee_cannot_manage_accounts_and_duplicate_create_is_rejected(environment):
    service = environment["service"]
    user_id, employee = employee_account(environment)
    with pytest.raises(PermissionDenied):
        service.update_user(employee, user_id, full_name="No", username="no")
    with pytest.raises(PermissionDenied):
        service.delete_user(employee, user_id)
    with pytest.raises(PermissionDenied):
        service.list_users(employee)
    with pytest.raises(ValidationError, match="registrado"):
        service.create_employee(
            environment["owner"],
            full_name="Otro",
            username="EMPLEADO",
            password="ClaveEmpleado-2026",
        )


def test_user_edit_dialog_saves_and_delete_requires_confirmation(qtbot, environment, monkeypatch):
    service = environment["service"]
    owner = environment["owner"]
    user_id, _ = employee_account(environment)
    page = UsersPage(service, owner)
    qtbot.addWidget(page)
    user = page.users[user_id]
    dialog = UserEditDialog(service, owner, user)
    qtbot.addWidget(dialog)
    assert dialog.password.text() == ""
    dialog.full_name.setText("Nombre actualizado")
    dialog.save_user()
    assert dialog.result() == QDialog.DialogCode.Accepted
    page.refresh()
    for row in range(page.table.rowCount()):
        if page.table.item(row, 1).text() == "empleado":
            page.table.selectRow(row)
            break
    assert page.edit_button.isEnabled() and page.delete_button.isEnabled()
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: QMessageBox.StandardButton.No)
    page.delete_button.click()
    assert user_id in page.users
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: QMessageBox.StandardButton.Yes)
    page.delete_button.click()
    assert user_id not in page.users
    page.show_deleted.setChecked(True)
    for row in range(page.table.rowCount()):
        if page.table.item(row, 1).text() == "empleado":
            page.table.selectRow(row)
            break
    assert not page.edit_button.isEnabled() and not page.delete_button.isEnabled()


def test_editing_own_account_requests_new_login(qtbot, environment, monkeypatch):
    page = UsersPage(environment["service"], environment["owner"])
    qtbot.addWidget(page)
    page.table.selectRow(0)

    def save(dialog):
        dialog.full_name.setText("Dueño actualizado")
        dialog.save_user()
        return dialog.result()

    monkeypatch.setattr(UserEditDialog, "exec", save)
    assert page.edit_button.isEnabled() and not page.delete_button.isEnabled()
    with qtbot.waitSignal(page.session_change_requested):
        page.edit_button.click()
