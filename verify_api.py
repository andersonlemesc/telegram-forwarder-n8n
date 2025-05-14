import asyncio
import os
import dotenv
from telethon import TelegramClient

# Carregar variáveis do arquivo .env
dotenv.load_dotenv()

# Obter as credenciais do ambiente
API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')

async def test_connection():
    print(f"Tentando conectar com API_ID={API_ID} e API_HASH={API_HASH}")
    client = TelegramClient('test_session', API_ID, API_HASH)
    
    try:
        await client.connect()
        print("Conexão bem-sucedida!")
        is_authorized = await client.is_user_authorized()
        print(f"Usuário autorizado: {is_authorized}")
        
        if not is_authorized:
            print("Não há sessão existente. Isso é esperado para um teste de conexão.")
            print("Mas a API ID e HASH estão corretos!")
        
        await client.disconnect()
        return True
        
    except Exception as e:
        print(f"Erro ao conectar: {e}")
        await client.disconnect()
        return False

if __name__ == "__main__":
    # Verificar se as credenciais estão definidas
    if not API_ID or not API_HASH:
        print("❌ API_ID ou API_HASH não definidos!")
        print("Verifique se o arquivo .env está configurado corretamente.")
        exit(1)
        
    success = asyncio.run(test_connection())
    if success:
        print("✅ API ID e API HASH são válidos!")
    else:
        print("❌ API ID e/ou API HASH são inválidos. Verifique os valores exatos em my.telegram.org")
