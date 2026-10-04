from datetime import date

import pytest
from conftest import add_student

from moove_recovery.application.service import GymService
from moove_recovery.domain.errors import (
    DomainError,
    DuplicatePayment,
    DuplicateStudent,
    PermissionDenied,
    ValidationError,
)


def test_migration_and_quota_generation_are_idempotent(environment) -> None:
    service: GymService = environment["service"]
    student_id = add_student(environment)
    assert service.generate_missing_dues() == {"created": 1, "without_price": 0}
    assert service.generate_missing_dues() == {"created": 0, "without_price": 0}
    student = next(
        item for item in service.list_students(environment["owner"]) if item["id"] == student_id
    )
    assert student["fees"][0]["period"] == "2026-10"
    assert student["fees"][0]["due_date"] == "2026-10-12"
    assert student["activity"] == "Musculación"
    service.initialize()
    assert environment["db"].integrity_check() == "ok"


def test_late_enrollment_gets_one_half_price_first_month(environment) -> None:
    clock = environment["clock"]
    clock.current = date(2026, 10, 25)
    student_id = add_student(environment, day=date(2026, 10, 25), dni="20-000-001")
    counts = environment["service"].generate_missing_dues()
    student = next(
        item
        for item in environment["service"].list_students(environment["owner"])
        if item["id"] == student_id
    )
    fee = student["fees"][0]
    assert counts["created"] == 1
    assert fee["base_cents"] == 3_000_000
    assert fee["discount_cents"] == 1_500_000
    assert fee["amount_cents"] == 1_500_000
    assert fee["due_date"] == "2026-10-25"


def test_employee_can_add_student_but_cannot_change_prices_or_deactivate(environment) -> None:
    service: GymService = environment["service"]
    service.create_employee(
        environment["owner"],
        full_name="Empleado Ficticio",
        username="empleado",
        password="ClaveEmpleado-2026",
    )
    employee = service.login("empleado", "ClaveEmpleado-2026")
    assert employee is not None
    student_id = service.create_student(
        employee,
        first_name="Luis",
        last_name="Gómez",
        dni="12345679",
        phone="011 4000-1111",
        activity="Entrenamiento funcional",
        enrolled_on=date(2026, 10, 3),
        plan_id=environment["plans"][3],
    )
    with pytest.raises(PermissionDenied):
        service.set_plan_price(employee, environment["plans"][2], 4_000_000, date(2026, 11, 1))
    with pytest.raises(PermissionDenied):
        service.deactivate_student(employee, student_id)
    with pytest.raises(PermissionDenied):
        service.list_users(employee)


def test_dni_duplicate_finds_inactive_record_and_all_filter_includes_it(environment) -> None:
    service: GymService = environment["service"]
    student_id = add_student(environment, dni="12.345.678")
    service.deactivate_student(environment["owner"], student_id)
    with pytest.raises(DuplicateStudent) as error:
        add_student(environment, dni="12345678")
    assert error.value.student_id == student_id
    assert not error.value.active
    assert any(item["id"] == student_id for item in service.list_students(environment["owner"]))
    assert any(
        item["id"] == student_id
        for item in service.list_students(environment["owner"], filter_name="Inactivos")
    )


def test_search_ignores_accents_and_treats_like_wildcards_literally(environment) -> None:
    service: GymService = environment["service"]
    student_id = add_student(environment, name="Ana 100%", dni="AB_12")
    assert any(
        item["id"] == student_id
        for item in service.list_students(environment["owner"], query="ana 100%")
    )
    assert (
        any(
            item["id"] == student_id
            for item in service.list_students(environment["owner"], query="12345678")
        )
        is False
    )
    assert any(
        item["id"] == student_id
        for item in service.list_students(environment["owner"], query="ab_12")
    )


def test_full_payment_records_period_and_retries_idempotently(environment) -> None:
    service: GymService = environment["service"]
    student_id = add_student(environment)
    service.generate_missing_dues()
    fee = next(
        item for item in service.list_students(environment["owner"]) if item["id"] == student_id
    )["fees"][0]
    key = "checkout-operation-1"
    payment_id = service.record_payment(
        environment["owner"],
        student_id=student_id,
        due_ids=[fee["id"]],
        total_cents=fee["amount_cents"],
        method="transferencia",
        reference="TRX ficticia 001",
        idempotency_key=key,
    )
    assert (
        service.record_payment(
            environment["owner"],
            student_id=student_id,
            due_ids=[fee["id"]],
            total_cents=fee["amount_cents"],
            method="transferencia",
            reference="TRX ficticia 001",
            idempotency_key=key,
        )
        == payment_id
    )
    payment_count = environment["db"].fetch_one("SELECT COUNT(*) FROM payments")[0]
    assert payment_count == 1
    history = service.list_student_history(environment["owner"], student_id)
    assert {row["kind"] for row in history} == {"cuota", "pago", "movimiento"}


def test_partial_payment_is_rejected_without_writing(environment) -> None:
    service: GymService = environment["service"]
    student_id = add_student(environment)
    service.generate_missing_dues()
    fee = next(
        item for item in service.list_students(environment["owner"]) if item["id"] == student_id
    )["fees"][0]
    with pytest.raises(ValidationError, match="cuotas completas"):
        service.record_payment(
            environment["owner"],
            student_id=student_id,
            due_ids=[fee["id"]],
            total_cents=fee["amount_cents"] - 1,
            method="efectivo",
        )
    assert environment["db"].fetch_one("SELECT COUNT(*) FROM payments")[0] == 0


def test_failure_between_payment_and_application_rolls_back(environment) -> None:
    service: GymService = environment["service"]
    student_id = add_student(environment)
    service.generate_missing_dues()
    fee = next(
        item for item in service.list_students(environment["owner"]) if item["id"] == student_id
    )["fees"][0]
    with environment["db"].transaction() as connection:
        connection.execute(
            "CREATE TRIGGER reject_application BEFORE INSERT ON payment_dues "
            "BEGIN SELECT RAISE(ABORT, 'fallo de prueba'); END"
        )
    with pytest.raises(Exception, match="fallo de prueba"):
        service.record_payment(
            environment["owner"],
            student_id=student_id,
            due_ids=[fee["id"]],
            total_cents=fee["amount_cents"],
            method="efectivo",
            idempotency_key="rollback-case",
        )
    assert environment["db"].fetch_one("SELECT COUNT(*) FROM payments")[0] == 0
    assert environment["db"].fetch_one("SELECT COUNT(*) FROM payment_dues")[0] == 0


def test_reusing_payment_key_for_different_operation_is_rejected(environment) -> None:
    service: GymService = environment["service"]
    student_id = add_student(environment)
    service.generate_missing_dues()
    fee = next(
        item for item in service.list_students(environment["owner"]) if item["id"] == student_id
    )["fees"][0]
    service.record_payment(
        environment["owner"],
        student_id=student_id,
        due_ids=[fee["id"]],
        total_cents=fee["amount_cents"],
        method="efectivo",
        idempotency_key="same-key",
    )
    with pytest.raises(DuplicatePayment):
        service.record_payment(
            environment["owner"],
            student_id=student_id,
            due_ids=[fee["id"]],
            total_cents=fee["amount_cents"],
            method="transferencia",
            idempotency_key="same-key",
        )


def test_void_payment_reopens_due_and_preserves_reason_and_audit(environment) -> None:
    service: GymService = environment["service"]
    student_id = add_student(environment)
    service.generate_missing_dues()
    fee = next(
        item for item in service.list_students(environment["owner"]) if item["id"] == student_id
    )["fees"][0]
    payment_id = service.record_payment(
        environment["owner"],
        student_id=student_id,
        due_ids=[fee["id"]],
        total_cents=fee["amount_cents"],
        method="efectivo",
    )

    service.void_payment(environment["owner"], payment_id, "  Cobro   duplicado  ")

    payment = environment["db"].fetch_one(
        "SELECT status, void_reason FROM payments WHERE id = ?", (payment_id,)
    )
    assert payment["status"] == "voided"
    assert payment["void_reason"] == "Cobro duplicado"
    assert environment["db"].fetch_one("SELECT COUNT(*) FROM payment_dues")[0] == 1
    history = service.list_student_history(environment["owner"], student_id)
    payment_history = next(row for row in history if row["kind"] == "pago")
    assert payment_history["void_reason"] == "Cobro duplicado"
    audit = environment["db"].fetch_one(
        "SELECT actor_id, action, details, created_at FROM audit_log "
        "WHERE entity_type = 'payments' AND entity_id = ? AND action = 'cobro_anulado'",
        (payment_id,),
    )
    assert audit["actor_id"] == environment["owner"].id
    assert audit["action"] == "cobro_anulado"
    assert '"reason": "Cobro duplicado"' in audit["details"]
    assert audit["created_at"].startswith("2026-10-03T12:00:00")
    refreshed_fee = next(
        item for item in service.list_students(environment["owner"]) if item["id"] == student_id
    )["fees"][0]
    assert refreshed_fee["outstanding_cents"] == fee["amount_cents"]


def test_void_payment_is_owner_only_and_requires_a_reason(environment) -> None:
    service: GymService = environment["service"]
    student_id = add_student(environment)
    service.generate_missing_dues()
    fee = next(
        item for item in service.list_students(environment["owner"]) if item["id"] == student_id
    )["fees"][0]
    payment_id = service.record_payment(
        environment["owner"],
        student_id=student_id,
        due_ids=[fee["id"]],
        total_cents=fee["amount_cents"],
        method="efectivo",
    )
    service.create_employee(
        environment["owner"],
        full_name="Empleado Ficticio",
        username="empleado-void",
        password="ClaveEmpleado-2026",
    )
    employee = service.login("empleado-void", "ClaveEmpleado-2026")
    assert employee is not None

    with pytest.raises(PermissionDenied):
        service.void_payment(employee, payment_id, "Intento no autorizado")
    with pytest.raises(ValidationError, match="motivo"):
        service.void_payment(environment["owner"], payment_id, "  \n  ")
    assert (
        environment["db"].fetch_one("SELECT status FROM payments WHERE id = ?", (payment_id,))[0]
        == "valid"
    )


def test_payment_cannot_be_voided_twice(environment) -> None:
    service: GymService = environment["service"]
    student_id = add_student(environment)
    service.generate_missing_dues()
    fee = next(
        item for item in service.list_students(environment["owner"]) if item["id"] == student_id
    )["fees"][0]
    payment_id = service.record_payment(
        environment["owner"],
        student_id=student_id,
        due_ids=[fee["id"]],
        total_cents=fee["amount_cents"],
        method="efectivo",
    )
    service.void_payment(environment["owner"], payment_id, "Error de registro")

    with pytest.raises(DomainError, match="ya fue anulado"):
        service.void_payment(environment["owner"], payment_id, "Segundo intento")
    assert (
        environment["db"].fetch_one(
            "SELECT COUNT(*) FROM audit_log WHERE action = 'cobro_anulado'"
        )[0]
        == 1
    )


def test_price_change_does_not_rewrite_generated_month(environment) -> None:
    service: GymService = environment["service"]
    student_id = add_student(environment)
    service.generate_missing_dues()
    student = next(
        item for item in service.list_students(environment["owner"]) if item["id"] == student_id
    )
    october_fee = student["fees"][0]
    service.set_plan_price(
        environment["owner"], environment["plans"][2], 3_300_000, date(2026, 11, 1)
    )
    environment["clock"].current = date(2026, 11, 3)
    service.generate_missing_dues()
    student = next(
        item for item in service.list_students(environment["owner"]) if item["id"] == student_id
    )
    prices = {fee["period"]: fee["base_cents"] for fee in student["fees"]}
    assert october_fee["base_cents"] == 3_000_000
    assert prices == {"2026-10": 3_000_000, "2026-11": 3_300_000}


def test_password_is_hashed_and_second_owner_setup_is_blocked(environment) -> None:
    from moove_recovery.domain.errors import ValidationError

    row = environment["db"].fetch_one("SELECT password_hash FROM users WHERE role = 'owner'")
    assert row["password_hash"].startswith("$argon2id$")
    assert "UnaClaveLocal-2026" not in row["password_hash"]
    with pytest.raises(ValidationError, match="ya fue realizada"):
        environment["service"].setup_owner(
            full_name="Segundo Dueño",
            username="otro-dueno",
            password="OtraClaveLocal-2026",
            prices_cents={2: 3_000_000, 3: 3_500_000, 4: 4_000_000},
        )
