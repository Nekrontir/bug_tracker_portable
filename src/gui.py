import json
import os
import textwrap

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QPushButton,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QFileDialog,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QDialog,
    QHeaderView,
)

from src.service import BugService
from src.settings import load_settings, save_settings


class BugTrackerWindow(QMainWindow):
    """
    PyQt6‑эквивалент твоего BugTrackerGUI.
    """

    STATUSES = ("Open", "In Progress", "Fixed", "Closed")
    PRIORITIES = ("Low", "Normal", "High", "Critical")
    # Используем стандартные стили Qt как "темы"
    THEMES = ("Fusion", "Windows", "WindowsVista")

    def __init__(self, service: BugService):
        super().__init__()
        self.service = service

        # -------- состояние / настройки --------
        self.settings = load_settings()
        saved_theme = self.settings.get("theme", "Fusion")

        # Применяем тему Qt
        QApplication.setStyle(saved_theme)

        # Геометрия окна: (x, y, w, h) или дефолт
        geometry = self.settings.get("geometry")
        if geometry and len(geometry) == 4:
            x, y, w, h = geometry
            self.setGeometry(x, y, w, h)
        else:
            self.resize(1050, 720)
            self.move(100, 100)

        self.setWindowTitle("Portable Bug Tracker (PyQt6)")

        # Состояние
        self.selected_bug_id: int | None = None
        self.selected_for_delete: set[int] = set()
        self.copied_bug_data: dict | None = None

        # Поля формы
        self.title_edit: QLineEdit | None = None
        self.priority_combo: QComboBox | None = None
        self.status_combo: QComboBox | None = None
        self.version_edit: QLineEdit | None = None
        self.steps_edit: QTextEdit | None = None

        # Фильтры
        self.filter_status_combo: QComboBox | None = None
        self.filter_priority_combo: QComboBox | None = None
        self.search_edit: QLineEdit | None = None

        # Таблица
        self.table: QTableWidget | None = None

        # Тема
        self.theme_combo: QComboBox | None = None

        # Флаг "импорт с заменой"
        self.import_replace_checkbox: QCheckBox | None = None

        self.build_ui()
        self.refresh_table()
        self.apply_saved_column_widths()
        self.bind_shortcuts()

    # ---------------- UI ----------------

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Верхняя панель: экспорт/импорт + тема
        top_bar = QHBoxLayout()
        main_layout.addLayout(top_bar)

        # Левая часть: экспорт / импорт
        export_widget = QWidget()
        export_layout = QHBoxLayout(export_widget)
        export_layout.setContentsMargins(0, 0, 0, 0)
        top_bar.addWidget(export_widget, stretch=1)

        export_btn = QPushButton("Экспорт")
        export_btn.clicked.connect(self.export_bugs)
        import_btn = QPushButton("Импорт")
        import_btn.clicked.connect(self.import_bugs)

        self.import_replace_checkbox = QCheckBox("с заменой")

        export_layout.addWidget(export_btn)
        export_layout.addWidget(import_btn)
        export_layout.addWidget(self.import_replace_checkbox)
        export_layout.addStretch()

        # Правая часть: тема
        theme_widget = QWidget()
        theme_layout = QHBoxLayout(theme_widget)
        theme_layout.setContentsMargins(0, 0, 0, 0)
        top_bar.addWidget(theme_widget)

        theme_label = QLabel("Тема:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(self.THEMES)
        current_theme = self.settings.get("theme", "Fusion")
        if current_theme in self.THEMES:
            self.theme_combo.setCurrentText(current_theme)
        else:
            self.theme_combo.setCurrentText("Fusion")

        apply_theme_btn = QPushButton("Применить")
        apply_theme_btn.clicked.connect(self.change_theme)

        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addWidget(apply_theme_btn)

        # Форма добавления/редактирования
        form_group = QGroupBox("Новый баг / редактирование")
        form_layout = QGridLayout(form_group)
        main_layout.addWidget(form_group)

        # Заголовок
        form_layout.addWidget(QLabel("Заголовок"), 0, 0)
        self.title_edit = QLineEdit()
        form_layout.addWidget(self.title_edit, 0, 1)

        # Приоритет
        form_layout.addWidget(QLabel("Приоритет"), 0, 2)
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(self.PRIORITIES)
        self.priority_combo.setCurrentText("Normal")
        form_layout.addWidget(self.priority_combo, 0, 3)

        # Статус
        form_layout.addWidget(QLabel("Статус"), 0, 4)
        self.status_combo = QComboBox()
        self.status_combo.addItems(self.STATUSES)
        self.status_combo.setCurrentText("Open")
        form_layout.addWidget(self.status_combo, 0, 5)

        # Версия
        form_layout.addWidget(QLabel("Версия"), 0, 6)
        self.version_edit = QLineEdit()
        form_layout.addWidget(self.version_edit, 0, 7)

        # Заметки
        form_layout.addWidget(QLabel("Заметки"), 1, 0, Qt.AlignmentFlag.AlignTop)
        self.steps_edit = QTextEdit()
        form_layout.addWidget(self.steps_edit, 1, 1, 1, 7)

        # Кнопки формы
        form_btns_widget = QWidget()
        form_btns_layout = QHBoxLayout(form_btns_widget)
        main_layout.addWidget(form_btns_widget)

        add_btn = QPushButton("Добавить баг")
        add_btn.clicked.connect(self.add_bug)
        save_btn = QPushButton("Сохранить изменения")
        save_btn.clicked.connect(self.save_changes)
        clear_btn = QPushButton("Очистить форму")
        clear_btn.clicked.connect(self.clear_inputs)
        attach_btn = QPushButton("Прикрепить файл")
        attach_btn.clicked.connect(self.attach_file)

        form_btns_layout.addWidget(add_btn)
        form_btns_layout.addWidget(save_btn)
        form_btns_layout.addWidget(clear_btn)
        form_btns_layout.addWidget(attach_btn)
        form_btns_layout.addStretch()

        # Фильтр и поиск
        filter_group = QGroupBox("Фильтр и поиск")
        filter_layout = QGridLayout(filter_group)
        main_layout.addWidget(filter_group)

        filter_layout.addWidget(QLabel("Статус"), 0, 0)
        self.filter_status_combo = QComboBox()
        self.filter_status_combo.addItems(["All"] + list(self.STATUSES))
        self.filter_status_combo.setCurrentText("All")
        filter_layout.addWidget(self.filter_status_combo, 0, 1)

        filter_layout.addWidget(QLabel("Приоритет"), 0, 2)
        self.filter_priority_combo = QComboBox()
        self.filter_priority_combo.addItems(["All"] + list(self.PRIORITIES))
        self.filter_priority_combo.setCurrentText("All")
        filter_layout.addWidget(self.filter_priority_combo, 0, 3)

        filter_layout.addWidget(QLabel("Поиск в заголовке"), 0, 4)
        self.search_edit = QLineEdit()
        filter_layout.addWidget(self.search_edit, 0, 5)

        apply_filter_btn = QPushButton("Применить")
        apply_filter_btn.clicked.connect(self.apply_filter)
        reset_filter_btn = QPushButton("Сбросить")
        reset_filter_btn.clicked.connect(self.reset_filter)

        filter_layout.addWidget(apply_filter_btn, 0, 6)
        filter_layout.addWidget(reset_filter_btn, 0, 7)

        # Таблица багов
        list_group = QGroupBox("Список багов")
        list_layout = QVBoxLayout(list_group)
        main_layout.addWidget(list_group, stretch=1)

        cols = ("Selected", "ID", "Title", "Status", "Priority", "Version", "Created")
        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.cellClicked.connect(self.on_table_click)
        self.table.cellDoubleClicked.connect(self.on_table_double_click)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        list_layout.addWidget(self.table)

        # Нижняя панель: вложения + удаление
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        main_layout.addWidget(bottom_widget)

        attachments_btn = QPushButton("Вложения...")
        attachments_btn.clicked.connect(self.show_attachments)
        delete_btn = QPushButton("Удалить выбранные")
        delete_btn.clicked.connect(self.delete_selected_bugs)

        bottom_layout.addWidget(attachments_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(delete_btn)

    # ---------------- Настройки ----------------

    def apply_saved_column_widths(self):
        cols_widths = self.settings.get("table_columns")
        if not cols_widths:
            return
        for col_name, width in cols_widths.items():
            for idx in range(self.table.columnCount()):
                header_item = self.table.horizontalHeaderItem(idx)
                if header_item is None:
                    continue
                if header_item.text() == col_name:
                    self.table.setColumnWidth(idx, int(width))

    def collect_current_settings(self) -> dict:
        # Тема
        theme = self.theme_combo.currentText()

        # Геометрия (x, y, w, h)
        geo = self.geometry()
        geometry = (geo.x(), geo.y(), geo.width(), geo.height())

        # Ширина колонок
        cols_widths: dict[str, int] = {}
        for idx in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(idx)
            if header_item is None:
                continue
            name = header_item.text()
            cols_widths[name] = self.table.columnWidth(idx)

        return {
            "theme": theme,
            "geometry": geometry,
            "table_columns": cols_widths,
        }

    def closeEvent(self, event):
        # Сохраняем настройки при закрытии
        self.settings.update(self.collect_current_settings())
        save_settings(self.settings)
        event.accept()

    # ---------------- Темы ----------------

    def change_theme(self):
        theme = self.theme_combo.currentText()
        if theme:
            QApplication.setStyle(theme)
            self.settings["theme"] = theme

    # ---------------- Работа со списком ----------------

    def wrap_title(self, text: str, width_chars: int = 30) -> str:
        if not text:
            return ""
        lines = textwrap.wrap(text, width=width_chars)
        return "\n".join(lines)

    def refresh_table(self, bugs=None):
        self.table.setRowCount(0)
        source = bugs if bugs is not None else self.service.get_all()
        for bug in source:
            row = self.table.rowCount()
            self.table.insertRow(row)

            checked = "[x]" if bug.id in self.selected_for_delete else "[ ]"
            wrapped_title = self.wrap_title(bug.title, width_chars=30)

            values = [
                checked,
                str(bug.id),
                wrapped_title,
                bug.status,
                bug.priority,
                getattr(bug, "version", ""),
                str(bug.created_at),
            ]

            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                if col == 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)

    def apply_filter(self):
        status = self.filter_status_combo.currentText()
        priority = self.filter_priority_combo.currentText()
        query = self.search_edit.text().strip()
        filtered = self.service.filter_bugs(status=status, priority=priority, query=query)
        self.refresh_table(filtered)

    def reset_filter(self):
        self.filter_status_combo.setCurrentText("All")
        self.filter_priority_combo.setCurrentText("All")
        self.search_edit.clear()
        self.refresh_table()

    # ---------------- Форма / выбор ----------------

    def clear_inputs(self):
        self.title_edit.clear()
        self.priority_combo.setCurrentText("Normal")
        self.status_combo.setCurrentText("Open")
        self.version_edit.clear()
        self.steps_edit.clear()
        self.selected_bug_id = None
        self.table.clearSelection()
        self.title_edit.setFocus()

    def get_selected_bug_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 1)  # ID во второй колонке
        if not item:
            return None
        try:
            return int(item.text())
        except ValueError:
            return None

    def on_table_double_click(self, row: int, column: int):
        # Двойной клик — заполняем форму
        self.fill_form_from_selected()

    def on_table_click(self, row: int, column: int):
        # Клик по первой колонке — "чекбокс"
        if column == 0:
            item_id = self.table.item(row, 1)
            if not item_id:
                return
            try:
                bug_id = int(item_id.text())
            except ValueError:
                return

            if bug_id in self.selected_for_delete:
                self.selected_for_delete.remove(bug_id)
                self.table.item(row, 0).setText("[ ]")
            else:
                self.selected_for_delete.add(bug_id)
                self.table.item(row, 0).setText("[x]")
        else:
            # просто выбор строки — для формы
            pass

    def fill_form_from_selected(self):
        bug_id = self.get_selected_bug_id()
        if bug_id is None:
            return

        bug = self.service.get_by_id(bug_id)
        if not bug:
            return

        self.selected_bug_id = bug_id
        self.title_edit.setText(bug.title)
        self.priority_combo.setCurrentText(bug.priority)
        self.status_combo.setCurrentText(bug.status)
        self.version_edit.setText(getattr(bug, "version", ""))
        self.steps_edit.setPlainText(bug.steps)

    # ---------------- Операции с багами ----------------

    def add_bug(self):
        title = self.title_edit.text().strip()
        priority = self.priority_combo.currentText() or "Normal"
        status = self.status_combo.currentText() or "Open"
        version = self.version_edit.text().strip()
        steps = self.steps_edit.toPlainText().strip()

        if not title:
            QMessageBox.warning(self, "Ошибка", "Введите заголовок бага")
            return

        self.service.add_bug(title, priority, status, steps, version)
        self.refresh_table()
        self.clear_inputs()

    def save_changes(self):
        if self.selected_bug_id is None:
            QMessageBox.information(self, "Инфо", "Выберите баг в списке")
            return

        title = self.title_edit.text().strip()
        priority = self.priority_combo.currentText() or "Normal"
        status = self.status_combo.currentText() or "Open"
        version = self.version_edit.text().strip()
        steps = self.steps_edit.toPlainText().strip()

        if not title:
            QMessageBox.warning(self, "Ошибка", "Заголовок не может быть пустым")
            return

        updated = self.service.update_bug(
            bug_id=self.selected_bug_id,
            title=title,
            priority=priority,
            status=status,
            steps=steps,
            version=version,
        )
        if not updated:
            QMessageBox.critical(
                self,
                "Ошибка",
                "Не удалось обновить баг (возможно, он был удалён)",
            )
            return

        self.apply_filter()

    def delete_bug(self, bug_id: int | None = None) -> bool:
        if bug_id is None:
            bug_id = self.get_selected_bug_id()
        if bug_id is None:
            QMessageBox.information(self, "Инфо", "Выберите баг в списке")
            return False

        bug = self.service.get_by_id(bug_id)
        if not bug:
            return False

        warn_text = f"Удалить баг #{bug_id}?"
        if getattr(bug, "attachments", []):
            warn_text += "\n\nУ него есть вложения. Удалить их тоже?"

        reply = QMessageBox.question(
            self,
            "Удаление",
            warn_text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
        if reply != QMessageBox.StandardButton.Yes:
            return False

        self.service.delete_bug(bug_id)
        return True

    def delete_selected_bugs(self):
        if not self.selected_for_delete:
            if self.delete_bug():
                self.refresh_table()
                self.clear_inputs()
            return

        ids = sorted(self.selected_for_delete)
        bugs_with_attachments = [
            b_id for b_id in ids
            if getattr(self.service.get_by_id(b_id), "attachments", [])
        ]

        if bugs_with_attachments:
            text = (
                f"Удалить выбранные баги: {ids}?\n\n"
                f"Часть из них имеет вложения: {bugs_with_attachments}.\n"
                f"Вложения будут удалены безвозвратно."
            )
        else:
            text = f"Удалить выбранные баги: {ids}?"

        reply = QMessageBox.question(
            self,
            "Удаление",
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
        if reply != QMessageBox.StandardButton.Yes:
            return

        for b_id in ids:
            self.service.delete_bug(b_id)

        self.selected_for_delete.clear()
        self.refresh_table()
        self.clear_inputs()

    # ---------------- Вложения ----------------

    def attach_file(self):
        """
        Открывает диалог выбора файлов и прикрепляет их к выбранному багу.
        """
        bug_id = self.get_selected_bug_id()
        if bug_id is None:
            QMessageBox.information(
                self,
                "Инфо",
                "Сначала выберите баг в списке, чтобы прикрепить файл",
            )
            return

        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите файлы для прикрепления",
        )
        if not paths:
            return

        bug = self.service.get_by_id(bug_id)
        if not bug:
            return

        new_names = self.service.attachments.add_attachments(bug_id, paths)
        bug.attachments.extend(new_names)
        self.service.storage.save(self.service.bugs)

        QMessageBox.information(
            self,
            "Вложения",
            f"Прикреплено файлов: {len(new_names)}",
        )

    def show_attachments(self):
        """
        Показывает окно со списком вложений выбранного бага.
        """
        bug_id = self.get_selected_bug_id()
        if bug_id is None:
            QMessageBox.information(self, "Вложения", "Сначала выберите баг в списке")
            return

        bug = self.service.get_by_id(bug_id)
        if not bug:
            return

        files = getattr(bug, "attachments", []) or []
        if not files:
            QMessageBox.information(self, "Вложения", "У этого бага нет вложений")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Вложения бага #{bug_id}")
        dlg.resize(400, 300)

        layout = QVBoxLayout(dlg)

        list_widget = QListWidget()
        for name in files:
            QListWidgetItem(name, list_widget)
        layout.addWidget(list_widget)

        btns_widget = QWidget()
        btns_layout = QHBoxLayout(btns_widget)
        layout.addWidget(btns_widget)

        def open_file():
            item = list_widget.currentItem()
            if not item:
                return
            fname = item.text()
            path = self.service.attachments.get_attachment_path(bug_id, fname)
            if not os.path.isfile(path):
                QMessageBox.critical(dlg, "Ошибка", f"Файл не найден:\n{path}")
                return
            try:
                import subprocess
                import sys as _sys
                if _sys.platform.startswith("win"):
                    os.startfile(path)
                elif _sys.platform == "darwin":
                    subprocess.call(["open", path])
                else:
                    subprocess.call(["xdg-open", path])
            except Exception as e:
                QMessageBox.critical(dlg, "Ошибка", str(e))

        def open_folder():
            folder = self.service.attachments.bug_folder_path(bug_id)
            if not os.path.isdir(folder):
                QMessageBox.critical(dlg, "Ошибка", f"Папка не найдена:\n{folder}")
                return
            try:
                import subprocess
                import sys as _sys
                if _sys.platform.startswith("win"):
                    os.startfile(folder)
                elif _sys.platform == "darwin":
                    subprocess.call(["open", folder])
                else:
                    subprocess.call(["xdg-open", folder])
            except Exception as e:
                QMessageBox.critical(dlg, "Ошибка", str(e))

        open_file_btn = QPushButton("Открыть файл")
        open_file_btn.clicked.connect(open_file)
        open_folder_btn = QPushButton("Открыть папку")
        open_folder_btn.clicked.connect(open_folder)
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dlg.accept)

        btns_layout.addWidget(open_file_btn)
        btns_layout.addWidget(open_folder_btn)
        btns_layout.addStretch()
        btns_layout.addWidget(close_btn)

        dlg.exec()

    # ---------------- Экспорт / импорт ----------------

    def export_bugs(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт багов (ZIP или JSON)",
            filter="ZIP archive (*.zip);;JSON files (*.json);;All files (*.*)",
            defaultSuffix="zip",
        )
        if not path:
            return
        try:
            if path.lower().endswith(".json"):
                self.service.storage.export_to_file(path, self.service.bugs)
            else:
                self.service.export_bugs(path)
            QMessageBox.information(self, "Экспорт", "Экспорт успешно завершён")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))

    def import_bugs(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт багов",
            filter="ZIP/JSON files (*.zip *.json);;All files (*.*)",
        )
        if not path:
            return
        try:
            merge = not self.import_replace_checkbox.isChecked()
            self.service.import_bugs(path, merge=merge)
            self.refresh_table()
            QMessageBox.information(self, "Импорт", "Импорт успешно завершён")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", str(e))

    # ---------------- Хоткеи ----------------

    def bind_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self.on_new_shortcut)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.on_save_shortcut)
        QShortcut(QKeySequence("Delete"), self, activated=self.on_delete_shortcut)
        QShortcut(QKeySequence("Ctrl+C"), self, activated=self.on_copy_shortcut)
        QShortcut(QKeySequence("Ctrl+V"), self, activated=self.on_paste_shortcut)

    def on_new_shortcut(self):
        self.clear_inputs()

    def on_save_shortcut(self):
        self.save_changes()

    def on_delete_shortcut(self):
        self.delete_selected_bugs()

    def on_copy_shortcut(self):
        """
        Копирует данные выбранного бага в JSON в системный буфер.
        """
        bug_id = self.get_selected_bug_id()
        if bug_id is None:
            return
        bug = self.service.get_by_id(bug_id)
        if not bug:
            return

        self.copied_bug_data = {
            "title": bug.title,
            "priority": bug.priority,
            "status": bug.status,
            "version": getattr(bug, "version", ""),
            "steps": bug.steps,
        }

        data = json.dumps(self.copied_bug_data, ensure_ascii=False, indent=2)
        clipboard = QApplication.clipboard()
        clipboard.setText(data)

    def on_paste_shortcut(self):
        """
        Вставляет данные бага из JSON в системном буфере или внутреннего буфера.
        """
        clipboard = QApplication.clipboard()
        clip = clipboard.text()

        pasted = None
        if clip:
            try:
                obj = json.loads(clip)
                if isinstance(obj, dict) and "title" in obj:
                    pasted = obj
            except Exception:
                pasted = None

        data = pasted or self.copied_bug_data
        if not data:
            return

        self.title_edit.setText(data.get("title", ""))
        self.priority_combo.setCurrentText(data.get("priority", "Normal"))
        self.status_combo.setCurrentText(data.get("status", "Open"))
        self.version_edit.setText(data.get("version", ""))
        self.steps_edit.setPlainText(data.get("steps", ""))