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

    def add_bug(self, title: str, priority: str,
                status: str = "Open", steps: str = "", version: str = ""):
        bug = Bug.create_new(self.next_id(), title, priority, status, steps, version)
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

    def update_bug(self, bug_id: int, title: str, priority: str,
                   status: str, steps: str, version: str):
        bug = self.get_by_id(bug_id)
        if not bug:
            return False
        bug.title = title
        bug.priority = priority
        bug.status = status
        bug.steps = steps
        bug.version = version
        self.storage.save(self.bugs)
        return True

    def filter_bugs(self, status: str | None = None, priority: str | None = None, query: str | None = None):
        result = self.bugs

        if status and status != "All":
            result = [b for b in result if b.status == status]

        if priority and priority != "All":
            result = [b for b in result if b.priority == priority]

        if query:
            q = query.lower()
            result = [b for b in result if q in b.title.lower()]

        return result

    # --------- экспорт / импорт ---------

    def export_bugs(self, path: str):
        self.storage.export_to_file(path, self.bugs)

    def import_bugs(self, path: str, merge: bool = True):
        imported = self.storage.import_from_file(path)
        if merge:
            # смержим по id, новые id для конфликтов
            existing_ids = {b.id for b in self.bugs}
            next_id = self.next_id()
            for bug in imported:
                if bug.id in existing_ids:
                    bug.id = next_id
                    next_id += 1
                self.bugs.append(bug)
        else:
            self.bugs = imported
        self.storage.save(self.bugs)