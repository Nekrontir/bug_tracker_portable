from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class Bug:
    id: int
    title: str
    status: str
    priority: str
    steps: str = ""
    created_at: str = ""

    @staticmethod
    def create_new(bug_id: int, title: str, priority: str, steps: str = ""):
        return Bug(
            id=bug_id,
            title=title,
            status="Open",
            priority=priority or "Normal",
            steps=steps,
            created_at=datetime.now().isoformat(timespec="seconds")
        )

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data: dict):
        return Bug(
            id=data.get("id", 0),
            title=data.get("title", ""),
            status=data.get("status", "Open"),
            priority=data.get("priority", "Normal"),
            steps=data.get("steps", ""),
            created_at=data.get("created_at", "")
        )