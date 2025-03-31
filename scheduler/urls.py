"""
URLs para o aplicativo de agenda do professor.
"""
from django.urls import path
from . import views

app_name = 'scheduler'

urlpatterns = [
    # Visualização principal do calendário
    path('', views.calendar_view, name='calendar'),
    
    # Gerenciamento de eventos
    path('events/', views.event_list, name='event_list'),
    path('events/create/', views.event_create, name='event_create'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('events/<int:pk>/edit/', views.event_edit, name='event_edit'),
    path('events/<int:pk>/delete/', views.event_delete, name='event_delete'),
    
    # Gerenciamento de estúdios
    path('locations/', views.location_list, name='location_list'),
    path('locations/create/', views.location_create, name='location_create'),
    path('locations/<int:pk>/', views.location_detail, name='location_detail'),
    path('locations/<int:pk>/edit/', views.location_update, name='location_update'),
    path('locations/<int:pk>/delete/', views.location_delete, name='location_delete'),
    
    # Gerenciamento de participantes
    path('events/<int:event_id>/participants/', views.participant_list, name='participant_list'),
    path('events/<int:event_id>/participants/add/', views.add_participant, name='add_participant'),
    
    # API para AJAX/Fetch
    path('api/events/', views.api_events, name='api_events'),
    path('api/events/<int:pk>/', views.api_event_detail, name='api_event_detail'),
]
