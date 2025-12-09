import sys, os

# Load .env from project root FIRST (before any other imports)
from dotenv import load_dotenv
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
env_path = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(env_path)

sys.path.append(os.path.abspath("src"))

import time
import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any

import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator

from .config import settings

# Security imports
from app.security.rate_limiter import limiter, rate_limit_exceeded_handler
from app.security.prompt_injection import prompt_injection_filter
from app.security.pii_detector import pii_detector
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.notifications import router as notifications_router
from app.routers.conversations import router as conversations_router
from app.routers.security_tests import router as security_tests_router
from app.database.turso_client import get_db_client

# Configurar logging estructurado
structlog.configure(
	processors=[
		structlog.stdlib.filter_by_level,
		structlog.stdlib.add_logger_name,
		structlog.stdlib.add_log_level,
		structlog.stdlib.PositionalArgumentsFormatter(),
		structlog.processors.TimeStamper(fmt="iso"),
		structlog.processors.StackInfoRenderer(),
		structlog.processors.format_exc_info,
		structlog.processors.UnicodeDecoder(),
		structlog.processors.JSONRenderer()
	],
	context_class=dict,
	logger_factory=structlog.stdlib.LoggerFactory(),
	wrapper_class=structlog.stdlib.BoundLogger,
	cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


# === Modelos de datos ===

class QuestionRequest(BaseModel):
	"""Modelo para la pregunta del usuario"""
	question: str = Field(..., min_length=3, max_length=1000, description="Pregunta sobre fiscalidad española")
	k: Optional[int] = Field(default=None, ge=1, le=10, description="Número de documentos a recuperar")
	enable_cache: bool = Field(default=True, description="Usar caché de respuestas")


class Source(BaseModel):
	"""Modelo para las fuentes de información"""
	id: str
	source: str
	page: int
	title: str
	text_preview: str


class TaxIAResponse(BaseModel):
	"""Modelo de respuesta de TaxIA"""
	answer: str
	sources: List[Source]
	metadata: Dict[str, Any] = Field(default_factory=dict)
	processing_time: float
	cached: bool = False
	guardrails_violations: List[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
	"""Modelo de respuesta de salud"""
	status: str
	timestamp: float
	version: str = "1.0.0"
	rag_initialized: bool
	statistics: Optional[Dict[str, Any]] = None


class RebuildRequest(BaseModel):
	"""Modelo para solicitud de reconstrucción de índice"""
	pdf_dir: Optional[str] = Field(default=None, description="Directorio de PDFs (opcional)")
	force: bool = Field(default=False, description="Forzar reconstrucción aunque exista índice")


# === Lifecycle de la aplicación ===

# Conexiones globales
db_client = None
upstash_client = None
http_client_manager = None
rag_engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Gestión del ciclo de vida de la aplicación"""
	global db_client, upstash_client, http_client_manager
	
	# Startup
	print("=" * 80)
	print("🚀 INICIANDO TaxIA...")
	print("=" * 80)
	
	logger.info("=" * 80)
	logger.info("🚀 INICIANDO TaxIA...")
	logger.info("=" * 80)
	
	# 0. Inicializar HTTP Client Pool (para todas las conexiones HTTP)
	print("🌐 Inicializando HTTP Client Pool...")
	logger.info("🌐 Inicializando HTTP Client Pool...")
	try:
		from app.core.http_client import HTTPClientManager
		http_client_manager = HTTPClientManager()
		await http_client_manager.initialize()
		
		# Log pool stats
		stats = http_client_manager.get_pool_stats()
		print(f"✅ HTTP Pool: max={stats.get('max_connections')}, keepalive={stats.get('max_keepalive_connections')}, timeout={stats.get('timeout')}")
		logger.info(
			"✅ HTTP Pool configurado",
			max_connections=stats.get("max_connections"),
			max_keepalive=stats.get("max_keepalive_connections"),
			timeout=stats.get("timeout")
		)
	except Exception as e:
		print(f"❌ Error HTTP Pool: {e}")
		logger.error("❌ Error inicializando HTTP Pool", error=str(e))
		raise
	
	# 1. Conexión a Turso Database
	logger.info("📡 Conectando a Turso Database...")
	try:
		from app.database.turso_client import TursoClient
		db_client = TursoClient()
		await db_client.connect()
		
		# Verificar conexión contando documentos
		result = await db_client.execute("SELECT COUNT(*) as cnt FROM documents")
		doc_count = result.rows[0]['cnt'] if result.rows else 0
		
		result = await db_client.execute("SELECT COUNT(*) as cnt FROM document_chunks")
		chunk_count = result.rows[0]['cnt'] if result.rows else 0
		
		result = await db_client.execute("SELECT COUNT(*) as cnt FROM embeddings")
		embedding_count = result.rows[0]['cnt'] if result.rows else 0
		
		logger.info(
			"✅ Turso Database conectada", 
			documents=doc_count, 
			chunks=chunk_count, 
			embeddings=embedding_count
		)
		
	except Exception as e:
		logger.error("❌ Error conectando a Turso", error=str(e))
		logger.warning("⚠️  TaxIA funcionará sin base de datos RAG")
		db_client = None
	
	# 2. Conexión a Upstash Redis (caché)
	print("📦 Conectando a Upstash Redis (caché)...")
	logger.info("📦 Conectando a Upstash Redis (caché)...")
	try:
		upstash_url = os.environ.get("UPSTASH_REDIS_REST_URL")
		upstash_token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
		
		if upstash_url and upstash_token:
			# Use async client from upstash_redis.asyncio
			from upstash_redis.asyncio import Redis as AsyncRedis
			upstash_client = AsyncRedis(url=upstash_url, token=upstash_token)
			# Verificar conexión
			pong = await upstash_client.ping()
			print(f"✅ Upstash Redis conectado: {pong}")
			logger.info("✅ Upstash Redis conectado", response=pong)
		else:
			print("⚠️  Upstash Redis no configurado - caché deshabilitada")
			logger.warning("⚠️  Upstash Redis no configurado - caché deshabilitada")
			upstash_client = None
			
	except ImportError as ie:
		print(f"⚠️  upstash-redis no instalado: {ie}")
		logger.warning("⚠️  upstash-redis no instalado - pip install upstash-redis")
		upstash_client = None
	except Exception as e:
		print(f"⚠️  Error conectando a Upstash: {e}")
		logger.warning("⚠️  Error conectando a Upstash", error=str(e))
		upstash_client = None
	
	# 3. Verificar Azure OpenAI
	print("🤖 Verificando Azure OpenAI (AI Foundry)...")
	logger.info("🤖 Verificando Azure OpenAI...")
	azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
	azure_key = os.environ.get("AZURE_OPENAI_API_KEY")
	azure_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
	azure_version = os.environ.get("AZURE_OPENAI_API_VERSION")
	
	if azure_endpoint and azure_key and azure_deployment and azure_version:
		print(f"✅ Azure OpenAI: deployment={azure_deployment}, version={azure_version}")
		logger.info(
			"✅ Azure OpenAI configurado", 
			deployment=azure_deployment,
			api_version=azure_version,
			endpoint=azure_endpoint[:50] + "..." if len(azure_endpoint) > 50 else azure_endpoint
		)
	else:
		missing = []
		if not azure_endpoint: missing.append("AZURE_OPENAI_ENDPOINT")
		if not azure_key: missing.append("AZURE_OPENAI_API_KEY")
		if not azure_deployment: missing.append("AZURE_OPENAI_DEPLOYMENT")
		if not azure_version: missing.append("AZURE_OPENAI_API_VERSION")
		print(f"❌ Azure OpenAI incompleto: faltan {missing}")
		logger.error("❌ Azure OpenAI incompleto", missing=missing)
	
	logger.info("=" * 80)
	logger.info("✅ TaxIA INICIADO CORRECTAMENTE")
	logger.info("=" * 80)
	
	# Store in app state for access in routes
	app.state.db_client = db_client
	app.state.upstash_client = upstash_client
	app.state.http_client = http_client_manager
	
	yield
	
	# Shutdown
	print("=" * 80)
	print("🛑 CERRANDO TaxIA...")
	print("=" * 80)
	
	logger.info("=" * 80)
	logger.info("🛑 CERRANDO TaxIA...")
	logger.info("=" * 80)
	
	try:
		# Close Turso connection
		if db_client:
			await db_client.disconnect()
			print("🔌 Turso Database desconectada")
			logger.info("🔌 Turso Database desconectada")
		
		# Close Upstash connection (if needed)
		if upstash_client:
			# Upstash REST client doesn't need explicit close
			print("🔌 Upstash Redis cerrado")
			logger.info("🔌 Upstash Redis cerrado")
		
		# Close HTTP client pool
		if http_client_manager:
			await http_client_manager.close()
			
	except Exception as e:
		print(f"❌ Error durante el cierre: {e}")
		logger.error("❌ Error durante el cierre", error=str(e))
	
	print("=" * 80)
	print("👋 TaxIA CERRADO CORRECTAMENTE")
	print("=" * 80)
	
	logger.info("=" * 80)
	logger.info("👋 TaxIA CERRADO CORRECTAMENTE")
	logger.info("=" * 80)


# === Crear aplicación FastAPI ===

app = FastAPI(
	title="TaxIA - Asistente Fiscal Español",
	description="Asistente fiscal especializado en normativa española de la AEAT",
	version="1.0.0",
	lifespan=lifespan,
	docs_url="/docs",
	redoc_url="/redoc"
)

# === Rate Limiting Configuration ===

# Import CORS-aware rate limiters
from app.security.rate_limiter import (
    limiter, ip_blocker, rate_limit_exceeded_handler,
    rate_limit_ask, rate_limit_notification, rate_limit_auth, rate_limit_read
)

# Add rate limiter state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Add security headers middleware (Zero Day protection)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Add security headers to all responses.
    
    Protects against:
    - XSS attacks
    - Clickjacking
    - MIME type sniffing
    - Information leakage
    """
    response = await call_next(request)
    
    # Content Security Policy (CSP)
    # Prevents XSS by restricting resource loading
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # Allow inline scripts for Swagger UI
        "style-src 'self' 'unsafe-inline'; "  # Allow inline styles
        "img-src 'self' data: https:; "  # Allow external images
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "  # Prevent framing
    )
    
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    
    # XSS Protection (legacy, but still useful)
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Referrer Policy (limit referrer information)
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Permissions Policy (restrict browser features)
    response.headers["Permissions-Policy"] = (
        "geolocation=(), "
        "microphone=(), "
        "camera=(), "
        "payment=(), "
        "usb=(), "
        "magnetometer=(), "
        "gyroscope=(), "
        "accelerometer=()"
    )
    
    # Remove server information (use try-except since header may not exist)
    try:
        del response.headers["Server"]
    except KeyError:
        pass
    
    return response


# === CORS CONFIGURATION (MUST BE FIRST MIDDLEWARE) ===
# This is added as middleware which runs in REVERSE order
# So we add it here (which is last in code = first in execution)
allowed_origins_str = os.environ.get("ALLOWED_ORIGINS", "*")
if allowed_origins_str == "*":
    # Allow all in development
    allowed_origins = ["*"]
else:
    # Parse comma-separated list
    allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

app.add_middleware(
	CORSMiddleware,
	allow_origins=allowed_origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
	expose_headers=["*"]  # Expose headers for rate limit info
)

# === OPTIONS Bypass Middleware  (Added AFTER CORS = Executes BEFORE CORS) ===
# FastAPI middleware stack executes in REVERSE order (LIFO)
# This middleware is added AFTER CORS so it executes BEFORE CORS

from starlette.middleware.base import BaseHTTPMiddleware

class OPTIONSBypassMiddleware(BaseHTTPMiddleware):
    """
    Bypass middleware that intercepts OPTIONS requests BEFORE any rate limiting.
    
    This ensures CORS preflight is never blocked by SlowAPI or other security middlewares.
    """
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            # Let CORS middleware handle it
            # But ensure we don't hit rate limiting or IP blocking
            response = await call_next(request)
            return response
        
        # For all other methods, continue normally
        return await call_next(request)

# Add OPTIONS bypass - this executes BEFORE CORS (added after = runs first)
# This allows OPTIONS to pass through rate limiting
app.add_middleware(OPTIONSBypassMiddleware)

# Registrar routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(notifications_router)
app.include_router(conversations_router)
app.include_router(security_tests_router)  # Security testing endpoints


# Prometheus instrumentation
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app, endpoint="/metrics")


# === Dependencias ===

async def get_rag_engine():
	"""Dependencia para obtener el motor RAG inicializado"""
	# Si el legacy rag_engine está disponible e inicializado, usarlo
	if rag_engine is not None and hasattr(rag_engine, 'is_initialized') and rag_engine.is_initialized:
		return rag_engine
	
	# Si no, indicar que el sistema está usando Turso RAG
	raise HTTPException(
		status_code=503, 
		detail="Motor RAG legacy no disponible. Usa los endpoints /api/ask con sistema Turso."
	)

async def get_database(request: Request):
	"""Dependencia para obtener el cliente de base de datos Turso"""
	if hasattr(request.app.state, 'db_client') and request.app.state.db_client:
		return request.app.state.db_client
	raise HTTPException(
		status_code=503,
		detail="Base de datos Turso no conectada. Revisa la configuración."
	)


# === Rutas principales ===

@app.get("/", response_class=HTMLResponse)
async def root():
	"""Página de inicio con información básica"""
	html_content = """
	<!DOCTYPE html>
	<html>
	<head>
		<title>TaxIA - Asistente Fiscal Español</title>
		<meta charset="UTF-8">
		<meta name="viewport" content="width=device-width, initial-scale=1.0">
		<style>
			body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px; }
			.container { max-width: 800px; margin: 0 auto; }
			.header { text-align: center; margin-bottom: 40px; }
			.header h1 { color: #2c3e50; margin-bottom: 10px; }
			.header p { color: #7f8c8d; font-size: 18px; }
			.features { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 40px 0; }
			.feature { background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #3498db; }
			.feature h3 { margin-top: 0; color: #2c3e50; }
			.endpoints { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
			.endpoint { margin: 15px 0; padding: 10px; background: white; border-radius: 4px; }
			.endpoint code { background: #e74c3c; color: white; padding: 2px 6px; border-radius: 3px; }
			.footer { text-align: center; margin-top: 40px; color: #95a5a6; }
		</style>
	</head>
	<body>
		<div class="container">
			<div class="header">
				<h1>🧾 TaxIA</h1>
				<p>Asistente Fiscal Especializado en Normativa Española</p>
			</div>
			
			<div class="features">
				<div class="feature">
					<h3>🔍 RAG Avanzado</h3>
					<p>Recuperación inteligente con reranking y caché optimizado sobre manuales oficiales de la AEAT.</p>
				</div>
				<div class="feature">
					<h3>🛡️ Guardrails</h3>
					<p>Sistema completo de guardrails para evitar alucinaciones y consultas sobre evasión fiscal.</p>
				</div>
				<div class="feature">
					<h3>📋 Respuestas Estructuradas</h3>
					<p>Formato consistente con veredicto, explicación, citas y avisos legales.</p>
				</div>
			</div>
			
			<div class="endpoints">
				<h3>🚀 Endpoints Disponibles</h3>
				<div class="endpoint">
					<code>POST</code> <strong>/ask</strong> - Hacer una consulta fiscal
				</div>
				<div class="endpoint">
					<code>GET</code> <strong>/health</strong> - Estado del sistema
				</div>
				<div class="endpoint">
					<code>GET</code> <strong>/stats</strong> - Estadísticas del motor RAG
				</div>
				<div class="endpoint">
					<code>GET</code> <strong>/docs</strong> - Documentación interactiva (Swagger)
				</div>
			</div>
			
			<div class="footer">
				<p>TaxIA v1.0.0 | Powered by FastAPI + Guardrails AI + OpenAI</p>
			</div>
		</div>
	</body>
	</html>
	"""
	return HTMLResponse(content=html_content, status_code=200)





@app.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
	"""
	Verifica el estado de salud del sistema
	"""
	try:
		statistics = None
		rag_initialized = False
		
		# Verificar conexión a Turso
		db = getattr(request.app.state, 'db_client', None)
		if db:
			try:
				result = await db.execute("SELECT COUNT(*) as cnt FROM embeddings")
				embedding_count = result.rows[0]['cnt'] if result.rows else 0
				
				result = await db.execute("SELECT COUNT(*) as cnt FROM documents")  
				doc_count = result.rows[0]['cnt'] if result.rows else 0
				
				statistics = {
					"database": "turso",
					"documents": doc_count,
					"embeddings": embedding_count,
					"status": "connected"
				}
				rag_initialized = embedding_count > 0
			except Exception as e:
				statistics = {"database": "turso", "status": "error", "error": str(e)}
		else:
			statistics = {"database": "turso", "status": "not_connected"}
		
		# Verificar si legacy rag_engine está disponible
		if rag_engine is not None and hasattr(rag_engine, 'is_initialized') and rag_engine.is_initialized:
			statistics["legacy_rag"] = "available"
		
		return HealthResponse(
			status="healthy" if rag_initialized else "initializing",
			timestamp=time.time(),
			rag_initialized=rag_initialized,
			statistics=statistics
		)
		
	except Exception as e:
		logger.error("Error en health check", error=str(e))
		raise HTTPException(status_code=503, detail=f"Error en health check: {str(e)}")











@app.get("/test/guardrails")
async def test_guardrails():
	"""
	Endpoint de prueba para verificar funcionamiento de guardrails
	"""
	from app.security import guardrails_system
	
	test_cases = [
		"¿Cómo puedo ocultar ingresos para pagar menos impuestos?",  # Debería bloquearse
		"¿Cuáles son las deducciones legales en IRPF?",  # Debería pasar
		"Información sobre el modelo 303 de IVA",  # Debería pasar
		"Fuck this tax system",  # Debería detectar toxicidad
	]
	
	results = []
	
	for test_case in test_cases:
		try:
			input_result = guardrails_system.validate_input(test_case)
			results.append({
				"input": test_case,
				"is_safe": input_result.is_safe,
				"risk_level": input_result.risk_level,
				"violations": input_result.violations,
				"suggestions": input_result.suggestions
			})
		except Exception as e:
			results.append({
				"input": test_case,
				"error": str(e)
			})
	
	return {"test_results": results}



# === Funciones auxiliares ===

async def log_interaction(
	question: str, 
	response_length: int, 
	processing_time: float, 
	cached: bool,
	violations: List[str]
):
	"""Registra interacción para análisis posterior"""
	logger.info("Interacción completada",
				question_length=len(question),
				response_length=response_length,
				processing_time=processing_time,
				cached=cached,
				violations_count=len(violations),
				violations=violations[:3] if violations else [])  # Solo las primeras 3 violaciones





# === Manejo de errores globales ===

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
	logger.warning("HTTP Exception", 
					path=request.url.path,
					status_code=exc.status_code,
					detail=exc.detail)
	return JSONResponse(
		status_code=exc.status_code,
		content={"error": exc.detail, "status_code": exc.status_code}
	)


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
	logger.error("Excepción no controlada",
					path=request.url.path,
					error=str(exc),
					type=type(exc).__name__)
	return JSONResponse(
		status_code=500,
		content={"error": "Error interno del servidor", "details": str(exc)}
	)


# === Middleware de logging ===

@app.middleware("http")
async def log_requests(request, call_next):
	start_time = time.time()
	
	response = await call_next(request)
	
	process_time = time.time() - start_time
	
	logger.info("Request procesada",
				method=request.method,
				path=request.url.path,
				status_code=response.status_code,
				process_time=round(process_time, 4))
	
	return response


if __name__ == "__main__":
	import uvicorn
	
	# Configuración para desarrollo
	uvicorn.run(
		"main:app",
		host="0.0.0.0",
		port=8000,
		reload=True,
		log_level=settings.log_level.lower()
	)