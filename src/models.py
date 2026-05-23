from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class Bug:
    """
    Модель бага для локального баг-трекера.
    """
    id: int
    title: str
    status: str
    priority: str
    steps: str = ""
    version: str = ""
    created_at: str = ""
    attachments: List[str] = field(default_factory=list)

    @staticmethod
    def create_new(
            bug_id: int,
            title: str,
            priority: str,
            status: str = "Open",
            steps: str = "",
            version: str = ""
    ):
        """
        Создаёт новый баг с текущим временем создания.
        """
        return Bug(
            id=bug_id,
            title=title,
            status=status,
            priority=priority or "Normal",
            steps=steps,
            version=version,
            created_at=datetime.now().isoformat(timespec="seconds"),
            attachments=[]
        )

    def to_dict(self):
        """
        Преобразует баг в словарь для JSON-сериализации.
        """
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "priority": self.priority,
            "steps": self.steps,
            "version": self.version,
            "created_at": self.created_at,
            "attachments": self.attachments,
        }

    @staticmethod
    def from_dict(data: dict):
        """
        Восстанавливает баг из словаря (строки JSON).
        Старые JSON без поля attachments тоже поддерживаются.
        """
        return Bug(
            id=data.get("id", 0),
            title=data.get("title", ""),
            status=data.get("status", "Open"),
            priority=data.get("priority", "Normal"),
            steps=data.get("steps", ""),
            version=data.get("version", ""),
            created_at=data.get("created_at", ""),
            attachments=data.get("attachments", []) or [],
        )