import json
import os
from src.models import Bug


class BugStorage:
    def __init__(self, filename: str):
        self.filename = filename
        self.ensure_file()

    def ensure_file(self):
        if not os.path.exists(self.filename):
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def load(self):
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return []
                raw = json.loads(content)
                if not isinstance(raw, list):
                    return []
                return [Bug.from_dict(item) for item in raw]
        except (json.JSONDecodeError, OSError):
            return []

    def save(self, bugs):
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump([bug.to_dict() for bug in bugs], f, ensure_ascii=False, indent=2)

    def export_to_file(self, path: str, bugs):
        with open(path, "w", encoding="utf-8") as f:
            json.dump([bug.to_dict() for bug in bugs], f, ensure_ascii=False, indent=2)

    def import_from_file(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, list):
            raise ValueError("Ожидается список багов в JSON")
        return [Bug.from_dict(item) for item in raw]