import sys
from PyQt6.QtWidgets import QApplication

from src.service import BugService
from src.gui import BugTrackerWindow


def main():
    app = QApplication(sys.argv)
    service = BugService("bugs.json")
    win = BugTrackerWindow(service)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()