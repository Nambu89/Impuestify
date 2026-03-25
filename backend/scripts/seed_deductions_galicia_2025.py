"""
Seed ALL 25 official Galicia autonomous deductions for IRPF 2025.

Source: AEAT Manual Practico IRPF 2025 — Comunidad Autonoma de Galicia
https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/
    irpf-2025-deducciones-autonomicas/comunidad-autonoma-galicia.html

Legal basis: Decreto Legislativo 1/2011, de 28 de julio, por el que se aprueba el
Texto Refundido de las disposiciones legales de la Comunidad Autonoma de Galicia en
materia de tributos cedidos por el Estado.

Idempotent: DELETE existing Galicia deductions for tax_year=2025, then INSERT all 25.

Usage:
    cd backend
    python scripts/seed_deductions_galicia_2025.py
    python scripts/seed_deductions_galicia_2025.py --dry-run
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

TERRITORY = "Galicia"
TAX_YEAR = 2025

# Common income limits for several Galicia deductions
LIMITES_GALICIA = {"individual": 22000, "conjunta": 31000}


# =============================================================================
# ALL 25 GALICIA DEDUCTIONS — IRPF 2025
# =============================================================================

GALICIA_2025 = [
    # =========================================================================
    # 1. Por nacimiento o adopcion de hijos
    # =========================================================================
    {
        "code": "GAL-FAM-001",
        "name": "Por nacimiento o adopcion de hijos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 2400.0,
        "percentage": None,
        "fixed_amount": 360.0,
        "requirements": json.dumps({
            "descripcion": "Deduccion escalonada por nacimiento/adopcion: 360/1.200/2.400 EUR segun orden del hijo y renta (<=22.000 EUR). 300 EUR si renta >22.000. Aplicable 3 anos (nacimiento + 2 siguientes). +20% si municipio <5.000 habitantes. Se duplica si discapacidad >= 33%.",
            "limites_renta": {"baja": 22000, "media": 31000},
            "condiciones": [
                "Ano nacimiento/adopcion: 1er hijo 360 EUR, 2o hijo 1.200 EUR, 3o+ hijo 2.400 EUR (renta <= 22.000)",
                "Renta > 22.000: 300 EUR por hijo",
                "2 anos siguientes: mismos importes si renta <= 22.000; 300 EUR si renta 22.000-31.000",
                "Incremento 20% para residentes en municipios < 5.000 habitantes",
                "Importes duplicados si hijo tiene discapacidad >= 33%",
                "Convivencia requerida a 31 de diciembre",
                "Si ambos progenitores conviven: division al 50%",
                "Renta = base imponible total menos minimo personal y familiar"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_adopcion_galicia", "label": "Ha tenido o adoptado hijos en 2025 (o en 2023/2024)?", "type": "boolean"},
            {"key": "num_hijo_orden_galicia", "label": "Que numero de hijo es (1o, 2o, 3o...)?", "type": "number"},
            {"key": "municipio_pequeno_galicia", "label": "Reside en un municipio de menos de 5.000 habitantes?", "type": "boolean"},
            {"key": "hijo_discapacidad_33_galicia", "label": "El hijo tiene discapacidad >= 33%?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 5 DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 2. Para familias con dos hijos
    # =========================================================================
    {
        "code": "GAL-FAM-002",
        "name": "Para familias con dos hijos e hijas",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 500.0,
        "percentage": None,
        "fixed_amount": 250.0,
        "requirements": json.dumps({
            "descripcion": "250 EUR para familias con 2 hijos que generen derecho al minimo por descendientes. 500 EUR si contribuyente o hijo tiene discapacidad >= 65%.",
            "limites_renta": {},
            "condiciones": [
                "Familias con exactamente 2 hijos que generen minimo por descendientes",
                "250 EUR importe base",
                "500 EUR si contribuyente o hijo tiene discapacidad >= 65%",
                "Si varios contribuyentes: division a partes iguales",
                "Incompatible con deduccion por familia numerosa"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familia_2_hijos_galicia", "label": "Tiene exactamente 2 hijos que generen minimo por descendientes?", "type": "boolean"},
            {"key": "discapacidad_65_familia_galicia", "label": "Usted o algun hijo tiene discapacidad >= 65%?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 5.Tres.1 DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 3. Por familia numerosa
    # =========================================================================
    {
        "code": "GAL-FAM-003",
        "name": "Por familia numerosa",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 250.0,
        "requirements": json.dumps({
            "descripcion": "Categoria general (hasta 2 hijos): 250 EUR. Especial (hasta 2 hijos): 400 EUR. +250 EUR por cada hijo a partir del 3o. Se duplica si contribuyente o descendiente tiene discapacidad >= 65%.",
            "limites_renta": {},
            "condiciones": [
                "Titulo de familia numerosa vigente a fecha de devengo",
                "General (hasta 2 hijos): 250 EUR",
                "Especial (hasta 2 hijos): 400 EUR",
                "+250 EUR por cada hijo adicional (3o, 4o, etc.)",
                "Se duplica si contribuyente o descendiente tiene discapacidad >= 65%",
                "Clasificacion segun Ley 40/2003",
                "Si varios contribuyentes: prorrateo a partes iguales",
                "Incompatible con deduccion para familias con 2 hijos"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familia_numerosa_galicia", "label": "Tiene titulo de familia numerosa?", "type": "boolean"},
            {"key": "categoria_fn_galicia", "label": "Categoria de familia numerosa", "type": "select", "options": ["general", "especial"]},
            {"key": "num_hijos_fn_galicia", "label": "Numero total de hijos", "type": "number"},
            {"key": "discapacidad_65_fn_galicia", "label": "Usted o algun descendiente tiene discapacidad >= 65%?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 5.Tres.2 DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 4. Por acogimiento de menores
    # =========================================================================
    {
        "code": "GAL-FAM-004",
        "name": "Por acogimiento de menores",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por cada menor en acogimiento familiar simple, permanente, provisional o preadoptivo formalizado por la Xunta de Galicia.",
            "limites_renta": {},
            "condiciones": [
                "Menores en acogimiento familiar (simple, permanente, provisional, preadoptivo)",
                "Formalizado por la autoridad competente de la Xunta de Galicia",
                "No aplica si se produce adopcion en el periodo impositivo",
                "En matrimonios o parejas de hecho: division a partes iguales en declaraciones individuales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "acogimiento_menores_galicia", "label": "Tiene menores en acogimiento familiar en Galicia?", "type": "boolean"},
            {"key": "num_menores_acogidos_galicia", "label": "Cuantos menores tiene en acogimiento?", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Cuatro DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 5. Por cuidado de hijos menores
    # =========================================================================
    {
        "code": "GAL-FAM-005",
        "name": "Por cuidado de hijos menores",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 600.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de las cantidades pagadas por cuidado de hijos <= 3 anos. Maximo 400 EUR (1 hijo) o 600 EUR (2+ hijos).",
            "limites_renta": LIMITES_GALICIA,
            "condiciones": [
                "Ambos progenitores deben trabajar (cuenta ajena o propia) y estar dados de alta en SS",
                "Hijos de 3 anos o menos a 31 de diciembre",
                "Cuidado por empleado de hogar (dado de alta en Sistema Especial) o guarderia autorizada (0-3 anos)",
                "Max 400 EUR con 1 hijo <= 3 anos",
                "Max 600 EUR con 2+ hijos <= 3 anos",
                "Division proporcional entre contribuyentes con derecho"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "cuidado_hijos_menores_galicia", "label": "Tiene hijos de 3 anos o menos en guarderia o con empleado de hogar?", "type": "boolean"},
            {"key": "num_hijos_3_galicia", "label": "Cuantos hijos de 3 anos o menos tiene?", "type": "number"},
            {"key": "gasto_cuidado_hijos", "label": "Importe pagado por cuidado de hijos menores", "type": "number"},
            {"key": "ambos_trabajan_galicia", "label": "Ambos progenitores trabajan y estan dados de alta en SS?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 5.Cinco DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 6. Por contribuyentes con discapacidad >= 65 anos que necesiten ayuda de terceros
    # =========================================================================
    {
        "code": "GAL-DIS-001",
        "name": "Por contribuyentes con discapacidad, de edad igual o superior a 65 anos, que precisen ayuda de terceras personas",
        "category": "discapacidad",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 600.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de las cantidades pagadas a terceras personas por contribuyentes con discapacidad >= 65% y >= 65 anos. Maximo 600 EUR.",
            "limites_renta": LIMITES_GALICIA,
            "condiciones": [
                "Edad >= 65 anos",
                "Discapacidad >= 65% (o incapacidad judicial, dependencia severa/gran dependencia)",
                "Acreditar necesidad de ayuda de terceras personas",
                "No puede residir en centro publico o concertado de Galicia",
                "Maximo 600 EUR de deduccion"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_65_mayor65_galicia", "label": "Tiene >= 65 anos y discapacidad >= 65% que requiera ayuda de terceros?", "type": "boolean"},
            {"key": "gasto_ayuda_terceros", "label": "Importe pagado a terceras personas por ayuda", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Seis DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 7. Por alquiler de vivienda habitual
    # =========================================================================
    {
        "code": "GAL-VIV-001",
        "name": "Por alquiler de la vivienda habitual",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 600.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% del alquiler de vivienda habitual (20% con 2+ hijos menores). Max 300 EUR (600 EUR con hijos menores). Se duplica para discapacidad >= 33%.",
            "limites_renta": {"individual": 22000, "conjunta": 22000},
            "condiciones": [
                "Edad <= 35 anos a 31 de diciembre (tributacion conjunta: al menos un conyuge)",
                "10% del alquiler; 20% si 2+ hijos menores dependientes",
                "Max 300 EUR por contrato (600 EUR con hijos menores)",
                "Se duplica para personas con discapacidad >= 33%",
                "Contrato posterior a 1 de enero de 2003",
                "Fianza depositada en Instituto Gallego de Vivienda",
                "Base imponible general + ahorro <= 22.000 EUR"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_vivienda_galicia", "label": "Vive de alquiler en Galicia?", "type": "boolean"},
            {"key": "importe_alquiler_galicia", "label": "Importe anual del alquiler", "type": "number"},
            {"key": "menor_35_galicia", "label": "Tiene 35 anos o menos?", "type": "boolean"},
            {"key": "hijos_menores_2_galicia", "label": "Tiene 2 o mas hijos menores dependientes?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 5.Siete DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 8. Por gastos dirigidos al uso de nuevas tecnologias en hogares gallegos
    # =========================================================================
    {
        "code": "GAL-TEC-001",
        "name": "Por gastos dirigidos al uso de nuevas tecnologias en hogares gallegos",
        "category": "tecnologia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 100.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de los gastos de conexion y cuotas mensuales de acceso a internet de alta velocidad. Maximo 100 EUR (50 EUR por conyuge en gananciales).",
            "limites_renta": {},
            "condiciones": [
                "Solo aplicable en el ano de contratacion del servicio",
                "Linea destinada exclusivamente al hogar (no actividad profesional)",
                "No aplica si cambia de proveedor manteniendo contrato previo",
                "En gananciales: maximo 50 EUR por conyuge",
                "Requiere justificacion documental"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "internet_alta_velocidad_galicia", "label": "Ha contratado internet de alta velocidad en su hogar gallego en 2025?", "type": "boolean"},
            {"key": "gasto_internet_galicia", "label": "Importe de gastos de conexion y cuotas de internet", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Ocho DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 9. Por inversion en acciones/participaciones de entidades nuevas o reciente creacion
    # =========================================================================
    {
        "code": "GAL-INV-001",
        "name": "Por inversion en adquisicion de acciones o participaciones sociales de entidades nuevas o de reciente creacion",
        "category": "inversion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 9000.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de las cantidades invertidas (max 6.000 EUR). +15% adicional para PYME innovadoras, empresas de base tecnologica o con participacion universitaria (max 9.000 EUR).",
            "limites_renta": {},
            "condiciones": [
                "30% de cantidades invertidas, max 6.000 EUR",
                "+15% adicional para PYME innovadoras/base tecnologica/participacion universitaria (max 9.000 EUR)",
                "Participacion entre 1% y 40% del capital",
                "Entidad domiciliada en Galicia durante 3+ anos",
                "Actividad economica (no gestion patrimonio)",
                "Minimo 1 empleado a tiempo completo residente en Galicia durante 3+ anos",
                "Mantenimiento minimo 3 anos",
                "Formalizado en escritura publica",
                "Incompatible con otras deducciones autonomicas de inversion"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_empresa_nueva_galicia", "label": "Ha invertido en empresas nuevas o de reciente creacion en Galicia?", "type": "boolean"},
            {"key": "importe_inversion_galicia", "label": "Importe total invertido", "type": "number"},
            {"key": "empresa_innovadora_galicia", "label": "Es PYME innovadora, empresa de base tecnologica o con participacion universitaria?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 5.Nueve DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 10. Por inversion en acciones/participaciones y financiacion de entidades nuevas
    # =========================================================================
    {
        "code": "GAL-INV-002",
        "name": "Por inversion en adquisicion de acciones o participaciones sociales de entidades nuevas o de reciente creacion y su financiacion",
        "category": "inversion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 35000.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de las cantidades invertidas (max 20.000 EUR). +15% adicional para PYME innovadoras (max 35.000 EUR).",
            "limites_renta": {},
            "condiciones": [
                "30% de cantidades invertidas, max 20.000 EUR",
                "+15% adicional para PYME innovadoras/base tecnologica/participacion universitaria (max 35.000 EUR)",
                "Participacion entre 1% y 40% del capital",
                "Entidad domiciliada en Galicia con actividad durante 3 anos",
                "No gestion de patrimonio",
                "Minimo 1 empleado a tiempo completo",
                "Mantenimiento minimo 3 anos; escritura publica",
                "No ejercer funciones ejecutivas durante 10 anos",
                "Incompatible con otras deducciones autonomicas de inversion"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_financiacion_galicia", "label": "Ha invertido o financiado empresas nuevas en Galicia (adquisicion + prestamos)?", "type": "boolean"},
            {"key": "importe_inversion_financiacion", "label": "Importe total invertido y/o financiado", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Diez DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 11. Por inversion en acciones de entidades cotizadas en segmento de expansion del MAB
    # =========================================================================
    {
        "code": "GAL-INV-003",
        "name": "Por inversion en acciones de entidades que cotizan en el segmento de empresas en expansion del mercado alternativo bursatil",
        "category": "inversion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 4000.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades invertidas en acciones de entidades cotizadas en el segmento de expansion del MAB. Max 4.000 EUR. Deduccion repartida en 4 anos.",
            "limites_renta": {},
            "condiciones": [
                "Participacion no superior al 10% del capital",
                "Mantenimiento minimo 3 anos",
                "Entidad domiciliada en Galicia",
                "No gestion de patrimonio como actividad principal",
                "Formalizado en escritura publica",
                "Deduccion distribuida a partes iguales en 4 periodos impositivos (inversion + 3 siguientes)",
                "Incompatible con otras deducciones autonomicas de inversion para las mismas cantidades"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_mab_galicia", "label": "Ha invertido en empresas cotizadas en el MAB con sede en Galicia?", "type": "boolean"},
            {"key": "importe_inversion_mab", "label": "Importe invertido en acciones del MAB", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Once DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 12. Por donaciones con finalidad de investigacion y desarrollo cientifico
    # =========================================================================
    {
        "code": "GAL-DON-001",
        "name": "Por donaciones con finalidad de investigacion y desarrollo cientifico e innovacion tecnologica",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 25.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "25% de las donaciones dinerarias a centros de investigacion gallegos o entidades sin animo de lucro de I+D+i. Limite: 10% de la cuota integra autonomica.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias",
                "Destinatarios: centros de investigacion vinculados a universidades gallegas o promovidos por la Xunta",
                "O entidades sin animo de lucro calificadas como organismos de investigacion (Reglamento UE 651/2014)",
                "Limite: 10% de la cuota integra autonomica del IRPF",
                "Requiere justificacion documental adecuada"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_investigacion_galicia", "label": "Ha donado a centros de investigacion o entidades de I+D en Galicia?", "type": "boolean"},
            {"key": "importe_donacion_investigacion", "label": "Importe total donado para investigacion", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Doce DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 13. Por inversion en instalaciones de climatizacion y/o agua caliente con renovables
    # =========================================================================
    {
        "code": "GAL-VIV-002",
        "name": "Por inversion en instalaciones de climatizacion y/o agua caliente sanitaria que empleen energias renovables",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 280.0,
        "percentage": 5.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "5% de las cantidades invertidas en instalaciones de climatizacion/ACS con renovables en vivienda habitual. Max 280 EUR por contribuyente.",
            "limites_renta": {},
            "condiciones": [
                "Instalacion registrada por instalador autorizado en OVI (Oficina Virtual de Industria)",
                "Pagos mediante tarjeta, transferencia o cheque nominativo (no efectivo)",
                "Presupuesto detallado, factura, justificante pago requeridos",
                "En comunidades: certificacion de aportacion individual",
                "Energias renovables segun Directiva UE 2009/28/CE",
                "Codigo OVI en casilla 1033 de la declaracion",
                "Incompatible con deducciones de eficiencia energetica o rehabilitacion para mismas cantidades"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "renovables_climatizacion_galicia", "label": "Ha instalado sistemas de climatizacion o ACS con renovables en su vivienda?", "type": "boolean"},
            {"key": "importe_renovables", "label": "Importe de la instalacion de renovables", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Trece DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 14. Por rehabilitacion de inmuebles situados en centros historicos
    # =========================================================================
    {
        "code": "GAL-VIV-003",
        "name": "Por rehabilitacion de bienes inmuebles situados en centros historicos",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 9000.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades invertidas en rehabilitacion de inmuebles en centros historicos de Galicia. Max 9.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Inmueble propiedad del contribuyente en centro historico designado",
                "Obras con permisos y autorizaciones administrativas",
                "Rehabilitacion: consolidacion y tratamiento de estructuras, fachadas o cubiertas",
                "Coste total > 25% del precio de adquisicion (ultimos 2 anos) o valor de mercado",
                "Excluido valor del suelo del calculo",
                "Certificado municipal acreditando ubicacion en centro historico",
                "Deduccion atribuida al pagador independientemente del regimen matrimonial",
                "Se aplica en el ejercicio de pago"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "rehabilitacion_centro_historico_galicia", "label": "Ha rehabilitado un inmueble en un centro historico de Galicia?", "type": "boolean"},
            {"key": "importe_rehabilitacion_ch", "label": "Importe invertido en la rehabilitacion", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Catorce DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 15. Por inversion en empresas agrarias
    # =========================================================================
    {
        "code": "GAL-INV-004",
        "name": "Por inversion en empresas que desarrollen actividades agrarias",
        "category": "inversion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 20000.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades invertidas en empresas agrarias de Galicia. Max 20.000 EUR de deduccion conjunta.",
            "limites_renta": {},
            "condiciones": [
                "Formalizado en escritura publica",
                "Mantenimiento minimo 5 anos desde formalizacion",
                "Financiacion: vencimiento >= 5 anos con amortizacion anual max 20%",
                "No ejercer funciones directivas durante 10 anos",
                "Sin relacion laboral con la entidad (excepto cooperativas de trabajo)",
                "Aplicable a adquisicion de capital, prestamos y participaciones agrarias",
                "Incompatible con otras deducciones autonomicas de inversion para mismas cantidades"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_agraria_galicia", "label": "Ha invertido en empresas agrarias en Galicia?", "type": "boolean"},
            {"key": "importe_inversion_agraria", "label": "Importe invertido en empresa agraria", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Quince DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 16. Por subvenciones/ayudas por danos forestales (PEIFOGA 2025)
    # =========================================================================
    {
        "code": "GAL-OTR-001",
        "name": "Por subvenciones y ayudas obtenidas por danos causados por incendios forestales",
        "category": "otros",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Deduccion equivalente a aplicar los tipos medios de gravamen al importe de subvenciones/ayudas por incendios forestales integradas en la base imponible general.",
            "limites_renta": {},
            "condiciones": [
                "El contribuyente debe integrar la subvencion en la base imponible general",
                "Ayuda procedente de la Administracion autonómica gallega",
                "Incluida en Decreto 76/2025 de ayudas de emergencia por incendios forestales en Galicia (verano/otono 2025)",
                "Deduccion = tipo medio de gravamen x importe de la ayuda"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "ayuda_incendio_forestal_galicia", "label": "Ha recibido ayudas por danos de incendios forestales en Galicia en 2025?", "type": "boolean"},
            {"key": "importe_ayuda_forestal", "label": "Importe de la subvencion/ayuda recibida", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Dieciseis DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 17. Por obras de mejora de eficiencia energetica en edificios y viviendas
    # =========================================================================
    {
        "code": "GAL-VIV-004",
        "name": "Por obras de mejora de eficiencia energetica en edificios residenciales y viviendas unifamiliares",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 9000.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades invertidas en mejora de eficiencia energetica (max 9.000 EUR). Ademas, 100% del coste del certificado energetico (max 150 EUR).",
            "limites_renta": {},
            "condiciones": [
                "Edificios residenciales o viviendas unifamiliares propiedad del contribuyente",
                "Permisos y autorizaciones administrativas requeridos",
                "Mejora de al menos una letra en calificacion energetica (emisiones CO2 o energia primaria no renovable)",
                "Pagos: tarjeta, transferencia, cheque nominativo o deposito bancario (no efectivo)",
                "Certificado energetico registrado en Registro de Certificados de Eficiencia Energetica de Galicia",
                "Informe tecnico confirmando mejora de letra",
                "100% del coste de certificados y registro (max 150 EUR, prorrateado por titularidad)",
                "Incompatible con deducciones de renovables o aldeas modelo para mismas cantidades"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "eficiencia_energetica_galicia", "label": "Ha realizado obras de mejora de eficiencia energetica en su vivienda en Galicia?", "type": "boolean"},
            {"key": "importe_eficiencia_energetica", "label": "Importe invertido en mejora energetica", "type": "number"},
            {"key": "mejora_letra_energetica", "label": "Las obras mejoran al menos una letra en la calificacion energetica?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 5.Dieciocho DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 18. Por ayudas y subvenciones recibidas por deportistas de alto nivel
    # =========================================================================
    {
        "code": "GAL-OTR-002",
        "name": "Por ayudas y subvenciones recibidas por deportistas de alto nivel de Galicia",
        "category": "otros",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Deduccion equivalente a aplicar los tipos medios de gravamen al importe de ayudas deportivas integradas en la base imponible general.",
            "limites_renta": {},
            "condiciones": [
                "La subvencion debe proceder de la Administracion publica gallega o del sector publico autonomico",
                "Destinada al desarrollo de actividad deportiva",
                "La actividad deportiva no puede generar rendimientos de actividades economicas",
                "El contribuyente debe tener reconocimiento oficial como deportista de alto nivel por la autoridad deportiva gallega",
                "Deduccion = tipo medio de gravamen x importe de la ayuda"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "deportista_alto_nivel_galicia", "label": "Es deportista de alto nivel reconocido en Galicia?", "type": "boolean"},
            {"key": "ayuda_deportiva_galicia", "label": "Importe de ayudas deportivas recibidas de la Xunta", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Diecinueve DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 19. Por adquisicion/rehabilitacion de viviendas en proyectos de aldeas modelo
    # =========================================================================
    {
        "code": "GAL-VIV-005",
        "name": "Por adquisicion y rehabilitacion de viviendas en proyectos de aldeas modelo",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 9000.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades invertidas en adquisicion/rehabilitacion de viviendas en aldeas modelo. Max 9.000 EUR (vivienda habitual) o 4.500 EUR (otras).",
            "limites_renta": {},
            "condiciones": [
                "Viviendas adquiridas/rehabilitadas desde 1 de enero de 2021",
                "Ubicadas en proyectos de aldeas modelo segun Ley 11/2021",
                "Destinadas a residencia del contribuyente (habitual u ocasional)",
                "Rehabilitacion: coste > 25% del precio de adquisicion o valor de mercado",
                "Requiere permisos/autorizaciones administrativas",
                "Vivienda habitual: max 9.000 EUR",
                "Otros usos: max 4.500 EUR",
                "Incompatible con deducciones de renovables o eficiencia energetica para mismas cantidades"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "aldea_modelo_galicia", "label": "Ha adquirido o rehabilitado vivienda en una aldea modelo de Galicia?", "type": "boolean"},
            {"key": "importe_aldea_modelo", "label": "Importe invertido", "type": "number"},
            {"key": "vivienda_habitual_aldea", "label": "Es su vivienda habitual?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 5.Veinte DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 20. Por inversion en proyectos de especial interes publico, social o economico
    # =========================================================================
    {
        "code": "GAL-INV-005",
        "name": "Por inversion en adquisicion de acciones o participaciones sociales en proyectos de especial interes publico, social o economico",
        "category": "inversion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 10000.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades invertidas en entidades con proyectos de especial interes publico. Max 10.000 EUR por entidad (acumulado en todos los periodos).",
            "limites_renta": {},
            "condiciones": [
                "Inversion en acciones/participaciones por constitucion o ampliacion de capital",
                "Objeto social exclusivo: realizacion de proyectos de especial interes publico, social o economico",
                "Proyectos segun Ley 2/2024, arts. 17 y 20",
                "Incluye proyectos de energias renovables con criterios especificos",
                "Max 10.000 EUR por entidad independientemente del numero de periodos",
                "Incompatible con otras deducciones regionales para mismas inversiones"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_interes_publico_galicia", "label": "Ha invertido en entidades con proyectos de especial interes publico en Galicia?", "type": "boolean"},
            {"key": "importe_inversion_publico", "label": "Importe invertido", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Veintiuno DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 21. Por gastos de adecuacion de inmueble vacio para arrendamiento
    # =========================================================================
    {
        "code": "GAL-VIV-006",
        "name": "Por gastos derivados de la adecuacion de un inmueble vacio destinado al arrendamiento como vivienda",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 9000.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de los gastos de adecuacion de inmueble vacio para alquiler como vivienda. Base max 9.000 EUR por inmueble (3.000 EUR/ano con 2 anos de arrastre). Caso especial 2-3 inmuebles: 6.000 EUR/ano con 4 anos arrastre.",
            "limites_renta": {},
            "condiciones": [
                "Inmueble en Galicia",
                "Vacio al menos 1 ano antes del inicio de obras",
                "Obras completadas en 2 anos",
                "Arrendamiento en 6 meses desde finalizacion",
                "Duracion minima arrendamiento: 3 anos (o equivalente por renovaciones)",
                "Valor inmueble <= 250.000 EUR",
                "Inquilino no puede ser conyuge o pariente hasta 3er grado",
                "Maximo 3 inmuebles en arrendamiento",
                "Gastos: reparacion, certificacion energetica, formalizacion, tasacion, suministros, publicidad"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "adecuacion_inmueble_vacio_galicia", "label": "Ha adecuado un inmueble vacio para alquiler como vivienda en Galicia?", "type": "boolean"},
            {"key": "importe_adecuacion_vacio", "label": "Importe de los gastos de adecuacion", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Veintidos DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 22. Por arrendamiento de viviendas vacias
    # =========================================================================
    {
        "code": "GAL-VIV-007",
        "name": "Por el arrendamiento de viviendas vacias",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por cada inmueble vacio puesto en el mercado de alquiler. Solo en el primer periodo impositivo de arrendamiento.",
            "limites_renta": {},
            "condiciones": [
                "Inmueble en Galicia",
                "Vacio al menos 1 ano antes del contrato de arrendamiento",
                "Duracion minima del contrato: 3 anos",
                "Inquilino no puede ser conyuge o pariente hasta 3er grado",
                "Renta mensual maxima: 700 EUR (excluidos incrementos anuales)",
                "Maximo 3 inmuebles en arrendamiento por propietario/usufructuario",
                "Prorrateo por porcentaje de titularidad",
                "Solo en el primer periodo impositivo de puesta en alquiler"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_vivienda_vacia_galicia", "label": "Ha puesto en alquiler una vivienda vacia en Galicia por primera vez?", "type": "boolean"},
            {"key": "num_viviendas_vacias_alquiler", "label": "Cuantas viviendas vacias ha puesto en alquiler?", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Veintitres DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 23. Por ayudas a personas con diagnostico de ELA
    # =========================================================================
    {
        "code": "GAL-OTR-003",
        "name": "Por ayudas y subvenciones recibidas por personas con diagnostico de esclerosis lateral amiotrofica (ELA)",
        "category": "otros",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Deduccion equivalente a aplicar los tipos medios de gravamen al importe de ayudas por ELA integradas en la base imponible general.",
            "limites_renta": {},
            "condiciones": [
                "El contribuyente debe integrar la ayuda publica en la base imponible general",
                "Ayuda destinada especificamente a personas con diagnostico de ELA o sus fenotipos",
                "Deduccion = tipo medio de gravamen x importe de la ayuda"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "ayuda_ela_galicia", "label": "Ha recibido ayudas publicas por diagnostico de ELA?", "type": "boolean"},
            {"key": "importe_ayuda_ela", "label": "Importe de la ayuda recibida", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Veinticuatro DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 24. Por adquisicion de libros de texto y material escolar
    # =========================================================================
    {
        "code": "GAL-EDU-001",
        "name": "Por la adquisicion de libros de texto y material escolar",
        "category": "educacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades pagadas en libros de texto y material escolar. Max 105 EUR por hijo matriculado. Renta familiar per capita <= 30.000 EUR.",
            "limites_renta": {"renta_per_capita_familiar": 30000},
            "condiciones": [
                "Hijos matriculados en centros sostenidos con fondos publicos",
                "Solo Educacion Primaria, ESO y Educacion Especial",
                "Compras entre 1 julio y 31 diciembre de 2025",
                "Pago: tarjeta, transferencia, cheque o plataformas electronicas (efectivo excepcionalmente en 2025)",
                "Hijo debe generar minimo por descendientes (salvo que pague el progenitor sin derecho)",
                "Renta familiar per capita <= 30.000 EUR (renta 2024 / miembros computables)",
                "Incompatible con becas publicas para material escolar del mismo curso"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "libros_texto_galicia", "label": "Ha comprado libros de texto o material escolar en Galicia?", "type": "boolean"},
            {"key": "num_hijos_material_escolar", "label": "Cuantos hijos tienen gastos de material escolar?", "type": "number"},
            {"key": "importe_material_escolar", "label": "Importe total de libros y material escolar", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Veinticinco DLeg 1/2011 Galicia"
    },

    # =========================================================================
    # 25. Por ayudas a personas afectadas por talidomida (1950-1985)
    # =========================================================================
    {
        "code": "GAL-OTR-004",
        "name": "Por ayudas recibidas por personas afectadas por la talidomida en Espana durante el periodo 1950-1985",
        "category": "otros",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Deduccion equivalente a aplicar los tipos medios de gravamen al importe de ayudas por talidomida integradas en la base imponible general.",
            "limites_renta": {},
            "condiciones": [
                "El contribuyente debe incluir la ayuda publica en la base imponible general",
                "Ayuda destinada a personas afectadas por talidomida en Espana (1950-1985)",
                "Deduccion = tipo medio de gravamen x importe de la ayuda",
                "Aplicable a ayudas recibidas e incluidas en bases imponibles generales desde 2023 en adelante",
                "Para 2023-2024: posibilidad de rectificar autoliquidaciones (casilla 1038, Anexo B.5)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "ayuda_talidomida_galicia", "label": "Ha recibido ayudas publicas como afectado por talidomida?", "type": "boolean"},
            {"key": "importe_ayuda_talidomida", "label": "Importe de la ayuda recibida", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Veintiseis DLeg 1/2011 Galicia"
    },
]


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

async def seed_galicia(dry_run: bool = False):
    """Delete existing Galicia 2025 deductions and insert all 25."""

    print(f"{'[DRY RUN] ' if dry_run else ''}Seeding {len(GALICIA_2025)} Galicia deductions for IRPF {TAX_YEAR}")
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
                    print(f"  Deleted {result.rows_affected} existing Galicia deductions (column: {col_name})")
                else:
                    print(f"  No existing deductions found to delete (column: {col_name})")
            except Exception:
                pass

        print()

    inserted = 0
    for i, d in enumerate(GALICIA_2025, 1):
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
    print(f"{'[DRY RUN] ' if dry_run else ''}Total: {inserted}/{len(GALICIA_2025)} deductions {'would be ' if dry_run else ''}inserted")
    print()

    categories = {}
    for d in GALICIA_2025:
        cat = d["category"]
        categories[cat] = categories.get(cat, 0) + 1
    print("By category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Seed all 25 Galicia IRPF deductions for 2025")
    parser.add_argument("--dry-run", action="store_true", help="Print deductions without inserting into DB")
    args = parser.parse_args()
    asyncio.run(seed_galicia(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
