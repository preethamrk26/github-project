import csv
import re
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "tasks.db"

COLORS = {
    "navy": "#17233c", "blue": "#3b82f6", "blue_dark": "#2563eb",
    "bg": "#f4f7fb", "card": "#ffffff", "text": "#17233c",
    "muted": "#6b7894", "line": "#dfe6f1", "green": "#16a34a",
    "orange": "#f59e0b", "red": "#dc2626", "purple": "#7c3aed"
}

class TaskManager:
    def __init__(self, root):
        self.root = root
        self.root.title("FocusFlow | Student Productivity Manager")
        self.root.geometry("1120x720")
        self.root.minsize(960, 620)
        self.root.configure(bg=COLORS["bg"])
        self.selected_id = None
        self.setup_db()
        self.setup_styles()
        self.build_ui()
        self.load_tasks()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def close(self):
        self.conn.close()
        self.root.destroy()

    def setup_db(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, subject TEXT, priority TEXT NOT NULL,
            due_date TEXT, status TEXT NOT NULL DEFAULT 'Pending',
            notes TEXT, created_at TEXT NOT NULL
        )""")
        self.conn.commit()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="white", fieldbackground="white", foreground=COLORS["text"], rowheight=38, borderwidth=0, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background="#eef3fb", foreground=COLORS["muted"], font=("Segoe UI Semibold", 9), padding=10, relief="flat")
        style.map("Treeview", background=[("selected", "#dceafe")], foreground=[("selected", COLORS["text"])])
        style.configure("TCombobox", padding=7, font=("Segoe UI", 10))
        style.configure("TEntry", padding=7, font=("Segoe UI", 10))

    def label(self, parent, text, size=10, color=None, bold=False):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color or COLORS["text"], font=("Segoe UI", size, "bold" if bold else "normal"))

    def button(self, parent, text, command, primary=False, width=None):
        b = tk.Button(parent, text=text, command=command, cursor="hand2", bd=0, padx=15, pady=9,
                      bg=COLORS["blue"] if primary else "#edf2fb", fg="white" if primary else COLORS["text"],
                      activebackground=COLORS["blue_dark"] if primary else "#dce6f6",
                      activeforeground="white" if primary else COLORS["text"], font=("Segoe UI Semibold", 10))
        if width: b.configure(width=width)
        return b

    def build_ui(self):
        header = tk.Frame(self.root, bg=COLORS["navy"], height=84)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="FocusFlow", bg=COLORS["navy"], fg="white", font=("Segoe UI", 24, "bold")).pack(side="left", padx=30, pady=18)
        tk.Label(header, text="Plan less. Accomplish more.", bg=COLORS["navy"], fg="#a9b8d4", font=("Segoe UI", 11)).pack(side="left", pady=24)
        self.button(header, "AI Assistant", self.open_assistant).pack(side="right", padx=(8, 0), pady=20)
        self.button(header, "Export CSV", self.export_csv).pack(side="right", padx=25, pady=20)

        body = tk.Frame(self.root, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=28, pady=24)
        top = tk.Frame(body, bg=COLORS["bg"])
        top.pack(fill="x")
        self.label(top, "Good day! Here's your study overview.", 20, bold=True).pack(side="left")
        self.date_label = self.label(top, date.today().strftime("%A, %B %d, %Y"), 10, COLORS["muted"])
        self.date_label.pack(side="right", pady=8)

        cards = tk.Frame(body, bg=COLORS["bg"])
        cards.pack(fill="x", pady=(20, 20))
        self.card_values = {}
        for key, title, color in [("total", "TOTAL TASKS", COLORS["blue"]), ("pending", "PENDING", COLORS["orange"]), ("completed", "COMPLETED", COLORS["green"]), ("overdue", "OVERDUE", COLORS["red"])]:
            card = tk.Frame(cards, bg=COLORS["card"], highlightbackground=COLORS["line"], highlightthickness=1)
            card.pack(side="left", fill="x", expand=True, padx=(0, 13))
            tk.Frame(card, bg=color, width=5).pack(side="left", fill="y")
            inner = tk.Frame(card, bg=COLORS["card"]); inner.pack(padx=16, pady=11, fill="both")
            tk.Label(inner, text=title, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI Semibold", 9)).pack(anchor="w")
            v = tk.Label(inner, text="0", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 22, "bold")); v.pack(anchor="w", pady=(3, 0)); self.card_values[key] = v

        content = tk.Frame(body, bg=COLORS["bg"]); content.pack(fill="both", expand=True)
        left = tk.Frame(content, bg=COLORS["card"], highlightbackground=COLORS["line"], highlightthickness=1)
        left.pack(side="left", fill="both", expand=True, padx=(0, 18))
        toolbar = tk.Frame(left, bg=COLORS["card"]); toolbar.pack(fill="x", padx=18, pady=15)
        tk.Label(toolbar, text="My tasks", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 14, "bold")).pack(side="left")
        self.search_var = tk.StringVar(); self.search_var.trace_add("write", lambda *_: self.load_tasks())
        search = ttk.Entry(toolbar, textvariable=self.search_var, width=24); search.pack(side="right", padx=(8, 0));
        tk.Label(toolbar, text="Search", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(side="right")
        filterbar = tk.Frame(left, bg=COLORS["card"]); filterbar.pack(fill="x", padx=18, pady=(0, 10))
        tk.Label(filterbar, text="Show:", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(side="left")
        self.filter_var = tk.StringVar(value="All")
        filterbox = ttk.Combobox(filterbar, textvariable=self.filter_var, values=["All", "Pending", "In Progress", "Completed"], state="readonly", width=14); filterbox.pack(side="left", padx=7); filterbox.bind("<<ComboboxSelected>>", lambda e: self.load_tasks())
        self.progress_label = tk.Label(filterbar, text="0% complete", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)); self.progress_label.pack(side="right")

        columns = ("title", "subject", "priority", "due", "status")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="browse")
        for col, heading, width in [("title", "TASK", 220), ("subject", "SUBJECT", 115), ("priority", "PRIORITY", 85), ("due", "DUE DATE", 105), ("status", "STATUS", 105)]:
            self.tree.heading(col, text=heading); self.tree.column(col, width=width, anchor="w")
        self.tree.tag_configure("overdue", foreground=COLORS["red"]); self.tree.tag_configure("completed", foreground="#8490a5")
        self.tree.pack(fill="both", expand=True, padx=18, pady=(0, 18)); self.tree.bind("<<TreeviewSelect>>", self.on_select)

        right_panel = tk.Frame(content, bg=COLORS["card"], width=285, highlightbackground=COLORS["line"], highlightthickness=1)
        right_panel.pack(side="right", fill="y"); right_panel.pack_propagate(False)
        right_canvas = tk.Canvas(right_panel, bg=COLORS["card"], highlightthickness=0, bd=0)
        right_scrollbar = ttk.Scrollbar(right_panel, orient="vertical", command=right_canvas.yview)
        right_canvas.configure(yscrollcommand=right_scrollbar.set)
        right_scrollbar.pack(side="right", fill="y")
        right_canvas.pack(side="left", fill="both", expand=True)
        right = tk.Frame(right_canvas, bg=COLORS["card"])
        right_window = right_canvas.create_window((0, 0), window=right, anchor="nw")
        right.bind("<Configure>", lambda _: right_canvas.configure(scrollregion=right_canvas.bbox("all")))
        right_canvas.bind("<Configure>", lambda event: right_canvas.itemconfigure(right_window, width=event.width))
        tk.Label(right, text="Task details", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=20, pady=(18, 3))
        tk.Label(right, text="Create a task or select one to edit", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", padx=20, pady=(0, 16))
        form = tk.Frame(right, bg=COLORS["card"]); form.pack(fill="x", padx=20)
        self.title_var = tk.StringVar(); self.subject_var = tk.StringVar(); self.priority_var = tk.StringVar(value="Medium"); self.due_var = tk.StringVar(); self.status_var = tk.StringVar(value="Pending")
        for text, var, values in [("Task title *", self.title_var, None), ("Subject", self.subject_var, None), ("Priority", self.priority_var, ["Low", "Medium", "High"]), ("Due date (YYYY-MM-DD)", self.due_var, None), ("Status", self.status_var, ["Pending", "In Progress", "Completed"])]:
            tk.Label(form, text=text, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI Semibold", 9)).pack(anchor="w", pady=(0, 4))
            if values: ttk.Combobox(form, textvariable=var, values=values, state="readonly").pack(fill="x", pady=(0, 11))
            else: ttk.Entry(form, textvariable=var).pack(fill="x", pady=(0, 11))
        tk.Label(form, text="Notes", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI Semibold", 9)).pack(anchor="w", pady=(0, 4))
        self.notes = tk.Text(form, height=4, font=("Segoe UI", 10), bd=1, relief="solid", highlightthickness=0); self.notes.pack(fill="x", pady=(0, 14))
        self.button(form, "＋  Save task", self.save_task, primary=True).pack(fill="x", pady=(0, 8))
        actions = tk.Frame(form, bg=COLORS["card"]); actions.pack(fill="x")
        self.button(actions, "Clear", self.clear_form).pack(side="left", fill="x", expand=True, padx=(0, 4)); self.button(actions, "Delete", self.delete_task).pack(side="right", fill="x", expand=True, padx=(4, 0))

    def load_tasks(self):
        query = "SELECT * FROM tasks WHERE 1=1"; params = []
        search = self.search_var.get().strip() if hasattr(self, "search_var") else ""
        filt = self.filter_var.get() if hasattr(self, "filter_var") else "All"
        if search: query += " AND (title LIKE ? OR subject LIKE ?)"; params += [f"%{search}%", f"%{search}%"]
        if filt != "All": query += " AND status = ?"; params.append(filt)
        query += " ORDER BY CASE WHEN status='Completed' THEN 1 ELSE 0 END, due_date IS NULL, due_date ASC, id DESC"
        rows = self.conn.execute(query, params).fetchall()
        for item in self.tree.get_children(): self.tree.delete(item)
        today = date.today().isoformat()
        for r in rows:
            tag = "completed" if r["status"] == "Completed" else ("overdue" if r["due_date"] and r["due_date"] < today else "")
            self.tree.insert("", "end", iid=str(r["id"]), values=(r["title"], r["subject"] or "—", r["priority"], r["due_date"] or "—", r["status"]), tags=(tag,))
        allrows = self.conn.execute("SELECT * FROM tasks").fetchall(); total=len(allrows); done=sum(r["status"]=="Completed" for r in allrows); pending=sum(r["status"]!="Completed" for r in allrows); overdue=sum(r["status"]!="Completed" and r["due_date"] and r["due_date"] < today for r in allrows)
        for key, val in [("total", total), ("pending", pending), ("completed", done), ("overdue", overdue)]: self.card_values[key].config(text=str(val))
        self.progress_label.config(text=f"{round(done/total*100) if total else 0}% complete")

    def open_assistant(self):
        assistant = tk.Toplevel(self.root)
        assistant.title("FocusFlow AI Assistant")
        assistant.geometry("720x650")
        assistant.minsize(580, 500)
        assistant.configure(bg=COLORS["bg"])
        assistant.columnconfigure(0, weight=1)
        assistant.rowconfigure(1, weight=1)

        header = tk.Frame(assistant, bg=COLORS["navy"])
        header.grid(row=0, column=0, sticky="ew")
        tk.Label(header, text="FocusFlow AI", bg=COLORS["navy"], fg="white", font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=22, pady=(16, 2))
        tk.Label(header, text="Task guidance, doubt solving, and scheduling", bg=COLORS["navy"], fg="#a9b8d4", font=("Segoe UI", 10)).pack(anchor="w", padx=22, pady=(0, 16))

        chat_frame = tk.Frame(assistant, bg=COLORS["bg"])
        chat_frame.grid(row=1, column=0, sticky="nsew", padx=18, pady=(18, 10))
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)
        chat = tk.Text(chat_frame, wrap="word", state="disabled", bg="white", fg=COLORS["text"], relief="solid", bd=1, padx=16, pady=14, font=("Segoe UI", 10), spacing3=5)
        chat.grid(row=0, column=0, sticky="nsew")
        chat_scroll = ttk.Scrollbar(chat_frame, orient="vertical", command=chat.yview)
        chat_scroll.grid(row=0, column=1, sticky="ns")
        chat.configure(yscrollcommand=chat_scroll.set)
        chat.tag_configure("assistant", foreground=COLORS["blue_dark"], font=("Segoe UI Semibold", 10))
        chat.tag_configure("user", foreground=COLORS["text"], font=("Segoe UI Semibold", 10))

        def add_message(sender, text):
            chat.configure(state="normal")
            tag = "user" if sender == "You" else "assistant"
            chat.insert("end", f"{sender}\n", tag)
            chat.insert("end", f"{text}\n\n")
            chat.configure(state="disabled")
            chat.see("end")

        def ask():
            question = question_var.get().strip()
            if not question:
                return
            question_var.set("")
            add_message("You", question)
            add_message("FocusFlow AI", self.answer_question(question))

        quick = tk.Frame(assistant, bg=COLORS["bg"])
        quick.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 9))
        for column, prompt in enumerate(("Plan my day", "Show overdue", "Explain my task", "Schedule a task")):
            quick.columnconfigure(column, weight=1)
            tk.Button(quick, text=prompt, command=lambda value=prompt: (question_var.set(value), ask()), bd=0, cursor="hand2", bg="#e8eef9", fg=COLORS["text"], padx=8, pady=7, font=("Segoe UI", 9)).grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 4, 4))

        composer = tk.Frame(assistant, bg=COLORS["bg"])
        composer.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 18))
        composer.columnconfigure(0, weight=1)
        question_var = tk.StringVar()
        entry = ttk.Entry(composer, textvariable=question_var, font=("Segoe UI", 11))
        entry.grid(row=0, column=0, sticky="ew", ipady=8)
        send_button = self.button(composer, "Send", ask, primary=True, width=9)
        send_button.grid(row=0, column=1, padx=(8, 0), ipady=2)
        entry.bind("<Return>", lambda _: ask())
        add_message("FocusFlow AI", "Ask me about a task, say what you do not understand, or type a command such as 'schedule maths assignment for tomorrow'.")
        entry.focus_set()

    def answer_question(self, question):
        scheduled = self.schedule_from_question(question)
        if scheduled:
            return scheduled
        rows = self.conn.execute("SELECT * FROM tasks ORDER BY due_date IS NULL, due_date ASC, id DESC").fetchall()
        lowered = question.lower()
        today = date.today().isoformat()
        pending = [row for row in rows if row["status"] != "Completed"]
        overdue = [row for row in pending if row["due_date"] and row["due_date"] < today]
        high_priority = [row for row in pending if row["priority"] == "High"]
        completed = [row for row in rows if row["status"] == "Completed"]

        if not rows:
            return "You do not have any tasks yet. Add your first task from the Task details panel and I will help you organize it."
        if "overdue" in lowered or "late" in lowered:
            if not overdue:
                return "Good news: you have no overdue tasks."
            return "You have %d overdue task(s):\n%s\n\nStart with the oldest due date, then update its status when you finish." % (len(overdue), "\n".join(f"- {row['title']} (due {row['due_date']})" for row in overdue[:8]))
        if "progress" in lowered or "summary" in lowered or "how am i" in lowered:
            percent = round(len(completed) / len(rows) * 100)
            return "You have completed %d of %d tasks (%d%%). There are %d pending and %d overdue. %s" % (len(completed), len(rows), percent, len(pending), len(overdue), "Keep going - your next win is waiting." if pending else "Everything is complete. Nice work!")
        if "today" in lowered or "next" in lowered or "priorit" in lowered or "plan" in lowered:
            choices = sorted(pending, key=lambda row: (0 if row["priority"] == "High" else 1, row["due_date"] is None, row["due_date"] or "9999-12-31"))
            if not choices:
                return "All your tasks are completed. Use the task form to add the next thing you want to accomplish."
            lines = []
            for index, row in enumerate(choices[:5], 1):
                due = row["due_date"] or "no due date"
                lines.append(f"{index}. {row['title']} - {row['priority']} priority, {due}")
            return "Here is your recommended order:\n%s\n\nWork on the first task for 25 minutes, take a short break, then continue down the list." % "\n".join(lines)
        if "high" in lowered or "important" in lowered:
            if not high_priority:
                return "You have no pending high-priority tasks right now."
            return "Your pending high-priority tasks are:\n%s" % "\n".join(f"- {row['title']} ({row['status']})" for row in high_priority[:8])
        matching = [row for row in rows if any(term in (row["title"] + " " + (row["subject"] or "") + " " + (row["notes"] or "")).lower() for term in lowered.split() if len(term) > 3)]
        if matching:
            task = matching[0]
            details = [f"Task: {task['title']}", f"Subject: {task['subject'] or 'Not set'}", f"Status: {task['status']}", f"Due: {task['due_date'] or 'No due date'}"]
            if task["notes"]:
                details.append(f"Your notes: {task['notes']}")
            details.append("Break the task into one small first step, work for 25 minutes, and update its status when you make progress.")
            return "I found the task you mentioned.\n" + "\n".join(details)
        return "I found %d task(s): %d completed, %d pending, and %d overdue. Ask me for a plan, overdue tasks, high-priority work, or a progress summary." % (len(rows), len(completed), len(pending), len(overdue))

    def schedule_from_question(self, question):
        lowered = question.lower().strip()
        scheduling_words = ("schedule", "add task", "create task", "remind me")
        if not any(word in lowered for word in scheduling_words):
            return None
        title = re.sub(r"\b(schedule|add task|create task|remind me|for|on|by)\b", " ", question, flags=re.IGNORECASE)
        due = None
        if "tomorrow" in lowered:
            due = date.today() + timedelta(days=1)
            title = re.sub(r"\btomorrow\b", " ", title, flags=re.IGNORECASE)
        elif "today" in lowered:
            due = date.today()
            title = re.sub(r"\btoday\b", " ", title, flags=re.IGNORECASE)
        else:
            date_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", question)
            if date_match:
                try:
                    due = datetime.strptime(date_match.group(1), "%Y-%m-%d").date()
                except ValueError:
                    return "That date is not valid. Please use YYYY-MM-DD, or say 'tomorrow'."
                title = title.replace(date_match.group(1), " ")
        title = re.sub(r"\s+", " ", title).strip(" ,.-")
        if not title:
            return "Tell me the task name and date, for example: schedule physics revision for tomorrow."
        self.conn.execute("INSERT INTO tasks(title, subject, priority, due_date, status, notes, created_at) VALUES (?,?,?,?,?,?,?)", (title, "", "Medium", due.isoformat() if due else None, "Pending", "Scheduled by FocusFlow AI", datetime.now().isoformat(timespec="seconds")))
        self.conn.commit()
        self.load_tasks()
        due_text = due.strftime("%A, %d %B") if due else "with no due date"
        return f"Scheduled '{title}' for {due_text}. It has been added as a medium-priority pending task."

    def on_select(self, _=None):
        selected = self.tree.selection()
        if not selected: return
        self.selected_id = int(selected[0]); r = self.conn.execute("SELECT * FROM tasks WHERE id=?", (self.selected_id,)).fetchone()
        self.title_var.set(r["title"]); self.subject_var.set(r["subject"] or ""); self.priority_var.set(r["priority"]); self.due_var.set(r["due_date"] or ""); self.status_var.set(r["status"]); self.notes.delete("1.0", "end"); self.notes.insert("1.0", r["notes"] or "")

    def clear_form(self):
        self.selected_id = None
        for v in [self.title_var, self.subject_var, self.due_var]: v.set("")
        self.priority_var.set("Medium"); self.status_var.set("Pending"); self.notes.delete("1.0", "end"); self.tree.selection_remove(self.tree.selection())

    def save_task(self):
        title = self.title_var.get().strip(); due = self.due_var.get().strip(); notes = self.notes.get("1.0", "end").strip()
        if not title: messagebox.showwarning("Missing title", "Please enter a task title."); return
        if due:
            try: datetime.strptime(due, "%Y-%m-%d")
            except ValueError: messagebox.showwarning("Invalid date", "Use the format YYYY-MM-DD, for example 2026-09-30."); return
        values = (title, self.subject_var.get().strip(), self.priority_var.get(), due or None, self.status_var.get(), notes)
        if self.selected_id: self.conn.execute("UPDATE tasks SET title=?, subject=?, priority=?, due_date=?, status=?, notes=? WHERE id=?", values + (self.selected_id,))
        else: self.conn.execute("INSERT INTO tasks(title, subject, priority, due_date, status, notes, created_at) VALUES (?,?,?,?,?,?,?)", values + (datetime.now().isoformat(timespec="seconds"),))
        self.conn.commit(); self.clear_form(); self.load_tasks()

    def delete_task(self):
        if not self.selected_id: messagebox.showinfo("Delete task", "Select a task first."); return
        if messagebox.askyesno("Delete task", "Delete the selected task permanently?"):
            self.conn.execute("DELETE FROM tasks WHERE id=?", (self.selected_id,)); self.conn.commit(); self.clear_form(); self.load_tasks()

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], initialfile="focusflow_tasks.csv")
        if not path: return
        rows = self.conn.execute("SELECT title, subject, priority, due_date, status, notes, created_at FROM tasks ORDER BY due_date").fetchall()
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f); writer.writerow(["Title", "Subject", "Priority", "Due date", "Status", "Notes", "Created at"]); writer.writerows(rows)
        messagebox.showinfo("Export complete", f"Exported {len(rows)} task(s) to:\n{path}")

if __name__ == "__main__":
    root = tk.Tk(); TaskManager(root); root.mainloop()
