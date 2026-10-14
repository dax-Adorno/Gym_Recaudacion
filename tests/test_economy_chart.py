from datetime import date

from conftest import add_student

from moove_recovery.ui.dashboard_page import DashboardPage


def test_paid_expense_without_dues_is_red_not_empty(qtbot, environment):
    service, owner = environment["service"], environment["owner"]
    service.save_expense(
        owner,
        concept="Servicio ficticio",
        category="Servicios",
        scheduled_on=date(2026, 10, 2),
        amount_cents=123456,
        paid_on=date(2026, 10, 2),
        method="efectivo",
    )
    service.save_expense(
        owner,
        concept="Pendiente ficticio",
        category="Servicios",
        scheduled_on=date(2026, 10, 10),
        amount_cents=750000,
    )
    page = DashboardPage(service, owner)
    qtbot.addWidget(page)
    page.show()
    assert page.chart.total_cents == 123456
    assert page.chart.applied_cents == 0
    assert page.chart.pending_cents == 123456
    assert page.empty_label.isHidden()
    assert "Gastos pagados" in page.pending_legend.text()
    assert page.net_value.text() == "$ -1.234,56"
    assert "#b14842" in page.net_value.styleSheet()
    pixmap = page.chart.grab().toImage()
    assert (
        pixmap.pixelColor(pixmap.width() // 2, pixmap.height() // 2 + 15)
        == page.chart.pending_color
    )
    page.chart_mode.setCurrentIndex(1)
    assert page.chart.total_cents == 0
    assert not page.empty_label.isHidden()


def test_equal_cobros_and_gastos_have_two_colors_and_zero_net(qtbot, environment):
    service, owner = environment["service"], environment["owner"]
    student = add_student(environment)
    service.generate_missing_dues()
    fee = service.list_students(owner)[0]["fees"][0]
    service.record_payment(
        owner,
        student_id=student,
        due_ids=[fee["id"]],
        total_cents=fee["amount_cents"],
        method="efectivo",
    )
    service.save_expense(
        owner,
        concept="Gasto ficticio",
        category="Servicios",
        scheduled_on=date(2026, 10, 3),
        amount_cents=fee["amount_cents"],
        paid_on=date(2026, 10, 3),
        method="efectivo",
    )
    page = DashboardPage(service, owner)
    qtbot.addWidget(page)
    page.show()
    assert page.chart.total_cents == fee["amount_cents"] * 2
    assert page.chart.applied_cents == page.chart.pending_cents
    assert page.summary["net_cents"] == 0
    pixmap = page.chart.grab().toImage()
    x, y = pixmap.width() // 2, pixmap.height() // 2
    colors = {pixmap.pixelColor(x - 30, y).name(), pixmap.pixelColor(x + 30, y).name()}
    assert colors == {page.chart.applied_color.name(), page.chart.pending_color.name()}
