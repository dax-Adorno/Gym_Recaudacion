import runpy
from pathlib import Path

import pytest

from moove_recovery.infrastructure.licensing import machine_code, validate_license

issuer = runpy.run_path(str(Path(__file__).resolve().parents[1] / "tools/license_issuer/issuer.py"))


def test_encrypted_key_and_issued_license():
    password = b"temporary-test-password"
    private, public = issuer["create_key"](password)
    assert b"BEGIN ENCRYPTED PRIVATE KEY" in private
    code = machine_code("12345678-1234-1234-1234-123456789abc")
    license_bytes = issuer["issue_license"](private, password, code)
    validate_license(license_bytes, public, code)
    with pytest.raises(ValueError):
        issuer["issue_license"](private, b"wrong-password", code)
    with pytest.raises(ValueError):
        issuer["issue_license"](private, password, "invalid")


def test_short_password_rejected():
    with pytest.raises(ValueError):
        issuer["create_key"](b"short")


def test_no_secret_outputs_in_repository():
    with pytest.raises(ValueError):
        issuer["outside_repository"](Path(__file__).resolve().parents[1] / "secret.key")


def test_existing_files_never_overwritten(tmp_path):
    path = tmp_path / "test.license"
    issuer["save_new"](path, b"original")
    with pytest.raises(FileExistsError):
        issuer["save_new"](path, b"replacement")
    assert path.read_bytes() == b"original"
