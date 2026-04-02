"""Pharmacy-specific constants for Impuestify.

CNAE 47.73 — Comercio al por menor de productos farmaceuticos
IAE 652.1 — Farmacias
Regimen Especial de Recargo de Equivalencia (Art. 154-163 LIVA)
"""

PHARMACY_CNAE = "47.73"
PHARMACY_IAE = "652.1"
PHARMACY_ACTIVITY = (
    "Comercio al por menor de productos farmaceuticos en establecimientos especializados"
)

# Recargo de Equivalencia rates (Art. 154-163 LIVA)
# Key = IVA rate (%), Value = RE rate (%)
RE_RATES = {
    21: 5.2,   # IVA general 21% -> RE 5.2%
    10: 1.4,   # IVA reducido 10% -> RE 1.4%
    4: 0.5,    # IVA superreducido 4% -> RE 0.5%
}

# Pharmacy-specific deductions
PHARMACY_DEDUCTIONS = [
    {
        "code": "FARM-01",
        "name": "Cuota Colegio de Farmaceuticos",
        "category": "profesional",
        "max_amount": None,
        "percentage": 100,
    },
    {
        "code": "FARM-02",
        "name": "Seguro de Responsabilidad Civil profesional",
        "category": "profesional",
        "max_amount": None,
        "percentage": 100,
    },
    {
        "code": "FARM-03",
        "name": "Formacion continua farmaceutica",
        "category": "formacion",
        "max_amount": None,
        "percentage": 100,
    },
    {
        "code": "FARM-04",
        "name": "Amortizacion fondo de comercio (compra farmacia)",
        "category": "amortizacion",
        "max_amount": None,
        "percentage": 5,
    },
    {
        "code": "FARM-05",
        "name": "Local comercial (alquiler o amortizacion)",
        "category": "local",
        "max_amount": None,
        "percentage": 100,
    },
    {
        "code": "FARM-06",
        "name": "Vehiculo (reparto domiciliario)",
        "category": "vehiculo",
        "max_amount": None,
        "percentage": 50,
    },
]

# IVA types for pharmacy products
PHARMACY_IVA_TYPES = {
    "medicamentos_uso_humano": 4,
    "formulas_magistrales": 4,
    "productos_dieteticos": 4,
    "productos_sanitarios": 10,
    "complementos_alimenticios": 10,
    "parafarmacia": 21,
    "cosmetica": 21,
    "productos_veterinarios": 21,
}
