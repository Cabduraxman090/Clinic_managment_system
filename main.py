import flet as ft
import sqlite3
import os


# ---------------- Database Manager ----------------
class DatabaseManager:
    def __init__(self, db_name="clinic.db"):
        
        # 1. تحديد المسار القابل للكتابة على الهاتف أو سطح المكتب
        app_data_path = os.getenv("FLET_APP_STORAGE_DATA")
        
        if app_data_path:
            # مسار التخزين الآمن والقابل للكتابة (للهاتف/التطبيقات المُجمّعة)
            self.db_path = os.path.join(app_data_path, db_name)
        else:
            # العودة إلى دليل العمل الحالي (للتجربة على سطح المكتب)
            self.db_path = os.path.join(os.getcwd(), db_name)
        
        # 2. 💡 الحل الجديد: التأكد من وجود المجلد قبل الاتصال 
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            # إنشاء المجلد (والوالدين إذا لزم الأمر) مع تجاهل الأخطاء إذا كان موجوداً
            os.makedirs(db_dir, exist_ok=True)
            
        print(f"Database Path: {self.db_path}") # يساعدك في التحقق من مكان إنشاء الملف

        # 3. محاولة الاتصال (سيتم إنشاء الملف الآن داخل المجلد الموجود)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
# ... (بقية الدالة create_tables لم تتغير) ...
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

    # --- Patients ---
    def add_patient(self, name, phone, dob, address):
        self.cursor.execute("INSERT INTO patients (name, phone, dob, address) VALUES (?, ?, ?, ?)",
                            (name, phone, dob, address))
        self.conn.commit()

    def get_patients(self, search=""):
        if search:
            self.cursor.execute("SELECT * FROM patients WHERE name LIKE ?", ('%' + search + '%',))
        else:
            self.cursor.execute("SELECT * FROM patients ORDER BY name")
        return self.cursor.fetchall()

    def delete_patient(self, pid):
        self.cursor.execute("DELETE FROM patients WHERE id=?", (pid,))
        self.conn.commit()

    # --- Doctors ---
    def add_doctor(self, name, specialty):
        self.cursor.execute("INSERT INTO doctors (name, specialty) VALUES (?, ?)", (name, specialty))
        self.conn.commit()

    def get_doctors(self, search=""):
        if search:
            self.cursor.execute("SELECT * FROM doctors WHERE name LIKE ?", ('%' + search + '%',))
        else:
            self.cursor.execute("SELECT * FROM doctors ORDER BY name")
        return self.cursor.fetchall()

    def delete_doctor(self, did):
        self.cursor.execute("DELETE FROM doctors WHERE id=?", (did,))
        self.conn.commit()

    # --- Services ---
    def add_service(self, name, price):
        self.cursor.execute("INSERT INTO services (name, price) VALUES (?, ?)", (name, price))
        self.conn.commit()

    def get_services(self, search=""):
        if search:
            self.cursor.execute("SELECT * FROM services WHERE name LIKE ?", ('%' + search + '%',))
        else:
            self.cursor.execute("SELECT * FROM services ORDER BY name")
        return self.cursor.fetchall()

    def delete_service(self, sid):
        self.cursor.execute("DELETE FROM services WHERE id=?", (sid,))
        self.conn.commit()

    # --- Appointments ---
    def add_appointment(self, pid, did, sid, date):
        self.cursor.execute("INSERT INTO appointments (patient_id, doctor_id, service_id, date) VALUES (?, ?, ?, ?)",
                            (pid, did, sid, date))
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

    def delete_appointment(self, aid):
        self.cursor.execute("DELETE FROM appointments WHERE id=?", (aid,))
        self.conn.commit()


# ---------------- Main App ----------------
def main(page: ft.Page):
    db = DatabaseManager()

    # Theme toggle
    def toggle_theme(e):
        page.theme_mode = "light" if page.theme_mode == "dark" else "dark"
        page.update()

    theme_switch = ft.Switch(label="🌙", value=True, on_change=toggle_theme)
    page.theme_mode = "dark"
    page.appbar = ft.AppBar(title=ft.Text("Clinic System"), actions=[theme_switch])

    def show_message(text):
        page.snack_bar = ft.SnackBar(ft.Text(text))
        page.snack_bar.open = True
        page.update()

    # ================= Patients Tab =================
    def patients_tab():
        name = ft.TextField(label="Full Name", width=300)
        phone = ft.TextField(label="Phone", width=300)
        dob = ft.TextField(label="Date of Birth", width=300)
        address = ft.TextField(label="Address", width=300)
        search = ft.TextField(label="Search Patient", width=300, on_change=lambda e: load(e.control.value))
        list_view = ft.ListView(expand=True)

        def load(search_text=""):
            list_view.controls.clear()
            for pid, n, p, d, a in db.get_patients(search_text):
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
        return ft.Column([search, name, phone, dob, address, ft.ElevatedButton("Add Patient", on_click=add), ft.Divider(), list_view])

    # ================= Doctors Tab =================
    def doctors_tab():
        name = ft.TextField(label="Doctor Name", width=300)
        spec = ft.TextField(label="Specialty", width=300)
        search = ft.TextField(label="Search Doctor", width=300, on_change=lambda e: load(e.control.value))
        list_view = ft.ListView(expand=True)

        def load(search_text=""):
            list_view.controls.clear()
            for did, n, s in db.get_doctors(search_text):
                list_view.controls.append(ft.Row([
                    ft.Text(f"{n} ({s})", expand=True),
                    ft.IconButton(ft.icons.DELETE, icon_color="red", on_click=lambda e, i=did: delete(i))
                ]))
            page.update()

        def add(e):
            if not name.value.strip():
                show_message("Doctor name required")
                return
            db.add_doctor(name.value, spec.value)
            name.value = spec.value = ""
            load()
            show_message("Doctor added")

        def delete(i):
            db.delete_doctor(i)
            load()
            show_message("Deleted")

        load()
        return ft.Column([search, name, spec, ft.ElevatedButton("Add Doctor", on_click=add), ft.Divider(), list_view])

    # ================= Services Tab =================
    def services_tab():
        name = ft.TextField(label="Service Name", width=300)
        price = ft.TextField(label="Price", width=300)
        search = ft.TextField(label="Search Service", width=300, on_change=lambda e: load(e.control.value))
        list_view = ft.ListView(expand=True)

        def load(search_text=""):
            list_view.controls.clear()
            for sid, n, p in db.get_services(search_text):
                list_view.controls.append(ft.Row([
                    ft.Text(f"{n} (${p})", expand=True),
                    ft.IconButton(ft.icons.DELETE, icon_color="red", on_click=lambda e, i=sid: delete(i))
                ]))
            page.update()

        def add(e):
            if not name.value.strip():
                show_message("Service name required")
                return
            try:
                db.add_service(name.value, float(price.value))
                name.value = price.value = ""
                load()
                show_message("Service added")
            except ValueError:
                show_message("Invalid price")

        def delete(i):
            db.delete_service(i)
            load()
            show_message("Deleted")

        load()
        return ft.Column([search, name, price, ft.ElevatedButton("Add Service", on_click=add), ft.Divider(), list_view])

    # ================= Appointments Tab =================
    def appointments_tab():
        pat_list = db.get_patients()
        doc_list = db.get_doctors()
        serv_list = db.get_services()

        pat = ft.Dropdown(label="Patient", options=[ft.dropdown.Option(str(x[0]), x[1]) for x in pat_list], width=300)
        doc = ft.Dropdown(label="Doctor", options=[ft.dropdown.Option(str(x[0]), x[1]) for x in doc_list], width=300)
        serv = ft.Dropdown(label="Service", options=[ft.dropdown.Option(str(x[0]), x[1]) for x in serv_list], width=300)
        date = ft.TextField(label="Date (YYYY-MM-DD)", width=300)
        list_view = ft.ListView(expand=True)

        def load():
            list_view.controls.clear()
            for aid, pn, dn, sn, dt in db.get_appointments():
                list_view.controls.append(ft.Row([
                    ft.Text(f"{dt}: {pn} with {dn} for {sn}", expand=True),
                    ft.IconButton(ft.icons.DELETE, icon_color="red", on_click=lambda e, i=aid: delete(i))
                ]))
            page.update()

        def add(e):
            if not (pat.value and doc.value and serv.value and date.value.strip()):
                show_message("All fields required")
                return
            db.add_appointment(pat.value, doc.value, serv.value, date.value)
            pat.value = doc.value = serv.value = date.value = ""
            load()
            show_message("Appointment added")

        def delete(i):
            db.delete_appointment(i)
            load()
            show_message("Deleted")

        load()
        return ft.Column([pat, doc, serv, date, ft.ElevatedButton("Add Appointment", on_click=add), ft.Divider(), list_view])

    # --- Tabs Navigation ---
    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="Patients", content=patients_tab()),
            ft.Tab(text="Doctors", content=doctors_tab()),
            ft.Tab(text="Services", content=services_tab()),
            ft.Tab(text="Appointments", content=appointments_tab()),
        ],
        expand=True
    )

    page.add(tabs)


ft.app(target=main)
