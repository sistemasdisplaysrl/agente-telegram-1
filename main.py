from typing import Final
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from fastapi import FastAPI, Request
import aiohttp
import json
import os
from dotenv import load_dotenv
import uvicorn

# Cargar variables del archivo .env
load_dotenv()

TOKEN: Final = os.getenv('TOKEN')
BOT_USERNAME: Final = os.getenv('BOT_USERNAME')
API_URL: Final = os.getenv('API_URL')
WEBHOOK_URL: Final = os.getenv('WEBHOOK_URL')
PORT: Final = int(os.getenv('PORT', 8443))

# Almacenamiento simple de áreas por usuario (en memoria)
user_areas = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot Display Activado. Usa /area <nombre_area> para configurar tu área de consulta")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
Comandos disponibles:
/start - Iniciar el bot
/help - Mostrar esta ayuda
/area <nombre_area> - Establecer tu área de consulta (ejemplo: /area domino)
/myarea - Mostrar tu área actual
    
Puedes hacer consultas como "¿cómo jugar domino?" y el bot buscará en tu área configurada
    """
    await update.message.reply_text(help_text)

async def area_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not context.args:
        await update.message.reply_text("Por favor especifica un área. Ejemplo: /area domino")
        return
    
    new_area = ' '.join(context.args)
    user_areas[user_id] = new_area
    await update.message.reply_text(f"✅ Área configurada como: {new_area}\n\nAhora puedes hacer consultas sobre este tema.")

async def myarea_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    current_area = user_areas.get(user_id)
    
    if current_area:
        await update.message.reply_text(f"📁 Tu área actual es: {current_area}\nUsa /area <nueva_area> para cambiarla")
    else:
        await update.message.reply_text("❌ No tienes un área configurada. Usa /area <nombre_area> para configurar una.")

async def query_api(question: str, area: str) -> str:
    url = f"{API_URL}/query"
    payload = {
        "question": question,
        "area": area,
        "top_k": 5
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('answer', 'No se encontró respuesta en la base de datos')
                else:
                    return f"❌ Error en el servidor (código {response.status})"
    except aiohttp.ClientConnectorError:
        return "❌ No se pudo conectar al servidor. Verifica que la API esté ejecutándose."
    except Exception as e:
        return f"❌ Error de conexión: {str(e)}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text
    user_id = update.message.from_user.id

    print(f'User ({update.message.chat.id}) in {message_type}: "{text}"')

    # Ignorar mensajes en grupos que no mencionen al bot
    if message_type == 'group':
        if BOT_USERNAME and BOT_USERNAME in text:
            text = text.replace(BOT_USERNAME, '').strip()
        else:
            return

    # Verificar si el usuario tiene área configurada
    if user_id not in user_areas:
        await update.message.reply_text(
            "❌ Primero configura tu área usando /area <nombre_area>\n"
            "Ejemplo: /area domino\n"
            "Usa /help para ver todos los comandos disponibles."
        )
        return

    # Obtener el área del usuario y consultar a la API
    user_area = user_areas[user_id]
    
    # Mostrar que se está procesando la consulta
    processing_msg = await update.message.reply_text("🔍 Buscando información...")
    
    response = await query_api(text, user_area)
    
    # Eliminar el mensaje de "procesando" y enviar la respuesta
    await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_msg.message_id)
    
    print('Bot: ', response)
    await update.message.reply_text(response)

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"{update} causo el error {context.error}")

# Crear la aplicación de Telegram
ptb_app = Application.builder().token(TOKEN).build()

# Agregar handlers
ptb_app.add_handler(CommandHandler("start", start_command))
ptb_app.add_handler(CommandHandler("help", help_command))
ptb_app.add_handler(CommandHandler("area", area_command))
ptb_app.add_handler(CommandHandler("myarea", myarea_command))
ptb_app.add_handler(MessageHandler(filters.TEXT, handle_message))
ptb_app.add_error_handler(error)

# Crear la aplicación FastAPI
app = FastAPI(title="Bot Display Webhook")

@app.on_event("startup")
async def startup():
    """Inicializar el bot de Telegram al arrancar FastAPI"""
    await ptb_app.initialize()
    await ptb_app.start()
    
    # Configurar el webhook en Telegram
    webhook_url = f"{WEBHOOK_URL}/webhook/{TOKEN}"
    await ptb_app.bot.set_webhook(url=webhook_url)
    print(f"✅ Webhook configurado en: {webhook_url}")

@app.on_event("shutdown")
async def shutdown():
    """Limpiar recursos al cerrar la aplicación"""
    await ptb_app.stop()
    await ptb_app.shutdown()
    print("🛑 Bot detenido")

@app.post(f"/webhook/{TOKEN}")
async def telegram_webhook(request: Request):
    """
    Endpoint que recibe las actualizaciones (updates) de Telegram.
    Este es el webhook que Telegram llamará cada vez que haya un evento.
    """
    try:
        data = await request.json()
        update = Update.de_json(data, ptb_app.bot)
        await ptb_app.process_update(update)
        return {"ok": True}
    except Exception as e:
        print(f"Error procesando update: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/")
async def root():
    """Endpoint raíz para verificar que el servidor está corriendo"""
    return {
        "status": "running",
        "bot": "Bot Display",
        "mode": "webhook"
    }

@app.get("/health")
async def health():
    """Health check para servicios de monitoreo"""
    return {"status": "healthy", "bot_running": True}

if __name__ == "__main__":
    # Verificar que las variables de entorno estén configuradas
    if not TOKEN:
        raise ValueError("❌ TOKEN no encontrado en el archivo .env")
    if not BOT_USERNAME:
        raise ValueError("❌ BOT_USERNAME no encontrado en el archivo .env")
    if not API_URL:
        raise ValueError("❌ API_URL no encontrado en el archivo .env")
    if not WEBHOOK_URL:
        raise ValueError("❌ WEBHOOK_URL no encontrado en el archivo .env")
    
    print("🚀 Iniciando Bot Display con FastAPI + Webhook")
    print(f"📡 Puerto: {PORT}")
    print(f"🌐 Webhook URL: {WEBHOOK_URL}")
    
    # Ejecutar el servidor FastAPI
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT
    )