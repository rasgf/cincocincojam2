#!/bin/bash

# Definir porta padrão
PORT=8000

# Mensagem de cabeçalho
echo "===== Iniciando Servidor CincoCincoJAM 2.0 ====="
echo "Porta: $PORT"

# Verificar se há processos usando a porta
PID=$(lsof -ti :$PORT)

# Se encontrar algum processo, mata
if [ ! -z "$PID" ]; then
    echo "🔴 Processo $PID encontrado usando a porta $PORT"
    echo "🔄 Encerrando processo anterior..."
    kill -9 $PID
    echo "✅ Processo encerrado!"
fi

# Iniciar o servidor Django
echo "🚀 Iniciando o servidor Django..."
python3 manage.py runserver $PORT
