import multiprocessing
import os

# ===== CONFIGURACIÓN DE WORKERS =====
workers = 3

# Tipo de worker - IMPORTANTE: usar uvicorn para FastAPI
worker_class = "uvicorn.workers.UvicornWorker"

# Threads por worker (para I/O bound como requests a MySQL y API)
threads = 2

# ===== BINDING =====
# Dirección y puerto donde escucha Gunicorn
bind = "0.0.0.0:8443"

# ===== TIMEOUTS =====
# Timeout para requests (30 segundos es suficiente para tu query_api)
timeout = 30

# Timeout para workers silenciosos (detectar workers colgados)
graceful_timeout = 30

# Keep-alive para conexiones persistentes
keepalive = 5

# ===== LOGGING =====
# Nivel de log
loglevel = "info"

# Archivo de log de acceso (requests recibidos), requiere carpeta /logs
# accesslog = "logs/access.log"

# Archivo de log de errores
# errorlog = "logs/error.log"

# Formato de log de acceso
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Capturar salida estándar en los logs
capture_output = True

# ===== PROCESS NAMING =====
# Nombre del proceso para identificarlo fácilmente
proc_name = "bot_display_webhook"

# ===== SEGURIDAD =====
# Limitar el tamaño del header (prevenir ataques)
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# ===== PERFORMANCE =====
# Reiniciar workers después de N requests (prevenir memory leaks)
max_requests = 1000
max_requests_jitter = 50  # Añade aleatoriedad para evitar reinicios simultáneos

# Pre-cargar la aplicación antes de fork (ahorra memoria)
preload_app = False  # False porque python-telegram-bot maneja estado

# ===== RESTART Y RELOAD =====
# Reiniciar workers gradualmente cuando hay cambios
reload = False  # True solo en desarrollo

# Archivos a monitorear para auto-reload (solo desarrollo)
# reload_extra_files = []

# ===== HOOKS =====
def on_starting(server):
    """Ejecutado antes de que el master process se inicie"""
    print("🚀 Iniciando Gunicorn para Bot Display")
    
    # Crear directorio de logs si no existe
    # os.makedirs("logs", exist_ok=True)

def on_reload(server):
    """Ejecutado cuando se recarga la configuración"""
    print("🔄 Recargando configuración de Gunicorn")

def when_ready(server):
    """Ejecutado cuando el servidor está listo para recibir requests"""
    print("✅ Gunicorn está listo y escuchando en", bind)
    print(f"📊 Workers: {workers} | Threads por worker: {threads}")

def worker_int(worker):
    """Ejecutado cuando un worker recibe SIGINT o SIGQUIT"""
    print(f"⚠️  Worker {worker.pid} interrumpido")

def worker_abort(worker):
    """Ejecutado cuando un worker es abortado"""
    print(f"❌ Worker {worker.pid} abortado")

def pre_fork(server, worker):
    """Ejecutado justo antes de hacer fork de un worker"""
    pass

def post_fork(server, worker):
    """Ejecutado en el worker después del fork"""
    print(f"👶 Worker {worker.pid} iniciado")

def pre_exec(server):
    """Ejecutado antes de re-ejecutar el master"""
    print("🔄 Re-ejecutando master process")

def pre_request(worker, req):
    """Ejecutado antes de procesar cada request"""
    # Descomenta para debug detallado
    # print(f"📥 Request: {req.method} {req.path}")
    pass

def post_request(worker, req, environ, resp):
    """Ejecutado después de procesar cada request"""
    # Descomenta para debug detallado
    # print(f"📤 Response: {resp.status}")
    pass

def worker_exit(server, worker):
    """Ejecutado cuando un worker termina"""
    print(f"👋 Worker {worker.pid} terminado")

def nworkers_changed(server, new_value, old_value):
    """Ejecutado cuando cambia el número de workers"""
    print(f"📊 Workers cambiados: {old_value} → {new_value}")

def on_exit(server):
    """Ejecutado cuando el master process termina"""
    print("🛑 Gunicorn detenido")