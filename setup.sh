#!/bin/bash

# Script para facilitar a primeira execução do Telegram Forwarder

echo "=== Telegram Forwarder Setup ==="
echo "Este script ajudará a configurar e iniciar o Telegram Forwarder."

# Verificar se o arquivo .env existe
if [ ! -f .env ]; then
  echo "ERRO: Arquivo .env não encontrado."
  echo "Por favor, crie um arquivo .env baseado nas instruções do README."
  exit 1
fi

# Criar diretórios necessários
echo "Criando diretórios para sessão e logs..."
mkdir -p session logs
chmod 777 session logs

# Construir a imagem Docker
echo "Construindo a imagem Docker..."
docker-compose build

# Iniciar o container
echo "Iniciando o container..."
echo "IMPORTANTE: Na primeira execução, você precisará inserir o código de verificação"
echo "que será enviado ao seu telefone através do Telegram."
echo ""
echo "Pressione ENTER para continuar..."
read

# Executar em primeiro plano para poder inserir o código de verificação
docker-compose up

echo ""
echo "Se a autenticação foi bem-sucedida, você pode agora executar o container em segundo plano:"
echo "docker-compose up -d"
