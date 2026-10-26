from django import forms
from .models import Employee, WorkLocation, Payroll, Holiday


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'employee_id',
            'name',
            'email',
            'phone',
            'department',
            'joining_date',
            'basic_salary',
            'hourly_rate',
            'salary_type',
        ]

        widgets = {
            'employee_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Employee ID'
            }),

            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Employee Name'
            }),

            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'official@company.com'
            }),

            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone Number'
            }),

            'department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Department'
            }),

            'joining_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),

            'basic_salary': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Basic Salary'
            }),

            'hourly_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Hourly Rate'
            }),

            'salary_type': forms.Select(attrs={
                'class': 'form-select'
            }),
        }


class WorkLocationForm(forms.ModelForm):
    class Meta:
        model = WorkLocation
        fields = [
            'name',
            'latitude',
            'longitude',
            'allowed_radius',
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Office / Location Name'
            }),

            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Example: 22.3072',
                'step': 'any'
            }),

            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Example: 73.1812',
                'step': 'any'
            }),

            'allowed_radius': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Example: 100'
            }),
        }


class PayrollForm(forms.ModelForm):
    class Meta:
        model = Payroll
        fields = [
            'employee',
            'month',
            'year',
            'salary_type',
            'total_hours',
            'hourly_rate',
            'basic_salary',
            'bonus',
            'deductions',
        ]

        widgets = {
            'employee': forms.Select(attrs={
                'class': 'form-select'
            }),
            'month': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Month (1-12)',
                'min': 1,
                'max': 12
            }),
            'year': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Year'
            }),
            'salary_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'total_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'hourly_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'basic_salary': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'bonus': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'deductions': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
        }


class HolidayForm(forms.ModelForm):
    class Meta:
        model = Holiday
        fields = [
            'title',
            'date',
            'holiday_type',
            'description',
        ]

        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Diwali, Eid, Christmas, Independence Day'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'holiday_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional details or notes about the holiday'
            }),
        }