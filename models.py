import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'placement.db')

def get_db():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  
    conn.execute("PRAGMA foreign_keys = ON")  
    return conn


def create_tables():
    """Creates all tables if they don't already exist."""
    conn = get_db()
    cursor = conn.cursor()


    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            admin_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    NOT NULL UNIQUE,
            password    TEXT    NOT NULL,
            email       TEXT    NOT NULL UNIQUE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company (
            company_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name    TEXT    NOT NULL,
            email           TEXT    NOT NULL UNIQUE,
            password        TEXT    NOT NULL,
            hr_contact      TEXT,
            website         TEXT,
            description     TEXT,
            approval_status TEXT    NOT NULL DEFAULT 'Pending',
            is_blacklisted  INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student (
            student_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL,
            email           TEXT    NOT NULL UNIQUE,
            password        TEXT    NOT NULL,
            phone           TEXT,
            skills          TEXT,
            education       TEXT,
            resume_path     TEXT,
            cgpa            REAL,
            is_active       INTEGER NOT NULL DEFAULT 1,
            is_blacklisted  INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS placement_drive (
            drive_id            INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id          INTEGER NOT NULL,
            job_title           TEXT    NOT NULL,
            job_description     TEXT,
            eligibility         TEXT,
            skills_required     TEXT,
            salary_range        TEXT,
            application_deadline TEXT,
            status              TEXT    NOT NULL DEFAULT 'Pending',
            created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (company_id) REFERENCES company(company_id) ON DELETE CASCADE
        )
    ''')
 
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS application (
            application_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id      INTEGER NOT NULL,
            drive_id        INTEGER NOT NULL,
            application_date TEXT   NOT NULL DEFAULT (datetime('now')),
            status          TEXT    NOT NULL DEFAULT 'Applied',
            FOREIGN KEY (student_id) REFERENCES student(student_id) ON DELETE CASCADE,
            FOREIGN KEY (drive_id)   REFERENCES placement_drive(drive_id) ON DELETE CASCADE,
            UNIQUE (student_id, drive_id)
        )
    ''')
    conn.commit()
    conn.close()
    print("All tables created successfully.")


def seed_admin():
    """Inserts the default admin if one doesn't already exist."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM admin WHERE username = 'admin'")
    existing = cursor.fetchone()

    if not existing:
        cursor.execute('''
            INSERT INTO admin (username, password, email)
            VALUES (?, ?, ?)
        ''', ('admin', 'admin123', 'admin@placement.com'))
        conn.commit()
        print("Default admin seeded: username='admin', password='admin123'")
    else:
        print("Admin already exists, skipping seed.")

    conn.close()

def get_user_by_email(email, role):
    """
    Fetch a user by email for a given role.
    role must be: 'admin', 'student', or 'company'
    """
    conn = get_db()
    cursor = conn.cursor()

    if role == 'admin':
        cursor.execute("SELECT * FROM admin WHERE email = ?", (email,))
    elif role == 'student':
        cursor.execute("SELECT * FROM student WHERE email = ?", (email,))
    elif role == 'company':
        cursor.execute("SELECT * FROM company WHERE email = ?", (email,))
    else:
        conn.close()
        return None

    user = cursor.fetchone()
    conn.close()
    return user