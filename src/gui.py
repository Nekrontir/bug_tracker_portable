import tkinter as tk
from tkinter import messagebox, filedialog
import json

import ttkbootstrap as ttkb
from ttkbootstrap.constants import *


class BugTrackerGUI:
    STATUSES = ("Open", "In Progress", "Fixed", "Closed")
    PRIORITIES = ("Low", "Normal", "High", "Critical")
    THEMES = ("flatly", "cosmo", "litera", "darkly", "superhero", "cyborg")

    def __init__(self, service):
        self.service = service

        # Главное окно ttkbootstrap
        self.root = ttkb.Window(title="Portable Bug Tracker", themename="flatly")
        self.root.geometry("1000x700")

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
        self.selected_bug_id = None

        # Копирование/вставка (внутренний буфер)
        self.copied_bug_data = None

        # Флаг "импорт с заменой"
        self.import_replace_var = tk.BooleanVar(value=False)

        self.style = self.root.style

        self.build_ui()
        self.bind_shortcuts()
        self.refresh_list()

    def build_ui(self):
        # Верхняя панель: тема + экспорт/импорт
        top_bar = ttkb.Frame(self.root, padding=(10, 5))
        top_bar.pack(fill=X)

        # Левая часть: экспорт / импорт
        export_frame = ttkb.Frame(top_bar)
        export_frame.pack(side=LEFT)

        ttkb.Button(export_frame, text="Экспорт", bootstyle=INFO, command=self.export_bugs).pack(side=LEFT, padx=2)
        ttkb.Button(export_frame, text="Импорт", bootstyle=WARNING, command=self.import_bugs).pack(side=LEFT, padx=2)

        # Чекбокс "Импорт с заменой"
        ttkb.Checkbutton(
            export_frame,
            text="с заменой",
            variable=self.import_replace_var,
            bootstyle="round-toggle"  # красивый переключатель ttkbootstrap [web:169]
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

        ttkb.Label(form, text="Шаги/заметки").grid(row=1, column=0, sticky=NW, pady=5)
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
        search_entry = ttkb.Entry(filter_frame, textvariable=self.search_var, width=22)
        search_entry.grid(row=0, column=5, sticky=W, padx=5)

        ttkb.Button(filter_frame, text="Применить", bootstyle=PRIMARY, command=self.apply_filter).grid(row=0, column=6, padx=10)
        ttkb.Button(filter_frame, text="Сбросить", bootstyle=SECONDARY, command=self.reset_filter).grid(row=0, column=7, padx=5)

        # Таблица багов
        list_frame = ttkb.Labelframe(frame, text="Список багов", padding=10)
        list_frame.pack(fill=BOTH, expand=YES)

        cols = ("ID", "Title", "Status", "Priority", "Version", "Created")
        self.tree = ttkb.Treeview(list_frame, columns=cols, show="headings")

        for c in cols:
            self.tree.heading(c, text=c)
            if c == "Title":
                self.tree.column(c, width=260)
            elif c == "Version":
                self.tree.column(c, width=80)
            else:
                self.tree.column(c, width=110)

        self.tree.pack(fill=BOTH, expand=YES)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # Кнопка удаления ближе к списку
        bottom_btns = ttkb.Frame(frame)
        bottom_btns.pack(fill=X, pady=5)
        ttkb.Button(bottom_btns, text="Удалить выбранный баг", bootstyle=DANGER, command=self.delete_bug).pack(side=RIGHT, padx=5)

    # ---------- Темы ----------

    def change_theme(self):
        theme = self.theme_combo.get()
        if theme:
            self.style.theme_use(theme)

    # ---------- Работа со списком ----------

    def refresh_list(self, bugs=None):
        self.tree.delete(*self.tree.get_children())
        source = bugs if bugs is not None else self.service.get_all()
        for bug in source:
            self.tree.insert("", "end", values=(
                bug.id,
                bug.title,
                bug.status,
                bug.priority,
                getattr(bug, "version", ""),
                bug.created_at
            ))

    def apply_filter(self):
        status = self.filter_status_var.get()
        priority = self.filter_priority_var.get()
        query = self.search_var.get().strip()
        filtered = self.service.filter_bugs(status=status, priority=priority, query=query)
        self.refresh_list(filtered)

    def reset_filter(self):
        self.filter_status_var.set("All")
        self.filter_priority_var.set("All")
        self.search_var.set("")
        self.refresh_list()

    # ---------- Форма / выбор ----------

    def clear_inputs(self):
        self.title_var.set("")
        self.priority_var.set("Normal")
        self.status_var.set("Open")
        self.version_var.set("")
        self.steps_text.delete("1.0", "end")
        self.selected_bug_id = None
        self.tree.selection_remove(self.tree.selection())
        self.title_entry.focus_set()

    def get_selected_bug_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        values = self.tree.item(sel[0], "values")
        if not values:
            return None
        try:
            return int(values[0])
        except ValueError:
            return None

    def on_select(self, event=None):
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

    # ---------- Операции ----------

    def add_bug(self):
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

    def delete_bug(self):
        bug_id = self.get_selected_bug_id()
        if bug_id is None:
            messagebox.showinfo("Инфо", "Выберите баг в списке")
            return

        if messagebox.askyesno("Удаление", f"Удалить баг #{bug_id}?"):
            self.service.delete_bug(bug_id)
            self.refresh_list()
            self.clear_inputs()

    # ---------- Экспорт / импорт ----------

    def export_bugs(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Экспорт багов в JSON"
        )
        if not path:
            return
        try:
            self.service.export_bugs(path)
            messagebox.showinfo("Экспорт", "Экспорт успешно завершён")
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", str(e))

    def import_bugs(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Импорт багов из JSON"
        )
        if not path:
            return
        try:
            merge = not self.import_replace_var.get()  # если галка стоит, merge=False
            self.service.import_bugs(path, merge=merge)
            self.refresh_list()
            messagebox.showinfo("Импорт", "Импорт успешно завершён")
        except Exception as e:
            messagebox.showerror("Ошибка импорта", str(e))

    # ---------- Хоткеи ----------

    def bind_shortcuts(self):
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
        self.delete_bug()

    def on_copy_shortcut(self, event=None):
        bug_id = self.get_selected_bug_id()
        if bug_id is None:
            return
        bug = self.service.get_by_id(bug_id)
        if not bug:
            return

        # внутренний буфер
        self.copied_bug_data = {
            "title": bug.title,
            "priority": bug.priority,
            "status": bug.status,
            "version": getattr(bug, "version", ""),
            "steps": bug.steps,
        }

        # системный буфер обмена — JSON с данными бага
        data = json.dumps(self.copied_bug_data, ensure_ascii=False, indent=2)
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(data)
        except tk.TclError:
            pass

    def on_paste_shortcut(self, event=None):
        # пробуем сначала взять JSON из системного буфера
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
        self.root.mainloop()