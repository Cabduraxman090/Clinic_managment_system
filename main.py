
import flet as ft
import sqlite3
import os
import shutil
import json
import csv
from datetime import datetime

# Optional encryption
try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except Exception:
    HAS_CRYPTO = False

DB_NAME = "clinic.db"
SETTINGS_FILE = "settings.json"
BACKUP_DIR = "backups"
EXPORT_DIR = "exports"

# ----------------------- Utilities -----------------------

def ensure_files():
    if not os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        # Create schema
        c.execute('''
            CREATE TABLE settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                age INTEGER,
                gender TEXT,
                phone TEXT,
                address TEXT,
                medical_history TEXT,
                created_at TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE doctors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                specialty TEXT,
                phone TEXT,
                email TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                doctor_id INTEGER,
                date TEXT,
                time TEXT,
                notes TEXT,
                status TEXT DEFAULT 'scheduled',
                created_at TEXT,
                FOREIGN KEY(patient_id) REFERENCES patients(id),
                FOREIGN KEY(doctor_id) REFERENCES doctors(id)
            )
        ''')
        c.execute('''
            CREATE TABLE invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                description TEXT,
                total REAL,
                paid REAL,
                created_at TEXT,
                FOREIGN KEY(patient_id) REFERENCES patients(id)
            )
        ''')
        # Default admin user
        c.execute("INSERT INTO users (username, password) VALUES (?,?)", ("admin", "admin"))
        conn.commit()
        conn.close()

    for d in (BACKUP_DIR, EXPORT_DIR):
        if not os.path.exists(d):
            os.makedirs(d)

    if not os.path.exists(SETTINGS_FILE):
        settings = {
            "language": "en",
            "dark_mode": False,
            "username": "admin",
            "encrypt_backups": False,
            "encryption_key": None
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f)

def db_connect():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def generate_key():
    if not HAS_CRYPTO:
        return None
    # Ensure key is returned as string for JSON storage
    key = Fernet.generate_key()
    return key.decode()

def get_fernet_from_key(key_str: str):
    if not HAS_CRYPTO or not key_str:
        return None
    try:
        return Fernet(key_str.encode())
    except Exception:
        return None

def make_backup(encrypt=False, key=None):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"clinic_backup_{timestamp}.db"
    dest = os.path.join(BACKUP_DIR, backup_name)
    shutil.copyfile(DB_NAME, dest)
    
    if encrypt and HAS_CRYPTO and key:
        f = get_fernet_from_key(key)
        if f:
            try:
                with open(dest, 'rb') as rf:
                    data = rf.read()
                enc = f.encrypt(data)
                enc_path = dest + '.enc'
                with open(enc_path, 'wb') as wf:
                    wf.write(enc)
                os.remove(dest)
                return enc_path
            except Exception as ex:
                # If encryption fails, keep the unencrypted copy and log error
                print(f"Encryption failed: {ex}")
                return dest 
    return dest

def restore_backup(filepath, encrypted=False, key=None):
    if encrypted:
        if not HAS_CRYPTO or not key:
            return False, "Encryption support or key missing"
        f = get_fernet_from_key(key)
        if not f:
            return False, "Invalid key"
        try:
            with open(filepath, 'rb') as rf:
                data = rf.read()
            dec = f.decrypt(data)
            tmp = DB_NAME + '.tmp'
            with open(tmp, 'wb') as wf:
                wf.write(dec)
            shutil.copyfile(tmp, DB_NAME)
            os.remove(tmp)
            return True, "Restored (decrypted)"
        except Exception as ex:
            return False, f"Decryption/Restore failed: {str(ex)}"
    else:
        try:
            shutil.copyfile(filepath, DB_NAME)
            return True, "Restored"
        except Exception as ex:
            return False, f"Restore failed: {str(ex)}"

# CSV helpers
def export_csv(table_name: str, filepath: str):
    conn = db_connect()
    c = conn.cursor()
    c.execute(f"SELECT * FROM {table_name}")
    rows = c.fetchall()
    cols = [d[0] for d in c.description]
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        for r in rows:
            # Use dictionary keys from row_factory
            writer.writerow([r[c] for c in cols]) 
    conn.close()

def import_csv(table_name: str, filepath: str):
    conn = db_connect()
    c = conn.cursor()
    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        keys = reader.fieldnames
        if not keys:
            conn.close()
            return False, "CSV file is empty or missing headers"

        placeholders = ','.join('?' for _ in keys)
        cols = ','.join(keys)
        rows = [tuple(row[k] for k in keys) for row in reader]
        
        # Simple approach: attempt to insert rows (may fail for PK collisions)
        try:
            c.executemany(f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})", rows)
            conn.commit()
        except Exception as ex:
            conn.close()
            return False, f"Database insertion error: {str(ex)}"
    
    conn.close()
    return True, f'Imported {len(rows)} rows into {table_name}'

# ----------------------- App UI -----------------------

class DentalApp:
    def __init__(self, page: ft.Page):
        self.page = page
        page.title = "Dental Clinic Manager"
        page.window_width = 420
        page.window_height = 800
        page.padding = 10
        page.spacing = 10
        
        # Apply theme settings
        with open(SETTINGS_FILE, "r") as f:
            self.settings = json.load(f)

        if self.settings.get('dark_mode'):
            page.theme_mode = ft.ThemeMode.DARK
        else:
            page.theme_mode = ft.ThemeMode.LIGHT
        
        self.logged_in_user = None
        self.build_login()
        # Add the initial content to the page
        page.add(self.content)

    # ----------------------- Login -----------------------
    def build_login(self):
        self.content = ft.Column()
        self.content.controls.append(ft.Text("Dental Clinic Manager", size=24, weight="bold"))
        self.username = ft.TextField(label="Username", value=self.settings.get("username", "admin"))
        self.password = ft.TextField(label="Password", password=True, can_reveal_password=True)
        login_btn = ft.ElevatedButton(text="Login", on_click=self.on_login)
        self.content.controls.extend([self.username, self.password, login_btn])
        self.page.update()

    def on_login(self, e):
        u = self.username.value.strip()
        p = self.password.value.strip()
        conn = db_connect()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))
        r = c.fetchone()
        conn.close()
        if r:
            self.logged_in_user = u
            self.build_main_ui()
        else:
            self.page.snack_bar = ft.SnackBar(ft.Text("Login failed — wrong username or password"))
            self.page.snack_bar.open = True
            self.page.update()

    # ----------------------- Main UI -----------------------
    def build_main_ui(self):
        self.content.controls.clear()

        top_row = ft.Row([], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        top_row.controls.append(ft.Text(f"Welcome, {self.logged_in_user}", size=16))
        logout_btn = ft.TextButton("Logout", on_click=self.logout)
        backup_btn = ft.IconButton(ft.icons.BACKUP, tooltip="Backup database", on_click=self.backup_db)
        import_btn = ft.IconButton(ft.icons.FILE_OPEN, tooltip="Import database (restore)", on_click=self.import_db)
        top_row.controls.extend([ft.Row([backup_btn, import_btn]), logout_btn])

        nav_buttons = ft.Column([
            ft.ElevatedButton("Dashboard", on_click=self.show_dashboard),
            ft.ElevatedButton("Patients", on_click=self.show_patients),
            ft.ElevatedButton("Appointments", on_click=self.show_appointments),
            ft.ElevatedButton("Doctors", on_click=self.show_doctors),
            ft.ElevatedButton("Invoices", on_click=self.show_invoices),
            ft.ElevatedButton("Settings", on_click=self.show_settings)
        ], spacing=8)

        self.main_area = ft.Column(expand=True) # Ensure main_area can expand
        self.content.controls.extend([top_row, ft.Divider(), ft.Row([nav_buttons, ft.VerticalDivider(), self.main_area], expand=True)])
        self.show_dashboard()
        self.page.update()

    def logout(self, e):
        self.logged_in_user = None
        self.build_login()

    def clear_main_area(self):
        self.main_area.controls.clear()

    def show_dashboard(self, e=None):
        self.clear_main_area()
        conn = db_connect()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) AS cnt FROM patients")
        patients_cnt = c.fetchone()[0]
        # Use ISO format for date comparison
        c.execute("SELECT COUNT(*) AS cnt FROM appointments WHERE date>=?", (datetime.now().strftime('%Y-%m-%d'),))
        upcoming_cnt = c.fetchone()[0]
        # Calculate revenue for the current month
        c.execute("SELECT COALESCE(SUM(total),0) FROM invoices WHERE created_at LIKE ?", (datetime.now().strftime('%Y-%m') + '%',))
        month_total = c.fetchone()[0] or 0
        conn.close()

        self.main_area.controls.append(ft.Text("Dashboard", size=20, weight="bold"))
        stats = ft.Row([
            ft.Card(ft.Container(ft.Column([ft.Text("Patients", size=14), ft.Text(str(patients_cnt), size=22, weight="bold")]), padding=10), elevation=2, width=140),
            ft.Card(ft.Container(ft.Column([ft.Text("Upcoming", size=14), ft.Text(str(upcoming_cnt), size=22, weight="bold")]), padding=10), elevation=2, width=140),
            ft.Card(ft.Container(ft.Column([ft.Text("This month revenue", size=12), ft.Text(f"{month_total:.2f}", size=18, weight="bold")]), padding=10), elevation=2, width=200)
        ], spacing=12)
        self.main_area.controls.append(stats)
        self.page.update()

    # ---------- Patients ----------
    def show_patients(self, e=None):
        self.clear_main_area()
        self.main_area.controls.append(ft.Text("Patients", size=20, weight="bold"))
        search = ft.TextField(label="Search patients (name/phone)", expand=True)
        list_view = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

        def load_patients(q: str = None):
            list_view.controls.clear()
            conn = db_connect()
            c = conn.cursor()
            if q:
                c.execute("SELECT * FROM patients WHERE name LIKE ? OR phone LIKE ? ORDER BY name", (f"%{q}%", f"%{q}%"))
            else:
                c.execute("SELECT * FROM patients ORDER BY name")
            rows = c.fetchall()
            conn.close()
            for r in rows:
                btn = ft.ListTile(title=ft.Text(r['name']), subtitle=ft.Text(f"Phone: {r['phone'] or '-'} | Age: {r['age'] or '-'}"), 
                                  on_click=lambda e, rid=r['id']: self.open_patient(rid))
                list_view.controls.append(btn)
            self.page.update()

        def on_search(e):
            load_patients(search.value.strip())

        search.on_submit = on_search
        
        add_btn = ft.ElevatedButton("Add Patient", on_click=lambda e: self.add_patient(on_done=load_patients))
        export_btn = ft.ElevatedButton("Export Patients CSV", on_click=self.export_patients_csv)
        import_btn = ft.ElevatedButton("Import Patients CSV", on_click=lambda e: self.import_csv_ui('patients'))
        
        self.main_area.controls.extend([
            ft.Row([search, ft.IconButton(ft.icons.SEARCH, on_click=on_search)]), 
            ft.Row([add_btn, export_btn, import_btn]), 
            ft.Divider(), 
            list_view
        ])
        load_patients()
        self.page.update()

    def add_patient(self, on_done=None):
        name = ft.TextField(label="Name")
        age = ft.TextField(label="Age", value="0", input_filter=ft.InputFilter(r"[0-9]"))
        gender = ft.Dropdown(options=[ft.dropdown.Option("Male"), ft.dropdown.Option("Female")], label="Gender")
        phone = ft.TextField(label="Phone", input_filter=ft.InputFilter(r"[0-9\-\s\+()]*"))
        address = ft.TextField(label="Address")
        med = ft.TextField(label="Medical history", multiline=True)
        
        dlg_content = ft.Column([name, age, gender, phone, address, med], scroll=ft.ScrollMode.AUTO, height=450)
        
        def submit(e):
            conn = db_connect()
            c = conn.cursor()
            try:
                c.execute("INSERT INTO patients (name, age, gender, phone, address, medical_history, created_at) VALUES (?,?,?,?,?,?,?)",
                          (name.value.strip(), int(age.value or 0), gender.value or '', phone.value.strip(), address.value.strip(), med.value.strip(), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                self.page.dialog.open = False
                self.page.update()
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"))
                self.page.snack_bar.open = True
            conn.close()
            if on_done:
                on_done()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Add Patient"),
            content=dlg_content,
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(self.page.dialog, 'open', False) or self.page.update()),
                ft.ElevatedButton("Save", on_click=submit)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def open_patient(self, patient_id):
        conn = db_connect()
        c = conn.cursor()
        c.execute("SELECT * FROM patients WHERE id=?", (patient_id,))
        r = c.fetchone()
        conn.close()
        if not r:
            return
        
        info = ft.Column([
            ft.Text(f"ID: {r['id']}", size=14, weight="bold"),
            ft.Text(f"Name: {r['name']}"),
            ft.Text(f"Age: {r['age'] or '-'}"),
            ft.Text(f"Gender: {r['gender'] or '-'}"),
            ft.Text(f"Phone: {r['phone'] or '-'}"),
            ft.Text(f"Address: {r['address'] or '-'}"),
            ft.Text("Medical history:", weight="bold"),
            ft.Container(ft.Text(r['medical_history'] or "-", italic=True), padding=ft.padding.only(left=10))
        ])

        def close_dialog(e):
            self.page.dialog.open = False
            self.page.update()

        def add_invoice(e):
            close_dialog(e)
            self.create_invoice(patient_id)

        def add_appointment(e):
            close_dialog(e)
            self.create_appointment(patient_id)

        dlg = ft.AlertDialog(
            title=ft.Text(f"Patient Details: {r['name']}"),
            content=info,
            actions=[
                ft.TextButton("Close", on_click=close_dialog), 
                ft.ElevatedButton("New Appointment", on_click=add_appointment), 
                ft.ElevatedButton("New Invoice", on_click=add_invoice)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    # ---------- Doctors ----------
    def show_doctors(self, e=None):
        self.clear_main_area()
        self.main_area.controls.append(ft.Text("Doctors", size=20, weight="bold"))
        list_view = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

        conn = db_connect()
        c = conn.cursor()
        c.execute("SELECT * FROM doctors ORDER BY name")
        rows = c.fetchall()
        conn.close()
        for r in rows:
            list_view.controls.append(ft.ListTile(title=ft.Text(r['name']), subtitle=ft.Text(f"{r['specialty'] or '-'} | Phone: {r['phone'] or '-'}")))

        add_btn = ft.ElevatedButton("Add Doctor", on_click=self.add_doctor)
        self.main_area.controls.extend([add_btn, ft.Divider(), list_view])
        self.page.update()

    def add_doctor(self, e=None):
        name = ft.TextField(label="Name")
        specialty = ft.TextField(label="Specialty")
        phone = ft.TextField(label="Phone")
        email = ft.TextField(label="Email")

        def submit(e):
            conn = db_connect()
            c = conn.cursor()
            try:
                c.execute("INSERT INTO doctors (name, specialty, phone, email) VALUES (?,?,?,?)", 
                          (name.value.strip(), specialty.value.strip(), phone.value.strip(), email.value.strip()))
                conn.commit()
                self.page.dialog.open = False
                self.show_doctors() # Refresh the list
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"))
                self.page.snack_bar.open = True
            conn.close()
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Add Doctor"),
            content=ft.Column([name, specialty, phone, email], height=250),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(self.page.dialog, 'open', False) or self.page.update()), 
                ft.ElevatedButton("Save", on_click=submit)
            ]
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    # ---------- Appointments ----------
    def show_appointments(self, e=None):
        self.clear_main_area()
        self.main_area.controls.append(ft.Text("Appointments", size=20, weight="bold"))
        add_btn = ft.ElevatedButton("New Appointment", on_click=lambda e: self.create_appointment())
        list_view = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

        conn = db_connect()
        c = conn.cursor()
        c.execute("SELECT a.*, p.name AS patient_name, d.name AS doctor_name FROM appointments a LEFT JOIN patients p ON a.patient_id=p.id LEFT JOIN doctors d ON a.doctor_id=d.id ORDER BY date DESC, time DESC")
        rows = c.fetchall()
        conn.close()
        for r in rows:
            list_view.controls.append(ft.ListTile(
                title=ft.Text(f"{r['date']} {r['time']} - {r['patient_name'] or 'Unknown'}"), 
                subtitle=ft.Text(f"Doctor: {r['doctor_name'] or '-'} | Status: {r['status']}")
            ))

        self.main_area.controls.extend([add_btn, ft.Divider(), list_view])
        self.page.update()

    def create_appointment(self, patient_id=None):
        conn = db_connect()
        c = conn.cursor()
        c.execute("SELECT id, name FROM patients ORDER BY name")
        patients = c.fetchall()
        c.execute("SELECT id, name FROM doctors ORDER BY name")
        doctors = c.fetchall()
        conn.close()

        patient_dd_options = [ft.dropdown.Option(key=str(p['id']), text=p['name']) for p in patients]
        doctor_dd_options = [ft.dropdown.Option(key=str(d['id']), text=d['name']) for d in doctors]
        
        patient_dd = ft.Dropdown(options=patient_dd_options, label="Patient", hint_text="Select Patient")
        if patient_id:
            patient_dd.value = str(patient_id)
            
        doctor_dd = ft.Dropdown(options=doctor_dd_options, label="Doctor", hint_text="Select Doctor")
        
        date = ft.TextField(label="Date (YYYY-MM-DD)", value=datetime.now().strftime('%Y-%m-%d'))
        time_field = ft.TextField(label="Time (HH:MM)", value=datetime.now().strftime('%H:%M'))
        notes = ft.TextField(label="Notes", multiline=True)

        def submit(e):
            try:
                pid = int(patient_dd.value) if patient_dd.value else None
                did = int(doctor_dd.value) if doctor_dd.value else None
                
                conn = db_connect()
                c = conn.cursor()
                c.execute("INSERT INTO appointments (patient_id, doctor_id, date, time, notes, created_at) VALUES (?,?,?,?,?,?)",
                          (pid, did, date.value.strip(), time_field.value.strip(), notes.value.strip(), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                conn.close()
                self.page.dialog.open = False
                self.show_appointments()
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Error creating appointment: {ex}"))
                self.page.snack_bar.open = True
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Create Appointment"),
            content=ft.Column([patient_dd, doctor_dd, date, time_field, notes], height=400, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(self.page.dialog, 'open', False) or self.page.update()), 
                ft.ElevatedButton("Save", on_click=submit)
            ]
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    # ---------- Invoices ----------
    def show_invoices(self, e=None):
        self.clear_main_area()
        self.main_area.controls.append(ft.Text("Invoices & Payments", size=20, weight="bold"))
        add_btn = ft.ElevatedButton("Create Invoice", on_click=lambda e: self.create_invoice())
        export_btn = ft.ElevatedButton("Export Invoices CSV", on_click=self.export_invoices_csv)
        import_btn = ft.ElevatedButton("Import Invoices CSV", on_click=lambda e: self.import_csv_ui('invoices'))
        list_view = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

        conn = db_connect()
        c = conn.cursor()
        c.execute("SELECT i.*, p.name AS patient_name FROM invoices i LEFT JOIN patients p ON i.patient_id=p.id ORDER BY i.created_at DESC")
        rows = c.fetchall()
        conn.close()
        for r in rows:
            list_view.controls.append(ft.ListTile(
                title=ft.Text(f"{r['patient_name'] or 'Unknown'} - {r['description'] or '-'}"), 
                subtitle=ft.Text(f"Total: {r['total']:.2f} | Paid: {r['paid']:.2f} | Date: {r['created_at'].split()[0]}")
            ))

        self.main_area.controls.extend([ft.Row([add_btn, export_btn, import_btn]), ft.Divider(), list_view])
        self.page.update()

    def create_invoice(self, patient_id=None):
        conn = db_connect()
        c = conn.cursor()
        c.execute("SELECT id, name FROM patients ORDER BY name")
        patients = c.fetchall()
        conn.close()
        
        patient_dd_options = [ft.dropdown.Option(key=str(p['id']), text=p['name']) for p in patients]
        patient_dd = ft.Dropdown(options=patient_dd_options, label="Patient", hint_text="Select Patient")
        if patient_id:
            patient_dd.value = str(patient_id)

        desc = ft.TextField(label="Description", multiline=True)
        total = ft.TextField(label="Total (e.g. 150.00)", input_filter=ft.InputFilter(r"[0-9\.]*"))
        paid = ft.TextField(label="Paid (e.g. 50.00)", input_filter=ft.InputFilter(r"[0-9\.]*"))

        def submit(e):
            try:
                pid = int(patient_dd.value) if patient_dd.value else None
                
                # Input validation
                try:
                    total_val = float(total.value or 0)
                    paid_val = float(paid.value or 0)
                except ValueError:
                    self.page.snack_bar = ft.SnackBar(ft.Text("Error: Total and Paid must be valid numbers."))
                    self.page.snack_bar.open = True
                    self.page.update()
                    return

                conn = db_connect()
                c = conn.cursor()
                c.execute("INSERT INTO invoices (patient_id, description, total, paid, created_at) VALUES (?,?,?,?,?)",
                          (pid, desc.value.strip(), total_val, paid_val, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                conn.close()
                self.page.dialog.open = False
                self.show_invoices()
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Error creating invoice: {ex}"))
                self.page.snack_bar.open = True
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Create Invoice"),
            content=ft.Column([patient_dd, desc, total, paid], height=350, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(self.page.dialog, 'open', False) or self.page.update()), 
                ft.ElevatedButton("Save", on_click=submit)
            ]
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    # ---------- Settings / Backup / Restore ----------
    def show_settings(self, e=None):
        self.clear_main_area()
        self.main_area.controls.append(ft.Text("Settings", size=20, weight="bold"))
        
        # Load settings immediately before building UI
        with open(SETTINGS_FILE, "r") as f:
            self.settings = json.load(f)

        lang = ft.Dropdown(options=[ft.dropdown.Option("en", "English"), ft.dropdown.Option("ar", "Arabic")], label="Language", value=self.settings.get('language', 'en'))
        
        dark = ft.Switch(label="Dark mode", value=self.settings.get('dark_mode', False))
        username = ft.TextField(label="Default username", value=self.settings.get('username', 'admin'))
        change_pass_btn = ft.ElevatedButton("Change admin password", on_click=self.change_password)

        encrypt_switch = ft.Switch(label="Encrypt backups (requires cryptography)", value=self.settings.get('encrypt_backups', False), 
                                   disabled=not HAS_CRYPTO)
        key_field = ft.TextField(label="Encryption key (leave blank to auto-generate)", value=self.settings.get('encryption_key') or '', password=True, can_reveal_password=True)

        def save_settings(e):
            self.settings['language'] = lang.value
            new_dark_mode = dark.value
            self.settings['dark_mode'] = new_dark_mode
            self.settings['username'] = username.value.strip()
            
            # Key/Encryption logic
            self.settings['encrypt_backups'] = encrypt_switch.value and HAS_CRYPTO
            k = key_field.value.strip()
            
            if self.settings['encrypt_backups']:
                if not k:
                    # generate key
                    k = generate_key() 
                # Validate key if provided
                if k and get_fernet_from_key(k) is None:
                    self.page.snack_bar = ft.SnackBar(ft.Text("Error: Invalid encryption key provided."))
                    self.page.snack_bar.open = True
                    self.page.update()
                    return
            else:
                k = None # Clear key if encryption is off
                
            self.settings['encryption_key'] = k

            try:
                with open(SETTINGS_FILE, 'w') as f:
                    json.dump(self.settings, f, indent=4) # Use indent for readability
                
                # Apply theme change immediately
                self.page.theme_mode = ft.ThemeMode.DARK if new_dark_mode else ft.ThemeMode.LIGHT
                
                self.page.snack_bar = ft.SnackBar(ft.Text("Settings saved. Theme updated."))
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Error saving settings: {ex}"))
            
            self.page.snack_bar.open = True
            self.page.update()

        save_btn = ft.ElevatedButton("Save Settings", on_click=save_settings)
        backup_btn = ft.ElevatedButton("Create backup now", on_click=self.backup_db)
        import_btn = ft.ElevatedButton("Import backup (restore)", on_click=self.import_db)
        export_csv_btn = ft.ElevatedButton("Export all CSVs", on_click=self.export_all_csv)

        note = ft.Text("Warning: Storing the key enables anyone with access to the settings file to decrypt backups.", color=ft.colors.RED_400)

        self.main_area.controls.extend([
            ft.Text("General", size=16, weight="bold"),
            lang, dark, username, change_pass_btn,
            ft.Divider(),
            ft.Text("Backup & Encryption", size=16, weight="bold"),
            encrypt_switch, 
            key_field, 
            note,
            ft.Divider(),
            ft.Row([save_btn]),
            ft.Row([backup_btn, import_btn, export_csv_btn])
        ])
        self.page.update()

    def change_password(self, e):
        old = ft.TextField(label="Old password", password=True, can_reveal_password=True)
        new = ft.TextField(label="New password", password=True, can_reveal_password=True)

        def submit(e):
            conn = db_connect()
            c = conn.cursor()
            username_to_change = self.settings.get('username', 'admin')
            
            # Check old password
            c.execute("SELECT * FROM users WHERE username=? AND password=?", (username_to_change, old.value))
            r = c.fetchone()
            
            if r:
                # Update password
                c.execute("UPDATE users SET password=? WHERE username=?", (new.value, username_to_change))
                conn.commit()
                conn.close()
                self.page.dialog.open = False
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Password for {username_to_change} changed"))
            else:
                self.page.snack_bar = ft.SnackBar(ft.Text("Old password incorrect"))
            
            self.page.snack_bar.open = True
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Change admin password"),
            content=ft.Column([old, new], height=150),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(self.page.dialog, 'open', False) or self.page.update()), 
                ft.ElevatedButton("Save", on_click=submit)
            ]
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def backup_db(self, e=None):
        # Reload settings just in case it was modified on the Settings screen
        with open(SETTINGS_FILE, "r") as f:
            self.settings = json.load(f)
            
        enc = self.settings.get('encrypt_backups', False)
        key = self.settings.get('encryption_key')
        
        if enc and not key:
            self.page.snack_bar = ft.SnackBar(ft.Text("Error: Encryption enabled but key is missing."))
        elif enc and not HAS_CRYPTO:
            self.page.snack_bar = ft.SnackBar(ft.Text("Error: Encryption enabled but cryptography not installed."))
        else:
            dest = make_backup(encrypt=enc and HAS_CRYPTO, key=key)
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Backup created: {os.path.basename(dest)}"))
        
        self.page.snack_bar.open = True
        self.page.update()

    def import_db(self, e=None):
        # File picker filter for .db and .db.enc files
        allowed_extensions = ["db", "enc"]
        
        def on_pick(result):
            if result.files and len(result.files) > 0:
                fpath = result.files[0].path
                if not fpath:
                    self.page.snack_bar = ft.SnackBar(ft.Text("File path not available."))
                else:
                    encrypted = fpath.lower().endswith('.enc')
                    # Reload settings to ensure latest key is used
                    with open(SETTINGS_FILE, "r") as f:
                        current_settings = json.load(f)
                    key = current_settings.get('encryption_key')
                    
                    if encrypted and (not HAS_CRYPTO or not key):
                        msg = "Cannot restore encrypted backup: Encryption support or key missing."
                        success = False
                    else:
                        success, msg = restore_backup(fpath, encrypted, key)

                    self.page.snack_bar = ft.SnackBar(ft.Text(msg))
                    if success:
                        # Force re-login/refresh UI after successful restore
                        self.logout(None) 
            else:
                self.page.snack_bar = ft.SnackBar(ft.Text("File selection cancelled."))
                
            self.page.snack_bar.open = True
            self.page.update()

        self.page.pick_files(
            allow_multiple=False, 
            on_result=on_pick, 
            allowed_extensions=allowed_extensions
        )

    # CSV UI
    def export_patients_csv(self, e=None):
        path = os.path.join(EXPORT_DIR, f"patients_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        try:
            export_csv('patients', path)
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Patients exported to {os.path.basename(path)}"))
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Error exporting CSV: {ex}"))
        self.page.snack_bar.open = True
        self.page.update()

    def export_invoices_csv(self, e=None):
        path = os.path.join(EXPORT_DIR, f"invoices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        try:
            export_csv('invoices', path)
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Invoices exported to {os.path.basename(path)}"))
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Error exporting CSV: {ex}"))
        self.page.snack_bar.open = True
        self.page.update()

    def export_all_csv(self, e=None):
        try:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            export_csv('patients', os.path.join(EXPORT_DIR, f"patients_{ts}.csv"))
            export_csv('appointments', os.path.join(EXPORT_DIR, f"appointments_{ts}.csv"))
            export_csv('invoices', os.path.join(EXPORT_DIR, f"invoices_{ts}.csv"))
            export_csv('doctors', os.path.join(EXPORT_DIR, f"doctors_{ts}.csv")) # Added doctors export
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Exported all CSVs to {EXPORT_DIR}"))
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Error exporting all CSVs: {ex}"))
        self.page.snack_bar.open = True
        self.page.update()

    def import_csv_ui(self, table_name: str):
        
        def on_pick(result):
            if result.files and len(result.files) > 0:
                fpath = result.files[0].path
                ok, msg = import_csv(table_name, fpath)
                self.page.snack_bar = ft.SnackBar(ft.Text(msg if ok else f"Error: {msg}"))
                self.page.snack_bar.open = True
                
                # refresh view
                if ok:
                    if table_name == 'patients':
                        self.show_patients()
                    elif table_name == 'invoices':
                        self.show_invoices()
                    elif table_name == 'doctors':
                        self.show_doctors()
                    elif table_name == 'appointments':
                        self.show_appointments()
            else:
                self.page.snack_bar = ft.SnackBar(ft.Text("File selection cancelled."))
                self.page.snack_bar.open = True
                
            self.page.update()

        self.page.pick_files(
            allow_multiple=False, 
            on_result=on_pick,
            allowed_extensions=["csv"]
        )

# ----------------------- Entry point -----------------------

def main(page: ft.Page): 
    # Must be called before DentalApp is initialized
    ensure_files() 
    DentalApp(page)

# Fixed entry point structure for flet
if __name__ == '__main__': 
    ft.app(target=main)
