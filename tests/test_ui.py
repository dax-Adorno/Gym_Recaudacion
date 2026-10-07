from datetime import date

from conftest import add_student
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox

from moove_recovery.application.service import GymService
from moove_recovery.ui.calendar_page import CalendarPage
from moove_recovery.ui.dashboard_page import DashboardPage
from moove_recovery.ui.dialogs import LoginDialog, PaymentDialog
from moove_recovery.ui.main_window import MainWindow
from moove_recovery.ui.students_page import StudentsPage


def test_students_page_shows_searchable_real_service_rows(qtbot, environment) -> None:
    student_id = add_student(environment, name="Lucía", dni="31.234.567")
    service: GymService = environment["service"]
    page = StudentsPage(service, environment["owner"])
    qtbot.addWidget(page)
    page.show()
    assert page.table.rowCount() == 1
    assert page.table.item(0, 0).text() == "Lucía Pérez"
    page.search.setText("lucia")
    assert page.table.rowCount() == 1
    page.search.setText("999")
    assert page.table.rowCount() == 0
    assert page.selected_id is None
    assert student_id not in page.students


def test_dashboard_period_selector_refreshes_owner_metrics(qtbot, environment) -> None:
    student_id = add_student(environment)
    service: GymService = environment["service"]
    service.generate_missing_dues()
    student = next(
        item for item in service.list_students(environment["owner"]) if item["id"] == student_id
    )
    fee = student["fees"][0]
    service.record_payment(
        environment["owner"],
        student_id=student_id,
        due_ids=[fee["id"]],
        total_cents=fee["amount_cents"],
        method="efectivo",
    )

    page = DashboardPage(service, environment["owner"])
    qtbot.addWidget(page)
    assert page.received_value.text() == "$ 30.000,00"
    assert page.applied_value.text() == "$ 30.000,00"
    assert page.pending_value.text() == "$ 0,00"
    assert page.dues_table.rowCount() == 1
    assert page.payments_table.rowCount() == 1
    assert page.export_pdf_button.isEnabled()
    assert page.export_xlsx_button.isEnabled()
    assert page.empty_label.isHidden()

    page.month.setCurrentIndex(10)
    assert page.summary["period"] == "2026-11"
    assert page.summary["due_count"] == 0
    assert not page.empty_label.isHidden()

    window = MainWindow(service, environment["owner"])
    qtbot.addWidget(window)
    assert "Panel" in window.nav_buttons
    assert "Calendario" in window.nav_buttons
    assert "Respaldos" in window.nav_buttons
    service.create_employee(
        environment["owner"],
        full_name="Empleado Ficticio",
        username="empleado-sin-panel",
        password="ClaveEmpleado-Panel",
    )
    employee = service.login("empleado-sin-panel", "ClaveEmpleado-Panel")
    assert employee is not None
    employee_window = MainWindow(service, employee)
    qtbot.addWidget(employee_window)
    assert "Panel" not in employee_window.nav_buttons
    assert "Calendario" not in employee_window.nav_buttons
    assert "Respaldos" not in employee_window.nav_buttons
    assert employee_window.students_page.delete_button.isHidden()


def test_delete_student_requires_confirmation_and_removes_only_selection(
    qtbot, environment, monkeypatch
):
    target = add_student(environment, name="Eliminar", dni="10000001")
    remaining = add_student(environment, name="Conservar", dni="10000002")
    service = environment["service"]
    page = StudentsPage(service, environment["owner"])
    qtbot.addWidget(page)
    for row in range(page.table.rowCount()):
        if page.table.item(row, 0).data(Qt.ItemDataRole.UserRole) == target:
            page.table.selectRow(row)
            break
    assert page.selected_id == target
    prompts = []

    def cancel(*args):
        prompts.append(args)
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "warning", cancel)
    page.delete_button.click()
    assert len(service.list_students(environment["owner"])) == 2
    assert "Eliminar Pérez" in prompts[0][2]
    assert "10000001" in prompts[0][2]
    assert prompts[0][-1] == QMessageBox.StandardButton.No
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: QMessageBox.StandardButton.Yes)
    page.delete_button.click()
    assert list(page.students) == [remaining]
    assert page.selected_id == remaining


def test_calendar_page_has_three_event_actions_and_month_navigation(qtbot, environment) -> None:
    add_student(environment)
    service: GymService = environment["service"]
    service.generate_missing_dues()
    page = CalendarPage(service, environment["owner"])
    qtbot.addWidget(page)

    assert set(page.category_buttons) == {"vencimientos", "cobros", "movimientos"}
    assert len(page.day_button_list) == 42
    page.day_buttons[date(2026, 10, 10)].click()
    assert page.events_table.rowCount() == 1
    page.select_category("movimientos")
    page.day_buttons[date(2026, 10, 3)].click()
    assert page.events_table.rowCount() == 1
    assert page.events_table.item(0, 0).text() == "Ana Pérez"
    page.shift_month(1)
    assert page.month_title.text() == "Noviembre 2026"
    assert page.events_table.rowCount() == 0


def test_owner_can_reactivate_selected_inactive_student_from_detail(qtbot, environment) -> None:
    student_id = add_student(environment)
    service: GymService = environment["service"]
    service.deactivate_student(environment["owner"], student_id)
    page = StudentsPage(service, environment["owner"])
    qtbot.addWidget(page)
    page.filter.setCurrentText("Inactivos")
    page.table.selectRow(0)

    assert page.selected_id == student_id
    assert not page.reactivate_button.isHidden()
    assert page.reactivate_button.isEnabled()


def test_deactivation_preserves_other_students_dues_and_shows_fee_not_balance(
    qtbot, environment, monkeypatch
) -> None:
    service = environment["service"]
    owner = environment["owner"]
    selected_id = add_student(environment, name="Baja", dni="10000001")
    pending_id = add_student(environment, name="Pendiente", dni="10000002")
    paid_id = add_student(environment, name="Pagado", dni="10000003")
    service.generate_missing_dues()
    paid_student = next(s for s in service.list_students(owner) if s["id"] == paid_id)
    fee = paid_student["fees"][0]
    service.record_payment(
        owner,
        student_id=paid_id,
        due_ids=[fee["id"]],
        total_cents=fee["amount_cents"],
        method="efectivo",
    )
    before = {s["id"]: s for s in service.list_students(owner)}
    page = StudentsPage(service, owner)
    qtbot.addWidget(page)
    for row in range(page.table.rowCount()):
        if page.table.item(row, 0).data(Qt.ItemDataRole.UserRole) == selected_id:
            page.table.selectRow(row)
            break
    assert page.selected_id == selected_id
    monkeypatch.setattr(
        QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes
    )
    page.deactivate_button.click()
    after = {s["id"]: s for s in service.list_students(owner)}
    assert not after[selected_id]["active"]
    assert after[selected_id]["fees"] == before[selected_id]["fees"]
    for student_id in (pending_id, paid_id):
        assert after[student_id] == before[student_id]
    for row in range(page.table.rowCount()):
        assert page.table.item(row, 5).text() == "$ 30.000,00"
        if page.table.item(row, 0).data(Qt.ItemDataRole.UserRole) == paid_id:
            assert "Saldo pendiente: $ 0,00" in page.table.item(row, 5).toolTip()


def test_login_shows_gym_logo(qtbot, environment) -> None:
    dialog = LoginDialog(environment["service"])
    qtbot.addWidget(dialog)

    assert dialog.gym_logo.pixmap() is not None
    assert not dialog.gym_logo.pixmap().isNull()


def test_creator_credit_opens_personal_instagram(qtbot, environment, monkeypatch) -> None:
    window = MainWindow(environment["service"], environment["owner"])
    qtbot.addWidget(window)
    opened_urls: list[str] = []
    monkeypatch.setattr(
        QDesktopServices,
        "openUrl",
        lambda url: opened_urls.append(url.toString()),
    )

    assert not window.creator_button.icon().isNull()
    window.creator_button.click()

    assert opened_urls == ["https://www.instagram.com/daxadorno/"]


def test_navigation_sections_expand_as_an_accordion(qtbot, environment) -> None:
    window = MainWindow(environment["service"], environment["owner"])
    qtbot.addWidget(window)

    operation_toggle, operation_content, _ = window.nav_sections["OPERACIÓN"]
    management_toggle, management_content, _ = window.nav_sections["GESTIÓN"]
    admin_toggle, admin_content, _ = window.nav_sections["ADMINISTRACIÓN"]
    qtbot.wait(240)

    assert operation_toggle.isChecked()
    assert operation_content.maximumHeight() > 0
    assert not management_toggle.isChecked()

    management_toggle.click()
    qtbot.wait(240)
    assert management_toggle.isChecked()
    assert not operation_toggle.isChecked()
    assert operation_content.maximumHeight() == 0
    assert management_content.maximumHeight() > 0

    admin_toggle.click()
    qtbot.wait(240)
    assert admin_toggle.isChecked()
    assert not management_toggle.isChecked()
    assert management_content.maximumHeight() == 0
    assert admin_content.maximumHeight() > 0

    window.nav_buttons["Calendario"].click()
    qtbot.wait(240)
    assert window.pages.currentWidget() is window.page_widgets["Calendario"]
    assert management_toggle.isChecked()
    assert not admin_toggle.isChecked()
    assert admin_content.maximumHeight() == 0

    management_toggle.click()
    qtbot.wait(240)
    assert management_content.maximumHeight() == 0
    management_toggle.click()
    qtbot.wait(40)
    management_toggle.click()
    qtbot.wait(240)
    assert management_content.maximumHeight() == 0


def test_payment_dialog_total_tracks_complete_period_selection(qtbot, environment) -> None:
    student_id = add_student(environment, day=date(2026, 10, 3))
    service: GymService = environment["service"]
    service.generate_missing_dues()
    student = next(
        item for item in service.list_students(environment["owner"]) if item["id"] == student_id
    )
    dialog = PaymentDialog(service, environment["owner"], student)
    qtbot.addWidget(dialog)
    item = dialog.dues.item(0)
    item.setCheckState(Qt.CheckState.Checked)
    assert dialog.total.text() == "$ 30.000,00"
    assert dialog.submit.isEnabled()
    item.setCheckState(Qt.CheckState.Unchecked)
    assert dialog.total.text() == "$ 0,00"
    assert not dialog.submit.isEnabled()


def test_payment_dialog_loads_future_periods_without_losing_selection(qtbot, environment) -> None:
    student_id = add_student(environment)
    service: GymService = environment["service"]
    service.generate_missing_dues()
    student = next(
        item for item in service.list_students(environment["owner"]) if item["id"] == student_id
    )
    dialog = PaymentDialog(service, environment["owner"], student)
    qtbot.addWidget(dialog)

    current_item = dialog.dues.item(0)
    current_item.setCheckState(Qt.CheckState.Checked)
    dialog.through_month.setDate(QDate(2027, 1, 18))
    dialog.load_dues_button.click()

    periods = {
        str(dialog.dues.item(index).data(Qt.ItemDataRole.UserRole + 2)): dialog.dues.item(index)
        for index in range(dialog.dues.count())
    }
    assert set(periods) == {"2026-10", "2026-11", "2026-12", "2027-01"}
    assert periods["2026-10"].checkState() == Qt.CheckState.Checked
    periods["2027-01"].setCheckState(Qt.CheckState.Checked)
    assert dialog.total.text() == "$ 60.000,00"


def test_void_payment_action_is_owner_only_and_selects_valid_payments(qtbot, environment) -> None:
    student_id = add_student(environment)
    service: GymService = environment["service"]
    service.generate_missing_dues()
    student = next(
        item for item in service.list_students(environment["owner"]) if item["id"] == student_id
    )
    fee = student["fees"][0]
    payment_id = service.record_payment(
        environment["owner"],
        student_id=student_id,
        due_ids=[fee["id"]],
        total_cents=fee["amount_cents"],
        method="efectivo",
    )
    page = StudentsPage(service, environment["owner"])
    qtbot.addWidget(page)
    assert not page.void_payment_button.isHidden()
    page.history_table.selectRow(0)
    assert page.void_payment_button.isEnabled()
    service.void_payment(environment["owner"], payment_id, "Prueba de anulación")
    page.refresh()
    payment_row = next(
        row
        for row in range(page.history_table.rowCount())
        if page.history_table.item(row, 1).data(Qt.ItemDataRole.UserRole) == payment_id
    )
    page.history_table.selectRow(payment_row)
    assert not page.void_payment_button.isEnabled()

    employee_service = GymService(service.db, today=service.today, now=service.now)
    employee_service.create_employee(
        environment["owner"],
        full_name="Empleado Ficticio",
        username="empleado-ui",
        password="ClaveEmpleado-2026",
    )
    employee = employee_service.login("empleado-ui", "ClaveEmpleado-2026")
    assert employee is not None
    employee_page = StudentsPage(employee_service, employee)
    qtbot.addWidget(employee_page)
    assert employee_page.void_payment_button.isHidden()
