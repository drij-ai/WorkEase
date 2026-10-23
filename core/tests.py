from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import Employee
import datetime


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
