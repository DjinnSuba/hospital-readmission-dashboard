from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('clinician_dashboard/', views.clinician_dashboard, name='clinician_dashboard'),
    path('logout', views.sign_out, name='logout'),
    path('patient-list/', views.patient_list, name='patient_list'),
    path('user-list/', views.user_list, name='user_list'),
    path('add-patient/', views.add_patient, name='add_patient'),
    path('add-admission/', views.add_admission, name='add_admission'),
    path('add-user/', views.add_user, name='add_user'),
    path('admissions/', views.admissions, name='admissions'),
    path('edit-user/<int:pk>/', views.edit_user, name='edit_user'),

    path('edit-admission/<int:pk>/', views.edit_admission, name='edit_admission'),
    
    path('admissions/patients/', views.admission_patients, name='admission_patients'),
    path('admissions/patients/<int:id>/', views.admit_patient, name='admit_patient'),
    path('add-admission/patient/<int:pk>', views.add_patient_admission, name='add_patient_admission'),
    path('admissions/admin/', views.manage_admissions, name='manage_admissions'),

    path('edit-patient/<int:pk>/', views.edit_patient, name='edit_patient'),
    path('delete-patient/<int:pk>/', views.delete_patient, name='delete_patient'),
    path('delete-user/<int:pk>/', views.delete_user, name='delete_user'),
    path('delete-admission/<int:pk>/', views.delete_admission, name='delete_admission'),
    path('import-admissions/', views.import_admissions, name='import_admissions'),
    path('import-patients/', views.import_patients, name='import_patients'),
    path('import-users/', views.import_users, name='import_users'),

    path('download-admission-template/', views.download_admission_csv_template, name='download_admission_csv_template'),
    path('download-patient-template/', views.download_patient_csv_template, name='download_patient_csv_template'),
    path('download-account-template/', views.download_account_csv_template, name='download_account_csv_template'),
]
