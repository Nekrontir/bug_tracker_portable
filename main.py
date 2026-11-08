import sys
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.service import BugService
from src.gui import BugTrackerWindow


def exception_hook(exc_type, exc_value, exc_tb):
    text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(text, file=sys.stderr)

    try:
        QMessageBox.critical(None, "Непредвиденная ошибка", text)
    except Exception:
        pass


sys.excepthook = exception_hook


def main():
    app = QApplication(sys.argv)
    service = BugService("bugs.json")
    win = BugTrackerWindow(service)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
