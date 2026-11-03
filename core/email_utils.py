import os
import calendar
import logging
from email.utils import parseaddr
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

from .pdf_utils import generate_payroll_pdf

logger = logging.getLogger(__name__)


def get_admin_emails():
    """
    Returns a list of HR / Admin email addresses to notify for workflow approvals.
    Checks environment variables HR_EMAIL and ADMIN_EMAIL first, then queries active
    staff/superuser accounts with valid emails, and falls back to DEFAULT_FROM_EMAIL.
    """
    admin_emails = []

    # 1. Check environment variables
    env_hr = os.environ.get('HR_EMAIL', '').strip()
    env_admin = os.environ.get('ADMIN_EMAIL', '').strip()
    for e in (env_hr, env_admin):
        if e and '@' in e:
            for item in e.split(','):
                cleaned = item.strip()
                if cleaned and cleaned not in admin_emails:
                    admin_emails.append(cleaned)

    # 2. Query active staff/superusers with email
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        staff_emails = list(
            User.objects.filter(is_active=True, is_staff=True)
            .exclude(email='')
            .values_list('email', flat=True)
        )
        for email in staff_emails:
            cleaned = email.strip()
            if cleaned and cleaned not in admin_emails:
                admin_emails.append(cleaned)
    except Exception as e:
        logger.warning(f"Could not query staff user emails: {e}")

    # 3. Fallback
    if not admin_emails:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'admin@workease.com')
        _, parsed = parseaddr(from_email)
        admin_emails = [parsed if parsed else 'admin@workease.com']

    return admin_emails


def send_leave_submitted_email(leave):
    """
    Send an email notification to HR / Admin when a new leave request is submitted.
    Returns (success: bool, message: str).
    """
    employee = getattr(leave, 'employee', None)
    if not employee:
        return False, "Employee not associated with leave."

    recipients = get_admin_emails()
    if not recipients:
        return False, "No HR / Admin recipient emails found."

    leave_type_name = str(leave.leave_type)
    from_date_str = leave.from_date.strftime('%d %b %Y') if leave.from_date else 'N/A'
    to_date_str = leave.to_date.strftime('%d %b %Y') if leave.to_date else 'N/A'
    days = (leave.to_date - leave.from_date).days + 1 if (leave.from_date and leave.to_date) else 1

    subject = f"[WorkEase HR] New Leave Application: {employee.name} ({leave_type_name})"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; margin: 0; padding: 24px; color: #1E293B; }}
        .card {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
        .header {{ background: #142D4E; padding: 24px; color: #ffffff; text-align: left; }}
        .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; letter-spacing: -0.5px; }}
        .header p {{ margin: 4px 0 0; font-size: 13px; color: #94A3B8; }}
        .content {{ padding: 28px 24px; }}
        .badge {{ display: inline-block; padding: 6px 14px; border-radius: 9999px; font-weight: 600; font-size: 13px; color: #D97706; background-color: #FEF3C7; border: 1px solid #FDE68A; margin-bottom: 20px; }}
        .table-info {{ width: 100%; border-collapse: collapse; margin-top: 16px; margin-bottom: 20px; font-size: 14px; }}
        .table-info td {{ padding: 10px 12px; border-bottom: 1px solid #F1F5F9; }}
        .table-info td.label {{ color: #64748B; font-weight: 500; width: 38%; }}
        .table-info td.val {{ color: #0F172A; font-weight: 600; }}
        .btn {{ display: inline-block; background-color: #142D4E; color: #ffffff !important; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 14px; margin-top: 12px; }}
        .footer {{ padding: 16px 24px; background: #F8FAFC; border-top: 1px solid #E2E8F0; font-size: 12px; color: #94A3B8; text-align: center; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">
          <h1>WorkEase HR Portal</h1>
          <p>New Leave Request Pending Review</p>
        </div>
        <div class="content">
          <p style="font-size: 16px; margin-top: 0;">Hello <strong>HR Team</strong>,</p>
          <p style="color: #475569; font-size: 14px; line-height: 1.5;">
            An employee has submitted a new leave application awaiting your approval.
          </p>

          <div class="badge">&#9203; Action Required: Pending Review</div>

          <table class="table-info">
            <tr>
              <td class="label">Employee</td>
              <td class="val">{employee.name} ({employee.employee_id})</td>
            </tr>
            <tr>
              <td class="label">Department</td>
              <td class="val">{employee.department or 'General'}</td>
            </tr>
            <tr>
              <td class="label">Leave Type</td>
              <td class="val">{leave_type_name}</td>
            </tr>
            <tr>
              <td class="label">Duration</td>
              <td class="val">{from_date_str} to {to_date_str} ({days} day(s))</td>
            </tr>
            <tr>
              <td class="label">Reason</td>
              <td class="val">{leave.reason or 'None provided'}</td>
            </tr>
          </table>

          <p style="text-align: center; margin-top: 24px;">
            <a href="/admin-dashboard/leave/" class="btn" style="color: #ffffff;">Review in Leave Management</a>
          </p>
        </div>
        <div class="footer">
          &copy; WorkEase HR Management &bull; Automated HR Notification
        </div>
      </div>
    </body>
    </html>
    """

    plain_content = strip_tags(html_content)

    try:
        from_email = settings.DEFAULT_FROM_EMAIL
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_content,
            from_email=from_email,
            to=recipients
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        logger.info(f"Leave submitted alert sent to {recipients}")
        return True, f"Notification email sent to {', '.join(recipients)}."
    except Exception as e:
        logger.error(f"Failed to send leave submitted email: {e}")
        return False, f"Could not send email: {str(e)}"


def send_leave_status_email(leave):
    """
    Send an email notification to the employee when their leave request
    is approved or rejected.
    Returns (success: bool, message: str).
    """
    employee = getattr(leave, 'employee', None)
    if not employee:
        return False, "Employee not associated with leave."

    to_email = employee.contact_email
    if not to_email:
        logger.info(f"Leave email skipped: No email found for {employee.name}")
        return False, f"No email address found for {employee.name}."

    status_str = str(leave.status).capitalize()
    status_color = "#10B981" if leave.status.lower() == 'approved' else "#EF4444"
    status_badge_bg = "#ECFDF5" if leave.status.lower() == 'approved' else "#FEF2F2"
    status_icon = "&#10004;" if leave.status.lower() == 'approved' else "&#10008;"

    leave_type_name = str(leave.leave_type)
    from_date_str = leave.from_date.strftime('%d %b %Y') if leave.from_date else 'N/A'
    to_date_str = leave.to_date.strftime('%d %b %Y') if leave.to_date else 'N/A'
    days = (leave.to_date - leave.from_date).days + 1 if (leave.from_date and leave.to_date) else 1

    subject = f"[WorkEase] Leave Request {status_str}: {leave_type_name}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; margin: 0; padding: 24px; color: #1E293B; }}
        .card {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
        .header {{ background: #142D4E; padding: 24px; color: #ffffff; text-align: left; }}
        .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; letter-spacing: -0.5px; }}
        .header p {{ margin: 4px 0 0; font-size: 13px; color: #94A3B8; }}
        .content {{ padding: 28px 24px; }}
        .status-badge {{ display: inline-block; padding: 6px 14px; border-radius: 9999px; font-weight: 600; font-size: 13px; color: {status_color}; background-color: {status_badge_bg}; border: 1px solid {status_color}33; margin-bottom: 20px; }}
        .table-info {{ width: 100%; border-collapse: collapse; margin-top: 16px; margin-bottom: 20px; font-size: 14px; }}
        .table-info td {{ padding: 10px 12px; border-bottom: 1px solid #F1F5F9; }}
        .table-info td.label {{ color: #64748B; font-weight: 500; width: 38%; }}
        .table-info td.val {{ color: #0F172A; font-weight: 600; }}
        .footer {{ padding: 16px 24px; background: #F8FAFC; border-top: 1px solid #E2E8F0; font-size: 12px; color: #94A3B8; text-align: center; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">
          <h1>WorkEase HR Portal</h1>
          <p>Leave Application Status Update</p>
        </div>
        <div class="content">
          <p style="font-size: 16px; margin-top: 0;">Dear <strong>{employee.name}</strong>,</p>
          <p style="color: #475569; font-size: 14px; line-height: 1.5;">
            Your leave application submitted for <strong>{leave_type_name}</strong> has been updated by management.
          </p>

          <div class="status-badge">
            {status_icon} Status: {status_str}
          </div>

          <table class="table-info">
            <tr>
              <td class="label">Leave Type</td>
              <td class="val">{leave_type_name}</td>
            </tr>
            <tr>
              <td class="label">Duration</td>
              <td class="val">{from_date_str} to {to_date_str}</td>
            </tr>
            <tr>
              <td class="label">Total Days</td>
              <td class="val">{days} day(s)</td>
            </tr>
            <tr>
              <td class="label">Reason / Notes</td>
              <td class="val">{leave.reason or 'None provided'}</td>
            </tr>
          </table>

          <p style="color: #64748B; font-size: 13px; line-height: 1.5; margin-bottom: 0;">
            If you have questions regarding this decision, please reach out to your HR administrator.
          </p>
        </div>
        <div class="footer">
          &copy; WorkEase HR Management &bull; This is an automated notification.
        </div>
      </div>
    </body>
    </html>
    """

    plain_content = strip_tags(html_content)

    try:
        from_email = settings.DEFAULT_FROM_EMAIL
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_content,
            from_email=from_email,
            to=[to_email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        logger.info(f"Leave status email sent successfully to {to_email}")
        return True, f"Notification email sent to {to_email}."
    except Exception as e:
        logger.error(f"Failed to send leave status email to {to_email}: {e}")
        return False, f"Could not send email: {str(e)}"


def send_regularization_submitted_email(regularization):
    """
    Send an email notification to HR / Admin when an attendance regularization
    request is submitted by an employee.
    Returns (success: bool, message: str).
    """
    employee = getattr(regularization, 'employee', None)
    if not employee:
        return False, "Employee not associated with regularization request."

    recipients = get_admin_emails()
    if not recipients:
        return False, "No HR / Admin recipient emails found."

    date_str = regularization.date.strftime('%d %b %Y') if regularization.date else 'N/A'
    in_str = regularization.requested_check_in.strftime('%H:%M') if regularization.requested_check_in else 'N/A'
    out_str = regularization.requested_check_out.strftime('%H:%M') if regularization.requested_check_out else 'N/A'

    subject = f"[WorkEase HR] Attendance Regularization Request: {employee.name} ({date_str})"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; margin: 0; padding: 24px; color: #1E293B; }}
        .card {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
        .header {{ background: #142D4E; padding: 24px; color: #ffffff; text-align: left; }}
        .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; }}
        .header p {{ margin: 4px 0 0; font-size: 13px; color: #94A3B8; }}
        .content {{ padding: 28px 24px; }}
        .badge {{ display: inline-block; padding: 6px 14px; border-radius: 9999px; font-weight: 600; font-size: 13px; color: #D97706; background-color: #FEF3C7; border: 1px solid #FDE68A; margin-bottom: 20px; }}
        .table-info {{ width: 100%; border-collapse: collapse; margin-top: 16px; margin-bottom: 20px; font-size: 14px; }}
        .table-info td {{ padding: 10px 12px; border-bottom: 1px solid #F1F5F9; }}
        .table-info td.label {{ color: #64748B; font-weight: 500; width: 40%; }}
        .table-info td.val {{ color: #0F172A; font-weight: 600; }}
        .btn {{ display: inline-block; background-color: #142D4E; color: #ffffff !important; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 14px; margin-top: 12px; }}
        .footer {{ padding: 16px 24px; background: #F8FAFC; border-top: 1px solid #E2E8F0; font-size: 12px; color: #94A3B8; text-align: center; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">
          <h1>WorkEase Attendance</h1>
          <p>Missed Punch Regularization Request</p>
        </div>
        <div class="content">
          <p style="font-size: 16px; margin-top: 0;">Hello <strong>HR Team</strong>,</p>
          <p style="color: #475569; font-size: 14px; line-height: 1.5;">
            An attendance regularization request has been submitted for missed punch correction.
          </p>

          <div class="badge">&#9203; Action Required: Pending Approval</div>

          <table class="table-info">
            <tr>
              <td class="label">Employee</td>
              <td class="val">{employee.name} ({employee.employee_id})</td>
            </tr>
            <tr>
              <td class="label">Date</td>
              <td class="val">{date_str}</td>
            </tr>
            <tr>
              <td class="label">Requested Check-In</td>
              <td class="val">{in_str}</td>
            </tr>
            <tr>
              <td class="label">Requested Check-Out</td>
              <td class="val">{out_str}</td>
            </tr>
            <tr>
              <td class="label">Reason / Explanation</td>
              <td class="val">{regularization.reason or 'None provided'}</td>
            </tr>
          </table>

          <p style="text-align: center; margin-top: 24px;">
            <a href="/admin-dashboard/attendance/regularizations/" class="btn" style="color: #ffffff;">Review Regularizations</a>
          </p>
        </div>
        <div class="footer">
          &copy; WorkEase HR Management &bull; Automated HR Notification
        </div>
      </div>
    </body>
    </html>
    """

    plain_content = strip_tags(html_content)

    try:
        from_email = settings.DEFAULT_FROM_EMAIL
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_content,
            from_email=from_email,
            to=recipients
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        logger.info(f"Regularization request alert sent to {recipients}")
        return True, f"Notification email sent to {', '.join(recipients)}."
    except Exception as e:
        logger.error(f"Failed to send regularization submitted email: {e}")
        return False, f"Could not send email: {str(e)}"


def send_regularization_status_email(regularization):
    """
    Send an email notification to the employee when their attendance
    regularization request is approved or rejected by management.
    Returns (success: bool, message: str).
    """
    employee = getattr(regularization, 'employee', None)
    if not employee:
        return False, "Employee not associated with regularization request."

    to_email = employee.contact_email
    if not to_email:
        logger.info(f"Regularization status email skipped: No email found for {employee.name}")
        return False, f"No email address found for {employee.name}."

    status_str = str(regularization.status).capitalize()
    status_color = "#10B981" if regularization.status.lower() == 'approved' else "#EF4444"
    status_badge_bg = "#ECFDF5" if regularization.status.lower() == 'approved' else "#FEF2F2"
    status_icon = "&#10004;" if regularization.status.lower() == 'approved' else "&#10008;"

    date_str = regularization.date.strftime('%d %b %Y') if regularization.date else 'N/A'
    in_str = regularization.requested_check_in.strftime('%H:%M') if regularization.requested_check_in else 'N/A'
    out_str = regularization.requested_check_out.strftime('%H:%M') if regularization.requested_check_out else 'N/A'
    admin_remarks = regularization.admin_remarks or 'None provided'

    subject = f"[WorkEase] Attendance Regularization {status_str}: {date_str}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; margin: 0; padding: 24px; color: #1E293B; }}
        .card {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
        .header {{ background: #142D4E; padding: 24px; color: #ffffff; text-align: left; }}
        .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; }}
        .header p {{ margin: 4px 0 0; font-size: 13px; color: #94A3B8; }}
        .content {{ padding: 28px 24px; }}
        .status-badge {{ display: inline-block; padding: 6px 14px; border-radius: 9999px; font-weight: 600; font-size: 13px; color: {status_color}; background-color: {status_badge_bg}; border: 1px solid {status_color}33; margin-bottom: 20px; }}
        .table-info {{ width: 100%; border-collapse: collapse; margin-top: 16px; margin-bottom: 20px; font-size: 14px; }}
        .table-info td {{ padding: 10px 12px; border-bottom: 1px solid #F1F5F9; }}
        .table-info td.label {{ color: #64748B; font-weight: 500; width: 40%; }}
        .table-info td.val {{ color: #0F172A; font-weight: 600; }}
        .footer {{ padding: 16px 24px; background: #F8FAFC; border-top: 1px solid #E2E8F0; font-size: 12px; color: #94A3B8; text-align: center; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">
          <h1>WorkEase Attendance</h1>
          <p>Regularization Request Status Update</p>
        </div>
        <div class="content">
          <p style="font-size: 16px; margin-top: 0;">Dear <strong>{employee.name}</strong>,</p>
          <p style="color: #475569; font-size: 14px; line-height: 1.5;">
            Your attendance regularization request for <strong>{date_str}</strong> has been reviewed.
          </p>

          <div class="status-badge">
            {status_icon} Status: {status_str}
          </div>

          <table class="table-info">
            <tr>
              <td class="label">Date</td>
              <td class="val">{date_str}</td>
            </tr>
            <tr>
              <td class="label">Requested Check-In</td>
              <td class="val">{in_str}</td>
            </tr>
            <tr>
              <td class="label">Requested Check-Out</td>
              <td class="val">{out_str}</td>
            </tr>
            <tr>
              <td class="label">Admin Remarks</td>
              <td class="val">{admin_remarks}</td>
            </tr>
          </table>

          <p style="color: #64748B; font-size: 13px; line-height: 1.5; margin-bottom: 0;">
            {'Your attendance log and working hours have been updated accordingly.' if regularization.status.lower() == 'approved' else 'Please contact HR if you require further clarification.'}
          </p>
        </div>
        <div class="footer">
          &copy; WorkEase Attendance Management &bull; Automated notification
        </div>
      </div>
    </body>
    </html>
    """

    plain_content = strip_tags(html_content)

    try:
        from_email = settings.DEFAULT_FROM_EMAIL
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_content,
            from_email=from_email,
            to=[to_email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        logger.info(f"Regularization status email sent successfully to {to_email}")
        return True, f"Notification email sent to {to_email}."
    except Exception as e:
        logger.error(f"Failed to send regularization status email to {to_email}: {e}")
        return False, f"Could not send email: {str(e)}"


def send_payslip_email(payroll, pdf_bytes=None):
    """
    Send monthly salary slip email with attached PDF to the employee.
    Returns (success: bool, message: str).
    """
    employee = getattr(payroll, 'employee', None)
    if not employee:
        return False, "Employee not associated with payroll record."

    to_email = employee.contact_email
    if not to_email:
        logger.info(f"Payslip email skipped: No email found for {employee.name}")
        return False, f"No email address found for {employee.name}."

    if not pdf_bytes:
        try:
            pdf_bytes = generate_payroll_pdf(payroll)
        except Exception as e:
            logger.error(f"Failed to generate PDF for payroll {payroll.id}: {e}")
            return False, f"PDF generation error: {str(e)}"

    month_name = calendar.month_name[payroll.month]
    year = payroll.year
    subject = f"[WorkEase] Salary Slip - {month_name} {year} - {employee.name}"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; margin: 0; padding: 24px; color: #1E293B; }}
        .card {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
        .header {{ background: #142D4E; padding: 24px; color: #ffffff; text-align: left; }}
        .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; }}
        .header p {{ margin: 4px 0 0; font-size: 13px; color: #94A3B8; }}
        .content {{ padding: 28px 24px; }}
        .highlight-box {{ background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; padding: 16px; margin: 20px 0; text-align: center; }}
        .highlight-box .amount {{ font-size: 26px; font-weight: 800; color: #166534; margin: 4px 0; }}
        .highlight-box .label {{ font-size: 12px; text-transform: uppercase; color: #15803D; font-weight: 600; letter-spacing: 0.5px; }}
        .table-info {{ width: 100%; border-collapse: collapse; margin-top: 16px; margin-bottom: 20px; font-size: 14px; }}
        .table-info td {{ padding: 10px 12px; border-bottom: 1px solid #F1F5F9; }}
        .table-info td.label {{ color: #64748B; font-weight: 500; width: 45%; }}
        .table-info td.val {{ color: #0F172A; font-weight: 600; text-align: right; }}
        .footer {{ padding: 16px 24px; background: #F8FAFC; border-top: 1px solid #E2E8F0; font-size: 12px; color: #94A3B8; text-align: center; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">
          <h1>WorkEase Payroll</h1>
          <p>Monthly Salary Statement</p>
        </div>
        <div class="content">
          <p style="font-size: 16px; margin-top: 0;">Dear <strong>{employee.name}</strong>,</p>
          <p style="color: #475569; font-size: 14px; line-height: 1.5;">
            Your salary slip for <strong>{month_name} {year}</strong> has been generated and is attached to this email as a PDF document.
          </p>

          <div class="highlight-box">
            <div class="label">Net Disbursed Salary</div>
            <div class="amount">&#8377;{payroll.net_salary:,.2f}</div>
          </div>

          <table class="table-info">
            <tr>
              <td class="label">Employee ID</td>
              <td class="val">{employee.employee_id}</td>
            </tr>
            <tr>
              <td class="label">Department</td>
              <td class="val">{employee.department or 'General'}</td>
            </tr>
            <tr>
              <td class="label">Basic / Gross Salary</td>
              <td class="val">&#8377;{payroll.gross_salary:,.2f}</td>
            </tr>
            <tr>
              <td class="label">Bonus / Allowances (+)</td>
              <td class="val">&#8377;{payroll.bonus:,.2f}</td>
            </tr>
            <tr>
              <td class="label">Deductions (-)</td>
              <td class="val">&#8377;{payroll.deductions:,.2f}</td>
            </tr>
          </table>

          <p style="color: #64748B; font-size: 13px; line-height: 1.5; margin-bottom: 0;">
            Please download and review the attached PDF salary slip for your records.
          </p>
        </div>
        <div class="footer">
          &copy; WorkEase Payroll &bull; Confidential Salary Statement
        </div>
      </div>
    </body>
    </html>
    """

    plain_content = strip_tags(html_content)
    filename = f"payslip_{employee.employee_id}_{year}_{payroll.month:02d}.pdf"

    try:
        from_email = settings.DEFAULT_FROM_EMAIL
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_content,
            from_email=from_email,
            to=[to_email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.attach(filename, pdf_bytes, 'application/pdf')
        msg.send(fail_silently=False)
        logger.info(f"Payslip email sent to {to_email} with attachment {filename}")
        return True, f"Payslip PDF sent to {to_email}."
    except Exception as e:
        logger.error(f"Failed to send payslip email to {to_email}: {e}")
        return False, f"Could not send payslip email: {str(e)}"
