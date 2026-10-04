from __future__ import annotations

import json
import sqlite3
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from moove_recovery.domain.billing_rules import (
    derive_student_status,
    enrollment_amount,
    first_due_date,
    month_start,
    monthly_due_date,
    next_month,
)
from moove_recovery.domain.errors import (
    DomainError,
    DuplicatePayment,
    DuplicateStudent,
    PermissionDenied,
    ValidationError,
)
from moove_recovery.domain.models import Actor, FeeStatusInput, Role, StudentState
from moove_recovery.infrastructure.backups import BackupManager
from moove_recovery.infrastructure.database import Database
from moove_recovery.infrastructure.security import hash_password, verify_password

BUSINESS_FILTERS = {
    "Todos",
    "Al día",
    "Próximos a vencer",
    "Deudores",
    "Inactivos",
    "Pendientes",
}
PAYMENT_METHODS = {"efectivo", "transferencia", "debito", "credito", "otro"}


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char)).strip()


def normalize_dni(value: str) -> str:
    return "".join(char for char in normalize_text(value) if char.isalnum())


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class GymService:
    def __init__(
        self,
        database: Database,
        *,
        today: Callable[[], date] | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.db = database
        self.now = now or (lambda: datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")))
        self.today = today or (lambda: self.now().date())

    def initialize(self) -> None:
        self.db.migrate()

    def is_setup_complete(self) -> bool:
        row = self.db.fetch_one("SELECT value FROM settings WHERE key = 'setup_complete'")
        return bool(row and row[0] == "1")

    def setup_owner(
        self,
        *,
        full_name: str,
        username: str,
        password: str,
        prices_cents: Mapping[int, int],
    ) -> None:
        full_name = " ".join(full_name.split())
        username = username.strip()
        if not full_name or not username:
            raise ValidationError("Completa el nombre y el usuario del dueño.")
        if set(prices_cents) != {2, 3, 4} or any(value <= 0 for value in prices_cents.values()):
            raise ValidationError("Ingresa un precio real mayor a cero para cada plan.")
        password_hash = hash_password(password)
        now = self.now().isoformat(timespec="seconds")
        today = self.today()
        effective = month_start(today).isoformat()
        with self.db.transaction() as connection:
            if connection.execute("SELECT 1 FROM users LIMIT 1").fetchone():
                raise ValidationError("La configuración inicial ya fue realizada.")
            cursor = connection.execute(
                "INSERT INTO users(username, full_name, password_hash, role, created_at) "
                "VALUES (?, ?, ?, 'owner', ?)",
                (username, full_name, password_hash, now),
            )
            owner_id = _lastrowid(cursor)
            plans = connection.execute("SELECT id, sessions_per_week FROM plans").fetchall()
            for plan in plans:
                connection.execute(
                    "INSERT INTO plan_prices(plan_id, starts_on, amount_cents, created_by, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (plan["id"], effective, prices_cents[plan["sessions_per_week"]], owner_id, now),
                )
            connection.executemany(
                "INSERT INTO settings(key, value) VALUES (?, ?)",
                [
                    ("setup_complete", "1"),
                    ("operational_start", today.isoformat()),
                    ("business_timezone", "America/Argentina/Buenos_Aires"),
                ],
            )
            self._audit(connection, owner_id, "configuracion_inicial", "settings", None, {}, now)

    def login(self, username: str, password: str) -> Actor | None:
        row = self.db.fetch_one(
            "SELECT id, username, full_name, password_hash, role FROM users "
            "WHERE username = ? COLLATE NOCASE AND active = 1",
            (username.strip(),),
        )
        if row is None or not verify_password(str(row["password_hash"]), password):
            return None
        return Actor(int(row["id"]), str(row["username"]), str(row["full_name"]), Role(row["role"]))

    def create_employee(self, actor: Actor, *, full_name: str, username: str, password: str) -> int:
        self._require_owner(actor)
        full_name = " ".join(full_name.split())
        username = username.strip()
        if not full_name or not username:
            raise ValidationError("Completa el nombre y el usuario.")
        password_hash = hash_password(password)
        now = self.now().isoformat(timespec="seconds")
        with self.db.transaction() as connection:
            cursor = connection.execute(
                "INSERT INTO users(username, full_name, password_hash, role, created_at) "
                "VALUES (?, ?, ?, 'employee', ?)",
                (username, full_name, password_hash, now),
            )
            user_id = _lastrowid(cursor)
            self._audit(
                connection, actor.id, "usuario_alta", "users", user_id, {"role": "employee"}, now
            )
            return user_id

    def list_users(self, actor: Actor) -> list[dict[str, object]]:
        self._require_owner(actor)
        rows = self.db.fetch_all(
            "SELECT id, username, full_name, role, active, created_at FROM users ORDER BY role, full_name"
        )
        return [dict(row) for row in rows]

    def list_plans(self, actor: Actor | None = None) -> list[dict[str, object]]:
        if actor is not None:
            self._require_owner(actor)
        rows = self.db.fetch_all(
            "SELECT p.id, p.code, p.sessions_per_week, pp.amount_cents, pp.starts_on "
            "FROM plans p LEFT JOIN plan_prices pp ON pp.id = ("
            " SELECT p2.id FROM plan_prices p2 WHERE p2.plan_id = p.id ORDER BY p2.starts_on DESC LIMIT 1) "
            "WHERE p.active = 1 ORDER BY p.sessions_per_week"
        )
        return [dict(row) for row in rows]

    def get_dashboard_summary(self, actor: Actor, year: int, month: int) -> dict[str, object]:
        self._require_owner(actor)
        if not 1 <= year <= 9999 or not 1 <= month <= 12:
            raise ValidationError("Selecciona un mes y año válidos.")

        period = f"{year:04d}-{month:02d}"
        received = self.db.fetch_one(
            "SELECT COALESCE(SUM(total_cents), 0) FROM payments "
            "WHERE status = 'valid' AND substr(paid_at, 1, 7) = ?",
            (period,),
        )
        applied = self.db.fetch_one(
            "SELECT COALESCE(SUM(pd.amount_cents), 0) "
            "FROM payment_dues pd JOIN payments p ON p.id = pd.payment_id "
            "JOIN dues d ON d.id = pd.due_id "
            "WHERE p.status = 'valid' AND d.period = ?",
            (period,),
        )
        dues = self.db.fetch_one(
            "SELECT COUNT(*), COALESCE(SUM(d.amount_cents), 0), "
            "COALESCE(SUM(MAX(0, d.amount_cents - COALESCE(paid.paid_cents, 0))), 0) "
            "FROM dues d LEFT JOIN ("
            "SELECT pd.due_id, SUM(pd.amount_cents) AS paid_cents "
            "FROM payment_dues pd JOIN payments p ON p.id = pd.payment_id "
            "WHERE p.status = 'valid' GROUP BY pd.due_id"
            ") paid ON paid.due_id = d.id WHERE d.period = ?",
            (period,),
        )
        return {
            "period": period,
            "cutoff_date": self.today().isoformat(),
            "received_cents": int(received[0]) if received else 0,
            "applied_cents": int(applied[0]) if applied else 0,
            "pending_cents": int(dues[2]) if dues else 0,
            "period_total_cents": int(dues[1]) if dues else 0,
            "due_count": int(dues[0]) if dues else 0,
        }

    def get_monthly_report(self, actor: Actor, year: int, month: int) -> dict[str, object]:
        self._require_owner(actor)
        summary = self.get_dashboard_summary(actor, year, month)
        period = str(summary["period"])
        due_rows = self.db.fetch_all(
            "SELECT d.id, s.first_name || ' ' || s.last_name AS student_name, s.dni, s.phone, s.active, "
            "d.period, d.due_date, d.base_cents, d.discount_cents, d.discount_source, d.amount_cents, "
            "COALESCE((SELECT SUM(pd.amount_cents) FROM payment_dues pd "
            "JOIN payments p ON p.id = pd.payment_id "
            "WHERE pd.due_id = d.id AND p.status = 'valid'), 0) AS paid_cents "
            "FROM dues d JOIN students s ON s.id = d.student_id "
            "WHERE d.period = ? ORDER BY s.last_name_normalized, s.first_name_normalized",
            (period,),
        )
        payment_rows = self.db.fetch_all(
            "SELECT DISTINCT p.id, p.paid_at, p.total_cents, p.method, p.reference, p.status, "
            "p.void_reason, u.full_name AS created_by, "
            "(SELECT group_concat(period, ', ') FROM (SELECT DISTINCT d.period AS period "
            "FROM payment_dues pd JOIN dues d ON d.id = pd.due_id "
            "WHERE pd.payment_id = p.id ORDER BY d.period)) AS periods "
            "FROM payments p JOIN users u ON u.id = p.created_by "
            "WHERE substr(p.paid_at, 1, 7) = ? OR EXISTS ("
            "SELECT 1 FROM payment_dues pd JOIN dues d ON d.id = pd.due_id "
            "WHERE pd.payment_id = p.id AND d.period = ?) "
            "ORDER BY p.paid_at, p.id",
            (period, period),
        )
        dues = [
            {
                **dict(row),
                "paid_cents": int(row["paid_cents"]),
                "outstanding_cents": max(0, int(row["amount_cents"]) - int(row["paid_cents"])),
            }
            for row in due_rows
        ]
        payments = [
            {
                **dict(row),
                "paid_in_month": str(row["paid_at"])[:7] == period,
            }
            for row in payment_rows
        ]
        return {"summary": summary, "dues": dues, "payments": payments}

    def create_backup(self, actor: Actor, destination: Path) -> Path:
        self._require_owner(actor)
        return BackupManager(self.db).create_backup(destination)

    def restore_backup(self, actor: Actor, source_path: Path) -> Path:
        self._require_owner(actor)
        return BackupManager(self.db).restore_backup(source_path)

    def set_backup_retention(self, actor: Actor, count: int) -> None:
        self._require_owner(actor)
        BackupManager(self.db).set_retention_count(count)

    def available_plans(self) -> list[dict[str, object]]:
        rows = self.db.fetch_all(
            "SELECT id, code, sessions_per_week FROM plans WHERE active = 1 ORDER BY sessions_per_week"
        )
        return [dict(row) for row in rows]

    def set_plan_price(
        self, actor: Actor, plan_id: int, amount_cents: int, starts_on: date
    ) -> None:
        self._require_owner(actor)
        if amount_cents <= 0:
            raise ValidationError("El precio debe ser mayor a cero.")
        if starts_on.day != 1:
            raise ValidationError("La vigencia del precio debe comenzar el primer día de un mes.")
        if starts_on < next_month(month_start(self.today())):
            raise ValidationError(
                "Los cambios de precio rigen desde el mes próximo para conservar cuotas existentes."
            )
        now = self.now().isoformat(timespec="seconds")
        with self.db.transaction() as connection:
            exists = connection.execute(
                "SELECT 1 FROM plans WHERE id = ? AND active = 1", (plan_id,)
            ).fetchone()
            if exists is None:
                raise ValidationError("El plan seleccionado no existe.")
            previous = connection.execute(
                "SELECT amount_cents FROM plan_prices WHERE plan_id = ? AND starts_on = ?",
                (plan_id, starts_on.isoformat()),
            ).fetchone()
            connection.execute(
                "INSERT INTO plan_prices(plan_id, starts_on, amount_cents, created_by, created_at) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(plan_id, starts_on) "
                "DO UPDATE SET amount_cents = excluded.amount_cents, created_by = excluded.created_by, "
                "created_at = excluded.created_at",
                (plan_id, starts_on.isoformat(), amount_cents, actor.id, now),
            )
            self._audit(
                connection,
                actor.id,
                "precio_actualizado",
                "plans",
                plan_id,
                {
                    "previous_cents": int(previous["amount_cents"]) if previous else None,
                    "amount_cents": amount_cents,
                    "starts_on": starts_on.isoformat(),
                },
                now,
            )

    def create_student(
        self,
        actor: Actor,
        *,
        first_name: str,
        last_name: str,
        dni: str,
        phone: str,
        activity: str,
        enrolled_on: date,
        plan_id: int,
        notes: str = "",
    ) -> int:
        if actor.role not in {Role.OWNER, Role.EMPLOYEE}:
            raise PermissionDenied("No tienes permiso para dar de alta alumnos.")
        first_name = " ".join(first_name.split())
        last_name = " ".join(last_name.split())
        dni = dni.strip()
        dni_normalized = normalize_dni(dni)
        phone = phone.strip()
        activity = " ".join(activity.split())
        if not first_name or not last_name or not dni_normalized or not phone or not activity:
            raise ValidationError("Nombre, apellido, DNI, teléfono y actividad son obligatorios.")
        today = self.today()
        if enrolled_on > today:
            raise ValidationError("La fecha de alta no puede ser futura.")
        now = self.now().isoformat(timespec="seconds")
        with self.db.transaction() as connection:
            plan = connection.execute(
                "SELECT id FROM plans WHERE id = ? AND active = 1", (plan_id,)
            ).fetchone()
            if plan is None:
                raise ValidationError("Selecciona un plan existente.")
            existing = connection.execute(
                "SELECT id, active FROM students WHERE dni_normalized = ?", (dni_normalized,)
            ).fetchone()
            if existing:
                raise DuplicateStudent(int(existing["id"]), bool(existing["active"]))
            cursor = connection.execute(
                "INSERT INTO students(first_name, first_name_normalized, last_name, last_name_normalized, "
                "dni, dni_normalized, phone, enrolled_on, activity, plan_id, notes, created_by, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    first_name,
                    normalize_text(first_name),
                    last_name,
                    normalize_text(last_name),
                    dni,
                    dni_normalized,
                    phone,
                    enrolled_on.isoformat(),
                    activity,
                    plan_id,
                    notes.strip(),
                    actor.id,
                    now,
                ),
            )
            student_id = _lastrowid(cursor)
            connection.execute(
                "INSERT INTO student_history(student_id, event_type, event_date, payload, actor_id, created_at) "
                "VALUES (?, 'alta', ?, '{}', ?, ?)",
                (student_id, enrolled_on.isoformat(), actor.id, now),
            )
            self._audit(connection, actor.id, "alumno_alta", "students", student_id, {}, now)
            return student_id

    def update_student_details(
        self,
        actor: Actor,
        student_id: int,
        *,
        first_name: str,
        last_name: str,
        dni: str,
        phone: str,
        activity: str,
        notes: str,
    ) -> None:
        self._require_owner(actor)
        first_name = " ".join(first_name.split())
        last_name = " ".join(last_name.split())
        dni_normalized = normalize_dni(dni)
        activity = " ".join(activity.split())
        if (
            not first_name
            or not last_name
            or not dni_normalized
            or not phone.strip()
            or not activity
        ):
            raise ValidationError("Nombre, apellido, DNI, teléfono y actividad son obligatorios.")
        now = self.now().isoformat(timespec="seconds")
        with self.db.transaction() as connection:
            duplicate = connection.execute(
                "SELECT id, active FROM students WHERE dni_normalized = ? AND id != ?",
                (dni_normalized, student_id),
            ).fetchone()
            if duplicate:
                raise DuplicateStudent(int(duplicate["id"]), bool(duplicate["active"]))
            updated = connection.execute(
                "UPDATE students SET first_name = ?, first_name_normalized = ?, last_name = ?, "
                "last_name_normalized = ?, dni = ?, dni_normalized = ?, phone = ?, activity = ?, "
                "notes = ? WHERE id = ?",
                (
                    first_name,
                    normalize_text(first_name),
                    last_name,
                    normalize_text(last_name),
                    dni.strip(),
                    dni_normalized,
                    phone.strip(),
                    activity,
                    notes.strip(),
                    student_id,
                ),
            )
            if updated.rowcount != 1:
                raise ValidationError("El alumno ya no existe.")
            self._audit(connection, actor.id, "alumno_edicion", "students", student_id, {}, now)

    def deactivate_student(self, actor: Actor, student_id: int) -> None:
        self._require_owner(actor)
        today = self.today()
        now = self.now().isoformat(timespec="seconds")
        with self.db.transaction() as connection:
            row = connection.execute(
                "SELECT active FROM students WHERE id = ?", (student_id,)
            ).fetchone()
            if row is None:
                raise ValidationError("El alumno no existe.")
            if not row["active"]:
                return
            connection.execute(
                "UPDATE students SET active = 0, inactive_on = ? WHERE id = ?",
                (today.isoformat(), student_id),
            )
            connection.execute(
                "INSERT INTO student_history(student_id, event_type, event_date, payload, actor_id, created_at) "
                "VALUES (?, 'baja', ?, '{}', ?, ?)",
                (student_id, today.isoformat(), actor.id, now),
            )
            self._audit(connection, actor.id, "alumno_baja", "students", student_id, {}, now)
        self.generate_missing_dues()

    def reactivate_student(self, actor: Actor, student_id: int) -> None:
        self._require_owner(actor)
        raise DomainError(
            "Reactivación pendiente de definición: hace falta acordar primera cuota e inactividad."
        )

    def generate_missing_dues(
        self, *, through: date | None = None, student_id: int | None = None
    ) -> dict[str, int]:
        today = self.today()
        now = self.now().isoformat(timespec="seconds")
        counts = {"created": 0, "without_price": 0}
        with self.db.transaction() as connection:
            start_row = connection.execute(
                "SELECT value FROM settings WHERE key = 'operational_start'"
            ).fetchone()
            if start_row is None:
                return counts
            operational_start = date.fromisoformat(start_row[0])
            students = connection.execute(
                "SELECT * FROM students WHERE id = ?"
                if student_id is not None
                else "SELECT * FROM students",
                (student_id,) if student_id is not None else (),
            ).fetchall()
            for student in students:
                enrollment = date.fromisoformat(student["enrolled_on"])
                lower = max(month_start(enrollment), month_start(operational_start))
                upper = month_start(through or today)
                inactive_on = (
                    date.fromisoformat(student["inactive_on"]) if student["inactive_on"] else None
                )
                if inactive_on:
                    upper = min(upper, month_start(inactive_on))
                period = lower
                while period <= upper:
                    exists = connection.execute(
                        "SELECT 1 FROM dues WHERE student_id = ? AND period = ?",
                        (student["id"], period.strftime("%Y-%m")),
                    ).fetchone()
                    if not exists:
                        price = connection.execute(
                            "SELECT pp.amount_cents FROM plan_prices pp "
                            "WHERE pp.plan_id = ? AND pp.starts_on <= ? ORDER BY pp.starts_on DESC LIMIT 1",
                            (student["plan_id"], period.isoformat()),
                        ).fetchone()
                        if price is None:
                            counts["without_price"] += 1
                        else:
                            base = int(price["amount_cents"])
                            first_operational_charge = (
                                period == month_start(enrollment)
                                and enrollment >= operational_start
                            )
                            amount, discount, source = (
                                enrollment_amount(base, enrollment, period)
                                if first_operational_charge
                                else (base, 0, None)
                            )
                            due = (
                                first_due_date(enrollment, period)
                                if first_operational_charge
                                else monthly_due_date(period)
                            )
                            connection.execute(
                                "INSERT INTO dues(student_id, plan_id, period, due_date, base_cents, "
                                "discount_cents, amount_cents, discount_source, created_at) "
                                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (
                                    student["id"],
                                    student["plan_id"],
                                    period.strftime("%Y-%m"),
                                    due.isoformat(),
                                    base,
                                    discount,
                                    amount,
                                    source,
                                    now,
                                ),
                            )
                            counts["created"] += 1
                    period = next_month(period)
        return counts

    def prepare_future_dues(self, actor: Actor, student_id: int, through: date) -> dict[str, int]:
        if actor.role not in {Role.OWNER, Role.EMPLOYEE}:
            raise PermissionDenied("No tienes permiso para preparar cuotas.")
        through = month_start(through)
        current_period = month_start(self.today())
        if through < current_period:
            raise ValidationError("Selecciona el mes actual o uno futuro.")
        student = self.db.fetch_one("SELECT active FROM students WHERE id = ?", (student_id,))
        if student is None:
            raise DomainError("No se encontró el alumno seleccionado.")
        if through > current_period and not student["active"]:
            raise DomainError("No se pueden generar cuotas futuras para un alumno inactivo.")
        return self.generate_missing_dues(through=through, student_id=student_id)

    def list_students(
        self, actor: Actor, *, query: str = "", filter_name: str = "Todos"
    ) -> list[dict[str, object]]:
        if filter_name not in BUSINESS_FILTERS:
            raise ValidationError("Filtro de alumnos desconocido.")
        today = self.today()
        current_period = today.strftime("%Y-%m")
        conditions: list[str] = []
        params: list[object] = []
        normalized_query = normalize_text(query)
        if normalized_query:
            needle = f"%{_escape_like(normalized_query)}%"
            conditions.append(
                "(s.first_name_normalized LIKE ? ESCAPE '\\' OR s.last_name_normalized LIKE ? ESCAPE '\\' "
                "OR s.dni_normalized LIKE ? ESCAPE '\\')"
            )
            params.extend((needle, needle, f"%{_escape_like(normalize_dni(query))}%"))
        if filter_name == "Inactivos":
            conditions.append("s.active = 0")
        elif filter_name != "Todos":
            conditions.append("s.active = 1")
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        rows = self.db.fetch_all(
            "SELECT s.*, p.code AS plan_code, p.sessions_per_week, "
            "d.id AS due_id, d.period, d.due_date, d.base_cents, d.discount_cents, d.amount_cents, "
            "d.discount_source, "
            "COALESCE(SUM(CASE WHEN pay.status = 'valid' THEN pd.amount_cents ELSE 0 END), 0) AS paid_cents "
            "FROM students s JOIN plans p ON p.id = s.plan_id "
            "LEFT JOIN dues d ON d.student_id = s.id "
            "LEFT JOIN payment_dues pd ON pd.due_id = d.id "
            "LEFT JOIN payments pay ON pay.id = pd.payment_id "
            + where
            + " GROUP BY s.id, d.id ORDER BY s.active DESC, s.last_name_normalized, s.first_name_normalized, d.period",
            tuple(params),
        )
        grouped: dict[int, dict[str, object]] = {}
        fees_by_student: dict[int, list[FeeStatusInput]] = {}
        current_by_student: dict[int, FeeStatusInput | None] = {}
        for row in rows:
            student_id = int(row["id"])
            if student_id not in grouped:
                grouped[student_id] = {
                    "id": student_id,
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "full_name": f"{row['first_name']} {row['last_name']}",
                    "dni": row["dni"],
                    "phone": row["phone"],
                    "activity": row["activity"],
                    "enrolled_on": row["enrolled_on"],
                    "plan_id": row["plan_id"],
                    "plan_code": row["plan_code"],
                    "sessions_per_week": row["sessions_per_week"],
                    "notes": row["notes"],
                    "active": bool(row["active"]),
                    "inactive_on": row["inactive_on"],
                    "fees": [],
                }
                fees_by_student[student_id] = []
                current_by_student[student_id] = None
            if row["due_id"] is not None:
                fee = FeeStatusInput(
                    date.fromisoformat(row["due_date"]),
                    int(row["amount_cents"]),
                    int(row["paid_cents"]),
                )
                fees_by_student[student_id].append(fee)
                if row["period"] == current_period:
                    current_by_student[student_id] = fee
                student_fees = grouped[student_id]["fees"]
                if not isinstance(student_fees, list):
                    raise RuntimeError("Estado interno de cuotas inválido.")
                student_fees.append(
                    {
                        "id": int(row["due_id"]),
                        "period": row["period"],
                        "due_date": row["due_date"],
                        "base_cents": row["base_cents"],
                        "discount_cents": row["discount_cents"],
                        "amount_cents": row["amount_cents"],
                        "discount_source": row["discount_source"],
                        "paid_cents": row["paid_cents"],
                        "outstanding_cents": max(
                            0, int(row["amount_cents"]) - int(row["paid_cents"])
                        ),
                    }
                )
        result = []
        state_filters = {
            "Al día": StudentState.CURRENT,
            "Próximos a vencer": StudentState.WARNING,
            "Deudores": StudentState.OVERDUE,
            "Pendientes": StudentState.PENDING,
        }
        for student_id, item in grouped.items():
            status = derive_student_status(
                active=bool(item["active"]),
                today=today,
                current_fee=current_by_student[student_id],
                fees=fees_by_student[student_id],
            )
            item["state"] = status.state.value
            item["state_label"] = status.label
            item["state_detail"] = status.detail
            if filter_name in state_filters and status.state != state_filters[filter_name]:
                continue
            result.append(item)
        return result

    def record_payment(
        self,
        actor: Actor,
        *,
        student_id: int,
        due_ids: Sequence[int],
        total_cents: int,
        method: str,
        reference: str = "",
        idempotency_key: str | None = None,
    ) -> int:
        if actor.role not in {Role.OWNER, Role.EMPLOYEE}:
            raise PermissionDenied("No tienes permiso para registrar cobros.")
        unique_due_ids = list(dict.fromkeys(int(value) for value in due_ids))
        if not unique_due_ids:
            raise ValidationError("Selecciona al menos una cuota completa.")
        if total_cents <= 0:
            raise ValidationError("El total debe ser mayor a cero.")
        if method not in PAYMENT_METHODS:
            raise ValidationError("Selecciona un medio de pago válido.")
        key = idempotency_key or str(uuid4())
        now = self.now()
        now_text = now.isoformat(timespec="seconds")
        with self.db.transaction() as connection:
            existing_payment = connection.execute(
                "SELECT id, total_cents, status, method, reference FROM payments "
                "WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
            if existing_payment:
                existing_rows = connection.execute(
                    "SELECT pd.due_id FROM payment_dues pd WHERE pd.payment_id = ? ORDER BY pd.due_id",
                    (existing_payment["id"],),
                ).fetchall()
                if (
                    int(existing_payment["total_cents"]) == total_cents
                    and existing_payment["status"] == "valid"
                    and existing_payment["method"] == method
                    and existing_payment["reference"] == reference.strip()
                    and [int(row[0]) for row in existing_rows] == sorted(unique_due_ids)
                ):
                    return int(existing_payment["id"])
                raise DuplicatePayment("La clave de operación ya fue utilizada para otro cobro.")
            placeholders = ",".join("?" for _ in unique_due_ids)
            rows = connection.execute(
                "SELECT d.id, d.student_id, d.amount_cents, "
                "COALESCE(SUM(CASE WHEN p.status = 'valid' THEN pd.amount_cents ELSE 0 END), 0) AS paid_cents "
                "FROM dues d LEFT JOIN payment_dues pd ON pd.due_id = d.id "
                "LEFT JOIN payments p ON p.id = pd.payment_id "
                f"WHERE d.id IN ({placeholders}) GROUP BY d.id",
                tuple(unique_due_ids),
            ).fetchall()
            if len(rows) != len(unique_due_ids) or any(
                int(row["student_id"]) != student_id for row in rows
            ):
                raise ValidationError("Una de las cuotas seleccionadas no pertenece a este alumno.")
            if any(int(row["paid_cents"]) != 0 for row in rows):
                raise ValidationError("Una cuota seleccionada ya tiene un cobro aplicado.")
            expected = sum(int(row["amount_cents"]) for row in rows)
            if expected != total_cents:
                raise ValidationError(
                    "El total debe coincidir con las cuotas completas seleccionadas."
                )
            cursor = connection.execute(
                "INSERT INTO payments(idempotency_key, paid_at, total_cents, method, reference, created_by, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (key, now_text, total_cents, method, reference.strip(), actor.id, now_text),
            )
            payment_id = _lastrowid(cursor)
            for row in rows:
                connection.execute(
                    "INSERT INTO payment_dues(payment_id, due_id, amount_cents) VALUES (?, ?, ?)",
                    (payment_id, row["id"], row["amount_cents"]),
                )
            self._audit(
                connection,
                actor.id,
                "cobro_registrado",
                "payments",
                payment_id,
                {"student_id": student_id, "due_ids": unique_due_ids, "total_cents": total_cents},
                now_text,
            )
            return payment_id

    def list_student_history(self, actor: Actor, student_id: int) -> list[dict[str, object]]:
        rows = self.db.fetch_all(
            "SELECT 'cuota' AS kind, d.id AS id, d.period AS date, d.amount_cents AS amount_cents, "
            "d.due_date AS detail, d.discount_source AS extra, "
            "COALESCE(SUM(CASE WHEN p.status = 'valid' THEN pd.amount_cents ELSE 0 END), 0) AS paid_cents, "
            "NULL AS void_reason "
            "FROM dues d LEFT JOIN payment_dues pd ON pd.due_id = d.id "
            "LEFT JOIN payments p ON p.id = pd.payment_id WHERE d.student_id = ? GROUP BY d.id "
            "UNION ALL "
            "SELECT DISTINCT 'pago', p.id, p.paid_at, p.total_cents, p.method, p.status, 0, p.void_reason "
            "FROM payments p JOIN payment_dues pd ON pd.payment_id = p.id "
            "JOIN dues d ON d.id = pd.due_id WHERE d.student_id = ? "
            "UNION ALL "
            "SELECT 'movimiento', h.id, h.event_date, 0, h.event_type, h.payload, 0, NULL "
            "FROM student_history h WHERE h.student_id = ? "
            "ORDER BY date DESC, id DESC",
            (student_id, student_id, student_id),
        )
        return [dict(row) for row in rows]

    def void_payment(self, actor: Actor, payment_id: int, reason: str) -> None:
        self._require_owner(actor)
        reason = " ".join(reason.split())
        if not reason:
            raise ValidationError("Indica el motivo de la anulación.")
        if len(reason) > 500:
            raise ValidationError("El motivo no puede superar los 500 caracteres.")
        now_text = self.now().isoformat(timespec="seconds")
        with self.db.transaction() as connection:
            payment = connection.execute(
                "SELECT status FROM payments WHERE id = ?", (payment_id,)
            ).fetchone()
            if payment is None:
                raise DomainError("No se encontró el cobro seleccionado.")
            if payment["status"] != "valid":
                raise DomainError("Este cobro ya fue anulado.")
            due_ids = [
                int(row[0])
                for row in connection.execute(
                    "SELECT due_id FROM payment_dues WHERE payment_id = ? ORDER BY due_id",
                    (payment_id,),
                ).fetchall()
            ]
            connection.execute(
                "UPDATE payments SET status = 'voided', void_reason = ? "
                "WHERE id = ? AND status = 'valid'",
                (reason, payment_id),
            )
            self._audit(
                connection,
                actor.id,
                "cobro_anulado",
                "payments",
                payment_id,
                {"reason": reason, "due_ids": due_ids},
                now_text,
            )

    def _require_owner(self, actor: Actor) -> None:
        if actor.role != Role.OWNER:
            raise PermissionDenied("Esta acción está reservada al dueño.")

    @staticmethod
    def _audit(
        connection: sqlite3.Connection,
        actor_id: int,
        action: str,
        entity: str,
        entity_id: int | None,
        details: dict[str, object],
        created_at: str,
    ) -> None:
        connection.execute(
            "INSERT INTO audit_log(actor_id, action, entity_type, entity_id, details, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                actor_id,
                action,
                entity,
                entity_id,
                json.dumps(details, ensure_ascii=True),
                created_at,
            ),
        )


def _lastrowid(cursor: sqlite3.Cursor) -> int:
    if cursor.lastrowid is None:
        raise RuntimeError("SQLite no devolvió el identificador de la fila insertada.")
    return cursor.lastrowid
