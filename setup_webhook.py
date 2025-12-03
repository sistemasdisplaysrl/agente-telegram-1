import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import RetryAfter, TimedOut, NetworkError
import time

load_dotenv()

TOKEN = os.getenv('TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

async def setup_webhook():
    bot = Bot(token=TOKEN)
    expected_webhook_url = f"{WEBHOOK_URL}/webhook/{TOKEN}"
    
    print("🔍 Verificando configuración actual del webhook...")
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Obtener información actual del webhook
            webhook_info = await bot.get_webhook_info()
            current_url = webhook_info.url
            
            print(f"📡 URL actual: {current_url if current_url else 'No configurado'}")
            print(f"📡 URL esperada: {expected_webhook_url}")
            
            # Verificar si ya está configurado correctamente
            if current_url == expected_webhook_url:
                print("✅ Webhook ya está configurado correctamente")
                print(f"📊 Updates pendientes: {webhook_info.pending_update_count}")
                
                if webhook_info.last_error_message:
                    print(f"⚠️  Último error: {webhook_info.last_error_message}")
                    print(f"🔧 Reconfigurar de todos modos...")
                    # Si hay errores, reconfigurar
                    await bot.set_webhook(url=expected_webhook_url)
                    print("✅ Webhook reconfigurado")
                else:
                    print("✨ No es necesario hacer cambios")
                
                await bot.close()
                return
            
            # Si la URL es diferente o no está configurado, proceder
            print("🔧 La URL es diferente, actualizando webhook...")
            
            # Solo eliminar si existe un webhook anterior
            if current_url:
                print(f"🗑️  Eliminando webhook anterior: {current_url}")
                await bot.delete_webhook(drop_pending_updates=True)
                print("✅ Webhook anterior eliminado")
                # Pequeña pausa para evitar rate limit
                await asyncio.sleep(1)
            
            # Configurar nuevo webhook
            print(f"⚙️  Configurando nuevo webhook...")
            result = await bot.set_webhook(url=expected_webhook_url)
            
            if result:
                print("✅ Webhook configurado exitosamente")
                
                # Verificar la nueva configuración
                await asyncio.sleep(1)
                new_info = await bot.get_webhook_info()
                print(f"📡 URL configurada: {new_info.url}")
                print(f"📊 Updates pendientes: {new_info.pending_update_count}")
            else:
                print("❌ Error al configurar webhook")
            
            await bot.close()
            return
            
        except RetryAfter as e:
            retry_count += 1
            wait_time = e.retry_after + 5  # Agregar 5 segundos extra por seguridad
            print(f"⏳ Flood control detectado. Esperando {wait_time} segundos...")
            print(f"   (Intento {retry_count}/{max_retries})")
            
            if retry_count < max_retries:
                time.sleep(wait_time)
            else:
                print("❌ Máximo de reintentos alcanzado")
                print("💡 Sugerencia: Espera unos minutos antes de reiniciar el contenedor")
                await bot.close()
                raise
                
        except (TimedOut, NetworkError) as e:
            retry_count += 1
            print(f"⚠️  Error de red: {e}")
            print(f"   (Intento {retry_count}/{max_retries})")
            
            if retry_count < max_retries:
                print("⏳ Reintentando en 5 segundos...")
                await asyncio.sleep(5)
            else:
                print("❌ No se pudo conectar después de varios intentos")
                await bot.close()
                raise
                
        except Exception as e:
            print(f"❌ Error inesperado: {type(e).__name__}: {e}")
            await bot.close()
            raise

if __name__ == "__main__":
    try:
        asyncio.run(setup_webhook())
    except KeyboardInterrupt:
        print("\n⚠️  Operación cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        exit(1)