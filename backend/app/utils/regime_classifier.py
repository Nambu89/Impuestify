"""
Fiscal Regime Classifier for TaxIA.

Classifies a CCAA into its fiscal regime to determine:
- Which IRPF system applies (comun vs foral)
- Which special rules or deductions apply (Ceuta/Melilla, Canarias)
"""

FORAL_VASCO = {"Araba", "Bizkaia", "Gipuzkoa"}
FORAL_NAVARRA = {"Navarra"}
CEUTA_MELILLA = {"Ceuta", "Melilla"}
CANARIAS = {"Canarias"}


def classify_regime(ccaa: str) -> str:
    """
    Classify a CCAA string into its fiscal regime.

    Args:
        ccaa: Comunidad Autonoma name (e.g. 'Madrid', 'Araba', 'Navarra')

    Returns:
        One of: 'foral_vasco', 'foral_navarra', 'ceuta_melilla', 'canarias', 'comun'
    """
    if ccaa in FORAL_VASCO:
        return "foral_vasco"
    if ccaa in FORAL_NAVARRA:
        return "foral_navarra"
    if ccaa in CEUTA_MELILLA:
        return "ceuta_melilla"
    if ccaa in CANARIAS:
        return "canarias"
    return "comun"


def is_foral(ccaa: str) -> bool:
    """Return True if the CCAA uses a foral IRPF system (not the common system)."""
    regime = classify_regime(ccaa)
    return regime in ("foral_vasco", "foral_navarra")
