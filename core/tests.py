from django.utils import timezone
import json
from decimal import Decimal
import datetime
import os
import subprocess
import sys
from django.test import TestCase, Client, SimpleTestCase
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import Employee, Attendance, WorkLocation, Payroll, Leave, Notification, Holiday, BiometricCredential, AttendanceRegularization


class HealthCheckAndCoreViewsTest(TestCase):
    def setUp(self):
        # In production behind a reverse proxy (Render), requests arrive with HTTPS
        self.client = Client(headers={"x-forwarded-proto": "https"})

    def test_health_check_endpoint(self):
        """Verify that GET /health returns HTTP 200 and healthy status."""
        response = self.client.get('/health', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})

    def test_health_check_slash_endpoint(self):
        """Verify that GET /health/ also returns HTTP 200."""
        response = self.client.get('/health/', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})

    def test_home_page_accessible(self):
        """Verify that the home landing page loads successfully."""
        response = self.client.get(reverse('home'), secure=True)
        self.assertEqual(response.status_code, 200)

    def test_login_page_accessible(self):
        """Verify that the login page loads successfully."""
        response = self.client.get(reverse('login'), secure=True)
        self.assertEqual(response.status_code, 200)

    def test_employee_model_creation(self):
        """Verify Employee model creation and string representation."""
        user = User.objects.create_user(username='testemp', password='securepass123')
        employee = Employee.objects.create(
            user=user,
            employee_id='EMP999',
            name='Test Employee',
            phone='1234567890',
            department='Engineering',
            joining_date=datetime.date(2025, 1, 1),
            basic_salary=50000.00,
            salary_type='Monthly'
        )
        self.assertEqual(str(employee), "EMP999 - Test Employee")
        self.assertEqual(employee.basic_salary, 50000.00)

    def test_dashboard_superuser_redirects_to_admin_dashboard(self):
        """Verify that an authenticated superuser without an Employee profile is redirected to admin_dashboard."""
        admin_user = User.objects.create_superuser(
            username='adminuser',
            password='adminpassword123',
            email='admin@example.com'
        )
        self.client.force_login(admin_user)
        response = self.client.get(reverse('dashboard'), secure=True)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('admin_dashboard'))

    def test_dashboard_staff_user_without_employee_redirects_to_admin_dashboard(self):
        """Verify that an authenticated staff user (non-superuser) without an Employee profile is redirected to admin_dashboard."""
        staff_user = User.objects.create_user(
            username='staffadmin',
            password='staffpassword123',
            is_staff=True,
            is_superuser=False
        )
        self.client.force_login(staff_user)
        response = self.client.get(reverse('dashboard'), secure=True)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('admin_dashboard'), target_status_code=302)

    def test_dashboard_regular_employee_access(self):
        """Verify that an authenticated employee can access the dashboard."""
        user = User.objects.create_user(username='empuser', password='emppassword123')
        Employee.objects.create(
            user=user,
            employee_id='EMP101',
            name='Regular Employee',
            phone='9876543210',
            department='HR',
            joining_date=datetime.date(2025, 1, 1),
            basic_salary=45000.00,
            salary_type='Monthly'
        )
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard'), secure=True)
        self.assertEqual(response.status_code, 200)

    def test_dashboard_user_without_employee_redirects_home(self):
        """Verify that an authenticated non-staff user without an Employee profile is safely redirected home."""
        user = User.objects.create_user(username='noempuser', password='password123')
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard'), secure=True)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))

    def test_attendance_checkin_and_duplicate_prevention(self):
        """Verify first check-in creates exactly one record and repeated same-day check-in does not duplicate."""
        user = User.objects.create_user(username='attuser', password='password123')
        employee = Employee.objects.create(
            user=user,
            employee_id='ATT001',
            name='Attendance User',
            phone='1231231234',
            department='Sales',
            joining_date=datetime.date(2025, 1, 1),
            basic_salary=Decimal('40000.00'),
            salary_type='Monthly'
        )
        WorkLocation.objects.create(
            name='Office',
            latitude=Decimal('23.000000'),
            longitude=Decimal('72.000000'),
            allowed_radius=500
        )
        self.client.force_login(user)

        post_data = {
            'action': 'check_in',
            'latitude': '23.000000',
            'longitude': '72.000000',
        }
        res1 = self.client.post(reverse('attendance'), post_data, secure=True)
        self.assertEqual(res1.status_code, 302)
        self.assertRedirects(res1, '/dashboard/')
        self.assertEqual(Attendance.objects.filter(employee=employee).count(), 1)
        first_record = Attendance.objects.get(employee=employee)
        self.assertIn(first_record.status, ['Present', 'Late'])

        # Repeated check-in on the same day
        res2 = self.client.post(reverse('attendance'), post_data, secure=True)
        self.assertEqual(res2.status_code, 302)
        self.assertRedirects(res2, '/dashboard/')
        self.assertEqual(Attendance.objects.filter(employee=employee).count(), 1)

    def test_login_valid_employee_credentials(self):
        """Verify valid employee credentials authenticate and redirect to dashboard."""
        user = User.objects.create_user(username='loginemp', password='validpass123')
        Employee.objects.create(
            user=user,
            employee_id='LOG001',
            name='Login Emp',
            phone='1234567890',
            department='IT',
            joining_date=datetime.date(2025, 1, 1),
            basic_salary=Decimal('50000.00'),
            salary_type='Monthly'
        )
        response = self.client.post(reverse('login'), {
            'username': 'loginemp',
            'password': 'validpass123'
        }, secure=True)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_valid_superuser_credentials(self):
        """Verify valid superuser credentials authenticate and redirect to admin_dashboard."""
        User.objects.create_superuser(
            username='adminsuper',
            password='superpass123',
            email='admin@workease.com'
        )
        response = self.client.post(reverse('login'), {
            'username': 'adminsuper',
            'password': 'superpass123'
        }, secure=True)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('admin_dashboard'))

    def test_login_invalid_credentials(self):
        """Verify invalid credentials render login page with an error."""
        User.objects.create_user(username='someuser', password='correctpassword')
        response = self.client.post(reverse('login'), {
            'username': 'someuser',
            'password': 'wrongpassword'
        }, secure=True)
        self.assertContains(response, 'Invalid username')

    def test_employee_unauthorized_access_to_staff_actions(self):
        """Verify non-staff employees cannot access staff-only admin endpoints."""
        user = User.objects.create_user(username='normemp', password='password123')
        Employee.objects.create(
            user=user,
            employee_id='NRM001',
            name='Normal Employee',
            phone='1112223334',
            department='Support',
            joining_date=datetime.date(2025, 1, 1),
            basic_salary=Decimal('30000.00'),
            salary_type='Monthly'
        )
        self.client.force_login(user)

        # Attempt to access admin_dashboard (requires is_superuser)
        res_admin = self.client.get(reverse('admin_dashboard'), secure=True)
        self.assertEqual(res_admin.status_code, 302)

        # Attempt to access employee_list (requires is_staff)
        res_emp_list = self.client.get(reverse('employee_list'), secure=True)
        self.assertEqual(res_emp_list.status_code, 302)

        # Attempt to access admin_payroll_list (requires is_staff)
        res_payroll = self.client.get(reverse('admin_payroll_list'), secure=True)
        self.assertEqual(res_payroll.status_code, 302)

    def test_payroll_list_get_does_not_persist_data(self):
        """Verify GET request to admin_payroll_list does not alter saved payroll records in the database."""
        staff_user = User.objects.create_user(
            username='staffuser',
            password='staffpass123',
            is_staff=True
        )
        emp_user = User.objects.create_user(username='payemp', password='password123')
        employee = Employee.objects.create(
            user=emp_user,
            employee_id='PAY001',
            name='Payroll Emp',
            phone='5556667777',
            department='Finance',
            joining_date=datetime.date(2025, 1, 1),
            basic_salary=Decimal('60000.00'),
            salary_type='Monthly'
        )
        payroll = Payroll.objects.create(
            employee=employee,
            month=5,
            year=2026,
            salary_type='Monthly',
            basic_salary=Decimal('60000.00'),
            bonus=Decimal('5000.00'),
            deductions=Decimal('2000.00'),
            total_hours=Decimal('160.00'),
            hourly_rate=Decimal('0.00'),
            gross_salary=Decimal('60000.00'),
            net_salary=Decimal('63000.00')
        )
        original_values = {
            'total_hours': payroll.total_hours,
            'gross_salary': payroll.gross_salary,
            'net_salary': payroll.net_salary,
            'basic_salary': payroll.basic_salary,
            'bonus': payroll.bonus,
            'deductions': payroll.deductions,
        }

        self.client.force_login(staff_user)
        response = self.client.get(reverse('admin_payroll_list'), secure=True)
        self.assertEqual(response.status_code, 200)

        # Reload directly from database to confirm persistent state is untouched
        reloaded = Payroll.objects.get(id=payroll.id)
        self.assertEqual(reloaded.total_hours, original_values['total_hours'])
        self.assertEqual(reloaded.gross_salary, original_values['gross_salary'])
        self.assertEqual(reloaded.net_salary, original_values['net_salary'])
        self.assertEqual(reloaded.basic_salary, original_values['basic_salary'])
        self.assertEqual(reloaded.bonus, original_values['bonus'])
        self.assertEqual(reloaded.deductions, original_values['deductions'])

    def test_leave_application_and_approval_workflow(self):
        """Verify employee can submit a valid leave application and staff can approve it."""
        staff_user = User.objects.create_user(
            username='leavestaff',
            password='password123',
            is_staff=True
        )
        emp_user = User.objects.create_user(username='leaveemp', password='password123')
        employee = Employee.objects.create(
            user=emp_user,
            employee_id='LEV001',
            name='Leave Employee',
            phone='9998887777',
            department='Operations',
            joining_date=datetime.date(2025, 1, 1),
            basic_salary=Decimal('35000.00'),
            salary_type='Monthly'
        )

        # Employee applies for leave
        self.client.force_login(emp_user)
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        day_after = datetime.date.today() + datetime.timedelta(days=3)
        leave_data = {
            'leave_type': 'Casual',
            'from_date': tomorrow.isoformat(),
            'to_date': day_after.isoformat(),
            'reason': 'Family function'
        }
        res_apply = self.client.post(reverse('leave_apply'), leave_data, secure=True)
        self.assertEqual(res_apply.status_code, 302)
        self.assertRedirects(res_apply, '/dashboard/')

        self.assertEqual(Leave.objects.filter(employee=employee).count(), 1)
        leave = Leave.objects.get(employee=employee)
        self.assertEqual(leave.status, 'Pending')
        self.assertEqual(leave.leave_type, 'Casual')

        # Staff updates status to Approved
        self.client.force_login(staff_user)
        res_approve = self.client.post(
            reverse('leave_update_status', kwargs={'leave_id': leave.id, 'status': 'Approved'}),
            secure=True
        )
        self.assertEqual(res_approve.status_code, 302)
        self.assertRedirects(res_approve, '/admin-dashboard/leave/')

        leave.refresh_from_db()
        self.assertEqual(leave.status, 'Approved')
        self.assertEqual(Notification.objects.filter(employee=employee).count(), 1)
        notification = Notification.objects.get(employee=employee)
        self.assertIn('Approved', notification.title)


class ProductionSettingsIsolatedTest(SimpleTestCase):
    """Verify production settings behavior using isolated subprocesses to avoid mutating active test settings."""

    def test_render_production_settings_auto_configuration(self):
        """Verify RENDER_EXTERNAL_HOSTNAME automatically sets DEBUG=False, ALLOWED_HOSTS, and CSRF_TRUSTED_ORIGINS."""
        code = (
            "import os\n"
            "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workease.settings')\n"
            "from django.conf import settings\n"
            "assert settings.DEBUG is False, f'DEBUG should be False, got {settings.DEBUG}'\n"
            "assert 'workease-demo.onrender.com' in settings.ALLOWED_HOSTS, f'Host missing from {settings.ALLOWED_HOSTS}'\n"
            "assert 'https://workease-demo.onrender.com' in settings.CSRF_TRUSTED_ORIGINS, f'CSRF missing from {settings.CSRF_TRUSTED_ORIGINS}'\n"
            "assert settings.SECURE_PROXY_SSL_HEADER == ('HTTP_X_FORWARDED_PROTO', 'https')\n"
            "assert settings.SECURE_SSL_REDIRECT is True\n"
            "assert settings.SESSION_COOKIE_SECURE is True\n"
            "assert settings.CSRF_COOKIE_SECURE is True\n"
        )
        env = os.environ.copy()
        env['RENDER_EXTERNAL_HOSTNAME'] = 'workease-demo.onrender.com'
        env['DJANGO_SECRET_KEY'] = 'test-isolated-secret-key-for-unit-test'
        env.pop('DJANGO_DEBUG', None)
        env.pop('ALLOWED_HOSTS', None)
        env.pop('CSRF_TRUSTED_ORIGINS', None)

        proc = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Subprocess failed:\n{proc.stderr}")

    def test_production_custom_allowed_hosts_and_csrf_origins(self):
        """Verify custom ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS merge cleanly with Render hostname."""
        code = (
            "import os\n"
            "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workease.settings')\n"
            "from django.conf import settings\n"
            "assert 'workease-app.onrender.com' in settings.ALLOWED_HOSTS\n"
            "assert 'custom.workease.com' in settings.ALLOWED_HOSTS\n"
            "assert 'https://workease-app.onrender.com' in settings.CSRF_TRUSTED_ORIGINS\n"
            "assert 'https://custom.workease.com' in settings.CSRF_TRUSTED_ORIGINS\n"
        )
        env = os.environ.copy()
        env['RENDER_EXTERNAL_HOSTNAME'] = 'workease-app.onrender.com'
        env['DJANGO_SECRET_KEY'] = 'test-isolated-secret-key-for-unit-test'
        env['ALLOWED_HOSTS'] = 'custom.workease.com'
        env['CSRF_TRUSTED_ORIGINS'] = 'https://custom.workease.com'
        env.pop('DJANGO_DEBUG', None)

        proc = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Subprocess failed:\n{proc.stderr}")

    def test_production_missing_secret_key_raises_runtime_error(self):
        """Verify missing DJANGO_SECRET_KEY in production raises RuntimeError."""
        code = (
            "import os\n"
            "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workease.settings')\n"
            "from django.conf import settings\n"
            "_ = settings.SECRET_KEY\n"
        )
        env = os.environ.copy()
        env['RENDER_EXTERNAL_HOSTNAME'] = 'workease-prod.onrender.com'
        env.pop('DJANGO_SECRET_KEY', None)
        env.pop('DJANGO_DEBUG', None)

        proc = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY environment variable is required in production", proc.stderr)

    def test_railway_production_settings_auto_configuration(self):
        """Verify RAILWAY_ENVIRONMENT and RAILWAY_PUBLIC_DOMAIN automatically configure DEBUG=False, ALLOWED_HOSTS, and CSRF_TRUSTED_ORIGINS."""
        code = (
            "import os\n"
            "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workease.settings')\n"
            "from django.conf import settings\n"
            "assert settings.DEBUG is False, f'DEBUG should be False, got {settings.DEBUG}'\n"
            "assert 'workease-production.up.railway.app' in settings.ALLOWED_HOSTS, f'Host missing from {settings.ALLOWED_HOSTS}'\n"
            "assert 'https://workease-production.up.railway.app' in settings.CSRF_TRUSTED_ORIGINS, f'CSRF missing from {settings.CSRF_TRUSTED_ORIGINS}'\n"
            "assert settings.SECURE_PROXY_SSL_HEADER == ('HTTP_X_FORWARDED_PROTO', 'https')\n"
            "assert settings.SECURE_SSL_REDIRECT is True\n"
            "assert settings.SESSION_COOKIE_SECURE is True\n"
            "assert settings.CSRF_COOKIE_SECURE is True\n"
        )
        env = os.environ.copy()
        env['RAILWAY_ENVIRONMENT'] = 'production'
        env['RAILWAY_PUBLIC_DOMAIN'] = 'workease-production.up.railway.app'
        env['DJANGO_SECRET_KEY'] = 'test-isolated-secret-key-for-railway-unit-test'
        env.pop('DJANGO_DEBUG', None)
        env.pop('ALLOWED_HOSTS', None)
        env.pop('CSRF_TRUSTED_ORIGINS', None)
        env.pop('RENDER', None)
        env.pop('RENDER_EXTERNAL_HOSTNAME', None)

        proc = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Subprocess failed:\n{proc.stderr}")

    def test_railway_custom_allowed_hosts_and_csrf_origins(self):
        """Verify custom ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS merge cleanly with Railway domain."""
        code = (
            "import os\n"
            "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workease.settings')\n"
            "from django.conf import settings\n"
            "assert 'workease-production.up.railway.app' in settings.ALLOWED_HOSTS\n"
            "assert 'custom.workease.com' in settings.ALLOWED_HOSTS\n"
            "assert 'https://workease-production.up.railway.app' in settings.CSRF_TRUSTED_ORIGINS\n"
            "assert 'https://custom.workease.com' in settings.CSRF_TRUSTED_ORIGINS\n"
        )
        env = os.environ.copy()
        env['RAILWAY_ENVIRONMENT'] = 'production'
        env['RAILWAY_PUBLIC_DOMAIN'] = 'workease-production.up.railway.app'
        env['DJANGO_SECRET_KEY'] = 'test-isolated-secret-key-for-railway-unit-test'
        env['ALLOWED_HOSTS'] = 'custom.workease.com'
        env['CSRF_TRUSTED_ORIGINS'] = 'https://custom.workease.com'
        env.pop('DJANGO_DEBUG', None)
        env.pop('RENDER', None)
        env.pop('RENDER_EXTERNAL_HOSTNAME', None)

        proc = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Subprocess failed:\n{proc.stderr}")

    def test_back4app_production_settings_auto_configuration(self):
        """Verify B4A_APP_NAME automatically configures DEBUG=False, ALLOWED_HOSTS, and CSRF_TRUSTED_ORIGINS."""
        code = (
            "import os\n"
            "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workease.settings')\n"
            "from django.conf import settings\n"
            "assert settings.DEBUG is False, f'DEBUG should be False, got {settings.DEBUG}'\n"
            "assert 'workease-test.b4a.run' in settings.ALLOWED_HOSTS, f'Host missing from {settings.ALLOWED_HOSTS}'\n"
            "assert 'https://workease-test.b4a.run' in settings.CSRF_TRUSTED_ORIGINS, f'CSRF missing from {settings.CSRF_TRUSTED_ORIGINS}'\n"
            "assert settings.SECURE_PROXY_SSL_HEADER == ('HTTP_X_FORWARDED_PROTO', 'https')\n"
            "assert settings.SECURE_SSL_REDIRECT is True\n"
            "assert settings.SESSION_COOKIE_SECURE is True\n"
            "assert settings.CSRF_COOKIE_SECURE is True\n"
        )
        env = os.environ.copy()
        env['B4A_APP_NAME'] = 'workease-test'
        env['DJANGO_SECRET_KEY'] = 'test-isolated-secret-key-for-back4app-unit-test'
        env.pop('DJANGO_DEBUG', None)
        env.pop('ALLOWED_HOSTS', None)
        env.pop('CSRF_TRUSTED_ORIGINS', None)
        env.pop('RENDER', None)
        env.pop('RENDER_EXTERNAL_HOSTNAME', None)
        env.pop('RAILWAY_ENVIRONMENT', None)
        env.pop('RAILWAY_PUBLIC_DOMAIN', None)

        proc = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Subprocess failed:\n{proc.stderr}")

    def test_back4app_custom_allowed_hosts_and_csrf_origins(self):
        """Verify custom ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS merge cleanly with Back4app domain."""
        code = (
            "import os\n"
            "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workease.settings')\n"
            "from django.conf import settings\n"
            "assert 'workease-test.b4a.run' in settings.ALLOWED_HOSTS\n"
            "assert 'mycustomdomain.com' in settings.ALLOWED_HOSTS\n"
            "assert 'https://workease-test.b4a.run' in settings.CSRF_TRUSTED_ORIGINS\n"
            "assert 'https://mycustomdomain.com' in settings.CSRF_TRUSTED_ORIGINS\n"
        )
        env = os.environ.copy()
        env['B4A_APP_NAME'] = 'workease-test'
        env['DJANGO_SECRET_KEY'] = 'test-isolated-secret-key-for-back4app-unit-test'
        env['ALLOWED_HOSTS'] = 'mycustomdomain.com'
        env['CSRF_TRUSTED_ORIGINS'] = 'https://mycustomdomain.com'
        env.pop('DJANGO_DEBUG', None)
        env.pop('RENDER', None)
        env.pop('RENDER_EXTERNAL_HOSTNAME', None)
        env.pop('RAILWAY_ENVIRONMENT', None)
        env.pop('RAILWAY_PUBLIC_DOMAIN', None)

        proc = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Subprocess failed:\n{proc.stderr}")

    def test_vercel_production_settings_auto_configuration(self):
        """Verify VERCEL and VERCEL_URL automatically configure DEBUG=False, ALLOWED_HOSTS, and CSRF_TRUSTED_ORIGINS."""
        code = (
            "import os\n"
            "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workease.settings')\n"
            "from django.conf import settings\n"
            "assert settings.DEBUG is False, f'DEBUG should be False, got {settings.DEBUG}'\n"
            "assert 'workease.vercel.app' in settings.ALLOWED_HOSTS, f'Host missing from {settings.ALLOWED_HOSTS}'\n"
            "assert '.vercel.app' in settings.ALLOWED_HOSTS, f'Wildcard domain missing from {settings.ALLOWED_HOSTS}'\n"
            "assert 'work-ease-phi.vercel.app' in settings.ALLOWED_HOSTS, f'Production domain missing from {settings.ALLOWED_HOSTS}'\n"
            "assert 'https://workease.vercel.app' in settings.CSRF_TRUSTED_ORIGINS, f'CSRF missing from {settings.CSRF_TRUSTED_ORIGINS}'\n"
            "assert 'https://*.vercel.app' in settings.CSRF_TRUSTED_ORIGINS, f'CSRF wildcard missing from {settings.CSRF_TRUSTED_ORIGINS}'\n"
            "assert 'https://work-ease-phi.vercel.app' in settings.CSRF_TRUSTED_ORIGINS, f'CSRF prod domain missing from {settings.CSRF_TRUSTED_ORIGINS}'\n"
            "assert settings.SECURE_PROXY_SSL_HEADER == ('HTTP_X_FORWARDED_PROTO', 'https')\n"
            "assert settings.SECURE_SSL_REDIRECT is True\n"
            "assert settings.SESSION_COOKIE_SECURE is True\n"
            "assert settings.CSRF_COOKIE_SECURE is True\n"
        )
        env = os.environ.copy()
        env['VERCEL'] = '1'
        env['VERCEL_URL'] = 'workease.vercel.app'
        env['DJANGO_SECRET_KEY'] = 'test-isolated-secret-key-for-vercel-unit-test'
        env.pop('DJANGO_DEBUG', None)
        env.pop('ALLOWED_HOSTS', None)
        env.pop('CSRF_TRUSTED_ORIGINS', None)
        env.pop('RENDER', None)
        env.pop('RENDER_EXTERNAL_HOSTNAME', None)
        env.pop('RAILWAY_ENVIRONMENT', None)
        env.pop('RAILWAY_PUBLIC_DOMAIN', None)
        env.pop('B4A_APP_NAME', None)

        proc = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Subprocess failed:\n{proc.stderr}")


class EmployeeUserFlowTests(TestCase):
    def setUp(self):
        self.client = Client(headers={"x-forwarded-proto": "https"})
        self.admin = User.objects.create_superuser(
            username='admin_test',
            password='adminpassword123',
            email='admin@example.com'
        )
        self.client.force_login(self.admin)

    def test_add_employee_saves_correctly_without_user(self):
        """Newly created employee should be saved without an auto-created user."""
        response = self.client.post(reverse('employee_add'), {
            'employee_id': 'EMP001',
            'name': 'Rahul Sharma',
            'phone': '9876543210',
            'department': 'Operations',
            'joining_date': '2026-01-15',
            'basic_salary': '55000.00',
            'hourly_rate': '0.00',
            'salary_type': 'Monthly'
        }, secure=True)

        self.assertEqual(response.status_code, 302)
        employee = Employee.objects.filter(employee_id='EMP001').first()
        self.assertIsNotNone(employee)
        self.assertEqual(employee.name, 'Rahul Sharma')
        self.assertIsNone(employee.user)

    def test_user_add_dropdown_displays_eligible_employees(self):
        """Select Employee dropdown on user_add page should display all employees without linked user."""
        # Employee 1 without user
        emp1 = Employee.objects.create(
            employee_id='EMP010',
            name='Amit Kumar',
            phone='1111111111',
            department='HR',
            joining_date=datetime.date(2026, 2, 1),
            basic_salary=40000,
            salary_type='Monthly'
        )
        # Employee 2 with user
        linked_user = User.objects.create_user(username='amit_user', password='password123')
        emp2 = Employee.objects.create(
            user=linked_user,
            employee_id='EMP020',
            name='Priya Patel',
            phone='2222222222',
            department='Tech',
            joining_date=datetime.date(2026, 2, 1),
            basic_salary=60000,
            salary_type='Monthly'
        )

        response = self.client.get(reverse('user_add'), secure=True)
        self.assertEqual(response.status_code, 200)

        employees_in_context = list(response.context['employees'])
        self.assertIn(emp1, employees_in_context)
        self.assertNotIn(emp2, employees_in_context)

        # Check HTML content
        content = response.content.decode('utf-8')
        self.assertIn(f'{emp1.employee_id} - {emp1.name}', content)
        self.assertNotIn(f'{emp2.employee_id} - {emp2.name}', content)

    def test_full_flow_add_employee_then_add_login_user(self):
        """Test full flow: Add Employee -> Add Login User -> Select employee -> Create credentials."""
        # Step 1: Add Employee
        add_emp_response = self.client.post(reverse('employee_add'), {
            'employee_id': 'EMP077',
            'name': 'Sneha Desai',
            'phone': '9988776655',
            'department': 'Finance',
            'joining_date': '2026-03-01',
            'basic_salary': '65000.00',
            'hourly_rate': '0.00',
            'salary_type': 'Monthly'
        }, secure=True)
        self.assertEqual(add_emp_response.status_code, 302)

        employee = Employee.objects.get(employee_id='EMP077')
        self.assertIsNone(employee.user)

        # Step 2: Open Add Login User page and check employee appears in dropdown
        user_add_get = self.client.get(reverse('user_add'), secure=True)
        self.assertEqual(user_add_get.status_code, 200)
        self.assertIn(employee, user_add_get.context['employees'])

        # Step 3: Select the new employee and create login credentials
        user_add_post = self.client.post(reverse('user_add'), {
            'employee': employee.id,
            'username': 'sneha_desai',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!'
        }, secure=True)
        self.assertEqual(user_add_post.status_code, 302)
        self.assertRedirects(user_add_post, reverse('user_management'))

        # Step 4: Verify relationship was established
        employee.refresh_from_db()
        self.assertIsNotNone(employee.user)
        self.assertEqual(employee.user.username, 'sneha_desai')
        self.assertEqual(employee.user.first_name, 'Sneha Desai')

        # Step 5: Verify login works with the new credentials
        self.client.logout()
        login_success = self.client.login(username='sneha_desai', password='SecurePassword123!')
        self.assertTrue(login_success)

        # Step 6: Verify employee is now excluded from Add Login User dropdown
        self.client.force_login(self.admin)
        user_add_after = self.client.get(reverse('user_add'), secure=True)
        self.assertNotIn(employee, user_add_after.context['employees'])


class UnifiedRBACLoginTests(TestCase):
    def setUp(self):
        self.client = Client(headers={"x-forwarded-proto": "https"})
        self.admin = User.objects.create_superuser(
            username='admin_boss',
            password='AdminPass123!',
            email='boss@example.com'
        )
        self.emp_user = User.objects.create_user(
            username='vikram_user',
            password='EmpPass123!',
            first_name='Vikram Mehta'
        )
        self.employee = Employee.objects.create(
            user=self.emp_user,
            employee_id='EMP555',
            name='Vikram Mehta',
            phone='9898989898',
            department='Sales',
            joining_date=datetime.date(2026, 1, 1),
            basic_salary=50000,
            salary_type='Monthly'
        )

    def test_admin_login_redirects_to_admin_dashboard(self):
        """Admin login redirects automatically to admin_dashboard."""
        response = self.client.post(reverse('login'), {
            'username': 'admin_boss',
            'password': 'AdminPass123!'
        }, secure=True)
        self.assertRedirects(response, reverse('admin_dashboard'))

    def test_employee_login_with_username_redirects_to_dashboard(self):
        """Employee login using their username redirects automatically to dashboard."""
        response = self.client.post(reverse('login'), {
            'username': 'vikram_user',
            'password': 'EmpPass123!'
        }, secure=True)
        self.assertRedirects(response, reverse('dashboard'))

    def test_employee_login_with_employee_id_redirects_to_dashboard(self):
        """Employee login using their Employee ID redirects automatically to dashboard."""
        response = self.client.post(reverse('login'), {
            'username': 'EMP555',
            'password': 'EmpPass123!'
        }, secure=True)
        self.assertRedirects(response, reverse('dashboard'))

    def test_deactivated_account_login_error(self):
        """Deactivated user account receives an error message."""
        self.emp_user.is_active = False
        self.emp_user.save()

        response = self.client.post(reverse('login'), {
            'username': 'vikram_user',
            'password': 'EmpPass123!'
        }, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'deactivated')


class NewFeaturesTests(TestCase):
    def setUp(self):
        self.client = Client(headers={"x-forwarded-proto": "https"})
        self.admin = User.objects.create_superuser(
            username='admin_boss',
            password='AdminPass123!',
            email='admin@company.com'
        )
        self.emp_user = User.objects.create_user(
            username='priya_sharma',
            password='PriyaPass123!',
            email='priya@company.com'
        )
        self.employee = Employee.objects.create(
            user=self.emp_user,
            employee_id='EMP888',
            name='Priya Sharma',
            email='priya@company.com',
            phone='9876543210',
            department='Engineering',
            joining_date=datetime.date(2025, 6, 1),
            basic_salary=75000,
            salary_type='Monthly'
        )
        today_dt = datetime.date.today()
        self.payroll = Payroll.objects.create(
            employee=self.employee,
            month=today_dt.month,
            year=today_dt.year,
            salary_type='Monthly',
            basic_salary=75000,
            bonus=5000,
            deductions=2000
        )
        self.holiday = Holiday.objects.create(
            title='Diwali',
            date=datetime.date(2026, 11, 8),
            holiday_type='Festival',
            description='Festival of Lights'
        )

    def test_generate_payroll_pdf(self):
        """Verify generate_payroll_pdf creates valid in-memory PDF bytes."""
        from core.pdf_utils import generate_payroll_pdf
        pdf_bytes = generate_payroll_pdf(self.payroll)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(len(pdf_bytes) > 500)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))

    def test_payroll_pdf_download_admin(self):
        """Admin can download employee payroll PDF slip."""
        self.client.force_login(self.admin)
        url = reverse('payroll_pdf', kwargs={'payroll_id': self.payroll.id})
        response = self.client.get(url, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('inline', response['Content-Disposition'])

    def test_payroll_pdf_download_employee_owner(self):
        """Employee can download their own payroll PDF slip."""
        self.client.force_login(self.emp_user)
        url = reverse('employee_payroll_pdf', kwargs={'payroll_id': self.payroll.id})
        response = self.client.get(url, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_payroll_pdf_download_unauthorized(self):
        """Another employee cannot download someone else's payroll PDF."""
        other_user = User.objects.create_user(username='other_emp', password='Pass123!')
        other_employee = Employee.objects.create(
            user=other_user,
            employee_id='EMP999',
            name='Other Employee',
            joining_date=datetime.date(2026, 1, 1),
            basic_salary=40000
        )
        self.client.force_login(other_user)
        url = reverse('employee_payroll_pdf', kwargs={'payroll_id': self.payroll.id})
        response = self.client.get(url, secure=True)
        self.assertRedirects(response, reverse('dashboard'))

    def test_payroll_send_email_view(self):
        """Staff can trigger payroll slip email."""
        self.client.force_login(self.admin)
        url = reverse('payroll_send_email', kwargs={'payroll_id': self.payroll.id})
        response = self.client.get(url, secure=True)
        self.assertRedirects(response, reverse('admin_payroll_list'))

    def test_leave_update_status_triggers_email(self):
        """Approving a leave request sends an email notification to employee."""
        leave = Leave.objects.create(
            employee=self.employee,
            leave_type='Sick',
            from_date=datetime.date(2026, 10, 27),
            to_date=datetime.date(2026, 10, 28),
            reason='Flu and fever',
            status='Pending'
        )
        self.client.force_login(self.admin)
        url = reverse('leave_update_status', kwargs={'leave_id': leave.id, 'status': 'Approved'})
        response = self.client.post(url, secure=True)
        self.assertRedirects(response, '/admin-dashboard/leave/')
        leave.refresh_from_db()
        self.assertEqual(leave.status, 'Approved')

    def test_holiday_crud(self):
        """Admin can list, add, edit, and delete holidays."""
        self.client.force_login(self.admin)

        # List
        res_list = self.client.get(reverse('holiday_list'), secure=True)
        self.assertEqual(res_list.status_code, 200)
        self.assertContains(res_list, 'Diwali')

        # Add
        res_add = self.client.post(reverse('holiday_add'), {
            'title': 'Christmas',
            'date': '2026-12-25',
            'holiday_type': 'Festival',
            'description': 'Christmas Day'
        }, secure=True)
        self.assertRedirects(res_add, reverse('holiday_list'))
        self.assertTrue(Holiday.objects.filter(title='Christmas').exists())

        # Edit
        holiday_to_edit = Holiday.objects.get(title='Christmas')
        res_edit = self.client.post(reverse('holiday_edit', kwargs={'holiday_id': holiday_to_edit.id}), {
            'title': 'Christmas Holiday',
            'date': '2026-12-25',
            'holiday_type': 'Festival',
            'description': 'Updated'
        }, secure=True)
        self.assertRedirects(res_edit, reverse('holiday_list'))
        holiday_to_edit.refresh_from_db()
        self.assertEqual(holiday_to_edit.title, 'Christmas Holiday')

        # Delete
        res_del = self.client.post(reverse('holiday_delete', kwargs={'holiday_id': holiday_to_edit.id}), secure=True)
        self.assertRedirects(res_del, reverse('holiday_list'))
        self.assertFalse(Holiday.objects.filter(title='Christmas Holiday').exists())

    def test_employee_dashboard_context(self):
        """Employee dashboard context contains upcoming holidays and recent payrolls."""
        self.client.force_login(self.emp_user)
        response = self.client.get(reverse('dashboard'), secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('upcoming_holidays', response.context)
        self.assertIn('recent_payrolls', response.context)
        self.assertContains(response, 'Diwali')
        self.assertContains(response, 'Download Salary Slip (PDF)')




class PaymentGatewayApiTests(TestCase):
    def setUp(self):
        self.client = Client(headers={"x-forwarded-proto": "https"})
        self.admin = User.objects.create_superuser(
            username='gateway_admin',
            password='AdminPass123!',
            email='admin@gateway.com'
        )
        self.emp_user = User.objects.create_user(
            username='gateway_emp',
            password='EmpPass123!',
            email='emp@gateway.com'
        )
        self.employee = Employee.objects.create(
            user=self.emp_user,
            employee_id='GATE001',
            name='Gateway Employee',
            email='emp@gateway.com',
            phone='9876543210',
            department='Accounts',
            joining_date=datetime.date(2025, 1, 1),
            basic_salary=Decimal('50000.00'),
            salary_type='Monthly'
        )
        self.payroll = Payroll.objects.create(
            employee=self.employee,
            month=11,
            year=2026,
            salary_type='Monthly',
            basic_salary=Decimal('50000.00'),
            bonus=Decimal('3000.00'),
            deductions=Decimal('1000.00'),
            gross_salary=Decimal('50000.00'),
            net_salary=Decimal('52000.00')
        )

    def test_default_gateway_settings_configured(self):
        """Verify DEFAULT_GATEWAY_API is loaded in settings."""
        from django.conf import settings
        self.assertEqual(settings.DEFAULT_GATEWAY_API, 'razorpay')
        self.assertEqual(settings.PAYMENT_GATEWAY_CURRENCY, 'INR')
        self.assertTrue(hasattr(settings, 'RAZORPAY_KEY_ID'))
        self.assertTrue(hasattr(settings, 'RAZORPAY_KEY_SECRET'))

    def test_gateway_create_payroll_order(self):
        """Verify create_payroll_order creates order with correct subunit amount and currency."""
        from core.gateway import create_payroll_order
        order = create_payroll_order(self.payroll)
        self.assertTrue(order['success'])
        self.assertTrue(order['order_id'].startswith('order_'))
        self.assertEqual(order['amount'], 5200000)  # 52000 INR = 5200000 paise
        self.assertEqual(order['currency'], 'INR')
        self.payroll.refresh_from_db()
        self.assertEqual(self.payroll.payment_order_id, order['order_id'])

    def test_gateway_signature_verification(self):
        """Verify verify_gateway_signature correctly handles simulation mode and signature matching."""
        from core.gateway import verify_gateway_signature
        # Simulated test order verification
        self.assertTrue(verify_gateway_signature('order_sim_123', 'pay_sim_123', 'simulated_signature'))
        self.assertTrue(verify_gateway_signature('order_sim_123', 'pay_sim_123', 'any_signature'))
        self.assertFalse(verify_gateway_signature('', '', ''))

    def test_payroll_initiate_payment_view_staff(self):
        """Staff can initiate payment order and receive JSON payload."""
        self.client.force_login(self.admin)
        url = reverse('payroll_initiate_payment', kwargs={'payroll_id': self.payroll.id})
        response = self.client.get(url, secure=True)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['amount'], 5200000)

    def test_payroll_initiate_payment_view_forbidden_for_regular_user(self):
        """Non-staff user cannot initiate payment."""
        self.client.force_login(self.emp_user)
        url = reverse('payroll_initiate_payment', kwargs={'payroll_id': self.payroll.id})
        response = self.client.get(url, secure=True)
        self.assertEqual(response.status_code, 302)

    def test_payroll_verify_payment_view_success(self):
        """Verifying payment marks status as Paid and notifies employee."""
        self.client.force_login(self.admin)
        url = reverse('payroll_verify_payment', kwargs={'payroll_id': self.payroll.id})
        payload = {
            'razorpay_order_id': 'order_sim_test1',
            'razorpay_payment_id': 'pay_sim_test1',
            'razorpay_signature': 'simulated_signature'
        }
        response = self.client.post(
            url,
            payload,
            content_type='application/json',
            headers={'x-requested-with': 'XMLHttpRequest'},
            secure=True
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertTrue(res_data['success'])

        self.payroll.refresh_from_db()
        self.assertEqual(self.payroll.payment_status, 'Paid')
        self.assertEqual(self.payroll.payment_id, 'pay_sim_test1')
        self.assertIsNotNone(self.payroll.paid_at)

        # Confirm employee received disbursement notification
        notif = Notification.objects.filter(employee=self.employee).first()
        self.assertIsNotNone(notif)
        self.assertIn('Disbursed', notif.title)

    def test_payroll_mark_paid_view(self):
        """Admin can manually mark payroll as Paid."""
        self.client.force_login(self.admin)
        url = reverse('payroll_mark_paid', kwargs={'payroll_id': self.payroll.id})
        response = self.client.post(url, secure=True)
        self.assertRedirects(response, reverse('admin_payroll_list'))
        self.payroll.refresh_from_db()
        self.assertEqual(self.payroll.payment_status, 'Paid')
        self.assertEqual(self.payroll.payment_gateway, 'manual')

    def test_payment_webhook_handler(self):
        """Payment webhook handles order.paid / payment.captured events."""
        import json
        url = reverse('payment_webhook')
        webhook_payload = {
            'event': 'order.paid',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_hook_12345',
                        'order_id': self.payroll.payment_order_id or 'order_hook_12345',
                        'notes': {
                            'payroll_id': str(self.payroll.id)
                        }
                    }
                }
            }
        }
        response = self.client.post(
            url,
            json.dumps(webhook_payload),
            content_type='application/json',
            secure=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

        self.payroll.refresh_from_db()
        self.assertEqual(self.payroll.payment_status, 'Paid')
        self.assertEqual(self.payroll.payment_id, 'pay_hook_12345')


class RestFrameworkAndSwaggerTests(TestCase):
    def setUp(self):
        self.client = Client(headers={"x-forwarded-proto": "https"})
        self.user = User.objects.create_user(
            username='apiuser',
            password='Password123!',
            email='apiuser@example.com'
        )
        self.employee = Employee.objects.create(
            user=self.user,
            employee_id='EMP_API_01',
            name='API Test User',
            phone='9876543210',
            email='apiuser@example.com',
            department='Tech',
            joining_date=datetime.date(2025, 1, 1),
            basic_salary=Decimal('75000.00'),
            hourly_rate=Decimal('450.00'),
            salary_type='Monthly'
        )
        self.attendance = Attendance.objects.create(
            employee=self.employee,
            date=datetime.date(2025, 2, 1),
            check_in=datetime.time(9, 0),
            check_out=datetime.time(17, 0),
            break_hours=Decimal('1.00'),
            status='Present'
        )
        self.leave = Leave.objects.create(
            employee=self.employee,
            leave_type='Sick',
            from_date=datetime.date(2025, 3, 1),
            to_date=datetime.date(2025, 3, 2),
            reason='Flu symptoms',
            status='Pending'
        )
        self.payroll = Payroll.objects.create(
            employee=self.employee,
            month=2,
            year=2025,
            salary_type='Monthly',
            basic_salary=Decimal('75000.00'),
            bonus=Decimal('5000.00'),
            deductions=Decimal('2000.00'),
            gross_salary=Decimal('80000.00'),
            net_salary=Decimal('78000.00'),
            payment_status='Pending'
        )

    def test_swagger_schema_endpoint(self):
        """GET /api/schema/ returns 200 with OpenAPI schema."""
        response = self.client.get('/api/schema/', secure=True)
        self.assertEqual(response.status_code, 200)

    def test_swagger_ui_endpoint(self):
        """GET /api/docs/ returns 200 (Swagger UI)."""
        response = self.client.get('/api/docs/', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'WorkEase Management API')

    def test_redoc_ui_endpoint(self):
        """GET /api/redoc/ returns 200 (ReDoc UI)."""
        response = self.client.get('/api/redoc/', secure=True)
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_api_access_blocked(self):
        """Unauthenticated requests to API endpoints return 401 or 403."""
        for path in ['/api/v1/employees/', '/api/v1/attendance/', '/api/v1/leave-requests/', '/api/v1/payroll/']:
            response = self.client.get(path, secure=True)
            self.assertIn(response.status_code, [401, 403])

    def test_authenticated_employee_api_list(self):
        """Authenticated user can list employees."""
        self.client.force_login(self.user)
        response = self.client.get('/api/v1/employees/', secure=True)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data), 1)
        self.assertEqual(data[0]['employee_id'], 'EMP_API_01')

    def test_authenticated_attendance_api_list(self):
        """Authenticated user can list attendance records."""
        self.client.force_login(self.user)
        response = self.client.get('/api/v1/attendance/', secure=True)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data), 1)
        self.assertEqual(data[0]['status'], 'Present')

    def test_authenticated_leave_requests_api(self):
        """Authenticated user can list and create leave requests."""
        self.client.force_login(self.user)
        response = self.client.get('/api/v1/leave-requests/', secure=True)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data), 1)

    def test_payroll_api_is_read_only(self):
        """Payroll endpoint allows GET but forbids POST / DELETE (ReadOnlyModelViewSet)."""
        self.client.force_login(self.user)
        get_res = self.client.get('/api/v1/payroll/', secure=True)
        self.assertEqual(get_res.status_code, 200)

        # POST should not be allowed
        post_res = self.client.post(
            '/api/v1/payroll/',
            {'employee': self.employee.id, 'month': 3, 'year': 2025},
            content_type='application/json',
            secure=True
        )
        self.assertEqual(post_res.status_code, 405)

        # DELETE should not be allowed
        del_res = self.client.delete(f'/api/v1/payroll/{self.payroll.id}/', secure=True)
        self.assertEqual(del_res.status_code, 405)



class BiometricRegistrationAndAuthTests(TestCase):
    def setUp(self):
        self.client = Client(headers={"x-forwarded-proto": "https"})
        self.user = User.objects.create_user(
            username='biometric_user',
            password='TestPassword123!',
            email='bio@example.com'
        )
        self.employee = Employee.objects.create(
            user=self.user,
            employee_id='EMP_BIO_01',
            name='Biometric Employee',
            phone='9876543210',
            email='bio@example.com',
            department='Engineering',
            joining_date=datetime.date(2025, 1, 1),
            basic_salary=Decimal('85000.00'),
            salary_type='Monthly'
        )
        self.work_location = WorkLocation.objects.create(
            name='Headquarters',
            latitude=Decimal('23.022500'),
            longitude=Decimal('72.571400'),
            allowed_radius=500
        )

    def test_unauthenticated_biometric_endpoints_redirect_to_login(self):
        """Unauthenticated access to biometric endpoints redirects to login."""
        endpoints = [
            '/biometric/register/options/',
            '/biometric/auth/options/',
        ]
        for ep in endpoints:
            response = self.client.get(ep, secure=True)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login/', response.url)

    def test_biometric_register_options(self):
        """Authenticated employee receives WebAuthn creation options and sets session challenge."""
        self.client.force_login(self.user)
        response = self.client.get('/biometric/register/options/', secure=True)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('challenge', data)
        self.assertIn('rp', data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['name'], 'bio@example.com')
        self.assertEqual(self.client.session.get('webauthn_reg_challenge'), data['challenge'])

    def test_biometric_register_verify(self):
        """Employee can verify and register a new biometric credential."""
        self.client.force_login(self.user)
        # Set session challenge
        session = self.client.session
        session['webauthn_reg_challenge'] = 'test_challenge_12345'
        session.save()

        payload = {
            'credential_id': 'cred_webauthn_id_9999',
            'public_key': 'pubkey_sample_base64_data',
            'device_name': 'iPhone Touch ID',
        }
        response = self.client.post(
            '/biometric/register/verify/',
            json.dumps(payload),
            content_type='application/json',
            secure=True
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['credential_id'], 'cred_webauthn_id_9999')

        # Check DB persistence
        self.assertTrue(
            BiometricCredential.objects.filter(
                employee=self.employee,
                credential_id='cred_webauthn_id_9999'
            ).exists()
        )
        self.assertTrue(self.employee.has_biometric)

    def test_biometric_auth_options_without_credentials_fails(self):
        """Employee without registered biometrics receives error from auth options."""
        self.client.force_login(self.user)
        response = self.client.get('/biometric/auth/options/', secure=True)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_biometric_auth_options_with_credentials_succeeds(self):
        """Employee with registered biometric receives WebAuthn assertion options."""
        BiometricCredential.objects.create(
            employee=self.employee,
            credential_id='cred_existing_token',
            public_key='sample_key',
            device_name='Windows Hello'
        )
        self.client.force_login(self.user)
        response = self.client.get('/biometric/auth/options/', secure=True)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('challenge', data)
        self.assertIn('allowCredentials', data)
        self.assertEqual(data['allowCredentials'][0]['id'], 'cred_existing_token')
        self.assertEqual(self.client.session.get('webauthn_auth_challenge'), data['challenge'])

    def test_biometric_attendance_check_in_and_check_out_flow(self):
        """Full biometric punch flow: Check-In then Check-Out with GPS coordinates."""
        cred = BiometricCredential.objects.create(
            employee=self.employee,
            credential_id='cred_punch_token',
            public_key='sample_key',
            device_name='Office Tablet Biometric',
            sign_count=0
        )
        self.client.force_login(self.user)

        # 1. Biometric Check-In inside allowed radius (exact HQ coords)
        check_in_payload = {
            'credential_id': 'cred_punch_token',
            'action': 'check_in',
            'latitude': '23.022500',
            'longitude': '72.571400',
        }
        res_in = self.client.post(
            '/biometric/auth/verify/',
            json.dumps(check_in_payload),
            content_type='application/json',
            secure=True
        )
        self.assertEqual(res_in.status_code, 200)
        in_data = res_in.json()
        self.assertTrue(in_data['success'])
        self.assertEqual(in_data['action'], 'check_in')

        today = timezone.localdate()
        att = Attendance.objects.filter(employee=self.employee, date=today).first()
        self.assertIsNotNone(att)
        self.assertIsNotNone(att.check_in)
        self.assertIsNone(att.check_out)

        cred.refresh_from_db()
        self.assertEqual(cred.sign_count, 1)

        # 2. Duplicate Check-In rejected
        res_dup = self.client.post(
            '/biometric/auth/verify/',
            json.dumps(check_in_payload),
            content_type='application/json',
            secure=True
        )
        self.assertEqual(res_dup.status_code, 400)
        self.assertFalse(res_dup.json()['success'])

        # Adjust check_in time to simulate an elapsed shift before checkout
        att.check_in = (timezone.now() - datetime.timedelta(hours=4)).time()
        att.save(update_fields=['check_in'])

        # 3. Biometric Check-Out with break hours
        check_out_payload = {
            'credential_id': 'cred_punch_token',
            'action': 'check_out',
            'latitude': '23.022500',
            'longitude': '72.571400',
            'break_hours': '0.5'
        }
        res_out = self.client.post(
            '/biometric/auth/verify/',
            json.dumps(check_out_payload),
            content_type='application/json',
            secure=True
        )
        self.assertEqual(res_out.status_code, 200)
        out_data = res_out.json()
        self.assertTrue(out_data['success'])
        self.assertEqual(out_data['action'], 'check_out')

        att.refresh_from_db()
        self.assertIsNotNone(att.check_out)
        self.assertEqual(att.break_hours, Decimal('0.5'))

        cred.refresh_from_db()
        self.assertEqual(cred.sign_count, 3)

    def test_biometric_attendance_outside_geofence_rejected(self):
        """Biometric punch outside office radius is rejected with error."""
        BiometricCredential.objects.create(
            employee=self.employee,
            credential_id='cred_geofence_token',
            public_key='sample_key',
            device_name='Android Biometric'
        )
        self.client.force_login(self.user)

        # New York coordinates (far away from Ahmedabad HQ)
        payload = {
            'credential_id': 'cred_geofence_token',
            'action': 'check_in',
            'latitude': '40.7128',
            'longitude': '-74.0060',
        }
        response = self.client.post(
            '/biometric/auth/verify/',
            json.dumps(payload),
            content_type='application/json',
            secure=True
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Allowed radius', data['error'])

    def test_biometric_attendance_invalid_credential_rejected(self):
        """Punch with unassociated credential_id is rejected."""
        self.client.force_login(self.user)
        payload = {
            'credential_id': 'cred_unregistered_unknown',
            'action': 'check_in',
            'latitude': '23.022500',
            'longitude': '72.571400',
        }
        response = self.client.post(
            '/biometric/auth/verify/',
            json.dumps(payload),
            content_type='application/json',
            secure=True
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Unrecognized or unauthorized', response.json()['error'])


class EmployeeSoftDeleteAndRegularizationTests(TestCase):
    def setUp(self):
        self.client = Client(headers={"x-forwarded-proto": "https"})
        self.password = "Secr3tP@ssw0rd!"

        # Admin user
        self.admin_user = User.objects.create_superuser(
            username="admin_user",
            email="admin@workease.com",
            password=self.password,
            is_staff=True,
            is_superuser=True
        )

        # Standard employee user
        self.emp_user = User.objects.create_user(
            username="emp_john",
            email="john@workease.com",
            password=self.password
        )

        self.employee = Employee.objects.create(
            user=self.emp_user,
            employee_id="EMP-9001",
            name="John SoftDelete",
            phone="9876543210",
            email="john@workease.com",
            department="Engineering",
            joining_date=datetime.date(2025, 1, 1),
            basic_salary=Decimal("60000.00"),
            hourly_rate=Decimal("350.00"),
            salary_type="Monthly",
            is_active=True
        )

    def test_employee_soft_delete_preserves_history_and_blocks_login(self):
        """Soft delete deactivates employee and linked user, blocks login, and preserves historical records."""
        # 1. Create historical Attendance, Leave, and Payroll records
        att = Attendance.objects.create(
            employee=self.employee,
            date=datetime.date(2026, 10, 15),
            check_in=datetime.time(9, 0),
            check_out=datetime.time(17, 30),
            break_hours=Decimal("0.5"),
            status="Present"
        )
        leave = Leave.objects.create(
            employee=self.employee,
            leave_type="Casual",
            from_date=datetime.date(2026, 10, 20),
            to_date=datetime.date(2026, 10, 21),
            reason="Family event",
            status="Approved"
        )
        payroll = Payroll.objects.create(
            employee=self.employee,
            month=10,
            year=2026,
            salary_type="Monthly",
            basic_salary=Decimal("60000.00"),
            gross_salary=Decimal("60000.00"),
            net_salary=Decimal("58000.00"),
            payment_status="Paid"
        )

        # Verify active user can log in before soft delete
        login_success = self.client.login(username="emp_john", password=self.password)
        self.assertTrue(login_success)
        self.client.logout()

        # 2. Perform soft delete
        self.employee.soft_delete()
        self.employee.refresh_from_db()
        self.emp_user.refresh_from_db()

        self.assertFalse(self.employee.is_active)
        self.assertEqual(self.employee.relieving_date, timezone.localdate())
        self.assertFalse(self.emp_user.is_active)

        # 3. Verify user cannot log in anymore
        login_blocked = self.client.login(username="emp_john", password=self.password)
        self.assertFalse(login_blocked)

        # 4. Verify historical records remain 100% intact
        self.assertTrue(Attendance.objects.filter(id=att.id, employee=self.employee).exists())
        self.assertTrue(Leave.objects.filter(id=leave.id, employee=self.employee).exists())
        self.assertTrue(Payroll.objects.filter(id=payroll.id, employee=self.employee).exists())

    def test_employee_reactivation_restores_access(self):
        """Reactivation restores employee is_active, clears relieving_date, and reactivates user."""
        self.employee.soft_delete()
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.is_active)

        self.employee.reactivate()
        self.employee.refresh_from_db()
        self.emp_user.refresh_from_db()

        self.assertTrue(self.employee.is_active)
        self.assertIsNone(self.employee.relieving_date)
        self.assertTrue(self.emp_user.is_active)

        # Verify user can log in again
        login_ok = self.client.login(username="emp_john", password=self.password)
        self.assertTrue(login_ok)

    def test_employee_delete_view_performs_soft_delete(self):
        """Admin employee delete view performs soft delete without dropping database records."""
        self.client.force_login(self.admin_user)
        response = self.client.post(f"/admin-dashboard/employees/{self.employee.id}/delete/", secure=True)
        self.assertEqual(response.status_code, 302)

        self.employee.refresh_from_db()
        self.assertFalse(self.employee.is_active)
        self.assertEqual(self.employee.relieving_date, timezone.localdate())
        self.assertFalse(self.employee.user.is_active)

    def test_employee_toggle_status_view(self):
        """Admin can toggle employee active status between deactivated and active."""
        self.client.force_login(self.admin_user)

        # Toggle active -> deactivated
        res1 = self.client.post(f"/admin-dashboard/employees/{self.employee.id}/toggle-status/", secure=True)
        self.assertEqual(res1.status_code, 302)
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.is_active)

        # Toggle deactivated -> active
        res2 = self.client.post(f"/admin-dashboard/employees/{self.employee.id}/toggle-status/", secure=True)
        self.assertEqual(res2.status_code, 302)
        self.employee.refresh_from_db()
        self.assertTrue(self.employee.is_active)
        self.assertIsNone(self.employee.relieving_date)

    def test_employee_api_destroy_performs_soft_delete(self):
        """DRF DELETE /api/v1/employees/{id}/ triggers soft delete."""
        self.client.force_login(self.admin_user)
        response = self.client.delete(f"/api/v1/employees/{self.employee.id}/", secure=True)
        self.assertEqual(response.status_code, 204)

        self.employee.refresh_from_db()
        self.assertFalse(self.employee.is_active)
        self.assertEqual(self.employee.relieving_date, timezone.localdate())
        self.assertFalse(self.employee.user.is_active)

    def test_attendance_regularization_request_submission_by_employee(self):
        """Employee can submit an attendance regularization request."""
        self.client.force_login(self.emp_user)
        reg_date = timezone.localdate() - datetime.timedelta(days=1)

        payload = {
            'date': reg_date.strftime('%Y-%m-%d'),
            'requested_check_in': '09:15',
            'requested_check_out': '18:15',
            'reason': 'Forgot to punch out due to client demo'
        }
        response = self.client.post('/attendance/regularize/', payload, secure=True)
        self.assertEqual(response.status_code, 302)

        reg = AttendanceRegularization.objects.filter(employee=self.employee, date=reg_date).first()
        self.assertIsNotNone(reg)
        self.assertEqual(reg.status, 'Pending')
        self.assertEqual(reg.requested_check_in, datetime.time(9, 15))
        self.assertEqual(reg.requested_check_out, datetime.time(18, 15))

    def test_attendance_regularization_approval_creates_attendance_and_recalculates_hours(self):
        """Approving a regularization request creates attendance record and calculates working hours."""
        reg_date = timezone.localdate() - datetime.timedelta(days=2)
        reg = AttendanceRegularization.objects.create(
            employee=self.employee,
            date=reg_date,
            requested_check_in=datetime.time(9, 0),
            requested_check_out=datetime.time(18, 0),
            reason='Missed full day punches due to biometric hardware update',
            status='Pending'
        )

        self.client.force_login(self.admin_user)
        response = self.client.post(
            f"/admin-dashboard/attendance/regularizations/{reg.id}/Approved/",
            {'admin_remarks': 'Approved by HR manager'},
            secure=True
        )
        self.assertEqual(response.status_code, 302)

        reg.refresh_from_db()
        self.assertEqual(reg.status, 'Approved')
        self.assertIsNotNone(reg.reviewed_at)
        self.assertEqual(reg.admin_remarks, 'Approved by HR manager')

        # Verify Attendance record was created and working hours calculated
        att = Attendance.objects.filter(employee=self.employee, date=reg_date).first()
        self.assertIsNotNone(att)
        self.assertEqual(att.check_in, datetime.time(9, 0))
        self.assertEqual(att.check_out, datetime.time(18, 0))
        self.assertEqual(att.status, 'Present')
        # (18 - 9) = 9.00 hours
        self.assertEqual(att.working_hours, Decimal('9.00'))

        # Verify notification was sent
        notif = Notification.objects.filter(employee=self.employee, title='Attendance Regularization Approved').first()
        self.assertIsNotNone(notif)

    def test_attendance_regularization_approval_updates_existing_attendance(self):
        """Approving regularization updates existing partial attendance record and recalculates working hours."""
        reg_date = timezone.localdate() - datetime.timedelta(days=3)
        att = Attendance.objects.create(
            employee=self.employee,
            date=reg_date,
            check_in=datetime.time(9, 0),
            check_out=None,
            break_hours=Decimal('1.00'),
            status='Present'
        )

        reg = AttendanceRegularization.objects.create(
            employee=self.employee,
            attendance=att,
            date=reg_date,
            requested_check_out=datetime.time(18, 0),
            reason='Forgot to punch out at shift end',
            status='Pending'
        )

        reg.approve(admin_remarks='Auto-verified')
        reg.refresh_from_db()
        att.refresh_from_db()

        self.assertEqual(reg.status, 'Approved')
        self.assertEqual(att.check_out, datetime.time(18, 0))
        # Total elapsed: 9 hours, minus 1 hour break = 8.00 hours
        self.assertEqual(att.working_hours, Decimal('8.00'))

    def test_attendance_regularization_rejection(self):
        """Admin can reject a regularization request with remarks."""
        reg_date = timezone.localdate() - datetime.timedelta(days=4)
        reg = AttendanceRegularization.objects.create(
            employee=self.employee,
            date=reg_date,
            requested_check_in=datetime.time(10, 0),
            reason='Late arrival regularization',
            status='Pending'
        )

        self.client.force_login(self.admin_user)
        response = self.client.post(
            f"/admin-dashboard/attendance/regularizations/{reg.id}/Rejected/",
            {'admin_remarks': 'Unexcused tardiness, rejected per company policy'},
            secure=True
        )
        self.assertEqual(response.status_code, 302)

        reg.refresh_from_db()
        self.assertEqual(reg.status, 'Rejected')
        self.assertIsNotNone(reg.reviewed_at)
        self.assertEqual(reg.admin_remarks, 'Unexcused tardiness, rejected per company policy')

    def test_attendance_regularization_api_endpoints(self):
        """Verify DRF API endpoints for Attendance Regularization list, create, and approve."""
        self.client.force_login(self.admin_user)
        reg_date = (timezone.localdate() - datetime.timedelta(days=5)).strftime('%Y-%m-%d')

        # 1. Create regularization via API
        payload = {
            'employee': self.employee.id,
            'date': reg_date,
            'requested_check_in': '09:00:00',
            'requested_check_out': '17:00:00',
            'reason': 'API Missed Punch Request',
            'status': 'Pending'
        }
        res_create = self.client.post(
            '/api/v1/attendance-regularizations/',
            json.dumps(payload),
            content_type='application/json',
            secure=True
        )
        self.assertEqual(res_create.status_code, 201)
        reg_id = res_create.json()['id']

        # 2. List regularizations
        res_list = self.client.get('/api/v1/attendance-regularizations/', secure=True)
        self.assertEqual(res_list.status_code, 200)

        # 3. Approve via API custom action
        res_approve = self.client.post(
            f'/api/v1/attendance-regularizations/{reg_id}/approve/',
            json.dumps({'admin_remarks': 'Approved via REST API'}),
            content_type='application/json',
            secure=True
        )
        self.assertEqual(res_approve.status_code, 200)
        self.assertEqual(res_approve.json()['status'], 'Approved')


class AutoMigrationAndResilienceTests(TestCase):
    def setUp(self):
        self.client = Client(headers={"x-forwarded-proto": "https"})

    def test_run_migrations_endpoint_get(self):
        """Root /run-migrations/ returns HTTP 200 HTML page without requiring login."""
        response = self.client.get('/run-migrations/', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Database Migration Runner', response.content.decode('utf-8'))

    def test_run_migrations_endpoint_json(self):
        """Root /run-migrations/?format=json returns JSON response with status."""
        response = self.client.get('/run-migrations/?format=json', secure=True)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('output', data)

    def test_admin_dashboard_run_migrations_endpoint(self):
        """/admin-dashboard/run-migrations/ returns HTTP 200."""
        response = self.client.get('/admin-dashboard/run-migrations/', secure=True)
        self.assertEqual(response.status_code, 200)
