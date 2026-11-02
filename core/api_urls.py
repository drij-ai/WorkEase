from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from .api_views import (
    EmployeeViewSet,
    AttendanceViewSet,
    LeaveViewSet,
    LeaveRequestViewSet,
    PayrollViewSet,
)

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'attendance', AttendanceViewSet, basename='attendance')
router.register(r'leave-requests', LeaveRequestViewSet, basename='leaverequest')
router.register(r'leaves', LeaveViewSet, basename='leave')
router.register(r'payroll', PayrollViewSet, basename='payroll')

urlpatterns = [
    path('v1/', include(router.urls)),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

