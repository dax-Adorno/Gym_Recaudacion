from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from moove_recovery.application.service import GymService
from moove_recovery.domain.models import Actor
from moove_recovery.ui.common import format_money, make_label

MONTHS = (
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)


class PeriodPie(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.applied_cents = 0
        self.pending_cents = 0
        self.total_cents = 0
        self.applied_color = QColor("#28734f")
        self.pending_color = QColor("#c75a53")
        self.setMinimumSize(190, 190)
        self.setAccessibleName("Gráfico de cobrado aplicado y pendiente")

    def set_values(self, applied_cents: int, pending_cents: int, total_cents: int) -> None:
        self.applied_cents = applied_cents
        self.pending_cents = pending_cents
        self.total_cents = total_cents
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        diameter = min(self.width(), self.height()) - 16
        pie = self.rect().adjusted(
            (self.width() - diameter) // 2,
            (self.height() - diameter) // 2,
            -(self.width() - diameter) // 2,
            -(self.height() - diameter) // 2,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        if self.total_cents <= 0:
            painter.setBrush(Qt.GlobalColor.lightGray)
            painter.drawEllipse(pie)
            return
        painter.setBrush(self.pending_color)
        painter.drawPie(pie, 90 * 16, -360 * 16)
        applied_angle = round(360 * 16 * self.applied_cents / self.total_cents)
        if applied_angle:
            painter.setBrush(self.applied_color)
            painter.drawPie(pie, 90 * 16, -applied_angle)


class DashboardPage(QWidget):
    def __init__(self, service: GymService, actor: Actor) -> None:
        super().__init__()
        self.service = service
        self.actor = actor
        self.summary: dict[str, object] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(16)
        layout.addWidget(make_label("Panel de cobranzas", "pageTitle"))

        period_controls = QHBoxLayout()
        period_controls.addWidget(make_label("Período"))
        self.month = QComboBox()
        for index, month in enumerate(MONTHS, start=1):
            self.month.addItem(month, index)
        self.year = QSpinBox()
        self.year.setRange(1, 9999)
        self.year.setGroupSeparatorShown(False)
        today = service.today()
        self.month.setCurrentIndex(today.month - 1)
        self.year.setValue(today.year)
        self.month.setAccessibleName("Mes del informe")
        self.year.setAccessibleName("Año del informe")
        period_controls.addWidget(self.month)
        period_controls.addWidget(self.year)
        period_controls.addStretch(1)
        layout.addLayout(period_controls)

        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        self.received_value = self._metric(metrics, "Recibido en el mes")
        self.applied_value = self._metric(metrics, "Aplicado a cuotas del período")
        self.pending_value = self._metric(metrics, "Pendiente del período")
        layout.addLayout(metrics)

        breakdown = QHBoxLayout()
        breakdown.setSpacing(22)
        chart_column = QVBoxLayout()
        chart_column.addWidget(make_label("Cuotas del período", "sectionTitle"))
        self.chart = PeriodPie()
        chart_column.addWidget(self.chart, 1, Qt.AlignmentFlag.AlignLeft)
        breakdown.addLayout(chart_column)

        legend = QVBoxLayout()
        self.applied_legend = make_label("")
        self.pending_legend = make_label("")
        self.total_legend = make_label("")
        self.applied_legend.setStyleSheet("color: #28734f; font-weight: 600")
        self.pending_legend.setStyleSheet("color: #b14842; font-weight: 600")
        legend.addWidget(self.applied_legend)
        legend.addWidget(self.pending_legend)
        legend.addWidget(self.total_legend)
        legend.addStretch(1)
        breakdown.addLayout(legend, 1)
        layout.addLayout(breakdown, 1)
        self.empty_label = make_label("Sin cuotas registradas", "muted")
        layout.addWidget(self.empty_label)
        self.cutoff_label = make_label("")
        layout.addWidget(self.cutoff_label)

        self.month.currentIndexChanged.connect(self.refresh)
        self.year.valueChanged.connect(self.refresh)
        self.refresh()

    @staticmethod
    def _metric(layout: QHBoxLayout, title: str) -> QLabel:
        frame = QFrame()
        frame.setObjectName("detailPanel")
        content = QVBoxLayout(frame)
        content.setContentsMargins(12, 10, 12, 10)
        content.addWidget(make_label(title, "muted"))
        value = make_label("$ 0,00", "kpiValue")
        content.addWidget(value)
        layout.addWidget(frame, 1)
        return value

    def refresh(self, *_args: object) -> None:
        summary = self.service.get_dashboard_summary(
            self.actor, self.year.value(), int(self.month.currentData())
        )
        self.summary = summary
        applied = int(summary["applied_cents"])
        pending = int(summary["pending_cents"])
        total = int(summary["period_total_cents"])
        self.received_value.setText(format_money(int(summary["received_cents"])))
        self.applied_value.setText(format_money(applied))
        self.pending_value.setText(format_money(pending))
        self.chart.set_values(applied, pending, total)
        self.applied_legend.setText(f"Cobrado aplicado: {format_money(applied)}")
        self.pending_legend.setText(f"Pendiente: {format_money(pending)}")
        self.total_legend.setText(f"Total de cuotas: {format_money(total)}")
        self.empty_label.setVisible(total == 0)
        self.chart.setAccessibleDescription(
            f"Cobrado aplicado {format_money(applied)}; pendiente {format_money(pending)}; "
            f"total de cuotas {format_money(total)}."
        )
        cutoff = date.fromisoformat(str(summary["cutoff_date"]))
        self.cutoff_label.setText(
            f"Corte: {cutoff.strftime('%d/%m/%Y')} · estado actual del período"
        )
