from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/employees/', views.employee_list, name='employee_list'),
    path('admin-dashboard/users/', views.user_management, name='user_management'),
    path('admin-dashboard/users/add/', views.user_add, name='user_add'),
    
    
path(
    'admin-dashboard/users/<int:user_id>/toggle-status/',
    views.toggle_user_status,
    name='toggle_user_status'
),


path(
    'admin-dashboard/users/<int:user_id>/reset-password/',
    views.reset_user_password,
    name='reset_user_password'
),


    path(
    'admin-dashboard/attendance/',
    views.attendance_list,
    name='attendance_list'
),

    path(
    'admin-dashboard/leave/',
    views.admin_leave_list,
    name='admin_leave_list'
),

    path(
    'admin-dashboard/payroll/',
    views.admin_payroll_list,
    name='admin_payroll_list'
),

    path(
    'admin-dashboard/payroll/add/',
    views.payroll_add,
    name='payroll_add'
),

    path(
    'admin-dashboard/payroll/<int:payroll_id>/edit/',
    views.payroll_edit,
    name='payroll_edit'
),

    path(
    'admin-dashboard/payroll/<int:payroll_id>/delete/',
    views.payroll_delete,
    name='payroll_delete'
),

   path(
    'admin-dashboard/leave/<int:leave_id>/<str:status>/',
    views.leave_update_status,
    name='leave_update_status'
),

    path(
    'admin-dashboard/employees/<int:employee_id>/delete/',
    views.employee_delete,
    name='employee_delete'
),
    path(
    'admin-dashboard/employees/<int:employee_id>/edit/',
    views.employee_edit,
    name='employee_edit'
),
    path(
    'admin-dashboard/work-locations/',
    views.work_location_list,
    name='work_location_list'
),

path(
    'admin-dashboard/work-locations/add/',
    views.work_location_add,
    name='work_location_add'
),

path(
    'admin-dashboard/work-locations/<int:location_id>/edit/',
    views.work_location_edit,
    name='work_location_edit'
),

path(
    'admin-dashboard/work-locations/<int:location_id>/delete/',
    views.work_location_delete,
    name='work_location_delete'
),
    
    path('admin-dashboard/employees/add/',views.employee_add, name='employee_add'),
    path('leave/', views.leave_apply, name='leave_apply'),
    path('attendance/', views.attendance, name='attendance'),
]
