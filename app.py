from flask import Flask, redirect, url_for
import os
from models import setup_db, create_default_admin
from routes.auth    import auth_bp
from routes.admin   import admin_bp
from routes.company import company_bp
from routes.student import student_bp

app = Flask(__name__)
app.secret_key = 'vedika_agarwal_secret'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max upload

os.makedirs('instance', exist_ok=True)
setup_db()
create_default_admin()

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(company_bp)
app.register_blueprint(student_bp)

@app.route('/')
def index():
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    app.run(debug=True)