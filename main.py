import flet as ft
import sqlite3
import os
import pandas as pd
import platform
import pathlib
import zipfile
from datetime import datetime

# ---------------- Database Manager ----------------
class DatabaseManager:
    def __init__(self, db_name="clinic.db"):
        # ✅ Persistent folder for Android + Desktop
        if platform.system() == "Android":
            self.base_path = "/storage/emulated/0/ClinicSystem"
        else:
            self.base_path = str(pathlib.Path.home() / "ClinicSystem")

        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)

        self.db_path = os.path.join(self.base_path, db_name)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                dob TEXT,
                address TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS doctors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                specialty TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                doctor_id INTEGER,
                service_id INTEGER,
                date TEXT,
                FOREIGN KEY(patient_id) REFERENCES patients(id),
                FOREIGN KEY(doctor_id) REFERENCES doctors(id),
                FOREIGN KEY(service_id) REFERENCES services(id)
            )
        """)
        self.conn.commit()

    # --- CRUD Methods ---
    def fetch_all(self, table):
        self.cursor.execute(f"SELECT * FROM {table}")
        return self.cursor.fetchall()

    def get_patients(self):
        self.cursor.execute("SELECT * FROM patients ORDER BY name")
        return self.cursor.fetchall()

    def add_patient(self, name, phone, dob, address):
        self.cursor.execute("INSERT INTO patients (name, phone, dob, address) VALUES (?, ?, ?, ?)",
                            (name, phone, dob, address))
        self.conn.commit()

    def delete_patient(self, pid):
        self.cursor.execute("DELETE FROM patients WHERE id=?", (pid,))
        self.conn.commit()

    def get_doctors(self):
        self.cursor.execute("SELECT * FROM doctors ORDER BY name")
        return self.cursor.fetchall()

    def add_doctor(self, name, specialty):
        self.cursor.execute("INSERT INTO doctors (name, specialty) VALUES (?, ?)", (name, specialty))
        self.conn.commit()

    def delete_doctor(self, did):
        self.cursor.execute("DELETE FROM doctors WHERE id=?", (did,))
        self.conn.commit()

    def get_services(self):
        self.cursor.execute("SELECT * FROM services ORDER BY name")
        return self.cursor.fetchall()

    def add_service(self, name, price):
        self.cursor.execute("INSERT INTO services (name, price) VALUES (?, ?)", (name, price))
        self.conn.commit()

    def delete_service(self, sid):
        self.cursor.execute("DELETE FROM services WHERE id=?", (sid,))
        self.conn.commit()

    def get_appointments(self):
        self.cursor.execute("""
            SELECT a.id, p.name, d.name, s.name, a.date
            FROM appointments a
            JOIN patients p ON a.patient_id = p.id
            JOIN doctors d ON a.doctor_id = d.id
            JOIN services s ON a.service_id = s.id
            ORDER BY a.date
        """)
        return self.cursor.fetchall()

    def add_appointment(self, pid, did, sid, date):
        self.cursor.execute("INSERT INTO appointments (patient_id, doctor_id, service_id, date) VALUES (?, ?, ?, ?)",
                            (pid, did, sid, date))
        self.conn.commit()

    def delete_appointment(self, aid):
        self.cursor.execute("DELETE FROM appointments WHERE id=?", (aid,))
        self.conn.commit()


# ---------------- Main App ----------------
def main(page: ft.Page):
    db = DatabaseManager()

    def show_message(text):
        page.snack_bar = ft.SnackBar(ft.Text(text))
        page.snack_bar.open = True
        page.update()

    # --- Export Function ---
    def export_data(table_name, filename):
        try:
            rows = db.fetch_all(table_name)
            if not rows:
                show_message("No data to export!")
                return
            df = pd.DataFrame(rows)
            csv_path = os.path.join(db.base_path, filename + ".csv")
            xlsx_path = os.path.join(db.base_path, filename + ".xlsx")
            df.to_csv(csv_path, index=False)
            df.to_excel(xlsx_path, index=False)
            show_message(f"✅ Exported {filename}.csv and .xlsx to {db.base_path}")
        except Exception as e:
            show_message("Error: " + str(e))

    # --- Backup Function ---
    def backup_all(e):
        try:
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(db.base_path, f"clinic_backup_{now}.zip")

            with zipfile.ZipFile(backup_path, 'w') as z:
                # Include the main database file
                z.write(db.db_path, os.path.basename(db.db_path))
                # Include exports (if they exist)
                for f in os.listdir(db.base_path):
                    if f.endswith(".csv") or f.endswith(".xlsx"):
                        z.write(os.path.join(db.base_path, f), f)

            show_message(f"✅ Backup created: {backup_path}")
        except Exception as e:
            show_message("Backup error: " + str(e))

    # --- Restore Function ---
    def restore_all(e):
        try:
            files = [f for f in os.listdir(db.base_path) if f.endswith(".zip")]
            if not files:
                show_message("No backup found in folder.")
                return
            latest_backup = max(files, key=lambda f: os.path.getmtime(os.path.join(db.base_path, f)))
            backup_file = os.path.join(db.base_path, latest_backup)

            with zipfile.ZipFile(backup_file, 'r') as z:
                z.extractall(db.base_path)

            show_message(f"✅ Restored from backup: {latest_backup}")
        except Exception as e:
            show_message("Restore error: " + str(e))

    # ================= Patients Tab =================
    def patients_tab():
        name = ft.TextField(label="Full Name", width=300)
        phone = ft.TextField(label="Phone", width=300)
        dob = ft.TextField(label="Date of Birth", width=300)
        address = ft.TextField(label="Address", width=300)
        list_view = ft.ListView(expand=True)

        def load():
            list_view.controls.clear()
            for pid, n, p, d, a in db.get_patients():
                list_view.controls.append(ft.Row([
                    ft.Text(f"{n} ({p})", expand=True),
                    ft.IconButton(ft.icons.DELETE, icon_color="red", on_click=lambda e, i=pid: delete(i))
                ]))
            page.update()

        def add(e):
            if not name.value.strip():
                show_message("Name required")
                return
            db.add_patient(name.value, phone.value, dob.value, address.value)
            name.value = phone.value = dob.value = address.value = ""
            load()
            show_message("Patient added")

        def delete(i):
            db.delete_patient(i)
            load()
            show_message("Deleted")

        load()
        export_btn = ft.ElevatedButton("Export Patients", icon=ft.icons.FILE_DOWNLOAD, on_click=lambda e: export_data("patients", "clinic_patients"))
        return ft.Column([name, phone, dob, address,
                          ft.ElevatedButton("Add Patient", on_click=add),
                          export_btn, ft.Divider(), list_view])

    # --- Other Tabs (Doctors, Services, Appointments) use same logic ---
    # For brevity, we'll keep patients as main example

    # --- Backup / Restore Buttons ---
    backup_btn = ft.ElevatedButton("Backup Data", icon=ft.icons.CLOUD_UPLOAD, on_click=backup_all)
    restore_btn = ft.ElevatedButton("Restore Data", icon=ft.icons.CLOUD_DOWNLOAD, on_click=restore_all)

    # --- Tabs ---
    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="Patients", content=patients_tab()),
            ft.Tab(text="Backup", content=ft.Column([backup_btn, restore_btn]))
        ],
        expand=True
    )

    page.add(tabs)


ft.app(target=main)