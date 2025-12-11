"""
Web Search Tool for Tax Regulations
Searches official sources for updated tax information
"""
import logging
import httpx
from typing import Dict, Any
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


async def search_tax_regulations_tool(
	query: str,
	year: int = 2025,
	max_results: int = 3
) -> Dict[str, Any]:
	"""
	Busca información fiscal actualizada en fuentes oficiales españolas.
	
	Args:
		query: Consulta de búsqueda (ej: "tramos IRPF madrid 2025")
		year: Año fiscal para la búsqueda (default: 2025)
		max_results: Número máximo de resultados (default: 3)
		
	Returns:
		Dict con resultados de búsqueda
	"""
	try:
		logger.info(f"Searching tax regulations: query='{query}', year={year}")
		
		# Fuentes oficiales prioritarias
		sources = [
			f"site:agenciatributaria.es {query} {year}",
			f"site:boe.es {query} {year}",
			f"site:seg-social.es {query} {year}",
		]
		
		results = []
		
		# Usar DuckDuckGo HTML API (no requiere API key)
		for source_query in sources[:max_results]:
			try:
				search_url = "https://html.duckduckgo.com/html/"
				
				async with httpx.AsyncClient(timeout=10.0) as client:
					response = await client.post(
						search_url,
						data={"q": source_query},
						headers={
							"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
						}
					)
					
					if response.status_code == 200:
						soup = BeautifulSoup(response.text, 'html.parser')
						search_results = soup.find_all('a', class_='result__a', limit=2)
						
						for result in search_results:
							title = result.get_text(strip=True)
							url = result.get('href', '')
							
							if url and any(domain in url for domain in ['agenciatributaria.es', 'boe.es', 'seg-social.es']):
								results.append({
									"title": title,
									"url": url,
									"source": "AEAT" if "agenciatributaria" in url else "BOE" if "boe" in url else "Seguridad Social"
								})
			
			except Exception as e:
				logger.warning(f"Error searching {source_query}: {e}")
				continue
		
		if not results:
			return {
				"success": False,
				"error": "No se encontraron resultados en fuentes oficiales",
				"formatted_response": f"No encontré información actualizada de {year} en AEAT, BOE o Seguridad Social. La documentación que tengo puede estar desactualizada. Te recomiendo consultar directamente en www.agenciatributaria.es"
			}
		
		# Formatear resultados
		formatted_results = "\n".join([
			f"• {r['title']} ({r['source']}): {r['url']}"
			for r in results[:max_results]
		])
		
		return {
			"success": True,
			"query": query,
			"year": year,
			"results": results[:max_results],
			"sources_text": formatted_results,
			"formatted_response": f"He encontrado información actualizada de {year} en:\n\n{formatted_results}\n\nPuedes consultar estos enlaces oficiales para más detalles."
		}
	
	except Exception as e:
		logger.error(f"Error in search_tax_regulations_tool: {e}", exc_info=True)
		return {
			"success": False,
			"error": str(e),
			"formatted_response": f"No pude buscar información actualizada en este momento. Error: {str(e)}"
		}


# Tool definition para OpenAI function calling
SEARCH_TAX_REGULATIONS_TOOL = {
	"type": "function",
	"function": {
		"name": "search_tax_regulations",
		"description": "Busca información fiscal actualizada en fuentes oficiales (AEAT, BOE, Seguridad Social). USA ESTA HERRAMIENTA cuando: (1) La documentación RAG no tiene info del año actual, (2) El usuario pregunta por plazos, fechas límite o cambios recientes, (3) Necesitas confirmar información de años anteriores.",
		"parameters": {
			"type": "object",
			"properties": {
				"query": {
					"type": "string",
					"description": "Consulta de búsqueda específica (ej: 'tramos IRPF 2025 madrid', 'modelo 303 plazos', 'cuotas autónomos 2025')"
				},
				"year": {
					"type": "integer",
					"description": "Año fiscal para la búsqueda (default: 2025)",
					"default": 2025
				},
				"max_results": {
					"type": "integer",
					"description": "Número máximo de resultados a devolver (default: 3)",
					"default": 3
				}
			},
			"required": ["query"]
		}
	}
}