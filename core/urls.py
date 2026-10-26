from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/employees/', views.employee_list, name='employee_list'),
    path('admin-dashboard/users/', views.user_management, name='user_management'),
    path('admin-dashboard/users/add/', views.user_add, name='user_add'),
    path('profile/', views.employee_profile, name='employee_profile'),
    
    path(
    'notifications/',
    views.employee_notifications,
    name='employee_notifications'
),
path(
    'notifications/<int:notification_id>/read/',
    views.mark_notification_read,
    name='mark_notification_read'
),

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
        'admin-dashboard/payroll/<int:payroll_id>/pdf/',
        views.payroll_pdf_download,
        name='payroll_pdf'
    ),
    path(
        'admin-dashboard/payroll/<int:payroll_id>/send-email/',
        views.payroll_send_email,
        name='payroll_send_email'
    ),
    path(
        'my-payroll/<int:payroll_id>/pdf/',
        views.payroll_pdf_download,
        name='employee_payroll_pdf'
    ),
    path(
        'admin-dashboard/holidays/',
        views.holiday_list,
        name='holiday_list'
    ),
    path(
        'admin-dashboard/holidays/add/',
        views.holiday_add,
        name='holiday_add'
    ),
    path(
        'admin-dashboard/holidays/<int:holiday_id>/edit/',
        views.holiday_edit,
        name='holiday_edit'
    ),
    path(
        'admin-dashboard/holidays/<int:holiday_id>/delete/',
        views.holiday_delete,
        name='holiday_delete'
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
    path('admin-dashboard/run-migrations/', views.run_migrations_view, name='run_migrations'),
    path('leave/', views.leave_apply, name='leave_apply'),
    path('attendance/', views.attendance, name='attendance'),
]

