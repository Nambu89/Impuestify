# Invoice Classifier + Accounting (Phase 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let autonomous users upload invoices (PDF/image), extract data with Gemini 3 Flash Vision, classify into PGC accounts, generate accounting entries, and export books for Registro Mercantil.

**Architecture:** Gemini 3 Flash Vision extracts structured invoice data → validation layer checks NIF/IVA math → classifier assigns PGC account → accounting service generates double-entry journal entries → export service produces CSV/Excel books.

**Tech Stack:** google-genai SDK, Pydantic models, Turso SQLite, FastAPI, openpyxl (already installed)

**Spec:** `docs/superpowers/specs/2026-04-05-invoice-classifier-accounting-design.md`

---

## File Structure

### New Files (Backend)

| File | Responsibility |
|------|---------------|
| `backend/app/services/invoice_ocr_service.py` | Gemini 3 Flash Vision OCR: PDF/image → FacturaExtraida |
| `backend/app/services/invoice_classifier_service.py` | PGC account classification via LLM |
| `backend/app/services/contabilidad_service.py` | Journal entries, ledger, balance, P&L |
| `backend/app/services/contabilidad_export_service.py` | CSV/Excel export of accounting books |
| `backend/app/routers/invoices.py` | REST endpoints: upload, list, reclassify, delete |
| `backend/app/routers/contabilidad.py` | REST endpoints: libro-diario, libro-mayor, balance, pyg, export |
| `backend/scripts/seed_pgc_accounts.py` | Seed ~200 PGC accounts (groups 1-7) |
| `backend/tests/test_invoice_ocr.py` | Tests for OCR extraction + validation |
| `backend/tests/test_invoice_classifier.py` | Tests for PGC classification |
| `backend/tests/test_contabilidad.py` | Tests for journal entries + books |
| `backend/tests/test_contabilidad_export.py` | Tests for CSV/Excel export |

### Modified Files

| File | Change |
|------|--------|
| `backend/requirements.txt` | Add `google-genai>=1.0.0` |
| `backend/app/config.py` | Add `GOOGLE_GEMINI_API_KEY`, `GEMINI_MODEL` |
| `backend/app/database/turso_client.py` | Add 3 tables in `init_schema()`: `pgc_accounts`, `libro_registro`, `asientos_contables` |
| `backend/app/main.py` | Register 2 new routers: invoices, contabilidad |

---

## Task 1: Config + Dependencies

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add google-genai to requirements.txt**

Add at the end of `backend/requirements.txt`:

```
# --- Google Gemini (Invoice OCR) ---
google-genai>=1.0.0
```

- [ ] **Step 2: Add Gemini config to config.py**

Add after the Azure Document Intelligence section (line ~49) in `backend/app/config.py`:

```python
    # -------------------------------
    # 🔮 Google Gemini (Invoice OCR)
    # -------------------------------
    GOOGLE_GEMINI_API_KEY: Optional[str] = Field(default=None)
    GEMINI_MODEL: str = Field(
        default="gemini-3-flash-preview",
        description="Gemini model for invoice OCR"
    )
```

- [ ] **Step 3: Install dependency**

Run: `cd backend && pip install google-genai>=1.0.0`

- [ ] **Step 4: Verify import works**

Run: `python -c "from google import genai; print('google-genai OK')"`
Expected: `google-genai OK`

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/app/config.py
git commit -m "feat: add google-genai dependency + Gemini config for invoice OCR"
```

---

## Task 2: Database Schema (3 tables)

**Files:**
- Modify: `backend/app/database/turso_client.py`

- [ ] **Step 1: Find init_schema() in turso_client.py**

Search for `async def init_schema` and locate where the last `CREATE TABLE IF NOT EXISTS` is.

- [ ] **Step 2: Add pgc_accounts table**

Add inside `init_schema()`:

```python
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pgc_accounts (
                id TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                group_code TEXT NOT NULL,
                group_name TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                keywords TEXT,
                common_for TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pgc_code ON pgc_accounts(code)
        """)
```

- [ ] **Step 3: Add libro_registro table**

```python
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS libro_registro (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                workspace_file_id TEXT,
                tipo TEXT NOT NULL,
                numero_factura TEXT,
                fecha_factura TEXT,
                fecha_operacion TEXT,
                emisor_nif TEXT,
                emisor_nombre TEXT,
                receptor_nif TEXT,
                receptor_nombre TEXT,
                concepto TEXT,
                base_imponible REAL NOT NULL,
                tipo_iva REAL,
                cuota_iva REAL,
                tipo_re REAL,
                cuota_re REAL,
                retencion_irpf_pct REAL,
                retencion_irpf REAL,
                total REAL NOT NULL,
                cuenta_pgc TEXT,
                cuenta_pgc_nombre TEXT,
                clasificacion_confianza TEXT,
                trimestre INTEGER,
                year INTEGER NOT NULL,
                raw_extraction TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_libro_user_year ON libro_registro(user_id, year)
        """)
```

- [ ] **Step 4: Add asientos_contables table**

```python
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS asientos_contables (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                libro_registro_id TEXT REFERENCES libro_registro(id) ON DELETE CASCADE,
                fecha TEXT NOT NULL,
                numero_asiento INTEGER NOT NULL,
                cuenta_code TEXT NOT NULL,
                cuenta_nombre TEXT NOT NULL,
                debe REAL DEFAULT 0,
                haber REAL DEFAULT 0,
                concepto TEXT,
                year INTEGER NOT NULL,
                trimestre INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_asientos_user_year ON asientos_contables(user_id, year)
        """)
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/database/turso_client.py
git commit -m "feat: add pgc_accounts, libro_registro, asientos_contables tables"
```

---

## Task 3: Seed PGC Accounts

**Files:**
- Create: `backend/scripts/seed_pgc_accounts.py`
- Test: Run script and verify count

- [ ] **Step 1: Create seed script**

Create `backend/scripts/seed_pgc_accounts.py`:

```python
"""
Seed Plan General Contable (PGC) accounts.
~200 most common accounts for autonomos and PYMEs.
Idempotent: deletes existing and re-inserts.
"""
import asyncio
import uuid
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.database.turso_client import get_db_client

PGC_ACCOUNTS = [
    # Grupo 1: Financiacion basica
    {"code": "100", "name": "Capital social", "group_code": "10", "group_name": "Capital", "type": "balance"},
    {"code": "170", "name": "Deudas a largo plazo con entidades de credito", "group_code": "17", "group_name": "Deudas LP", "type": "balance"},
    {"code": "171", "name": "Deudas a largo plazo", "group_code": "17", "group_name": "Deudas LP", "type": "balance"},
    {"code": "174", "name": "Acreedores por arrendamiento financiero LP", "group_code": "17", "group_name": "Deudas LP", "type": "balance"},
    {"code": "129", "name": "Resultado del ejercicio", "group_code": "12", "group_name": "Resultados pendientes", "type": "balance"},

    # Grupo 2: Inmovilizado
    {"code": "210", "name": "Terrenos y bienes naturales", "group_code": "21", "group_name": "Inmovilizado material", "type": "balance"},
    {"code": "211", "name": "Construcciones", "group_code": "21", "group_name": "Inmovilizado material", "type": "balance"},
    {"code": "213", "name": "Maquinaria", "group_code": "21", "group_name": "Inmovilizado material", "type": "balance"},
    {"code": "214", "name": "Utillaje", "group_code": "21", "group_name": "Inmovilizado material", "type": "balance"},
    {"code": "216", "name": "Mobiliario", "group_code": "21", "group_name": "Inmovilizado material", "type": "balance"},
    {"code": "217", "name": "Equipos para procesos de informacion", "group_code": "21", "group_name": "Inmovilizado material", "type": "balance"},
    {"code": "218", "name": "Elementos de transporte", "group_code": "21", "group_name": "Inmovilizado material", "type": "balance"},
    {"code": "206", "name": "Aplicaciones informaticas", "group_code": "20", "group_name": "Inmovilizado intangible", "type": "balance"},
    {"code": "281", "name": "Amortizacion acumulada inmovilizado material", "group_code": "28", "group_name": "Amortizaciones", "type": "balance"},
    {"code": "280", "name": "Amortizacion acumulada inmovilizado intangible", "group_code": "28", "group_name": "Amortizaciones", "type": "balance"},

    # Grupo 3: Existencias
    {"code": "300", "name": "Mercaderias", "group_code": "30", "group_name": "Existencias comerciales", "type": "balance"},
    {"code": "310", "name": "Materias primas", "group_code": "31", "group_name": "Materias primas", "type": "balance"},
    {"code": "350", "name": "Productos terminados", "group_code": "35", "group_name": "Productos terminados", "type": "balance"},

    # Grupo 4: Acreedores y deudores
    {"code": "400", "name": "Proveedores", "group_code": "40", "group_name": "Proveedores", "type": "balance",
     "keywords": ["proveedor", "compra", "suministro", "mercaderia"]},
    {"code": "410", "name": "Acreedores por prestaciones de servicios", "group_code": "41", "group_name": "Acreedores", "type": "balance",
     "keywords": ["servicio", "asesoria", "consultoria", "profesional"]},
    {"code": "430", "name": "Clientes", "group_code": "43", "group_name": "Clientes", "type": "balance",
     "keywords": ["cliente", "venta", "factura emitida"]},
    {"code": "440", "name": "Deudores", "group_code": "44", "group_name": "Deudores", "type": "balance"},
    {"code": "465", "name": "Remuneraciones pendientes de pago", "group_code": "46", "group_name": "Personal", "type": "balance"},
    {"code": "470", "name": "Hacienda Publica deudora", "group_code": "47", "group_name": "Admin. Publicas", "type": "balance"},
    {"code": "472", "name": "Hacienda Publica IVA soportado", "group_code": "47", "group_name": "Admin. Publicas", "type": "balance",
     "keywords": ["iva", "soportado", "deducible"]},
    {"code": "473", "name": "Hacienda Publica retenciones y pagos a cuenta", "group_code": "47", "group_name": "Admin. Publicas", "type": "balance"},
    {"code": "475", "name": "Hacienda Publica acreedora", "group_code": "47", "group_name": "Admin. Publicas", "type": "balance"},
    {"code": "4751", "name": "HP acreedora por retenciones practicadas", "group_code": "47", "group_name": "Admin. Publicas", "type": "balance",
     "keywords": ["retencion", "irpf", "practicada"]},
    {"code": "476", "name": "Organismos Seguridad Social acreedores", "group_code": "47", "group_name": "Admin. Publicas", "type": "balance"},
    {"code": "477", "name": "Hacienda Publica IVA repercutido", "group_code": "47", "group_name": "Admin. Publicas", "type": "balance",
     "keywords": ["iva", "repercutido", "cobrado"]},

    # Grupo 5: Cuentas financieras
    {"code": "520", "name": "Deudas a corto plazo con entidades de credito", "group_code": "52", "group_name": "Deudas CP", "type": "balance"},
    {"code": "523", "name": "Proveedores de inmovilizado CP", "group_code": "52", "group_name": "Deudas CP", "type": "balance"},
    {"code": "570", "name": "Caja", "group_code": "57", "group_name": "Tesoreria", "type": "balance",
     "keywords": ["efectivo", "caja", "metalico"]},
    {"code": "572", "name": "Bancos c/c", "group_code": "57", "group_name": "Tesoreria", "type": "balance",
     "keywords": ["banco", "transferencia", "cuenta corriente"]},

    # Grupo 6: Gastos
    {"code": "600", "name": "Compras de mercaderias", "group_code": "60", "group_name": "Compras", "type": "gasto",
     "keywords": ["compra", "mercaderia", "producto", "material", "stock"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "601", "name": "Compras de materias primas", "group_code": "60", "group_name": "Compras", "type": "gasto",
     "keywords": ["materia prima", "componente"]},
    {"code": "602", "name": "Compras de otros aprovisionamientos", "group_code": "60", "group_name": "Compras", "type": "gasto",
     "keywords": ["consumible", "envase", "embalaje", "material oficina"]},
    {"code": "606", "name": "Descuentos sobre compras por pronto pago", "group_code": "60", "group_name": "Compras", "type": "gasto"},
    {"code": "607", "name": "Trabajos realizados por otras empresas", "group_code": "60", "group_name": "Compras", "type": "gasto",
     "keywords": ["subcontrata", "outsourcing", "trabajo externo"]},
    {"code": "610", "name": "Variacion de existencias de mercaderias", "group_code": "61", "group_name": "Variacion existencias", "type": "gasto"},
    {"code": "621", "name": "Arrendamientos y canones", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["alquiler", "arrendamiento", "local", "oficina", "canon", "leasing", "renting"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "622", "name": "Reparaciones y conservacion", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["reparacion", "mantenimiento", "conservacion", "arreglo"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "623", "name": "Servicios de profesionales independientes", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["asesoria", "abogado", "gestor", "consultoria", "auditor", "notario", "profesional"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "624", "name": "Transportes", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["transporte", "mensajeria", "envio", "logistica", "correos"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "625", "name": "Primas de seguros", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["seguro", "poliza", "rc profesional", "responsabilidad civil"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "626", "name": "Servicios bancarios y similares", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["banco", "comision bancaria", "transferencia", "tpv"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "627", "name": "Publicidad, propaganda y relaciones publicas", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["publicidad", "marketing", "anuncio", "propaganda", "google ads", "meta ads"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "628", "name": "Suministros", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["luz", "agua", "gas", "electricidad", "telefono", "internet", "fibra"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "629", "name": "Otros servicios", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["servicio", "limpieza", "formacion", "suscripcion", "software", "hosting", "cloud", "saas"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "631", "name": "Otros tributos", "group_code": "63", "group_name": "Tributos", "type": "gasto",
     "keywords": ["ibi", "iae", "impuesto", "tasa", "tributo", "basura"]},
    {"code": "640", "name": "Sueldos y salarios", "group_code": "64", "group_name": "Gastos de personal", "type": "gasto",
     "keywords": ["nomina", "salario", "sueldo", "empleado", "trabajador"],
     "common_for": ["sociedad"]},
    {"code": "642", "name": "Seguridad Social a cargo de la empresa", "group_code": "64", "group_name": "Gastos de personal", "type": "gasto",
     "keywords": ["seguridad social", "cotizacion", "ss empresa"]},
    {"code": "649", "name": "Otros gastos sociales", "group_code": "64", "group_name": "Gastos de personal", "type": "gasto"},
    {"code": "662", "name": "Intereses de deudas", "group_code": "66", "group_name": "Gastos financieros", "type": "gasto",
     "keywords": ["interes", "prestamo", "hipoteca", "financiacion"]},
    {"code": "669", "name": "Otros gastos financieros", "group_code": "66", "group_name": "Gastos financieros", "type": "gasto"},
    {"code": "680", "name": "Amortizacion del inmovilizado intangible", "group_code": "68", "group_name": "Dotaciones amortizacion", "type": "gasto"},
    {"code": "681", "name": "Amortizacion del inmovilizado material", "group_code": "68", "group_name": "Dotaciones amortizacion", "type": "gasto",
     "keywords": ["amortizacion", "depreciacion"]},

    # Grupo 7: Ingresos
    {"code": "700", "name": "Ventas de mercaderias", "group_code": "70", "group_name": "Ventas", "type": "ingreso",
     "keywords": ["venta", "mercaderia", "producto"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "705", "name": "Prestaciones de servicios", "group_code": "70", "group_name": "Ventas", "type": "ingreso",
     "keywords": ["servicio", "honorarios", "factura emitida", "prestacion"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "708", "name": "Devoluciones de ventas", "group_code": "70", "group_name": "Ventas", "type": "ingreso"},
    {"code": "709", "name": "Rappels sobre ventas", "group_code": "70", "group_name": "Ventas", "type": "ingreso"},
    {"code": "740", "name": "Subvenciones a la explotacion", "group_code": "74", "group_name": "Subvenciones", "type": "ingreso",
     "keywords": ["subvencion", "ayuda", "kit digital"]},
    {"code": "752", "name": "Ingresos por arrendamientos", "group_code": "75", "group_name": "Otros ingresos", "type": "ingreso",
     "keywords": ["alquiler cobrado", "arrendamiento ingreso"]},
    {"code": "759", "name": "Ingresos por servicios diversos", "group_code": "75", "group_name": "Otros ingresos", "type": "ingreso"},
    {"code": "769", "name": "Otros ingresos financieros", "group_code": "76", "group_name": "Ingresos financieros", "type": "ingreso",
     "keywords": ["interes cobrado", "dividendo"]},
    {"code": "771", "name": "Beneficios procedentes del inmovilizado material", "group_code": "77", "group_name": "Beneficios activos", "type": "ingreso"},
]


async def seed():
    db = await get_db_client()
    async with db.connect() as conn:
        # Delete existing
        await conn.execute("DELETE FROM pgc_accounts")

        for account in PGC_ACCOUNTS:
            await conn.execute(
                """INSERT INTO pgc_accounts (id, code, name, group_code, group_name, type, description, keywords, common_for, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                [
                    str(uuid.uuid4()),
                    account["code"],
                    account["name"],
                    account["group_code"],
                    account["group_name"],
                    account["type"],
                    account.get("description"),
                    json.dumps(account.get("keywords")) if account.get("keywords") else None,
                    json.dumps(account.get("common_for")) if account.get("common_for") else None,
                ]
            )

        await conn.commit()
        result = await conn.execute("SELECT COUNT(*) as cnt FROM pgc_accounts")
        rows = result.rows if hasattr(result, 'rows') else []
        count = rows[0][0] if rows else 0
        print(f"Seeded {count} PGC accounts")


if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 2: Run seed script locally**

Run: `cd backend && python scripts/seed_pgc_accounts.py`
Expected: `Seeded 59 PGC accounts` (or similar count)

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/seed_pgc_accounts.py
git commit -m "feat: add PGC accounts seed script (59 accounts, groups 1-7)"
```

---

## Task 4: Invoice OCR Service (Gemini 3 Flash)

**Files:**
- Create: `backend/app/services/invoice_ocr_service.py`
- Create: `backend/tests/test_invoice_ocr.py`

- [ ] **Step 1: Write the tests**

Create `backend/tests/test_invoice_ocr.py`:

```python
"""Tests for Invoice OCR Service (Gemini 3 Flash Vision)."""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.invoice_ocr_service import (
    InvoiceOCRService,
    FacturaExtraida,
    EmisorReceptor,
    LineaFactura,
    validate_nif,
    validate_iva_math,
)


# --- NIF Validation ---

class TestValidateNIF:
    def test_valid_dni(self):
        assert validate_nif("12345678Z") is True

    def test_invalid_dni_letter(self):
        assert validate_nif("12345678A") is False

    def test_valid_nie_x(self):
        # X0000000T is valid
        assert validate_nif("X0000000T") is True

    def test_cif_format(self):
        # CIF starts with letter (A-W), 7 digits, control char
        assert validate_nif("B12345678") is True

    def test_short_nif(self):
        assert validate_nif("1234") is False

    def test_empty(self):
        assert validate_nif("") is False


# --- IVA Math Validation ---

class TestValidateIVAMath:
    def test_correct_iva_21(self):
        factura = FacturaExtraida(
            emisor=EmisorReceptor(nif_cif="B12345678", nombre="Test SL"),
            receptor=EmisorReceptor(nif_cif="12345678Z", nombre="Juan"),
            numero_factura="F-001",
            fecha_factura="2026-04-01",
            lineas=[LineaFactura(concepto="Servicio", cantidad=1, precio_unitario=100.0, base_imponible=100.0)],
            base_imponible_total=100.0,
            tipo_iva_pct=21.0,
            cuota_iva=21.0,
            total=121.0,
            tipo="recibida",
        )
        errors = validate_iva_math(factura)
        assert errors == []

    def test_iva_mismatch(self):
        factura = FacturaExtraida(
            emisor=EmisorReceptor(nif_cif="B12345678", nombre="Test SL"),
            receptor=EmisorReceptor(nif_cif="12345678Z", nombre="Juan"),
            numero_factura="F-002",
            fecha_factura="2026-04-01",
            lineas=[LineaFactura(concepto="Servicio", cantidad=1, precio_unitario=100.0, base_imponible=100.0)],
            base_imponible_total=100.0,
            tipo_iva_pct=21.0,
            cuota_iva=25.0,  # Wrong!
            total=125.0,
            tipo="recibida",
        )
        errors = validate_iva_math(factura)
        assert len(errors) > 0
        assert "IVA" in errors[0]

    def test_total_with_irpf(self):
        factura = FacturaExtraida(
            emisor=EmisorReceptor(nif_cif="12345678Z", nombre="Profesional"),
            receptor=EmisorReceptor(nif_cif="B12345678", nombre="Empresa SL"),
            numero_factura="F-003",
            fecha_factura="2026-04-01",
            lineas=[LineaFactura(concepto="Consultoria", cantidad=1, precio_unitario=1000.0, base_imponible=1000.0)],
            base_imponible_total=1000.0,
            tipo_iva_pct=21.0,
            cuota_iva=210.0,
            retencion_irpf_pct=15.0,
            retencion_irpf=150.0,
            total=1060.0,  # 1000 + 210 - 150
            tipo="emitida",
        )
        errors = validate_iva_math(factura)
        assert errors == []


# --- OCR Service (mocked Gemini) ---

class TestInvoiceOCRService:
    @pytest.fixture
    def mock_gemini_response(self):
        return json.dumps({
            "emisor": {"nif_cif": "B12345678", "nombre": "Proveedor SL", "direccion": "Madrid"},
            "receptor": {"nif_cif": "12345678Z", "nombre": "Juan Garcia", "direccion": None},
            "numero_factura": "F-2026-042",
            "fecha_factura": "2026-03-15",
            "fecha_operacion": None,
            "lineas": [{"concepto": "Servicio de consultoria", "cantidad": 1, "precio_unitario": 500.0, "base_imponible": 500.0}],
            "base_imponible_total": 500.0,
            "tipo_iva_pct": 21.0,
            "cuota_iva": 105.0,
            "tipo_re_pct": None,
            "cuota_re": None,
            "retencion_irpf_pct": None,
            "retencion_irpf": None,
            "total": 605.0,
            "tipo": "recibida",
        })

    @pytest.mark.asyncio
    async def test_extract_invoice_pdf(self, mock_gemini_response):
        with patch("app.services.invoice_ocr_service.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_response = MagicMock()
            mock_response.text = mock_gemini_response
            mock_client.models.generate_content.return_value = mock_response

            service = InvoiceOCRService(api_key="test-key")
            result = await service.extract_from_bytes(b"%PDF-fake", "application/pdf")

            assert result.factura.emisor.nif_cif == "B12345678"
            assert result.factura.numero_factura == "F-2026-042"
            assert result.factura.total == 605.0
            assert result.factura.tipo == "recibida"

    @pytest.mark.asyncio
    async def test_extract_returns_validation(self, mock_gemini_response):
        with patch("app.services.invoice_ocr_service.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_response = MagicMock()
            mock_response.text = mock_gemini_response
            mock_client.models.generate_content.return_value = mock_response

            service = InvoiceOCRService(api_key="test-key")
            result = await service.extract_from_bytes(b"%PDF-fake", "application/pdf")

            assert result.confianza in ("alta", "media", "baja")
            assert isinstance(result.errores_validacion, list)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_invoice_ocr.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Create the OCR service**

Create `backend/app/services/invoice_ocr_service.py`:

```python
"""
Invoice OCR Service using Gemini 3 Flash Vision.

Extracts structured data from Spanish invoices (PDF/image).
ADR-009: Gemini 3 Flash for user invoice OCR (not Azure DI).
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel, Field

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


# --- Pydantic models for structured extraction ---

class EmisorReceptor(BaseModel):
    nif_cif: str = Field(description="NIF o CIF")
    nombre: str = Field(description="Razon social o nombre completo")
    direccion: Optional[str] = None


class LineaFactura(BaseModel):
    concepto: str
    cantidad: float = 1.0
    precio_unitario: float
    base_imponible: float


class FacturaExtraida(BaseModel):
    emisor: EmisorReceptor
    receptor: EmisorReceptor
    numero_factura: str
    fecha_factura: str = Field(description="YYYY-MM-DD")
    fecha_operacion: Optional[str] = None
    lineas: list[LineaFactura]
    base_imponible_total: float
    tipo_iva_pct: float = Field(description="21, 10, 4 o 0")
    cuota_iva: float
    tipo_re_pct: Optional[float] = None
    cuota_re: Optional[float] = None
    retencion_irpf_pct: Optional[float] = None
    retencion_irpf: Optional[float] = None
    total: float
    tipo: str = Field(description="emitida o recibida")


@dataclass
class ExtractionResult:
    factura: FacturaExtraida
    confianza: str = "alta"  # alta, media, baja
    errores_validacion: list = field(default_factory=list)
    nif_emisor_valido: bool = True
    nif_receptor_valido: bool = True


# --- Validation functions ---

def validate_nif(nif: str) -> bool:
    """Validate Spanish NIF/CIF/NIE checksum."""
    if not nif:
        return False
    nif = nif.upper().replace("-", "").replace(" ", "").replace(".", "")
    if len(nif) != 9:
        return False

    # NIE: replace X/Y/Z prefix with 0/1/2
    if nif[0] in "XYZ":
        nie_map = {"X": "0", "Y": "1", "Z": "2"}
        nif_num = nie_map[nif[0]] + nif[1:]
    else:
        nif_num = nif

    # DNI: 8 digits + letter
    if nif_num[:8].isdigit():
        letters = "TRWAGMYFPDXBNJZSQVHLCKE"
        expected = letters[int(nif_num[:8]) % 23]
        return nif_num[8] == expected

    # CIF: starts with letter, basic format check
    if nif[0].isalpha() and nif[1:8].isdigit():
        return True

    return False


def validate_iva_math(f: FacturaExtraida) -> list[str]:
    """Check IVA and total arithmetic consistency."""
    errors = []
    expected_cuota = round(f.base_imponible_total * f.tipo_iva_pct / 100, 2)
    if abs(f.cuota_iva - expected_cuota) > 0.05:
        errors.append(f"IVA no cuadra: {f.cuota_iva} vs esperado {expected_cuota}")

    expected_total = f.base_imponible_total + f.cuota_iva
    if f.cuota_re:
        expected_total += f.cuota_re
    if f.retencion_irpf:
        expected_total -= f.retencion_irpf
    if abs(f.total - round(expected_total, 2)) > 0.05:
        errors.append(f"Total no cuadra: {f.total} vs esperado {round(expected_total, 2)}")

    return errors


# --- OCR Service ---

EXTRACTION_PROMPT = (
    "Extrae todos los datos de esta factura espanola. "
    "Devuelve JSON estricto segun el schema proporcionado. "
    "Si un campo no aparece en la factura, usa null. "
    "Formatea fechas como YYYY-MM-DD. "
    "Importes en EUR con 2 decimales. "
    "Si no puedes determinar si es emitida o recibida, pon 'recibida'."
)


class InvoiceOCRService:
    """Extracts structured data from invoices using Gemini 3 Flash Vision."""

    def __init__(self, api_key: str, model: str = "gemini-3-flash-preview"):
        self.model = model
        if GENAI_AVAILABLE:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None

    async def extract_from_bytes(
        self, file_bytes: bytes, mime_type: str
    ) -> ExtractionResult:
        """Extract invoice data from PDF or image bytes."""
        if not self.client:
            raise RuntimeError("google-genai not installed. Run: pip install google-genai")

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                EXTRACTION_PROMPT,
            ],
            config={
                "response_mime_type": "application/json",
                "response_json_schema": FacturaExtraida.model_json_schema(),
            },
        )

        factura = FacturaExtraida.model_validate_json(response.text)

        # Post-extraction validation
        errores = validate_iva_math(factura)
        nif_e = validate_nif(factura.emisor.nif_cif)
        nif_r = validate_nif(factura.receptor.nif_cif)

        if not nif_e:
            errores.append(f"NIF emisor invalido: {factura.emisor.nif_cif}")
        if not nif_r:
            errores.append(f"NIF receptor invalido: {factura.receptor.nif_cif}")

        # Determine confidence
        if len(errores) == 0:
            confianza = "alta"
        elif len(errores) <= 2 and all("NIF" in e for e in errores):
            confianza = "media"
        else:
            confianza = "baja"

        return ExtractionResult(
            factura=factura,
            confianza=confianza,
            errores_validacion=errores,
            nif_emisor_valido=nif_e,
            nif_receptor_valido=nif_r,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_invoice_ocr.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/invoice_ocr_service.py backend/tests/test_invoice_ocr.py
git commit -m "feat: InvoiceOCRService with Gemini 3 Flash Vision + NIF/IVA validation"
```

---

## Task 5: Invoice Classifier Service (PGC)

**Files:**
- Create: `backend/app/services/invoice_classifier_service.py`
- Create: `backend/tests/test_invoice_classifier.py`

- [ ] **Step 1: Write the tests**

Create `backend/tests/test_invoice_classifier.py`:

```python
"""Tests for Invoice PGC Classifier Service."""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.invoice_classifier_service import (
    InvoiceClassifierService,
    ClasificacionPGC,
)


class TestInvoiceClassifier:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        # Return some PGC accounts when queried
        mock_result = MagicMock()
        mock_result.rows = [
            {"code": "623", "name": "Servicios de profesionales independientes", "keywords": '["asesoria", "consultoria"]'},
            {"code": "629", "name": "Otros servicios", "keywords": '["servicio", "software"]'},
            {"code": "621", "name": "Arrendamientos y canones", "keywords": '["alquiler"]'},
        ]
        db.execute = AsyncMock(return_value=mock_result)
        return db

    @pytest.fixture
    def mock_gemini_classification(self):
        return json.dumps({
            "cuenta_code": "623",
            "cuenta_nombre": "Servicios de profesionales independientes",
            "confianza": "alta",
            "alternativas": [
                {"code": "629", "nombre": "Otros servicios"}
            ],
            "justificacion": "Factura de asesoria fiscal, servicio profesional independiente"
        })

    @pytest.mark.asyncio
    async def test_classify_invoice(self, mock_db, mock_gemini_classification):
        with patch("app.services.invoice_classifier_service.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_response = MagicMock()
            mock_response.text = mock_gemini_classification
            mock_client.models.generate_content.return_value = mock_response

            service = InvoiceClassifierService(api_key="test-key", db=mock_db)
            result = await service.classify(
                concepto="Servicio de asesoria fiscal Q1 2026",
                emisor_nombre="Gestoria Lopez SL",
                tipo="recibida",
                base_imponible=300.0,
            )

            assert isinstance(result, ClasificacionPGC)
            assert result.cuenta_code == "623"
            assert result.confianza == "alta"

    def test_clasificacion_model(self):
        c = ClasificacionPGC(
            cuenta_code="629",
            cuenta_nombre="Otros servicios",
            confianza="media",
            alternativas=[],
            justificacion="Servicio generico"
        )
        assert c.cuenta_code == "629"
        assert c.confianza == "media"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_invoice_classifier.py -v`
Expected: FAIL

- [ ] **Step 3: Create the classifier service**

Create `backend/app/services/invoice_classifier_service.py`:

```python
"""
Invoice PGC Classifier Service.

Classifies invoices into Plan General Contable accounts using Gemini 3 Flash.
"""
import json
import logging
from typing import Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


class AlternativaPGC(BaseModel):
    code: str
    nombre: str


class ClasificacionPGC(BaseModel):
    cuenta_code: str
    cuenta_nombre: str
    confianza: str = Field(description="alta, media o baja")
    alternativas: list[AlternativaPGC] = []
    justificacion: str = ""


CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "cuenta_code": {"type": "string"},
        "cuenta_nombre": {"type": "string"},
        "confianza": {"type": "string", "enum": ["alta", "media", "baja"]},
        "alternativas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "nombre": {"type": "string"},
                },
                "required": ["code", "nombre"],
            },
        },
        "justificacion": {"type": "string"},
    },
    "required": ["cuenta_code", "cuenta_nombre", "confianza", "justificacion"],
}


class InvoiceClassifierService:
    """Classifies invoices into PGC accounts using LLM."""

    def __init__(self, api_key: str, db=None, model: str = "gemini-3-flash-preview"):
        self.model = model
        self.db = db
        if GENAI_AVAILABLE:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None

    async def _get_candidate_accounts(self, tipo: str) -> list[dict]:
        """Get candidate PGC accounts from DB based on invoice type."""
        if not self.db:
            return []
        account_type = "gasto" if tipo == "recibida" else "ingreso"
        result = await self.db.execute(
            "SELECT code, name, keywords FROM pgc_accounts WHERE type = ? AND is_active = 1 ORDER BY code",
            [account_type],
        )
        return [dict(r) for r in (result.rows or [])]

    async def classify(
        self,
        concepto: str,
        emisor_nombre: str,
        tipo: str,
        base_imponible: float,
        cnae: str = "",
        actividad: str = "",
    ) -> ClasificacionPGC:
        """Classify an invoice into a PGC account."""
        if not self.client:
            raise RuntimeError("google-genai not installed")

        candidates = await self._get_candidate_accounts(tipo)
        candidates_text = "\n".join(
            f"- {c['code']} {c['name']}" + (f" (keywords: {c['keywords']})" if c.get("keywords") else "")
            for c in candidates
        )

        prompt = f"""Clasifica esta factura en una cuenta del Plan General Contable espanol.

Datos de la factura:
- Concepto: {concepto}
- Emisor: {emisor_nombre}
- Tipo: {tipo} ({"gasto" if tipo == "recibida" else "ingreso"})
- Importe base: {base_imponible} EUR
{"- Actividad del usuario: " + actividad if actividad else ""}
{"- CNAE: " + cnae if cnae else ""}

Cuentas PGC candidatas:
{candidates_text}

Elige la cuenta mas apropiada. Si no estas seguro, indica confianza "media" o "baja" y da alternativas."""

        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config={
                "response_mime_type": "application/json",
                "response_json_schema": CLASSIFICATION_SCHEMA,
            },
        )

        return ClasificacionPGC.model_validate_json(response.text)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_invoice_classifier.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/invoice_classifier_service.py backend/tests/test_invoice_classifier.py
git commit -m "feat: InvoiceClassifierService — PGC classification with Gemini 3 Flash"
```

---

## Task 6: Contabilidad Service (Journal Entries + Books)

**Files:**
- Create: `backend/app/services/contabilidad_service.py`
- Create: `backend/tests/test_contabilidad.py`

- [ ] **Step 1: Write the tests**

Create `backend/tests/test_contabilidad.py`:

```python
"""Tests for Contabilidad Service (journal entries + books)."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.contabilidad_service import ContabilidadService, AsientoLine


class TestContabilidadService:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(rows=[]))
        return db

    def test_generate_asiento_factura_recibida(self):
        """Factura recibida (gasto): Debe 6xx + 472, Haber 400/410."""
        lines = ContabilidadService.generate_asiento_lines(
            tipo="recibida",
            cuenta_pgc_code="629",
            cuenta_pgc_nombre="Otros servicios",
            base_imponible=100.0,
            cuota_iva=21.0,
            total=121.0,
            retencion_irpf=None,
            concepto="Hosting web",
        )
        assert len(lines) == 3
        # Debe: gasto
        assert lines[0].debe == 100.0 and lines[0].haber == 0
        assert lines[0].cuenta_code == "629"
        # Debe: IVA soportado
        assert lines[1].debe == 21.0 and lines[1].haber == 0
        assert lines[1].cuenta_code == "472"
        # Haber: proveedor
        assert lines[2].haber == 121.0 and lines[2].debe == 0
        assert lines[2].cuenta_code == "410"

    def test_generate_asiento_factura_emitida(self):
        """Factura emitida (ingreso): Debe 430, Haber 7xx + 477."""
        lines = ContabilidadService.generate_asiento_lines(
            tipo="emitida",
            cuenta_pgc_code="705",
            cuenta_pgc_nombre="Prestaciones de servicios",
            base_imponible=1000.0,
            cuota_iva=210.0,
            total=1210.0,
            retencion_irpf=None,
            concepto="Consultoria marzo",
        )
        assert len(lines) == 3
        assert lines[0].debe == 1210.0  # Cliente
        assert lines[0].cuenta_code == "430"
        assert lines[1].haber == 1000.0  # Ingreso
        assert lines[1].cuenta_code == "705"
        assert lines[2].haber == 210.0  # IVA repercutido
        assert lines[2].cuenta_code == "477"

    def test_generate_asiento_with_irpf(self):
        """Factura emitida con retencion IRPF."""
        lines = ContabilidadService.generate_asiento_lines(
            tipo="emitida",
            cuenta_pgc_code="705",
            cuenta_pgc_nombre="Prestaciones de servicios",
            base_imponible=1000.0,
            cuota_iva=210.0,
            total=1060.0,  # 1000+210-150
            retencion_irpf=150.0,
            concepto="Consultoria con retencion",
        )
        assert len(lines) == 4
        # Debe: cliente (total neto)
        assert lines[0].debe == 1060.0
        assert lines[0].cuenta_code == "430"
        # Debe: HP retenciones
        assert lines[1].debe == 150.0
        assert lines[1].cuenta_code == "473"
        # Haber: ingreso
        assert lines[2].haber == 1000.0
        # Haber: IVA repercutido
        assert lines[3].haber == 210.0

    def test_asiento_debe_equals_haber(self):
        """Sum of debe must equal sum of haber in every asiento."""
        for tipo, cuenta, base, iva, total, ret in [
            ("recibida", "629", 100, 21, 121, None),
            ("emitida", "705", 1000, 210, 1210, None),
            ("emitida", "705", 1000, 210, 1060, 150),
            ("recibida", "621", 500, 105, 605, None),
        ]:
            lines = ContabilidadService.generate_asiento_lines(
                tipo=tipo, cuenta_pgc_code=cuenta, cuenta_pgc_nombre="Test",
                base_imponible=base, cuota_iva=iva, total=total,
                retencion_irpf=ret, concepto="Test",
            )
            total_debe = sum(l.debe for l in lines)
            total_haber = sum(l.haber for l in lines)
            assert abs(total_debe - total_haber) < 0.01, f"Debe {total_debe} != Haber {total_haber}"

    @pytest.mark.asyncio
    async def test_get_libro_diario(self, mock_db):
        mock_db.execute.return_value = MagicMock(rows=[
            {"id": "1", "fecha": "2026-01-15", "numero_asiento": 1, "cuenta_code": "629",
             "cuenta_nombre": "Otros servicios", "debe": 100.0, "haber": 0, "concepto": "Hosting"},
        ])
        service = ContabilidadService(db=mock_db)
        result = await service.get_libro_diario(user_id="u1", year=2026)
        assert len(result) == 1
        assert result[0]["cuenta_code"] == "629"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_contabilidad.py -v`
Expected: FAIL

- [ ] **Step 3: Create the contabilidad service**

Create `backend/app/services/contabilidad_service.py`:

```python
"""
Contabilidad Service.

Generates journal entries (asientos contables) from classified invoices
and provides accounting book queries (Libro Diario, Mayor, Balance, PyG).
"""
import uuid
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AsientoLine:
    cuenta_code: str
    cuenta_nombre: str
    debe: float
    haber: float
    concepto: str


class ContabilidadService:
    """Manages accounting entries and book generation."""

    def __init__(self, db=None):
        self.db = db

    @staticmethod
    def generate_asiento_lines(
        tipo: str,
        cuenta_pgc_code: str,
        cuenta_pgc_nombre: str,
        base_imponible: float,
        cuota_iva: float,
        total: float,
        retencion_irpf: Optional[float],
        concepto: str,
    ) -> list[AsientoLine]:
        """Generate double-entry journal lines for an invoice.

        Factura recibida (gasto):
            Debe: 6xx (gasto, base)  +  472 (IVA soportado)
            Haber: 400/410 (proveedor, total)

        Factura emitida (ingreso):
            Debe: 430 (cliente, total)
            Haber: 7xx (ingreso, base)  +  477 (IVA repercutido)

        With IRPF retention on emitida:
            Debe: 430 (cliente, total neto)  +  473 (HP retenciones)
            Haber: 7xx + 477
        """
        lines = []

        if tipo == "recibida":
            # Gasto
            lines.append(AsientoLine(
                cuenta_code=cuenta_pgc_code,
                cuenta_nombre=cuenta_pgc_nombre,
                debe=base_imponible, haber=0,
                concepto=concepto,
            ))
            # IVA soportado
            if cuota_iva > 0:
                lines.append(AsientoLine(
                    cuenta_code="472",
                    cuenta_nombre="HP IVA soportado",
                    debe=cuota_iva, haber=0,
                    concepto=f"IVA soportado - {concepto}",
                ))
            # Proveedor (410 for services, 400 for goods)
            proveedor_code = "410" if cuenta_pgc_code.startswith("6") and not cuenta_pgc_code.startswith("60") else "400"
            lines.append(AsientoLine(
                cuenta_code=proveedor_code,
                cuenta_nombre="Acreedores" if proveedor_code == "410" else "Proveedores",
                debe=0, haber=total,
                concepto=concepto,
            ))

        elif tipo == "emitida":
            # Cliente
            lines.append(AsientoLine(
                cuenta_code="430",
                cuenta_nombre="Clientes",
                debe=total, haber=0,
                concepto=concepto,
            ))
            # HP retenciones (if IRPF withheld)
            if retencion_irpf and retencion_irpf > 0:
                lines.append(AsientoLine(
                    cuenta_code="473",
                    cuenta_nombre="HP retenciones y pagos a cuenta",
                    debe=retencion_irpf, haber=0,
                    concepto=f"Retencion IRPF - {concepto}",
                ))
            # Ingreso
            lines.append(AsientoLine(
                cuenta_code=cuenta_pgc_code,
                cuenta_nombre=cuenta_pgc_nombre,
                debe=0, haber=base_imponible,
                concepto=concepto,
            ))
            # IVA repercutido
            if cuota_iva > 0:
                lines.append(AsientoLine(
                    cuenta_code="477",
                    cuenta_nombre="HP IVA repercutido",
                    debe=0, haber=cuota_iva,
                    concepto=f"IVA repercutido - {concepto}",
                ))

        return lines

    async def save_asiento(
        self, user_id: str, libro_registro_id: str, fecha: str,
        lines: list[AsientoLine], year: int, trimestre: int,
    ) -> list[str]:
        """Save journal entry lines to DB. Returns list of created IDs."""
        if not self.db:
            raise RuntimeError("Database not available")

        # Get next asiento number for this user/year
        result = await self.db.execute(
            "SELECT COALESCE(MAX(numero_asiento), 0) as max_num FROM asientos_contables WHERE user_id = ? AND year = ?",
            [user_id, year],
        )
        rows = result.rows if hasattr(result, 'rows') else []
        next_num = (rows[0][0] if rows and rows[0] else 0) + 1

        ids = []
        for line in lines:
            line_id = str(uuid.uuid4())
            await self.db.execute(
                """INSERT INTO asientos_contables
                   (id, user_id, libro_registro_id, fecha, numero_asiento,
                    cuenta_code, cuenta_nombre, debe, haber, concepto, year, trimestre)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [line_id, user_id, libro_registro_id, fecha, next_num,
                 line.cuenta_code, line.cuenta_nombre, line.debe, line.haber,
                 line.concepto, year, trimestre],
            )
            ids.append(line_id)
        return ids

    async def get_libro_diario(
        self, user_id: str, year: int, trimestre: int = None,
    ) -> list[dict]:
        """Get Libro Diario (journal) entries."""
        query = "SELECT * FROM asientos_contables WHERE user_id = ? AND year = ?"
        params = [user_id, year]
        if trimestre:
            query += " AND trimestre = ?"
            params.append(trimestre)
        query += " ORDER BY numero_asiento, cuenta_code"
        result = await self.db.execute(query, params)
        return [dict(r) for r in (result.rows or [])]

    async def get_libro_mayor(self, user_id: str, year: int) -> list[dict]:
        """Get Libro Mayor (ledger) — balances by account."""
        result = await self.db.execute(
            """SELECT cuenta_code, cuenta_nombre,
                      SUM(debe) as total_debe, SUM(haber) as total_haber,
                      SUM(debe) - SUM(haber) as saldo
               FROM asientos_contables
               WHERE user_id = ? AND year = ?
               GROUP BY cuenta_code, cuenta_nombre
               ORDER BY cuenta_code""",
            [user_id, year],
        )
        return [dict(r) for r in (result.rows or [])]

    async def get_balance_sumas_saldos(self, user_id: str, year: int) -> dict:
        """Get Balance de Sumas y Saldos."""
        mayor = await self.get_libro_mayor(user_id, year)
        total_debe = sum(r["total_debe"] for r in mayor)
        total_haber = sum(r["total_haber"] for r in mayor)
        return {
            "cuentas": mayor,
            "total_debe": round(total_debe, 2),
            "total_haber": round(total_haber, 2),
            "diferencia": round(total_debe - total_haber, 2),
            "year": year,
        }

    async def get_pyg(self, user_id: str, year: int) -> dict:
        """Get Cuenta de Perdidas y Ganancias."""
        mayor = await self.get_libro_mayor(user_id, year)

        gastos = [r for r in mayor if r["cuenta_code"].startswith("6")]
        ingresos = [r for r in mayor if r["cuenta_code"].startswith("7")]

        total_gastos = sum(r["total_debe"] - r["total_haber"] for r in gastos)
        total_ingresos = sum(r["total_haber"] - r["total_debe"] for r in ingresos)

        return {
            "gastos": gastos,
            "ingresos": ingresos,
            "total_gastos": round(total_gastos, 2),
            "total_ingresos": round(total_ingresos, 2),
            "resultado": round(total_ingresos - total_gastos, 2),
            "year": year,
            "disclaimer": "Informacion orientativa. No sustituye el asesoramiento de un profesional contable.",
        }
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_contabilidad.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/contabilidad_service.py backend/tests/test_contabilidad.py
git commit -m "feat: ContabilidadService — journal entries, libro diario, mayor, balance, PyG"
```

---

## Task 7: Export Service (CSV/Excel)

**Files:**
- Create: `backend/app/services/contabilidad_export_service.py`
- Create: `backend/tests/test_contabilidad_export.py`

- [ ] **Step 1: Write the tests**

Create `backend/tests/test_contabilidad_export.py`:

```python
"""Tests for Contabilidad Export Service."""
import pytest
import io
import csv
from app.services.contabilidad_export_service import ContabilidadExportService


class TestExportCSV:
    def test_libro_diario_csv(self):
        entries = [
            {"fecha": "2026-01-15", "numero_asiento": 1, "cuenta_code": "629",
             "cuenta_nombre": "Otros servicios", "debe": 100.0, "haber": 0, "concepto": "Hosting"},
            {"fecha": "2026-01-15", "numero_asiento": 1, "cuenta_code": "472",
             "cuenta_nombre": "HP IVA soportado", "debe": 21.0, "haber": 0, "concepto": "IVA"},
            {"fecha": "2026-01-15", "numero_asiento": 1, "cuenta_code": "410",
             "cuenta_nombre": "Acreedores", "debe": 0, "haber": 121.0, "concepto": "Hosting"},
        ]
        csv_bytes = ContabilidadExportService.libro_diario_to_csv(entries)
        reader = csv.reader(io.StringIO(csv_bytes.decode("utf-8")))
        rows = list(reader)
        assert rows[0] == ["Fecha", "N Asiento", "Cuenta", "Nombre Cuenta", "Debe", "Haber", "Concepto"]
        assert len(rows) == 4  # header + 3 lines

    def test_libro_mayor_csv(self):
        mayor = [
            {"cuenta_code": "629", "cuenta_nombre": "Otros servicios",
             "total_debe": 500.0, "total_haber": 0, "saldo": 500.0},
        ]
        csv_bytes = ContabilidadExportService.libro_mayor_to_csv(mayor)
        reader = csv.reader(io.StringIO(csv_bytes.decode("utf-8")))
        rows = list(reader)
        assert rows[0] == ["Cuenta", "Nombre", "Total Debe", "Total Haber", "Saldo"]
        assert len(rows) == 2

    def test_libro_registro_csv(self):
        facturas = [
            {"fecha_factura": "2026-01-15", "numero_factura": "F-001", "tipo": "recibida",
             "emisor_nif": "B12345678", "emisor_nombre": "Proveedor SL",
             "base_imponible": 100.0, "tipo_iva": 21.0, "cuota_iva": 21.0,
             "total": 121.0, "cuenta_pgc": "629", "cuenta_pgc_nombre": "Otros servicios"},
        ]
        csv_bytes = ContabilidadExportService.libro_registro_to_csv(facturas)
        assert b"F-001" in csv_bytes
        assert b"Proveedor SL" in csv_bytes
```

- [ ] **Step 2: Create the export service**

Create `backend/app/services/contabilidad_export_service.py`:

```python
"""
Contabilidad Export Service.

Exports accounting books to CSV and Excel formats.
"""
import csv
import io
import logging
from typing import Optional

try:
    from openpyxl import Workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

logger = logging.getLogger(__name__)


class ContabilidadExportService:
    """Exports accounting data to CSV/Excel."""

    @staticmethod
    def libro_diario_to_csv(entries: list[dict]) -> bytes:
        """Export Libro Diario to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Fecha", "N Asiento", "Cuenta", "Nombre Cuenta", "Debe", "Haber", "Concepto"])
        for e in entries:
            writer.writerow([
                e["fecha"], e["numero_asiento"], e["cuenta_code"],
                e["cuenta_nombre"], e["debe"], e["haber"], e["concepto"],
            ])
        return output.getvalue().encode("utf-8")

    @staticmethod
    def libro_mayor_to_csv(mayor: list[dict]) -> bytes:
        """Export Libro Mayor to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Cuenta", "Nombre", "Total Debe", "Total Haber", "Saldo"])
        for m in mayor:
            writer.writerow([
                m["cuenta_code"], m["cuenta_nombre"],
                m["total_debe"], m["total_haber"], m["saldo"],
            ])
        return output.getvalue().encode("utf-8")

    @staticmethod
    def libro_registro_to_csv(facturas: list[dict]) -> bytes:
        """Export Libro Registro de Facturas to CSV (formato AEAT)."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Fecha", "N Factura", "Tipo", "NIF Emisor", "Emisor",
            "NIF Receptor", "Receptor", "Base Imponible", "Tipo IVA %",
            "Cuota IVA", "Retencion IRPF", "Total", "Cuenta PGC", "Descripcion",
        ])
        for f in facturas:
            writer.writerow([
                f.get("fecha_factura", ""), f.get("numero_factura", ""),
                f.get("tipo", ""), f.get("emisor_nif", ""), f.get("emisor_nombre", ""),
                f.get("receptor_nif", ""), f.get("receptor_nombre", ""),
                f.get("base_imponible", 0), f.get("tipo_iva", 0),
                f.get("cuota_iva", 0), f.get("retencion_irpf", 0),
                f.get("total", 0), f.get("cuenta_pgc", ""),
                f.get("cuenta_pgc_nombre", ""),
            ])
        return output.getvalue().encode("utf-8")

    @staticmethod
    def libro_diario_to_excel(entries: list[dict]) -> bytes:
        """Export Libro Diario to Excel."""
        if not OPENPYXL_AVAILABLE:
            raise RuntimeError("openpyxl not installed")
        wb = Workbook()
        ws = wb.active
        ws.title = "Libro Diario"
        ws.append(["Fecha", "N Asiento", "Cuenta", "Nombre Cuenta", "Debe", "Haber", "Concepto"])
        for e in entries:
            ws.append([
                e["fecha"], e["numero_asiento"], e["cuenta_code"],
                e["cuenta_nombre"], e["debe"], e["haber"], e["concepto"],
            ])
        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()

    @staticmethod
    def libro_mayor_to_excel(mayor: list[dict]) -> bytes:
        """Export Libro Mayor to Excel."""
        if not OPENPYXL_AVAILABLE:
            raise RuntimeError("openpyxl not installed")
        wb = Workbook()
        ws = wb.active
        ws.title = "Libro Mayor"
        ws.append(["Cuenta", "Nombre", "Total Debe", "Total Haber", "Saldo"])
        for m in mayor:
            ws.append([m["cuenta_code"], m["cuenta_nombre"], m["total_debe"], m["total_haber"], m["saldo"]])
        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()

    @staticmethod
    def pyg_to_excel(pyg: dict) -> bytes:
        """Export Cuenta de Perdidas y Ganancias to Excel."""
        if not OPENPYXL_AVAILABLE:
            raise RuntimeError("openpyxl not installed")
        wb = Workbook()
        ws = wb.active
        ws.title = "PyG"
        ws.append(["CUENTA DE PERDIDAS Y GANANCIAS", "", pyg["year"]])
        ws.append([])
        ws.append(["INGRESOS"])
        ws.append(["Cuenta", "Nombre", "Importe"])
        for i in pyg["ingresos"]:
            ws.append([i["cuenta_code"], i["cuenta_nombre"], i["total_haber"] - i["total_debe"]])
        ws.append(["", "TOTAL INGRESOS", pyg["total_ingresos"]])
        ws.append([])
        ws.append(["GASTOS"])
        ws.append(["Cuenta", "Nombre", "Importe"])
        for g in pyg["gastos"]:
            ws.append([g["cuenta_code"], g["cuenta_nombre"], g["total_debe"] - g["total_haber"]])
        ws.append(["", "TOTAL GASTOS", pyg["total_gastos"]])
        ws.append([])
        ws.append(["", "RESULTADO DEL EJERCICIO", pyg["resultado"]])
        ws.append([])
        ws.append([pyg["disclaimer"]])
        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()
```

- [ ] **Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_contabilidad_export.py -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/contabilidad_export_service.py backend/tests/test_contabilidad_export.py
git commit -m "feat: ContabilidadExportService — CSV/Excel export for all accounting books"
```

---

## Task 8: Invoices Router (REST endpoints)

**Files:**
- Create: `backend/app/routers/invoices.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create invoices router**

Create `backend/app/routers/invoices.py`:

```python
"""
Invoices Router — Upload, classify, and manage invoices.

Auth required. Plan Autonomo only.
Rate limit: 10 uploads/minute.
"""
import uuid
import json
import logging
from math import ceil
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Query
from pydantic import BaseModel, Field

from app.auth.jwt_handler import get_current_user, TokenData
from app.auth.subscription_guard import require_active_subscription
from app.services.subscription_service import SubscriptionAccess
from app.database.turso_client import get_db_client
from app.config import settings
from app.security.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/invoices", tags=["invoices"])

ALLOWED_MIME_TYPES = {
    "application/pdf": b"%PDF",
    "image/jpeg": b"\xff\xd8",
    "image/png": b"\x89PNG",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class InvoiceResponse(BaseModel):
    id: str
    numero_factura: str
    fecha_factura: str
    tipo: str
    emisor_nombre: str
    emisor_nif: str
    receptor_nombre: str
    receptor_nif: str
    base_imponible: float
    tipo_iva: float
    cuota_iva: float
    total: float
    cuenta_pgc: Optional[str] = None
    cuenta_pgc_nombre: Optional[str] = None
    clasificacion_confianza: Optional[str] = None
    trimestre: int
    year: int


class ReclassifyRequest(BaseModel):
    cuenta_pgc: str = Field(..., description="New PGC account code")
    cuenta_pgc_nombre: str = Field(..., description="New PGC account name")


def _get_trimestre(month: int) -> int:
    return ceil(month / 3)


@router.post("/upload")
@limiter.limit("10/minute")
async def upload_invoice(
    request: Request,
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
    access: SubscriptionAccess = Depends(require_active_subscription),
):
    """Upload an invoice, extract data with Gemini, classify PGC, create journal entry."""
    # Plan check
    if access.plan_type not in ("autonomo", "creator") and not access.is_owner:
        raise HTTPException(403, "Se requiere plan Autonomo o Creator para el clasificador de facturas.")

    # Read file
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(413, f"Archivo demasiado grande. Maximo {MAX_FILE_SIZE // (1024*1024)} MB.")

    # Validate mime type + magic bytes
    mime = file.content_type or ""
    if mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, f"Tipo de archivo no soportado: {mime}. Use PDF, JPG o PNG.")

    expected_magic = ALLOWED_MIME_TYPES[mime]
    if not file_bytes[:len(expected_magic)] == expected_magic:
        raise HTTPException(400, "El contenido del archivo no coincide con su tipo declarado.")

    # OCR extraction
    from app.services.invoice_ocr_service import InvoiceOCRService
    api_key = settings.GOOGLE_GEMINI_API_KEY
    if not api_key:
        raise HTTPException(500, "Servicio de OCR no configurado. Contacte al administrador.")

    ocr_service = InvoiceOCRService(api_key=api_key, model=settings.GEMINI_MODEL)
    try:
        extraction = await ocr_service.extract_from_bytes(file_bytes, mime)
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        raise HTTPException(500, "Error al procesar la factura. Intente con otro formato o revise la calidad de la imagen.")

    factura = extraction.factura

    # PGC Classification
    db = await get_db_client()
    from app.services.invoice_classifier_service import InvoiceClassifierService
    classifier = InvoiceClassifierService(api_key=api_key, db=db, model=settings.GEMINI_MODEL)
    try:
        clasificacion = await classifier.classify(
            concepto=factura.lineas[0].concepto if factura.lineas else "",
            emisor_nombre=factura.emisor.nombre,
            tipo=factura.tipo,
            base_imponible=factura.base_imponible_total,
        )
    except Exception as e:
        logger.error(f"PGC classification failed: {e}")
        clasificacion = None

    # Parse date for trimestre/year
    try:
        parts = factura.fecha_factura.split("-")
        year = int(parts[0])
        month = int(parts[1])
        trimestre = _get_trimestre(month)
    except (ValueError, IndexError):
        year = 2026
        trimestre = 1

    # Save to libro_registro
    registro_id = str(uuid.uuid4())
    async with db.connect() as conn:
        await conn.execute(
            """INSERT INTO libro_registro
               (id, user_id, tipo, numero_factura, fecha_factura, fecha_operacion,
                emisor_nif, emisor_nombre, receptor_nif, receptor_nombre,
                concepto, base_imponible, tipo_iva, cuota_iva,
                tipo_re, cuota_re, retencion_irpf_pct, retencion_irpf,
                total, cuenta_pgc, cuenta_pgc_nombre, clasificacion_confianza,
                trimestre, year, raw_extraction)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                registro_id, current_user.user_id, factura.tipo,
                factura.numero_factura, factura.fecha_factura, factura.fecha_operacion,
                factura.emisor.nif_cif, factura.emisor.nombre,
                factura.receptor.nif_cif, factura.receptor.nombre,
                factura.lineas[0].concepto if factura.lineas else "",
                factura.base_imponible_total, factura.tipo_iva_pct, factura.cuota_iva,
                factura.tipo_re_pct, factura.cuota_re,
                factura.retencion_irpf_pct, factura.retencion_irpf,
                factura.total,
                clasificacion.cuenta_code if clasificacion else None,
                clasificacion.cuenta_nombre if clasificacion else None,
                clasificacion.confianza if clasificacion else None,
                trimestre, year,
                json.dumps(factura.model_dump(), ensure_ascii=False),
            ],
        )

        # Generate and save journal entry
        if clasificacion:
            from app.services.contabilidad_service import ContabilidadService
            contabilidad = ContabilidadService(db=conn)
            lines = ContabilidadService.generate_asiento_lines(
                tipo=factura.tipo,
                cuenta_pgc_code=clasificacion.cuenta_code,
                cuenta_pgc_nombre=clasificacion.cuenta_nombre,
                base_imponible=factura.base_imponible_total,
                cuota_iva=factura.cuota_iva,
                total=factura.total,
                retencion_irpf=factura.retencion_irpf,
                concepto=factura.lineas[0].concepto if factura.lineas else factura.numero_factura,
            )
            await contabilidad.save_asiento(
                user_id=current_user.user_id,
                libro_registro_id=registro_id,
                fecha=factura.fecha_factura,
                lines=lines,
                year=year,
                trimestre=trimestre,
            )

        await conn.commit()

    return {
        "id": registro_id,
        "factura": factura.model_dump(),
        "clasificacion": clasificacion.model_dump() if clasificacion else None,
        "validacion": {
            "confianza": extraction.confianza,
            "errores": extraction.errores_validacion,
            "nif_emisor_valido": extraction.nif_emisor_valido,
            "nif_receptor_valido": extraction.nif_receptor_valido,
        },
    }


@router.get("")
async def list_invoices(
    request: Request,
    year: int = Query(default=2026),
    trimestre: Optional[int] = Query(default=None),
    tipo: Optional[str] = Query(default=None),
    current_user: TokenData = Depends(get_current_user),
    access: SubscriptionAccess = Depends(require_active_subscription),
):
    """List user's invoices with optional filters."""
    db = await get_db_client()
    query = "SELECT * FROM libro_registro WHERE user_id = ? AND year = ?"
    params = [current_user.user_id, year]
    if trimestre:
        query += " AND trimestre = ?"
        params.append(trimestre)
    if tipo:
        query += " AND tipo = ?"
        params.append(tipo)
    query += " ORDER BY fecha_factura DESC"

    result = await db.execute(query, params)
    return {"invoices": [dict(r) for r in (result.rows or [])]}


@router.get("/{invoice_id}")
async def get_invoice(
    request: Request,
    invoice_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    """Get invoice detail with journal entry."""
    db = await get_db_client()
    result = await db.execute(
        "SELECT * FROM libro_registro WHERE id = ? AND user_id = ?",
        [invoice_id, current_user.user_id],
    )
    rows = result.rows or []
    if not rows:
        raise HTTPException(404, "Factura no encontrada.")

    # Get journal entry
    asientos = await db.execute(
        "SELECT * FROM asientos_contables WHERE libro_registro_id = ? ORDER BY cuenta_code",
        [invoice_id],
    )

    return {
        "invoice": dict(rows[0]),
        "asiento": [dict(a) for a in (asientos.rows or [])],
    }


@router.put("/{invoice_id}/reclassify")
async def reclassify_invoice(
    request: Request,
    invoice_id: str,
    body: ReclassifyRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """Reclassify an invoice (user feedback/correction)."""
    db = await get_db_client()

    # Verify ownership
    result = await db.execute(
        "SELECT * FROM libro_registro WHERE id = ? AND user_id = ?",
        [invoice_id, current_user.user_id],
    )
    rows = result.rows or []
    if not rows:
        raise HTTPException(404, "Factura no encontrada.")

    invoice = dict(rows[0])

    async with db.connect() as conn:
        # Update classification
        await conn.execute(
            "UPDATE libro_registro SET cuenta_pgc = ?, cuenta_pgc_nombre = ?, clasificacion_confianza = 'manual' WHERE id = ?",
            [body.cuenta_pgc, body.cuenta_pgc_nombre, invoice_id],
        )

        # Delete old journal entries
        await conn.execute("DELETE FROM asientos_contables WHERE libro_registro_id = ?", [invoice_id])

        # Regenerate journal entry with new classification
        from app.services.contabilidad_service import ContabilidadService
        contabilidad = ContabilidadService(db=conn)
        lines = ContabilidadService.generate_asiento_lines(
            tipo=invoice["tipo"],
            cuenta_pgc_code=body.cuenta_pgc,
            cuenta_pgc_nombre=body.cuenta_pgc_nombre,
            base_imponible=invoice["base_imponible"],
            cuota_iva=invoice["cuota_iva"] or 0,
            total=invoice["total"],
            retencion_irpf=invoice.get("retencion_irpf"),
            concepto=invoice.get("concepto", ""),
        )
        await contabilidad.save_asiento(
            user_id=current_user.user_id,
            libro_registro_id=invoice_id,
            fecha=invoice["fecha_factura"],
            lines=lines,
            year=invoice["year"],
            trimestre=invoice["trimestre"],
        )
        await conn.commit()

    return {"status": "reclassified", "cuenta_pgc": body.cuenta_pgc}


@router.delete("/{invoice_id}")
async def delete_invoice(
    request: Request,
    invoice_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    """Delete an invoice and its journal entries (GDPR cascade)."""
    db = await get_db_client()
    result = await db.execute(
        "SELECT id FROM libro_registro WHERE id = ? AND user_id = ?",
        [invoice_id, current_user.user_id],
    )
    if not (result.rows or []):
        raise HTTPException(404, "Factura no encontrada.")

    async with db.connect() as conn:
        await conn.execute("DELETE FROM asientos_contables WHERE libro_registro_id = ?", [invoice_id])
        await conn.execute("DELETE FROM libro_registro WHERE id = ?", [invoice_id])
        await conn.commit()

    return {"status": "deleted"}
```

- [ ] **Step 2: Register router in main.py**

Add at the end of the router registrations in `backend/app/main.py` (after the plusvalia router, around line 508):

```python
# Invoice Classifier + Contabilidad
from app.routers.invoices import router as invoices_router
app.include_router(invoices_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/invoices.py backend/app/main.py
git commit -m "feat: invoices router — upload, list, reclassify, delete with Gemini OCR + PGC"
```

---

## Task 9: Contabilidad Router (Books + Export)

**Files:**
- Create: `backend/app/routers/contabilidad.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create contabilidad router**

Create `backend/app/routers/contabilidad.py`:

```python
"""
Contabilidad Router — Accounting books and export.

Auth required. Plan Autonomo only.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
import io

from app.auth.jwt_handler import get_current_user, TokenData
from app.auth.subscription_guard import require_active_subscription
from app.services.subscription_service import SubscriptionAccess
from app.database.turso_client import get_db_client
from app.services.contabilidad_service import ContabilidadService
from app.services.contabilidad_export_service import ContabilidadExportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contabilidad", tags=["contabilidad"])


@router.get("/libro-diario")
async def get_libro_diario(
    request: Request,
    year: int = Query(default=2026),
    trimestre: Optional[int] = Query(default=None),
    current_user: TokenData = Depends(get_current_user),
    access: SubscriptionAccess = Depends(require_active_subscription),
):
    """Get Libro Diario (journal entries)."""
    db = await get_db_client()
    service = ContabilidadService(db=db)
    entries = await service.get_libro_diario(current_user.user_id, year, trimestre)
    return {"entries": entries, "year": year, "trimestre": trimestre}


@router.get("/libro-mayor")
async def get_libro_mayor(
    request: Request,
    year: int = Query(default=2026),
    current_user: TokenData = Depends(get_current_user),
    access: SubscriptionAccess = Depends(require_active_subscription),
):
    """Get Libro Mayor (ledger by account)."""
    db = await get_db_client()
    service = ContabilidadService(db=db)
    mayor = await service.get_libro_mayor(current_user.user_id, year)
    return {"accounts": mayor, "year": year}


@router.get("/balance")
async def get_balance(
    request: Request,
    year: int = Query(default=2026),
    current_user: TokenData = Depends(get_current_user),
    access: SubscriptionAccess = Depends(require_active_subscription),
):
    """Get Balance de Sumas y Saldos."""
    db = await get_db_client()
    service = ContabilidadService(db=db)
    return await service.get_balance_sumas_saldos(current_user.user_id, year)


@router.get("/pyg")
async def get_pyg(
    request: Request,
    year: int = Query(default=2026),
    current_user: TokenData = Depends(get_current_user),
    access: SubscriptionAccess = Depends(require_active_subscription),
):
    """Get Cuenta de Perdidas y Ganancias."""
    db = await get_db_client()
    service = ContabilidadService(db=db)
    return await service.get_pyg(current_user.user_id, year)


@router.get("/export/{libro}")
async def export_libro(
    request: Request,
    libro: str,
    year: int = Query(default=2026),
    trimestre: Optional[int] = Query(default=None),
    format: str = Query(default="csv"),
    current_user: TokenData = Depends(get_current_user),
    access: SubscriptionAccess = Depends(require_active_subscription),
):
    """Export accounting book as CSV or Excel.

    libro: libro-diario, libro-mayor, libro-registro, pyg, balance
    format: csv, excel
    """
    db = await get_db_client()
    service = ContabilidadService(db=db)

    if libro == "libro-diario":
        data = await service.get_libro_diario(current_user.user_id, year, trimestre)
        if format == "excel":
            content = ContabilidadExportService.libro_diario_to_excel(data)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ext = "xlsx"
        else:
            content = ContabilidadExportService.libro_diario_to_csv(data)
            media_type = "text/csv"
            ext = "csv"

    elif libro == "libro-mayor":
        data = await service.get_libro_mayor(current_user.user_id, year)
        if format == "excel":
            content = ContabilidadExportService.libro_mayor_to_excel(data)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ext = "xlsx"
        else:
            content = ContabilidadExportService.libro_mayor_to_csv(data)
            media_type = "text/csv"
            ext = "csv"

    elif libro == "libro-registro":
        result = await db.execute(
            "SELECT * FROM libro_registro WHERE user_id = ? AND year = ? ORDER BY fecha_factura",
            [current_user.user_id, year],
        )
        data = [dict(r) for r in (result.rows or [])]
        content = ContabilidadExportService.libro_registro_to_csv(data)
        media_type = "text/csv"
        ext = "csv"

    elif libro == "pyg":
        pyg = await service.get_pyg(current_user.user_id, year)
        if format == "excel":
            content = ContabilidadExportService.pyg_to_excel(pyg)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ext = "xlsx"
        else:
            # Simple CSV for PyG
            content = ContabilidadExportService.libro_mayor_to_csv(pyg["gastos"] + pyg["ingresos"])
            media_type = "text/csv"
            ext = "csv"

    else:
        from fastapi import HTTPException
        raise HTTPException(400, f"Libro no reconocido: {libro}. Use: libro-diario, libro-mayor, libro-registro, pyg")

    filename = f"{libro}_{year}"
    if trimestre:
        filename += f"_T{trimestre}"
    filename += f".{ext}"

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 2: Register in main.py**

Add after the invoices router registration:

```python
from app.routers.contabilidad import router as contabilidad_router
app.include_router(contabilidad_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/contabilidad.py backend/app/main.py
git commit -m "feat: contabilidad router — libro diario, mayor, balance, PyG, CSV/Excel export"
```

---

## Task 10: Integration Test + GOOGLE_GEMINI_API_KEY in .env

**Files:**
- Modify: `.env` (add GOOGLE_GEMINI_API_KEY)
- Run: Full test suite

- [ ] **Step 1: Add env var to .env**

Add to `.env` file (root of project):

```
# Google Gemini (Invoice OCR — Phase 3)
GOOGLE_GEMINI_API_KEY=your-api-key-here
```

The user will replace `your-api-key-here` with their actual Vertex AI key.

- [ ] **Step 2: Run all new tests**

Run: `cd backend && python -m pytest tests/test_invoice_ocr.py tests/test_invoice_classifier.py tests/test_contabilidad.py tests/test_contabilidad_export.py -v`
Expected: All PASS

- [ ] **Step 3: Run full test suite for regression**

Run: `cd backend && python -m pytest tests/ -v --tb=short 2>&1 | tail -20`
Expected: ~1700+ tests PASS, 0 FAIL

- [ ] **Step 4: Commit .env.example update**

Do NOT commit the actual .env with the real key. Only update `.env.example` if it exists.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: Phase 3 — invoice classifier + contabilidad PGC (Gemini 3 Flash Vision)"
```

---

## Summary

| Task | Component | New Files | Tests |
|------|-----------|-----------|-------|
| 1 | Config + deps | 0 | 0 |
| 2 | DB schema (3 tables) | 0 | 0 |
| 3 | PGC seed script | 1 | manual |
| 4 | Invoice OCR Service | 2 | ~10 |
| 5 | Invoice Classifier | 2 | ~4 |
| 6 | Contabilidad Service | 2 | ~6 |
| 7 | Export Service | 2 | ~3 |
| 8 | Invoices Router | 1 | 0 (integration) |
| 9 | Contabilidad Router | 1 | 0 (integration) |
| 10 | Integration + env | 0 | regression |
| **Total** | | **11 new files** | **~23+ tests** |
