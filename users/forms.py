from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """
    Formulário para criação de novos usuários, com campos personalizados.
    """
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'user_type')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tornar alguns campos obrigatórios
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True


class CustomUserChangeForm(UserChangeForm):
    """
    Formulário para edição de usuários existentes, com campos personalizados.
    Não inclui campo de senha diretamente, pois isso é tratado separadamente.
    """
    password = None  # Remove o campo de senha deste formulário
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'user_type', 'bio', 'profile_image', 'is_active')
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tornar alguns campos obrigatórios
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
