from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStyle,
    QVBoxLayout,
)

from moove_recovery.infrastructure.licensing import LicenseError, LicenseStore
from moove_recovery.ui.dialogs import _gym_logo


class ActivationDialog(QDialog):
    def __init__(self, store: LicenseStore, reason: str) -> None:
        super().__init__()
        self.store = store
        self.setWindowTitle("Activar MOOVE RECOVERY")
        self.resize(650, 360)
        layout = QVBoxLayout(self)
        layout.addWidget(_gym_logo())
        layout.addWidget(QLabel("Código de esta computadora"))
        self.code = QLineEdit(store.code)
        self.code.setReadOnly(True)
        layout.addWidget(self.code)
        self.message = QLabel(reason)
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        buttons = QHBoxLayout()
        copy = QPushButton("Copiar código")
        copy.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        copy.clicked.connect(lambda: QApplication.clipboard().setText(store.code))
        buttons.addWidget(copy)
        self.import_button = QPushButton("Importar licencia")
        self.import_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)
        )
        self.import_button.clicked.connect(self.choose_license)
        buttons.addWidget(self.import_button)
        close = QPushButton("Salir")
        close.clicked.connect(self.reject)
        buttons.addWidget(close)
        layout.addLayout(buttons)

    def choose_license(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar licencia", "", "Licencia (*.license)"
        )
        if path:
            self.import_license(Path(path))

    def import_license(self, path: Path) -> None:
        try:
            self.store.install(path)
            self.store.check()
        except LicenseError as error:
            self.message.setText(str(error))
            return
        self.accept()


def require_activation(store: LicenseStore) -> bool:
    try:
        store.check()
        return True
    except LicenseError as error:
        dialog = ActivationDialog(store, str(error))
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False
    try:
        store.check()
        return True
    except LicenseError:
        return False
