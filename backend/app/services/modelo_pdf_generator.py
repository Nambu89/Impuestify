"""
Modelo PDF Generator for TaxIA.

Generates informational PDFs with calculated casilla data for
Spanish tax form models (Modelos Tributarios).

Fully implemented: 303, 130, 131, 200, 308, 349, 390, 720, 721, IPSI.
Placeholder stubs (under development): 100, 309, 420, 450, 455.
"""

import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Modelo display names
MODELO_NAMES: Dict[str, str] = {
    "303": "Autoliquidación IVA",
    "130": "IRPF Pago Fraccionado — Estimación Directa",
    "200": "Impuesto sobre Sociedades",
    "308": "IVA — Régimen Especial (Recargo de Equivalencia)",
    "720": "Declaración de Bienes y Derechos en el Extranjero",
    "721": "Declaración de Monedas Virtuales en el Extranjero",
    "ipsi": "IPSI — Impuesto sobre la Producción, los Servicios y la Importación",
    # Placeholders (en desarrollo)
    "100": "Declaración del IRPF (Renta)",
    "131": "IRPF Pago Fraccionado — Estimación Objetiva (Módulos)",
    "309": "Declaración no periódica — IVA",
    "349": "Declaración recapitulativa de operaciones intracomunitarias",
    "390": "Resumen anual del IVA",
    "420": "Autoliquidación IGIC (Canarias)",
    "450": "AIEM — Autoliquidación trimestral productores (Canarias)",
    "455": "AIEM ZEC — Autoliquidación anual operadores ZEC (Canarias)",
}

# Foral variant names
FORAL_NAMES: Dict[str, str] = {
    "300": "Modelo 300 — Autoliquidación IVA (Gipuzkoa)",
    "F69": "Modelo F69 — Autoliquidación IVA (Navarra)",
    "420": "Modelo 420 — Autoliquidación IGIC (Canarias)",
    "130-bizkaia": "Modelo 130 Bizkaia — Pago Fraccionado IRPF",
    "130-gipuzkoa": "Modelo 130 Gipuzkoa — Pago Fraccionado IRPF",
    "130-araba": "Modelo 130 Araba/Álava — Pago Fraccionado IRPF",
    "130-navarra": "Modelo 130 Navarra — Pago Fraccionado IRPF",
}

# Variantes forales del Modelo 130 admitidas en `user_info["variante_foral"]`
MODELO_130_FORAL_VARIANTS = {"130-bizkaia", "130-gipuzkoa", "130-araba", "130-navarra"}

# Modelos con render completo
FULL_MODELOS = {"303", "130", "131", "200", "308", "349", "390", "720", "721", "ipsi"}

# Modelos en desarrollo — devuelven PDF placeholder mínimo
PLACEHOLDER_MODELOS = {"100", "309", "420", "450", "455"}

VALID_MODELOS = FULL_MODELOS | PLACEHOLDER_MODELOS


def _format_eur(amount: float) -> str:
    """Format amount in Spanish style: 1.234,56 EUR."""
    if amount is None:
        return "0,00 EUR"
    # Format with 2 decimal places, then swap . and ,
    formatted = f"{abs(amount):,.2f}"
    # US style: 1,234.56 -> swap to Spanish: 1.234,56
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    sign = "-" if amount < 0 else ""
    return f"{sign}{formatted} EUR"


class ModeloPDFGenerator:
    """Generates informational PDFs for Spanish tax form models."""

    def generate(
        self,
        modelo_type: str,
        data: dict,
        user_info: dict,
        trimestre: str = "1T",
        ejercicio: int = 2026,
    ) -> bytes:
        """
        Generate a PDF for the given modelo type.

        Args:
            modelo_type: One of "303", "130", "308", "720", "721", "ipsi"
            data: Dict with casilla data (structure varies by modelo)
            user_info: Dict with contributor info (nombre, nif)
            trimestre: Period label ("1T", "2T", "3T", "4T", "anual")
            ejercicio: Fiscal year

        Returns:
            PDF file as bytes

        Raises:
            ValueError: If modelo_type is not supported
        """
        if modelo_type not in VALID_MODELOS:
            raise ValueError(
                f"Modelo '{modelo_type}' no soportado. "
                f"Valores válidos: {', '.join(sorted(VALID_MODELOS))}"
            )

        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import SimpleDocTemplate, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT  # noqa: F401

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        # Store styles for use in render methods
        self._setup_styles()

        story: list = []

        # Header
        self._render_header(story, modelo_type, trimestre, ejercicio, user_info)

        # Contributor data
        self._render_contribuyente(story, user_info)

        # Modelo-specific layout
        render_map = {
            "303": self._render_303,
            "130": self._render_130,
            "131": self._render_131,
            "200": self._render_200,
            "308": self._render_308,
            "349": self._render_modelo_349,
            "390": self._render_modelo_390,
            "720": self._render_720,
            "721": self._render_721,
            "ipsi": self._render_ipsi,
        }

        if modelo_type in render_map:
            render_map[modelo_type](story, data)
        else:
            # Placeholder stub para modelos en desarrollo (100, 309, 420)
            self._render_placeholder(
                story,
                modelo_type=modelo_type,
                data=data,
                user_info=user_info,
                trimestre=trimestre,
                ejercicio=ejercicio,
            )

        # Disclaimer
        story.append(Spacer(1, 8 * mm))
        self._render_disclaimer(story)

        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        logger.info(
            "Modelo %s PDF generated: %d bytes, trimestre=%s, ejercicio=%d",
            modelo_type,
            len(pdf_bytes),
            trimestre,
            ejercicio,
        )
        return pdf_bytes

    # ------------------------------------------------------------------ #
    # Style setup
    # ------------------------------------------------------------------ #

    def _setup_styles(self):
        """Initialize ReportLab styles (mirrors report_generator.py)."""
        from reportlab.lib.colors import HexColor
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT

        self._primary = HexColor("#1a56db")
        self._dark = HexColor("#1f2937")
        self._gray = HexColor("#6b7280")
        self._light_bg = HexColor("#f3f4f6")
        self._white = HexColor("#ffffff")
        self._green = HexColor("#059669")
        self._red = HexColor("#dc2626")

        styles = getSampleStyleSheet()

        self._title_style = ParagraphStyle(
            "ModeloTitle",
            parent=styles["Title"],
            fontSize=22,
            textColor=self._primary,
            spaceAfter=4,
        )
        self._subtitle_style = ParagraphStyle(
            "ModeloSubtitle",
            parent=styles["Normal"],
            fontSize=12,
            textColor=self._gray,
        )
        self._heading_style = ParagraphStyle(
            "ModeloHeading",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=self._dark,
            spaceBefore=24,
            spaceAfter=8,
        )
        self._body_style = ParagraphStyle(
            "ModeloBody",
            parent=styles["Normal"],
            fontSize=10,
            textColor=self._dark,
            leading=14,
        )
        self._small_style = ParagraphStyle(
            "ModeloSmall",
            parent=styles["Normal"],
            fontSize=8,
            textColor=self._gray,
            leading=10,
        )
        self._footer_style = ParagraphStyle(
            "ModeloFooter",
            parent=styles["Normal"],
            fontSize=8,
            textColor=self._gray,
            alignment=TA_CENTER,
        )
        self._result_pay_style = ParagraphStyle(
            "ResultPay",
            parent=styles["Normal"],
            fontSize=12,
            textColor=self._red,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        )
        self._result_refund_style = ParagraphStyle(
            "ResultRefund",
            parent=styles["Normal"],
            fontSize=12,
            textColor=self._green,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        )

    # ------------------------------------------------------------------ #
    # Common render helpers
    # ------------------------------------------------------------------ #

    def _render_header(
        self,
        story: list,
        modelo_type: str,
        trimestre: str,
        ejercicio: int,
        user_info: dict,
    ):
        """Render the document header with modelo name and period."""
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, Spacer, HRFlowable

        # Check for foral variant
        variante_foral = (user_info or {}).get("variante_foral") or (
            {} if not isinstance(user_info, dict) else user_info
        ).get("variante_foral")

        if variante_foral and variante_foral in FORAL_NAMES:
            title_text = FORAL_NAMES[variante_foral]
        else:
            modelo_name = MODELO_NAMES.get(modelo_type, modelo_type)
            title_text = f"Modelo {modelo_type.upper()} — {modelo_name}"

        story.append(Paragraph("Impuestify", self._title_style))
        story.append(Paragraph(title_text, self._subtitle_style))
        story.append(
            Paragraph(
                f"Periodo: {trimestre} — Ejercicio {ejercicio}",
                self._subtitle_style,
            )
        )
        story.append(Spacer(1, 4 * mm))
        story.append(HRFlowable(width="100%", thickness=1, color=self._primary))
        story.append(Spacer(1, 6 * mm))

    def _render_contribuyente(self, story: list, user_info: dict):
        """Render contributor data section."""
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, Table, TableStyle, Spacer
        from xml.sax.saxutils import escape

        if not user_info:
            return

        nombre = escape(user_info.get("nombre", ""))
        nif = escape(user_info.get("nif", ""))
        if not nombre and not nif:
            return

        story.append(Paragraph("Datos del contribuyente", self._heading_style))

        rows = [["Campo", "Valor"]]
        if nombre:
            rows.append(["Nombre / Razón social", nombre])
        if nif:
            rows.append(["NIF / CIF", nif])

        t = Table(rows, colWidths=[60 * mm, 100 * mm])
        t.setStyle(self._header_table_style())
        story.append(t)
        story.append(Spacer(1, 4 * mm))

    def _render_casillas_table(
        self,
        story: list,
        casillas: List[Tuple[str, str, float]],
        title: Optional[str] = None,
    ):
        """
        Render a reusable table of casillas.

        Args:
            casillas: List of (casilla_num, description, amount) tuples
            title: Optional section heading
        """
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, Table, TableStyle

        if title:
            story.append(Paragraph(title, self._heading_style))

        rows = [["Casilla", "Concepto", "Importe"]]
        for casilla_num, desc, amount in casillas:
            rows.append([casilla_num, desc, _format_eur(amount)])

        t = Table(rows, colWidths=[20 * mm, 100 * mm, 40 * mm])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), self._primary),
                    ("TEXTCOLOR", (0, 0), (-1, 0), self._white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 1), (-1, -1), self._light_bg),
                    ("GRID", (0, 0), (-1, -1), 0.5, self._gray),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(t)

    def _render_resultado(self, story: list, label: str, amount: float):
        """Render a highlighted result box. Green if refund, red if pay."""
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import (
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )

        is_refund = amount <= 0
        bg_color = HexColor("#ecfdf5") if is_refund else HexColor("#fef2f2")
        text_style = self._result_refund_style if is_refund else self._result_pay_style

        text = f"<b>{label}: {_format_eur(amount)}</b>"
        cell = Paragraph(text, text_style)

        t = Table([[cell]], colWidths=[160 * mm])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), bg_color),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("BOX", (0, 0), (-1, -1), 1, self._green if is_refund else self._red),
                ]
            )
        )
        story.append(Spacer(1, 4 * mm))
        story.append(t)

    def _render_disclaimer(self, story: list):
        """Render legal disclaimer at the bottom."""
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, Spacer, HRFlowable

        story.append(HRFlowable(width="100%", thickness=0.5, color=self._gray))
        story.append(Spacer(1, 3 * mm))
        story.append(
            Paragraph(
                "AVISO LEGAL: Este documento ha sido generado automáticamente por Impuestify y tiene "
                "carácter meramente orientativo e informativo. No constituye una declaración tributaria "
                "oficial ni sustituye la presentación del modelo ante la AEAT o hacienda foral correspondiente. "
                "Los cálculos se basan en la información proporcionada por el usuario y en la normativa fiscal "
                "vigente. Impuestify no se responsabiliza de errores u omisiones en los datos proporcionados "
                "ni de las decisiones tomadas en base a este documento.",
                self._small_style,
            )
        )
        story.append(Spacer(1, 3 * mm))
        now = datetime.now(timezone.utc)
        story.append(
            Paragraph(
                f"Generado el {now.strftime('%d/%m/%Y a las %H:%M')} UTC por Impuestify (impuestify.com)",
                self._footer_style,
            )
        )

    def _header_table_style(self):
        """Standard header table style matching report_generator.py."""
        from reportlab.lib.units import mm
        from reportlab.platypus import TableStyle

        return TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), self._primary),
                ("TEXTCOLOR", (0, 0), (-1, 0), self._white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 1), (-1, -1), self._light_bg),
                ("GRID", (0, 0), (-1, -1), 0.5, self._gray),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )

    def _simple_section_table(
        self,
        story: list,
        title: str,
        rows_data: List[Tuple[str, str]],
    ):
        """Render a simple two-column table (label, value) with a heading."""
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, Table, TableStyle

        story.append(Paragraph(title, self._heading_style))
        rows = [["Concepto", "Valor"]]
        rows.extend(list(rows_data))

        t = Table(rows, colWidths=[110 * mm, 50 * mm])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), self._primary),
                    ("TEXTCOLOR", (0, 0), (-1, 0), self._white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 1), (-1, -1), self._light_bg),
                    ("GRID", (0, 0), (-1, -1), 0.5, self._gray),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ]
            )
        )
        story.append(t)

    # ------------------------------------------------------------------ #
    # Modelo 303 — IVA trimestral
    # ------------------------------------------------------------------ #

    def _render_303(self, story: list, data: dict):
        """Render Modelo 303 layout: IVA devengado, deducible, resultado."""
        # Extract from tool return structure or flat casillas dict
        iva_dev = data.get("iva_devengado", {})
        iva_ded = data.get("iva_deducible", {})
        resultado_data = data.get("resultado", {})
        casillas = data.get("casillas", {})

        # IVA Devengado
        devengado_rows: List[Tuple[str, str, float]] = []
        # Try structured data first, then flat casillas
        base_21 = iva_dev.get("cuota_21") or casillas.get("03", 0)
        base_10 = iva_dev.get("cuota_10") or casillas.get("06", 0)
        base_4 = iva_dev.get("cuota_4") or casillas.get("09", 0)
        cuota_intra = iva_dev.get("cuota_intracomunitaria") or casillas.get("12", 0)
        total_dev = iva_dev.get("total_devengado") or casillas.get("27", 0)

        if base_21:
            devengado_rows.append(("03", "Cuota IVA al 21%", base_21))
        if base_10:
            devengado_rows.append(("06", "Cuota IVA al 10%", base_10))
        if base_4:
            devengado_rows.append(("09", "Cuota IVA al 4%", base_4))
        if cuota_intra:
            devengado_rows.append(("12", "Cuota adquisiciones intracomunitarias", cuota_intra))
        devengado_rows.append(("27", "Total IVA devengado", total_dev))

        self._render_casillas_table(story, devengado_rows, "IVA Devengado (repercutido)")

        # IVA Deducible
        deducible_rows: List[Tuple[str, str, float]] = []
        bienes_corr = iva_ded.get("bienes_corrientes") or casillas.get("29", 0)
        bienes_inv = iva_ded.get("bienes_inversion") or casillas.get("31", 0)
        importaciones = iva_ded.get("importaciones") or casillas.get("33", 0)
        intracom_ded = iva_ded.get("intracomunitarias") or casillas.get("37", 0)
        rectificacion = iva_ded.get("rectificacion") or casillas.get("41", 0)
        total_ded = iva_ded.get("total_deducible") or casillas.get("45", 0)

        if bienes_corr:
            deducible_rows.append(("29", "Bienes y servicios corrientes", bienes_corr))
        if bienes_inv:
            deducible_rows.append(("31", "Bienes de inversión", bienes_inv))
        if importaciones:
            deducible_rows.append(("33", "Importaciones", importaciones))
        if intracom_ded:
            deducible_rows.append(("37", "Adquisiciones intracomunitarias", intracom_ded))
        if rectificacion:
            deducible_rows.append(("41", "Rectificación deducciones", rectificacion))
        deducible_rows.append(("45", "Total a deducir", total_ded))

        self._render_casillas_table(story, deducible_rows, "IVA Deducible (soportado)")

        # Resultado
        resultado_final = resultado_data.get("resultado_final") or data.get("resultado_final", 0)
        compensacion = resultado_data.get("compensacion_anterior") or casillas.get("71", 0)
        regimen_gen = resultado_data.get("regimen_general") or casillas.get("46", 0)

        resultado_rows: List[Tuple[str, str, float]] = [
            ("46", "Resultado régimen general", regimen_gen),
        ]
        if compensacion:
            resultado_rows.append(("71", "Compensación periodos anteriores", -compensacion))

        self._render_casillas_table(story, resultado_rows, "Resultado")
        self._render_resultado(story, "Resultado final", resultado_final)

    # ------------------------------------------------------------------ #
    # Modelo 130 — Pago Fraccionado IRPF
    # ------------------------------------------------------------------ #

    def _render_130(self, story: list, data: dict):
        """Render Modelo 130 layout: Sections I-IV.

        If `data["variante_foral"]` is one of the foral 130 variants
        ("130-bizkaia", "130-gipuzkoa", "130-araba", "130-navarra"), the foral
        renderer is used instead. The foral payload is the dict returned by
        :func:`calculate_modelo_130_foral_tool` (contains `casillas`,
        `regimen` / `modalidad`, `tipo_aplicado`, `plazo`, `resultado_final`).
        """
        variante = (data or {}).get("variante_foral")
        if variante in MODELO_130_FORAL_VARIANTS:
            self._render_130_foral(story, data, variante)
            return

        seccion_i = data.get("seccion_i", {})

        # Section I
        s1_rows: List[Tuple[str, str, float]] = [
            ("01", "Ingresos computables", seccion_i.get("ingresos_computables", 0)),
            ("02", "Gastos deducibles", seccion_i.get("gastos_deducibles", 0)),
            ("03", "Rendimiento neto", seccion_i.get("rendimiento_neto", 0)),
            ("04", "20% del rendimiento neto", seccion_i.get("veinte_porciento", 0)),
        ]

        retenciones = seccion_i.get("retenciones", 0)
        if retenciones:
            s1_rows.append(("05", "Retenciones e ingresos a cuenta", retenciones))

        pagos_ant = seccion_i.get("pagos_anteriores", 0)
        if pagos_ant:
            s1_rows.append(("06", "Pagos fraccionados anteriores", pagos_ant))

        s1_rows.append(("07", "Resultado sección I", seccion_i.get("resultado_seccion", 0)))

        self._render_casillas_table(story, s1_rows, "Sección I: Actividades en estimación directa")

        # Section IV — deduccion 80 bis
        deduccion = data.get("deduccion_80bis", 0)
        if deduccion > 0:
            self._simple_section_table(
                story,
                "Sección IV: Deducción art. 80 bis LIRPF",
                [("Deducción trimestral", _format_eur(deduccion))],
            )

        # Resultado
        resultado_final = data.get("resultado_final", 0)
        self._render_resultado(story, "Resultado a ingresar", resultado_final)

    # ------------------------------------------------------------------ #
    # Modelo 130 — Variantes Forales (Bizkaia / Gipuzkoa / Araba / Navarra)
    # ------------------------------------------------------------------ #

    _FORAL_130_LABELS: Dict[str, str] = {
        "130-bizkaia": "Modelo 130 Bizkaia",
        "130-gipuzkoa": "Modelo 130 Gipuzkoa",
        "130-araba": "Modelo 130 Araba/Álava",
        "130-navarra": "Modelo 130 Navarra",
    }

    # Etiquetas humanas para las casillas devueltas por cada calculator foral.
    # Si una clave no aparece aquí, se muestra tal cual (con underscores).
    _FORAL_130_CASILLA_LABELS: Dict[str, str] = {
        # Bizkaia general / excepcional
        "01_base_calculo": "Base de cálculo",
        "02_tipo_aplicable_pct": "Tipo aplicable (%)",
        "03_cuota_base": "Cuota base",
        "04_retenciones_penultimo": "Retenciones penúltimo año",
        "05_minoracion_25pct_retenciones": "Minoración 25% retenciones",
        "06_resultado_pago_fraccionado": "Resultado pago fraccionado",
        # Bizkaia primeros 2 años
        "01_ingresos_acumulados": "Ingresos acumulados",
        "02_gastos_acumulados": "Gastos acumulados",
        "03_rendimiento_neto_acumulado": "Rendimiento neto acumulado",
        "04_cuota_20pct": "Cuota 20%",
        "05_retenciones_acumuladas": "Retenciones acumuladas",
        "06_pagos_anteriores": "Pagos fraccionados anteriores",
        "07_resultado_pago_fraccionado": "Resultado pago fraccionado",
        # Gipuzkoa general
        "01_rend_neto_penultimo": "Rendimiento neto penúltimo año",
        # Gipuzkoa excepcional
        "01_volumen_operaciones_trimestre": "Volumen operaciones trimestre",
        "04_retenciones_trimestre": "Retenciones del trimestre",
        "05_resultado_pago_fraccionado": "Resultado pago fraccionado",
        # Araba
        "01_ingresos_trimestre": "Ingresos del trimestre",
        "02_gastos_trimestre": "Gastos del trimestre",
        "03_rendimiento_neto_trimestral": "Rendimiento neto trimestral",
        "04_cuota_5pct": "Cuota 5%",
        "05_retenciones_trimestre": "Retenciones del trimestre",
        # Navarra modalidad primera (casillas oficiales 131-140)
        "131_rend_neto_penultimo": "Rendimiento neto penúltimo año",
        "132_porcentaje_tabla": "% tabla progresiva",
        "133_cuota_anual": "Cuota anual",
        "134_retenciones_penultimo": "Retenciones penúltimo año",
        "135_cuota_neta_anual": "Cuota neta anual",
        "140_pago_trimestral": "Pago trimestral",
        # Navarra modalidad segunda (casillas oficiales 01-15)
        "04_factor_anualizacion": "Factor anualización",
        "05_rendimiento_neto_anualizado": "Rendimiento neto anualizado",
        "06_porcentaje_tabla": "% tabla progresiva",
        "07_retenciones_acumuladas": "Retenciones acumuladas",
        "08_pagos_anteriores": "Pagos fraccionados anteriores",
        "10_cuota_sobre_rend_real": "Cuota sobre rendimiento real",
        "15_resultado_pago_fraccionado": "Resultado pago fraccionado",
    }

    def _render_130_foral(self, story: list, data: dict, variante: str):
        """
        Render una variante foral del Modelo 130.

        Args:
            data: Dict devuelto por `calculate_modelo_130_foral_tool` que
                contiene `casillas`, `tipo_aplicado`, `regimen` / `modalidad`,
                `plazo`, `resultado_final`.
            variante: Una de las claves de `MODELO_130_FORAL_VARIANTS`.
        """
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, Spacer

        # ---- Cabecera con régimen / modalidad ----
        territorio_label = self._FORAL_130_LABELS.get(variante, "Modelo 130 Foral")

        if data.get("dispensado"):
            self._render_resultado(
                story,
                f"{territorio_label} — DISPENSA DE PRESENTACIÓN",
                0.0,
            )
            disclaimer = (
                f"Con un {data.get('pct_retencion_anio_anterior', 0):.1f}% de "
                f"retención el año anterior (umbral aplicable "
                f"{data.get('umbral_dispensa_pct', 0):.0f}%), no estás "
                f"obligado a presentar el Modelo 130 este trimestre."
            )
            story.append(Spacer(1, 4 * mm))
            story.append(Paragraph(disclaimer, self._body_style))
            return

        regimen_modalidad: List[str] = []
        if data.get("regimen"):
            regimen_modalidad.append(f"Régimen: <b>{data['regimen']}</b>")
        if data.get("modalidad"):
            regimen_modalidad.append(f"Modalidad: <b>{data['modalidad']}</b>")
        tipo = data.get("tipo_aplicado")
        if tipo is not None:
            regimen_modalidad.append(f"Tipo aplicado: <b>{tipo}%</b>")

        if regimen_modalidad:
            story.append(Paragraph(" — ".join(regimen_modalidad), self._body_style))
            story.append(Spacer(1, 3 * mm))

        # ---- Tabla de casillas ----
        casillas = data.get("casillas", {})
        rows: List[Tuple[str, str, float]] = []
        for key, value in casillas.items():
            # key formato "NN_descripcion" → numero + label legible
            num, _, _ = key.partition("_")
            label = self._FORAL_130_CASILLA_LABELS.get(key, key.replace("_", " "))
            try:
                amount = float(value)
            except (TypeError, ValueError):
                amount = 0.0
            rows.append((num, label, amount))

        if rows:
            self._render_casillas_table(
                story,
                rows,
                f"{territorio_label} — Casillas",
            )

        # ---- Resultado ----
        resultado_final = data.get("resultado_final", 0)
        self._render_resultado(story, "Resultado a ingresar", resultado_final)

        # ---- Plazo informativo ----
        plazo = data.get("plazo")
        if plazo:
            story.append(Spacer(1, 3 * mm))
            story.append(
                Paragraph(
                    f"Plazo de presentación: <b>{plazo}</b>.",
                    self._small_style,
                )
            )

    # ------------------------------------------------------------------ #
    # Modelo 131 — Pago Fraccionado IRPF Estimación Objetiva (Módulos)
    # ------------------------------------------------------------------ #

    def _render_131(self, story: list, data: dict):
        """
        Render Modelo 131 layout — apartados I (empresarial), II (sin
        datos-base) y III (agraria).

        El `data` debe seguir la estructura devuelta por `Modelo131Calculator`
        (vía `calculate_modelo_131_tool`): contiene `casillas` (01-12),
        `desglose`, `apartado`, `tipo_aplicado`.
        """
        casillas = data.get("casillas", {})
        desglose = data.get("desglose", {})
        apartado = data.get("apartado", "I")

        # Sección I/II/III — cuotas
        if apartado == "I":
            cuota_rows: List[Tuple[str, str, float]] = [
                (
                    "01",
                    "Rendimiento neto previo módulos (anual)",
                    casillas.get("01_rendimiento_neto_modulos", 0),
                ),
                ("02", "Tipo aplicable (%)", casillas.get("02_tipo_aplicable", 0)),
                (
                    "03",
                    "Resultado actividades empresariales",
                    casillas.get("03_resultado_empresarial", 0),
                ),
            ]
            seccion_label = "Apartado I — Actividades empresariales en módulos"
        elif apartado == "III":
            cuota_rows = [
                (
                    "04",
                    "Volumen ingresos agrario (trimestre)",
                    casillas.get("04_volumen_ingresos_agrario", 0),
                ),
                ("05", "Cuota agraria 2%", casillas.get("05_cuota_agraria", 0)),
            ]
            seccion_label = (
                "Apartado III — Actividades agrícolas / ganaderas / forestales / pesqueras"
            )
        else:  # II
            cuota_rows = [
                (
                    "01",
                    "Volumen ingresos del trimestre",
                    casillas.get("01_rendimiento_neto_modulos", 0),
                ),
                ("02", "Tipo aplicable (%)", casillas.get("02_tipo_aplicable", 0)),
                ("03", "Resultado", casillas.get("03_resultado_empresarial", 0)),
            ]
            seccion_label = "Apartado II — Actividad empresarial sin datos-base"

        cuota_rows.append(
            (
                "06",
                "Total cuotas",
                casillas.get("06_total_cuotas", 0),
            )
        )
        self._render_casillas_table(story, cuota_rows, seccion_label)

        # Reducciones territoriales (Ceuta/Melilla, La Palma)
        reducciones = casillas.get("07_reducciones", 0)
        if reducciones > 0:
            concepto = desglose.get("reduccion_concepto", "Reducción territorial")
            self._simple_section_table(
                story,
                "Reducciones territoriales",
                [
                    (concepto, _format_eur(reducciones)),
                    (
                        "Resultado tras reducciones",
                        _format_eur(casillas.get("08_resultado_tras_reducciones", 0)),
                    ),
                ],
            )

        # Minoraciones (retenciones, pagos previos, complementaria)
        minoracion_rows: List[Tuple[str, str]] = []
        if casillas.get("09_retenciones_trimestre", 0) > 0:
            minoracion_rows.append(
                (
                    "Retenciones del trimestre [09]",
                    _format_eur(casillas["09_retenciones_trimestre"]),
                )
            )
        if casillas.get("10_pagos_anteriores", 0) > 0:
            minoracion_rows.append(
                (
                    "Pagos fraccionados anteriores [10]",
                    _format_eur(casillas["10_pagos_anteriores"]),
                )
            )
        if casillas.get("11_complementaria", 0) > 0:
            minoracion_rows.append(
                (
                    "Resultado autoliquidación anterior [11]",
                    _format_eur(casillas["11_complementaria"]),
                )
            )
        if apartado == "I":
            minoracion_brl = desglose.get("minoracion_rendimientos_bajos", 0)
            if minoracion_brl > 0:
                minoracion_rows.append(
                    (
                        "Minoración rendimientos bajos",
                        _format_eur(minoracion_brl),
                    )
                )
        if minoracion_rows:
            self._simple_section_table(
                story,
                "Retenciones y minoraciones",
                minoracion_rows,
            )

        # Resultado final
        resultado_final = casillas.get("12_resultado_final", data.get("resultado_final", 0))
        self._render_resultado(story, "Resultado a ingresar [12]", resultado_final)

    # ------------------------------------------------------------------ #
    # Modelo 308 — RE (Recargo de Equivalencia)
    # ------------------------------------------------------------------ #

    def _render_308(self, story: list, data: dict):
        """Render Modelo 308 layout: RE farmacia sections."""
        # Adquisiciones intracomunitarias
        intra = data.get("adquisiciones_intracomunitarias", {})
        desglose_intra = intra.get("desglose", {})

        if intra.get("base_total", 0) > 0:
            intra_rows: List[Tuple[str, str, float]] = []
            for rate_key, label in [("21", "21%"), ("10", "10%"), ("4", "4%")]:
                base = desglose_intra.get(f"base_{rate_key}", 0)
                iva = desglose_intra.get(f"iva_{rate_key}", 0)
                re = desglose_intra.get(f"re_{rate_key}", 0)
                if base > 0:
                    intra_rows.append(("", f"Base {label}", base))
                    intra_rows.append(("", f"IVA {label}", iva))
                    intra_rows.append(("", f"RE {label}", re))

            intra_rows.append(("", "Total IVA intracomunitarias", intra.get("cuota_iva", 0)))
            intra_rows.append(("", "Total RE intracomunitarias", intra.get("cuota_re", 0)))
            self._render_casillas_table(story, intra_rows, "Adquisiciones intracomunitarias")

        # Inversión sujeto pasivo
        isp = data.get("inversion_sujeto_pasivo", {})
        if isp.get("base_total", 0) > 0:
            isp_desglose = isp.get("desglose", {})
            isp_rows: List[Tuple[str, str, float]] = []
            for rate_key, label in [("21", "21%"), ("10", "10%"), ("4", "4%")]:
                base = isp_desglose.get(f"base_{rate_key}", 0)
                if base > 0:
                    isp_rows.append(("", f"Base ISP {label}", base))
                    isp_rows.append(
                        ("", f"IVA ISP {label}", isp_desglose.get(f"iva_{rate_key}", 0))
                    )
                    isp_rows.append(("", f"RE ISP {label}", isp_desglose.get(f"re_{rate_key}", 0)))
            self._render_casillas_table(story, isp_rows, "Inversión sujeto pasivo")

        # Exportaciones y transportes
        exports = data.get("exportaciones", {})
        if exports.get("base_exportaciones", 0) > 0 or exports.get("base_transporte", 0) > 0:
            exp_rows: List[Tuple[str, str, float]] = []
            if exports.get("base_exportaciones", 0) > 0:
                exp_rows.append(("", "Base exportaciones", exports["base_exportaciones"]))
                exp_rows.append(("", "RE soportado exportaciones", exports.get("re_soportado", 0)))
            if exports.get("base_transporte", 0) > 0:
                exp_rows.append(("", "Base transporte nuevo", exports["base_transporte"]))
                exp_rows.append(
                    ("", "IVA soportado transporte", exports.get("iva_soportado_transporte", 0))
                )
            self._render_casillas_table(story, exp_rows, "Exportaciones y transportes")

        # Resultado
        resultado = data.get("resultado", {})
        resultado_final = resultado.get("resultado_final", data.get("resultado_final", 0))
        self._render_resultado(story, "Resultado liquidación", resultado_final)

    # ------------------------------------------------------------------ #
    # Modelo 720 — Bienes extranjero
    # ------------------------------------------------------------------ #

    def _render_720(self, story: list, data: dict):
        """Render Modelo 720 layout: Foreign assets by category."""
        from reportlab.platypus import Paragraph

        detalles = data.get("detalles", [])
        ejercicio = data.get("ejercicio", "")

        if detalles:
            rows_data: List[Tuple[str, str]] = []
            for det in detalles:
                cat_desc = det.get("descripcion", det.get("categoria", ""))
                valor = det.get("valor_actual", 0)
                obligado = det.get("obligado", False)
                estado = "OBLIGADO" if obligado else "No obligado"
                rows_data.append((cat_desc, f"{_format_eur(valor)} ({estado})"))

            self._simple_section_table(
                story,
                f"Categorías de bienes en el extranjero — Ejercicio {ejercicio}",
                rows_data,
            )

        # Obligation summary
        obligado = data.get("obligado_720", False)
        label = (
            "OBLIGADO a presentar Modelo 720" if obligado else "No obligado a presentar Modelo 720"
        )
        story.append(Paragraph(f"<b>{label}</b>", self._body_style))

        plazo = data.get("plazo", "")
        if plazo:
            story.append(Paragraph(f"Plazo: {plazo}", self._body_style))

        # Recommendations
        recomendaciones = data.get("recomendaciones", [])
        if recomendaciones:
            story.append(Paragraph("Recomendaciones", self._heading_style))
            for rec in recomendaciones:
                story.append(Paragraph(f"- {rec}", self._body_style))

    # ------------------------------------------------------------------ #
    # Modelo 721 — Criptomonedas extranjero
    # ------------------------------------------------------------------ #

    def _render_721(self, story: list, data: dict):
        """Render Modelo 721 layout: Crypto foreign assets."""
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.units import mm

        ejercicio = data.get("ejercicio", "")
        valor = data.get("valor_crypto_extranjero", 0)
        obligado = data.get("obligado_721", False)

        summary_rows: List[Tuple[str, str]] = [
            ("Valor criptomonedas en el extranjero", _format_eur(valor)),
        ]

        incremento = data.get("incremento_vs_ultimo_721")
        if incremento is not None:
            summary_rows.append(("Incremento vs. último 721", _format_eur(incremento)))

        exchanges = data.get("exchanges_afectados", [])
        if exchanges:
            summary_rows.append(("Exchanges afectados", ", ".join(exchanges)))

        excluidos = data.get("exchanges_espanoles_excluidos", [])
        if excluidos:
            summary_rows.append(("Exchanges españoles (excluidos)", ", ".join(excluidos)))

        self._simple_section_table(
            story,
            f"Monedas virtuales en el extranjero — Ejercicio {ejercicio}",
            summary_rows,
        )

        label = (
            "OBLIGADO a presentar Modelo 721" if obligado else "No obligado a presentar Modelo 721"
        )
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(f"<b>{label}</b>", self._body_style))

        plazo = data.get("plazo", "")
        if plazo:
            story.append(Paragraph(f"Plazo: {plazo}", self._body_style))

        recomendaciones = data.get("recomendaciones", [])
        if recomendaciones:
            story.append(Paragraph("Recomendaciones", self._heading_style))
            for rec in recomendaciones:
                story.append(Paragraph(f"- {rec}", self._body_style))

    # ------------------------------------------------------------------ #
    # IPSI — Ceuta/Melilla
    # ------------------------------------------------------------------ #

    def _render_ipsi(self, story: list, data: dict):
        """Render IPSI layout: rates table for Ceuta/Melilla."""
        desglose = data.get("desglose_devengado", {})

        # IPSI Devengado
        devengado_rows: List[Tuple[str, str, float]] = []
        rate_map = [
            ("tipo_minimo_0_5", "Tipo 0,5%"),
            ("tipo_inferior_1", "Tipo 1%"),
            ("tipo_ordinario_2", "Tipo 2%"),
            ("tipo_general_4", "Tipo general 4%"),
            ("tipo_incrementado_8", "Tipo incrementado 8%"),
            ("tipo_especial_10", "Tipo especial 10%"),
        ]

        for key, label in rate_map:
            rate_data = desglose.get(key, {})
            base = rate_data.get("base", 0) if isinstance(rate_data, dict) else 0
            cuota = rate_data.get("cuota", 0) if isinstance(rate_data, dict) else 0
            if base > 0:
                devengado_rows.append(("", f"{label} — Base", base))
                devengado_rows.append(("", f"{label} — Cuota", cuota))

        total_dev = data.get("total_devengado", 0)
        devengado_rows.append(("", "Total IPSI devengado", total_dev))
        self._render_casillas_table(story, devengado_rows, "IPSI Devengado (repercutido)")

        # IPSI Deducible
        deducible = data.get("desglose_deducible", {})
        ded_rows: List[Tuple[str, str, float]] = []
        for key, label in [
            ("cuota_corrientes_interiores", "Bienes y servicios corrientes"),
            ("cuota_inversion_interiores", "Bienes de inversión"),
            ("cuota_importaciones_corrientes", "Importaciones"),
        ]:
            val = deducible.get(key, 0) if isinstance(deducible, dict) else 0
            if val > 0:
                ded_rows.append(("", label, val))

        total_ded = data.get("total_deducible", 0)
        ded_rows.append(("", "Total a deducir", total_ded))
        self._render_casillas_table(story, ded_rows, "IPSI Deducible (soportado)")

        # Resultado
        resultado = data.get("resultado_liquidacion", 0)
        self._render_resultado(story, "Resultado liquidación IPSI", resultado)

    # ------------------------------------------------------------------ #
    # Modelo 200 — Impuesto sobre Sociedades
    # ------------------------------------------------------------------ #

    def _render_200(self, story: list, data: dict):
        """Render Modelo 200 layout: IS liquidación completa."""

        # Base imponible section
        bi_rows: List[Tuple[str, str, float]] = [
            ("552", "Base imponible", data.get("base_imponible", 0)),
        ]

        # Add detail rows if available
        resultado_contable = data.get("resultado_contable", 0)
        ajustes_positivos = data.get("ajustes_positivos", 0)
        ajustes_negativos = data.get("ajustes_negativos", 0)
        reserva_cap = data.get("reserva_capitalizacion", 0)
        compensacion_bins = data.get("compensacion_bins", 0)

        detail_rows: List[Tuple[str, str, float]] = []
        if resultado_contable:
            detail_rows.append(("500", "Resultado contable", resultado_contable))
        if ajustes_positivos:
            detail_rows.append(("517", "Ajustes positivos", ajustes_positivos))
        if ajustes_negativos:
            detail_rows.append(("518", "Ajustes negativos", -ajustes_negativos))
        if reserva_cap:
            detail_rows.append(("547", "Reserva de capitalización", -reserva_cap))
        if compensacion_bins:
            detail_rows.append(("550", "Compensación BINs", -compensacion_bins))

        if detail_rows:
            self._render_casillas_table(story, detail_rows, "Determinación de la base imponible")

        # Cuota section
        tipo_gravamen = data.get("tipo_gravamen_aplicado", "25%")
        cuota_integra = data.get("cuota_integra", 0)
        deducciones_total = data.get("deducciones_total", 0)
        bonificaciones_total = data.get("bonificaciones_total", 0)
        cuota_liquida = data.get("cuota_liquida", 0)
        retenciones = data.get("retenciones", 0)
        resultado_liquidacion = data.get("resultado_liquidacion", 0)

        cuota_rows: List[Tuple[str, str, float]] = [
            ("552", "Base imponible", data.get("base_imponible", 0)),
            ("558", f"Tipo gravamen ({tipo_gravamen})", cuota_integra),
            ("560", "Cuota íntegra", cuota_integra),
        ]

        if deducciones_total:
            cuota_rows.append(("582", "Deducciones", -deducciones_total))
        if bonificaciones_total:
            cuota_rows.append(("584", "Bonificaciones", -bonificaciones_total))

        cuota_rows.append(("592", "Cuota líquida", cuota_liquida))

        if retenciones:
            cuota_rows.append(("595", "Retenciones e ingresos a cuenta", -retenciones))

        pagos_fraccionados = data.get("pagos_fraccionados", 0)
        if pagos_fraccionados:
            cuota_rows.append(("596", "Pagos fraccionados (Modelo 202)", -pagos_fraccionados))

        cuota_rows.append(("599", "Resultado de la liquidación", resultado_liquidacion))

        self._render_casillas_table(story, cuota_rows, "Liquidación")

        # Resultado highlight
        tipo = data.get("tipo", "a_ingresar")
        if tipo == "a_devolver":
            self._render_resultado(story, "A devolver (casilla 601)", abs(resultado_liquidacion))
        else:
            self._render_resultado(story, "A ingresar (casilla 600)", resultado_liquidacion)

        # Tipo efectivo
        tipo_efectivo = data.get("tipo_efectivo", 0)
        regimen = data.get("regimen", "")
        if tipo_efectivo or regimen:
            from reportlab.platypus import Paragraph, Spacer
            from reportlab.lib.units import mm

            info_parts = []
            if regimen:
                info_parts.append(f"Régimen: {regimen}")
            if tipo_efectivo:
                info_parts.append(f"Tipo efectivo: {tipo_efectivo}%")
            story.append(Spacer(1, 4 * mm))
            story.append(Paragraph(" | ".join(info_parts), self._body_style))

    # ------------------------------------------------------------------ #
    # Modelo 390 — Resumen Anual IVA
    # ------------------------------------------------------------------ #

    def _render_modelo_390(self, story: list, data: dict):
        """
        Render Modelo 390 layout: exoneracion (Art. 71.7 RIVA) o sumatorio
        anual de los 4 trimestres del 303.

        Acepta la salida de `calculate_modelo_390_tool` o de
        `Modelo390Calculator.calculate()`.
        """
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, Spacer
        from xml.sax.saxutils import escape

        territory_info = data.get("territory_info") or {}
        modelo = data.get("modelo")
        obligado = bool(data.get("obligado"))
        plazo = data.get("plazo", "1 al 30 de enero del año siguiente")
        hacienda = data.get("hacienda") or territory_info.get("hacienda", "AEAT")

        # Cabecera con plazo y hacienda
        cab_rows: List[Tuple[str, str]] = [
            ("Modelo aplicable", escape(str(modelo)) if modelo else "No aplica (IPSI)"),
            ("Plazo de presentacion", escape(str(plazo))),
            ("Hacienda", escape(str(hacienda))),
            ("Obligado a presentar", "Si" if obligado else "No"),
        ]
        if territory_info.get("nota"):
            cab_rows.append(("Nota territorial", escape(str(territory_info["nota"]))))
        self._simple_section_table(story, "Datos del resumen anual", cab_rows)
        story.append(Spacer(1, 4 * mm))

        # Exoneracion: mostrar motivo y salir
        if not obligado:
            story.append(Paragraph("Estado de la obligacion", self._heading_style))
            motivo = (
                data.get("motivo_exoneracion")
                or territory_info.get("nota")
                or ("No tienes obligacion de presentar este modelo.")
            )
            story.append(
                Paragraph(
                    f"<b>EXONERADO.</b> {escape(str(motivo))}",
                    self._body_style,
                )
            )

            chequeos = data.get("exoneraciones_aplicables") or []
            if chequeos:
                story.append(Spacer(1, 3 * mm))
                story.append(Paragraph("Causas:", self._body_style))
                for chk in chequeos:
                    chk_label = escape(str(chk.get("chequeo", "")))
                    chk_motivo = escape(str(chk.get("motivo", "")))
                    story.append(Paragraph(f"- <b>{chk_label}</b>: {chk_motivo}", self._body_style))
            return

        # Obligado: mostrar sumatorio anual si llega
        resumen = data.get("resumen_anual") or {}
        if not resumen:
            story.append(
                Paragraph(
                    "Estas obligado a presentar este modelo. Para ver el sumatorio "
                    "anual con casillas, completa los 4 trimestres del Modelo 303.",
                    self._body_style,
                )
            )
            return

        # IVA Devengado anual
        devengado_rows: List[Tuple[str, str, float]] = []
        if resumen.get("cuota_devengada_4"):
            devengado_rows.append(("", "Cuota IVA 4% anual", resumen["cuota_devengada_4"]))
        if resumen.get("cuota_devengada_10"):
            devengado_rows.append(("", "Cuota IVA 10% anual", resumen["cuota_devengada_10"]))
        if resumen.get("cuota_devengada_21"):
            devengado_rows.append(("", "Cuota IVA 21% anual", resumen["cuota_devengada_21"]))
        if resumen.get("cuota_devengada_intra"):
            devengado_rows.append(
                ("", "Adquisiciones intracomunitarias", resumen["cuota_devengada_intra"])
            )
        if resumen.get("cuota_devengada_isp"):
            devengado_rows.append(("", "Inversion sujeto pasivo", resumen["cuota_devengada_isp"]))
        devengado_rows.append(
            ("", "Total IVA devengado anual", resumen.get("total_devengado_anual", 0))
        )
        self._render_casillas_table(story, devengado_rows, "IVA Devengado anual (sumatorio 303)")

        # IVA Deducible anual
        deducible_rows: List[Tuple[str, str, float]] = []
        if resumen.get("cuota_deducible_corrientes"):
            deducible_rows.append(
                ("", "Bienes y servicios corrientes", resumen["cuota_deducible_corrientes"])
            )
        if resumen.get("cuota_deducible_inversion"):
            deducible_rows.append(("", "Bienes de inversion", resumen["cuota_deducible_inversion"]))
        if resumen.get("cuota_deducible_importaciones"):
            deducible_rows.append(("", "Importaciones", resumen["cuota_deducible_importaciones"]))
        if resumen.get("cuota_deducible_intra"):
            deducible_rows.append(
                ("", "Adquisiciones intracomunitarias", resumen["cuota_deducible_intra"])
            )
        deducible_rows.append(
            ("", "Total IVA deducible anual", resumen.get("total_deducible_anual", 0))
        )
        self._render_casillas_table(story, deducible_rows, "IVA Deducible anual (sumatorio 303)")

        # Resultado liquidacion anual
        resultado_anual = resumen.get("resultado_liquidacion_anual", 0)
        self._render_resultado(story, "Resultado liquidacion anual", resultado_anual)

    # ------------------------------------------------------------------ #
    # Modelo 349 — Declaracion recapitulativa intracomunitaria
    # ------------------------------------------------------------------ #

    def _render_modelo_349(self, story: list, data: dict):
        """Render Modelo 349 layout: periodicidad + resumen por clave + cuadre 303."""
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, Spacer

        # Periodicidad y plazo
        periodicidad = data.get("periodicidad", "trimestral")
        periodo = data.get("periodo", "")
        plazo = data.get("plazo", "")
        motivo = data.get("periodicidad_motivo", "")
        ccaa = data.get("ccaa") or "Territorio comun"

        meta_rows: List[Tuple[str, str]] = [
            ("Periodicidad", str(periodicidad).capitalize()),
            ("Periodo declarado", str(periodo)),
            ("Plazo de presentacion", str(plazo)),
            ("Territorio del declarante", str(ccaa)),
        ]
        if motivo:
            meta_rows.append(("Motivo de la periodicidad", str(motivo)))
        self._simple_section_table(story, "Datos de la declaracion", meta_rows)

        # Totales agregados
        totales = data.get("totales", {})
        if totales:
            tot_rows: List[Tuple[str, str, float]] = [
                (
                    "E+T+M+H",
                    "Entregas intracomunitarias de bienes",
                    float(totales.get("entregas_bienes", 0)),
                ),
                (
                    "A",
                    "Adquisiciones intracomunitarias de bienes",
                    float(totales.get("adquisiciones_bienes", 0)),
                ),
                (
                    "S",
                    "Prestaciones intracomunitarias de servicios",
                    float(totales.get("servicios_prestados", 0)),
                ),
                (
                    "I",
                    "Adquisiciones intracomunitarias de servicios",
                    float(totales.get("servicios_adquiridos", 0)),
                ),
                (
                    "R+D+C",
                    "Operaciones de consignacion (call-off stock)",
                    float(totales.get("consignacion", 0)),
                ),
                (
                    "N",
                    "Rectificaciones de periodos anteriores",
                    float(totales.get("rectificaciones", 0)),
                ),
                (
                    "",
                    "Volumen relevante (umbral 50.000 EUR)",
                    float(totales.get("volumen_relevante", 0)),
                ),
                ("", "Total general (todas las claves)", float(totales.get("total_general", 0))),
            ]
            self._render_casillas_table(story, tot_rows, "Totales agregados por clave")

        # Detalle por clave (n_operaciones / n_operadores)
        resumen = data.get("resumen") or {}
        por_clave = resumen.get("por_clave") or {}
        if por_clave:
            from xml.sax.saxutils import escape as _esc

            labels = {
                "E": "Entregas bienes (Art. 25 LIVA)",
                "A": "Adquisiciones bienes",
                "T": "Triangular",
                "S": "Servicios prestados (Art. 69.uno.1 LIVA)",
                "I": "Servicios adquiridos",
                "M": "Tras importacion",
                "H": "Representante en M",
                "R": "Transferencia consignacion",
                "D": "Devolucion consignacion",
                "C": "Sustitucion consignacion",
                "N": "Rectificacion",
            }
            detalle_rows: List[Tuple[str, str]] = []
            for clave, info in por_clave.items():
                if info.get("n_operaciones", 0) <= 0:
                    continue
                detalle_rows.append(
                    (
                        f"[{clave}] {_esc(labels.get(clave, clave))}",
                        f"{info.get('importe', 0):,.2f} EUR — {info.get('n_operaciones', 0)} ops "
                        f"/ {info.get('n_operadores', 0)} operadores",
                    )
                )
            if detalle_rows:
                self._simple_section_table(story, "Detalle por clave de operacion", detalle_rows)

        # Avisos NIF / VIES
        formato_inv = data.get("formato_invalidos") or []
        vies_warnings = data.get("vies_warnings") or []
        if formato_inv or vies_warnings:
            story.append(Spacer(1, 4 * mm))
            story.append(Paragraph("Avisos sobre operadores", self._heading_style))
            for v in formato_inv:
                story.append(
                    Paragraph(
                        f"- NIF-IVA con formato invalido: {v.get('nif_iva')} "
                        f"({v.get('country') or 's/p'}): {v.get('motivo') or ''}",
                        self._body_style,
                    )
                )
            for w in vies_warnings:
                story.append(Paragraph(f"- {w}", self._body_style))

        # Cuadre 303
        cuadre = data.get("cuadre_303")
        if cuadre:
            story.append(Spacer(1, 4 * mm))
            story.append(Paragraph("Cuadre 303 <-> 349", self._heading_style))
            if cuadre.get("cuadre_ok"):
                story.append(
                    Paragraph(
                        "Cuadre OK (diferencias dentro de tolerancia 0,5 EUR).",
                        self._body_style,
                    )
                )
            else:
                for w in cuadre.get("warnings", []) or []:
                    story.append(Paragraph(f"- {w}", self._body_style))

        # Resultado highlight (en 349 no hay cuota, mostramos volumen relevante)
        volumen = float((totales or {}).get("volumen_relevante", 0))
        self._render_resultado(story, "Volumen intracomunitario declarado", volumen)

    # ------------------------------------------------------------------ #
    # Placeholder stub — Modelos en desarrollo (100, 131, 309, 420)
    # ------------------------------------------------------------------ #

    def _render_placeholder(
        self,
        story: list,
        modelo_type: str,
        data: dict,
        user_info: dict,
        trimestre: str,
        ejercicio: int,
    ):
        """
        Render a minimal placeholder PDF for modelos in development.

        Includes header (already rendered upstream), basic user data,
        period info, and a clear "in development" notice with AEAT pointer.
        """
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, Spacer
        from xml.sax.saxutils import escape

        modelo_label = MODELO_NAMES.get(modelo_type, f"Modelo {modelo_type}")

        # Aviso destacado de borrador en desarrollo
        story.append(Paragraph("Estado del documento", self._heading_style))
        notice = (
            f"<b>Modelo {escape(modelo_type.upper())} — Borrador en desarrollo.</b> "
            "Esta funcionalidad estará disponible próximamente. "
            "Para presentación oficial, acude a Sede Electrónica AEAT "
            "(<a href='https://sede.agenciatributaria.gob.es'>sede.agenciatributaria.gob.es</a>)."
        )
        story.append(Paragraph(notice, self._body_style))
        story.append(Spacer(1, 6 * mm))

        # Datos básicos del usuario y periodo (recapitulación visible)
        nif = escape((user_info or {}).get("nif", "") or "—")
        nombre = escape((user_info or {}).get("nombre", "") or "—")

        rows_data: List[Tuple[str, str]] = [
            ("Modelo", f"{escape(modelo_type.upper())} — {escape(modelo_label)}"),
            ("Nombre / Razón social", nombre),
            ("NIF / CIF", nif),
            ("Ejercicio", str(ejercicio)),
            ("Periodo", escape(str(trimestre))),
        ]

        # Si llegan datos extra del caller (por ejemplo CCAA/ regimen), reflejarlos
        if isinstance(data, dict):
            for key in ("ccaa", "regimen", "actividad", "epigrafe_iae"):
                val = data.get(key)
                if val:
                    rows_data.append((key.replace("_", " ").capitalize(), escape(str(val))))

        self._simple_section_table(story, "Datos básicos", rows_data)

        # Nota técnica para el usuario
        story.append(Spacer(1, 6 * mm))
        story.append(
            Paragraph(
                "Este documento es un borrador placeholder generado por Impuestify mientras "
                "se finaliza la implementación específica de este modelo. La estructura final "
                "de casillas, casos especiales y validaciones será incorporada en próximas "
                "versiones.",
                self._small_style,
            )
        )
