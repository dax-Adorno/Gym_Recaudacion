import os
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from moove_recovery.application.service import GymService
from moove_recovery.domain.models import Actor
from moove_recovery.infrastructure.database import Database


class FakeClock:
    def __init__(self, today: date) -> None:
        self.current = today

    def today(self) -> date:
        return self.current

    def now(self) -> datetime:
        return datetime.combine(self.current, time(12), ZoneInfo("America/Argentina/Buenos_Aires"))


@pytest.fixture
def environment(tmp_path: Path):
    clock = FakeClock(date(2026, 10, 3))
    database = Database(tmp_path / "moove-test.sqlite3")
    service = GymService(database, today=clock.today, now=clock.now)
    service.initialize()
    service.setup_owner(
        full_name="Dueño Ficticio",
        username="dueno",
        password="UnaClaveLocal-2026",
        prices_cents={2: 3_000_000, 3: 3_500_000, 4: 4_000_000},
    )
    owner = service.login("DUENO", "UnaClaveLocal-2026")
    assert owner is not None
    plans = {row["sessions_per_week"]: row["id"] for row in service.list_plans(owner)}
    return {"clock": clock, "db": database, "service": service, "owner": owner, "plans": plans}


def add_student(
    environment, *, day: date = date(2026, 10, 3), name: str = "Ana", dni: str = "12.345.678"
) -> int:
    service: GymService = environment["service"]
    owner: Actor = environment["owner"]
    return service.create_student(
        owner,
        first_name=name,
        last_name="Pérez",
        dni=dni,
        phone="011 4444-0000",
        activity="Musculación",
        enrolled_on=day,
        plan_id=environment["plans"][2],
    )
