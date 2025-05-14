from telethon import TelegramClient, events
import requests
import json
import asyncio
import logging
import os
import dotenv
from datetime import datetime

# Carregar variáveis do arquivo .env
dotenv.load_dotenv()

# Configurações - pegando de variáveis de ambiente para docker
API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
PHONE_NUMBER = os.environ.get('PHONE_NUMBER')
GROUP_ID = int(os.environ.get('GROUP_ID'))
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/app/logs/telegram_forwarder.log")
    ]
)
logger = logging.getLogger(__name__)

# Habilitar logs detalhados da biblioteca Telethon
telethon_logger = logging.getLogger("telethon")
telethon_logger.setLevel(logging.DEBUG)

# Iniciar cliente
# Definir caminho absoluto para o arquivo de sessão
SESSION_PATH = '/app/telegram_session/telegram_session'

# Iniciar cliente com caminho absoluto
client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
logger.info(f"Usando arquivo de sessão em: {SESSION_PATH}")

@client.on(events.NewMessage(chats=GROUP_ID, incoming=True, outgoing=True))
async def handler(event):
    """Captura todas as mensagens do grupo e encaminha para o webhook"""
    try:
        # Adicione logs detalhados
        logger.debug(f"================================")
        logger.debug(f"Nova mensagem detectada! Event ID: {id(event)}")
        logger.debug(f"Tipo do evento: {type(event).__name__}")

        # Obter detalhes da mensagem
        message = event.message
        logger.debug(f"Message ID: {message.id}")
        logger.debug(f"Message text: {message.text or '[Sem texto]'}")
        logger.debug(f"Message date: {message.date}")
        logger.debug(f"Has media: {bool(message.media)}")

        sender = await event.get_sender()
        logger.debug(f"Sender ID: {sender.id}")
        logger.debug(
            f"Sender name: {getattr(sender, 'first_name', '')} {getattr(sender, 'last_name', '')}")
        logger.debug(f"Is bot: {getattr(sender, 'bot', False)}")

        # Data e hora formatada
        timestamp = datetime.now().isoformat()

        # Preparar dados para enviar
        data = {
            'message_id': message.id,
            'date': message.date.isoformat(),
            'text': message.text or '',
            'sender_id': sender.id,
            'sender_name': f"{getattr(sender, 'first_name', '')} {getattr(sender, 'last_name', '') or ''}",
            'sender_username': getattr(sender, 'username', ''),
            'is_bot': getattr(sender, 'bot', False),
            'group_id': GROUP_ID,
            'has_media': bool(message.media),
            'captured_at': timestamp
        }

        # Processar mídia de forma mais completa
        if message.media:
            try:
                # Identificar o tipo de mídia
                media_type = "unknown"
                media_details = {}
                
                # Foto
                if hasattr(message.media, 'photo'):
                    media_type = "photo"
                
                # Documento
                elif hasattr(message.media, 'document'):
                    media_type = "document"
                    if hasattr(message.media.document, 'mime_type'):
                        media_details['mime_type'] = message.media.document.mime_type
                    if hasattr(message.media.document, 'filename'):
                        media_details['filename'] = message.media.document.filename
                
                # Localização
                elif hasattr(message.media, 'geo'):
                    media_type = "location"
                    media_details['latitude'] = message.media.geo.lat
                    media_details['longitude'] = message.media.geo.long
                
                # Contato
                elif hasattr(message.media, 'phone_number'):
                    media_type = "contact"
                    media_details['phone'] = message.media.phone_number
                    if hasattr(message.media, 'first_name'):
                        media_details['first_name'] = message.media.first_name
                
                # URL
                elif hasattr(message.media, 'webpage'):
                    media_type = "webpage"
                    if hasattr(message.media.webpage, 'url'):
                        media_details['url'] = message.media.webpage.url
                    if hasattr(message.media.webpage, 'title'):
                        media_details['title'] = message.media.webpage.title
                
                # Adicionar aos dados
                data['media_type'] = media_type
                data['media_details'] = media_details
                
            except Exception as e:
                logger.error(f"Erro ao processar mídia: {e}", exc_info=True)
                data['media_error'] = str(e)

        # Enviar para webhook com retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.debug(f"Tentando enviar para webhook: {WEBHOOK_URL}")
                logger.debug(
                    f"Dados a serem enviados: {json.dumps(data, default=str)}")
                response = requests.post(WEBHOOK_URL, json=data, timeout=10)
                response.raise_for_status()  # Lança exceção para códigos de erro HTTP
                logger.info(
                    f"Mensagem encaminhada com sucesso. Status: {response.status_code}")
                logger.debug(f"Resposta do webhook: {response.text[:200]}")
                break  # Sai do loop se bem-sucedido
            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"Tentativa {attempt+1}/{max_retries} falhou: {e}")
                if attempt == max_retries - 1:  # Última tentativa
                    logger.error(
                        f"Falha ao enviar para webhook após {max_retries} tentativas")
                else:
                    await asyncio.sleep(2 ** attempt)  # Espera exponencial

        # Log para debug
        logger.info(f"Mensagem capturada: {data.get('text')[:100]}...")

    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}", exc_info=True)


# Handler global para todos os eventos em todos os chats
@client.on(events.NewMessage())
async def global_handler(event):
    try:
        chat = await event.get_chat()
        sender = await event.get_sender()
        
        logger.debug(f"==== GLOBAL HANDLER ACIONADO ====")
        logger.debug(f"Chat ID: {chat.id}, Tipo: {type(chat).__name__}")
        logger.debug(f"Mensagem: {event.message.text[:50] if event.message.text else '[Sem texto]'}")
        logger.debug(f"Remetente: {getattr(sender, 'first_name', '') or 'Unknown'} (ID: {sender.id}, Bot: {getattr(sender, 'bot', False)})")
        logger.debug(f"GROUP_ID definido: {GROUP_ID}")
        
        # SOLUÇÃO: Comparar ignorando o sinal (positivo/negativo)
        is_target_group_ignoring_sign = abs(chat.id) == abs(GROUP_ID)
        logger.debug(f"É o grupo alvo (ignorando sinal)? {is_target_group_ignoring_sign}")
        
        # Tentativa normal
        logger.debug(f"É o grupo alvo (comparação exata)? {chat.id == GROUP_ID}")
        
        # Tente outros formatos do GROUP_ID
        group_id_alt = str(GROUP_ID).replace('-100', '')
        group_id_alt = group_id_alt.replace('-', '')  # Remover qualquer sinal negativo
        logger.debug(f"Alternativa 1: {abs(chat.id) == int(group_id_alt) if group_id_alt.isdigit() else False}")
        
        # Verificar os possíveis formatos do ID do grupo
        target_group_ids = [
            GROUP_ID, 
            -GROUP_ID,  # Versão com sinal trocado
            abs(GROUP_ID),  # Versão absoluta
            -abs(GROUP_ID),  # Versão absoluta negativa
            int(group_id_alt) if group_id_alt.isdigit() else 0
        ]
        
        # Se for o grupo alvo em qualquer formato, envie para o webhook
        if abs(chat.id) == abs(GROUP_ID) or chat.id in target_group_ids:
            logger.debug(f"🚨 CORRESPONDÊNCIA ENCONTRADA! Mensagem do grupo alvo detectada!")
            
            # Coletar informações adicionais para diagnóstico
            message_info = ""
            if event.message.text:
                message_info = event.message.text[:200]
            elif hasattr(event.message, 'media') and event.message.media:
                message_info = f"[Mensagem com mídia: {type(event.message.media).__name__}]"
            else:
                message_info = "[Sem texto ou mídia]"
                
            # Verificar se tem botões
            has_buttons = False
            buttons_info = ""
            if hasattr(event.message, 'buttons') and event.message.buttons:
                has_buttons = True
                buttons_info = str(event.message.buttons)
            
            # Processar mídia de forma mais completa
            media_type = "none"
            media_details = {}
            media_base64 = None
            mime_type = None
            file_ext = None
            
            if hasattr(event.message, 'media') and event.message.media:
                try:
                    # Identificar o tipo de mídia
                    media_type = "unknown"
                    
                    # Foto
                    if hasattr(event.message.media, 'photo'):
                        media_type = "photo"
                        mime_type = "image/jpeg"
                        file_ext = "jpg"
                        
                        # Baixar a foto
                        logger.debug(f"Baixando foto do Telegram...")
                        media_bytes = await event.message.download_media(bytes)
                        
                        # Converter para Base64
                        import base64
                        media_base64 = base64.b64encode(media_bytes).decode('utf-8')
                        logger.debug(f"Foto convertida para Base64 ({len(media_base64)} caracteres)")
                    
                    # Documento
                    elif hasattr(event.message.media, 'document'):
                        media_type = "document"
                        if hasattr(event.message.media.document, 'mime_type'):
                            mime_type = event.message.media.document.mime_type
                            media_details['mime_type'] = mime_type
                        if hasattr(event.message.media.document, 'filename'):
                            filename = event.message.media.document.filename
                            media_details['filename'] = filename
                            if '.' in filename:
                                file_ext = filename.split('.')[-1]
                        
                        # Baixar o documento
                        logger.debug(f"Baixando documento do Telegram...")
                        media_bytes = await event.message.download_media(bytes)
                        
                        # Converter para Base64
                        import base64
                        media_base64 = base64.b64encode(media_bytes).decode('utf-8')
                        logger.debug(f"Documento convertido para Base64 ({len(media_base64)} caracteres)")
                    
                    # Localização
                    elif hasattr(event.message.media, 'geo'):
                        media_type = "location"
                        media_details['latitude'] = event.message.media.geo.lat
                        media_details['longitude'] = event.message.media.geo.long
                    
                    # Contato
                    elif hasattr(event.message.media, 'phone_number'):
                        media_type = "contact"
                        media_details['phone'] = event.message.media.phone_number
                        if hasattr(event.message.media, 'first_name'):
                            media_details['first_name'] = event.message.media.first_name
                    
                    # URL
                    elif hasattr(event.message.media, 'webpage'):
                        media_type = "webpage"
                        if hasattr(event.message.media.webpage, 'url'):
                            media_details['url'] = event.message.media.webpage.url
                        if hasattr(event.message.media.webpage, 'title'):
                            media_details['title'] = event.message.media.webpage.title
                    
                except Exception as e:
                    logger.error(f"Erro ao processar mídia: {e}", exc_info=True)
                    media_details['error'] = str(e)
            
            # Enviar para o webhook
            data = {
                'event': 'group_message',
                'timestamp': datetime.now().isoformat(),
                'chat_id': chat.id,
                'chat_id_abs': abs(chat.id),
                'message_id': event.message.id,
                'text': event.message.text or '',
                'message_info': message_info,
                'has_buttons': has_buttons,
                'buttons_info': buttons_info[:100] if has_buttons else "",
                'sender_id': sender.id,
                'sender_name': f"{getattr(sender, 'first_name', '') or ''} {getattr(sender, 'last_name', '') or ''}",
                'is_bot': getattr(sender, 'bot', False),
                'match_type': 'abs_match' if abs(chat.id) == abs(GROUP_ID) else 'target_list_match',
                'media_type': media_type,
                'media_details': media_details
            }
            
            # Adicionar base64 e mime_type se estiverem disponíveis
            if media_base64:
                data['media_base64'] = media_base64
            if mime_type:
                data['mime_type'] = mime_type
            if file_ext:
                data['file_ext'] = file_ext
            
            response = requests.post(WEBHOOK_URL, json=data, timeout=10)
            logger.info(f"✅ Mensagem do grupo enviada para webhook: {response.status_code}")
        
        # Também envie um evento para o webhook mesmo que não seja do grupo alvo (para teste)
        elif not is_target_group_ignoring_sign:
            test_data = {
                'event': 'other_chat_message',
                'timestamp': datetime.now().isoformat(),
                'chat_id': chat.id,
                'chat_type': type(chat).__name__,
                'message': event.message.text[:100] if event.message.text else '[Sem texto]',
                'sender_id': sender.id,
                'is_target_group': False
            }
            response = requests.post(WEBHOOK_URL, json=test_data, timeout=10)
            logger.debug(f"Teste de webhook com mensagem de outro chat: {response.status_code}")
    except Exception as e:
        logger.error(f"Erro no handler global: {e}", exc_info=True)


# Handler mais abrangente para o grupo alvo
@client.on(events.NewMessage)
async def alternative_group_handler(event):
    try:
        chat = await event.get_chat()
        
        # Verificar se é o grupo alvo ignorando sinal (positivo/negativo)
        if abs(chat.id) == abs(GROUP_ID):
            logger.debug(f"HANDLER ALTERNATIVO: Mensagem detectada no grupo alvo via abs()!")
            sender = await event.get_sender()
            
            # Enviar para o webhook
            data = {
                'event': 'group_message_via_alternative_handler',
                'timestamp': datetime.now().isoformat(),
                'chat_id': chat.id,
                'message_id': event.message.id,
                'text': event.message.text or '[Sem texto]',
                'sender_id': sender.id,
                'sender_name': f"{getattr(sender, 'first_name', '') or ''} {getattr(sender, 'last_name', '') or ''}",
                'is_bot': getattr(sender, 'bot', False),
                'match_type': 'alternative_abs_handler'
            }
            
            response = requests.post(WEBHOOK_URL, json=data, timeout=10)
            logger.debug(f"Mensagem do grupo enviada via handler alternativo: {response.status_code}")
    except Exception as e:
        logger.error(f"Erro no handler alternativo: {e}", exc_info=True)


# Handler para qualquer tipo de evento no grupo
@client.on(events.Raw)
async def raw_handler(event):
    try:
        # Tentativa de identificar se o evento está relacionado ao grupo
        chat_id = None
        if hasattr(event, 'chat_id'):
            chat_id = event.chat_id
        elif hasattr(event, 'message') and hasattr(event.message, 'chat_id'):
            chat_id = event.message.chat_id
            
        # Log para todos os eventos Raw com detalhes do tipo
        logger.debug(f"RAW event type: {type(event).__name__}")
        
        # Se o evento tiver um atributo de mensagem, tente extrair mais informações
        if hasattr(event, 'message'):
            logger.debug(f"RAW event message attributes: {dir(event.message)}")

        # Verificar se o evento está relacionado ao grupo alvo (ignorando sinal)
        if chat_id and abs(chat_id) == abs(GROUP_ID):
            logger.debug(f"Evento RAW detectado no grupo alvo (abs match): {type(event).__name__}")
            
            # Tente enviar para o webhook
            try:
                raw_data = {
                    'event': 'raw_telegram_event',
                    'timestamp': datetime.now().isoformat(),
                    'chat_id': chat_id,
                    'event_type': str(type(event).__name__),
                    'match_type': 'raw_abs_handler'
                }
                
                response = requests.post(WEBHOOK_URL, json=raw_data, timeout=10)
                logger.debug(f"Evento RAW enviado para webhook: {response.status_code}")
            except Exception as e:
                logger.error(f"Erro ao enviar evento RAW para webhook: {e}")
    except Exception as e:
        logger.error(f"Erro ao processar evento RAW: {e}", exc_info=True)


# Handler para mensagens editadas
@client.on(events.MessageEdited(chats=GROUP_ID))
async def edit_handler(event):
    logger.debug(f"Mensagem editada: {event.message.id}")
    # Você pode adicionar aqui o mesmo código de processamento do handler principal


# Handler para ações de chat (entrada/saída de membros, etc)
@client.on(events.ChatAction(chats=GROUP_ID))
async def chat_action_handler(event):
    logger.debug(f"Ação de chat detectada no grupo: {event.action_message}")


async def main():
    # Iniciar cliente
    logger.info("Iniciando cliente Telegram...")
    
    # Verificar se o arquivo de sessão existe
    session_file = f"{SESSION_PATH}.session"
    if os.path.exists(session_file):
        logger.info(f"Arquivo de sessão encontrado: {session_file}")
    else:
        logger.warning(f"Arquivo de sessão não encontrado em: {session_file}")
        logger.warning("Uma nova sessão será criada após autenticação")
    
    # Iniciar o cliente
    await client.start(phone=PHONE_NUMBER)
    
    # Verificar novamente se o arquivo de sessão foi criado
    if os.path.exists(session_file):
        logger.info(f"Sessão salva com sucesso em: {session_file}")
        # Garantir que o arquivo tem permissões corretas
        os.chmod(session_file, 0o666)  # rw-rw-rw-
        logger.info("Permissões do arquivo de sessão atualizadas para garantir escrita")
    else:
        logger.error(f"Arquivo de sessão não foi criado após autenticação: {session_file}")

    # Verificar conexão
    me = await client.get_me()
    logger.info(f"Conectado como: {me.first_name} (ID: {me.id})")
    logger.info(f"Monitorando o grupo ID: {GROUP_ID}")
    logger.info(f"Webhook configurado para: {WEBHOOK_URL}")

    # Teste periódico do webhook
    async def periodic_test():
        while True:
            try:
                test_data = {
                    'event': 'heartbeat',
                    'timestamp': datetime.now().isoformat(),
                    'status': 'running'
                }
                logger.info(f"Enviando teste periódico para webhook...")
                response = requests.post(
                    WEBHOOK_URL, json=test_data, timeout=10)
                logger.info(
                    f"Resposta do webhook (teste periódico): {response.status_code}")
            except Exception as e:
                logger.error(
                    f"Erro ao enviar teste periódico: {e}", exc_info=True)
            await asyncio.sleep(60)  # teste a cada 60 segundos

    # Inicie o teste periódico
    client.loop.create_task(periodic_test())

    # Enviar notificação de início para webhook
    try:
        startup_data = {
            'event': 'startup',
            'timestamp': datetime.now().isoformat(),
            'client_id': me.id,
            'client_name': me.first_name,
            'group_id': GROUP_ID,
            'abs_group_id': abs(GROUP_ID)
        }
        requests.post(WEBHOOK_URL, json=startup_data)
        logger.info("Notificação de inicialização enviada para webhook")
    except Exception as e:
        logger.error(f"Erro ao enviar notificação de inicialização: {e}")

    # Manter executando até ser desconectado
    logger.info("Cliente Telegram iniciado. Aguardando mensagens...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    # Criar diretório de logs se não existir
    os.makedirs("/app/logs", exist_ok=True)
    
    # Verificar se o diretório de sessão existe e tem permissões corretas
    session_dir = os.path.dirname(SESSION_PATH)
    os.makedirs(session_dir, exist_ok=True)
    
    # Garantir permissões no diretório de sessão
    os.chmod(session_dir, 0o777)  # rwxrwxrwx
    logger.info(f"Diretório de sessão {session_dir} verificado e com permissões atualizadas")

    # Executar o loop assíncrono
    logger.info("Iniciando aplicação Telegram Forwarder")
    asyncio.run(main())
