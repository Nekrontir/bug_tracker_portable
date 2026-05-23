from src.models import Bug
from src.storage import BugStorage

class BugService:
    def __init__(self, filename: str):
        self.storage = BugStorage(filename)
        self.bugs = self.storage.load()

    def get_all(self):
        return self.bugs

    def next_id(self):
        return max((bug.id for bug in self.bugs), default=0) + 1

    def add_bug(self, title: str, priority: str, steps: str = ""):
        bug = Bug.create_new(self.next_id(), title, priority, steps)
        self.bugs.append(bug)
        self.storage.save(self.bugs)
        return bug

    def change_status(self, bug_id: int, new_status: str):
        bug = self.get_by_id(bug_id)
        if bug:
            bug.status = new_status
            self.storage.save(self.bugs)
            return True
        return False

    def delete_bug(self, bug_id: int):
        bug = self.get_by_id(bug_id)
        if bug:
            self.bugs.remove(bug)
            self.storage.save(self.bugs)
            return True
        return False

    def get_by_id(self, bug_id: int):
        for bug in self.bugs:
            if bug.id == bug_id:
                return bug
        return None