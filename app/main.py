import sys, os
sys.path.append(os.path.abspath("src"))

import time
import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any

import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .config import settings
from rag_engine import rag_engine, RAGEngine
from taxia_guardrails import guardrails_system

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

@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Gestión del ciclo de vida de la aplicación"""
	# Startup
	logger.info("Iniciando TaxIA...")
	
	try:
		# Inicializar motor RAG
		rag_engine.initialize()
		
		logger.info("TaxIA iniciado correctamente", 
					chunks=len(rag_engine.df) if rag_engine.df is not None else 0,
					embedding_model=settings.embedding_model)
		
	except Exception as e:
		logger.error("Error durante el inicio", error=str(e))
		raise
	
	yield
	
	# Shutdown
	logger.info("Cerrando TaxIA...")
	
	try:
		# Guardar cachés
		if rag_engine.cache_manager:
			rag_engine.cache_manager.save_all_caches()
			logger.info("Cachés guardados correctamente")
		
	except Exception as e:
		logger.error("Error durante el cierre", error=str(e))
	
	logger.info("TaxIA cerrado correctamente")


# === Crear aplicación FastAPI ===

app = FastAPI(
	title="TaxIA - Asistente Fiscal Español",
	description="Asistente fiscal especializado en normativa española de la AEAT",
	version="1.0.0",
	lifespan=lifespan,
	docs_url="/docs",
	redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # En producción, especificar dominios exactos
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


# === Dependencias ===

async def get_rag_engine():
	"""Dependencia para obtener el motor RAG inicializado"""
	if not rag_engine.is_initialized:
		raise HTTPException(
			status_code=503, 
			detail="Motor RAG no inicializado. Consulta /health para más información."
		)
	return rag_engine


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


@app.post("/ask", response_model=TaxIAResponse)
async def ask_question(
	request: QuestionRequest,
	background_tasks: BackgroundTasks,
	rag: RAGEngine = Depends(get_rag_engine)
):
	"""
	Hace una consulta fiscal a TaxIA
	
	- **question**: La pregunta sobre fiscalidad española
	- **k**: Número de documentos a recuperar (opcional, por defecto desde config)
	- **enable_cache**: Usar caché de respuestas (opcional, por defecto True)
	"""
	start_time = time.time()
	
	try:
		logger.info("Nueva consulta recibida", 
					question=request.question[:100] + "..." if len(request.question) > 100 else request.question,
					k=request.k)
		
		# Generar respuesta
		result = rag.generate_response(
			query=request.question,
			k=request.k or settings.retrieval_k
		)
		
		processing_time = time.time() - start_time
		
		# Formatear fuentes
		sources = [
			Source(**source_data) for source_data in result["sources"]
		]
		
		# Preparar metadatos
		metadata = {
			"retrieval_time": result.get("retrieval_time", 0),
			"rerank_time": result.get("rerank_time", 0),
			"similarity_scores": result.get("similarity_scores", []),
			"rerank_scores": result.get("rerank_scores", []),
			"model_used": settings.openai_model,
			"embedding_model": settings.embedding_model,
			"k_retrieved": len(sources)
		}
		
		response = TaxIAResponse(
			answer=result["answer"],
			sources=sources,
			metadata=metadata,
			processing_time=processing_time,
			cached=result.get("cached", False),
			guardrails_violations=result.get("guardrails_violations", [])
		)
		
		# Log de respuesta (en background)
		background_tasks.add_task(
			log_interaction,
			question=request.question,
			response_length=len(result["answer"]),
			processing_time=processing_time,
			cached=result.get("cached", False),
			violations=result.get("guardrails_violations", [])
		)
		
		return response
		
	except Exception as e:
		logger.error("Error procesando consulta", error=str(e), question=request.question)
		raise HTTPException(status_code=500, detail=f"Error procesando consulta: {str(e)}")


@app.get("/health", response_model=HealthResponse)
async def health_check():
	"""
	Verifica el estado de salud del sistema
	"""
	try:
		statistics = None
		
		if rag_engine.is_initialized:
			statistics = rag_engine.get_statistics()
		
		return HealthResponse(
			status="healthy" if rag_engine.is_initialized else "initializing",
			timestamp=time.time(),
			rag_initialized=rag_engine.is_initialized,
			statistics=statistics
		)
		
	except Exception as e:
		logger.error("Error en health check", error=str(e))
		raise HTTPException(status_code=503, detail=f"Error en health check: {str(e)}")


@app.get("/stats")
async def get_statistics(rag: RAGEngine = Depends(get_rag_engine)):
	"""
	Obtiene estadísticas detalladas del motor RAG
	"""
	try:
		return rag.get_statistics()
		
	except Exception as e:
		logger.error("Error obteniendo estadísticas", error=str(e))
		raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")


@app.post("/admin/rebuild")
async def rebuild_index(
	request: RebuildRequest,
	background_tasks: BackgroundTasks,
	api_key: str = Query(..., description="API key de administración")
):
	"""
	Reconstruye el índice RAG (solo para administradores)
	
	Requiere API key de administración en query parameter.
	"""
	# Verificación simple de API key (mejorar en producción)
	if api_key != os.getenv("ADMIN_API_KEY", "admin123"):
		raise HTTPException(status_code=403, detail="API key de administración inválida")
	
	try:
		logger.info("Iniciando reconstrucción de índice", 
					pdf_dir=request.pdf_dir, 
					force=request.force)
		
		# Reconstruir en background
		background_tasks.add_task(
			rebuild_index_task, 
			pdf_dir=request.pdf_dir or settings.pdf_dir
		)
		
		return {
			"message": "Reconstrucción de índice iniciada en background",
			"pdf_dir": request.pdf_dir or settings.pdf_dir,
			"status": "iniciado"
		}
		
	except Exception as e:
		logger.error("Error iniciando reconstrucción", error=str(e))
		raise HTTPException(status_code=500, detail=f"Error iniciando reconstrucción: {str(e)}")


@app.get("/admin/cache/clear")
async def clear_cache(api_key: str = Query(..., description="API key de administración")):
	"""
	Limpia los cachés del sistema (solo para administradores)
	"""
	if api_key != os.getenv("ADMIN_API_KEY", "admin123"):
		raise HTTPException(status_code=403, detail="API key de administración inválida")
	
	try:
		if rag_engine.cache_manager:
			embeddings_count = len(rag_engine.cache_manager.embeddings_cache)
			responses_count = len(rag_engine.cache_manager.responses_cache)
			
			rag_engine.cache_manager.embeddings_cache.clear()
			rag_engine.cache_manager.responses_cache.clear()
			rag_engine.cache_manager.save_all_caches()
			
			logger.info("Cachés limpiados", 
						embeddings_cleared=embeddings_count,
						responses_cleared=responses_count)
			
			return {
				"message": "Cachés limpiados correctamente",
				"embeddings_cleared": embeddings_count,
				"responses_cleared": responses_count
			}
		else:
			return {"message": "Cache manager no inicializado"}
			
	except Exception as e:
		logger.error("Error limpiando cachés", error=str(e))
		raise HTTPException(status_code=500, detail=f"Error limpiando cachés: {str(e)}")


@app.get("/test/guardrails")
async def test_guardrails():
	"""
	Endpoint de prueba para verificar funcionamiento de guardrails
	"""
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
				"passed": input_result.passed,
				"violations": input_result.violations,
				"output": input_result.content[:100] + "..." if len(input_result.content) > 100 else input_result.content
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


async def rebuild_index_task(pdf_dir: str):
	"""Tarea de reconstrucción de índice en background"""
	try:
		logger.info("Iniciando reconstrucción de índice en background", pdf_dir=pdf_dir)
		rag_engine.rebuild_index(pdf_dir)
		logger.info("Reconstrucción de índice completada")
		
	except Exception as e:
		logger.error("Error en reconstrucción de índice", error=str(e))


# === Manejo de errores globales ===

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
	logger.warning("HTTP Exception", 
					path=request.url.path,
					status_code=exc.status_code,
					detail=exc.detail)
	return {"error": exc.detail, "status_code": exc.status_code}


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
	logger.error("Excepción no controlada",
					path=request.url.path,
					error=str(exc),
					type=type(exc).__name__)
	return {"error": "Error interno del servidor", "status_code": 500}


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