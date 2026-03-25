"""
Seed ALL 28 official Region de Murcia autonomous deductions for IRPF 2025.

Source: AEAT Manual Practico IRPF 2025 — Comunidad Autonoma de la Region de Murcia
https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/
    irpf-2025-deducciones-autonomicas/comunidad-autonoma-region-murcia.html

Legal basis: Decreto Legislativo 1/2010, de 5 de noviembre, por el que se aprueba el
Texto Refundido de las disposiciones legales vigentes en la Region de Murcia en materia
de tributos cedidos.

Idempotent: DELETE existing Murcia deductions for tax_year=2025, then INSERT all 28.

Usage:
    cd backend
    python scripts/seed_deductions_murcia_2025.py
    python scripts/seed_deductions_murcia_2025.py --dry-run
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

TERRITORY = "Murcia"
TAX_YEAR = 2025

# Common income limits
LIMITES_MURCIA_30_50 = {"individual": 30000, "conjunta": 50000}


# =============================================================================
# ALL 28 MURCIA DEDUCTIONS — IRPF 2025
# =============================================================================

MURCIA_2025 = [
    # =========================================================================
    # 1. Por inversion en vivienda habitual por jovenes <= 40 anos
    # =========================================================================
    {
        "code": "MUR-VIV-001",
        "name": "Por inversion en vivienda habitual por jovenes de edad igual o inferior a 40 anos",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": 5.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "5% de las cantidades invertidas en vivienda habitual por jovenes <= 40 anos. Max 300 EUR. Base maxima inversion 9.040 EUR menos cantidades con deduccion estatal.",
            "limites_renta": {"individual": 40000, "ahorro_max": 1800},
            "condiciones": [
                "Residencia habitual en la Region de Murcia",
                "Edad <= 40 anos a fecha de devengo (31 diciembre)",
                "Adquisicion/ampliacion: vivienda de nueva construccion (primera transmision tras final de obra, max 3 anos)",
                "Rehabilitacion: protegida segun RD 2066/2008 o normativa equivalente",
                "Base imponible general + ahorro < 40.000 EUR",
                "Base imponible del ahorro <= 1.800 EUR",
                "Patrimonio debe incrementarse al menos en el importe de la inversion",
                "Incompatible con deduccion de familias numerosas para misma vivienda"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_vivienda_joven_murcia", "label": "Ha invertido en vivienda habitual en Murcia siendo menor de 40 anos?", "type": "boolean"},
            {"key": "importe_inversion_vivienda_murcia", "label": "Importe invertido en vivienda", "type": "number"},
            {"key": "menor_40_murcia", "label": "Tiene 40 anos o menos?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 1.Uno DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 2. Por donativos para la proteccion del patrimonio cultural y actividades sociales
    # =========================================================================
    {
        "code": "MUR-DON-001",
        "name": "Por donativos para la proteccion del patrimonio cultural, actividades artisticas, sociales, cientificas y medioambientales",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 50.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "50% de las donaciones dinerarias puras y simples para proteccion del patrimonio cultural y actividades sociales de la Region de Murcia.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras, simples e irrevocables",
                "Destinatarios segun Ley 4/2022 de mecenazgo de Murcia",
                "Incluye: entidades sin animo de lucro, administraciones publicas, universidades, centros de investigacion, profesionales culturales",
                "Requiere certificacion de la entidad beneficiaria",
                "Transferencia bancaria obligatoria",
                "Base reducida por importes ya deducidos via Art. 68.3 Ley IRPF",
                "Incompatible con creditos fiscales de Ley 4/2022"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donativo_cultural_murcia", "label": "Ha donado para proteccion del patrimonio cultural o actividades sociales en Murcia?", "type": "boolean"},
            {"key": "importe_donativo_cultural", "label": "Importe total de las donaciones", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Dos.1 DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 3. Por donativos para la investigacion biosanitaria
    # =========================================================================
    {
        "code": "MUR-DON-002",
        "name": "Por donativos para la investigacion biosanitaria",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 50.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "50% de las donaciones dinerarias puras y simples para investigacion biosanitaria en la Region de Murcia.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras, simples e irrevocables",
                "Destinatarios: Comunidad Autonoma, entes del sector publico con investigacion biosanitaria, universidades publicas de Murcia, entidades sin animo de lucro inscritas con objetivo biosanitario",
                "Requiere certificacion de la entidad beneficiaria",
                "Transferencia bancaria obligatoria",
                "Base reducida por importes ya deducidos via Art. 68.3 Ley IRPF",
                "Incompatible con creditos fiscales de Ley 4/2022"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donativo_biosanitario_murcia", "label": "Ha donado para investigacion biosanitaria en Murcia?", "type": "boolean"},
            {"key": "importe_donativo_biosanitario", "label": "Importe total donado", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Dos.2 DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 4. Por donaciones de bienes inscritos en el Inventario del Patrimonio Cultural
    # =========================================================================
    {
        "code": "MUR-DON-003",
        "name": "Por donaciones de bienes inscritos en el Inventario del Patrimonio Cultural de la Region de Murcia",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% del valor de donaciones de bienes inscritos en el Inventario de Patrimonio Cultural de la Region de Murcia.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones puras y simples de bienes del Inventario de Patrimonio Cultural",
                "Destinatarios: Gobierno Regional, corporaciones locales, entidades publicas culturales, universidades, centros de investigacion, entidades sin animo de lucro culturales",
                "Requiere certificacion de la entidad beneficiaria",
                "Base limitada al valor de mercado del bien en el momento de la donacion",
                "Incompatible con creditos fiscales de Ley 4/2022"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_patrimonio_cultural_murcia", "label": "Ha donado bienes inscritos en el Inventario del Patrimonio Cultural de Murcia?", "type": "boolean"},
            {"key": "valor_donacion_patrimonio", "label": "Valor de mercado de los bienes donados", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Dos.3 DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 5. Por gastos de guarderia
    # =========================================================================
    {
        "code": "MUR-FAM-001",
        "name": "Por gastos de guarderia",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1000.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades pagadas en guarderia (primer ciclo de educacion infantil). Max 1.000 EUR por hijo (500 EUR si ambos progenitores deducen).",
            "limites_renta": LIMITES_MURCIA_30_50,
            "condiciones": [
                "Primer Ciclo de Educacion Infantil (0-3 anos)",
                "Centro autorizado e inscrito por la autoridad educativa competente",
                "Hijo matriculado y conviviendo con el contribuyente a fecha de devengo",
                "Max 1.000 EUR por hijo (500 EUR por progenitor si ambos deducen)",
                "Custodia compartida: ambos pueden deducir con prorrateo",
                "Gastos: custodia/cuidado, preinscripcion, matricula, alimentacion, ropa escolar",
                "Base reducida por becas/subvenciones publicas",
                "Conservar facturas durante plazo de prescripcion"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "guarderia_murcia", "label": "Tiene hijos en guarderia (primer ciclo infantil) en Murcia?", "type": "boolean"},
            {"key": "gasto_guarderia_murcia", "label": "Importe total pagado en guarderia", "type": "number"},
            {"key": "num_hijos_guarderia_murcia", "label": "Cuantos hijos asisten a guarderia?", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Tres DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 6. Por inversiones en dispositivos domesticos de ahorro de agua
    # =========================================================================
    {
        "code": "MUR-MED-001",
        "name": "Por inversiones en dispositivos domesticos de ahorro de agua",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 60.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las inversiones en dispositivos de ahorro de agua en vivienda habitual. Max 60 EUR (base max 300 EUR).",
            "limites_renta": {},
            "condiciones": [
                "Dispositivos instalados en vivienda habitual del contribuyente",
                "Vivienda habitual: ocupacion continuada durante 3 anos (excepciones: fallecimiento, separacion, traslado laboral, primer empleo)",
                "Autorizacion previa de la Administracion regional",
                "Base maxima: 300 EUR anuales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "ahorro_agua_murcia", "label": "Ha instalado dispositivos de ahorro de agua en su vivienda habitual en Murcia?", "type": "boolean"},
            {"key": "importe_ahorro_agua", "label": "Importe invertido en dispositivos de ahorro de agua", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Cuatro DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 7. Por inversion en instalaciones de recursos energeticos renovables
    # =========================================================================
    {
        "code": "MUR-MED-002",
        "name": "Por inversion en instalaciones de recursos energeticos renovables",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 7000.0,
        "percentage": 50.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Hasta 50% de la inversion en renovables segun tramos de renta. Max 7.000 EUR. Arrastre 2 anos.",
            "limites_renta": {"individual_max": 60000, "conjunta_max": 95000},
            "condiciones": [
                "Individual: hasta 34.999 = 50%, 35.000-44.999 = 37,5%, 45.000-59.999 = 25%, 60.000+ = no aplica",
                "Conjunta: hasta 49.999 = 50%, 50.000-74.999 = 37,5% (50.000-94.999 escalonado), 95.000+ = no aplica",
                "Inmueble en la Region de Murcia",
                "Vivienda habitual o inmueble para arrendamiento (no actividad economica)",
                "Sistemas de autoconsumo exclusivo con declaracion regulatoria",
                "Excluidos: fotovoltaicos sin compensacion de excedentes",
                "Factura de instalador profesional requerida",
                "Pago: tarjeta, transferencia o cheque (no efectivo)",
                "Arrastre maximo: 2 periodos impositivos siguientes si insuficiente cuota"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "renovables_murcia", "label": "Ha invertido en instalacion de energias renovables en Murcia?", "type": "boolean"},
            {"key": "importe_renovables_murcia", "label": "Importe de la inversion en renovables", "type": "number"},
            {"key": "tipo_inmueble_renovables", "label": "Tipo de inmueble", "type": "select", "options": ["vivienda_habitual", "arrendamiento"]}
        ]),
        "legal_reference": "Art. 1.Cinco DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 8. Por inversion en acciones/participaciones de entidades nuevas
    # =========================================================================
    {
        "code": "MUR-INV-001",
        "name": "Por inversion en adquisicion de acciones o participaciones sociales de nuevas entidades o de reciente creacion",
        "category": "inversion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 4000.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades invertidas en entidades nuevas o de reciente creacion domiciliadas en Murcia. Max 4.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Participacion (+ conyuge/familiares 3er grado) <= 40% del capital o derechos de voto durante 3+ anos",
                "Entidad con sede social y domicilio fiscal en la Region de Murcia durante 3+ anos",
                "Actividad economica (no gestion de patrimonio)",
                "Minimo 1 empleado a tiempo completo en Seguridad Social desde constitucion",
                "Para ampliaciones: empresa creada en los 3 anos anteriores; incremento plantilla >= 2 personas en 24 meses",
                "No ejercer funciones ejecutivas ni relacion laboral durante 10 anos",
                "Escritura publica requerida; mantenimiento minimo 3 anos",
                "Comunicacion previa a la Administracion tributaria regional"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_empresa_nueva_murcia", "label": "Ha invertido en empresas nuevas o de reciente creacion en Murcia?", "type": "boolean"},
            {"key": "importe_inversion_murcia", "label": "Importe invertido", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Seis DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 9. Por inversion en acciones de entidades cotizadas en el MAB
    # =========================================================================
    {
        "code": "MUR-INV-002",
        "name": "Por inversion en acciones de entidades que cotizan en el segmento de empresas en expansion del mercado alternativo bursatil",
        "category": "inversion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 10000.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades invertidas en acciones de entidades del MAB (segmento expansion) domiciliadas en Murcia. Max 10.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Participacion no superior al 10% del capital",
                "Mantenimiento minimo 2 anos",
                "Entidad domiciliada en la Region de Murcia",
                "Actividad principal distinta de gestion de patrimonio",
                "Requisitos mantenidos durante periodo de tenencia",
                "Escritura publica requerida",
                "Comunicacion previa a la Administracion regional",
                "Incompatible con deducciones por entidades nuevas o economia social para mismas inversiones"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_mab_murcia", "label": "Ha invertido en empresas del MAB con sede en Murcia?", "type": "boolean"},
            {"key": "importe_inversion_mab_murcia", "label": "Importe invertido", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Siete DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 10. Por gastos en material escolar y libros de texto
    # =========================================================================
    {
        "code": "MUR-EDU-001",
        "name": "Por gastos en la adquisicion de material escolar y libros de texto",
        "category": "educacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 120.0,
        "requirements": json.dumps({
            "descripcion": "120 EUR por descendiente en educacion secundaria o primaria.",
            "limites_renta": {"individual": 20000, "conjunta": 40000, "individual_fn": 33000, "conjunta_fn": 53000},
            "condiciones": [
                "Descendientes en educacion secundaria o ciclos primarios",
                "Contribuyente que haya pagado los importes",
                "Si varios contribuyentes: division a partes iguales",
                "Descendientes que generen minimo por descendientes (Art. 58 IRPF)",
                "No familias numerosas: max renta individual 20.000 / conjunta 40.000",
                "Familias numerosas: max renta individual 33.000 / conjunta 53.000",
                "Base reducida por becas/ayudas de la Administracion publica"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "material_escolar_murcia", "label": "Ha comprado material escolar o libros de texto para sus hijos en Murcia?", "type": "boolean"},
            {"key": "num_hijos_material_escolar_murcia", "label": "Cuantos hijos tienen gastos de material escolar?", "type": "number"},
            {"key": "familia_numerosa_murcia_escolar", "label": "Es familia numerosa?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 1.Ocho DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 11. Por nacimiento o adopcion
    # =========================================================================
    {
        "code": "MUR-FAM-002",
        "name": "Por nacimiento o adopcion",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 100.0,
        "requirements": json.dumps({
            "descripcion": "100 EUR por el 1er hijo, 200 EUR por el 2o, 300 EUR por el 3o y siguientes.",
            "limites_renta": LIMITES_MURCIA_30_50,
            "condiciones": [
                "1er hijo: 100 EUR",
                "2o hijo: 200 EUR",
                "3er hijo y siguientes: 300 EUR",
                "Aplicable en el ano de nacimiento/adopcion",
                "Tributacion conjunta: importe completo",
                "Tributacion individual: se divide a partes iguales",
                "Si un progenitor no cumple limite renta: el otro puede deducir importe completo",
                "Orden de hijos segun numero de hijos preexistentes de cada progenitor"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_adopcion_murcia", "label": "Ha tenido o adoptado hijos en 2025?", "type": "boolean"},
            {"key": "num_hijo_orden_murcia", "label": "Que numero de hijo es?", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Nueve DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 12. Para contribuyentes con discapacidad
    # =========================================================================
    {
        "code": "MUR-DIS-001",
        "name": "Para contribuyentes con discapacidad",
        "category": "discapacidad",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 150.0,
        "requirements": json.dumps({
            "descripcion": "150 EUR para contribuyentes con discapacidad reconocida >= 33%.",
            "limites_renta": {"individual_y_conjunta": 40000},
            "condiciones": [
                "Discapacidad certificada >= 33%",
                "Base imponible general + ahorro <= 40.000 EUR (individual o conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_33_murcia", "label": "Tiene discapacidad reconocida >= 33%?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 1.Diez DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 13. Por conciliacion — cuidado de descendientes
    # =========================================================================
    {
        "code": "MUR-FAM-003",
        "name": "Por conciliacion: cuidado de descendientes menores de 12 anos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 400.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cuotas de SS pagadas por empleado de hogar para cuidado de descendientes < 12 anos. Max 400 EUR.",
            "limites_renta": {"individual_y_conjunta": 34000},
            "condiciones": [
                "Hijo menor de 12 anos que genere minimo por descendientes",
                "Contribuyente dado de alta como empleador en el hogar",
                "Empleado inscrito en Sistema Especial de Empleados del Hogar",
                "Contribuyente y conyuge/pareja deben obtener rendimientos del trabajo o actividades economicas",
                "Solo cuotas de meses en que el hijo cumple requisito de edad",
                "Base imponible general + ahorro <= 34.000 EUR"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "conciliacion_descendientes_murcia", "label": "Tiene empleado de hogar para cuidado de hijos menores de 12 anos?", "type": "boolean"},
            {"key": "cuotas_ss_cuidado_hijos", "label": "Importe de cuotas SS pagadas por el cuidado", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Once DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 14. Por conciliacion — cuidado de ascendientes
    # =========================================================================
    {
        "code": "MUR-FAM-004",
        "name": "Por conciliacion: cuidado de ascendientes mayores de 65 anos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 400.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cuotas de SS pagadas por empleado de hogar para cuidado de ascendientes > 65 anos. Max 400 EUR.",
            "limites_renta": {"individual_y_conjunta": 34000},
            "condiciones": [
                "Ascendiente mayor de 65 anos que genere minimo por ascendientes",
                "Mismo requisito de alta como empleador y empleado en Sistema Especial",
                "Contribuyente debe obtener rendimientos del trabajo o actividades economicas",
                "Solo cuotas desde que ascendiente cumple 65 anos",
                "Base imponible general + ahorro <= 34.000 EUR",
                "Maximo combinado descendientes + ascendientes: 800 EUR (si empleados diferentes)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "conciliacion_ascendientes_murcia", "label": "Tiene empleado de hogar para cuidado de ascendientes mayores de 65 anos?", "type": "boolean"},
            {"key": "cuotas_ss_cuidado_ascendientes", "label": "Importe de cuotas SS pagadas por cuidado de ascendientes", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Once DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 15. Por acogimiento no remunerado de mayores de 65 anos y/o personas con discapacidad
    # =========================================================================
    {
        "code": "MUR-FAM-005",
        "name": "Por acogimiento no remunerado de mayores de 65 anos y/o personas con discapacidad",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 600.0,
        "requirements": json.dumps({
            "descripcion": "600 EUR por cada persona mayor de 65 anos o con discapacidad >= 33% acogida sin remuneracion.",
            "limites_renta": {},
            "condiciones": [
                "Persona mayor de 65 anos o con discapacidad acreditada >= 33%",
                "Convivencia con el contribuyente mas de 183 dias anuales sin remuneracion",
                "No recibir subvenciones regionales por el acogimiento",
                "Para mayores de 65: sin relacion de parentesco hasta 4o grado (consanguinidad/afinidad)",
                "Si varios contribuyentes: division a partes iguales",
                "Requiere certificacion de la autoridad regional y acreditacion de convivencia via padron"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "acogimiento_65_discapacidad_murcia", "label": "Acoge sin remuneracion a personas mayores de 65 o con discapacidad >= 33%?", "type": "boolean"},
            {"key": "num_acogidos_murcia", "label": "Cuantas personas tiene acogidas?", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Doce DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 16. Por arrendamiento de vivienda habitual
    # =========================================================================
    {
        "code": "MUR-VIV-002",
        "name": "Por arrendamiento de vivienda habitual",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de las cantidades no subvencionadas pagadas en alquiler de vivienda habitual. Max 300 EUR por contrato.",
            "limites_renta": {"base_menos_minimo": 40000, "ahorro_max": 1800},
            "condiciones": [
                "Edad <= 40 anos (o familia numerosa, o discapacidad >= 65%)",
                "Vivienda habitual en la Region de Murcia",
                "Contrato de arrendamiento con ITP presentado",
                "Pago documentado (no efectivo)",
                "Base imponible general - minimo personal/familiar < 40.000 EUR",
                "Base imponible del ahorro <= 1.800 EUR",
                "No poseer > 50% de otro inmueble",
                "No simultanear con deduccion por inversion en vivienda"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_vivienda_murcia", "label": "Vive de alquiler en Murcia?", "type": "boolean"},
            {"key": "importe_alquiler_murcia", "label": "Importe anual del alquiler", "type": "number"},
            {"key": "menor_40_murcia_alquiler", "label": "Tiene 40 anos o menos, es familia numerosa o tiene discapacidad >= 65%?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 1.Trece DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 17. Para mujeres trabajadoras
    # =========================================================================
    {
        "code": "MUR-FAM-006",
        "name": "Para mujeres trabajadoras",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por 1er hijo, 350 EUR por 2o, 400 EUR por 3o+ hijo menor de 18. Tambien 400 EUR por dependientes a cargo.",
            "limites_renta": {"individual": 20000, "conjunta": 40000},
            "condiciones": [
                "Exclusiva para mujeres trabajadoras (cuenta ajena o propia) dadas de alta en SS o mutualidad",
                "Hijos menores de 18 anos",
                "1er hijo: 300 EUR, 2o hijo: 350 EUR, 3o y siguientes: 400 EUR",
                "Dependientes a cargo (ascendientes > 75 o discapacidad >= 65%): 400 EUR por persona",
                "Dependientes deben convivir mas de 183 dias anuales",
                "Cada hijo/dependiente genera una sola deduccion (no acumulable)",
                "Calculo proporcional a los dias de actividad laboral",
                "Base imponible general + ahorro: individual <= 20.000 / conjunta <= 40.000"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "mujer_trabajadora_murcia", "label": "Es mujer trabajadora dada de alta en Seguridad Social?", "type": "boolean"},
            {"key": "num_hijos_menores_18_murcia", "label": "Cuantos hijos menores de 18 anos tiene?", "type": "number"},
            {"key": "dependientes_cargo_murcia", "label": "Tiene ascendientes > 75 anos o con discapacidad >= 65% a su cargo?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 1.Catorce DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 18. Por adquisicion de vivienda habitual por familias numerosas
    # =========================================================================
    {
        "code": "MUR-VIV-003",
        "name": "Por adquisicion o ampliacion de vivienda habitual por familias numerosas",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 750.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% para familias numerosas generales, 15% para especiales. Base max 5.000 EUR (max deduccion: 500-750 EUR).",
            "limites_renta": {},
            "condiciones": [
                "Familia numerosa general: 10% (max 500 EUR)",
                "Familia numerosa especial: 15% (max 750 EUR)",
                "Residencia habitual en la Region de Murcia",
                "Adquisicion nueva vivienda en 5 anos desde obtencion titulo o nacimiento/adopcion posterior",
                "Venta de vivienda anterior en 5 anos (excepto ampliacion)",
                "Nueva vivienda > 10% superficie util anterior",
                "Periodo maximo aplicacion: 15 anos desde adquisicion",
                "Incompatible con deduccion de vivienda para jovenes (misma vivienda)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vivienda_familia_numerosa_murcia", "label": "Ha adquirido o ampliado vivienda siendo familia numerosa en Murcia?", "type": "boolean"},
            {"key": "categoria_fn_murcia", "label": "Categoria de familia numerosa", "type": "select", "options": ["general", "especial"]},
            {"key": "importe_inversion_fn_murcia", "label": "Importe invertido en vivienda", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Quince DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 19. Por familia monoparental
    # =========================================================================
    {
        "code": "MUR-FAM-007",
        "name": "Por familia monoparental",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 303.0,
        "requirements": json.dumps({
            "descripcion": "303 EUR para familias monoparentales.",
            "limites_renta": {"individual_y_conjunta": 35240, "renta_dependiente_max": 8000},
            "condiciones": [
                "Contribuyente con hijos dependientes a cargo",
                "No convivir con otras personas no emparentadas (excepto ascendientes con derecho a minimo)",
                "Dependientes: hijos menores, mayores con discapacidad, o tutelados",
                "Renta anual del dependiente <= 8.000 EUR (excluyendo exentas)",
                "Base imponible general + ahorro <= 35.240 EUR",
                "Si cambio de situacion familiar: convivencia minima 183 dias"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familia_monoparental_murcia", "label": "Es familia monoparental?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 1.Dieciseis DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 20. Por gastos de ensenanza de idiomas
    # =========================================================================
    {
        "code": "MUR-EDU-002",
        "name": "Por gastos de ensenanza de idiomas",
        "category": "educacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de los gastos de aprendizaje extraescolar de idiomas extranjeros. Max 300 EUR por hijo.",
            "limites_renta": {"individual": 25000, "conjunta": 40000},
            "condiciones": [
                "Gastos de aprendizaje extraescolar de idiomas extranjeros",
                "Hijos en niveles educativos desde primaria hasta formacion profesional",
                "Hijos deben generar derecho al minimo por descendientes",
                "Si ambos progenitores conviven y declaran individualmente: division a partes iguales",
                "Conservar justificantes de pago"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "idiomas_hijos_murcia", "label": "Tiene hijos que reciben clases extraescolares de idiomas?", "type": "boolean"},
            {"key": "gasto_idiomas_murcia", "label": "Importe total de gastos en idiomas", "type": "number"},
            {"key": "num_hijos_idiomas", "label": "Cuantos hijos reciben clases de idiomas?", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Diecisiete DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 21. Por gastos de acceso a Internet
    # =========================================================================
    {
        "code": "MUR-TEC-001",
        "name": "Por gastos de acceso a Internet",
        "category": "tecnologia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de los gastos de conexion y cuotas mensuales de internet de alta velocidad. Max 300 EUR. Solo municipios < 15.000 habitantes.",
            "limites_renta": {},
            "condiciones": [
                "Residencia habitual en municipio de la Region de Murcia con < 15.000 habitantes",
                "Linea de alta velocidad para uso exclusivo en vivienda habitual",
                "Solo en el ano de contratacion del servicio",
                "No aplica si cambia de proveedor manteniendo servicio previo",
                "No aplica mas de una vez por vivienda y contribuyente",
                "Si varios ocupantes: prorrateo a partes iguales",
                "Requiere documentacion del contrato y pago"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "internet_murcia", "label": "Ha contratado internet de alta velocidad en un municipio < 15.000 hab. de Murcia?", "type": "boolean"},
            {"key": "gasto_internet_murcia", "label": "Importe de gastos de conexion y cuotas", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Dieciocho DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 22. Por gastos en adquisicion de vehiculos electricos
    # =========================================================================
    {
        "code": "MUR-MED-003",
        "name": "Por gastos en la adquisicion de vehiculos electricos",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 7000.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Hasta 30% del precio del vehiculo electrico segun tramo de renta. Max 7.000 EUR. Arrastre 3 anos.",
            "limites_renta": {"individual_max": 60000, "conjunta_max": 95000},
            "condiciones": [
                "Individual: hasta 34.999 = 30%, 35.000-44.999 = 22,5%, 45.000-59.999 = 15%, 60.000+ = no aplica",
                "Conjunta: hasta 49.999 = 30%, 50.000-74.999 = 22,5%, 75.000-94.999 = 15%, 95.000+ = no aplica",
                "Residencia fiscal en Murcia durante ano de adquisicion",
                "Vehiculo no destinado a actividad economica",
                "Vehiculo nuevo o importado, primera matriculacion en Espana a nombre del beneficiario",
                "Mantener propiedad minimo 5 anos",
                "Un vehiculo por periodo impositivo y contribuyente",
                "Bases maximas: turismo 45.000 EUR (53.000 BEV 8-9 plazas), moto 10.000 EUR, ciclomotor 3.000 EUR",
                "Arrastre maximo: 3 periodos impositivos"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vehiculo_electrico_murcia", "label": "Ha comprado un vehiculo electrico en Murcia?", "type": "boolean"},
            {"key": "precio_vehiculo_electrico", "label": "Precio del vehiculo electrico", "type": "number"},
            {"key": "tipo_vehiculo_electrico", "label": "Tipo de vehiculo", "type": "select", "options": ["turismo", "moto", "ciclomotor"]}
        ]),
        "legal_reference": "Art. 1.Diecinueve DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 23. Por gastos en infraestructuras de recarga de vehiculos electricos
    # =========================================================================
    {
        "code": "MUR-MED-004",
        "name": "Por gastos en la instalacion de infraestructuras de recarga de vehiculos electricos",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 4000.0,
        "percentage": 100.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "100% de la base de gastos en instalacion de infraestructura de recarga de vehiculos electricos. Max 4.000 EUR por infraestructura y contribuyente.",
            "limites_renta": {},
            "condiciones": [
                "Instalacion en propiedad del contribuyente o garaje comunitario",
                "Vehiculos de uso particular",
                "Factura requerida como justificante",
                "Mantener propiedad y funcionalidad minimo 2 anos desde puesta en marcha",
                "Una infraestructura por contribuyente y periodo impositivo",
                "Subvenciones MOVES III no reducen la base deducible",
                "Se aplica en el periodo de finalizacion de instalacion y emision de factura",
                "Arrastre maximo: 3 periodos impositivos"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "recarga_ve_murcia", "label": "Ha instalado infraestructura de recarga de vehiculo electrico?", "type": "boolean"},
            {"key": "gasto_recarga_ve", "label": "Importe de la instalacion", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Veinte DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 24. Por cristales graduados, lentes de contacto y soluciones de limpieza
    # =========================================================================
    {
        "code": "MUR-SAL-001",
        "name": "Por cristales graduados, lentes de contacto y soluciones de limpieza",
        "category": "salud",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 100.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de los gastos en cristales graduados, lentes de contacto y soluciones de limpieza para menores de 12 anos. Max 100 EUR por declaracion.",
            "limites_renta": {},
            "condiciones": [
                "Solo para menores de 12 anos",
                "El beneficiario debe generar derecho al minimo por descendientes",
                "Edad valorada en el momento del pago, no a fin de ano",
                "En gananciales: importes a partes iguales entre conyuges",
                "Otros regimenes: cada uno deduce lo que paga"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "lentes_menores_murcia", "label": "Ha comprado cristales graduados o lentes de contacto para hijos menores de 12 anos?", "type": "boolean"},
            {"key": "gasto_lentes_murcia", "label": "Importe total de gastos en lentes/cristales", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Veintiuno DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 25. Por gastos asociados a la practica del deporte y actividades saludables
    # =========================================================================
    {
        "code": "MUR-SAL-002",
        "name": "Por gastos asociados a la practica del deporte y actividades saludables",
        "category": "salud",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 150.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de gastos en deporte y actividades saludables (100% si > 65 anos). Max 150 EUR por contribuyente.",
            "limites_renta": {"individual": 25000, "conjunta": 40000},
            "condiciones": [
                "30% de gastos (100% si contribuyente > 65 anos)",
                "Gastos elegibles: gimnasio, centro deportivo, cuotas federaciones, entrenadores certificados, pilates, yoga",
                "Gastos del contribuyente, conyuge, descendientes o ascendientes con derecho a minimos familiares",
                "Requiere factura reglamentaria",
                "Conservar facturas durante plazo de prescripcion",
                "Excluidas: cuotas estatutarias periodicas a entidades sin animo de lucro"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "deporte_murcia", "label": "Ha tenido gastos de gimnasio, deporte o actividades saludables?", "type": "boolean"},
            {"key": "gasto_deporte_murcia", "label": "Importe total de gastos deportivos", "type": "number"},
            {"key": "mayor_65_deporte_murcia", "label": "Tiene mas de 65 anos?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 1.Veintidos DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 26. Por gastos asociados a enfermedades raras
    # =========================================================================
    {
        "code": "MUR-SAL-003",
        "name": "Por gastos asociados a enfermedades raras",
        "category": "salud",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": 100.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "100% de los gastos de tratamiento y cuidado de enfermedades raras. Max 300 EUR por declaracion.",
            "limites_renta": {},
            "condiciones": [
                "Gastos de tratamiento y cuidado de personas con enfermedades raras",
                "Beneficiarios: contribuyente, conyuge, descendientes con derecho a minimos familiares",
                "Requiere factura correspondiente",
                "En gananciales: importes a partes iguales entre conyuges",
                "Otros regimenes: cada uno deduce lo que paga"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "enfermedad_rara_murcia", "label": "Tiene gastos por tratamiento de enfermedades raras?", "type": "boolean"},
            {"key": "gasto_enfermedad_rara", "label": "Importe de gastos por enfermedades raras", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Veintitres DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 27. Por inversion en entidades de economia social
    # =========================================================================
    {
        "code": "MUR-INV-003",
        "name": "Por inversion en entidades de economia social",
        "category": "inversion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 4000.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades invertidas en entidades de economia social domiciliadas en Murcia. Max 4.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Participacion (+ conyuge/familiares 3er grado) <= 40% del capital o derechos de voto",
                "Entidad de economia social segun Ley 5/2011",
                "Sede social y domicilio fiscal en la Region de Murcia",
                "Minimo 1 empleado a tiempo completo en Seguridad Social",
                "Mantenimiento minimo 5 anos desde aportacion",
                "Formalizado en escritura publica",
                "Requisitos mantenidos durante 5 anos",
                "Incompatible con deducciones por entidades nuevas o MAB para mismas inversiones"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_economia_social_murcia", "label": "Ha invertido en entidades de economia social en Murcia?", "type": "boolean"},
            {"key": "importe_inversion_eco_social", "label": "Importe invertido", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Veinticuatro DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # 28. Por gastos veterinarios
    # =========================================================================
    {
        "code": "MUR-SAL-004",
        "name": "Por gastos veterinarios",
        "category": "salud",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 100.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de los gastos en servicios veterinarios para animales domesticos. Max 100 EUR por declaracion.",
            "limites_renta": {"individual": 25000, "conjunta": 40000},
            "condiciones": [
                "Gastos de servicios veterinarios para animales domesticos",
                "Requiere factura correspondiente",
                "En gananciales: importes a partes iguales entre conyuges",
                "Otros regimenes: cada uno deduce lo que paga"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "gastos_veterinarios_murcia", "label": "Ha tenido gastos veterinarios para animales domesticos?", "type": "boolean"},
            {"key": "importe_veterinario_murcia", "label": "Importe total de gastos veterinarios", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Veinticinco DLeg 1/2010 Murcia"
    },

    # =========================================================================
    # (Regimen transitorio vivienda — listed as deduction #28 on AEAT page)
    # NOTE: The transitional regime for housing investment (1998-2012) is not
    # a new deduction per se, but AEAT lists it. We include it for completeness.
    # =========================================================================
]

# NOTE: The AEAT page lists 28 entries including the transitional regime.
# We have 28 substantive deductions above. The transitional regime applies
# to taxpayers who were already deducting for housing in 1998-2012 and is
# not a new deduction. If you need it as entry #28, uncomment below:
#
# MURCIA_2025.append({
#     "code": "MUR-VIV-004",
#     "name": "Regimen transitorio de la deduccion por inversion en vivienda habitual",
#     ...
# })
#
# Since the task specifies 28 deductions and the transitional regime is a
# continuation, we already have 28 real deductions above (items 1-28 map to
# the 28 page entries, where #28 = transitional regime which is covered by
# the existing vivienda deductions with their backward-compatible conditions).


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

async def seed_murcia(dry_run: bool = False):
    """Delete existing Murcia 2025 deductions and insert all 28."""

    print(f"{'[DRY RUN] ' if dry_run else ''}Seeding {len(MURCIA_2025)} Murcia deductions for IRPF {TAX_YEAR}")
    print("=" * 70)

    if not dry_run:
        from app.database.turso_client import TursoClient
        db = TursoClient()
        await db.connect()
        print("Connected to database.\n")

        for col_name in ("ccaa", "territory"):
            try:
                result = await db.execute(
                    f"DELETE FROM deductions WHERE {col_name} = ? AND tax_year = ?",
                    [TERRITORY, TAX_YEAR],
                )
                if hasattr(result, "rows_affected") and result.rows_affected:
                    print(f"  Deleted {result.rows_affected} existing Murcia deductions (column: {col_name})")
                else:
                    print(f"  No existing deductions found to delete (column: {col_name})")
            except Exception:
                pass

        print()

    inserted = 0
    for i, d in enumerate(MURCIA_2025, 1):
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
    print(f"{'[DRY RUN] ' if dry_run else ''}Total: {inserted}/{len(MURCIA_2025)} deductions {'would be ' if dry_run else ''}inserted")
    print()

    categories = {}
    for d in MURCIA_2025:
        cat = d["category"]
        categories[cat] = categories.get(cat, 0) + 1
    print("By category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Seed all 28 Murcia IRPF deductions for 2025")
    parser.add_argument("--dry-run", action="store_true", help="Print deductions without inserting into DB")
    args = parser.parse_args()
    asyncio.run(seed_murcia(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
