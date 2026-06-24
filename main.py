from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from datetime import datetime
import numpy as np
import pandas as pd
import pickle
import uuid
import os
import re
import razorpay
import hmac
import hashlib
from werkzeug.utils import secure_filename
# Gemini via REST — no heavy SDK needed on Vercel

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'pharmalane-dev-key-change-in-prod')

_db_url = os.environ.get('DATABASE_URL', 'sqlite:///pharmalane.db')
if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True, 'pool_recycle': 300}

UPLOAD_FOLDER = '/tmp/reports' if os.environ.get('VERCEL') else os.path.join('static', 'uploads', 'reports')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── Flask-Mail (Gmail SMTP) ───────────────────────────────────────────────────
app.config['MAIL_SERVER']   = os.environ.get('MAIL_SERVER',   'smtp.gmail.com')
app.config['MAIL_PORT']     = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS']  = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', 'noreply@pharmalane.com')

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# ── Gemini ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
if GEMINI_API_KEY:
    pass  # used in get_gemini_analysis via requests

# ── Razorpay ──────────────────────────────────────────────────────────────────
RAZORPAY_KEY_ID     = os.environ.get('RAZORPAY_KEY_ID',     'rzp_test_placeholder')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'placeholder_secret')
CONSULTATION_FEE    = 50000

# ── Models ────────────────────────────────────────────────────────────────────

class User(db.Model, UserMixin):
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password      = db.Column(db.String(200), nullable=False)
    role          = db.Column(db.String(20), default='patient')
    specialty     = db.Column(db.String(100), nullable=True)
    profile_image = db.Column(db.String(300), nullable=True)
    fees          = db.Column(db.Integer, default=500)  # consultation fee in ₹
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    appointments_as_patient = db.relationship('Appointment', foreign_keys='Appointment.patient_id', backref='patient', lazy=True)
    appointments_as_doctor  = db.relationship('Appointment', foreign_keys='Appointment.doctor_id',  backref='doctor',  lazy=True)

class Appointment(db.Model):
    id                  = db.Column(db.Integer, primary_key=True)
    patient_id          = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_id           = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date                = db.Column(db.String(20), nullable=False)
    time                = db.Column(db.String(10), nullable=False)
    reason              = db.Column(db.String(300), nullable=True)
    status              = db.Column(db.String(20), default='pending_payment')
    room_id             = db.Column(db.String(100), unique=True, nullable=False)
    meet_link           = db.Column(db.String(200), nullable=True)
    payment_status      = db.Column(db.String(20), default='pending')
    razorpay_order_id   = db.Column(db.String(100), nullable=True)
    razorpay_payment_id = db.Column(db.String(100), nullable=True)
    amount_paise        = db.Column(db.Integer, default=50000)
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)
    reports             = db.relationship('PatientReport', backref='appointment', lazy=True)
    prescriptions       = db.relationship('Prescription', backref='appointment', lazy=True)

class PatientReport(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    patient_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=True)
    filename       = db.Column(db.String(300), nullable=False)
    description    = db.Column(db.Text, nullable=True)
    uploaded_at    = db.Column(db.DateTime, default=datetime.utcnow)
    patient        = db.relationship('User', backref='reports')

class Prescription(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    doctor_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    patient_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    diagnosis      = db.Column(db.String(200), nullable=True)
    medications    = db.Column(db.Text, nullable=True)
    instructions   = db.Column(db.Text, nullable=True)
    follow_up      = db.Column(db.String(100), nullable=True)
    prescription_file = db.Column(db.String(300), nullable=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    doctor         = db.relationship('User', foreign_keys=[doctor_id])
    patient        = db.relationship('User', foreign_keys=[patient_id])

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ── ML Assets ─────────────────────────────────────────────────────────────────
try:
    sym_des     = pd.read_csv("datasets/symtoms_df.csv")
    precautions = pd.read_csv("datasets/precautions_df.csv")
    workout_df  = pd.read_csv("datasets/workout_df.csv")
    description = pd.read_csv("datasets/description.csv")
    medications = pd.read_csv('datasets/medications.csv')
    diets       = pd.read_csv("datasets/diets.csv")
    svc         = pickle.load(open('models/svc.pkl', 'rb'))
except Exception as e:
    print(f'ML assets load error: {e}')
    sym_des = precautions = workout_df = description = medications = diets = None
    svc = None

symptoms_dict = {'itching': 0, 'skin_rash': 1, 'nodal_skin_eruptions': 2, 'continuous_sneezing': 3, 'shivering': 4, 'chills': 5, 'joint_pain': 6, 'stomach_pain': 7, 'acidity': 8, 'ulcers_on_tongue': 9, 'muscle_wasting': 10, 'vomiting': 11, 'burning_micturition': 12, 'spotting_ urination': 13, 'fatigue': 14, 'weight_gain': 15, 'anxiety': 16, 'cold_hands_and_feets': 17, 'mood_swings': 18, 'weight_loss': 19, 'restlessness': 20, 'lethargy': 21, 'patches_in_throat': 22, 'irregular_sugar_level': 23, 'cough': 24, 'high_fever': 25, 'sunken_eyes': 26, 'breathlessness': 27, 'sweating': 28, 'dehydration': 29, 'indigestion': 30, 'headache': 31, 'yellowish_skin': 32, 'dark_urine': 33, 'nausea': 34, 'loss_of_appetite': 35, 'pain_behind_the_eyes': 36, 'back_pain': 37, 'constipation': 38, 'abdominal_pain': 39, 'diarrhoea': 40, 'mild_fever': 41, 'yellow_urine': 42, 'yellowing_of_eyes': 43, 'acute_liver_failure': 44, 'fluid_overload': 45, 'swelling_of_stomach': 46, 'swelled_lymph_nodes': 47, 'malaise': 48, 'blurred_and_distorted_vision': 49, 'phlegm': 50, 'throat_irritation': 51, 'redness_of_eyes': 52, 'sinus_pressure': 53, 'runny_nose': 54, 'congestion': 55, 'chest_pain': 56, 'weakness_in_limbs': 57, 'fast_heart_rate': 58, 'pain_during_bowel_movements': 59, 'pain_in_anal_region': 60, 'bloody_stool': 61, 'irritation_in_anus': 62, 'neck_pain': 63, 'dizziness': 64, 'cramps': 65, 'bruising': 66, 'obesity': 67, 'swollen_legs': 68, 'swollen_blood_vessels': 69, 'puffy_face_and_eyes': 70, 'enlarged_thyroid': 71, 'brittle_nails': 72, 'swollen_extremeties': 73, 'excessive_hunger': 74, 'extra_marital_contacts': 75, 'drying_and_tingling_lips': 76, 'slurred_speech': 77, 'knee_pain': 78, 'hip_joint_pain': 79, 'muscle_weakness': 80, 'stiff_neck': 81, 'swelling_joints': 82, 'movement_stiffness': 83, 'spinning_movements': 84, 'loss_of_balance': 85, 'unsteadiness': 86, 'weakness_of_one_body_side': 87, 'loss_of_smell': 88, 'bladder_discomfort': 89, 'foul_smell_of urine': 90, 'continuous_feel_of_urine': 91, 'passage_of_gases': 92, 'internal_itching': 93, 'toxic_look_(typhos)': 94, 'depression': 95, 'irritability': 96, 'muscle_pain': 97, 'altered_sensorium': 98, 'red_spots_over_body': 99, 'belly_pain': 100, 'abnormal_menstruation': 101, 'dischromic _patches': 102, 'watering_from_eyes': 103, 'increased_appetite': 104, 'polyuria': 105, 'family_history': 106, 'mucoid_sputum': 107, 'rusty_sputum': 108, 'lack_of_concentration': 109, 'visual_disturbances': 110, 'receiving_blood_transfusion': 111, 'receiving_unsterile_injections': 112, 'coma': 113, 'stomach_bleeding': 114, 'distention_of_abdomen': 115, 'history_of_alcohol_consumption': 116, 'fluid_overload.1': 117, 'blood_in_sputum': 118, 'prominent_veins_on_calf': 119, 'palpitations': 120, 'painful_walking': 121, 'pus_filled_pimples': 122, 'blackheads': 123, 'scurring': 124, 'skin_peeling': 125, 'silver_like_dusting': 126, 'small_dents_in_nails': 127, 'inflammatory_nails': 128, 'blister': 129, 'red_sore_around_nose': 130, 'yellow_crust_ooze': 131}
diseases_list = {15: 'Fungal infection', 4: 'Allergy', 16: 'GERD', 9: 'Chronic cholestasis', 14: 'Drug Reaction', 33: 'Peptic ulcer diseae', 1: 'AIDS', 12: 'Diabetes ', 17: 'Gastroenteritis', 6: 'Bronchial Asthma', 23: 'Hypertension ', 30: 'Migraine', 7: 'Cervical spondylosis', 32: 'Paralysis (brain hemorrhage)', 28: 'Jaundice', 29: 'Malaria', 8: 'Chicken pox', 11: 'Dengue', 37: 'Typhoid', 40: 'hepatitis A', 19: 'Hepatitis B', 20: 'Hepatitis C', 21: 'Hepatitis D', 22: 'Hepatitis E', 3: 'Alcoholic hepatitis', 36: 'Tuberculosis', 10: 'Common Cold', 34: 'Pneumonia', 13: 'Dimorphic hemmorhoids(piles)', 18: 'Heart attack', 39: 'Varicose veins', 26: 'Hypothyroidism', 24: 'Hyperthyroidism', 25: 'Hypoglycemia', 31: 'Osteoarthristis', 5: 'Arthritis', 0: '(vertigo) Paroymsal  Positional Vertigo', 2: 'Acne', 38: 'Urinary tract infection', 35: 'Psoriasis', 27: 'Impetigo'}

def parse_list_string(val):
    import ast
    try:
        result = ast.literal_eval(str(val))
        if isinstance(result, list):
            return [str(x).strip() for x in result if str(x).strip()]
    except Exception:
        pass
    cleaned = str(val).strip().strip("[]").replace("'", "").replace('"', '')
    return [x.strip() for x in cleaned.split(',') if x.strip()]

def helper(dis):
    if description is None:
        return '', [], [], [], []
    desc = " ".join(description[description['Disease'] == dis]['Description'].tolist())
    pre_df = precautions[precautions['Disease'] == dis][['Precaution_1','Precaution_2','Precaution_3','Precaution_4']]
    pre = [str(v).strip() for row in pre_df.values for v in row if str(v).strip() and str(v) != 'nan']
    med = []
    for val in medications[medications['Disease'] == dis]['Medication'].values:
        med.extend(parse_list_string(val))
    die = []
    for val in diets[diets['Disease'] == dis]['Diet'].values:
        die.extend(parse_list_string(val))
    wrkout = [str(w).strip() for w in workout_df[workout_df['disease'] == dis]['workout'].values if str(w).strip() and str(w) != 'nan']
    return desc, pre, med, die, wrkout

def get_predicted_value(patient_symptoms):
    if svc is None:
        return 'Unknown'
    input_vector = np.zeros(len(symptoms_dict))
    for item in patient_symptoms:
        input_vector[symptoms_dict[item]] = 1
    return diseases_list[svc.predict([input_vector])[0]]

def get_confidence_score(patient_symptoms):
    matched = sum(1 for s in patient_symptoms if s in symptoms_dict)
    return min(72 + (matched * 4), 97)

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

# ── Gemini AI Analysis ────────────────────────────────────────────────────────

def get_gemini_analysis(symptoms_list, svm_disease):
    if not GEMINI_API_KEY:
        return None
    try:
        symptoms_str = ', '.join(s.replace('_', ' ') for s in symptoms_list)
        prompt = (
            f"Patient symptoms: {symptoms_str}. ML model predicts: {svm_disease}.\n"
            "Reply in this exact format, plain text, no markdown:\n"
            "DISEASE: <name>\n"
            "OVERVIEW: <2 sentences>\n"
            "MEDICATIONS: 1.<drug—dose—purpose> 2.<...> 3.<...> 4.<...> 5.<...>\n"
            "PRECAUTIONS: 1.<action> 2.<action> 3.<action> 4.<action>\n"
            "DIET: 1.<food> 2.<food> 3.<avoid> 4.<hydration>\n"
            "WORKOUT: 1.<exercise—duration> 2.<exercise> 3.<avoid>\n"
            "DOCTOR_ALERT: <1 sentence red-flag>"
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}],
                   "generationConfig": {"temperature": 0.2, "maxOutputTokens": 600}}
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        raw = resp.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        return _parse_gemini(raw)
    except Exception as e:
        print(f'Gemini error: {e}')
        return None

def _parse_gemini(raw):
    result = {'disease':'','overview':'','medications':[],'precautions':[],'diet':[],'workout':[],'when_to_see_doctor':''}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith('DISEASE:'):
            result['disease'] = line.split(':',1)[1].strip()
        elif line.upper().startswith('OVERVIEW:'):
            result['overview'] = line.split(':',1)[1].strip()
        elif line.upper().startswith('MEDICATIONS:'):
            result['medications'] = [re.sub(r'^\d+\.','',p).strip() for p in re.split(r'\s+\d+\.', line.split(':',1)[1]) if p.strip()]
        elif line.upper().startswith('PRECAUTIONS:'):
            result['precautions'] = [re.sub(r'^\d+\.','',p).strip() for p in re.split(r'\s+\d+\.', line.split(':',1)[1]) if p.strip()]
        elif line.upper().startswith('DIET:'):
            result['diet'] = [re.sub(r'^\d+\.','',p).strip() for p in re.split(r'\s+\d+\.', line.split(':',1)[1]) if p.strip()]
        elif line.upper().startswith('WORKOUT:'):
            result['workout'] = [re.sub(r'^\d+\.','',p).strip() for p in re.split(r'\s+\d+\.', line.split(':',1)[1]) if p.strip()]
        elif line.upper().startswith('DOCTOR_ALERT:'):
            result['when_to_see_doctor'] = line.split(':',1)[1].strip()
    return result

# ── Email helpers ─────────────────────────────────────────────────────────────

def _send_appointment_emails(appt):
    try:
        if not app.config.get('MAIL_USERNAME'):
            return
        doc = User.query.get(appt.doctor_id)
        pat = User.query.get(appt.patient_id)
        with app.app_context():
            body_patient = (
                f"Hi {pat.name},\n\n"
                f"Your appointment is confirmed!\n\n"
                f"  Doctor : {doc.name} ({doc.specialty})\n"
                f"  Date   : {appt.date}\n"
                f"  Time   : {appt.time}\n"
                f"  Reason : {appt.reason or 'Not specified'}\n\n"
                f"Login to Medicure to join your video call.\n\n— Medicure Team"
            )
            body_doctor = (
                f"Hi {doc.name},\n\nNew appointment scheduled:\n\n"
                f"  Patient : {pat.name} ({pat.email})\n"
                f"  Date    : {appt.date}\n"
                f"  Time    : {appt.time}\n"
                f"  Reason  : {appt.reason or 'Not specified'}\n\n— Medicure"
            )
            mail.send(Message(subject="Appointment Confirmed — Medicure",
                              recipients=[pat.email], body=body_patient))
            mail.send(Message(subject=f"New Appointment: {pat.name} on {appt.date}",
                              recipients=[doc.email], body=body_doctor))
    except Exception as e:
        print(f'Email error: {e}')

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name      = request.form.get('name','').strip()
        email     = request.form.get('email','').strip().lower()
        password  = request.form.get('password','')
        role      = request.form.get('role','patient')
        specialty = request.form.get('specialty','').strip()
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register'))
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        profile_image = request.form.get('profile_image','').strip() or None
        user = User(name=name, email=email, password=hashed_pw, role=role,
                    specialty=specialty if role=='doctor' else None,
                    profile_image=profile_image if role=='doctor' else None)
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
        email    = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        user     = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(request.args.get('next') or url_for('dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('landing'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    symptoms = request.form.get('symptoms','').strip()
    if not symptoms or symptoms == 'Symptoms':
        flash('Please enter valid symptoms.', 'warning')
        return redirect(url_for('dashboard'))

    user_symptoms  = [s.strip().strip("[]' ") for s in symptoms.split(',')]
    valid_symptoms = [s for s in user_symptoms if s in symptoms_dict]

    if not valid_symptoms:
        flash('No recognizable symptoms found.', 'warning')
        return redirect(url_for('dashboard'))

    predicted_disease = get_predicted_value(valid_symptoms)
    dis_des, prec, meds, rec_diet, wrkout = helper(predicted_disease)
    confidence = get_confidence_score(valid_symptoms)
    severity   = get_severity(predicted_disease)

    ai_result  = get_gemini_analysis(valid_symptoms, predicted_disease)

    return render_template('dashboard.html',
        # ML dataset results (always shown)
        ml_disease=predicted_disease.strip(),
        ml_overview=dis_des,
        ml_precautions=prec,
        ml_medications=meds,
        ml_diet=rec_diet,
        ml_workout=wrkout,
        # Gemini AI results (shown above if available)
        ai_result=ai_result,
        # shared
        entered_symptoms=symptoms,
        confidence=confidence,
        severity=severity,
        symptom_count=len(valid_symptoms),
    )

# ── Report Upload (pre-booking: no appt_id, post-booking: with appt_id) ───────

def _save_report(patient_id, description_text, file_obj, appt_id=None):
    saved_filename = None
    if file_obj and file_obj.filename:
        ext = file_obj.filename.rsplit('.',1)[-1].lower() if '.' in file_obj.filename else ''
        if ext not in ALLOWED_EXTENSIONS:
            return None, 'File type not allowed.'
        safe_name = f"{uuid.uuid4().hex}_{secure_filename(file_obj.filename)}"
        file_obj.save(os.path.join(app.config['UPLOAD_FOLDER'], safe_name))
        saved_filename = safe_name
    if not saved_filename and not description_text:
        return None, 'Please add a description or attach a file.'
    report = PatientReport(
        patient_id=patient_id,
        appointment_id=appt_id,
        filename=saved_filename or 'text_note',
        description=description_text
    )
    db.session.add(report)
    db.session.commit()
    return report, None

@app.route('/upload-report', methods=['POST'])
@login_required
def upload_report_general():
    """Pre-booking: upload report not linked to any appointment yet."""
    description_text = request.form.get('description','').strip()
    report, err = _save_report(current_user.id, description_text, request.files.get('report_file'))
    if err:
        flash(err, 'warning')
    else:
        flash('Report saved. It will be visible to your doctor.', 'success')
    return redirect(url_for('appointments'))

@app.route('/upload-report/<int:appt_id>', methods=['POST'])
@login_required
def upload_report(appt_id):
    """Post-booking: link report to a specific appointment."""
    appt = Appointment.query.get_or_404(appt_id)
    if appt.patient_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('appointments'))
    description_text = request.form.get('description','').strip()
    report, err = _save_report(current_user.id, description_text, request.files.get('report_file'), appt_id)
    if err:
        flash(err, 'warning')
    else:
        flash('Report saved successfully.', 'success')
    return redirect(url_for('appointments'))

# ── Appointment Routes ────────────────────────────────────────────────────────

@app.route('/appointments')
@login_required
def appointments():
    try:
        doctors = User.query.filter_by(role='doctor').all()
        now = datetime.utcnow()
        today_str = now.strftime('%Y-%m-%d')

        if current_user.role == 'doctor':
            my_appointments = Appointment.query.filter_by(doctor_id=current_user.id).order_by(Appointment.date, Appointment.time).all()
            today_appointments = [a for a in my_appointments if a.date == today_str and a.status == 'scheduled']
            upcoming = [a for a in my_appointments if a.date >= today_str and a.status == 'scheduled']
            appt_reports = {a.id: a.reports for a in my_appointments}
            unlinked_reports = PatientReport.query.filter_by(appointment_id=None).all()
        else:
            my_appointments = Appointment.query.filter_by(patient_id=current_user.id).order_by(Appointment.date, Appointment.time).all()
            today_appointments = []
            upcoming = [a for a in my_appointments if a.date >= today_str and a.status == 'scheduled']
            appt_reports = {}
            unlinked_reports = []

        booked_slots = {}
        for doc in doctors:
            try:
                slots = db.session.execute(
                    db.select(Appointment.date, Appointment.time).where(
                        Appointment.doctor_id == doc.id,
                        Appointment.status.in_(['pending_payment', 'scheduled'])
                    )
                ).all()
                booked_slots[str(doc.id)] = [{'date': s.date, 'time': s.time} for s in slots]
            except Exception:
                booked_slots[str(doc.id)] = []

        return render_template('appointments.html',
            doctors=doctors,
            my_appointments=my_appointments,
            today_appointments=today_appointments,
            upcoming=upcoming,
            now=now,
            today_str=today_str,
            appt_reports=appt_reports,
            unlinked_reports=unlinked_reports,
            booked_slots_json=booked_slots,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'Error loading appointments: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/api/booked-slots/<int:doctor_id>')
@login_required
def api_booked_slots(doctor_id):
    try:
        slots = db.session.execute(
            db.select(Appointment.date, Appointment.time).where(
                Appointment.doctor_id == doctor_id,
                Appointment.status.in_(['pending_payment', 'scheduled'])
            )
        ).all()
        return jsonify([{'date': s.date, 'time': s.time} for s in slots])
    except Exception as e:
        return jsonify([])

@app.route('/book-appointment', methods=['POST'])
@login_required
def book_appointment():
    doctor_id = request.form.get('doctor_id')
    date      = request.form.get('date')
    time      = request.form.get('time')
    reason    = request.form.get('reason','')

    if not all([doctor_id, date, time]):
        flash('Please fill all required fields.', 'danger')
        return redirect(url_for('appointments'))

    # Conflict detection
    conflict = Appointment.query.filter_by(doctor_id=doctor_id, date=date, time=time).filter(
        Appointment.status.in_(['pending_payment','scheduled'])
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

    # Link any unattached reports from this patient to this appointment
    unlinked = PatientReport.query.filter_by(patient_id=current_user.id, appointment_id=None).all()
    for r in unlinked:
        r.appointment_id = appt.id
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
    try:
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        order  = client.order.create({'amount': appt.amount_paise, 'currency': 'INR',
                                      'receipt': f'appt_{appt.id}',
                                      'notes': {'appointment_id': str(appt.id), 'patient': current_user.name}})
        appt.razorpay_order_id = order['id']
        db.session.commit()
    except Exception as e:
        print(f'Razorpay error: {e}')
        order = None
    return render_template('payment.html', appt=appt, order=order,
        key_id=RAZORPAY_KEY_ID, amount=appt.amount_paise,
        user_name=current_user.name, user_email=current_user.email)

@app.route('/payment/verify', methods=['POST'])
@login_required
def payment_verify():
    data = request.form
    rp_order   = data.get('razorpay_order_id','')
    rp_payment = data.get('razorpay_payment_id','')
    rp_sig     = data.get('razorpay_signature','')
    appt_id    = data.get('appt_id','')
    appt = Appointment.query.get_or_404(int(appt_id))
    if appt.patient_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('appointments'))
    try:
        msg    = f"{rp_order}|{rp_payment}"
        digest = hmac.new(RAZORPAY_KEY_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
        valid  = hmac.compare_digest(digest, rp_sig)
    except Exception:
        valid = False
    if valid:
        appt.payment_status      = 'paid'
        appt.status              = 'scheduled'
        appt.razorpay_payment_id = rp_payment
        appt.razorpay_order_id   = rp_order
        db.session.commit()
        _send_appointment_emails(appt)
        flash('Payment successful! Your appointment is confirmed. Check your email.', 'success')
    else:
        flash('Payment verification failed.', 'danger')
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
    appt = Appointment.query.get_or_404(appt_id)
    if appt.doctor_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    link = request.json.get('link','').strip()
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

# ── Prescription Routes ───────────────────────────────────────────────────────

@app.route('/add-prescription/<int:appt_id>', methods=['POST'])
@login_required
def add_prescription(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    if appt.doctor_id != current_user.id and current_user.role != 'admin':
        flash('Unauthorized.', 'danger')
        return redirect(url_for('appointments'))
    existing = Prescription.query.filter_by(appointment_id=appt_id).first()
    # Handle prescription file upload
    rx_file = request.files.get('prescription_file')
    saved_rx_file = existing.prescription_file if existing else None
    if rx_file and rx_file.filename:
        ext = rx_file.filename.rsplit('.',1)[-1].lower()
        if ext in {'pdf','jpg','jpeg','png'}:
            fname = f"rx_{uuid.uuid4().hex}.{ext}"
            rx_file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
            saved_rx_file = fname
    data = dict(
        diagnosis=request.form.get('diagnosis','').strip(),
        medications=request.form.get('medications','').strip(),
        instructions=request.form.get('instructions','').strip(),
        follow_up=request.form.get('follow_up','').strip(),
        prescription_file=saved_rx_file
    )
    if existing:
        for k,v in data.items(): setattr(existing, k, v)
    else:
        db.session.add(Prescription(appointment_id=appt_id, doctor_id=appt.doctor_id,
                                    patient_id=appt.patient_id, **data))
    db.session.commit()
    flash('Prescription saved.', 'success')
    return redirect(url_for('appointments'))

@app.route('/api/upcoming-appointments')
@login_required
def api_upcoming_appointments():
    now = datetime.utcnow()
    today_str = now.strftime('%Y-%m-%d')
    appts = (Appointment.query.filter_by(patient_id=current_user.id, status='scheduled').all()
             if current_user.role == 'patient'
             else Appointment.query.filter_by(doctor_id=current_user.id, status='scheduled').all())
    alerts = []
    for a in appts:
        if a.date != today_str:
            continue
        try:
            diff = (datetime.strptime(f"{a.date} {a.time}", '%Y-%m-%d %H:%M') - now).total_seconds() / 60
            if 0 <= diff <= 30:
                alerts.append({'id': a.id, 'time': a.time,
                                'other': a.doctor.name if current_user.role=='patient' else a.patient.name,
                                'minutes': int(diff), 'room_id': a.room_id})
        except Exception:
            pass
    return jsonify(alerts)

@app.route('/video-call/<room_id>')
@login_required
def video_call(room_id):
    appt = Appointment.query.filter_by(room_id=room_id).first_or_404()
    if appt.patient_id != current_user.id and appt.doctor_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('appointments'))
    return render_template('video_call.html', room_id=room_id, appointment=appt,
                           is_doctor=(current_user.id == appt.doctor_id))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/api/symptoms')
def api_symptoms():
    return jsonify(list(symptoms_dict.keys()))

# ── Admin Routes ─────────────────────────────────────────────────────────────

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    doctors  = User.query.filter_by(role='doctor').all()
    patients = User.query.filter_by(role='patient').all()
    appts    = Appointment.query.order_by(Appointment.date.desc(), Appointment.time).all()
    return render_template('admin.html', doctors=doctors, patients=patients, appts=appts)

@app.route('/admin/add-user', methods=['POST'])
@login_required
@admin_required
def admin_add_user():
    name      = request.form.get('name','').strip()
    email     = request.form.get('email','').strip().lower()
    password  = request.form.get('password','')
    role      = request.form.get('role','patient')
    specialty = request.form.get('specialty','').strip()
    photo     = request.form.get('profile_image','').strip() or None
    if User.query.filter_by(email=email).first():
        flash('Email already exists.', 'danger')
        return redirect(url_for('admin_panel'))
    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    db.session.add(User(name=name, email=email, password=hashed, role=role,
                        specialty=specialty if role=='doctor' else None,
                        profile_image=photo if role=='doctor' else None))
    db.session.commit()
    flash(f'{role.capitalize()} {name} added.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted.', 'info')
    return redirect(url_for('admin_panel'))

@app.route('/admin/set-meet-link/<int:appt_id>', methods=['POST'])
@login_required
@admin_required
def admin_set_meet_link(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    appt.meet_link = request.form.get('meet_link','').strip()
    db.session.commit()
    flash('Meet link updated.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/update-appt/<int:appt_id>', methods=['POST'])
@login_required
@admin_required
def admin_update_appt(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    appt.status = request.form.get('status', appt.status)
    meet = request.form.get('meet_link', '').strip()
    if meet:
        appt.meet_link = meet
    db.session.commit()
    flash('Appointment updated.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete-appt/<int:appt_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_appt(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    # delete related prescriptions and reports first
    Prescription.query.filter_by(appointment_id=appt_id).delete()
    PatientReport.query.filter_by(appointment_id=appt_id).delete()
    db.session.delete(appt)
    db.session.commit()
    flash('Appointment deleted.', 'info')
    return redirect(url_for('admin_panel'))

@app.route('/admin/update-doctor/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_update_doctor(user_id):
    doc = User.query.get_or_404(user_id)
    doc.name          = request.form.get('name', doc.name).strip()
    doc.specialty     = request.form.get('specialty', doc.specialty or '').strip()
    doc.profile_image = request.form.get('profile_image', doc.profile_image or '').strip() or doc.profile_image
    try:
        doc.fees = int(request.form.get('fees', doc.fees or 500))
    except ValueError:
        pass
    db.session.commit()
    flash(f'{doc.name} updated.', 'success')
    return redirect(url_for('admin_panel'))

# ── Init ──────────────────────────────────────────────────────────────────────
with app.app_context():
    db.create_all()
    # Add missing columns if they don't exist (safe migration)
    try:
        db.session.execute(db.text('ALTER TABLE prescription ADD COLUMN IF NOT EXISTS prescription_file VARCHAR(300)'))
        db.session.execute(db.text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS fees INTEGER DEFAULT 500'))
        db.session.commit()
    except Exception:
        db.session.rollback()
    # Seed admin
    if not User.query.filter_by(role='admin').first():
        pw = bcrypt.generate_password_hash('admin@medicure123').decode('utf-8')
        db.session.add(User(name='Admin', email='admin@medicure.com', password=pw, role='admin'))
        db.session.commit()
    if not User.query.filter_by(role='doctor').first():
        demo_doctors = [
            ('Dr. Arjun Mehta',  'arjun@pharmalane.com',  'Cardiologist',      'https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=200&h=200&fit=crop&crop=face'),
            ('Dr. Priya Sharma', 'priya@pharmalane.com',  'Neurologist',       'https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=200&h=200&fit=crop&crop=face'),
            ('Dr. Rahul Verma',  'rahul@pharmalane.com',  'General Physician', 'https://images.unsplash.com/photo-1622253692010-333f2da6031d?w=200&h=200&fit=crop&crop=face'),
            ('Dr. Sneha Kapoor', 'sneha@pharmalane.com',  'Dermatologist',     'https://images.unsplash.com/photo-1594824476967-48c8b964273f?w=200&h=200&fit=crop&crop=face'),
            ('Dr. Vikram Singh', 'vikram@pharmalane.com', 'Orthopedist',       'https://images.unsplash.com/photo-1537368910025-700350fe46c7?w=200&h=200&fit=crop&crop=face'),
        ]
        for name, email, spec, photo in demo_doctors:
            pw = bcrypt.generate_password_hash('doctor123').decode('utf-8')
            db.session.add(User(name=name, email=email, password=pw, role='doctor', specialty=spec, profile_image=photo))
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
