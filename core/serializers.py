from rest_framework import serializers
from .models import Employee, Attendance, Leave, Payroll


class EmployeeSerializer(serializers.ModelSerializer):
    contact_email = serializers.EmailField(read_only=True, allow_null=True)

    class Meta:
        model = Employee
        fields = [
            'id',
            'user',
            'employee_id',
            'name',
            'phone',
            'email',
            'contact_email',
            'department',
            'joining_date',
            'basic_salary',
            'hourly_rate',
            'salary_type',
        ]
        read_only_fields = ['id', 'contact_email']


class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.ReadOnlyField(source='employee.name')

    class Meta:
        model = Attendance
        fields = [
            'id',
            'employee',
            'employee_name',
            'date',
            'check_in',
            'check_out',
            'working_hours',
            'break_hours',
            'status',
            'created_at',
        ]
        read_only_fields = ['id', 'working_hours', 'created_at']


class LeaveSerializer(serializers.ModelSerializer):
    employee_name = serializers.ReadOnlyField(source='employee.name')

    class Meta:
        model = Leave
        fields = [
            'id',
            'employee',
            'employee_name',
            'leave_type',
            'from_date',
            'to_date',
            'reason',
            'status',
        ]
        read_only_fields = ['id']


# Alias for explicit naming compatibility
LeaveRequestSerializer = LeaveSerializer


class PayrollSerializer(serializers.ModelSerializer):
    employee_name = serializers.ReadOnlyField(source='employee.name')

    class Meta:
        model = Payroll
        fields = [
            'id',
            'employee',
            'employee_name',
            'month',
            'year',
            'salary_type',
            'total_hours',
            'hourly_rate',
            'basic_salary',
            'bonus',
            'deductions',
            'gross_salary',
            'net_salary',
            'payment_status',
            'payment_gateway',
            'payment_order_id',
            'payment_id',
            'paid_at',
            'generated_at',
        ]
        read_only_fields = [
            'id',
            'generated_at',
        ]
