from __future__ import annotations

import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from issuer import issue_license, save_new
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStyle,
    QVBoxLayout,
)

from moove_recovery.infrastructure.licensing import bundled_public_key, validate_license


def issue_verified(private: bytes, password: bytes, code: str) -> bytes:
    key = serialization.load_pem_private_key(private, password=password)
    if (
        not isinstance(key, Ed25519PrivateKey)
        or key.public_key().public_bytes_raw() != bundled_public_key()
    ):
        raise ValueError("La clave seleccionada no corresponde a este programa.")
    result = issue_license(private, password, code)
    validate_license(result, bundled_public_key(), code)
    return result


class IssuerWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DAX - Generador de licencias MOOVE RECOVERY")
        self.resize(700, 320)
        root = QVBoxLayout(self)
        title = QLabel("Generador de licencias DAX")
        title.setStyleSheet("font-size: 21px; font-weight: 700")
        root.addWidget(title)
        form = QFormLayout()
        self.code = QLineEdit()
        self.code.setPlaceholderText("MR1-...")
        self.key_path = QLineEdit()
        self.key_path.setReadOnly(True)
        if getattr(sys, "frozen", False):
            adjacent = Path(sys.executable).parent / "issuer.pem"
            if adjacent.is_file():
                self.key_path.setText(str(adjacent))
        browse = QPushButton("Seleccionar clave")
        browse.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        browse.clicked.connect(self.choose_key)
        key_row = QHBoxLayout()
        key_row.addWidget(self.key_path, 1)
        key_row.addWidget(browse)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Codigo de la PC", self.code)
        form.addRow("Clave privada cifrada", key_row)
        form.addRow("Contrasena de la clave", self.password)
        root.addLayout(form)
        self.message = QLabel()
        self.message.setWordWrap(True)
        root.addWidget(self.message)
        generate = QPushButton("Generar licencia")
        generate.setObjectName("generate")
        generate.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        generate.clicked.connect(self.generate)
        root.addWidget(generate)
        self.secret_directory = (
            Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.home()
        )
        reference = QPushButton("Guardar contrasena en TXT (no recomendado)")
        reference.setStyleSheet("color: #85362b; border-color: #ac5d50")
        reference.clicked.connect(self.save_password_reference)
        root.addWidget(reference)

    def save_password_reference(self):
        answer = QMessageBox.warning(
            self,
            "Contrasena en texto plano",
            "Este TXT dejara visible la contrasena. Quien obtenga el TXT y issuer.pem "
            "podra emitir licencias. No lo compartas ni lo guardes junto a la clave "
            "en un pendrive sin proteccion. ¿Guardar de todos modos?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        password, accepted = QInputDialog.getText(
            self,
            "Contrasena de la clave privada",
            "Ingresala localmente para verificarla:",
            QLineEdit.EchoMode.Password,
        )
        if not accepted:
            return
        try:
            private = Path(self.key_path.text()).read_bytes()
            issue_verified(private, password.encode("utf-8"), "MR1-" + "0" * 64)
            destination = self.secret_directory / "CONTRASENA_PRIVADA.txt"
            save_new(
                destination,
                ("CONTRASENA DE LA CLAVE PRIVADA - NO COMPARTIR\n" + password + "\n").encode(
                    "utf-8"
                ),
            )
        except FileExistsError:
            self.message.setText("CONTRASENA_PRIVADA.txt ya existe. No se sobrescribio.")
            return
        except (ValueError, TypeError, OSError):
            self.message.setText("No se guardo el TXT. Revisa clave, contrasena y permisos.")
            return
        finally:
            password = ""
        self.message.setText(
            "TXT privado guardado junto al generador. No compartirlo con el cliente."
        )

    def choose_key(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar clave privada", "", "Clave cifrada (*.pem)"
        )
        if path:
            self.key_path.setText(path)

    def generate(self):
        password = self.password.text().encode("utf-8")
        self.password.clear()
        code = self.code.text().strip().upper()
        try:
            private = Path(self.key_path.text()).read_bytes()
        except OSError:
            self.message.setText(
                "No se pudo abrir la clave privada. Selecciona el archivo issuer.pem."
            )
            return
        try:
            license_bytes = issue_verified(private, password, code)
        except (ValueError, TypeError):
            self.message.setText(
                "No se genero la licencia. Revisa codigo, clave y contrasena; la clave debe corresponder a MOOVE RECOVERY."
            )
            return
        finally:
            password = b""
            private = b""
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar licencia", f"pc-{code[4:12]}.license", "Licencia (*.license)"
        )
        if not path:
            self.message.setText("Operacion cancelada. No se guardo ningun archivo.")
            return
        destination = Path(path)
        if destination.suffix.lower() != ".license":
            destination = destination.with_suffix(".license")
        try:
            save_new(destination, license_bytes)
        except FileExistsError:
            self.message.setText(
                "Ese archivo ya existe. Elige otro nombre; no se sobrescriben licencias."
            )
            return
        except OSError:
            self.message.setText("No se pudo guardar. Revisa los permisos de la carpeta.")
            return
        self.message.setText(
            f"Licencia verificada y guardada: {destination}\nEntrega solo el archivo .license al cliente."
        )


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QDialog { background: white; }
        QLabel { color: #243b2e; }
        QLineEdit { padding: 8px; border: 1px solid #8d9fa9; border-radius: 4px; }
        QPushButton { padding: 8px 12px; border: 2px solid #8d9fa9; border-radius: 5px; background: #f1f5f8; color: #253d4d; }
        QPushButton:hover { background: #dbeaf4; }
        QPushButton#generate { background: #215a40; color: white; border-color: #123d2b; }
        QPushButton#generate:hover { background: #2d7252; }
    """)
    window = IssuerWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
