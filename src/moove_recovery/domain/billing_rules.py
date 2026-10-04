from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from moove_recovery.domain.models import FeeStatusInput, StudentState, StudentStatus


def month_start(value: date) -> date:
    return value.replace(day=1)


def next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def add_months(value: date, count: int) -> date:
    absolute = value.year * 12 + value.month - 1 + count
    year, month0 = divmod(absolute, 12)
    month = month0 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def monthly_due_date(period: date) -> date:
    due = date(period.year, period.month, 10)
    if due.weekday() == 5:
        return due + timedelta(days=2)
    if due.weekday() == 6:
        return due + timedelta(days=1)
    return due


def notice_start(due: date) -> date:
    cursor = due
    business_days = 0
    while business_days < 3:
        cursor -= timedelta(days=1)
        if cursor.weekday() < 5:
            business_days += 1
    return cursor


def first_due_date(enrolled_on: date, period: date) -> date:
    regular = monthly_due_date(period)
    return enrolled_on if enrolled_on > regular else regular


def half_discount_cents(base_cents: int) -> int:
    if base_cents < 0:
        raise ValueError("El precio no puede ser negativo.")
    return (base_cents * 50 + 50) // 100


def enrollment_amount(
    base_cents: int, enrolled_on: date, period: date
) -> tuple[int, int, str | None]:
    if month_start(enrolled_on) != month_start(period) or enrolled_on.day < 21:
        return base_cents, 0, None
    discount = half_discount_cents(base_cents)
    return base_cents - discount, discount, "alta_50"


def derive_student_status(
    *,
    active: bool,
    today: date,
    current_fee: FeeStatusInput | None,
    fees: list[FeeStatusInput],
) -> StudentStatus:
    if not active:
        return StudentStatus(StudentState.INACTIVE, "Inactivo", "Alumno inactivo")

    overdue = [fee for fee in fees if fee.due_date < today and fee.paid_cents < fee.amount_cents]
    if overdue:
        return StudentStatus(StudentState.OVERDUE, "Deudor", "Tiene cuotas vencidas impagas")

    if current_fee is None:
        return StudentStatus(
            StudentState.MISSING_FEE,
            "Sin cuota generada",
            "Revisar configuración de precios o generación de cuotas",
        )

    if current_fee.paid_cents >= current_fee.amount_cents:
        return StudentStatus(StudentState.CURRENT, "Al día", "Cuota del período cubierta")

    if today >= notice_start(current_fee.due_date):
        return StudentStatus(
            StudentState.WARNING, "Próximo a vencer", "Cuota pendiente en ventana de aviso"
        )

    return StudentStatus(StudentState.PENDING, "Pendiente", "Cuota actual pendiente")
