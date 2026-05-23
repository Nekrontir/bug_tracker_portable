from dataclasses import dataclass
from datetime import datetime


@dataclass
class Bug:
    id: int
    title: str
    status: str
    priority: str
    steps: str = ""
    version: str = ""
    created_at: str = ""

    @staticmethod
    def create_new(
            bug_id: int,
            title: str,
            priority: str,
            status: str = "Open",
            steps: str = "",
            version: str = ""
    ):
        return Bug(
            id=bug_id,
            title=title,
            status=status,
            priority=priority or "Normal",
            steps=steps,
            version=version,
            created_at=datetime.now().isoformat(timespec="seconds")
        )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "priority": self.priority,
            "steps": self.steps,
            "version": self.version,
            "created_at": self.created_at
        }

    @staticmethod
    def from_dict(data: dict):
        return Bug(
            id=data.get("id", 0),
            title=data.get("title", ""),
            status=data.get("status", "Open"),
            priority=data.get("priority", "Normal"),
            steps=data.get("steps", ""),
            version=data.get("version", ""),
            created_at=data.get("created_at", "")
        )