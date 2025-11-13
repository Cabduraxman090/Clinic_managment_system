import flet as ft
import sqlite3
import os
import json
import hashlib
from datetime import datetime, date, timedelta
import shutil
import uuid
from typing import List, Dict, Optional, Tuple

# Database class for handling all SQLite operations
class DentalClinicDB:
    def __init__(self, db_path="dental_clinic.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table for login
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """)
        
        # Patients table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            phone TEXT,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Medical history table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS medical_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            allergies TEXT,
            chronic_diseases TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (id)
        )
        """)
        
        # Doctors table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialty TEXT,
            phone TEXT,
            email TEXT
        )
        """)
        
        # Appointments table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            doctor_id INTEGER,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            notes TEXT,
            status TEXT DEFAULT 'scheduled',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (id),
            FOREIGN KEY (doctor_id) REFERENCES doctors (id)
        )
        """)
        
        # Treatments table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS treatments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            appointment_id INTEGER,
            description TEXT,
            cost REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (id),
            FOREIGN KEY (appointment_id) REFERENCES appointments (id)
        )
        """)
        
        # Invoices table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            service_provided TEXT,
            total_cost REAL,
            amount_paid REAL,
            remaining_balance REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (id)
        )
        """)
        
        # Settings table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT
        )
        """)
        
        # Check if default user exists, if not create one
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            # Default password is 'admin'
            hashed_password = hashlib.sha256("admin".encode()).hexdigest()
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                          ("admin", hashed_password))
        
        # Initialize default settings
        default_settings = [
            ("language", "English"),
            ("dark_mode", "False")
        ]
        for key, value in default_settings:
            cursor.execute("SELECT * FROM settings WHERE key = ?", (key,))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", 
                              (key, value))
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """Get a database connection"""
        return sqlite3.connect(self.db_path)
    
    def verify_user(self, username, password):
        """Verify user credentials"""
        conn = self.get_connection()
        cursor = conn.cursor()
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", 
                      (username, hashed_password))
        user = cursor.fetchone()
        conn.close()
        return user is not None
    
    def update_user_credentials(self, username, new_password):
        """Update user credentials"""
        conn = self.get_connection()
        cursor = conn.cursor()
        hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
        cursor.execute("UPDATE users SET password = ? WHERE username = ?", 
                      (hashed_password, username))
        conn.commit()
        conn.close()
    
    def add_patient(self, name, age, gender, phone, address):
        """Add a new patient"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO patients (name, age, gender, phone, address) 
        VALUES (?, ?, ?, ?, ?)
        """, (name, age, gender, phone, address))
        patient_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return patient_id
    
    def get_patients(self, search_term=""):
        """Get all patients or search by name"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if search_term:
            cursor.execute("""
            SELECT * FROM patients 
            WHERE name LIKE ? OR phone LIKE ?
            ORDER BY name
            """, (f"%{search_term}%", f"%{search_term}%"))
        else:
            cursor.execute("SELECT * FROM patients ORDER BY name")
        patients = cursor.fetchall()
        conn.close()
        return patients
    
    def get_patient_by_id(self, patient_id):
        """Get patient by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
        patient = cursor.fetchone()
        conn.close()
        return patient
    
    def update_patient(self, patient_id, name, age, gender, phone, address):
        """Update patient information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE patients 
        SET name = ?, age = ?, gender = ?, phone = ?, address = ?
        WHERE id = ?
        """, (name, age, gender, phone, address, patient_id))
        conn.commit()
        conn.close()
    
    def delete_patient(self, patient_id):
        """Delete a patient and all related records"""
        conn = self.get_connection()
        cursor = conn.cursor()
        # Delete related records first
        cursor.execute("DELETE FROM medical_history WHERE patient_id = ?", (patient_id,))
        cursor.execute("DELETE FROM treatments WHERE patient_id = ?", (patient_id,))
        cursor.execute("DELETE FROM invoices WHERE patient_id = ?", (patient_id,))
        cursor.execute("DELETE FROM appointments WHERE patient_id = ?", (patient_id,))
        # Delete patient
        cursor.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        conn.commit()
        conn.close()
    
    def add_medical_history(self, patient_id, allergies, chronic_diseases, notes):
        """Add medical history for a patient"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO medical_history (patient_id, allergies, chronic_diseases, notes) 
        VALUES (?, ?, ?, ?)
        """, (patient_id, allergies, chronic_diseases, notes))
        conn.commit()
        conn.close()
    
    def get_medical_history(self, patient_id):
        """Get medical history for a patient"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM medical_history 
        WHERE patient_id = ? 
        ORDER BY created_at DESC
        """, (patient_id,))
        history = cursor.fetchall()
        conn.close()
        return history
    
    def add_doctor(self, name, specialty, phone, email):
        """Add a new doctor"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO doctors (name, specialty, phone, email) 
        VALUES (?, ?, ?, ?)
        """, (name, specialty, phone, email))
        doctor_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return doctor_id
    
    def get_doctors(self, search_term=""):
        """Get all doctors or search by name"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if search_term:
            cursor.execute("""
            SELECT * FROM doctors 
            WHERE name LIKE ? OR specialty LIKE ?
            ORDER BY name
            """, (f"%{search_term}%", f"%{search_term}%"))
        else:
            cursor.execute("SELECT * FROM doctors ORDER BY name")
        doctors = cursor.fetchall()
        conn.close()
        return doctors
    
    def update_doctor(self, doctor_id, name, specialty, phone, email):
        """Update doctor information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE doctors 
        SET name = ?, specialty = ?, phone = ?, email = ?
        WHERE id = ?
        """, (name, specialty, phone, email, doctor_id))
        conn.commit()
        conn.close()
    
    def delete_doctor(self, doctor_id):
        """Delete a doctor"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM doctors WHERE id = ?", (doctor_id,))
        conn.commit()
        conn.close()
    
    def add_appointment(self, patient_id, doctor_id, date, time, notes):
        """Add a new appointment"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO appointments (patient_id, doctor_id, date, time, notes) 
        VALUES (?, ?, ?, ?, ?)
        """, (patient_id, doctor_id, date, time, notes))
        appointment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return appointment_id
    
    def get_appointments(self, date_filter=None, search_term=""):
        """Get all appointments or filter by date"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if date_filter:
            cursor.execute("""
            SELECT a.*, p.name as patient_name, d.name as doctor_name 
            FROM appointments a
            JOIN patients p ON a.patient_id = p.id
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.date = ?
            ORDER BY a.date, a.time
            """, (date_filter,))
        elif search_term:
            cursor.execute("""
            SELECT a.*, p.name as patient_name, d.name as doctor_name 
            FROM appointments a
            JOIN patients p ON a.patient_id = p.id
            JOIN doctors d ON a.doctor_id = d.id
            WHERE p.name LIKE ? OR d.name LIKE ?
            ORDER BY a.date, a.time
            """, (f"%{search_term}%", f"%{search_term}%"))
        else:
            cursor.execute("""
            SELECT a.*, p.name as patient_name, d.name as doctor_name 
            FROM appointments a
            JOIN patients p ON a.patient_id = p.id
            JOIN doctors d ON a.doctor_id = d.id
            ORDER BY a.date, a.time
            """)
        
        appointments = cursor.fetchall()
        conn.close()
        return appointments
    
    def update_appointment(self, appointment_id, patient_id, doctor_id, date, time, notes, status):
        """Update appointment information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE appointments 
        SET patient_id = ?, doctor_id = ?, date = ?, time = ?, notes = ?, status = ?
        WHERE id = ?
        """, (patient_id, doctor_id, date, time, notes, status, appointment_id))
        conn.commit()
        conn.close()
    
    def delete_appointment(self, appointment_id):
        """Delete an appointment"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
        conn.commit()
        conn.close()
    
    def add_invoice(self, patient_id, service_provided, total_cost, amount_paid):
        """Add a new invoice"""
        conn = self.get_connection()
        cursor = conn.cursor()
        remaining_balance = total_cost - amount_paid
        cursor.execute("""
        INSERT INTO invoices (patient_id, service_provided, total_cost, amount_paid, remaining_balance) 
        VALUES (?, ?, ?, ?, ?)
        """, (patient_id, service_provided, total_cost, amount_paid, remaining_balance))
        invoice_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return invoice_id
    
    def get_invoices(self, search_term=""):
        """Get all invoices or search by patient name"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if search_term:
            cursor.execute("""
            SELECT i.*, p.name as patient_name 
            FROM invoices i
            JOIN patients p ON i.patient_id = p.id
            WHERE p.name LIKE ? OR i.service_provided LIKE ?
            ORDER BY i.created_at DESC
            """, (f"%{search_term}%", f"%{search_term}%"))
        else:
            cursor.execute("""
            SELECT i.*, p.name as patient_name 
            FROM invoices i
            JOIN patients p ON i.patient_id = p.id
            ORDER BY i.created_at DESC
            """)
        invoices = cursor.fetchall()
        conn.close()
        return invoices
    
    def update_invoice(self, invoice_id, patient_id, service_provided, total_cost, amount_paid):
        """Update invoice information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        remaining_balance = total_cost - amount_paid
        cursor.execute("""
        UPDATE invoices 
        SET patient_id = ?, service_provided = ?, total_cost = ?, amount_paid = ?, remaining_balance = ?
        WHERE id = ?
        """, (patient_id, service_provided, total_cost, amount_paid, remaining_balance, invoice_id))
        conn.commit()
        conn.close()
    
    def delete_invoice(self, invoice_id):
        """Delete an invoice"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
        conn.commit()
        conn.close()
    
    def get_dashboard_stats(self):
        """Get dashboard statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Total patients
        cursor.execute("SELECT COUNT(*) FROM patients")
        total_patients = cursor.fetchone()[0]
        
        # Today's appointments
        today = date.today().strftime("%Y-%m-%d")
        cursor.execute("SELECT COUNT(*) FROM appointments WHERE date = ?", (today,))
        today_appointments = cursor.fetchone()[0]
        
        # This month's revenue
        current_month = date.today().strftime("%Y-%m")
        cursor.execute("""
        SELECT SUM(amount_paid) FROM invoices 
        WHERE created_at LIKE ?
        """, (f"{current_month}%",))
        monthly_revenue = cursor.fetchone()[0] or 0
        
        # Upcoming appointments (next 7 days)
        next_week = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
        cursor.execute("""
        SELECT COUNT(*) FROM appointments 
        WHERE date BETWEEN ? AND ?
        """, (today, next_week))
        upcoming_appointments = cursor.fetchone()[0]
        
        conn.close()
        return {
            "total_patients": total_patients,
            "today_appointments": today_appointments,
            "monthly_revenue": monthly_revenue,
            "upcoming_appointments": upcoming_appointments
        }
    
    def get_setting(self, key):
        """Get a setting value"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def update_setting(self, key, value):
        """Update a setting value"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO settings (key, value) 
        VALUES (?, ?)
        """, (key, value))
        conn.commit()
        conn.close()
    
    def export_db(self, export_path):
        """Export database to a file"""
        try:
            shutil.copy2(self.db_path, export_path)
            return True
        except Exception as e:
            print(f"Error exporting database: {e}")
            return False
    
    def import_db(self, import_path):
        """Import database from a file"""
        try:
            # Close current connection if any
            conn = self.get_connection()
            conn.close()
            
            # Replace current database with imported one
            shutil.copy2(import_path, self.db_path)
            return True
        except Exception as e:
            print(f"Error importing database: {e}")
            return False

# Main application class
class DentalClinicApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Dental Clinic Management"
        self.page.window.width = 400
        self.page.window.height = 800
        self.page.window.min_width = 350
        self.page.window.min_height = 600
        
        # Initialize database
        self.db = DentalClinicDB()
        
        # App state
        self.logged_in = False
        self.current_user = None
        self.dark_mode = self.db.get_setting("dark_mode") == "True"
        self.language = self.db.get_setting("language") or "English"
        
        # Theme colors
        self.primary_color = ft.colors.BLUE_600
        self.secondary_color = ft.colors.BLUE_50
        self.text_color = ft.colors.BLACK if not self.dark_mode else ft.colors.WHITE
        self.bg_color = ft.colors.WHITE if not self.dark_mode else ft.colors.GREY_900
        self.card_color = ft.colors.WHITE if not self.dark_mode else ft.colors.GREY_800
        
        # Apply theme
        self.apply_theme()
        
        # Navigation
        self.navigation_rail = None
        self.content_area = None
        
        # Initialize UI
        self.init_ui()
        
        # Check if user is logged in
        self.check_login_status()
    
    def apply_theme(self):
        """Apply dark/light theme"""
        self.page.theme_mode = ft.ThemeMode.DARK if self.dark_mode else ft.ThemeMode.LIGHT
        self.page.bgcolor = self.bg_color
        self.page.update()
    
    def init_ui(self):
        """Initialize the UI components"""
        # Create navigation rail
        self.navigation_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.icons.DASHBOARD_OUTLINED,
                    selected_icon=ft.icons.DASHBOARD,
                    label="Dashboard"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.PERSON_OUTLINED,
                    selected_icon=ft.icons.PERSON,
                    label="Patients"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.CALENDAR_MONTH_OUTLINED,
                    selected_icon=ft.icons.CALENDAR_MONTH,
                    label="Appointments"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.LOCAL_HOSPITAL_OUTLINED,
                    selected_icon=ft.icons.LOCAL_HOSPITAL,
                    label="Doctors"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.RECEIPT_OUTLINED,
                    selected_icon=ft.icons.RECEIPT,
                    label="Invoices"
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.SETTINGS_OUTLINED,
                    selected_icon=ft.icons.SETTINGS,
                    label="Settings"
                ),
            ],
            on_change=self.navigation_changed
        )
        
        # Create content area
        self.content_area = ft.Container(
            content=ft.Text("Select a section from the menu"),
            padding=20,
            expand=True
        )
        
        # Create main layout
        self.main_layout = ft.Row([
            self.navigation_rail,
            ft.VerticalDivider(width=1),
            self.content_area
        ], expand=True)
        
        # Login page
        self.login_page = self.create_login_page()
        
        # Set initial view
        self.page.controls = [self.login_page]
        self.page.update()
    
    def create_login_page(self):
        """Create the login page"""
        username_field = ft.TextField(
            label="Username",
            width=300,
            autofocus=True
        )
        
        password_field = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            width=300
        )
        
        login_button = ft.ElevatedButton(
            text="Login",
            width=300,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=self.primary_color
            ),
            on_click=lambda e: self.login(username_field.value, password_field.value)
        )
        
        login_container = ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.HEALING, size=80, color=self.primary_color),
                ft.Text("Dental Clinic Management", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("Please login to continue", size=14, color=ft.colors.GREY_600),
                ft.Divider(height=20, color="transparent"),
                username_field,
                password_field,
                ft.Divider(height=10, color="transparent"),
                login_button
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10
            ),
            padding=30,
            width=400,
            bgcolor=self.card_color,
            border_radius=15,
            shadow=ft.BoxShadow(blur_radius=10, spread_radius=1, color=ft.colors.BLUE_GREY_100)
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Container(height=50),
                login_container
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            padding=20,
            bgcolor=self.bg_color,
            expand=True
        )
    
    def login(self, username, password):
        """Handle login"""
        if not username or not password:
            self.show_snack_bar("Please enter username and password", ft.colors.RED_500)
            return
        
        if self.db.verify_user(username, password):
            self.logged_in = True
            self.current_user = username
            self.page.controls = [self.main_layout]
            self.page.update()
            self.navigation_changed(None)  # Load dashboard
        else:
            self.show_snack_bar("Invalid username or password", ft.colors.RED_500)
    
    def check_login_status(self):
        """Check if user is already logged in"""
        # In a real app, you might check for a stored token or session
        # For this demo, we'll just show the login page
        pass
    
    def logout(self):
        """Handle logout"""
        self.logged_in = False
        self.current_user = None
        self.page.controls = [self.login_page]
        self.page.update()
    
    def navigation_changed(self, e):
        """Handle navigation rail change"""
        if not self.logged_in:
            return
        
        index = self.navigation_rail.selected_index
        
        if index == 0:  # Dashboard
            self.show_dashboard()
        elif index == 1:  # Patients
            self.show_patients()
        elif index == 2:  # Appointments
            self.show_appointments()
        elif index == 3:  # Doctors
            self.show_doctors()
        elif index == 4:  # Invoices
            self.show_invoices()
        elif index == 5:  # Settings
            self.show_settings()
    
    def show_dashboard(self):
        """Show dashboard view"""
        stats = self.db.get_dashboard_stats()
        
        # Create stat cards
        stat_cards = [
            self.create_stat_card("Total Patients", stats["total_patients"], ft.icons.PEOPLE_OUTLINED, ft.colors.BLUE_500),
            self.create_stat_card("Today's Appointments", stats["today_appointments"], ft.icons.CALENDAR_TODAY, ft.colors.GREEN_500),
            self.create_stat_card("Monthly Revenue", f"${stats['monthly_revenue']:.2f}", ft.icons.PAYMENTS_OUTLINED, ft.colors.ORANGE_500),
            self.create_stat_card("Upcoming Appointments", stats["upcoming_appointments"], ft.icons.EVENT_UPCOMING, ft.colors.PURPLE_500)
        ]
        
        # Get today's appointments
        today = date.today().strftime("%Y-%m-%d")
        today_appointments = self.db.get_appointments(date_filter=today)
        
        # Create appointments list
        appointments_list = []
        if today_appointments:
            for apt in today_appointments[:5]:  # Show only first 5
                appointments_list.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.PERSON),
                        title=ft.Text(f"{apt[8]} with Dr. {apt[9]}"),
                        subtitle=ft.Text(f"{apt[4]} at {apt[5]}"),
                        trailing=ft.Icon(ft.icons.CHECK_CIRCLE, color=ft.colors.GREEN_500)
                    )
                )
        else:
            appointments_list.append(
                ft.ListTile(
                    title=ft.Text("No appointments for today"),
                    subtitle=ft.Text("Enjoy your day!"),
                    leading=ft.Icon(ft.icons.BEACH_ACCESS, color=ft.colors.BLUE_300)
                )
            )
        
        self.content_area.content = ft.Column([
            ft.Text("Dashboard", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(height=10, color="transparent"),
            ft.Row(stat_cards, spacing=10, wrap=True),
            ft.Divider(height=20, color="transparent"),
            ft.Text("Today's Appointments", size=18, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.Column(appointments_list, spacing=0),
                border_radius=10,
                bgcolor=self.card_color,
                padding=10,
                shadow=ft.BoxShadow(blur_radius=5, spread_radius=1, color=ft.colors.BLUE_GREY_100)
            )
        ], scroll=ft.ScrollMode.AUTO)
        
        self.page.update()
    
    def create_stat_card(self, title, value, icon, color):
        """Create a statistics card"""
        return ft.Container(
            content=ft.Column([
                ft.Icon(icon, size=30, color=color),
                ft.Text(str(value), size=24, weight=ft.FontWeight.BOLD, color=color),
                ft.Text(title, size=14, color=ft.colors.GREY_600)
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=150,
            height=120,
            bgcolor=self.card_color,
            border_radius=10,
            shadow=ft.BoxShadow(blur_radius=5, spread_radius=1, color=ft.colors.BLUE_GREY_100),
            padding=10
        )
    
    def show_patients(self):
        """Show patients view"""
        # Search field
        search_field = ft.TextField(
            label="Search patients",
            width=300,
            prefix_icon=ft.icons.SEARCH,
            on_change=lambda e: self.update_patients_list(search_field.value)
        )
        
        # Add patient button
        add_patient_button = ft.ElevatedButton(
            text="Add New Patient",
            icon=ft.icons.ADD,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=self.primary_color
            ),
            on_click=self.show_add_patient_dialog
        )
        
        # Patients list
        self.patients_list = ft.Column([], spacing=5, scroll=ft.ScrollMode.AUTO)
        
        # Initial load
        self.update_patients_list()
        
        self.content_area.content = ft.Column([
            ft.Row([
                ft.Text("Patients", size=24, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                add_patient_button
            ]),
            ft.Divider(height=10, color="transparent"),
            search_field,
            ft.Divider(height=10, color="transparent"),
            ft.Container(
                content=self.patients_list,
                border_radius=10,
                bgcolor=self.card_color,
                padding=10,
                height=500,
                shadow=ft.BoxShadow(blur_radius=5, spread_radius=1, color=ft.colors.BLUE_GREY_100)
            )
        ], scroll=ft.ScrollMode.AUTO)
        
        self.page.update()
    
    def update_patients_list(self, search_term=""):
        """Update the patients list"""
        patients = self.db.get_patients(search_term)
        
        self.patients_list.controls = []
        
        if patients:
            for patient in patients:
                patient_card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.ListTile(
                                leading=ft.Icon(ft.icons.PERSON),
                                title=ft.Text(patient[1], weight=ft.FontWeight.BOLD),
                                subtitle=ft.Text(f"Age: {patient[2]}, Phone: {patient[4]}"),
                                trailing=ft.PopupMenuButton(
                                    icon=ft.icons.MORE_VERT,
                                    items=[
                                        ft.PopupMenuItem(
                                            text="View Details",
                                            icon=ft.icons.VISIBILITY,
                                            on_click=lambda e, p=patient: self.show_patient_details(p)
                                        ),
                                        ft.PopupMenuItem(
                                            text="Edit",
                                            icon=ft.icons.EDIT,
                                            on_click=lambda e, p=patient: self.show_edit_patient_dialog(p)
                                        ),
                                        ft.PopupMenuItem(
                                            text="Delete",
                                            icon=ft.icons.DELETE,
                                            on_click=lambda e, p=patient: self.delete_patient(p)
                                        ),
                                    ]
                                )
                            ),
                        ]),
                        padding=10
                    ),
                    elevation=2
                )
                self.patients_list.controls.append(patient_card)
        else:
            self.patients_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.SEARCH_OFF, size=50, color=ft.colors.GREY_400),
                        ft.Text("No patients found", size=16, color=ft.colors.GREY_600)
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
        
        self.page.update()
    
    def show_add_patient_dialog(self, e):
        """Show dialog to add a new patient"""
        name_field = ft.TextField(label="Name", width=300)
        age_field = ft.TextField(label="Age", width=300, keyboard_type=ft.KeyboardType.NUMBER)
        gender_dropdown = ft.Dropdown(
            label="Gender",
            width=300,
            options=[
                ft.dropdown.Option("Male"),
                ft.dropdown.Option("Female"),
                ft.dropdown.Option("Other")
            ]
        )
        phone_field = ft.TextField(label="Phone", width=300)
        address_field = ft.TextField(label="Address", width=300)
        
        allergies_field = ft.TextField(label="Allergies", width=300)
        diseases_field = ft.TextField(label="Chronic Diseases", width=300)
        notes_field = ft.TextField(label="Notes", width=300, multiline=True)
        
        def save_patient(e):
            if not name_field.value:
                self.show_snack_bar("Please enter patient name", ft.colors.RED_500)
                return
            
            patient_id = self.db.add_patient(
                name_field.value,
                age_field.value,
                gender_dropdown.value,
                phone_field.value,
                address_field.value
            )
            
            if allergies_field.value or diseases_field.value or notes_field.value:
                self.db.add_medical_history(
                    patient_id,
                    allergies_field.value,
                    diseases_field.value,
                    notes_field.value
                )
            
            self.update_patients_list()
            dialog.open = False
            self.page.update()
            self.show_snack_bar("Patient added successfully", ft.colors.GREEN_500)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Add New Patient"),
            content=ft.Column([
                ft.Text("Personal Information", weight=ft.FontWeight.BOLD),
                name_field,
                age_field,
                gender_dropdown,
                phone_field,
                address_field,
                ft.Divider(),
                ft.Text("Medical History", weight=ft.FontWeight.BOLD),
                allergies_field,
                diseases_field,
                notes_field
            ], scroll=ft.ScrollMode.AUTO, tight=True, height=400),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Save", on_click=save_patient)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def show_edit_patient_dialog(self, patient):
        """Show dialog to edit a patient"""
        name_field = ft.TextField(label="Name", width=300, value=patient[1])
        age_field = ft.TextField(label="Age", width=300, value=str(patient[2]) if patient[2] else "", keyboard_type=ft.KeyboardType.NUMBER)
        gender_dropdown = ft.Dropdown(
            label="Gender",
            width=300,
            value=patient[3],
            options=[
                ft.dropdown.Option("Male"),
                ft.dropdown.Option("Female"),
                ft.dropdown.Option("Other")
            ]
        )
        phone_field = ft.TextField(label="Phone", width=300, value=patient[4])
        address_field = ft.TextField(label="Address", width=300, value=patient[5])
        
        def update_patient(e):
            if not name_field.value:
                self.show_snack_bar("Please enter patient name", ft.colors.RED_500)
                return
            
            self.db.update_patient(
                patient[0],
                name_field.value,
                age_field.value,
                gender_dropdown.value,
                phone_field.value,
                address_field.value
            )
            
            self.update_patients_list()
            dialog.open = False
            self.page.update()
            self.show_snack_bar("Patient updated successfully", ft.colors.GREEN_500)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Edit Patient"),
            content=ft.Column([
                name_field,
                age_field,
                gender_dropdown,
                phone_field,
                address_field
            ], scroll=ft.ScrollMode.AUTO, tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Update", on_click=update_patient)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def show_patient_details(self, patient):
        """Show patient details including medical history"""
        medical_history = self.db.get_medical_history(patient[0])
        
        # Create medical history list
        history_list = []
        if medical_history:
            for history in medical_history:
                history_list.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column([
                                ft.Text(f"Recorded: {history[5]}", size=12, color=ft.colors.GREY_600),
                                ft.Text(f"Allergies: {history[2] or 'None'}"),
                                ft.Text(f"Chronic Diseases: {history[3] or 'None'}"),
                                ft.Text(f"Notes: {history[4] or 'None'}")
                            ]),
                            padding=10
                        ),
                        elevation=2
                    )
                )
        else:
            history_list.append(
                ft.Text("No medical history records", color=ft.colors.GREY_600)
            )
        
        # Add medical history button
        add_history_button = ft.ElevatedButton(
            text="Add Medical History",
            icon=ft.icons.ADD,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=self.primary_color
            ),
            on_click=lambda e: self.show_add_medical_history_dialog(patient[0])
        )
        
        dialog = ft.AlertDialog(
            title=ft.Text(f"Patient Details: {patient[1]}"),
            content=ft.Column([
                ft.Text(f"Age: {patient[2] or 'Not specified'}"),
                ft.Text(f"Gender: {patient[3] or 'Not specified'}"),
                ft.Text(f"Phone: {patient[4] or 'Not specified'}"),
                ft.Text(f"Address: {patient[5] or 'Not specified'}"),
                ft.Divider(),
                ft.Text("Medical History", weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.Column(history_list, spacing=5),
                    height=200,
                    padding=10
                ),
                add_history_button
            ], scroll=ft.ScrollMode.AUTO, tight=True, height=400),
            actions=[
                ft.TextButton("Close", on_click=lambda e: self.close_dialog(dialog))
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def show_add_medical_history_dialog(self, patient_id):
        """Show dialog to add medical history"""
        allergies_field = ft.TextField(label="Allergies", width=300)
        diseases_field = ft.TextField(label="Chronic Diseases", width=300)
        notes_field = ft.TextField(label="Notes", width=300, multiline=True)
        
        def save_history(e):
            self.db.add_medical_history(
                patient_id,
                allergies_field.value,
                diseases_field.value,
                notes_field.value
            )
            
            dialog.open = False
            self.page.update()
            self.show_snack_bar("Medical history added successfully", ft.colors.GREEN_500)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Add Medical History"),
            content=ft.Column([
                allergies_field,
                diseases_field,
                notes_field
            ], scroll=ft.ScrollMode.AUTO, tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Save", on_click=save_history)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def delete_patient(self, patient):
        """Delete a patient"""
        def confirm_delete(e):
            self.db.delete_patient(patient[0])
            self.update_patients_list()
            dialog.open = False
            self.page.update()
            self.show_snack_bar("Patient deleted successfully", ft.colors.GREEN_500)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete {patient[1]}? This will also delete all related records."),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Delete", on_click=confirm_delete, bgcolor=ft.colors.RED_500, color=ft.colors.WHITE)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def show_appointments(self):
        """Show appointments view"""
        # Search field
        search_field = ft.TextField(
            label="Search appointments",
            width=300,
            prefix_icon=ft.icons.SEARCH,
            on_change=lambda e: self.update_appointments_list(search_term=search_field.value)
        )
        
        # Date filter
        date_field = ft.TextField(
            label="Filter by date (YYYY-MM-DD)",
            width=300,
            prefix_icon=ft.icons.CALENDAR_TODAY,
            on_change=lambda e: self.update_appointments_list(date_filter=date_field.value)
        )
        
        # Add appointment button
        add_appointment_button = ft.ElevatedButton(
            text="Add New Appointment",
            icon=ft.icons.ADD,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=self.primary_color
            ),
            on_click=self.show_add_appointment_dialog
        )
        
        # Appointments list
        self.appointments_list = ft.Column([], spacing=5, scroll=ft.ScrollMode.AUTO)
        
        # Initial load
        self.update_appointments_list()
        
        self.content_area.content = ft.Column([
            ft.Row([
                ft.Text("Appointments", size=24, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                add_appointment_button
            ]),
            ft.Divider(height=10, color="transparent"),
            search_field,
            date_field,
            ft.Divider(height=10, color="transparent"),
            ft.Container(
                content=self.appointments_list,
                border_radius=10,
                bgcolor=self.card_color,
                padding=10,
                height=500,
                shadow=ft.BoxShadow(blur_radius=5, spread_radius=1, color=ft.colors.BLUE_GREY_100)
            )
        ], scroll=ft.ScrollMode.AUTO)
        
        self.page.update()
    
    def update_appointments_list(self, date_filter=None, search_term=""):
        """Update the appointments list"""
        appointments = self.db.get_appointments(date_filter, search_term)
        
        self.appointments_list.controls = []
        
        if appointments:
            for apt in appointments:
                status_color = ft.colors.GREEN_500 if apt[7] == "completed" else ft.colors.ORANGE_500
                
                appointment_card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.ListTile(
                                leading=ft.Icon(ft.icons.CALENDAR_MONTH),
                                title=ft.Text(f"{apt[8]} with Dr. {apt[9]}", weight=ft.FontWeight.BOLD),
                                subtitle=ft.Text(f"{apt[4]} at {apt[5]}"),
                                trailing=ft.Row([
                                    ft.Container(
                                        content=ft.Text(apt[7].capitalize(), size=12, color=ft.colors.WHITE),
                                        bgcolor=status_color,
                                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                        border_radius=10
                                    ),
                                    ft.PopupMenuButton(
                                        icon=ft.icons.MORE_VERT,
                                        items=[
                                            ft.PopupMenuItem(
                                                text="Edit",
                                                icon=ft.icons.EDIT,
                                                on_click=lambda e, a=apt: self.show_edit_appointment_dialog(a)
                                            ),
                                            ft.PopupMenuItem(
                                                text="Mark Complete",
                                                icon=ft.icons.CHECK,
                                                on_click=lambda e, a=apt: self.complete_appointment(a)
                                            ),
                                            ft.PopupMenuItem(
                                                text="Delete",
                                                icon=ft.icons.DELETE,
                                                on_click=lambda e, a=apt: self.delete_appointment(a)
                                            ),
                                        ]
                                    )
                                ])
                            ),
                        ]),
                        padding=10
                    ),
                    elevation=2
                )
                self.appointments_list.controls.append(appointment_card)
        else:
            self.appointments_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.SEARCH_OFF, size=50, color=ft.colors.GREY_400),
                        ft.Text("No appointments found", size=16, color=ft.colors.GREY_600)
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
        
        self.page.update()
    
    def show_add_appointment_dialog(self, e):
        """Show dialog to add a new appointment"""
        # Get patients and doctors for dropdowns
        patients = self.db.get_patients()
        doctors = self.db.get_doctors()
        
        patient_dropdown = ft.Dropdown(
            label="Patient",
            width=300,
            options=[ft.dropdown.Option(p[1], key=str(p[0])) for p in patients]
        )
        
        doctor_dropdown = ft.Dropdown(
            label="Doctor",
            width=300,
            options=[ft.dropdown.Option(d[1], key=str(d[0])) for d in doctors]
        )
        
        date_field = ft.TextField(
            label="Date (YYYY-MM-DD)",
            width=300,
            value=date.today().strftime("%Y-%m-%d")
        )
        
        time_field = ft.TextField(
            label="Time (HH:MM)",
            width=300,
            value="09:00"
        )
        
        notes_field = ft.TextField(label="Notes", width=300, multiline=True)
        
        def save_appointment(e):
            if not patient_dropdown.value or not doctor_dropdown.value:
                self.show_snack_bar("Please select patient and doctor", ft.colors.RED_500)
                return
            
            self.db.add_appointment(
                int(patient_dropdown.value),
                int(doctor_dropdown.value),
                date_field.value,
                time_field.value,
                notes_field.value
            )
            
            self.update_appointments_list()
            dialog.open = False
            self.page.update()
            self.show_snack_bar("Appointment added successfully", ft.colors.GREEN_500)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Add New Appointment"),
            content=ft.Column([
                patient_dropdown,
                doctor_dropdown,
                date_field,
                time_field,
                notes_field
            ], scroll=ft.ScrollMode.AUTO, tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Save", on_click=save_appointment)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def show_edit_appointment_dialog(self, appointment):
        """Show dialog to edit an appointment"""
        # Get patients and doctors for dropdowns
        patients = self.db.get_patients()
        doctors = self.db.get_doctors()
        
        patient_dropdown = ft.Dropdown(
            label="Patient",
            width=300,
            value=str(appointment[1]),
            options=[ft.dropdown.Option(p[1], key=str(p[0])) for p in patients]
        )
        
        doctor_dropdown = ft.Dropdown(
            label="Doctor",
            width=300,
            value=str(appointment[2]),
            options=[ft.dropdown.Option(d[1], key=str(d[0])) for d in doctors]
        )
        
        date_field = ft.TextField(
            label="Date (YYYY-MM-DD)",
            width=300,
            value=appointment[4]
        )
        
        time_field = ft.TextField(
            label="Time (HH:MM)",
            width=300,
            value=appointment[5]
        )
        
        notes_field = ft.TextField(label="Notes", width=300, value=appointment[6], multiline=True)
        
        status_dropdown = ft.Dropdown(
            label="Status",
            width=300,
            value=appointment[7],
            options=[
                ft.dropdown.Option("scheduled"),
                ft.dropdown.Option("completed"),
                ft.dropdown.Option("cancelled")
            ]
        )
        
        def update_appointment(e):
            if not patient_dropdown.value or not doctor_dropdown.value:
                self.show_snack_bar("Please select patient and doctor", ft.colors.RED_500)
                return
            
            self.db.update_appointment(
                appointment[0],
                int(patient_dropdown.value),
                int(doctor_dropdown.value),
                date_field.value,
                time_field.value,
                notes_field.value,
                status_dropdown.value
            )
            
            self.update_appointments_list()
            dialog.open = False
            self.page.update()
            self.show_snack_bar("Appointment updated successfully", ft.colors.GREEN_500)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Edit Appointment"),
            content=ft.Column([
                patient_dropdown,
                doctor_dropdown,
                date_field,
                time_field,
                notes_field,
                status_dropdown
            ], scroll=ft.ScrollMode.AUTO, tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Update", on_click=update_appointment)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def complete_appointment(self, appointment):
        """Mark an appointment as completed"""
        self.db.update_appointment(
            appointment[0],
            appointment[1],
            appointment[2],
            appointment[4],
            appointment[5],
            appointment[6],
            "completed"
        )
        self.update_appointments_list()
        self.show_snack_bar("Appointment marked as completed", ft.colors.GREEN_500)
    
    def delete_appointment(self, appointment):
        """Delete an appointment"""
        def confirm_delete(e):
            self.db.delete_appointment(appointment[0])
            self.update_appointments_list()
            dialog.open = False
            self.page.update()
            self.show_snack_bar("Appointment deleted successfully", ft.colors.GREEN_500)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete this appointment?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Delete", on_click=confirm_delete, bgcolor=ft.colors.RED_500, color=ft.colors.WHITE)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def show_doctors(self):
        """Show doctors view"""
        # Search field
        search_field = ft.TextField(
            label="Search doctors",
            width=300,
            prefix_icon=ft.icons.SEARCH,
            on_change=lambda e: self.update_doctors_list(search_field.value)
        )
        
        # Add doctor button
        add_doctor_button = ft.ElevatedButton(
            text="Add New Doctor",
            icon=ft.icons.ADD,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=self.primary_color
            ),
            on_click=self.show_add_doctor_dialog
        )
        
        # Doctors list
        self.doctors_list = ft.Column([], spacing=5, scroll=ft.ScrollMode.AUTO)
        
        # Initial load
        self.update_doctors_list()
        
        self.content_area.content = ft.Column([
            ft.Row([
                ft.Text("Doctors", size=24, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                add_doctor_button
            ]),
            ft.Divider(height=10, color="transparent"),
            search_field,
            ft.Divider(height=10, color="transparent"),
            ft.Container(
                content=self.doctors_list,
                border_radius=10,
                bgcolor=self.card_color,
                padding=10,
                height=500,
                shadow=ft.BoxShadow(blur_radius=5, spread_radius=1, color=ft.colors.BLUE_GREY_100)
            )
        ], scroll=ft.ScrollMode.AUTO)
        
        self.page.update()
    
    def update_doctors_list(self, search_term=""):
        """Update the doctors list"""
        doctors = self.db.get_doctors(search_term)
        
        self.doctors_list.controls = []
        
        if doctors:
            for doctor in doctors:
                doctor_card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.ListTile(
                                leading=ft.Icon(ft.icons.LOCAL_HOSPITAL),
                                title=ft.Text(doctor[1], weight=ft.FontWeight.BOLD),
                                subtitle=ft.Text(f"{doctor[2]}, Phone: {doctor[3]}, Email: {doctor[4]}"),
                                trailing=ft.PopupMenuButton(
                                    icon=ft.icons.MORE_VERT,
                                    items=[
                                        ft.PopupMenuItem(
                                            text="Edit",
                                            icon=ft.icons.EDIT,
                                            on_click=lambda e, d=doctor: self.show_edit_doctor_dialog(d)
                                        ),
                                        ft.PopupMenuItem(
                                            text="Delete",
                                            icon=ft.icons.DELETE,
                                            on_click=lambda e, d=doctor: self.delete_doctor(d)
                                        ),
                                    ]
                                )
                            ),
                        ]),
                        padding=10
                    ),
                    elevation=2
                )
                self.doctors_list.controls.append(doctor_card)
        else:
            self.doctors_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.SEARCH_OFF, size=50, color=ft.colors.GREY_400),
                        ft.Text("No doctors found", size=16, color=ft.colors.GREY_600)
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
        
        self.page.update()
    
    def show_add_doctor_dialog(self, e):
        """Show dialog to add a new doctor"""
        name_field = ft.TextField(label="Name", width=300)
        specialty_field = ft.TextField(label="Specialty", width=300)
        phone_field = ft.TextField(label="Phone", width=300)
        email_field = ft.TextField(label="Email", width=300)
        
        def save_doctor(e):
            if not name_field.value:
                self.show_snack_bar("Please enter doctor name", ft.colors.RED_500)
                return
            
            self.db.add_doctor(
                name_field.value,
                specialty_field.value,
                phone_field.value,
                email_field.value
            )
            
            self.update_doctors_list()
            dialog.open = False
            self.page.update()
            self.show_snack_bar("Doctor added successfully", ft.colors.GREEN_500)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Add New Doctor"),
            content=ft.Column([
                name_field,
                specialty_field,
                phone_field,
                email_field
            ], scroll=ft.ScrollMode.AUTO, tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Save", on_click=save_doctor)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def show_edit_doctor_dialog(self, doctor):
        """Show dialog to edit a doctor"""
        name_field = ft.TextField(label="Name", width=300, value=doctor[1])
        specialty_field = ft.TextField(label="Specialty", width=300, value=doctor[2])
        phone_field = ft.TextField(label="Phone", width=300, value=doctor[3])
        email_field = ft.TextField(label="Email", width=300, value=doctor[4])
        
        def update_doctor(e):
            if not name_field.value:
                self.show_snack_bar("Please enter doctor name", ft.colors.RED_500)
                return
            
            self.db.update_doctor(
                doctor[0],
                name_field.value,
                specialty_field.value,
                phone_field.value,
                email_field.value
            )
            
            self.update_doctors_list()
            dialog.open = False
            self.page.update()
            self.show_snack_bar("Doctor updated successfully", ft.colors.GREEN_500)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Edit Doctor"),
            content=ft.Column([
                name_field,
                specialty_field,
                phone_field,
                email_field
            ], scroll=ft.ScrollMode.AUTO, tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Update", on_click=update_doctor)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def delete_doctor(self, doctor):
        """Delete a doctor"""
        def confirm_delete(e):
            self.db.delete_doctor(doctor[0])
            self.update_doctors_list()
            dialog.open = False
            self.page.update()
            self.show_snack_bar("Doctor deleted successfully", ft.colors.GREEN_500)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete Dr. {doctor[1]}?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Delete", on_click=confirm_delete, bgcolor=ft.colors.RED_500, color=ft.colors.WHITE)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def show_invoices(self):
        """Show invoices view"""
        # Search field
        search_field = ft.TextField(
            label="Search invoices",
            width=300,
            prefix_icon=ft.icons.SEARCH,
            on_change=lambda e: self.update_invoices_list(search_field.value)
        )
        
        # Add invoice button
        add_invoice_button = ft.ElevatedButton(
            text="Add New Invoice",
            icon=ft.icons.ADD,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=self.primary_color
            ),
            on_click=self.show_add_invoice_dialog
        )
        
        # Invoices list
        self.invoices_list = ft.Column([], spacing=5, scroll=ft.ScrollMode.AUTO)
        
        # Initial load
        self.update_invoices_list()
        
        self.content_area.content = ft.Column([
            ft.Row([
                ft.Text("Invoices & Payments", size=24, weight=ft.FontWeight.BOLD),
                ft.Container(expand=True),
                add_invoice_button
            ]),
            ft.Divider(height=10, color="transparent"),
            search_field,
            ft.Divider(height=10, color="transparent"),
            ft.Container(
                content=self.invoices_list,
                border_radius=10,
                bgcolor=self.card_color,
                padding=10,
                height=500,
                shadow=ft.BoxShadow(blur_radius=5, spread_radius=1, color=ft.colors.BLUE_GREY_100)
            )
        ], scroll=ft.ScrollMode.AUTO)
        
        self.page.update()
    
    def update_invoices_list(self, search_term=""):
        """Update the invoices list"""
        invoices = self.db.get_invoices(search_term)
        
        self.invoices_list.controls = []
        
        if invoices:
            for invoice in invoices:
                balance_color = ft.colors.RED_500 if invoice[6] > 0 else ft.colors.GREEN_500
                
                invoice_card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.ListTile(
                                leading=ft.Icon(ft.icons.RECEIPT),
                                title=ft.Text(f"{invoice[7]}", weight=ft.FontWeight.BOLD),
                                subtitle=ft.Text(f"Service: {invoice[3]}, Date: {invoice[6][:10]}"),
                                trailing=ft.Row([
                                    ft.Column([
                                        ft.Text(f"Total: ${invoice[4]:.2f}", size=12),
                                        ft.Text(f"Paid: ${invoice[5]:.2f}", size=12),
                                        ft.Text(f"Balance: ${invoice[6]:.2f}", size=12, color=balance_color)
                                    ]),
                                    ft.PopupMenuButton(
                                        icon=ft.icons.MORE_VERT,
                                        items=[
                                            ft.PopupMenuItem(
                                                text="Edit",
                                                icon=ft.icons.EDIT,
                                                on_click=lambda e, i=invoice: self.show_edit_invoice_dialog(i)
                                            ),
                                            ft.PopupMenuItem(
                                                text="Delete",
                                                icon=ft.icons.DELETE,
                                                on_click=lambda e, i=invoice: self.delete_invoice(i)
                                            ),
                                        ]
                                    )
                                ])
                            ),
                        ]),
                        padding=10
                    ),
                    elevation=2
                )
                self.invoices_list.controls.append(invoice_card)
        else:
            self.invoices_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.SEARCH_OFF, size=50, color=ft.colors.GREY_400),
                        ft.Text("No invoices found", size=16, color=ft.colors.GREY_600)
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
        
        self.page.update()
    
    def show_add_invoice_dialog(self, e):
        """Show dialog to add a new invoice"""
        # Get patients for dropdown
        patients = self.db.get_patients()
        
        patient_dropdown = ft.Dropdown(
            label="Patient",
            width=300,
            options=[ft.dropdown.Option(p[1], key=str(p[0])) for p in patients]
        )
        
        service_field = ft.TextField(label="Service Provided", width=300)
        total_field = ft.TextField(label="Total Cost", width=300, keyboard_type=ft.KeyboardType.NUMBER)
        paid_field = ft.TextField(label="Amount Paid", width=300, keyboard_type=ft.KeyboardType.NUMBER)
        
        def save_invoice(e):
            if not patient_dropdown.value or not service_field.value or not total_field.value:
                self.show_snack_bar("Please fill all required fields", ft.colors.RED_500)
                return
            
            try:
                total = float(total_field.value)
                paid = float(paid_field.value) if paid_field.value else 0
            except ValueError:
                self.show_snack_bar("Please enter valid numbers", ft.colors.RED_500)
                return
            
            self.db.add_invoice(
                int(patient_dropdown.value),
                service_field.value,
                total,
                paid
            )
            
            self.update_invoices_list()
            dialog.open = False
            self.page.update()
            self.show_snack_bar("Invoice added successfully", ft.colors.GREEN_500)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Add New Invoice"),
            content=ft.Column([
                patient_dropdown,
                service_field,
                total_field,
                paid_field
            ], scroll=ft.ScrollMode.AUTO, tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Save", on_click=save_invoice)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def show_edit_invoice_dialog(self, invoice):
        """Show dialog to edit an invoice"""
        # Get patients for dropdown
        patients = self.db.get_patients()
        
        patient_dropdown = ft.Dropdown(
            label="Patient",
            width=300,
            value=str(invoice[1]),
            options=[ft.dropdown.Option(p[1], key=str(p[0])) for p in patients]
        )
        
        service_field = ft.TextField(label="Service Provided", width=300, value=invoice[3])
        total_field = ft.TextField(label="Total Cost", width=300, value=str(invoice[4]), keyboard_type=ft.KeyboardType.NUMBER)
        paid_field = ft.TextField(label="Amount Paid", width=300, value=str(invoice[5]), keyboard_type=ft.KeyboardType.NUMBER)
        
        def update_invoice(e):
            if not patient_dropdown.value or not service_field.value or not total_field.value:
                self.show_snack_bar("Please fill all required fields", ft.colors.RED_500)
                return
            
            try:
                total = float(total_field.value)
                paid = float(paid_field.value) if paid_field.value else 0
            except ValueError:
                self.show_snack_bar("Please enter valid numbers", ft.colors.RED_500)
                return
            
            self.db.update_invoice(
                invoice[0],
                int(patient_dropdown.value),
                service_field.value,
                total,
                paid
            )
            
            self.update_invoices_list()
            dialog.open = False
            self.page.update()
            self.show_snack_bar("Invoice updated successfully", ft.colors.GREEN_500)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Edit Invoice"),
            content=ft.Column([
                patient_dropdown,
                service_field,
                total_field,
                paid_field
            ], scroll=ft.ScrollMode.AUTO, tight=True),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Update", on_click=update_invoice)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def delete_invoice(self, invoice):
        """Delete an invoice"""
        def confirm_delete(e):
            self.db.delete_invoice(invoice[0])
            self.update_invoices_list()
            dialog.open = False
            self.page.update()
            self.show_snack_bar("Invoice deleted successfully", ft.colors.GREEN_500)
        
        dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Are you sure you want to delete this invoice?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.close_dialog(dialog)),
                ft.ElevatedButton("Delete", on_click=confirm_delete, bgcolor=ft.colors.RED_500, color=ft.colors.WHITE)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def show_settings(self):
        """Show settings view"""
        # User credentials section
        username_field = ft.TextField(
            label="Username",
            width=300,
            value=self.current_user
        )
        
        password_field = ft.TextField(
            label="New Password",
            width=300,
            password=True,
            can_reveal_password=True
        )
        
        def update_credentials(e):
            if not password_field.value:
                self.show_snack_bar("Please enter a new password", ft.colors.RED_500)
                return
            
            self.db.update_user_credentials(username_field.value, password_field.value)
            self.show_snack_bar("Credentials updated successfully", ft.colors.GREEN_500)
        
        # Language section
        language_dropdown = ft.Dropdown(
            label="Language",
            width=300,
            value=self.language,
            options=[
                ft.dropdown.Option("English"),
                ft.dropdown.Option("Arabic")
            ],
            on_change=lambda e: self.update_language(e.control.value)
        )
        
        # Dark mode toggle
        dark_mode_switch = ft.Switch(
            label="Dark Mode",
            value=self.dark_mode,
            on_change=lambda e: self.toggle_dark_mode(e.control.value)
        )
        
        # Backup/Restore section
        def export_db(e):
            # In a real app, you would use file picker to select location
            # For this demo, we'll use a fixed path
            export_path = "dental_clinic_backup.db"
            if self.db.export_db(export_path):
                self.show_snack_bar(f"Database exported to {export_path}", ft.colors.GREEN_500)
            else:
                self.show_snack_bar("Failed to export database", ft.colors.RED_500)
        
        def import_db(e):
            # In a real app, you would use file picker to select file
            # For this demo, we'll use a fixed path
            import_path = "dental_clinic_backup.db"
            if os.path.exists(import_path) and self.db.import_db(import_path):
                self.show_snack_bar("Database imported successfully", ft.colors.GREEN_500)
                # Refresh all views
                self.update_patients_list()
                self.update_appointments_list()
                self.update_doctors_list()
                self.update_invoices_list()
            else:
                self.show_snack_bar("Failed to import database", ft.colors.RED_500)
        
        # Logout button
        logout_button = ft.ElevatedButton(
            text="Logout",
            icon=ft.icons.LOGOUT,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.RED_500
            ),
            on_click=self.logout
        )
        
        self.content_area.content = ft.Column([
            ft.Text("Settings", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(height=20, color="transparent"),
            ft.Text("User Credentials", size=18, weight=ft.FontWeight.BOLD),
            username_field,
            password_field,
            ft.ElevatedButton(
                text="Update Credentials",
                on_click=update_credentials,
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=self.primary_color
                )
            ),
            ft.Divider(height=20, color="transparent"),
            ft.Text("App Settings", size=18, weight=ft.FontWeight.BOLD),
            language_dropdown,
            dark_mode_switch,
            ft.Divider(height=20, color="transparent"),
            ft.Text("Data Management", size=18, weight=ft.FontWeight.BOLD),
            ft.ElevatedButton(
                text="Export Database",
                icon=ft.icons.DOWNLOAD,
                on_click=export_db,
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=ft.colors.GREEN_500
                )
            ),
            ft.ElevatedButton(
                text="Import Database",
                icon=ft.icons.UPLOAD,
                on_click=import_db,
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=ft.colors.ORANGE_500
                )
            ),
            ft.Divider(height=20, color="transparent"),
            logout_button
        ], scroll=ft.ScrollMode.AUTO)
        
        self.page.update()
    
    def update_language(self, language):
        """Update app language"""
        self.language = language
        self.db.update_setting("language", language)
        self.show_snack_bar(f"Language changed to {language}", ft.colors.GREEN_500)
        # In a real app, you would update all UI text based on language
    
    def toggle_dark_mode(self, is_dark):
        """Toggle dark mode"""
        self.dark_mode = is_dark
        self.db.update_setting("dark_mode", str(is_dark))
        self.apply_theme()
        self.show_snack_bar(f"Dark mode {'enabled' if is_dark else 'disabled'}", ft.colors.GREEN_500)
    
    def close_dialog(self, dialog):
        """Close a dialog"""
        dialog.open = False
        self.page.update()
    
    def show_snack_bar(self, message, color):
        """Show a snack bar notification"""
        snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=color
        )
        self.page.snack_bar = snack_bar
        snack_bar.open = True
        self.page.update()

# Main function to run the app
def main(page: ft.Page):
    app = DentalClinicApp(page)

# Run the app
if __name__ == "__main__":
    ft.app(target=main)