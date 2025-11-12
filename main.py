import flet as ft
import sqlite3
from datetime import datetime
import os # 🌟 (1) إضافة استيراد مكتبة os

# --- Database Manager (Optimized for Flet Concurrency) ---
class DatabaseManager:
    def __init__(self, db_name):
        # تم استخدام check_same_thread=False لتمكين الوصول من خيوط متعددة
        self.conn = sqlite3.connect(db_name, check_same_thread=False) 
        # تم إزالة self.cursor. سيتم إنشاء مؤشر جديد لكل عملية
        self.create_tables()

    def create_tables(self):
        # استخدام with self.conn لضمان عمل commit/rollback وتحرير القفل
        with self.conn:
            try:
                 # محاولة قراءة جدول للتأكد من وجوده، وإلا سيتم حذفه وإنشاؤه
                 self.conn.execute("SELECT service_id, payment_status FROM appointments LIMIT 1")
            except sqlite3.OperationalError:
                self.conn.execute("DROP TABLE IF EXISTS appointments")
            
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS patients (
                    patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    phone TEXT,
                    date_of_birth TEXT,
                    address TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS doctors (
                    doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    specialization TEXT,
                    phone TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS services (
                    service_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL,
                    price REAL NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS appointments (
                    appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER,
                    doctor_id INTEGER,
                    service_id INTEGER,           
                    appointment_date TEXT NOT NULL,
                    appointment_time TEXT NOT NULL,
                    notes TEXT,
                    payment_status TEXT DEFAULT 'Pending', 
                    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
                    FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id),
                    FOREIGN KEY (service_id) REFERENCES services(service_id)
                )
            """)

    # --- CRUD Methods (MODIFIED TO USE 'with self.conn:') ---
    
    # Patient CRUD
    def add_patient(self, name, phone, dob, address):
        with self.conn:
            self.conn.execute("INSERT INTO patients (full_name, phone, date_of_birth, address) VALUES (?, ?, ?, ?)", (name, phone, dob, address))
            
    def get_all_patients(self):
        # استخدام cursor() لعمليات SELECT التي لا تغير قاعدة البيانات
        return self.conn.cursor().execute("SELECT * FROM patients ORDER BY full_name").fetchall()

    def update_patient(self, patient_id, name, phone, dob, address):
        with self.conn:
            self.conn.execute("UPDATE patients SET full_name=?, phone=?, date_of_birth=?, address=? WHERE patient_id=?", (name, phone, dob, address, patient_id))

    def delete_patient(self, patient_id):
        with self.conn:
            self.conn.execute("DELETE FROM patients WHERE patient_id=?", (patient_id,))

    # Doctor CRUD
    def add_doctor(self, name, specialization, phone):
        with self.conn:
            self.conn.execute("INSERT INTO doctors (full_name, specialization, phone) VALUES (?, ?, ?)", (name, specialization, phone))
            
    def get_all_doctors(self):
        return self.conn.cursor().execute("SELECT * FROM doctors ORDER BY full_name").fetchall()
        
    def update_doctor(self, doctor_id, name, specialization, phone):
        with self.conn:
            self.conn.execute("UPDATE doctors SET full_name=?, specialization=?, phone=? WHERE doctor_id=?", (name, specialization, phone, doctor_id))

    def delete_doctor(self, doctor_id):
        with self.conn:
            self.conn.execute("DELETE FROM doctors WHERE doctor_id=?", (doctor_id,))

    # Service CRUD
    def add_service(self, name, price):
        # تم تصحيح المشكلة في هذه الدالة تحديداً
        with self.conn:
            self.conn.execute("INSERT INTO services (service_name, price) VALUES (?, ?)", (name, price))
            
    def get_all_services(self):
        return self.conn.cursor().execute("SELECT * FROM services ORDER BY service_name").fetchall()

    def get_service_price(self, service_id):
        # عملية SELECT بسيطة لا تتطلب معاملة كاملة، ولكن تتطلب مؤشر
        cursor = self.conn.cursor()
        cursor.execute("SELECT price FROM services WHERE service_id = ?", (service_id,))
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else 0.0

    def update_service(self, service_id, name, price): 
        with self.conn:
            self.conn.execute("UPDATE services SET service_name=?, price=? WHERE service_id=?", (name, price, service_id))

    def delete_service(self, service_id):
        with self.conn:
            self.conn.execute("DELETE FROM services WHERE service_id=?", (service_id,))
            
    # Appointment CRUD
    def get_appointment_details(self, appointment_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT patient_id, doctor_id, service_id, appointment_date, appointment_time, notes, payment_status FROM appointments WHERE appointment_id = ?", (appointment_id,))
        details = cursor.fetchone()
        cursor.close()
        return details

    def add_appointment(self, patient_id, doctor_id, service_id, date, time, notes, payment_status):
        with self.conn:
            self.conn.execute("INSERT INTO appointments (patient_id, doctor_id, service_id, appointment_date, appointment_time, notes, payment_status) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                            (patient_id, doctor_id, service_id, date, time, notes, payment_status))

    def get_all_appointments(self):
        return self.conn.cursor().execute("""
            SELECT 
                a.appointment_id, 
                p.full_name, 
                d.full_name, 
                s.service_name,  
                s.price,         
                a.appointment_date, 
                a.appointment_time, 
                a.payment_status 
            FROM appointments a 
            LEFT JOIN patients p ON a.patient_id = p.patient_id 
            LEFT JOIN doctors d ON a.doctor_id = d.doctor_id 
            LEFT JOIN services s ON a.service_id = s.service_id 
            ORDER BY a.appointment_date, a.appointment_time
        """).fetchall()

    def update_appointment(self, appointment_id, patient_id, doctor_id, service_id, date, time, notes, payment_status):
        with self.conn:
            self.conn.execute("UPDATE appointments SET patient_id=?, doctor_id=?, service_id=?, appointment_date=?, appointment_time=?, notes=?, payment_status=? WHERE appointment_id=?", 
                            (patient_id, doctor_id, service_id, date, time, notes, payment_status, appointment_id))

    def delete_appointment(self, appointment_id):
        with self.conn:
            self.conn.execute("DELETE FROM appointments WHERE appointment_id=?", (appointment_id,))

# --- Flet Main Application Function (التعديلات هنا) ---
def main(page: ft.Page):
    
    # --- App Configuration & Theme ---
    page.title = "Clinic System"
    page.theme_mode = ft.ThemeMode.DARK 
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.bgcolor = "#2E3440" 
    
    # 🌟 التعديل الأساسي لتحديد مسار قاعدة البيانات على الأندرويد 🌟
    # تحديد مسار التخزين الداعم للتطبيق
    db_path = os.path.join(page.platform_dirs.app_support_dir, "clinic.db")
    
    # --- Database Instance ---
    # استخدام المسار الكامل لقاعدة البيانات
    db = DatabaseManager(db_path)

    # --- Global Page Controls (Widgets) ---
    selected_patient_id = ft.Text(value=None, visible=False) 
    selected_doctor_id = ft.Text(value=None, visible=False)
    selected_service_id = ft.Text(value=None, visible=False)
    selected_appointment_id = ft.Text(value=None, visible=False)

    # --- Widget Definitions (Unchanged) ---
    patient_name_entry = ft.TextField(label="Full Name", bgcolor="#3B4252")
    patient_phone_entry = ft.TextField(label="Phone", bgcolor="#3B4252")
    patient_dob_entry = ft.TextField(label="DOB (YYYY-MM-DD)", hint_text="YYYY-MM-DD", bgcolor="#3B4252")
    patient_address_entry = ft.TextField(label="Address", bgcolor="#3B4252")
    patients_list_view = ft.ListView(expand=1, spacing=10, auto_scroll=True)

    doctor_name_entry = ft.TextField(label="Full Name", bgcolor="#3B4252")
    doctor_spec_entry = ft.TextField(label="Specialization", bgcolor="#3B4252")
    doctor_phone_entry = ft.TextField(label="Phone", bgcolor="#3B4252")
    doctors_list_view = ft.ListView(expand=1, spacing=10, auto_scroll=True)

    service_name_entry = ft.TextField(label="Service Name", bgcolor="#3B4252")
    service_price_entry = ft.TextField(label="Price", prefix_text="$", input_filter=ft.InputFilter(r"[0-9.]"), bgcolor="#3B4252")
    services_list_view = ft.ListView(expand=1, spacing=10, auto_scroll=True)

    patient_dropdown = ft.Dropdown(label="Patient", bgcolor="#3B4252")
    doctor_dropdown = ft.Dropdown(label="Doctor", bgcolor="#3B4252")
    service_dropdown = ft.Dropdown(label="Service", bgcolor="#3B4252")
    appointment_date_entry = ft.TextField(label="Date (YYYY-MM-DD)", hint_text="YYYY-MM-DD", bgcolor="#3B4252")
    appointment_time_entry = ft.TextField(label="Time (HH:MM)", hint_text="HH:MM", bgcolor="#3B4252")
    appointment_notes_entry = ft.TextField(label="Notes", bgcolor="#3B4252")
    payment_status_dropdown = ft.Dropdown(label="Payment Status", bgcolor="#3B4252", options=[
        ft.dropdown.Option("Pending"),
        ft.dropdown.Option("Paid"),
        ft.dropdown.Option("Cancelled"),
    ], value="Pending")
    price_label = ft.Text("Service Price: $0.00", size=14, weight=ft.FontWeight.BOLD)
    appointments_list_view = ft.ListView(expand=1, spacing=10, auto_scroll=True)

    # --- Utility Functions ---
    def show_snackbar(message, color='RED_700'): 
        page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=color)
        page.snack_bar.open = True
        page.update()

    def close_drawer(e=None):
        page.drawer.open = False
        page.update()
        
    def update_appointment_price_label(e=None):
        selected_text = service_dropdown.value
        price = 0.0
        if selected_text and "(ID: " in selected_text:
            try:
                parts = selected_text.split(" (ID: ")
                if len(parts) > 1:
                    id_part = parts[1].split(") - ")
                    service_id = int(id_part[0].strip())
                    price = db.get_service_price(service_id)
            except (IndexError, ValueError):
                pass
        price_label.value = f"Service Price: ${price:.2f}"
        page.update()

    # --- Patient Handlers (Includes UI Refresh) ---
    def update_patient_handler(e):
        pid = selected_patient_id.value
        if not pid: 
            show_snackbar("Please select a patient to update.", 'RED_700')
            return
        try:
            db.update_patient(pid, patient_name_entry.value, patient_phone_entry.value, patient_dob_entry.value, patient_address_entry.value)
            show_snackbar("Patient updated successfully!", 'GREEN_700')
            clear_patient_fields()
            populate_patients_list()
            populate_appointment_dropdowns() 
        except Exception as ex:
            show_snackbar(f"Update failed: {ex}", 'RED_700')

    def delete_patient_handler(e):
        pid = selected_patient_id.value
        if not pid:
            show_snackbar("Please select a patient to delete.", 'RED_700')
            return
        try:
            db.delete_patient(pid)
            show_snackbar("Patient deleted successfully!", 'GREEN_700')
            clear_patient_fields()
            populate_patients_list()
            populate_appointment_dropdowns() 
        except Exception as ex:
            show_snackbar(f"Deletion failed: {ex}", 'RED_700')

    def populate_patients_list():
        patients_list_view.controls.clear()
        for (pid, name, phone, dob, address) in db.get_all_patients():
            patients_list_view.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"{name} (ID: {pid})", weight=ft.FontWeight.BOLD),
                        ft.Text(f"Phone: {phone if phone else 'N/A'} | DOB: {dob if dob else 'N/A'}"),
                    ], spacing=2),
                    padding=10, border_radius=5, bgcolor="#3B4252",
                    on_click=lambda e, pid=pid, name=name, phone=phone, dob=dob, address=address: select_patient(e, pid, name, phone, dob, address)
                )
            )
        page.update()
        
    def select_patient(e, pid, name, phone, dob, address):
        selected_patient_id.value = pid
        patient_name_entry.value = name
        patient_phone_entry.value = phone
        patient_dob_entry.value = dob
        patient_address_entry.value = address
        page.update()

    def add_patient(e):
        if not patient_name_entry.value: show_snackbar("Full Name is required!", 'RED_700'); return
        try:
            db.add_patient(patient_name_entry.value, patient_phone_entry.value, patient_dob_entry.value, patient_address_entry.value)
            show_snackbar("Patient added successfully!", 'GREEN_700')
            clear_patient_fields()
            populate_patients_list()
            populate_appointment_dropdowns() 
        except Exception as ex:
            show_snackbar(f"Add patient failed: {ex}", 'RED_700')
        
    def clear_patient_fields(e=None):
        selected_patient_id.value = None
        patient_name_entry.value = patient_phone_entry.value = patient_dob_entry.value = patient_address_entry.value = ""
        page.update()
        
    # --- Doctor Handlers (Includes UI Refresh) ---
    def update_doctor_handler(e):
        did = selected_doctor_id.value
        if not did: 
            show_snackbar("Please select a doctor to update.", 'RED_700')
            return
        try:
            db.update_doctor(did, doctor_name_entry.value, doctor_spec_entry.value, doctor_phone_entry.value)
            show_snackbar("Doctor updated successfully!", 'GREEN_700')
            clear_doctor_fields()
            populate_doctors_list()
            populate_appointment_dropdowns() 
        except Exception as ex:
            show_snackbar(f"Update failed: {ex}", 'RED_700')

    def delete_doctor_handler(e):
        did = selected_doctor_id.value
        if not did:
            show_snackbar("Please select a doctor to delete.", 'RED_700')
            return
        try:
            db.delete_doctor(did)
            show_snackbar("Doctor deleted successfully!", 'GREEN_700')
            clear_doctor_fields()
            populate_doctors_list()
            populate_appointment_dropdowns() 
        except Exception as ex:
            show_snackbar(f"Deletion failed: {ex}", 'RED_700')
            
    def populate_doctors_list():
        doctors_list_view.controls.clear()
        for (did, name, spec, phone) in db.get_all_doctors():
            doctors_list_view.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"{name} (ID: {did})", weight=ft.FontWeight.BOLD),
                        ft.Text(f"Spec: {spec} | Phone: {phone if phone else 'N/A'}"),
                    ]),
                    padding=10, border_radius=5, bgcolor="#3B4252",
                    on_click=lambda e, did=did, name=name, spec=spec, phone=phone: select_doctor(e, did, name, spec, phone)
                )
            )
        page.update()
        
    def select_doctor(e, did, name, spec, phone):
        selected_doctor_id.value = did
        doctor_name_entry.value = name
        doctor_spec_entry.value = spec
        doctor_phone_entry.value = phone
        page.update()
    
    def add_doctor(e):
        if not doctor_name_entry.value or not doctor_spec_entry.value: show_snackbar("Name and Specialization are required!", 'RED_700'); return
        try:
            db.add_doctor(doctor_name_entry.value, doctor_spec_entry.value, doctor_phone_entry.value)
            show_snackbar("Doctor added successfully!", 'GREEN_700')
            clear_doctor_fields()
            populate_doctors_list()
            populate_appointment_dropdowns() 
        except Exception as ex:
            show_snackbar(f"Add doctor failed: {ex}", 'RED_700')

    def clear_doctor_fields(e=None):
        selected_doctor_id.value = None
        doctor_name_entry.value = doctor_spec_entry.value = doctor_phone_entry.value = ""
        page.update()

    # --- Service Handlers (Includes UI Refresh) ---
    def update_service_handler(e):
        sid = selected_service_id.value
        if not sid:
            show_snackbar("Please select a service to update.", 'RED_700')
            return
        try:
            name = service_name_entry.value
            price = float(service_price_entry.value)
            if not name or price <= 0:
                show_snackbar("Invalid service name or price.", 'RED_700')
                return
            db.update_service(sid, name, price)
            show_snackbar("Service updated successfully!", 'GREEN_700')
            clear_service_fields()
            populate_services_list()
            populate_appointment_dropdowns() 
        except ValueError:
            show_snackbar("Price must be a valid number.", 'RED_700')
        except Exception as ex:
            show_snackbar(f"Update failed: {ex}", 'RED_700')
            
    def delete_service_handler(e):
        sid = selected_service_id.value
        if not sid:
            show_snackbar("Please select a service to delete.", 'RED_700')
            return
        try:
            db.delete_service(sid)
            show_snackbar("Service deleted successfully!", 'GREEN_700')
            clear_service_fields()
            populate_services_list()
            populate_appointment_dropdowns() 
        except Exception as ex:
            show_snackbar(f"Deletion failed: {ex}", 'RED_700')

    def populate_services_list():
        services_list_view.controls.clear()
        for (sid, name, price) in db.get_all_services():
            services_list_view.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(f"{name} (ID: {sid})", weight=ft.FontWeight.BOLD, expand=1),
                        ft.Text(f"${price:.2f}", weight=ft.FontWeight.BOLD, color='YELLOW_ACCENT_700'), 
                    ]),
                    padding=10, border_radius=5, bgcolor="#3B4252",
                    on_click=lambda e, sid=sid, name=name, price=price: select_service(e, sid, name, str(price))
                )
            )
        page.update()
        
    def select_service(e, sid, name, price):
        selected_service_id.value = sid
        service_name_entry.value = name
        service_price_entry.value = price
        page.update()
        
    def add_service(e):
        try:
            name = service_name_entry.value
            price = float(service_price_entry.value)
            if not name or price <= 0: show_snackbar("Service Name and a valid Price are required!", 'RED_700'); return
            db.add_service(name, price)
            show_snackbar("Service added successfully!", 'GREEN_700')
            clear_service_fields()
            populate_services_list()
            populate_appointment_dropdowns() 
        except ValueError: show_snackbar("Price must be a valid number.", 'RED_700')
        except Exception as ex:
            show_snackbar(f"Add service failed: {ex}", 'RED_700')


    def clear_service_fields(e=None):
        selected_service_id.value = None
        service_name_entry.value = service_price_entry.value = ""
        page.update()


    # --- Appointment Handlers (Includes UI Refresh) ---
    def populate_appointment_dropdowns():
        patient_dropdown.options = [ft.dropdown.Option(text=f"{p[1]} (ID: {p[0]})", key=f"{p[1]} (ID: {p[0]})") for p in db.get_all_patients()]
        doctor_dropdown.options = [ft.dropdown.Option(text=f"{d[1]} (ID: {d[0]})", key=f"{d[1]} (ID: {d[0]})") for d in db.get_all_doctors()]
        service_dropdown.options = [ft.dropdown.Option(text=f"{s[1]} (ID: {s[0]}) - {s[2]:.2f}", key=f"{s[1]} (ID: {s[0]}) - {s[2]:.2f}") for s in db.get_all_services()]
        update_appointment_price_label()
        page.update()

    def populate_appointments_list():
        appointments_list_view.controls.clear()
        for (aid, p_name, d_name, s_name, price, date, time, status) in db.get_all_appointments():
            price_str = f"${price:.2f}" if price else "$0.00"
            status_color = 'GREEN_700' if status == 'Paid' else ('RED_700' if status == 'Cancelled' else 'YELLOW_700')
            
            appointments_list_view.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"{date} @ {time}", weight=ft.FontWeight.BOLD),
                            ft.Container(ft.Text(status, size=10, color='BLACK'), padding=ft.padding.only(left=5, right=5, top=2, bottom=2), border_radius=3, bgcolor=status_color) 
                        ]),
                        ft.Text(f"Patient: {p_name if p_name else 'N/A'}"),
                        ft.Text(f"Doctor: {d_name if d_name else 'N/A'}"),
                        ft.Text(f"Service: {s_name if s_name else 'N/A'} ({price_str})", color='BLUE_GREY_100'), 
                    ], spacing=2),
                    padding=10, border_radius=5, bgcolor="#3B4252",
                    on_click=lambda e, aid=aid: select_appointment(e, aid)
                )
            )
        page.update()

    def select_appointment(e, aid):
        selected_appointment_id.value = aid
        details = db.get_appointment_details(aid) 
        if details:
            pid, did, sid, date, time, notes, status = details
            
            patient_name = next((f"{p[1]} (ID: {p[0]})" for p in db.get_all_patients() if p[0] == pid), '')
            doctor_name = next((f"{d[1]} (ID: {d[0]})" for d in db.get_all_doctors() if d[0] == did), '')
            service_text = next((f"{s[1]} (ID: {s[0]}) - {s[2]:.2f}" for s in db.get_all_services() if s[0] == sid), '')

            patient_dropdown.value = patient_name
            doctor_dropdown.value = doctor_name
            service_dropdown.value = service_text
            appointment_date_entry.value = date
            appointment_time_entry.value = time
            appointment_notes_entry.value = notes
            payment_status_dropdown.value = status
            
            update_appointment_price_label()
            page.update()

    def get_appointment_data():
        p_text, d_text, s_text = patient_dropdown.value, doctor_dropdown.value, service_dropdown.value
        if not all([p_text, d_text, s_text, appointment_date_entry.value, appointment_time_entry.value, payment_status_dropdown.value]):
            show_snackbar("Please fill all required fields!", 'RED_700')
            return None
            
        try:
            # استخدام .split() للحصول على الـ ID من القائمة المنسدلة
            p_id = int(p_text.split("(ID: ")[1].strip(")"))
            d_id = int(d_text.split("(ID: ")[1].strip(")"))
            s_id = int(s_text.split("(ID: ")[1].split(")")[0].strip()) 
            
            return (p_id, d_id, s_id, appointment_date_entry.value, appointment_time_entry.value, appointment_notes_entry.value, payment_status_dropdown.value)
        except (IndexError, ValueError):
            show_snackbar("Please select valid Patient, Doctor, and Service from the lists.", 'RED_700')
            return None

    def add_appointment(e):
        data = get_appointment_data()
        if not data: return
        try:
            db.add_appointment(*data)
            show_snackbar("Appointment added successfully!", 'GREEN_700')
            clear_appointment_fields()
            populate_appointments_list()
        except Exception as ex:
            show_snackbar(f"Add appointment failed: {ex}", 'RED_700')


    def update_appointment(e):
        if not selected_appointment_id.value: show_snackbar("Please select an appointment to update.", 'RED_700'); return
        data = get_appointment_data()
        if not data: return
        try:
            db.update_appointment(selected_appointment_id.value, *data)
            show_snackbar("Appointment updated successfully!", 'GREEN_700')
            clear_appointment_fields()
            populate_appointments_list()
        except Exception as ex:
            show_snackbar(f"Update failed: {ex}", 'RED_700')

    def delete_appointment(e):
        if not selected_appointment_id.value: show_snackbar("Please select an appointment to delete.", 'RED_700'); return
        try:
            db.delete_appointment(selected_appointment_id.value)
            show_snackbar("Appointment deleted successfully!", 'GREEN_700')
            clear_appointment_fields()
            populate_appointments_list()
        except Exception as ex:
            show_snackbar(f"Deletion failed: {ex}", 'RED_700')


    def clear_appointment_fields(e=None):
        selected_appointment_id.value = None
        patient_dropdown.value = doctor_dropdown.value = service_dropdown.value = None
        appointment_date_entry.value = appointment_time_entry.value = appointment_notes_entry.value = ""
        payment_status_dropdown.value = "Pending"
        update_appointment_price_label()
        page.update()

    # --- Page Content Layouts (Unchanged) ---
    app_title = ft.Text("Dashboard", size=20, weight=ft.FontWeight.BOLD)
    main_content_area = ft.Column(expand=1, scroll=ft.ScrollMode.ADAPTIVE, controls=[])

    def create_stat_card(title, count_func):
        count_label = ft.Text(str(count_func()), size=20, weight=ft.FontWeight.BOLD)
        return ft.Container(
            content=ft.Column([
                ft.Text(title, color='BLUE_GREY_300'), 
                count_label
            ]),
            padding=15, margin=ft.padding.only(bottom=10), border_radius=10, bgcolor="#3B4252"
        )
        
    def show_dashboard(e=None):
        app_title.value = "Dashboard"
        main_content_area.controls = [
            ft.Container(ft.Text("Clinic Overview", size=24, weight=ft.FontWeight.BOLD), padding=10),
            create_stat_card("Total Patients", lambda: len(db.get_all_patients())),
            create_stat_card("Total Doctors", lambda: len(db.get_all_doctors())),
            create_stat_card("Total Appointments", lambda: len(db.get_all_appointments())),
            create_stat_card("Total Services", lambda: len(db.get_all_services())),
        ]
        close_drawer(); page.update()

    def show_patients(e):
        app_title.value = "Patients"
        main_content_area.controls = [
            ft.Container(ft.Text("Patient Details", size=18, weight=ft.FontWeight.BOLD), padding=10),
            patient_name_entry, patient_phone_entry, patient_dob_entry, patient_address_entry,
            ft.Row([
                ft.ElevatedButton("Add", on_click=add_patient, expand=1, icon='add', bgcolor="#5E81AC"),
                ft.ElevatedButton("Update", on_click=update_patient_handler, expand=1, icon='update', bgcolor="#5E81AC"), 
            ]),
            ft.Row([
                ft.ElevatedButton("Delete", on_click=delete_patient_handler, expand=1, icon='delete_forever', color='WHITE', bgcolor='RED_700'), 
                ft.ElevatedButton("Clear", on_click=clear_patient_fields, expand=1, icon='clear_all'), 
            ]),
            ft.Divider(),
            ft.Container(ft.Text("Patient List", size=16), padding=ft.padding.only(left=10, top=10)),
            ft.Container(patients_list_view, expand=True, padding=10),
            selected_patient_id
        ]
        populate_patients_list(); close_drawer(); page.update()

    def show_doctors(e):
        app_title.value = "Doctors"
        main_content_area.controls = [
            ft.Container(ft.Text("Doctor Details", size=18, weight=ft.FontWeight.BOLD), padding=10),
            doctor_name_entry, doctor_spec_entry, doctor_phone_entry,
            ft.Row([
                ft.ElevatedButton("Add", on_click=add_doctor, expand=1, icon='add', bgcolor="#5E81AC"),
                ft.ElevatedButton("Update", on_click=update_doctor_handler, expand=1, icon='update', bgcolor="#5E81AC"),
            ]),
            ft.Row([
                ft.ElevatedButton("Delete", on_click=delete_doctor_handler, expand=1, icon='delete_forever', color='WHITE', bgcolor='RED_700'),
                ft.ElevatedButton("Clear", on_click=clear_doctor_fields, expand=1, icon='clear_all'),
            ]),
            ft.Divider(),
            ft.Container(ft.Text("Doctor List", size=16), padding=ft.padding.only(left=10, top=10)),
            ft.Container(doctors_list_view, expand=True, padding=10),
            selected_doctor_id
        ]
        populate_doctors_list(); close_drawer(); page.update()

    def show_services(e):
        app_title.value = "Services"
        main_content_area.controls = [
            ft.Container(ft.Text("Service Details", size=18, weight=ft.FontWeight.BOLD), padding=10),
            service_name_entry, service_price_entry,
            ft.Row([
                ft.ElevatedButton("Add", on_click=add_service, expand=1, icon='add', bgcolor="#5E81AC"),
                ft.ElevatedButton("Update", on_click=update_service_handler, expand=1, icon='update', bgcolor="#5E81AC"),
            ]),
            ft.Row([
                ft.ElevatedButton("Delete", on_click=delete_service_handler, expand=1, icon='delete_forever', color='WHITE', bgcolor='RED_700'),
                ft.ElevatedButton("Clear", on_click=clear_service_fields, expand=1, icon='clear_all'),
            ]),
            ft.Divider(),
            ft.Container(ft.Text("Service List", size=16), padding=ft.padding.only(left=10, top=10)),
            ft.Container(services_list_view, expand=True, padding=10),
            selected_service_id
        ]
        populate_services_list(); close_drawer(); page.update()

    def show_appointments(e):
        app_title.value = "Appointments"
        main_content_area.controls = [
            ft.Container(ft.Text("Appointment Details", size=18, weight=ft.FontWeight.BOLD), padding=10),
            patient_dropdown, doctor_dropdown, service_dropdown,
            appointment_date_entry, appointment_time_entry, appointment_notes_entry,
            payment_status_dropdown, price_label,
            ft.Row([
                ft.ElevatedButton("Add", on_click=add_appointment, expand=1, icon='add', bgcolor="#5E81AC"), 
                ft.ElevatedButton("Update", on_click=update_appointment, expand=1, icon='update', bgcolor="#5E81AC"), 
            ]),
            ft.Row([
                ft.ElevatedButton("Delete", on_click=delete_appointment, expand=1, icon='delete_forever', color='WHITE', bgcolor='RED_700'), 
                ft.ElevatedButton("Clear", on_click=clear_appointment_fields, expand=1, icon='clear_all'), 
            ]),
            ft.Divider(),
            ft.Container(ft.Text("Appointment List", size=16), padding=ft.padding.only(left=10, top=10)),
            ft.Container(appointments_list_view, expand=True, padding=10),
            selected_appointment_id
        ]
        populate_appointment_dropdowns(); populate_appointments_list(); close_drawer(); page.update()
        
    # Bind service dropdown change to update price label
    service_dropdown.on_change = update_appointment_price_label

    # --- Navigation Drawer Setup (Unchanged) ---
    def nav_menu_change(e):
        selected_index = e.control.selected_index
        if selected_index == 0: show_dashboard()
        elif selected_index == 1: show_patients(None)
        elif selected_index == 2: show_doctors(None)
        elif selected_index == 3: show_services(None)
        elif selected_index == 4: show_appointments(None)

    page.drawer = ft.NavigationDrawer(
        controls=[
            ft.Container(height=12),
            ft.NavigationDrawerDestination(icon='dashboard_outlined', label="Dashboard", selected_icon='dashboard'), 
            ft.Divider(thickness=1),
            ft.NavigationDrawerDestination(icon='people_alt_outlined', label="Patients", selected_icon='people_alt'), 
            ft.NavigationDrawerDestination(icon='medical_services_outlined', label="Doctors", selected_icon='medical_services'), 
            ft.NavigationDrawerDestination(icon='list_alt_outlined', label="Services", selected_icon='list_alt'), 
            ft.NavigationDrawerDestination(icon='calendar_month_outlined', label="Appointments", selected_icon='calendar_month'), 
        ],
        on_change=nav_menu_change,
        bgcolor="#242933" 
    )

    def open_drawer(e):
        page.drawer.open = True
        page.update()

    # --- AppBar Setup (Unchanged) ---
    page.appbar = ft.AppBar(
        leading=ft.IconButton('menu', on_click=open_drawer), 
        title=app_title,
        bgcolor="#5E81AC" 
    )

    # --- Initial Page Load ---
    page.add(main_content_area)
    show_dashboard() 

# --- Flet Entry Point (التعديل هنا) ---
if __name__ == "__main__":
    # 🌟 (2) إزالة محاولة الاتصال والإغلاق اليدوية لتجنب المشاكل في بيئات مختلفة
    ft.app(target=main)
