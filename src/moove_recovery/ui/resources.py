import sys
from pathlib import Path


def branding_path(name: str) -> Path:
    bundle = getattr(sys, "_MEIPASS", None)
    root = Path(bundle) if bundle else Path(__file__).resolve().parents[3]
    return root / "assets" / "branding" / name
