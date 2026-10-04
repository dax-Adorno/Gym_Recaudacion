from datetime import date

from conftest import add_student
from PySide6.QtCore import QDate, Qt

from moove_recovery.application.service import GymService
from moove_recovery.ui.dialogs import PaymentDialog
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
