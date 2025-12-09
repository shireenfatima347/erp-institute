"""
erp_app_with_credentials.py
Single-file ERP with Tkinter + SQLite.

Features:
- Login (Admin / Teacher / Student)
- Admin can add students, teachers, subjects, notices, assign teacher->subject, create login
- Admin can view stored login credentials and reveal/reset passwords
- Separate attendance and marks tables
- Teacher can mark attendance and update marks per subject/class
- Student can view marks, attendance and notices

Security note:
- For demo convenience passwords are stored as plain text so admin can retrieve them.
  **This is insecure for real systems.** For production, store hashed passwords (bcrypt)
  and implement secure "forgot password" flows.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from datetime import date, datetime

DB = "erp_credentials_erp.db"

# ---------- Database helpers ----------
def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript("""
    -- Users table stores login credentials for admin/teacher/student
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin','teacher','student')),
        reference_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS teachers (
        teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT
    );

    CREATE TABLE IF NOT EXISTS students (
        student_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        roll_no TEXT UNIQUE NOT NULL,
        phone TEXT,
        email TEXT,
        course TEXT
    );

    CREATE TABLE IF NOT EXISTS subjects (
        subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_name TEXT NOT NULL,
        subject_code TEXT UNIQUE
    );

    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER,
        subject_id INTEGER,
        FOREIGN KEY(teacher_id) REFERENCES teachers(teacher_id),
        FOREIGN KEY(subject_id) REFERENCES subjects(subject_id)
    );

    CREATE TABLE IF NOT EXISTS attendance (
        attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        teacher_id INTEGER,
        subject_id INTEGER,
        date TEXT,
        status TEXT CHECK(status IN ('Present','Absent')) DEFAULT 'Absent',
        FOREIGN KEY(student_id) REFERENCES students(student_id),
        FOREIGN KEY(teacher_id) REFERENCES teachers(teacher_id),
        FOREIGN KEY(subject_id) REFERENCES subjects(subject_id)
    );

    CREATE TABLE IF NOT EXISTS marks (
        marks_id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        subject_id INTEGER,
        teacher_id INTEGER,
        marks INTEGER,
        exam_type TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(student_id),
        FOREIGN KEY(subject_id) REFERENCES subjects(subject_id),
        FOREIGN KEY(teacher_id) REFERENCES teachers(teacher_id)
    );

    CREATE TABLE IF NOT EXISTS notices (
        notice_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT,
        date TEXT
    );
    """)
    conn.commit()

    # create default admin user if none exists
    cur.execute("SELECT * FROM users WHERE role='admin'")
    if cur.fetchone() is None:
        # default admin credentials
        cur.execute("INSERT INTO users (username,password,role) VALUES (?,?,?)",
                    ("admin", "admin123", "admin"))
        conn.commit()
    conn.close()

# ---------- Application ----------
class ERPApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ERP - Tkinter + SQLite (Credentials Enabled)")
        self.geometry("1000x650")
        self.resizable(True, True)
        init_db()
        self.user = None  # will store dict row
        self._frame = None
        self.switch_frame(LoginPage)

    def switch_frame(self, frame_class, **kwargs):
        new_frame = frame_class(self, **kwargs)
        if self._frame is not None:
            self._frame.destroy()
        self._frame = new_frame
        self._frame.pack(fill="both", expand=True)

# ---------- Login Page ----------
class LoginPage(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        ttk.Label(self, text="ERP Login", font=("TkDefaultFont", 22)).pack(pady=20)
        form = ttk.Frame(self)
        form.pack(pady=10)

        ttk.Label(form, text="Username").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.username = ttk.Entry(form)
        self.username.grid(row=0, column=1, pady=5)

        ttk.Label(form, text="Password").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.password = ttk.Entry(form, show="*")
        self.password.grid(row=1, column=1, pady=5)

        login_btn = ttk.Button(self, text="Login", command=self.do_login)
        login_btn.pack(pady=10)

        ttk.Label(self, text="Default admin: admin / admin123").pack(pady=5)
        ttk.Button(self, text="Quit", command=self.master.destroy).pack(pady=5)

    def do_login(self):
        u = self.username.get().strip()
        p = self.password.get().strip()
        if not u or not p:
            messagebox.showerror("Error","Enter username and password")
            return
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p))
        row = cur.fetchone()
        conn.close()
        if not row:
            messagebox.showerror("Login failed","Invalid username or password")
            return
        self.master.user = dict(row)
        role = row["role"]
        if role == 'admin':
            self.master.switch_frame(AdminDashboard)
        elif role == 'teacher':
            self.master.switch_frame(TeacherDashboard)
        elif role == 'student':
            self.master.switch_frame(StudentDashboard)
        else:
            messagebox.showerror("Error","Unknown role")

# ---------- Admin Dashboard ----------
class AdminDashboard(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        ttk.Label(self, text="Admin Dashboard", font=("TkDefaultFont", 18)).pack(pady=8)
        top = ttk.Frame(self)
        top.pack(pady=8, fill="x")

        ttk.Button(top, text="Add Student", command=self.add_student).grid(row=0, column=0, padx=6, pady=6)
        ttk.Button(top, text="Add Teacher", command=self.add_teacher).grid(row=0, column=1, padx=6, pady=6)
        ttk.Button(top, text="Add Subject", command=self.add_subject).grid(row=0, column=2, padx=6, pady=6)
        ttk.Button(top, text="Assign Teacher -> Subject", command=self.assign_teacher).grid(row=0, column=3, padx=6, pady=6)
        ttk.Button(top, text="Create Login", command=self.create_login).grid(row=0, column=4, padx=6, pady=6)
        ttk.Button(top, text="Add Notice", command=self.add_notice).grid(row=0, column=5, padx=6, pady=6)
        ttk.Button(top, text="Logout", command=self.logout).grid(row=0, column=6, padx=6, pady=6)

        # Notebook for tabs (Students, Teachers, Subjects, Assignments, Notices, Credentials, Attendance, Marks)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.tabs = {}
        for name in ("Students","Teachers","Subjects","Assignments","Notices","Credentials","Attendance","Marks"):
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=name)
            self.tabs[name] = frame

        self.refresh_all()

    def refresh_all(self):
        self.load_students(); self.load_teachers(); self.load_subjects()
        self.load_assignments(); self.load_notices(); self.load_credentials()
        self.load_attendance(); self.load_marks()

    def logout(self):
        self.master.user = None
        self.master.switch_frame(LoginPage)

    # ---------- Loading functions ----------
    def load_students(self):
        f = self.tabs["Students"]
        for w in f.winfo_children(): w.destroy()
        cols = ("student_id","name","roll_no","phone","email","course")
        tree = ttk.Treeview(f, columns=cols, show="headings", height=12)
        for c in cols: tree.heading(c, text=c.title())
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(f, command=tree.yview); sb.pack(side="right", fill="y")
        tree.configure(yscrollcommand=sb.set)

        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT student_id,name,roll_no,phone,email,course FROM students ORDER BY roll_no")
        for r in cur.fetchall():
            tree.insert("", "end", values=(r["student_id"], r["name"], r["roll_no"], r["phone"], r["email"], r["course"]))
        conn.close()

    def load_teachers(self):
        f = self.tabs["Teachers"]; 
        for w in f.winfo_children(): w.destroy()
        cols = ("teacher_id","name","phone","email")
        tree = ttk.Treeview(f, columns=cols, show="headings", height=12)
        for c in cols: tree.heading(c, text=c.title())
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(f, command=tree.yview); sb.pack(side="right", fill="y")
        tree.configure(yscrollcommand=sb.set)

        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT teacher_id,name,phone,email FROM teachers")
        for r in cur.fetchall():
            tree.insert("", "end", values=(r["teacher_id"], r["name"], r["phone"], r["email"]))
        conn.close()

    def load_subjects(self):
        f = self.tabs["Subjects"]; 
        for w in f.winfo_children(): w.destroy()
        cols = ("subject_id","subject_name","subject_code")
        tree = ttk.Treeview(f, columns=cols, show="headings", height=12)
        for c in cols: tree.heading(c, text=c.title())
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(f, command=tree.yview); sb.pack(side="right", fill="y")
        tree.configure(yscrollcommand=sb.set)

        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT subject_id,subject_name,subject_code FROM subjects")
        for r in cur.fetchall():
            tree.insert("", "end", values=(r["subject_id"], r["subject_name"], r["subject_code"]))
        conn.close()

    def load_assignments(self):
        f = self.tabs["Assignments"]; 
        for w in f.winfo_children(): w.destroy()
        cols = ("id","teacher","subject")
        tree = ttk.Treeview(f, columns=cols, show="headings", height=12)
        for c in cols: tree.heading(c, text=c.title())
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(f, command=tree.yview); sb.pack(side="right", fill="y")
        tree.configure(yscrollcommand=sb.set)

        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            SELECT a.id, t.name as teacher, s.subject_name as subject
            FROM assignments a
            LEFT JOIN teachers t ON a.teacher_id = t.teacher_id
            LEFT JOIN subjects s ON a.subject_id = s.subject_id
        """)
        for r in cur.fetchall():
            tree.insert("", "end", values=(r["id"], r["teacher"], r["subject"]))
        conn.close()

    def load_notices(self):
        f = self.tabs["Notices"]; 
        for w in f.winfo_children(): w.destroy()
        cols = ("notice_id","title","date")
        tree = ttk.Treeview(f, columns=cols, show="headings", height=8)
        for c in cols: tree.heading(c, text=c.title())
        tree.pack(side="top", fill="both", expand=True)
        sb = ttk.Scrollbar(f, command=tree.yview); sb.pack(side="right", fill="y")
        tree.configure(yscrollcommand=sb.set)

        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT notice_id,title,date FROM notices ORDER BY date DESC")
        for r in cur.fetchall():
            tree.insert("", "end", values=(r["notice_id"], r["title"], r["date"]))
        conn.close()

        # show recent notice text below
        text = tk.Text(f, height=6, state="disabled")
        text.pack(side="bottom", fill="x", padx=6, pady=6)
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT title,content,date FROM notices ORDER BY date DESC LIMIT 5")
        text.config(state="normal")
        text.delete("1.0","end")
        for n in cur.fetchall():
            text.insert("end", f"{n['date']} - {n['title']}\n{n['content']}\n\n")
        text.config(state="disabled")
        conn.close()

    def load_credentials(self):
        f = self.tabs["Credentials"]
        for w in f.winfo_children(): w.destroy()
        cols = ("user_id","username","role","reference_id","created_at")
        tree = ttk.Treeview(f, columns=cols, show="headings", height=12)
        for c in cols: tree.heading(c, text=c.title())
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(f, command=tree.yview); sb.pack(side="right", fill="y")
        tree.configure(yscrollcommand=sb.set)

        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT user_id,username,role,reference_id,created_at FROM users ORDER BY created_at DESC")
        for r in cur.fetchall():
            tree.insert("", "end", values=(r["user_id"], r["username"], r["role"], r["reference_id"], r["created_at"]))
        conn.close()

        # controls to reveal/reset password
        ctrl = ttk.Frame(f)
        ctrl.pack(side="bottom", fill="x", padx=6, pady=6)
        ttk.Button(ctrl, text="Show Password", command=lambda: self.show_password(tree)).pack(side="left", padx=6)
        ttk.Button(ctrl, text="Reset Password", command=lambda: self.reset_password(tree)).pack(side="left", padx=6)
        ttk.Button(ctrl, text="Refresh", command=self.load_credentials).pack(side="left", padx=6)
        ttk.Label(ctrl, text="(Admin can view or reset passwords here)").pack(side="left", padx=10)

    def show_password(self, tree):
        sel = tree.selection()
        if not sel:
            messagebox.showerror("Error","Select a user row to show password")
            return
        item = tree.item(sel[0])
        user_id = item["values"][0]
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT username,password,role FROM users WHERE user_id=?", (user_id,))
        r = cur.fetchone(); conn.close()
        if not r:
            messagebox.showerror("Error","User not found")
            return
        # WARNING: reveals plaintext password
        messagebox.showinfo("Password", f"Username: {r['username']}\nRole: {r['role']}\nPassword: {r['password']}")

    def reset_password(self, tree):
        sel = tree.selection()
        if not sel:
            messagebox.showerror("Error","Select a user row to reset password")
            return
        item = tree.item(sel[0])
        user_id = item["values"][0]
        new_pw = simpledialog.askstring("Reset Password", "Enter new password for user (leave blank to cancel)", show="*")
        if not new_pw:
            return
        conn = get_conn(); cur = conn.cursor()
        cur.execute("UPDATE users SET password=?, created_at=? WHERE user_id=?", (new_pw, datetime.now().isoformat(), user_id))
        conn.commit(); conn.close()
        messagebox.showinfo("Success", "Password reset")
        self.load_credentials()

    def load_attendance(self):
        f = self.tabs["Attendance"]
        for w in f.winfo_children(): w.destroy()
        cols = ("attendance_id","student","subject","date","status","marked_by")
        tree = ttk.Treeview(f, columns=cols, show="headings", height=12)
        for c in cols: tree.heading(c, text=c.title())
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(f, command=tree.yview); sb.pack(side="right", fill="y")
        tree.configure(yscrollcommand=sb.set)

        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            SELECT a.attendance_id,
                   COALESCE(s.name, 'Unknown') AS student,
                   COALESCE(sub.subject_name, 'Unknown') AS subject,
                   a.date, a.status,
                   COALESCE(t.name, 'Admin') as marked_by
            FROM attendance a
            LEFT JOIN students s ON a.student_id = s.student_id
            LEFT JOIN subjects sub ON a.subject_id = sub.subject_id
            LEFT JOIN teachers t ON a.teacher_id = t.teacher_id
            ORDER BY a.date DESC
        """)
        for r in cur.fetchall():
            tree.insert("", "end", values=(r["attendance_id"], r["student"], r["subject"], r["date"], r["status"], r["marked_by"]))
        conn.close()

    def load_marks(self):
        f = self.tabs["Marks"]
        for w in f.winfo_children(): w.destroy()
        cols = ("marks_id","student","subject","marks","exam_type","recorded_by","created_at")
        tree = ttk.Treeview(f, columns=cols, show="headings", height=12)
        for c in cols: tree.heading(c, text=c.title())
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(f, command=tree.yview); sb.pack(side="right", fill="y")
        tree.configure(yscrollcommand=sb.set)

        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            SELECT m.marks_id,
                   COALESCE(s.name,'Unknown') AS student,
                   COALESCE(sub.subject_name,'Unknown') AS subject,
                   m.marks, m.exam_type,
                   COALESCE(t.name,'Admin') AS recorded_by,
                   m.created_at
            FROM marks m
            LEFT JOIN students s ON m.student_id = s.student_id
            LEFT JOIN subjects sub ON m.subject_id = sub.subject_id
            LEFT JOIN teachers t ON m.teacher_id = t.teacher_id
            ORDER BY m.created_at DESC
        """)
        for r in cur.fetchall():
            tree.insert("", "end", values=(r["marks_id"], r["student"], r["subject"], r["marks"], r["exam_type"], r["recorded_by"], r["created_at"]))
        conn.close()

    # ---------- Admin actions ----------
    def add_student(self):
        dlg = SimpleForm(self, "Add Student", ("Name","Roll No","Phone","Email","Course"))
        self.wait_window(dlg.top)
        if dlg.result:
            name, roll, phone, email, course = dlg.result
            conn = get_conn(); cur = conn.cursor()
            try:
                cur.execute("INSERT INTO students (name,roll_no,phone,email,course) VALUES (?,?,?,?,?)", (name,roll,phone,email,course))
                conn.commit()
                messagebox.showinfo("Success","Student added")
            except sqlite3.IntegrityError:
                messagebox.showerror("Error","Roll No must be unique")
            conn.close()
            self.refresh_all()

    def add_teacher(self):
        dlg = SimpleForm(self, "Add Teacher", ("Name","Phone","Email"))
        self.wait_window(dlg.top)
        if dlg.result:
            name, phone, email = dlg.result
            conn = get_conn(); cur = conn.cursor()
            cur.execute("INSERT INTO teachers (name,phone,email) VALUES (?,?,?)", (name,phone,email))
            conn.commit(); conn.close()
            messagebox.showinfo("Success","Teacher added")
            self.refresh_all()

    def add_subject(self):
        dlg = SimpleForm(self, "Add Subject", ("Subject Name","Subject Code"))
        self.wait_window(dlg.top)
        if dlg.result:
            name, code = dlg.result
            conn = get_conn(); cur = conn.cursor()
            try:
                cur.execute("INSERT INTO subjects (subject_name,subject_code) VALUES (?,?)", (name,code))
                conn.commit()
                messagebox.showinfo("Success","Subject added")
            except sqlite3.IntegrityError:
                messagebox.showerror("Error","Subject code must be unique")
            conn.close()
            self.refresh_all()

    def assign_teacher(self):
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT teacher_id,name FROM teachers"); teachers = cur.fetchall()
        cur.execute("SELECT subject_id,subject_name FROM subjects"); subjects = cur.fetchall()
        conn.close()
        if not teachers or not subjects:
            messagebox.showerror("Error","Add teachers and subjects first")
            return
        dlg = AssignDialog(self, teachers, subjects)
        self.wait_window(dlg.top)
        if dlg.result:
            t_id, s_id = dlg.result
            conn = get_conn(); cur = conn.cursor()
            cur.execute("INSERT INTO assignments (teacher_id,subject_id) VALUES (?,?)", (t_id, s_id))
            conn.commit(); conn.close()
            messagebox.showinfo("Success","Assigned")
            self.refresh_all()

    def create_login(self):
        role = simpledialog.askstring("Role","Enter role to create login (teacher/student)")
        if not role or role.lower() not in ("teacher","student"):
            messagebox.showerror("Error","Role must be 'teacher' or 'student'")
            return
        conn = get_conn(); cur = conn.cursor()
        if role.lower() == "teacher":
            cur.execute("SELECT teacher_id,name FROM teachers"); rows = cur.fetchall()
        else:
            cur.execute("SELECT student_id,name,roll_no FROM students"); rows = cur.fetchall()
        conn.close()
        if not rows:
            messagebox.showerror("Error","No records found for that role")
            return
        dlg = CreateLoginDialog(self, role.lower(), rows)
        self.wait_window(dlg.top)
        if dlg.result:
            username, password, ref_id = dlg.result
            conn = get_conn(); cur = conn.cursor()
            try:
                cur.execute("INSERT INTO users (username,password,role,reference_id) VALUES (?,?,?,?)",
                            (username,password,role.lower(),ref_id))
                conn.commit()
                messagebox.showinfo("Success","Login created")
            except sqlite3.IntegrityError:
                messagebox.showerror("Error","Username already exists")
            conn.close()
            self.refresh_all()

    def add_notice(self):
        dlg = SimpleForm(self, "Add Notice", ("Title","Content"))
        self.wait_window(dlg.top)
        if dlg.result:
            title, content = dlg.result
            conn = get_conn(); cur = conn.cursor()
            cur.execute("INSERT INTO notices (title,content,date) VALUES (?,?,?)", (title,content,str(date.today())))
            conn.commit(); conn.close()
            messagebox.showinfo("Success","Notice added")
            self.refresh_all()

# ---------- Teacher Dashboard ----------
class TeacherDashboard(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        ttk.Label(self, text="Teacher Dashboard", font=("TkDefaultFont", 18)).pack(pady=8)
        ttk.Button(self, text="Logout", command=self.logout).pack(anchor="ne", padx=10)

        # find teacher ref id from user
        teacher_ref = master.user.get("reference_id")
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT name FROM teachers WHERE teacher_id=?", (teacher_ref,))
        trow = cur.fetchone()
        conn.close()
        tname = trow["name"] if trow else "Teacher"

        ttk.Label(self, text=f"Welcome, {tname}").pack(pady=6)

        # load assigned subjects
        conn = get_conn(); cur = conn.cursor()
        cur.execute("""
            SELECT s.subject_id, s.subject_name, s.subject_code
            FROM assignments a
            JOIN subjects s ON a.subject_id = s.subject_id
            WHERE a.teacher_id = ?
        """, (teacher_ref,))
        self.subjects = cur.fetchall()
        conn.close()

        frame = ttk.Frame(self)
        frame.pack(pady=10)
        ttk.Label(frame, text="Select Subject").grid(row=0, column=0, padx=6)
        self.sub_cb = ttk.Combobox(frame, values=[f"{r['subject_id']} - {r['subject_name']}" for r in self.subjects])
        self.sub_cb.grid(row=0, column=1, padx=6)
        ttk.Button(frame, text="Load Students", command=self.load_students).grid(row=0, column=2, padx=6)

        self.tree = ttk.Treeview(self, columns=("id","roll","name","att","marks"), show="headings", height=18)
        for c in ("id","roll","name","att","marks"):
            self.tree.heading(c, text=c.title())
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        btns = ttk.Frame(self)
        btns.pack(pady=6)
        ttk.Button(btns, text="Mark Attendance (toggle)", command=self.mark_attendance).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Update Marks", command=self.update_marks).grid(row=0, column=1, padx=6)
        ttk.Button(btns, text="Refresh", command=self.load_students).grid(row=0, column=2, padx=6)

        self.load_students_initial()

    def logout(self):
        self.master.user = None
        self.master.switch_frame(LoginPage)

    def load_students_initial(self):
        if not self.subjects:
            messagebox.showinfo("No assignment", "You have no assigned subjects. Contact admin.")
        else:
            self.sub_cb.current(0)
            self.load_students()

    def load_students(self):
        sel = self.sub_cb.get().strip()
        if not sel:
            messagebox.showerror("Error","Select a subject")
            return
        subject_id = int(sel.split(" - ")[0])
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT student_id, name, roll_no FROM students ORDER BY roll_no")
        students = cur.fetchall()
        self.tree.delete(*self.tree.get_children())
        for s in students:
            today = str(date.today())
            cur.execute("SELECT status FROM attendance WHERE student_id=? AND subject_id=? AND date=?", (s["student_id"], subject_id, today))
            att_r = cur.fetchone()
            status = att_r["status"] if att_r else "NotMarked"
            cur.execute("SELECT marks FROM marks WHERE student_id=? AND subject_id=?", (s["student_id"], subject_id))
            m = cur.fetchone()
            marks = m["marks"] if m else ""
            self.tree.insert("", "end", values=(s["student_id"], s["roll_no"], s["name"], status, marks))
        conn.close()

    def mark_attendance(self):
        sel = self.sub_cb.get().strip()
        if not sel:
            messagebox.showerror("Error","Select a subject")
            return
        subject_id = int(sel.split(" - ")[0])
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error","Select a student row to toggle attendance")
            return
        item = self.tree.item(selected[0])
        student_id = item["values"][0]
        today = str(date.today())
        teacher_ref = self.master.user.get("reference_id")
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT attendance_id,status FROM attendance WHERE student_id=? AND subject_id=? AND date=?", (student_id, subject_id, today))
        r = cur.fetchone()
        if r:
            new_status = "Present" if r["status"]=="Absent" else "Absent"
            cur.execute("UPDATE attendance SET status=?, teacher_id=? WHERE attendance_id=?", (new_status, teacher_ref, r["attendance_id"]))
        else:
            new_status = "Present"
            cur.execute("INSERT INTO attendance (student_id,teacher_id,subject_id,date,status) VALUES (?,?,?,?,?)",
                        (student_id, teacher_ref, subject_id, today, new_status))
        conn.commit(); conn.close()
        self.load_students()

    def update_marks(self):
        sel = self.sub_cb.get().strip()
        if not sel:
            messagebox.showerror("Error","Select a subject")
            return
        subject_id = int(sel.split(" - ")[0])
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error","Select a student row to update marks")
            return
        item = self.tree.item(selected[0])
        student_id = item["values"][0]
        current_marks = item["values"][4] or ""
        val = simpledialog.askinteger("Marks", f"Enter marks for student (current: {current_marks})", minvalue=0, maxvalue=100)
        if val is None:
            return
        exam_type = simpledialog.askstring("Exam Type", "Enter exam type (e.g., Midterm, Final) or leave blank")
        teacher_ref = self.master.user.get("reference_id")
        conn = get_conn(); cur = conn.cursor()
        # insert a new marks record (keeps history)
        cur.execute("INSERT INTO marks (student_id,subject_id,teacher_id,marks,exam_type) VALUES (?,?,?,?,?)",
                    (student_id, subject_id, teacher_ref, val, exam_type))
        conn.commit(); conn.close()
        self.load_students()

# ---------- Student Dashboard ----------
class StudentDashboard(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        ttk.Label(self, text="Student Dashboard", font=("TkDefaultFont", 18)).pack(pady=8)
        ttk.Button(self, text="Logout", command=self.logout).pack(anchor="ne", padx=10)

        ref = master.user.get("reference_id")
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT * FROM students WHERE student_id=?", (ref,))
        self.student = cur.fetchone()
        conn.close()
        if not self.student:
            messagebox.showerror("Error","Student record not found")
            master.switch_frame(LoginPage)
            return

        ttk.Label(self, text=f"Welcome, {self.student['name']} (Roll: {self.student['roll_no']})").pack(pady=6)
        ttk.Button(self, text="Refresh Info", command=self.load_info).pack(pady=6)

        ttk.Label(self, text="Notices").pack()
        self.notice_box = tk.Text(self, height=6, width=100, state="disabled")
        self.notice_box.pack(pady=6)

        ttk.Label(self, text="Marks").pack()
        self.mtree = ttk.Treeview(self, columns=("subject","marks","exam_type","recorded_at"), show="headings", height=7)
        for c in ("subject","marks","exam_type","recorded_at"):
            self.mtree.heading(c, text=c.title())
        self.mtree.pack(pady=6)

        ttk.Label(self, text="Attendance (Recent)").pack()
        self.atree = ttk.Treeview(self, columns=("date","subject","status"), show="headings", height=8)
        for c in ("date","subject","status"):
            self.atree.heading(c, text=c.title())
        self.atree.pack(pady=6)

        self.load_info()

    def logout(self):
        self.master.user = None
        self.master.switch_frame(LoginPage)

    def load_info(self):
        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT title,content,date FROM notices ORDER BY date DESC LIMIT 5")
        notices = cur.fetchall()
        self.notice_box.config(state="normal")
        self.notice_box.delete("1.0","end")
        for n in notices:
            self.notice_box.insert("end", f"{n['date']} - {n['title']}\n{n['content']}\n\n")
        self.notice_box.config(state="disabled")

        self.mtree.delete(*self.mtree.get_children())
        cur.execute("""
            SELECT sub.subject_name as subject, m.marks, m.exam_type, m.created_at
            FROM marks m
            JOIN subjects sub ON m.subject_id = sub.subject_id
            WHERE m.student_id = ?
            ORDER BY m.created_at DESC
        """, (self.student["student_id"],))
        for r in cur.fetchall():
            self.mtree.insert("", "end", values=(r["subject"], r["marks"], r["exam_type"], r["created_at"]))

        self.atree.delete(*self.atree.get_children())
        cur.execute("""
            SELECT a.date, sub.subject_name as subject, a.status
            FROM attendance a
            JOIN subjects sub ON a.subject_id = sub.subject_id
            WHERE a.student_id = ?
            ORDER BY a.date DESC LIMIT 20
        """, (self.student["student_id"],))
        for r in cur.fetchall():
            self.atree.insert("", "end", values=(r["date"], r["subject"], r["status"]))
        conn.close()

# ---------- Utility dialogs ----------
class SimpleForm:
    def __init__(self, parent, title, fields):
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.entries = []
        frame = ttk.Frame(self.top); frame.pack(padx=10,pady=10)
        for i, f in enumerate(fields):
            ttk.Label(frame, text=f).grid(row=i, column=0, padx=6, pady=6, sticky="e")
            e = ttk.Entry(frame, width=50)
            e.grid(row=i, column=1, padx=6, pady=6)
            self.entries.append(e)
        btn = ttk.Button(frame, text="OK", command=self.on_ok); btn.grid(row=len(fields), column=0, columnspan=2, pady=8)
        self.result = None

    def on_ok(self):
        vals = [e.get().strip() for e in self.entries]
        if any(v=="" for v in vals):
            messagebox.showerror("Error","All fields required")
            return
        self.result = vals
        self.top.destroy()

class AssignDialog:
    def __init__(self, parent, teachers, subjects):
        self.top = tk.Toplevel(parent)
        self.top.title("Assign Teacher to Subject")
        ttk.Label(self.top, text="Select Teacher").grid(row=0, column=0, padx=6, pady=6)
        self.tcb = ttk.Combobox(self.top, values=[f"{r['teacher_id']} - {r['name']}" for r in teachers]); self.tcb.grid(row=0, column=1)
        ttk.Label(self.top, text="Select Subject").grid(row=1, column=0, padx=6, pady=6)
        self.scb = ttk.Combobox(self.top, values=[f"{r['subject_id']} - {r['subject_name']}" for r in subjects]); self.scb.grid(row=1, column=1)
        ttk.Button(self.top, text="Assign", command=self.assign).grid(row=2, column=0, columnspan=2, pady=8)
        self.result = None

    def assign(self):
        t = self.tcb.get().strip(); s = self.scb.get().strip()
        if not t or not s: messagebox.showerror("Error","Select both"); return
        tid = int(t.split(" - ")[0]); sid = int(s.split(" - ")[0])
        self.result = (tid, sid); self.top.destroy()

class CreateLoginDialog:
    def __init__(self, parent, role, rows):
        self.top = tk.Toplevel(parent)
        self.top.title("Create Login")
        ttk.Label(self.top, text="Select " + role.title()).grid(row=0, column=0, padx=6, pady=6)
        # rows may contain extra col for roll_no - map accordingly
        display = []
        for r in rows:
            if 'roll_no' in r.keys():
                display.append(f"{r[0]} - {r['name']} ({r['roll_no']})")
            else:
                display.append(f"{r[0]} - {r['name']}")
        self.cb = ttk.Combobox(self.top, values=display); self.cb.grid(row=0, column=1)
        ttk.Label(self.top, text="Username").grid(row=1, column=0, padx=6, pady=6)
        self.u = ttk.Entry(self.top); self.u.grid(row=1, column=1)
        ttk.Label(self.top, text="Password").grid(row=2, column=0, padx=6, pady=6)
        self.p = ttk.Entry(self.top, show="*"); self.p.grid(row=2, column=1)
        ttk.Button(self.top, text="Create", command=self.create).grid(row=3, column=0, columnspan=2, pady=8)
        self.result = None

    def create(self):
        sel = self.cb.get().strip(); username = self.u.get().strip(); password = self.p.get().strip()
        if not sel or not username or not password: messagebox.showerror("Error","All fields required"); return
        ref_id = int(sel.split(" - ")[0])
        self.result = (username,password,ref_id)
        self.top.destroy()

# ---------- Start App ----------
if __name__ == "__main__":
    app = ERPApp()
    app.mainloop()
