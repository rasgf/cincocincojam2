from django.urls import path
from . import views
from . import pix_views

app_name = 'payments'

# URLs para professores
professor_patterns = [
    path('dashboard/', views.ProfessorFinancialDashboardView.as_view(), name='professor_dashboard'),
    path('transactions/', views.ProfessorTransactionListView.as_view(), name='professor_transactions'),
    path('course/<int:course_id>/enrollments/', views.ProfessorCourseEnrollmentListView.as_view(), name='professor_course_enrollments'),
    
    # Novas URLs para gestão de alunos
    path('students/', views.ProfessorStudentListView.as_view(), name='professor_students'),
    path('student/<int:pk>/', views.ProfessorStudentDetailView.as_view(), name='professor_student_detail'),
]

# URLs para administradores
admin_patterns = [
    path('admin/dashboard/', views.AdminFinancialDashboardView.as_view(), name='admin_dashboard'),
    path('admin/transactions/', views.AdminTransactionListView.as_view(), name='admin_transactions'),
    path('admin/professor/<int:pk>/', views.AdminProfessorDetailView.as_view(), name='admin_professor_detail'),
]

# URLs para alunos
student_patterns = [
    path('student/payments/', views.StudentPaymentListView.as_view(), name='student_payments'),
    path('student/enrollment/<int:pk>/', views.StudentEnrollmentDetailView.as_view(), name='student_enrollment_detail'),
]

# URLs para pagamentos via Pix
pix_patterns = [
    path('pix/create/<int:course_id>/', pix_views.create_pix_payment, name='create_pix_payment'),
    path('pix/detail/<int:payment_id>/', pix_views.pix_payment_detail, name='pix_payment_detail'),
    path('pix/check-status/<int:payment_id>/', pix_views.check_payment_status, name='check_pix_status'),
    path('pix/webhook/', pix_views.pix_webhook, name='pix_webhook'),
    path('pix/simulate/<int:payment_id>/', pix_views.simulate_pix_payment, name='simulate_pix_payment'),
]

urlpatterns = [
    # Incluir todas as URLs
    *professor_patterns,
    *admin_patterns,
    *student_patterns,
    *pix_patterns,
]
