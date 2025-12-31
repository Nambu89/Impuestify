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
	max_results: int = 3,
	extract_data: bool = True
) -> Dict[str, Any]:
	"""
	Busca información fiscal actualizada en fuentes oficiales españolas.
	Opcionalmente extrae datos estructurados usando LLM.
	
	Args:
		query: Consulta de búsqueda (ej: "tramos IRPF madrid 2025")
		year: Año fiscal para la búsqueda (default: 2025)
		max_results: Número máximo de resultados (default: 3)
		extract_data: Si True, intenta extraer datos estructurados (default: True)
		
	Returns:
		Dict con resultados de búsqueda y datos extraídos (si extract_data=True)
	"""
	try:
		logger.info(f"Searching tax regulations: query='{query}', year={year}, extract_data={extract_data}")
		
		MAX_RETRIES_YEARS = 1
		from datetime import datetime
		
		current_year_real = datetime.now().year
		years_to_try = [year]
		
		# If looking for current year or future, allow fallback to previous year
		if year >= current_year_real:
			years_to_try.append(year - 1)
			
		results = []
		effective_year = year
		
		for attempt_year in years_to_try:
			if attempt_year != year:
				logger.info(f"🔄 Fallback: Trying search for previous year: {attempt_year}")
				
			# Fuentes oficiales prioritarias (en orden)
			sources = [
				f"site:agenciatributaria.es {query} {attempt_year}",
				f"site:boe.es {query} {attempt_year}",
				f"site:seg-social.es {query} {attempt_year}",
			]
			
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
								
								# Solo incluir fuentes oficiales
								if url and any(domain in url for domain in ['agenciatributaria.es', 'boe.es', 'seg-social.es']):
									# Check if it's already added
									if not any(r['url'] == url for r in results):
										results.append({
											"title": title,
											"url": url,
											"source": "AEAT" if "agenciatributaria" in url else "BOE" if "boe" in url else "Seguridad Social"
										})

					# Check if we have results for this year, if so, stop searching this year
					if len(results) >= max_results:
						break
						
				except Exception as e:
					logger.warning(f"Error searching {source_query}: {e}")
					continue
			
			# If we found results, we are done. Break year loop.
			if results:
				effective_year = attempt_year
				logger.info(f"✅ Found {len(results)} results for year {effective_year}")
				break
				
		if not results:
			# Determine message based on attempts
			years_tried = ", ".join(map(str, years_to_try))
			return {
				"success": False,
				"error": "No se encontraron resultados en fuentes oficiales",
				"formatted_response": f"No encontré información actualizada de {years_tried} en AEAT, BOE o Seguridad Social. Posiblemente aún no se ha publicado. Te recomiendo consultar directamente en www.agenciatributaria.es"
			}
		
		# Update year to effective_year for next steps (extraction)
		year = effective_year
		
		# Si extract_data=True y la query es sobre IRPF, intentar extraer datos
		if extract_data and "irpf" in query.lower():
			from app.tools.web_scraper_tool import extract_irpf_data_from_url, detect_ccaa_from_query, format_tramos
			
			# Detectar CCAA del query
			ccaa = detect_ccaa_from_query(query)
			
			if ccaa:
				logger.info(f"Detected CCAA: {ccaa}, attempting data extraction")
				
				# Intentar extracción en orden de prioridad: AEAT → BOE → Seguridad Social
				sorted_results = sorted(
					results,
					key=lambda r: 0 if r['source'] == 'AEAT' else 1 if r['source'] == 'BOE' else 2
				)
				
				for result in sorted_results:
					logger.info(f"Attempting extraction from {result['source']}: {result['url']}")
					
					extracted = await extract_irpf_data_from_url(
						url=result['url'],
						year=year,
						ccaa=ccaa
					)
					
					if extracted and extracted.get("success"):
						tramos = extracted.get('tramos', [])
						logger.info(f"✅ Successfully extracted {len(tramos)} tramos from {result['source']}")
						
						return {
							"success": True,
							"query": query,
							"year": year,
							"source_url": result['url'],
							"source_title": result['title'],
							"source_name": result['source'],
							"extracted_data": extracted['data'],
							"tramos": tramos,
							"jurisdiction": ccaa,
							"formatted_response": f"""✅ He encontrado los tramos de IRPF para {ccaa} {year} en fuentes oficiales:

**Fuente**: {result['title']} ({result['source']})
**URL**: {result['url']}

**Tramos encontrados**:
{format_tramos(tramos)}

Estos datos se usarán para calcular tu IRPF."""
						}
					else:
						logger.info(f"No data extracted from {result['url']}")
				
				# Si no se pudo extraer de ninguna URL
				logger.warning(f"Could not extract structured data from any source")
			else:
				logger.info("Could not detect CCAA from query, skipping extraction")
		
		# Si no se pidió extracción o no se pudo extraer, devolver solo URLs
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
		"description": "Busca información fiscal actualizada en fuentes oficiales (AEAT, BOE, Seguridad Social) y opcionalmente extrae datos estructurados. USA ESTA HERRAMIENTA cuando: (1) La documentación RAG no tiene info del año actual, (2) El usuario pregunta por plazos, fechas límite o cambios recientes, (3) Necesitas confirmar información de años anteriores, (4) Necesitas datos de IRPF que no están en la base de datos.",
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
				},
				"extract_data": {
					"type": "boolean",
					"description": "Si True, intenta extraer datos estructurados de IRPF usando LLM (default: True). Útil cuando necesitas tramos de IRPF para cálculos.",
					"default": True
				}
			},
			"required": ["query"]
		}
	}
}