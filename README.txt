🧾 AL-ATTAR CLOTHING INVOICE SYSTEM – INSTALLATION GUIDE

🖥️ SYSTEM REQUIREMENTS:
- Python 3.11+
- PostgreSQL (v15+ recommended)
- pip

🧱 INSTALL STEPS:

1. Install Python dependencies:
   > pip install -r requirements.txt

2. Setup PostgreSQL:
   - Install PostgreSQL from https://www.postgresql.org/download/windows/
   - Create a database named: al_attar_db
   - Create a user (e.g., postgres) with access to the DB

3. Configure environment:
   - Copy `.env.example` to `.env`
   - Update credentials inside `.env` file (DB name, user, password, etc.)

4. Run database migrations:
   > python manage.py migrate

5. Create admin user:
   > python manage.py createsuperuser

6. (Optional) Load sample data:
   > python manage.py loaddata data.json

7. Start the server:
   > python manage.py runserver

📂 Access the site:
- http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin

✅ You’re ready to go!
