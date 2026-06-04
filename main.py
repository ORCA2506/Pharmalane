from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime
import numpy as np
import pandas as pd
import pickle
import uuid
import os
import requests
from groq import Groq
import razorpay
import hmac
import hashlib
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'pharmalane-dev-key-change-in-prod')

# Use PostgreSQL in production (Railway/Vercel), SQLite locally
_db_url = os.environ.get('DATABASE_URL', 'sqlite:///pharmalane.db')
# Fix postgres:// -> postgresql:// for SQLAlchemy
if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'reports')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# ── Models ────────────────────────────────────────────────────────────────────

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='patient')
    specialty = db.Column(db.String(100), nullable=True)
    profile_image = db.Column(db.String(300), nullable=True)  # URL to doctor photo
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    appointments_as_patient = db.relationship('Appointment', foreign_keys='Appointment.patient_id', backref='patient', lazy=True)
    appointments_as_doctor  = db.relationship('Appointment', foreign_keys='Appointment.doctor_id',  backref='doctor',  lazy=True)

class PatientReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=True)
    filename      = db.Column(db.String(300), nullable=False)
    description   = db.Column(db.Text, nullable=True)
    uploaded_at   = db.Column(db.DateTime, default=datetime.utcnow)
    patient       = db.relationship('User', backref='reports')

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_id       = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date            = db.Column(db.String(20), nullable=False)
    time            = db.Column(db.String(10), nullable=False)
    reason          = db.Column(db.String(300), nullable=True)
    status          = db.Column(db.String(20), default='pending_payment')  # pending_payment | scheduled | completed | cancelled
    room_id         = db.Column(db.String(100), unique=True, nullable=False)
    meet_link       = db.Column(db.String(200), nullable=True)
    # Payment fields
    payment_status  = db.Column(db.String(20), default='pending')   # pending | paid | refunded
    razorpay_order_id   = db.Column(db.String(100), nullable=True)
    razorpay_payment_id = db.Column(db.String(100), nullable=True)
    amount_paise    = db.Column(db.Integer, default=50000)           # ₹500
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    reports         = db.relationship('PatientReport', backref='appointment', lazy=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ── ML Assets ─────────────────────────────────────────────────────────────────

sym_des     = pd.read_csv("datasets/symtoms_df.csv")
precautions = pd.read_csv("datasets/precautions_df.csv")
workout     = pd.read_csv("datasets/workout_df.csv")
description = pd.read_csv("datasets/description.csv")
medications = pd.read_csv('datasets/medications.csv')
diets       = pd.read_csv("datasets/diets.csv")
svc         = pickle.load(open('models/svc.pkl', 'rb'))

symptoms_dict = {'itching': 0, 'skin_rash': 1, 'nodal_skin_eruptions': 2, 'continuous_sneezing': 3, 'shivering': 4, 'chills': 5, 'joint_pain': 6, 'stomach_pain': 7, 'acidity': 8, 'ulcers_on_tongue': 9, 'muscle_wasting': 10, 'vomiting': 11, 'burning_micturition': 12, 'spotting_ urination': 13, 'fatigue': 14, 'weight_gain': 15, 'anxiety': 16, 'cold_hands_and_feets': 17, 'mood_swings': 18, 'weight_loss': 19, 'restlessness': 20, 'lethargy': 21, 'patches_in_throat': 22, 'irregular_sugar_level': 23, 'cough': 24, 'high_fever': 25, 'sunken_eyes': 26, 'breathlessness': 27, 'sweating': 28, 'dehydration': 29, 'indigestion': 30, 'headache': 31, 'yellowish_skin': 32, 'dark_urine': 33, 'nausea': 34, 'loss_of_appetite': 35, 'pain_behind_the_eyes': 36, 'back_pain': 37, 'constipation': 38, 'abdominal_pain': 39, 'diarrhoea': 40, 'mild_fever': 41, 'yellow_urine': 42, 'yellowing_of_eyes': 43, 'acute_liver_failure': 44, 'fluid_overload': 45, 'swelling_of_stomach': 46, 'swelled_lymph_nodes': 47, 'malaise': 48, 'blurred_and_distorted_vision': 49, 'phlegm': 50, 'throat_irritation': 51, 'redness_of_eyes': 52, 'sinus_pressure': 53, 'runny_nose': 54, 'congestion': 55, 'chest_pain': 56, 'weakness_in_limbs': 57, 'fast_heart_rate': 58, 'pain_during_bowel_movements': 59, 'pain_in_anal_region': 60, 'bloody_stool': 61, 'irritation_in_anus': 62, 'neck_pain': 63, 'dizziness': 64, 'cramps': 65, 'bruising': 66, 'obesity': 67, 'swollen_legs': 68, 'swollen_blood_vessels': 69, 'puffy_face_and_eyes': 70, 'enlarged_thyroid': 71, 'brittle_nails': 72, 'swollen_extremeties': 73, 'excessive_hunger': 74, 'extra_marital_contacts': 75, 'drying_and_tingling_lips': 76, 'slurred_speech': 77, 'knee_pain': 78, 'hip_joint_pain': 79, 'muscle_weakness': 80, 'stiff_neck': 81, 'swelling_joints': 82, 'movement_stiffness': 83, 'spinning_movements': 84, 'loss_of_balance': 85, 'unsteadiness': 86, 'weakness_of_one_body_side': 87, 'loss_of_smell': 88, 'bladder_discomfort': 89, 'foul_smell_of urine': 90, 'continuous_feel_of_urine': 91, 'passage_of_gases': 92, 'internal_itching': 93, 'toxic_look_(typhos)': 94, 'depression': 95, 'irritability': 96, 'muscle_pain': 97, 'altered_sensorium': 98, 'red_spots_over_body': 99, 'belly_pain': 100, 'abnormal_menstruation': 101, 'dischromic _patches': 102, 'watering_from_eyes': 103, 'increased_appetite': 104, 'polyuria': 105, 'family_history': 106, 'mucoid_sputum': 107, 'rusty_sputum': 108, 'lack_of_concentration': 109, 'visual_disturbances': 110, 'receiving_blood_transfusion': 111, 'receiving_unsterile_injections': 112, 'coma': 113, 'stomach_bleeding': 114, 'distention_of_abdomen': 115, 'history_of_alcohol_consumption': 116, 'fluid_overload.1': 117, 'blood_in_sputum': 118, 'prominent_veins_on_calf': 119, 'palpitations': 120, 'painful_walking': 121, 'pus_filled_pimples': 122, 'blackheads': 123, 'scurring': 124, 'skin_peeling': 125, 'silver_like_dusting': 126, 'small_dents_in_nails': 127, 'inflammatory_nails': 128, 'blister': 129, 'red_sore_around_nose': 130, 'yellow_crust_ooze': 131}
diseases_list = {15: 'Fungal infection', 4: 'Allergy', 16: 'GERD', 9: 'Chronic cholestasis', 14: 'Drug Reaction', 33: 'Peptic ulcer diseae', 1: 'AIDS', 12: 'Diabetes ', 17: 'Gastroenteritis', 6: 'Bronchial Asthma', 23: 'Hypertension ', 30: 'Migraine', 7: 'Cervical spondylosis', 32: 'Paralysis (brain hemorrhage)', 28: 'Jaundice', 29: 'Malaria', 8: 'Chicken pox', 11: 'Dengue', 37: 'Typhoid', 40: 'hepatitis A', 19: 'Hepatitis B', 20: 'Hepatitis C', 21: 'Hepatitis D', 22: 'Hepatitis E', 3: 'Alcoholic hepatitis', 36: 'Tuberculosis', 10: 'Common Cold', 34: 'Pneumonia', 13: 'Dimorphic hemmorhoids(piles)', 18: 'Heart attack', 39: 'Varicose veins', 26: 'Hypothyroidism', 24: 'Hyperthyroidism', 25: 'Hypoglycemia', 31: 'Osteoarthristis', 5: 'Arthritis', 0: '(vertigo) Paroymsal  Positional Vertigo', 2: 'Acne', 38: 'Urinary tract infection', 35: 'Psoriasis', 27: 'Impetigo'}

def parse_list_string(val):
    """Convert "['item1', 'item2']" string into a clean Python list."""
    import ast
    try:
        result = ast.literal_eval(str(val))
        if isinstance(result, list):
            return [str(x).strip() for x in result if str(x).strip()]
    except Exception:
        pass
    # fallback: strip brackets and split
    cleaned = str(val).strip().strip("[]").replace("'", "").replace('"', '')
    return [x.strip() for x in cleaned.split(',') if x.strip()]

def helper(dis):
    desc   = description[description['Disease'] == dis]['Description']
    desc   = " ".join([w for w in desc])

    pre_df = precautions[precautions['Disease'] == dis][['Precaution_1','Precaution_2','Precaution_3','Precaution_4']]
    pre    = [str(v).strip() for row in pre_df.values for v in row if str(v).strip() and str(v) != 'nan']

    med_raw = medications[medications['Disease'] == dis]['Medication']
    med = []
    for val in med_raw.values:
        med.extend(parse_list_string(val))

    die_raw = diets[diets['Disease'] == dis]['Diet']
    die = []
    for val in die_raw.values:
        die.extend(parse_list_string(val))

    wrkout_raw = workout[workout['disease'] == dis]['workout']
    wrkout = [str(w).strip() for w in wrkout_raw.values if str(w).strip() and str(w) != 'nan']

    return desc, pre, med, die, wrkout

def get_predicted_value(patient_symptoms):
    input_vector = np.zeros(len(symptoms_dict))
    for item in patient_symptoms:
        input_vector[symptoms_dict[item]] = 1
    return diseases_list[svc.predict([input_vector])[0]]

def get_confidence_score(patient_symptoms):
    """Return a pseudo-confidence based on symptom match density."""
    matched = sum(1 for s in patient_symptoms if s in symptoms_dict)
    base = min(72 + (matched * 4), 97)
    return base

SEVERITY_MAP = {
    'AIDS': 'Critical', 'Heart attack': 'Critical', 'Paralysis (brain hemorrhage)': 'Critical',
    'Tuberculosis': 'High', 'Dengue': 'High', 'Malaria': 'High', 'Typhoid': 'High',
    'Hepatitis B': 'High', 'Hepatitis C': 'High', 'Hepatitis D': 'High',
    'Diabetes ': 'High', 'Hypertension ': 'High', 'Bronchial Asthma': 'High',
    'Pneumonia': 'High', 'Jaundice': 'Medium', 'Migraine': 'Medium',
    'GERD': 'Medium', 'Hyperthyroidism': 'Medium', 'Hypothyroidism': 'Medium',
    'Hypoglycemia': 'Medium', 'Gastroenteritis': 'Medium', 'Urinary tract infection': 'Medium',
    'Common Cold': 'Low', 'Acne': 'Low', 'Fungal infection': 'Low',
    'Allergy': 'Low', 'Impetigo': 'Low', 'Psoriasis': 'Low',
}

def get_severity(disease):
    return SEVERITY_MAP.get(disease.strip(), 'Medium')

# ── Groq LLaMA3 AI Analysis ───────────────────────────────────────────────────
# Get your FREE API key at https://console.groq.com (free tier: 14,400 req/day)
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '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')

# Razorpay — get free test keys at https://dashboard.razorpay.com → Settings → API Keys
RAZORPAY_KEY_ID     = os.environ.get('RAZORPAY_KEY_ID',     'rzp_test_placeholder')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'placeholder_secret')
CONSULTATION_FEE   = 50000  # ₹500 in paise (100 paise = ₹1)

def get_groq_analysis(symptoms_list, svm_disease, dataset_meds, dataset_diet, dataset_workout, dataset_precautions):
    """
    Uses Groq LLaMA3-70B (free) to generate a full structured medical analysis.
    SVM prediction is passed as strong context so LLM validates + enriches it.
    Falls back to dataset if API key not set or call fails.
    """
    if GROQ_API_KEY == 'gsk_placeholder':
        return None

    symptoms_clean = ', '.join([s.replace('_', ' ') for s in symptoms_list])
    meds_clean     = ', '.join(dataset_meds[:5])
    diet_clean     = ', '.join(dataset_diet[:5])
    workout_clean  = ', '.join(dataset_workout[:4])
    prec_clean     = ', '.join(dataset_precautions[:4])

    prompt = f"""You are a senior medical AI assistant. A patient reports these symptoms: {symptoms_clean}.

Our ML model (SVM trained on 4900+ cases) predicts: {svm_disease}
Dataset medications: {meds_clean}
Dataset diet: {diet_clean}
Dataset workout: {workout_clean}
Dataset precautions: {prec_clean}

Provide a structured medical analysis in this EXACT format (no markdown, no asterisks, no bullet symbols, use plain text):

DISEASE: [confirm or refine the disease name]

OVERVIEW:
[2-3 sentences explaining what this disease is and why these symptoms indicate it]

MEDICATIONS:
1. [Medication name] - [what it does and typical use]
2. [Medication name] - [what it does and typical use]
3. [Medication name] - [what it does and typical use]
4. [Medication name] - [what it does and typical use]
5. [Medication name] - [what it does and typical use]

PRECAUTIONS:
1. [Clear actionable precaution]
2. [Clear actionable precaution]
3. [Clear actionable precaution]
4. [Clear actionable precaution]

DIET PLAN:
1. [Specific food or dietary advice]
2. [Specific food or dietary advice]
3. [Specific food or dietary advice]
4. [Specific food or dietary advice]

WORKOUT:
1. [Specific exercise recommendation]
2. [Specific exercise recommendation]
3. [Specific exercise recommendation]

WHEN TO SEE A DOCTOR:
[1-2 sentences on urgency and red flag symptoms]

Keep all points concise, practical, and medically accurate. No asterisks, no dashes as bullets, use numbers only."""

    try:
        client = Groq(api_key=GROQ_API_KEY)
        chat   = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.3,
            max_tokens=900,
        )
        raw = chat.choices[0].message.content.strip()
        return parse_groq_response(raw)
    except Exception as e:
        print(f'Groq error: {e}')
        return None


def parse_groq_response(raw):
    """Parse the structured Groq response into a clean dict."""
    result = {
        'disease': '', 'overview': '',
        'medications': [], 'precautions': [],
        'diet': [], 'workout': [], 'when_to_see_doctor': ''
    }
    current = None
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('DISEASE:'):
            result['disease'] = line.replace('DISEASE:', '').strip()
        elif line.startswith('OVERVIEW:'):
            current = 'overview'
        elif line.startswith('MEDICATIONS:'):
            current = 'medications'
        elif line.startswith('PRECAUTIONS:'):
            current = 'precautions'
        elif line.startswith('DIET PLAN:'):
            current = 'diet'
        elif line.startswith('WORKOUT:'):
            current = 'workout'
        elif line.startswith('WHEN TO SEE A DOCTOR:'):
            current = 'doctor'
        else:
            if current == 'overview':
                result['overview'] += (' ' + line) if result['overview'] else line
            elif current == 'doctor':
                result['when_to_see_doctor'] += (' ' + line) if result['when_to_see_doctor'] else line
            elif current in ('medications', 'precautions', 'diet', 'workout'):
                # strip leading number+dot like "1. "
                clean = line.lstrip('0123456789').lstrip('. ').strip()
                if clean:
                    key = 'diet' if current == 'diet' else current
                    result[key].append(clean)
    return result

def generate_meet_link(room_id):
    """
    Returns a placeholder until doctor sets the real Google Meet link.
    Doctor creates the meeting on meet.google.com/new and pastes the link back.
    """
    return None  # Will be set by doctor via /set-meet-link route

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name      = request.form.get('name', '').strip()
        email     = request.form.get('email', '').strip().lower()
        password  = request.form.get('password', '')
        role      = request.form.get('role', 'patient')
        specialty = request.form.get('specialty', '').strip()

        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please login.', 'danger')
            return redirect(url_for('register'))

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        profile_image = request.form.get('profile_image', '').strip() or None
        user = User(name=name, email=email, password=hashed_pw, role=role,
                    specialty=specialty if role == 'doctor' else None,
                    profile_image=profile_image if role == 'doctor' else None)
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user     = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('landing'))

# ── Core App Routes ───────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    symptoms = request.form.get('symptoms', '').strip()
    if not symptoms or symptoms == 'Symptoms':
        flash('Please enter valid symptoms.', 'warning')
        return redirect(url_for('dashboard'))

    user_symptoms = [s.strip().strip("[]' ") for s in symptoms.split(',')]
    valid_symptoms = [s for s in user_symptoms if s in symptoms_dict]

    if not valid_symptoms:
        flash('No recognizable symptoms found. Please check spelling.', 'warning')
        return redirect(url_for('dashboard'))

    predicted_disease = get_predicted_value(valid_symptoms)
    dis_des, prec, meds, rec_diet, wrkout = helper(predicted_disease)
    confidence  = get_confidence_score(valid_symptoms)
    severity    = get_severity(predicted_disease)

    # Try Groq LLaMA3 AI — enriches and validates the SVM result
    ai_result = get_groq_analysis(valid_symptoms, predicted_disease, meds, rec_diet, wrkout, prec)

    # If AI returned data, use it; otherwise fall back to dataset
    final_disease     = ai_result['disease']   if ai_result and ai_result['disease']   else predicted_disease.strip()
    final_overview    = ai_result['overview']  if ai_result and ai_result['overview']  else dis_des
    final_meds        = ai_result['medications']   if ai_result and ai_result['medications']   else meds
    final_prec        = ai_result['precautions']   if ai_result and ai_result['precautions']   else prec
    final_diet        = ai_result['diet']          if ai_result and ai_result['diet']          else rec_diet
    final_workout     = ai_result['workout']       if ai_result and ai_result['workout']       else wrkout
    when_to_see_doc   = ai_result['when_to_see_doctor'] if ai_result else ''
    ai_powered        = ai_result is not None

    return render_template('dashboard.html',
        predicted_disease=final_disease,
        dis_des=final_overview,
        my_precautions=final_prec,
        medications=final_meds,
        my_diet=final_diet,
        workout=final_workout,
        when_to_see_doc=when_to_see_doc,
        entered_symptoms=symptoms,
        confidence=confidence,
        severity=severity,
        symptom_count=len(valid_symptoms),
        ai_powered=ai_powered
    )

@app.route('/upload-report/<int:appt_id>', methods=['POST'])
@login_required
def upload_report(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    if appt.patient_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('appointments'))

    file = request.files.get('report_file')
    description = request.form.get('description', '').strip()
    saved_filename = None

    if file and file.filename:
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in ALLOWED_EXTENSIONS:
            flash('File type not allowed.', 'danger')
            return redirect(url_for('appointments'))
        safe_name = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], safe_name))
        saved_filename = safe_name

    if not saved_filename and not description:
        flash('Please add a description or attach a file.', 'warning')
        return redirect(url_for('appointments'))

    report = PatientReport(
        patient_id=current_user.id,
        appointment_id=appt_id,
        filename=saved_filename or 'text_note',
        description=description
    )
    db.session.add(report)
    db.session.commit()
    flash('Report saved successfully.', 'success')
    return redirect(url_for('appointments'))


# ── Appointment Routes ────────────────────────────────────────────────────────

@app.route('/appointments')
@login_required
def appointments():
    doctors = User.query.filter_by(role='doctor').all()
    now = datetime.utcnow()
    today_str = now.strftime('%Y-%m-%d')
    if current_user.role == 'doctor':
        my_appointments = Appointment.query.filter_by(doctor_id=current_user.id).order_by(Appointment.date, Appointment.time).all()
        today_appointments = [a for a in my_appointments if a.date == today_str and a.status == 'scheduled']
        upcoming = [a for a in my_appointments if a.date >= today_str and a.status == 'scheduled']
        # Collect reports keyed by appointment id for doctor view
        appt_reports = {a.id: a.reports for a in my_appointments}
    else:
        my_appointments = Appointment.query.filter_by(patient_id=current_user.id).order_by(Appointment.date, Appointment.time).all()
        today_appointments = []
        upcoming = [a for a in my_appointments if a.date >= today_str and a.status == 'scheduled']
        appt_reports = {}
    return render_template('appointments.html',
        doctors=doctors,
        my_appointments=my_appointments,
        today_appointments=today_appointments,
        upcoming=upcoming,
        now=now,
        today_str=today_str,
        appt_reports=appt_reports
    )

@app.route('/book-appointment', methods=['POST'])
@login_required
def book_appointment():
    doctor_id = request.form.get('doctor_id')
    date      = request.form.get('date')
    time      = request.form.get('time')
    reason    = request.form.get('reason', '')

    if not all([doctor_id, date, time]):
        flash('Please fill all required fields.', 'danger')
        return redirect(url_for('appointments'))

    conflict = Appointment.query.filter_by(doctor_id=doctor_id, date=date, time=time).filter(
        Appointment.status.in_(['pending_payment', 'scheduled'])
    ).first()
    if conflict:
        flash('That time slot is already booked. Please choose another.', 'warning')
        return redirect(url_for('appointments'))

    room_id = f"pharmalane-{uuid.uuid4().hex[:16]}"
    appt = Appointment(
        patient_id=current_user.id,
        doctor_id=int(doctor_id),
        date=date, time=time, reason=reason,
        room_id=room_id,
        status='pending_payment',
        payment_status='pending',
        amount_paise=CONSULTATION_FEE
    )
    db.session.add(appt)
    db.session.commit()
    return redirect(url_for('payment_page', appt_id=appt.id))


@app.route('/payment/<int:appt_id>')
@login_required
def payment_page(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    if appt.patient_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('appointments'))
    if appt.payment_status == 'paid':
        return redirect(url_for('appointments'))

    # Create Razorpay order
    try:
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        order  = client.order.create({
            'amount':   appt.amount_paise,
            'currency': 'INR',
            'receipt':  f'appt_{appt.id}',
            'notes':    {'appointment_id': str(appt.id), 'patient': current_user.name}
        })
        appt.razorpay_order_id = order['id']
        db.session.commit()
    except Exception as e:
        print(f'Razorpay order error: {e}')
        order = None

    return render_template('payment.html',
        appt=appt,
        order=order,
        key_id=RAZORPAY_KEY_ID,
        amount=appt.amount_paise,
        user_name=current_user.name,
        user_email=current_user.email
    )


@app.route('/payment/verify', methods=['POST'])
@login_required
def payment_verify():
    """Called by Razorpay after successful payment — verifies signature and confirms appointment."""
    data = request.form
    razorpay_order_id   = data.get('razorpay_order_id', '')
    razorpay_payment_id = data.get('razorpay_payment_id', '')
    razorpay_signature  = data.get('razorpay_signature', '')
    appt_id             = data.get('appt_id', '')

    appt = Appointment.query.get_or_404(int(appt_id))
    if appt.patient_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('appointments'))

    try:
        msg    = f"{razorpay_order_id}|{razorpay_payment_id}"
        digest = hmac.new(RAZORPAY_KEY_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
        valid  = hmac.compare_digest(digest, razorpay_signature)
    except Exception:
        valid = False

    if valid:
        appt.payment_status      = 'paid'
        appt.status              = 'scheduled'
        appt.razorpay_payment_id = razorpay_payment_id
        appt.razorpay_order_id   = razorpay_order_id
        db.session.commit()
        flash('Payment successful! Your appointment is confirmed.', 'success')
    else:
        flash('Payment verification failed. Please contact support.', 'danger')

    return redirect(url_for('appointments'))


@app.route('/payment/cancel/<int:appt_id>')
@login_required
def payment_cancel(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    if appt.patient_id == current_user.id and appt.payment_status == 'pending':
        db.session.delete(appt)
        db.session.commit()
        flash('Booking cancelled.', 'info')
    return redirect(url_for('appointments'))

@app.route('/set-meet-link/<int:appt_id>', methods=['POST'])
@login_required
def set_meet_link(appt_id):
    """Doctor saves the real Google Meet link for this appointment."""
    appt = Appointment.query.get_or_404(appt_id)
    if appt.doctor_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    link = request.json.get('link', '').strip()
    if not link.startswith('https://meet.google.com/'):
        return jsonify({'error': 'Invalid Google Meet link'}), 400
    appt.meet_link = link
    db.session.commit()
    return jsonify({'ok': True, 'link': link})


@app.route('/cancel-appointment/<int:appt_id>', methods=['POST'])
@login_required
def cancel_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    if appt.patient_id != current_user.id and appt.doctor_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('appointments'))
    appt.status = 'cancelled'
    db.session.commit()
    flash('Appointment cancelled.', 'info')
    return redirect(url_for('appointments'))

@app.route('/complete-appointment/<int:appt_id>', methods=['POST'])
@login_required
def complete_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    if appt.doctor_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('appointments'))
    appt.status = 'completed'
    db.session.commit()
    flash('Appointment marked as completed.', 'success')
    return redirect(url_for('appointments'))

@app.route('/api/upcoming-appointments')
@login_required
def api_upcoming_appointments():
    """Returns appointments starting within the next 30 minutes for notification popup."""
    now = datetime.utcnow()
    today_str = now.strftime('%Y-%m-%d')
    current_time = now.strftime('%H:%M')

    if current_user.role == 'patient':
        appts = Appointment.query.filter_by(patient_id=current_user.id, status='scheduled').all()
    else:
        appts = Appointment.query.filter_by(doctor_id=current_user.id, status='scheduled').all()

    alerts = []
    for a in appts:
        if a.date != today_str:
            continue
        try:
            appt_dt = datetime.strptime(f"{a.date} {a.time}", '%Y-%m-%d %H:%M')
            diff_minutes = (appt_dt - now).total_seconds() / 60
            if 0 <= diff_minutes <= 30:
                other = a.doctor.name if current_user.role == 'patient' else a.patient.name
                alerts.append({
                    'id': a.id,
                    'time': a.time,
                    'other': other,
                    'minutes': int(diff_minutes),
                    'room_id': a.room_id
                })
        except Exception:
            pass
    return jsonify(alerts)

@app.route('/video-call/<room_id>')
@login_required
def video_call(room_id):
    appt = Appointment.query.filter_by(room_id=room_id).first_or_404()
    if appt.patient_id != current_user.id and appt.doctor_id != current_user.id:
        flash('Unauthorized access to this call.', 'danger')
        return redirect(url_for('appointments'))
    is_doctor = (current_user.id == appt.doctor_id)
    return render_template('video_call.html', room_id=room_id, appointment=appt, is_doctor=is_doctor)

# ── Static Pages ──────────────────────────────────────────────────────────────

@app.route('/about')
def about():
    return render_template('about.html')

# ── API: symptoms list for autocomplete ──────────────────────────────────────

@app.route('/api/symptoms')
def api_symptoms():
    return jsonify(list(symptoms_dict.keys()))

# ── Init ──────────────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()
    # Seed demo doctors if none exist
    if not User.query.filter_by(role='doctor').first():
        demo_doctors = [
            ('Dr. Arjun Mehta',  'arjun@pharmalane.com',  'Cardiologist',     'https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=200&h=200&fit=crop&crop=face'),
            ('Dr. Priya Sharma', 'priya@pharmalane.com',  'Neurologist',      'https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=200&h=200&fit=crop&crop=face'),
            ('Dr. Rahul Verma',  'rahul@pharmalane.com',  'General Physician','https://images.unsplash.com/photo-1622253692010-333f2da6031d?w=200&h=200&fit=crop&crop=face'),
            ('Dr. Sneha Kapoor', 'sneha@pharmalane.com',  'Dermatologist',    'https://images.unsplash.com/photo-1594824476967-48c8b964273f?w=200&h=200&fit=crop&crop=face'),
            ('Dr. Vikram Singh', 'vikram@pharmalane.com', 'Orthopedist',      'https://images.unsplash.com/photo-1537368910025-700350fe46c7?w=200&h=200&fit=crop&crop=face'),
        ]
        for name, email, spec, photo in demo_doctors:
            pw = bcrypt.generate_password_hash('doctor123').decode('utf-8')
            db.session.add(User(name=name, email=email, password=pw, role='doctor', specialty=spec, profile_image=photo))
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
