import pytest
from PySide6.QtWidgets import QDialog

from moove_recovery.ui import session as session_module
from moove_recovery.ui.session import SessionController


def test_logout_switches_roles_with_fresh_windows_and_stops_old_timers(
    qtbot, qapp, environment, monkeypatch
):
    service = environment["service"]
    owner = environment["owner"]
    service.create_employee(
        owner,
        full_name="Empleado Ficticio",
        username="empleado-sesion",
        password="ClaveEmpleado-2026",
    )
    employee = service.login("empleado-sesion", "ClaveEmpleado-2026")
    assert employee is not None
    actors = iter((employee, owner))
    controller = SessionController(service, qapp)
    controller.start(owner)
    old_windows = []

    class FakeLogin:
        def __init__(self, service):
            self.actor = next(actors)

        def exec(self):
            assert controller.window is None
            assert old_windows[-1].isHidden()
            assert not old_windows[-1].day_timer.isActive()
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(session_module, "LoginDialog", FakeLogin)
    for actor in (employee, owner):
        previous = controller.window
        old_windows.append(previous)
        previous.logout_button.click()
        current = controller.window
        assert current is not previous
        assert current.actor == actor
        assert current.students_page.actor == actor
        assert current.nav_buttons["Alumnos"].isChecked()
        assert ("Usuarios" in current.nav_buttons) == (actor == owner)
        assert current.students_page.delete_button.isHidden() == (actor == employee)
        assert qapp.quitOnLastWindowClosed()
    qtbot.addWidget(controller.window)


@pytest.mark.parametrize("result", [QDialog.DialogCode.Rejected, QDialog.DialogCode.Accepted])
def test_cancel_or_missing_actor_after_logout_never_reopens_previous_session(
    qtbot, qapp, environment, monkeypatch, result
):
    controller = SessionController(environment["service"], qapp)
    controller.start(environment["owner"])
    previous = controller.window
    quit_calls = []
    monkeypatch.setattr(qapp, "quit", lambda: quit_calls.append(True))

    class FakeLogin:
        actor = None

        def __init__(self, service):
            pass

        def exec(self):
            return result

    monkeypatch.setattr(session_module, "LoginDialog", FakeLogin)
    previous.logout_button.click()
    assert previous.isHidden()
    assert not previous.day_timer.isActive()
    assert controller.window is None
    assert quit_calls == [True]
    assert qapp.quitOnLastWindowClosed()
