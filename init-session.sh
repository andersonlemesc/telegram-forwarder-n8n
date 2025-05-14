#!/bin/bash

echo "=== Inicialização da Sessão do Telegram ==="
echo "Este script irá criar uma sessão inicial do Telegram fora do Swarm."

# Verificar se o arquivo .env existe
if [ ! -f .env ]; then
  echo "ERRO: Arquivo .env não encontrado."
  echo "Por favor, crie um arquivo .env baseado nas instruções do README."
  exit 1
fi

# Criar diretórios se não existirem
mkdir -p session logs
chmod 777 session logs

echo "Iniciando container temporário para autenticação..."
docker run -it --rm \
  -v $(pwd)/session:/app/telegram_session \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  telegram-forwarder:latest

echo ""
echo "Se a autenticação foi bem-sucedida, você pode agora implantar o serviço no Swarm:"
echo "docker stack deploy -c docker-compose.yml telegram-forwarder"
