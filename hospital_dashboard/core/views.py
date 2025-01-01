from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Count
from django.db.models.functions import TruncMonth

from .forms import UserRegisterForm, UserLoginForm, AdmissionRecordEntry, PatientRecordEntry, UserEditForm
from .models import Admission, Patient, Account

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'User registered successfully!'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = UserRegisterForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = UserLoginForm() 
    return render(request, 'login.html', {'form': form})

@login_required(login_url="/login")
def dashboard(request):
    context={}

    user_id = request.user.id
    user = Account.objects.get(id=user_id)
    role = user.role    

    if role == 'Clinician':
        admissions = Admission.objects.filter(clinician__id=user_id)
    else:
        admissions = Admission.objects.all()

    admissions_by_sex = admissions.values('patient__sex').annotate(count=Count('id')).order_by('patient__sex')
    context['sex_labels'] = [entry['patient__sex'] for entry in admissions_by_sex]
    context['sex_data'] = [entry['count'] for entry in admissions_by_sex]

    readmissions_count = admissions.filter(is_readmission=True).count()
    non_readmissions_count = admissions.filter(is_readmission=False).count()
    context['readmission_labels'] = ['Readmissions', 'Non-Readmissions']
    context['readmission_data'] = [readmissions_count, non_readmissions_count]

    admissions.filter().annotate(month=TruncMonth('date')).values('month').annotate(count=Count('id')).order_by('month')

    context['user'] = user
    return render(request, 'dashboard.html', context)


@login_required(login_url="/login")
def admin_dashboard(request):
    if request.method == 'POST':
        form = PatientRecordEntry(request.POST)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f"Patient record created for {patient.name}!")
            return redirect('admin_dashboard')
    else:
        form = PatientRecordEntry()
    return render(request, 'adminDashboard.html', {'form': form})

@login_required(login_url="/login")
def clinician_dashboard(request):
    if request.method == 'POST':
        form = AdmissionRecordEntry(request.POST)
        if form.is_valid():
            admission = form.save()
            messages.success(request, f"Admission record created for {admission.patient}!")
            return redirect('clinician_dashboard')
    else:
        form = AdmissionRecordEntry()
    return render(request, 'clinicianDashboard.html', {'form': form})



@login_required(login_url="/login")
def sign_out(request):
    request.session.flush()
    return redirect('login')

@login_required(login_url="/login")
def patient_list(request):
    patients = Patient.objects.all()  # Retrieve all patients
    return render(request, 'patient_list.html', {'patients': patients})

@login_required(login_url="/login")
def user_list(request):
    accounts = Account.objects.all()
    return render(request, 'user_list.html', {'accounts': accounts})

@login_required(login_url="/login")
def admissions(request):
    context={}
    user_id = request.user.id
    context['admissions'] = Admission.objects.filter(clinician=user_id)  # Retrieve all patients
    return render(request, 'admissions.html', context)

def add_patient(request):
    if request.method == 'POST':
        form = PatientRecordEntry(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = PatientRecordEntry()
    return render(request, 'partials/add_patient_form.html', {'form': form})

def add_admission(request):
    if request.method == 'POST':
        form = AdmissionRecordEntry(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = AdmissionRecordEntry()
    return render(request, 'partials/add_admission_form.html', {'form': form})

def add_user(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'User registered successfully!'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = UserRegisterForm()
    return render(request, 'partials/add_user_form.html', {'form': form})

@login_required(login_url="/login")
def edit_user(request, pk):
    try:
        acc = Account.objects.get(pk=pk)
    except Account.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found.'}, status=404)

    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=acc)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'User updated successfully!'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors.get_json_data()}, status=400)
    else:
        form = UserEditForm(instance=acc)
    return render(request, 'partials/edit_user_form.html', {'form': form})