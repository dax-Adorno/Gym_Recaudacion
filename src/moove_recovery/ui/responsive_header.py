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
        minimum = self.minimumSectionSize()
        sizes = [minimum] * len(widths)
        remaining = max(available, minimum * len(widths))
        active = list(range(len(widths)))
        while active:
            weight = sum(widths[index] for index in active)
            small = [index for index in active if remaining * widths[index] // weight < minimum]
            if not small:
                for index in active:
                    sizes[index] = remaining * widths[index] // weight
                sizes[active[-1]] += remaining - sum(sizes[index] for index in active)
                break
            for index in small:
                remaining -= minimum
                active.remove(index)
        self._resizing = True
        try:
            for index, size in enumerate(sizes):
                self.resizeSection(index, size)
        finally:
            self._resizing = False
