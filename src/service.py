import os
import shutil
import zipfile

from src.models import Bug
from src.storage import BugStorage
from src.attachments import AttachmentsManager


class BugService:
    def __init__(self, filename: str):
        self.storage = BugStorage(filename)
        self.bugs = self.storage.load()
        self.attachments = AttachmentsManager()

    # ---------- базовые операции ----------

    def get_all(self):
        return self.bugs

    def next_id(self):
        return max((bug.id for bug in self.bugs), default=0) + 1

    def get_by_id(self, bug_id: int):
        for bug in self.bugs:
            if bug.id == bug_id:
                return bug
        return None

    def add_bug(self, title: str, priority: str,
                status: str = "Open", steps: str = "",
                version: str = "", file_paths: list[str] | None = None):
        bug = Bug.create_new(self.next_id(), title, priority, status, steps, version)
        if file_paths:
            bug.attachments = self.attachments.add_attachments(bug.id, file_paths)
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

    def delete_bug(self, bug_id: int):
        bug = self.get_by_id(bug_id)
        if bug:
            self.bugs.remove(bug)
            # удаляем вложения
            self.attachments.delete_bug_attachments(bug_id)
            self.storage.save(self.bugs)
            return True
        return False

    # ---------- фильтрация / поиск ----------

    def filter_bugs(self, status: str | None = None,
                    priority: str | None = None,
                    query: str | None = None):
        result = self.bugs

        if status and status != "All":
            result = [b for b in result if b.status == status]

        if priority and priority != "All":
            result = [b for b in result if b.priority == priority]

        if query:
            q = query.lower()
            result = [b for b in result if q in b.title.lower()]

        return result

    # ---------- экспорт / импорт ----------

    def export_bugs(self, zip_path: str):
        """
        Экспортирует текущие баги + папку attachments в zip-архив.
        Структура архива:
        - bugs.json
        - attachments/
        """
        temp_dir = "_export_tmp"
        if os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)

        # bugs.json
        export_json = os.path.join(temp_dir, "bugs.json")
        self.storage.export_to_file(export_json, self.bugs)

        # attachments, если есть
        if os.path.isdir(self.attachments.root):
            dst_attachments = os.path.join(temp_dir, self.attachments.root)
            if os.path.isdir(dst_attachments):
                shutil.rmtree(dst_attachments)
            shutil.copytree(self.attachments.root, dst_attachments)

        # сборка zip
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(temp_dir):
                for name in files:
                    full = os.path.join(root, name)
                    rel = os.path.relpath(full, temp_dir)
                    zf.write(full, rel)

        shutil.rmtree(temp_dir, ignore_errors=True)

    def import_bugs(self, path: str, merge: bool = True):
        """
        Если path оканчивается на .zip — импорт из архива (bugs.json + attachments/),
        иначе считаем, что это обычный JSON только с багами.
        """
        if path.lower().endswith(".zip"):
            self._import_from_zip(path, merge)
        else:
            self._import_from_json(path, merge)

    def _import_from_json(self, path: str, merge: bool):
        imported = self.storage.import_from_file(path)
        if merge:
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

    def _import_from_zip(self, zip_path: str, merge: bool):
        temp_dir = "_import_tmp"
        if os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)

        # распаковываем архив
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(temp_dir)

        json_path = os.path.join(temp_dir, "bugs.json")
        imported = self.storage.import_from_file(json_path)

        attachments_src = os.path.join(temp_dir, self.attachments.root)

        if not merge:
            # полностью заменяем локальные данные и вложения
            self.bugs = imported
            if os.path.isdir(self.attachments.root):
                shutil.rmtree(self.attachments.root)
            if os.path.isdir(attachments_src):
                shutil.copytree(attachments_src, self.attachments.root)
            self.storage.save(self.bugs)
            shutil.rmtree(temp_dir, ignore_errors=True)
            return

        # merge: баги + папка attachments
        existing_ids = {b.id for b in self.bugs}
        next_id = self.next_id()

        # сначала просто переносим attachments, потом перенумеровку учтём
        if os.path.isdir(attachments_src):
            if not os.path.isdir(self.attachments.root):
                os.makedirs(self.attachments.root, exist_ok=True)
            # копируем папки по id
            for name in os.listdir(attachments_src):
                src_folder = os.path.join(attachments_src, name)
                dst_folder = os.path.join(self.attachments.root, name)
                if os.path.isdir(src_folder) and not os.path.exists(dst_folder):
                    shutil.copytree(src_folder, dst_folder)

        for bug in imported:
            if bug.id in existing_ids:
                old_id = bug.id
                bug.id = next_id
                next_id += 1
                # если у старого id была папка, переносим её под новый id
                old_folder = os.path.join(self.attachments.root, str(old_id))
                new_folder = os.path.join(self.attachments.root, str(bug.id))
                if os.path.isdir(old_folder):
                    if os.path.isdir(new_folder):
                        shutil.rmtree(new_folder)
                    shutil.move(old_folder, new_folder)
            self.bugs.append(bug)

        self.storage.save(self.bugs)
        shutil.rmtree(temp_dir, ignore_errors=True)