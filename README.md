# WorkEase — Employee Management System

WorkEase is a Django-based web application designed to simplify employee management and everyday HR operations.

## Features

- Employee management
- Attendance tracking
- Leave management
- Payroll management
- Work location management
- User authentication

## Tech Stack

- **Backend:** Python, Django
- **Database:** SQLite
- **Frontend:** HTML, CSS, JavaScript

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/drij-ai/WorkEase.git
cd WorkEase
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Django secret key

Set the `DJANGO_SECRET_KEY` environment variable before running the application. Do not commit secret keys to GitHub.

### 5. Run database migrations

```bash
python manage.py migrate
```

### 6. Start the development server

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.

## Project Status

This project is under development.

## Author

**drij-ai**
