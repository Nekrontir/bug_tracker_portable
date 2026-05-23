import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

class BugTrackerGUI:
    def __init__(self, service):
        self.service = service
        self.root = tk.Tk()
        self.root.title("Portable Bug Tracker")
        self.root.geometry("860x520")

        self.title_var = tk.StringVar()
        self.priority_var = tk.StringVar(value="Normal")

        self.build_ui()
        self.refresh_list()

    def build_ui(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)

        form = ttk.LabelFrame(frame, text="Новый баг", padding=10)
        form.pack(fill="x")

        ttk.Label(form, text="Заголовок").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.title_var, width=50).grid(row=0, column=1, sticky="we", padx=5)

        ttk.Label(form, text="Приоритет").grid(row=0, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.priority_var, width=15).grid(row=0, column=3, sticky="we", padx=5)

        ttk.Label(form, text="Шаги/заметки").grid(row=1, column=0, sticky="nw", pady=5)
        self.steps_text = tk.Text(form, height=5, width=70)
        self.steps_text.grid(row=1, column=1, columnspan=3, sticky="we", padx=5, pady=5)

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        btns = ttk.Frame(frame)
        btns.pack(fill="x", pady=5)

        ttk.Button(btns, text="Добавить баг", command=self.add_bug).pack(side="left", padx=5)
        ttk.Button(btns, text="Сменить статус", command=self.change_status).pack(side="left", padx=5)
        ttk.Button(btns, text="Удалить", command=self.delete_bug).pack(side="left", padx=5)
        ttk.Button(btns, text="Очистить", command=self.clear_inputs).pack(side="left", padx=5)

        list_frame = ttk.LabelFrame(frame, text="Список багов", padding=10)
        list_frame.pack(fill="both", expand=True)

        cols = ("ID", "Title", "Status", "Priority", "Created")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings")

        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=110 if c != "Title" else 320)

        self.tree.pack(fill="both", expand=True)

    def refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for bug in self.service.get_all():
            self.tree.insert("", "end", values=(
                bug.id,
                bug.title,
                bug.status,
                bug.priority,
                bug.created_at
            ))

    def clear_inputs(self):
        self.title_var.set("")
        self.priority_var.set("Normal")
        self.steps_text.delete("1.0", "end")

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

    def add_bug(self):
        title = self.title_var.get().strip()
        priority = self.priority_var.get().strip() or "Normal"
        steps = self.steps_text.get("1.0", "end").strip()

        if not title:
            messagebox.showwarning("Ошибка", "Введите заголовок бага")
            return

        self.service.add_bug(title, priority, steps)
        self.refresh_list()
        self.clear_inputs()

    def change_status(self):
        bug_id = self.get_selected_bug_id()
        if bug_id is None:
            messagebox.showinfo("Инфо", "Выберите баг в списке")
            return

        new_status = simpledialog.askstring(
            "Статус",
            "Введите новый статус (Open, In Progress, Fixed, Closed):"
        )
        if new_status:
            self.service.change_status(bug_id, new_status.strip())
            self.refresh_list()

    def delete_bug(self):
        bug_id = self.get_selected_bug_id()
        if bug_id is None:
            messagebox.showinfo("Инфо", "Выберите баг в списке")
            return

        if messagebox.askyesno("Удаление", f"Удалить баг #{bug_id}?"):
            self.service.delete_bug(bug_id)
            self.refresh_list()

    def run(self):
        self.root.mainloop()