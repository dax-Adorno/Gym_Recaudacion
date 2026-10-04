from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel


def format_money(cents: int) -> str:
    formatted = f"{Decimal(cents) / 100:,.2f}"
    formatted = formatted.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"$ {formatted}"


def parse_money(value: str) -> int:
    cleaned = value.strip().replace("$", "").replace(" ", "")
    if not cleaned:
        raise ValueError("Ingresa un importe.")
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        amount = Decimal(cleaned).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation as error:
        raise ValueError("El importe no tiene un formato válido.") from error
    if not amount.is_finite() or amount <= 0:
        raise ValueError("El importe debe ser mayor a cero.")
    return int(amount * 100)


def make_label(text: str, object_name: str = "") -> QLabel:
    label = QLabel(text)
    if object_name:
        label.setObjectName(object_name)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label
