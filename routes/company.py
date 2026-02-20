from flask import Blueprint, render_template, session, redirect, url_for
from functools import wraps

company_bp = Blueprint('company', __name__, url_prefix='/company')

def company_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'company':
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

@company_bp.route('/dashboard')
@company_required
def dashboard():
    return render_template('company/dashboard.html')