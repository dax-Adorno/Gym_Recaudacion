from PySide6.QtCore import Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QHeaderView, QWidget


class ResponsiveHeader(QHeaderView):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._resizing = False

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._resizing or event.size().width() == event.oldSize().width() or not self.count():
            return
        available = self.viewport().width()
        widths = [self.sectionSize(index) for index in range(self.count())]
        total = sum(widths)
        if available <= 0 or total <= 0:
            return
        sizes = [max(self.minimumSectionSize(), available * width // total) for width in widths]
        if sum(sizes) < available:
            sizes[-1] += available - sum(sizes)
        self._resizing = True
        try:
            for index, size in enumerate(sizes):
                self.resizeSection(index, size)
        finally:
            self._resizing = False
