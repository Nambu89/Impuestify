"""
Modelo PDF Generator for TaxIA.

Generates informational PDFs with calculated casilla data for
Spanish tax form models (Modelos Tributarios): 303, 130, 308, 720, 721, IPSI.
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
    "308": "IVA — Régimen Especial (Recargo de Equivalencia)",
    "720": "Declaración de Bienes y Derechos en el Extranjero",
    "721": "Declaración de Monedas Virtuales en el Extranjero",
    "ipsi": "IPSI — Impuesto sobre la Producción, los Servicios y la Importación",
}

# Foral variant names
FORAL_NAMES: Dict[str, str] = {
    "300": "Modelo 300 — Autoliquidación IVA (Gipuzkoa)",
    "F69": "Modelo F69 — Autoliquidación IVA (Navarra)",
    "420": "Modelo 420 — Autoliquidación IGIC (Canarias)",
}

VALID_MODELOS = {"303", "130", "308", "720", "721", "ipsi"}


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
        render_method = {
            "303": self._render_303,
            "130": self._render_130,
            "308": self._render_308,
            "720": self._render_720,
            "721": self._render_721,
            "ipsi": self._render_ipsi,
        }[modelo_type]

        render_method(story, data)

        # Disclaimer
        story.append(Spacer(1, 8 * mm))
        self._render_disclaimer(story)

        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        logger.info(
            "Modelo %s PDF generated: %d bytes, trimestre=%s, ejercicio=%d",
            modelo_type, len(pdf_bytes), trimestre, ejercicio,
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
        variante_foral = (user_info or {}).get("variante_foral") or \
                         ({} if not isinstance(user_info, dict) else user_info).get("variante_foral")

        if variante_foral and variante_foral in FORAL_NAMES:
            title_text = FORAL_NAMES[variante_foral]
        else:
            modelo_name = MODELO_NAMES.get(modelo_type, modelo_type)
            title_text = f"Modelo {modelo_type.upper()} — {modelo_name}"

        story.append(Paragraph("Impuestify", self._title_style))
        story.append(Paragraph(title_text, self._subtitle_style))
        story.append(Paragraph(
            f"Periodo: {trimestre} — Ejercicio {ejercicio}",
            self._subtitle_style,
        ))
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
        t.setStyle(TableStyle([
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
        ]))
        story.append(t)

    def _render_resultado(self, story: list, label: str, amount: float):
        """Render a highlighted result box. Green if refund, red if pay."""
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import (
            Paragraph, Spacer, Table, TableStyle,
        )

        is_refund = amount <= 0
        bg_color = HexColor("#ecfdf5") if is_refund else HexColor("#fef2f2")
        text_style = self._result_refund_style if is_refund else self._result_pay_style

        text = f"<b>{label}: {_format_eur(amount)}</b>"
        cell = Paragraph(text, text_style)

        t = Table([[cell]], colWidths=[160 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg_color),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOX", (0, 0), (-1, -1), 1, self._green if is_refund else self._red),
        ]))
        story.append(Spacer(1, 4 * mm))
        story.append(t)

    def _render_disclaimer(self, story: list):
        """Render legal disclaimer at the bottom."""
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, Spacer, HRFlowable

        story.append(HRFlowable(width="100%", thickness=0.5, color=self._gray))
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(
            "AVISO LEGAL: Este documento ha sido generado automáticamente por Impuestify y tiene "
            "carácter meramente orientativo e informativo. No constituye una declaración tributaria "
            "oficial ni sustituye la presentación del modelo ante la AEAT o hacienda foral correspondiente. "
            "Los cálculos se basan en la información proporcionada por el usuario y en la normativa fiscal "
            "vigente. Impuestify no se responsabiliza de errores u omisiones en los datos proporcionados "
            "ni de las decisiones tomadas en base a este documento.",
            self._small_style,
        ))
        story.append(Spacer(1, 3 * mm))
        now = datetime.now(timezone.utc)
        story.append(Paragraph(
            f"Generado el {now.strftime('%d/%m/%Y a las %H:%M')} UTC por Impuestify (impuestify.com)",
            self._footer_style,
        ))

    def _header_table_style(self):
        """Standard header table style matching report_generator.py."""
        from reportlab.lib.units import mm
        from reportlab.platypus import TableStyle

        return TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), self._primary),
            ("TEXTCOLOR", (0, 0), (-1, 0), self._white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 1), (-1, -1), self._light_bg),
            ("GRID", (0, 0), (-1, -1), 0.5, self._gray),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ])

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
        t.setStyle(TableStyle([
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
        ]))
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
        """Render Modelo 130 layout: Sections I-IV."""
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

        self._render_casillas_table(
            story, s1_rows, "Sección I: Actividades en estimación directa"
        )

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
                    isp_rows.append(("", f"IVA ISP {label}", isp_desglose.get(f"iva_{rate_key}", 0)))
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
                exp_rows.append(("", "IVA soportado transporte", exports.get("iva_soportado_transporte", 0)))
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
        label = "OBLIGADO a presentar Modelo 720" if obligado else "No obligado a presentar Modelo 720"
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

        label = "OBLIGADO a presentar Modelo 721" if obligado else "No obligado a presentar Modelo 721"
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
