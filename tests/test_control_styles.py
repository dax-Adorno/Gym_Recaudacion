import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QPushButton, QTabWidget, QVBoxLayout, QWidget

from moove_recovery.ui.main_window import APP_STYLES


@pytest.mark.parametrize("role", ["primaryButton", "secondaryButton", "dangerButton"])
def test_button_hover_and_disabled_states_keep_size(qtbot, role):
    root = QWidget()
    root.setStyleSheet(APP_STYLES)
    layout = QVBoxLayout(root)
    button = QPushButton("Accion de prueba")
    button.setObjectName(role)
    button.setMinimumWidth(200)
    layout.addWidget(button)
    qtbot.addWidget(root)
    root.show()
    qtbot.mouseMove(root, QPoint(1, 1))
    QApplication.processEvents()
    size = button.size()
    normal = button.grab().toImage().pixelColor(15, 8)
    qtbot.mouseMove(button, QPoint(button.width() // 2, button.height() // 2))
    QApplication.processEvents()
    hovered = button.grab().toImage().pixelColor(15, 8)
    assert normal != hovered
    assert button.size() == size
    button.setEnabled(False)
    QApplication.processEvents()
    assert button.grab().toImage().pixelColor(15, 8) != hovered
    assert button.size() == size


def test_selected_tabs_have_contrasting_colors_without_resizing(qtbot):
    tabs = QTabWidget()
    tabs.setStyleSheet(APP_STYLES)
    tabs.addTab(QWidget(), "Pagados")
    tabs.addTab(QWidget(), "Pendientes")
    qtbot.addWidget(tabs)
    tabs.resize(500, 250)
    tabs.show()
    qtbot.mouseMove(tabs, QPoint(400, 200))
    QApplication.processEvents()
    bar = tabs.tabBar()
    rects = [bar.tabRect(index) for index in range(2)]
    snapshot = bar.grab().toImage()
    assert snapshot.pixelColor(rects[0].center().x(), 8).name() == "#215a40"
    assert snapshot.pixelColor(rects[1].center().x(), 8).name() == "#f1f5f8"
    tabs.setCurrentIndex(1)
    QApplication.processEvents()
    assert [bar.tabRect(index) for index in range(2)] == rects
    snapshot = bar.grab().toImage()
    assert snapshot.pixelColor(rects[1].center().x(), 8).name() == "#215a40"


def test_calendar_selected_day_keeps_dark_event_text(qtbot, environment):
    from datetime import date

    from moove_recovery.ui.calendar_page import CalendarPage

    service, owner = environment["service"], environment["owner"]
    service.save_expense(
        owner,
        concept="Servicio ficticio",
        category="Servicios",
        scheduled_on=date(2026, 10, 3),
        amount_cents=123456,
        paid_on=date(2026, 10, 3),
        method="efectivo",
    )
    page = CalendarPage(service, owner)
    page.setStyleSheet(APP_STYLES)
    qtbot.addWidget(page)
    page.resize(1000, 850)
    page.show()
    page.select_category("gastos")
    button = page.day_buttons[date(2026, 10, 3)]
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    assert button.isChecked()
    assert "1 evento" in button.text()
    for hovered in (False, True):
        qtbot.mouseMove(button if hovered else page, QPoint(10, 10))
        QApplication.processEvents()
        snapshot = button.grab().toImage()
        dark = sum(
            1
            for x in range(6, snapshot.width() - 6)
            for y in range(6, snapshot.height() - 6)
            if max(
                snapshot.pixelColor(x, y).red(),
                snapshot.pixelColor(x, y).green(),
                snapshot.pixelColor(x, y).blue(),
            )
            < 90
        )
        assert dark > 10
    assert page.events_table.rowCount() == 1
