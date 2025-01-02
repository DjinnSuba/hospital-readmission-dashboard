from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Account, Patient, Admission

class UserRegisterForm(UserCreationForm):
    role = forms.ChoiceField(choices=Account.ROLE_CHOICES, required=True)

    class Meta:
        model = Account
        fields = ['username', 'email', 'password1', 'password2', 'role']

class UserLoginForm(AuthenticationForm):
    class Meta:
        model = Account
        fields = ['username', 'password']

class PatientRecordEntry(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['name', 'sex', 'birthdate', 'address', 'contact_number', 'email']
        widgets = {
            'birthdate': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class AdmissionRecordEntry(forms.ModelForm):
    class Meta:
        model = Admission
        fields = ['clinician', 'patient', 'is_readmission', 'diagnosis', 'treatment', 'date', 'remarks']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'diagnosis': forms.Textarea(attrs={'rows': 3}),
            'treatment': forms.Textarea(attrs={'rows': 3}),
            'remarks': forms.Textarea(attrs={'rows': 2}),
        }
class UserEditForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['username', 'email', 'role']

class PatientEditForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['name', 'sex', 'birthdate', 'address', 'contact_number', 'email']

class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(label="Upload CSV File")
