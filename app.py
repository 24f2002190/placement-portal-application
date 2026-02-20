from flask import Flask
from models import create_tables, seed_admin
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  

os.makedirs('instance', exist_ok=True)
create_tables()
seed_admin()

@app.route('/')
def index():
    return "Placement Portal is running!"

if __name__ == '__main__':
    app.run(debug=True)