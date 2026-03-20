"""
Report Generator for TaxIA.

Generates PDF reports using ReportLab with IRPF simulation results,
deductions, and fiscal profile data.
"""
import io
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _parse_markdown_to_reportlab(markdown_text: str) -> List[str]:
    """
    Convert basic markdown to ReportLab-compatible paragraphs.

    Handles:
    - **bold** → <b>bold</b>
    - ### headers → <b>header text</b>
    - - bullet items → bullet character prefix
    - Blank lines → paragraph breaks
    """
    import re

    lines = markdown_text.split("\n")
    paragraphs: List[str] = []
    current_paragraph: List[str] = []

    for line in lines:
        stripped = line.strip()

        # Skip empty lines (paragraph break)
        if not stripped:
            if current_paragraph:
                paragraphs.append(" ".join(current_paragraph))
                current_paragraph = []
            continue

        # Headers: ### Text → bold
        if stripped.startswith("#"):
            if current_paragraph:
                paragraphs.append(" ".join(current_paragraph))
                current_paragraph = []
            header_text = re.sub(r"^#+\s*", "", stripped)
            paragraphs.append(f"<b>{header_text}</b>")
            continue

        # Bullet lists: - item or * item
        if re.match(r"^[-*]\s+", stripped):
            if current_paragraph:
                paragraphs.append(" ".join(current_paragraph))
                current_paragraph = []
            bullet_text = re.sub(r"^[-*]\s+", "", stripped)
            # Convert **bold** inside bullets too
            bullet_text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", bullet_text)
            paragraphs.append(f"\u2022 {bullet_text}")
            continue

        # Regular text: convert **bold**
        processed = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", stripped)
        current_paragraph.append(processed)

    # Flush remaining paragraph
    if current_paragraph:
        paragraphs.append(" ".join(current_paragraph))

    return paragraphs


def generate_irpf_report(
    user_name: str,
    simulation_data: Optional[Dict[str, Any]] = None,
    deductions: Optional[List[Dict[str, Any]]] = None,
    fiscal_profile: Optional[Dict[str, Any]] = None,
    estimated_savings: float = 0.0,
    chat_content: Optional[str] = None,
) -> bytes:
    """
    Generate a PDF report with IRPF simulation and deductions.

    Args:
        user_name: Name of the taxpayer
        simulation_data: Results from simulate_irpf tool
        deductions: List of eligible deductions
        fiscal_profile: User's fiscal profile
        estimated_savings: Estimated savings from deductions
        chat_content: Optional markdown content from the assistant's analysis

    Returns:
        PDF file as bytes
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    # Colors
    primary = HexColor("#1a56db")
    dark = HexColor("#1f2937")
    gray = HexColor("#6b7280")
    light_bg = HexColor("#f3f4f6")
    white = HexColor("#ffffff")
    green = HexColor("#059669")

    # Styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=22,
        textColor=primary,
        spaceAfter=6 * mm,
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=dark,
        spaceBefore=8 * mm,
        spaceAfter=3 * mm,
    )
    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontSize=10,
        textColor=dark,
        leading=14,
    )
    small_style = ParagraphStyle(
        "CustomSmall",
        parent=styles["Normal"],
        fontSize=8,
        textColor=gray,
        leading=10,
    )
    amount_style = ParagraphStyle(
        "Amount",
        parent=styles["Normal"],
        fontSize=10,
        textColor=dark,
        alignment=TA_RIGHT,
    )
    green_amount_style = ParagraphStyle(
        "GreenAmount",
        parent=styles["Normal"],
        fontSize=11,
        textColor=green,
        alignment=TA_RIGHT,
        fontName="Helvetica-Bold",
    )

    elements = []

    # === HEADER ===
    elements.append(Paragraph("Impuestify", title_style))
    elements.append(Paragraph(
        f"Informe Fiscal IRPF — {datetime.now().strftime('%d/%m/%Y')}",
        ParagraphStyle("Subtitle", parent=body_style, fontSize=12, textColor=gray),
    ))
    elements.append(Spacer(1, 4 * mm))
    elements.append(HRFlowable(width="100%", thickness=1, color=primary))
    elements.append(Spacer(1, 6 * mm))

    # === TAXPAYER DATA ===
    elements.append(Paragraph("Datos del contribuyente", heading_style))

    taxpayer_data = [["Campo", "Valor"]]
    taxpayer_data.append(["Nombre", user_name])

    if fiscal_profile:
        fp_fields = {
            "ccaa_residencia": "CCAA de residencia",
            "situacion_laboral": "Situación laboral",
            "epigrafe_iae": "Epígrafe IAE",
            "tipo_actividad": "Tipo de actividad",
            "metodo_estimacion_irpf": "Método estimación IRPF",
            "regimen_iva": "Régimen IVA",
        }
        for key, label in fp_fields.items():
            val = fiscal_profile.get(key)
            if val:
                taxpayer_data.append([label, str(val)])

    if len(taxpayer_data) > 1:
        t = Table(taxpayer_data, colWidths=[60 * mm, 100 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), primary),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 1), (-1, -1), light_bg),
            ("GRID", (0, 0), (-1, -1), 0.5, gray),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)

    # === IRPF SIMULATION ===
    if simulation_data:
        elements.append(Paragraph("Simulación IRPF", heading_style))

        sim_rows = [["Concepto", "Importe"]]

        field_map = [
            ("ingresos_trabajo", "Ingresos brutos del trabajo"),
            ("ss_empleado", "Cotización SS empleado"),
            ("otros_gastos", "Otros gastos deducibles"),
            ("reduccion_trabajo", "Reducción rendimientos trabajo"),
            ("base_imponible_general", "Base imponible general"),
            ("base_imponible_ahorro", "Base imponible del ahorro"),
            ("cuota_integra_estatal", "Cuota íntegra estatal"),
            ("cuota_integra_autonomica", "Cuota íntegra autonómica"),
            ("cuota_integra_total", "Cuota íntegra total"),
            ("mpyf_total", "Mínimo personal y familiar"),
            ("reduccion_conjunta", "Reducción tributación conjunta"),
            ("deduccion_vivienda", "Deducción vivienda habitual"),
            ("deduccion_donativos", "Deducción por donativos"),
            ("deduccion_maternidad", "Deducción por maternidad"),
            ("deduccion_familia_numerosa", "Deducción familia numerosa"),
            ("deducciones_autonomicas_total", "Deducciones autonómicas"),
            ("cuota_liquida", "Cuota líquida"),
            ("retenciones_trabajo", "Retenciones del trabajo"),
            ("retenciones_actividad", "Retenciones actividad"),
            ("pagos_fraccionados_130", "Pagos fraccionados M130"),
            ("resultado_declaracion", "Resultado declaración"),
            ("tipo_efectivo", "Tipo efectivo"),
        ]

        for key, label in field_map:
            val = simulation_data.get(key)
            if val is not None:
                if key == "tipo_efectivo":
                    sim_rows.append([label, f"{val:.2f}%"])
                else:
                    sim_rows.append([label, f"{val:,.2f} EUR"])

        t = Table(sim_rows, colWidths=[100 * mm, 60 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), primary),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 1), (-1, -1), light_bg),
            ("GRID", (0, 0), (-1, -1), 0.5, gray),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ]))
        elements.append(t)

    # === DEDUCTIONS ===
    if deductions:
        elements.append(Paragraph("Deducciones aplicables", heading_style))

        ded_rows = [["Deducción", "Tipo", "Ahorro estimado"]]
        for d in deductions:
            name = d.get("name", "")
            dtype = d.get("type", "deduccion").capitalize()
            if d.get("fixed_amount"):
                amount = f"{d['fixed_amount']:,.0f} EUR"
            elif d.get("max_amount") and d.get("percentage"):
                amount = f"{d['percentage']}% (max {d['max_amount']:,.0f} EUR)"
            elif d.get("percentage"):
                amount = f"{d['percentage']}%"
            else:
                amount = "Variable"
            ded_rows.append([name, dtype, amount])

        t = Table(ded_rows, colWidths=[80 * mm, 30 * mm, 50 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), green),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 1), (-1, -1), light_bg),
            ("GRID", (0, 0), (-1, -1), 0.5, gray),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(t)

        if estimated_savings > 0:
            elements.append(Spacer(1, 3 * mm))
            elements.append(Paragraph(
                f"Ahorro estimado total por deducciones: {estimated_savings:,.0f} EUR",
                green_amount_style,
            ))

    # === PERSONALIZED ANALYSIS (from chat) ===
    if chat_content:
        elements.append(Paragraph("Análisis personalizado", heading_style))
        # Parse basic markdown: **bold** → <b>bold</b>, remove ### headers, bullet lists
        analysis_text = _parse_markdown_to_reportlab(chat_content)
        for paragraph_text in analysis_text:
            if paragraph_text.strip():
                elements.append(Paragraph(paragraph_text, body_style))
                elements.append(Spacer(1, 2 * mm))

    # === DISCLAIMER ===
    elements.append(Spacer(1, 10 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=gray))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(
        "AVISO LEGAL: Este informe ha sido generado automáticamente por Impuestify y tiene "
        "carácter meramente orientativo e informativo. No constituye asesoramiento fiscal "
        "profesional ni sustituye la consulta a un asesor fiscal cualificado. Los cálculos "
        "se basan en la información proporcionada por el usuario y en la normativa fiscal "
        "vigente en el momento de la generación. Impuestify no se responsabiliza de errores "
        "u omisiones en los datos proporcionados ni de las decisiones tomadas en base a este informe.",
        small_style,
    ))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph(
        f"Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')} por Impuestify (impuestify.com)",
        ParagraphStyle("Footer", parent=small_style, alignment=TA_CENTER),
    ))

    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    logger.info(f"PDF report generated: {len(pdf_bytes)} bytes")
    return pdf_bytes
