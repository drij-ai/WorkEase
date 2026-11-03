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

    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether this employee record is active."
    )

    relieving_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when the employee was relieved or deactivated."
    )

    @property
    def contact_email(self):
        if self.email:
            return self.email
        if self.user and self.user.email:
            return self.user.email
        return None

    @property
    def has_biometric(self):
        return self.biometric_credentials.exists()

    @property
    def primary_biometric(self):
        return self.biometric_credentials.first()

    def soft_delete(self):
        from django.utils import timezone
        self.is_active = False
        self.relieving_date = timezone.localdate()
        self.save(update_fields=['is_active', 'relieving_date'])
        if self.user:
            self.user.is_active = False
            self.user.save(update_fields=['is_active'])

    def reactivate(self):
        self.is_active = True
        self.relieving_date = None
        self.save(update_fields=['is_active', 'relieving_date'])
        if self.user:
            self.user.is_active = True
            self.user.save(update_fields=['is_active'])

    def delete(self, using=None, keep_parents=False):
        self.soft_delete()

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

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
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
    ]

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

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='Pending'
    )

    payment_gateway = models.CharField(
        max_length=50,
        default='razorpay',
        blank=True
    )

    payment_order_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    payment_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    paid_at = models.DateTimeField(
        blank=True,
        null=True
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


class BiometricCredential(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='biometric_credentials'
    )
    credential_id = models.CharField(
        max_length=512,
        unique=True,
        help_text="Base64 or string WebAuthn Credential ID"
    )
    public_key = models.TextField(
        help_text="Public key representation or COSE key in base64"
    )
    sign_count = models.IntegerField(
        default=0
    )
    device_name = models.CharField(
        max_length=150,
        blank=True,
        default='Biometric Device'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee.name} - {self.device_name} ({self.credential_id[:16]}...)"


class AttendanceRegularization(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='regularization_requests'
    )
    attendance = models.ForeignKey(
        Attendance,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='regularizations'
    )
    date = models.DateField()
    requested_check_in = models.TimeField(
        null=True,
        blank=True,
        help_text="Requested check-in time for missed punch"
    )
    requested_check_out = models.TimeField(
        null=True,
        blank=True,
        help_text="Requested check-out time for missed punch"
    )
    reason = models.TextField(
        help_text="Reason for attendance regularization"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )
    admin_remarks = models.TextField(
        blank=True,
        default=''
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee.name} - Regularization ({self.date}) [{self.status}]"

    def approve(self, admin_remarks=''):
        from django.utils import timezone
        self.status = 'Approved'
        if admin_remarks:
            self.admin_remarks = admin_remarks
        self.reviewed_at = timezone.now()

        # Create or update Attendance record for self.employee and self.date
        attendance, _ = Attendance.objects.get_or_create(
            employee=self.employee,
            date=self.date,
            defaults={
                'status': 'Present',
                'break_hours': 0,
            }
        )
        if self.requested_check_in:
            attendance.check_in = self.requested_check_in
        if self.requested_check_out:
            attendance.check_out = self.requested_check_out
        attendance.status = 'Present'
        attendance.save()

        self.attendance = attendance
        self.save()
        return attendance

    def reject(self, admin_remarks=''):
        from django.utils import timezone
        self.status = 'Rejected'
        if admin_remarks:
            self.admin_remarks = admin_remarks
        self.reviewed_at = timezone.now()
        self.save()

    def save(self, *args, **kwargs):
        from django.utils import timezone
        if self.status == 'Approved':
            if not self.reviewed_at:
                self.reviewed_at = timezone.now()
            # If attendance is not updated yet or status changed directly
            attendance, _ = Attendance.objects.get_or_create(
                employee=self.employee,
                date=self.date,
                defaults={
                    'status': 'Present',
                    'break_hours': 0,
                }
            )
            if self.requested_check_in:
                attendance.check_in = self.requested_check_in
            if self.requested_check_out:
                attendance.check_out = self.requested_check_out
            attendance.status = 'Present'
            attendance.save()
            self.attendance = attendance
        elif self.status == 'Rejected':
            if not self.reviewed_at:
                self.reviewed_at = timezone.now()

        super().save(*args, **kwargs)


