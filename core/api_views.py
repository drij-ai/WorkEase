from rest_framework import viewsets, permissions
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Employee, Attendance, Leave, Payroll
from .serializers import (
    EmployeeSerializer,
    AttendanceSerializer,
    LeaveSerializer,
    LeaveRequestSerializer,
    PayrollSerializer,
)


@extend_schema_view(
    list=extend_schema(summary="List all employees", tags=["Employees"]),
    retrieve=extend_schema(summary="Retrieve employee details", tags=["Employees"]),
    create=extend_schema(summary="Create a new employee", tags=["Employees"]),
    update=extend_schema(summary="Update full employee record", tags=["Employees"]),
    partial_update=extend_schema(summary="Partially update employee record", tags=["Employees"]),
    destroy=extend_schema(summary="Delete an employee", tags=["Employees"]),
)
class EmployeeViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Employee records.
    Requires authentication.
    """
    queryset = Employee.objects.select_related('user').all().order_by('employee_id')
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated]


@extend_schema_view(
    list=extend_schema(summary="List attendance records", tags=["Attendance"]),
    retrieve=extend_schema(summary="Retrieve attendance record", tags=["Attendance"]),
    create=extend_schema(summary="Log attendance record", tags=["Attendance"]),
    update=extend_schema(summary="Update attendance record", tags=["Attendance"]),
    partial_update=extend_schema(summary="Partially update attendance record", tags=["Attendance"]),
    destroy=extend_schema(summary="Delete attendance record", tags=["Attendance"]),
)
class AttendanceViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Employee Attendance records.
    Requires authentication.
    """
    queryset = Attendance.objects.select_related('employee').all().order_by('-date', '-id')
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]


@extend_schema_view(
    list=extend_schema(summary="List leave requests", tags=["Leave Requests"]),
    retrieve=extend_schema(summary="Retrieve leave request details", tags=["Leave Requests"]),
    create=extend_schema(summary="Submit a new leave request", tags=["Leave Requests"]),
    update=extend_schema(summary="Update leave request", tags=["Leave Requests"]),
    partial_update=extend_schema(summary="Partially update leave request (e.g. approve/reject)", tags=["Leave Requests"]),
    destroy=extend_schema(summary="Delete leave request", tags=["Leave Requests"]),
)
class LeaveViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Employee Leave Requests.
    Requires authentication.
    """
    queryset = Leave.objects.select_related('employee').all().order_by('-from_date', '-id')
    serializer_class = LeaveSerializer
    permission_classes = [permissions.IsAuthenticated]


# Direct alias for LeaveRequestViewSet
LeaveRequestViewSet = LeaveViewSet


@extend_schema_view(
    list=extend_schema(summary="List payroll records", tags=["Payroll"]),
    retrieve=extend_schema(summary="Retrieve payroll record details", tags=["Payroll"]),
)
class PayrollViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for Employee Payroll records.
    Requires authentication.
    """
    queryset = Payroll.objects.select_related('employee').all().order_by('-year', '-month', '-id')
    serializer_class = PayrollSerializer
    permission_classes = [permissions.IsAuthenticated]

