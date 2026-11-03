from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Employee, Attendance, Leave, Payroll, BiometricCredential, AttendanceRegularization
from .serializers import (
    EmployeeSerializer,
    AttendanceSerializer,
    LeaveSerializer,
    LeaveRequestSerializer,
    PayrollSerializer,
    BiometricCredentialSerializer,
    AttendanceRegularizationSerializer,
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

    def perform_destroy(self, instance):
        instance.soft_delete()


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



@extend_schema_view(
    list=extend_schema(summary="List registered biometric credentials", tags=["Biometrics"]),
    retrieve=extend_schema(summary="Retrieve biometric credential details", tags=["Biometrics"]),
)
class BiometricCredentialViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for employee WebAuthn biometric credentials.
    Requires authentication.
    """
    queryset = BiometricCredential.objects.select_related('employee').all().order_by('-created_at')
    serializer_class = BiometricCredentialSerializer
    permission_classes = [permissions.IsAuthenticated]


@extend_schema_view(
    list=extend_schema(summary="List attendance regularization requests", tags=["Attendance Regularization"]),
    retrieve=extend_schema(summary="Retrieve attendance regularization request", tags=["Attendance Regularization"]),
    create=extend_schema(summary="Submit attendance regularization request", tags=["Attendance Regularization"]),
    update=extend_schema(summary="Update regularization request", tags=["Attendance Regularization"]),
    partial_update=extend_schema(summary="Partially update regularization request", tags=["Attendance Regularization"]),
    destroy=extend_schema(summary="Delete regularization request", tags=["Attendance Regularization"]),
)
class AttendanceRegularizationViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Employee Attendance Regularization (Missed Punch Correction) requests.
    Requires authentication.
    """
    queryset = AttendanceRegularization.objects.select_related('employee', 'attendance').all().order_by('-date', '-created_at')
    serializer_class = AttendanceRegularizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        employee = serializer.validated_data.get('employee')
        if not employee and hasattr(self.request.user, 'employee'):
            employee = self.request.user.employee
            serializer.validated_data['employee'] = employee
        reg_date = serializer.validated_data.get('date')
        att = Attendance.objects.filter(employee=employee, date=reg_date).first()
        serializer.save(employee=employee, attendance=att)

    @extend_schema(
        summary="Approve regularization request",
        description="Approves a pending attendance regularization request, automatically creating or updating the attendance record and recalculating working hours.",
        tags=["Attendance Regularization"]
    )
    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        regularization = self.get_object()
        admin_remarks = request.data.get('admin_remarks', '')
        regularization.approve(admin_remarks=admin_remarks)
        return Response(self.get_serializer(regularization).data)

    @extend_schema(
        summary="Reject regularization request",
        description="Rejects a pending attendance regularization request.",
        tags=["Attendance Regularization"]
    )
    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        regularization = self.get_object()
        admin_remarks = request.data.get('admin_remarks', '')
        regularization.reject(admin_remarks=admin_remarks)
        return Response(self.get_serializer(regularization).data)
