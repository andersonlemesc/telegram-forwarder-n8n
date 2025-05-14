FROM python:3.10-slim

# Definindo variáveis para a compilação
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Definir diretório de trabalho
WORKDIR /app

# Instalar dependências 
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libc6-dev && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir telethon requests python-dotenv && \
    apt-get purge -y --auto-remove gcc libc6-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Criar diretório para a sessão e logs
RUN mkdir -p /app/logs /app/temp

# Copiar o código
COPY telegram_forwarder.py /app/
COPY .env /app/

# Definir permissões
RUN chmod +x /app/telegram_forwarder.py

# Executar script
CMD ["python", "/app/telegram_forwarder.py"]
