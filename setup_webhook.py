import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

TOKEN = os.getenv('TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

async def setup_webhook():
    bot = Bot(token=TOKEN)
    webhook_url = f"{WEBHOOK_URL}/webhook/{TOKEN}"
    
    print(f"🔧 Configurando webhook en: {webhook_url}")
    
    # Eliminar webhook anterior (si existe)
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Webhook anterior eliminado")
    
    # Configurar nuevo webhook
    await bot.set_webhook(url=webhook_url)
    print("✅ Webhook configurado exitosamente")
    
    # Verificar
    webhook_info = await bot.get_webhook_info()
    print(f"📡 URL del webhook: {webhook_info.url}")
    print(f"📊 Updates pendientes: {webhook_info.pending_update_count}")
    
    await bot.close()

if __name__ == "__main__":
    asyncio.run(setup_webhook())