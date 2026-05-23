from src.service import BugService
from src.gui import BugTrackerGUI

def main():
    service = BugService("bugs.json")
    app = BugTrackerGUI(service)
    app.run()

if __name__ == "__main__":
    main()