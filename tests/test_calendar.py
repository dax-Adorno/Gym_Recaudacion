from datetime import date

import pytest
from conftest import add_student

from moove_recovery.domain.errors import PermissionDenied, ValidationError


def test_calendar_lists_due_payment_and_student_activity(environment) -> None:
    service = environment["service"]
    owner = environment["owner"]
    student_id = add_student(environment)
    service.generate_missing_dues()
    student = next(item for item in service.list_students(owner) if item["id"] == student_id)
    fee = student["fees"][0]
    service.record_payment(
        owner,
        student_id=student_id,
        due_ids=[fee["id"]],
        total_cents=int(fee["amount_cents"]),
        method="efectivo",
    )
    service.deactivate_student(owner, student_id)
    service.reactivate_student(owner, student_id)
    start, end = date(2026, 10, 1), date(2026, 10, 31)

    dues = service.list_calendar_events(owner, start, end, "vencimientos")
    payments = service.list_calendar_events(owner, start, end, "cobros")
    activity = service.list_calendar_events(owner, start, end, "movimientos")

    assert len(dues) == 1
    assert dues[0]["date"] == date(2026, 10, 10)
    assert dues[0]["details"] == "Cuota 2026-10 · Pagada"
    assert len(payments) == 1
    assert payments[0]["date"] == date(2026, 10, 3)
    assert payments[0]["amount_cents"] == 3_000_000
    assert [event["details"] for event in activity] == ["Alta", "Baja", "Reactivación"]
    assert all(event["student_id"] == student_id for event in activity)


def test_calendar_is_owner_only_and_validates_query(environment) -> None:
    service = environment["service"]
    service.create_employee(
        environment["owner"],
        full_name="Empleado Ficticio",
        username="empleado-calendario",
        password="ClaveEmpleado-Calendario",
    )
    employee = service.login("empleado-calendario", "ClaveEmpleado-Calendario")
    assert employee is not None
    with pytest.raises(PermissionDenied):
        service.list_calendar_events(employee, date(2026, 10, 1), date(2026, 10, 31), "cobros")
    with pytest.raises(ValidationError, match="categoría válida"):
        service.list_calendar_events(
            environment["owner"], date(2026, 10, 1), date(2026, 10, 31), "otro"
        )
    with pytest.raises(ValidationError, match="no puede preceder"):
        service.list_calendar_events(
            environment["owner"], date(2026, 11, 1), date(2026, 10, 31), "cobros"
        )


def test_calendar_marks_weekend_due_overdue_on_monday(environment) -> None:
    service = environment["service"]
    add_student(environment)
    service.generate_missing_dues()
    environment["clock"].current = date(2026, 10, 12)

    events = service.list_calendar_events(
        environment["owner"], date(2026, 10, 1), date(2026, 10, 31), "vencimientos"
    )

    assert events[0]["date"] == date(2026, 10, 10)
    assert events[0]["details"].endswith("Vencida")
