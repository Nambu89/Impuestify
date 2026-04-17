"""Generate synthetic anonymized PDF fixtures for DefensIA E2E tests (T3-001b).

Source of truth: backend/tests/defensia/fixtures/caso_david/expediente_anonimizado.json
Output: tests/e2e/fixtures/defensia/caso_david/*.pdf

These are NOT scans of real AEAT/TEAR documents. They are deterministic,
machine-generated PDFs that mimic the structure and key fields the DefensIA
extractors expect, using the already-anonymized figures from the JSON
ground truth. Any resemblance to a real taxpayer is excluded by design.

Run: python backend/scripts/generate_defensia_fixtures.py
"""
from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors

REPO_ROOT = Path(__file__).resolve().parents[2]
JSON_PATH = REPO_ROOT / "backend/tests/defensia/fixtures/caso_david/expediente_anonimizado.json"
OUT_DIR = REPO_ROOT / "tests/e2e/fixtures/defensia/caso_david"

NIF_FAKE = "00000000T"
NOMBRE_FAKE = "CONTRIBUYENTE ANONIMO"
DOMICILIO_FAKE = "C/ FICTICIA 1, 28000 MADRID"
REF_PROP = "REF-PROP-ANON"
REF_LIQ = "REF-LIQ-ANON"
REF_SANC = "REF-SANC-ANON"

styles = getSampleStyleSheet()
H1 = ParagraphStyle(
    "H1",
    parent=styles["Heading1"],
    fontSize=14,
    leading=18,
    spaceAfter=6,
)
H2 = ParagraphStyle(
    "H2",
    parent=styles["Heading2"],
    fontSize=11,
    leading=14,
    spaceBefore=8,
    spaceAfter=4,
)
BODY = ParagraphStyle(
    "Body",
    parent=styles["BodyText"],
    fontSize=9.5,
    leading=12,
    spaceAfter=4,
)


def _doc(path: Path) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=path.stem,
        author="DefensIA test fixture",
    )


def _kv_table(rows: list[tuple[str, str]]) -> Table:
    t = Table(rows, colWidths=[55 * mm, 115 * mm])
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
                ("INNERGRID", (0, 0), (-1, -1), 0.15, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return t


def generate_liquidacion(data: dict) -> Path:
    out = OUT_DIR / "liquidacion_anonimizada.pdf"
    doc = _doc(out)
    story: list = []

    story.append(Paragraph("AGENCIA ESTATAL DE ADMINISTRACION TRIBUTARIA", H1))
    story.append(Paragraph("Delegacion Especial de Madrid", BODY))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("LIQUIDACION PROVISIONAL DE IRPF - Ejercicio 2024", H1))
    story.append(
        Paragraph(
            "Procedimiento de comprobacion limitada (articulos 136 a 140 LGT).",
            BODY,
        )
    )
    story.append(Spacer(1, 3 * mm))

    story.append(
        _kv_table(
            [
                ("Referencia", REF_LIQ),
                ("Fecha del acto", "30 de enero de 2026"),
                ("Obligado tributario", NOMBRE_FAKE),
                ("NIF", NIF_FAKE),
                ("Domicilio", DOMICILIO_FAKE),
                ("Ejercicio", "2024"),
                ("Concepto", "IRPF - Ganancia patrimonial transmision inmueble"),
                ("Organo", "Dependencia de Gestion Tributaria - Administracion de Madrid"),
            ]
        )
    )
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("HECHOS", H2))
    story.append(
        Paragraph(
            "Del examen de la declaracion presentada se constata una "
            "ganancia patrimonial por importe de "
            f"{data['ganancia_patrimonial']:.2f} euros derivada de la "
            "transmision del inmueble declarada como vivienda habitual.",
            BODY,
        )
    )
    story.append(
        Paragraph(
            "Los gastos de adquisicion declarados por el contribuyente "
            f"ascienden a {data['gastos_adquisicion_declarados']:.2f} euros, "
            "de los cuales esta Administracion admite "
            f"{data['gastos_adquisicion_admitidos']:.2f} euros, rechazando "
            f"{data['diff_gastos_adquisicion_no_admitidos']:.2f} euros "
            "al no haberse acreditado suficientemente mediante justificante.",
            BODY,
        )
    )
    story.append(
        Paragraph(
            "Los gastos de transmision admitidos ascienden a "
            f"{data['gastos_transmision_admitidos']:.2f} euros.",
            BODY,
        )
    )

    story.append(Paragraph("FUNDAMENTOS DE DERECHO", H2))
    story.append(
        Paragraph(
            "Resultan de aplicacion, entre otros, los siguientes preceptos: "
            + ", ".join(data["motivacion_articulos_citados"])
            + ".",
            BODY,
        )
    )
    story.append(
        Paragraph(
            "De conformidad con el articulo 105.1 LGT, corresponde a quien "
            "haga valer su derecho la prueba de los hechos constitutivos del "
            "mismo, sin que el contribuyente haya aportado justificante "
            "suficiente de los gastos rechazados.",
            BODY,
        )
    )

    story.append(Paragraph("LIQUIDACION RESULTANTE", H2))
    story.append(
        _kv_table(
            [
                ("Cuota", f"{data['cuota']:.2f} EUR"),
                ("Intereses de demora", f"{data['intereses_demora']:.2f} EUR"),
                ("Total a ingresar", f"{data['total_a_ingresar']:.2f} EUR"),
            ]
        )
    )

    story.append(Paragraph("RECURSOS", H2))
    story.append(
        Paragraph(
            "Contra el presente acto podra interponerse recurso de reposicion "
            "ante el organo que lo dicto en el plazo de UN MES, o reclamacion "
            "economico-administrativa ante el Tribunal Economico-Administrativo "
            "Regional de Madrid en el plazo de UN MES, contados ambos a partir "
            "del dia siguiente al de la notificacion del presente acto "
            f"(plazo recurso: {data['plazo_recurso_dias']} dias).",
            BODY,
        )
    )

    doc.build(story)
    return out


def generate_sancion(data: dict) -> Path:
    out = OUT_DIR / "sancion_anonimizada.pdf"
    doc = _doc(out)
    story: list = []

    story.append(Paragraph("AGENCIA ESTATAL DE ADMINISTRACION TRIBUTARIA", H1))
    story.append(Paragraph("Delegacion Especial de Madrid", BODY))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("ACUERDO DE IMPOSICION DE SANCION", H1))
    story.append(
        Paragraph(
            "Procedimiento sancionador tributario (articulos 207 a 212 LGT).",
            BODY,
        )
    )
    story.append(Spacer(1, 3 * mm))

    story.append(
        _kv_table(
            [
                ("Referencia", REF_SANC),
                ("Fecha del acto", "7 de abril de 2026"),
                ("Obligado tributario", NOMBRE_FAKE),
                ("NIF", NIF_FAKE),
                ("Domicilio", DOMICILIO_FAKE),
                ("Ejercicio", "2024"),
                ("Acto origen", f"Liquidacion provisional {REF_LIQ}"),
            ]
        )
    )
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("HECHOS", H2))
    story.append(
        Paragraph(
            "Como consecuencia de la liquidacion provisional practicada, "
            "se aprecia que el obligado tributario dejo de ingresar parte "
            "de la deuda tributaria derivada de la ganancia patrimonial "
            "transmision inmueble, existiendo ademas una solicitud "
            "improcedente de devolucion.",
            BODY,
        )
    )

    story.append(Paragraph("FUNDAMENTOS DE DERECHO", H2))
    story.append(
        Paragraph(
            "Los hechos son constitutivos de las infracciones tipificadas en "
            + ", ".join(data["articulos_tipicos"])
            + ".",
            BODY,
        )
    )
    story.append(
        Paragraph(
            f"Infraccion del articulo 191 LGT calificada como {data['calificacion_191']}, "
            f"base de la sancion {data['base_sancion_191']:.2f} EUR, "
            f"porcentaje aplicable {data['porcentaje_191']:.0f}%.",
            BODY,
        )
    )
    story.append(
        Paragraph(
            f"Infraccion del articulo 194.1 LGT calificada como {data['calificacion_194']}, "
            f"base de la sancion {data['base_sancion_194']:.2f} EUR, "
            f"porcentaje aplicable {data['porcentaje_194']:.0f}%.",
            BODY,
        )
    )

    story.append(Paragraph("ACUERDO", H2))
    story.append(
        _kv_table(
            [
                ("Importe total sancion", f"{data['importe_sancion']:.2f} EUR"),
                ("Articulos aplicados", ", ".join(data["articulos_tipicos"])),
                ("Plazo de recurso", f"{data['plazo_recurso_dias']} dias"),
            ]
        )
    )

    story.append(Paragraph("RECURSOS", H2))
    story.append(
        Paragraph(
            "Contra el presente acuerdo podra interponerse recurso de "
            "reposicion o reclamacion economico-administrativa ante el TEAR "
            "de Madrid en el plazo de UN MES a contar desde el dia siguiente "
            "al de la notificacion.",
            BODY,
        )
    )

    doc.build(story)
    return out


def generate_sentencia_medidas() -> Path:
    out = OUT_DIR / "sentencia_medidas_anonimizada.pdf"
    doc = _doc(out)
    story: list = []

    story.append(Paragraph("JUZGADO DE PRIMERA INSTANCIA", H1))
    story.append(Paragraph("Procedimiento: Medidas provisionales previas", BODY))
    story.append(
        Paragraph("Autos numero 0000/2024 (datos anonimizados)", BODY)
    )
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("SENTENCIA", H1))
    story.append(Paragraph("En Madrid, a 28 de junio de 2024", BODY))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("ANTECEDENTES DE HECHO", H2))
    story.append(
        Paragraph(
            "Se interpuso demanda de medidas provisionales previas en "
            "relacion con la ruptura de la convivencia entre las partes "
            "(identidades anonimizadas). Tras la celebracion de la vista "
            "y con audiencia de ambas partes, se dictan las presentes "
            "medidas al amparo del articulo 103 del Codigo Civil.",
            BODY,
        )
    )

    story.append(Paragraph("FUNDAMENTOS DE DERECHO", H2))
    story.append(
        Paragraph(
            "Se aplica el articulo 103 del Codigo Civil y el articulo 771 "
            "de la Ley de Enjuiciamiento Civil. La atribucion del uso de "
            "la vivienda familiar se acuerda en favor del progenitor "
            "custodio, en atencion al interes superior de los menores.",
            BODY,
        )
    )

    story.append(Paragraph("FALLO", H2))
    story.append(
        Paragraph(
            "PRIMERO. Se acuerda la atribucion del uso y disfrute de la "
            "vivienda que constituyo el domicilio familiar al progenitor "
            "custodio y a los hijos menores.",
            BODY,
        )
    )
    story.append(
        Paragraph(
            "SEGUNDO. Se fijan medidas provisionales sobre guarda, custodia "
            "y pension de alimentos en favor de los menores, conforme a los "
            "terminos expuestos en los fundamentos de derecho.",
            BODY,
        )
    )
    story.append(
        Paragraph(
            "TERCERO. Notifiquese la presente resolucion a las partes "
            "personadas, haciendoles saber los recursos procedentes.",
            BODY,
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            "Documento anonimizado generado automaticamente para pruebas "
            "E2E del sistema DefensIA. NO constituye resolucion judicial real.",
            BODY,
        )
    )

    doc.build(story)
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    docs_by_tipo = {d["tipo_documento"]: d for d in payload["documentos"]}

    liq_data = docs_by_tipo["LIQUIDACION_PROVISIONAL"]["datos"]
    sanc_data = docs_by_tipo["ACUERDO_IMPOSICION_SANCION"]["datos"]

    generated = [
        generate_liquidacion(liq_data),
        generate_sancion(sanc_data),
        generate_sentencia_medidas(),
    ]
    for p in generated:
        size = p.stat().st_size
        print(f"  wrote {p.relative_to(REPO_ROOT)}  ({size} bytes)")


if __name__ == "__main__":
    main()
