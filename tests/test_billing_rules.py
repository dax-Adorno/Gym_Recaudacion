from datetime import date

from moove_recovery.domain.billing_rules import (
    add_months,
    derive_student_status,
    enrollment_amount,
    first_due_date,
    monthly_due_date,
    notice_start,
    overdue_on,
)
from moove_recovery.domain.models import FeeStatusInput, StudentState


def test_weekend_due_becomes_overdue_the_following_monday() -> None:
    due = monthly_due_date(date(2026, 10, 1))
    assert due == date(2026, 10, 10)
    assert overdue_on(due) == date(2026, 10, 12)
    assert notice_start(due) == date(2026, 10, 7)
    sunday_due = monthly_due_date(date(2027, 1, 1))
    assert sunday_due == date(2027, 1, 10)
    assert overdue_on(sunday_due) == date(2027, 1, 11)


def test_notice_window_includes_weekend_and_overdue_starts_monday() -> None:
    current = FeeStatusInput(date(2026, 10, 10), 30_000, 0)
    assert (
        derive_student_status(
            active=True, today=date(2026, 10, 6), current_fee=current, fees=[current]
        ).state
        == StudentState.PENDING
    )
    assert (
        derive_student_status(
            active=True, today=date(2026, 10, 7), current_fee=current, fees=[current]
        ).state
        == StudentState.WARNING
    )
    for today in (date(2026, 10, 10), date(2026, 10, 11)):
        result = derive_student_status(
            active=True, today=today, current_fee=current, fees=[current]
        )
        assert result.state == StudentState.WARNING
    assert (
        derive_student_status(
            active=True,
            today=date(2026, 10, 12),
            current_fee=current,
            fees=[current],
        ).state
        == StudentState.OVERDUE
    )


def test_enrollment_discount_changes_after_day_twenty_and_only_first_period() -> None:
    base = 3_000_001
    full = enrollment_amount(base, date(2026, 10, 20), date(2026, 10, 1))
    half = enrollment_amount(base, date(2026, 10, 21), date(2026, 10, 1))
    following_month = enrollment_amount(base, date(2026, 10, 21), date(2026, 11, 1))
    assert full == (base, 0, None)
    assert half == (1_500_000, 1_500_001, "alta_50")
    assert following_month == (base, 0, None)


def test_first_due_uses_enrollment_day_only_when_after_effective_due() -> None:
    period = date(2026, 10, 1)
    assert first_due_date(date(2026, 10, 11), period) == date(2026, 10, 11)
    assert first_due_date(date(2026, 10, 10), period) == date(2026, 10, 10)
    assert first_due_date(date(2026, 10, 13), period) == date(2026, 10, 13)


def test_current_fee_does_not_hide_older_debt_and_missing_fee_is_not_paid() -> None:
    current = FeeStatusInput(date(2026, 11, 10), 30_000, 30_000)
    old = FeeStatusInput(date(2026, 9, 10), 30_000, 0)
    assert (
        derive_student_status(
            active=True, today=date(2026, 11, 1), current_fee=current, fees=[old, current]
        ).state
        == StudentState.OVERDUE
    )
    assert (
        derive_student_status(active=True, today=date(2026, 11, 1), current_fee=None, fees=[]).state
        == StudentState.MISSING_FEE
    )
    assert (
        derive_student_status(
            active=True, today=date(2026, 11, 1), current_fee=None, fees=[old]
        ).state
        == StudentState.OVERDUE
    )
    assert (
        derive_student_status(
            active=False, today=date(2026, 11, 1), current_fee=old, fees=[old]
        ).state
        == StudentState.INACTIVE
    )


def test_month_helpers_handle_year_boundary_and_leap_year() -> None:
    assert add_months(date(2026, 12, 31), 1) == date(2027, 1, 31)
    assert add_months(date(2027, 1, 31), 1) == date(2027, 2, 28)
    assert add_months(date(2028, 1, 31), 1) == date(2028, 2, 29)
