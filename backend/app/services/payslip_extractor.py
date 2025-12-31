"""
Servicio para extraer datos de nóminas españolas en PDF
Usa el módulo centralizado pdf_extractor para extracción de texto
"""
import re
import json
import hashlib
from typing import Dict, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PayslipExtractor:
    """Extrae y parsea datos de nóminas españolas"""
    
    def __init__(self):
        self.patterns = self._init_patterns()
    
    def _init_patterns(self) -> Dict[str, re.Pattern]:
        """Patrones regex para extraer campos comunes de nóminas españolas"""
        return {
            # Periodo
            'period': re.compile(r'(?:periodo|mes)[\s:]*(\d{1,2})[/-](\d{4})', re.IGNORECASE),
            
            # Empresa
            'company_name': re.compile(r'(?:empresa|razón social)[\s:]*([A-ZÀ-Ú\s\.]+?)(?:\n|CIF)', re.IGNORECASE),
            'company_cif': re.compile(r'CIF[\s:]*([A-Z]\d{8})', re.IGNORECASE),
            
            # Empleado
            'employee_name': re.compile(r'(?:trabajador|empleado|nombre)[\s:]*([A-ZÀ-Ú\s]+?)(?:\n|DNI|NIE)', re.IGNORECASE),
            'employee_nif': re.compile(r'(?:DNI|NIE)[\s:]*(\d{8}[A-Z])', re.IGNORECASE),
            'employee_ss': re.compile(r'(?:n[úu]mero? ?seguridad social|nº? ?s\.s\.)[\s:]*(\d{12})', re.IGNORECASE),
            
            # Salarios
            'gross_salary': re.compile(r'(?:total devengado|devengos totales|bruto)[\s:]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?', re.IGNORECASE),
            'net_salary': re.compile(r'(?:líquido a? ?percibir|neto|total a? ?percibir)[\s:]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?', re.IGNORECASE),
            'base_salary': re.compile(r'(?:salario base|sueldo base)[\s:]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?', re.IGNORECASE),
            
            # IRPF
            'irpf_amount': re.compile(r'(?:retención|I\.?R\.?P\.?F\.?)[\s:]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?', re.IGNORECASE),
            'irpf_percentage': re.compile(r'I\.?R\.?P\.?F\.?.*?(\d{1,2},\d{2})\s*%', re.IGNORECASE),
            
            # Seguridad Social
            'ss_contribution': re.compile(r'(?:contingencias comunes|aportación trabajador|cotización)[\s:]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?', re.IGNORECASE),
            'unemployment': re.compile(r'desempleo[\s:]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?', re.IGNORECASE),
            
            # Extras
            'extra_payments': re.compile(r'(?:paga extra|pagas prorrateadas)[\s:]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?', re.IGNORECASE),
            'overtime': re.compile(r'horas extraordinarias[\s:]*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?', re.IGNORECASE),
        }
    
    async def extract_from_pdf(self, pdf_path: str) -> Dict:
        """
        Extrae texto y datos estructurados de un PDF de nómina
        
        Args:
            pdf_path: Ruta al archivo PDF
            
        Returns:
            Dict con datos extraídos
        """
        try:
            # Calcular hash del archivo para deduplicación
            file_hash = self._calculate_file_hash(pdf_path)
            
            # Usar el módulo centralizado de extracción de PDFs
            from app.utils.pdf_extractor import get_pdf_extractor
            
            logger.info(f"Extrayendo texto de {pdf_path}")
            extractor = get_pdf_extractor()
            result = await extractor.extract_from_file(pdf_path)
            
            if not result.success:
                return {
                    'extraction_status': 'failed',
                    'error': result.error,
                    'full_text': None,
                    'file_hash': None
                }
            
            # Parsear datos estructurados del texto markdown
            extracted_data = self._parse_payslip_data(result.markdown_text)
            
            # Añadir el texto completo para contexto
            extracted_data['full_text'] = result.markdown_text
            extracted_data['file_hash'] = file_hash
            extracted_data['extraction_status'] = 'completed'
            extracted_data['total_pages'] = result.total_pages
            
            logger.info(f"Extracción completada: {len(extracted_data)} campos extraídos")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extrayendo PDF: {e}", exc_info=True)
            return {
                'extraction_status': 'failed',
                'error': str(e),
                'full_text': None,
                'file_hash': None
            }
    
    def _calculate_file_hash(self, pdf_path: str) -> str:
        """Calcula SHA256 hash del archivo para deduplicación"""
        sha256_hash = hashlib.sha256()
        with open(pdf_path, "rb") as f:
            # Leer en chunks para archivos grandes
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _parse_payslip_data(self, text: str) -> Dict:
        """Parsea el texto extraído usando regex patterns"""
        data = {}
        
        # Extraer cada campo
        for field, pattern in self.patterns.items():
            match = pattern.search(text)
            if match:
                if field == 'period':
                    data['period_month'] = int(match.group(1))
                    data['period_year'] = int(match.group(2))
                else:
                    value = match.group(1).strip()
                    # Convertir cantidades españolas (1.234,56) a float
                    if any(x in field for x in ['salary', 'amount', 'contribution', 'payments', 'overtime']):
                        value = self._parse_spanish_number(value)
                    elif field == 'irpf_percentage':
                        value = float(value.replace(',', '.'))
                    data[field] = value
        
        # Calcular tipo efectivo si tenemos los datos
        if 'irpf_amount' in data and 'gross_salary' in data:
            effective_rate = self.calculate_effective_tax_rate(
                data['irpf_amount'], 
                data['gross_salary']
            )
            if effective_rate:
                data['irpf_effective_rate'] = effective_rate
        
        return data
    
    def _parse_spanish_number(self, num_str: str) -> Optional[float]:
        """Convierte número español (1.234,56) a float"""
        try:
            # Eliminar puntos de miles y cambiar coma por punto
            clean = num_str.replace('.', '').replace(',', '.')
            return float(clean)
        except Exception as e:
            logger.warning(f"Error parseando número '{num_str}': {e}")
            return None
    
    def calculate_effective_tax_rate(self, irpf_amount: float, gross_salary: float) -> Optional[float]:
        """Calcula el tipo efectivo de IRPF"""
        if gross_salary and gross_salary > 0:
            return round((irpf_amount / gross_salary) * 100, 2)
        return None
    
    def generate_summary(self, data: Dict) -> str:
        """Genera un resumen legible de la nómina"""
        summary_parts = []
        
        if data.get('period_month') and data.get('period_year'):
            summary_parts.append(f"Periodo: {data['period_month']}/{data['period_year']}")
        
        if data.get('gross_salary'):
            summary_parts.append(f"Salario bruto: {data['gross_salary']:.2f}€")
        
        if data.get('net_salary'):
            summary_parts.append(f"Salario neto: {data['net_salary']:.2f}€")
        
        if data.get('irpf_amount'):
            summary_parts.append(f"Retención IRPF: {data['irpf_amount']:.2f}€")
            if data.get('irpf_percentage'):
                summary_parts.append(f"({data['irpf_percentage']}%)")
        
        if data.get('ss_contribution'):
            summary_parts.append(f"Cotización SS: {data['ss_contribution']:.2f}€")
        
        return " | ".join(summary_parts) if summary_parts else "Sin datos extraídos"
    
    def get_extraction_stats(self, data: Dict) -> Dict:
        """Obtiene estadísticas de la extracción"""
        total_fields = len(self.patterns)
        extracted_fields = sum(1 for field in self.patterns.keys() 
                              if field in data or f"{field}_month" in data)
        
        return {
            'total_fields': total_fields,
            'extracted_fields': extracted_fields,
            'extraction_rate': round((extracted_fields / total_fields) * 100, 2),
            'status': data.get('extraction_status', 'unknown')
        }
