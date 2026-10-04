from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest
from conftest import add_student

from moove_recovery.domain.errors import PermissionDenied
from moove_recovery.infrastructure import backups as backups_module
from moove_recovery.infrastructure.backups import BackupError, BackupManager
from moove_recovery.infrastructure.database import SCHEMA_VERSION


def test_daily_backup_is_idempotent_and_rotates_to_thirty(environment, tmp_path) -> None:
    manager = BackupManager(environment["db"], tmp_path / "backups")
    assert manager.retention_count() == 30
    start = date(2026, 8, 1)
    for offset in range(31):
        day = start + timedelta(days=offset)
        manager.create_backup(
            manager.backup_directory / f"moove-auto-{day.isoformat()}-120000.sqlite3"
        )

    today = date(2026, 10, 3)
    created = manager.create_daily_backup(today)
    assert created is not None and created.exists()
    assert manager.create_daily_backup(today) is None
    automatic = manager.automatic_backups()
    assert len(automatic) == 30
    assert created.name == automatic[0]["name"]
    assert manager.last_result()["backup_last_result"] == "Copia verificada"


def test_owner_can_configure_backup_retention_and_prune(environment, tmp_path) -> None:
    service = environment["service"]
    owner = environment["owner"]
    manager = BackupManager(environment["db"], tmp_path / "backups")
    start = date(2026, 8, 1)
    for offset in range(7):
        day = start + timedelta(days=offset)
        manager.create_backup(
            manager.backup_directory / f"moove-auto-{day.isoformat()}-120000.sqlite3"
        )

    service.set_backup_retention(owner, 5)

    assert manager.retention_count() == 5
    assert len(manager.automatic_backups()) == 5
    assert len(list(manager.backup_directory.glob("moove-auto-*.sqlite3"))) == 5


def test_backup_retention_rejects_invalid_values_and_non_owner(environment, tmp_path) -> None:
    service = environment["service"]
    manager = BackupManager(environment["db"], tmp_path / "backups")
    with pytest.raises(BackupError, match="entre 1 y 3650"):
        manager.set_retention_count(0)
    with pytest.raises(BackupError, match="entre 1 y 3650"):
        manager.set_retention_count(3651)

    service.create_employee(
        environment["owner"],
        full_name="Empleado Retención",
        username="empleado-retencion",
        password="ClaveEmpleado-Retencion",
    )
    employee = service.login("empleado-retencion", "ClaveEmpleado-Retencion")
    assert employee is not None
    with pytest.raises(PermissionDenied):
        service.set_backup_retention(employee, 10)


def test_restore_creates_safety_copy_and_replaces_database(environment, tmp_path) -> None:
    service = environment["service"]
    owner = environment["owner"]
    original_id = add_student(environment, dni="10.000.001")
    manager = BackupManager(environment["db"], tmp_path / "backups")
    snapshot = manager.create_backup(tmp_path / "external" / "gym.sqlite3")
    add_student(environment, name="Posterior", dni="10.000.002")

    safety_copy = manager.restore_backup(snapshot)

    students = service.list_students(owner)
    assert [student["id"] for student in students] == [original_id]
    assert safety_copy.exists()
    manager.validate_backup(safety_copy)
    assert environment["db"].integrity_check() == "ok"
    assert "Restauración validada" in manager.last_result()["backup_last_result"]


def test_invalid_backup_never_changes_active_database(environment, tmp_path) -> None:
    student_id = add_student(environment)
    invalid = tmp_path / "not-a-backup.sqlite3"
    invalid.write_bytes(b"not a SQLite database")
    manager = BackupManager(environment["db"], tmp_path / "backups")

    with pytest.raises(BackupError, match="no es una copia válida"):
        manager.restore_backup(invalid)

    students = environment["service"].list_students(environment["owner"])
    assert [student["id"] for student in students] == [student_id]
    assert environment["db"].integrity_check() == "ok"


def test_incompatible_schema_is_rejected_before_restore(environment, tmp_path) -> None:
    student_id = add_student(environment)
    incompatible = tmp_path / "future-schema.sqlite3"
    connection = sqlite3.connect(incompatible)
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
    connection.close()
    manager = BackupManager(environment["db"], tmp_path / "backups")

    with pytest.raises(BackupError, match="versión de esquema incompatible"):
        manager.restore_backup(incompatible)

    students = environment["service"].list_students(environment["owner"])
    assert [student["id"] for student in students] == [student_id]


def test_failed_atomic_replace_rolls_back_active_database(
    environment, tmp_path, monkeypatch
) -> None:
    student_id = add_student(environment)
    manager = BackupManager(environment["db"], tmp_path / "backups")
    snapshot = manager.create_backup(tmp_path / "snapshot.sqlite3")
    real_replace = backups_module.os.replace

    def fail_staged_restore(source, destination):
        if ".restore-" in str(source) and str(source).endswith(".tmp"):
            raise OSError("simulated replace failure")
        real_replace(source, destination)

    monkeypatch.setattr(backups_module.os, "replace", fail_staged_restore)
    with pytest.raises(BackupError, match="se conservó la base actual"):
        manager.restore_backup(snapshot)

    students = environment["service"].list_students(environment["owner"])
    assert [student["id"] for student in students] == [student_id]
    assert environment["db"].integrity_check() == "ok"


def test_database_migration_takes_snapshot_before_upgrade(
    environment, tmp_path, monkeypatch
) -> None:
    from moove_recovery.infrastructure import database as database_module

    monkeypatch.setattr(database_module, "SCHEMA_VERSION", 2)
    environment["service"].initialize()

    snapshots = list((environment["db"].path.parent / "backups").glob("pre-migration-*.sqlite3"))
    assert len(snapshots) == 1
    BackupManager(environment["db"]).validate_backup(snapshots[0])


def test_manual_backup_and_restore_are_owner_only(environment, tmp_path) -> None:
    service = environment["service"]
    source = BackupManager(environment["db"]).create_backup(tmp_path / "owner-copy.sqlite3")
    service.create_employee(
        environment["owner"],
        full_name="Empleado Ficticio",
        username="empleado-backup",
        password="ClaveEmpleado-Backup",
    )
    employee = service.login("empleado-backup", "ClaveEmpleado-Backup")
    assert employee is not None

    with pytest.raises(PermissionDenied):
        service.create_backup(employee, tmp_path / "unauthorized.sqlite3")
    with pytest.raises(PermissionDenied):
        service.restore_backup(employee, source)
