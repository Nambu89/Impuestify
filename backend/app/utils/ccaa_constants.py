"""
Single source of truth for CCAA identifiers across the entire project.

Convention: short names with correct Spanish accents.
Display labels (e.g. "Comunidad de Madrid") are separate — never stored in DB.
"""

# Canonical CCAA identifiers — used in BD, API payloads, and frontend values
CCAA_CANONICAL: list[str] = [
    "Andalucía",
    "Aragón",
    "Asturias",
    "Baleares",
    "Canarias",
    "Cantabria",
    "Castilla y León",
    "Castilla-La Mancha",
    "Cataluña",
    "Ceuta",
    "Valencia",
    "Extremadura",
    "Galicia",
    "La Rioja",
    "Madrid",
    "Melilla",
    "Murcia",
    "Navarra",
    "Araba",
    "Bizkaia",
    "Gipuzkoa",
]

# Display labels for UI (official/verbose names where they differ)
CCAA_DISPLAY_LABELS: dict[str, str] = {
    "Baleares": "Illes Balears",
    "Valencia": "Comunitat Valenciana",
    "Madrid": "Comunidad de Madrid",
    "Murcia": "Región de Murcia",
    "Araba": "Araba/Álava",
}

# All known aliases → canonical. Lowercase keys.
CCAA_ALIASES: dict[str, str] = {
    # Without accents (frontend legacy, user input)
    "andalucia": "Andalucía",
    "aragon": "Aragón",
    "cataluna": "Cataluña",
    "castilla y leon": "Castilla y León",
    # With accents (already canonical, but included for safety)
    "andalucía": "Andalucía",
    "aragón": "Aragón",
    "cataluña": "Cataluña",
    "castilla y león": "Castilla y León",
    # Official long names → canonical short
    "comunidad de madrid": "Madrid",
    "comunitat valenciana": "Valencia",
    "comunidad valenciana": "Valencia",
    "illes balears": "Baleares",
    "islas baleares": "Baleares",
    "región de murcia": "Murcia",
    "region de murcia": "Murcia",
    # Catalan/Basque variants
    "catalunya": "Cataluña",
    "país vasco": "Gipuzkoa",  # ambiguous, but needed for text extraction
    "pais vasco": "Gipuzkoa",
    "euskadi": "Gipuzkoa",
    # Ciudad autónoma variants
    "ciudad autónoma de ceuta": "Ceuta",
    "ciudad autonoma de ceuta": "Ceuta",
    "ciudad autónoma de melilla": "Melilla",
    "ciudad autonoma de melilla": "Melilla",
    # Already-canonical passthrough (lowercase)
    "asturias": "Asturias",
    "baleares": "Baleares",
    "canarias": "Canarias",
    "cantabria": "Cantabria",
    "castilla-la mancha": "Castilla-La Mancha",
    "castilla la mancha": "Castilla-La Mancha",
    "ceuta": "Ceuta",
    "valencia": "Valencia",
    "extremadura": "Extremadura",
    "galicia": "Galicia",
    "la rioja": "La Rioja",
    "rioja": "La Rioja",
    "madrid": "Madrid",
    "melilla": "Melilla",
    "murcia": "Murcia",
    "navarra": "Navarra",
    "araba": "Araba",
    "bizkaia": "Bizkaia",
    "gipuzkoa": "Gipuzkoa",
}

# Regime sets (for classify_regime)
FORAL_VASCO = {"Araba", "Bizkaia", "Gipuzkoa"}
FORAL_NAVARRA = {"Navarra"}
CEUTA_MELILLA = {"Ceuta", "Melilla"}
CANARIAS_SET = {"Canarias"}


def normalize_ccaa(name: str) -> str:
    """
    Normalize any CCAA name variant to canonical form.

    Examples:
        normalize_ccaa("Cataluna") → "Cataluña"
        normalize_ccaa("Comunidad de Madrid") → "Madrid"
        normalize_ccaa("Madrid") → "Madrid"
    """
    if not name:
        return name
    key = name.lower().strip()
    return CCAA_ALIASES.get(key, name)


def get_display_label(canonical: str) -> str:
    """Get the UI display label for a canonical CCAA name."""
    return CCAA_DISPLAY_LABELS.get(canonical, canonical)


# Migration map: old DB values → canonical (for one-time migration)
DB_MIGRATION_MAP: dict[str, str] = {
    # irpf_scales / tax_parameters (official long → canonical short)
    "Comunidad de Madrid": "Madrid",
    "Comunitat Valenciana": "Valencia",
    "Illes Balears": "Baleares",
    "Región de Murcia": "Murcia",
    # deductions (no-accent → canonical with accent)
    "Aragon": "Aragón",
    "Andalucia": "Andalucía",
    "Cataluna": "Cataluña",
    "Castilla y Leon": "Castilla y León",
    # deductions (mixed from seed_deductions_xsd)
    "Comunidad Valenciana": "Valencia",
}
