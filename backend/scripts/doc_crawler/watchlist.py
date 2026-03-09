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
    status: str = "active"              # active, future, html_only
    pattern: str = ""                   # URL template for future docs


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
    ),
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/static_files/Sede/Programas_Ayuda/Retenciones/2026/Cuadro_tipos_retenciones_2026.pdf",
        dest="AEAT/IRPF/AEAT-Cuadro_tipos_retenciones_IRPF_2026.pdf",
        territory="AEAT",
        description="Cuadro tipos retenciones IRPF 2026",
    ),

    # ── Algoritmo retenciones ──
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/static_files/Sede/Programas_Ayuda/Retenciones/2025/Algoritmo_2025.pdf",
        dest="AEAT/IRPF/AEAT-Algoritmo_2025.pdf",
        territory="AEAT",
        description="Algoritmo retenciones IRPF 2025",
    ),
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/static_files/Sede/Programas_Ayuda/Retenciones/2026/Algoritmo_2026.pdf",
        dest="AEAT/IRPF/AEAT-Algoritmo_2026.pdf",
        territory="AEAT",
        description="Algoritmo retenciones IRPF 2026",
    ),

    # ── Instrucciones Modelos ──
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/static_files/Sede/Programas_Ayuda/Modelo303/2025/Instrucciones_Modelo303_2025.pdf",
        dest="AEAT/Modelos/AEAT-Modelo303_IVA_Instrucciones_2025.pdf",
        territory="AEAT",
        description="Instrucciones Modelo 303 IVA 2025",
    ),
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/static_files/Sede/Programas_Ayuda/Modelo390/2025/Instrucciones_Modelo390_2025.pdf",
        dest="AEAT/Modelos/AEAT-Modelo390_IVA_Instrucciones_2025.pdf",
        territory="AEAT",
        description="Instrucciones Modelo 390 IVA 2025",
    ),
    WatchItem(
        url="https://sede.agenciatributaria.gob.es/static_files/Sede/Programas_Ayuda/Modelo190/Instrucciones_Modelo190.pdf",
        dest="AEAT/Modelos/AEAT-Modelo190_Retenciones_Instrucciones.pdf",
        territory="AEAT",
        description="Instrucciones Modelo 190 retenciones",
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
    ),
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2007/BOE-A-2007-9364-consolidado.pdf",
        dest="Estatal/RealesDecretos/Estatal-RD_439_2007_ReglamentoIRPF_consolidado.pdf",
        territory="Estatal",
        description="RD 439/2007 Reglamento IRPF consolidado",
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
    ),
    WatchItem(
        url=f"{AEAT_DR_BASE}/DR390_e2025.xlsx",
        dest="AEAT/DisenosRegistro/DR390_e2025.xlsx",
        file_type="xlsx",
        territory="AEAT",
        description="Diseno Registro Modelo 390 IVA 2025",
        priority="medium",
    ),
    WatchItem(
        url=f"{AEAT_DR_BASE}/DR130_e2019.xls",
        dest="AEAT/DisenosRegistro/DR130_e2019.xls",
        file_type="xls",
        territory="AEAT",
        description="Diseno Registro Modelo 130 pagos fraccionados",
        priority="low",
    ),
    WatchItem(
        url=f"{AEAT_DR_BASE}/DR131_e2025.xlsx",
        dest="AEAT/DisenosRegistro/DR131_e2025.xlsx",
        file_type="xlsx",
        territory="AEAT",
        description="Diseno Registro Modelo 131 modulos",
        priority="low",
    ),
]


# ═══════════════════════════════════════════════════════════════
# Navarra
# ═══════════════════════════════════════════════════════════════

NAVARRA_ITEMS = [
    WatchItem(
        url="https://www.navarra.es/documents/48192/17863227/Manual+te%C3%B3rico+de+la+campa%C3%B1a+de+2024.pdf",
        dest="Navarra/IRPF/Navarra-Manual_teorico_IRPF_2024.pdf",
        territory="Navarra",
        description="Manual teorico IRPF Navarra 2024",
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
    ),
    # Aragon
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2005/BOE-A-2005-20647-consolidado.pdf",
        dest="Aragon/Aragon-DLeg_1_2005_TributosCedidos_consolidado.pdf",
        territory="Aragon",
        description="Aragon DLeg 1/2005 tributos cedidos consolidado",
        priority="medium",
    ),
    # Asturias
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2014/BOE-A-2014-12730-consolidado.pdf",
        dest="Asturias/Asturias-DLeg_2_2014_TributosCedidos_consolidado.pdf",
        territory="Asturias",
        description="Asturias DLeg 2/2014 tributos cedidos consolidado",
        priority="medium",
    ),
    # Baleares
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2014/BOE-A-2014-7235-consolidado.pdf",
        dest="Baleares/Baleares-DLeg_1_2014_TributosCedidos_consolidado.pdf",
        territory="Baleares",
        description="Baleares DLeg 1/2014 tributos cedidos consolidado",
        priority="medium",
    ),
    # Canarias
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2009/BOE-A-2009-11432-consolidado.pdf",
        dest="Canarias/Canarias-DLeg_1_2009_TributosCedidos_consolidado.pdf",
        territory="Canarias",
        description="Canarias DLeg 1/2009 tributos cedidos consolidado",
        priority="medium",
    ),
    # Cantabria
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2008/BOE-A-2008-20587-consolidado.pdf",
        dest="Cantabria/Cantabria-DLeg_62_2008_TributosCedidos_consolidado.pdf",
        territory="Cantabria",
        description="Cantabria DLeg 62/2008 tributos cedidos consolidado",
        priority="medium",
    ),
    # Castilla-La Mancha
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2013/BOE-A-2013-13919-consolidado.pdf",
        dest="CastillaLaMancha/CastillaLaMancha-Ley_8_2013_MedidasTributarias_consolidado.pdf",
        territory="CastillaLaMancha",
        description="CLM Ley 8/2013 medidas tributarias consolidado",
        priority="low",
    ),
    # Castilla y Leon
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2013/BOE-A-2013-10937-consolidado.pdf",
        dest="CastillaYLeon/CastillaYLeon-DLeg_1_2013_TributosCedidos_consolidado.pdf",
        territory="CastillaYLeon",
        description="CyL DLeg 1/2013 tributos cedidos consolidado",
        priority="medium",
    ),
    # Cataluna
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2024/BOE-A-2024-16710-consolidado.pdf",
        dest="Cataluna/Cataluna-DLeg_1_2024_LibroSextoCodigoTributario_TributosCedidos.pdf",
        territory="Cataluna",
        description="Cataluna DLeg 1/2024 Libro Sexto tributos cedidos",
        priority="medium",
    ),
    # Extremadura
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2018/BOE-A-2018-16799-consolidado.pdf",
        dest="Extremadura/Extremadura-DLeg_1_2018_TributosCedidos_consolidado.pdf",
        territory="Extremadura",
        description="Extremadura DLeg 1/2018 tributos cedidos consolidado",
        priority="medium",
    ),
    # Galicia
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2011/BOE-A-2011-17966-consolidado.pdf",
        dest="Galicia/Galicia-DLeg_1_2011_TributosCedidos_consolidado.pdf",
        territory="Galicia",
        description="Galicia DLeg 1/2011 tributos cedidos consolidado",
        priority="medium",
    ),
    # La Rioja
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2017/BOE-A-2017-14705-consolidado.pdf",
        dest="LaRioja/LaRioja-Ley_10_2017_TributosCedidos_consolidado.pdf",
        territory="LaRioja",
        description="La Rioja Ley 10/2017 tributos cedidos consolidado",
        priority="medium",
    ),
    # Madrid
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2010/BOE-A-2010-18472-consolidado.pdf",
        dest="Madrid/Madrid-DLeg_1_2010_TributosCedidos_consolidado.pdf",
        territory="Madrid",
        description="Madrid DLeg 1/2010 tributos cedidos consolidado",
        priority="medium",
    ),
    # Murcia
    WatchItem(
        url="https://www.boe.es/buscar/pdf/2010/BOE-A-2010-12261-consolidado.pdf",
        dest="Murcia/Murcia-DLeg_1_2010_TributosCedidos_consolidado.pdf",
        territory="Murcia",
        description="Murcia DLeg 1/2010 tributos cedidos consolidado",
        priority="medium",
    ),
    # Valencia
    WatchItem(
        url="https://www.boe.es/buscar/pdf/1997/BOE-A-1997-3219-consolidado.pdf",
        dest="Valencia/Valencia-Ley_13_1997_TributosCedidos.pdf",
        territory="Valencia",
        description="Valencia Ley 13/1997 tributos cedidos consolidado",
        priority="medium",
    ),
]


# ═══════════════════════════════════════════════════════════════
# Seguridad Social
# ═══════════════════════════════════════════════════════════════

SS_ITEMS = [
    WatchItem(
        url="https://www.seg-social.es/wps/wcm/connect/wss/ficheros/tablas_cotizacion_autonomos_reta_2025.pdf",
        dest="Estatal/SegSocial/SS-Tabla_Cotizacion_Autonomos_RETA_2025.pdf",
        territory="Estatal",
        description="Tabla cotizacion RETA 2025",
        priority="low",
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
    + SS_ITEMS
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
