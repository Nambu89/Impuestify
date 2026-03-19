"""
URL registry — all monitored documents organized by territory and priority.

Sources: 12 crawl sessions (docs/_inventario.md), docscrawler.md URLs, AEAT portals.
"""
from dataclasses import dataclass, field


@dataclass
class WatchItem:
    url: str
    dest: str                           # Relative to docs/
    file_type: str = "pdf"              # pdf, xlsx, xls
    priority: str = "high"              # high, medium, low
    territory: str = ""
    description: str = ""
    status: str = "active"              # active, future, html_only, deprecated
    pattern: str = ""                   # URL template for future docs
    notes: str = ""                     # Audit notes (TIPO A/B/C/D classification)


# ═══════════════════════════════════════════════════════════════
# AEAT — Agencia Tributaria Estatal
# ═══════════════════════════════════════════════════════════════

AEAT_BASE = "https://sede.agenciatributaria.gob.es/static_files/Sede/Biblioteca"

AEAT_ITEMS = [
    # ── Manuales Practicos (alta prioridad, actualizacion anual) ──
    WatchItem(
        url=f"{AEAT_BASE}/Manual/Practicos/Renta/IRPF/IRPF-2025/ManualRenta2025Tomo1_es_es.pdf",
        dest="AEAT/IRPF/AEAT-Manual_Practico_IRPF_2025_Tomo1.pdf",
        territory="AEAT",
        description="Manual Practico Renta 2025 Tomo 1 (previsto ~marzo 2026)",
        status="future",
        pattern="{BASE}/Manual/Practicos/Renta/IRPF/IRPF-{year}/ManualRenta{year}Tomo1_es_es.pdf",
    ),
    WatchItem(
        url=f"{AEAT_BASE}/Manual/Practicos/Renta/IRPF/IRPF-2025/ManualRenta2025Tomo2_es_es.pdf",
        dest="AEAT/IRPF/AEAT-Manual_Practico_IRPF_2025_Tomo2.pdf",
        territory="AEAT",
        description="Manual Practico Renta 2025 Tomo 2 Ded. Autonomicas",
        status="future",
    ),
    WatchItem(
        url=f"{AEAT_BASE}/Manual/Practicos/IVA/Manual_IVA.pdf",
        dest="AEAT/IVA/AEAT-Manual_Practico_IVA_2025.pdf",
        territory="AEAT",
        description="Manual Practico IVA (actualizacion anual)",
    ),
    WatchItem(
        url=f"{AEAT_BASE}/Manual/Practicos/Sociedades/Manual_Sociedades_2024.pdf",
        dest="AEAT/Sociedades/AEAT-Manual_Practico_Sociedades_2024.pdf",
        territory="AEAT",
        description="Manual Practico Sociedades 2024",
    ),
    WatchItem(
        url=f"{AEAT_BASE}/Manual/Practicos/Patrimonio/Patrimonio-2024/ManualPatrimonio2024_es_es.pdf",
        dest="AEAT/Patrimonio/AEAT-Manual_Practico_Patrimonio_2024.pdf",
        territory="AEAT",
        description="Manual Practico Patrimonio 2024",
    ),

    # ── Retenciones IRPF ──
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/static_files/Sede/Programas_Ayuda/Retenciones/2025/Cuadro_tipos_retenciones_2025.pdf",
        dest="AEAT/IRPF/AEAT-Cuadro_tipos_retenciones_IRPF_2025.pdf",
        territory="AEAT",
        description="Cuadro tipos retenciones IRPF 2025",
        status="future",
        notes="Pendiente publicacion AEAT en sede.agenciatributaria.gob.es",
    ),
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/static_files/Sede/Programas_Ayuda/Retenciones/2026/Cuadro_tipos_retenciones_2026.pdf",
        dest="AEAT/IRPF/AEAT-Cuadro_tipos_retenciones_IRPF_2026.pdf",
        territory="AEAT",
        description="Cuadro tipos retenciones IRPF 2026",
        status="future",
        notes="Pendiente publicacion AEAT",
    ),

    # ── Algoritmo retenciones ──
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/static_files/Sede/Programas_Ayuda/Retenciones/2025/Algoritmo_2025.pdf",
        dest="AEAT/IRPF/AEAT-Algoritmo_2025.pdf",
        territory="AEAT",
        description="Algoritmo retenciones IRPF 2025",
        status="future",
        notes="Pendiente publicacion AEAT",
    ),
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/static_files/Sede/Programas_Ayuda/Retenciones/2026/Algoritmo_2026.pdf",
        dest="AEAT/IRPF/AEAT-Algoritmo_2026.pdf",
        territory="AEAT",
        description="Algoritmo retenciones IRPF 2026",
        status="future",
        notes="Pendiente publicacion AEAT",
    ),

    # ── Instrucciones Modelos ──
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/static_files/Sede/Programas_Ayuda/Modelo303/2025/Instrucciones_Modelo303_2025.pdf",
        dest="AEAT/Modelos/AEAT-Modelo303_IVA_Instrucciones_2025.pdf",
        territory="AEAT",
        description="Instrucciones Modelo 303 IVA 2025",
        status="future",
        notes="Pendiente publicacion AEAT",
    ),
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/static_files/Sede/Programas_Ayuda/Modelo390/2025/Instrucciones_Modelo390_2025.pdf",
        dest="AEAT/Modelos/AEAT-Modelo390_IVA_Instrucciones_2025.pdf",
        territory="AEAT",
        description="Instrucciones Modelo 390 IVA 2025",
        status="future",
        notes="Pendiente publicacion AEAT",
    ),
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/static_files/Sede/Programas_Ayuda/Modelo190/Instrucciones_Modelo190.pdf",
        dest="AEAT/Modelos/AEAT-Modelo190_Retenciones_Instrucciones.pdf",
        territory="AEAT",
        description="Instrucciones Modelo 190 retenciones",
        status="future",
        notes="Pendiente publicacion AEAT en pagina actualizada",
    ),
]


# ═══════════════════════════════════════════════════════════════
# BOE — Legislacion Estatal
# ═══════════════════════════════════════════════════════════════

BOE_ITEMS = [
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2006/BOE-A-2006-20764-consolidado.pdf",
        dest="Estatal/BOE/Estatal-Ley_35_2006_IRPF_consolidado.pdf",
        territory="Estatal",
        description="Ley 35/2006 IRPF consolidado",
    ),
    WatchItem(
        url="https://www.boe.es/buscar/pdf/1992/BOE-A-1992-28740-consolidado.pdf",
        dest="Estatal/BOE/Estatal-Ley_37_1992_IVA_consolidado.pdf",
        territory="Estatal",
        description="Ley 37/1992 IVA consolidado",
    ),
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2014/BOE-A-2014-12328-consolidado.pdf",
        dest="Estatal/BOE/Estatal-Ley_27_2014_IS_consolidado.pdf",
        territory="Estatal",
        description="Ley 27/2014 IS consolidado",
    ),
    WatchItem(
        url="https://www.boe.es/buscar/pdf/1987/BOE-A-1987-28141-consolidado.pdf",
        dest="Estatal/BOE/Estatal-Ley_29_1987_ISD_consolidado.pdf",
        territory="Estatal",
        description="Ley 29/1987 ISD consolidado",
    ),
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2003/BOE-A-2003-23186-consolidado.pdf",
        dest="Estatal/LeyGeneralTributaria/Estatal-Ley_58_2003_LGT_consolidado.pdf",
        territory="Estatal",
        description="Ley 58/2003 LGT consolidado",
    ),
    WatchItem(
        url="https://www.boe.es/buscar/pdf/1991/BOE-A-1991-28191-consolidado.pdf",
        dest="Estatal/BOE/Estatal-Ley_19_1991_Patrimonio_consolidado.pdf",
        territory="Estatal",
        description="Ley 19/1991 Patrimonio consolidado",
        status="future",
        notes="TIPO B: URL verificada pero PDF consolidado no disponible. Alternativa: /boe/dias/1991/12/06/pdfs/A37801-37801.pdf (publicacion original, no consolidada)",
    ),
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2007/BOE-A-2007-9364-consolidado.pdf",
        dest="Estatal/RealesDecretos/Estatal-RD_439_2007_ReglamentoIRPF_consolidado.pdf",
        territory="Estatal",
        description="RD 439/2007 Reglamento IRPF consolidado",
        status="future",
        notes="TIPO B: URL consolidada no disponible en BOE. Alternativa: /boe/dias/2007/05/12/pdfs/ (publicacion original)",
    ),
    WatchItem(
        url="https://www.boe.es/buscar/pdf/1992/BOE-A-1992-28925-consolidado.pdf",
        dest="Estatal/RealesDecretos/Estatal-RD_1624_1992_ReglamentoIVA_consolidado.pdf",
        territory="Estatal",
        description="RD 1624/1992 Reglamento IVA consolidado",
    ),
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2015/BOE-A-2015-8147-consolidado.pdf",
        dest="Estatal/RealesDecretos/Estatal-RD_634_2015_ReglamentoIS_consolidado.pdf",
        territory="Estatal",
        description="RD 634/2015 Reglamento IS consolidado",
    ),
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2007/BOE-A-2007-13409-consolidado.pdf",
        dest="Estatal/BOE/Estatal-Ley_20_2007_EstatutoAutonomo_consolidado.pdf",
        territory="Estatal",
        description="Ley 20/2007 Estatuto Autonomo consolidado",
        priority="medium",
    ),
    WatchItem(
        url="https://www.boe.es/buscar/pdf/1991/BOE-A-1991-29631-consolidado.pdf",
        dest="Estatal/RealesDecretos/Estatal-RD_1629_1991_ReglamentoISD_consolidado.pdf",
        territory="Estatal",
        description="RD 1629/1991 Reglamento ISD consolidado",
        priority="medium",
    ),
]


# ═══════════════════════════════════════════════════════════════
# AEAT Disenos de Registro
# ═══════════════════════════════════════════════════════════════

AEAT_DR_BASE = "https://sede.agenciatributaria.gob.es/static_files/Sede/Disenyo_registro"

AEAT_DR_ITEMS = [
    WatchItem(
        url=f"{AEAT_DR_BASE}/DR303_e2026.xlsx",
        dest="AEAT/DisenosRegistro/DR303_e2026.xlsx",
        file_type="xlsx",
        territory="AEAT",
        description="Diseno Registro Modelo 303 IVA 2026",
        priority="medium",
        status="future",
        notes="TIPO A: Pendiente publicacion AEAT para ejercicio 2026",
    ),
    WatchItem(
        url=f"{AEAT_DR_BASE}/DR390_e2025.xlsx",
        dest="AEAT/DisenosRegistro/DR390_e2025.xlsx",
        file_type="xlsx",
        territory="AEAT",
        description="Diseno Registro Modelo 390 IVA 2025",
        priority="medium",
        status="future",
        notes="TIPO A: Pendiente publicacion AEAT para ejercicio 2025",
    ),
    WatchItem(
        url=f"{AEAT_DR_BASE}/DR130_e2019.xls",
        dest="AEAT/DisenosRegistro/DR130_e2019.xls",
        file_type="xls",
        territory="AEAT",
        description="Diseno Registro Modelo 130 pagos fraccionados",
        priority="low",
        status="future",
        notes="TIPO A: Historico (2019). Buscar version actualizada 2025 o posterior",
    ),
    WatchItem(
        url=f"{AEAT_DR_BASE}/DR131_e2025.xlsx",
        dest="AEAT/DisenosRegistro/DR131_e2025.xlsx",
        file_type="xlsx",
        territory="AEAT",
        description="Diseno Registro Modelo 131 modulos",
        priority="low",
        status="future",
        notes="TIPO A: Pendiente publicacion AEAT para ejercicio 2025",
    ),
]


# ═══════════════════════════════════════════════════════════════
# Navarra
# ═══════════════════════════════════════════════════════════════

NAVARRA_ITEMS = [
    WatchItem(
        url="https://www.navarra.es/es/documents/48192/17863227/Manual+te%C3%B3rico+de+la+campa%C3%B1a+de+2024.pdf",
        dest="Navarra/IRPF/Navarra-Manual_teorico_IRPF_2024.pdf",
        territory="Navarra",
        description="Manual teorico IRPF Navarra 2024",
        status="future",
        notes="TIPO B: URL da error 500. Comprobar portal Hacienda Navarra para actualizacion anual (2025)",
    ),
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2016/BOE-A-2016-11953-consolidado.pdf",
        dest="Navarra/IS/Navarra-LeyForal_26_2016_IS_consolidado.pdf",
        territory="Navarra",
        description="LF 26/2016 IS Navarra consolidado",
        priority="medium",
    ),
]


# ═══════════════════════════════════════════════════════════════
# Bizkaia
# ═══════════════════════════════════════════════════════════════

BIZKAIA_ITEMS = [
    WatchItem(
        url="https://www.bizkaia.eus/fitxategiak/4/Ogasuna/Manual_Renta_Patrimonio_2024.pdf",
        dest="Bizkaia/IRPF/Bizkaia-Manual_Renta_Patrimonio_2024.pdf",
        territory="Bizkaia",
        description="Manual Renta/Patrimonio Bizkaia 2024",
        status="future",
        notes="TIPO B: URL da error 404. Buscar manual actualizado 2025 en portal Hacienda Bizkaia",
    ),
]


# ═══════════════════════════════════════════════════════════════
# Gipuzkoa
# ═══════════════════════════════════════════════════════════════

GIPUZKOA_ITEMS = [
    WatchItem(
        url="https://www.gipuzkoa.eus/documents/2456431/0/Manual+Divulgacion+Renta+2024.pdf",
        dest="Gipuzkoa/IRPF/Gipuzkoa-Manual_Divulgacion_Renta2024.pdf",
        territory="Gipuzkoa",
        description="Manual Divulgacion Renta Gipuzkoa 2024",
        status="future",
        notes="TIPO B: URL da error 404. Buscar en portal Hacienda Gipuzkoa version 2025",
    ),
]


# ═══════════════════════════════════════════════════════════════
# Araba
# ═══════════════════════════════════════════════════════════════

ARABA_ITEMS = [
    WatchItem(
        url="https://web.araba.eus/documents/105044/0/Manual+Renta+2024.pdf",
        dest="Araba/IRPF/Araba-Manual_Renta_2024.pdf",
        territory="Araba",
        description="Manual Renta Araba 2024",
        status="future",
        notes="TIPO B: URL da error 404. Buscar en portal Hacienda Araba version 2025",
    ),
]


# ═══════════════════════════════════════════════════════════════
# CCAA Regimen Comun — Textos consolidados BOE
# ═══════════════════════════════════════════════════════════════

CCAA_ITEMS = [
    # Andalucia
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2021/BOE-A-2021-20796-consolidado.pdf",
        dest="Andalucia/Andalucia-Ley_5_2021_TributosCedidos_consolidado.pdf",
        territory="Andalucia",
        description="Andalucia Ley 5/2021 tributos cedidos consolidado",
        priority="medium",
        status="future",
        notes="TIPO A/B: PDF consolidado puede no estar disponible. Verificar en sede BOE",
    ),
    # Aragon
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2005/BOE-A-2005-20647-consolidado.pdf",
        dest="Aragon/Aragon-DLeg_1_2005_TributosCedidos_consolidado.pdf",
        territory="Aragon",
        description="Aragon DLeg 1/2005 tributos cedidos consolidado",
        priority="medium",
        status="future",
        notes="TIPO A/B: PDF consolidado puede no estar disponible en BOE",
    ),
    # Asturias
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2014/BOE-A-2014-12730-consolidado.pdf",
        dest="Asturias/Asturias-DLeg_2_2014_TributosCedidos_consolidado.pdf",
        territory="Asturias",
        description="Asturias DLeg 2/2014 tributos cedidos consolidado",
        priority="medium",
        status="future",
        notes="TIPO A/B: PDF consolidado puede no estar disponible en BOE",
    ),
    # Baleares
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2014/BOE-A-2014-7235-consolidado.pdf",
        dest="Baleares/Baleares-DLeg_1_2014_TributosCedidos_consolidado.pdf",
        territory="Baleares",
        description="Baleares DLeg 1/2014 tributos cedidos consolidado",
        priority="medium",
        status="future",
        notes="TIPO A/B: PDF consolidado puede no estar disponible en BOE",
    ),
    # Canarias
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2009/BOE-A-2009-11432-consolidado.pdf",
        dest="Canarias/Canarias-DLeg_1_2009_TributosCedidos_consolidado.pdf",
        territory="Canarias",
        description="Canarias DLeg 1/2009 tributos cedidos consolidado",
        priority="medium",
        status="future",
        notes="TIPO A/B: PDF consolidado puede no estar disponible en BOE",
    ),
    # Cantabria
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2008/BOE-A-2008-20587-consolidado.pdf",
        dest="Cantabria/Cantabria-DLeg_62_2008_TributosCedidos_consolidado.pdf",
        territory="Cantabria",
        description="Cantabria DLeg 62/2008 tributos cedidos consolidado",
        priority="medium",
        status="future",
        notes="TIPO A/B: PDF consolidado puede no estar disponible en BOE",
    ),
    # Castilla-La Mancha
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2013/BOE-A-2013-13919-consolidado.pdf",
        dest="CastillaLaMancha/CastillaLaMancha-Ley_8_2013_MedidasTributarias_consolidado.pdf",
        territory="CastillaLaMancha",
        description="CLM Ley 8/2013 medidas tributarias consolidado",
        priority="low",
        status="future",
        notes="TIPO A/B: PDF consolidado puede no estar disponible en BOE",
    ),
    # Castilla y Leon
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2013/BOE-A-2013-10937-consolidado.pdf",
        dest="CastillaYLeon/CastillaYLeon-DLeg_1_2013_TributosCedidos_consolidado.pdf",
        territory="CastillaYLeon",
        description="CyL DLeg 1/2013 tributos cedidos consolidado",
        priority="medium",
        status="future",
        notes="TIPO A/B: PDF consolidado puede no estar disponible en BOE",
    ),
    # Cataluna
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2024/BOE-A-2024-16710-consolidado.pdf",
        dest="Cataluna/Cataluna-DLeg_1_2024_LibroSextoCodigoTributario_TributosCedidos.pdf",
        territory="Cataluna",
        description="Cataluna DLeg 1/2024 Libro Sexto tributos cedidos",
        priority="medium",
        status="future",
        notes="TIPO A/B: PDF consolidado puede no estar disponible en BOE",
    ),
    # Extremadura
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2018/BOE-A-2018-16799-consolidado.pdf",
        dest="Extremadura/Extremadura-DLeg_1_2018_TributosCedidos_consolidado.pdf",
        territory="Extremadura",
        description="Extremadura DLeg 1/2018 tributos cedidos consolidado",
        priority="medium",
        status="future",
        notes="TIPO A/B: PDF consolidado puede no estar disponible en BOE",
    ),
    # Galicia
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2011/BOE-A-2011-17966-consolidado.pdf",
        dest="Galicia/Galicia-DLeg_1_2011_TributosCedidos_consolidado.pdf",
        territory="Galicia",
        description="Galicia DLeg 1/2011 tributos cedidos consolidado",
        priority="medium",
        status="future",
        notes="TIPO A/B: PDF consolidado puede no estar disponible en BOE",
    ),
    # La Rioja
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2017/BOE-A-2017-14705-consolidado.pdf",
        dest="LaRioja/LaRioja-Ley_10_2017_TributosCedidos_consolidado.pdf",
        territory="LaRioja",
        description="La Rioja Ley 10/2017 tributos cedidos consolidado",
        priority="medium",
        status="future",
        notes="TIPO A/B: PDF consolidado puede no estar disponible en BOE",
    ),
    # Madrid
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2010/BOE-A-2010-18472-consolidado.pdf",
        dest="Madrid/Madrid-DLeg_1_2010_TributosCedidos_consolidado.pdf",
        territory="Madrid",
        description="Madrid DLeg 1/2010 tributos cedidos consolidado",
        priority="medium",
        status="future",
        notes="TIPO A/B: PDF consolidado puede no estar disponible en BOE",
    ),
    # Murcia
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2010/BOE-A-2010-12261-consolidado.pdf",
        dest="Murcia/Murcia-DLeg_1_2010_TributosCedidos_consolidado.pdf",
        territory="Murcia",
        description="Murcia DLeg 1/2010 tributos cedidos consolidado",
        priority="medium",
        status="future",
        notes="TIPO A/B: PDF consolidado puede no estar disponible en BOE",
    ),
    # Valencia
    WatchItem(
        url="https://www.boe.es/boe/dias/1997/02/13/pdfs/A04860-04870.pdf",
        dest="Valencia/Valencia-Ley_13_1997_TributosCedidos.pdf",
        territory="Valencia",
        description="Valencia Ley 13/1997 tributos cedidos consolidado",
        priority="medium",
        status="future",
        notes="TIPO B: URL de dias historica. Buscar consolidado en sede BOE actual",
    ),
]


# ═══════════════════════════════════════════════════════════════
# Ceuta y Melilla — IPSI y Estatutos
# ═══════════════════════════════════════════════════════════════

CEUTA_MELILLA_ITEMS = [
    # Ceuta — IPSI (Ley 8/1991)
    WatchItem(
        url="https://www.boe.es/boe/dias/1991/11/21/pdfs/A37801-37801.pdf",
        dest="Ceuta/Ceuta-Ley_8_1991_IPSI_Ceuta_consolidado.pdf",
        territory="Ceuta",
        description="Ley 8/1991 IPSI Ceuta consolidado",
        priority="medium",
        status="future",
        notes="TIPO B: URL de publicacion original (1991). Buscar consolidado en BOE act.php",
    ),
    # Melilla — IPSI (Ley 13/1996, art. 40+)
    WatchItem(
        url="https://www.boe.es/buscar/pdf/1996/BOE-A-1996-29117-consolidado.pdf",
        dest="Melilla/Melilla-Ley_13_1996_IPSI_Melilla_consolidado.pdf",
        territory="Melilla",
        description="Ley 13/1996 IPSI Melilla (Titulo II) consolidado",
        priority="medium",
        status="future",
        notes="TIPO A/B: PDF consolidado puede no estar disponible en BOE",
    ),
    # Ceuta — Estatuto de Autonomia
    WatchItem(
        url="https://www.boe.es/boe/dias/1995/03/02/pdfs/A06847-06854.pdf",
        dest="Ceuta/Ceuta-Ley_Organica_1_1995_Estatuto_consolidado.pdf",
        territory="Ceuta",
        description="Estatuto Autonomia Ceuta consolidado",
        priority="low",
        status="future",
        notes="TIPO B: URL de publicacion original (1995). Buscar consolidado en BOE act.php",
    ),
    # Melilla — Estatuto de Autonomia
    WatchItem(
        url="https://www.boe.es/boe/dias/1995/03/02/pdfs/A06854-06861.pdf",
        dest="Melilla/Melilla-Ley_Organica_2_1995_Estatuto_consolidado.pdf",
        territory="Melilla",
        description="Estatuto Autonomia Melilla consolidado",
        priority="low",
        status="future",
        notes="TIPO B: URL de publicacion original (1995). Buscar consolidado en BOE act.php",
    ),
]


# ═══════════════════════════════════════════════════════════════
# Canarias — IGIC y REF
# ═══════════════════════════════════════════════════════════════

CANARIAS_EXTRA_ITEMS = [
    # IGIC — Ley 20/1991 (equivalente IVA en Canarias)
    WatchItem(
        url="https://www.boe.es/buscar/pdf/1991/BOE-A-1991-14463-consolidado.pdf",
        dest="Canarias/Canarias-Ley_20_1991_IGIC_consolidado.pdf",
        territory="Canarias",
        description="Ley 20/1991 IGIC Canarias consolidado",
        status="future",
        notes="TIPO A/B: PDF consolidado puede no estar disponible en BOE",
    ),
    # REF Canarias — Ley 19/1994 (Regimen Economico Fiscal)
    WatchItem(
        url="https://www.boe.es/boe/dias/1994/07/15/pdfs/A23024-23084.pdf",
        dest="Canarias/Canarias-Ley_19_1994_REF_consolidado.pdf",
        territory="Canarias",
        description="Ley 19/1994 REF Canarias consolidado",
        priority="medium",
        status="future",
        notes="TIPO B: URL de publicacion original (1994). Buscar consolidado en BOE act.php",
    ),
]


# ═══════════════════════════════════════════════════════════════
# Seguridad Social
# ═══════════════════════════════════════════════════════════════

SS_ITEMS = [
    WatchItem(
        url="https://www.seg-social.es/descargacontents/ficheros/afiliacion/tablas_cotizacion_2025/tablas_cotizacion_autonomos_reta_2025.pdf",
        dest="Estatal/SegSocial/SS-Tabla_Cotizacion_Autonomos_RETA_2025.pdf",
        territory="Estatal",
        description="Tabla cotizacion RETA 2025",
        priority="low",
        status="future",
        notes="TIPO B: URL estructura cambio. Buscar en portal Seguridad Social versión actualizada",
    ),
]


# ═══════════════════════════════════════════════════════════════
# Creadores de Contenido / Emprendedores Digitales
# ═══════════════════════════════════════════════════════════════

CREATORS_ITEMS = [
    # ── Estatuto del Trabajo Autonomo (base legal autonomos/emprendedores) ──
    # Ya en BOE_ITEMS como Ley 20/2007 — no duplicar

    # ── Ley de Emprendedores ──
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2013/BOE-A-2013-10074-consolidado.pdf",
        dest="Estatal/Emprendedores/Estatal-Ley_14_2013_Emprendedores_consolidado.pdf",
        territory="Estatal",
        description="Ley 14/2013 de apoyo a emprendedores consolidado",
    ),

    # ── Ley Startups (Ley 28/2022 Crea y Crece) ──
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2022/BOE-A-2022-21739-consolidado.pdf",
        dest="Estatal/Emprendedores/Estatal-Ley_28_2022_Startups_consolidado.pdf",
        territory="Estatal",
        description="Ley 28/2022 startups y emprendimiento consolidado",
    ),

    # ── Ley Crea y Crece (facturacion electronica obligatoria) ──
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2022/BOE-A-2022-15818-consolidado.pdf",
        dest="Estatal/Emprendedores/Estatal-Ley_18_2022_CreaYCrece_consolidado.pdf",
        territory="Estatal",
        description="Ley 18/2022 Crea y Crece (facturacion electronica) consolidado",
    ),

    # ── Modelo 720 — Declaracion bienes en el extranjero ──
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/static_files/Sede/Programas_Ayuda/Modelo720/Instrucciones_Modelo720.pdf",
        dest="AEAT/Modelos/AEAT-Modelo720_BienesExtranjero_Instrucciones.pdf",
        territory="AEAT",
        description="Instrucciones Modelo 720 bienes en el extranjero",
        priority="high",
        status="future",
        notes="TIPO A: Pendiente publicacion AEAT en pagina actualizada",
    ),

    # ── Modelo 349 — Operaciones intracomunitarias (facturacion a Google/Meta/ByteDance) ──
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/static_files/Sede/Programas_Ayuda/Modelo349/Instrucciones_Modelo349.pdf",
        dest="AEAT/Modelos/AEAT-Modelo349_OperacionesIntracomunitarias_Instrucciones.pdf",
        territory="AEAT",
        description="Instrucciones Modelo 349 operaciones intracomunitarias",
        priority="high",
        status="future",
        notes="TIPO A: Pendiente publicacion AEAT en pagina actualizada",
    ),

    # ── Modelo 036/037 — Alta censal autonomos / IAE ──
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/static_files/Sede/Programas_Ayuda/Modelo036_037/Instrucciones_Modelo036.pdf",
        dest="AEAT/Modelos/AEAT-Modelo036_AltaCensal_Instrucciones.pdf",
        territory="AEAT",
        description="Instrucciones Modelo 036 alta censal / IAE",
        priority="high",
        status="future",
        notes="TIPO A: Pendiente publicacion AEAT en pagina actualizada",
    ),

    # ── Convenios doble imposicion (principales para plataformas digitales) ──
    # Irlanda (Google, Meta, Apple)
    WatchItem(
        url="https://www.boe.es/boe/dias/1994/03/18/pdfs/A08736-08753.pdf",
        dest="Estatal/ConveniosDI/Estatal-CDI_Espana_Irlanda_consolidado.pdf",
        territory="Estatal",
        description="Convenio doble imposicion Espana-Irlanda (Google, Meta, Apple)",
        priority="high",
        status="future",
        notes="TIPO B: URL de publicacion original (1994). Buscar consolidado en BOE act.php",
    ),
    # Paises Bajos (Booking, Adyen)
    WatchItem(
        url="https://www.boe.es/boe/dias/1972/03/30/pdfs/A06066-06084.pdf",
        dest="Estatal/ConveniosDI/Estatal-CDI_Espana_PaisesBajos_consolidado.pdf",
        territory="Estatal",
        description="Convenio doble imposicion Espana-Paises Bajos",
        priority="medium",
        status="future",
        notes="TIPO B: URL de publicacion original (1972). Buscar consolidado en BOE act.php",
    ),
    # Reino Unido (ByteDance/TikTok, Twitch)
    WatchItem(
        url="https://www.boe.es/boe/dias/2014/06/10/pdfs/BOE-A-2014-6268.pdf",
        dest="Estatal/ConveniosDI/Estatal-CDI_Espana_ReinoUnido_consolidado.pdf",
        territory="Estatal",
        description="Convenio doble imposicion Espana-Reino Unido (TikTok, Twitch)",
        priority="high",
        status="future",
        notes="TIPO B: URL de publicacion original (2014). Buscar consolidado en BOE act.php",
    ),
    # EEUU (YouTube/Google US, Amazon/Twitch)
    WatchItem(
        url="https://www.boe.es/boe/dias/1990/12/28/pdfs/A38893-38911.pdf",
        dest="Estatal/ConveniosDI/Estatal-CDI_Espana_EEUU_consolidado.pdf",
        territory="Estatal",
        description="Convenio doble imposicion Espana-EEUU (YouTube, Amazon, Twitch)",
        priority="high",
        status="future",
        notes="TIPO B: URL de publicacion original (1990). Buscar consolidado en BOE act.php",
    ),

    # ── Reglamento VeriFactu (facturacion electronica obligatoria) ──
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2024/BOE-A-2024-22138-consolidado.pdf",
        dest="Estatal/VeriFactu/Estatal-RD_1007_2023_VeriFactu_Reglamento_consolidado.pdf",
        territory="Estatal",
        description="RD 1007/2023 Reglamento VeriFactu facturacion electronica consolidado",
        priority="medium",
        status="future",
        notes="TIPO A/B: PDF consolidado puede no estar disponible en BOE",
    ),

    # ── IAE — Tarifas (epigrafes para creadores de contenido) ──
    WatchItem(
        url="https://www.boe.es/buscar/pdf/1990/BOE-A-1990-23930-consolidado.pdf",
        dest="Estatal/IAE/Estatal-RDLeg_1175_1990_Tarifas_IAE_consolidado.pdf",
        territory="Estatal",
        description="RDLeg 1175/1990 Tarifas IAE consolidado (epigrafes creadores)",
        priority="high",
    ),

    # ── Ley IVA servicios digitales / reglas de localizacion ──
    # Ya en BOE_ITEMS como Ley 37/1992 — no duplicar

    # ── Canarias — ZEC para emprendedores digitales ──
    WatchItem(
        url="https://www.boe.es/boe/dias/2000/02/02/pdfs/A04206-04224.pdf",
        dest="Canarias/ZEC/Canarias-RD_2_2000_ZEC_Reglamento_consolidado.pdf",
        territory="Canarias",
        description="RD 2/2000 Reglamento ZEC Canarias consolidado",
        priority="medium",
        status="future",
        notes="TIPO B: URL de publicacion original (2000). Buscar consolidado en BOE act.php",
    ),
]


# ═══════════════════════════════════════════════════════════════
# Influencers / Creadores de Contenido — Normativa especifica
# Estructura: docs/Influencers/{territorio}/
# ═══════════════════════════════════════════════════════════════

INFLUENCERS_ITEMS = [
    # ── Estatal: Ley General Comunicacion Audiovisual (regula influencers) ──
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2022/BOE-A-2022-11789-consolidado.pdf",
        dest="Influencers/Estatal/Influencers-Ley_13_2022_Comunicacion_Audiovisual_consolidado.pdf",
        territory="Estatal",
        description="Ley 13/2022 General Comunicacion Audiovisual (regula influencers)",
        priority="high",
        status="future",
        notes="TIPO A/B: PDF consolidado puede no estar disponible en BOE",
    ),
    # ── RD 444/2024 desarrollo Ley Audiovisual (obligaciones influencers) ──
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2024/BOE-A-2024-8716-consolidado.pdf",
        dest="Influencers/Estatal/Influencers-RD_444_2024_DesarrolloLeyAudiovisual_consolidado.pdf",
        territory="Estatal",
        description="RD 444/2024 desarrollo Ley Audiovisual (obligaciones influencers)",
        priority="high",
    ),
    # ── CNAE-2025 (nuevo codigo 60.39 para creadores) ──
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2025/BOE-A-2025-587-consolidado.pdf",
        dest="Influencers/Estatal/Influencers-RD_10_2025_CNAE2025_consolidado.pdf",
        territory="Estatal",
        description="RD 10/2025 CNAE-2025 (nuevo codigo 60.39 creadores contenido)",
        priority="high",
    ),
    # ── Plan Tributario AEAT 2026 (influencers como objetivo) ──
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2026/BOE-A-2026-5082-consolidado.pdf",
        dest="Influencers/Estatal/Influencers-Resolucion_AEAT_PlanTributario_2026.pdf",
        territory="Estatal",
        description="Plan Tributario AEAT 2026 (influencers objetivo prioritario)",
        priority="high",
        status="future",
        notes="TIPO A: PDF para ano futuro (2026) puede no estar publicado aun",
    ),
    # ── DAC7 / Modelo 238 (plataformas reportan ingresos creadores) ──
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2023/BOE-A-2023-24843-consolidado.pdf",
        dest="Influencers/Estatal/Influencers-RD_1065_2023_DAC7_Modelo238_consolidado.pdf",
        territory="Estatal",
        description="RD 1065/2007 mod. DAC7 Modelo 238 (plataformas reportan ingresos)",
        priority="high",
        status="future",
        notes="TIPO A/B: PDF consolidado puede no estar disponible en BOE",
    ),

    # ── Forales: guias autonomos / creadores ──
    # Bizkaia — Manual autonomos
    WatchItem(
        url="https://www.bizkaia.eus/fitxategiak/4/Ogasuna/Guia_actividades_economicas.pdf",
        dest="Influencers/Bizkaia/Influencers-Bizkaia_Guia_Actividades_Economicas.pdf",
        territory="Bizkaia",
        description="Bizkaia guia actividades economicas (IAE foral, autonomos, creadores)",
        priority="high",
        status="future",
        notes="TIPO B: URL da error 404. Buscar version actualizada en portal Bizkaia Hacienda",
    ),
    # Gipuzkoa — Guia autonomos
    WatchItem(
        url="https://www.gipuzkoa.eus/documents/2456431/0/Guia+fiscal+autonomos.pdf",
        dest="Influencers/Gipuzkoa/Influencers-Gipuzkoa_Guia_Fiscal_Autonomos.pdf",
        territory="Gipuzkoa",
        description="Gipuzkoa guia fiscal autonomos (aplicable a creadores)",
        priority="high",
        status="future",
        notes="TIPO B: URL da error 404. Buscar version actualizada en portal Gipuzkoa Hacienda",
    ),
    # Araba — Guia autonomos
    WatchItem(
        url="https://web.araba.eus/documents/105044/0/Guia+fiscal+actividades+economicas.pdf",
        dest="Influencers/Araba/Influencers-Araba_Guia_Fiscal_Actividades_Economicas.pdf",
        territory="Araba",
        description="Araba guia fiscal actividades economicas (IAE foral, creadores)",
        priority="high",
        status="future",
        notes="TIPO B: URL da error 404. Buscar version actualizada en portal Araba Hacienda",
    ),
    # Navarra — Autonomos actividades economicas
    WatchItem(
        url="https://www.navarra.es/documents/48192/17863227/Guia+para+iniciar+una+actividad+economica.pdf",
        dest="Influencers/Navarra/Influencers-Navarra_Guia_Iniciar_Actividad_Economica.pdf",
        territory="Navarra",
        description="Navarra guia inicio actividad economica (autonomos, creadores)",
        priority="high",
        status="future",
        notes="TIPO B: URL da error 404. Buscar version actualizada en portal Navarra Hacienda",
    ),

    # ── Canarias: REF + ZEC para emprendedores digitales ──
    WatchItem(
        url="https://www3.gobiernodecanarias.org/hacienda/portal/recursos/ref.pdf",
        dest="Influencers/Canarias/Influencers-Canarias_Guia_REF_Fiscal.pdf",
        territory="Canarias",
        description="Canarias guia REF fiscal (ventajas emprendedores digitales)",
        priority="high",
        status="future",
        notes="TIPO B: URL da error 404. Buscar guia REF en portal Gobierno Canarias",
    ),

    # ── CCAA: Guias autonomos / emprendedores de haciendas autonomicas ──
    # Madrid — Guia autonomos
    WatchItem(
        url="https://www.comunidad.madrid/sites/default/files/doc/hacienda/guia_fiscal_autonomos.pdf",
        dest="Influencers/Madrid/Influencers-Madrid_Guia_Emprendedores.pdf",
        territory="Madrid",
        description="Madrid guia emprendedores (deducciones autoempleo, creadores)",
        priority="medium",
        status="future",
        notes="TIPO B: URL da error 404. Buscar guia en portal Hacienda Madrid",
    ),
    # Cataluna — Guia autonomos (TIPO D: bloqueado por robots.txt)
    WatchItem(
        url="https://www20.gencat.cat/portal/site/economia/menuitem.8b47ae3e67cf14001faec10bb3ba0e0e/?vgnextoid=db0f4a3cda42f610VgnVCM1000008d0c1e0aRCRD&vgnextchannel=db0f4a3cda42f610VgnVCM1000008d0c1e0aRCRD",
        dest="Influencers/Cataluna/Influencers-Cataluna_Guia_Fiscal_Emprendedores.pdf",
        territory="Cataluna",
        description="Cataluna guia fiscal emprendedores",
        priority="medium",
        status="future",
        notes="TIPO D: Bloqueado por robots.txt del dominio. Contactar directamente Gencat",
    ),
    # Andalucia — Incentivos autonomos
    WatchItem(
        url="https://www.juntadeandalucia.es/hacienda/portal/publicaciones/guias",
        dest="Influencers/Andalucia/Influencers-Andalucia_Guia_Incentivos_Autonomos.pdf",
        territory="Andalucia",
        description="Andalucia guia incentivos autonomos (deducciones autoempleo)",
        priority="medium",
        status="future",
        notes="TIPO B: URL da error 404. Buscar guia en portal Junta Andalucia Hacienda",
    ),
    # Valencia — Guia fiscal autonomos
    WatchItem(
        url="https://www.gva.es/es/web/hacienda/publicaciones",
        dest="Influencers/Valencia/Influencers-Valencia_Guia_Fiscal_Autonomos.pdf",
        territory="Valencia",
        description="Valencia guia fiscal autonomos",
        priority="medium",
        status="future",
        notes="TIPO B: Validation failed. Buscar guia PDF en portal Generalitat Valencia",
    ),

    # ── Ceuta y Melilla: IPSI para actividades digitales ──
    WatchItem(
        url="https://www.tributosceuta.org/publicaciones",
        dest="Influencers/Ceuta/Influencers-Ceuta_IPSI_Guia_Actividades.pdf",
        territory="Ceuta",
        description="Ceuta IPSI guia actividades (creadores digitales)",
        priority="medium",
        status="future",
        notes="TIPO B: URL da error 404. Buscar guia en portal Tributos Ceuta",
    ),

    # ── Articulos/guias de referencia (HTML→PDF no viable, status html_only) ──
    # AEAT — Regimenes estimacion directa
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/Sede/irpf/empresarios-individuales-profesionales/regimenes-determinar-rendimiento-actividad.html",
        dest="Influencers/Estatal/AEAT-Regimenes_Estimacion_Directa_Autonomos.html",
        territory="Estatal",
        description="AEAT regimenes estimacion directa autonomos (ref para creadores)",
        priority="high",
        status="html_only",
    ),
    # AEAT — Modelo 349 operaciones intracomunitarias
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/Sede/iva/operadores-intracomunitarios/modelo349.html",
        dest="Influencers/Estatal/AEAT-Modelo349_Intracomunitarias_Info.html",
        territory="Estatal",
        description="AEAT info Modelo 349 (creadores facturan a Google/Meta Ireland)",
        priority="high",
        status="html_only",
    ),
]


# ═══════════════════════════════════════════════════════════════
# Modelos fiscales especificos creadores — forales + Canarias
# ═══════════════════════════════════════════════════════════════

CREATOR_MODELS_ITEMS = [
    # ── Gipuzkoa: Modelo 300 (equivalente al 303) ──
    WatchItem(
        url="https://www.gipuzkoa.eus/documents/2456431/0/Modelo+300+instrucciones.pdf",
        dest="Influencers/Gipuzkoa/Influencers-Gipuzkoa_Modelo300_IVA_Instrucciones.pdf",
        territory="Gipuzkoa",
        description="Gipuzkoa Modelo 300 IVA trimestral (equivalente al 303 estatal)",
        priority="high",
    ),
    # ── Navarra: F69 (equivalente al 303) ──
    WatchItem(
        url="http://www.navarra.es/appsext/impresos/instrucciones/INSTRF69.PDF",
        dest="Influencers/Navarra/Influencers-Navarra_F69_IVA_Instrucciones.pdf",
        territory="Navarra",
        description="Navarra F69 IVA trimestral (equivalente al 303 estatal)",
        priority="high",
    ),
    # ── Canarias: Modelo 420 IGIC ──
    WatchItem(
        url="https://sede.gobiernodecanarias.org/sede/descargar/11825",
        dest="Influencers/Canarias/Influencers-Canarias_Modelo420_IGIC_Instrucciones.pdf",
        territory="Canarias",
        description="Canarias Modelo 420 IGIC trimestral (equivalente al 303/IVA)",
        priority="high",
    ),
    # ── Modelo 721 Criptomonedas extranjero ──
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/static_files/Sede/Programas_Ayuda/Modelo721/Instrucciones_Modelo721.pdf",
        dest="Influencers/Estatal/Influencers-Modelo721_Criptomonedas_Instrucciones.pdf",
        territory="Estatal",
        description="Modelo 721 declaracion criptomonedas en extranjero (desde 2023)",
        priority="high",
    ),
    # ── Tributacion Autonomica 2025 — Hacienda (deducciones por CCAA) ──
    WatchItem(
        url="https://www.hacienda.gob.es/SGFAL/FinanciacionTerritorial/Autonomica/Capitulo-IV-Tributacion-Autonomica-2025.pdf",
        dest="Influencers/Estatal/Influencers-Tributacion_Autonomica_2025_Hacienda.pdf",
        territory="Estatal",
        description="Tributacion autonomica 2025 — deducciones por CCAA para autonomos/creadores",
        priority="high",
    ),
    # ── DAC7 Modelo 238 — FAQ vendedores/creadores ──
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/static_files/Sede/Programas_Ayuda/Modelo238/FAQ_Modelo238.pdf",
        dest="Influencers/Estatal/Influencers-DAC7_Modelo238_FAQ.pdf",
        territory="Estatal",
        description="DAC7 Modelo 238 FAQ para vendedores/creadores en plataformas digitales",
        priority="high",
    ),
]


# ═══════════════════════════════════════════════════════════════
# All items combined
# ═══════════════════════════════════════════════════════════════

ALL_ITEMS: list[WatchItem] = (
    AEAT_ITEMS
    + BOE_ITEMS
    + AEAT_DR_ITEMS
    + NAVARRA_ITEMS
    + BIZKAIA_ITEMS
    + GIPUZKOA_ITEMS
    + ARABA_ITEMS
    + CCAA_ITEMS
    + CEUTA_MELILLA_ITEMS
    + CANARIAS_EXTRA_ITEMS
    + SS_ITEMS
    + CREATORS_ITEMS
    + INFLUENCERS_ITEMS
    + CREATOR_MODELS_ITEMS
)


def get_items(
    territory: str | None = None,
    priority: str | None = None,
    include_future: bool = True,
) -> list[WatchItem]:
    """Filter watchlist items by territory and/or priority."""
    items = ALL_ITEMS
    if territory:
        territory_lower = territory.lower()
        items = [i for i in items if i.territory.lower() == territory_lower]
    if priority:
        items = [i for i in items if i.priority == priority]
    if not include_future:
        items = [i for i in items if i.status != "future"]
    return items


def get_territories() -> list[str]:
    """Get list of unique territories in the watchlist."""
    return sorted(set(i.territory for i in ALL_ITEMS))


def get_stats() -> dict:
    """Get watchlist statistics."""
    total = len(ALL_ITEMS)
    by_priority = {}
    by_territory = {}
    by_status = {}

    for item in ALL_ITEMS:
        by_priority[item.priority] = by_priority.get(item.priority, 0) + 1
        by_territory[item.territory] = by_territory.get(item.territory, 0) + 1
        by_status[item.status] = by_status.get(item.status, 0) + 1

    return {
        "total": total,
        "by_priority": by_priority,
        "by_territory": dict(sorted(by_territory.items())),
        "by_status": by_status,
    }
