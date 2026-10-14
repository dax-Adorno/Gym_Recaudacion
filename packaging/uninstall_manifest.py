from pathlib import Path


def nsis_path(path: Path) -> str:
    return str(path).replace("/", "\\").replace("$", "$$").replace('"', '$\\"')


def manifest(bundle: Path) -> str:
    entries = list(bundle.rglob("*"))
    if any(path.is_symlink() for path in entries):
        raise ValueError("No se permiten enlaces en el paquete.")
    files = sorted(path.relative_to(bundle) for path in entries if path.is_file())
    directories = sorted(
        (path.relative_to(bundle) for path in entries if path.is_dir()),
        key=lambda path: (len(path.parts), str(path)),
        reverse=True,
    )
    lines = [f'Delete "$INSTDIR\\{nsis_path(path)}"' for path in files]
    lines += [f'RMDir "$INSTDIR\\{nsis_path(path)}"' for path in directories]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    bundle = root / "dist" / "MooveRecovery"
    if not (bundle / "MooveRecovery.exe").is_file():
        raise SystemExit("No existe el ejecutable a empaquetar.")
    target = root / "build" / "uninstall-files.nsh"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(manifest(bundle), encoding="utf-8")
