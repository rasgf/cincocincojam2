from django.contrib import admin
from .models import ChatSession, Message

# Register your models here.

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_id', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('user__username', 'session_id')
    date_hierarchy = 'created_at'

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat_session', 'sender', 'content_preview', 'timestamp')
    list_filter = ('sender', 'timestamp')
    search_fields = ('content', 'chat_session__user__username')
    date_hierarchy = 'timestamp'
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    
    content_preview.short_description = 'Conteúdo'
