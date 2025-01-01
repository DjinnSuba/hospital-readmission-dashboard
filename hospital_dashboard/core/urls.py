from django.urls import path
from . import views

urlpatterns = [
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

    path('admissions/patients/', views.admission_patients, name='admission_patients'),
    path('admissions/patients/<int:id>/', views.admit_patient, name='admit_patient'),

]
