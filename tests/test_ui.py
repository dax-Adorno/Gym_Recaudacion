from datetime import date

from conftest import add_student
from PySide6.QtCore import Qt

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
