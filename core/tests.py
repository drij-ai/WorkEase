from decimal import Decimal
import datetime
import os
import subprocess
import sys
from django.test import TestCase, Client, SimpleTestCase
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import Employee, Attendance, WorkLocation, Payroll, Leave, Notification


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
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Username athva password wrong chhe.')

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
            "assert 'https://workease.vercel.app' in settings.CSRF_TRUSTED_ORIGINS, f'CSRF missing from {settings.CSRF_TRUSTED_ORIGINS}'\n"
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
