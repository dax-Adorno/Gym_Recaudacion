import runpy
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from moove_recovery.infrastructure.licensing import LicenseError, LicenseStore, machine_code
from moove_recovery.ui.activation import ActivationDialog, require_activation

issuer = runpy.run_path(str(Path(__file__).resolve().parents[1] / "tools/license_issuer/issuer.py"))


@pytest.fixture
def license_files(tmp_path):
    password = b"temporary-test-password"
    private, public = issuer["create_key"](password)
    code = machine_code("12345678-1234-1234-1234-123456789abc")
    source = tmp_path / "valid.license"
    source.write_bytes(issuer["issue_license"](private, password, code))
    store = LicenseStore(tmp_path / "activation" / "installed.license", public, code)
    return store, source


def test_store_install_restart_and_invalid_replacement(license_files, tmp_path):
    store, source = license_files
    with pytest.raises(LicenseError):
        store.check()
    store.install(source)
    LicenseStore(store.path, store.public_key, store.code).check()
    original = store.path.read_bytes()
    invalid = tmp_path / "invalid.license"
    invalid.write_bytes(b"invalid")
    with pytest.raises(LicenseError):
        store.install(invalid)
    assert store.path.read_bytes() == original


def test_failed_replace_preserves_license(license_files, monkeypatch):
    store, source = license_files
    store.install(source)
    original = store.path.read_bytes()

    def fail(*args):
        raise OSError("test failure")

    monkeypatch.setattr("moove_recovery.infrastructure.licensing.os.replace", fail)
    with pytest.raises(LicenseError):
        store.install(source)
    assert store.path.read_bytes() == original
    assert list(store.path.parent.iterdir()) == [store.path]


def test_dialog_accepts_only_valid_license(qtbot, license_files, tmp_path):
    store, source = license_files
    dialog = ActivationDialog(store, "Sin licencia")
    qtbot.addWidget(dialog)
    dialog.show()
    invalid = tmp_path / "bad.license"
    invalid.write_bytes(b"[]")
    dialog.import_license(invalid)
    assert dialog.result() == QDialog.DialogCode.Rejected
    assert not store.path.exists()
    dialog.import_license(source)
    assert dialog.result() == QDialog.DialogCode.Accepted
    assert require_activation(store)


def test_cancel_blocks_access(qtbot, license_files, monkeypatch):
    store, _ = license_files
    monkeypatch.setattr(ActivationDialog, "exec", lambda self: QDialog.DialogCode.Rejected)
    assert not require_activation(store)


@pytest.mark.parametrize("configured", [True, False])
def test_startup_does_not_open_database_before_activation(qtbot, tmp_path, monkeypatch, configured):
    from moove_recovery import __main__ as startup

    monkeypatch.setattr(startup, "QApplication", lambda args: QApplication.instance())
    monkeypatch.setattr(startup, "data_directory", lambda: tmp_path / "data")
    monkeypatch.setattr(startup, "windows_machine_code", lambda: "test-code")
    monkeypatch.setattr(startup, "require_activation", lambda store: False)
    monkeypatch.setattr(startup.QMessageBox, "critical", lambda *args: None)

    def public_key():
        if not configured:
            raise LicenseError("No public key")
        return b"x" * 32

    def forbidden_database(*args):
        pytest.fail("Database opened before activation")

    monkeypatch.setattr(startup, "bundled_public_key", public_key)
    monkeypatch.setattr(startup, "Database", forbidden_database)
    assert startup.main() == (0 if configured else 1)
    assert not (tmp_path / "data" / "moove.sqlite3").exists()
