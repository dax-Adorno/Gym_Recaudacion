from dataclasses import dataclass
from datetime import date
from enum import Enum


class Role(str, Enum):
    OWNER = "owner"
    EMPLOYEE = "employee"


class StudentState(str, Enum):
    INACTIVE = "inactivo"
    OVERDUE = "deudor"
    WARNING = "por_vencer"
    PENDING = "pendiente"
    CURRENT = "al_dia"
    MISSING_FEE = "sin_cuota"


@dataclass(frozen=True)
class Actor:
    id: int
    username: str
    full_name: str
    role: Role


@dataclass(frozen=True)
class FeeStatusInput:
    due_date: date
    amount_cents: int
    paid_cents: int


@dataclass(frozen=True)
class StudentStatus:
    state: StudentState
    label: str
    detail: str
