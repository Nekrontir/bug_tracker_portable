import os
import shutil
from typing import Iterable

ATTACHMENTS_ROOT = "attachments"


class AttachmentsManager:
    def __init__(self, root: str = ATTACHMENTS_ROOT):
        self.root = root
        os.makedirs(self.root, exist_ok=True)

    def bug_folder_path(self, bug_id: int) -> str:
        return os.path.join(self.root, str(bug_id))

    def add_attachments(self, bug_id: int, file_paths: Iterable[str]) -> list[str]:
        """
        Копирует файлы в папку бага и возвращает список имён файлов (без пути).
        Папка создаётся только если реально есть файлы.
        """
        file_paths = [p for p in file_paths if p]
        if not file_paths:
            return []

        folder = self.bug_folder_path(bug_id)
        os.makedirs(folder, exist_ok=True)

        saved_names: list[str] = []
        for src in file_paths:
            name = os.path.basename(src)
            dst = os.path.join(folder, name)
            shutil.copy2(src, dst)  # сохраняем метаданные файла [web:202][web:203]
            saved_names.append(name)
        return saved_names

    def get_attachment_path(self, bug_id: int, filename: str) -> str:
        return os.path.join(self.bug_folder_path(bug_id), filename)

    def delete_bug_attachments(self, bug_id: int):
        folder = self.bug_folder_path(bug_id)
        if os.path.isdir(folder):
            shutil.rmtree(folder, ignore_errors=True)