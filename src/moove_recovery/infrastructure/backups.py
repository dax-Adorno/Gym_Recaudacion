from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from moove_recovery.infrastructure.database import SCHEMA_VERSION, Database

DEFAULT_AUTOMATIC_BACKUPS = 30
MAX_AUTOMATIC_BACKUPS = 3650
REQUIRED_TABLES = {
    "settings",
    "users",
    "plans",
    "plan_prices",
    "students",
    "student_history",
    "dues",
    "payments",
    "payment_dues",
    "audit_log",
}


class BackupError(RuntimeError):
    pass


class BackupManager:
    def __init__(self, database: Database, backup_directory: Path | None = None) -> None:
        self.database = database
        self.backup_directory = backup_directory or database.path.parent / "backups"

    def create_backup(self, destination: Path) -> Path:
        destination = destination.resolve()
        if destination == self.database.path.resolve():
            raise BackupError("El destino no puede ser la base de datos activa.")
        temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
        try:
            self.database.backup_to(temporary)
            self.validate_backup(temporary)
            os.replace(temporary, destination)
            self._record_result(destination, "Copia verificada")
            return destination
        except Exception as error:
            temporary.unlink(missing_ok=True)
            self._record_result(destination, f"Error al crear la copia: {error}")
            if isinstance(error, BackupError):
                raise
            raise BackupError(f"No se pudo crear una copia válida: {error}") from error

    def create_daily_backup(self, today: date) -> Path | None:
        self.backup_directory.mkdir(parents=True, exist_ok=True)
        prefix = f"moove-auto-{today.isoformat()}"
        existing = sorted(self.backup_directory.glob(f"{prefix}*.sqlite3"))
        for path in existing:
            try:
                self.validate_backup(path)
                return None
            except BackupError:
                continue

        stamp = datetime.now(timezone.utc).strftime("%H%M%S")
        destination = self.backup_directory / f"{prefix}-{stamp}-{uuid4().hex[:8]}.sqlite3"
        created = self.create_backup(destination)
        self._prune_automatic_backups()
        return created

    def restore_backup(self, source_path: Path) -> Path:
        source_path = source_path.resolve()
        self.validate_backup(source_path)
        self.backup_directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        pre_restore = self.backup_directory / f"pre-restore-{stamp}-{uuid4().hex[:8]}.sqlite3"
        self.create_backup(pre_restore)

        active_path = self.database.path.resolve()
        staged_path = active_path.with_name(f".{active_path.name}.restore-{uuid4().hex}.tmp")
        rollback_path = active_path.with_name(f".{active_path.name}.previous-{uuid4().hex}")
        moved_sidecars: list[tuple[Path, Path]] = []
        original_moved = False
        try:
            self._copy_database(source_path, staged_path)
            self.validate_backup(staged_path)
            os.replace(active_path, rollback_path)
            original_moved = True
            for suffix in ("-wal", "-shm"):
                sidecar = Path(f"{active_path}{suffix}")
                if sidecar.exists():
                    saved_sidecar = Path(f"{rollback_path}{suffix}")
                    os.replace(sidecar, saved_sidecar)
                    moved_sidecars.append((sidecar, saved_sidecar))
            os.replace(staged_path, active_path)
            self.validate_backup(active_path)
        except Exception as error:
            rollback_error: Exception | None = None
            if original_moved:
                try:
                    active_path.unlink(missing_ok=True)
                    if rollback_path.exists():
                        os.replace(rollback_path, active_path)
                    for original, saved in moved_sidecars:
                        if saved.exists():
                            os.replace(saved, original)
                except Exception as restore_error:
                    rollback_error = restore_error
            if rollback_error:
                self._record_result(
                    pre_restore,
                    f"Falló la restauración y el rollback: {rollback_error}",
                )
                raise BackupError(
                    "Falló la restauración y no se pudo reponer automáticamente la base. "
                    f"Conserva la copia preventiva {pre_restore}. Detalle: {rollback_error}"
                ) from error
            self._record_result(source_path, f"Restauración fallida: {error}")
            raise BackupError(
                f"No se pudo restaurar la copia; se conservó la base actual: {error}"
            ) from error
        finally:
            staged_path.unlink(missing_ok=True)

        rollback_path.unlink(missing_ok=True)
        for _, saved in moved_sidecars:
            saved.unlink(missing_ok=True)
        self._record_result(active_path, f"Restauración validada desde {source_path}")
        return pre_restore

    def validate_backup(self, path: Path) -> None:
        path = path.resolve()
        if not path.is_file():
            raise BackupError("El archivo de copia no existe.")
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True, timeout=5)
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version != SCHEMA_VERSION:
                raise BackupError("La copia tiene una versión de esquema incompatible.")
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            if not REQUIRED_TABLES.issubset(tables):
                raise BackupError("La copia no contiene todas las tablas de MOOVE RECOVERY.")
            setup = connection.execute(
                "SELECT value FROM settings WHERE key = 'setup_complete'"
            ).fetchone()
            if setup is None or setup[0] != "1":
                raise BackupError("La copia no contiene una configuración inicial completa.")
            checks = connection.execute("PRAGMA integrity_check").fetchall()
            if checks != [("ok",)]:
                raise BackupError("La copia está dañada: falló la comprobación de integridad.")
            if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise BackupError("La copia contiene relaciones de datos inválidas.")
        except BackupError:
            raise
        except (OSError, sqlite3.Error, ValueError) as error:
            raise BackupError(
                f"El archivo no es una copia válida de MOOVE RECOVERY: {error}"
            ) from error
        finally:
            if connection is not None:
                connection.close()

    def automatic_backups(self) -> list[dict[str, object]]:
        if not self.backup_directory.exists():
            return []
        files = sorted(self.backup_directory.glob("moove-auto-*.sqlite3"), reverse=True)[
            : self.retention_count()
        ]
        return [
            {
                "path": path,
                "name": path.name,
                "size_bytes": path.stat().st_size,
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime).astimezone(),
            }
            for path in files
        ]

    def retention_count(self) -> int:
        row = self.database.fetch_one(
            "SELECT value FROM settings WHERE key = 'backup_retention_count'"
        )
        if row is None:
            return DEFAULT_AUTOMATIC_BACKUPS
        try:
            count = int(row[0])
        except (TypeError, ValueError):
            return DEFAULT_AUTOMATIC_BACKUPS
        if not 1 <= count <= MAX_AUTOMATIC_BACKUPS:
            return DEFAULT_AUTOMATIC_BACKUPS
        return count

    def set_retention_count(self, count: int) -> None:
        if not 1 <= count <= MAX_AUTOMATIC_BACKUPS:
            raise BackupError(f"La retención debe estar entre 1 y {MAX_AUTOMATIC_BACKUPS} copias.")
        with self.database.transaction() as connection:
            connection.execute(
                "INSERT INTO settings(key, value) VALUES ('backup_retention_count', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (str(count),),
            )
        self._prune_automatic_backups()

    def last_result(self) -> dict[str, str] | None:
        try:
            rows = self.database.fetch_all(
                "SELECT key, value FROM settings WHERE key IN "
                "('backup_last_at', 'backup_last_path', 'backup_last_result')"
            )
        except sqlite3.Error:
            return None
        result = {str(row["key"]): str(row["value"]) for row in rows}
        if "backup_last_result" not in result:
            return None
        return result

    def _record_result(self, path: Path, status: str) -> None:
        try:
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            with self.database.transaction() as connection:
                connection.executemany(
                    "INSERT INTO settings(key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    [
                        ("backup_last_at", now),
                        ("backup_last_path", str(path)),
                        ("backup_last_result", status),
                    ],
                )
        except sqlite3.Error:
            return

    def _prune_automatic_backups(self) -> None:
        files = sorted(self.backup_directory.glob("moove-auto-*.sqlite3"))
        for path in files[: -self.retention_count()]:
            path.unlink(missing_ok=True)

    @staticmethod
    def _copy_database(source_path: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(f"{source_path.as_uri()}?mode=ro", uri=True, timeout=5)
        target = sqlite3.connect(destination, timeout=5)
        try:
            source.backup(target)
            target.commit()
        finally:
            target.close()
            source.close()
