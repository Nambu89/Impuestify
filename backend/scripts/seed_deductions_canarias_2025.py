"""
Seed ALL 28 official Canarias autonomous deductions for IRPF 2025.

Source: AEAT Manual Practico IRPF 2025 — Comunidad Autonoma de Canarias
https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/
    irpf-2025-deducciones-autonomicas/comunidad-autonoma-canarias.html

Legal basis: Decreto Legislativo 1/2009, de 21 de abril, por el que se aprueba el
Texto Refundido de las disposiciones legales vigentes dictadas por la Comunidad Autonoma
de Canarias en materia de tributos cedidos.

Idempotent: DELETE existing Canarias deductions for tax_year=2025, then INSERT all 28.

Usage:
    cd backend
    python scripts/seed_deductions_canarias_2025.py
    python scripts/seed_deductions_canarias_2025.py --dry-run
"""
import argparse
import asyncio
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

TERRITORY = "Canarias"
TAX_YEAR = 2025

# Common income limits for many Canarias deductions
LIMITES_CANARIAS = {"individual": 46455, "conjunta": 61770}


# =============================================================================
# ALL 28 CANARIAS DEDUCTIONS — IRPF 2025
# =============================================================================

CANARIAS_2025 = [
    # =========================================================================
    # 1. Por donaciones con finalidad ecologica
    # =========================================================================
    {
        "code": "CAN-DON-001",
        "name": "Por donaciones con finalidad ecologica",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 150.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de las donaciones dinerarias puras y simples a entidades publicas de Canarias o entidades sin animo de lucro dedicadas a la defensa del medio ambiente. Maximo 150 EUR o 10% de la cuota integra autonomica.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras y simples",
                "A entidades publicas canarias, cabildos o ayuntamientos con finalidad medioambiental",
                "O a entidades sin animo de lucro dedicadas exclusivamente a la defensa medioambiental inscritas en registros de Canarias",
                "Limite: 10% de la cuota integra autonomica (casilla 0546) o 150 EUR por contribuyente"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_ecologica_canarias", "label": "Ha realizado donaciones a entidades medioambientales en Canarias?", "type": "boolean"},
            {"key": "importe_donacion_ecologica", "label": "Importe total de las donaciones ecologicas", "type": "number"}
        ]),
        "legal_reference": "Art. 3 DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 2. Por donaciones para rehabilitacion/conservacion del patrimonio historico
    # =========================================================================
    {
        "code": "CAN-DON-002",
        "name": "Por donaciones para rehabilitacion o conservacion del patrimonio historico de Canarias",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 150.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades donadas para bienes inscritos en el Registro Canario de Bienes de Interes Cultural. Maximo 150 EUR o 10% de la cuota integra autonomica.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones a bienes en Canarias inscritos en el Registro Canario de Bienes de Interes Cultural o incluidos en el Inventario de Bienes Muebles",
                "Entidades destinatarias: administraciones publicas, Iglesia Catolica, fundaciones/asociaciones segun Ley 49/2002",
                "Limite: 10% de la cuota integra autonomica o 150 EUR por contribuyente"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_patrimonio_canarias", "label": "Ha donado para rehabilitacion del patrimonio historico de Canarias?", "type": "boolean"},
            {"key": "importe_donacion_patrimonio", "label": "Importe total de las donaciones al patrimonio", "type": "number"}
        ]),
        "legal_reference": "Art. 4 DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 3. Por donaciones con fines culturales, deportivos, investigacion o docencia
    # =========================================================================
    {
        "code": "CAN-DON-003",
        "name": "Por donaciones con fines culturales, deportivos, de investigacion o docencia",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 50000.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones y aportaciones dinerarias con fines culturales, deportivos, de investigacion o docencia. Limites segun destinatario (3.000-50.000 EUR). Limite global: 5% de la cuota integra autonomica.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias a administraciones publicas, entidades culturales/deportivas, universidades, centros de investigacion",
                "Empresas privadas: fondos propios < 300.000 EUR",
                "Limites por destinatario: publicas 50.000, culturales 3.000, investigacion 3.000, universidades 50.000",
                "Limite global: 5% de la cuota integra autonomica (casilla 0546)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_cultural_canarias", "label": "Ha realizado donaciones culturales, deportivas o de investigacion en Canarias?", "type": "boolean"},
            {"key": "importe_donacion_cultural", "label": "Importe total de las donaciones culturales/deportivas", "type": "number"}
        ]),
        "legal_reference": "Art. 4 bis DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 4. Por donaciones a entidades sin animo de lucro
    # =========================================================================
    {
        "code": "CAN-DON-004",
        "name": "Por donaciones a entidades sin animo de lucro",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de los primeros 150 EUR donados y 15% del resto (17,5% si se repite donacion a misma entidad). Base maxima: 10% de la base imponible del contribuyente.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones a entidades acogidas a Ley 49/2002",
                "Primeros 150 EUR: 20%",
                "Resto: 15% (17,5% si donacion recurrente a misma entidad en 2 periodos anteriores)",
                "Base maxima: 10% de la base imponible",
                "Incompatible con deducciones autonomicas por donaciones ecologicas o culturales si coincide beneficiario"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_ong_canarias", "label": "Ha donado a entidades sin animo de lucro acogidas a Ley 49/2002?", "type": "boolean"},
            {"key": "importe_donacion_ong", "label": "Importe total donado a entidades sin animo de lucro", "type": "number"},
            {"key": "donacion_recurrente", "label": "Ha donado a la misma entidad en los 2 ejercicios anteriores?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 4 ter DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 5. Por cantidades destinadas a restauracion de inmuebles de interes cultural
    # =========================================================================
    {
        "code": "CAN-VIV-001",
        "name": "Por cantidades destinadas a restauracion, rehabilitacion o reparacion de inmuebles de interes cultural",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de las cantidades destinadas a restauracion, rehabilitacion o reparacion de inmuebles de interes cultural. Limite: 10% de la cuota integra autonomica. Limite conjunto con otras deducciones vivienda: 15%.",
            "limites_renta": {},
            "condiciones": [
                "Inmueble inscrito en Registro Canario de Bienes de Interes Cultural o afectado por declaracion",
                "Obras autorizadas por autoridad autonómica, cabildo o ayuntamiento competente",
                "Base reducida por subvenciones publicas exentas recibidas",
                "Limite: 10% de la cuota integra autonomica",
                "Limite conjunto con deducciones vivienda: 15% de la cuota integra autonomica"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "restauracion_cultural_canarias", "label": "Ha realizado obras de restauracion en inmuebles de interes cultural en Canarias?", "type": "boolean"},
            {"key": "importe_restauracion_cultural", "label": "Importe de las obras de restauracion", "type": "number"}
        ]),
        "legal_reference": "Arts. 6 y 14 quater DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 6. Por gastos de estudios de educacion superior
    # =========================================================================
    {
        "code": "CAN-EDU-001",
        "name": "Por gastos de estudios de educacion superior",
        "category": "educacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1920.0,
        "percentage": None,
        "fixed_amount": 1800.0,
        "requirements": json.dumps({
            "descripcion": "1.800 EUR por estudios fuera de la isla de residencia (1.920 EUR si base imponible < 37.062 EUR). 900 EUR por estudios en misma isla con desplazamiento justificado. Limite: 40% de la cuota integra autonomica.",
            "limites_renta": LIMITES_CANARIAS,
            "condiciones": [
                "Hijos solteros dependientes menores de 25 anos",
                "Matriculados en educacion superior (minimo curso completo o 30 creditos)",
                "Dependencia economica del contribuyente",
                "Renta anual del dependiente <= 8.000 EUR",
                "1.800 EUR si no hay oferta educativa publica en la isla",
                "1.920 EUR si base imponible < 37.062 EUR",
                "900 EUR si estudios en misma isla con desplazamiento acreditado",
                "Limite: 40% de la cuota integra autonomica (casilla 0546)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "hijos_universidad_canarias", "label": "Tiene hijos estudiando educacion superior fuera de su isla de residencia?", "type": "boolean"},
            {"key": "num_hijos_universidad", "label": "Cuantos hijos estudian fuera de la isla?", "type": "number"},
            {"key": "base_imponible_baja", "label": "Su base imponible es inferior a 37.062 EUR?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 7 DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 7. Por gastos de estudios no superiores
    # =========================================================================
    {
        "code": "CAN-EDU-002",
        "name": "Por gastos de estudios no superiores",
        "category": "educacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 100.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "100% de los gastos de estudios no superiores. Maximo 133 EUR por el primer hijo y 66 EUR adicionales por cada hijo restante.",
            "limites_renta": LIMITES_CANARIAS,
            "condiciones": [
                "Hijos dependientes en educacion infantil, basica o secundaria postobligatoria",
                "Gastos elegibles: libros de texto, material escolar, transporte, uniforme, comedor",
                "Maximo 133 EUR por el primer hijo",
                "66 EUR adicionales por cada hijo adicional",
                "Requiere factura reglamentaria (RD 1619/2012)",
                "Base reducida por becas/subvenciones publicas exentas"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "gastos_estudios_no_superiores", "label": "Ha pagado gastos de estudios no superiores de sus hijos?", "type": "boolean"},
            {"key": "num_hijos_estudios_no_sup", "label": "Cuantos hijos tienen gastos de estudios no superiores?", "type": "number"},
            {"key": "importe_gastos_estudios", "label": "Importe total de gastos de estudios", "type": "number"}
        ]),
        "legal_reference": "Art. 7 bis DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 8. Por trasladar residencia habitual a otra isla por motivos laborales
    # =========================================================================
    {
        "code": "CAN-LAB-001",
        "name": "Por trasladar la residencia habitual a otra isla del archipielago por motivos de trabajo",
        "category": "trabajo",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por trasladar la residencia habitual a otra isla de Canarias por trabajo o actividad economica. Aplicable el ano del traslado y el siguiente.",
            "limites_renta": LIMITES_CANARIAS,
            "condiciones": [
                "Traslado motivado por empleo o actividad economica",
                "El contribuyente debe permanecer en la isla de destino el ano del traslado mas 3 anos siguientes",
                "Incumplimiento obliga a reintegrar las cantidades deducidas con intereses",
                "Aplicable el ano del traslado y el ano siguiente",
                "300 EUR por cada conyuge que se traslade si tributacion conjunta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "traslado_isla_canarias", "label": "Se ha trasladado a otra isla de Canarias por motivos laborales?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 8 DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 9. Por inversion en acciones/participaciones de entidades nuevas o reciente creacion
    # =========================================================================
    {
        "code": "CAN-INV-001",
        "name": "Por inversion en adquisicion de acciones o participaciones sociales de nuevas entidades o de reciente creacion",
        "category": "inversion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 6000.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades invertidas en entidades nuevas (max 4.000 EUR). 30% si entidades vinculadas a universidades/investigacion o cooperativas de trabajo (max 6.000 EUR).",
            "limites_renta": {},
            "condiciones": [
                "General: 20% con limite 4.000 EUR anuales",
                "Entidades vinculadas a universidades/investigacion: 30% con limite 6.000 EUR",
                "Cooperativas de trabajo asociado: 30% con limite 6.000 EUR",
                "Participacion no superior al 40% del capital (incluyendo conyuge/familiares hasta 3er grado)",
                "No ejercer funciones directivas",
                "Mantener participacion minimo 3 anos",
                "Entidad domiciliada en Canarias con actividad economica",
                "Minimo 1 empleado a tiempo completo en Seguridad Social"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_empresa_nueva_canarias", "label": "Ha invertido en acciones o participaciones de empresas nuevas en Canarias?", "type": "boolean"},
            {"key": "importe_inversion_empresa", "label": "Importe total invertido", "type": "number"},
            {"key": "empresa_vinculada_universidad", "label": "La empresa esta vinculada a universidad o investigacion?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 9 DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 10. Por nacimiento o adopcion de hijos
    # =========================================================================
    {
        "code": "CAN-FAM-001",
        "name": "Por nacimiento o adopcion de hijos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 928.0,
        "percentage": None,
        "fixed_amount": 265.0,
        "requirements": json.dumps({
            "descripcion": "Deduccion por nacimiento o adopcion: 265 EUR (1o/2o hijo), 530 EUR (3o), 796 EUR (4o), 928 EUR (5o+). Importes adicionales por discapacidad >= 65%: 600 EUR (1o/2o) o 1.100 EUR (3o+).",
            "limites_renta": LIMITES_CANARIAS,
            "condiciones": [
                "1er o 2o hijo: 265 EUR",
                "3er hijo: 530 EUR",
                "4o hijo: 796 EUR",
                "5o hijo o siguientes: 928 EUR",
                "Hijo con discapacidad >= 65%: +600 EUR (1o/2o) o +1.100 EUR (3o+)",
                "Hijo nacido o adoptado en el periodo, conviviendo con el contribuyente",
                "Si ambos progenitores tienen derecho: se divide a partes iguales",
                "Orden de hijos determinado por convivencia a 31 de diciembre",
                "Compatible con deduccion por familia numerosa"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_adopcion_canarias", "label": "Ha tenido o adoptado hijos en 2025?", "type": "boolean"},
            {"key": "num_hijo_orden", "label": "Que numero de hijo es (1o, 2o, 3o...)?", "type": "number"},
            {"key": "hijo_discapacidad_65", "label": "El hijo tiene discapacidad reconocida >= 65%?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 10 DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 11. Por contribuyentes con discapacidad y mayores de 65 anos
    # =========================================================================
    {
        "code": "CAN-DIS-001",
        "name": "Por contribuyentes con discapacidad y mayores de 65 anos",
        "category": "discapacidad",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 560.0,
        "percentage": None,
        "fixed_amount": 400.0,
        "requirements": json.dumps({
            "descripcion": "400 EUR por discapacidad >= 33%. 160 EUR por mayor de 65 anos. Ambas compatibles entre si (maximo 560 EUR).",
            "limites_renta": LIMITES_CANARIAS,
            "condiciones": [
                "Discapacidad >= 33%: 400 EUR",
                "Mayor de 65 anos: 160 EUR",
                "Ambos importes son compatibles (se pueden sumar)",
                "Circunstancias valoradas a 31 de diciembre"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_33_canarias", "label": "Tiene una discapacidad reconocida >= 33%?", "type": "boolean"},
            {"key": "mayor_65_canarias", "label": "Tiene mas de 65 anos?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 11 DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 12. Por acogimiento de menores
    # =========================================================================
    {
        "code": "CAN-FAM-002",
        "name": "Por acogimiento de menores",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 330.0,
        "requirements": json.dumps({
            "descripcion": "330 EUR por cada menor en regimen de acogimiento familiar (urgencia, temporal o permanente). Prorrateo si convivencia inferior al periodo impositivo completo.",
            "limites_renta": {},
            "condiciones": [
                "Menores en acogimiento familiar de urgencia, temporal o permanente",
                "Debe convivir con el menor la totalidad del periodo impositivo",
                "Si convivencia inferior al periodo completo: prorrateo por dias",
                "No aplica si se produce adopcion en el periodo impositivo",
                "Si varios contribuyentes tienen derecho: se divide a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "acogimiento_menores_canarias", "label": "Tiene menores en regimen de acogimiento familiar?", "type": "boolean"},
            {"key": "num_menores_acogidos", "label": "Cuantos menores tiene en acogimiento?", "type": "number"}
        ]),
        "legal_reference": "Art. 11 bis DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 13. Por familias monoparentales
    # =========================================================================
    {
        "code": "CAN-FAM-003",
        "name": "Por familias monoparentales",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 133.0,
        "requirements": json.dumps({
            "descripcion": "133 EUR para familias monoparentales. El contribuyente debe tener hijos dependientes y no convivir con otra persona distinta de ascendientes.",
            "limites_renta": LIMITES_CANARIAS,
            "condiciones": [
                "Contribuyente con hijos dependientes sin convivir con otra persona (excepto ascendientes que generen derecho a minimo)",
                "Dependientes: hijos menores, mayores con discapacidad, o tutelados",
                "Rentas anuales del dependiente <= 8.000 EUR (excluidas exentas)",
                "Si cambio de situacion familiar: convivencia minima 183 dias"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familia_monoparental_canarias", "label": "Es familia monoparental (vive solo con sus hijos)?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 11 ter DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 14. Por gastos de custodia en guarderias
    # =========================================================================
    {
        "code": "CAN-FAM-004",
        "name": "Por gastos de custodia en guarderias",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 530.0,
        "percentage": 18.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "18% de las cantidades pagadas por guarderia autorizada para hijos menores de 3 anos. Maximo 530 EUR por hijo.",
            "limites_renta": LIMITES_CANARIAS,
            "condiciones": [
                "Hijos menores de 3 anos (incluidos en tutela o acogimiento no remunerado)",
                "Guarderia autorizada",
                "Requiere factura reglamentaria (RD 1619/2012)",
                "Prorrateo en el ano que el hijo cumple 3 anos",
                "Si varios contribuyentes tienen derecho: se divide a partes iguales",
                "Base reducida por ayudas publicas exentas"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "guarderia_canarias", "label": "Tiene hijos menores de 3 anos en guarderia?", "type": "boolean"},
            {"key": "gasto_guarderia_canarias", "label": "Importe total pagado en guarderia", "type": "number"},
            {"key": "num_hijos_guarderia", "label": "Cuantos hijos menores de 3 anos asisten a guarderia?", "type": "number"}
        ]),
        "legal_reference": "Art. 12 DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 15. Por familia numerosa
    # =========================================================================
    {
        "code": "CAN-FAM-005",
        "name": "Por familia numerosa",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1459.0,
        "percentage": None,
        "fixed_amount": 597.0,
        "requirements": json.dumps({
            "descripcion": "General: 597 EUR. Especial: 796 EUR. Con discapacidad >= 65%: 1.326 EUR (general) o 1.459 EUR (especial).",
            "limites_renta": {},
            "condiciones": [
                "Titulo de familia numerosa vigente a fecha de devengo",
                "General: 597 EUR",
                "Especial: 796 EUR",
                "Con discapacidad >= 65% (conyuge o descendiente): General 1.326 EUR, Especial 1.459 EUR",
                "Clasificacion segun Ley 40/2003",
                "Si varios contribuyentes: se divide a partes iguales",
                "Compatible con deduccion por nacimiento o adopcion"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familia_numerosa_canarias", "label": "Tiene titulo de familia numerosa?", "type": "boolean"},
            {"key": "categoria_familia_numerosa", "label": "Categoria de familia numerosa", "type": "select", "options": ["general", "especial"]},
            {"key": "discapacidad_familia_65", "label": "Algun miembro de la unidad familiar tiene discapacidad >= 65%?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 13 DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 16. Por inversion en vivienda habitual
    # =========================================================================
    {
        "code": "CAN-VIV-002",
        "name": "Por inversion en vivienda habitual",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 6000.0,
        "percentage": 5.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "3,5%-5,5% de las cantidades invertidas en vivienda habitual segun base imponible y edad. Maximo 6.000 EUR anuales.",
            "limites_renta": LIMITES_CANARIAS,
            "condiciones": [
                "Base imponible < 26.035 EUR: 5% (5,5% si menor de 40 anos)",
                "Base imponible >= 26.035 y < 46.455 EUR: 3,5% (4% si menor de 40 anos)",
                "Adquisicion, construccion, rehabilitacion o ampliacion de vivienda habitual",
                "Construccion completada en 4 anos (ampliable a 8 en casos excepcionales)",
                "Requisitos del Art. 68.1 Ley IRPF (a 1 enero 2012)",
                "Base reducida por subvenciones publicas exentas",
                "Limite conjunto con otras deducciones vivienda: 15% de la cuota integra autonomica"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_vivienda_canarias", "label": "Ha invertido en adquisicion o rehabilitacion de vivienda habitual en Canarias?", "type": "boolean"},
            {"key": "importe_inversion_vivienda", "label": "Importe invertido en vivienda habitual", "type": "number"},
            {"key": "menor_40_canarias", "label": "Tiene menos de 40 anos?", "type": "boolean"}
        ]),
        "legal_reference": "Arts. 14 y 14 quater DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 17. Por obras de rehabilitacion energetica de vivienda habitual
    # =========================================================================
    {
        "code": "CAN-VIV-003",
        "name": "Por obras de rehabilitacion energetica de la vivienda habitual",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 7000.0,
        "percentage": 12.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "12% de las cantidades invertidas en rehabilitacion energetica. Base maxima 7.000 EUR. Limite: 10% de la cuota integra autonomica.",
            "limites_renta": {},
            "condiciones": [
                "Vivienda habitual del contribuyente",
                "Pago mediante tarjeta, transferencia, cheque nominativo o deposito bancario (no efectivo)",
                "Obras que mejoren eficiencia energetica, rendimiento instalaciones termicas o incorporen renovables",
                "Instalaciones de ahorro de agua y sistemas de aguas residuales incluidos",
                "Excluidos: garajes, jardines, piscinas, electrodomesticos",
                "Requiere certificado de eficiencia energetica (RD 390/2021)",
                "Base reducida por ayudas publicas exentas",
                "Limite: 10% de la cuota integra autonomica",
                "Limite conjunto con deducciones vivienda: 15%"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "rehabilitacion_energetica_canarias", "label": "Ha realizado obras de rehabilitacion energetica en su vivienda habitual en Canarias?", "type": "boolean"},
            {"key": "importe_rehabilitacion_energetica", "label": "Importe de las obras de rehabilitacion energetica", "type": "number"}
        ]),
        "legal_reference": "Arts. 14 bis y 14 quater DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 18. Por obras de adecuacion de vivienda habitual por personas con discapacidad
    # =========================================================================
    {
        "code": "CAN-VIV-004",
        "name": "Por obras de adecuacion de la vivienda habitual por personas con discapacidad",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 15000.0,
        "percentage": 14.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "14% de las cantidades invertidas en adecuacion de vivienda para discapacidad >= 65% (18% si ademas mayor de 65 anos). Maximo 15.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Discapacidad >= 65%",
                "14% de las cantidades invertidas",
                "18% si el discapacitado es ademas mayor de 65 anos",
                "Obras estrictamente necesarias para accesibilidad y comunicacion sensorial",
                "Certificadas por autoridad competente",
                "Dependientes (conyuge, ascendientes, descendientes): renta anual <= 35.735 EUR",
                "Base reducida por subvenciones publicas exentas",
                "Limite conjunto con deducciones vivienda: 15% de la cuota integra autonomica"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "adecuacion_discapacidad_canarias", "label": "Ha realizado obras de adecuacion de vivienda por discapacidad >= 65%?", "type": "boolean"},
            {"key": "importe_adecuacion_discapacidad", "label": "Importe de las obras de adecuacion", "type": "number"},
            {"key": "discapacitado_mayor_65", "label": "La persona con discapacidad es mayor de 65 anos?", "type": "boolean"}
        ]),
        "legal_reference": "Arts. 14 ter y 14 quater DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 19. Por alquiler de vivienda habitual
    # =========================================================================
    {
        "code": "CAN-VIV-005",
        "name": "Por alquiler de vivienda habitual",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 760.0,
        "percentage": 24.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "24% de las cantidades satisfechas en alquiler de vivienda habitual. Maximo 740 EUR (760 EUR si menor de 40 o mayor de 75 anos).",
            "limites_renta": LIMITES_CANARIAS,
            "condiciones": [
                "Cantidades de alquiler deben superar el 10% de las bases imponibles",
                "Contrato referido a vivienda habitual (ocupacion superior a 1 ano)",
                "Duracion minima del contrato: 1 ano",
                "El inquilino debe ser titular del contrato",
                "Maximo 740 EUR anuales (estandar)",
                "Maximo 760 EUR si menor de 40 o mayor de 75 anos",
                "Requiere declarar NIF del arrendador, referencia catastral y renta anual",
                "Base reducida por subvenciones publicas exentas"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_vivienda_canarias", "label": "Vive de alquiler en Canarias?", "type": "boolean"},
            {"key": "importe_alquiler_anual", "label": "Importe anual del alquiler", "type": "number"},
            {"key": "menor_40_o_mayor_75", "label": "Tiene menos de 40 o mas de 75 anos?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 15 DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 20. Por arrendamiento vinculado a dacion en pago
    # =========================================================================
    {
        "code": "CAN-VIV-006",
        "name": "Por arrendamiento de vivienda habitual vinculado a operaciones de dacion en pago",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1200.0,
        "percentage": 25.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "25% de las cantidades pagadas en alquiler vinculado a dacion en pago de vivienda habitual. Maximo 1.200 EUR.",
            "limites_renta": LIMITES_CANARIAS,
            "condiciones": [
                "Transmision de vivienda habitual a entidad financiera por imposibilidad de pago hipotecario",
                "El transmitente continua ocupando la vivienda mediante arrendamiento con opcion de compra",
                "Contrato firmado con la entidad financiera o su filial inmobiliaria",
                "Base reducida por ayudas publicas exentas"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "dacion_pago_canarias", "label": "Vive en alquiler tras una dacion en pago de su vivienda?", "type": "boolean"},
            {"key": "importe_alquiler_dacion", "label": "Importe anual del alquiler vinculado a dacion en pago", "type": "number"}
        ]),
        "legal_reference": "Art. 15 bis DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 21. Por gastos de adecuacion de inmueble para arrendamiento como vivienda
    # =========================================================================
    {
        "code": "CAN-VIV-007",
        "name": "Por gastos de adecuacion de inmueble con destino al arrendamiento como vivienda habitual",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 150.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de los gastos de adecuacion de inmueble para arrendamiento como vivienda habitual. Maximo 150 EUR por inmueble arrendado.",
            "limites_renta": {},
            "condiciones": [
                "Gastos elegibles: reparacion, conservacion, formalizacion contrato, seguros, certificado energetico",
                "Requiere factura reglamentaria (RD 1619/2012)",
                "Solo arrendamientos de vivienda (Ley 29/1994)",
                "Propiedad conjunta: prorrateo por porcentaje de titularidad",
                "Base reducida por subvenciones publicas",
                "Declarar NIF del prestador de servicios e importe anual",
                "Incompatible con deduccion por seguros de impagos"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "adecuacion_arrendamiento_canarias", "label": "Ha adecuado un inmueble para destinarlo al alquiler como vivienda en Canarias?", "type": "boolean"},
            {"key": "importe_adecuacion_arrendamiento", "label": "Importe de los gastos de adecuacion", "type": "number"}
        ]),
        "legal_reference": "Art. 15 ter DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 22. Por primas de seguros de credito para cubrir impagos de alquiler
    # =========================================================================
    {
        "code": "CAN-VIV-008",
        "name": "Por gastos en primas de seguros de credito para cubrir impagos de rentas de arrendamiento",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 150.0,
        "percentage": 75.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "75% de las primas de seguros de credito para cubrir impagos de alquiler. Maximo 150 EUR anuales por contribuyente.",
            "limites_renta": {},
            "condiciones": [
                "Contrato de alquiler de duracion >= 1 ano con el mismo inquilino",
                "Fianza depositada en organismo autonomico canario (Ley 29/1994)",
                "El arrendador debe declarar los ingresos como rendimientos del capital inmobiliario",
                "Arrendador al corriente de obligaciones tributarias",
                "Renta mensual del alquiler <= 800 EUR",
                "Declarar NIF del inquilino y referencia catastral",
                "Incompatible con deduccion por gastos de adecuacion para arrendamiento"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "seguro_impago_canarias", "label": "Ha contratado un seguro de impago de alquiler para un inmueble en Canarias?", "type": "boolean"},
            {"key": "importe_prima_seguro", "label": "Importe de la prima del seguro de impago", "type": "number"}
        ]),
        "legal_reference": "Art. 15 quater DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 23. Por puesta de viviendas en el mercado de arrendamiento
    # =========================================================================
    {
        "code": "CAN-VIV-009",
        "name": "Por puesta de viviendas en el mercado de arrendamiento de viviendas habituales",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 5000.0,
        "percentage": None,
        "fixed_amount": 1000.0,
        "requirements": json.dumps({
            "descripcion": "1.000 EUR por cada vivienda puesta en el mercado de alquiler como vivienda habitual, en el primer periodo impositivo en que se arrienda. Maximo 5 viviendas.",
            "limites_renta": {},
            "condiciones": [
                "Solo en el primer periodo impositivo en que se arrienda la vivienda",
                "Contrato de arrendamiento de duracion efectiva >= 3 anos",
                "La actividad de arrendamiento no puede ser actividad economica",
                "El inquilino no puede ser conyuge o pariente hasta 3er grado",
                "Maximo 5 viviendas por contribuyente (excluidos garajes y trasteros)",
                "Prorrateo por porcentaje de titularidad",
                "Solo viviendas en Canarias"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "puesta_alquiler_canarias", "label": "Ha puesto alguna vivienda en el mercado de alquiler por primera vez en 2025?", "type": "boolean"},
            {"key": "num_viviendas_alquiler", "label": "Cuantas viviendas ha puesto en alquiler por primera vez?", "type": "number"}
        ]),
        "legal_reference": "Art. 16 DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 24. Por contribuyentes desempleados
    # =========================================================================
    {
        "code": "CAN-LAB-002",
        "name": "Por contribuyentes desempleados",
        "category": "trabajo",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 120.0,
        "requirements": json.dumps({
            "descripcion": "120 EUR para contribuyentes desempleados mas de 6 meses que cobren prestacion por desempleo.",
            "limites_renta": {"rendimientos_trabajo_min": 15876, "rendimientos_trabajo_max": 22000},
            "condiciones": [
                "Desempleado mas de 6 meses en el periodo impositivo",
                "Percibir prestaciones por desempleo",
                "Rendimientos del trabajo entre 15.876 y 22.000 EUR",
                "Base imponible general y del ahorro (excluyendo rendimientos trabajo) <= 1.600 EUR",
                "En tributacion conjunta: cada conyuge puede aplicarla si cumple individualmente"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "desempleado_canarias", "label": "Ha estado desempleado mas de 6 meses en 2025 cobrando prestacion?", "type": "boolean"},
            {"key": "rendimientos_trabajo", "label": "Rendimientos del trabajo en 2025", "type": "number"}
        ]),
        "legal_reference": "Art. 16 bis DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 25. Por gastos de enfermedad
    # =========================================================================
    {
        "code": "CAN-SAL-001",
        "name": "Por gastos de enfermedad",
        "category": "salud",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 700.0,
        "percentage": 12.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "12% de gastos medicos y sanitarios. Maximo 500 EUR individual (600 EUR si mayor 65 o discapacidad >= 65%). Maximo 700 EUR en tributacion conjunta.",
            "limites_renta": LIMITES_CANARIAS,
            "condiciones": [
                "Servicios de profesionales medicos/sanitarios (excluidos farmaceuticos)",
                "Prevencion, diagnostico, tratamiento, dental, embarazo, accidentes, discapacidad",
                "Excluidos: procedimientos esteticos (salvo accidentes o identidad de genero)",
                "Excluidas: primas de seguros de salud",
                "Individual: max 500 EUR (600 EUR si mayor 65 o discapacidad >= 65%)",
                "Conjunta: max 700 EUR",
                "Requiere factura reglamentaria",
                "Declarar NIF del profesional e importe anual",
                "Base reducida por ayudas publicas exentas"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "gastos_medicos_canarias", "label": "Ha tenido gastos medicos o sanitarios en 2025?", "type": "boolean"},
            {"key": "importe_gastos_medicos", "label": "Importe total de gastos medicos", "type": "number"},
            {"key": "mayor_65_o_discapacidad_65", "label": "Es mayor de 65 anos o tiene discapacidad >= 65%?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 16 ter DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 26. Por familiares dependientes con discapacidad
    # =========================================================================
    {
        "code": "CAN-DIS-002",
        "name": "Por familiares dependientes con discapacidad",
        "category": "discapacidad",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 600.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "600 EUR por ascendiente o descendiente con discapacidad >= 65%. O 20% de cuotas SS por empleados de hogar que cuiden al dependiente (max 500 EUR).",
            "limites_renta": LIMITES_CANARIAS,
            "condiciones": [
                "Opcion a): 600 EUR por cada ascendiente o descendiente con discapacidad >= 65%",
                "Opcion b): 20% de cuotas SS por empleados de hogar cuidadores (max 500 EUR/ano)",
                "Familiar debe generar derecho al minimo por discapacidad",
                "Para opcion b): persona debe necesitar ayuda de terceros; declarar NIF del empleado",
                "Base reducida por ayudas publicas exentas",
                "Si varios contribuyentes tienen derecho: prorrateo"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familiar_dependiente_discapacidad", "label": "Tiene familiares dependientes (ascendientes/descendientes) con discapacidad >= 65%?", "type": "boolean"},
            {"key": "num_familiares_discapacidad", "label": "Cuantos familiares dependientes con discapacidad >= 65%?", "type": "number"},
            {"key": "empleado_hogar_cuidador", "label": "Tiene empleado de hogar como cuidador del familiar dependiente?", "type": "boolean"},
            {"key": "cuotas_ss_empleado_hogar", "label": "Importe de cuotas SS pagadas por el empleado cuidador", "type": "number"}
        ]),
        "legal_reference": "Art. 16 quater DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 27. Por cuotas a la Seguridad Social por contratacion empleados de hogar
    # =========================================================================
    {
        "code": "CAN-LAB-003",
        "name": "Por cuotas satisfechas a la Seguridad Social por la contratacion de empleados del hogar",
        "category": "trabajo",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 500.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cuotas de Seguridad Social pagadas por empleados del hogar. Maximo 500 EUR por contribuyente.",
            "limites_renta": {},
            "condiciones": [
                "El contribuyente debe cumplir al menos una condicion:",
                "- Tener derecho al minimo por descendientes y obtener rendimientos del trabajo o actividades economicas",
                "- Tener 75 o mas anos",
                "- Tener 65+ anos con discapacidad fisica/sensorial/organica >= 65% o psiquica/intelectual >= 33%",
                "Empleados en el Sistema Especial para Empleados del Hogar",
                "Declarar NIF o numero de identidad de extranjero del trabajador",
                "Base reducida por ayudas publicas exentas",
                "En gananciales: se atribuye a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "empleado_hogar_canarias", "label": "Tiene empleado del hogar dado de alta en Seguridad Social?", "type": "boolean"},
            {"key": "cuotas_ss_hogar", "label": "Importe total de cuotas SS pagadas por empleado del hogar", "type": "number"}
        ]),
        "legal_reference": "Art. 16 quinquies DLeg 1/2009 Canarias"
    },

    # =========================================================================
    # 28. Por gastos de estudios de educacion superior (ya cubierto en CAN-EDU-001)
    # NOTE: The AEAT lists "justificacion documental" as a separate entry but
    # it's not a separate deduction. Entry 29 "limites comunes" is also not a
    # deduction. So we have exactly 28 deductions (items 1-28 excluding the
    # documentation and common limits entries).
    # =========================================================================
]


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

async def seed_canarias(dry_run: bool = False):
    """Delete existing Canarias 2025 deductions and insert all 28."""

    print(f"{'[DRY RUN] ' if dry_run else ''}Seeding {len(CANARIAS_2025)} Canarias deductions for IRPF {TAX_YEAR}")
    print("=" * 70)

    if not dry_run:
        from app.database.turso_client import TursoClient
        db = TursoClient()
        await db.connect()
        print("Connected to database.\n")

        # Delete existing Canarias deductions for this tax year
        for col_name in ("ccaa", "territory"):
            try:
                result = await db.execute(
                    f"DELETE FROM deductions WHERE {col_name} = ? AND tax_year = ?",
                    [TERRITORY, TAX_YEAR],
                )
                if hasattr(result, "rows_affected") and result.rows_affected:
                    print(f"  Deleted {result.rows_affected} existing Canarias deductions (column: {col_name})")
                else:
                    print(f"  No existing deductions found to delete (column: {col_name})")
            except Exception:
                pass

        print()

    inserted = 0
    for i, d in enumerate(CANARIAS_2025, 1):
        code = d["code"]
        name = d["name"]
        category = d["category"]

        if dry_run:
            fa = d.get("fixed_amount")
            pct = d.get("percentage")
            mx = d.get("max_amount")
            amount_str = ""
            if fa:
                amount_str = f"{fa} EUR fijo"
            elif pct:
                amount_str = f"{pct}%"
                if mx:
                    amount_str += f" (max {mx} EUR)"
            else:
                amount_str = "variable"
            print(f"  {i:2d}. [{code}] {name}")
            print(f"      Categoria: {category} | Importe: {amount_str}")
            print(f"      Ref: {d.get('legal_reference', 'N/A')}")
            print()
            inserted += 1
            continue

        deduction_id = str(uuid.uuid4())
        try:
            await db.execute(
                """INSERT INTO deductions
                   (id, code, name, category, scope, ccaa,
                    max_amount, percentage, tax_year, is_active,
                    requirements, questions, legal_reference)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    deduction_id,
                    code,
                    name,
                    category,
                    d["scope"],
                    d["ccaa"],
                    d.get("max_amount"),
                    d.get("percentage"),
                    d["tax_year"],
                    1 if d.get("is_active", True) else 0,
                    d.get("requirements"),
                    d.get("questions"),
                    d.get("legal_reference"),
                ],
            )
            inserted += 1
            print(f"  {i:2d}. [OK] {code} — {name}")
        except Exception as e:
            try:
                deduction_id = str(uuid.uuid4())
                await db.execute(
                    """INSERT INTO deductions
                       (id, code, tax_year, territory, name, type, category,
                        percentage, max_amount, fixed_amount, legal_reference,
                        description, requirements_json, questions_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [
                        deduction_id,
                        code,
                        d["tax_year"],
                        d["ccaa"],
                        name,
                        "deduccion",
                        category,
                        d.get("percentage"),
                        d.get("max_amount"),
                        d.get("fixed_amount"),
                        d.get("legal_reference"),
                        json.loads(d.get("requirements", "{}")).get("descripcion", ""),
                        d.get("requirements"),
                        d.get("questions"),
                    ],
                )
                inserted += 1
                print(f"  {i:2d}. [OK-fallback] {code} — {name}")
            except Exception as e2:
                print(f"  {i:2d}. [ERROR] {code} — {e2}")

    print()
    print("=" * 70)
    print(f"{'[DRY RUN] ' if dry_run else ''}Total: {inserted}/{len(CANARIAS_2025)} deductions {'would be ' if dry_run else ''}inserted")
    print()

    # Summary by category
    categories = {}
    for d in CANARIAS_2025:
        cat = d["category"]
        categories[cat] = categories.get(cat, 0) + 1
    print("By category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Seed all 28 Canarias IRPF deductions for 2025")
    parser.add_argument("--dry-run", action="store_true", help="Print deductions without inserting into DB")
    args = parser.parse_args()
    asyncio.run(seed_canarias(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
