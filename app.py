from flask import Flask, render_template, request, redirect, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)

# Secret Key
app.secret_key = "mysecretkey"

# Upload Folder
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Maximum File Size (5MB)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

# Allowed File Extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'txt'}

# MySQL Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root1234@localhost/secureapp'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Create uploads folder automatically
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Check File Extension
def allowed_file(filename):

    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ================= USER MODEL =================

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100))

    email = db.Column(db.String(100), unique=True)

    password = db.Column(db.String(300))

    role = db.Column(db.String(20), default='user')


# ================= FILE MODEL =================

class File(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    filename = db.Column(db.String(300))

    uploaded_by = db.Column(db.String(100))


# ================= ACTIVITY LOG MODEL =================

class ActivityLog(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(100))

    action = db.Column(db.String(300))

    time = db.Column(db.String(100))


# ================= HOME ROUTE =================

@app.route('/')
def home():

    return render_template('index.html')


# ================= REGISTER ROUTE =================

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        name = request.form['name']

        email = request.form['email']

        password = request.form['password']

        # Hash Password
        hashed_password = generate_password_hash(password)

        # Create User
        new_user = User(
            name=name,
            email=email,
            password=hashed_password
        )

        db.session.add(new_user)

        db.session.commit()

        return redirect('/login')

    return render_template('register.html')


# ================= LOGIN ROUTE =================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']

        password = request.form['password']

        # Find User
        user = User.query.filter_by(email=email).first()

        # Check Password
        if user and check_password_hash(user.password, password):

            session['user'] = user.name

            session['role'] = user.role

            # Save Login Activity
            log = ActivityLog(
                username=user.name,
                action="User Logged In",
                time=str(datetime.now())
            )

            db.session.add(log)
            db.session.commit()

            return redirect('/dashboard')

        else:

            return "Invalid Email or Password"

    return render_template('login.html')


# ================= DASHBOARD ROUTE =================

@app.route('/dashboard')
def dashboard():

    if 'user' not in session:

        return redirect('/login')

    return render_template(
        'dashboard.html',
        username=session['user']
    )


# ================= UPLOAD ROUTE =================

@app.route('/upload', methods=['GET', 'POST'])
def upload():

    if 'user' not in session:

        return redirect('/login')

    if request.method == 'POST':

        # Get Uploaded File
        file = request.files['file']

        # Check File Selected
        if file.filename == '':

            return "No File Selected"

        # Validate File Type
        if file and allowed_file(file.filename):

            # Secure Filename
            filename = secure_filename(file.filename)

            # Save File
            file.save(
                os.path.join(
                    app.config['UPLOAD_FOLDER'],
                    filename
                )
            )

            # Save File Details in Database
            new_file = File(
                filename=filename,
                uploaded_by=session['user']
            )

            db.session.add(new_file)

            # Save Upload Activity
            log = ActivityLog(
                username=session['user'],
                action=f"Uploaded File: {filename}",
                time=str(datetime.now())
            )

            db.session.add(log)

            db.session.commit()

            return "File Uploaded Successfully"

        else:

            return "Invalid File Type"

    return render_template('upload.html')


# ================= DOWNLOAD ROUTE =================

@app.route('/download/<filename>')
def download_file(filename):

    if 'user' not in session:

        return redirect('/login')

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename,
        as_attachment=True
    )


# ================= LOGOUT ROUTE =================

@app.route('/logout')
def logout():

    session.pop('user', None)

    session.pop('role', None)

    return redirect('/login')


# ================= ADMIN ROUTE =================

@app.route('/admin')
def admin():

    if 'user' not in session:

        return redirect('/login')

    if session.get('role') != 'admin':

        return "Access Denied"

    users = User.query.all()

    files = File.query.all()

    logs = ActivityLog.query.all()

    return render_template(
        'admin.html',
        users=users,
        files=files,
        logs=logs
    )


# ================= RUN APP =================

if __name__ == '__main__':

    with app.app_context():

        db.create_all()

    app.run(debug=True)