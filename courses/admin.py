from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.contrib.admin import SimpleListFilter
from django.shortcuts import redirect, render
from django.template.response import TemplateResponse
from django.urls import path

from .models import Course, Lesson, Enrollment


class LessonInline(admin.TabularInline):
    """
    Inline para gerenciar aulas dentro da interface de administração de um curso.
    """
    model = Lesson
    extra = 1
    fields = ('title', 'order', 'video_url', 'status')
    

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """
    Configuração da interface de administração para o modelo Course.
    """
    list_display = ('title', 'professor', 'price', 'status', 'created_at', 'get_lessons_count')
    list_filter = ('status', 'created_at', 'professor')
    search_fields = ('title', 'description', 'professor__email', 'professor__first_name')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('professor', 'title', 'slug', 'description', 'short_description', 'price', 'image')
        }),
        (_('Status e Controle'), {
            'fields': ('status', 'created_at', 'updated_at')
        }),
    )
    
    inlines = [LessonInline]
    
    def get_lessons_count(self, obj):
        """Retorna o número de aulas do curso."""
        return obj.lessons.count()
    get_lessons_count.short_description = _('Aulas')


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    """
    Configuração da interface de administração para o modelo Lesson.
    """
    list_display = ('title', 'course', 'order', 'status', 'created_at')
    list_filter = ('status', 'course', 'created_at')
    search_fields = ('title', 'description', 'course__title')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('course', 'title', 'description', 'order')
        }),
        (_('Vídeo'), {
            'fields': ('video_url', 'youtube_id')
        }),
        (_('Status e Controle'), {
            'fields': ('status', 'created_at', 'updated_at')
        }),
    )


class EnrollmentStatusFilter(SimpleListFilter):
    """Filtro personalizado para status de matrícula"""
    title = _('Status da matrícula')
    parameter_name = 'status'
    
    def lookups(self, request, model_admin):
        return Enrollment.Status.choices
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """
    Configuração da interface de administração para o modelo Enrollment.
    Permite matricular alunos em cursos diretamente.
    """
    list_display = ('id', 'student_email', 'course_title', 'status', 'progress', 'enrolled_at')
    list_filter = (EnrollmentStatusFilter, 'enrolled_at', 'course')
    search_fields = ('student__email', 'student__first_name', 'course__title')
    readonly_fields = ('enrolled_at', 'completed_at', 'progress')
    raw_id_fields = ('student', 'course')
    actions = ['activate_enrollment', 'cancel_enrollment']
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('criar-matricula/', 
                 self.admin_site.admin_view(self.create_enrollment_view), 
                 name='courses_enrollment_criar_matricula'),
        ]
        return custom_urls + urls
    
    def changelist_view(self, request, extra_context=None):
        """Adiciona botão de matricular na listagem de matrículas"""
        extra_context = extra_context or {}
        extra_context['has_create_enrollment_button'] = True
        return super().changelist_view(request, extra_context=extra_context)
    
    def student_email(self, obj):
        """Retorna o email do aluno da matrícula"""
        return obj.student.email
    student_email.short_description = _('Aluno')
    
    def course_title(self, obj):
        """Retorna o título do curso da matrícula"""
        return obj.course.title
    course_title.short_description = _('Curso')
    
    def activate_enrollment(self, request, queryset):
        """Ativa as matrículas selecionadas"""
        count = 0
        for enrollment in queryset:
            if enrollment.status != Enrollment.Status.ACTIVE:
                enrollment.status = Enrollment.Status.ACTIVE
                enrollment.save()
                count += 1
        
        messages.success(request, _(f'{count} matrículas ativadas com sucesso.'))
    activate_enrollment.short_description = _('Ativar matrículas selecionadas')
    
    def cancel_enrollment(self, request, queryset):
        """Cancela as matrículas selecionadas"""
        count = 0
        for enrollment in queryset:
            if enrollment.status != Enrollment.Status.CANCELLED:
                enrollment.status = Enrollment.Status.CANCELLED
                enrollment.save()
                count += 1
        
        messages.success(request, _(f'{count} matrículas canceladas com sucesso.'))
    cancel_enrollment.short_description = _('Cancelar matrículas selecionadas')
    
    def create_enrollment_view(self, request):
        """View para criar uma matrícula diretamente"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Contexto inicial
        context = {
            'title': _('Matricular aluno em curso'),
            'app_label': 'courses',
            'opts': Enrollment._meta,
            'has_view_permission': True,
        }
        
        # Se for um POST, tenta criar a matrícula
        if request.method == 'POST':
            student_id = request.POST.get('student')
            course_id = request.POST.get('course')
            status = request.POST.get('status', Enrollment.Status.ACTIVE)
            
            if student_id and course_id:
                try:
                    student = User.objects.get(id=student_id)
                    course = Course.objects.get(id=course_id)
                    
                    # Verifica se já existe matrícula
                    existing = Enrollment.objects.filter(student=student, course=course).first()
                    
                    if existing:
                        # Atualiza status se já existir
                        existing.status = status
                        existing.save()
                        messages.success(
                            request, 
                            _(f'Matrícula de {student.email} atualizada no curso "{course.title}"!')
                        )
                    else:
                        # Cria nova matrícula
                        enrollment = Enrollment.objects.create(
                            student=student,
                            course=course,
                            status=status
                        )
                        messages.success(
                            request, 
                            _(f'Aluno {student.email} matriculado no curso "{course.title}" com sucesso!')
                        )
                        
                    return redirect('admin:courses_enrollment_changelist')
                except (User.DoesNotExist, Course.DoesNotExist) as e:
                    messages.error(request, _(f'Erro ao criar matrícula: {str(e)}'))
            else:
                messages.error(request, _('Selecione um aluno e um curso para criar a matrícula.'))
        
        # Lista de estudantes e cursos
        students = User.objects.filter(user_type='STUDENT').order_by('email')
        courses = Course.objects.filter(status=Course.Status.PUBLISHED).order_by('title')
        
        context.update({
            'students': students,
            'courses': courses,
            'status_choices': Enrollment.Status.choices,
        })
        
        return TemplateResponse(
            request,
            'admin/courses/enrollment/create_enrollment.html',
            context
        )
