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
    source = (Path(__file__).resolve().parents[1] / "packaging/installer.nsi").read_text()
    assert "RMDir /r" not in source
    assert "Delete /REBOOTOK" not in source
    assert "RequestExecutionLevel user" in source
    assert "BETA 1.0.1" in source


def test_uninstaller_manifest_deletes_only_bundle_files(tmp_path):
    import runpy

    tools = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "packaging/uninstall_manifest.py")
    )
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "file.dll").write_bytes(b"fake")
    output = tools["manifest"](tmp_path)
    assert 'Delete "$INSTDIR\\sub\\file.dll"' in output
    assert 'RMDir "$INSTDIR\\sub"' in output
    assert "/r" not in output


def test_beta_version_consistency():
    from moove_recovery import VERSION_LABEL, __version__

    assert VERSION_LABEL == "BETA 1.0.1"
    assert __version__ == "1.0.1b1"
    source = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    assert f'version = "{__version__}"' in source
