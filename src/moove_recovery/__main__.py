from __future__ import annotations

import sys

from PySide6.QtCore import QLockFile
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from moove_recovery.application.service import GymService
from moove_recovery.infrastructure.backups import BackupManager
from moove_recovery.infrastructure.database import Database
from moove_recovery.infrastructure.paths import data_directory
from moove_recovery.ui.dialogs import InitialSetupDialog, LoginDialog
from moove_recovery.ui.main_window import APP_STYLES, MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("MOOVE RECOVERY")
    app.setOrganizationName("MOOVE RECOVERY")
    app.setFont(QFont("Segoe UI", 9))
    app.setStyleSheet(APP_STYLES)

    directory = data_directory()
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        QMessageBox.critical(
            None, "Error de almacenamiento", f"No se puede abrir la carpeta de datos.\n\n{error}"
        )
        return 1
    lock = QLockFile(str(directory / "moove-recovery.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        QMessageBox.warning(
            None,
            "MOOVE RECOVERY ya está abierto",
            "Cierra la otra ventana antes de iniciar otra instancia.",
        )
        return 1

    service = GymService(Database(directory / "moove.sqlite3"))
    try:
        service.initialize()
    except Exception as error:
        QMessageBox.critical(
            None, "Error de base de datos", f"No se pudo abrir la base de datos.\n\n{error}"
        )
        lock.unlock()
        return 1

    if not service.is_setup_complete():
        setup = InitialSetupDialog(service)
        if setup.exec() != InitialSetupDialog.DialogCode.Accepted:
            lock.unlock()
            return 0
    try:
        BackupManager(service.db).create_daily_backup(service.today())
    except Exception as error:
        QMessageBox.warning(
            None,
            "No se pudo crear el respaldo diario",
            f"La aplicación continuará, pero no se creó el respaldo automático.\n\n{error}",
        )
    login = LoginDialog(service)
    if login.exec() != LoginDialog.DialogCode.Accepted or login.actor is None:
        lock.unlock()
        return 0
    try:
        result = service.generate_missing_dues()
    except Exception as error:
        QMessageBox.critical(
            None, "Error de cuotas", f"No se pudieron generar las cuotas.\n\n{error}"
        )
        lock.unlock()
        return 1
    if result["without_price"]:
        QMessageBox.warning(
            None,
            "Falta configurar precios",
            f"No se generaron {result['without_price']} cuota(s) porque falta el precio de un plan.",
        )

    window = MainWindow(service, login.actor)
    window.show()
    app.aboutToQuit.connect(lock.unlock)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
