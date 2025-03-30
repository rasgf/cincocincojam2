from django.urls import path, include
from . import views
from . import student_views

app_name = 'courses'

# URLs específicas para estudantes
student_patterns = [
    path('dashboard/', student_views.StudentDashboardView.as_view(), name='dashboard'),
    path('catalog/', student_views.CourseListView.as_view(), name='course_list'),
    path('course/<int:pk>/', student_views.CourseDetailView.as_view(), name='course_detail'),
    path('course/<int:pk>/enroll/', student_views.CourseEnrollView.as_view(), name='course_enroll'),
    path('course/<int:pk>/learn/', student_views.CourseLearnView.as_view(), name='course_learn'),
    path('course/<int:pk>/cancel/', student_views.EnrollmentCancelView.as_view(), name='enrollment_cancel'),
    path('course/<int:course_id>/lesson/<int:lesson_id>/complete/', 
         student_views.LessonCompleteView.as_view(), name='lesson_complete'),
]

urlpatterns = [
    # Dashboard do professor
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Cursos - Professor
    path('', views.CourseListView.as_view(), name='course_list'),
    path('create/', views.CourseCreateView.as_view(), name='course_create'),
    path('<int:pk>/', views.CourseDetailView.as_view(), name='course_detail'),
    path('<int:pk>/update/', views.CourseUpdateView.as_view(), name='course_update'),
    path('<int:pk>/delete/', views.CourseDeleteView.as_view(), name='course_delete'),
    path('<int:pk>/publish/', views.CoursePublishView.as_view(), name='course_publish'),
    
    # Aulas - Professor
    path('<int:course_id>/lessons/create/', views.LessonCreateView.as_view(), name='lesson_create'),
    path('lessons/<int:pk>/update/', views.LessonUpdateView.as_view(), name='lesson_update'),
    path('lessons/<int:pk>/delete/', views.LessonDeleteView.as_view(), name='lesson_delete'),
    
    # Alunos - Incluir submódulo de URLs
    path('student/', include((student_patterns, 'student'))),
]
