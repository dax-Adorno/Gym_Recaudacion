import importlib.util
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("issuer_gui", root / "tools/license_issuer/gui.py")
module = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(root / "tools/license_issuer"))
try:
    spec.loader.exec_module(module)
finally:
    sys.path.pop(0)


def test_gui_issues_verified_license_and_clears_password(qtbot, tmp_path, monkeypatch):
    import issuer

    private, public = issuer.create_key(b"temporary-test-password")
    monkeypatch.setattr(module, "bundled_public_key", lambda: public)
    key = tmp_path / "test.pem"
    key.write_bytes(private)
    output = tmp_path / "client.license"
    monkeypatch.setattr(module.QFileDialog, "getSaveFileName", lambda *args: (str(output), ""))
    window = module.IssuerWindow()
    qtbot.addWidget(window)
    window.key_path.setText(str(key))
    window.password.setText("temporary-test-password")
    window.code.setText("MR1-" + "A" * 64)
    window.generate()
    assert window.password.text() == ""
    module.validate_license(output.read_bytes(), public, "MR1-" + "A" * 64)
    original = output.read_bytes()
    window.password.setText("temporary-test-password")
    window.generate()
    assert output.read_bytes() == original
    assert "ya existe" in window.message.text()


def test_issuer_rejects_wrong_key_and_password(monkeypatch):
    import issuer

    private, _ = issuer.create_key(b"temporary-test-password")
    monkeypatch.setattr(
        module,
        "bundled_public_key",
        lambda: Ed25519PrivateKey.generate().public_key().public_bytes_raw(),
    )
    with pytest.raises(ValueError):
        module.issue_verified(private, b"temporary-test-password", "MR1-" + "A" * 64)
    with pytest.raises(ValueError):
        module.issue_verified(private, b"wrong-password", "MR1-" + "A" * 64)


def test_password_txt_requires_confirmation_and_valid_key(qtbot, tmp_path, monkeypatch):
    import issuer

    private, public = issuer.create_key(b"temporary-test-password")
    monkeypatch.setattr(module, "bundled_public_key", lambda: public)
    path = tmp_path / "test.pem"
    path.write_bytes(private)
    window = module.IssuerWindow()
    qtbot.addWidget(window)
    window.key_path.setText(str(path))
    window.secret_directory = tmp_path
    monkeypatch.setattr(
        module.QMessageBox, "warning", lambda *args: module.QMessageBox.StandardButton.No
    )
    window.save_password_reference()
    assert not (tmp_path / "CONTRASENA_PRIVADA.txt").exists()
    monkeypatch.setattr(
        module.QMessageBox, "warning", lambda *args: module.QMessageBox.StandardButton.Yes
    )
    monkeypatch.setattr(module.QInputDialog, "getText", lambda *args: ("wrong-password", True))
    window.save_password_reference()
    assert not (tmp_path / "CONTRASENA_PRIVADA.txt").exists()
    monkeypatch.setattr(
        module.QInputDialog, "getText", lambda *args: ("temporary-test-password", True)
    )
    window.save_password_reference()
    assert "temporary-test-password" in (tmp_path / "CONTRASENA_PRIVADA.txt").read_text()
