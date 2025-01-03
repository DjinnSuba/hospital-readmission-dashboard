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

from .forms import UserRegisterForm, UserLoginForm, AdmissionRecordEntry, PatientRecordEntry, UserEditForm, PatientAdmissionRecordEntry, CSVUploadForm, PatientEditForm
from .models import Admission, Patient, Account

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

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
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = UserLoginForm() 
    return render(request, 'login.html', {'form': form})

def download_data(user, admissions):
    filename = 'admissions-' + user.username.replace(' ', '_') + '-' + str(date.today())
    
    response = HttpResponse(content_type='text/csv')  
    response['Content-Disposition'] = 'attachment; filename=' + filename + '.csv'  
    writer = csv.writer(response)  

    writer.writerow([
        "clinician_username",
        "patient_email",
        "is_readmission",
        "diagnosis",
        "treatment",
        "date",
        "remarks"
    ])

    # Write data rows
    for admission in admissions:
        writer.writerow([
            admission.clinician.username,        # Clinician name
            admission.patient.email,         # Patient email
            'True' if admission.is_readmission else 'False',  # Is readmission
            admission.diagnosis,             # Diagnosis
            admission.treatment,             # Treatment
            admission.date,                  # Date
            admission.remarks or ''          # Remarks (handles null)
        ])

    return response  

def download_patients_data(user, patients):
    filename = 'patients-' + user.username.replace(' ', '_') + '-' + str(date.today())
    
    response = HttpResponse(content_type='text/csv')  
    response['Content-Disposition'] = 'attachment; filename=' + filename + '.csv'  
    writer = csv.writer(response)  
    writer.writerow([
        'name', 
        'sex', 
        'birthdate', 
        'address', 
        'contact_number', 
        'email'])

    # Write data rows
    for patient in patients:
        writer.writerow([
            patient.name,          # Patient name
            patient.sex,         # Patient email
            patient.birthdate,        # Clinician name
            patient.contact_number,
            patient.email
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
    user_id = request.user.id
    user = Account.objects.get(id=user_id)
    action = request.GET.get('action')
    if action == "download":
        return download_patients_data(user, patients)
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

    name = ''
    if 'name' in request.GET:
        name = request.GET.get('name')
        admissions = admissions.filter(patient__name__icontains=name)

    diagnosis = ''
    if 'diagnosis' in request.GET:
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

    patients = Patient.objects.all()

    name = ''
    if 'name' in request.GET:
        name = request.GET.get('name')
        patients = patients.filter(name__icontains=name)

    diagnosis = ''
    if 'diagnosis' in request.GET:
        diagnosis = request.GET.get('diagnosis')
        if diagnosis != '':
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

    diagnosis = ''
    if 'diagnosis' in request.GET:
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

@login_required(login_url="/login")
def edit_patient(request, pk):
    print(f"Accessing edit_patient with pk={pk}")
    try:
        patient = Patient.objects.get(pk=pk)
    except Patient.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Patient not found.'}, status=404)

    if request.method == 'POST':
        form = PatientEditForm(request.POST, instance=patient)
        print(f"Form Valid: {form.is_valid()} Errors: {form.errors}")
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Patient updated successfully!'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors.get_json_data()}, status=400)
    else:
        form = PatientEditForm(instance=patient)
    return render(request, 'partials/edit_patient_form.html', {'form': form, 'patient': patient})

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
                            treatment=row.get("treatment", ""),
                            date=row.get("date", ""),
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

def generate_patient_pdf(request, patient_id):
    patient = Patient.objects.get(id=patient_id)
    admissions = Admission.objects.filter(patient=patient)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{patient.name}_admissions.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []

    # Add patient name
    styles = getSampleStyleSheet()
    patient_name_style = styles['Title']
    patient_name = Paragraph(f"{patient.name}", patient_name_style)
    elements.append(patient_name)
    elements.append(Spacer(1, 20))  # Add spacing

    # Add patient details
    detail_style = styles['Normal']

    # Patient Sex
    sex = Paragraph(f"Sex: {patient.get_sex_display()}", detail_style)
    elements.append(sex)

    # Patient Birthdate
    birthdate = Paragraph(f"Birthdate: {patient.birthdate.strftime('%B %d, %Y')}", detail_style)
    elements.append(birthdate)

    # Patient Address
    address = Paragraph(f"Address: {patient.address}", detail_style)
    elements.append(address)

    # Patient Contact Number
    contact_number = Paragraph(f"Contact Number: {patient.contact_number}", detail_style)
    elements.append(contact_number)

    # Patient Email
    email = Paragraph(f"Email: {patient.email}", detail_style)
    elements.append(email)

    # Add spacing after details
    elements.append(Spacer(1, 20))

    # Add admissions details
    for index, admission in enumerate(admissions, start=1):
        admission_title = Table([[f"Admission #{index}"]], colWidths=[500])
        admission_title.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(admission_title)
        elements.append(Spacer(1, 10))

        # Row for Diagnosis, Treatment, Date
        row1 = [
            Paragraph(f"<b>Diagnosis:</b> {admission.diagnosis}", styles["Normal"]),
            Paragraph(f"<b>Treatment:</b> {admission.treatment}", styles["Normal"]),
            Paragraph(f"<b>Date:</b> {admission.date.strftime('%Y-%m-%d')}", styles["Normal"]),
        ]
        table_row1 = Table([row1], colWidths=[166, 167, 167])
        table_row1.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        elements.append(table_row1)

        # Row for Doctor
        row2 = [[Paragraph(f"<b>Doctor:</b> {admission.clinician.name if admission.clinician else ''}", styles["Normal"])]]
        table_row2 = Table(row2, colWidths=[500])
        table_row2.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        elements.append(table_row2)

        # Row for Remarks
        row3 = [[Paragraph(f"<b>Remarks:</b> {admission.remarks}", styles["Normal"])]]
        table_row3 = Table(row3, colWidths=[500])
        table_row3.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        elements.append(table_row3)

        # Add spacing between admissions
        elements.append(Spacer(1, 20))

    # Build the PDF
    doc.build(elements)
    return response

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
    patients = Patient.objects.all()
    return render(request, "partials/import_patient_form.html", {"form": form, "patients": patients})


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


@login_required(login_url="/login")
def delete_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    
    if request.method == "POST":
        patient.delete()
        messages.success(request, "Patient deleted successfully.")
          # Replace with your patient list view name

    return redirect(request.META['HTTP_REFERER']) # Adjust for GET or other methods

@login_required(login_url="/login")
def delete_admission(request, pk):
    admission = get_object_or_404(Admission, pk=pk)
    
    if request.method == "POST":
        admission.delete()
        messages.success(request, "Admission deleted successfully.") # Replace with your admission list view name
    
    return redirect(request.META['HTTP_REFERER'])

@login_required(login_url="/login")
def delete_user(request, pk):
    user = get_object_or_404(Account, pk=pk)
    
    if request.method == "POST":
        user.delete()
        messages.success(request, "User deleted successfully.")
    
    return redirect(request.META['HTTP_REFERER'])

@login_required(login_url="/login")
def manage_admissions(request):
    context={}
    admissions = Admission.objects.all()

    name = ''
    if 'name' in request.GET:
        name = request.GET.get('name')
        admissions = admissions.filter(patient__name__icontains=name)

    diagnosis = ''
    if 'diagnosis' in request.GET:
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
    return render(request, 'manage_admissions.html', context)
    accounts = Account.objects.all()
    return render(request, "partials/import_user_form.html", {"form": form, "accounts": accounts})

def download_admission_csv_template(request):
    # Create a response object with the appropriate header for a CSV file
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="admissions_template.csv"'

    # Define the CSV structure
    writer = csv.writer(response)
    writer.writerow(['clinician_username', 'patient_email', 'is_readmission', 'diagnosis', 'treatment', 'date', 'remarks'])
    writer.writerow(['Dr. Username', 'patient@email.com', 'True','Flu', 'Rest and hydration', '2024-01-01', 'first readmission'])

    return response

def download_patient_csv_template(request):
    # Create a response object with the appropriate header for a CSV file
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="patient_template.csv"'

    # Define the CSV structure
    writer = csv.writer(response)
    writer.writerow(['name', 'sex', 'birthdate', 'address', 'contact_number', 'email'])
    writer.writerow(['Eleanor Rigby', 'F', '1970-03-12', '12 Penny Lane, Liverpool', '1112223333', 'eleanor.rigby@example.com'])

    return response

def download_account_csv_template(request):
    # Create a response object with the appropriate header for a CSV file
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users_template.csv"'

    # Define the CSV structure
    writer = csv.writer(response)
    writer.writerow(['username', 'name', 'email',  'password', 'role'])
    writer.writerow(['jdoe', 'Jane Doe', 'john.doe@example.com', 'password123', 'Admin'])

    return response