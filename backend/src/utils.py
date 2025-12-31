import os
import time
import hashlib
import asyncio
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import logging

import requests
from openai import OpenAI

from config import settings

logger = logging.getLogger(__name__)


class ModelDownloader:
	"""Descarga y verifica modelos de ML necesarios"""
	
	def __init__(self):
		self.models_dir = Path("./models")
		self.models_dir.mkdir(exist_ok=True)
	
	async def download_model_if_needed(self, model_name: str) -> bool:
		"""Descarga un modelo si no existe localmente"""
		try:
			from sentence_transformers import SentenceTransformer
			
			# Intentar cargar el modelo (descarga automática si no existe)
			model = SentenceTransformer(model_name)
			logger.info(f"Modelo {model_name} disponible")
			return True
			
		except Exception as e:
			logger.error(f"Error descargando modelo {model_name}: {e}")
			return False
	
	async def verify_all_models(self) -> Dict[str, bool]:
		"""Verifica que todos los modelos necesarios estén disponibles"""
		models_status = {}
		
		required_models = [
			settings.embedding_model,
			settings.reranking_model
		]
		
		for model_name in required_models:
			status = await self.download_model_if_needed(model_name)
			models_status[model_name] = status
		
		return models_status


class SystemValidator:
	"""Valida que el sistema tenga todo lo necesario para funcionar"""
	
	@staticmethod
	def validate_openai_key() -> bool:
		"""Valida que la API key de OpenAI funcione"""
		try:
			client = OpenAI(api_key=settings.openai_api_key)
			
			# Hacer una llamada mínima para validar la key
			response = client.chat.completions.create(
				model=settings.OPENAI_MODEL,
				messages=[{"role": "user", "content": "test"}],
				max_tokens=1
			)
			
			logger.info("API key de OpenAI validada correctamente")
			return True
			
		except Exception as e:
			logger.error(f"Error validando API key de OpenAI: {e}")
			return False
	
	@staticmethod
	def validate_directories() -> Dict[str, bool]:
		"""Valida que todos los directorios necesarios existan"""
		dirs_status = {}
		
		required_dirs = [
			settings.pdf_dir,
			settings.cache_dir,
			os.path.dirname(settings.parquet_path),
		]
		
		for dir_path in required_dirs:
			try:
				os.makedirs(dir_path, exist_ok=True)
				dirs_status[dir_path] = os.path.exists(dir_path) and os.access(dir_path, os.W_OK)
			except Exception as e:
				logger.error(f"Error con directorio {dir_path}: {e}")
				dirs_status[dir_path] = False
		
		return dirs_status
	
	@staticmethod
	def validate_pdf_files() -> Dict[str, Any]:
		"""Valida archivos PDF disponibles"""
		pdf_dir = Path(settings.pdf_dir)
		
		if not pdf_dir.exists():
			return {
				"status": False,
				"message": f"Directorio {pdf_dir} no existe",
				"files": []
			}
		
		pdf_files = list(pdf_dir.glob("*.pdf"))
		
		if not pdf_files:
			return {
				"status": False,
				"message": f"No se encontraron archivos PDF en {pdf_dir}",
				"files": []
			}
		
		# Verificar que los archivos sean legibles
		valid_files = []
		invalid_files = []
		
		for pdf_file in pdf_files:
			try:
				from pypdf import PdfReader
				reader = PdfReader(pdf_file)
				if len(reader.pages) > 0:
					valid_files.append({
						"name": pdf_file.name,
						"size": pdf_file.stat().st_size,
						"pages": len(reader.pages)
					})
				else:
					invalid_files.append(pdf_file.name)
			except Exception as e:
				logger.warning(f"PDF inválido {pdf_file.name}: {e}")
				invalid_files.append(pdf_file.name)
		
		return {
			"status": len(valid_files) > 0,
			"message": f"Encontrados {len(valid_files)} archivos PDF válidos",
			"valid_files": valid_files,
			"invalid_files": invalid_files,
			"total_files": len(pdf_files)
		}
	
	@staticmethod
	async def run_full_validation() -> Dict[str, Any]:
		"""Ejecuta validación completa del sistema"""
		logger.info("Iniciando validación completa del sistema...")
		
		results = {
			"timestamp": time.time(),
			"openai_key": SystemValidator.validate_openai_key(),
			"directories": SystemValidator.validate_directories(),
			"pdf_files": SystemValidator.validate_pdf_files(),
			"models": {}
		}
		
		# Validar modelos
		downloader = ModelDownloader()
		results["models"] = await downloader.verify_all_models()
		
		# Calcular estado general
		results["overall_status"] = (
			results["openai_key"] and
			all(results["directories"].values()) and
			results["pdf_files"]["status"] and
			all(results["models"].values())
		)
		
		if results["overall_status"]:
			logger.info("✅ Validación completa exitosa")
		else:
			logger.warning("⚠️ Algunas validaciones fallaron")
		
		return results


class DataProcessor:
	"""Utilidades para procesamiento de datos"""
	
	@staticmethod
	def calculate_chunk_stats(text_chunks: List[str]) -> Dict[str, Any]:
		"""Calcula estadísticas de chunks de texto"""
		if not text_chunks:
			return {"error": "No hay chunks para analizar"}
		
		lengths = [len(chunk) for chunk in text_chunks]
		word_counts = [len(chunk.split()) for chunk in text_chunks]
		
		return {
			"total_chunks": len(text_chunks),
			"total_characters": sum(lengths),
			"total_words": sum(word_counts),
			"avg_chunk_length": sum(lengths) / len(lengths),
			"avg_words_per_chunk": sum(word_counts) / len(word_counts),
			"min_chunk_length": min(lengths),
			"max_chunk_length": max(lengths),
			"chunks_under_100_chars": sum(1 for l in lengths if l < 100),
			"chunks_over_2000_chars": sum(1 for l in lengths if l > 2000)
		}
	
	@staticmethod
	def extract_model_references(text: str) -> List[str]:
		"""Extrae referencias a modelos fiscales del texto"""
		import re
		
		model_patterns = [
			r'\bModelo\s+(\d{3}[A-Z]?)\b',
			r'\b(\d{3}[A-Z]?)\b(?=.*(?:declaración|presentar|formulario))',
			r'\bformulario\s+(\d{3}[A-Z]?)\b'
		]
		
		models_found = set()
		
		for pattern in model_patterns:
			matches = re.findall(pattern, text, re.IGNORECASE)
			models_found.update(matches)
		
		return sorted(list(models_found))
	
	@staticmethod
	def detect_fiscal_topics(text: str) -> List[str]:
		"""Detecta temas fiscales en el texto"""
		import re
		
		topic_patterns = {
			"IRPF": r'\b(?:IRPF|Impuesto.*Renta|renta.*personas)\b',
			"IVA": r'\b(?:IVA|Impuesto.*Valor.*Añadido)\b',
			"Sociedades": r'\b(?:Impuesto.*Sociedades|IS)\b',
			"Patrimonio": r'\b(?:Impuesto.*Patrimonio)\b',
			"Sucesiones": r'\b(?:Impuesto.*Sucesiones|Donaciones)\b',
			"Aduanas": r'\b(?:aduanas?|aranceles?|DUA)\b',
			"Seguridad Social": r'\b(?:Seguridad Social|cotizaciones?)\b'
		}
		
		topics_found = []
		
		for topic, pattern in topic_patterns.items():
			if re.search(pattern, text, re.IGNORECASE):
				topics_found.append(topic)
		
		return topics_found


class PerformanceMonitor:
	"""Monitor de rendimiento del sistema"""
	
	def __init__(self):
		self.metrics = {
			"requests": 0,
			"total_time": 0.0,
			"avg_time": 0.0,
			"cache_hits": 0,
			"cache_misses": 0,
			"errors": 0
		}
	
	def record_request(self, processing_time: float, cached: bool = False, error: bool = False):
		"""Registra métricas de una request"""
		self.metrics["requests"] += 1
		self.metrics["total_time"] += processing_time
		self.metrics["avg_time"] = self.metrics["total_time"] / self.metrics["requests"]
		
		if cached:
			self.metrics["cache_hits"] += 1
		else:
			self.metrics["cache_misses"] += 1
		
		if error:
			self.metrics["errors"] += 1
	
	def get_cache_ratio(self) -> float:
		"""Obtiene la ratio de cache hits"""
		total_requests = self.metrics["cache_hits"] + self.metrics["cache_misses"]
		if total_requests == 0:
			return 0.0
		return self.metrics["cache_hits"] / total_requests
	
	def get_error_rate(self) -> float:
		"""Obtiene la tasa de errores"""
		if self.metrics["requests"] == 0:
			return 0.0
		return self.metrics["errors"] / self.metrics["requests"]
	
	def get_stats(self) -> Dict[str, Any]:
		"""Obtiene todas las estadísticas"""
		return {
			**self.metrics,
			"cache_ratio": self.get_cache_ratio(),
			"error_rate": self.get_error_rate()
		}
	
	def reset_stats(self):
		"""Reinicia las estadísticas"""
		self.metrics = {
			"requests": 0,
			"total_time": 0.0,
			"avg_time": 0.0,
			"cache_hits": 0,
			"cache_misses": 0,
			"errors": 0
		}


class ConfigValidator:
	"""Validador de configuración"""
	
	@staticmethod
	def validate_config() -> Dict[str, Any]:
		"""Valida la configuración actual"""
		issues = []
		warnings = []
		
		# Validar API key
		if not settings.openai_api_key or "your" in settings.openai_api_key.lower():
			issues.append("OPENAI_API_KEY no está configurada o contiene valor placeholder")
		
		# Validar rutas
		if not os.path.exists(settings.pdf_dir):
			issues.append(f"Directorio PDF {settings.pdf_dir} no existe")
		
		# Validar configuración de chunking
		if settings.chunk_overlap >= settings.chunk_size:
			issues.append("CHUNK_OVERLAP debe ser menor que CHUNK_SIZE")
		
		if settings.chunk_size < 200:
			warnings.append("CHUNK_SIZE muy pequeño, podría afectar la calidad")
		
		if settings.chunk_size > 2000:
			warnings.append("CHUNK_SIZE muy grande, podría afectar el rendimiento")
		
		# Validar configuración de retrieval
		if settings.retrieval_k < 1:
			issues.append("RETRIEVAL_K debe ser mayor que 0")
		
		if settings.retrieval_k > 20:
			warnings.append("RETRIEVAL_K muy alto, podría afectar el rendimiento")
		
		# Validar thresholds
		if not 0 <= settings.toxicity_threshold <= 1:
			issues.append("TOXICITY_THRESHOLD debe estar entre 0 y 1")
		
		if not 0 <= settings.hallucination_threshold <= 1:
			issues.append("HALLUCINATION_THRESHOLD debe estar entre 0 y 1")
		
		return {
			"valid": len(issues) == 0,
			"issues": issues,
			"warnings": warnings,
			"config_summary": {
				"embedding_model": settings.embedding_model,
				"chunk_size": settings.chunk_size,
				"retrieval_k": settings.retrieval_k,
				"guardrails_enabled": settings.enable_guardrails
			}
		}


# Instancias globales
performance_monitor = PerformanceMonitor()


# Funciones de utilidad independientes

def hash_text(text: str) -> str:
	"""Genera hash MD5 de un texto"""
	return hashlib.md5(text.encode()).hexdigest()


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
	"""Trunca texto a longitud máxima"""
	if len(text) <= max_length:
		return text
	return text[:max_length - len(suffix)] + suffix


def format_file_size(size_bytes: int) -> str:
	"""Formatea tamaño de archivo en formato humano"""
	for unit in ['B', 'KB', 'MB', 'GB']:
		if size_bytes < 1024.0:
			return f"{size_bytes:.1f} {unit}"
		size_bytes /= 1024.0
	return f"{size_bytes:.1f} TB"


def sanitize_filename(filename: str) -> str:
	"""Sanitiza nombre de archivo para uso seguro"""
	import re
	# Eliminar caracteres peligrosos
	sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
	# Limitar longitud
	sanitized = sanitized[:255]
	return sanitized


async def test_model_loading():
	"""Función de prueba para verificar carga de modelos"""
	try:
		from sentence_transformers import SentenceTransformer, CrossEncoder
		
		print("🧪 Probando carga de modelos...")
		
		# Probar embedding model
		print(f"Cargando embedding model: {settings.embedding_model}")
		embedder = SentenceTransformer(settings.embedding_model)
		test_emb = embedder.encode(["prueba"])
		print(f"✅ Embedding model cargado. Dimensión: {len(test_emb[0])}")
		
		# Probar reranking model
		print(f"Cargando reranking model: {settings.reranking_model}")
		reranker = CrossEncoder(settings.reranking_model)
		test_score = reranker.predict([("pregunta test", "respuesta test")])
		print(f"✅ Reranking model cargado. Score test: {test_score[0]:.3f}")
		
		print("✅ Todos los modelos cargados correctamente")
		return True
		
	except Exception as e:
		print(f"❌ Error cargando modelos: {e}")
		return False


if __name__ == "__main__":
	# Script de pruebas cuando se ejecuta directamente
	import asyncio
	
	async def main():
		print("🔍 Ejecutando validación completa del sistema...")
		
		# Validar configuración
		config_status = ConfigValidator.validate_config()
		print(f"Configuración válida: {config_status['valid']}")
		
		if config_status['issues']:
			print("❌ Problemas encontrados:")
			for issue in config_status['issues']:
				print(f"  - {issue}")
		
		if config_status['warnings']:
			print("⚠️ Advertencias:")
			for warning in config_status['warnings']:
				print(f"  - {warning}")
		
		# Validar sistema
		system_status = await SystemValidator.run_full_validation()
		print(f"\nEstado general del sistema: {'✅' if system_status['overall_status'] else '❌'}")
		
		# Probar modelos
		await test_model_loading()
	
	asyncio.run(main())