import json
import secrets
import base64
from django.shortcuts import render, redirect
from django.db import DatabaseError, OperationalError, ProgrammingError
from django.core.management import call_command
from django.contrib.auth import authenticate, login, logout
from django.db.models import Sum
from django.utils import timezone

from django.contrib.auth.models import User
from django.contrib.auth import login
from django.utils.crypto import get_random_string
from django.contrib import messages

import calendar

from datetime import time

from django.shortcuts import get_object_or_404


from django.http import HttpResponse, Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .forms import EmployeeForm, WorkLocationForm, PayrollForm, HolidayForm

from .models import Attendance, Leave, WorkLocation, Employee, Payroll, Holiday, BiometricCredential, AttendanceRegularization
from django.contrib.admin.views.decorators import staff_member_required

def safe_run_migrations():
    """Attempt to apply pending migrations if schema error is detected."""
    try:
        call_command('migrate', interactive=False)
        return True
    except Exception:
        return False

from math import radians, sin, cos, sqrt, atan2


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db import DatabaseError, OperationalError, ProgrammingError
from django.core.management import call_command

from .models import Notification
from django.views.decorators.http import require_POST


from .models import Attendance, Payroll, Employee
from django.shortcuts import render
from django.db.models import Sum
from decimal import Decimal

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import user_passes_test

def calculate_distance(lat1, lon1, lat2, lon2):
    earth_radius = 6371000

    lat1 = radians(float(lat1))
    lon1 = radians(float(lon1))
    lat2 = radians(float(lat2))
    lon2 = radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return earth_radius * c


def owner_required(view_func):
    return user_passes_test(
        lambda user: user.is_authenticated
        and user.is_active
        and user.is_superuser,
        login_url='login'
    )(view_func)


def home(request):
    return render(request, 'core/home.html')


def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.is_staff:
            return redirect('admin_dashboard')

        if Employee.objects.filter(user=request.user).exists():
            return redirect('dashboard')

        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        # Allow login via Employee ID as well as username
        if user is None and username:
            try:
                matched_employee = Employee.objects.filter(
                    employee_id__iexact=username
                ).select_related('user').first()
                if matched_employee and matched_employee.user:
                    user = authenticate(
                        request,
                        username=matched_employee.user.username,
                        password=password
                    )
            except Exception:
                pass

        # Check if account credentials are valid but account is deactivated
        if user is None and username:
            try:
                lookup_user = User.objects.filter(username=username).first()
                if not lookup_user:
                    matched_emp = Employee.objects.filter(
                        employee_id__iexact=username
                    ).select_related('user').first()
                    if matched_emp:
                        lookup_user = matched_emp.user
                if lookup_user and lookup_user.check_password(password) and not lookup_user.is_active:
                    return render(request, 'core/login.html', {
                        'error': 'Your account is currently deactivated. Please contact your administrator.'
                    })
            except Exception:
                pass

        if user is None:
            return render(request, 'core/login.html', {
                'error': 'Invalid username, employee ID, or password.'
            })

        if not user.is_active:
            return render(request, 'core/login.html', {
                'error': 'Your account is currently deactivated. Please contact your administrator.'
            })

        login(request, user)

        # Role-Based Access Control (RBAC) redirection
        if user.is_superuser or user.is_staff:
            return redirect('admin_dashboard')

        if Employee.objects.filter(user=user).exists():
            return redirect('dashboard')

        return redirect('home')

    return render(request, 'core/login.html')



def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    try:
        employee = request.user.employee
    except (Employee.DoesNotExist, AttributeError):
        if request.user.is_superuser or request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('home')

    attendance_records = employee.attendance_records.all().order_by(
        '-date',
        '-check_in'
    )

    leave_requests = employee.leave_requests.all().order_by(
        '-created_at'
    )

    current_month = timezone.now().month
    current_year = timezone.now().year

    monthly_hours = attendance_records.filter(
        date__month=current_month,
        date__year=current_year
    ).aggregate(
        total=Sum('working_hours')
    )['total'] or 0

    if employee.salary_type == 'Hourly':
        monthly_salary = monthly_hours * employee.hourly_rate
    else:
        monthly_salary = employee.basic_salary

    try:
        payroll = employee.payroll_records.filter(
            month=current_month,
            year=current_year
        ).first()
    except Exception:
        try:
            payroll = employee.payroll_records.defer(
                'payment_status', 'payment_gateway', 'payment_order_id', 'payment_id', 'paid_at'
            ).filter(
                month=current_month,
                year=current_year
            ).first()
            if payroll:
                payroll.payment_status = 'Pending'
                payroll.payment_gateway = 'razorpay'
        except Exception:
            payroll = None
    
    unread_notifications_count = Notification.objects.filter(
    employee=employee,
    is_read=False
    ).count()


    # Current month attendance summary
    today = timezone.localdate()
    month_start = today.replace(day=1)

    month_attendance = employee.attendance_records.filter(
        date__gte=month_start,
        date__lte=today
    )

    present_days = month_attendance.filter(
        status='Present'
    ).count()

    late_days = month_attendance.filter(
        status='Late'
    ).count()

    # Approved leave dates: aa dates absent ma count nahi thay
    approved_leaves = employee.leave_requests.filter(
        status='Approved',
        from_date__lte=today,
        to_date__gte=month_start
    )

    approved_leave_dates = set()
    for leave in approved_leaves:
        start = max(leave.from_date, month_start)
        end = min(leave.to_date, today)
        current_date = start

        while current_date <= end:
            approved_leave_dates.add(current_date)
            current_date += timedelta(days=1)

    # Monday-Friday working days; weekends absent ma count nahi thay
    absent_days = 0
    current_date = month_start

    while current_date <= today:
        if (
            current_date.weekday() < 5
            and current_date not in approved_leave_dates
            and not month_attendance.filter(date=current_date).exists()
        ):
            absent_days += 1

        current_date += timedelta(days=1)



    try:
        upcoming_holidays = Holiday.objects.filter(
            date__gte=today
        ).order_by('date')[:5]
    except Exception:
        upcoming_holidays = []

    try:
        recent_payrolls = list(employee.payroll_records.all().order_by('-year', '-month')[:6])
    except Exception:
        try:
            recent_payrolls = list(employee.payroll_records.defer(
                'payment_status', 'payment_gateway', 'payment_order_id', 'payment_id', 'paid_at'
            ).all().order_by('-year', '-month')[:6])
            for p in recent_payrolls:
                p.payment_status = getattr(p, 'payment_status', 'Pending')
                p.payment_gateway = getattr(p, 'payment_gateway', 'razorpay')
        except Exception:
            recent_payrolls = []

    return render(request, 'core/dashboard.html', {
        'employee': employee,
        'attendance_records': attendance_records,
        'leave_requests': leave_requests,
        'monthly_hours': monthly_hours,
        'monthly_salary': monthly_salary,
        'payroll': payroll,
        'recent_payrolls': recent_payrolls,
        'upcoming_holidays': upcoming_holidays,
        'unread_notifications_count': unread_notifications_count,
        'present_days': present_days,
        'absent_days': absent_days,
        'late_days': late_days,
    })


from datetime import date, timedelta, time
from django.shortcuts import render, redirect
from django.db import DatabaseError, OperationalError, ProgrammingError
from django.core.management import call_command
from .models import Leave


def leave_apply(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    employee = request.user.employee
    today = date.today()
    error = None

    if request.method == 'POST':
        leave_type = request.POST.get('leave_type', '').strip()
        from_date = request.POST.get('from_date', '').strip()
        to_date = request.POST.get('to_date', '').strip()
        reason = request.POST.get('reason', '').strip()

        valid_leave_types = [
            'Casual',
            'Sick',
            'Paid',
            'Unpaid',
        ]

        # Check leave type
        if leave_type not in valid_leave_types:
            error = 'Please select a valid leave type.'

        # Check reason
        elif not reason:
            error = 'Please enter a reason for your leave.'

        else:
            try:
                start_date = date.fromisoformat(from_date)
                end_date = date.fromisoformat(to_date)

                # Prevent past dates
                if start_date < today:
                    error = 'Past dates mate leave apply na kari shako.'

                # End date cannot be before start date
                elif end_date < start_date:
                    error = 'To Date, From Date karta pehla na hoi shake.'

                else:
                    Leave.objects.create(
                        employee=employee,
                        leave_type=leave_type,
                        from_date=start_date,
                        to_date=end_date,
                        reason=reason
                    )

                    return redirect('/dashboard/')

            except (ValueError, TypeError):
                error = 'Please enter valid leave dates.'

    return render(request, 'core/leave.html', {
        'employee': employee,
        'today': today.isoformat(),
        'error': error,
    })


def attendance(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    employee = request.user.employee

    if request.method == 'POST':
        action = request.POST.get('action')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')

        # Break hours entered by employee
        try:
            break_hours = float(
                request.POST.get('break_hours', 0) or 0
            )
            if break_hours < 0 or break_hours > 12:
                raise ValueError
        except (TypeError, ValueError):
            return render(request, 'core/attendance.html', {
                'employee': employee,
                'error': 'Break hours 0 thi 12 vachche enter karo.'
            })

        # Location required
        if not latitude or not longitude:
            return render(request, 'core/attendance.html', {
                'employee': employee,
                'error': (
                    'Location detect thai nathi. '
                    'Please location permission Allow karo.'
                )
            })

        # Get all work locations
        work_locations = WorkLocation.objects.all()

        if not work_locations.exists():
            return render(request, 'core/attendance.html', {
                'employee': employee,
                'error': (
                    'Work Location set nathi. '
                    'Admin ma Work Location add karo.'
                )
            })

        # Check distance from all work locations
        location_allowed = False
        nearest_distance = None
        nearest_location = None

        for work_location in work_locations:
            distance = calculate_distance(
                latitude,
                longitude,
                work_location.latitude,
                work_location.longitude
            )

            if (
                nearest_distance is None
                or distance < nearest_distance
            ):
                nearest_distance = distance
                nearest_location = work_location

            if distance <= work_location.allowed_radius:
                location_allowed = True
                break

        # Reject if employee is outside every work location
        if not location_allowed:
            return render(request, 'core/attendance.html', {
                'employee': employee,
                'error': (
                    f'❌ Tame nearest office location thi '
                    f'{round(nearest_distance)} meters door cho. '
                    f'Allowed radius '
                    f'{nearest_location.allowed_radius} meters chhe.'
                )
            })

        today = timezone.localdate()
        current_time = timezone.localtime().time()

        # Check In
        if action == 'check_in':
            attendance_record = Attendance.objects.filter(
                employee=employee,
                date=today
            ).first()

            if attendance_record is None:
                check_in_status = (
                    'Late' if current_time > time(9, 0)
                    else 'Present'
                )

                Attendance.objects.create(
                    employee=employee,
                    date=today,
                    check_in=current_time,
                    break_hours=0,
                    status=check_in_status
                )

            return redirect('/dashboard/')

        # Check Out
        elif action == 'check_out':
            attendance_record = Attendance.objects.filter(
                employee=employee,
                date=today,
                check_in__isnull=False,
                check_out__isnull=True
            ).first()

            if attendance_record:
                from decimal import Decimal

                elapsed_hours = (
                    current_time.hour * 60
                    + current_time.minute
                    + current_time.second / 60
                    - (
                        attendance_record.check_in.hour * 60
                        + attendance_record.check_in.minute
                        + attendance_record.check_in.second / 60
                    )
                ) / 60

                if elapsed_hours < 0:
                    return render(request, 'core/attendance.html', {
                        'employee': employee,
                        'error': (
                            'Overnight shift hoy to admin pase '
                            'attendance correct karavo.'
                        )
                    })

                if break_hours > elapsed_hours:
                    return render(request, 'core/attendance.html', {
                        'employee': employee,
                        'error': (
                            'Break hours total elapsed working time '
                            'karta vadhu na hoi shake.'
                        )
                    })

                attendance_record.check_out = current_time
                attendance_record.break_hours = Decimal(
                    str(break_hours)
                )
                attendance_record.save()

            return redirect('/dashboard/')

    biometric_credentials = employee.biometric_credentials.all()
    today = timezone.localdate()
    today_attendance = Attendance.objects.filter(employee=employee, date=today).first()
    try:
        regularizations = AttendanceRegularization.objects.filter(employee=employee).order_by('-date', '-created_at')
        list(regularizations)
    except (ProgrammingError, OperationalError, DatabaseError):
        safe_run_migrations()
        try:
            regularizations = AttendanceRegularization.objects.filter(employee=employee).order_by('-date', '-created_at')
            list(regularizations)
        except Exception:
            regularizations = []

    return render(request, 'core/attendance.html', {
        'employee': employee,
        'biometric_credentials': biometric_credentials,
        'has_biometric': biometric_credentials.exists(),
        'primary_biometric': biometric_credentials.first(),
        'today_attendance': today_attendance,
        'regularizations': regularizations,
        'today': today.isoformat(),
    })

@owner_required
def admin_dashboard(request):
    today = timezone.localdate()

    current_month = today.month
    current_year = today.year

    total_employees = Employee.objects.count()

    present_today = Attendance.objects.filter(
        date=today,
        status='Present'
    ).count()

    absent_today = Attendance.objects.filter(
        date=today,
        status='Absent'
    ).count()

    pending_leaves = Leave.objects.filter(
        status='Pending'
    ).count()

    monthly_payroll = Payroll.objects.filter(
        month=current_month,
        year=current_year
    ).aggregate(
        total=Sum('net_salary')
    )['total'] or 0

    total_locations = WorkLocation.objects.count()

    try:
        upcoming_holidays_count = Holiday.objects.filter(date__gte=today).count()
        upcoming_holidays = Holiday.objects.filter(date__gte=today).order_by('date')[:5]
    except Exception:
        upcoming_holidays_count = 0
        upcoming_holidays = []

    try:
        pending_regularizations_count = AttendanceRegularization.objects.filter(status='Pending').count()
    except (ProgrammingError, OperationalError, DatabaseError):
        safe_run_migrations()
        try:
            pending_regularizations_count = AttendanceRegularization.objects.filter(status='Pending').count()
        except Exception:
            pending_regularizations_count = 0

    return render(request, 'core/admin_dashboard.html', {
        'total_employees': total_employees,
        'present_today': present_today,
        'absent_today': absent_today,
        'pending_leaves': pending_leaves,
        'monthly_payroll': monthly_payroll,
        'pending_regularizations_count': pending_regularizations_count,
        'total_locations': total_locations,
        'upcoming_holidays_count': upcoming_holidays_count,
        'upcoming_holidays': upcoming_holidays,
    })

@staff_member_required
def employee_list(request):
    status_filter = request.GET.get('status', 'all')
    try:
        all_qs = Employee.objects.all().order_by('name')
        all_count = all_qs.count()
        active_count = Employee.objects.filter(is_active=True).count()
        inactive_count = Employee.objects.filter(is_active=False).count()

        if status_filter == 'active':
            employees = all_qs.filter(is_active=True)
        elif status_filter == 'inactive':
            employees = all_qs.filter(is_active=False)
        else:
            employees = all_qs
        list(employees)
    except (ProgrammingError, OperationalError, DatabaseError):
        safe_run_migrations()
        try:
            all_qs = Employee.objects.all().order_by('name')
            all_count = all_qs.count()
            active_count = Employee.objects.filter(is_active=True).count()
            inactive_count = Employee.objects.filter(is_active=False).count()

            if status_filter == 'active':
                employees = all_qs.filter(is_active=True)
            elif status_filter == 'inactive':
                employees = all_qs.filter(is_active=False)
            else:
                employees = all_qs
            list(employees)
        except Exception:
            try:
                employees = Employee.objects.only(
                    'id', 'user', 'employee_id', 'name', 'phone', 'email',
                    'department', 'joining_date', 'basic_salary', 'hourly_rate', 'salary_type'
                ).order_by('name')
                all_count = len(employees)
                active_count = all_count
                inactive_count = 0
            except Exception:
                employees = []
                all_count = 0
                active_count = 0
                inactive_count = 0

    return render(request, 'core/employees.html', {
        'employees': employees,
        'status_filter': status_filter,
        'total_count': all_count,
        'all_count': all_count,
        'total_employees_count': all_count,
        'active_count': active_count,
        'inactive_count': inactive_count,
    })


@staff_member_required
def employee_toggle_status(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    if request.method == 'POST':
        if employee.is_active:
            employee.soft_delete()
            messages.success(
                request,
                f"Employee '{employee.name}' has been deactivated. Historical records preserved."
            )
        else:
            employee.reactivate()
            messages.success(
                request,
                f"Employee '{employee.name}' has been reactivated successfully."
            )
    return redirect('/admin-dashboard/employees/')


@staff_member_required
def employee_add(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)

        if form.is_valid():
            employee = form.save()

            messages.success(
                request,
                f"Employee '{employee.name}' added successfully."
            )

            return redirect('/admin-dashboard/employees/')

    else:
        form = EmployeeForm()

    return render(request, 'core/employee_form.html', {
        'form': form,
        'title': 'Add Employee'
    })


@staff_member_required
def employee_edit(request, employee_id):
    employee = Employee.objects.get(id=employee_id)

    if request.method == 'POST':
        form = EmployeeForm(
            request.POST,
            instance=employee
        )

        if form.is_valid():
            form.save()
            return redirect('/admin-dashboard/employees/')

    else:
        form = EmployeeForm(instance=employee)

    return render(request, 'core/employee_form.html', {
        'form': form,
        'title': 'Edit Employee'
    })

@staff_member_required
def employee_delete(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    if request.method == 'POST':
        employee.soft_delete()
        messages.success(
            request,
            f"Employee '{employee.name}' deactivated successfully. All attendance, leave, and payroll records preserved."
        )
    return redirect('/admin-dashboard/employees/')


@staff_member_required
def user_management(request):
    employees_without_user = Employee.objects.filter(
        user__isnull=True
    ).order_by('name')

    users = User.objects.all().order_by('username')

    return render(request, 'core/user_management.html', {
        'users': users,
        'employees_without_user': employees_without_user,
    })

@staff_member_required
def user_add(request):
    selected_employee = (
        request.POST.get('employee')
        or request.GET.get('employee')
        or request.GET.get('employee_id')
        or ''
    )
    username = request.POST.get('username', '').strip() if request.method == 'POST' else ''

    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not employee_id:
            messages.error(request, 'Please select an employee.')
        else:
            employee = Employee.objects.filter(
                id=employee_id,
                user__isnull=True
            ).first()

            if not employee:
                messages.error(request, 'Selected employee is invalid or already has a login account.')

            elif not username or not password:
                messages.error(request, 'Username and password are required.')

            elif User.objects.filter(username=username).exists():
                messages.error(request, 'This username already exists.')

            elif password != confirm_password:
                messages.error(request, 'Passwords do not match.')

            elif len(password) < 8:
                messages.error(request, 'Password must be at least 8 characters.')

            else:
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=employee.name
                )

                employee.user = user
                employee.save(update_fields=['user'])

                messages.success(
                    request,
                    f'Login account created successfully for {employee.name}.'
                )
                return redirect('user_management')

    employees = Employee.objects.filter(
        user__isnull=True
    ).order_by('name')

    return render(request, 'core/user_add.html', {
        'employees': employees,
        'selected_employee': selected_employee,
        'username': username,
    })


@staff_member_required
def work_location_list(request):
    work_locations = WorkLocation.objects.all().order_by('name')

    return render(request, 'core/work_locations.html', {
        'work_locations': work_locations
    })


@staff_member_required
def work_location_add(request):
    if request.method == 'POST':
        form = WorkLocationForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('/admin-dashboard/work-locations/')

    else:
        form = WorkLocationForm()

    return render(request, 'core/work_location_form.html', {
        'form': form,
        'title': 'Add Work Location'
    })

@staff_member_required
def work_location_edit(request, location_id):
    location = WorkLocation.objects.get(id=location_id)

    if request.method == 'POST':
        form = WorkLocationForm(
            request.POST,
            instance=location
        )

        if form.is_valid():
            form.save()
            return redirect('/admin-dashboard/work-locations/')

    else:
        form = WorkLocationForm(instance=location)

    return render(request, 'core/work_location_form.html', {
        'form': form,
        'title': 'Edit Work Location'
    })

@staff_member_required
def work_location_delete(request, location_id):
    if request.method == 'POST':
        location = WorkLocation.objects.get(id=location_id)
        location.delete()

    return redirect('/admin-dashboard/work-locations/')

@staff_member_required
def attendance_list(request):

    attendance_records = Attendance.objects.select_related(
        'employee'
    ).all().order_by(
        '-date',
        '-check_in'
    )

    employees = Employee.objects.all().order_by('name')

    employee_id = request.GET.get('employee')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    status = request.GET.get('status')

    if employee_id:
        attendance_records = attendance_records.filter(
            employee_id=employee_id
        )

    if from_date:
        attendance_records = attendance_records.filter(
            date__gte=from_date
        )

    if to_date:
        attendance_records = attendance_records.filter(
            date__lte=to_date
        )

    if status:
        attendance_records = attendance_records.filter(
            status=status
        )

    total_records = attendance_records.count()

    present_count = attendance_records.filter(
        status='Present'
    ).count()

    late_count = attendance_records.filter(
        status='Late'
    ).count()

    absent_count = attendance_records.filter(
        status='Absent'
    ).count()

    total_working_hours = attendance_records.aggregate(
        total=Sum('working_hours')
    )['total'] or 0

    return render(request, 'core/admin_attendance.html', {
        'attendance_records': attendance_records,
        'employees': employees,
        'selected_employee': employee_id,
        'from_date': from_date,
        'to_date': to_date,
        'selected_status': status,

                'total_records': total_records,
        'present_count': present_count,
        'late_count': late_count,
        'absent_count': absent_count,
        'total_working_hours': total_working_hours,
    })

@staff_member_required
def admin_leave_list(request):

    leave_requests = Leave.objects.select_related(
        'employee'
    ).all().order_by(
        '-created_at'
    )

    return render(request, 'core/admin_leave.html', {
        'leave_requests': leave_requests
    })


@staff_member_required
def leave_update_status(request, leave_id, status):
    if request.method == 'POST':
        leave = get_object_or_404(Leave, id=leave_id)

        if status in ['Approved', 'Rejected']:
            old_status = leave.status
            leave.status = status
            leave.save()

            if old_status != status:
                Notification.objects.create(
                    employee=leave.employee,
                    title=f'Leave Request {status}',
                    message=(
                        f'Your {leave.leave_type} leave request '
                        f'from {leave.from_date} to {leave.to_date} '
                        f'has been {status.lower()}.'
                    )
                )

                # Send email notification to employee if email is set
                try:
                    from .email_utils import send_leave_status_email
                    sent, msg = send_leave_status_email(leave)
                    if sent:
                        messages.success(request, f'Leave status updated to {status}. {msg}')
                    else:
                        messages.info(request, f'Leave status updated to {status}. ({msg})')
                except Exception as e:
                    messages.success(request, f'Leave status updated to {status}.')

    return redirect('/admin-dashboard/leave/')


@staff_member_required
def payroll_add(request):

    if request.method == 'POST':
        form = PayrollForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('admin_payroll_list')

    else:
        form = PayrollForm()

    return render(request, 'core/payroll_form.html', {
        'form': form,
        'title': 'Add Payroll',
    })

@staff_member_required
def payroll_edit(request, payroll_id):

    payroll = Payroll.objects.get(id=payroll_id)

    if request.method == 'POST':
        form = PayrollForm(request.POST, instance=payroll)

        if form.is_valid():
            form.save()
            return redirect('admin_payroll_list')

    else:
        form = PayrollForm(instance=payroll)

    return render(request, 'core/payroll_form.html', {
        'form': form,
        'title': 'Edit Payroll',
    })

@staff_member_required
def payroll_delete(request, payroll_id):

    payroll = Payroll.objects.get(id=payroll_id)

    if request.method == 'POST':
        payroll.delete()
        return redirect('admin_payroll_list')

    return render(request, 'core/payroll_confirm_delete.html', {
        'payroll': payroll,
    })





@staff_member_required
def admin_payroll_list(request):
    import logging
    logger = logging.getLogger(__name__)

    from .gateway import get_gateway_config
    try:
        gateway_config = get_gateway_config()
    except Exception:
        gateway_config = {'provider': 'razorpay', 'is_configured': False, 'currency': 'INR'}

    schema_pending = False
    payroll_qs = Payroll.objects.select_related('employee').all().order_by('-year', '-month')

    employee_id = request.GET.get('employee')
    month = request.GET.get('month')
    year = request.GET.get('year')
    salary_type = request.GET.get('salary_type')
    payment_status = request.GET.get('payment_status')

    if employee_id:
        payroll_qs = payroll_qs.filter(employee_id=employee_id)
    if month:
        payroll_qs = payroll_qs.filter(month=month)
    if year:
        payroll_qs = payroll_qs.filter(year=year)
    if salary_type:
        payroll_qs = payroll_qs.filter(salary_type=salary_type)

    try:
        if payment_status:
            payroll_qs = payroll_qs.filter(payment_status=payment_status)
        payroll_records = list(payroll_qs)
        if payroll_records:
            _ = getattr(payroll_records[0], 'payment_status', 'Pending')
    except Exception as schema_err:
        logger.warning(f"Schema delay in payroll query: {schema_err}. Attempting auto-migration...")
        schema_pending = True
        try:
            from django.core.management import call_command
            call_command('migrate', interactive=False)
            payroll_records = list(payroll_qs)
            schema_pending = False
        except Exception as mig_err:
            logger.error(f"Auto-migration in admin_payroll_list failed: {mig_err}")
            try:
                deferred_qs = Payroll.objects.defer(
                    'payment_status', 'payment_gateway', 'payment_order_id', 'payment_id', 'paid_at'
                ).select_related('employee').all().order_by('-year', '-month')
                if employee_id:
                    deferred_qs = deferred_qs.filter(employee_id=employee_id)
                if month:
                    deferred_qs = deferred_qs.filter(month=month)
                if year:
                    deferred_qs = deferred_qs.filter(year=year)
                if salary_type:
                    deferred_qs = deferred_qs.filter(salary_type=salary_type)
                payroll_records = list(deferred_qs)
            except Exception as final_err:
                logger.error(f"Fatal payroll load error: {final_err}")
                payroll_records = []

    employees = Employee.objects.all().order_by('name')

    month_choices = [
        (i, calendar.month_name[i])
        for i in range(1, 13)
    ]

    # Attendance mathi selected month na total working hours
    for payroll in payroll_records:
        if not hasattr(payroll, 'payment_status') or schema_pending:
            payroll.payment_status = 'Pending'
            payroll.payment_gateway = getattr(gateway_config, 'provider', 'razorpay')

        attendance_total = Attendance.objects.filter(
            employee=payroll.employee,
            date__month=payroll.month,
            date__year=payroll.year,
            check_in__isnull=False,
            check_out__isnull=False,
        ).aggregate(total=Sum('working_hours'))['total']

        payroll.total_hours = attendance_total or Decimal('0.00')

        basic = payroll.basic_salary or Decimal('0.00')
        hourly_rate = payroll.hourly_rate or Decimal('0.00')
        bonus = payroll.bonus or Decimal('0.00')
        deductions = payroll.deductions or Decimal('0.00')

        if payroll.salary_type == 'Hourly':
            payroll.gross_salary = Decimal(str(payroll.total_hours)) * hourly_rate
        else:
            payroll.gross_salary = basic

        payroll.net_salary = payroll.gross_salary + bonus - deductions

    total_payrolls = len(payroll_records)
    total_gross = sum((p.gross_salary or Decimal('0.00')) for p in payroll_records)
    total_bonus = sum((p.bonus or Decimal('0.00')) for p in payroll_records)
    total_deductions = sum((p.deductions or Decimal('0.00')) for p in payroll_records)
    total_net = sum((p.net_salary or Decimal('0.00')) for p in payroll_records)

    return render(request, 'core/admin_payroll.html', {
        'payroll_records': payroll_records,
        'employees': employees,
        'selected_employee': employee_id,
        'selected_month': month,
        'selected_year': year,
        'selected_salary_type': salary_type,
        'selected_payment_status': payment_status,
        'month_choices': month_choices,
        'total_payrolls': total_payrolls,
        'total_gross': total_gross,
        'total_bonus': total_bonus,
        'total_deductions': total_deductions,
        'total_net': total_net,
        'gateway_config': gateway_config,
        'schema_pending': schema_pending,
    })


@staff_member_required
def toggle_user_status(request, user_id):
    if request.method == 'POST':
        user = User.objects.filter(id=user_id).first()

        if user and not user.is_superuser:
            user.is_active = not user.is_active
            user.save(update_fields=['is_active'])

            if user.is_active:
                messages.success(request, f'{user.username} activated successfully.')
            else:
                messages.success(request, f'{user.username} deactivated successfully.')

    return redirect('user_management')


@staff_member_required
def reset_user_password(request, user_id):
    if request.method == 'POST':
        user = User.objects.filter(
            id=user_id,
            is_superuser=False
        ).first()

        if not user:
            messages.error(request, 'User not found or cannot be modified.')
            return redirect('user_management')

        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
        elif password != confirm_password:
            messages.error(request, 'Passwords do not match.')
        else:
            user.set_password(password)
            user.save(update_fields=['password'])
            messages.success(
                request,
                f'Password reset successfully for {user.username}.'
            )

    return redirect('user_management')


@login_required(login_url='/login/')
def employee_profile(request):
    try:
        employee = request.user.employee
    except Exception:
        return redirect('/dashboard/')

    return render(
        request,
        'core/profile.html',
        {'employee': employee}
    )


def employee_notifications(request):
    if not request.user.is_authenticated:
        return redirect('/login/')

    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        return redirect('/login/')

    notifications = Notification.objects.filter(
        employee=employee
    )

    unread_count = notifications.filter(
        is_read=False
    ).count()

    return render(request, 'core/notifications.html', {
        'notifications': notifications,
        'unread_count': unread_count,
    })


@require_POST
def mark_notification_read(request, notification_id):
    if not request.user.is_authenticated:
        return redirect('/login/')

    try:
        employee = request.user.employee
    except Employee.DoesNotExist:
        return redirect('/login/')

    Notification.objects.filter(
        id=notification_id,
        employee=employee
    ).update(is_read=True)

    return redirect('employee_notifications')


@login_required(login_url='/login/')
def payroll_pdf_download(request, payroll_id):
    """
    Generate and stream salary slip PDF for admin or the employee owner.
    """
    payroll = get_object_or_404(
        Payroll.objects.select_related('employee', 'employee__user'),
        id=payroll_id
    )

    is_staff = request.user.is_superuser or request.user.is_staff
    is_owner = hasattr(request.user, 'employee') and request.user.employee == payroll.employee

    if not (is_staff or is_owner):
        messages.error(request, 'You do not have permission to access this salary slip.')
        return redirect('dashboard')

    from .pdf_utils import generate_payroll_pdf
    pdf_bytes = generate_payroll_pdf(payroll)

    filename = f"payslip_{payroll.employee.employee_id}_{payroll.year}_{payroll.month:02d}.pdf"
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    if request.GET.get('download') == '1':
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
    else:
        response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@staff_member_required
def payroll_send_email(request, payroll_id):
    """
    Send salary slip PDF via email to employee.
    """
    payroll = get_object_or_404(
        Payroll.objects.select_related('employee', 'employee__user'),
        id=payroll_id
    )
    from .email_utils import send_payslip_email

    sent, msg = send_payslip_email(payroll)
    if sent:
        messages.success(request, f"Salary slip for {payroll.employee.name} emailed successfully! ({msg})")
    else:
        messages.warning(request, f"Could not email payslip for {payroll.employee.name}: {msg}")

    return redirect('admin_payroll_list')


@staff_member_required
def holiday_list(request):
    """
    Company holidays calendar for admin.
    """
    holidays = Holiday.objects.all().order_by('date')
    today = timezone.localdate()
    return render(request, 'core/holidays.html', {
        'holidays': holidays,
        'today': today,
    })


@staff_member_required
def holiday_add(request):
    """
    Add a new holiday.
    """
    if request.method == 'POST':
        form = HolidayForm(request.POST)
        if form.is_valid():
            holiday = form.save()
            messages.success(request, f'Holiday "{holiday.title}" added successfully.')
            return redirect('holiday_list')
    else:
        form = HolidayForm()

    return render(request, 'core/holiday_form.html', {
        'form': form,
        'title': 'Add Company Holiday',
    })


@staff_member_required
def holiday_edit(request, holiday_id):
    """
    Edit an existing holiday.
    """
    holiday = get_object_or_404(Holiday, id=holiday_id)
    if request.method == 'POST':
        form = HolidayForm(request.POST, instance=holiday)
        if form.is_valid():
            form.save()
            messages.success(request, f'Holiday "{holiday.title}" updated successfully.')
            return redirect('holiday_list')
    else:
        form = HolidayForm(instance=holiday)

    return render(request, 'core/holiday_form.html', {
        'form': form,
        'holiday': holiday,
        'title': 'Edit Company Holiday',
    })


@staff_member_required
def holiday_delete(request, holiday_id):
    """
    Delete a holiday.
    """
    holiday = get_object_or_404(Holiday, id=holiday_id)
    if request.method == 'POST':
        title = holiday.title
        holiday.delete()
        messages.success(request, f'Holiday "{title}" deleted successfully.')
        return redirect('holiday_list')

    return render(request, 'core/holiday_confirm_delete.html', {
        'holiday': holiday,
    })


@csrf_exempt
def run_migrations_view(request):
    """
    Allow administrator or browser navigation to apply pending database migrations directly.
    Works seamlessly via GET or POST without querying unmigrated models first.
    """
    import io
    from django.core.management import call_command
    out = io.StringIO()
    success = False
    try:
        call_command('migrate', interactive=False, stdout=out)
        res_output = out.getvalue().strip() or "Database is already up to date."
        success = True
    except Exception as e:
        res_output = f"Migration execution error: {str(e)}"

    if request.headers.get('accept') == 'application/json' or request.GET.get('format') == 'json':
        return JsonResponse({
            'success': success,
            'output': res_output
        }, status=200 if success else 500)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Database Migrations | WorkEase</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body style="background: #f4f7fc; padding: 40px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
    <div style="max-width: 650px; margin: 40px auto; background: #fff; padding: 32px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px;">
            <span style="font-size: 28px;">{'✅' if success else '❌'}</span>
            <div>
                <h2 style="font-size: 20px; font-weight: 700; color: #1e293b; margin: 0;">Database Migration Runner</h2>
                <p style="font-size: 13px; color: #64748b; margin: 0;">Automated schema synchronization for WorkEase PostgreSQL database.</p>
            </div>
        </div>
        <div class="alert {'alert-success' if success else 'alert-danger'}" role="alert">
            <strong>Status:</strong> {'Migrations successfully applied!' if success else 'Migration execution failed.'}
        </div>
        <pre style="background: #0f172a; color: #38bdf8; padding: 16px; border-radius: 8px; font-size: 12px; max-height: 250px; overflow-y: auto;">{res_output}</pre>
        <div style="margin-top: 24px; display: flex; gap: 12px;">
            <a href="/admin-dashboard/" class="btn btn-primary" style="padding: 8px 18px; font-weight: 600;">Go to Admin Dashboard</a>
            <a href="/dashboard/" class="btn btn-outline-secondary" style="padding: 8px 18px;">Employee Dashboard</a>
        </div>
    </div>
</body>
</html>"""
    return HttpResponse(html_content, status=200 if success else 500)



# ==============================================================================
# Payment Gateway API Views (Razorpay Default Integration)
# ==============================================================================

@staff_member_required
def payroll_initiate_payment(request, payroll_id):
    """
    Gateway API: Initiate Razorpay payment order for specified payroll record.
    Returns JSON payload with order_id, key_id, amount, currency, and notes.
    """
    payroll = get_object_or_404(
        Payroll.objects.select_related('employee'),
        id=payroll_id
    )
    from .gateway import create_payroll_order
    order_data = create_payroll_order(payroll)
    return JsonResponse(order_data)


@staff_member_required
@require_POST
def payroll_verify_payment(request, payroll_id):
    """
    Gateway API: Verify payment callback signature and mark payroll as Paid.
    """
    payroll = get_object_or_404(
        Payroll.objects.select_related('employee'),
        id=payroll_id
    )
    from .gateway import verify_gateway_signature, process_payment_success

    if request.content_type == 'application/json':
        try:
            import json
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = {}
    else:
        data = request.POST

    order_id = data.get('razorpay_order_id') or payroll.payment_order_id or ''
    payment_id = data.get('razorpay_payment_id') or data.get('payment_id') or ''
    signature = data.get('razorpay_signature') or data.get('signature') or ''

    is_valid = verify_gateway_signature(order_id, payment_id, signature)

    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or request.content_type == 'application/json'
        or request.GET.get('format') == 'json'
    )

    if not is_valid:
        if is_ajax:
            return JsonResponse({
                'success': False,
                'error': 'Payment signature verification failed.'
            }, status=400)
        messages.error(request, 'Payment signature verification failed.')
        return redirect('admin_payroll_list')

    success, msg = process_payment_success(
        payroll,
        payment_id=payment_id,
        order_id=order_id,
        gateway='razorpay'
    )

    if is_ajax:
        return JsonResponse({
            'success': True,
            'message': msg,
            'payment_id': payment_id,
            'payroll_id': payroll.id,
            'status': payroll.payment_status
        })

    messages.success(request, f"Salary payment for {payroll.employee.name} confirmed successfully! ({msg})")
    return redirect('admin_payroll_list')


@staff_member_required
@require_POST
def payroll_mark_paid(request, payroll_id):
    """
    Directly mark a payroll record as Paid (e.g. for offline bank transfer or check).
    """
    import uuid
    payroll = get_object_or_404(
        Payroll.objects.select_related('employee'),
        id=payroll_id
    )
    from .gateway import process_payment_success
    manual_id = f"manual_{payroll.id}_{uuid.uuid4().hex[:6]}"
    success, msg = process_payment_success(
        payroll,
        payment_id=manual_id,
        gateway='manual'
    )
    messages.success(request, f"Payroll for {payroll.employee.name} marked as Paid.")
    return redirect('admin_payroll_list')


@csrf_exempt
def payment_webhook(request):
    """
    Public Gateway API Webhook endpoint for async payment notifications.
    """
    import json
    import hmac
    import hashlib
    from django.conf import settings
    from .models import Payroll
    from .gateway import process_payment_success

    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '').strip()
    body = request.body

    if webhook_secret:
        received_sig = request.headers.get('X-Razorpay-Signature', '')
        generated_sig = hmac.new(
            webhook_secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(generated_sig, received_sig):
            return JsonResponse({'error': 'Invalid webhook signature'}, status=400)

    try:
        data = json.loads(body.decode('utf-8'))
        event = data.get('event', '')

        if event in ('payment.captured', 'order.paid'):
            payload_entity = data.get('payload', {}).get('payment', {}).get('entity', {})
            order_id = payload_entity.get('order_id')
            payment_id = payload_entity.get('id')

            payroll = None
            if order_id:
                payroll = Payroll.objects.filter(payment_order_id=order_id).first()

            if not payroll:
                payroll_id = payload_entity.get('notes', {}).get('payroll_id')
                if payroll_id:
                    payroll = Payroll.objects.filter(id=payroll_id).first()

            if payroll:
                process_payment_success(
                    payroll,
                    payment_id=payment_id,
                    order_id=order_id,
                    gateway='razorpay'
                )

        return JsonResponse({'status': 'ok', 'event': event})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ==============================================================================
# WebAuthn / Biometric Authentication Endpoints
# ==============================================================================

def _b64url_decode(s):
    if isinstance(s, str):
        s = s.encode('utf-8')
    s += b'=' * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s)


@login_required(login_url='login')
def biometric_register_options(request):
    """
    WebAuthn Registration Options:
    Generates a cryptographic challenge and returns options for navigator.credentials.create()
    """
    employee = getattr(request.user, 'employee', None)
    if not employee:
        return JsonResponse({'error': 'Employee profile not found.'}, status=403)

    challenge_bytes = secrets.token_bytes(32)
    challenge_b64 = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')
    request.session['webauthn_reg_challenge'] = challenge_b64

    user_id_b64 = base64.urlsafe_b64encode(f"user_{employee.id}_{employee.employee_id}".encode('utf-8')).decode('utf-8').rstrip('=')
    rp_id = request.get_host().split(':')[0]

    exclude_credentials = [
        {"type": "public-key", "id": cred.credential_id}
        for cred in employee.biometric_credentials.all()
    ]

    options = {
        "challenge": challenge_b64,
        "rp": {
            "name": "WorkEase HRMS",
            "id": rp_id,
        },
        "user": {
            "id": user_id_b64,
            "name": employee.contact_email or employee.employee_id,
            "displayName": employee.name,
        },
        "pubKeyCredParams": [
            {"type": "public-key", "alg": -7},    # ES256 (ECDSA w/ SHA-256)
            {"type": "public-key", "alg": -257},  # RS256 (RSA w/ SHA-256)
        ],
        "authenticatorSelection": {
            "authenticatorAttachment": "platform",
            "userVerification": "preferred",
            "residentKey": "preferred",
        },
        "excludeCredentials": exclude_credentials,
        "timeout": 60000,
        "attestation": "none",
    }
    return JsonResponse(options)


@login_required(login_url='login')
def biometric_register_verify(request):
    """
    WebAuthn Registration Verification:
    Saves the credential_id and public_key to the employee's BiometricCredential records.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required.'}, status=405)

    employee = getattr(request.user, 'employee', None)
    if not employee:
        return JsonResponse({'error': 'Employee profile not found.'}, status=403)

    try:
        if request.content_type == 'application/json' or request.body:
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST
    except Exception:
        data = request.POST

    credential_id = (data.get('credential_id') or data.get('id') or '').strip()
    public_key = data.get('public_key') or data.get('attestationObject') or 'webauthn_platform_key'
    device_name = (data.get('device_name') or '').strip() or 'Biometric Device'
    client_data_json = data.get('clientDataJSON')

    if not credential_id:
        return JsonResponse({'error': 'credential_id is required.'}, status=400)

    # Challenge validation when clientDataJSON is provided
    expected_challenge = request.session.get('webauthn_reg_challenge')
    if client_data_json and expected_challenge:
        try:
            client_data = json.loads(_b64url_decode(client_data_json).decode('utf-8'))
            received_challenge = client_data.get('challenge', '').rstrip('=')
            if received_challenge and received_challenge != expected_challenge:
                return JsonResponse({'error': 'Registration challenge validation failed.'}, status=400)
        except Exception:
            pass

    cred, created = BiometricCredential.objects.update_or_create(
        credential_id=credential_id,
        defaults={
            'employee': employee,
            'public_key': str(public_key),
            'device_name': device_name,
            'sign_count': 0,
        }
    )

    request.session.pop('webauthn_reg_challenge', None)

    return JsonResponse({
        'success': True,
        'message': f'Biometric credential registered successfully for {device_name}!',
        'credential_id': cred.credential_id,
        'device_name': cred.device_name,
        'created': created,
    })


@login_required(login_url='login')
def biometric_auth_options(request):
    """
    WebAuthn Authentication Options:
    Generates challenge for the logged-in employee's registered credential_id(s).
    """
    employee = getattr(request.user, 'employee', None)
    if not employee:
        return JsonResponse({'error': 'Employee profile not found.'}, status=403)

    credentials = employee.biometric_credentials.all()
    if not credentials.exists():
        return JsonResponse({
            'error': 'No biometric credentials registered. Please register fingerprint or Face ID first.'
        }, status=400)

    challenge_bytes = secrets.token_bytes(32)
    challenge_b64 = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')
    request.session['webauthn_auth_challenge'] = challenge_b64

    rp_id = request.get_host().split(':')[0]
    allow_credentials = [
        {
            "type": "public-key",
            "id": cred.credential_id,
        } for cred in credentials
    ]

    options = {
        "challenge": challenge_b64,
        "rpId": rp_id,
        "allowCredentials": allow_credentials,
        "userVerification": "preferred",
        "timeout": 60000,
    }
    return JsonResponse(options)


@login_required(login_url='login')
def biometric_auth_verify(request):
    """
    WebAuthn Authentication & Attendance Verification:
    Verifies signature and triggers Check-In / Check-Out with GPS coordinates.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required.'}, status=405)

    employee = getattr(request.user, 'employee', None)
    if not employee:
        return JsonResponse({'error': 'Employee profile not found.'}, status=403)

    try:
        if request.content_type == 'application/json' or request.body:
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST
    except Exception:
        data = request.POST

    credential_id = (data.get('credential_id') or data.get('id') or '').strip()
    client_data_json = data.get('clientDataJSON')
    action = (data.get('action') or '').strip().lower()
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    break_hours_val = data.get('break_hours', 0)

    if not credential_id:
        return JsonResponse({'error': 'credential_id is required.'}, status=400)

    if action not in ('check_in', 'check_out'):
        return JsonResponse({'error': 'Invalid attendance action. Must be check_in or check_out.'}, status=400)

    # Verify credential belongs to this employee
    cred = employee.biometric_credentials.filter(credential_id=credential_id).first()
    if not cred:
        return JsonResponse({'error': 'Unrecognized or unauthorized biometric credential.'}, status=400)

    # Validate challenge if clientDataJSON is provided
    expected_challenge = request.session.get('webauthn_auth_challenge')
    if client_data_json and expected_challenge:
        try:
            client_data = json.loads(_b64url_decode(client_data_json).decode('utf-8'))
            received_challenge = client_data.get('challenge', '').rstrip('=')
            if received_challenge and received_challenge != expected_challenge:
                return JsonResponse({'error': 'Authentication challenge mismatch.'}, status=400)
        except Exception:
            pass

    # Increment sign counter and remove single-use challenge
    cred.sign_count += 1
    cred.save(update_fields=['sign_count'])
    request.session.pop('webauthn_auth_challenge', None)

    # GPS Location Verification
    if not latitude or not longitude:
        return JsonResponse({'error': 'GPS location required for biometric attendance.'}, status=400)

    work_locations = WorkLocation.objects.all()
    if not work_locations.exists():
        return JsonResponse({'error': 'No office work location is configured by administrator.'}, status=400)

    location_allowed = False
    nearest_distance = None
    nearest_location = None

    for work_location in work_locations:
        distance = calculate_distance(latitude, longitude, work_location.latitude, work_location.longitude)
        if nearest_distance is None or distance < nearest_distance:
            nearest_distance = distance
            nearest_location = work_location
        if distance <= work_location.allowed_radius:
            location_allowed = True
            break

    if not location_allowed:
        return JsonResponse({
            'error': (
                f'You are {round(nearest_distance)} meters away from nearest office. '
                f'Allowed radius is {nearest_location.allowed_radius} meters.'
            )
        }, status=400)

    today = timezone.localdate()
    current_time = timezone.localtime().time()

    if action == 'check_in':
        record = Attendance.objects.filter(employee=employee, date=today).first()
        if record and record.check_in:
            return JsonResponse({
                'success': False,
                'error': 'Already checked in for today.',
                'status': record.status,
                'check_in': record.check_in.strftime('%H:%M:%S'),
            }, status=400)

        check_in_status = 'Late' if current_time > time(9, 0) else 'Present'
        if record:
            record.check_in = current_time
            record.status = check_in_status
            record.save()
        else:
            record = Attendance.objects.create(
                employee=employee,
                date=today,
                check_in=current_time,
                break_hours=0,
                status=check_in_status
            )

        return JsonResponse({
            'success': True,
            'message': f'Biometric Check-In successful at {current_time.strftime("%H:%M:%S")} ({check_in_status})!',
            'action': 'check_in',
            'time': current_time.strftime('%H:%M:%S'),
            'status': check_in_status,
            'device': cred.device_name,
        })

    elif action == 'check_out':
        try:
            break_hours = float(break_hours_val or 0)
            if break_hours < 0 or break_hours > 12:
                raise ValueError
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Break hours must be between 0 and 12.'}, status=400)

        record = Attendance.objects.filter(
            employee=employee,
            date=today,
            check_in__isnull=False,
            check_out__isnull=True
        ).first()

        if not record:
            return JsonResponse({'error': 'No active check-in found for today.'}, status=400)

        elapsed_hours = (
            current_time.hour * 60 + current_time.minute + current_time.second / 60
            - (record.check_in.hour * 60 + record.check_in.minute + record.check_in.second / 60)
        ) / 60

        if elapsed_hours < 0:
            return JsonResponse({'error': 'Invalid shift timestamps for today.'}, status=400)

        if break_hours > elapsed_hours:
            return JsonResponse({'error': 'Break hours cannot exceed total elapsed working time.'}, status=400)

        record.check_out = current_time
        record.break_hours = Decimal(str(break_hours))
        record.save()

        return JsonResponse({
            'success': True,
            'message': f'Biometric Check-Out successful at {current_time.strftime("%H:%M:%S")}! Working hours: {record.working_hours} hrs.',
            'action': 'check_out',
            'time': current_time.strftime('%H:%M:%S'),
            'working_hours': str(record.working_hours),
            'device': cred.device_name,
        })


@login_required
def attendance_regularize(request):
    if not hasattr(request.user, 'employee'):
        messages.error(request, "Employee profile not found.")
        return redirect('/dashboard/')

    employee = request.user.employee
    if request.method == 'POST':
        date_str = request.POST.get('date')
        check_in_str = request.POST.get('requested_check_in')
        check_out_str = request.POST.get('requested_check_out')
        reason = request.POST.get('reason', '').strip()

        if not date_str:
            messages.error(request, "Please select a date for attendance regularization.")
            return redirect('attendance')

        if not check_in_str and not check_out_str:
            messages.error(request, "Please enter at least a requested check-in or check-out time.")
            return redirect('attendance')

        if not reason:
            messages.error(request, "Please provide a reason explaining the missed punch.")
            return redirect('attendance')

        from datetime import datetime
        try:
            reg_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            req_in = datetime.strptime(check_in_str, '%H:%M').time() if check_in_str else None
            req_out = datetime.strptime(check_out_str, '%H:%M').time() if check_out_str else None
        except ValueError:
            messages.error(request, "Invalid date or time format.")
            return redirect('attendance')

        if req_in and req_out and req_out <= req_in:
            messages.error(request, "Requested check-out time must be after check-in time.")
            return redirect('attendance')

        att_record = Attendance.objects.filter(employee=employee, date=reg_date).first()

        regularization = AttendanceRegularization.objects.create(
            employee=employee,
            attendance=att_record,
            date=reg_date,
            requested_check_in=req_in,
            requested_check_out=req_out,
            reason=reason,
            status='Pending'
        )

        messages.success(
            request,
            f"Attendance regularization request for {reg_date} submitted successfully. Awaiting manager approval."
        )

    return redirect('attendance')


@staff_member_required
def admin_regularization_list(request):
    status_filter = request.GET.get('status', 'all')
    employee_id = request.GET.get('employee')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    try:
        requests_qs = AttendanceRegularization.objects.select_related('employee', 'attendance').all().order_by('-created_at')
        if status_filter in ['Pending', 'Approved', 'Rejected']:
            requests_qs = requests_qs.filter(status=status_filter)
        if employee_id:
            requests_qs = requests_qs.filter(employee_id=employee_id)
        if from_date:
            requests_qs = requests_qs.filter(date__gte=from_date)
        if to_date:
            requests_qs = requests_qs.filter(date__lte=to_date)
        list(requests_qs)
        total_requests = AttendanceRegularization.objects.count()
        pending_count = AttendanceRegularization.objects.filter(status='Pending').count()
        approved_count = AttendanceRegularization.objects.filter(status='Approved').count()
        rejected_count = AttendanceRegularization.objects.filter(status='Rejected').count()
    except (ProgrammingError, OperationalError, DatabaseError):
        safe_run_migrations()
        try:
            requests_qs = AttendanceRegularization.objects.select_related('employee', 'attendance').all().order_by('-created_at')
            if status_filter in ['Pending', 'Approved', 'Rejected']:
                requests_qs = requests_qs.filter(status=status_filter)
            if employee_id:
                requests_qs = requests_qs.filter(employee_id=employee_id)
            if from_date:
                requests_qs = requests_qs.filter(date__gte=from_date)
            if to_date:
                requests_qs = requests_qs.filter(date__lte=to_date)
            list(requests_qs)
            total_requests = AttendanceRegularization.objects.count()
            pending_count = AttendanceRegularization.objects.filter(status='Pending').count()
            approved_count = AttendanceRegularization.objects.filter(status='Approved').count()
            rejected_count = AttendanceRegularization.objects.filter(status='Rejected').count()
        except Exception:
            requests_qs = []
            total_requests = 0
            pending_count = 0
            approved_count = 0
            rejected_count = 0

    try:
        employees = Employee.objects.all().order_by('name')
    except Exception:
        employees = []

    return render(request, 'core/admin_regularization.html', {
        'regularization_requests': requests_qs,
        'employees': employees,
        'status_filter': status_filter,
        'selected_employee': employee_id,
        'from_date': from_date,
        'to_date': to_date,
        'total_requests': total_requests,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    })


@staff_member_required
def admin_regularization_action(request, regularization_id, status):
    regularization = get_object_or_404(
        AttendanceRegularization.objects.select_related('employee', 'attendance'),
        id=regularization_id
    )

    if status not in ['Approved', 'Rejected']:
        messages.error(request, "Invalid regularization status.")
        return redirect('admin_regularizations')

    admin_remarks = request.POST.get('admin_remarks', '').strip() if request.method == 'POST' else ''

    if status == 'Approved':
        regularization.approve(admin_remarks=admin_remarks)
        Notification.objects.create(
            employee=regularization.employee,
            title='Attendance Regularization Approved',
            message=(
                f'Your attendance regularization request for {regularization.date} '
                f'has been approved. Total working hours recalculated.'
            )
        )
        messages.success(
            request,
            f"Attendance regularization for {regularization.employee.name} on {regularization.date} approved. Attendance updated."
        )
    elif status == 'Rejected':
        regularization.reject(admin_remarks=admin_remarks)
        Notification.objects.create(
            employee=regularization.employee,
            title='Attendance Regularization Rejected',
            message=(
                f'Your attendance regularization request for {regularization.date} '
                f'has been rejected. Remarks: {admin_remarks or "No remarks provided."}'
            )
        )
        messages.warning(
            request,
            f"Attendance regularization for {regularization.employee.name} on {regularization.date} rejected."
        )

    return redirect('admin_regularizations')


@staff_member_required
def employee_export_csv(request):
    """Export all employee records as a formatted CSV file."""
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    today_str = timezone.localdate().strftime('%Y%m%d')
    response['Content-Disposition'] = f'attachment; filename="workease_employees_{today_str}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'employee_id',
        'name',
        'email',
        'phone',
        'department',
        'salary_type',
        'basic_salary',
        'hourly_rate',
        'is_active',
        'joining_date',
        'relieving_date',
    ])

    employees = Employee.objects.select_related('user').all().order_by('employee_id')
    for emp in employees:
        writer.writerow([
            emp.employee_id,
            emp.name,
            emp.contact_email or '',
            emp.phone or '',
            emp.department or '',
            emp.salary_type or 'Monthly',
            emp.basic_salary if emp.basic_salary is not None else '0.00',
            emp.hourly_rate if emp.hourly_rate is not None else '0.00',
            'True' if emp.is_active else 'False',
            emp.joining_date.strftime('%Y-%m-%d') if emp.joining_date else '',
            emp.relieving_date.strftime('%Y-%m-%d') if emp.relieving_date else '',
        ])

    return response


@staff_member_required
def employee_sample_csv(request):
    """Download a template CSV header and sample rows for bulk employee onboarding."""
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="workease_employee_import_sample.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'employee_id',
        'name',
        'email',
        'phone',
        'department',
        'salary_type',
        'basic_salary',
        'hourly_rate',
        'is_active',
        'joining_date',
        'relieving_date',
    ])
    writer.writerow([
        'EMP-1001',
        'Alex Mercer',
        'alex.mercer@example.com',
        '9876543210',
        'Engineering',
        'Monthly',
        '75000.00',
        '0.00',
        'True',
        '2026-01-15',
        '',
    ])
    writer.writerow([
        'EMP-1002',
        'Sara Connor',
        'sara.connor@example.com',
        '9876543211',
        'Operations',
        'Hourly',
        '0.00',
        '450.00',
        'True',
        '2026-02-01',
        '',
    ])
    return response


@staff_member_required
def employee_import_csv(request):
    """Parse uploaded CSV, create or update Employee and linked User accounts."""
    import csv
    import io
    from datetime import datetime
    from decimal import Decimal
    from django.contrib.auth.models import User

    if request.method != 'POST':
        return redirect('employee_list')

    csv_file = request.FILES.get('csv_file')
    if not csv_file:
        messages.error(request, "No CSV file selected. Please select a .csv file to import.")
        return redirect('employee_list')

    if not csv_file.name.lower().endswith('.csv'):
        messages.error(request, "Invalid file format. Please upload a file with a .csv extension.")
        return redirect('employee_list')

    try:
        file_data = csv_file.read().decode('utf-8-sig', errors='replace')
        reader = csv.DictReader(io.StringIO(file_data))
    except Exception as e:
        messages.error(request, f"Could not read CSV file: {str(e)}")
        return redirect('employee_list')

    created_count = 0
    updated_count = 0
    errors = []

    for row_idx, raw_row in enumerate(reader, start=2):
        row = {k.strip(): (v.strip() if v else '') for k, v in raw_row.items() if k}
        emp_id = row.get('employee_id')
        name = row.get('name')

        if not emp_id or not name:
            errors.append(f"Row {row_idx}: Missing required employee_id or name.")
            continue

        email = row.get('email', '')
        phone = row.get('phone', '')
        department = row.get('department') or 'General'
        salary_type = row.get('salary_type', 'Monthly')
        if salary_type not in ['Monthly', 'Hourly']:
            salary_type = 'Monthly'

        try:
            basic_salary = Decimal(str(row.get('basic_salary') or 0))
        except Exception:
            basic_salary = Decimal('0.00')

        try:
            hourly_rate = Decimal(str(row.get('hourly_rate') or 0))
        except Exception:
            hourly_rate = Decimal('0.00')

        is_active_raw = row.get('is_active', 'True').lower()
        is_active = is_active_raw in ['true', '1', 'yes', 't', 'active']

        joining_date_raw = row.get('joining_date')
        joining_date = timezone.localdate()
        if joining_date_raw:
            for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d'):
                try:
                    joining_date = datetime.strptime(joining_date_raw, fmt).date()
                    break
                except ValueError:
                    pass

        relieving_date_raw = row.get('relieving_date')
        relieving_date = None
        if relieving_date_raw:
            for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d'):
                try:
                    relieving_date = datetime.strptime(relieving_date_raw, fmt).date()
                    break
                except ValueError:
                    pass

        try:
            employee, created = Employee.objects.get_or_create(
                employee_id=emp_id,
                defaults={
                    'name': name,
                    'email': email or None,
                    'phone': phone,
                    'department': department,
                    'salary_type': salary_type,
                    'basic_salary': basic_salary,
                    'hourly_rate': hourly_rate,
                    'is_active': is_active,
                    'joining_date': joining_date,
                    'relieving_date': relieving_date,
                }
            )

            if not created:
                employee.name = name
                if email:
                    employee.email = email
                if phone:
                    employee.phone = phone
                employee.department = department
                employee.salary_type = salary_type
                employee.basic_salary = basic_salary
                employee.hourly_rate = hourly_rate
                employee.is_active = is_active
                employee.joining_date = joining_date
                employee.relieving_date = relieving_date
                employee.save()
                updated_count += 1
            else:
                created_count += 1

            # Sync or create linked User account
            if not employee.user:
                username = emp_id.lower().replace('-', '_')
                user_obj = User.objects.filter(username=username).first()
                if not user_obj and email:
                    user_obj = User.objects.filter(email=email).first()
                if not user_obj:
                    user_obj = User.objects.create_user(
                        username=username,
                        email=email or f"{username}@workease.local",
                        password=secrets.token_urlsafe(10),
                        is_active=is_active
                    )
                employee.user = user_obj
                employee.save(update_fields=['user'])
            else:
                if employee.user.is_active != is_active:
                    employee.user.is_active = is_active
                    employee.user.save(update_fields=['is_active'])

        except Exception as e:
            errors.append(f"Row {row_idx} ({emp_id}): {str(e)}")

    if created_count > 0 or updated_count > 0:
        messages.success(
            request,
            f"Employee Import Completed: {created_count} created, {updated_count} updated."
        )
    if errors:
        messages.warning(
            request,
            f"Import Warnings ({len(errors)} issues): {'; '.join(errors[:3])}"
        )

    return redirect('employee_list')


@staff_member_required
def admin_attendance_export_csv(request):
    """Export filtered Attendance records to CSV for accounting and audit."""
    import csv
    from django.http import HttpResponse

    employee_id = request.GET.get('employee')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    status = request.GET.get('status')

    attendance_records = Attendance.objects.select_related('employee').all().order_by('-date', '-check_in')

    if employee_id:
        attendance_records = attendance_records.filter(employee_id=employee_id)
    if from_date:
        attendance_records = attendance_records.filter(date__gte=from_date)
    if to_date:
        attendance_records = attendance_records.filter(date__lte=to_date)
    if status:
        attendance_records = attendance_records.filter(status=status)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    today_str = timezone.localdate().strftime('%Y%m%d')
    response['Content-Disposition'] = f'attachment; filename="workease_attendance_{today_str}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Date',
        'Employee ID',
        'Employee Name',
        'Department',
        'Check-In',
        'Check-Out',
        'Break Hours',
        'Working Hours',
        'Status',
    ])

    for rec in attendance_records:
        writer.writerow([
            rec.date.strftime('%Y-%m-%d') if rec.date else '',
            rec.employee.employee_id if rec.employee else '',
            rec.employee.name if rec.employee else '',
            rec.employee.department if rec.employee else '',
            rec.check_in.strftime('%H:%M:%S') if rec.check_in else '',
            rec.check_out.strftime('%H:%M:%S') if rec.check_out else '',
            rec.break_hours if rec.break_hours is not None else '0.00',
            rec.working_hours if rec.working_hours is not None else '0.00',
            rec.status,
        ])

    return response


@staff_member_required
def payroll_export_csv(request):
    """Export filtered Payroll statements to CSV for CA & tax accounting."""
    import csv
    from django.http import HttpResponse

    month = request.GET.get('month')
    year = request.GET.get('year')
    employee_id = request.GET.get('employee')
    payment_status = request.GET.get('payment_status')

    payroll_records = Payroll.objects.select_related('employee').all().order_by('-year', '-month')

    if month:
        payroll_records = payroll_records.filter(month=month)
    if year:
        payroll_records = payroll_records.filter(year=year)
    if employee_id:
        payroll_records = payroll_records.filter(employee_id=employee_id)
    if payment_status:
        payroll_records = payroll_records.filter(payment_status=payment_status)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    today_str = timezone.localdate().strftime('%Y%m%d')
    response['Content-Disposition'] = f'attachment; filename="workease_payroll_{today_str}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Month',
        'Year',
        'Employee ID',
        'Employee Name',
        'Department',
        'Salary Type',
        'Basic Salary',
        'Hourly Rate',
        'Total Hours',
        'Bonus',
        'Deductions',
        'Gross Salary',
        'Net Payable',
        'Payment Status',
        'Payment Gateway',
        'Payment Order ID',
        'Payment ID',
        'Paid At',
    ])

    for p in payroll_records:
        writer.writerow([
            p.month,
            p.year,
            p.employee.employee_id if p.employee else '',
            p.employee.name if p.employee else '',
            p.employee.department if p.employee else '',
            p.salary_type,
            p.basic_salary,
            p.hourly_rate,
            p.total_hours,
            p.bonus,
            p.deductions,
            p.gross_salary,
            p.net_salary,
            p.payment_status,
            p.payment_gateway,
            p.payment_order_id or '',
            p.payment_id or '',
            p.paid_at.strftime('%Y-%m-%d %H:%M:%S') if p.paid_at else '',
        ])

    return response
