from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from functools import wraps
from models import get_db
import os
from werkzeug.utils import secure_filename

student_bp = Blueprint('student', __name__, url_prefix='/student')

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ── DECORATOR ────────────────────────────────────────────────────────────────

def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'student':
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ── DASHBOARD ────────────────────────────────────────────────────────────────

@student_bp.route('/dashboard')
@student_required
def dashboard():
    student_id = session['user_id']
    conn = get_db()

    # All approved drives with company name
    # Also check if this student has already applied to each drive
    drives = conn.execute("""
        SELECT pd.*, c.company_name,
               a.application_id, a.status AS app_status
        FROM placement_drive pd
        JOIN company c ON pd.company_id = c.company_id
        LEFT JOIN application a
               ON pd.drive_id = a.drive_id AND a.student_id = ?
        WHERE pd.status = 'Approved'
        ORDER BY pd.created_at DESC
    """, (student_id,)).fetchall()

    # Student's own applications with drive and company info
    my_applications = conn.execute("""
        SELECT a.*, pd.job_title, pd.salary_range,
               pd.application_deadline, c.company_name
        FROM application a
        JOIN placement_drive pd ON a.drive_id = pd.drive_id
        JOIN company c ON pd.company_id = c.company_id
        WHERE a.student_id = ?
        ORDER BY a.application_date DESC
    """, (student_id,)).fetchall()

    conn.close()
    return render_template('student/dashboard.html',
                           drives=drives,
                           my_applications=my_applications)


# ── APPLY FOR A DRIVE ────────────────────────────────────────────────────────

@student_bp.route('/apply/<int:drive_id>', methods=['POST'])
@student_required
def apply(drive_id):
    student_id = session['user_id']
    conn = get_db()

    # Check drive exists and is approved
    drive = conn.execute("""
        SELECT * FROM placement_drive
        WHERE drive_id = ? AND status = 'Approved'
    """, (drive_id,)).fetchone()

    if not drive:
        flash('This drive is not available.', 'danger')
        conn.close()
        return redirect(url_for('student.dashboard'))

    # Check for duplicate application
    existing = conn.execute("""
        SELECT * FROM application
        WHERE student_id = ? AND drive_id = ?
    """, (student_id, drive_id)).fetchone()

    if existing:
        flash('You have already applied for this drive.', 'warning')
        conn.close()
        return redirect(url_for('student.dashboard'))

    # Insert application
    try:
        conn.execute("""
            INSERT INTO application (student_id, drive_id)
            VALUES (?, ?)
        """, (student_id, drive_id))
        conn.commit()
        flash('Application submitted successfully!', 'success')
    except Exception as e:
        flash(f'Could not apply: {str(e)}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('student.dashboard'))


# ── VIEW APPLICATION HISTORY ─────────────────────────────────────────────────

@student_bp.route('/applications')
@student_required
def applications():
    student_id = session['user_id']
    conn = get_db()

    apps = conn.execute("""
        SELECT a.*, pd.job_title, pd.job_description,
               pd.salary_range, pd.application_deadline,
               pd.skills_required, c.company_name
        FROM application a
        JOIN placement_drive pd ON a.drive_id = pd.drive_id
        JOIN company c ON pd.company_id = c.company_id
        WHERE a.student_id = ?
        ORDER BY a.application_date DESC
    """, (student_id,)).fetchall()

    conn.close()
    return render_template('student/applications.html', apps=apps)


# ── EDIT PROFILE ─────────────────────────────────────────────────────────────

@student_bp.route('/profile', methods=['GET', 'POST'])
@student_required
def profile():
    student_id = session['user_id']
    conn = get_db()

    student = conn.execute(
        "SELECT * FROM student WHERE student_id = ?", (student_id,)
    ).fetchone()

    if request.method == 'POST':
        name      = request.form.get('name', '').strip()
        phone     = request.form.get('phone', '').strip()
        education = request.form.get('education', '').strip()
        skills    = request.form.get('skills', '').strip()
        cgpa      = request.form.get('cgpa', '').strip()

        if not name:
            flash('Name is required.', 'danger')
            conn.close()
            return render_template('student/profile.html', student=student)

        # Handle resume upload
        resume_path = student['resume_path']  # keep existing if no new file
        file = request.files.get('resume')

        if file and file.filename:
            if allowed_file(file.filename):
                # Make sure uploads folder exists
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                filename    = secure_filename(f"student_{student_id}_{file.filename}")
                save_path   = os.path.join(UPLOAD_FOLDER, filename)
                file.save(save_path)
                resume_path = os.path.join('uploads', filename)
            else:
                flash('Only PDF, DOC, DOCX files allowed for resume.', 'danger')
                conn.close()
                return render_template('student/profile.html', student=student)

        conn.execute("""
            UPDATE student
            SET name=?, phone=?, education=?, skills=?, cgpa=?, resume_path=?
            WHERE student_id=?
        """, (name, phone, education, skills,
              float(cgpa) if cgpa else None,
              resume_path, student_id))
        conn.commit()

        # Update name in session
        session['user_name'] = name
        flash('Profile updated successfully!', 'success')
        conn.close()
        return redirect(url_for('student.profile'))

    conn.close()
    return render_template('student/profile.html', student=student)

@student_bp.route('/history')
@student_required
def history():
    student_id = session['user_id']
    conn = get_db()

    # Complete history — all statuses, all time, never filtered out
    history = conn.execute("""
        SELECT a.*, pd.job_title, pd.job_description,
               pd.salary_range, pd.eligibility,
               pd.skills_required, pd.application_deadline,
               pd.status AS drive_status,
               c.company_name, c.website
        FROM application a
        JOIN placement_drive pd ON a.drive_id  = pd.drive_id
        JOIN company c          ON pd.company_id = c.company_id
        WHERE a.student_id = ?
        ORDER BY a.application_date DESC
    """, (student_id,)).fetchall()

    # Summary counts
    summary = {
        'total'      : len(history),
        'applied'    : sum(1 for h in history if h['status'] == 'Applied'),
        'shortlisted': sum(1 for h in history if h['status'] == 'Shortlisted'),
        'selected'   : sum(1 for h in history if h['status'] == 'Selected'),
        'rejected'   : sum(1 for h in history if h['status'] == 'Rejected'),
    }

    conn.close()
    return render_template('student/history.html', history=history, summary=summary)