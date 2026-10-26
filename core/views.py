from django.shortcuts import render, redirect
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


from .forms import EmployeeForm, WorkLocationForm, PayrollForm

from .models import Attendance, Leave, WorkLocation
from .models import Attendance, Leave, WorkLocation, Employee, Payroll
from django.contrib.admin.views.decorators import staff_member_required
from math import radians, sin, cos, sqrt, atan2


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

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
            matched_employee = Employee.objects.filter(
                employee_id__iexact=username
            ).select_related('user').first()
            if matched_employee and matched_employee.user:
                user = authenticate(
                    request,
                    username=matched_employee.user.username,
                    password=password
                )

        # Check if account credentials are valid but account is deactivated
        if user is None and username:
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

    payroll = employee.payroll_records.filter(
        month=current_month,
        year=current_year
    ).first()
    
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



    return render(request, 'core/dashboard.html', {
        'employee': employee,
        'attendance_records': attendance_records,
        'leave_requests': leave_requests,
        'monthly_hours': monthly_hours,
        'monthly_salary': monthly_salary,
        'payroll': payroll,
        'unread_notifications_count': unread_notifications_count,
        'present_days': present_days,
        'absent_days': absent_days,
        'late_days': late_days,
    })


from datetime import date, timedelta, time
from django.shortcuts import render, redirect
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

    return render(request, 'core/attendance.html', {
        'employee': employee
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

    return render(request, 'core/admin_dashboard.html', {
        'total_employees': total_employees,
        'present_today': present_today,
        'absent_today': absent_today,
        'pending_leaves': pending_leaves,
        'monthly_payroll': monthly_payroll,
        'total_locations': total_locations,
    })

@staff_member_required
def employee_list(request):
    employees = Employee.objects.all().order_by('name')

    return render(request, 'core/employees.html', {
        'employees': employees
    })


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
    if request.method == 'POST':
        employee = Employee.objects.get(id=employee_id)
        employee.delete()

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
    payroll_records = Payroll.objects.select_related(
        'employee'
    ).all().order_by('-year', '-month')

    employees = Employee.objects.all().order_by('name')

    employee_id = request.GET.get('employee')
    month = request.GET.get('month')
    year = request.GET.get('year')
    salary_type = request.GET.get('salary_type')

    if employee_id:
        payroll_records = payroll_records.filter(employee_id=employee_id)

    if month:
        payroll_records = payroll_records.filter(month=month)

    if year:
        payroll_records = payroll_records.filter(year=year)

    if salary_type:
        payroll_records = payroll_records.filter(salary_type=salary_type)

    month_choices = [
        (i, calendar.month_name[i])
        for i in range(1, 13)
    ]

    # Attendance mathi selected month na total working hours
    for payroll in payroll_records:
        attendance_total = Attendance.objects.filter(
            employee=payroll.employee,
            date__month=payroll.month,
            date__year=payroll.year,
            check_in__isnull=False,
            check_out__isnull=False,
        ).aggregate(total=Sum('working_hours'))['total']

        payroll.total_hours = attendance_total or 0

        # Updated hours pramane salary calculate karo
        if payroll.salary_type == 'Hourly':
            payroll.gross_salary = (
                payroll.total_hours * payroll.hourly_rate
            )
        else:
            payroll.gross_salary = payroll.basic_salary

        payroll.net_salary = (
            payroll.gross_salary
            + payroll.bonus
            - payroll.deductions
        )

    total_payrolls = payroll_records.count()

    total_gross = sum(p.gross_salary for p in payroll_records)
    total_bonus = sum(p.bonus for p in payroll_records)
    total_deductions = sum(p.deductions for p in payroll_records)
    total_net = sum(p.net_salary for p in payroll_records)

    return render(request, 'core/admin_payroll.html', {
        'payroll_records': payroll_records,
        'employees': employees,
        'selected_employee': employee_id,
        'selected_month': month,
        'selected_year': year,
        'selected_salary_type': salary_type,
        'month_choices': month_choices,
        'total_payrolls': total_payrolls,
        'total_gross': total_gross,
        'total_bonus': total_bonus,
        'total_deductions': total_deductions,
        'total_net': total_net,
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
