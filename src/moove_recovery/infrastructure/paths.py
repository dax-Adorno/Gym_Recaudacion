from __future__ import annotations

import os
from pathlib import Path


def data_directory() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    root = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return root / "MOOVE RECOVERY" / "data"
