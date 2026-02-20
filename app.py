from flask import Flask, redirect, url_for
import os
from models import create_tables, seed_admin
from routes.auth    import auth_bp
from routes.admin   import admin_bp
from routes.company import company_bp
from routes.student import student_bp

app = Flask(__name__)
app.secret_key = 'ppa_secret_key_change_in_production'

# Set up DB on startup
os.makedirs('instance', exist_ok=True)
create_tables()
seed_admin()

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(company_bp)
app.register_blueprint(student_bp)

@app.route('/')
def index():
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    app.run(debug=True)