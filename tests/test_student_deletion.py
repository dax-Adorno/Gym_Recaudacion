import sqlite3
from datetime import date

import pytest
from conftest import add_student

from moove_recovery.domain.errors import DomainError, PermissionDenied, ValidationError


@pytest.mark.parametrize("voided", [False, True])
@pytest.mark.parametrize("inactive", [False, True])
def test_delete_removes_all_history_without_changing_other_students(environment, voided, inactive):
    service = environment["service"]
    owner = environment["owner"]
    target = add_student(environment, name="Eliminar", dni="10000001")
    remaining = add_student(environment, name="Conservar", dni="10000002")
    service.generate_missing_dues()
    service.prepare_future_dues(owner, target, date(2026, 11, 1))
    students = {s["id"]: s for s in service.list_students(owner)}
    payment_ids = {}
    for student_id in (target, remaining):
        fees = students[student_id]["fees"]
        payment_ids[student_id] = service.record_payment(
            owner,
            student_id=student_id,
            due_ids=[fee["id"] for fee in fees],
            total_cents=sum(fee["amount_cents"] for fee in fees),
            method="efectivo",
        )
    if voided:
        service.void_payment(owner, payment_ids[target], "Prueba de eliminación")
    if inactive:
        service.deactivate_student(owner, target)
    before = next(s for s in service.list_students(owner) if s["id"] == remaining)
    history_before = service.list_student_history(owner, remaining)
    service.delete_student(owner, target)
    assert service.list_students(owner) == [before]
    assert service.list_student_history(owner, target) == []
    assert service.list_student_history(owner, remaining) == history_before
    db = environment["db"]
    assert db.fetch_one("SELECT id FROM payments WHERE id = ?", (payment_ids[target],)) is None
    assert (
        db.fetch_one("SELECT id FROM payments WHERE id = ?", (payment_ids[remaining],)) is not None
    )
    assert db.fetch_all("PRAGMA foreign_key_check") == []
    assert (
        db.fetch_all(
            "SELECT id FROM audit_log WHERE entity_type = 'students' AND entity_id = ?", (target,)
        )
        == []
    )
    assert db.fetch_one("SELECT id FROM audit_log WHERE action = 'alumno_eliminacion'") is not None


def test_employee_cannot_delete_and_missing_student_is_rejected(environment):
    service = environment["service"]
    owner = environment["owner"]
    target = add_student(environment)
    service.create_employee(
        owner, full_name="Empleado Ficticio", username="empleado", password="ClaveEmpleado-2026"
    )
    employee = service.login("empleado", "ClaveEmpleado-2026")
    assert employee is not None
    with pytest.raises(PermissionDenied):
        service.delete_student(employee, target)
    assert len(service.list_students(owner)) == 1
    with pytest.raises(ValidationError, match="no existe"):
        service.delete_student(owner, target + 100)


def test_delete_rolls_back_everything_if_final_delete_fails(environment):
    service = environment["service"]
    owner = environment["owner"]
    target = add_student(environment)
    service.generate_missing_dues()
    fee = service.list_students(owner)[0]["fees"][0]
    service.record_payment(
        owner,
        student_id=target,
        due_ids=[fee["id"]],
        total_cents=fee["amount_cents"],
        method="efectivo",
    )
    db = environment["db"]
    tables = ("students", "dues", "payments", "payment_dues", "student_history", "audit_log")
    before = {t: [tuple(r) for r in db.fetch_all(f"SELECT * FROM {t}")] for t in tables}
    with db.transaction() as connection:
        connection.execute(
            "CREATE TRIGGER refuse_student_delete BEFORE DELETE ON students "
            "BEGIN SELECT RAISE(ABORT, 'test rollback'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="test rollback"):
        service.delete_student(owner, target)
    after = {t: [tuple(r) for r in db.fetch_all(f"SELECT * FROM {t}")] for t in tables}
    assert after == before


def test_shared_payment_cannot_delete_another_students_payment(environment):
    service = environment["service"]
    owner = environment["owner"]
    target = add_student(environment, dni="10000001")
    remaining = add_student(environment, dni="10000002")
    service.generate_missing_dues()
    students = {s["id"]: s for s in service.list_students(owner)}
    fee = students[target]["fees"][0]
    payment = service.record_payment(
        owner,
        student_id=target,
        due_ids=[fee["id"]],
        total_cents=fee["amount_cents"],
        method="efectivo",
    )
    with environment["db"].transaction() as connection:
        other_fee = students[remaining]["fees"][0]
        connection.execute(
            "INSERT INTO payment_dues(payment_id, due_id, amount_cents) VALUES (?, ?, ?)",
            (payment, other_fee["id"], other_fee["amount_cents"]),
        )
    before = service.list_students(owner)
    with pytest.raises(DomainError, match="compartido"):
        service.delete_student(owner, target)
    assert service.list_students(owner) == before
