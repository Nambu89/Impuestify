"""
Servicio para extraer datos de facturas españolas en PDF
Usa el módulo centralizado pdf_extractor para extracción de texto
"""
import re
import hashlib
from typing import Dict, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class InvoiceData:
    """Datos estructurados de una factura española."""
    # Identificación
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None

    # Emisor
    issuer_name: Optional[str] = None
    issuer_nif: Optional[str] = None
    issuer_address: Optional[str] = None

    # Receptor
    recipient_name: Optional[str] = None
    recipient_nif: Optional[str] = None
    recipient_address: Optional[str] = None

    # Importes base
    base_imponible_21: Optional[float] = None
    base_imponible_10: Optional[float] = None
    base_imponible_4: Optional[float] = None
    base_imponible_0: Optional[float] = None  # Exento

    # Cuotas IVA
    cuota_iva_21: Optional[float] = None
    cuota_iva_10: Optional[float] = None
    cuota_iva_4: Optional[float] = None

    # Totales
    total_base_imponible: Optional[float] = None
    total_iva: Optional[float] = None
    total_factura: Optional[float] = None

    # Retenciones (si aplica)
    retencion_irpf: Optional[float] = None
    porcentaje_retencion: Optional[float] = None

    # Metadata
    extraction_status: str = "pending"
    full_text: Optional[str] = None
    file_hash: Optional[str] = None
    confidence_score: float = 0.0


class InvoiceExtractor:
    """Extrae y parsea datos de facturas españolas."""

    def __init__(self):
        self.patterns = self._init_patterns()

    def _init_patterns(self) -> Dict[str, re.Pattern]:
        """Patrones regex para extraer campos de facturas españolas."""
        return {
            # Número de factura
            'invoice_number': re.compile(
                r'(?:n[úu]mero?\s*(?:de\s*)?factura|factura\s*n[°ºo]?|n[°ºo]?\s*factura)[\s:]*([A-Z0-9\-/]+)',
                re.IGNORECASE
            ),

            # Fechas
            'invoice_date': re.compile(
                r'(?:fecha\s*(?:de\s*)?(?:factura|emisi[óo]n)|fecha)[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                re.IGNORECASE
            ),
            'due_date': re.compile(
                r'(?:fecha\s*(?:de\s*)?vencimiento|vencimiento)[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
                re.IGNORECASE
            ),

            # NIF/CIF (emisor y receptor)
            'nif_cif': re.compile(
                r'(?:NIF|CIF|N\.I\.F\.|C\.I\.F\.)[\s:]*([A-Z]?\d{7,8}[A-Z]?)',
                re.IGNORECASE
            ),

            # Bases imponibles por tipo de IVA
            'base_21': re.compile(
                r'(?:base\s*(?:imponible)?[\s:]*)?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?\s*(?:21\s*%|IVA\s*21)',
                re.IGNORECASE
            ),
            'base_10': re.compile(
                r'(?:base\s*(?:imponible)?[\s:]*)?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?\s*(?:10\s*%|IVA\s*10)',
                re.IGNORECASE
            ),
            'base_4': re.compile(
                r'(?:base\s*(?:imponible)?[\s:]*)?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?\s*(?:4\s*%|IVA\s*4)',
                re.IGNORECASE
            ),

            # Base imponible general (cuando no está desglosada)
            'base_imponible': re.compile(
                r'(?:base\s*imponible|subtotal|importe\s*neto)[\s:]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?',
                re.IGNORECASE
            ),

            # Cuotas IVA
            'cuota_iva_21': re.compile(
                r'(?:cuota\s*)?IVA\s*21\s*%?[\s:]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?',
                re.IGNORECASE
            ),
            'cuota_iva_10': re.compile(
                r'(?:cuota\s*)?IVA\s*10\s*%?[\s:]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?',
                re.IGNORECASE
            ),
            'cuota_iva_4': re.compile(
                r'(?:cuota\s*)?IVA\s*4\s*%?[\s:]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?',
                re.IGNORECASE
            ),

            # IVA general (cuando no está desglosado)
            'iva_total': re.compile(
                r'(?:total\s*)?IVA[\s:]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?',
                re.IGNORECASE
            ),

            # Total factura
            'total_factura': re.compile(
                r'(?:total\s*(?:factura)?|importe\s*total|total\s*a\s*pagar)[\s:]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?',
                re.IGNORECASE
            ),

            # Retención IRPF (para autónomos)
            'retencion_irpf': re.compile(
                r'(?:retenci[óo]n\s*(?:IRPF)?|IRPF)[\s:]*-?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?',
                re.IGNORECASE
            ),
            'porcentaje_retencion': re.compile(
                r'(?:retenci[óo]n|IRPF).*?(\d{1,2}(?:,\d{1,2})?)\s*%',
                re.IGNORECASE
            ),
        }

    async def extract_from_pdf(self, pdf_path: str) -> Dict:
        """
        Extrae datos de un PDF de factura.

        Args:
            pdf_path: Ruta al archivo PDF

        Returns:
            Dict con datos extraídos
        """
        try:
            # Calcular hash del archivo
            file_hash = self._calculate_file_hash(pdf_path)

            # Usar el módulo centralizado de extracción de PDFs
            from app.utils.pdf_extractor import get_pdf_extractor

            logger.info(f"Extrayendo texto de factura: {pdf_path}")
            extractor = get_pdf_extractor()
            result = await extractor.extract_from_file(pdf_path)

            if not result.success:
                return {
                    'extraction_status': 'failed',
                    'error': result.error,
                    'full_text': None,
                    'file_hash': None
                }

            # Parsear datos estructurados
            extracted_data = self._parse_invoice_data(result.markdown_text)

            # Añadir metadata
            extracted_data['full_text'] = result.markdown_text
            extracted_data['file_hash'] = file_hash
            extracted_data['extraction_status'] = 'completed'
            extracted_data['total_pages'] = result.total_pages

            # Calcular score de confianza
            extracted_data['confidence_score'] = self._calculate_confidence(extracted_data)

            logger.info(f"Extracción completada: confianza={extracted_data['confidence_score']:.2f}")
            return extracted_data

        except Exception as e:
            logger.error(f"Error extrayendo factura: {e}", exc_info=True)
            return {
                'extraction_status': 'failed',
                'error': str(e),
                'full_text': None,
                'file_hash': None
            }

    async def extract_from_text(self, text: str) -> Dict:
        """
        Extrae datos de texto ya extraído.

        Args:
            text: Texto de la factura

        Returns:
            Dict con datos extraídos
        """
        extracted_data = self._parse_invoice_data(text)
        extracted_data['extraction_status'] = 'completed'
        extracted_data['confidence_score'] = self._calculate_confidence(extracted_data)
        return extracted_data

    def _calculate_file_hash(self, pdf_path: str) -> str:
        """Calcula SHA256 hash del archivo."""
        sha256_hash = hashlib.sha256()
        with open(pdf_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _parse_invoice_data(self, text: str) -> Dict:
        """Parsea el texto extraído usando regex patterns."""
        data = {}

        # Extraer número de factura
        match = self.patterns['invoice_number'].search(text)
        if match:
            data['invoice_number'] = match.group(1).strip()

        # Extraer fechas
        match = self.patterns['invoice_date'].search(text)
        if match:
            data['invoice_date'] = match.group(1)

        match = self.patterns['due_date'].search(text)
        if match:
            data['due_date'] = match.group(1)

        # Extraer NIFs (primero emisor, segundo receptor típicamente)
        nif_matches = self.patterns['nif_cif'].findall(text)
        if len(nif_matches) >= 1:
            data['issuer_nif'] = nif_matches[0]
        if len(nif_matches) >= 2:
            data['recipient_nif'] = nif_matches[1]

        # Extraer bases imponibles por tipo
        match = self.patterns['base_21'].search(text)
        if match:
            data['base_imponible_21'] = self._parse_spanish_number(match.group(1))

        match = self.patterns['base_10'].search(text)
        if match:
            data['base_imponible_10'] = self._parse_spanish_number(match.group(1))

        match = self.patterns['base_4'].search(text)
        if match:
            data['base_imponible_4'] = self._parse_spanish_number(match.group(1))

        # Base imponible general (si no hay desglose)
        if not any(k in data for k in ['base_imponible_21', 'base_imponible_10', 'base_imponible_4']):
            match = self.patterns['base_imponible'].search(text)
            if match:
                data['total_base_imponible'] = self._parse_spanish_number(match.group(1))

        # Extraer cuotas IVA
        match = self.patterns['cuota_iva_21'].search(text)
        if match:
            data['cuota_iva_21'] = self._parse_spanish_number(match.group(1))

        match = self.patterns['cuota_iva_10'].search(text)
        if match:
            data['cuota_iva_10'] = self._parse_spanish_number(match.group(1))

        match = self.patterns['cuota_iva_4'].search(text)
        if match:
            data['cuota_iva_4'] = self._parse_spanish_number(match.group(1))

        # IVA total
        match = self.patterns['iva_total'].search(text)
        if match:
            data['total_iva'] = self._parse_spanish_number(match.group(1))

        # Total factura
        match = self.patterns['total_factura'].search(text)
        if match:
            data['total_factura'] = self._parse_spanish_number(match.group(1))

        # Retención IRPF
        match = self.patterns['retencion_irpf'].search(text)
        if match:
            data['retencion_irpf'] = self._parse_spanish_number(match.group(1))

        match = self.patterns['porcentaje_retencion'].search(text)
        if match:
            data['porcentaje_retencion'] = float(match.group(1).replace(',', '.'))

        # Calcular totales si faltan
        self._calculate_totals(data)

        return data

    def _parse_spanish_number(self, num_str: str) -> Optional[float]:
        """Convierte número español (1.234,56) a float."""
        try:
            clean = num_str.replace('.', '').replace(',', '.')
            return float(clean)
        except Exception as e:
            logger.warning(f"Error parseando número '{num_str}': {e}")
            return None

    def _calculate_totals(self, data: Dict):
        """Calcula totales si no fueron extraídos directamente."""
        # Total base imponible
        if 'total_base_imponible' not in data:
            bases = [
                data.get('base_imponible_21', 0) or 0,
                data.get('base_imponible_10', 0) or 0,
                data.get('base_imponible_4', 0) or 0,
                data.get('base_imponible_0', 0) or 0,
            ]
            if any(b > 0 for b in bases):
                data['total_base_imponible'] = sum(bases)

        # Total IVA
        if 'total_iva' not in data:
            cuotas = [
                data.get('cuota_iva_21', 0) or 0,
                data.get('cuota_iva_10', 0) or 0,
                data.get('cuota_iva_4', 0) or 0,
            ]
            if any(c > 0 for c in cuotas):
                data['total_iva'] = sum(cuotas)

        # Calcular cuotas IVA si tenemos bases pero no cuotas
        if data.get('base_imponible_21') and not data.get('cuota_iva_21'):
            data['cuota_iva_21'] = round(data['base_imponible_21'] * 0.21, 2)
        if data.get('base_imponible_10') and not data.get('cuota_iva_10'):
            data['cuota_iva_10'] = round(data['base_imponible_10'] * 0.10, 2)
        if data.get('base_imponible_4') and not data.get('cuota_iva_4'):
            data['cuota_iva_4'] = round(data['base_imponible_4'] * 0.04, 2)

    def _calculate_confidence(self, data: Dict) -> float:
        """Calcula un score de confianza basado en campos extraídos."""
        critical_fields = ['total_factura', 'total_base_imponible', 'invoice_number']
        important_fields = ['invoice_date', 'issuer_nif', 'total_iva']
        optional_fields = ['recipient_nif', 'due_date', 'retencion_irpf']

        score = 0.0

        # Campos críticos: 0.2 cada uno
        for field in critical_fields:
            if data.get(field):
                score += 0.2

        # Campos importantes: 0.1 cada uno
        for field in important_fields:
            if data.get(field):
                score += 0.1

        # Campos opcionales: 0.05 cada uno
        for field in optional_fields:
            if data.get(field):
                score += 0.05

        return min(score, 1.0)

    def generate_summary(self, data: Dict) -> str:
        """Genera un resumen legible de la factura."""
        parts = []

        if data.get('invoice_number'):
            parts.append(f"Factura: {data['invoice_number']}")

        if data.get('invoice_date'):
            parts.append(f"Fecha: {data['invoice_date']}")

        if data.get('total_base_imponible'):
            parts.append(f"Base: {data['total_base_imponible']:.2f}€")

        if data.get('total_iva'):
            parts.append(f"IVA: {data['total_iva']:.2f}€")

        if data.get('total_factura'):
            parts.append(f"Total: {data['total_factura']:.2f}€")

        if data.get('retencion_irpf'):
            parts.append(f"Ret. IRPF: -{data['retencion_irpf']:.2f}€")

        return " | ".join(parts) if parts else "Sin datos extraídos"

    def get_vat_breakdown(self, data: Dict) -> Dict[str, Dict[str, float]]:
        """Obtiene desglose de IVA por tipos."""
        breakdown = {}

        if data.get('base_imponible_21') or data.get('cuota_iva_21'):
            breakdown['21%'] = {
                'base': data.get('base_imponible_21', 0) or 0,
                'cuota': data.get('cuota_iva_21', 0) or 0
            }

        if data.get('base_imponible_10') or data.get('cuota_iva_10'):
            breakdown['10%'] = {
                'base': data.get('base_imponible_10', 0) or 0,
                'cuota': data.get('cuota_iva_10', 0) or 0
            }

        if data.get('base_imponible_4') or data.get('cuota_iva_4'):
            breakdown['4%'] = {
                'base': data.get('base_imponible_4', 0) or 0,
                'cuota': data.get('cuota_iva_4', 0) or 0
            }

        if data.get('base_imponible_0'):
            breakdown['0% (exento)'] = {
                'base': data.get('base_imponible_0', 0) or 0,
                'cuota': 0
            }

        return breakdown


# Global instance
_invoice_extractor: Optional[InvoiceExtractor] = None


def get_invoice_extractor() -> InvoiceExtractor:
    """Get global invoice extractor instance."""
    global _invoice_extractor
    if _invoice_extractor is None:
        _invoice_extractor = InvoiceExtractor()
    return _invoice_extractor
