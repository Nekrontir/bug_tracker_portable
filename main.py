from src.service import BugService
from src.gui import BugTrackerGUI


def main():
    """
    Точка входа в приложение Portable Bug Tracker.
    Создаёт сервис, GUI и запускает главный цикл.
    """
    service = BugService("bugs.json")
    app = BugTrackerGUI(service)
    app.run()


if __name__ == "__main__":
    main()