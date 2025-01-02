from django.contrib.auth.models import AbstractUser
from django.db import models

class Account(AbstractUser):
    ADMIN = 'Admin'
    CLINICIAN = 'Clinician'
    ANALYST = 'Analyst'

    ROLE_CHOICES = [
        (ADMIN, 'Admin'),
        (CLINICIAN, 'Clinician'),
        (ANALYST, 'Analyst'),
    ]

    username = models.CharField(max_length=150, unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=CLINICIAN)

    def __str__(self):
        return f"{self.username} ({self.role})"

class Patient(models.Model):
    SEX_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]

    name = models.CharField(max_length=255)
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)
    birthdate = models.DateField()
    address = models.TextField()
    contact_number = models.CharField(max_length=15)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.name

class Admission(models.Model):
    clinician = models.ForeignKey(Account, on_delete=models.CASCADE, limit_choices_to={'role': 'Clinician'})
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='admissions')
    is_readmission = models.BooleanField(default=False)
    diagnosis = models.TextField()
    treatment = models.TextField()
    date = models.DateField()
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Admission of {self.patient.name} by {self.clinician.name} on {self.date}"
