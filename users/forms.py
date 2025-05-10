from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """
    Formulário para criação de novos usuários, com campos personalizados.
    """
    email = forms.EmailField(label='Email', required=True)
    first_name = forms.CharField(label='Nome', required=True)
    last_name = forms.CharField(label='Sobrenome', required=True)
    user_type = forms.ChoiceField(
        label='Tipo de Usuário',
        choices=User.Types.choices,
        required=True
    )
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'user_type', 'password1', 'password2')
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Adicionar mensagens de ajuda
        self.fields['password1'].help_text = 'Sua senha deve conter pelo menos 8 caracteres e não pode ser muito comum.'
        self.fields['password2'].help_text = 'Repita a senha para confirmação.'
        self.fields['email'].help_text = 'Este será o login do usuário. Precisa ser um email válido.'


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
        
        # Verificar se o usuário atual é admin
        request = kwargs.get('initial', {}).get('request')
        if request and not request.user.is_admin:
            # Se não for admin, remover campos que usuários comuns não devem editar
            self.fields.pop('user_type', None)
            self.fields.pop('is_active', None)
            
            # E fazer o email somente leitura
            self.fields['email'].widget.attrs['readonly'] = True