from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

class Command(BaseCommand):
    help = 'Cria usuários padrão do sistema'

    def handle(self, *args, **kwargs):
        # Lista de usuários padrão
        default_users = [
            {
                'email': 'admin@example.com',
                'password': 'admin123',
                'first_name': 'Admin',
                'last_name': 'Sistema',
                'user_type': 'ADMIN',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'email': 'professor@example.com',
                'password': 'prof123',
                'first_name': 'Professor',
                'last_name': 'Exemplo',
                'user_type': 'PROFESSOR',
            },
            {
                'email': 'aluno@example.com',
                'password': 'aluno123',
                'first_name': 'Aluno',
                'last_name': 'Teste',
                'user_type': 'STUDENT',
            },
        ]

        # Criar cada usuário se não existir
        for user_data in default_users:
            email = user_data.pop('email')
            password = user_data.pop('password')
            
            if not User.objects.filter(email=email).exists():
                user = User.objects.create_user(email=email, password=password, **user_data)
                self.stdout.write(self.style.SUCCESS(f'Usuário criado: {email}'))
            else:
                self.stdout.write(self.style.WARNING(f'Usuário já existe: {email}'))
