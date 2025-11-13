import flet as ft
import sqlite3
import os
import shutil
import json
import csv
from datetime import datetime
import sys

# Optional encryption
try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except Exception:
    HAS_CRYPTO = False

# ----------------------- Paths -----------------------
# Determine writable path for Android or desktop
if getattr(sys, 'frozen', False):
    # Running as packaged APK
    DATA_DIR = os.path.join(os.path.expanduser("~"), "DentalClinicApp")
else:
    # Running as Python script
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))

os.makedirs(DATA_DIR, exist_ok=True)

DB_NAME = os.path.join(DATA_DIR, "clinic.db")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
EXPORT_DIR = os.path.join(DATA_DIR, "exports")

# ----------------------- Utilities -----------------------

def ensure_files():
    """Ensure database, folders, and settings exist."""
    if not os.path.exists(DB_NAME):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        # Create schema
        c.execute('''CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)''')
        c.execute('''CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
        c.execute('''CREATE TABLE patients (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        age INTEGER,
                        gender TEXT,
                        phone TEXT,
                        address TEXT,
                        medical_history TEXT,
                        created_at TEXT)''')
        c.execute('''CREATE TABLE doctors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        specialty TEXT,
                        phone TEXT,
                        email TEXT)''')
        c.execute('''CREATE TABLE appointments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        patient_id INTEGER,
                        doctor_id INTEGER,
                        date TEXT,
                        time TEXT,
                        notes TEXT,
                        status TEXT DEFAULT 'scheduled',
                        created_at TEXT,
                        FOREIGN KEY(patient_id) REFERENCES patients(id),
                        FOREIGN KEY(doctor_id) REFERENCES doctors(id))''')
        c.execute('''CREATE TABLE invoices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        patient_id INTEGER,
                        description TEXT,
                        total REAL,
                        paid REAL,
                        created_at TEXT,
                        FOREIGN KEY(patient_id) REFERENCES patients(id))''')
        # Default admin user
        c.execute("INSERT INTO users (username, password) VALUES (?,?)", ("admin", "admin"))
        conn.commit()
        conn.close()

    # Ensure folders exist
    for d in (BACKUP_DIR, EXPORT_DIR):
        if not os.path.exists(d):
            os.makedirs(d)

    # Settings file
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
    """Connect to SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def generate_key():
    if not HAS_CRYPTO:
        return None
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
        try:
            c.executemany(f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})", rows)
            conn.commit()
        except Exception as ex:
            conn.close()
            return False, f"Database insertion error: {str(ex)}"
    
    conn.close()
    return True, f'Imported {len(rows)} rows into {table_name}'

# ----------------------- Flet App -----------------------

class DentalApp:
    def __init__(self, page: ft.Page):
        self.page = page
        page.title = "Dental Clinic Manager"
        page.window_width = 420
        page.window_height = 800
        page.padding = 10
        page.spacing = 10

        with open(SETTINGS_FILE, "r") as f:
            self.settings = json.load(f)
        page.theme_mode = ft.ThemeMode.DARK if self.settings.get('dark_mode') else ft.ThemeMode.LIGHT
        self.logged_in_user = None
        self.build_login()
        page.add(self.content)

    # ---------- Login ----------
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

    # ---------- Main UI ----------
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

        self.main_area = ft.Column(expand=True)
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
        c.execute("SELECT COUNT(*) AS cnt FROM appointments WHERE date>=?", (datetime.now().strftime('%Y-%m-%d'),))
        upcoming_cnt = c.fetchone()[0]
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

    # ---------- More UI code (patients, doctors, appointments, invoices, settings, backup/restore) ----------
    # You can copy the rest of your existing code for patients, doctors, appointments, invoices, and settings
    # but remember all file paths now use DB_NAME, SETTINGS_FILE, BACKUP_DIR, EXPORT_DIR as absolute paths.

# ----------------------- Entry Point -----------------------

def main(page: ft.Page):
    ensure_files()
    DentalApp(page)

if __name__ == '__main__':
    ft.app(target=main)
