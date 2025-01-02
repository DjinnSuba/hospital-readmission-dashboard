from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from .forms import UserRegisterForm, UserLoginForm, AdmissionRecordEntry, PatientRecordEntry, UserEditForm, CSVUploadForm
from .models import Admission, Patient, Account

import csv

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
            if user.role == 'Admin':
                return redirect('admin_dashboard')
            elif user.role == 'Clinician':
                return redirect('clinician_dashboard')
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = UserLoginForm()
    return render(request, 'login.html', {'form': form})

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

@login_required(login_url="/login")
def edit_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == "POST":
        form = PatientRecordEntry(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Patient updated successfully!'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = PatientRecordEntry(instance=patient)
    return render(request, 'edit_patient_form.html', {'form': form})


@login_required(login_url="/login")
def import_admissions(request):
    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data["csv_file"]
            try:
                decoded_file = csv_file.read().decode("utf-8").splitlines()
                csv_reader = csv.DictReader(decoded_file)

                records_created = 0
                for row in csv_reader:
                    try:
                        # Ensure patient and clinician exist
                        patient = Patient.objects.get(email=row["patient_email"])
                        clinician = Account.objects.get(username=row["clinician_username"], role="Clinician")

                        # Create admission record
                        Admission.objects.create(
                            clinician=clinician,
                            patient=patient,
                            is_readmission=bool(row["is_readmission"]),
                            diagnosis=row["diagnosis"],
                            treatment=row["treatment"],
                            date=row["date"],
                            remarks=row.get("remarks", ""),
                        )
                        records_created += 1
                    except Exception as e:
                        messages.warning(
                            request,
                            f"Error processing row: {row} - {str(e)}"
                        )
                messages.success(request, f"Successfully imported {records_created} admission records.")
                return redirect("admissions")
            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
        else:
            messages.error(request, "Invalid form submission. Please try again.")
    else:
        form = CSVUploadForm()

    return render(request, "partials/import_admission_form.html", {"form": form})

def process_csv_file(csv_file, model, unique_field, create_update_func):
    """
    Generic function to process CSV data and create or update records.
    """
    decoded_file = csv_file.read().decode("utf-8").splitlines()
    csv_reader = csv.DictReader(decoded_file)

    records_created = 0
    records_updated = 0

    for row in csv_reader:
        try:
            # Check if the record exists
            record = model.objects.filter(**{unique_field: row[unique_field]}).first()

            if record:
                # Update the record
                create_update_func(record, row)
                records_updated += 1
            else:
                # Create a new record
                record = model()
                create_update_func(record, row)
                records_created += 1
        except Exception as e:
            raise Exception(f"Error processing row: {row} - {str(e)}")
    
    return records_created, records_updated


def create_or_update_patient(patient, data):
    """
    Function to create or update a Patient record.
    """
    patient.name = data["name"]
    patient.sex = data["sex"]
    patient.birthdate = data["birthdate"]
    patient.address = data["address"]
    patient.contact_number = data["contact_number"]
    patient.email = data["email"]
    patient.save()


def create_or_update_account(account, data):
    """
    Function to create or update an Account record.
    """
    account.username = data["username"]
    account.name = data["name"]
    account.email = data["email"]
    account.password = data["password"]  # Consider hashing passwords here
    account.role = data["role"]
    account.save()


@login_required(login_url="/login")
def import_patients(request):
    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data["csv_file"]
            try:
                records_created, records_updated = process_csv_file(
                    csv_file,
                    Patient,
                    unique_field="email",
                    create_update_func=create_or_update_patient,
                )
                messages.success(request, f"Successfully imported {records_created} new patients and updated {records_updated} existing patients.")
                return redirect("patient_list")
            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
        else:
            messages.error(request, "Invalid form submission. Please try again.")
    else:
        form = CSVUploadForm()
    return render(request, "partials/import_patient_form.html", {"form": form})


@login_required(login_url="/login")
def import_users(request):
    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data["csv_file"]
            try:
                records_created, records_updated = process_csv_file(
                    csv_file,
                    Account,
                    unique_field="email",
                    create_update_func=create_or_update_account,
                )
                messages.success(request, f"Successfully imported {records_created} new users and updated {records_updated} existing users.")
                return redirect("user_list")
            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
        else:
            messages.error(request, "Invalid form submission. Please try again.")
    else:
        form = CSVUploadForm()
    return render(request, "partials/import_user_form.html", {"form": form})