from django.contrib import admin
from .models import Employee, Attendance, Payroll, Leave, WorkLocation


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):

    list_display = (
        'employee_id',
        'name',
        'department',
        'phone',
        'salary_type',
        'basic_salary',
        'joining_date',
    )

    search_fields = (
        'employee_id',
        'name',
        'phone',
        'department',
    )

    list_filter = (
        'department',
        'salary_type',
    )

    ordering = (
        'name',
    )


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):

    list_display = (
        'employee',
        'date',
        'check_in',
        'check_out',
        'working_hours',
        'status',
    )

    search_fields = (
        'employee__name',
        'employee__employee_id',
    )

    list_filter = (
        'status',
        'date',
    )

    ordering = (
        '-date',
        '-check_in',
    )


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):

    list_display = (
        'employee',
        'month',
        'year',
        'salary_type',
        'total_hours',
        'gross_salary',
        'net_salary',
    )

    search_fields = (
        'employee__name',
        'employee__employee_id',
    )

    list_filter = (
        'salary_type',
        'month',
        'year',
    )

    ordering = (
        '-year',
        '-month',
    )


@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):

    list_display = (
        'employee',
        'leave_type',
        'from_date',
        'to_date',
        'status',
        'created_at',
    )

    search_fields = (
        'employee__name',
        'employee__employee_id',
    )

    list_filter = (
        'status',
        'leave_type',
    )

    ordering = (
        '-created_at',
    )


@admin.register(WorkLocation)
class WorkLocationAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'latitude',
        'longitude',
        'allowed_radius',
        'created_at',
    )

    search_fields = (
        'name',
    )

    list_filter = (
        'allowed_radius',
    )

    ordering = (
        'name',
    )