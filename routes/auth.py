from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import connect_db, fetch_user

auth_bp = Blueprint('auth', __name__)


# ── LOGIN ────────────────────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
   
    if 'user_id' in session:
        return redirect(url_for(session['role'] + '.dashboard'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        role     = request.form.get('role', '').strip()  

        if not email or not password or not role:
            flash('All fields are required. Please try again.', 'danger')
            return render_template('auth/login.html')

        user = fetch_user(email, role)

        if not user:
            flash('Invalid credentials. Please check your details.', 'danger')
            return render_template('auth/login.html')

        # Check password — admin was seeded with plain text so handle separately
        # For admin seeded with plain text 'admin123':
        if role == 'admin':
            password_correct = (password == user['password'])
        else:
            password_correct = check_password_hash(user['password'], password)

        if not password_correct:
            flash('Wrong password. Please try again.', 'danger')
            return render_template('auth/login.html')

        if role == 'company':
            if user['approval_status'] == 'Pending':
                flash('Your account is under review. Please wait for admin verification.', 'warning')
                return render_template('auth/login.html')
            if user['approval_status'] == 'Rejected':
                flash('Your registration was not approved. Please contact the admin.', 'danger')
                return render_template('auth/login.html')
            if user['is_blacklisted']:
                flash('Your account has been suspended. Please contact the placement cell.', 'danger')
                return render_template('auth/login.html')

        if role == 'student':
            if user['is_blacklisted']:
                flash('Your account has been suspended. Please contact the placement cell.', 'danger')
                return render_template('auth/login.html')
            if not user['is_active']:
                flash('Your account is currently inactive. Please contact the placement cell.', 'danger')
                return render_template('auth/login.html')

        if role == 'admin':
            session['user_id']   = user['admin_id']
            session['user_name'] = user['username']
        elif role == 'student':
            session['user_id']   = user['student_id']
            session['user_name'] = user['name']
        elif role == 'company':
            session['user_id']   = user['company_id']
            session['user_name'] = user['company_name']

        session['role']  = role
        session['email'] = user['email']

        flash(f'Login successful! Welcome back, {session["user_name"]}.', 'success')
        return redirect(url_for(role + '.dashboard'))

    return render_template('auth/login.html')


# ── STUDENT REGISTRATION ─────────────────────────────────────────────────────

@auth_bp.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        name      = request.form.get('name', '').strip()
        email     = request.form.get('email', '').strip()
        password  = request.form.get('password', '').strip()
        phone     = request.form.get('phone', '').strip()
        education = request.form.get('education', '').strip()
        skills    = request.form.get('skills', '').strip()
        cgpa      = request.form.get('cgpa', '').strip()

        # Validation
        if not name or not email or not password:
            flash('Name, email, and password are required.', 'danger')
            return render_template('auth/register_student.html')

        existing = fetch_user(email, 'student')
        if existing:
            flash('An account with this email already exists.', 'danger')
            return render_template('auth/register_student.html')

        hashed_password = generate_password_hash(password)

        conn = connect_db()
        try:
            conn.execute('''
                INSERT INTO student (name, email, password, phone, education, skills, cgpa)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, email, hashed_password, phone, education, skills,
                  float(cgpa) if cgpa else None))
            conn.commit()
            flash('Account created successfully! You can now sign in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'danger')
        finally:
            conn.close()

    return render_template('auth/register_student.html')


# ── COMPANY REGISTRATION ─────────────────────────────────────────────────────

@auth_bp.route('/register/company', methods=['GET', 'POST'])
def register_company():
    if request.method == 'POST':
        company_name = request.form.get('company_name', '').strip()
        email        = request.form.get('email', '').strip()
        password     = request.form.get('password', '').strip()
        hr_contact   = request.form.get('hr_contact', '').strip()
        website      = request.form.get('website', '').strip()
        description  = request.form.get('description', '').strip()

        if not company_name or not email or not password:
            flash('Company name, email, and password are required.', 'danger')
            return render_template('auth/register_company.html')

        existing = fetch_user(email, 'company')
        if existing:
            flash('A company with this email already exists.', 'danger')
            return render_template('auth/register_company.html')

        hashed_password = generate_password_hash(password)

        conn = connect_db()
        try:
            conn.execute('''
                INSERT INTO company (company_name, email, password, hr_contact, website, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (company_name, email, hashed_password, hr_contact, website, description))
            conn.commit()
            flash('Company registered successfully! Please wait for admin approval before signing in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'danger')
        finally:
            conn.close()

    return render_template('auth/register_company.html')


# ── LOGOUT ───────────────────────────────────────────────────────────────────

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been signed out successfully.', 'info')
    return redirect(url_for('auth.login'))