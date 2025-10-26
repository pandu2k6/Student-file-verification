from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session
import os
import shutil
import random
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
# The ObjectId import is no longer needed since we are using composite keys
# from bson.objectid import ObjectId 

# Load environment variables from .env file
load_dotenv()

# Placeholder for check_conditions (for demonstration purposes)
def check_conditions(filepath, conditions):
    """
    Simulates document content verification based on teacher-defined keywords.
    """
    filename = os.path.basename(filepath)
    is_verified = any(cond in filename.lower() for cond in conditions)
    if not is_verified:
        return False, f"File name must contain one of these keywords: {', '.join(conditions)}"
    return True, "Conditions met."

# --- DATABASE AND EMAIL CONFIGURATION ---
MONGO_URI = os.getenv("MONGO_URI")
MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'your_email@gmail.com')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', 'your_app_password')
SECRET_KEY = os.getenv('SECRET_KEY', 'a_default_secret_for_dev')

# Global variables for MongoDB collections
client = None
db = None
users_col = None
settings_col = None
files_col = None
otps_col = None
TEACHER_CONFIG_ID = 'teacher_config'
DB_INITIALIZED = False

def initialize_db_collections():
    """Initializes MongoDB connection and collection handles."""
    global client, db, users_col, settings_col, files_col, otps_col, DB_INITIALIZED
    try:
        client = MongoClient(MONGO_URI)
        client.admin.command('ping')
        
        db = client.get_database("doc_verify") 
        
        users_col = db.users
        settings_col = db.settings
        files_col = db.files
        otps_col = db.otps
        
        settings_col.update_one(
            {'_id': TEACHER_CONFIG_ID},
            {'$setOnInsert': {'conditions': [], 'required_file_extension': ''}},
            upsert=True
        )
        DB_INITIALIZED = True
        print("Successfully connected to MongoDB Atlas and initialized collections.")
        
    except Exception as e:
        print("--- MongoDB CONNECTION FAILED ---")
        print(f"Error: {e}")
        print("Please ensure your Atlas cluster is running and your MONGO_URI is correct and whitelisted.")
        print("---------------------------------")


# Initialize DB immediately upon starting the app
initialize_db_collections()


# --- APP SETUP ---
app = Flask(__name__)
app.secret_key = SECRET_KEY

UPLOAD_FOLDER = 'uploads'
VERIFIED_FOLDER = 'verified'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(VERIFIED_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['VERIFIED_FOLDER'] = VERIFIED_FOLDER

# FUNCTIONS FOR OTP/EMAIL
def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(email, otp):
    try:
        msg = MIMEText(f"Your password reset OTP is: {otp}\nIt is valid for a short time.")
        msg['Subject'] = 'Password Reset OTP'
        msg['From'] = MAIL_USERNAME
        msg['To'] = email

        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.sendmail(MAIL_USERNAME, email, msg.as_string())
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

# ------------------------------------------------------------------
# UTILITY FUNCTIONS
# ------------------------------------------------------------------

def get_teacher_settings():
    """Fetches teacher settings (conditions, extension) from MongoDB."""
    settings = settings_col.find_one({'_id': TEACHER_CONFIG_ID})
    if not settings:
        return {'conditions': [], 'required_file_extension': ''}
    return settings

# ------------------------------------------------------------------
# ROUTES 
# ------------------------------------------------------------------

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    form_type = None
    success_message = session.pop('success_message', None) 
    
    if not DB_INITIALIZED: 
        error = "Database Connection Error. Please check server logs."
        return render_template('index.html', error=error, form_type='login', success_message=success_message)

    if 'username' in session:
        if session.get('role') == 'student':
            return redirect(url_for('student'))
        elif session.get('role') == 'teacher':
            return redirect(url_for('teacher'))
            
    if request.method == 'POST':
        form_type = request.form.get("form_type")
        uname = request.form.get('username')
        pwd = request.form.get('password')

        if form_type == "login":
            user = users_col.find_one({'email': uname})
            
            if user and check_password_hash(user['password_hash'], pwd):
                session['username'] = uname
                session['role'] = user['role']
                
                if user['role'] == "student":
                    return redirect(url_for('student'))
                else:
                    return redirect(url_for('teacher'))
            else:
                error = "Invalid Credentials"

        elif form_type == "signup":
            role = request.form.get("role", "student")
            if users_col.find_one({'email': uname}):
                error = "Username already exists"
            else:
                password_hash = generate_password_hash(pwd)
                users_col.insert_one({'email': uname, 'password_hash': password_hash, 'role': role})
                
                session['username'] = uname
                session['role'] = role
                
                if role == "student":
                    return redirect(url_for('student'))
                else:
                    return redirect(url_for('teacher'))

    return render_template('index.html', error=error, form_type=form_type, success_message=success_message)

@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('login'))

# FORGOT PASSWORD ROUTES (Omitted for brevity, logic unchanged)
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if not DB_INITIALIZED: return redirect(url_for('login'))
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        
        if users_col.find_one({'email': email}):
            otp = generate_otp()
            otps_col.update_one(
                {'email': email},
                {'$set': {'code': otp, 'expires': datetime.utcnow() + timedelta(minutes=10)}},
                upsert=True
            )
            
            if send_otp_email(email, otp):
                return redirect(url_for('verify_otp', email=email))
            else:
                error = "Failed to send OTP email. Check server logs and configuration."
        else:
            error = "Email not found."
    return render_template('forgot_password.html', error=error)

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if not DB_INITIALIZED: return redirect(url_for('login'))
    error = None
    email = request.args.get('email') or request.form.get('email')
    if not email: return redirect(url_for('forgot_password'))
        
    if request.method == 'POST':
        submitted_otp = request.form.get('otp')
        new_password = request.form.get('new_password')
        otp_doc = otps_col.find_one({'email': email, 'code': submitted_otp})
        
        if otp_doc and otp_doc['expires'] > datetime.utcnow():
            if not new_password or len(new_password) < 6:
                error = "New password must be at least 6 characters."
            else:
                new_hash = generate_password_hash(new_password)
                users_col.update_one({'email': email}, {'$set': {'password_hash': new_hash}})
                otps_col.delete_one({'email': email})
                session['success_message'] = "Password successfully reset! Please sign in."
                return redirect(url_for('login'))
        else:
            error = "Invalid or expired OTP."

    return render_template('verify_otp.html', email=email, error=error)


# ------------------------------------------------------------------
# STUDENT PORTAL 
# ------------------------------------------------------------------

@app.route('/student', methods=['GET', 'POST'])
def student():
    if not DB_INITIALIZED: return redirect(url_for('login'))
    if session.get('role') != 'student':
        return redirect(url_for('login'))
        
    status_message = ""
    current_user_email = session['username']
    
    settings = get_teacher_settings()
    teacher_conditions = settings['conditions']
    required_file_extension = settings['required_file_extension']
    
    current_user_files = files_col.find({'uploader': current_user_email})

    if request.method == 'POST':
        file = request.files.get('file')
        
        if file and file.filename:
            filename = file.filename
            is_verified = True
            reason = "Conditions met."
            
            # 1. OPTIONAL CHECK: File Extension
            if required_file_extension:
                if not filename.lower().endswith(required_file_extension):
                    is_verified = False
                    reason = f"File Rejected ❌: Only {required_file_extension.upper()} files are accepted."
            
            # 2. OPTIONAL CHECK: Keywords
            if is_verified and teacher_conditions:
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath) 
                
                is_verified, reason = check_conditions(filepath, teacher_conditions)

            
            if is_verified:
                if not os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
                     file.save(os.path.join(UPLOAD_FOLDER, filename))
                     
                shutil.copy(os.path.join(UPLOAD_FOLDER, filename), os.path.join(VERIFIED_FOLDER, filename))
                
                # Use replace_one to overwrite the existing document if the student re-submits the same filename.
                files_col.replace_one(
                    {"filename": filename, "uploader": current_user_email}, # Filter by filename AND uploader
                    {
                        "filename": filename,
                        "uploader": current_user_email,
                        "feedback": "Awaiting teacher feedback.",
                        "status": "Verified (Awaiting Feedback)",
                        "upload_date": datetime.utcnow()
                    },
                    upsert=True # Insert if not found
                )
                status_message = f"File '{filename}' Verified ✅ and sent to teacher for review."
            else:
                status_message = f"Not Verified ❌: {reason}"
        else:
            status_message = "No file selected for upload ❌"
            
        current_user_files = files_col.find({'uploader': current_user_email})
            
    return render_template('student.html', 
                           status=status_message, 
                           username=current_user_email,
                           files=list(current_user_files),
                           teacher_conditions=teacher_conditions,
                           required_extension=required_file_extension) 

# ------------------------------------------------------------------
# TEACHER PORTAL (FIXED FEEDBACK UPDATE USING COMPOSITE KEY)
# ------------------------------------------------------------------

@app.route('/teacher', methods=['GET', 'POST'])
def teacher():
    if not DB_INITIALIZED: return redirect(url_for('login'))
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))
        
    settings = get_teacher_settings()
    teacher_conditions = settings['conditions']
    required_file_extension = settings['required_file_extension']
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            new_conds = request.form.get('conditions', '')
            new_list = teacher_conditions + [c.strip().lower() for c in new_conds.split(',') if c.strip()]
            settings_col.update_one({'_id': TEACHER_CONFIG_ID}, {'$set': {'conditions': new_list}})
            teacher_conditions = new_list
            
        elif action == 'remove':
            to_remove = request.form.get('remove_condition', '').strip().lower()
            if to_remove in teacher_conditions:
                teacher_conditions.remove(to_remove)
                settings_col.update_one({'_id': TEACHER_CONFIG_ID}, {'$set': {'conditions': teacher_conditions}})
                
        elif action == 'clear_verified':
            for f in os.listdir(VERIFIED_FOLDER):
                os.remove(os.path.join(VERIFIED_FOLDER, f))
            files_col.delete_many({})
            
        elif action == 'set_extension':
            new_ext = request.form.get('file_extension', '').strip().lower()
            if new_ext:
                if not new_ext.startswith('.'):
                    new_ext = '.' + new_ext
            settings_col.update_one({'_id': TEACHER_CONFIG_ID}, {'$set': {'required_file_extension': new_ext}})
            required_file_extension = new_ext
        
        # 🌟 FIXED FEEDBACK submission logic using composite key
        elif action == 'submit_feedback':
            filename = request.form.get('filename')
            uploader_email = request.form.get('uploader_email') # Get uploader email from form
            feedback = request.form.get('feedback')
            
            # Use the combination of filename AND uploader_email to find the unique document
            files_col.update_one(
                {'filename': filename, 'uploader': uploader_email}, 
                {'$set': {"feedback": feedback, "status": "Feedback Received"}}
            )

    verified_files = files_col.find()

    return render_template('teacher.html', 
                           conditions=teacher_conditions, 
                           files=verified_files, 
                           username=session['username'],
                           required_extension=required_file_extension) 

@app.route('/download/<filename>')
def download_file(filename):
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))
    return send_from_directory(VERIFIED_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    if DB_INITIALIZED:
        if not users_col.find_one({'email': "student@gmail.com"}):
             users_col.insert_one({'email': "student@gmail.com", 'password_hash': generate_password_hash("student123"), 'role': "student"})
        if not users_col.find_one({'email': "teacher@gmail.com"}):
             users_col.insert_one({'email': "teacher@gmail.com", 'password_hash': generate_password_hash("teacher123"), 'role': "teacher"})

    app.run(debug=True)
