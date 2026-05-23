import os
import json
import textwrap
import tkinter as tk
from tkinter import messagebox, filedialog

import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

from src.service import BugService
from src.settings import load_settings, save_settings  # новый импорт


class BugTrackerGUI:
    """
    Графический интерфейс для локального баг-трекера.
    """

    STATUSES = ("Open", "In Progress", "Fixed", "Closed")
    PRIORITIES = ("Low", "Normal", "High", "Critical")
    THEMES = ("flatly", "cosmo", "litera", "darkly", "superhero", "cyborg")

    def __init__(self, service: BugService):
        """
        Инициализирует GUI, загружает настройки и строит интерфейс.
        """
        self.service = service

        # Загружаем настройки
        self.settings = load_settings()

        # Тема по умолчанию или из настроек
        initial_theme = self.settings.get("theme", "flatly")

        # Главное окно ttkbootstrap
        self.root = ttkb.Window(title="Portable Bug Tracker", themename=initial_theme)

        # Геометрия окна: из настроек или дефолт
        geometry = self.settings.get("geometry")
        if geometry:
            self.root.geometry(geometry)
        else:
            self.root.geometry("1050x720")

        # Поля формы
        self.title_var = tk.StringVar()
        self.priority_var = tk.StringVar(value="Normal")
        self.status_var = tk.StringVar(value="Open")
        self.version_var = tk.StringVar()

        # Поля фильтра/поиска
        self.filter_status_var = tk.StringVar(value="All")
        self.filter_priority_var = tk.StringVar(value="All")
        self.search_var = tk.StringVar()

        # Текущий выбранный баг
        self.selected_bug_id: int | None = None

        # Копирование/вставка (внутренний буфер)
        self.copied_bug_data: dict | None = None

        # Флаг "импорт с заменой"
        self.import_replace_var = tk.BooleanVar(value=False)

        # Чекбоксы для массового удаления
        self.selected_for_delete: set[int] = set()

        self.style = self.root.style

        # Настройка стиля таблицы: тело без рамок, заголовки с рамкой
        self.style.configure(
            "Treeview",
            borderwidth=0,
            relief="flat",
            rowheight=40  # увеличенная высота под 2 строки title
        )
        self.style.configure(
            "Treeview.Heading",
            borderwidth=2,
            relief="groove",
        )

        self.build_ui()
        self.bind_shortcuts()
        self.refresh_list()
        self.apply_saved_column_widths()

        # Сохраняем настройки при закрытии окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self):
        """
        Строит все элементы интерфейса.
        """
        # Верхняя панель: тема + экспорт/импорт
        top_bar = ttkb.Frame(self.root, padding=(10, 5))
        top_bar.pack(fill=X)

        # Левая часть: экспорт / импорт
        export_frame = ttkb.Frame(top_bar)
        export_frame.pack(side=LEFT)

        ttkb.Button(export_frame, text="Экспорт", bootstyle=INFO, command=self.export_bugs).pack(side=LEFT, padx=2)
        ttkb.Button(export_frame, text="Импорт", bootstyle=WARNING, command=self.import_bugs).pack(side=LEFT, padx=2)

        ttkb.Checkbutton(
            export_frame,
            text="с заменой",
            variable=self.import_replace_var,
            bootstyle="round-toggle"
        ).pack(side=LEFT, padx=8)

        # Правая часть: выбор темы
        theme_frame = ttkb.Frame(top_bar)
        theme_frame.pack(side=RIGHT)

        ttkb.Label(theme_frame, text="Тема:").pack(side=LEFT)
        self.theme_combo = ttkb.Combobox(
            theme_frame,
            values=self.THEMES,
            state="readonly",
            width=10
        )
        # Установим выбранную тему в комбобоксе
        current_theme = self.settings.get("theme", "flatly")
        if current_theme in self.THEMES:
            self.theme_combo.set(current_theme)
        else:
            self.theme_combo.set("flatly")

        self.theme_combo.pack(side=LEFT, padx=2)
        ttkb.Button(theme_frame, text="Применить", bootstyle=INFO, command=self.change_theme).pack(side=LEFT, padx=2)

        # Основной контейнер
        frame = ttkb.Frame(self.root, padding=10)
        frame.pack(fill=BOTH, expand=YES)

        # Форма добавления/редактирования
        form = ttkb.Labelframe(frame, text="Новый баг / редактирование", padding=10)
        form.pack(fill=X)

        ttkb.Label(form, text="Заголовок").grid(row=0, column=0, sticky=W)
        self.title_entry = ttkb.Entry(form, textvariable=self.title_var, width=40)
        self.title_entry.grid(row=0, column=1, sticky=EW, padx=5)

        ttkb.Label(form, text="Приоритет").grid(row=0, column=2, sticky=W)
        self.priority_combo = ttkb.Combobox(
            form,
            textvariable=self.priority_var,
            values=self.PRIORITIES,
            state="readonly",
            width=12
        )
        self.priority_combo.grid(row=0, column=3, sticky=EW, padx=5)

        ttkb.Label(form, text="Статус").grid(row=0, column=4, sticky=W)
        self.status_combo = ttkb.Combobox(
            form,
            textvariable=self.status_var,
            values=self.STATUSES,
            state="readonly",
            width=15
        )
        self.status_combo.grid(row=0, column=5, sticky=EW, padx=5)

        ttkb.Label(form, text="Версия").grid(row=0, column=6, sticky=W)
        ttkb.Entry(form, textvariable=self.version_var, width=10).grid(
            row=0, column=7, sticky=EW, padx=5
        )

        ttkb.Label(form, text="Заметки").grid(row=1, column=0, sticky=NW, pady=5)
        self.steps_text = tk.Text(form, height=6, width=90)
        self.steps_text.grid(row=1, column=1, columnspan=7, sticky=EW, padx=5, pady=5)

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=0)
        form.columnconfigure(5, weight=0)
        form.columnconfigure(7, weight=0)

        # Кнопки формы (под формой)
        form_btns = ttkb.Frame(frame)
        form_btns.pack(fill=X, pady=5)

        ttkb.Button(form_btns, text="Добавить баг", bootstyle=SUCCESS, command=self.add_bug).pack(side=LEFT, padx=5)
        ttkb.Button(form_btns, text="Сохранить изменения", bootstyle=PRIMARY, command=self.save_changes).pack(side=LEFT, padx=5)
        ttkb.Button(form_btns, text="Очистить форму", bootstyle=SECONDARY, command=self.clear_inputs).pack(side=LEFT, padx=5)
        ttkb.Button(form_btns, text="Прикрепить файл", bootstyle=INFO, command=self.attach_file).pack(side=LEFT, padx=5)

        # Фильтр + поиск
        filter_frame = ttkb.Labelframe(frame, text="Фильтр и поиск", padding=10)
        filter_frame.pack(fill=X, pady=5)

        ttkb.Label(filter_frame, text="Статус").grid(row=0, column=0, sticky=W)
        self.filter_status_combo = ttkb.Combobox(
            filter_frame,
            textvariable=self.filter_status_var,
            values=("All",) + self.STATUSES,
            state="readonly",
            width=18
        )
        self.filter_status_combo.grid(row=0, column=1, sticky=W, padx=5)

        ttkb.Label(filter_frame, text="Приоритет").grid(row=0, column=2, sticky=W)
        self.filter_priority_combo = ttkb.Combobox(
            filter_frame,
            textvariable=self.filter_priority_var,
            values=("All",) + self.PRIORITIES,
            state="readonly",
            width=18
        )
        self.filter_priority_combo.grid(row=0, column=3, sticky=W, padx=5)

        ttkb.Label(filter_frame, text="Поиск в заголовке").grid(row=0, column=4, sticky=W)
        ttkb.Entry(filter_frame, textvariable=self.search_var, width=22).grid(row=0, column=5, sticky=W, padx=5)

        ttkb.Button(filter_frame, text="Применить", bootstyle=PRIMARY, command=self.apply_filter).grid(row=0, column=6, padx=10)
        ttkb.Button(filter_frame, text="Сбросить", bootstyle=SECONDARY, command=self.reset_filter).grid(row=0, column=7, padx=5)

        # Таблица багов
        list_frame = ttkb.Labelframe(frame, text="Список багов", padding=10)
        list_frame.pack(fill=BOTH, expand=YES)

        cols = ("Selected", "ID", "Title", "Status", "Priority", "Version", "Created")
        self.tree = ttkb.Treeview(list_frame, columns=cols, show="headings")

        for c in cols:
            self.tree.heading(c, text=c)
            if c == "Title":
                self.tree.column(c, width=250, anchor=W)
            elif c == "Selected":
                self.tree.column(c, width=70, anchor=CENTER)
            else:
                self.tree.column(c, width=90, anchor=CENTER)

        self.tree.pack(fill=BOTH, expand=YES)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Button-1>", self.on_tree_click)

        # Нижняя панель: вложения + удаление
        bottom_btns = ttkb.Frame(frame)
        bottom_btns.pack(fill=X, pady=5)
        ttkb.Button(bottom_btns, text="Вложения...", bootstyle=INFO, command=self.show_attachments).pack(side=LEFT, padx=5)
        ttkb.Button(bottom_btns, text="Удалить выбранные", bootstyle=DANGER, command=self.delete_selected_bugs).pack(side=RIGHT, padx=5)

    # ---------- Настройки / колонки ----------

    def apply_saved_column_widths(self) -> None:
        """
        Применяет сохранённые ширины колонок Treeview из настроек, если они есть.
        """
        cols_widths = self.settings.get("tree_columns")
        if not cols_widths:
            return

        for col, width in cols_widths.items():
            if col in self.tree["columns"]:
                try:
                    self.tree.column(col, width=int(width))
                except Exception:
                    pass

    def collect_current_settings(self) -> dict:
        """
        Собирает текущие настройки (тема, геометрия, ширина колонок) в словарь.
        """
        theme = self.theme_combo.get() or self.root.style.theme.name
        geometry = self.root.geometry()

        cols_widths = {}
        for col in self.tree["columns"]:
            try:
                cols_widths[col] = self.tree.column(col, "width")
            except Exception:
                pass

        return {
            "theme": theme,
            "geometry": geometry,
            "tree_columns": cols_widths,
        }

    def on_close(self):
        """
        Обработчик закрытия окна: сохраняет настройки и закрывает приложение.
        """
        self.settings.update(self.collect_current_settings())
        save_settings(self.settings)
        self.root.destroy()

    # ---------- Темы ----------

    def change_theme(self):
        """
        Меняет тему оформления и обновляет её в настройках.
        """
        theme = self.theme_combo.get()
        if theme:
            self.style.theme_use(theme)
            self.settings["theme"] = theme

    # ---------- Работа со списком ----------

    def wrap_title(self, text: str, width_chars: int = 30) -> str:
        """
        Оборачивает заголовок по числу символов для отображения в таблице.
        """
        if not text:
            return ""
        lines = textwrap.wrap(text, width=width_chars)
        return "\n".join(lines)

    def refresh_list(self, bugs=None):
        """
        Обновляет содержимое таблицы багов (с учётом фильтра).
        """
        self.tree.delete(*self.tree.get_children())
        source = bugs if bugs is not None else self.service.get_all()
        for bug in source:
            checked = "[x]" if bug.id in self.selected_for_delete else "[ ]"
            wrapped_title = self.wrap_title(bug.title, width_chars=30)
            self.tree.insert("", "end", values=(
                checked,
                bug.id,
                wrapped_title,
                bug.status,
                bug.priority,
                getattr(bug, "version", ""),
                bug.created_at
            ))

    def apply_filter(self):
        """
        Применяет фильтр по статусу, приоритету и поисковую строку.
        """
        status = self.filter_status_var.get()
        priority = self.filter_priority_var.get()
        query = self.search_var.get().strip()
        filtered = self.service.filter_bugs(status=status, priority=priority, query=query)
        self.refresh_list(filtered)

    def reset_filter(self):
        """
        Сбрасывает фильтр и поиск.
        """
        self.filter_status_var.set("All")
        self.filter_priority_var.set("All")
        self.search_var.set("")
        self.refresh_list()

    # ---------- Форма / выбор ----------

    def clear_inputs(self):
        """
        Очищает поля формы и снимает выбор бага.
        """
        self.title_var.set("")
        self.priority_var.set("Normal")
        self.status_var.set("Open")
        self.version_var.set("")
        self.steps_text.delete("1.0", "end")
        self.selected_bug_id = None
        self.tree.selection_remove(self.tree.selection())
        self.title_entry.focus_set()

    def get_selected_bug_id(self):
        """
        Возвращает ID выделенного в таблице бага или None.
        """
        sel = self.tree.selection()
        if not sel:
            return None
        values = self.tree.item(sel[0], "values")
        if not values:
            return None
        try:
            return int(values[1])  # ID во второй колонке
        except ValueError:
            return None

    def on_select(self, event=None):
        """
        Обработчик выбора строки в таблице — заполняет форму данными бага.
        """
        bug_id = self.get_selected_bug_id()
        if bug_id is None:
            return

        bug = self.service.get_by_id(b_id := bug_id)
        if not bug:
            return

        self.selected_bug_id = b_id
        self.title_var.set(bug.title)
        self.priority_var.set(bug.priority)
        self.status_var.set(bug.status)
        self.version_var.set(getattr(bug, "version", ""))
        self.steps_text.delete("1.0", "end")
        self.steps_text.insert("1.0", bug.steps)

    # ---------- Клик по чекбоксу в таблице ----------

    def on_tree_click(self, event):
        """
        Обрабатывает клики по первой колонке (чекбоксы для массового удаления).
        """
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        column = self.tree.identify_column(event.x)  # '#1', '#2', ...
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return

        col_index = int(column.replace("#", ""))
        if col_index != 1:  # "Selected"
            return

        values = list(self.tree.item(row_id, "values"))
        if not values:
            return

        try:
            bug_id = int(values[1])
        except ValueError:
            return

        if bug_id in self.selected_for_delete:
            self.selected_for_delete.remove(bug_id)
            values[0] = "[ ]"
        else:
            self.selected_for_delete.add(bug_id)
            values[0] = "[x]"

        self.tree.item(row_id, values=values)

    # ---------- Операции с багами ----------

    def add_bug(self):
        """
        Добавляет новый баг из данных формы.
        """
        title = self.title_var.get().strip()
        priority = self.priority_var.get().strip() or "Normal"
        status = self.status_var.get().strip() or "Open"
        version = self.version_var.get().strip()
        steps = self.steps_text.get("1.0", "end").strip()

        if not title:
            messagebox.showwarning("Ошибка", "Введите заголовок бага")
            return

        self.service.add_bug(title, priority, status, steps, version)
        self.refresh_list()
        self.clear_inputs()

    def save_changes(self):
        """
        Сохраняет изменения для выбранного бага.
        """
        if self.selected_bug_id is None:
            messagebox.showinfo("Инфо", "Выберите баг в списке")
            return

        title = self.title_var.get().strip()
        priority = self.priority_var.get().strip() or "Normal"
        status = self.status_var.get().strip() or "Open"
        version = self.version_var.get().strip()
        steps = self.steps_text.get("1.0", "end").strip()

        if not title:
            messagebox.showwarning("Ошибка", "Заголовок не может быть пустым")
            return

        updated = self.service.update_bug(
            bug_id=self.selected_bug_id,
            title=title,
            priority=priority,
            status=status,
            steps=steps,
            version=version
        )
        if not updated:
            messagebox.showerror("Ошибка", "Не удалось обновить баг (возможно, он был удалён)")
            return

        self.apply_filter()

    def delete_bug(self, bug_id: int | None = None):
        """
        Удаляет один баг (с подтверждением и учётом вложений).
        """
        if bug_id is None:
            bug_id = self.get_selected_bug_id()
        if bug_id is None:
            messagebox.showinfo("Инфо", "Выберите баг в списке")
            return False

        bug = self.service.get_by_id(bug_id)
        if not bug:
            return False

        warn_text = f"Удалить баг #{bug_id}?"
        if getattr(bug, "attachments", []):
            warn_text += "\n\nУ него есть вложения. Удалить их тоже?"

        if not messagebox.askyesno("Удаление", warn_text):
            return False

        self.service.delete_bug(bug_id)
        return True

    def delete_selected_bugs(self):
        """
        Удаляет один или несколько багов (по чекбоксам) с подтверждением.
        """
        if not self.selected_for_delete:
            if self.delete_bug():
                self.refresh_list()
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

        if not messagebox.askyesno("Удаление", text):
            return

        for b_id in ids:
            self.service.delete_bug(b_id)

        self.selected_for_delete.clear()
        self.refresh_list()
        self.clear_inputs()

    # ---------- Вложения ----------

    def attach_file(self):
        """
        Открывает диалог выбора файлов и прикрепляет их к выбранному багу.
        """
        bug_id = self.get_selected_bug_id()
        if bug_id is None:
            messagebox.showinfo("Инфо", "Сначала выберите баг в списке, чтобы прикрепить файл")
            return

        paths = filedialog.askopenfilenames(
            title="Выберите файлы для прикрепления"
        )
        if not paths:
            return

        bug = self.service.get_by_id(bug_id)
        if not bug:
            return

        new_names = self.service.attachments.add_attachments(bug_id, paths)
        bug.attachments.extend(new_names)
        self.service.storage.save(self.service.bugs)

        messagebox.showinfo("Вложения", f"Прикреплено файлов: {len(new_names)}")

    def show_attachments(self):
        """
        Показывает окно со списком вложений выбранного бага.
        """
        bug_id = self.get_selected_bug_id()
        if bug_id is None:
            messagebox.showinfo("Вложения", "Сначала выберите баг в списке")
            return

        bug = self.service.get_by_id(bug_id)
        if not bug:
            return

        files = bug.attachments if hasattr(bug, "attachments") else []
        if not files:
            messagebox.showinfo("Вложения", "У этого бага нет вложений")
            return

        win = ttkb.Toplevel(self.root)
        win.title(f"Вложения бага #{bug_id}")
        win.geometry("400x300")

        frame = ttkb.Frame(win, padding=10)
        frame.pack(fill=BOTH, expand=YES)

        listbox = tk.Listbox(frame)
        listbox.pack(fill=BOTH, expand=YES, side=TOP)

        for name in files:
            listbox.insert(END, name)

        btns = ttkb.Frame(frame)
        btns.pack(fill=X, side=BOTTOM, pady=5)

        def open_file():
            sel = listbox.curselection()
            if not sel:
                return
            fname = listbox.get(sel[0])
            path = self.service.attachments.get_attachment_path(bug_id, fname)
            if not os.path.isfile(path):
                messagebox.showerror("Ошибка", f"Файл не найден:\n{path}")
                return
            try:
                import subprocess, sys
                if sys.platform.startswith("win"):
                    os.startfile(path)
                elif sys.platform == "darwin":
                    subprocess.call(["open", path])
                else:
                    subprocess.call(["xdg-open", path])
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        def open_folder():
            folder = self.service.attachments.bug_folder_path(bug_id)
            if not os.path.isdir(folder):
                messagebox.showerror("Ошибка", f"Папка не найдена:\n{folder}")
                return
            try:
                import subprocess, sys
                if sys.platform.startswith("win"):
                    os.startfile(folder)
                elif sys.platform == "darwin":
                    subprocess.call(["open", folder])
                else:
                    subprocess.call(["xdg-open", folder])
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        ttkb.Button(btns, text="Открыть файл", bootstyle=PRIMARY, command=open_file).pack(side=LEFT, padx=5)
        ttkb.Button(btns, text="Открыть папку", bootstyle=SECONDARY, command=open_folder).pack(side=LEFT, padx=5)
        ttkb.Button(btns, text="Закрыть", bootstyle=SECONDARY, command=win.destroy).pack(side=RIGHT, padx=5)

    # ---------- Экспорт / импорт ----------

    def export_bugs(self):
        """
        Экспортирует баги и вложения в JSON или ZIP.
        """
        path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP archive", "*.zip"), ("JSON files", "*.json"), ("All files", "*.*")],
            title="Экспорт багов (ZIP или JSON)"
        )
        if not path:
            return
        try:
            if path.lower().endswith(".json"):
                self.service.storage.export_to_file(path, self.service.bugs)
            else:
                self.service.export_bugs(path)
            messagebox.showinfo("Экспорт", "Экспорт успешно завершён")
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", str(e))

    def import_bugs(self):
        """
        Импортирует баги и вложения из JSON или ZIP.
        """
        path = filedialog.askopenfilename(
            filetypes=[("ZIP/JSON files", "*.zip *.json"), ("All files", "*.*")],
            title="Импорт багов"
        )
        if not path:
            return
        try:
            merge = not self.import_replace_var.get()
            self.service.import_bugs(path, merge=merge)
            self.refresh_list()
            messagebox.showinfo("Импорт", "Импорт успешно завершён")
        except Exception as e:
            messagebox.showerror("Ошибка импорта", str(e))

    # ---------- Хоткеи ----------

    def bind_shortcuts(self):
        """
        Регистрирует глобальные горячие клавиши.
        """
        self.root.bind_all("<Control-n>", self.on_new_shortcut)
        self.root.bind_all("<Control-N>", self.on_new_shortcut)

        self.root.bind_all("<Control-s>", self.on_save_shortcut)
        self.root.bind_all("<Control-S>", self.on_save_shortcut)

        self.root.bind_all("<Delete>", self.on_delete_shortcut)

        self.root.bind_all("<Control-c>", self.on_copy_shortcut)
        self.root.bind_all("<Control-C>", self.on_copy_shortcut)

        self.root.bind_all("<Control-v>", self.on_paste_shortcut)
        self.root.bind_all("<Control-V>", self.on_paste_shortcut)

    def on_new_shortcut(self, event=None):
        self.clear_inputs()

    def on_save_shortcut(self, event=None):
        self.save_changes()

    def on_delete_shortcut(self, event=None):
        self.delete_selected_bugs()

    def on_copy_shortcut(self, event=None):
        """
        Копирует данные выбранного бага во внутренний и системный буфер обмена.
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
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(data)
        except tk.TclError:
            pass

    def on_paste_shortcut(self, event=None):
        """
        Вставляет данные бага из системного буфера или внутреннего буфера в форму.
        """
        try:
            clip = self.root.clipboard_get()
        except tk.TclError:
            clip = ""

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

        self.title_var.set(data.get("title", ""))
        self.priority_var.set(data.get("priority", "Normal"))
        self.status_var.set(data.get("status", "Open"))
        self.version_var.set(data.get("version", ""))
        self.steps_text.delete("1.0", "end")
        self.steps_text.insert("1.0", data.get("steps", ""))

    # ---------- Запуск ----------

    def run(self):
        """
        Запускает главный цикл приложения.
        """
        self.root.mainloop()