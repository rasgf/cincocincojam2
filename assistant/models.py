from django.db import models
from django.conf import settings

# Create your models here.

class ChatSession(models.Model):
    """Modelo para armazenar uma sessão de chat"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        if self.user:
            return f"Chat de {self.user.username} ({self.session_id})"
        return f"Chat anônimo ({self.session_id})"

class Message(models.Model):
    """Modelo para armazenar mensagens de chat"""
    SENDER_CHOICES = (
        ('user', 'Usuário'),
        ('bot', 'Assistente'),
    )
    
    chat_session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.get_sender_display()}: {self.content[:50]}..."
