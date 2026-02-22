from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from functools import wraps
from models import get_db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ── DECORATOR ────────────────────────────────────────────────────────────────

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ── DASHBOARD ────────────────────────────────────────────────────────────────

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    conn = get_db()

    stats = {
        'total_students'  : conn.execute("SELECT COUNT(*) FROM student").fetchone()[0],
        'total_companies' : conn.execute("SELECT COUNT(*) FROM company").fetchone()[0],
        'total_drives'    : conn.execute("SELECT COUNT(*) FROM placement_drive").fetchone()[0],
        'total_apps'      : conn.execute("SELECT COUNT(*) FROM application").fetchone()[0],
        'pending_companies': conn.execute("SELECT COUNT(*) FROM company WHERE approval_status='Pending'").fetchone()[0],
        'pending_drives'  : conn.execute("SELECT COUNT(*) FROM placement_drive WHERE status='Pending'").fetchone()[0],
    }

    conn.close()
    return render_template('admin/dashboard.html', stats=stats)


# ── COMPANIES ────────────────────────────────────────────────────────────────

@admin_bp.route('/companies')
@admin_required
def companies():
    search = request.args.get('search', '').strip()
    conn   = get_db()

    if search:
        companies = conn.execute(
            "SELECT * FROM company WHERE company_name LIKE ? OR CAST(company_id AS TEXT) LIKE ?",
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        companies = conn.execute("SELECT * FROM company ORDER BY created_at DESC").fetchall()

    conn.close()
    return render_template('admin/companies.html', companies=companies, search=search)


@admin_bp.route('/companies/<int:company_id>/approve')
@admin_required
def approve_company(company_id):
    conn = get_db()
    conn.execute("UPDATE company SET approval_status='Approved' WHERE company_id=?", (company_id,))
    conn.commit()
    conn.close()
    flash('Company approved.', 'success')
    return redirect(url_for('admin.companies'))


@admin_bp.route('/companies/<int:company_id>/reject')
@admin_required
def reject_company(company_id):
    conn = get_db()
    conn.execute("UPDATE company SET approval_status='Rejected' WHERE company_id=?", (company_id,))
    conn.commit()
    conn.close()
    flash('Company rejected.', 'warning')
    return redirect(url_for('admin.companies'))


@admin_bp.route('/companies/<int:company_id>/blacklist')
@admin_required
def blacklist_company(company_id):
    conn = get_db()
    current = conn.execute("SELECT is_blacklisted FROM company WHERE company_id=?", (company_id,)).fetchone()
    new_status = 0 if current['is_blacklisted'] else 1
    conn.execute("UPDATE company SET is_blacklisted=? WHERE company_id=?", (new_status, company_id))
    conn.commit()
    conn.close()
    flash('Company blacklist status updated.', 'info')
    return redirect(url_for('admin.companies'))


@admin_bp.route('/companies/<int:company_id>/delete')
@admin_required
def delete_company(company_id):
    conn = get_db()
    conn.execute("DELETE FROM company WHERE company_id=?", (company_id,))
    conn.commit()
    conn.close()
    flash('Company deleted.', 'danger')
    return redirect(url_for('admin.companies'))


# ── STUDENTS ─────────────────────────────────────────────────────────────────

@admin_bp.route('/students')
@admin_required
def students():
    search = request.args.get('search', '').strip()
    conn   = get_db()

    if search:
        students = conn.execute(
            """SELECT * FROM student
               WHERE name LIKE ? OR CAST(student_id AS TEXT) LIKE ? OR phone LIKE ? OR email LIKE ?""",
            (f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        students = conn.execute("SELECT * FROM student ORDER BY created_at DESC").fetchall()

    conn.close()
    return render_template('admin/students.html', students=students, search=search)


@admin_bp.route('/students/<int:student_id>/blacklist')
@admin_required
def blacklist_student(student_id):
    conn = get_db()
    current = conn.execute("SELECT is_blacklisted FROM student WHERE student_id=?", (student_id,)).fetchone()
    new_status = 0 if current['is_blacklisted'] else 1
    conn.execute("UPDATE student SET is_blacklisted=? WHERE student_id=?", (new_status, student_id))
    conn.commit()
    conn.close()
    flash('Student blacklist status updated.', 'info')
    return redirect(url_for('admin.students'))


@admin_bp.route('/students/<int:student_id>/toggle_active')
@admin_required
def toggle_student_active(student_id):
    conn = get_db()
    current = conn.execute("SELECT is_active FROM student WHERE student_id=?", (student_id,)).fetchone()
    new_status = 0 if current['is_active'] else 1
    conn.execute("UPDATE student SET is_active=? WHERE student_id=?", (new_status, student_id))
    conn.commit()
    conn.close()
    flash('Student active status updated.', 'info')
    return redirect(url_for('admin.students'))


@admin_bp.route('/students/<int:student_id>/delete')
@admin_required
def delete_student(student_id):
    conn = get_db()
    conn.execute("DELETE FROM student WHERE student_id=?", (student_id,))
    conn.commit()
    conn.close()
    flash('Student deleted.', 'danger')
    return redirect(url_for('admin.students'))


# ── PLACEMENT DRIVES ─────────────────────────────────────────────────────────

@admin_bp.route('/drives')
@admin_required
def drives():
    conn   = get_db()
    drives = conn.execute("""
        SELECT pd.*, c.company_name
        FROM placement_drive pd
        JOIN company c ON pd.company_id = c.company_id
        ORDER BY pd.created_at DESC
    """).fetchall()
    conn.close()
    return render_template('admin/drives.html', drives=drives)


@admin_bp.route('/drives/<int:drive_id>/approve')
@admin_required
def approve_drive(drive_id):
    conn = get_db()
    conn.execute("UPDATE placement_drive SET status='Approved' WHERE drive_id=?", (drive_id,))
    conn.commit()
    conn.close()
    flash('Drive approved.', 'success')
    return redirect(url_for('admin.drives'))


@admin_bp.route('/drives/<int:drive_id>/reject')
@admin_required
def reject_drive(drive_id):
    conn = get_db()
    conn.execute("UPDATE placement_drive SET status='Rejected' WHERE drive_id=?", (drive_id,))
    conn.commit()
    conn.close()
    flash('Drive rejected.', 'warning')
    return redirect(url_for('admin.drives'))


# ── APPLICATIONS ─────────────────────────────────────────────────────────────

@admin_bp.route('/applications')
@admin_required
def applications():
    conn = get_db()
    apps = conn.execute("""
        SELECT a.*, s.name AS student_name, s.email AS student_email,
               pd.job_title, c.company_name
        FROM application a
        JOIN student s         ON a.student_id = s.student_id
        JOIN placement_drive pd ON a.drive_id   = pd.drive_id
        JOIN company c         ON pd.company_id = c.company_id
        ORDER BY a.application_date DESC
    """).fetchall()
    conn.close()
    return render_template('admin/applications.html', apps=apps)

@admin_bp.route('/students/<int:student_id>/view')
@admin_required
def view_student(student_id):
    conn = get_db()

    student = conn.execute(
        "SELECT * FROM student WHERE student_id=?", (student_id,)
    ).fetchone()

    if not student:
        flash('Student not found.', 'danger')
        conn.close()
        return redirect(url_for('admin.students'))

    applications = conn.execute("""
        SELECT a.*, pd.job_title, c.company_name
        FROM application a
        JOIN placement_drive pd ON a.drive_id   = pd.drive_id
        JOIN company c          ON pd.company_id = c.company_id
        WHERE a.student_id = ?
        ORDER BY a.application_date DESC
    """, (student_id,)).fetchall()

    conn.close()
    return render_template('admin/view_student.html',
                           student=student, applications=applications)