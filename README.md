# WorkEase - Enterprise Employee & HR Management System

[![Django CI/CD Pipeline](https://github.com/drij-ai/WorkEase/actions/workflows/django.yml/badge.svg)](https://github.com/drij-ai/WorkEase/actions/workflows/django.yml)
![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)
![Django Version](https://img.shields.io/badge/django-6.1.1-green.svg)
![DRF Version](https://img.shields.io/badge/DRF-3.15%2B-red.svg)
![OpenAPI 3.0](https://img.shields.io/badge/OpenAPI-3.0.3-teal.svg)
![License](https://img.shields.io/badge/license-MIT-purple.svg)
![Maintenance](https://img.shields.io/badge/status-active-success.svg)

**WorkEase** is a production-grade Human Resource Management System (HRMS) and Workforce Management platform engineered with Django 6 and Django REST Framework (DRF). Built with a hybrid architecture combining Django's robust Model-View-Template (MVT) pattern for administrative operations with enterprise RESTful APIs documented under OpenAPI 3.0 via `drf-spectacular`.

---

## 🌐 Live Deployments & API Documentation

| Service / Resource | Access URL | Description |
| :--- | :--- | :--- |
| **Production Web Application** | [work-ease-phi.vercel.app](https://work-ease-phi.vercel.app/) | Live cloud web application deployed on Vercel |
| **Interactive Swagger UI** | [/api/docs/](https://work-ease-phi.vercel.app/api/docs/) | OpenAPI 3.0 interactive Swagger exploration & testing |
| **Interactive ReDoc** | [/api/redoc/](https://work-ease-phi.vercel.app/api/redoc/) | Detailed, human-readable OpenAPI endpoint reference |
| **OpenAPI Schema (Raw)** | [/api/schema/](https://work-ease-phi.vercel.app/api/schema/) | Machine-readable OpenAPI 3.0.3 schema specification |
| **Health Check Probe** | [/health](https://work-ease-phi.vercel.app/health) | Uptime & container orchestration probe (JSON) |

---

## 🏗️ System Architecture

WorkEase is architected as an enterprise dual-flow platform, serving responsive web interfaces to administrators and employees while exposing standardized, authenticated REST endpoints to external microservices and client applications.

```mermaid
flowchart TD
    subgraph Clients["Client Layer"]
        Browser["Web Browser (Admin / Employee)"]
        APIClient["API Consumer / Mobile Client"]
    end

    subgraph Gateway["Routing & Gateway Layer"]
        Vercel["Edge CDN & Proxy (Vercel / Render)"]
        Security["Django Security & Middleware (WhiteNoise / CSRF / Auth)"]
    end

    subgraph Application["Application Layer (WorkEase Core)"]
        direction TB
        subgraph MVTFlow["Django MVT (Templates & Views)"]
            Views["Class & Function Views"]
            Templates["Bootstrap 5.3 Responsive Templates"]
        end

        subgraph DRFFlow["Django REST Framework (API v1)"]
            Router["DefaultRouter (/api/v1/)"]
            ViewSets["ModelViewSets (Employees, Attendance, Leave, Payroll)"]
            Serializers["ModelSerializers & Validators"]
            Swagger["drf-spectacular (OpenAPI 3.0 / Swagger / ReDoc)"]
        end

        Models["Django ORM Models (Employee, Attendance, Leave, Payroll)"]
    end

    subgraph External["External Integrations & Services"]
        Razorpay["Razorpay Payment Gateway API"]
        ReportLab["ReportLab PDF Payslip Engine"]
        EmailService["SMTP Email Notification Service"]
    end

    subgraph Persistence["Persistence Layer"]
        DB[("PostgreSQL Database / SQLite Local")]
    end

    Browser -->|HTTP Requests| Vercel
    APIClient -->|JSON REST Requests| Vercel
    Vercel --> Security
    Security -->|HTML / Form Requests| Views
    Security -->|API / Swagger Requests| Router
    Router --> ViewSets
    ViewSets --> Serializers
    Serializers --> Models
    Views --> Templates
    Views --> Models
    ViewSets -.-> Swagger
    Models --> DB
    Views --> Razorpay
    Views --> ReportLab
    Views --> EmailService
    ViewSets --> Razorpay
```

---

## 📦 Key Functional Modules

### 1. 👥 Employee Management
* **Directory & Profiles:** Comprehensive digital profiles tracking personal information, contact email, phone, joining date, and departmental allocation.
* **Compensation Setup:** Supports both **Monthly Salary** and **Hourly Rate** pay schemes.
* **Role-Based Provisioning:** Granular linking between Django `User` accounts and `Employee` profiles with automatic administrative permission controls.

### 2. 📍 Attendance & Geofencing
* **Geofenced Check-In / Check-Out:** Validates employee GPS coordinates against configured office location radii using the Haversine distance formula.
* **Working Hours Tracking:** Automatically computes total working hours and break deductions on punch-out.
* **Attendance Classifications:** Flags attendance records as `Present`, `Late`, or `Absent`.

### 3. 🏖️ Leave Management Workflow
* **Self-Service Requests:** Employees apply for leaves under four formal categories: `Casual`, `Sick`, `Paid`, and `Unpaid`.
* **Managerial Review:** Full review dashboard for HR administrators with single-click approval and rejection workflows.
* **Automated Notifications:** Sends automated email dispatches upon status transitions.

### 4. 💳 Payroll & Payment Gateway API
* **Automated Computation:** Calculates gross salary, hourly deductions, bonuses, and net payouts for any given month/year.
* **Default Payment Gateway API:** Integrated with **Razorpay Gateway API** for order generation, payment processing, signature verification, and automated transaction audit trails (`payment_order_id`, `payment_id`, `paid_at`).
* **Simulation Mode:** Built-in development mode that safely simulates payments locally without requiring live third-party API credentials.
* **PDF Payslips:** Generates downloadable, printable salary slips via **ReportLab**.

### 5. 📊 Admin & Employee Dashboards
* **Admin Dashboard:** High-level executive KPIs, quick employee management shortcuts, database migration health monitors, and payroll summaries.
* **Employee Portal:** Personalized view of recent attendance history, remaining leave quotas, upcoming company holidays, and payslip downloads.

---

## 🛠️ Tech Stack Matrix

| Category | Technology | Purpose |
| :--- | :--- | :--- |
| **Core Framework** | Python 3.11+ / Django 6.1 | Backend engine, ORM, authentication, and core business logic |
| **API Architecture** | Django REST Framework (DRF) 3.15+ | Serializers, ViewSets, and RESTful CRUD endpoints |
| **API Documentation** | drf-spectacular 0.27+ | OpenAPI 3.0 schema generation with Swagger UI & ReDoc |
| **Database** | PostgreSQL / SQLite | Production relational database (Neon, Render, Railway) & local fallback |
| **Payment Gateway** | Razorpay Gateway API | Order initiation, checkout, and webhook verification |
| **Document Generation**| ReportLab | Automated PDF salary slip generation |
| **Static Assets** | WhiteNoise 6.12 | Efficient static file compression and caching |
| **Frontend Styling** | Bootstrap 5.3 & Bootstrap Icons | Modern, responsive mobile-friendly interface |
| **Continuous Integration** | GitHub Actions | Automated build validation, schema check, and test suite on PostgreSQL |
| **Deployment Platforms** | Vercel & Render | Serverless web execution & containerized production hosting |

---

## 🔌 RESTful API Reference

All REST endpoints are grouped under `/api/v1/` and protected with `SessionAuthentication` and `BasicAuthentication`.

| Endpoint | HTTP Methods | Description | Permissions |
| :--- | :--- | :--- | :--- |
| `/api/v1/employees/` | `GET`, `POST` | List all employees or create a new profile | Authenticated |
| `/api/v1/employees/{id}/` | `GET`, `PUT`, `PATCH`, `DELETE` | Retrieve, update, or remove an employee | Authenticated |
| `/api/v1/attendance/` | `GET`, `POST` | List attendance records or punch attendance | Authenticated |
| `/api/v1/attendance/{id}/` | `GET`, `PUT`, `PATCH`, `DELETE` | Retrieve or adjust attendance timestamps | Authenticated |
| `/api/v1/leave-requests/` | `GET`, `POST` | List all leave requests or submit a request | Authenticated |
| `/api/v1/leave-requests/{id}/` | `GET`, `PUT`, `PATCH`, `DELETE` | Retrieve, approve, reject, or edit a request | Authenticated |
| `/api/v1/payroll/` | `GET` | List payroll disbursement records | Authenticated (Read-only) |
| `/api/v1/payroll/{id}/` | `GET` | Retrieve detailed payroll calculations | Authenticated (Read-only) |
| `/api/schema/` | `GET` | Raw OpenAPI 3.0.3 schema specification | Public |
| `/api/docs/` | `GET` | Interactive Swagger UI API documentation | Public |
| `/api/redoc/` | `GET` | Interactive ReDoc API documentation | Public |

---

## 🚀 Local Development Setup

Follow these instructions to run WorkEase locally on your development machine.

### 1. Clone the Repository

```bash
git clone https://github.com/drij-ai/WorkEase.git
cd WorkEase
```

### 2. Create and Activate Virtual Environment

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory (or copy from `.env.example`):

```bash
cp .env.example .env
```

Key environment variables:
```ini
DJANGO_SECRET_KEY=your-secure-development-secret-key
DJANGO_DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration (Leave unset for local SQLite fallback)
# DATABASE_URL=postgresql://user:password@localhost:5432/workease

# Payment Gateway API Configuration
DEFAULT_GATEWAY_API=razorpay
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
PAYMENT_GATEWAY_CURRENCY=INR

# Email Configuration (Optional for notifications)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

> **Note:** When `RAZORPAY_KEY_ID` is left empty or set to mock values, WorkEase automatically activates **Simulation Mode**, enabling full order creation and payment workflows locally without external network dependencies.

### 5. Apply Database Migrations

```bash
python manage.py migrate
```

### 6. Create Superuser (Admin)

```bash
python manage.py createsuperuser
```

### 7. Run Development Server

```bash
python manage.py runserver
```

Open your browser at:
* **Web Portal:** `http://127.0.0.1:8000/`
* **Swagger API UI:** `http://127.0.0.1:8000/api/docs/`
* **ReDoc:** `http://127.0.0.1:8000/api/redoc/`
* **Admin Panel:** `http://127.0.0.1:8000/admin/`

---

## 🧪 Automated Testing & CI/CD Pipeline

WorkEase includes a comprehensive test suite covering authentication, geofencing logic, payroll calculation, payment gateway transactions, RESTful API endpoints, and OpenAPI schema generation.

### Run Tests Locally

Execute the test suite with:

```bash
python manage.py test
```

Validate the OpenAPI schema:

```bash
python manage.py spectacular --validate
```

Run Django system check:

```bash
python manage.py check
```

### Continuous Integration (GitHub Actions)

Every push and pull request to the `main` branch automatically triggers the [Django CI/CD Pipeline](.github/workflows/django.yml) which:
1. Spins up an **Ubuntu 22.04 LTS** runner with **Python 3.11**.
2. Launches a dedicated **PostgreSQL 15** service container with automated health checks.
3. Installs dependencies from `requirements.txt`.
4. Executes `python manage.py check` to verify configuration integrity.
5. Executes `python manage.py spectacular --validate` to verify OpenAPI schema accuracy.
6. Executes `python manage.py test` against the live PostgreSQL database.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

## 👨‍💻 Maintainer

Maintained with ❤️ by **[drij-ai](https://github.com/drij-ai)**.
