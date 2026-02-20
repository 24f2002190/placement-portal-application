import os
from models import create_tables, seed_admin

os.makedirs('instance', exist_ok=True)

print("Initializing database...")
create_tables()
seed_admin()
print("Database ready at instance/placement.db")