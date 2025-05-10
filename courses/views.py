from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.http import HttpResponseRedirect, JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required

from .models import Course, Lesson, Enrollment
from .forms import CourseForm, LessonForm, CoursePublishForm

User = get_user_model()


class ProfessorRequiredMixin(UserPassesTestMixin):
    """
    Mixin para restringir acesso apenas a usuários com tipo professor.
    """
    def test_func(self):
        is_professor = self.request.user.is_authenticated and self.request.user.is_professor
        print(f"ProfessorRequiredMixin test_func: usuário {self.request.user}, is_professor={is_professor}, resultado={is_professor}")
        return is_professor


class AdminRequiredMixin(UserPassesTestMixin):
    """
    Mixin para restringir acesso apenas a usuários com tipo administrador.
    """
    def test_func(self):
        is_admin = self.request.user.is_authenticated and self.request.user.is_admin
        print(f"AdminRequiredMixin test_func: usuário {self.request.user}, is_admin={is_admin}, resultado={is_admin}")
        return is_admin


class ProfessorOrAdminRequiredMixin(UserPassesTestMixin):
    """
    Mixin para restringir acesso a usuários com tipo professor ou administrador.
    """
    def test_func(self):
        is_professor = self.request.user.is_authenticated and self.request.user.is_professor
        is_admin = self.request.user.is_authenticated and self.request.user.is_admin
        return is_professor or is_admin


class StudentRequiredMixin(UserPassesTestMixin):
    """
    Mixin para restringir acesso apenas a usuários com tipo aluno.
    """
    def test_func(self):
        is_student = self.request.user.is_authenticated and self.request.user.is_student
        print(f"StudentRequiredMixin test_func: usuário {self.request.user}, is_student={is_student}, resultado={is_student}")
        return is_student


class ProfessorCourseMixin(UserPassesTestMixin):
    """
    Mixin para verificar se o curso pertence ao professor logado ou se o usuário é administrador.
    """
    def test_func(self):
        # Se é administrador, tem acesso a tudo
        if self.request.user.is_authenticated and self.request.user.is_admin:
            return True
            
        # Se não é professor autenticado, não tem acesso
        if not self.request.user.is_authenticated or not self.request.user.is_professor:
            return False
            
        # Verificar contexto - para CourseViews
        course_id = self.kwargs.get('course_id') or self.kwargs.get('pk')
        if course_id:
            # Para CourseViews
            course = get_object_or_404(Course, pk=course_id)
            return course.professor == self.request.user
        
        # Para LessonViews (update/delete) onde temos pk da lição
        if hasattr(self, 'get_object') and self.model == Lesson:
            try:
                lesson = self.get_object()
                return lesson.course.professor == self.request.user
            except:
                pass
            
        return True  # Para CreateView, que não tem curso ainda


class DashboardView(LoginRequiredMixin, ProfessorOrAdminRequiredMixin, ListView):
    """
    Dashboard do professor mostrando seus cursos e estatísticas gerais.
    """
    template_name = 'courses/dashboard.html'
    context_object_name = 'courses'
    
    def get_queryset(self):
        # Retorna os cursos do professor logado com contagem de aulas
        return Course.objects.filter(professor=self.request.user).annotate(
            total_lessons=Count('lessons')
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        professor = self.request.user
        
        # Estatísticas básicas de cursos
        courses = self.get_queryset()
        context['total_courses'] = courses.count()
        context['published_courses'] = courses.filter(status=Course.Status.PUBLISHED).count()
        context['draft_courses'] = courses.filter(status=Course.Status.DRAFT).count()
        
        # Cursos recentemente editados
        context['recent_courses'] = courses.order_by('-updated_at')[:5]
        
        # Estatísticas de alunos
        # Alunos ativos nos cursos do professor
        active_students = User.objects.filter(
            user_type='STUDENT',
            enrollments__course__professor=professor,
            enrollments__status=Enrollment.Status.ACTIVE
        ).distinct()
        context['total_students'] = active_students.count()
        
        # Alunos recentes (matriculados nos últimos 30 dias)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_students = User.objects.filter(
            user_type='STUDENT',
            enrollments__course__professor=professor,
            enrollments__enrolled_at__gte=thirty_days_ago
        ).distinct()
        context['recent_students'] = recent_students.count()
        
        # Totalizar ganhos financeiros
        try:
            from payments.models import PaymentTransaction
            # Total recebido (status PAID)
            transactions = PaymentTransaction.objects.filter(enrollment__course__professor=professor)
            total_paid = transactions.filter(status=PaymentTransaction.Status.PAID).aggregate(
                total=Sum('amount')
            )['total'] or 0
            context['total_revenue'] = total_paid
        except:
            # Se o app payments não estiver disponível
            context['total_revenue'] = 0
        
        return context


class CourseListView(LoginRequiredMixin, ProfessorOrAdminRequiredMixin, ListView):
    """
    Lista todos os cursos. Para professores, filtra apenas seus cursos.
    Para administradores, mostra todos os cursos.
    """
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    
    def get_queryset(self):
        # Se o usuário é um administrador, mostra todos os cursos
        if self.request.user.is_admin:
            return Course.objects.all().order_by('-created_at')
            
        # Se é um professor, filtra apenas os cursos dele
        return Course.objects.filter(professor=self.request.user).order_by('-created_at')


class CourseDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    Exibe os detalhes de um curso específico, incluindo suas aulas.
    Administradores podem ver qualquer curso, professores apenas seus próprios cursos.
    """
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'
    
    def test_func(self):
        # Se for administrador, tem acesso a qualquer curso
        if self.request.user.is_admin:
            return True
            
        # Se for professor, só tem acesso aos seus cursos
        if self.request.user.is_professor:
            course = self.get_object()
            return course.professor == self.request.user
        
        # Se for aluno, também tem acesso aos cursos publicados
        if self.request.user.is_student:
            course = self.get_object()
            return course.status == 'PUBLISHED'
            
        return False
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adiciona as aulas do curso ao contexto
        context['lessons'] = Lesson.objects.filter(course=self.object).order_by('order')
        return context


class CourseCreateView(LoginRequiredMixin, ProfessorOrAdminRequiredMixin, CreateView):
    """
    Cria um novo curso.
    """
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    success_url = reverse_lazy('courses:course_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Passa o professor atual para o formulário
        kwargs['professor'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Curso criado com sucesso!')
        return super().form_valid(form)


class CourseUpdateView(LoginRequiredMixin, ProfessorCourseMixin, UpdateView):
    """
    Atualiza um curso existente.
    """
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    
    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Curso atualizado com sucesso!')
        return super().form_valid(form)


class CourseDeleteView(LoginRequiredMixin, ProfessorCourseMixin, DeleteView):
    """
    Exclui um curso.
    """
    model = Course
    template_name = 'courses/course_confirm_delete.html'
    success_url = reverse_lazy('courses:course_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Curso excluído com sucesso!')
        return super().delete(request, *args, **kwargs)


class CoursePublishView(LoginRequiredMixin, ProfessorCourseMixin, FormView):
    """
    Publica um curso, alterando seu status para publicado.
    """
    form_class = CoursePublishForm
    template_name = 'courses/course_publish.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = get_object_or_404(Course, pk=self.kwargs['pk'])
        return context
    
    def form_valid(self, form):
        course = get_object_or_404(Course, pk=self.kwargs['pk'])
        course.status = Course.Status.PUBLISHED
        course.save()
        messages.success(self.request, f'O curso "{course.title}" foi publicado com sucesso!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'pk': self.kwargs['pk']})


# Views para aulas
class LessonCreateView(LoginRequiredMixin, ProfessorCourseMixin, CreateView):
    """
    Cria uma nova aula para um curso específico.
    """
    model = Lesson
    form_class = LessonForm
    template_name = 'courses/lesson_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Passa o curso atual para o formulário
        kwargs['course'] = get_object_or_404(Course, pk=self.kwargs['course_id'])
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = get_object_or_404(Course, pk=self.kwargs['course_id'])
        return context
    
    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'pk': self.kwargs['course_id']})
    
    def form_valid(self, form):
        messages.success(self.request, 'Aula adicionada com sucesso!')
        return super().form_valid(form)


class LessonUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Atualiza uma aula existente.
    Administradores podem editar qualquer aula, professores apenas suas próprias aulas.
    """
    model = Lesson
    form_class = LessonForm
    template_name = 'courses/lesson_form.html'
    
    def test_func(self):
        # Se é administrador, pode editar qualquer aula
        if self.request.user.is_admin:
            return True
            
        # Se é professor, só pode editar suas próprias aulas
        if self.request.user.is_professor:
            lesson = self.get_object()
            return lesson.course.professor == self.request.user
            
        return False
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Passar o curso associado à aula para o formulário
        kwargs['course'] = self.object.course
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.object.course
        return context
    
    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'pk': self.object.course.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Aula atualizada com sucesso!')
        return super().form_valid(form)


class LessonDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    Exclui uma aula.
    Administradores podem excluir qualquer aula, professores apenas suas próprias aulas.
    """
    model = Lesson
    template_name = 'courses/lesson_confirm_delete.html'
    
    def test_func(self):
        # Se é administrador, pode excluir qualquer aula
        if self.request.user.is_admin:
            return True
            
        # Se é professor, só pode excluir suas próprias aulas
        if self.request.user.is_professor:
            lesson = self.get_object()
            return lesson.course.professor == self.request.user
            
        return False
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.object.course
        return context
    
    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'pk': self.object.course.pk})
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Aula excluída com sucesso!')
        return super().delete(request, *args, **kwargs)


# API para buscar cursos do professor
@login_required
def api_professor_courses(request):
    """API para buscar cursos do professor logado, para uso em dropdowns e seleções."""
    try:
        if not request.user.is_professor:
            return JsonResponse({'error': 'Acesso negado. Somente professores podem acessar esta API.'}, status=403)
        
        # Buscar cursos do professor logado
        courses = Course.objects.filter(professor=request.user).order_by('title')
        
        # Adicionar contagem de alunos para cada curso
        courses_data = []
        for course in courses:
            student_count = Enrollment.objects.filter(
                course=course, 
                status=Enrollment.Status.ACTIVE
            ).count()
            
            courses_data.append({
                'id': course.id,
                'title': course.title,
                'student_count': student_count
            })
        
        return JsonResponse({'courses': courses_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
