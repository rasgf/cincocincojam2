from django.urls import path
from . import views

app_name = 'assistant'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/session/create/', views.create_session, name='create_session'),
    path('api/message/send/', views.send_message, name='send_message'),
    path('api/message/history/', views.get_message_history, name='get_message_history'),
    path('history/', views.chat_history, name='history'),
    path('history/<str:session_id>/', views.chat_history, name='history_detail'),
    path('config/', views.behavior_config, name='behavior_config'),
    path('config/save/', views.save_behavior, name='save_behavior'),
]
