import calendar
import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

from .pdf_utils import generate_payroll_pdf

logger = logging.getLogger(__name__)


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
