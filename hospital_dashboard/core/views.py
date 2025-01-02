import csv
from datetime import date, datetime
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Count
from django.db.models.functions import TruncMonth

from .forms import UserRegisterForm, UserLoginForm, AdmissionRecordEntry, PatientRecordEntry, UserEditForm, PatientAdmissionRecordEntry
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

def download_data(user, admissions):
    filename = user.name.replace(' ', '_') + '-' + str(date.today())
    
    response = HttpResponse(content_type='text/csv')  
    response['Content-Disposition'] = 'attachment; filename=' + filename + '.csv'  
    writer = csv.writer(response)  

    writer.writerow([
        'Patient Name', 
        'Patient Email', 
        'Clinician Name', 
        'Clinician Email', 
        'Is Readmission', 
        'Diagnosis', 
        'Treatment', 
        'Date', 
        'Remarks'
    ])

    # Write data rows
    for admission in admissions:
        writer.writerow([
            admission.patient.name,          # Patient name
            admission.patient.email,         # Patient email
            admission.clinician.name,        # Clinician name
            admission.clinician.email,       # Clinician email
            'Yes' if admission.is_readmission else 'No',  # Is readmission
            admission.diagnosis,             # Diagnosis
            admission.treatment,             # Treatment
            admission.date,                  # Date
            admission.remarks or ''          # Remarks (handles null)
        ])

    return response  

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

    before = request.GET.get('before')
    after = request.GET.get('after')

    if before:
        try:
            # Convert to datetime object for validation
            before_date = datetime.strptime(before, "%Y-%m-%d").date()
            admissions = admissions.filter(date__lte=before_date)
        except ValueError:
            # Handle invalid date format
            before_date = None

    # Validate and filter by 'after' date
    if after:
        try:
            after_date = datetime.strptime(after, "%Y-%m-%d").date()
            admissions = admissions.filter(date__gte=after_date)
        except ValueError:
            after_date = None

    context['before'] = before
    context['after'] = after  

    action = request.GET.get('action')
    if action == "download":
        return download_data(user, admissions)

    admissions_by_sex = admissions.values('patient__sex').annotate(count=Count('id')).order_by('patient__sex')
    context['sex_labels'] = [entry['patient__sex'] for entry in admissions_by_sex]
    context['sex_data'] = [entry['count'] for entry in admissions_by_sex]

    readmissions_count = admissions.filter(is_readmission=True).count()
    non_readmissions_count = admissions.filter(is_readmission=False).count()
    context['readmission_labels'] = ['Readmissions', 'Non-Readmissions']
    context['readmission_data'] = [readmissions_count, non_readmissions_count]

    common_diseases = admissions.values('diagnosis').annotate(count=Count('id')).order_by('-count')[:10]
    context['commonDiseases_labels'] = [entry['diagnosis'] for entry in common_diseases]
    context['commonDiseases_data'] = [entry['count'] for entry in common_diseases]

    common_treatments = admissions.values('treatment').annotate(count=Count('id')).order_by('-count')[:10]
    context['commonTreatments_labels'] = [entry['treatment'] for entry in common_treatments]
    context['commonTreatments_data'] = [entry['count'] for entry in common_treatments]


    # Monthly admissions for all admissions
    admissions_by_month = (
        admissions.annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    # Monthly admissions for readmissions only
    readmissions_by_month = (
        admissions.filter(is_readmission=True)
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    # Prepare data for the chart
    months = [entry['month'].strftime('%B') for entry in admissions_by_month]
    all_admissions_data = [entry['count'] for entry in admissions_by_month]
    readmissions_data = [
        next((entry['count'] for entry in readmissions_by_month if entry['month'] == month), 0)
        for month in [entry['month'] for entry in admissions_by_month]
    ]

    context['line_chart_labels'] = months
    context['all_admissions_data'] = all_admissions_data
    context['readmissions_data'] = readmissions_data

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

    admissions = Admission.objects.filter(clinician=user_id)

    if 'name' not in request.GET:
        name = ''
    else:
        name = request.GET.get('name')
        admissions = admissions.filter(patient__name__icontains=name)

    if 'diagnosis' not in request.GET:
        diagnosis = ''
    else:
        diagnosis = request.GET.get('diagnosis')
        admissions = admissions.filter(diagnosis__icontains=diagnosis)

    before = request.GET.get('before')
    #admissions = admissions.filter(date__lte=before)

    after = request.GET.get('after')
    #admissions = admissions.filter(date__gte=after)

    if before:
        try:
            # Convert to datetime object for validation
            before_date = datetime.strptime(before, "%Y-%m-%d").date()
            admissions = admissions.filter(date__lte=before_date)
        except ValueError:
            # Handle invalid date format
            before_date = None

    # Validate and filter by 'after' date
    if after:
        try:
            after_date = datetime.strptime(after, "%Y-%m-%d").date()
            admissions = admissions.filter(date__gte=after_date)
        except ValueError:
            after_date = None

    context['name'] = name
    context['diagnosis'] = diagnosis
    context['before'] = before
    context['after'] = after        
    context['admissions'] = admissions.order_by('-date')  # Retrieve all patients
    return render(request, 'admissions.html', context)

@login_required(login_url="/login")
def admission_patients(request):
    context={}
    user_id = request.user.id

    patients = Patient.objects.all()

    if 'name' not in request.GET:
        name = ''
    else:
        name = request.GET.get('name')
        patients = patients.filter(name__icontains=name)

    if 'diagnosis' not in request.GET:
        diagnosis = ''
    else:
        diagnosis = request.GET.get('diagnosis')
        admissions = Admission.objects.filter(diagnosis__icontains=diagnosis)
        patients = patients.filter(admissions__in=admissions).distinct()

    context['name'] = name
    context['diagnosis'] = diagnosis

    context['patients'] = patients
    return render(request, 'admissions_patients.html', context)

@login_required(login_url="/login")
def admit_patient(request, id):
    context={}

    admissions = Admission.objects.filter(patient=id)

    if 'diagnosis' not in request.GET:
        diagnosis = ''
    else:
        diagnosis = request.GET.get('diagnosis')
        admissions = admissions.filter(diagnosis__icontains=diagnosis)

    context['patient'] = Patient.objects.get(id=id)
    context['admissions'] = admissions.order_by('-date')
    context['diagnosis'] = diagnosis

    return render(request, 'admit_patient.html', context)

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

@login_required
def add_patient_admission(request, pk):
    patient = get_object_or_404(Patient, id=pk)
    clinician = request.user

    if request.method == 'POST':
        form = PatientAdmissionRecordEntry(request.POST)
        if form.is_valid():
            admission = form.save(commit=False)
            admission.patient = patient
            admission.clinician = clinician
            admission.save()
            return JsonResponse({'success': True, 'message': 'Admission created successfully.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        # Pre-fill the form but exclude clinician and patient fields from the user input
        form = PatientAdmissionRecordEntry()

    return render(request, 'partials/add_patient_admission_form.html', {
        'form': form,
        'patient': patient,
    })
@login_required
def edit_admission(request, pk):
    admission = get_object_or_404(Admission, id=pk)

    if request.method == 'POST':
        form = PatientAdmissionRecordEntry(request.POST, instance=admission)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Admission updated successfully.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = PatientAdmissionRecordEntry(instance=admission)

    return render(request, 'partials/edit_admission_form.html', {
        'form': form,
        'admission': admission,
    })
