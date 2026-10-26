import io
import calendar
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


def generate_payroll_pdf(payroll):
    """
    Generate an executive-level, corporate branded salary slip PDF in memory.
    Returns bytes of the generated PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    brand_title_style = ParagraphStyle(
        'BrandTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#142D4E'),
        alignment=TA_LEFT
    )

    brand_sub_style = ParagraphStyle(
        'BrandSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#64748B'),
        alignment=TA_LEFT
    )

    doc_title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#2563EB'),
        alignment=TA_RIGHT
    )

    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#142D4E')
    )

    cell_bold_style = ParagraphStyle(
        'CellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1E293B')
    )

    cell_normal_style = ParagraphStyle(
        'CellNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )

    cell_right_style = ParagraphStyle(
        'CellRight',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155'),
        alignment=TA_RIGHT
    )

    cell_right_bold_style = ParagraphStyle(
        'CellRightBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1E293B'),
        alignment=TA_RIGHT
    )

    net_pay_label_style = ParagraphStyle(
        'NetPayLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#142D4E')
    )

    net_pay_value_style = ParagraphStyle(
        'NetPayValue',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1D4ED8'),
        alignment=TA_RIGHT
    )

    footer_style = ParagraphStyle(
        'FooterNote',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#94A3B8'),
        alignment=TA_CENTER
    )

    month_name = calendar.month_name[payroll.month]
    story = []

    # 1. Header Banner (Brand Left, Title Right)
    brand_p = Paragraph("<b>WorkEase</b> Enterprise", brand_title_style)
    sub_p = Paragraph("Workforce Attendance & Payroll Management System", brand_sub_style)
    doc_title_p = Paragraph(f"SALARY SLIP<br/><font size=9 color='#64748B'>{month_name.upper()} {payroll.year}</font>", doc_title_style)

    header_table = Table(
        [[[brand_p, sub_p], doc_title_p]],
        colWidths=[340, 200]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))

    # Divider Line
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2563EB'), spaceAfter=14))

    # 2. Employee & Period Details (2-Column Grid)
    emp = payroll.employee
    emp_details = [
        [
            Paragraph("<b>Employee ID:</b>", cell_normal_style),
            Paragraph(str(emp.employee_id), cell_bold_style),
            Paragraph("<b>Payslip Ref:</b>", cell_normal_style),
            Paragraph(f"PAY-{payroll.year}{payroll.month:02d}-{payroll.id:04d}", cell_normal_style),
        ],
        [
            Paragraph("<b>Employee Name:</b>", cell_normal_style),
            Paragraph(emp.name, cell_bold_style),
            Paragraph("<b>Pay Period:</b>", cell_normal_style),
            Paragraph(f"{month_name} {payroll.year}", cell_normal_style),
        ],
        [
            Paragraph("<b>Department:</b>", cell_normal_style),
            Paragraph(emp.department or "—", cell_normal_style),
            Paragraph("<b>Salary Type:</b>", cell_normal_style),
            Paragraph(payroll.salary_type, cell_normal_style),
        ],
        [
            Paragraph("<b>Phone:</b>", cell_normal_style),
            Paragraph(emp.phone or "—", cell_normal_style),
            Paragraph("<b>Generated On:</b>", cell_normal_style),
            Paragraph(payroll.generated_at.strftime("%d-%b-%Y") if payroll.generated_at else datetime.now().strftime("%d-%b-%Y"), cell_normal_style),
        ],
    ]

    emp_table = Table(emp_details, colWidths=[100, 170, 100, 170])
    emp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(emp_table)
    story.append(Spacer(1, 14))

    # 3. Earnings & Deductions Table
    story.append(Paragraph("<b>Salary Breakdown</b>", section_header_style))
    story.append(Spacer(1, 6))

    # Rows
    basic_label = "Basic Salary (Monthly)" if payroll.salary_type == 'Monthly' else f"Hourly Earnings ({payroll.total_hours} hrs @ ₹{payroll.hourly_rate})"
    table_data = [
        [
            Paragraph("<b>Earnings Component</b>", cell_bold_style),
            Paragraph("<b>Amount (₹)</b>", cell_right_bold_style),
            Paragraph("<b>Deductions</b>", cell_bold_style),
            Paragraph("<b>Amount (₹)</b>", cell_right_bold_style),
        ],
        [
            Paragraph(basic_label, cell_normal_style),
            Paragraph(f"{payroll.gross_salary - payroll.bonus:,.2f}", cell_right_style),
            Paragraph("Statutory / Standard Deductions", cell_normal_style),
            Paragraph(f"{payroll.deductions:,.2f}", cell_right_style),
        ],
        [
            Paragraph("Performance Bonus / Incentives", cell_normal_style),
            Paragraph(f"{payroll.bonus:,.2f}", cell_right_style),
            Paragraph("—", cell_normal_style),
            Paragraph("—", cell_right_style),
        ],
        [
            Paragraph("<b>Total Gross Earnings</b>", cell_bold_style),
            Paragraph(f"<b>₹{payroll.gross_salary:,.2f}</b>", cell_right_bold_style),
            Paragraph("<b>Total Deductions</b>", cell_bold_style),
            Paragraph(f"<b>₹{payroll.deductions:,.2f}</b>", cell_right_bold_style),
        ],
    ]

    breakdown_table = Table(table_data, colWidths=[180, 90, 180, 90])
    breakdown_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#142D4E')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F1F5F9')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    # Color headers
    for i in range(4):
        table_data[0][i].style.textColor = colors.white
    story.append(breakdown_table)
    story.append(Spacer(1, 14))

    # 4. Net Salary Highlight Box
    net_data = [
        [
            Paragraph("<b>NET TAKE-HOME SALARY:</b>", net_pay_label_style),
            Paragraph(f"₹ {payroll.net_salary:,.2f}", net_pay_value_style),
        ]
    ]
    net_table = Table(net_data, colWidths=[270, 270])
    net_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#EFF6FF')),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#2563EB')),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(net_table)
    story.append(Spacer(1, 24))

    # 5. Signature / Verification Row
    sig_data = [
        [
            Paragraph("Employee Signature: _______________________", cell_normal_style),
            Paragraph("Authorized Signature: _______________________", cell_right_style),
        ]
    ]
    sig_table = Table(sig_data, colWidths=[270, 270])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 20))

    # 6. Disclaimer Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#E2E8F0'), spaceAfter=8))
    story.append(Paragraph(
        "This is an electronically generated salary slip by WorkEase Workforce Management System. No physical signature is required.",
        footer_style
    ))

    # Build PDF
    doc.build(story)
    return buffer.getvalue()
