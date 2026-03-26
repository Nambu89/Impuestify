"""
Region Detector for AEAT notifications.

Detects taxpayer's autonomous community from notification text.
Handles both territorio común and haciendas forales.
"""
import re
from typing import Dict, Optional


class RegionDetector:
    """Detect taxpayer's autonomous community from text."""
    
    # Mapping: city/province → autonomous community
    LOCATION_TO_REGION = {
        # Madrid
        "madrid": "Comunidad de Madrid",
        "alcalá de henares": "Comunidad de Madrid",
        "móstoles": "Comunidad de Madrid",
        "fuenlabrada": "Comunidad de Madrid",
        "leganés": "Comunidad de Madrid",
        
        # Cataluña
        "cataluña": "Cataluña",
        "cataluna": "Cataluña",
        "catalunya": "Cataluña",
        "barcelona": "Cataluña",
        "tarragona": "Cataluña",
        "lleida": "Cataluña",
        "girona": "Cataluña",
        
        # Andalucía
        "andalucía": "Andalucía",
        "andalucia": "Andalucía",
        "sevilla": "Andalucía",
        "málaga": "Andalucía",
        "granada": "Andalucía",
        "córdoba": "Andalucía",
        "cádiz": "Andalucía",
        "almería": "Andalucía",
        "huelva": "Andalucía",
        "jaén": "Andalucía",
        
        # Comunitat Valenciana
        "comunitat valenciana": "Comunitat Valenciana",
        "comunidad valenciana": "Comunitat Valenciana",
        "valencia": "Comunitat Valenciana",
        "alicante": "Comunitat Valenciana",
        "castellón": "Comunitat Valenciana",
        
        # Galicia
        "galicia": "Galicia",
        "a coruña": "Galicia",
        "santiago de compostela": "Galicia",
        "vigo": "Galicia",
        "pontevedra": "Galicia",
        "ourense": "Galicia",
        "lugo": "Galicia",
        
        # País Vasco (FORAL)
        "país vasco": "País Vasco",
        "pais vasco": "País Vasco",
        "euskadi": "País Vasco",
        "bilbao": "País Vasco",
        "vitoria-gasteiz": "País Vasco",
        "vitoria": "País Vasco",
        "donostia": "País Vasco",
        "san sebastián": "País Vasco",
        "bizkaia": "País Vasco",
        "vizcaya": "País Vasco",
        "araba": "País Vasco",
        "álava": "País Vasco",
        "alava": "País Vasco",
        "gipuzkoa": "País Vasco",
        "guipúzcoa": "País Vasco",
        "guipuzkoa": "País Vasco",
        
        # Navarra (FORAL)
        "navarra": "Navarra",
        "pamplona": "Navarra",
        "iruña": "Navarra",
        "tudela": "Navarra",
        
        # Aragón
        "aragón": "Aragón",
        "aragon": "Aragón",
        "zaragoza": "Aragón",
        "huesca": "Aragón",
        "teruel": "Aragón",
        
        # Castilla y León
        "castilla y león": "Castilla y León",
        "castilla y leon": "Castilla y León",
        "valladolid": "Castilla y León",
        "salamanca": "Castilla y León",
        "burgos": "Castilla y León",
        "león": "Castilla y León",
        "segovia": "Castilla y León",
        "ávila": "Castilla y León",
        "soria": "Castilla y León",
        "palencia": "Castilla y León",
        "zamora": "Castilla y León",
        
        # Castilla-La Mancha
        "castilla-la mancha": "Castilla-La Mancha",
        "castilla la mancha": "Castilla-La Mancha",
        "toledo": "Castilla-La Mancha",
        "albacete": "Castilla-La Mancha",
        "ciudad real": "Castilla-La Mancha",
        "cuenca": "Castilla-La Mancha",
        "guadalajara": "Castilla-La Mancha",
        
        # Extremadura
        "extremadura": "Extremadura",
        "badajoz": "Extremadura",
        "cáceres": "Extremadura",
        "mérida": "Extremadura",
        
        # Murcia
        "región de murcia": "Región de Murcia",
        "region de murcia": "Región de Murcia",
        "murcia": "Región de Murcia",
        "cartagena": "Región de Murcia",
        
        # Asturias
        "asturias": "Principado de Asturias",
        "principado de asturias": "Principado de Asturias",
        "oviedo": "Principado de Asturias",
        "gijón": "Principado de Asturias",
        
        # Cantabria
        "cantabria": "Cantabria",
        "santander": "Cantabria",
        
        # La Rioja
        "la rioja": "La Rioja",
        "rioja": "La Rioja",
        "logroño": "La Rioja",
        
        # Baleares
        "baleares": "Illes Balears",
        "illes balears": "Illes Balears",
        "islas baleares": "Illes Balears",
        "mallorca": "Illes Balears",
        "palma": "Illes Balears",
        "palma de mallorca": "Illes Balears",
        "ibiza": "Illes Balears",
        "menorca": "Illes Balears",
        
        # Canarias
        "canarias": "Canarias",
        "las palmas": "Canarias",
        "santa cruz de tenerife": "Canarias",
        "tenerife": "Canarias",
        "gran canaria": "Canarias",
        
        # Ceuta y Melilla
        "ceuta": "Ceuta",
        "melilla": "Melilla",
    }
    
    # Haciendas Forales (special tax regime)
    FORAL_REGIONS = {"País Vasco", "Navarra"}
    
    # Postal code ranges → regions (fallback)
    POSTAL_CODE_RANGES = {
        (28000, 28999): "Comunidad de Madrid",
        (8000, 8999): "Cataluña",
        (41000, 41999): "Andalucía",  # Sevilla
        (50000, 50999): "Aragón",  # Zaragoza
        (48000, 48999): "País Vasco",  # Bizkaia
        (31000, 31999): "Navarra",  # Pamplona
        # Añadir más según necesidad
    }
    
    def detect_from_text(self, text: str) -> Dict[str, Optional[str]]:
        """
        Detect region from notification text.
        
        Args:
            text: Notification content
        
        Returns:
            {
                'region': 'Comunidad de Madrid',
                'province': 'Madrid',
                'is_foral': False,
                'confidence': 'high' | 'medium' | 'low'
            }
        
        Detection strategies (in order):
        1. Direct city/province mention
        2. Postal code
        3. Delegación/Oficina name
        4. Fallback to general
        """
        text_lower = text.lower()
        
        # Strategy 1: City/Province mention
        for location, region in self.LOCATION_TO_REGION.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(location) + r'\b'
            if re.search(pattern, text_lower):
                return {
                    'region': region,
                    'province': location.title(),
                    'is_foral': region in self.FORAL_REGIONS,
                    'confidence': 'high',
                    'detection_method': 'location_name'
                }
        
        # Strategy 2: Postal code
        postal_match = re.search(r'\b(\d{5})\b', text)
        if postal_match:
            postal_code = int(postal_match.group(1))
            for (start, end), region in self.POSTAL_CODE_RANGES.items():
                if start <= postal_code <= end:
                    return {
                        'region': region,
                        'province': None,
                        'is_foral': region in self.FORAL_REGIONS,
                        'confidence': 'medium',
                        'detection_method': 'postal_code',
                        'postal_code': postal_code
                    }
        
        # Strategy 3: Delegación mentions (e.g., "Delegación de Madrid")
        deleg_pattern = r'delegación\s+(?:de\s+)?(\w+(?:\s+\w+)?)'
        deleg_match = re.search(deleg_pattern, text_lower)
        if deleg_match:
            deleg_location = deleg_match.group(1).strip()
            if deleg_location in self.LOCATION_TO_REGION:
                region = self.LOCATION_TO_REGION[deleg_location]
                return {
                    'region': region,
                    'province': deleg_location.title(),
                    'is_foral': region in self.FORAL_REGIONS,
                    'confidence': 'high',
                    'detection_method': 'delegation_name'
                }
        
        # Fallback: General (territorio común)
        return {
            'region': 'General (territorio común)',
            'province': None,
            'is_foral': False,
            'confidence': 'low',
            'detection_method': 'fallback'
        }
    
    def get_tax_authority_name(self, region: str, is_foral: bool) -> str:
        """
        Get the name of the tax authority for this region.
        
        Args:
            region: Autonomous community name
            is_foral: Whether it's a foral region
        
        Returns:
            Name of tax authority (AEAT or Hacienda Foral)
        """
        if not is_foral:
            return "Agencia Tributaria (AEAT)"
        
        if region == "Navarra":
            return "Hacienda Foral de Navarra"
        elif region == "País Vasco":
            return "Hacienda Foral del País Vasco"
        else:
            return "Agencia Tributaria (AEAT)"
    
    def get_tax_authority_url(self, region: str, is_foral: bool) -> str:
        """
        Get URL of tax authority website.
        
        Args:
            region: Autonomous community
            is_foral: Whether it's foral
        
        Returns:
            URL of relevant tax authority
        """
        if not is_foral:
            return "https://sede.agenciatributaria.gob.es"
        
        if region == "Navarra":
            return "https://hacienda.navarra.es"
        elif region == "País Vasco":
            return "https://www.euskadi.eus/hacienda"
        else:
            return "https://sede.agenciatributaria.gob.es"
    
    def requires_special_handling(self, is_foral: bool) -> bool:
        """
        Check if region requires special tax handling.
        
        Args:
            is_foral: Whether region is foral
        
        Returns:
            True if special rules apply
        """
        return is_foral
