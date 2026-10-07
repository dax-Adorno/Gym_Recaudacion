from pathlib import Path

from moove_recovery.infrastructure.licensing import bundled_public_key
from moove_recovery.ui.resources import branding_path


def test_source_branding_and_public_key():
    assert branding_path("moove_recovery.png").is_file()
    assert branding_path("dax.png").is_file()
    assert len(bundled_public_key()) == 32


def test_frozen_branding_root(monkeypatch, tmp_path):
    monkeypatch.setattr("sys._MEIPASS", str(tmp_path), raising=False)
    assert branding_path("dax.png") == tmp_path / "assets" / "branding" / "dax.png"


def test_installer_does_not_delete_local_data():
    source = (Path(__file__).resolve().parents[1] / "packaging/installer.iss").read_text()
    assert "[UninstallDelete]" not in source
    assert "[InstallDelete]" not in source
    assert "PrivilegesRequired=lowest" in source
