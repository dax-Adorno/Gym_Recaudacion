from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

SCHEMA_VERSION = 1

MIGRATION_1 = """
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('owner', 'employee')),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX one_owner_per_database ON users(role) WHERE role = 'owner';

CREATE TABLE plans (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    sessions_per_week INTEGER NOT NULL UNIQUE CHECK (sessions_per_week IN (2, 3, 4)),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);
INSERT INTO plans(code, sessions_per_week) VALUES ('2x', 2), ('3x', 3), ('4x', 4);

CREATE TABLE plan_prices (
    id INTEGER PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES plans(id),
    starts_on TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    UNIQUE(plan_id, starts_on)
);

CREATE TABLE students (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    first_name_normalized TEXT NOT NULL,
    last_name TEXT NOT NULL,
    last_name_normalized TEXT NOT NULL,
    dni TEXT NOT NULL,
    dni_normalized TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL,
    enrolled_on TEXT NOT NULL,
    activity TEXT NOT NULL,
    plan_id INTEGER NOT NULL REFERENCES plans(id),
    notes TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    inactive_on TEXT,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    CHECK ((active = 1 AND inactive_on IS NULL) OR active = 0)
);
CREATE INDEX students_name_search ON students(last_name COLLATE NOCASE, first_name COLLATE NOCASE);
CREATE INDEX students_active ON students(active);

CREATE TABLE student_history (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id),
    event_type TEXT NOT NULL,
    event_date TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    actor_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL
);

CREATE TABLE dues (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id),
    plan_id INTEGER NOT NULL REFERENCES plans(id),
    period TEXT NOT NULL,
    due_date TEXT NOT NULL,
    base_cents INTEGER NOT NULL CHECK (base_cents > 0),
    discount_cents INTEGER NOT NULL DEFAULT 0 CHECK (discount_cents >= 0),
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    discount_source TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(student_id, period),
    CHECK (base_cents - discount_cents = amount_cents)
);
CREATE INDEX dues_student_period ON dues(student_id, period);
CREATE INDEX dues_due_date ON dues(due_date);

CREATE TABLE payments (
    id INTEGER PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    paid_at TEXT NOT NULL,
    total_cents INTEGER NOT NULL CHECK (total_cents > 0),
    method TEXT NOT NULL CHECK (method IN ('efectivo', 'transferencia', 'debito', 'credito', 'otro')),
    reference TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'valid' CHECK (status IN ('valid', 'voided')),
    void_reason TEXT,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL
);

CREATE TABLE payment_dues (
    payment_id INTEGER NOT NULL REFERENCES payments(id),
    due_id INTEGER NOT NULL REFERENCES dues(id),
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    PRIMARY KEY(payment_id, due_id)
);
CREATE INDEX payment_dues_due ON payment_dues(due_id);

CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY,
    actor_id INTEGER NOT NULL REFERENCES users(id),
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    details TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def migrate(self) -> None:
        with self.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise RuntimeError("La base de datos fue creada por una versión más nueva.")
            if version < 1:
                try:
                    connection.executescript(
                        "BEGIN IMMEDIATE;\n" + MIGRATION_1 + "\nPRAGMA user_version = 1;\nCOMMIT;"
                    )
                except Exception:
                    connection.rollback()
                    raise

    @contextmanager
    def transaction(self, *, immediate: bool = True) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def fetch_all(self, sql: str, params: tuple[object, ...] = ()) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return list(connection.execute(sql, params).fetchall())

    def fetch_one(self, sql: str, params: tuple[object, ...] = ()) -> sqlite3.Row | None:
        with self.connect() as connection:
            return cast(sqlite3.Row | None, connection.execute(sql, params).fetchone())

    def integrity_check(self) -> str:
        row = self.fetch_one("PRAGMA integrity_check")
        return str(row[0]) if row else "sin resultado"
