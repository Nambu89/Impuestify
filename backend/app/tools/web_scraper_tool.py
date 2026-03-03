"""
Web Scraper Tool for IRPF Data Extraction

Extracts structured IRPF tax scale data from official Spanish sources
using web scraping + LLM extraction.

Official Sources (priority order):
1. AEAT (Agencia Tributaria) - agenciatributaria.es
2. BOE (Boletín Oficial del Estado) - boe.es
3. Seguridad Social - seg-social.es
"""
import httpx
import logging
import os
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
from openai import OpenAI

logger = logging.getLogger(__name__)

# Official sources whitelist
OFFICIAL_SOURCES = {
    "agenciatributaria.es": "AEAT",
    "aeat.es": "AEAT",
    "boe.es": "BOE",
    "seg-social.es": "Seguridad Social",
    "segsocial.es": "Seguridad Social"
}

# CCAA name normalization mapping
CCAA_NORMALIZATION = {
    "madrid": "Comunidad de Madrid",
    "cataluña": "Cataluña",
    "catalunya": "Cataluña",
    "valencia": "Comunitat Valenciana",
    "comunidad valenciana": "Comunitat Valenciana",
    "baleares": "Illes Balears",
    "islas baleares": "Illes Balears",
    "murcia": "Región de Murcia",
    "andalucía": "Andalucía",
    "andalucia": "Andalucía",
    "aragón": "Aragón",
    "aragon": "Aragón",
    "asturias": "Asturias",
    "canarias": "Canarias",
    "cantabria": "Cantabria",
    "castilla y león": "Castilla y León",
    "castilla y leon": "Castilla y León",
    "castilla-la mancha": "Castilla-La Mancha",
    "castilla la mancha": "Castilla-La Mancha",
    "extremadura": "Extremadura",
    "galicia": "Galicia",
    "la rioja": "La Rioja",
    "rioja": "La Rioja",
    "ceuta": "Ceuta",
    "melilla": "Melilla",
    "ciudad autónoma de ceuta": "Ceuta",
    "ciudad autonoma de ceuta": "Ceuta",
    "ciudad autónoma de melilla": "Melilla",
    "ciudad autonoma de melilla": "Melilla",
}


def normalize_ccaa_name(name: str) -> str:
    """
    Normalize CCAA name to match database format.
    
    Args:
        name: CCAA name (any format)
        
    Returns:
        Normalized CCAA name
    """
    name_lower = name.lower().strip()
    return CCAA_NORMALIZATION.get(name_lower, name)


def validate_official_source(url: str) -> Optional[str]:
    """
    Validate that URL is from an official source.
    
    Args:
        url: URL to validate
        
    Returns:
        Source name if official, None otherwise
    """
    url_lower = url.lower()
    for domain, source_name in OFFICIAL_SOURCES.items():
        if domain in url_lower:
            return source_name
    return None


def detect_ccaa_from_query(query: str) -> Optional[str]:
    """
    Detect CCAA name from search query.
    
    Args:
        query: Search query
        
    Returns:
        Normalized CCAA name if detected, None otherwise
    """
    query_lower = query.lower()
    
    # Check for exact matches first
    for ccaa_variant, ccaa_official in CCAA_NORMALIZATION.items():
        if ccaa_variant in query_lower:
            return ccaa_official
    
    # Check for official names
    official_names = set(CCAA_NORMALIZATION.values())
    for official_name in official_names:
        if official_name.lower() in query_lower:
            return official_name
    
    return None


def format_tramos(tramos: List[Dict]) -> str:
    """
    Format IRPF tramos for display.
    
    Args:
        tramos: List of tramo dicts
        
    Returns:
        Formatted string
    """
    lines = []
    for tramo in tramos:
        base_hasta = tramo.get('base_hasta', 0)
        tipo = tramo.get('tipo_aplicable', 0)
        
        if base_hasta >= 999999:
            lines.append(f"  • En adelante: {tipo}%")
        else:
            lines.append(f"  • Hasta {base_hasta:,.0f}€: {tipo}%")
    
    return "\n".join(lines)


async def extract_irpf_data_from_url(
    url: str,
    year: int,
    ccaa: str
) -> Optional[Dict[str, Any]]:
    """
    Extract IRPF tax scale data from a URL using scraping + LLM.
    
    Args:
        url: URL of official page (AEAT, BOE, etc.)
        year: Tax year
        ccaa: Autonomous community name
        
    Returns:
        Dict with extracted data or None if extraction fails
    """
    try:
        # Validate official source
        source_name = validate_official_source(url)
        if not source_name:
            logger.warning(f"URL is not from official source: {url}")
            return None
        
        logger.info(f"Extracting IRPF data from {source_name}: {url}")
        
        # 1. Download content
        # Disable SSL verification for official Spanish government sites
        # (they use weak signature algorithms that Python rejects)
        verify_ssl = not any(domain in url.lower() for domain in [
            'agenciatributaria.es',
            'aeat.es', 
            'boe.es',
            'seg-social.es'
        ])
        
        async with httpx.AsyncClient(
            timeout=15.0, 
            follow_redirects=True,
            verify=verify_ssl  # Disable SSL verification for Spanish gov sites
        ) as client:
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
        if response.status_code != 200:
            logger.warning(f"Failed to fetch {url}: HTTP {response.status_code}")
            return None
        
        # 2. Extract relevant text
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove scripts, styles, navigation, etc.
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        
        text_content = soup.get_text(separator='\n', strip=True)
        
        # 3. Find relevant section (to reduce LLM input size)
        if len(text_content) > 10000:
            keywords = ['irpf', 'tramos', 'escala', 'gravamen', 'tipo', ccaa.lower(), str(year)]
            lines = text_content.split('\n')
            relevant_lines = []
            
            for i, line in enumerate(lines):
                if any(kw in line.lower() for kw in keywords):
                    # Include context (15 lines before and after)
                    start = max(0, i - 15)
                    end = min(len(lines), i + 15)
                    relevant_lines.extend(lines[start:end])
            
            if relevant_lines:
                text_content = '\n'.join(relevant_lines[:600])  # Max 600 lines
            else:
                # If no keywords found, take first 10k chars
                text_content = text_content[:10000]
        
        # 4. Use LLM (gpt-5-mini) to extract structured data
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        extraction_prompt = f"""Extrae los tramos de IRPF para {ccaa} del año {year} del siguiente texto de fuente oficial ({source_name}).

IMPORTANTE: Busca la escala AUTONÓMICA (de la comunidad autónoma), NO la escala estatal.

Texto de la fuente oficial:
{text_content}

Devuelve SOLO un JSON válido con este formato exacto (sin explicaciones ni texto adicional):
{{
  "found": true,
  "year": {year},
  "jurisdiction": "{ccaa}",
  "scale_type": "general",
  "tramos": [
    {{
      "tramo_num": 1,
      "base_hasta": 12450.00,
      "cuota_integra": 0.00,
      "resto_base": 12450.00,
      "tipo_aplicable": 9.50
    }},
    {{
      "tramo_num": 2,
      "base_hasta": 20200.00,
      "cuota_integra": 1185.75,
      "resto_base": 7750.00,
      "tipo_aplicable": 12.00
    }}
  ]
}}

Si NO encuentras los datos de {ccaa} {year}, devuelve:
{{"found": false}}

REGLAS:
- tramo_num: número del tramo (1, 2, 3...)
- base_hasta: límite superior del tramo en euros
- cuota_integra: cuota acumulada hasta el inicio de este tramo
- resto_base: base del tramo (base_hasta - base_hasta_anterior)
- tipo_aplicable: porcentaje a aplicar (sin el símbolo %)
- El último tramo debe tener base_hasta muy alto (ej: 999999999)
"""
        
        from app.config import settings
        system_prompt = "Eres un experto en extraer datos fiscales de documentos oficiales españoles. Devuelves SOLO JSON válido, sin explicaciones."
        user_prompt = extraction_prompt
        
        response = client.chat.completions.create(
            # Use theconfigured OpenAI model from settings
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=1,  # gpt-5-mini only supports temperature=1
            max_completion_tokens=3000,  # Needs tokens for extracting complex IRPF data
            response_format={"type": "json_object"}
        )
        
        import json
        extracted_data = json.loads(response.choices[0].message.content)
        
        if extracted_data.get("found"):
            logger.info(f"✅ Successfully extracted IRPF data from {url}")
            logger.info(f"   Found {len(extracted_data.get('tramos', []))} tramos for {ccaa} {year}")
            
            return {
                "success": True,
                "source_url": url,
                "source_name": source_name,
                "data": extracted_data,
                "tramos": extracted_data.get("tramos", []),
                "year": year,
                "jurisdiction": ccaa
            }
        else:
            logger.warning(f"No IRPF data found in {url} for {ccaa} {year}")
            return None
    
    except httpx.TimeoutException:
        logger.error(f"Timeout fetching {url}")
        return None
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error extracting from {url}: {e}", exc_info=True)
        return None
