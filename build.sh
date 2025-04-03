#!/usr/bin/env bash
# exit on error
set -o errexit

# Comentário adicional para forçar um novo commit
# Script para build no Render - versão atualizada

# Instalação de dependências
pip install --upgrade pip
pip install -r requirements.txt

# Dependências adicionais necessárias que não estavam no requirements.txt
pip install whitenoise openai django-environ dj-database-url gunicorn requests

# Criação das pastas necessárias
mkdir -p staticfiles media logs

# Compilar arquivos estáticos
python manage.py collectstatic --no-input

# Executar migrações
python manage.py migrate

# Criar usuários iniciais em todos os ambientes para teste inicial
python manage.py create_default_users 