from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.UserListView.as_view(), name='user_list'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('create/', views.UserCreateView.as_view(), name='user_create'),
    path('<int:pk>/update/', views.UserUpdateView.as_view(), name='user_update'),
    path('<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
]
