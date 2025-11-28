from typing import Final, Optional
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from fastapi import FastAPI, Request
import aiohttp
import aiomysql
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

# Credenciales MySQL
DB_HOST: Final = os.getenv('DB_HOST')
DB_PORT: Final = int(os.getenv('DB_PORT', 3306))
DB_USER: Final = os.getenv('DB_USER')
DB_PASSWORD: Final = os.getenv('DB_PASSWORD')
DB_NAME: Final = os.getenv('DB_NAME')

# Pool de conexiones a MySQL
db_pool = None

async def init_db_pool():
    """Inicializar el pool de conexiones a MySQL"""
    global db_pool
    db_pool = await aiomysql.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        autocommit=True,
        minsize=1,
        maxsize=10
    )
    print("✅ Pool de conexiones MySQL inicializado")

async def close_db_pool():
    """Cerrar el pool de conexiones"""
    global db_pool
    if db_pool:
        db_pool.close()
        await db_pool.wait_closed()
        print("🛑 Pool de conexiones MySQL cerrado")

async def get_user_from_db(username: str) -> Optional[dict]:
    """
    Buscar usuario en la base de datos por username
    Retorna dict con datos del usuario o None si no existe/no autorizado
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            query = """
                SELECT cargo, nro_coorporativo, usuario_telegram, estado 
                FROM cargos 
                WHERE usuario_telegram = %s AND estado = 1
            """
            await cursor.execute(query, (username,))
            result = await cursor.fetchone()
            return result

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start con verificación de autorización"""
    user = update.message.from_user
    username = user.username
    
    if not username:
        await update.message.reply_text(
            "❌ No tienes un nombre de usuario (@username) configurado en Telegram.\n"
            "Por favor configura uno en Ajustes de Telegram para poder usar este bot."
        )
        return
    
    # Agregar @ si no lo tiene
    if not username.startswith('@'):
        username = f"@{username}"
    
    print(f"Usuario intentando acceder: {username}")
    
    # Verificar en la base de datos
    user_data = await get_user_from_db(username)
    
    if not user_data:
        await update.message.reply_text(
            "🚫 **Acceso Denegado**\n\n"
            "Lo sentimos, no estás autorizado para usar este bot.\n"
            "Si crees que esto es un error, contacta con el área de sistemas."
        )
        print(f"⚠️ Acceso denegado para: {username}")
        return
    
    # Usuario autorizado
    cargo = user_data['cargo']
    nro_coorporativo = user_data['nro_coorporativo']
    
    await update.message.reply_text(
        f"✅ **Bot Display Activado**\n\n"
        f"👤 Usuario: {username}\n"
        f"🏢 Cargo: {cargo}\n"
        f"📋 Nro. Corporativo: {nro_coorporativo}\n\n"
        f"Puedes comenzar a hacer consultas relacionadas con el manual de: **{cargo}**\n"
        f"Usa /help para ver más información."
    )
    print(f"✅ Acceso autorizado: {username} - Cargo: {cargo}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help con verificación de autorización"""
    user = update.message.from_user
    username = user.username
    
    if not username:
        await update.message.reply_text("❌ No tienes un @username configurado.")
        return
    
    if not username.startswith('@'):
        username = f"@{username}"
    
    # Verificar autorización
    user_data = await get_user_from_db(username)
    if not user_data:
        await update.message.reply_text(
            "🚫 No estás autorizado para usar este bot.\n"
            "Usa /start para más información."
        )
        return
    
    help_text = f"""
📖 **Ayuda - Bot Display**

Tu área de consulta actual: **{user_data['cargo']}**

**Comandos disponibles:**
/start - Verificar acceso y ver información de tu cuenta
/help - Mostrar esta ayuda

**Cómo usar el bot:**
Simplemente escribe tu pregunta y consultaremos el manual de área asignada ({user_data['cargo']}).

**Ejemplo:**
"¿Cuáles son las responsabilidades de mi área?"
"Explícame los parámetros básicos"
    """
    await update.message.reply_text(help_text)

async def query_api(question: str, area: str) -> str:
    """Consultar la API externa"""
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
    """Manejar mensajes con verificación de autorización"""
    message_type: str = update.message.chat.type
    text: str = update.message.text
    user = update.message.from_user
    username = user.username

    print(f'User ({update.message.chat.id}) in {message_type}: "{text}"')

    # Ignorar mensajes en grupos que no mencionen al bot
    if message_type == 'group':
        if BOT_USERNAME and BOT_USERNAME in text:
            text = text.replace(BOT_USERNAME, '').strip()
        else:
            return

    # Verificar que tenga username
    if not username:
        await update.message.reply_text(
            "❌ Necesitas configurar un @username en Telegram para usar este bot."
        )
        return
    
    if not username.startswith('@'):
        username = f"@{username}"

    # Verificar autorización en la base de datos
    user_data = await get_user_from_db(username)
    
    if not user_data:
        await update.message.reply_text(
            "🚫 No estás autorizado para usar este bot.\n"
            "Usa /start para verificar tu acceso."
        )
        print(f"⚠️ Usuario no autorizado intentó consultar: {username}")
        return

    # Obtener el área (cargo) del usuario desde la BD
    user_area = user_data['cargo']
    
    # Mostrar que se está procesando la consulta
    processing_msg = await update.message.reply_text("🔍 Buscando información...")
    
    response = await query_api(text, user_area)
    
    # Eliminar el mensaje de "procesando" y enviar la respuesta
    await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_msg.message_id)
    
    print(f'Bot response for {username} (cargo: {user_area}): {response[:100]}...')
    await update.message.reply_text(response)

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar errores"""
    print(f"❌ Update {update} causó el error {context.error}")

# Crear la aplicación de Telegram
ptb_app = Application.builder().token(TOKEN).build()

# Agregar handlers
ptb_app.add_handler(CommandHandler("start", start_command))
ptb_app.add_handler(CommandHandler("help", help_command))
ptb_app.add_handler(MessageHandler(filters.TEXT, handle_message))
ptb_app.add_error_handler(error)

# Crear la aplicación FastAPI
app = FastAPI(title="Bot Display Webhook")

@app.on_event("startup")
async def startup():
    """Inicializar bot y base de datos al arrancar FastAPI"""
    # Inicializar pool de MySQL
    await init_db_pool()
    
    # Inicializar bot de Telegram
    await ptb_app.initialize()
    await ptb_app.start()
    
    # EL WEBHOOK YA NO SE REGISTRA AQUI SINO EN setup_webhook.py
    # webhook_url = f"{WEBHOOK_URL}/webhook/{TOKEN}"
    # await ptb_app.bot.set_webhook(url=webhook_url)
    # print(f"✅ Webhook configurado en: {webhook_url}")
    
    print(f"✅ Bot inicializado y listo para recibir webhooks")

@app.on_event("shutdown")
async def shutdown():
    """Limpiar recursos al cerrar la aplicación"""
    await ptb_app.stop()
    await ptb_app.shutdown()
    await close_db_pool()
    print("🛑 Bot y base de datos detenidos")

@app.post(f"/webhook/{TOKEN}")
async def telegram_webhook(request: Request):
    """Endpoint que recibe las actualizaciones de Telegram"""
    try:
        data = await request.json()
        update = Update.de_json(data, ptb_app.bot)
        await ptb_app.process_update(update)
        return {"ok": True}
    except Exception as e:
        print(f"❌ Error procesando update: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/")
async def root():
    """Endpoint raíz para verificar que el servidor está corriendo"""
    return {
        "status": "running",
        "bot": "Bot Display",
        "mode": "webhook",
        "database": "MySQL connected"
    }

@app.get("/health")
async def health():
    """Health check para servicios de monitoreo"""
    db_status = "connected" if db_pool else "disconnected"
    return {
        "status": "healthy",
        "bot_running": True,
        "database": db_status
    }

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
    if not all([DB_HOST, DB_USER, DB_PASSWORD, DB_NAME]):
        raise ValueError("❌ Faltan credenciales de MySQL en el archivo .env")
    
    print("🚀 Iniciando Bot Display con FastAPI + Webhook + MySQL")
    print(f"📡 Puerto: {PORT}")
    print(f"🌐 Webhook URL: {WEBHOOK_URL}")
    print(f"🗄️  Base de datos: {DB_NAME}@{DB_HOST}")
    
    # Ejecutar el servidor FastAPI
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT
    )