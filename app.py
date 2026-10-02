from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify, send_file
from flask_mail import Mail, Message
from functools import wraps
from datetime import datetime, timedelta
from io import BytesIO
from collections import defaultdict
import secrets
import os
import json
import pandas as pd
import numpy as np
import plotly
import plotly.graph_objs as go
import random
from datetime import datetime, timedelta


# -------------------------------------------------------------------
# ReportLab for PDF generation
# -------------------------------------------------------------------
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Warning: reportlab not installed. PDF generation disabled.")
# -------------------------------------------------------------------
# Flask app configuration
# -------------------------------------------------------------------
app = Flask(__name__, static_folder='frontend/static', template_folder='frontend/templates')
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Session configuration
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'your-email@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your-app-password')
app.config['MAIL_DEFAULT_SENDER'] = ('MedPredict Support', app.config['MAIL_USERNAME'])
app.config['MAIL_SUPPRESS_SEND'] = True

mail = Mail(app)

# -------------------------------------------------------------------
# Mock databases (in‑memory)
# -------------------------------------------------------------------
users_db = {
    'admin': {
        'id': 1,
        'password': 'admin123',
        'name': 'System Admin',
        'email': 'admin@medpredict.com',
        'role': 'admin',
        'created_at': datetime.now().strftime('%Y-%m-%d')
    },
    'doctor': {
        'id': 2,
        'password': 'pass123',
        'name': 'Dr. Smith',
        'email': 'doctor@example.com',
        'role': 'doctor',
        'created_at': datetime.now().strftime('%Y-%m-%d')
    },
    'patient': {
        'id': 3,
        'password': 'patient123',
        'name': 'John Doe',
        'email': 'patient@example.com',
        'role': 'patient',
        'created_at': datetime.now().strftime('%Y-%m-%d')
    }
}
next_user_id = 4

patients_db = {}
predictions_db = {}
next_patient_id = 1
next_prediction_id = 1

appointments_db = {}
next_appointment_id = 1

cancellation_counts_by_email = {}
CANCELLATION_LIMIT = 3

# -------------------------------------------------------------------
# File persistence for users_db
# -------------------------------------------------------------------
USERS_FILE = 'users.json'

def load_users_from_file():
    global users_db, next_user_id
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                data = json.load(f)
                users_db = data.get('users_db', users_db)
                next_user_id = data.get('next_user_id', next_user_id)
        except Exception as e:
            print(f"Error loading users: {e}")

def save_users_to_file():
    global users_db, next_user_id
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump({'users_db': users_db, 'next_user_id': next_user_id}, f, indent=2)
    except Exception as e:
        print(f"Error saving users: {e}")

load_users_from_file()

# -------------------------------------------------------------------
# Reset doctors to exactly 15
# -------------------------------------------------------------------
def reset_doctors_to_15():
    global users_db, next_user_id
    doctors = [
        {"username": "dr_john_smith", "name": "Dr. John Smith", "email": "john.smith@medpredict.com"},
        {"username": "dr_emily_johnson", "name": "Dr. Emily Johnson", "email": "emily.johnson@medpredict.com"},
        {"username": "dr_michael_williams", "name": "Dr. Michael Williams", "email": "michael.williams@medpredict.com"},
        {"username": "dr_sarah_brown", "name": "Dr. Sarah Brown", "email": "sarah.brown@medpredict.com"},
        {"username": "dr_david_jones", "name": "Dr. David Jones", "email": "david.jones@medpredict.com"},
        {"username": "dr_lisa_garcia", "name": "Dr. Lisa Garcia", "email": "lisa.garcia@medpredict.com"},
        {"username": "dr_james_miller", "name": "Dr. James Miller", "email": "james.miller@medpredict.com"},
        {"username": "dr_patricia_davis", "name": "Dr. Patricia Davis", "email": "patricia.davis@medpredict.com"},
        {"username": "dr_robert_rodriguez", "name": "Dr. Robert Rodriguez", "email": "robert.rodriguez@medpredict.com"},
        {"username": "dr_jennifer_martinez", "name": "Dr. Jennifer Martinez", "email": "jennifer.martinez@medpredict.com"},
        {"username": "dr_christopher_anderson", "name": "Dr. Christopher Anderson", "email": "christopher.anderson@medpredict.com"},
        {"username": "dr_ashley_thomas", "name": "Dr. Ashley Thomas", "email": "ashley.thomas@medpredict.com"},
        {"username": "dr_matthew_jackson", "name": "Dr. Matthew Jackson", "email": "matthew.jackson@medpredict.com"},
        {"username": "dr_amanda_white", "name": "Dr. Amanda White", "email": "amanda.white@medpredict.com"},
        {"username": "dr_joshua_harris", "name": "Dr. Joshua Harris", "email": "joshua.harris@medpredict.com"},
    ]
    to_delete = [username for username, data in users_db.items() if data.get('role') == 'doctor']
    for username in to_delete:
        del users_db[username]
    for doc in doctors:
        users_db[doc['username']] = {
            'id': next_user_id,
            'password': 'doctor123',
            'name': doc['name'],
            'email': doc['email'],
            'role': 'doctor',
            'created_at': datetime.now().strftime('%Y-%m-%d')
        }
        next_user_id += 1
    save_users_to_file()
    print(f"✅ Reset doctors to exactly {len(doctors)} accounts.")

reset_doctors_to_15()

# ===================================================================
# Add 7 specific patient users with credentials
# ===================================================================
def add_seven_patients():
    global users_db, patients_db, next_user_id, next_patient_id
    seven_patients = [
        {"username": "patient_john_doe", "name": "John Doe", "email": "john.doe@example.com", "phone": "555-1001"},
        {"username": "patient_jane_smith", "name": "Jane Smith", "email": "jane.smith@example.com", "phone": "555-1002"},
        {"username": "patient_robert_johnson", "name": "Robert Johnson", "email": "robert.johnson@example.com", "phone": "555-1003"},
        {"username": "patient_maria_garcia", "name": "Maria Garcia", "email": "maria.garcia@example.com", "phone": "555-1004"},
        {"username": "patient_james_brown", "name": "James Brown", "email": "james.brown@example.com", "phone": "555-1005"},
        {"username": "patient_linda_davis", "name": "Linda Davis", "email": "linda.davis@example.com", "phone": "555-1006"},
        {"username": "patient_michael_miller", "name": "Michael Miller", "email": "michael.miller@example.com", "phone": "555-1007"},
    ]

    for p in seven_patients:
        if p["username"] not in users_db:
            users_db[p["username"]] = {
                'id': next_user_id,
                'password': 'patient123',
                'name': p["name"],
                'email': p["email"],
                'role': 'patient',
                'created_at': datetime.now().strftime('%Y-%m-%d')
            }
            patients_db[next_patient_id] = {
                'id': next_patient_id,
                'name': p["name"],
                'age': random.randint(30, 75),
                'gender': random.choice(['M', 'F']),
                'phone': p["phone"],
                'email': p["email"],
                'address': '123 Main St, Anytown',
                'medical_history': random.choice(['None', 'Hypertension', 'Diabetes Type 2', 'Hyperlipidemia']),
                'smoking_status': random.choice(['Never', 'Former', 'Current']),
                'bmi': round(random.uniform(18.5, 35.0), 1),
                'user_id': next_user_id,
                'last_prediction_date': None
            }
            next_patient_id += 1
            next_user_id += 1
        else:
            print(f"⚠️ Username {p['username']} already exists – skipping.")

    save_users_to_file()
    print("✅ Added 7 specific patient users with credentials (password: patient123).")

add_seven_patients()

# -------------------------------------------------------------------
# Context processors
# -------------------------------------------------------------------
class FakeUser:
    def __init__(self, is_authenticated=False, name='', email='', role=''):
        self.is_authenticated = is_authenticated
        self.name = name
        self.email = email
        self.role = role

@app.context_processor
def inject_current_user():
    if 'user_id' in session:
        username = session.get('username')
        user_data = users_db.get(username) if username else None
        if user_data:
            user = FakeUser(
                is_authenticated=True,
                name=user_data.get('name', username),
                email=user_data.get('email', ''),
                role=user_data.get('role', 'patient')
            )
        else:
            user = FakeUser(
                is_authenticated=True,
                name=session.get('user_name', 'User'),
                email=session.get('email', ''),
                role=session.get('role', 'patient')
            )
    else:
        user = FakeUser(is_authenticated=False)
    return dict(current_user=user)
@app.context_processor
def inject_datetime():
    return {'datetime': datetime}

@app.context_processor
def inject_available_roles():
    return {'available_roles': {'admin': 'admin', 'doctor': 'doctor', 'patient': 'patient'}}

# -------------------------------------------------------------------
# Built‑in data: 50 patients & predictions
# -------------------------------------------------------------------
def load_builtin_data():
    global patients_db, predictions_db, next_patient_id, next_prediction_id

    patients_db.update({
        1: {'id': 1, 'name': 'Margaret Hensley', 'age': 50, 'gender': 'F', 'phone': '555-0101', 'email': 'margaret@example.com', 'medical_history': 'Hypertension', 'smoking_status': 'Never', 'bmi': 22.5},
        2: {'id': 2, 'name': 'Robert Chen', 'age': 62, 'gender': 'M', 'phone': '555-0102', 'email': 'robert@example.com', 'medical_history': 'Diabetes Type 2', 'smoking_status': 'Former', 'bmi': 29.8},
        3: {'id': 3, 'name': 'Susan Park', 'age': 45, 'gender': 'F', 'phone': '555-0103', 'email': 'susan@example.com', 'medical_history': 'None', 'smoking_status': 'Current', 'bmi': 34.2},
        4: {'id': 4, 'name': 'James Wilson', 'age': 70, 'gender': 'M', 'phone': '555-0104', 'email': 'james@example.com', 'medical_history': 'Atrial Fibrillation', 'smoking_status': 'Former', 'bmi': 26.0},
        5: {'id': 5, 'name': 'Linda Martinez', 'age': 38, 'gender': 'F', 'phone': '555-0105', 'email': 'linda@example.com', 'medical_history': 'None', 'smoking_status': 'Never', 'bmi': 19.5},
        6: {'id': 6, 'name': 'David Kim', 'age': 55, 'gender': 'M', 'phone': '555-0106', 'email': 'david@example.com', 'medical_history': 'Hyperlipidemia', 'smoking_status': 'Current', 'bmi': 31.0},
        7: {'id': 7, 'name': 'Patricia Garcia', 'age': 67, 'gender': 'F', 'phone': '555-0107', 'email': 'patricia@example.com', 'medical_history': 'CAD', 'smoking_status': 'Former', 'bmi': 24.3},
        8: {'id': 8, 'name': 'Michael Johnson', 'age': 48, 'gender': 'M', 'phone': '555-0108', 'email': 'michael@example.com', 'medical_history': 'None', 'smoking_status': 'Never', 'bmi': 27.8},
        9: {'id': 9, 'name': 'Jennifer Lee', 'age': 33, 'gender': 'F', 'phone': '555-0109', 'email': 'jennifer@example.com', 'medical_history': 'None', 'smoking_status': 'Never', 'bmi': 21.2},
        10: {'id': 10, 'name': 'William Brown', 'age': 78, 'gender': 'M', 'phone': '555-0110', 'email': 'william@example.com', 'medical_history': 'CHF; COPD', 'smoking_status': 'Current', 'bmi': 35.6},
        11: {'id': 11, 'name': 'Barbara Taylor', 'age': 58, 'gender': 'F', 'phone': '555-0111', 'email': 'barbara@example.com', 'medical_history': 'Hypertension; Diabetes', 'smoking_status': 'Former', 'bmi': 30.1},
        12: {'id': 12, 'name': 'Richard Singh', 'age': 42, 'gender': 'M', 'phone': '555-0112', 'email': 'richard@example.com', 'medical_history': 'None', 'smoking_status': 'Never', 'bmi': 24.9},
        13: {'id': 13, 'name': 'Nancy Wilson', 'age': 64, 'gender': 'F', 'phone': '555-0113', 'email': 'nancy@example.com', 'medical_history': 'Osteoporosis', 'smoking_status': 'Never', 'bmi': 20.7},
        14: {'id': 14, 'name': 'Thomas Moore', 'age': 51, 'gender': 'M', 'phone': '555-0114', 'email': 'thomas@example.com', 'medical_history': 'Hyperlipidemia', 'smoking_status': 'Former', 'bmi': 28.3},
        15: {'id': 15, 'name': 'Deborah Rodriguez', 'age': 69, 'gender': 'F', 'phone': '555-0115', 'email': 'deborah@example.com', 'medical_history': 'Hypertension', 'smoking_status': 'Current', 'bmi': 33.7},
        16: {'id': 16, 'name': 'Charles Anderson', 'age': 47, 'gender': 'M', 'phone': '555-0116', 'email': 'charles@example.com', 'medical_history': 'None', 'smoking_status': 'Never', 'bmi': 25.3},
        17: {'id': 17, 'name': 'Sarah Thomas', 'age': 54, 'gender': 'F', 'phone': '555-0117', 'email': 'sarah@example.com', 'medical_history': 'Hyperlipidemia', 'smoking_status': 'Former', 'bmi': 27.1},
        18: {'id': 18, 'name': 'Christopher Jackson', 'age': 61, 'gender': 'M', 'phone': '555-0118', 'email': 'chris@example.com', 'medical_history': 'Diabetes Type 2', 'smoking_status': 'Current', 'bmi': 32.8},
        19: {'id': 19, 'name': 'Jessica White', 'age': 39, 'gender': 'F', 'phone': '555-0119', 'email': 'jessica@example.com', 'medical_history': 'None', 'smoking_status': 'Never', 'bmi': 22.0},
        20: {'id': 20, 'name': 'Daniel Harris', 'age': 66, 'gender': 'M', 'phone': '555-0120', 'email': 'daniel@example.com', 'medical_history': 'CAD', 'smoking_status': 'Former', 'bmi': 25.7},
        21: {'id': 21, 'name': 'Emily Martinez', 'age': 44, 'gender': 'F', 'phone': '555-0121', 'email': 'emily@example.com', 'medical_history': 'None', 'smoking_status': 'Never', 'bmi': 23.4},
        22: {'id': 22, 'name': 'Matthew Robinson', 'age': 73, 'gender': 'M', 'phone': '555-0122', 'email': 'matthew@example.com', 'medical_history': 'CHF; Hypertension', 'smoking_status': 'Current', 'bmi': 34.9},
        23: {'id': 23, 'name': 'Amanda Clark', 'age': 29, 'gender': 'F', 'phone': '555-0123', 'email': 'amanda@example.com', 'medical_history': 'None', 'smoking_status': 'Never', 'bmi': 20.1},
        24: {'id': 24, 'name': 'Andrew Lewis', 'age': 57, 'gender': 'M', 'phone': '555-0124', 'email': 'andrew@example.com', 'medical_history': 'Hyperlipidemia', 'smoking_status': 'Former', 'bmi': 28.9},
        25: {'id': 25, 'name': 'Melissa Walker', 'age': 63, 'gender': 'F', 'phone': '555-0125', 'email': 'melissa@example.com', 'medical_history': 'Diabetes Type 2', 'smoking_status': 'Never', 'bmi': 31.5},
        26: {'id': 26, 'name': 'Joshua Hall', 'age': 49, 'gender': 'M', 'phone': '555-0126', 'email': 'joshua@example.com', 'medical_history': 'None', 'smoking_status': 'Current', 'bmi': 29.2},
        27: {'id': 27, 'name': 'Laura Young', 'age': 71, 'gender': 'F', 'phone': '555-0127', 'email': 'laura@example.com', 'medical_history': 'Hypertension; CAD', 'smoking_status': 'Former', 'bmi': 23.8},
        28: {'id': 28, 'name': 'Kevin Allen', 'age': 36, 'gender': 'M', 'phone': '555-0128', 'email': 'kevin@example.com', 'medical_history': 'None', 'smoking_status': 'Never', 'bmi': 26.5},
        29: {'id': 29, 'name': 'Maria King', 'age': 59, 'gender': 'F', 'phone': '555-0129', 'email': 'maria@example.com', 'medical_history': 'Osteoporosis', 'smoking_status': 'Never', 'bmi': 22.9},
        30: {'id': 30, 'name': 'Jason Wright', 'age': 52, 'gender': 'M', 'phone': '555-0130', 'email': 'jason@example.com', 'medical_history': 'Hyperlipidemia', 'smoking_status': 'Former', 'bmi': 27.6},
        31: {'id': 31, 'name': 'Stephanie Lopez', 'age': 68, 'gender': 'F', 'phone': '555-0131', 'email': 'stephanie@example.com', 'medical_history': 'Hypertension; Diabetes', 'smoking_status': 'Current', 'bmi': 33.2},
        32: {'id': 32, 'name': 'Ryan Hill', 'age': 40, 'gender': 'M', 'phone': '555-0132', 'email': 'ryan@example.com', 'medical_history': 'None', 'smoking_status': 'Never', 'bmi': 24.1},
        33: {'id': 33, 'name': 'Rebecca Scott', 'age': 77, 'gender': 'F', 'phone': '555-0133', 'email': 'rebecca@example.com', 'medical_history': 'CHF; COPD', 'smoking_status': 'Former', 'bmi': 26.7},
        34: {'id': 34, 'name': 'Nicholas Green', 'age': 43, 'gender': 'M', 'phone': '555-0134', 'email': 'nicholas@example.com', 'medical_history': 'None', 'smoking_status': 'Never', 'bmi': 21.8},
        35: {'id': 35, 'name': 'Christina Adams', 'age': 56, 'gender': 'F', 'phone': '555-0135', 'email': 'christina@example.com', 'medical_history': 'Hypertension', 'smoking_status': 'Current', 'bmi': 30.4},
        36: {'id': 36, 'name': 'Brandon Baker', 'age': 65, 'gender': 'M', 'phone': '555-0136', 'email': 'brandon@example.com', 'medical_history': 'Diabetes Type 2', 'smoking_status': 'Former', 'bmi': 28.8},
        37: {'id': 37, 'name': 'Kimberly Nelson', 'age': 31, 'gender': 'F', 'phone': '555-0137', 'email': 'kimberly@example.com', 'medical_history': 'None', 'smoking_status': 'Never', 'bmi': 19.9},
        38: {'id': 38, 'name': 'Jonathan Carter', 'age': 76, 'gender': 'M', 'phone': '555-0138', 'email': 'jonathan@example.com', 'medical_history': 'CAD; Hypertension', 'smoking_status': 'Current', 'bmi': 36.1},
        39: {'id': 39, 'name': 'Nicole Mitchell', 'age': 34, 'gender': 'F', 'phone': '555-0139', 'email': 'nicole@example.com', 'medical_history': 'None', 'smoking_status': 'Never', 'bmi': 22.3},
        40: {'id': 40, 'name': 'Justin Perez', 'age': 60, 'gender': 'M', 'phone': '555-0140', 'email': 'justin@example.com', 'medical_history': 'Hyperlipidemia', 'smoking_status': 'Former', 'bmi': 27.3},
        41: {'id': 41, 'name': 'Megan Roberts', 'age': 53, 'gender': 'F', 'phone': '555-0141', 'email': 'megan@example.com', 'medical_history': 'None', 'smoking_status': 'Never', 'bmi': 23.7},
        42: {'id': 42, 'name': 'Timothy Turner', 'age': 75, 'gender': 'M', 'phone': '555-0142', 'email': 'timothy@example.com', 'medical_history': 'CHF; Diabetes', 'smoking_status': 'Former', 'bmi': 30.2},
        43: {'id': 43, 'name': 'Cynthia Phillips', 'age': 41, 'gender': 'F', 'phone': '555-0143', 'email': 'cynthia@example.com', 'medical_history': 'None', 'smoking_status': 'Never', 'bmi': 25.6},
        44: {'id': 44, 'name': 'Samuel Campbell', 'age': 72, 'gender': 'M', 'phone': '555-0144', 'email': 'samuel@example.com', 'medical_history': 'Hypertension', 'smoking_status': 'Current', 'bmi': 32.3},
        45: {'id': 45, 'name': 'Anna Parker', 'age': 37, 'gender': 'F', 'phone': '555-0145', 'email': 'anna@example.com', 'medical_history': 'None', 'smoking_status': 'Never', 'bmi': 20.4},
        46: {'id': 46, 'name': 'Zachary Evans', 'age': 46, 'gender': 'M', 'phone': '555-0146', 'email': 'zachary@example.com', 'medical_history': 'None', 'smoking_status': 'Current', 'bmi': 29.0},
        47: {'id': 47, 'name': 'Michelle Edwards', 'age': 63, 'gender': 'F', 'phone': '555-0147', 'email': 'michelle@example.com', 'medical_history': 'Diabetes Type 2', 'smoking_status': 'Former', 'bmi': 27.9},
        48: {'id': 48, 'name': 'Dylan Collins', 'age': 35, 'gender': 'M', 'phone': '555-0148', 'email': 'dylan@example.com', 'medical_history': 'None', 'smoking_status': 'Never', 'bmi': 23.1},
        49: {'id': 49, 'name': 'Brianna Stewart', 'age': 68, 'gender': 'F', 'phone': '555-0149', 'email': 'brianna@example.com', 'medical_history': 'Hypertension', 'smoking_status': 'Never', 'bmi': 26.4},
        50: {'id': 50, 'name': 'Nathan Morris', 'age': 59, 'gender': 'M', 'phone': '555-0150', 'email': 'nathan@example.com', 'medical_history': 'Hyperlipidemia', 'smoking_status': 'Former', 'bmi': 28.0},
    })

    predictions_db.update({
        101: {'id': 101, 'patient_id': 1, 'patient_name': 'Margaret Hensley', 'date': '2025-06-03', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 18.3, 'recommendation': 'Low risk - maintain healthy lifestyle.', 'framingham': 6.2, 'ascvd': 5.1, 'qrisk3': 7.8},
        102: {'id': 102, 'patient_id': 2, 'patient_name': 'Robert Chen', 'date': '2025-05-28', 'risk_level': 'High', 'risk_class': 'high', 'probability': 74.2, 'recommendation': 'High risk - cardiology consultation advised.', 'framingham': 15.4, 'ascvd': 14.2, 'qrisk3': 16.1},
        103: {'id': 103, 'patient_id': 3, 'patient_name': 'Susan Park', 'date': '2025-05-15', 'risk_level': 'High', 'risk_class': 'high', 'probability': 68.1, 'recommendation': 'High risk - immediate lifestyle changes required.', 'framingham': 12.8, 'ascvd': 11.5, 'qrisk3': 13.9},
        104: {'id': 104, 'patient_id': 4, 'patient_name': 'James Wilson', 'date': '2025-06-01', 'risk_level': 'High', 'risk_class': 'high', 'probability': 89.5, 'recommendation': 'Very high risk - urgent cardiology referral.', 'framingham': 18.9, 'ascvd': 17.3, 'qrisk3': 19.5},
        105: {'id': 105, 'patient_id': 5, 'patient_name': 'Linda Martinez', 'date': '2025-05-20', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 14.5, 'recommendation': 'Low risk - maintain healthy habits.', 'framingham': 4.5, 'ascvd': 3.8, 'qrisk3': 5.2},
        106: {'id': 106, 'patient_id': 6, 'patient_name': 'David Kim', 'date': '2025-05-25', 'risk_level': 'Medium', 'risk_class': 'medium', 'probability': 63.2, 'recommendation': 'Moderate risk - consider statin therapy.', 'framingham': 11.2, 'ascvd': 10.1, 'qrisk3': 12.0},
        107: {'id': 107, 'patient_id': 7, 'patient_name': 'Patricia Garcia', 'date': '2025-06-02', 'risk_level': 'High', 'risk_class': 'high', 'probability': 78.4, 'recommendation': 'High risk - cardiac workup recommended.', 'framingham': 16.7, 'ascvd': 15.3, 'qrisk3': 17.8},
        108: {'id': 108, 'patient_id': 8, 'patient_name': 'Michael Johnson', 'date': '2025-05-10', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 21.8, 'recommendation': 'Low risk - encourage regular exercise.', 'framingham': 5.8, 'ascvd': 4.9, 'qrisk3': 6.5},
        109: {'id': 109, 'patient_id': 9, 'patient_name': 'Jennifer Lee', 'date': '2025-05-22', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 9.7, 'recommendation': 'Very low risk - maintain healthy lifestyle.', 'framingham': 3.2, 'ascvd': 2.7, 'qrisk3': 4.1},
        110: {'id': 110, 'patient_id': 10, 'patient_name': 'William Brown', 'date': '2025-06-05', 'risk_level': 'High', 'risk_class': 'high', 'probability': 92.3, 'recommendation': 'Critical risk - immediate hospitalization.', 'framingham': 22.1, 'ascvd': 20.5, 'qrisk3': 23.4},
        111: {'id': 111, 'patient_id': 11, 'patient_name': 'Barbara Taylor', 'date': '2025-05-30', 'risk_level': 'High', 'risk_class': 'high', 'probability': 71.2, 'recommendation': 'High risk - diabetes management crucial.', 'framingham': 14.8, 'ascvd': 13.6, 'qrisk3': 15.9},
        112: {'id': 112, 'patient_id': 12, 'patient_name': 'Richard Singh', 'date': '2025-05-18', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 16.7, 'recommendation': 'Low risk - maintain healthy habits.', 'framingham': 4.8, 'ascvd': 4.0, 'qrisk3': 5.7},
        113: {'id': 113, 'patient_id': 13, 'patient_name': 'Nancy Wilson', 'date': '2025-06-04', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 28.9, 'recommendation': 'Low to moderate risk - monitor annually.', 'framingham': 6.9, 'ascvd': 5.8, 'qrisk3': 7.3},
        114: {'id': 114, 'patient_id': 14, 'patient_name': 'Thomas Moore', 'date': '2025-05-27', 'risk_level': 'Medium', 'risk_class': 'medium', 'probability': 59.8, 'recommendation': 'Moderate risk - lipid management recommended.', 'framingham': 10.4, 'ascvd': 9.3, 'qrisk3': 11.1},
        115: {'id': 115, 'patient_id': 15, 'patient_name': 'Deborah Rodriguez', 'date': '2025-06-06', 'risk_level': 'High', 'risk_class': 'high', 'probability': 85.6, 'recommendation': 'High risk - immediate intervention needed.', 'framingham': 17.9, 'ascvd': 16.4, 'qrisk3': 18.9},
        116: {'id': 116, 'patient_id': 16, 'patient_name': 'Charles Anderson', 'date': '2025-05-21', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 20.1, 'recommendation': 'Low risk - maintain healthy lifestyle.', 'framingham': 5.1, 'ascvd': 4.2, 'qrisk3': 5.9},
        117: {'id': 117, 'patient_id': 17, 'patient_name': 'Sarah Thomas', 'date': '2025-06-07', 'risk_level': 'High', 'risk_class': 'high', 'probability': 66.8, 'recommendation': 'High risk - monitor closely.', 'framingham': 14.2, 'ascvd': 12.8, 'qrisk3': 15.3},
        118: {'id': 118, 'patient_id': 18, 'patient_name': 'Christopher Jackson', 'date': '2025-05-14', 'risk_level': 'High', 'risk_class': 'high', 'probability': 75.9, 'recommendation': 'High risk - cardiology referral advised.', 'framingham': 16.8, 'ascvd': 15.1, 'qrisk3': 17.4},
        119: {'id': 119, 'patient_id': 19, 'patient_name': 'Jessica White', 'date': '2025-05-29', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 12.3, 'recommendation': 'Very low risk - maintain healthy habits.', 'framingham': 3.8, 'ascvd': 3.1, 'qrisk3': 4.5},
        120: {'id': 120, 'patient_id': 20, 'patient_name': 'Daniel Harris', 'date': '2025-06-08', 'risk_level': 'High', 'risk_class': 'high', 'probability': 81.1, 'recommendation': 'High risk - aggressive risk factor management.', 'framingham': 18.2, 'ascvd': 16.9, 'qrisk3': 19.1},
        121: {'id': 121, 'patient_id': 21, 'patient_name': 'Emily Martinez', 'date': '2025-05-11', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 19.8, 'recommendation': 'Low risk - regular check-ups.', 'framingham': 5.3, 'ascvd': 4.4, 'qrisk3': 6.1},
        122: {'id': 122, 'patient_id': 22, 'patient_name': 'Matthew Robinson', 'date': '2025-06-10', 'risk_level': 'High', 'risk_class': 'high', 'probability': 92.2, 'recommendation': 'Very high risk - immediate intervention.', 'framingham': 22.0, 'ascvd': 20.2, 'qrisk3': 23.5},
        123: {'id': 123, 'patient_id': 23, 'patient_name': 'Amanda Clark', 'date': '2025-05-03', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 8.9, 'recommendation': 'Low risk - maintain healthy habits.', 'framingham': 3.1, 'ascvd': 2.6, 'qrisk3': 4.0},
        124: {'id': 124, 'patient_id': 24, 'patient_name': 'Andrew Lewis', 'date': '2025-06-12', 'risk_level': 'Medium', 'risk_class': 'medium', 'probability': 66.5, 'recommendation': 'Moderate risk - follow-up in 2 months.', 'framingham': 13.9, 'ascvd': 12.5, 'qrisk3': 14.8},
        125: {'id': 125, 'patient_id': 25, 'patient_name': 'Melissa Walker', 'date': '2025-05-19', 'risk_level': 'High', 'risk_class': 'high', 'probability': 71.3, 'recommendation': 'High risk - diabetes and weight management.', 'framingham': 15.1, 'ascvd': 13.8, 'qrisk3': 16.2},
        126: {'id': 126, 'patient_id': 26, 'patient_name': 'Joshua Hall', 'date': '2025-06-01', 'risk_level': 'High', 'risk_class': 'high', 'probability': 78.5, 'recommendation': 'High risk - consider statin therapy.', 'framingham': 16.5, 'ascvd': 15.0, 'qrisk3': 17.6},
        127: {'id': 127, 'patient_id': 27, 'patient_name': 'Laura Young', 'date': '2025-05-26', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 27.8, 'recommendation': 'Low to moderate - monitor BP.', 'framingham': 6.7, 'ascvd': 5.6, 'qrisk3': 7.2},
        128: {'id': 128, 'patient_id': 28, 'patient_name': 'Kevin Allen', 'date': '2025-05-08', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 15.6, 'recommendation': 'Low risk - maintain lifestyle.', 'framingham': 4.2, 'ascvd': 3.5, 'qrisk3': 5.0},
        129: {'id': 129, 'patient_id': 29, 'patient_name': 'Maria King', 'date': '2025-06-14', 'risk_level': 'Medium', 'risk_class': 'medium', 'probability': 31.2, 'recommendation': 'Moderate risk - lifestyle modifications.', 'framingham': 7.5, 'ascvd': 6.3, 'qrisk3': 8.1},
        130: {'id': 130, 'patient_id': 30, 'patient_name': 'Jason Wright', 'date': '2025-05-17', 'risk_level': 'Medium', 'risk_class': 'medium', 'probability': 61.2, 'recommendation': 'Moderate risk - lipid management.', 'framingham': 11.0, 'ascvd': 9.9, 'qrisk3': 11.9},
        131: {'id': 131, 'patient_id': 31, 'patient_name': 'Stephanie Lopez', 'date': '2025-06-09', 'risk_level': 'High', 'risk_class': 'high', 'probability': 84.1, 'recommendation': 'High risk - urgent cardiology referral.', 'framingham': 18.0, 'ascvd': 16.3, 'qrisk3': 19.2},
        132: {'id': 132, 'patient_id': 32, 'patient_name': 'Ryan Hill', 'date': '2025-05-24', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 19.0, 'recommendation': 'Low risk - maintain healthy habits.', 'framingham': 5.0, 'ascvd': 4.1, 'qrisk3': 5.8},
        133: {'id': 133, 'patient_id': 33, 'patient_name': 'Rebecca Scott', 'date': '2025-06-13', 'risk_level': 'High', 'risk_class': 'high', 'probability': 71.9, 'recommendation': 'High risk - cardiac evaluation.', 'framingham': 15.3, 'ascvd': 13.9, 'qrisk3': 16.4},
        134: {'id': 134, 'patient_id': 34, 'patient_name': 'Nicholas Green', 'date': '2025-05-05', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 13.4, 'recommendation': 'Low risk - regular exercise.', 'framingham': 3.9, 'ascvd': 3.2, 'qrisk3': 4.6},
        135: {'id': 135, 'patient_id': 35, 'patient_name': 'Christina Adams', 'date': '2025-06-11', 'risk_level': 'High', 'risk_class': 'high', 'probability': 80.2, 'recommendation': 'High risk - immediate medication.', 'framingham': 17.5, 'ascvd': 15.9, 'qrisk3': 18.7},
        136: {'id': 136, 'patient_id': 36, 'patient_name': 'Brandon Baker', 'date': '2025-05-23', 'risk_level': 'Medium', 'risk_class': 'medium', 'probability': 67.5, 'recommendation': 'Moderate risk - follow-up.', 'framingham': 14.0, 'ascvd': 12.6, 'qrisk3': 15.0},
        137: {'id': 137, 'patient_id': 37, 'patient_name': 'Kimberly Nelson', 'date': '2025-05-09', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 11.2, 'recommendation': 'Very low risk - maintain habits.', 'framingham': 3.5, 'ascvd': 2.9, 'qrisk3': 4.2},
        138: {'id': 138, 'patient_id': 38, 'patient_name': 'Jonathan Carter', 'date': '2025-06-15', 'risk_level': 'High', 'risk_class': 'high', 'probability': 93.5, 'recommendation': 'Critical risk - urgent hospitalization.', 'framingham': 22.5, 'ascvd': 20.8, 'qrisk3': 23.9},
        139: {'id': 139, 'patient_id': 39, 'patient_name': 'Nicole Mitchell', 'date': '2025-05-12', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 17.5, 'recommendation': 'Low risk - maintain healthy lifestyle.', 'framingham': 4.7, 'ascvd': 3.9, 'qrisk3': 5.5},
        140: {'id': 140, 'patient_id': 40, 'patient_name': 'Justin Perez', 'date': '2025-06-04', 'risk_level': 'Medium', 'risk_class': 'medium', 'probability': 64.8, 'recommendation': 'Moderate risk - consider statin.', 'framingham': 12.0, 'ascvd': 10.8, 'qrisk3': 12.9},
        141: {'id': 141, 'patient_id': 41, 'patient_name': 'Megan Roberts', 'date': '2025-05-31', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 23.8, 'recommendation': 'Low risk - maintain habits.', 'framingham': 5.9, 'ascvd': 5.0, 'qrisk3': 6.6},
        142: {'id': 142, 'patient_id': 42, 'patient_name': 'Timothy Turner', 'date': '2025-06-02', 'risk_level': 'High', 'risk_class': 'high', 'probability': 75.4, 'recommendation': 'High risk - close monitoring.', 'framingham': 16.2, 'ascvd': 14.8, 'qrisk3': 17.2},
        143: {'id': 143, 'patient_id': 43, 'patient_name': 'Cynthia Phillips', 'date': '2025-05-25', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 26.9, 'recommendation': 'Low to moderate - check BP.', 'framingham': 6.8, 'ascvd': 5.7, 'qrisk3': 7.4},
        144: {'id': 144, 'patient_id': 44, 'patient_name': 'Samuel Campbell', 'date': '2025-06-07', 'risk_level': 'High', 'risk_class': 'high', 'probability': 86.3, 'recommendation': 'High risk - immediate intervention.', 'framingham': 18.7, 'ascvd': 17.0, 'qrisk3': 19.8},
        145: {'id': 145, 'patient_id': 45, 'patient_name': 'Anna Parker', 'date': '2025-05-13', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 10.5, 'recommendation': 'Very low risk - maintain habits.', 'framingham': 3.3, 'ascvd': 2.8, 'qrisk3': 4.0},
        146: {'id': 146, 'patient_id': 46, 'patient_name': 'Zachary Evans', 'date': '2025-06-16', 'risk_level': 'High', 'risk_class': 'high', 'probability': 79.1, 'recommendation': 'High risk - cardiology consult.', 'framingham': 17.0, 'ascvd': 15.4, 'qrisk3': 18.1},
        147: {'id': 147, 'patient_id': 47, 'patient_name': 'Michelle Edwards', 'date': '2025-05-27', 'risk_level': 'High', 'risk_class': 'high', 'probability': 70.8, 'recommendation': 'High risk - weight management.', 'framingham': 15.0, 'ascvd': 13.6, 'qrisk3': 16.0},
        148: {'id': 148, 'patient_id': 48, 'patient_name': 'Dylan Collins', 'date': '2025-05-04', 'risk_level': 'Low', 'risk_class': 'low', 'probability': 14.9, 'recommendation': 'Low risk - maintain healthy lifestyle.', 'framingham': 4.0, 'ascvd': 3.3, 'qrisk3': 4.8},
        149: {'id': 149, 'patient_id': 49, 'patient_name': 'Brianna Stewart', 'date': '2025-06-10', 'risk_level': 'Medium', 'risk_class': 'medium', 'probability': 32.1, 'recommendation': 'Moderate risk - lifestyle changes.', 'framingham': 7.8, 'ascvd': 6.6, 'qrisk3': 8.5},
        150: {'id': 150, 'patient_id': 50, 'patient_name': 'Nathan Morris', 'date': '2025-05-29', 'risk_level': 'Medium', 'risk_class': 'medium', 'probability': 62.2, 'recommendation': 'Moderate risk - lipid management.', 'framingham': 11.4, 'ascvd': 10.2, 'qrisk3': 12.2},
    })

    next_patient_id = 51
    next_prediction_id = 151
    print("✅ Loaded 50 patients with predictions.")

load_builtin_data()

# -------------------------------------------------------------------
# Generate appointments for all doctors
# -------------------------------------------------------------------
def generate_appointments():
    global appointments_db, next_appointment_id
    appointments_db.clear()
    next_appointment_id = 1
    doctors = [data for data in users_db.values() if data.get('role') == 'doctor']
    if not doctors:
        print("No doctors found.")
        return
    patients = list(patients_db.values())
    if not patients:
        print("No patients found.")
        return
    reasons = [
        "Routine check-up", "Chest pain evaluation", "Follow-up on hypertension",
        "Diabetes management", "Lipid profile review", "ECG interpretation",
        "Stress test", "Medication review", "Post-surgery follow-up",
        "Cardiology consultation", "Annual physical", "Blood pressure monitoring"
    ]
    statuses = ['scheduled', 'confirmed', 'cancelled', 'rejected']
    weights = [0.5, 0.3, 0.1, 0.1]

    for doctor in doctors:
        doctor_name = doctor['name']
        num = random.randint(3, 6)
        selected = random.sample(patients, min(num, len(patients)))
        for patient in selected:
            date_offset = random.randint(-20, 20)
            appointment_date = (datetime.now() + timedelta(days=date_offset)).strftime('%Y-%m-%d %H:%M')
            status = random.choices(statuses, weights=weights)[0]
            reason = random.choice(reasons)
            appointments_db[next_appointment_id] = {
                'id': next_appointment_id,
                'patient_id': patient['id'],
                'patient_name': patient['name'],
                'doctor_name': doctor_name,
                'date': appointment_date,
                'reason': reason,
                'status': status,
                'created_by': 'system',
                'email': patient.get('email', ''),
                'is_guest': False,
                'cancellation_count': 0
            }
            next_appointment_id += 1
    print(f"✅ Generated {len(appointments_db)} appointments.")

generate_appointments()

# -------------------------------------------------------------------
# Generate 20 Appointments for Doctors
# -------------------------------------------------------------------
def generate_doctor_appointments():
    """Generate 20 sample appointments for doctors"""
    global appointments_db, next_appointment_id
    
    # Clear existing appointments
    appointments_db.clear()
    next_appointment_id = 1
    
    # Get all doctors
    doctors = [data for data in users_db.values() if data.get('role') == 'doctor']
    if not doctors:
        print("No doctors found.")
        return
    
    # Get all patients
    patients = list(patients_db.values())
    if not patients:
        print("No patients found.")
        return
    
    # Sample reasons for appointments
    reasons = [
        "Routine check-up", "Chest pain evaluation", "Follow-up on hypertension",
        "Diabetes management", "Lipid profile review", "ECG interpretation",
        "Stress test", "Medication review", "Post-surgery follow-up",
        "Cardiology consultation", "Annual physical", "Blood pressure monitoring",
        "Heart murmur evaluation", "Palpitations assessment", "Cholesterol screening",
        "Diabetes screening", "Heart health consultation", "Medication adjustment",
        "Post-hospitalization follow-up", "Pre-surgery clearance"
    ]
    
    statuses = ['scheduled', 'confirmed', 'cancelled', 'rejected', 'completed']
    weights = [0.35, 0.30, 0.10, 0.05, 0.20]  # 35% scheduled, 30% confirmed, 10% cancelled, 5% rejected, 20% completed
    
    # Generate appointments for each doctor
    for doctor in doctors:
        doctor_name = doctor['name']
        # Each doctor gets 3-5 appointments
        num_appointments = random.randint(3, 5)
        selected_patients = random.sample(patients, min(num_appointments, len(patients)))
        
        for patient in selected_patients:
            # Random date within last 30 days to next 30 days
            date_offset = random.randint(-20, 30)
            appointment_date = datetime.now() + timedelta(days=date_offset)
            appointment_date_str = appointment_date.strftime('%Y-%m-%d %H:%M')
            
            status = random.choices(statuses, weights=weights)[0]
            reason = random.choice(reasons)
            
            appointments_db[next_appointment_id] = {
                'id': next_appointment_id,
                'patient_id': patient['id'],
                'patient_name': patient['name'],
                'doctor_name': doctor_name,
                'date': appointment_date_str,
                'reason': reason,
                'status': status,
                'created_by': 'system',
                'email': patient.get('email', ''),
                'phone': patient.get('phone', ''),
                'is_guest': False,
                'cancellation_count': 0,
                'notes': random.choice([
                    'Patient needs blood work', 'Follow-up required in 2 weeks',
                    'Bring previous medical records', 'Fasting required',
                    'Bring current medications list', 'Family history of heart disease'
                ])
            }
            next_appointment_id += 1
    
    print(f"✅ Generated {len(appointments_db)} doctor appointments.")
# Generate appointments for all doctors
generate_doctor_appointments()

# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------
def framingham_score(age, sex, systolic_bp, total_chol, hdl, smoker, diabetic):
    return round(5 + (age-50)*0.5 + (10 if smoker else 0) + (5 if diabetic else 0), 1)

def ascvd_score(age, sex, systolic_bp, total_chol, hdl, smoker, diabetic, race='white'):
    return round(4 + (age-50)*0.4 + (12 if smoker else 0) + (8 if diabetic else 0), 1)

def qrisk3_score(age, sex, systolic_bp, total_chol, hdl, smoker, diabetic, family_history):
    return round(3 + (age-50)*0.3 + (10 if smoker else 0) + (7 if diabetic else 0) + (5 if family_history else 0), 1)

def calculate_risk(age, systolic_bp, diastolic_bp, smoking):
    risk = 0
    if age > 60: risk += 20
    elif age > 50: risk += 10
    if systolic_bp > 140: risk += 15
    elif systolic_bp > 120: risk += 5
    if diastolic_bp > 90: risk += 10
    if smoking == 'current': risk += 20
    elif smoking == 'former': risk += 10
    risk = min(max(risk, 0), 100)
    if risk >= 60:
        level = 'High'; cls = 'high'; rec = 'Immediate cardiology consultation advised.'
    elif risk >= 30:
        level = 'Medium'; cls = 'medium'; rec = 'Lifestyle changes and follow-up in 3 months.'
    else:
        level = 'Low'; cls = 'low'; rec = 'Maintain healthy habits.'
    return level, cls, round(risk, 1), rec

def dashboard_redirect():
    role = session.get('role')
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'doctor':
        return redirect(url_for('doctor_dashboard'))
    elif role == 'patient':
        return redirect(url_for('patient_dashboard'))
    else:
        return redirect(url_for('login_choice'))

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login_choice'))
        return f(*args, **kwargs)
    return wrapper

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get('role') not in allowed_roles:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('login_choice'))
            return f(*args, **kwargs)
        return wrapper
    return decorator

# -------------------------------------------------------------------
# Authentication routes
# -------------------------------------------------------------------
@app.route('/')
def index():
    # If user is already logged in, redirect to their dashboard
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif role == 'doctor':
            return redirect(url_for('doctor_dashboard'))
        elif role == 'patient':
            return redirect(url_for('patient_dashboard'))
    return render_template('predictor/index.html')

# Dashboard route that redirects based on role


@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role')
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'doctor':
        return redirect(url_for('doctor_dashboard'))
    elif role == 'patient':
        return redirect(url_for('patient_dashboard'))
    else:
        return redirect(url_for('login_choice'))


@app.route('/login-choice')
def login_choice():
    # If user is already logged in, redirect to their dashboard
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif role == 'doctor':
            return redirect(url_for('doctor_dashboard'))
        elif role == 'patient':
            return redirect(url_for('patient_dashboard'))
    return render_template('predictor/login_choice.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    # If already logged in as admin, redirect to admin dashboard
    if 'user_id' in session and session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('predictor/admin_login.html')
        
        user = users_db.get(username)
        if user and user.get('password') == password and user.get('role') == 'admin':
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = username
            session['user_name'] = user.get('name', username)
            session['role'] = user.get('role')
            session['email'] = user.get('email', '')
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid admin credentials. Please try again.', 'error')
    return render_template('predictor/admin_login.html')

@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    if 'user_id' in session and session.get('role') == 'doctor':
        return redirect(url_for('dashboard'))  # Changed from doctor_dashboard to dashboard
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('predictor/doctor_login.html')
        
        user = users_db.get(username)
        if user and user.get('password') == password and user.get('role') == 'doctor':
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = username
            session['user_name'] = user.get('name', username)
            session['role'] = user.get('role')
            session['email'] = user.get('email', '')
            flash('Doctor login successful!', 'success')
            return redirect(url_for('dashboard'))  # Changed from doctor_dashboard to dashboard
        flash('Invalid doctor credentials. Please try again.', 'error')
    return render_template('predictor/doctor_login.html')
@app.route('/patient/login', methods=['GET', 'POST'])
def patient_login():
    # If already logged in as patient, redirect to dashboard
    if 'user_id' in session and session.get('role') == 'patient':
        return redirect(url_for('dashboard'))  # Use dashboard instead
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('predictor/patient_login.html')
        
        user = users_db.get(username)
        if user and user.get('password') == password and user.get('role') == 'patient':
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = username
            session['user_name'] = user.get('name', username)
            session['role'] = user.get('role')
            session['email'] = user.get('email', '')
            flash('Patient login successful!', 'success')
            return redirect(url_for('dashboard'))  # Use dashboard instead
        flash('Invalid patient credentials. Please try again.', 'error')
    return render_template('predictor/patient_login.html')

@app.route('/patient/dashboard')
@login_required
@role_required(['patient'])
def patient_dashboard():
    """Patient Dashboard - View health records and appointments"""
    user_id = session.get('user_id')
    username = session.get('username')
    
    # Get patient data
    patient = None
    for pid, p in patients_db.items():
        if p.get('user_id') == user_id:
            patient = p
            break
    
    if not patient:
        # Try to find by username
        for pid, p in patients_db.items():
            if p.get('name') == session.get('user_name'):
                patient = p
                break
    
    # Get patient's appointments
    patient_appointments = []
    for app_id, app in appointments_db.items():
        if app.get('patient_id') == patient.get('id') if patient else False:
            patient_appointments.append(app)
        elif app.get('email') == session.get('email'):
            patient_appointments.append(app)
    
    # Get patient's predictions
    patient_predictions = []
    for pred_id, pred in predictions_db.items():
        if pred.get('patient_id') == patient.get('id') if patient else False:
            patient_predictions.append(pred)
        elif pred.get('email') == session.get('email'):
            patient_predictions.append(pred)
    
    # Sort predictions by date
    patient_predictions.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    return render_template('predictor/patient_dashboard.html',
                          patient=patient,
                          appointments=patient_appointments,
                          predictions=patient_predictions,
                          now=datetime.now())

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user_found = None
        for username, user_data in users_db.items():
            if user_data.get('email') == email:
                user_found = user_data
                break
        
        if user_found:
            flash('Password reset link has been sent to your email.', 'success')
        else:
            flash('Email address not found.', 'error')
        return redirect(url_for('forgot_password'))
    return render_template('predictor/forgot_password.html')
@app.route('/register', methods=['GET', 'POST'])
def register():
    # If already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        name = request.form.get('name', username)
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('predictor/register.html')
        
        if username in users_db:
            flash('Username already exists. Please choose a different username.', 'error')
            return render_template('predictor/register.html')
        
        global next_user_id
        users_db[username] = {
            'id': next_user_id,
            'password': password,
            'name': name,
            'email': email,
            'role': 'patient',
            'created_at': datetime.now().strftime('%Y-%m-%d')
        }
        
        # Also create patient record
        global next_patient_id
        patients_db[next_patient_id] = {
            'id': next_patient_id,
            'name': name,
            'age': None,
            'gender': None,
            'phone': '',
            'email': email,
            'address': '',
            'medical_history': '',
            'smoking_status': 'Not recorded',
            'bmi': '—',
            'user_id': next_user_id,
            'last_prediction_date': None
        }
        next_patient_id += 1
        next_user_id += 1
        save_users_to_file()
        
        # Log the user in immediately
        session.permanent = True
        session['user_id'] = users_db[username]['id']
        session['username'] = username
        session['user_name'] = name
        session['role'] = 'patient'
        session['email'] = email
        
        flash('Registration successful! Welcome to MedPredict!', 'success')
        return redirect(url_for('patient_dashboard'))
    
    return render_template('predictor/register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

# -------------------------------------------------------------------
# Admin Dashboard
# -------------------------------------------------------------------
@app.route('/admin/dashboard')
@login_required
@role_required(['admin'])
def admin_dashboard():
    users_list = [{'username': un, **data} for un, data in users_db.items()]
    predictions_count = len(predictions_db)
    return render_template('predictor/admin_dashboard.html', users=users_list, predictions_count=predictions_count)

@app.route('/admin/create_user', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def admin_create_user():
    if request.method == 'POST':
        global next_user_id
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        email = request.form['email']
        role = request.form['role']
        if username in users_db:
            flash('Username already exists', 'error')
        else:
            users_db[username] = {
                'id': next_user_id,
                'password': password,
                'name': name,
                'email': email,
                'role': role,
                'created_at': datetime.now().strftime('%Y-%m-%d')
            }
            next_user_id += 1
            save_users_to_file()
            flash(f'User {username} created as {role}', 'success')
            return redirect(url_for('admin_dashboard'))
    return render_template('predictor/admin_create_user.html')

@app.route('/admin/delete_user/<username>')
@login_required
@role_required(['admin'])
def admin_delete_user(username):
    if username in users_db and username != 'admin':
        del users_db[username]
        save_users_to_file()
        flash(f'User {username} deleted', 'success')
    else:
        flash('Cannot delete this user', 'error')
    return redirect(url_for('admin_dashboard'))

# -------------------------------------------------------------------
# Admin Appointments Route (alias for appointments)
# -------------------------------------------------------------------
@app.route('/admin/appointments')
@login_required
@role_required(['admin'])
def admin_appointments():
    return redirect(url_for('appointments'))

# -------------------------------------------------------------------
# Doctor Dashboard
# -------------------------------------------------------------------
@app.route('/doctor/dashboard')
@login_required
@role_required(['doctor', 'admin'])
def doctor_dashboard():
    total_predictions = len(predictions_db)
    high_risk = sum(1 for p in predictions_db.values() if p['risk_level'] == 'High')
    total_patients = len(patients_db)
    stats = {'total_predictions': total_predictions, 'high_risk': high_risk, 'total_patients': total_patients}
    daily_avg = defaultdict(list)
    for pred in predictions_db.values():
        daily_avg[pred['date']].append(pred['probability'])
    sorted_dates = sorted(daily_avg.keys())
    trend_data = [round(sum(daily_avg[d])/len(daily_avg[d]),1) for d in sorted_dates] if sorted_dates else [0]
    if not trend_data:
        sorted_dates = ['No data']
    return render_template('predictor/doctor_dashboard.html', stats=stats,
                           trend_labels=sorted_dates, trend_data=trend_data,
                           now=datetime.now())

# -------------------------------------------------------------------
# Patient Dashboard
# -------------------------------------------------------------------
# ---------- Patient Management Routes ----------
@app.route('/patients')
@login_required
@role_required(['doctor', 'admin'])
def patients():
    # Get all patients with their latest prediction data
    patients_list = []
    male_count = 0
    female_count = 0
    high_risk_count = 0
    
    for pid, patient in patients_db.items():
        # Find latest prediction for this patient
        patient_predictions = [p for p in predictions_db.values() if p.get('patient_id') == pid]
        latest_prediction = None
        if patient_predictions:
            latest_prediction = max(patient_predictions, key=lambda x: x.get('date', ''))
        
        # Get risk level from latest prediction
        risk_level = 'Unknown'
        if latest_prediction:
            risk_level = latest_prediction.get('risk_level', 'Unknown')
            if risk_level == 'High':
                high_risk_count += 1
        
        # Get last prediction date
        last_prediction_date = 'Never'
        if latest_prediction:
            last_prediction_date = latest_prediction.get('date', 'Never')
        
        # Count gender
        gender = patient.get('gender', '')
        if gender == 'M':
            male_count += 1
        elif gender == 'F':
            female_count += 1
        
        patients_list.append({
            'id': patient.get('id'),
            'name': patient.get('name', 'Unknown'),
            'age': patient.get('age', 'N/A'),
            'gender': gender,
            'phone': patient.get('phone', 'N/A'),
            'email': patient.get('email', 'N/A'),
            'medical_history': patient.get('medical_history', 'None'),
            'smoking_status': patient.get('smoking_status', 'Not recorded'),
            'bmi': patient.get('bmi', '—'),
            'risk_level': risk_level,
            'last_prediction_date': last_prediction_date,
            'latest_prediction': latest_prediction
        })
    
    total_patients = len(patients_list)
    recent_predictions = len(predictions_db)
    
    return render_template('predictor/patients.html', 
                           patients=patients_list,
                           total_patients=total_patients,
                           male_count=male_count,
                           female_count=female_count,
                           recent_predictions=recent_predictions,
                           high_risk_count=high_risk_count)


@app.route('/patient/new', methods=['GET', 'POST'])
@login_required
@role_required(['doctor', 'admin'])
def new_patient():
    global next_patient_id
    if request.method == 'POST':
        pid = next_patient_id
        patients_db[pid] = {
            'id': pid,
            'name': request.form['name'],
            'age': int(request.form['age']),
            'gender': request.form['gender'],
            'phone': request.form['phone'],
            'email': request.form.get('email', ''),
            'address': request.form.get('address', ''),
            'medical_history': request.form.get('medical_history', ''),
            'smoking_status': request.form.get('smoking_status', 'Not recorded'),
            'bmi': request.form.get('bmi', '—'),
            'last_prediction_date': None
        }
        next_patient_id += 1
        flash('Patient added successfully.', 'success')
        return redirect(url_for('patients'))
    return render_template('predictor/patient_form.html')


@app.route('/patient/<int:patient_id>')
@login_required
@role_required(['doctor', 'admin'])
def view_patient(patient_id):
    """View patient details with all predictions"""
    patient = patients_db.get(patient_id)
    if not patient:
        flash('Patient not found', 'error')
        return redirect(url_for('patients'))
    
    # Get all predictions for this patient
    patient_predictions = []
    for pred_id, pred in predictions_db.items():
        if pred.get('patient_id') == patient_id:
            # Add prediction data with patient info
            pred_copy = pred.copy()
            pred_copy['id'] = pred_id
            patient_predictions.append(pred_copy)
    
    # Sort by date descending (newest first)
    patient_predictions.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    # Get the latest prediction for risk display
    latest_prediction = patient_predictions[0] if patient_predictions else None
    
    return render_template('predictor/patient_detail.html', 
                          patient=patient, 
                          predictions=patient_predictions,
                          latest_prediction=latest_prediction)


@app.route('/patient/<int:patient_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required(['doctor', 'admin'])
def edit_patient(patient_id):
    patient = patients_db.get(patient_id)
    if not patient:
        flash('Patient not found', 'error')
        return redirect(url_for('patients'))
    
    if request.method == 'POST':
        # Update patient data
        patient['name'] = request.form.get('name', patient.get('name', ''))
        patient['age'] = int(request.form.get('age', patient.get('age', 0)))
        patient['gender'] = request.form.get('gender', patient.get('gender', ''))
        patient['phone'] = request.form.get('phone', patient.get('phone', ''))
        patient['email'] = request.form.get('email', patient.get('email', ''))
        patient['address'] = request.form.get('address', patient.get('address', ''))
        patient['medical_history'] = request.form.get('medical_history', patient.get('medical_history', ''))
        patient['smoking_status'] = request.form.get('smoking_status', patient.get('smoking_status', 'Not recorded'))
        patient['bmi'] = request.form.get('bmi', patient.get('bmi', '—'))
        
        flash('Patient updated successfully.', 'success')
        return redirect(url_for('view_patient', patient_id=patient_id))
    
    return render_template('predictor/patient_form.html', patient=patient)


@app.route('/patient/<int:patient_id>/delete', methods=['POST'])
@login_required
@role_required(['doctor', 'admin'])
def delete_patient(patient_id):
    if patient_id in patients_db:
        del patients_db[patient_id]
        # Delete associated predictions
        to_delete = [pid for pid, p in predictions_db.items() if p.get('patient_id') == patient_id]
        for pid in to_delete:
            del predictions_db[pid]
        flash('Patient deleted successfully.', 'success')
    else:
        flash('Patient not found.', 'error')
    return redirect(url_for('patients'))


@app.route('/patient/<int:patient_id>/predict', methods=['GET'])
@login_required
@role_required(['doctor', 'admin'])
def predict_patient(patient_id):
    """Redirect to prediction page with patient pre-filled"""
    return redirect(url_for('predict', patient_id=patient_id))
# ---------- Prediction ----------
@app.route('/predict', methods=['GET', 'POST'])
@login_required
@role_required(['doctor', 'admin'])
def predict():
    global next_prediction_id
    
    # Get patient_id from query parameter (GET request) for pre-filling
    prefill_patient_id = request.args.get('patient_id')
    prefill_patient = None
    if prefill_patient_id and prefill_patient_id.isdigit():
        prefill_patient = patients_db.get(int(prefill_patient_id))
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        age = int(request.form['age'])
        gender = request.form['gender']
        systolic_bp = int(request.form['systolic_bp'])
        diastolic_bp = int(request.form['diastolic_bp'])
        smoking = request.form.get('smoking', 'never')
        hdl = int(request.form.get('hdl_cholesterol', 45))
        total_chol = int(request.form.get('cholesterol', 180))
        diabetic = 'diabetic' in request.form
        family_history = 'family_history' in request.form
        height = float(request.form.get('height', 0)) if request.form.get('height') else 0
        weight = float(request.form.get('weight', 0)) if request.form.get('weight') else 0
        bmi = round(weight / ((height/100)**2), 1) if height > 0 and weight > 0 else None
        hospital_name = request.form.get('hospital_name')

        patient_id = request.form.get('patient_id')
        if patient_id and patient_id.isdigit():
            patient = patients_db.get(int(patient_id))
            if patient:
                full_name = patient.get('name', full_name)
                age = patient.get('age', age)
                gender = patient.get('gender', gender)
        else:
            patient = None

        risk_level, risk_class, probability, recommendation = calculate_risk(age, systolic_bp, diastolic_bp, smoking)

        fram = framingham_score(age, gender, systolic_bp, total_chol, hdl, smoking in ('current','former'), diabetic)
        ascvd = ascvd_score(age, gender, systolic_bp, total_chol, hdl, smoking in ('current','former'), diabetic)
        qrisk = qrisk3_score(age, gender, systolic_bp, total_chol, hdl, smoking in ('current','former'), diabetic, family_history)

        pred_id = next_prediction_id
        predictions_db[pred_id] = {
            'id': pred_id,
            'patient_id': patient['id'] if patient else None,
            'patient_name': full_name,
            'email': email,
            'phone': phone,
            'age': age,
            'gender': gender,
            'systolic_bp': systolic_bp,
            'diastolic_bp': diastolic_bp,
            'smoking': smoking,
            'hdl': hdl,
            'total_cholesterol': total_chol,
            'diabetic': diabetic,
            'family_history': family_history,
            'bmi': bmi,
            'height': height,
            'weight': weight,
            'hospital_name': hospital_name,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'risk_level': risk_level,
            'risk_class': risk_class,
            'probability': probability,
            'recommendation': recommendation,
            'framingham': fram,
            'ascvd': ascvd,
            'qrisk3': qrisk
        }
        next_prediction_id += 1
        flash(f'Prediction completed for {full_name}.', 'success')
        return redirect(url_for('result', prediction_id=pred_id))
    
    patients_list = list(patients_db.values())
    return render_template('predictor/predict.html', 
                          patients=patients_list,
                          prefill_patient=prefill_patient)
@app.route('/result/<int:prediction_id>')
@login_required
def result(prediction_id):
    pred = predictions_db.get(prediction_id)
    if not pred:
        flash('Prediction not found', 'error')
        return dashboard_redirect()
    return render_template('predictor/result.html', prediction=pred)

# -------------------------------------------------------------------
# Analytics
# -------------------------------------------------------------------
@app.route('/analytics')
@login_required
@role_required(['doctor', 'admin'])
def analytics():
    global predictions_db, patients_db
    
    # Get all predictions as a list for the modal
    all_predictions_list = []
    for pred_id, pred in predictions_db.items():
        # Get patient name if available
        patient_name = pred.get('patient_name', 'Unknown')
        if pred.get('patient_id'):
            patient = patients_db.get(pred.get('patient_id'))
            if patient:
                patient_name = patient.get('name', patient_name)
        
        all_predictions_list.append({
            'id': pred_id,
            'patient_name': patient_name,
            'date': pred.get('date', 'N/A'),
            'risk_level': pred.get('risk_level', 'Unknown'),
            'probability': pred.get('probability', 0)
        })
    
    # Sort by date descending
    all_predictions_list.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    for pred in predictions_db.values():
        pid = pred.get('patient_id')
        if pid:
            patient = patients_db.get(pid, {})
            pred['patient_name'] = pred.get('patient_name') or patient.get('name', 'Unknown')
            pred['age'] = pred.get('age') or patient.get('age', 'N/A')
            pred['gender'] = pred.get('gender') or patient.get('gender', 'N/A')
            pred['smoking'] = patient.get('smoking_status', 'Not recorded')
            pred['bmi'] = patient.get('bmi', '—')

    total_predictions = len(predictions_db)
    
    # Handle empty predictions
    if total_predictions == 0:
        return render_template('predictor/analytics.html', 
                               total_predictions=0,
                               high_risk_rate=0,
                               avg_risk_probability=0,
                               patients_analyzed=0,
                               risk_distribution={'High': 0, 'Medium': 0, 'Low': 0},
                               monthly_labels=[],
                               monthly_data=[],
                               high_risk_patients=[],
                               risk_chart='{}',
                               monthly_chart='{}',
                               factors_chart='{}',
                               patients_with_risk=[],
                               all_predictions=[])

    high_risk_count = sum(1 for p in predictions_db.values() if p.get('risk_level') == 'High')
    high_risk_rate = round((high_risk_count / total_predictions) * 100, 1) if total_predictions > 0 else 0
    all_probs = [p.get('probability', 0) for p in predictions_db.values()]
    avg_risk_probability = round(sum(all_probs) / total_predictions, 1) if total_predictions > 0 else 0
    patients_analyzed = len(set(p.get('patient_id') for p in predictions_db.values() if p.get('patient_id')))

    risk_dist = {'High': 0, 'Medium': 0, 'Low': 0}
    for p in predictions_db.values():
        risk_dist[p.get('risk_level', 'Low')] += 1

    monthly_counts = defaultdict(int)
    for p in predictions_db.values():
        date_str = p.get('date', '')
        if date_str:
            monthly_counts[date_str[:7]] += 1
    monthly_labels = sorted(monthly_counts.keys())
    monthly_data = [monthly_counts[m] for m in monthly_labels]

    patient_risk_map = {}
    for p in predictions_db.values():
        pid = p.get('patient_id')
        if pid:
            risk = p.get('probability', 0)
            if pid not in patient_risk_map or risk > patient_risk_map[pid]['risk']:
                patient_risk_map[pid] = {
                    'risk': risk,
                    'name': p.get('patient_name', 'Unknown'),
                    'smoking': p.get('smoking', 'Not recorded'),
                    'bmi': p.get('bmi', '—'),
                    'age': p.get('age', 'N/A'),
                    'gender': p.get('gender', 'N/A'),
                    'id': pid
                }

    patients_with_risk = []
    for pid, info in patient_risk_map.items():
        patient = patients_db.get(pid, {})
        patients_with_risk.append({
            'id': pid,
            'name': info['name'],
            'age': info['age'],
            'gender': info['gender'],
            'phone': patient.get('phone', 'N/A'),
            'email': patient.get('email', 'N/A'),
            'smoking': info['smoking'],
            'bmi': info['bmi'],
            'latest_risk': f"{info['risk']:.1f}%"
        })
    patients_with_risk.sort(key=lambda x: float(x['latest_risk'].rstrip('%')), reverse=True)

    high_risk_patients = [
        {'name': info['name'], 'risk': f"{info['risk']:.1f}%"}
        for info in sorted(patient_risk_map.values(), key=lambda x: x['risk'], reverse=True)[:5]
    ]

    high_risk_preds = [p for p in predictions_db.values() if p.get('risk_level') == 'High']
    risk_factors = {'Smoker': 0, 'Diabetic': 0, 'Family History': 0, 'Hypertension': 0}
    for p in high_risk_preds:
        if p.get('smoking') in ('current', 'former', 'Current', 'Former'):
            risk_factors['Smoker'] += 1
        if p.get('diabetic'):
            risk_factors['Diabetic'] += 1
        if p.get('family_history'):
            risk_factors['Family History'] += 1
        if p.get('systolic_bp', 0) > 140:
            risk_factors['Hypertension'] += 1
    factors = list(risk_factors.keys())
    counts = list(risk_factors.values())

    try:
        fig1 = go.Figure(data=[go.Pie(labels=list(risk_dist.keys()), values=list(risk_dist.values()), hole=0.4)])
        risk_chart = json.dumps(fig1, cls=plotly.utils.PlotlyJSONEncoder)
    except:
        risk_chart = '{}'
    
    try:
        fig2 = go.Figure(data=[go.Scatter(x=monthly_labels, y=monthly_data, mode='lines+markers')])
        monthly_chart = json.dumps(fig2, cls=plotly.utils.PlotlyJSONEncoder)
    except:
        monthly_chart = '{}'
    
    try:
        fig3 = go.Figure(data=[go.Bar(x=factors, y=counts)])
        factors_chart = json.dumps(fig3, cls=plotly.utils.PlotlyJSONEncoder)
    except:
        factors_chart = '{}'

    return render_template('predictor/analytics.html',
                           total_predictions=total_predictions,
                           high_risk_rate=high_risk_rate,
                           avg_risk_probability=avg_risk_probability,
                           patients_analyzed=patients_analyzed,
                           risk_distribution=risk_dist,
                           monthly_labels=monthly_labels,
                           monthly_data=monthly_data,
                           high_risk_patients=high_risk_patients,
                           risk_chart=risk_chart,
                           monthly_chart=monthly_chart,
                           factors_chart=factors_chart,
                           patients_with_risk=patients_with_risk,
                           all_predictions=all_predictions_list)
        
# ---------- Reports & PDF ----------
@app.route('/reports')
@login_required
@role_required(['doctor', 'admin'])
def reports():
    all_reports = list(predictions_db.values())
    return render_template('predictor/reports.html', reports=all_reports)

@app.route('/report_preview/<int:prediction_id>')
@login_required
@role_required(['doctor', 'admin'])
def view_report_preview(prediction_id):
    """
    LOGIC: View full report preview for a specific prediction
    1. Fetches prediction data from predictions_db
    2. Gets patient data from patients_db
    3. Calculates risk factors based on age, smoking, BMI, BP, cholesterol
    4. Creates treatment plan based on risk level (High/Medium/Low)
    5. Generates clinical insights with key observations
    6. Renders the full report preview page
    """
    # Step 1: Get prediction data
    report = predictions_db.get(prediction_id)
    if not report:
        flash('Report not found', 'error')
        return redirect(url_for('reports'))

    # Step 2: Get patient data
    patient = patients_db.get(report.get('patient_id'), {})
    
    # Step 3: Merge data
    report['patient'] = patient
    report['patient_name'] = report.get('patient_name') or patient.get('name', 'Unknown')
    report['patient_age'] = report.get('age') or patient.get('age', 'N/A')
    report['patient_gender'] = report.get('gender') or patient.get('gender', 'N/A')
    report['patient_phone'] = patient.get('phone', 'N/A')
    report['patient_email'] = patient.get('email', 'N/A')
    report['patient_address'] = patient.get('address', 'N/A')
    report['medical_history'] = patient.get('medical_history', 'None reported')
    report['smoking_status'] = patient.get('smoking_status', 'Not recorded')
    report['bmi'] = patient.get('bmi', '—')

    # Step 4: Calculate Risk Factors
    risk_factors = []
    
    # Age risk
    if int(report['patient_age']) > 55:
        risk_factors.append("Age > 55 years")
    
    # Smoking risk
    if report['smoking_status'] in ('Current', 'current'):
        risk_factors.append("Current smoker")
    elif report['smoking_status'] in ('Former', 'former'):
        risk_factors.append("Former smoker")
    
    # BMI risk
    bmi_val = report['bmi']
    if bmi_val and isinstance(bmi_val, (int, float)):
        if bmi_val > 30:
            risk_factors.append(f"Obesity (BMI {bmi_val})")
        elif bmi_val > 25:
            risk_factors.append(f"Overweight (BMI {bmi_val})")
    
    # Other risk factors
    if report.get('diabetic'):
        risk_factors.append("Diabetes")
    if report.get('family_history'):
        risk_factors.append("Family history of CVD")
    if report.get('systolic_bp', 0) > 140:
        risk_factors.append(f"Elevated systolic BP ({report.get('systolic_bp')} mmHg)")
    if report.get('total_cholesterol', 0) > 200:
        risk_factors.append(f"Elevated total cholesterol ({report.get('total_cholesterol')} mg/dL)")
    if report.get('hdl', 0) < 40:
        risk_factors.append(f"Low HDL ({report.get('hdl')} mg/dL)")
    
    report['risk_factors'] = risk_factors if risk_factors else ["No significant risk factors identified"]

    # Step 5: Create Treatment Plan based on risk level
    treatment_plan = {}
    risk_level = report.get('risk_level', 'Low')

    # 5a. Lifestyle Modifications
    lifestyle = [
        "• Adopt a heart‑healthy diet (Mediterranean or DASH diet)",
        "• Regular physical activity (≥150 minutes of moderate exercise per week)",
        "• Maintain healthy weight (target BMI < 25)"
    ]
    if report['smoking_status'] in ('Current', 'current'):
        lifestyle.append("• Smoking cessation – enrol in a cessation programme")
    if bmi_val and isinstance(bmi_val, (int, float)) and bmi_val > 30:
        lifestyle.append("• Weight management – consider referral to dietitian")
    treatment_plan['Lifestyle Modifications'] = lifestyle

    # 5b. Pharmacotherapy based on risk level
    medications = []
    if risk_level == 'High':
        medications.append("• Statin therapy (e.g., atorvastatin 20-80 mg) – high intensity")
        medications.append("• Low‑dose aspirin (75-100 mg daily) – consider after risk/benefit")
        if report.get('systolic_bp', 0) > 140:
            medications.append("• Antihypertensive therapy (ACEi/ARB, CCB, or thiazide)")
        if report.get('diabetic'):
            medications.append("• Glycaemic control – optimize metformin or other agents")
        if report.get('total_cholesterol', 0) > 200:
            medications.append("• Additional lipid‑lowering therapy (ezetimibe) if needed")
    elif risk_level == 'Medium':
        medications.append("• Consider moderate‑intensity statin (e.g., atorvastatin 10-20 mg)")
        medications.append("• Evaluate aspirin therapy based on risk/benefit")
        if report.get('systolic_bp', 0) > 140:
            medications.append("• Blood pressure management (lifestyle + medication if needed)")
        if report.get('diabetic'):
            medications.append("• Glycaemic control – lifestyle and/or metformin")
    else:
        medications.append("• No pharmacotherapy indicated at this time")
        medications.append("• Continue monitoring and re‑assess annually")
    treatment_plan['Pharmacotherapy'] = medications

    # 5c. Follow-up Schedule
    follow_up = []
    if risk_level == 'High':
        follow_up.append("• Cardiology consultation within 2 weeks")
        follow_up.append("• Re‑assess risk in 1 month")
        follow_up.append("• Regular follow‑up every 3 months")
    elif risk_level == 'Medium':
        follow_up.append("• Cardiology consultation within 1 month")
        follow_up.append("• Re‑assess risk in 3 months")
        follow_up.append("• Annual follow‑up thereafter")
    else:
        follow_up.append("• Routine annual check‑up")
        follow_up.append("• Re‑assess risk in 12 months")
    treatment_plan['Follow‑up Schedule'] = follow_up

    # 5d. Patient Education
    education = [
        "• Explain risk factors and the importance of adherence",
        "• Provide educational materials on heart‑healthy living",
        "• Discuss warning signs (chest pain, SOB, palpitations)"
    ]
    treatment_plan['Patient Education'] = education
    report['treatment_plan'] = treatment_plan

    # Step 6: Generate Clinical Insights
    insights = []
    
    # Age insights
    if int(report['patient_age']) > 60:
        insights.append("• Age > 60 – elevated risk.")
    elif int(report['patient_age']) > 50:
        insights.append("• Age > 50 – moderate risk.")
    
    # Risk level insights
    if risk_level == 'High':
        insights.append("• HIGH RISK – urgent cardiology involvement required.")
    elif risk_level == 'Medium':
        insights.append("• MODERATE RISK – consider specialist referral and lifestyle changes.")
    else:
        insights.append("• LOW RISK – continue preventive measures.")
    
    # BMI insights
    if bmi_val and isinstance(bmi_val, (int, float)):
        if bmi_val > 30:
            insights.append(f"• BMI {bmi_val} – obesity; weight management is key.")
    
    # Smoking insights
    if report['smoking_status'] in ('Current', 'current'):
        insights.append("• Smoking cessation – top priority.")
    
    # Diabetes insights
    if report.get('diabetic'):
        insights.append("• Diabetes – optimize glycaemic control.")
    
    # Family history insights
    if report.get('family_history'):
        insights.append("• Family history of CVD – enhanced surveillance.")
    
    if not insights:
        insights.append("• No additional insights.")
    
    report['clinical_insights'] = insights

    # Step 7: Render the full report preview
    return render_template('predictor/report_preview.html', 
                          report=report, 
                          generated_on=datetime.now().strftime('%Y-%m-%d %H:%M'))

    
@app.route('/send_report/<int:prediction_id>', methods=['POST'])
@login_required
def send_report(prediction_id):
    flash('Email sending not fully implemented.', 'warning')
    return redirect(url_for('result', prediction_id=prediction_id))

@app.route('/history')
@login_required
@role_required(['doctor', 'admin'])
def history():
    return render_template('predictor/history.html', history=list(predictions_db.values()))
# -------------------------------------------------------------------
# Appointment Management Routes
# -------------------------------------------------------------------

@app.route('/appointments')
@login_required
def appointments():
    """
    View appointments based on user role
    LOGIC:
    1. Admin: Sees all appointments
    2. Doctor: Sees only their assigned appointments
    3. Patient: Sees only their own appointments
    4. Calculates statistics (total, pending, completed, cancelled)
    5. Sorts appointments by date (newest first)
    """
    user_id = session.get('user_id')
    role = session.get('role')
    username = session.get('username')
    
    # Get appointments based on role
    if role == 'admin':
        # Admin sees all appointments
        user_appointments = list(appointments_db.values())
    elif role == 'doctor':
        # Doctor sees appointments assigned to them
        doctor_data = users_db.get(username)
        doctor_name = doctor_data.get('name') if doctor_data else None
        if doctor_name:
            user_appointments = [a for a in appointments_db.values() if a.get('doctor_name') == doctor_name]
        else:
            user_appointments = []
    else:  # patient
        # Patient sees their own appointments
        user_appointments = [a for a in appointments_db.values() if a.get('patient_id') == user_id or a.get('email') == session.get('email')]
    
    # Sort by date (newest first)
    user_appointments.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    # Calculate statistics
    total = len(user_appointments)
    pending = sum(1 for a in user_appointments if a.get('status') in ['scheduled', 'confirmed'])
    completed = sum(1 for a in user_appointments if a.get('status') == 'completed')
    cancelled = sum(1 for a in user_appointments if a.get('status') == 'cancelled')
    
    # Count by status for badges
    status_counts = {
        'scheduled': sum(1 for a in user_appointments if a.get('status') == 'scheduled'),
        'confirmed': sum(1 for a in user_appointments if a.get('status') == 'confirmed'),
        'completed': sum(1 for a in user_appointments if a.get('status') == 'completed'),
        'cancelled': sum(1 for a in user_appointments if a.get('status') == 'cancelled'),
        'rejected': sum(1 for a in user_appointments if a.get('status') == 'rejected')
    }
    
    return render_template('predictor/appointments.html',
                          appointments=user_appointments,
                          total=total,
                          pending=pending,
                          completed=completed,
                          cancelled=cancelled,
                          status_counts=status_counts,
                          role=role)

@app.route('/appointments/create', methods=['GET', 'POST'])
@login_required
@role_required(['doctor', 'admin'])
def create_appointment():
    """
    Create a new appointment
    LOGIC:
    1. GET: Display form with patients and doctors list
    2. POST: Validate input, create appointment, save to database
    3. Auto-assign status as 'scheduled'
    4. Redirect to appointments list
    """
    global next_appointment_id
    
    if request.method == 'POST':
        # Get form data
        patient_id = int(request.form.get('patient_id'))
        doctor_name = request.form.get('doctor_name')
        appointment_date = request.form.get('appointment_date')
        reason = request.form.get('reason', '')
        notes = request.form.get('notes', '')
        
        # Validate required fields
        if not patient_id or not doctor_name or not appointment_date:
            flash('Please fill all required fields.', 'error')
            return redirect(url_for('create_appointment'))
        
        # Get patient details
        patient = patients_db.get(patient_id, {})
        patient_name = patient.get('name', f'Patient {patient_id}')
        
        # Create appointment
        appointments_db[next_appointment_id] = {
            'id': next_appointment_id,
            'patient_id': patient_id,
            'patient_name': patient_name,
            'doctor_name': doctor_name,
            'date': appointment_date,
            'reason': reason,
            'status': 'scheduled',
            'created_by': session.get('username'),
            'email': patient.get('email', ''),
            'phone': patient.get('phone', ''),
            'is_guest': False,
            'cancellation_count': 0,
            'notes': notes,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        next_appointment_id += 1
        
        flash(f'Appointment created for {patient_name} with {doctor_name}.', 'success')
        return redirect(url_for('appointments'))
    
    # GET request - display form
    patients_list = list(patients_db.values())
    doctors_list = [data for data in users_db.values() if data.get('role') == 'doctor']
    
    return render_template('predictor/create_appointment.html', 
                          patients=patients_list, 
                          doctors=doctors_list)
    


@app.route('/appointments/<int:appointment_id>/status/<string:status>', methods=['POST'])
@login_required
@role_required(['doctor', 'admin'])
def update_appointment_status(appointment_id, status):
    """
    Update appointment status
    LOGIC:
    1. Check if appointment exists
    2. Verify user has permission (admin or assigned doctor)
    3. Validate status is allowed
    4. Update status and show feedback
    """
    appointment = appointments_db.get(appointment_id)
    
    if not appointment:
        flash('Appointment not found.', 'error')
        return redirect(url_for('appointments'))
    
    # Check permissions
    if session.get('role') != 'admin':
        doctor_data = users_db.get(session.get('username'))
        doctor_name = doctor_data.get('name') if doctor_data else None
        if appointment.get('doctor_name') != doctor_name:
            flash('You are not authorized to update this appointment.', 'error')
            return redirect(url_for('appointments'))
    
    # Validate status
    valid_statuses = ['scheduled', 'confirmed', 'cancelled', 'rejected', 'completed']
    if status not in valid_statuses:
        flash('Invalid status.', 'error')
        return redirect(url_for('appointments'))
    
    # Don't allow status changes for completed or cancelled appointments
    if appointment['status'] in ['completed', 'cancelled', 'rejected']:
        flash(f'Cannot change status of {appointment["status"]} appointment.', 'error')
        return redirect(url_for('appointments'))
    
    # Update status
    old_status = appointment['status']
    appointment['status'] = status
    appointment['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    flash(f'Appointment #{appointment_id} status changed from {old_status} to {status}.', 'success')
    return redirect(url_for('appointments'))

@app.route('/appointments/<int:appointment_id>/delete', methods=['POST'])
@login_required
@role_required(['admin'])
def delete_appointment(appointment_id):
    """
    Delete an appointment (Admin only)
    LOGIC:
    1. Check if appointment exists
    2. Verify admin permission
    3. Delete appointment from database
    4. Show feedback
    """
    if appointment_id in appointments_db:
        # Store patient name for feedback
        patient_name = appointments_db[appointment_id].get('patient_name', 'Unknown')
        del appointments_db[appointment_id]
        flash(f'Appointment for {patient_name} deleted successfully.', 'success')
    else:
        flash('Appointment not found.', 'error')
    
    return redirect(url_for('appointments'))

@app.route('/appointments/<int:appointment_id>/view')
@login_required
def view_appointment(appointment_id):
    """
    View appointment details
    LOGIC:
    1. Get appointment by ID
    2. Check user has permission to view
    3. Display appointment details
    """
    appointment = appointments_db.get(appointment_id)
    
    if not appointment:
        flash('Appointment not found.', 'error')
        return redirect(url_for('appointments'))
    
    # Check permissions
    role = session.get('role')
    username = session.get('username')
    
    if role == 'admin':
        pass  # Admin can view all
    elif role == 'doctor':
        doctor_data = users_db.get(username)
        doctor_name = doctor_data.get('name') if doctor_data else None
        if appointment.get('doctor_name') != doctor_name:
            flash('You are not authorized to view this appointment.', 'error')
            return redirect(url_for('appointments'))
    else:  # patient
        if appointment.get('patient_id') != session.get('user_id') and appointment.get('email') != session.get('email'):
            flash('You are not authorized to view this appointment.', 'error')
            return redirect(url_for('appointments'))
    
    return render_template('predictor/view_appointment.html', appointment=appointment)

@app.route('/appointments/cancel/<int:appointment_id>', methods=['POST'])
@login_required
@role_required(['doctor', 'admin'])
def cancel_appointment(appointment_id):
    appointment = appointments_db.get(appointment_id)
    if not appointment or appointment['status'] != 'scheduled':
        flash('Cannot cancel this appointment.', 'error')
        return redirect(url_for('appointments'))
    if session.get('role') != 'admin':
        doctor_data = users_db.get(session.get('username'))
        doctor_name = doctor_data.get('name') if doctor_data else None
        if appointment.get('doctor_name') != doctor_name:
            flash('You are not the assigned doctor for this appointment.', 'error')
            return redirect(url_for('appointments'))
    appointment['status'] = 'cancelled'
    flash('Appointment cancelled by staff.', 'success')
    return redirect(url_for('appointments'))

@app.route('/appointments/reject/<int:appointment_id>', methods=['POST'])
@login_required
@role_required(['doctor', 'admin'])
def reject_appointment(appointment_id):
    appointment = appointments_db.get(appointment_id)
    if not appointment or appointment['status'] != 'scheduled':
        flash('Cannot reject this appointment.', 'error')
        return redirect(url_for('appointments'))
    if session.get('role') != 'admin':
        doctor_data = users_db.get(session.get('username'))
        doctor_name = doctor_data.get('name') if doctor_data else None
        if appointment.get('doctor_name') != doctor_name:
            flash('You are not the assigned doctor for this appointment.', 'error')
            return redirect(url_for('appointments'))
    appointment['status'] = 'rejected'
    flash('Appointment rejected.', 'success')
    return redirect(url_for('appointments'))

# ---------- Public booking & cancellation ----------
@app.route('/api/check-patient', methods=['POST'])
def api_check_patient():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    if not email:
        return jsonify({'exists': False, 'name': '', 'phone': ''})
    for pid, patient in patients_db.items():
        if patient.get('email', '').lower() == email:
            return jsonify({'exists': True, 'name': patient.get('name', ''), 'phone': patient.get('phone', '')})
    for username, user in users_db.items():
        if user.get('role') == 'patient' and user.get('email', '').lower() == email:
            return jsonify({'exists': True, 'name': user.get('name', ''), 'phone': ''})
    return jsonify({'exists': False})

@app.route('/book-appointment', methods=['GET', 'POST'])
def book_appointment():
    if request.method == 'POST':
        global next_appointment_id
        patient_name = request.form.get('patient_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        doctor_name = request.form.get('doctor_name', '').strip()
        appointment_date = request.form.get('appointment_date', '').strip()
        reason = request.form.get('reason', '').strip()

        if not all([patient_name, email, phone, doctor_name, appointment_date]):
            flash('Please fill all required fields.', 'error')
            return redirect(url_for('book_appointment'))

        patient_id = None
        for pid, patient in patients_db.items():
            if patient.get('email', '').lower() == email.lower():
                patient_id = pid
                break
        if not patient_id:
            for username, user in users_db.items():
                if user.get('role') == 'patient' and user.get('email', '').lower() == email.lower():
                    patient_id = user.get('id')
                    break

        appointments_db[next_appointment_id] = {
            'id': next_appointment_id,
            'patient_id': patient_id,
            'patient_name': patient_name,
            'email': email,
            'phone': phone,
            'doctor_name': doctor_name,
            'date': appointment_date,
            'reason': reason,
            'status': 'scheduled',
            'is_guest': patient_id is None,
            'created_by': 'public',
            'cancellation_count': 0
        }
        next_appointment_id += 1

        doctor_email = None
        for username, data in users_db.items():
            if data.get('role') == 'doctor' and data.get('name') == doctor_name:
                doctor_email = data.get('email')
                break
        if not doctor_email:
            doctor_email = 'doctor@example.com'
        admin_email = 'admin@medpredict.com'

        subject = f"New Appointment Request – {patient_name}"
        body = f"""A new appointment has been booked via the public form.

Patient: {patient_name}
Email: {email}
Phone: {phone}
Doctor: {doctor_name}
Date & Time: {appointment_date}
Reason: {reason or 'Not specified'}

Please log in to confirm or cancel this appointment.

MedPredict Team
"""
        try:
            mail.send(Message(subject, recipients=[doctor_email], body=body))
            mail.send(Message(subject, recipients=[admin_email], body=body))
            flash('Appointment booked successfully!', 'success')
        except Exception as e:
            flash('Appointment booked but email notification failed.', 'warning')
        return redirect(url_for('index'))

    doctors = [{'name': data['name'], 'email': data['email']}
               for username, data in users_db.items() if data.get('role') == 'doctor']
    return render_template('predictor/book_appointment.html', doctors=doctors)

@app.route('/cancel-appointment', methods=['GET', 'POST'])
def cancel_appointment_public():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        appointment_id = request.form.get('appointment_id', '').strip()
        if not email or not appointment_id:
            flash('Please provide both email and appointment ID.', 'error')
            return redirect(url_for('cancel_appointment_public'))
        try:
            app_id = int(appointment_id)
        except ValueError:
            flash('Invalid appointment ID.', 'error')
            return redirect(url_for('cancel_appointment_public'))
        appointment = appointments_db.get(app_id)
        if not appointment:
            flash('Appointment not found.', 'error')
            return redirect(url_for('cancel_appointment_public'))
        if appointment.get('email', '').lower() != email:
            flash('Email does not match the appointment record.', 'error')
            return redirect(url_for('cancel_appointment_public'))
        if appointment['status'] != 'scheduled':
            flash('Only scheduled appointments can be cancelled.', 'error')
            return redirect(url_for('cancel_appointment_public'))
        count = cancellation_counts_by_email.get(email, 0)
        if count >= CANCELLATION_LIMIT:
            flash(f'You have reached the cancellation limit of {CANCELLATION_LIMIT} times. Please contact the clinic.', 'error')
            return redirect(url_for('cancel_appointment_public'))
        appointment['status'] = 'cancelled'
        cancellation_counts_by_email[email] = count + 1
        remaining = CANCELLATION_LIMIT - (count + 1)
        flash(f'Appointment cancelled successfully. You have {remaining} cancellation(s) remaining.', 'success')
        return redirect(url_for('index'))
    return render_template('predictor/cancel_appointment.html')

# ---------- Additional routes ----------
@app.route('/profile')
@login_required
def profile():
    user = users_db.get(session.get('username'), {})
    return render_template('predictor/profile.html', user=user)

@app.route('/comparison')
@login_required
@role_required(['doctor', 'admin'])
def comparison():
    return render_template('predictor/comparison.html', patients=list(patients_db.values()))

@app.route('/recommendations')
@login_required
@role_required(['doctor', 'admin'])
def recommendations():
    return render_template('predictor/recommendations.html')

@app.route('/notifications')
@login_required
@role_required(['doctor', 'admin'])
def notifications():
    sample_notifications = [
        {'icon': 'fa-calendar-check', 'title': 'Appointment reminder: Cardiology checkup tomorrow at 10:30 AM', 'time': '2 hours ago', 'type': 'appointment'},
        {'icon': 'fa-chart-line', 'title': 'New prediction result: Your risk score improved to 28%', 'time': 'Yesterday', 'type': 'prediction'},
        {'icon': 'fa-file-pdf', 'title': 'Monthly health report ready to download', 'time': '3 days ago', 'type': 'report'},
    ]
    return render_template('predictor/notifications.html', notifications=sample_notifications)

# ===================================================================
# SIDEBAR BUTTONS ROUTES - FEEDBACK, REPORT, REPORT PREVIEW (FIXED)
# ===================================================================
# ===================================================================
# SIDEBAR BUTTONS ROUTES - FEEDBACK, REPORT, REPORT PREVIEW (FIXED)
# ===================================================================

@app.route('/feedback')
@login_required
@role_required(['doctor', 'admin'])
def feedback():
    """
    Render the feedback page with data
    Logic: Fetches all predictions, generates feedback entries with random ratings,
    calculates statistics (total, average rating, positive rate)
    """
    feedback_list = []
    
    # Loop through all predictions to generate feedback data
    for pred_id, pred in predictions_db.items():
        patient_name = pred.get('patient_name', 'Unknown')
        patient_id = pred.get('patient_id')
        patient = patients_db.get(patient_id, {}) if patient_id else {}
        
        # Create a feedback entry for each prediction
        feedback_list.append({
            'id': pred_id,
            'patient_name': patient_name,
            'rating': random.randint(3, 5),  # Simulated rating
            'comment': random.choice([
                "Excellent care and attention from the medical team",
                "Very professional staff, quick service",
                "The appointment system is very convenient",
                "Doctor explained everything clearly",
                "Clean facility, friendly reception",
                "Great experience overall",
                "Would recommend to others",
                "Very thorough examination"
            ]),
            'category': random.choice(['Service Quality', 'Doctor Communication', 'Wait Times', 'Facility Cleanliness', 'Appointment System']),
            'date': pred.get('date', datetime.now().strftime('%Y-%m-%d'))
        })
    
    # Calculate statistics
    total = len(feedback_list)
    avg_rating = round(sum(f['rating'] for f in feedback_list) / total, 1) if total > 0 else 0
    positive_count = sum(1 for f in feedback_list if f['rating'] >= 4)
    positive_rate = round((positive_count / total) * 100) if total > 0 else 0
    
    # Return rendered template with data
    return render_template('predictor/feedback_page.html',
                           feedbacks=feedback_list,
                           total_feedback=total,
                           avg_rating=avg_rating,
                           positive_rate=positive_rate)

@app.route('/report', methods=['GET', 'POST'])
@login_required
@role_required(['doctor', 'admin'])
def report():
    """
    Generate Report Page - Shows form to select patient and generate new report
    Logic: 
    - GET: Display patient selection form and recent reports
    - POST: Generate new report for selected patient
    """
    patients_list = list(patients_db.values())
    recent_predictions = list(predictions_db.values())[:5]
    
    # Get latest reports for display
    reports = []
    for pred_id, pred in list(predictions_db.items())[:10]:
        patient_id = pred.get('patient_id')
        patient = patients_db.get(patient_id, {}) if patient_id else {}
        reports.append({
            'id': pred_id,
            'patient_name': pred.get('patient_name', 'Unknown'),
            'risk_level': pred.get('risk_level', 'Unknown'),
            'probability': pred.get('probability', 0),
            'date': pred.get('date', 'N/A'),
            'recommendation': pred.get('recommendation', '')
        })
    
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        if patient_id:
            try:
                patient_id = int(patient_id)
                patient = patients_db.get(patient_id)
                if patient:
                    global next_prediction_id
                    pred_id = next_prediction_id
                    
                    # Get patient data for risk calculation
                    age = patient.get('age', 50)
                    gender = patient.get('gender', 'M')
                    smoking = patient.get('smoking_status', 'Never')
                    
                    # Calculate risk
                    risk_level, risk_class, probability, recommendation = calculate_risk(
                        age, 
                        random.randint(110, 160),
                        random.randint(70, 95),
                        smoking.lower()
                    )
                    
                    # Save prediction
                    predictions_db[pred_id] = {
                        'id': pred_id,
                        'patient_id': patient_id,
                        'patient_name': patient.get('name', 'Unknown'),
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'risk_level': risk_level,
                        'risk_class': risk_class,
                        'probability': probability,
                        'recommendation': recommendation,
                        'age': age,
                        'gender': gender,
                        'smoking': smoking,
                        'bmi': patient.get('bmi', 25),
                        'systolic_bp': random.randint(110, 160),
                        'diastolic_bp': random.randint(70, 95),
                        'total_cholesterol': random.randint(150, 250),
                        'hdl': random.randint(30, 60),
                        'diabetic': random.choice([True, False]),
                        'family_history': random.choice([True, False]),
                        'framingham': random.randint(5, 25),
                        'ascvd': random.randint(4, 20),
                        'qrisk3': random.randint(5, 22)
                    }
                    next_prediction_id += 1
                    
                    flash(f'Report generated for {patient.get("name")}!', 'success')
                    return redirect(url_for('view_report_preview', prediction_id=pred_id))
            except Exception as e:
                flash(f'Error generating report: {str(e)}', 'error')
    
    return render_template('predictor/report_page.html',
                           patients=patients_list,
                           predictions=recent_predictions,
                           reports=reports)

@app.route('/report-preview')
@login_required
@role_required(['doctor', 'admin'])
def report_preview():
    """
    Report Preview Page - Shows list of all available reports with preview
    Logic: Fetches all predictions and formats them for preview display
    """
    preview_data = []
    for pred_id, pred in list(predictions_db.items())[:20]:
        patient = patients_db.get(pred.get('patient_id'), {}) if pred.get('patient_id') else {}
        
        preview_data.append({
            'id': pred_id,
            'patient_name': pred.get('patient_name', 'Unknown'),
            'age': pred.get('age', patient.get('age', 'N/A')),
            'gender': pred.get('gender', patient.get('gender', 'N/A')),
            'risk_level': pred.get('risk_level', 'Unknown'),
            'probability': pred.get('probability', 0),
            'date': pred.get('date', 'N/A'),
            'recommendation': pred.get('recommendation', ''),
            'framingham': pred.get('framingham', 0),
            'ascvd': pred.get('ascvd', 0),
            'qrisk3': pred.get('qrisk3', 0),
            'systolic_bp': pred.get('systolic_bp', 'N/A'),
            'diastolic_bp': pred.get('diastolic_bp', 'N/A'),
            'total_cholesterol': pred.get('total_cholesterol', 'N/A'),
            'hdl': pred.get('hdl', 'N/A'),
            'bmi': pred.get('bmi', patient.get('bmi', 'N/A'))
        })
    
    preview_data.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    return render_template('predictor/report_preview_page.html',
                           reports=preview_data,
                           generated_on=datetime.now().strftime('%Y-%m-%d %H:%M'))


# ===================================================================
# API ENDPOINTS FOR AJAX BUTTONS (FIXED)
# ===================================================================
# ===================================================================
# API ENDPOINTS FOR AJAX BUTTONS
# ===================================================================

@app.route('/api/feedback/', methods=['GET'])
@login_required
def get_feedback_api():
    """
    API endpoint to get patient feedback data
    Logic: Returns feedback data as JSON for AJAX calls
    """
    try:
        # Generate feedback data from predictions
        feedback_list = []
        for pred_id, pred in predictions_db.items():
            patient_name = pred.get('patient_name', 'Unknown')
            patient_id = pred.get('patient_id')
            patient = patients_db.get(patient_id, {}) if patient_id else {}
            
            feedback_list.append({
                'patient_name': patient_name,
                'rating': random.randint(3, 5),
                'comment': random.choice([
                    "Excellent care and attention from Dr. Smith",
                    "Very professional staff, quick service",
                    "The new appointment system is very convenient",
                    "Doctor explained everything clearly",
                    "Clean facility, friendly reception",
                    "Great experience overall",
                    "Would recommend to others"
                ]),
                'category': random.choice(['Service Quality', 'Doctor Communication', 'Wait Times', 'Facility Cleanliness']),
                'date': pred.get('date', datetime.now().strftime('%Y-%m-%d'))
            })
        
        return jsonify({
            'feedbacks': feedback_list,
            'count': len(feedback_list)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/feedback/report/', methods=['GET'])
@login_required
def get_feedback_report_api():
    """
    API endpoint to get comprehensive feedback report
    Logic: Returns aggregated feedback statistics as JSON
    """
    try:
        total_predictions = len(predictions_db)
        
        # Simulate feedback report data
        report_data = {
            'total_feedback': total_predictions,
            'avg_rating': 4.5,
            'positive_rate': 85,
            'response_rate': 92,
            'categories': {
                'Service Quality': 4.6,
                'Doctor Communication': 4.8,
                'Wait Times': 4.2,
                'Facility Cleanliness': 4.7
            },
            'recent_comments': [
                'Excellent care and attention from Dr. Smith',
                'Very professional staff, quick service',
                'The new appointment system is very convenient',
                'Doctor took time to explain everything clearly',
                'Clean and well-maintained facility'
            ],
            'insights': [
                'Patient satisfaction has increased by 12% this quarter',
                'Doctor communication scores highest at 4.8/5',
                'Average response time to feedback: 2.3 hours',
                'Most common suggestion: More weekend appointments',
                'Service quality rating improved by 8% compared to last quarter'
            ]
        }
        return jsonify(report_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/dashboard/refresh/', methods=['GET'])
@login_required
def refresh_dashboard():
    """
    API endpoint to refresh dashboard data
    Logic: Returns updated dashboard statistics including trend data
    """
    try:
        total_predictions = len(predictions_db)
        total_patients = len(patients_db)
        high_risk = sum(1 for p in predictions_db.values() if p.get('risk_level') == 'High')
        
        # Calculate daily average risk trend
        daily_avg = defaultdict(list)
        for pred in predictions_db.values():
            daily_avg[pred['date']].append(pred['probability'])
        sorted_dates = sorted(daily_avg.keys())
        trend_data = [round(sum(daily_avg[d])/len(daily_avg[d]),1) for d in sorted_dates] if sorted_dates else [0]
        if not trend_data:
            sorted_dates = ['No data']
            trend_data = [0]
        
        # Calculate monthly prediction volume
        monthly_counts = defaultdict(int)
        for p in predictions_db.values():
            date_str = p.get('date', '')
            if date_str:
                monthly_counts[date_str[:7]] += 1
        volume_labels = sorted(monthly_counts.keys())
        volume_counts = [monthly_counts[m] for m in volume_labels]
        
        if not volume_labels:
            volume_labels = ['No data']
            volume_counts = [0]
        
        return jsonify({
            'total_predictions': total_predictions,
            'high_risk': high_risk,
            'total_patients': total_patients,
            'trend_labels': sorted_dates,
            'trend_data': trend_data,
            'volume_labels': volume_labels,
            'volume_counts': volume_counts
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/generate_report/<int:prediction_id>')
@login_required
@role_required(['doctor', 'admin'])
def generate_report(prediction_id):
    """
    Generate PDF report with PROFESSIONAL MEDICAL REPORT DESIGN
    FIXED: Properly handles null values and missing data
    """
    if not REPORTLAB_AVAILABLE:
        flash('PDF generation requires ReportLab. Please install: pip install reportlab', 'error')
        return redirect(url_for('view_report_preview', prediction_id=prediction_id))
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        import io
        
        pred = predictions_db.get(prediction_id)
        if not pred:
            flash('Prediction not found', 'error')
            return redirect(url_for('reports'))
        
        patient = patients_db.get(pred.get('patient_id'), {})
        
        # ============ HELPER FUNCTION TO GET VALUE WITH DEFAULT ============
        def get_val(key, default='N/A'):
            """Safely get value from pred or patient dict"""
            if key in pred and pred[key] is not None and pred[key] != '':
                return pred[key]
            if key in patient and patient[key] is not None and patient[key] != '':
                return patient[key]
            return default
        
        def get_int_val(key, default='N/A'):
            """Safely get integer value"""
            val = get_val(key, None)
            if val is not None and val != 'N/A':
                try:
                    return int(val)
                except:
                    return default
            return default
        
        # ============ GET ALL VALUES SAFELY ============
        patient_name = get_val('patient_name', 'Unknown Patient')
        patient_id = get_val('patient_id', 'N/A')
        age = get_val('age', 'N/A')
        gender = get_val('gender', 'N/A')
        email = get_val('email', 'N/A')
        phone = get_val('phone', 'N/A')
        address = get_val('address', 'N/A')
        medical_history = get_val('medical_history', 'None reported')
        smoking_status = get_val('smoking_status', 'Not recorded')
        bmi = get_val('bmi', 'N/A')
        diabetic = pred.get('diabetic', False)
        family_history = pred.get('family_history', False)
        
        # Risk values
        risk_level = get_val('risk_level', 'Unknown')
        probability = get_val('probability', 0)
        framingham = get_val('framingham', 0)
        ascvd = get_val('ascvd', 0)
        qrisk3 = get_val('qrisk3', 0)
        
        # Vital signs - with proper defaults
        systolic_bp = get_int_val('systolic_bp', 'N/A')
        diastolic_bp = get_int_val('diastolic_bp', 'N/A')
        total_cholesterol = get_int_val('total_cholesterol', 'N/A')
        hdl = get_int_val('hdl', 'N/A')
        bmi_val = get_val('bmi', 'N/A')
        
        # Recommendation
        recommendation = get_val('recommendation', 'No specific recommendation')
        
        # ============ CREATE PDF ============
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=72)
        
        styles = getSampleStyleSheet()
        
        # Custom styles
        main_title_style = ParagraphStyle(
            'MainTitle',
            parent=styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#1a237e'),
            alignment=TA_CENTER,
            spaceAfter=5,
            fontName='Helvetica-Bold'
        )
        
        sub_title_style = ParagraphStyle(
            'SubTitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        section_style = ParagraphStyle(
            'SectionStyle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#0d47a1'),
            spaceAfter=8,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        subsection_style = ParagraphStyle(
            'SubSectionStyle',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#1565c0'),
            spaceAfter=6,
            spaceBefore=8,
            fontName='Helvetica-Bold'
        )
        
        label_style = ParagraphStyle(
            'LabelStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#1a237e'),
            fontName='Helvetica-Bold',
            alignment=TA_LEFT
        )
        
        value_style = ParagraphStyle(
            'ValueStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            fontName='Helvetica',
            alignment=TA_LEFT
        )
        
        normal_style = ParagraphStyle(
            'NormalStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            spaceAfter=4,
            fontName='Helvetica'
        )
        
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#999999'),
            alignment=TA_CENTER,
            spaceTop=20
        )
        
        story = []
        
        # Header
        story.append(Paragraph("MEDPREDICT", main_title_style))
        story.append(Paragraph("Clinical Decision Support System", sub_title_style))
        story.append(Paragraph("Comprehensive Clinical Report", 
                              ParagraphStyle('ReportTitle', parent=styles['Normal'], 
                                            fontSize=16, textColor=colors.HexColor('#0d47a1'), 
                                            alignment=TA_CENTER, spaceAfter=15)))
        
        story.append(Table([['']], colWidths=[6.5*inch], 
                          style=TableStyle([('LINEABOVE', (0, 0), (-1, -1), 1, colors.HexColor('#1a237e'))])))
        story.append(Spacer(1, 10))
        
        # Report Info
        report_info = [
            [Paragraph(f"<b>Report ID:</b> RPT-{prediction_id:06d}", normal_style)],
            [Paragraph(f"<b>Date Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", normal_style)],
            [Paragraph(f"<b>Generated By:</b> {session.get('user_name', 'MedPredict System')}", normal_style)]
        ]
        info_table = Table(report_info, colWidths=[6.5*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 15))
        
        # Patient Information
        story.append(Paragraph("PATIENT INFORMATION", section_style))
        
        patient_data = [
            [Paragraph("<b>Patient Name:</b>", label_style), Paragraph(str(patient_name), value_style)],
            [Paragraph("<b>Patient ID:</b>", label_style), Paragraph(str(patient_id), value_style)],
            [Paragraph("<b>Age:</b>", label_style), Paragraph(str(age), value_style)],
            [Paragraph("<b>Gender:</b>", label_style), Paragraph(str(gender), value_style)],
            [Paragraph("<b>Email:</b>", label_style), Paragraph(str(email), value_style)],
            [Paragraph("<b>Phone:</b>", label_style), Paragraph(str(phone), value_style)],
            [Paragraph("<b>Address:</b>", label_style), Paragraph(str(address), value_style)]
        ]
        
        patient_table = Table(patient_data, colWidths=[1.8*inch, 4.7*inch])
        patient_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8eaf6')),
            ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#fafafa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a237e')),
        ]))
        story.append(patient_table)
        story.append(Spacer(1, 15))
        
        # Medical History
        story.append(Paragraph("MEDICAL HISTORY", section_style))
        
        history_data = [
            [Paragraph("<b>Medical History:</b>", label_style), Paragraph(str(medical_history), value_style)],
            [Paragraph("<b>Smoking Status:</b>", label_style), Paragraph(str(smoking_status), value_style)],
            [Paragraph("<b>BMI:</b>", label_style), Paragraph(str(bmi), value_style)],
            [Paragraph("<b>Diabetic:</b>", label_style), Paragraph("Yes" if diabetic else "No", value_style)],
            [Paragraph("<b>Family History of CVD:</b>", label_style), Paragraph("Yes" if family_history else "No", value_style)]
        ]
        
        history_table = Table(history_data, colWidths=[1.8*inch, 4.7*inch])
        history_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3e5f5')),
            ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#fafafa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4a148c')),
        ]))
        story.append(history_table)
        story.append(Spacer(1, 15))
        
        # Risk Assessment
        story.append(Paragraph("RISK ASSESSMENT", section_style))
        
        risk_color = '#c62828' if risk_level == 'High' else '#e65100' if risk_level == 'Medium' else '#2e7d32'
        risk_bg_color = '#ffebee' if risk_level == 'High' else '#fff3e0' if risk_level == 'Medium' else '#e8f5e9'
        
        risk_data = [
            [Paragraph("<b>Risk Level:</b>", label_style), 
             Paragraph(f"<font color='{risk_color}'><b>{risk_level}</b></font>", 
                      ParagraphStyle('RiskText', parent=styles['Normal'], fontSize=12, fontName='Helvetica-Bold'))],
            [Paragraph("<b>Risk Probability:</b>", label_style), 
             Paragraph(f"<b>{probability}%</b>", value_style)],
            [Paragraph("<b>Framingham Score:</b>", label_style), 
             Paragraph(f"{framingham}%", value_style)],
            [Paragraph("<b>ASCVD Score:</b>", label_style), 
             Paragraph(f"{ascvd}%", value_style)],
            [Paragraph("<b>QRISK3 Score:</b>", label_style), 
             Paragraph(f"{qrisk3}%", value_style)]
        ]
        
        risk_table = Table(risk_data, colWidths=[1.8*inch, 4.7*inch])
        risk_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor(risk_bg_color)),
            ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#fafafa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a237e')),
        ]))
        story.append(risk_table)
        story.append(Spacer(1, 15))
        
        # Vital Signs
        story.append(Paragraph("VITAL SIGNS", section_style))
        
        # Helper function to get status
        def get_status(value, normal_min, normal_max, unit=''):
            if value == 'N/A' or value is None:
                return "N/A"
            try:
                val = float(value)
                if val < normal_min:
                    return "Low"
                elif val > normal_max:
                    return "High"
                else:
                    return "Normal"
            except:
                return "N/A"
        
        # Get status for each vital
        sbp_status = get_status(systolic_bp, 90, 120)
        dbp_status = get_status(diastolic_bp, 60, 80)
        chol_status = get_status(total_cholesterol, 125, 200)
        hdl_status = "Low" if (hdl != 'N/A' and hdl is not None and hdl < 40) else "Normal" if (hdl != 'N/A' and hdl is not None and hdl >= 40) else "N/A"
        bmi_status = "Normal" if (bmi_val != 'N/A' and bmi_val is not None and bmi_val < 25) else "High" if (bmi_val != 'N/A' and bmi_val is not None and bmi_val >= 25) else "N/A"
        
        vital_data = [
            ["Parameter", "Value", "Status"],
            ["Systolic BP", f"{systolic_bp} mmHg", sbp_status],
            ["Diastolic BP", f"{diastolic_bp} mmHg", dbp_status],
            ["Total Cholesterol", f"{total_cholesterol} mg/dL", chol_status],
            ["HDL Cholesterol", f"{hdl} mg/dL", hdl_status],
            ["BMI", str(bmi_val), bmi_status]
        ]
        
        vital_table = Table(vital_data, colWidths=[2*inch, 2*inch, 2.5*inch])
        vital_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d47a1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fafafa'), colors.HexColor('#f5f5f5')]),
        ]))
        story.append(vital_table)
        story.append(Spacer(1, 15))
        
        # Risk Factors
        story.append(Paragraph("RISK FACTORS IDENTIFIED", section_style))
        
        risk_factors = []
        if age != 'N/A' and age is not None:
            try:
                if int(age) > 55:
                    risk_factors.append("• Age > 55 years")
            except:
                pass
        if smoking_status in ('Current', 'current', 'Former', 'former'):
            risk_factors.append(f"• {smoking_status} smoker")
        if bmi_val != 'N/A' and bmi_val is not None:
            try:
                bmi_float = float(bmi_val)
                if bmi_float > 30:
                    risk_factors.append(f"• Obesity (BMI {bmi_float})")
                elif bmi_float > 25:
                    risk_factors.append(f"• Overweight (BMI {bmi_float})")
            except:
                pass
        if diabetic:
            risk_factors.append("• Diabetes")
        if family_history:
            risk_factors.append("• Family history of CVD")
        if systolic_bp != 'N/A' and systolic_bp is not None:
            try:
                if int(systolic_bp) > 140:
                    risk_factors.append(f"• Elevated systolic BP ({systolic_bp} mmHg)")
            except:
                pass
        if total_cholesterol != 'N/A' and total_cholesterol is not None:
            try:
                if int(total_cholesterol) > 200:
                    risk_factors.append(f"• Elevated cholesterol ({total_cholesterol} mg/dL)")
            except:
                pass
        if hdl != 'N/A' and hdl is not None:
            try:
                if int(hdl) < 40:
                    risk_factors.append(f"• Low HDL ({hdl} mg/dL)")
            except:
                pass
        
        if risk_factors:
            for factor in risk_factors:
                story.append(Paragraph(factor, normal_style))
        else:
            story.append(Paragraph("No significant risk factors identified", normal_style))
        story.append(Spacer(1, 10))
        
        # Recommendation
        story.append(Paragraph("RECOMMENDATION", section_style))
        
        rec_data = [[Paragraph(str(recommendation), 
                              ParagraphStyle('RecText', parent=styles['Normal'], fontSize=11, 
                                            textColor=colors.HexColor('#1a237e'), alignment=TA_LEFT))]]
        rec_table = Table(rec_data, colWidths=[6.5*inch])
        rec_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e3f2fd')),
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#0d47a1')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 12),
        ]))
        story.append(rec_table)
        story.append(Spacer(1, 15))
        
        # Treatment Plan
        story.append(Paragraph("TREATMENT PLAN", section_style))
        
        # Lifestyle Modifications
        story.append(Paragraph("Lifestyle Modifications:", subsection_style))
        lifestyle_items = [
            "• Adopt a heart-healthy diet (Mediterranean or DASH diet)",
            "• Regular physical activity (≥150 minutes of moderate exercise per week)",
            "• Maintain healthy weight (target BMI < 25)"
        ]
        if smoking_status in ('Current', 'current'):
            lifestyle_items.append("• Smoking cessation – enrol in a cessation programme")
        if bmi_val != 'N/A' and bmi_val is not None:
            try:
                if float(bmi_val) > 30:
                    lifestyle_items.append("• Weight management – consider referral to dietitian")
            except:
                pass
        
        for item in lifestyle_items:
            story.append(Paragraph(item, normal_style))
        story.append(Spacer(1, 8))
        
        # Pharmacotherapy
        story.append(Paragraph("Pharmacotherapy:", subsection_style))
        meds = []
        if risk_level == 'High':
            meds.append("• Statin therapy (e.g., atorvastatin 20-80 mg) – high intensity")
            meds.append("• Low-dose aspirin (75-100 mg daily) – consider after risk/benefit")
            if systolic_bp != 'N/A' and systolic_bp is not None:
                try:
                    if int(systolic_bp) > 140:
                        meds.append("• Antihypertensive therapy (ACEi/ARB, CCB, or thiazide)")
                except:
                    pass
            if diabetic:
                meds.append("• Glycaemic control – optimize metformin or other agents")
        elif risk_level == 'Medium':
            meds.append("• Consider moderate-intensity statin (e.g., atorvastatin 10-20 mg)")
            meds.append("• Evaluate aspirin therapy based on risk/benefit")
        else:
            meds.append("• No pharmacotherapy indicated at this time")
            meds.append("• Continue monitoring and re-assess annually")
        
        for med in meds:
            story.append(Paragraph(med, normal_style))
        story.append(Spacer(1, 8))
        
        # Follow-up Schedule
        story.append(Paragraph("Follow-up Schedule:", subsection_style))
        follow_ups = []
        if risk_level == 'High':
            follow_ups.append("• Cardiology consultation within 2 weeks")
            follow_ups.append("• Re-assess risk in 1 month")
            follow_ups.append("• Regular follow-up every 3 months")
        elif risk_level == 'Medium':
            follow_ups.append("• Cardiology consultation within 1 month")
            follow_ups.append("• Re-assess risk in 3 months")
            follow_ups.append("• Annual follow-up thereafter")
        else:
            follow_ups.append("• Routine annual check-up")
            follow_ups.append("• Re-assess risk in 12 months")
        
        for follow_up in follow_ups:
            story.append(Paragraph(follow_up, normal_style))
        story.append(Spacer(1, 8))
        
        # Patient Education
        story.append(Paragraph("Patient Education:", subsection_style))
        education_items = [
            "• Explain risk factors and the importance of adherence",
            "• Provide educational materials on heart-healthy living",
            "• Discuss warning signs (chest pain, SOB, palpitations)"
        ]
        for item in education_items:
            story.append(Paragraph(item, normal_style))
        story.append(Spacer(1, 15))
        
        # Clinical Insights
        story.append(Paragraph("CLINICAL INSIGHTS", section_style))
        
        insights = []
        if age != 'N/A' and age is not None:
            try:
                if int(age) > 60:
                    insights.append("• Age > 60 – elevated risk.")
                elif int(age) > 50:
                    insights.append("• Age > 50 – moderate risk.")
            except:
                pass
        if risk_level == 'High':
            insights.append("• HIGH RISK – urgent cardiology involvement required.")
        elif risk_level == 'Medium':
            insights.append("• MODERATE RISK – consider specialist referral.")
        else:
            insights.append("• LOW RISK – continue preventive measures.")
        if bmi_val != 'N/A' and bmi_val is not None:
            try:
                if float(bmi_val) > 30:
                    insights.append(f"• BMI {bmi_val} – obesity; weight management is key.")
            except:
                pass
        if smoking_status in ('Current', 'current'):
            insights.append("• Smoking cessation – top priority.")
        if not insights:
            insights.append("• No additional insights.")
        
        for insight in insights:
            story.append(Paragraph(insight, normal_style))
        story.append(Spacer(1, 20))
        
        # Footer
        story.append(Table([['']], colWidths=[6.5*inch], 
                          style=TableStyle([('LINEABOVE', (0, 0), (-1, -1), 1, colors.HexColor('#1a237e'))])))
        story.append(Spacer(1, 10))
        
        story.append(Paragraph("This report is generated by MedPredict Clinical Decision Support System", 
                              footer_style))
        story.append(Paragraph(f"© {datetime.now().year} MedPredict Healthcare. All rights reserved.", 
                              footer_style))
        story.append(Paragraph("Confidential - For Medical Use Only", 
                              ParagraphStyle('Confidential', parent=styles['Normal'], 
                                            fontSize=8, textColor=colors.HexColor('#c62828'), 
                                            alignment=TA_CENTER, spaceTop=5)))
        
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"MedPredict_Report_{prediction_id}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"PDF Generation Error: {str(e)}")
        flash(f'Error generating PDF: {str(e)}', 'error')
        return redirect(url_for('view_report_preview', prediction_id=prediction_id))

@app.route('/api/preview-report', methods=['GET'])
@login_required
def preview_report_api():
    """API endpoint to get report preview"""
    try:
        # Get sample preview data
        preview_data = {
            'patient_name': 'John Doe',
            'patient_id': 'P-2026-001',
            'age': '45',
            'gender': 'Male',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'doctor': 'Dr. Sarah Johnson',
            'diagnosis': 'Hypertension with mild cardiovascular risk (DRAFT)',
            'tests': [
                {'name': 'Blood Pressure', 'result': '120/80 mmHg', 'status': 'Normal'},
                {'name': 'Cholesterol', 'result': '180 mg/dL', 'status': 'Normal'},
                {'name': 'Blood Sugar', 'result': '140 mg/dL', 'status': 'High'},
                {'name': 'BMI', 'result': '27.5', 'status': 'High'},
                {'name': 'ECG', 'result': 'Normal sinus rhythm', 'status': 'Normal'}
            ],
            'recommendations': [
                'Follow up with cardiology specialist (PREVIEW)',
                'Maintain healthy diet and exercise routine',
                'Schedule regular blood pressure monitoring'
            ],
            'medical_history': 'None reported',
            'smoking_status': 'Former',
            'report_id': 'RPT-PREVIEW-' + str(datetime.now().timestamp()).replace('.', '')[-6:]
        }
        
        return jsonify({
            'success': True,
            'report': preview_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/generate-feedback', methods=['POST'])
@login_required
def generate_feedback_api():
    """API endpoint to generate feedback report"""
    try:
        # Get feedback data from predictions
        feedback_list = []
        for pred_id, pred in predictions_db.items():
            patient_id = pred.get('patient_id')
            patient = patients_db.get(patient_id, {}) if patient_id else {}
            
            feedback_list.append({
                'rating': random.randint(3, 5),
                'comment': random.choice([
                    "Excellent care and attention",
                    "Very professional staff",
                    "The appointment system is very convenient",
                    "Doctor explained everything clearly",
                    "Clean facility, friendly reception",
                    "Great experience overall",
                    "Would recommend to others",
                    "Very thorough examination"
                ]),
                'category': random.choice(['Service Quality', 'Doctor Communication', 'Wait Times', 'Facility Cleanliness']),
                'date': pred.get('date', datetime.now().strftime('%Y-%m-%d'))
            })
        
        # Calculate statistics
        total = len(feedback_list)
        avg_rating = round(sum(f['rating'] for f in feedback_list) / total, 1) if total > 0 else 0
        positive_count = sum(1 for f in feedback_list if f['rating'] >= 4)
        positive_rate = round((positive_count / total) * 100) if total > 0 else 0
        
        feedback_data = {
            'total_feedback': total,
            'avg_rating': avg_rating,
            'positive_rate': positive_rate,
            'response_rate': 92,
            'categories': {
                'Service Quality': 4.6,
                'Doctor Communication': 4.8,
                'Wait Times': 4.2,
                'Facility Cleanliness': 4.7
            },
            'recent_comments': [
                "Excellent care and attention from Dr. Smith",
                "Very professional staff, quick service",
                "The new appointment system is very convenient",
                "Dr. Johnson explained everything clearly",
                "Clean facility, friendly reception"
            ],
            'insights': [
                'Patient satisfaction has increased by 12% this quarter',
                'Doctor communication scores highest at 4.8/5',
                'Average response time to feedback: 2.3 hours',
                'Most common suggestion: More weekend appointments'
            ]
        }
        
        return jsonify({
            'success': True,
            'feedback': feedback_data,
            'report_id': 'FDBK-' + str(datetime.now().timestamp()).replace('.', '')[-6:]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/preview-feedback', methods=['GET'])
@login_required
def preview_feedback_api():
    """API endpoint to preview feedback report"""
    try:
        preview_data = {
            'total_feedback': 156,
            'avg_rating': 4.5,
            'positive_rate': 85,
            'response_rate': 92,
            'categories': {
                'Service Quality': 4.6,
                'Doctor Communication': 4.8,
                'Wait Times': 4.2,
                'Facility Cleanliness': 4.7
            },
            'recent_comments': [
                "Excellent care and attention from Dr. Smith",
                "Very professional staff, quick service",
                "The new appointment system is very convenient"
            ],
            'insights': [
                'Patient satisfaction has increased by 12% this quarter',
                'Doctor communication scores highest at 4.8/5',
                'Average response time to feedback: 2.3 hours'
            ]
        }
        
        return jsonify({
            'success': True,
            'feedback': preview_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/get-feedback', methods=['GET'])
@login_required
def get_feedback_list_api():
    """API endpoint to get feedback data"""
    try:
        # Get feedback data from predictions
        feedback_list = []
        for pred_id, pred in predictions_db.items():
            patient_id = pred.get('patient_id')
            patient = patients_db.get(patient_id, {}) if patient_id else {}
            
            feedback_list.append({
                'id': pred_id,
                'rating': random.randint(3, 5),
                'comment': random.choice([
                    "Excellent care and attention",
                    "Very professional staff",
                    "The appointment system is very convenient",
                    "Doctor explained everything clearly",
                    "Clean facility, friendly reception"
                ]),
                'category': random.choice(['Service Quality', 'Doctor Communication', 'Wait Times', 'Facility Cleanliness']),
                'date': pred.get('date', datetime.now().strftime('%Y-%m-%d'))
            })
        
        return jsonify({
            'success': True,
            'feedbacks': feedback_list,
            'count': len(feedback_list)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/search')
@login_required
@role_required(['doctor', 'admin'])
def search_records():
    query = request.args.get('q', '').strip()
    risk_filter = request.args.get('risk', '')
    from_date = request.args.get('from', '')
    to_date = request.args.get('to', '')
    patients_list = list(patients_db.values())
    if query:
        patients_list = [p for p in patients_list
                         if query.lower() in p.get('name', '').lower()
                         or query.lower() in p.get('phone', '').lower()
                         or query.lower() in p.get('email', '').lower()]
    results = []
    for patient in patients_list:
        patient_id = patient.get('id')
        preds = [p for p in predictions_db.values() if p.get('patient_id') == patient_id]
        if not preds:
            continue
        latest_pred = max(preds, key=lambda x: x.get('date', ''))
        if risk_filter and latest_pred.get('risk_level') != risk_filter:
            continue
        pred_date = latest_pred.get('date', '')
        if from_date and pred_date < from_date:
            continue
        if to_date and pred_date > to_date:
            continue
        results.append({'patient': patient, 'latest_prediction': latest_pred})
    return render_template('predictor/search_records.html', results=results, query=query,
                           risk_filter=risk_filter, from_date=from_date, to_date=to_date)

@app.route('/about')
def about():
    return render_template('predictor/about.html', trend_labels=[], trend_data=[])

@app.route('/contact')
def contact():
    return render_template('predictor/contact.html')

@app.route('/contact_submit', methods=['POST'])
def contact_submit():
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']
    try:
        user_msg = Message("We received your message – MedPredict", recipients=[email],
                           body=f"Dear {name},\n\nThank you for contacting MedPredict...")
        mail.send(user_msg)
        admin_msg = Message(f"New contact from {name}", recipients=[app.config['MAIL_USERNAME']],
                            body=f"Name: {name}\nEmail: {email}\nMessage:\n{message}")
        mail.send(admin_msg)
        flash('Message sent. Confirmation email sent.', 'success')
    except Exception as e:
        flash('Message received but email failed.', 'warning')
    return redirect(url_for('index'))

@app.route('/terms')
def terms():
    return render_template('predictor/terms.html')

@app.route('/privacy')
def privacy():
    return render_template('predictor/privacy.html')

# ---------- API endpoints ----------
@app.route('/api/patients')
@login_required
@role_required(['doctor', 'admin'])
def api_patients():
    return jsonify(list(patients_db.values()))

@app.route('/api/reports')
@login_required
@role_required(['doctor', 'admin'])
def api_reports():
    return jsonify(list(predictions_db.values()))

@app.route('/api/compare/<int:pid1>/<int:pid2>')
@login_required
@role_required(['doctor', 'admin'])
def api_compare(pid1, pid2):
    p1 = patients_db.get(pid1)
    p2 = patients_db.get(pid2)
    if not p1 or not p2:
        return jsonify({'error': 'Patient not found'}), 404
    return jsonify({'patient_a': p1, 'patient_b': p2})

@app.route('/api/all_predictions')
@login_required
@role_required(['doctor', 'admin'])
def api_all_predictions():
    return jsonify(list(predictions_db.values()))

@app.route('/api/high_risk_patients')
@login_required
@role_required(['doctor', 'admin'])
def api_high_risk_patients():
    high_risk = [p for p in predictions_db.values() if p['risk_level'] == 'High']
    return jsonify(high_risk)

@app.route('/api/all_patients')
@login_required
@role_required(['doctor', 'admin'])
def api_all_patients():
    result = []
    patient_risk_map = {}
    for p in predictions_db.values():
        pid = p.get('patient_id')
        if pid:
            risk = p.get('probability', 0)
            if pid not in patient_risk_map or risk > patient_risk_map[pid]['risk']:
                patient_risk_map[pid] = {
                    'risk': risk,
                    'name': p.get('patient_name', 'Unknown'),
                    'smoking': p.get('smoking', 'N/A'),
                    'bmi': p.get('bmi', 'N/A'),
                    'age': p.get('age', 'N/A'),
                    'gender': p.get('gender', 'N/A')
                }
    for pid, patient in patients_db.items():
        info = patient_risk_map.get(pid)
        if info:
            result.append({
                'id': patient.get('id'),
                'name': info['name'],
                'age': info['age'],
                'gender': info['gender'],
                'phone': patient.get('phone', 'N/A'),
                'email': patient.get('email', 'N/A'),
                'smoking': info['smoking'],
                'bmi': info['bmi'],
                'latest_risk': f"{info['risk']:.1f}%"
            })
        else:
            result.append({
                'id': patient.get('id'),
                'name': patient.get('name', 'N/A'),
                'age': patient.get('age', 'N/A'),
                'gender': patient.get('gender', 'N/A'),
                'phone': patient.get('phone', 'N/A'),
                'email': patient.get('email', 'N/A'),
                'smoking': 'N/A',
                'bmi': 'N/A',
                'latest_risk': '—'
            })
    return jsonify(result)

# -------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)