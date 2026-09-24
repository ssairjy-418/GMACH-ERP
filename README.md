# GMACH-ERP

A single Flask application for **Attendance + Inventory + HR/Employee Management + Leave**.

## Included
- Role-based login: Admin, HR, Manager, Inventory, Employee
- Employee Master
- Check-in / Check-out attendance
- Attendance CSV export
- Inventory master
- Stock add / issue / return transaction foundation
- Low-stock indicator
- Inventory CSV export
- Leave request and approval
- Employee profile and password change
- SQLite database with automatic first-run setup

## Local setup

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

### First login
- Employee ID: `ADMIN001`
- Password: `ChangeMe123!`
- Email: `admin@gmachaero.com`

**Change the admin password immediately after first login.**

## GitHub

From the project folder:

```bash
git init
git add .
git commit -m "Initial GMACH ERP application"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

## Production deployment

Set a strong `SECRET_KEY` environment variable and use PostgreSQL for a multi-user production deployment. The included `Procfile` can be used by platforms that support Gunicorn.

## Next recommended modules
- Employee document upload
- Salary/CTC and payslips
- Expense claims
- Purchase orders
- Asset assignment with employee acknowledgement
- Attendance monthly summary and late rules
- Holiday calendar
- Email/WhatsApp notifications
- Excel import/export for Employee Master and Inventory
- Audit logs
- Backup/restore
