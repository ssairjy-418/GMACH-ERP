import os
import sqlite3
from datetime import datetime, date
from functools import wraps
from flask import Flask, request, redirect, url_for, session, flash, render_template_string, send_file

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "gmach_erp.db")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "gmach-erp-change-this-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ROLES = ["Admin", "HR", "Manager", "Inventory", "Employee"]

BASE_CSS = """
:root{--bg:#f5f7fb;--card:#fff;--text:#172033;--muted:#667085;--primary:#2563eb;--danger:#dc2626;--success:#16a34a;--border:#e5e7eb}
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;background:var(--bg);color:var(--text)}
a{text-decoration:none;color:inherit}.nav{background:#111827;color:#fff;padding:14px 18px;display:flex;align-items:center;justify-content:space-between;gap:12px;position:sticky;top:0;z-index:10}
.brand{font-size:20px;font-weight:800}.navlinks{display:flex;gap:7px;flex-wrap:wrap}.navlinks a{padding:8px 10px;border-radius:8px;font-size:13px}.navlinks a:hover{background:#253047}
.container{max-width:1200px;margin:auto;padding:20px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:18px;box-shadow:0 2px 8px rgba(0,0,0,.03)}
.kpi{font-size:28px;font-weight:800;margin-top:7px}.muted{color:var(--muted);font-size:13px}.title{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:16px}.title h1,.title h2{margin:0}
table{width:100%;border-collapse:collapse;background:#fff}.tablewrap{overflow:auto;border:1px solid var(--border);border-radius:12px}th,td{padding:11px 12px;border-bottom:1px solid var(--border);text-align:left;white-space:nowrap;font-size:13px}th{background:#f8fafc;font-weight:700}
.formgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.field{display:flex;flex-direction:column;gap:6px}.field.full{grid-column:1/-1}label{font-size:13px;font-weight:650}
input,select,textarea{width:100%;padding:10px 11px;border:1px solid #d0d5dd;border-radius:9px;background:#fff;font:inherit;font-size:14px}textarea{min-height:90px;resize:vertical}
button,.btn{border:0;border-radius:9px;padding:10px 14px;background:var(--primary);color:#fff;font-weight:700;cursor:pointer;display:inline-block;font-size:14px}.btn.secondary{background:#475467}.btn.success{background:var(--success)}.btn.danger{background:var(--danger)}.btn.light{background:#eef2ff;color:#3730a3}
.actions{display:flex;gap:7px;flex-wrap:wrap;margin-top:14px}.flash{padding:11px 13px;border-radius:9px;background:#ecfdf3;color:#166534;margin-bottom:12px}.flash.error{background:#fef2f2;color:#991b1b}
.badge{display:inline-block;padding:4px 8px;border-radius:999px;font-size:12px;font-weight:700;background:#eef2ff;color:#3730a3}.badge.green{background:#dcfce7;color:#166534}.badge.red{background:#fee2e2;color:#991b1b}.badge.yellow{background:#fef3c7;color:#92400e}
.login{min-height:100vh;display:grid;place-items:center;padding:20px;background:linear-gradient(135deg,#111827,#1d4ed8)}.loginbox{width:min(420px,100%);background:#fff;border-radius:18px;padding:26px;box-shadow:0 20px 60px rgba(0,0,0,.25)}.loginbox h1{margin:0 0 5px}.loginbox .field{margin-top:12px}
.small{font-size:12px}.footer{text-align:center;color:#98a2b3;padding:30px}.dangertext{color:#b42318}
@media(max-width:800px){.grid{grid-template-columns:repeat(2,1fr)}.nav{align-items:flex-start;flex-direction:column}.navlinks{width:100%;overflow:auto;flex-wrap:nowrap}.formgrid{grid-template-columns:1fr}.field.full{grid-column:auto}.container{padding:14px}.kpi{font-size:23px}}
@media(max-width:480px){.grid{grid-template-columns:1fr 1fr}.card{padding:14px}.navlinks a{font-size:12px;padding:7px 8px}}
"""

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'Employee',
        department TEXT DEFAULT '',
        designation TEXT DEFAULT '',
        phone TEXT DEFAULT '',
        joining_date TEXT DEFAULT '',
        status TEXT DEFAULT 'Active',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id TEXT NOT NULL,
        work_date TEXT NOT NULL,
        check_in TEXT,
        check_out TEXT,
        UNIQUE(employee_id,work_date)
    );
    CREATE TABLE IF NOT EXISTS leaves(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id TEXT NOT NULL,
        leave_type TEXT NOT NULL,
        from_date TEXT NOT NULL,
        to_date TEXT NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'Pending',
        applied_at TEXT NOT NULL,
        approved_by TEXT
    );
    CREATE TABLE IF NOT EXISTS inventory(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_code TEXT UNIQUE NOT NULL,
        item_name TEXT NOT NULL,
        category TEXT DEFAULT '',
        brand TEXT DEFAULT '',
        serial_no TEXT DEFAULT '',
        quantity INTEGER DEFAULT 0,
        min_quantity INTEGER DEFAULT 0,
        location TEXT DEFAULT '',
        supplier TEXT DEFAULT '',
        purchase_date TEXT DEFAULT '',
        assigned_to TEXT DEFAULT '',
        status TEXT DEFAULT 'Available',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS inventory_txn(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        employee_id TEXT DEFAULT '',
        txn_type TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        notes TEXT DEFAULT '',
        txn_at TEXT NOT NULL
    );
    """)
    admin = con.execute("SELECT id FROM users WHERE employee_id='ADMIN001'").fetchone()
    if not admin:
        con.execute("""INSERT INTO users(employee_id,name,email,password,role,department,designation,status,created_at)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    ("ADMIN001","System Administrator","admin@gmachaero.com",
                     "ChangeMe123!","Admin","Administration","Administrator","Active",datetime.now().isoformat(timespec="seconds")))
    con.commit()
    con.close()

def current_user():
    if not session.get("employee_id"):
        return None
    con = db()
    row = con.execute("SELECT * FROM users WHERE employee_id=?", (session["employee_id"],)).fetchone()
    con.close()
    return row

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            u = current_user()
            if not u:
                return redirect(url_for("login"))
            if u["role"] not in roles:
                flash("You do not have permission for this page.", "error")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapper
    return deco

def layout(title, body, **ctx):
    u = current_user()
    nav = ""
    if u:
        nav = f"""
        <nav class="nav">
          <div class="brand">GMACH-ERP</div>
          <div class="navlinks">
            <a href="{url_for('dashboard')}">Dashboard</a>
            <a href="{url_for('attendance')}">Attendance</a>
            <a href="{url_for('leaves')}">Leave</a>
            <a href="{url_for('inventory')}">Inventory</a>
            <a href="{url_for('employees')}">Employees</a>
            <a href="{url_for('profile')}">Profile</a>
            <a href="{url_for('change_password')}">Password</a>
            <a href="{url_for('logout')}">Logout</a>
          </div>
        </nav>"""
    flashes = ""
    for msg in []:
        flashes += msg
    return render_template_string("""
    <!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{{title}} - GMACH-ERP</title><style>{{css|safe}}</style></head><body>
    {{nav|safe}}<main class="container">
    {% with messages=get_flashed_messages(with_categories=true) %}
      {% for category,message in messages %}<div class="flash {% if category=='error' %}error{% endif %}">{{message}}</div>{% endfor %}
    {% endwith %}
    {{body|safe}}
    </main><div class="footer">GMACH-ERP • Personal Project</div></body></html>
    """, title=title, css=BASE_CSS, nav=nav, **ctx)

@app.route("/")
def index():
    return redirect(url_for("dashboard") if current_user() else url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("identifier","").strip()
        password = request.form.get("password","")
        con = db()
        user = con.execute("""SELECT * FROM users WHERE (employee_id=? OR lower(email)=lower(?)) AND password=? AND status='Active'""",
                           (identifier,identifier,password)).fetchone()
        con.close()
        if user:
            session["employee_id"] = user["employee_id"]
            flash("Login successful.")
            return redirect(url_for("dashboard"))
        flash("Invalid login details.", "error")
    body = """
    <div class="login"><div class="loginbox">
      <h1>GMACH-ERP</h1><div class="muted">Attendance • Inventory • HR</div>
      <form method="post">
        <div class="field"><label>Email or Employee ID</label><input name="identifier" required autocomplete="username"></div>
        <div class="field"><label>Password</label><input name="password" type="password" required autocomplete="current-password"></div>
        <div class="actions"><button type="submit">Login</button></div>
      </form>
      <hr style="border:0;border-top:1px solid #eee;margin:20px 0">
      <div class="small"><b>First login:</b> ADMIN001 / ChangeMe123!</div>
    </div></div>
    """
    return render_template_string("""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Login</title><style>""" + BASE_CSS + """</style></head><body>""" + body + "</body></html>")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    u = current_user()
    con = db()
    employees = con.execute("SELECT COUNT(*) c FROM users WHERE status='Active'").fetchone()["c"]
    today = date.today().isoformat()
    present = con.execute("SELECT COUNT(*) c FROM attendance WHERE work_date=? AND check_in IS NOT NULL", (today,)).fetchone()["c"]
    on_leave = con.execute("SELECT COUNT(*) c FROM leaves WHERE ? BETWEEN from_date AND to_date AND status='Approved'", (today,)).fetchone()["c"]
    items = con.execute("SELECT COUNT(*) c FROM inventory").fetchone()["c"]
    low = con.execute("SELECT COUNT(*) c FROM inventory WHERE quantity<=min_quantity").fetchone()["c"]
    recent = con.execute("SELECT * FROM inventory ORDER BY id DESC LIMIT 5").fetchall()
    con.close()
    body = """
    <div class="title"><div><h1>Dashboard</h1><div class="muted">Welcome, {{u['name']}} • {{u['role']}}</div></div></div>
    <div class="grid">
      <div class="card"><div class="muted">Active Employees</div><div class="kpi">{{employees}}</div></div>
      <div class="card"><div class="muted">Present Today</div><div class="kpi">{{present}}</div></div>
      <div class="card"><div class="muted">On Leave Today</div><div class="kpi">{{on_leave}}</div></div>
      <div class="card"><div class="muted">Inventory Items</div><div class="kpi">{{items}}</div></div>
    </div>
    <div class="grid" style="margin-top:14px">
      <div class="card"><div class="muted">Low Stock Items</div><div class="kpi">{{low}}</div></div>
      <div class="card"><div class="muted">Today's Date</div><div class="kpi" style="font-size:20px">{{today}}</div></div>
    </div>
    <div class="card" style="margin-top:14px"><div class="title"><h2>Quick Actions</h2></div>
      <div class="actions">
        <a class="btn" href="{{url_for('attendance')}}">Attendance</a>
        <a class="btn" href="{{url_for('inventory')}}">Inventory</a>
        <a class="btn secondary" href="{{url_for('leaves')}}">Leave</a>
        <a class="btn light" href="{{url_for('employees')}}">Employee Master</a>
      </div>
    </div>
    <div class="card" style="margin-top:14px"><div class="title"><h2>Recent Inventory</h2></div>
      <div class="tablewrap"><table><tr><th>Code</th><th>Item</th><th>Qty</th><th>Location</th></tr>
      {% for r in recent %}<tr><td>{{r['item_code']}}</td><td>{{r['item_name']}}</td><td>{{r['quantity']}}</td><td>{{r['location']}}</td></tr>{% endfor %}
      </table></div>
    </div>
    """
    return layout("Dashboard", body, u=u, employees=employees, present=present, on_leave=on_leave,
                  items=items, low=low, today=today, recent=recent)

@app.route("/attendance")
@login_required
def attendance():
    u = current_user()
    con = db()
    if u["role"] in ("Admin","HR","Manager"):
        rows = con.execute("""SELECT a.*,u.name,u.department FROM attendance a LEFT JOIN users u ON u.employee_id=a.employee_id
                              ORDER BY a.work_date DESC,a.id DESC LIMIT 200""").fetchall()
    else:
        rows = con.execute("""SELECT a.*,u.name,u.department FROM attendance a LEFT JOIN users u ON u.employee_id=a.employee_id
                              WHERE a.employee_id=? ORDER BY a.work_date DESC,a.id DESC LIMIT 100""", (u["employee_id"],)).fetchall()
    today = con.execute("SELECT * FROM attendance WHERE employee_id=? AND work_date=?", (u["employee_id"], date.today().isoformat())).fetchone()
    con.close()
    body = """
    <div class="title"><div><h1>Attendance</h1><div class="muted">Daily check-in / check-out</div></div></div>
    <div class="card">
      <h2>Today: {{today_date}}</h2>
      {% if today %}
        <p>Check-in: <b>{{today['check_in'] or '-'}}</b> &nbsp; Check-out: <b>{{today['check_out'] or '-'}}</b></p>
      {% else %}<p class="muted">No attendance marked yet.</p>{% endif %}
      <div class="actions">
        {% if not today or not today['check_in'] %}<form method="post" action="{{url_for('check_in')}}"><button class="btn success">Check In</button></form>{% endif %}
        {% if today and today['check_in'] and not today['check_out'] %}<form method="post" action="{{url_for('check_out')}}"><button class="btn danger">Check Out</button></form>{% endif %}
      </div>
    </div>
    <div class="card" style="margin-top:14px"><div class="title"><h2>Attendance Records</h2><a class="btn light" href="{{url_for('attendance_csv')}}">Export CSV</a></div>
      <div class="tablewrap"><table><tr><th>Date</th><th>Employee</th><th>Department</th><th>Check In</th><th>Check Out</th></tr>
      {% for r in rows %}<tr><td>{{r['work_date']}}</td><td>{{r['name'] or r['employee_id']}}</td><td>{{r['department'] or '-'}}</td><td>{{r['check_in'] or '-'}}</td><td>{{r['check_out'] or '-'}}</td></tr>{% endfor %}
      </table></div>
    </div>
    """
    return layout("Attendance", body, today=today, today_date=date.today().isoformat(), rows=rows)

@app.post("/attendance/check-in")
@login_required
def check_in():
    u = current_user()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    d = date.today().isoformat()
    con = db()
    try:
        con.execute("INSERT INTO attendance(employee_id,work_date,check_in) VALUES(?,?,?)", (u["employee_id"],d,now))
        con.commit()
        flash("Check-in recorded.")
    except sqlite3.IntegrityError:
        flash("Today's attendance already exists.", "error")
    con.close()
    return redirect(url_for("attendance"))

@app.post("/attendance/check-out")
@login_required
def check_out():
    u = current_user()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    con = db()
    con.execute("UPDATE attendance SET check_out=? WHERE employee_id=? AND work_date=? AND check_out IS NULL",
                (now,u["employee_id"],date.today().isoformat()))
    con.commit()
    con.close()
    flash("Check-out recorded.")
    return redirect(url_for("attendance"))

@app.route("/employees", methods=["GET","POST"])
@roles_required("Admin","HR","Manager")
def employees():
    if request.method == "POST":
        f = request.form
        try:
            con = db()
            con.execute("""INSERT INTO users(employee_id,name,email,password,role,department,designation,phone,joining_date,status,created_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (f["employee_id"].strip(),f["name"].strip(),f["email"].strip(),f.get("password") or "ChangeMe123!",
                         f["role"],f.get("department",""),f.get("designation",""),f.get("phone",""),f.get("joining_date",""),
                         f.get("status","Active"),datetime.now().isoformat(timespec="seconds")))
            con.commit(); con.close()
            flash("Employee added successfully.")
        except sqlite3.IntegrityError:
            flash("Employee ID or email already exists.", "error")
        return redirect(url_for("employees"))
    con = db()
    rows = con.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    con.close()
    body = """
    <div class="title"><div><h1>Employee Master</h1><div class="muted">HR and employee records</div></div></div>
    <div class="card">
      <h2>Add Employee</h2>
      <form method="post"><div class="formgrid">
        <div class="field"><label>Employee ID *</label><input name="employee_id" required></div>
        <div class="field"><label>Name *</label><input name="name" required></div>
        <div class="field"><label>Email *</label><input name="email" type="email" required></div>
        <div class="field"><label>Initial Password</label><input name="password" placeholder="ChangeMe123!"></div>
        <div class="field"><label>Role</label><select name="role">{% for r in roles %}<option>{{r}}</option>{% endfor %}</select></div>
        <div class="field"><label>Department</label><input name="department"></div>
        <div class="field"><label>Designation</label><input name="designation"></div>
        <div class="field"><label>Phone</label><input name="phone"></div>
        <div class="field"><label>Joining Date</label><input name="joining_date" type="date"></div>
        <div class="field"><label>Status</label><select name="status"><option>Active</option><option>Inactive</option></select></div>
      </div><div class="actions"><button>Add Employee</button></div></form>
    </div>
    <div class="card" style="margin-top:14px"><div class="title"><h2>Employees</h2></div>
    <div class="tablewrap"><table><tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th><th>Department</th><th>Designation</th><th>Status</th></tr>
    {% for r in rows %}<tr><td>{{r['employee_id']}}</td><td>{{r['name']}}</td><td>{{r['email']}}</td><td>{{r['role']}}</td><td>{{r['department']}}</td><td>{{r['designation']}}</td><td>{{r['status']}}</td></tr>{% endfor %}
    </table></div></div>
    """
    return layout("Employees", body, rows=rows, roles=ROLES)

@app.route("/profile")
@login_required
def profile():
    u = current_user()
    body = """
    <div class="title"><h1>My Profile</h1></div>
    <div class="card"><div class="formgrid">
      <div><div class="muted">Employee ID</div><b>{{u['employee_id']}}</b></div>
      <div><div class="muted">Name</div><b>{{u['name']}}</b></div>
      <div><div class="muted">Email</div><b>{{u['email']}}</b></div>
      <div><div class="muted">Role</div><b>{{u['role']}}</b></div>
      <div><div class="muted">Department</div><b>{{u['department'] or '-'}}</b></div>
      <div><div class="muted">Designation</div><b>{{u['designation'] or '-'}}</b></div>
      <div><div class="muted">Phone</div><b>{{u['phone'] or '-'}}</b></div>
      <div><div class="muted">Joining Date</div><b>{{u['joining_date'] or '-'}}</b></div>
    </div></div>
    """
    return layout("Profile", body, u=u)

@app.route("/change-password", methods=["GET","POST"])
@login_required
def change_password():
    u = current_user()
    if request.method == "POST":
        old = request.form.get("old_password","")
        new = request.form.get("new_password","")
        confirm = request.form.get("confirm_password","")
        if old != u["password"]:
            flash("Current password is incorrect.", "error")
        elif len(new) < 8:
            flash("New password must be at least 8 characters.", "error")
        elif new != confirm:
            flash("New passwords do not match.", "error")
        else:
            con = db(); con.execute("UPDATE users SET password=? WHERE employee_id=?", (new,u["employee_id"])); con.commit(); con.close()
            flash("Password changed successfully.")
            return redirect(url_for("profile"))
    body = """
    <div class="title"><h1>Change Password</h1></div>
    <div class="card"><form method="post"><div class="formgrid">
      <div class="field full"><label>Current Password</label><input name="old_password" type="password" required></div>
      <div class="field"><label>New Password</label><input name="new_password" type="password" minlength="8" required></div>
      <div class="field"><label>Confirm Password</label><input name="confirm_password" type="password" minlength="8" required></div>
    </div><div class="actions"><button>Change Password</button></div></form></div>
    """
    return layout("Change Password", body)

@app.route("/leaves", methods=["GET","POST"])
@login_required
def leaves():
    u = current_user()
    if request.method == "POST":
        f = request.form
        con = db()
        con.execute("""INSERT INTO leaves(employee_id,leave_type,from_date,to_date,reason,status,applied_at)
                       VALUES(?,?,?,?,?,?,?)""",
                    (u["employee_id"],f["leave_type"],f["from_date"],f["to_date"],f.get("reason",""),"Pending",
                     datetime.now().isoformat(timespec="seconds")))
        con.commit(); con.close()
        flash("Leave application submitted.")
        return redirect(url_for("leaves"))
    con = db()
    if u["role"] in ("Admin","HR","Manager"):
        rows = con.execute("""SELECT l.*,u.name FROM leaves l LEFT JOIN users u ON u.employee_id=l.employee_id
                              ORDER BY l.id DESC LIMIT 200""").fetchall()
    else:
        rows = con.execute("""SELECT l.*,u.name FROM leaves l LEFT JOIN users u ON u.employee_id=l.employee_id
                              WHERE l.employee_id=? ORDER BY l.id DESC""",(u["employee_id"],)).fetchall()
    con.close()
    body = """
    <div class="title"><h1>Leave Management</h1></div>
    <div class="card"><h2>Apply Leave</h2><form method="post"><div class="formgrid">
      <div class="field"><label>Leave Type</label><select name="leave_type"><option>Casual Leave</option><option>Sick Leave</option><option>Earned Leave</option><option>Permission</option><option>Other</option></select></div>
      <div class="field"><label>From</label><input name="from_date" type="date" required></div>
      <div class="field"><label>To</label><input name="to_date" type="date" required></div>
      <div class="field full"><label>Reason</label><textarea name="reason"></textarea></div>
    </div><div class="actions"><button>Submit Leave</button></div></form></div>
    <div class="card" style="margin-top:14px"><h2>Leave Applications</h2><div class="tablewrap"><table>
    <tr><th>Employee</th><th>Type</th><th>From</th><th>To</th><th>Reason</th><th>Status</th><th>Action</th></tr>
    {% for r in rows %}<tr><td>{{r['name'] or r['employee_id']}}</td><td>{{r['leave_type']}}</td><td>{{r['from_date']}}</td><td>{{r['to_date']}}</td><td>{{r['reason'] or '-'}}</td>
    <td>{{r['status']}}</td><td>{% if u['role'] in ['Admin','HR','Manager'] and r['status']=='Pending' %}
      <a class="btn success" href="{{url_for('leave_action',leave_id=r['id'],action='Approved')}}">Approve</a>
      <a class="btn danger" href="{{url_for('leave_action',leave_id=r['id'],action='Rejected')}}">Reject</a>
    {% else %}-{% endif %}</td></tr>{% endfor %}
    </table></div></div>
    """
    return layout("Leave", body, rows=rows, u=u)

@app.route("/leave/<int:leave_id>/<action>")
@roles_required("Admin","HR","Manager")
def leave_action(leave_id, action):
    if action not in ("Approved","Rejected"):
        return redirect(url_for("leaves"))
    u = current_user()
    con = db()
    con.execute("UPDATE leaves SET status=?,approved_by=? WHERE id=? AND status='Pending'", (action,u["employee_id"],leave_id))
    con.commit(); con.close()
    flash("Leave status updated.")
    return redirect(url_for("leaves"))

@app.route("/inventory", methods=["GET","POST"])
@login_required
def inventory():
    u = current_user()
    if request.method == "POST":
        if u["role"] not in ("Admin","Inventory","HR"):
            flash("You do not have permission to add inventory.", "error")
            return redirect(url_for("inventory"))
        f=request.form
        try:
            con=db()
            con.execute("""INSERT INTO inventory(item_code,item_name,category,brand,serial_no,quantity,min_quantity,location,supplier,purchase_date,assigned_to,status,created_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (f["item_code"].strip(),f["item_name"].strip(),f.get("category",""),f.get("brand",""),f.get("serial_no",""),
                         int(f.get("quantity") or 0),int(f.get("min_quantity") or 0),f.get("location",""),f.get("supplier",""),
                         f.get("purchase_date",""),f.get("assigned_to",""),f.get("status","Available"),datetime.now().isoformat(timespec="seconds")))
            con.commit(); con.close()
            flash("Inventory item added.")
        except (sqlite3.IntegrityError,ValueError):
            flash("Invalid data or item code already exists.", "error")
        return redirect(url_for("inventory"))
    con=db()
    rows=con.execute("SELECT * FROM inventory ORDER BY id DESC").fetchall()
    con.close()
    can_edit=u["role"] in ("Admin","Inventory","HR")
    body="""
    <div class="title"><div><h1>Inventory</h1><div class="muted">Stock and asset management</div></div></div>
    {% if can_edit %}<div class="card"><h2>Add Inventory Item</h2><form method="post"><div class="formgrid">
      <div class="field"><label>Item Code *</label><input name="item_code" required></div><div class="field"><label>Item Name *</label><input name="item_name" required></div>
      <div class="field"><label>Category</label><input name="category"></div><div class="field"><label>Brand</label><input name="brand"></div>
      <div class="field"><label>Serial No.</label><input name="serial_no"></div><div class="field"><label>Quantity</label><input name="quantity" type="number" min="0" value="0"></div>
      <div class="field"><label>Minimum Quantity</label><input name="min_quantity" type="number" min="0" value="0"></div><div class="field"><label>Location</label><input name="location"></div>
      <div class="field"><label>Supplier</label><input name="supplier"></div><div class="field"><label>Purchase Date</label><input name="purchase_date" type="date"></div>
      <div class="field"><label>Assigned To (Employee ID)</label><input name="assigned_to"></div><div class="field"><label>Status</label><select name="status"><option>Available</option><option>Issued</option><option>Repair</option><option>Disposed</option></select></div>
    </div><div class="actions"><button>Add Item</button></div></form></div>{% endif %}
    <div class="card" style="margin-top:14px"><div class="title"><h2>Stock Register</h2><a class="btn light" href="{{url_for('inventory_csv')}}">Export CSV</a></div>
    <div class="tablewrap"><table><tr><th>Code</th><th>Item</th><th>Category</th><th>Serial</th><th>Qty</th><th>Min</th><th>Location</th><th>Assigned</th><th>Status</th>{% if can_edit %}<th>Transaction</th>{% endif %}</tr>
    {% for r in rows %}<tr><td>{{r['item_code']}}</td><td>{{r['item_name']}}</td><td>{{r['category'] or '-'}}</td><td>{{r['serial_no'] or '-'}}</td>
    <td>{% if r['quantity']<=r['min_quantity'] %}<span class="badge red">{{r['quantity']}}</span>{% else %}{{r['quantity']}}{% endif %}</td><td>{{r['min_quantity']}}</td><td>{{r['location'] or '-'}}</td><td>{{r['assigned_to'] or '-'}}</td><td>{{r['status']}}</td>
    {% if can_edit %}<td><a class="btn" href="{{url_for('inventory_txn',item_id=r['id'])}}">Issue / Return</a></td>{% endif %}</tr>{% endfor %}
    </table></div></div>
    """
    return layout("Inventory", body, rows=rows, can_edit=can_edit)

@app.route("/inventory/<int:item_id>/transaction", methods=["GET","POST"])
@roles_required("Admin","Inventory","HR")
def inventory_txn(item_id):
    con=db()
    item=con.execute("SELECT * FROM inventory WHERE id=?",(item_id,)).fetchone()
    if not item:
        con.close(); flash("Item not found.","error"); return redirect(url_for("inventory"))
    if request.method=="POST":
        f=request.form
        try:
            qty=int(f["quantity"])
            typ=f["txn_type"]
            if qty<=0: raise ValueError
            newqty=item["quantity"]-qty if typ=="Issue" else item["quantity"]+qty
            if newqty<0: raise ValueError
            con.execute("UPDATE inventory SET quantity=?,status=? WHERE id=?",
                        (newqty,"Issued" if typ=="Issue" and newqty==0 else ("Available" if newqty>0 else item["status"]),item_id))
            con.execute("""INSERT INTO inventory_txn(item_id,employee_id,txn_type,quantity,notes,txn_at)
                           VALUES(?,?,?,?,?,?)""",(item_id,f.get("employee_id",""),typ,qty,f.get("notes",""),datetime.now().isoformat(timespec="seconds")))
            con.commit(); con.close(); flash("Inventory transaction recorded."); return redirect(url_for("inventory"))
        except ValueError:
            flash("Invalid quantity or insufficient stock.","error")
    con.close()
    body="""
    <div class="title"><h1>Issue / Return</h1></div>
    <div class="card"><p><b>{{item['item_name']}}</b> ({{item['item_code']}})</p><p>Current Quantity: <b>{{item['quantity']}}</b></p>
    <form method="post"><div class="formgrid">
      <div class="field"><label>Transaction</label><select name="txn_type"><option>Issue</option><option>Return</option></select></div>
      <div class="field"><label>Quantity</label><input name="quantity" type="number" min="1" required></div>
      <div class="field"><label>Employee ID</label><input name="employee_id"></div>
      <div class="field full"><label>Notes</label><textarea name="notes"></textarea></div>
    </div><div class="actions"><button>Save Transaction</button><a class="btn secondary" href="{{url_for('inventory')}}">Cancel</a></div></form></div>
    """
    return layout("Inventory Transaction", body, item=item)

@app.route("/attendance.csv")
@login_required
def attendance_csv():
    import csv, io
    u=current_user(); con=db()
    if u["role"] in ("Admin","HR","Manager"):
        rows=con.execute("""SELECT a.work_date,u.employee_id,u.name,u.department,a.check_in,a.check_out
                            FROM attendance a LEFT JOIN users u ON u.employee_id=a.employee_id ORDER BY a.work_date DESC""").fetchall()
    else:
        rows=con.execute("""SELECT a.work_date,u.employee_id,u.name,u.department,a.check_in,a.check_out
                            FROM attendance a LEFT JOIN users u ON u.employee_id=a.employee_id WHERE a.employee_id=? ORDER BY a.work_date DESC""",(u["employee_id"],)).fetchall()
    con.close()
    s=io.StringIO(); w=csv.writer(s); w.writerow(["Date","Employee ID","Name","Department","Check In","Check Out"])
    for r in rows: w.writerow([r["work_date"],r["employee_id"],r["name"],r["department"],r["check_in"],r["check_out"]])
    from io import BytesIO
    b=BytesIO(s.getvalue().encode("utf-8")); b.seek(0)
    return send_file(b,as_attachment=True,download_name="attendance.csv",mimetype="text/csv")

@app.route("/inventory.csv")
@login_required
def inventory_csv():
    import csv, io
    con=db(); rows=con.execute("SELECT item_code,item_name,category,brand,serial_no,quantity,min_quantity,location,supplier,purchase_date,assigned_to,status FROM inventory ORDER BY id").fetchall(); con.close()
    s=io.StringIO(); w=csv.writer(s)
    w.writerow(["Item Code","Item Name","Category","Brand","Serial No","Quantity","Minimum","Location","Supplier","Purchase Date","Assigned To","Status"])
    for r in rows: w.writerow(list(r))
    from io import BytesIO
    b=BytesIO(s.getvalue().encode("utf-8")); b.seek(0)
    return send_file(b,as_attachment=True,download_name="inventory.csv",mimetype="text/csv")

@app.errorhandler(404)
def not_found(e):
    return redirect(url_for("dashboard"))

@app.errorhandler(500)
def server_error(e):
    return "Application error. Check the server logs.", 500

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
