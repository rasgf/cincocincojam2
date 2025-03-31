@echo off
:: Script para iniciar o servidor CincoCincoJAM 2.0 no Windows
:: Equivalente ao start_server.sh para ambiente Windows

:: Habilitar expansão de variáveis dentro de loops
setlocal enabledelayedexpansion

:: Definir porta padrão
set PORT=8000

:: Mensagem de cabeçalho
echo ===== Iniciando Servidor CincoCincoJAM 2.0 =====
echo Porta: %PORT%

:: Verificar e matar processos usando a porta
echo 🔍 Verificando processos na porta %PORT%...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
    set PID=%%p
    if not "!PID!"=="" (
        echo 🔴 Processo !PID! encontrado usando a porta %PORT%
        echo 🔄 Encerrando processo anterior...
        taskkill /F /PID !PID!
        echo ✅ Processo encerrado!
    )
)

:: Iniciar o servidor Django
echo 🚀 Iniciando o servidor Django...
python manage.py runserver %PORT%
