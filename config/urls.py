"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect

# View personalizada para redirecionar para o dashboard apropriado com base no tipo de usuário
def dashboard_redirect(request):
    if request.user.is_authenticated:
        if request.user.is_admin:
            return redirect('users:dashboard')
        elif request.user.is_professor:
            return redirect('courses:dashboard')
        elif request.user.is_student:
            return redirect('courses:student:course_list')
    return redirect('home')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),  # Inclui reset de senha e outras URLs de autenticação
    
    # Dashboard redirect
    path('dashboard/', dashboard_redirect, name='dashboard_redirect'),
    
    # User management
    path('users/', include('users.urls')),
    
    # Courses management
    path('courses/', include('courses.urls')),
    
    # Payments management
    path('payments/', include('payments.urls')),
    
    # Assistant
    path('assistant/', include('assistant.urls')),
    
    # Invoices
    path('invoices/', include('invoices.urls')),
    
    # Home page
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
