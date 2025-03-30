from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db.models import Count
from django.http import HttpResponseRedirect, JsonResponse

from .models import Course, Lesson
from .forms import CourseForm, LessonForm, CoursePublishForm


class ProfessorRequiredMixin(UserPassesTestMixin):
    """
    Mixin para restringir acesso apenas a usuários com tipo professor.
    """
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_professor


class ProfessorCourseMixin(UserPassesTestMixin):
    """
    Mixin para verificar se o curso pertence ao professor logado.
    """
    def test_func(self):
        if not self.request.user.is_authenticated or not self.request.user.is_professor:
            return False
            
        # Obter o curso da URL
        course_id = self.kwargs.get('course_id') or self.kwargs.get('pk')
        if course_id:
            course = get_object_or_404(Course, pk=course_id)
            return course.professor == self.request.user
            
        return True  # Para CreateView, que não tem curso ainda


class DashboardView(LoginRequiredMixin, ProfessorRequiredMixin, ListView):
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
        
        # Estatísticas básicas
        courses = self.get_queryset()
        context['total_courses'] = courses.count()
        context['published_courses'] = courses.filter(status=Course.Status.PUBLISHED).count()
        context['draft_courses'] = courses.filter(status=Course.Status.DRAFT).count()
        
        # Cursos recentemente editados
        context['recent_courses'] = courses.order_by('-updated_at')[:5]
        
        return context


class CourseListView(LoginRequiredMixin, ProfessorRequiredMixin, ListView):
    """
    Lista todos os cursos do professor logado.
    """
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    
    def get_queryset(self):
        # Filtra os cursos do professor logado
        return Course.objects.filter(professor=self.request.user).order_by('-created_at')


class CourseDetailView(LoginRequiredMixin, ProfessorCourseMixin, DetailView):
    """
    Exibe os detalhes de um curso específico, incluindo suas aulas.
    """
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adiciona as aulas do curso ao contexto
        context['lessons'] = Lesson.objects.filter(course=self.object).order_by('order')
        return context


class CourseCreateView(LoginRequiredMixin, ProfessorRequiredMixin, CreateView):
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


class LessonUpdateView(LoginRequiredMixin, ProfessorCourseMixin, UpdateView):
    """
    Atualiza uma aula existente.
    """
    model = Lesson
    form_class = LessonForm
    template_name = 'courses/lesson_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.object.course
        return context
    
    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'pk': self.object.course.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Aula atualizada com sucesso!')
        return super().form_valid(form)


class LessonDeleteView(LoginRequiredMixin, ProfessorCourseMixin, DeleteView):
    """
    Exclui uma aula.
    """
    model = Lesson
    template_name = 'courses/lesson_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.object.course
        return context
    
    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'pk': self.object.course.pk})
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Aula excluída com sucesso!')
        return super().delete(request, *args, **kwargs)
