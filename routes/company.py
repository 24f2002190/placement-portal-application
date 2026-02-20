from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from functools import wraps
from models import get_db

company_bp = Blueprint('company', __name__, url_prefix='/company')


# ── DECORATOR ────────────────────────────────────────────────────────────────

def company_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'company':
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ── DASHBOARD ────────────────────────────────────────────────────────────────

@company_bp.route('/dashboard')
@company_required
def dashboard():
    company_id = session['user_id']
    conn = get_db()

    company = conn.execute(
        "SELECT * FROM company WHERE company_id=?", (company_id,)
    ).fetchone()

    # Get all drives by this company with applicant count per drive
    drives = conn.execute("""
        SELECT pd.*,
               COUNT(a.application_id) AS applicant_count
        FROM placement_drive pd
        LEFT JOIN application a ON pd.drive_id = a.drive_id
        WHERE pd.company_id = ?
        GROUP BY pd.drive_id
        ORDER BY pd.created_at DESC
    """, (company_id,)).fetchall()

    stats = {
        'total_drives'     : len(drives),
        'total_applicants' : conn.execute("""
            SELECT COUNT(*) FROM application a
            JOIN placement_drive pd ON a.drive_id = pd.drive_id
            WHERE pd.company_id = ?
        """, (company_id,)).fetchone()[0],
        'approved_drives'  : conn.execute(
            "SELECT COUNT(*) FROM placement_drive WHERE company_id=? AND status='Approved'",
            (company_id,)).fetchone()[0],
        'pending_drives'   : conn.execute(
            "SELECT COUNT(*) FROM placement_drive WHERE company_id=? AND status='Pending'",
            (company_id,)).fetchone()[0],
    }

    conn.close()
    return render_template('company/dashboard.html', company=company, drives=drives, stats=stats)


# ── CREATE DRIVE ─────────────────────────────────────────────────────────────

@company_bp.route('/drives/create', methods=['GET', 'POST'])
@company_required
def create_drive():
    if request.method == 'POST':
        job_title    = request.form.get('job_title', '').strip()
        description  = request.form.get('job_description', '').strip()
        eligibility  = request.form.get('eligibility', '').strip()
        skills       = request.form.get('skills_required', '').strip()
        salary       = request.form.get('salary_range', '').strip()
        deadline     = request.form.get('application_deadline', '').strip()

        if not job_title:
            flash('Job title is required.', 'danger')
            return render_template('company/create_drive.html')

        conn = get_db()
        conn.execute("""
            INSERT INTO placement_drive
                (company_id, job_title, job_description, eligibility,
                 skills_required, salary_range, application_deadline)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session['user_id'], job_title, description, eligibility,
              skills, salary, deadline))
        conn.commit()
        conn.close()

        flash('Drive submitted for admin approval.', 'success')
        return redirect(url_for('company.dashboard'))

    return render_template('company/create_drive.html')


# ── EDIT DRIVE ───────────────────────────────────────────────────────────────

@company_bp.route('/drives/<int:drive_id>/edit', methods=['GET', 'POST'])
@company_required
def edit_drive(drive_id):
    conn  = get_db()
    drive = conn.execute(
        "SELECT * FROM placement_drive WHERE drive_id=? AND company_id=?",
        (drive_id, session['user_id'])
    ).fetchone()

    if not drive:
        flash('Drive not found.', 'danger')
        conn.close()
        return redirect(url_for('company.dashboard'))

    if request.method == 'POST':
        job_title   = request.form.get('job_title', '').strip()
        description = request.form.get('job_description', '').strip()
        eligibility = request.form.get('eligibility', '').strip()
        skills      = request.form.get('skills_required', '').strip()
        salary      = request.form.get('salary_range', '').strip()
        deadline    = request.form.get('application_deadline', '').strip()

        conn.execute("""
            UPDATE placement_drive
            SET job_title=?, job_description=?, eligibility=?,
                skills_required=?, salary_range=?, application_deadline=?,
                status='Pending'
            WHERE drive_id=? AND company_id=?
        """, (job_title, description, eligibility, skills, salary, deadline,
              drive_id, session['user_id']))
        # status resets to Pending so admin re-approves any edits
        conn.commit()
        conn.close()

        flash('Drive updated and resubmitted for approval.', 'success')
        return redirect(url_for('company.dashboard'))

    conn.close()
    return render_template('company/edit_drive.html', drive=drive)


# ── CLOSE DRIVE ──────────────────────────────────────────────────────────────

@company_bp.route('/drives/<int:drive_id>/close')
@company_required
def close_drive(drive_id):
    conn = get_db()
    conn.execute("""
        UPDATE placement_drive SET status='Closed'
        WHERE drive_id=? AND company_id=?
    """, (drive_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Drive closed.', 'info')
    return redirect(url_for('company.dashboard'))


# ── DELETE DRIVE ─────────────────────────────────────────────────────────────

@company_bp.route('/drives/<int:drive_id>/delete')
@company_required
def delete_drive(drive_id):
    conn = get_db()
    conn.execute("""
        DELETE FROM placement_drive
        WHERE drive_id=? AND company_id=?
    """, (drive_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Drive deleted.', 'danger')
    return redirect(url_for('company.dashboard'))


# ── VIEW APPLICATIONS FOR A DRIVE ────────────────────────────────────────────

@company_bp.route('/drives/<int:drive_id>/applications')
@company_required
def drive_applications(drive_id):
    conn = get_db()

    # Make sure this drive belongs to this company
    drive = conn.execute("""
        SELECT * FROM placement_drive
        WHERE drive_id=? AND company_id=?
    """, (drive_id, session['user_id'])).fetchone()

    if not drive:
        flash('Drive not found.', 'danger')
        conn.close()
        return redirect(url_for('company.dashboard'))

    applications = conn.execute("""
        SELECT a.*, s.name, s.email, s.phone, s.skills,
               s.education, s.cgpa, s.resume_path
        FROM application a
        JOIN student s ON a.student_id = s.student_id
        WHERE a.drive_id = ?
        ORDER BY a.application_date DESC
    """, (drive_id,)).fetchall()

    conn.close()
    return render_template('company/applications.html',
                           drive=drive, applications=applications)


# ── UPDATE APPLICATION STATUS ─────────────────────────────────────────────────

@company_bp.route('/applications/<int:application_id>/update', methods=['POST'])
@company_required
def update_application(application_id):
    new_status = request.form.get('status')
    valid = ['Applied', 'Shortlisted', 'Selected', 'Rejected']

    if new_status not in valid:
        flash('Invalid status.', 'danger')
        return redirect(url_for('company.dashboard'))

    conn = get_db()

    # Get drive_id so we can redirect back to the right applications page
    app_row = conn.execute("""
        SELECT a.drive_id FROM application a
        JOIN placement_drive pd ON a.drive_id = pd.drive_id
        WHERE a.application_id=? AND pd.company_id=?
    """, (application_id, session['user_id'])).fetchone()

    if not app_row:
        flash('Application not found.', 'danger')
        conn.close()
        return redirect(url_for('company.dashboard'))

    conn.execute("""
        UPDATE application SET status=?
        WHERE application_id=?
    """, (new_status, application_id))
    conn.commit()
    drive_id = app_row['drive_id']
    conn.close()

    flash(f'Application status updated to {new_status}.', 'success')
    return redirect(url_for('company.drive_applications', drive_id=drive_id))