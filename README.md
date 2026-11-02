# WorkEase — Employee Management System

WorkEase is a Django-based web application designed to simplify employee management and everyday HR operations.

## Features

- **Employee Management:** Employee directory, profiles, departments, and user account linking.
- **Attendance Tracking:** Geofenced check-in/check-out with GPS radius validation and working hours tracking.
- **Leave Management:** Applications, manager approvals/rejections, and automated email updates.
- **Payroll & Payment Gateway API:** Monthly and hourly salary computation, PDF payslip generation, and **Default Payment Gateway API** (Razorpay integration for salary disbursement, verification, and payment tracking).
- **Company Holiday Calendar:** Festival, national, and company holidays with upcoming calendar alerts.
- **Smart RBAC Authentication:** Unified single login page for employees (Employee ID / username) and administrators.

## Tech Stack

- **Backend:** Python 3.13, Django 6.1
- **Database:** PostgreSQL (Neon / Render / Railway / Back4app) & SQLite (Local fallback)
- **Payment Gateway API:** Razorpay (Default Gateway API with zero-dependency test simulation)
- **Reports & PDF:** ReportLab for official monthly salary slips
- **Frontend:** Bootstrap 5.3, Bootstrap Icons, HTML5, Vanilla JavaScript

## Payment Gateway API Configuration

WorkEase includes a configurable **Default Gateway API** for payroll disbursements:

In `workease/settings.py` (and `.env`):
- `DEFAULT_GATEWAY_API`: Default provider (`razorpay`). Extensible to Stripe and Cashfree.
- `RAZORPAY_KEY_ID`: Razorpay API Key ID (e.g. `rzp_test_...` or `rzp_live_...`).
- `RAZORPAY_KEY_SECRET`: Razorpay API Secret Key.
- `RAZORPAY_WEBHOOK_SECRET`: Optional webhook secret for asynchronous payment callbacks (`/api/payment/webhook/`).
- `PAYMENT_GATEWAY_CURRENCY`: Default currency code (default: `INR`).

> **Note for Local Development:** When `RAZORPAY_KEY_ID` is not set or set to mock values, WorkEase automatically activates **Test / Simulation Mode**, allowing administrators to test order generation, checkout simulation, signature validation, and email disbursement locally without requiring live network access or real credentials.

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

Linux / macOS:
```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to `.env` and configure your credentials:
```bash
cp .env.example .env
```

Set `DJANGO_SECRET_KEY`, `DEFAULT_GATEWAY_API`, `RAZORPAY_KEY_ID`, and database/email parameters as needed.

### 5. Run database migrations

```bash
python manage.py migrate
```

### 6. Start the development server

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.

## Running Tests

Execute the full automated test suite:

```bash
python manage.py test
```

## Project Status

This project is actively maintained.

## Author

**drij-ai**
