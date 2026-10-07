import pytest
from PySide6.QtWidgets import QHeaderView, QTableWidget

from moove_recovery.ui.responsive_header import ResponsiveHeader


@pytest.mark.parametrize("columns", [3, 4, 6])
def test_columns_fill_resized_table_and_stay_manually_adjustable(qtbot, columns):
    table = QTableWidget(1, columns)
    header = ResponsiveHeader(table)
    table.setHorizontalHeader(header)
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    header.setMinimumSectionSize(95)
    table.verticalHeader().hide()
    qtbot.addWidget(table)
    table.resize(700, 200)
    table.show()
    qtbot.waitUntil(lambda: header.length() == table.viewport().width())
    before = table.columnWidth(0)
    table.resize(920, 200)
    qtbot.waitUntil(lambda: header.length() == table.viewport().width())
    assert table.columnWidth(0) > before
    header.resizeSection(0, 350)
    assert table.columnWidth(0) == 350
    table.resize(800, 200)
    qtbot.waitUntil(lambda: header.length() == table.viewport().width())
    assert table.columnWidth(0) > table.columnWidth(1)
    table.resize(220, 200)
    qtbot.waitUntil(lambda: table.horizontalScrollBar().maximum() > 0)
    assert all(table.columnWidth(index) >= 95 for index in range(columns))
