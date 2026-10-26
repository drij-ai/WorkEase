from django.db import models
from django.contrib.auth.models import User


class Employee(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    employee_id = models.CharField(
        max_length=20,
        unique=True
    )

    name = models.CharField(
        max_length=100
    )

    phone = models.CharField(
        max_length=15
    )

    email = models.EmailField(
        max_length=150,
        blank=True,
        null=True
    )

    department = models.CharField(
        max_length=100
    )

    joining_date = models.DateField()

    basic_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    salary_type = models.CharField(
        max_length=20,
        choices=[
            ('Monthly', 'Monthly'),
            ('Hourly', 'Hourly'),
        ],
        default='Monthly'
    )

    @property
    def contact_email(self):
        if self.email:
            return self.email
        if self.user and self.user.email:
            return self.user.email
        return None

    def __str__(self):
        return f"{self.employee_id} - {self.name}"


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
        ('Late', 'Late'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )

    date = models.DateField()

    check_in = models.TimeField(
        null=True,
        blank=True
    )

    check_out = models.TimeField(
        null=True,
        blank=True
    )

    working_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    break_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Present'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def save(self, *args, **kwargs):
        if self.check_in and self.check_out:
            from datetime import datetime

            start = datetime.combine(
                self.date,
                self.check_in
            )

            end = datetime.combine(
                self.date,
                self.check_out
            )

            difference = (
                end - start
            ).total_seconds() / 3600

            self.working_hours = round(
                max(
                    0,
                    difference - float(self.break_hours)
                ),
                2
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.employee.name} - "
            f"{self.date} - {self.status}"
        )


class Payroll(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='payroll_records'
    )

    month = models.PositiveIntegerField()

    year = models.PositiveIntegerField()

    salary_type = models.CharField(
        max_length=20,
        choices=[
            ('Monthly', 'Monthly'),
            ('Hourly', 'Hourly'),
        ],
        default='Monthly'
    )

    total_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    basic_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    bonus = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    deductions = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    gross_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    net_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    generated_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        unique_together = (
            'employee',
            'month',
            'year'
        )

    def save(self, *args, **kwargs):
        if self.salary_type == 'Hourly':
            self.gross_salary = (
                self.total_hours * self.hourly_rate
            )
        else:
            self.gross_salary = self.basic_salary

        self.net_salary = (
            self.gross_salary
            + self.bonus
            - self.deductions
        )

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.employee.name} - "
            f"{self.month}/{self.year}"
        )


class Leave(models.Model):
    LEAVE_TYPE_CHOICES = [
        ('Casual', 'Casual'),
        ('Sick', 'Sick'),
        ('Paid', 'Paid'),
        ('Unpaid', 'Unpaid'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='leave_requests'
    )

    leave_type = models.CharField(
        max_length=20,
        choices=LEAVE_TYPE_CHOICES
    )

    from_date = models.DateField()

    to_date = models.DateField()

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.employee.name} - "
            f"{self.leave_type} - {self.status}"
        )


class WorkLocation(models.Model):
    name = models.CharField(
        max_length=100
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6
    )

    allowed_radius = models.PositiveIntegerField(
        default=100
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name


class Notification(models.Model):
    employee = models.ForeignKey(
        'Employee',
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee.name} - {self.title}"


class Holiday(models.Model):
    HOLIDAY_TYPES = [
        ('Festival', 'Festival'),
        ('National', 'National Holiday'),
        ('Company', 'Company Off'),
        ('Optional', 'Optional Holiday'),
    ]

    title = models.CharField(
        max_length=150
    )

    date = models.DateField()

    holiday_type = models.CharField(
        max_length=30,
        choices=HOLIDAY_TYPES,
        default='Festival'
    )

    description = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"{self.date} - {self.title}"
