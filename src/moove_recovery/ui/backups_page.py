from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from moove_recovery.application.service import GymService
from moove_recovery.domain.models import Actor
from moove_recovery.infrastructure.backups import BackupManager
from moove_recovery.ui.common import make_label


class BackupsPage(QWidget):
    restored = Signal()

    def __init__(self, service: GymService, actor: Actor) -> None:
        super().__init__()
        self.service = service
        self.actor = actor
        self.backups = BackupManager(service.db)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(14)
        layout.addWidget(make_label("Respaldos", "pageTitle"))
        layout.addWidget(
            make_label(
                "Las copias contienen datos personales y no están cifradas. Guárdalas en un lugar protegido.",
                "muted",
            )
        )

        actions = QHBoxLayout()
        self.create_button = QPushButton("Guardar copia en otra ubicación")
        self.create_button.setObjectName("primaryButton")
        self.restore_button = QPushButton("Restaurar copia")
        self.create_button.clicked.connect(self.create_manual_backup)
        self.restore_button.clicked.connect(self.restore_from_file)
        actions.addWidget(self.create_button)
        actions.addWidget(self.restore_button)
        actions.addStretch(1)
        layout.addLayout(actions)

        layout.addWidget(make_label("Última operación", "sectionTitle"))
        self.last_result = QLabel("Todavía no hay operaciones de respaldo registradas.")
        self.last_result.setWordWrap(True)
        layout.addWidget(self.last_result)

        layout.addWidget(make_label("Copias automáticas locales", "sectionTitle"))
        retention = QHBoxLayout()
        retention.addWidget(QLabel("Conservar"))
        self.retention_input = QSpinBox()
        self.retention_input.setRange(1, 3650)
        self.retention_input.setSuffix(" copias")
        self.retention_input.setValue(self.backups.retention_count())
        self.retention_save = QPushButton("Guardar retención")
        self.retention_save.clicked.connect(self.save_retention)
        retention.addWidget(self.retention_input)
        retention.addWidget(self.retention_save)
        retention.addStretch(1)
        layout.addLayout(retention)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["FECHA", "ARCHIVO", "TAMAÑO"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        self.refresh()

    def save_retention(self) -> None:
        try:
            self.service.set_backup_retention(self.actor, self.retention_input.value())
        except Exception as error:
            QMessageBox.warning(self, "No se pudo guardar la retención", str(error))
            return
        self.refresh()

    def refresh(self) -> None:
        last = self.backups.last_result()
        if last:
            timestamp = last.get("backup_last_at", "")
            self.last_result.setText(
                f"{last.get('backup_last_result', '')} · {timestamp} · "
                f"{last.get('backup_last_path', '')}"
            )
        records = self.backups.automatic_backups()
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            modified = record["modified_at"]
            date_text = (
                modified.astimezone().strftime("%d/%m/%Y %H:%M")
                if isinstance(modified, datetime)
                else str(modified)
            )
            values = (
                date_text,
                str(record["name"]),
                self._format_size(int(record["size_bytes"])),
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))

    def create_manual_backup(self) -> None:
        suggestion = f"MOOVE_RECOVERY_{self.service.today().isoformat()}.sqlite3"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar copia de seguridad",
            suggestion,
            "Copia SQLite (*.sqlite3)",
        )
        if not path:
            return
        destination = Path(path)
        if destination.suffix.lower() != ".sqlite3":
            destination = destination.with_suffix(".sqlite3")
        try:
            self.service.create_backup(self.actor, destination)
        except Exception as error:
            QMessageBox.warning(self, "No se pudo crear el respaldo", str(error))
            self.refresh()
            return
        self.refresh()
        QMessageBox.information(
            self,
            "Copia verificada",
            f"Se creó y verificó la copia en:\n{destination}\n\nEl archivo no está cifrado.",
        )

    def restore_from_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar copia para restaurar",
            str(self.backups.backup_directory),
            "Copias SQLite (*.sqlite3 *.db);;Todos los archivos (*.*)",
        )
        if not path:
            return
        answer = QMessageBox.question(
            self,
            "Confirmar restauración",
            "La base actual será reemplazada. Se creará primero una copia preventiva. "
            "Después de restaurar, MOOVE RECOVERY se cerrará y tendrás que iniciar sesión de nuevo.\n\n"
            "¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            safety_copy = self.service.restore_backup(self.actor, Path(path))
        except Exception as error:
            self.refresh()
            QMessageBox.critical(
                self,
                "No se pudo restaurar la copia",
                f"No se completó la restauración. Conserva la copia preventiva si se indica abajo.\n\n{error}",
            )
            return
        QMessageBox.information(
            self,
            "Restauración verificada",
            f"La copia se validó y restauró. La base anterior se guardó en:\n{safety_copy}\n\n"
            "La aplicación se cerrará para volver a iniciar sesión.",
        )
        self.restored.emit()

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        if size_bytes < 1_000_000:
            return f"{size_bytes / 1_000:.0f} KB"
        return f"{size_bytes / 1_000_000:.1f} MB"
