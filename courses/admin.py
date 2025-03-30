from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Course, Lesson


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
