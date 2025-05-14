# Telegram Forwarder para n8n

Este projeto captura todas as mensagens de um grupo do Telegram (incluindo mensagens de bots) e as encaminha para um webhook no n8n.

## Visão Geral

O Telegram Forwarder é uma solução para monitorar grupos do Telegram e encaminhar todas as mensagens para um webhook, possibilitando a automação e processamento dessas mensagens através do n8n ou qualquer outra plataforma que receba webhooks.

Características principais:
- Captura todas as mensagens, incluindo mensagens de bots (o que não seria possível utilizando um bot do Telegram)
- Processa e encaminha conteúdo de mídia (fotos, documentos, localização, etc.)
- Funciona com Docker para fácil implantação
- Suporta implantação via Docker Swarm para alta disponibilidade

## Pré-requisitos

- Docker e Docker Compose instalados
- Uma conta regular do Telegram
- API ID e API Hash do Telegram
- Webhook configurado no n8n

## Passo a Passo para Configuração

### 1. Obter Credenciais do Telegram

1. Acesse https://my.telegram.org/auth e faça login com sua conta do Telegram
2. Selecione "API development tools"
3. Crie um novo aplicativo (ou use um existente)
4. Anote o `API ID` e `API HASH` fornecidos
5. Estas credenciais são exclusivas para sua conta e não devem ser compartilhadas

### 2. Configurar o Webhook no n8n

1. No n8n, crie um novo workflow
2. Adicione um nó "Webhook" como trigger
3. Configure o webhook para receber requisições POST
4. Ative o webhook e copie a URL gerada
5. Esta URL será usada no arquivo .env como `WEBHOOK_URL`

### 3. Preparar o Ambiente

1. Clone este repositório:
   ```bash
   git clone https://github.com/andersonlemesc/telegram-forwarder-n8n.git
   cd telegram-forwarder-n8n
   ```

2. Crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo:
   ```
   # Credenciais do Telegram
   API_ID=12345678
   API_HASH=abcdef0123456789abcdef0123456789
   PHONE_NUMBER=+5511999999999
   
   # Configurações do Bot
   GROUP_ID=-1001234567890
   WEBHOOK_URL=https://sua-instancia-n8n.com/webhook/seu-webhook-id
   ```

3. Substitua os valores acima pelos dados obtidos nas etapas anteriores:
   - `API_ID` e `API_HASH`: obtidos do my.telegram.org
   - `PHONE_NUMBER`: seu número de telefone no formato internacional
   - `GROUP_ID`: ID do grupo a ser monitorado (veja abaixo como obter)
   - `WEBHOOK_URL`: URL do webhook gerado no n8n

### 4. Obtendo o ID do Grupo

1. Adicione o bot [@userinfobot](https://t.me/userinfobot) ao grupo
2. Envie qualquer mensagem no grupo
3. O bot responderá com informações do grupo, incluindo o ID
4. Copie este ID incluindo o sinal negativo (normalmente começa com `-100`)

### 5. Configurar o Docker Compose

1. Edite o arquivo `docker-compose.yml` para usar o arquivo .env:
   ```yaml
   version: '3.8'
   
   services:
     telegram-forwarder:
       image: telegram-forwarder:latest
       build:
         context: .
       deploy:
         mode: replicated
         replicas: 1
         restart_policy:
           condition: on-failure
           delay: 5s
           max_attempts: 3
       volumes:
         - ./session:/app/telegram_session
         - ./logs:/app/logs
       env_file:
         - .env
       networks:
         - telegram_network
   
   networks:
     telegram_network:
       driver: overlay
       attachable: true
   ```

2. Crie os diretórios necessários:
   ```bash
   mkdir -p session logs
   chmod 777 session logs
   ```

### 6. Primeira Execução e Autenticação

Existem duas maneiras de fazer a primeira autenticação:

#### Opção 1: Usando o script init-session.sh (Recomendado)

Este script foi criado especificamente para facilitar a primeira autenticação:

1. Torne o script executável:
   ```bash
   chmod +x init-session.sh
   ```

2. Execute o script:
   ```bash
   ./init-session.sh
   ```

3. Na primeira execução, você receberá uma mensagem no Telegram com código de verificação
4. Digite o código quando solicitado no terminal
5. Após a autenticação bem-sucedida, a sessão será salva na pasta `session/`

#### Opção 2: Usando o Docker Compose

1. Construa a imagem Docker:
   ```bash
   docker-compose build
   ```

2. Inicie o container pela primeira vez:
   ```bash
   docker-compose up
   ```

3. Na primeira execução, você receberá uma mensagem no Telegram com código de verificação
4. Digite o código quando solicitado no terminal
5. Após a autenticação bem-sucedida, a sessão será salva na pasta `session/`

### 7. Execução em Produção

1. Após a autenticação inicial, você pode executar o container em segundo plano:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

2. Para verificar logs:
   ```bash
   docker-compose logs -f
   ```

## Usando Docker Swarm (Opcional)

Se você deseja usar o Docker Swarm para alta disponibilidade:

1. Certifique-se de ter inicializado o Swarm:
   ```bash
   docker swarm init
   ```

2. **Importante:** Realize a autenticação primeiro usando o script `init-session.sh` antes de implantar no Swarm.

3. Implante o serviço:
   ```bash
   docker stack deploy -c docker-compose.yml telegram-forwarder
   ```

4. Verifique o status do serviço:
   ```bash
   docker service ls
   docker service logs telegram-forwarder_telegram-forwarder
   ```

## Monitoramento

- Os logs são armazenados no diretório `logs/`
- O serviço envia heartbeats periódicos para o webhook (a cada 60 segundos)
- Você pode monitorar os logs com:
  ```bash
  tail -f logs/telegram_forwarder.log
  ```

## Solução de Problemas

- **Erro de autenticação**: Verifique se as credenciais `API_ID` e `API_HASH` estão corretas
- **Não recebe mensagens**: Certifique-se de que:
  - A conta está no grupo correto
  - O `GROUP_ID` está correto
  - O webhook está ativo e acessível
- **Webhook não recebe dados**: Verifique se a URL está correta e acessível de fora
- **Erro ao iniciar**: Certifique-se de que os diretórios `session` e `logs` existem e têm permissões corretas

## Estrutura dos Dados Enviados ao Webhook

O serviço envia os seguintes dados em formato JSON:

```json
{
  "message_id": 12345,
  "date": "2023-01-01T12:00:00+00:00",
  "text": "Conteúdo da mensagem",
  "sender_id": 67890,
  "sender_name": "Nome do Remetente",
  "sender_username": "username",
  "is_bot": false,
  "group_id": -10012345678,
  "has_media": false,
  "captured_at": "2023-01-01T12:00:01.123456",
  "media_type": "photo",
  "media_details": {
    // Detalhes adicionais específicos do tipo de mídia
  }
}
```

Para mensagens com mídia, campos adicionais são incluídos dependendo do tipo.

## Notas

- Este projeto usa uma conta regular do Telegram em vez de um bot para poder ver mensagens de outros bots
- A sessão Telegram é salva no diretório `session/` para persistir entre reinicializações
- Para segurança, não compartilhe seu arquivo `.env` ou a pasta `session/`
- Não use esta solução para fins que violem os Termos de Serviço do Telegram

## Licença

[MIT](LICENSE)
