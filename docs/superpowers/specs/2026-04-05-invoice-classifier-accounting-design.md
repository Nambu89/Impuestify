# Clasificador de Facturas + Contabilidad PGC — Design Spec

> Fecha: 2026-04-05
> ADRs: ADR-009 (Gemini 3 Flash OCR), ADR-010 (Contabilidad completa)
> Phase: 3 del roadmap-contabilidad-2026-Q2
> Prerequisitos: Phase 1 completada (model obligations + umbrales)

---

## Objetivo

Permitir a usuarios autonomos subir facturas (PDF/foto), extraer datos automaticamente con Gemini 3 Flash Vision, clasificarlas en cuentas del Plan General Contable (PGC), generar asientos contables, y exportar libros oficiales para el Registro Mercantil.

## Arquitectura

```
Usuario sube factura (PDF/JPG/PNG)
       |
       v
[1] InvoiceOCRService (Gemini 3 Flash Vision)
    - Extrae campos: emisor, receptor, NIF, fecha, lineas, IVA, total
    - Output: Pydantic model `FacturaExtraida`
       |
       v
[2] InvoiceValidationService
    - NIF checksum (DNI letra, CIF digito control)
    - Cuadre IVA: base * tipo% == cuota (±0.02 EUR)
    - Cuadre total: base + IVA + RE - IRPF == total
    - Output: confianza alta/media/baja + lista errores
       |
       v
[3] InvoiceClassifierService (Gemini 3 Flash o gpt-5-mini)
    - Clasifica en cuenta PGC (6xx gasto, 7xx ingreso)
    - Input: datos factura + perfil usuario (CNAE) + top 20 cuentas candidatas
    - Output: cuenta PGC + confianza + alternativas
       |
       v
[4] ContabilidadService
    - Genera asiento contable (Libro Diario: debe/haber)
    - Actualiza saldos (Libro Mayor)
    - Almacena en BD
       |
       v
[5] ExportService
    - Libro Registro Facturas (CSV formato AEAT)
    - Libro Diario (CSV/Excel)
    - Libro Mayor (CSV/Excel)
    - Balance de Sumas y Saldos (PDF/Excel)
    - Cuenta de Perdidas y Ganancias (PDF/Excel)
```

## Motor OCR: Gemini 3 Flash Vision

**Modelo:** `gemini-3-flash-preview`
**SDK:** `google-genai` (nuevo SDK unificado de Google)
**Coste:** $0.50/1M input, $3/1M output → ~$0.0003/factura

### Schema de extraccion

```python
from pydantic import BaseModel, Field

class EmisorReceptor(BaseModel):
    nif_cif: str = Field(description="NIF o CIF")
    nombre: str = Field(description="Razon social o nombre completo")
    direccion: str | None = None

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
    fecha_operacion: str | None = None
    lineas: list[LineaFactura]
    base_imponible_total: float
    tipo_iva_pct: float = Field(description="21, 10, 4 o 0")
    cuota_iva: float
    tipo_re_pct: float | None = None
    cuota_re: float | None = None
    retencion_irpf_pct: float | None = None
    retencion_irpf: float | None = None
    total: float
    tipo: str = Field(description="emitida o recibida")
```

### Llamada a Gemini

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=settings.GOOGLE_GEMINI_API_KEY)

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=[
        types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
        "Extrae todos los datos de esta factura espanola. JSON estricto segun schema. "
        "Fechas en YYYY-MM-DD. Importes en EUR con 2 decimales. "
        "Si un campo no aparece, usa null.",
    ],
    config={
        "response_mime_type": "application/json",
        "response_json_schema": FacturaExtraida.model_json_schema(),
    },
)
factura = FacturaExtraida.model_validate_json(response.text)
```

### Fallback

Si Gemini falla (error 5xx, timeout, rate limit), retry 3 veces con backoff exponencial. Si sigue fallando, intentar con gpt-5-mini (ya integrado en el proyecto).

## Clasificacion PGC

### Cuentas del PGC

Tabla `pgc_accounts` con ~200 cuentas mas comunes:

| Grupo | Tipo | Ejemplo |
|-------|------|---------|
| 1xx | Balance: Financiacion basica | 170 Deudas LP entidades credito |
| 2xx | Balance: Inmovilizado | 218 Elementos transporte |
| 3xx | Balance: Existencias | 300 Mercaderias |
| 4xx | Balance: Acreedores/Deudores | 400 Proveedores, 430 Clientes |
| 5xx | Balance: Cuentas financieras | 572 Bancos c/c |
| 6xx | PyG: Gastos | 621 Arrendamientos, 629 Otros servicios |
| 7xx | PyG: Ingresos | 700 Ventas mercaderias, 705 Prestacion servicios |

### Logica de clasificacion

Segundo prompt a Gemini 3 Flash (texto, sin vision):

```
Dado esta factura:
- Emisor: {emisor_nombre} ({emisor_nif})
- Concepto: {lineas[0].concepto}
- Tipo: {tipo} (emitida/recibida)

Y el perfil del usuario:
- Actividad: {cnae} / {iae}
- Tipo: autonomo/sociedad

Clasifica en una cuenta del PGC. Opciones mas probables:
{top_20_cuentas_por_keywords}

Responde con: {"cuenta_code": "629", "cuenta_nombre": "Otros servicios", "confianza": "alta"}
```

Si confianza < alta → mostrar alternativas al usuario para que confirme.

## Contabilidad: Asientos y Libros

### Asiento contable por factura

**Factura recibida (gasto):**
```
Debe:  6xx (Gasto, base imponible)
Debe:  472 (HP IVA soportado, cuota IVA)
Haber: 400/410 (Proveedor, total factura)
```

Si hay IRPF:
```
Debe:  6xx (Gasto, base)
Debe:  472 (HP IVA soportado)
Haber: 4751 (HP acreedora retenciones, retencion IRPF)
Haber: 400 (Proveedor, total - retencion)
```

**Factura emitida (ingreso):**
```
Debe:  430 (Cliente, total factura)
Haber: 7xx (Ingreso, base imponible)
Haber: 477 (HP IVA repercutido, cuota IVA)
```

### Tabla `asientos_contables`

```sql
CREATE TABLE IF NOT EXISTS asientos_contables (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    libro_registro_id TEXT REFERENCES libro_registro(id),
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
);
```

### Libros exportables

| Libro | Contenido | Formato | Destinatario |
|-------|-----------|---------|-------------|
| Libro Registro Facturas Emitidas | Todas las facturas emitidas | CSV (formato AEAT) | AEAT (Modelo 303) |
| Libro Registro Facturas Recibidas | Todas las facturas recibidas | CSV (formato AEAT) | AEAT (Modelo 303) |
| Libro Diario | Asientos cronologicos (debe/haber) | Excel | Registro Mercantil |
| Libro Mayor | Saldos por cuenta PGC | Excel | Registro Mercantil |
| Balance de Sumas y Saldos | Resumen por cuenta: sumas debe/haber + saldo | Excel/PDF | Registro Mercantil |
| Cuenta de Perdidas y Ganancias | Ingresos (7xx) - Gastos (6xx) = Resultado | Excel/PDF | Registro Mercantil |

## Tablas BD

### libro_registro (ya planificada, sin cambios)

Mantiene la estructura definida en el roadmap original.

### asientos_contables (NUEVA)

Un asiento por cada linea contable (multiples filas por factura). La suma de debe == suma de haber para cada factura.

### pgc_accounts (ya planificada, ampliar)

Ampliar de ~150 cuentas (solo 6xx/7xx) a ~200 cuentas (grupos 1-7) para soportar asientos completos con cuentas de balance.

## Endpoints API

| Metodo | Ruta | Auth | Plan | Descripcion |
|--------|------|------|------|-------------|
| POST | `/api/invoices/upload` | Si | Autonomo | Sube factura, extrae datos, clasifica PGC, genera asiento |
| GET | `/api/invoices` | Si | Autonomo | Lista facturas del usuario (con filtros year/trimestre/tipo) |
| GET | `/api/invoices/{id}` | Si | Autonomo | Detalle factura + asiento contable |
| PUT | `/api/invoices/{id}/reclassify` | Si | Autonomo | Corregir clasificacion PGC (feedback) |
| DELETE | `/api/invoices/{id}` | Si | Autonomo | Borrar factura + asiento (GDPR cascade) |
| GET | `/api/contabilidad/libro-diario` | Si | Autonomo | Libro Diario (filtros year/trimestre) |
| GET | `/api/contabilidad/libro-mayor` | Si | Autonomo | Libro Mayor por cuenta |
| GET | `/api/contabilidad/balance` | Si | Autonomo | Balance Sumas y Saldos |
| GET | `/api/contabilidad/pyg` | Si | Autonomo | Cuenta de Perdidas y Ganancias |
| GET | `/api/contabilidad/export/{libro}` | Si | Autonomo | Exportar libro en CSV/Excel |

## Frontend

### Pagina `/clasificador-facturas`

- Zona upload drag & drop (PDF/JPG/PNG, max 10MB)
- Tras upload: muestra datos extraidos + clasificacion PGC sugerida
- Botones: confirmar / corregir cuenta PGC / descartar
- Vista lista de facturas (tabla con filtros trimestre/tipo)

### Pagina `/contabilidad`

- Tabs: Libro Diario | Libro Mayor | Balance | PyG
- Filtros: ano, trimestre
- Boton exportar (CSV/Excel) en cada tab
- Resumen visual: total gastos, total ingresos, resultado

## Seguridad

- Auth requerida + plan Autonomo (Depends(get_current_user) + check plan)
- Rate limit: 10 uploads/min (slowapi)
- File validation: magic bytes (PDF: %PDF, JPEG: FF D8, PNG: 89 50)
- Max size: 10MB por archivo
- GDPR: DELETE cascade en facturas + asientos + libro_registro
- Datos factura cifrados en transito (HTTPS) — no cifrado at rest en Turso (evaluar si necesario)

## Configuracion

```python
# backend/app/config.py
GOOGLE_GEMINI_API_KEY: str = ""  # Vertex AI habilitado
GEMINI_MODEL: str = "gemini-3-flash-preview"
INVOICE_MAX_SIZE_MB: int = 10
INVOICE_RATE_LIMIT: str = "10/minute"
INVOICE_FALLBACK_MODEL: str = "gpt-5-mini"  # Si Gemini falla
```

## Disclaimer legal

TODAS las paginas de contabilidad deben mostrar:

> "Herramienta de apoyo contable. La informacion generada es orientativa y no sustituye el asesoramiento de un profesional contable. Impuestify no es responsable de errores en la clasificacion automatica. Revise siempre los asientos antes de depositarlos en el Registro Mercantil."

## Dependencias nuevas

- `google-genai` — SDK Gemini (invoice OCR)
- `openpyxl` — Exportacion Excel (ya instalado? verificar)
- `tenacity` — Retry con backoff (ya instalado? verificar)

## Fuera de scope

- Facturacion (emitir facturas) — no es objetivo de esta fase
- Conciliacion bancaria — futuro
- Amortizaciones automaticas — futuro
- Impuesto de Sociedades (Modelo 200) — futuro
- Formato XBRL para Registro Mercantil — futuro (requiere parser XBRL, evaluar en Q3)
