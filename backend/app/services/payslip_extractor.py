"""
Servicio para extraer datos de nóminas españolas en PDF
Usa el módulo centralizado pdf_extractor para extracción de texto

Regex patterns calibrados con nóminas reales españolas (formato Devoteam/SAP/A3Nom/etc.)
Formato típico:
  - Devengos a la izquierda, deducciones a la derecha
  - "TRIBUTACION I.R.P.F.19,03" (porcentaje pegado al nombre)
  - "LIQUIDO A PERCIBIR" en línea separada del importe
  - Periodo: "MENS 01 ENE 26 a 31 ENE 26"
  - Multi-página cuando hay bonus/atrasos
"""
import re
import json
import hashlib
from typing import Dict, Optional, List, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Spanish month names → month number
MONTH_MAP = {
    'ene': 1, 'enero': 1, 'feb': 2, 'febrero': 2, 'mar': 3, 'marzo': 3,
    'abr': 4, 'abril': 4, 'may': 5, 'mayo': 5, 'jun': 6, 'junio': 6,
    'jul': 7, 'julio': 7, 'ago': 8, 'agosto': 8, 'sep': 9, 'sept': 9,
    'septiembre': 9, 'oct': 10, 'octubre': 10, 'nov': 11, 'noviembre': 11,
    'dic': 12, 'diciembre': 12,
}

# Spanish number regex fragment: matches 1.234,56 or 234,56 or 1234,56
_NUM = r'(\d{1,3}(?:\.\d{3})*,\d{2})'


class PayslipExtractor:
    """Extrae y parsea datos de nóminas españolas"""

    def __init__(self):
        pass

    async def extract_from_pdf(self, pdf_path: str) -> Dict:
        """
        Extrae texto y datos estructurados de un PDF de nómina.
        Uses plain text extraction (not markdown) because payslip PDFs
        have tabular layouts that pymupdf4llm mangles into unusable markdown.

        Args:
            pdf_path: Ruta al archivo PDF

        Returns:
            Dict con datos extraídos
        """
        try:
            file_hash = self._calculate_file_hash(pdf_path)

            from app.utils.pdf_extractor import extract_pdf_text_plain

            logger.info(f"Extrayendo texto (plain) de {pdf_path}")
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            result = await extract_pdf_text_plain(pdf_bytes, pdf_path)

            if not result.success:
                return {
                    'extraction_status': 'failed',
                    'error': result.error,
                    'full_text': None,
                    'file_hash': None
                }

            extracted_data = self._parse_payslip_data(result.markdown_text)

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
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    # -------------------------------------------------------------------------
    # Number parsing
    # -------------------------------------------------------------------------

    @staticmethod
    def _parse_spanish_number(num_str: str) -> Optional[float]:
        """Convierte número español (1.234,56) a float"""
        if not num_str:
            return None
        try:
            clean = num_str.strip().replace('.', '').replace(',', '.')
            return float(clean)
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def _find_all_amounts(pattern: re.Pattern, text: str) -> List[float]:
        """Finds ALL matches of a pattern and returns parsed amounts (for multi-page summing)."""
        amounts = []
        for m in pattern.finditer(text):
            val = PayslipExtractor._parse_spanish_number(m.group(1))
            if val is not None:
                amounts.append(val)
        return amounts

    # -------------------------------------------------------------------------
    # Main parser
    # -------------------------------------------------------------------------

    def _parse_payslip_data(self, text: str) -> Dict:
        """
        Parsea el texto extraído de una nómina española.
        Soporta formatos multi-página y diversos layouts de nómina.
        """
        data: Dict = {}

        # --- 1. PERIODO ---
        # Format: "MENS 01 ENE 26 a 31 ENE 26" or "01/2026" or "Enero 2026"
        m = re.search(
            r'(?:MENS|PERIODO)\s+\d{1,2}\s+([A-Z]{3,})\s+(\d{2,4})\s+a\s+\d{1,2}\s+[A-Z]{3,}\s+\d{2,4}',
            text, re.IGNORECASE
        )
        if m:
            month_name = m.group(1).lower()
            year_raw = m.group(2)
            data['period_month'] = MONTH_MAP.get(month_name[:3])
            data['period_year'] = int(year_raw) if len(year_raw) == 4 else 2000 + int(year_raw)
        else:
            # Fallback: "periodo: 03/2026" or "mes: 03/2026"
            m2 = re.search(r'(?:periodo|mes)[\s:]*(\d{1,2})[/-](\d{4})', text, re.IGNORECASE)
            if m2:
                data['period_month'] = int(m2.group(1))
                data['period_year'] = int(m2.group(2))
            else:
                # Fallback: "Enero 2026" or "ENERO 2026"
                m3 = re.search(r'\b(' + '|'.join(MONTH_MAP.keys()) + r')\s+(\d{4})\b', text, re.IGNORECASE)
                if m3:
                    data['period_month'] = MONTH_MAP.get(m3.group(1).lower()[:3])
                    data['period_year'] = int(m3.group(2))

        # --- 2. EMPRESA ---
        # NIF: "NIF. A83115667" or "CIF: B12345678" or "NIF/CIF A12345678"
        m = re.search(r'(?:NIF|CIF)[.\s/:]*([A-Z]\d{7,8})', text, re.IGNORECASE)
        if m:
            data['company_nif'] = m.group(1)

        # Company name: find corporate suffix pattern (S.A.U., S.L., S.A., S.COOP.)
        corp_suffixes = r'(?:S\.?A\.?U\.?|S\.?L\.?U?\.?|S\.?L\.?L\.?|S\.?COOP\.?)'
        m = re.search(
            r'(\b[A-ZÀ-Ú][A-ZÀ-Ú0-9\s&\-]{1,40}?' + corp_suffixes + r')\b',
            text
        )
        if m:
            name = re.sub(r'\s{2,}', ' ', m.group(1)).strip()
            # Remove common prefixes that aren't part of the company name
            name = re.sub(r'^(?:INS\.?\s*S\.?S\.?\s*|Nº?\s*)', '', name).strip()
            if len(name) > 2:
                data['company_name'] = name

        # Nº Inscripción S.S. empresa
        m = re.search(r'(?:Nº?\s*INS\.?\s*S\.?S\.?|C\.?C\.?C\.?)[\s:]*(\d{2}/\d{5,10}-\d{2})', text, re.IGNORECASE)
        if m:
            data['company_ss_number'] = m.group(1)

        # --- 3. TRABAJADOR ---
        # DNI: "D.N.I." header may be far from value in tabular payslips
        # First try header + value together
        m = re.search(r'D\.?N\.?I\.?\s*[:\s]*(\d{8}[A-Z])', text, re.IGNORECASE)
        if m:
            data['employee_nif'] = m.group(1)
        else:
            # Fallback: find standalone 8-digit+letter pattern (Spanish DNI)
            # Exclude NIF/CIF patterns (start with letter) and SS numbers
            for m in re.finditer(r'\b(\d{8}[A-Z])\b', text):
                data['employee_nif'] = m.group(1)
                break  # take first match

        # NIE: X/Y/Z + 7 digits + letter
        if 'employee_nif' not in data:
            m = re.search(r'\b([XYZ]\d{7}[A-Z])\b', text, re.IGNORECASE)
            if m:
                data['employee_nif'] = m.group(1)

        # Nº Afiliación S.S.: "52/10066317-86" or "28/12345678-90"
        m = re.search(r'(?:AFILIACI[OÓ]N|Nº?\s*S\.?S\.?)[\s.:]*(\d{2}/\d{8,10}-\d{2})', text, re.IGNORECASE)
        if m:
            data['employee_ss'] = m.group(1)

        # Employee name: after TRABAJADOR/A header, next line with CAPS name
        m = re.search(r'TRABAJADOR/?A?\s*\n\s*([A-ZÀ-Ú][A-ZÀ-Ú\s,\.]+?)(?:\s{3,}|\n)', text)
        if m:
            name = m.group(1).strip().rstrip(',')
            if len(name) > 3:
                data['employee_name'] = name
        # Fallback: look for "APELLIDO, NOMBRE" pattern near DNI
        if 'employee_name' not in data:
            m = re.search(r'([A-ZÀ-Ú]{2,}(?:\s+[A-ZÀ-Ú]{2,})*,\s*[A-ZÀ-Ú]{2,}(?:\s+[A-ZÀ-Ú]\.?)*)\s', text)
            if m:
                data['employee_name'] = m.group(1).strip()

        # Antigüedad
        m = re.search(r'ANTIG[UÜ]EDAD\s*\n?\s*.*?(\d{1,2}\s+[A-Z]{3,}\s+\d{2,4})', text, re.IGNORECASE)
        if m:
            data['seniority_date'] = m.group(1).strip()

        # Categoría / Grupo cotización
        m = re.search(r'(?:CATEGOR[IÍ]A|GRUPO\s*COT)\s*\n?\s*.*?(\d{1,2})', text, re.IGNORECASE)
        if m:
            data['contribution_group'] = int(m.group(1))

        # Total días — look for number at end of the TARIFA/PERIODO line
        m = re.search(r'TOT\.?\s*D[IÍ]AS\s*\n.*?\s+(\d{2})\s*$', text, re.IGNORECASE | re.MULTILINE)
        if m:
            days = int(m.group(1))
            if 1 <= days <= 31:
                data['total_days'] = days

        # --- 4. DEVENGOS (earnings) ---
        # Salario Base
        m = re.search(r'\*?\s*Salario\s+Base\s+' + _NUM, text, re.IGNORECASE)
        if m:
            data['base_salary'] = self._parse_spanish_number(m.group(1))

        # Plus Convenio
        m = re.search(r'\*?\s*Plus\s+Convenio\s+' + _NUM, text, re.IGNORECASE)
        if m:
            data['plus_convenio'] = self._parse_spanish_number(m.group(1))

        # Cuenta Convenio / Complemento Convenio
        m = re.search(r'\*?\s*(?:Cuenta|Complemento)\s+Convenio\s+' + _NUM, text, re.IGNORECASE)
        if m:
            data['cuenta_convenio'] = self._parse_spanish_number(m.group(1))

        # P.P.P.EXTRAS (pagas extras prorrateadas)
        amounts_ppp = self._find_all_amounts(
            re.compile(r'P\.?P\.?P\.?\s*EXTRAS?\s+' + _NUM, re.IGNORECASE), text
        )
        if amounts_ppp:
            data['ppp_extras'] = round(sum(amounts_ppp), 2)
            data['pagas_extras_prorrateadas'] = True

        # Bonus / Incentivos
        amounts_bonus = self._find_all_amounts(
            re.compile(r'\*?\s*BONUS\s+' + _NUM, re.IGNORECASE), text
        )
        if amounts_bonus:
            data['bonus'] = round(sum(amounts_bonus), 2)

        # Teletrabajo / Trabajo remoto
        m = re.search(r'\*?\s*Teletrabajo\s+' + _NUM, text, re.IGNORECASE)
        if m:
            data['teletrabajo'] = self._parse_spanish_number(m.group(1))

        # Horas extraordinarias
        m = re.search(r'[Hh]oras?\s+[Ee]xtraordinarias?\s+' + _NUM, text)
        if m:
            data['overtime'] = self._parse_spanish_number(m.group(1))

        # Retribución flexible / Seguro médico
        m = re.search(r'(?:Retrib\.?\s*Flex|Seguro\s+M[eé]dico)\s+.*?' + _NUM, text, re.IGNORECASE)
        if m:
            data['seguro_medico'] = self._parse_spanish_number(m.group(1))

        # Antigüedad (complemento)
        m = re.search(r'\*?\s*Antig[uü]edad\s+' + _NUM, text, re.IGNORECASE)
        if m:
            data['complemento_antiguedad'] = self._parse_spanish_number(m.group(1))

        # Peligrosidad / Nocturnidad / Turnicidad
        for concept in ['peligrosidad', 'nocturnidad', 'turnicidad', 'disponibilidad']:
            m = re.search(rf'\*?\s*{concept}\s+{_NUM}', text, re.IGNORECASE)
            if m:
                data[concept] = self._parse_spanish_number(m.group(1))

        # --- 5. T. DEVENGADO (total devengado = gross salary) ---
        # In table format, T. DEVENGADO label is in header row, value in data row
        # Try direct: "T. DEVENGADO 4.583,50"
        m = re.search(r'T\.?\s*DEVENGADO\s+' + _NUM, text, re.IGNORECASE)
        if m:
            data['gross_salary'] = self._parse_spanish_number(m.group(1))

        if 'gross_salary' not in data:
            # Fallback: "TOTAL DEVENGADO 4.583,50"
            m = re.search(r'(?:TOTAL\s+DEVENGADO|DEVENGOS\s+TOTALES|TOTAL\s+HABERES)\s+' + _NUM, text, re.IGNORECASE)
            if m:
                data['gross_salary'] = self._parse_spanish_number(m.group(1))

        # NOTE: gross_salary fallback computation moved to section 11 (after deductions)

        # --- 6. DEDUCCIONES ---
        # IRPF — "TRIBUTACION I.R.P.F.19,03  590,12" (percentage glued to name)
        # Sum all occurrences across pages
        irpf_pattern = re.compile(
            r'(?:TRIBUTACION\s+)?I\.?R\.?P\.?F\.?\s*(\d{1,2},\d{2})\s+' + _NUM,
            re.IGNORECASE
        )
        irpf_matches = list(irpf_pattern.finditer(text))
        if irpf_matches:
            data['irpf_percentage'] = float(irpf_matches[0].group(1).replace(',', '.'))
            total_irpf = sum(
                self._parse_spanish_number(m.group(2)) or 0 for m in irpf_matches
            )
            data['irpf_amount'] = round(total_irpf, 2)
        else:
            # Fallback: "I.R.P.F. 18,15% 532,88" (with % sign)
            m = re.search(
                r'(?:TRIBUTACION\s+)?I\.?R\.?P\.?F\.?\s*[\s:]*(?:(\d{1,2},\d{2})\s*%\s*)?' + _NUM,
                text, re.IGNORECASE
            )
            if m:
                if m.group(1):
                    data['irpf_percentage'] = float(m.group(1).replace(',', '.'))
                data['irpf_amount'] = self._parse_spanish_number(m.group(2))

        # Cotización Contingencias Comunes — sum all pages
        cc_amounts = self._find_all_amounts(
            re.compile(r'COTIZACION\s+CONT\.?\s*COMU\.?\s+\d{1,2},\d{2}\s+' + _NUM, re.IGNORECASE), text
        )
        if cc_amounts:
            data['ss_contingencias_comunes'] = round(sum(cc_amounts), 2)

        # Cotización MEI (Mecanismo de Equidad Intergeneracional) — sum all pages
        mei_amounts = self._find_all_amounts(
            re.compile(r'COTIZACION\s+MEI\s+\d{1,2},\d{2}\s+' + _NUM, re.IGNORECASE), text
        )
        if mei_amounts:
            data['ss_mei'] = round(sum(mei_amounts), 2)

        # Cotización Formación — sum all pages
        fp_amounts = self._find_all_amounts(
            re.compile(r'COTIZACION\s+FORMACION\s+\d{1,2},\d{2}\s+' + _NUM, re.IGNORECASE), text
        )
        if fp_amounts:
            data['ss_formacion'] = round(sum(fp_amounts), 2)

        # Cotización Desempleo — sum all pages
        de_amounts = self._find_all_amounts(
            re.compile(r'(?:COTIZACION\s+)?DESEMPLEO\s+\d{1,2},\d{2}\s+' + _NUM, re.IGNORECASE), text
        )
        if de_amounts:
            data['ss_desempleo'] = round(sum(de_amounts), 2)

        # Descuento conceptos en especie
        m = re.search(r'Dcto\.?\s*Conceptos?\s+en\s+Especie\s+' + _NUM, text, re.IGNORECASE)
        if m:
            data['descuento_especie'] = self._parse_spanish_number(m.group(1))

        # Total SS contribution = sum of all cotizaciones del trabajador
        ss_total = sum(filter(None, [
            data.get('ss_contingencias_comunes'),
            data.get('ss_mei'),
            data.get('ss_formacion'),
            data.get('ss_desempleo'),
        ]))
        if ss_total > 0:
            data['ss_contribution'] = round(ss_total, 2)
        else:
            # Fallback: single "contingencias comunes" line
            m = re.search(r'(?:contingencias\s+comunes|aportaci[oó]n\s+trabajador)[\s:]*' + _NUM, text, re.IGNORECASE)
            if m:
                data['ss_contribution'] = self._parse_spanish_number(m.group(1))

        # T. A DEDUCIR (total deductions)
        m = re.search(r'T\.?\s*A?\s*DEDUCIR\s+' + _NUM, text, re.IGNORECASE)
        if m:
            data['total_deducir'] = self._parse_spanish_number(m.group(1))

        # --- 7. LIQUIDO A PERCIBIR (net salary) ---
        # May appear on separate line from amount in some PDF extractions
        m = re.search(r'L[IÍ]QUIDO\s+A\s+PERCIBIR\s*\n?\s*' + _NUM, text, re.IGNORECASE)
        if m:
            data['net_salary'] = self._parse_spanish_number(m.group(1))
        else:
            # Fallback with more distance between label and number
            m = re.search(r'L[IÍ]QUIDO\s+A\s+PERCIBIR[\s\S]{0,100}?' + _NUM, text, re.IGNORECASE)
            if m:
                data['net_salary'] = self._parse_spanish_number(m.group(1))
            else:
                m = re.search(r'(?:NETO|TOTAL\s+A\s+PERCIBIR)\s+' + _NUM, text, re.IGNORECASE)
                if m:
                    data['net_salary'] = self._parse_spanish_number(m.group(1))

        # --- 8. BASES DE COTIZACIÓN ---
        # Try direct (label + number on same line)
        m = re.search(r'BASE\s+S\.?S\.?\s+' + _NUM, text, re.IGNORECASE)
        if m:
            data['base_ss'] = self._parse_spanish_number(m.group(1))

        m = re.search(r'BASE\s+I\.?R\.?P\.?F\.?\s+' + _NUM, text, re.IGNORECASE)
        if m:
            data['base_irpf'] = self._parse_spanish_number(m.group(1))

        m = re.search(r'BASE\s+A\.?T\.?\s+' + _NUM, text, re.IGNORECASE)
        if m:
            data['base_at'] = self._parse_spanish_number(m.group(1))

        # Tabular layout fallback: headers on separate lines, values on one row
        # In many Spanish payslips, the summary section has headers like
        # "BASE S.S." / "T. A DEDUCIR" / "BASE I.R.P.F." on separate lines,
        # followed by a single data line with all values.
        # Typical order (6 values): BASE_SS, REM_TOTAL, PP_EXTRAS(or BASE_SS again),
        #   BASE_IRPF, T_DEVENGADO, T_A_DEDUCIR
        if 'base_ss' not in data or 'total_deducir' not in data:
            # Check that BASE S.S. header exists somewhere above
            has_base_header = bool(re.search(r'BASE\s+S\.?S\.?', text, re.IGNORECASE))
            if has_base_header:
                for line in text.split('\n'):
                    amounts = re.findall(_NUM, line)
                    if len(amounts) >= 5:
                        parsed = [self._parse_spanish_number(a) for a in amounts]
                        # All values should be > 100 (bases/totals are always > 100 EUR)
                        if all(p and p > 50 for p in parsed):
                            if 'base_ss' not in data:
                                data['base_ss'] = parsed[0]
                            # BASE I.R.P.F. is typically 4th value (index 3)
                            if 'base_irpf' not in data and len(parsed) >= 4:
                                # Find the value that differs (base_irpf may differ from base_ss)
                                data['base_irpf'] = parsed[3]
                            if 'gross_salary' not in data and len(parsed) >= 5:
                                data['gross_salary'] = parsed[4]
                            if 'total_deducir' not in data:
                                data['total_deducir'] = parsed[-1]
                            if 'base_at' not in data:
                                data['base_at'] = parsed[0]
                            break

        # --- 9. DATOS BANCARIOS ---
        m = re.search(r'IBAN[\s:]*([A-Z]{2}\d{2}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4})', text, re.IGNORECASE)
        if m:
            data['iban'] = m.group(1).replace(' ', '')

        # --- 10. APORTACIÓN EMPRESARIAL (employer costs) ---
        emp_cc = re.search(r'Contingencias\s+comunes.*?' + _NUM + r'\s+' + _NUM, text, re.IGNORECASE)
        if emp_cc:
            data['employer_ss_comunes'] = self._parse_spanish_number(emp_cc.group(2))

        # MEI employer: "Mecanismo Equidad Intergeneracional (MEI)..  BASE  TIPO  AMOUNT"
        emp_mei = re.search(r'Equidad\s+Intergeneracional.*?' + _NUM + r'\s+' + _NUM + r'\s+' + _NUM, text, re.IGNORECASE)
        if emp_mei:
            data['employer_mei'] = self._parse_spanish_number(emp_mei.group(3))
        else:
            emp_mei = re.search(r'MEI\).*?' + _NUM + r'\s+\d+,\d+\s+' + _NUM, text, re.IGNORECASE)
            if emp_mei:
                data['employer_mei'] = self._parse_spanish_number(emp_mei.group(2))

        emp_at = re.search(r'AT\s+y\s+EP.*?' + _NUM + r'\s+' + _NUM, text, re.IGNORECASE)
        if emp_at:
            data['employer_at_ep'] = self._parse_spanish_number(emp_at.group(2))

        emp_des = re.search(r'Desempleo\.*\s+' + _NUM + r'\s+' + _NUM + r'\s+' + _NUM, text, re.IGNORECASE)
        if emp_des:
            data['employer_desempleo'] = self._parse_spanish_number(emp_des.group(3))

        emp_fogasa = re.search(r'Garant[ií]a\s+Salarial.*?' + _NUM + r'\s+' + _NUM, text, re.IGNORECASE)
        if emp_fogasa:
            data['employer_fogasa'] = self._parse_spanish_number(emp_fogasa.group(2))

        # --- 11. DERIVED CALCULATIONS ---
        # Gross salary fallback (after deductions are known)
        if 'gross_salary' not in data:
            net = data.get('net_salary')
            total_ded = data.get('total_deducir')
            if net and total_ded:
                data['gross_salary'] = round(net + total_ded, 2)
                data['gross_salary_computed'] = True

        if 'gross_salary' not in data:
            net = data.get('net_salary')
            irpf = data.get('irpf_amount', 0)
            ss = data.get('ss_contribution', 0)
            especie = data.get('descuento_especie', 0)
            if net and (irpf or ss):
                data['gross_salary'] = round(net + irpf + ss + especie, 2)
                data['gross_salary_computed'] = True

        if data.get('irpf_amount') and data.get('gross_salary') and data['gross_salary'] > 0:
            data['irpf_effective_rate'] = round(
                (data['irpf_amount'] / data['gross_salary']) * 100, 2
            )

        if data.get('ss_contribution') and data.get('gross_salary') and data['gross_salary'] > 0:
            data['ss_effective_rate'] = round(
                (data['ss_contribution'] / data['gross_salary']) * 100, 2
            )

        # Pagas extras: infer from PPP presence
        if data.get('pagas_extras_prorrateadas'):
            data['num_pagas_anuales'] = 12
        elif data.get('gross_salary') and data.get('base_salary'):
            # If gross is significantly more than base + complements, probably 14 pagas
            data['num_pagas_anuales'] = 14  # default assumption

        # Region detection from address
        region = self._detect_region(text)
        if region:
            data['region'] = region

        return data

    def _detect_region(self, text: str) -> Optional[str]:
        """Detecta la CCAA del trabajador por la dirección postal."""
        # Map of cities/provinces to CCAA
        region_keywords = {
            'Madrid': 'Madrid', 'Barcelona': 'Cataluna', 'Valencia': 'Valencia',
            'Sevilla': 'Andalucia', 'Zaragoza': 'Aragon', 'Malaga': 'Andalucia',
            'Murcia': 'Murcia', 'Palma': 'Baleares', 'Bilbao': 'Bizkaia',
            'Alicante': 'Valencia', 'Valladolid': 'Castilla y Leon',
            'Vigo': 'Galicia', 'Oviedo': 'Asturias', 'Santander': 'Cantabria',
            'Pamplona': 'Navarra', 'Vitoria': 'Araba', 'San Sebastian': 'Gipuzkoa',
            'Donostia': 'Gipuzkoa', 'Las Palmas': 'Canarias', 'Tenerife': 'Canarias',
            'Ceuta': 'Ceuta', 'Melilla': 'Melilla', 'Logroño': 'La Rioja',
            'Toledo': 'Castilla-La Mancha', 'Badajoz': 'Extremadura',
            'Caceres': 'Extremadura', 'Cordoba': 'Andalucia', 'Granada': 'Andalucia',
            'A Coruña': 'Galicia', 'Coruña': 'Galicia', 'Gijon': 'Asturias',
        }
        text_upper = text.upper()
        for city, ccaa in region_keywords.items():
            if city.upper() in text_upper:
                return ccaa
        return None

    def calculate_effective_tax_rate(self, irpf_amount: float, gross_salary: float) -> Optional[float]:
        """Calcula el tipo efectivo de IRPF"""
        if gross_salary and gross_salary > 0:
            return round((irpf_amount / gross_salary) * 100, 2)
        return None

    def generate_summary(self, data: Dict) -> str:
        """Genera un resumen legible de la nómina"""
        parts = []

        if data.get('period_month') and data.get('period_year'):
            parts.append(f"Periodo: {data['period_month']}/{data['period_year']}")

        if data.get('company_name'):
            parts.append(f"Empresa: {data['company_name']}")

        if data.get('gross_salary'):
            parts.append(f"Bruto: {data['gross_salary']:,.2f}EUR")

        if data.get('net_salary'):
            parts.append(f"Neto: {data['net_salary']:,.2f}EUR")

        if data.get('irpf_amount'):
            pct = f" ({data['irpf_percentage']}%)" if data.get('irpf_percentage') else ""
            parts.append(f"IRPF: {data['irpf_amount']:,.2f}EUR{pct}")

        if data.get('ss_contribution'):
            parts.append(f"SS: {data['ss_contribution']:,.2f}EUR")

        if data.get('bonus'):
            parts.append(f"Bonus: {data['bonus']:,.2f}EUR")

        return " | ".join(parts) if parts else "Sin datos extraídos"

    def get_extraction_stats(self, data: Dict) -> Dict:
        """Obtiene estadísticas de la extracción"""
        key_fields = [
            'period_month', 'company_name', 'employee_nif',
            'gross_salary', 'net_salary', 'base_salary',
            'irpf_amount', 'irpf_percentage', 'ss_contribution',
        ]
        extracted = sum(1 for f in key_fields if data.get(f) is not None)

        return {
            'total_fields': len(key_fields),
            'extracted_fields': extracted,
            'extraction_rate': round((extracted / len(key_fields)) * 100, 2),
            'status': data.get('extraction_status', 'unknown')
        }

    # -------------------------------------------------------------------------
    # PII Anonymization — NEVER send real PII to LLM
    # -------------------------------------------------------------------------

    # Fields that contain PII and must NEVER reach the LLM
    PII_FIELDS = {
        'employee_nif', 'employee_name', 'employee_ss',
        'company_nif', 'company_ss_number',
        'iban', 'seniority_date',
    }

    @staticmethod
    def anonymize_text(text: str) -> str:
        """
        Redact PII from raw PDF text BEFORE sending to LLM.

        Redacts: DNI/NIE, NIF/CIF, IBAN, SS numbers, full addresses,
        phone numbers, email addresses.
        Keeps: amounts, percentages, dates, job categories, concepts.
        """
        if not text:
            return text

        result = text

        # DNI: 45308568V → [DNI_REDACTED]
        result = re.sub(r'\b\d{8}[A-Z]\b', '[DNI_REDACTED]', result)

        # NIE: X1234567A → [NIE_REDACTED]
        result = re.sub(r'\b[XYZ]\d{7}[A-Z]\b', '[NIE_REDACTED]', result)

        # NIF/CIF empresa: A83115667 → [NIF_REDACTED]
        result = re.sub(r'\b[A-HJ-NP-SUVW]\d{7,8}\b', '[NIF_REDACTED]', result)

        # IBAN: ES89 1465 0100 9117 4732 8589 → [IBAN_REDACTED]
        result = re.sub(
            r'[A-Z]{2}\d{2}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}',
            '[IBAN_REDACTED]', result
        )

        # SWIFT/BIC: only after "SWIFT" or "BIC" keyword
        result = re.sub(r'(?:SWIFT|BIC)[/:\s]*([A-Z]{4}[A-Z]{2}[A-Z0-9]{2,5})', r'SWIFT [SWIFT_REDACTED]', result)

        # Nº Afiliación SS: 52/10066317-86 → [SS_NUM_REDACTED]
        result = re.sub(r'\b\d{2}/\d{7,10}-\d{2}\b', '[SS_NUM_REDACTED]', result)

        # Nº Inscripción SS empresa: 50/1207052-01 → [SS_EMP_REDACTED]
        # (already covered by pattern above)

        # Phone numbers: +34 612345678 or 612 345 678
        result = re.sub(r'(?:\+34\s?)?\b[6-9]\d{2}\s?\d{3}\s?\d{3}\b', '[PHONE_REDACTED]', result)

        # Email addresses
        result = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', result)

        # Full street addresses: "AV CESAR AUGUSTO 56 1" — redact after street type
        result = re.sub(
            r'(?:AV|AVDA|AVENIDA|C/|CL|CALLE|PZ|PLAZA|PS|PASEO|RONDA|CTRA|CAMINO)\s+[A-ZÀ-Ú\s]+\d+[A-Z\s,]*\d*',
            '[ADDRESS_REDACTED]',
            result, flags=re.IGNORECASE
        )

        # Postal codes (5 digits at line start or after spaces, near city names)
        result = re.sub(r'\b\d{5}\b(?=\s+[A-ZÀ-Ú])', '[CP_REDACTED]', result)

        # Employee name: "APELLIDO APELLIDO, NOMBRE" pattern → redact
        result = re.sub(
            r'\b([A-ZÀ-Ú]{2,}\s+[A-ZÀ-Ú]{2,},\s*[A-ZÀ-Ú]{2,}(?:\s+[A-ZÀ-Ú]\.?)*)\b',
            '[NOMBRE_REDACTED]',
            result
        )

        return result

    @staticmethod
    def anonymize_data(data: Dict) -> Dict:
        """
        Remove PII fields from extracted payslip data before sending to LLM.
        Returns a copy — does NOT modify the original.

        Keeps: all financial amounts, percentages, dates, categories, region.
        Removes: DNI, NIF, IBAN, SS numbers, full names, addresses.
        """
        safe = {}
        for key, value in data.items():
            if key in PayslipExtractor.PII_FIELDS:
                continue
            if key == 'full_text':
                continue  # never send raw text to LLM
            safe[key] = value
        return safe
