from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication, QDialog

from moove_recovery.application.service import GymService
from moove_recovery.domain.models import Actor
from moove_recovery.ui.dialogs import LoginDialog
from moove_recovery.ui.main_window import MainWindow


class SessionController(QObject):
    def __init__(self, service: GymService, app: QApplication) -> None:
        super().__init__(app)
        self.service = service
        self.app = app
        self.window: MainWindow | None = None

    def start(self, actor: Actor) -> None:
        self.window = MainWindow(self.service, actor)
        self.window.logout_requested.connect(self.logout)
        self.window.show()

    def logout(self) -> None:
        if self.window is None:
            return
        quit_on_close = self.app.quitOnLastWindowClosed()
        self.app.setQuitOnLastWindowClosed(False)
        previous = self.window
        self.window = None
        previous.day_timer.stop()
        previous.close()
        previous.deleteLater()
        try:
            login = LoginDialog(self.service)
            if login.exec() != QDialog.DialogCode.Accepted or login.actor is None:
                self.app.quit()
                return
            self.start(login.actor)
        finally:
            self.app.setQuitOnLastWindowClosed(quit_on_close)
