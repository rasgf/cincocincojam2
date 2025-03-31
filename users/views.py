from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages

from .forms import CustomUserCreationForm, CustomUserChangeForm

User = get_user_model()


class AdminRequiredMixin(UserPassesTestMixin):
    """
    Mixin para restringir acesso apenas a usuários admin.
    """
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_admin


class DashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """
    View para o dashboard do administrador.
    """
    template_name = 'users/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estatísticas de usuários
        users = User.objects.all()
        context['total_users'] = users.count()
        context['total_admins'] = users.filter(user_type=User.Types.ADMIN).count()
        context['total_professors'] = users.filter(user_type=User.Types.PROFESSOR).count()
        context['total_students'] = users.filter(user_type=User.Types.STUDENT).count()
        
        # Usuários recentes
        context['recent_users'] = users.order_by('-date_joined')[:5]
        
        return context


class UserListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """
    View para listar todos os usuários (apenas admins podem acessar).
    """
    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'users'
    
    def get_queryset(self):
        return User.objects.all().order_by('-date_joined')


class UserDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    """
    View para exibir detalhes de um usuário específico.
    """
    model = User
    template_name = 'users/user_detail.html'
    context_object_name = 'user_obj'  # Renomeado para evitar conflito com user da request


class UserCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """
    View para criar um novo usuário.
    """
    model = User
    form_class = CustomUserCreationForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:user_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Criar Novo Usuário'
        
        # Debug para verificar o formulário
        if 'form' in context:
            print(f"Form fields: {context['form'].fields}")
            for field_name, field in context['form'].fields.items():
                print(f"Field {field_name}: {field}")
        else:
            print("Form not in context!")
            
        return context
    
    def form_valid(self, form):
        # Garantir que o usuário seja salvo corretamente
        user = form.save(commit=False)
        # Se a senha não foi definida pelo formulário, definimos aqui
        if not user.password and form.cleaned_data.get('password1'):
            user.set_password(form.cleaned_data['password1'])
        user.save()
        
        messages.success(self.request, f"Usuário {user.email} criado com sucesso!")
        return super().form_valid(form)


class UserUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """
    View para atualizar um usuário existente.
    """
    model = User
    form_class = CustomUserChangeForm
    template_name = 'users/user_form.html'
    success_url = reverse_lazy('users:user_list')
    context_object_name = 'user_obj'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Usuário'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Usuário atualizado com sucesso!')
        return super().form_valid(form)


class UserDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """
    View para excluir um usuário.
    """
    model = User
    template_name = 'users/user_confirm_delete.html'
    success_url = reverse_lazy('users:user_list')
    context_object_name = 'user_obj'
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Usuário excluído com sucesso!')
        return super().delete(request, *args, **kwargs)
