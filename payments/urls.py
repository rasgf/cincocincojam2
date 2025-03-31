from django.urls import path
from . import views

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

urlpatterns = [
    # Incluir todas as URLs
    *professor_patterns,
    *admin_patterns,
    *student_patterns,
]
