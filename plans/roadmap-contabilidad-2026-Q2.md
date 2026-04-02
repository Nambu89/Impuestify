# Roadmap Contabilidad & Verticales 2026-Q2

> Fecha: 2026-03-31
> Estado: PLANIFICADO
> Sesion origen: 25 (research contabilidad + territorio plugins)
> Prerequisito: Territory plugin system (`backend/app/territories/`) DONE

---

## Resumen Ejecutivo

5 features organizadas en 3 fases, de menor a mayor complejidad. La Fase 1 usa infraestructura existente (territory plugins, calculadoras). La Fase 2 abre un vertical nuevo (farmacias). La Fase 3 introduce OCR + clasificacion IA (mayor esfuerzo).

**Estimacion total:** ~8-12 sesiones de desarrollo

---

## FASE 1: Quick Wins (sin nueva infra)

**Estimacion:** 2-3 sesiones | **Dependencias externas:** ninguna

### 1A. Asesor de Obligaciones Fiscales ("Que modelos tienes que presentar")

> El usuario introduce su perfil (CCAA, autonomo/sociedad/particular, actividad) y recibe la lista completa de modelos que debe presentar con fechas limite.

#### Tareas Backend

| ID | Tarea | Archivo(s) | Complejidad | Parallelizable |
|----|-------|-----------|-------------|----------------|
| 1A-B1 | Crear `ModelObligation` dataclass en base.py del territory plugin | `backend/app/territories/base.py` | Baja | Si |
| 1A-B2 | Anadir metodo abstracto `get_model_obligations(profile)` a `TerritoryPlugin` | `backend/app/territories/base.py` | Baja | Con 1A-B1 |
| 1A-B3 | Implementar `get_model_obligations()` en `CommonTerritory` | `backend/app/territories/comun/plugin.py` | Media | Tras 1A-B2 |
| 1A-B4 | Implementar `get_model_obligations()` en `CanariasTerritory` (IGIC 420 en vez de 303) | `backend/app/territories/canarias/plugin.py` | Media | Tras 1A-B2 |
| 1A-B5 | Implementar `get_model_obligations()` en `ForalVascoTerritory` (300 Gipuzkoa, 303 Bizkaia/Araba) | `backend/app/territories/foral_vasco/plugin.py` | Media | Tras 1A-B2 |
| 1A-B6 | Implementar `get_model_obligations()` en `ForalNavarraTerritory` (F69 en vez de 303) | `backend/app/territories/foral_navarra/plugin.py` | Media | Tras 1A-B2 |
| 1A-B7 | Implementar `get_model_obligations()` en `CeutaMelillaTerritory` (IPSI, bonificacion 60%) | `backend/app/territories/ceuta_melilla/plugin.py` | Media | Tras 1A-B2 |
| 1A-B8 | Crear endpoint `POST /api/irpf/model-obligations` | `backend/app/routers/irpf_estimate.py` | Media | Tras 1A-B3..B7 |
| 1A-B9 | Crear tests para todas las combinaciones perfil x territorio | `backend/tests/test_model_obligations.py` | Media | Tras 1A-B8 |

**Detalle del dataclass `ModelObligation`:**

```python
@dataclass
class ModelObligation:
    modelo: str            # "303", "130", "100", "420", etc.
    nombre: str            # "IVA trimestral"
    descripcion: str       # "Declaracion trimestral del IVA"
    periodicidad: str      # "trimestral", "anual", "mensual"
    aplica_si: str         # "autonomo", "sociedad", "todos", "retenedor"
    obligatorio: bool      # True si es obligatorio, False si opcional
    deadlines: List[Deadline]  # Lista de fechas limite del ano en curso
    notas: Optional[str]   # Notas especificas del territorio
```

**Logica del metodo `get_model_obligations(profile)`:**

El perfil contiene:
- `situacion_laboral`: "particular" | "autonomo" | "sociedad"
- `actividad_economica`: str (CNAE/IAE)
- `tiene_empleados`: bool
- `tiene_alquileres`: bool
- `tiene_operaciones_intracomunitarias`: bool
- `estimacion`: "directa_simplificada" | "directa_normal" | "objetiva"

Reglas (ejemplo regimen comun):
- Particular: solo Modelo 100 (renta anual)
- Autonomo sin empleados, estimacion directa: 303, 130, 100, (347 si >3005.06 EUR con terceros)
- Autonomo con empleados: + 111, 190
- Autonomo con alquileres: + 115, 180
- Autonomo estimacion objetiva: 131 en vez de 130
- Sociedad: 200, 202 (pagos fraccionados IS), 303, 111, 190
- Operaciones intracomunitarias: + 349

#### Tareas Frontend

| ID | Tarea | Archivo(s) | Complejidad | Parallelizable |
|----|-------|-----------|-------------|----------------|
| 1A-F1 | Crear pagina `ModelObligationsPage.tsx` | `frontend/src/pages/ModelObligationsPage.tsx` | Media | Tras 1A-B8 |
| 1A-F2 | Anadir formulario de perfil rapido (CCAA + situacion + actividad) | Dentro de `ModelObligationsPage.tsx` | Media | Con 1A-F1 |
| 1A-F3 | Mostrar tarjetas de modelos con iconos, deadlines, estado | Dentro de `ModelObligationsPage.tsx` | Media | Con 1A-F1 |
| 1A-F4 | Anadir CSS responsive | `frontend/src/pages/ModelObligationsPage.css` | Baja | Con 1A-F1 |
| 1A-F5 | Registrar ruta `/modelos-obligatorios` en App.tsx | `frontend/src/App.tsx` | Baja | Tras 1A-F1 |
| 1A-F6 | Anadir enlace en Header.tsx (dentro de dropdown "Herramientas") | `frontend/src/components/Header.tsx` | Baja | Tras 1A-F5 |
| 1A-F7 | Anadir seccion en Home.tsx (CTA al asesor de modelos) | `frontend/src/pages/Home.tsx` | Baja | Tras 1A-F5 |

**UX:** Pagina publica (sin login). El usuario selecciona CCAA + situacion laboral + actividad. La pagina muestra en tiempo real (sin submit) la lista de modelos con:
- Nombre y numero del modelo
- Periodicidad (trimestral/anual)
- Proxima fecha limite (con countdown si <15 dias)
- Enlace a sede AEAT para presentacion
- Nota territorial si aplica

**SEO:** Title "Que modelos fiscales tengo que presentar | Impuestify". Meta description orientada a autonomos.

---

### 1B. Calculadora de Umbrales (Normal vs Abreviado vs PYME)

> Input: activo total, cifra negocios, empleados (ultimos 2 anos). Output: tipo de empresa, PGC aplicable, obligacion auditoria.

#### Tareas Backend

| ID | Tarea | Archivo(s) | Complejidad | Parallelizable |
|----|-------|-----------|-------------|----------------|
| 1B-B1 | Crear `backend/app/utils/calculators/company_size.py` con logica de umbrales | `backend/app/utils/calculators/company_size.py` (NUEVO) | Baja | Si |
| 1B-B2 | Crear endpoint `POST /api/irpf/company-size` (publico, sin auth) | `backend/app/routers/irpf_estimate.py` | Baja | Tras 1B-B1 |
| 1B-B3 | Tests de umbrales y edge cases | `backend/tests/test_company_size.py` (NUEVO) | Baja | Tras 1B-B2 |

**Logica de umbrales (2026, con Directiva UE 2023/2775):**

```python
# Umbrales para clasificacion de empresas (Art. 257-258 LSC + Directiva 2023/2775)
# Una empresa es "micro/pequena/mediana" si NO supera 2 de 3 limites durante 2 anos consecutivos

THRESHOLDS_2026 = {
    "micro": {
        "activo_total": 450_000,      # EUR (antes 350K, sube con Directiva)
        "cifra_negocios": 900_000,    # EUR (antes 700K)
        "empleados": 10,
    },
    "pequena": {
        "activo_total": 5_000_000,    # EUR (antes 4M)
        "cifra_negocios": 10_000_000, # EUR (antes 8M)
        "empleados": 50,
    },
    "mediana": {
        "activo_total": 25_000_000,   # EUR (antes 20M)
        "cifra_negocios": 50_000_000, # EUR (antes 40M)
        "empleados": 250,
    },
}

# PGC aplicable
# Micro/Pequena → PGC PYMES (RD 1515/2007) o incluso Microempresas
# Mediana/Grande → PGC Normal (RD 1514/2007)
# Si aplica PGC PYMES → Balance y Memoria abreviados automatico

# Auditoria obligatoria (Art. 263 LSC)
# Superar 2 de 3: activo 2.85M, cifra negocios 5.7M, empleados 50
# Durante 2 ejercicios consecutivos
AUDIT_THRESHOLDS = {
    "activo_total": 2_850_000,
    "cifra_negocios": 5_700_000,
    "empleados": 50,
}
```

**Output del endpoint:**

```json
{
    "clasificacion": "pequena",
    "pgc_aplicable": "PGC PYMES (RD 1515/2007)",
    "balance_abreviado": true,
    "memoria_abreviada": true,
    "auditoria_obligatoria": false,
    "cuenta_perdidas_abreviada": true,
    "notas": [
        "Puede aplicar el PGC de PYMES con balance y memoria abreviados",
        "No esta obligada a depositar el informe de gestion"
    ],
    "umbrales_aplicados": {
        "activo_total": {"valor": 2000000, "limite": 5000000, "supera": false},
        "cifra_negocios": {"valor": 4000000, "limite": 10000000, "supera": false},
        "empleados": {"valor": 30, "limite": 50, "supera": false}
    },
    "disclaimer": "Informacion orientativa. Consulte con un asesor profesional."
}
```

#### Tareas Frontend

| ID | Tarea | Archivo(s) | Complejidad | Parallelizable |
|----|-------|-----------|-------------|----------------|
| 1B-F1 | Crear `CalculadoraUmbralesPage.tsx` con formulario 6 campos (2 anos x 3 datos) | `frontend/src/pages/CalculadoraUmbralesPage.tsx` (NUEVO) | Media | Tras 1B-B2 |
| 1B-F2 | CSS responsive con resultados visuales (barras progreso vs umbral) | `frontend/src/pages/CalculadoraUmbralesPage.css` (NUEVO) | Baja | Con 1B-F1 |
| 1B-F3 | Registrar ruta `/calculadora-umbrales` (publica) en App.tsx | `frontend/src/App.tsx` | Baja | Tras 1B-F1 |
| 1B-F4 | Enlace en Header.tsx + Home.tsx | `frontend/src/components/Header.tsx`, `frontend/src/pages/Home.tsx` | Baja | Tras 1B-F3 |

**UX:** Formulario con 3 inputs por ano (activo, cifra negocios, empleados) x 2 anos. Resultado instantaneo (calculo puede ser frontend-only o con backend para tener disclaimer legal). Mostrar barras visuales de cuanto falta para cada umbral.

---

### Dependencias Fase 1

```
1A-B1 + 1A-B2 ─┬─> 1A-B3 ──┐
                ├─> 1A-B4 ──┤
                ├─> 1A-B5 ──┤
                ├─> 1A-B6 ──┤
                └─> 1A-B7 ──┼─> 1A-B8 ──> 1A-B9
                            │
                            └─> 1A-F1..F4 ──> 1A-F5..F7

1B-B1 ──> 1B-B2 ──> 1B-B3
                └──> 1B-F1..F2 ──> 1B-F3..F4
```

**1A y 1B son totalmente independientes y pueden ejecutarse en paralelo.**

---

## FASE 2: Vertical Farmacias

**Estimacion:** 2-3 sesiones | **Dependencias:** Fase 1A completada (model obligations)

### 2A. Perfil Farmaceutico (Backend)

| ID | Tarea | Archivo(s) | Complejidad | Parallelizable |
|----|-------|-----------|-------------|----------------|
| 2A-B1 | Anadir `"farmaceutico"` como valor valido en `situacion_laboral` (user_profiles) | `backend/app/routers/fiscal_profile.py` | Baja | Si |
| 2A-B2 | Crear constantes CNAE/IAE farmaceutico | `backend/app/utils/pharmacy_constants.py` (NUEVO) | Baja | Si |
| 2A-B3 | Implementar logica Recargo de Equivalencia en modelo 303 | `backend/app/utils/calculators/modelo_303.py` | Alta | Tras 2A-B2 |
| 2A-B4 | Crear seed de deducciones especificas farmacia | `backend/scripts/seed_deductions_pharmacy.py` (NUEVO) | Media | Tras 2A-B2 |
| 2A-B5 | Extender `get_model_obligations()` para perfil farmaceutico (sin 303 si RE puro) | Todos los territory plugins | Media | Tras 2A-B3 |
| 2A-B6 | Anadir contexto farmaceutico al TaxAgent system prompt | `backend/app/agents/tax_agent.py` | Baja | Tras 2A-B2 |
| 2A-B7 | Tests farmaceutico (RE, deducciones, model obligations) | `backend/tests/test_pharmacy.py` (NUEVO) | Media | Tras 2A-B3..B5 |

**Detalle Recargo de Equivalencia:**

```python
# Art. 154-163 LIVA — Regimen Especial de Recargo de Equivalencia
# Aplica a: comerciantes minoristas personas fisicas (farmacias, tiendas)
# CNAE 47.73 (farmacias) / IAE 652.1

# Tipos de RE sobre la base imponible:
RE_RATES = {
    21: 5.2,   # IVA 21% → RE 5.2%
    10: 1.4,   # IVA 10% → RE 1.4%
    4: 0.5,    # IVA  4% → RE 0.5%
}

# Consecuencias:
# - No presenta Modelo 303 (el proveedor cobra IVA + RE)
# - No puede deducir IVA soportado
# - No lleva libro registro de IVA
# - Factura SIN IVA (ticket simplificado)
# - SI presenta Modelo 130/131 de IRPF
```

**Deducciones especificas farmacia:**

| Deduccion | Concepto | Limite |
|-----------|----------|--------|
| Colegio de Farmaceuticos | Cuota colegial obligatoria | 100% deducible |
| RC Profesional | Seguro responsabilidad civil | 100% deducible |
| Formacion continua | Cursos farmacia, congresos | 100% si relacionados |
| Fondo de comercio | Amortizacion compra farmacia | 5% anual (max 20 anos) |
| Local comercial | Alquiler o amortizacion | Segun uso afecto |
| Vehiculo | Si reparto domiciliario | 50% deducible (presuncion) |

### 2B. Perfil Farmaceutico (Frontend)

| ID | Tarea | Archivo(s) | Complejidad | Parallelizable |
|----|-------|-----------|-------------|----------------|
| 2B-F1 | Anadir opcion "Farmaceutico" en wizard guia fiscal (paso 1: situacion laboral) | `frontend/src/pages/TaxGuidePage.tsx` | Baja | Tras 2A-B1 |
| 2B-F2 | Auto-fill CNAE 47.73 / IAE 652.1 cuando se selecciona Farmaceutico | `frontend/src/pages/TaxGuidePage.tsx` | Baja | Con 2B-F1 |
| 2B-F3 | Mostrar nota "Recargo de Equivalencia: no presentas Modelo 303" en resultado | `frontend/src/pages/TaxGuidePage.tsx` | Baja | Tras 2A-B3 |
| 2B-F4 | Adaptar DynamicFiscalForm para campos farmacia | `frontend/src/components/DynamicFiscalForm.tsx` | Media | Tras 2A-B1 |

### 2C. Landing Page Farmacias (SEO)

| ID | Tarea | Archivo(s) | Complejidad | Parallelizable |
|----|-------|-----------|-------------|----------------|
| 2C-F1 | Crear `FarmaciasPage.tsx` landing SEO | `frontend/src/pages/FarmaciasPage.tsx` (NUEVO) | Media | Si (paralelo con 2A) |
| 2C-F2 | CSS con diseno farmacia (colores verde farmacia + blanco) | `frontend/src/pages/FarmaciasPage.css` (NUEVO) | Baja | Con 2C-F1 |
| 2C-F3 | Schema.org structured data (LocalBusiness + Pharmacy) | Dentro de `FarmaciasPage.tsx` | Baja | Con 2C-F1 |
| 2C-F4 | Registrar ruta `/farmacias` (publica) en App.tsx | `frontend/src/App.tsx` | Baja | Tras 2C-F1 |
| 2C-F5 | Anadir enlace en footer Home.tsx | `frontend/src/pages/Home.tsx` | Baja | Tras 2C-F4 |

**Contenido landing `/farmacias`:**

1. Hero: "Impuestos de tu farmacia, resueltos con IA"
2. Pain points: RE complicado, fondo de comercio, cuotas colegiales
3. Features: simulador IRPF para farmacias, RE automatico, deducciones especificas
4. Comparativa: Asesoria tradicional (300+ EUR/mes) vs Impuestify (39 EUR/mes)
5. CTA: "Empezar como Autonomo" → /subscribe
6. SEO keywords: "impuestos farmacia", "recargo equivalencia farmacia", "declaracion renta farmaceutico", "deducciones farmacia"

### 2D. RAG Farmacia

| ID | Tarea | Archivo(s) | Complejidad | Parallelizable |
|----|-------|-----------|-------------|----------------|
| 2D-R1 | Anadir URLs farmacia al crawler watchlist | `backend/scripts/doc_crawler/watchlist.py` | Baja | Si (paralelo con 2A) |
| 2D-R2 | Descargar e ingestar normativa RE (Art. 154-163 LIVA) | Manual + `scripts/ingest_documents.py` | Media | Tras 2D-R1 |
| 2D-R3 | Descargar guias CGCOF (Consejo General Colegios Farmaceuticos) | Manual | Baja | Con 2D-R2 |
| 2D-R4 | Ingestar documentos farmacia con tag `topic: farmacia` | `scripts/ingest_documents.py` | Baja | Tras 2D-R2..R3 |

**URLs a anadir al watchlist:**

```python
# Normativa RE
{"url": "https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740&p=20240101&tn=1#cixlviii",
 "name": "LIVA Art. 154-163 Recargo Equivalencia", "territory": "Estatal"},
# Guia AEAT RE
{"url": "https://sede.agenciatributaria.gob.es/Sede/iva/regimenes-especiales/recargo-equivalencia.html",
 "name": "AEAT Guia Recargo Equivalencia", "territory": "Estatal"},
# Tributacion farmacias
{"url": "https://www.agenciatributaria.es/AEAT.internet/Inicio/La_Agencia_Tributaria/Campanas/_Campanas_/Renta.shtml",
 "name": "AEAT Renta Farmacias", "territory": "Estatal", "status": "future"},
```

### Dependencias Fase 2

```
2A-B1 + 2A-B2 ─┬─> 2A-B3 ──> 2A-B5 ──> 2A-B7
                ├─> 2A-B4 ──────────────> 2A-B7
                ├─> 2A-B6
                └─> 2B-F1..F4

2C-F1..F5 (paralelo con todo 2A/2B)

2D-R1..R4 (paralelo con todo 2A/2B)

Prerequisito: 1A completado (get_model_obligations existe en plugins)
```

---

## FASE 3: Clasificador de Facturas

**Estimacion:** 3-4 sesiones | **Dependencias:** Fase 1 completada. No depende de Fase 2.

### 3A. Pipeline OCR

| ID | Tarea | Archivo(s) | Complejidad | Parallelizable |
|----|-------|-----------|-------------|----------------|
| 3A-B1 | Evaluar OCR: Azure Document Intelligence (ya tenemos key) vs Tesseract local | Research | Media | Si |
| 3A-B2 | Crear `InvoiceOCRService` que recibe PDF/imagen y extrae texto + campos | `backend/app/services/invoice_ocr_service.py` (NUEVO) | Alta | Tras 3A-B1 |
| 3A-B3 | Extender `InvoiceExtractor` existente para usar OCR en imagenes (actualmente solo PDF) | `backend/app/services/invoice_extractor.py` | Media | Tras 3A-B2 |
| 3A-B4 | Endpoint `POST /api/invoices/classify` (auth required, plan Autonomo) | `backend/app/routers/invoices.py` (NUEVO) | Media | Tras 3A-B3 |
| 3A-B5 | Tests OCR con facturas de ejemplo | `backend/tests/test_invoice_ocr.py` (NUEVO) | Media | Tras 3A-B4 |

**Nota:** Ya tenemos `AZURE_DI_ENDPOINT` y `AZURE_DI_API_KEY` configurados (usados para ingesta RAG). Azure DI es la opcion preferida porque:
- Ya pagamos por el servicio
- Soporta facturas espanolas nativamente (prebuilt-invoice model)
- Extrae campos estructurados (emisor, receptor, importes, IVA)

### 3B. Clasificacion PGC

| ID | Tarea | Archivo(s) | Complejidad | Parallelizable |
|----|-------|-----------|-------------|----------------|
| 3B-B1 | Crear tabla `pgc_accounts` con cuentas del PGC (grupo 6xx, 7xx) | `backend/app/database/turso_client.py` (init_schema) | Baja | Si |
| 3B-B2 | Seed de cuentas PGC mas comunes (~150 cuentas) | `backend/scripts/seed_pgc_accounts.py` (NUEVO) | Media | Tras 3B-B1 |
| 3B-B3 | Crear `InvoiceClassifierService` con logica de clasificacion | `backend/app/services/invoice_classifier.py` (NUEVO) | Alta | Tras 3B-B2 |
| 3B-B4 | Prompt engineering: GPT clasifica factura en cuenta PGC | Dentro de `invoice_classifier.py` | Media | Con 3B-B3 |
| 3B-B5 | Sistema de feedback: usuario corrige clasificacion → almacenar para reentrenamiento | `backend/app/services/invoice_classifier.py` | Media | Tras 3B-B3 |
| 3B-B6 | Endpoint `POST /api/invoices/{id}/reclassify` | `backend/app/routers/invoices.py` | Baja | Tras 3B-B5 |
| 3B-B7 | Tests clasificacion | `backend/tests/test_invoice_classifier.py` (NUEVO) | Media | Tras 3B-B3 |

**Esquema tabla `pgc_accounts`:**

```sql
CREATE TABLE IF NOT EXISTS pgc_accounts (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL,          -- "6290"
    name TEXT NOT NULL,          -- "Otros servicios"
    group_code TEXT NOT NULL,    -- "62"
    group_name TEXT NOT NULL,    -- "Servicios exteriores"
    type TEXT NOT NULL,          -- "gasto" | "ingreso"
    description TEXT,            -- Descripcion ampliada
    keywords TEXT,               -- JSON: ["asesoria", "consultoria", "gestor"]
    common_for TEXT,             -- JSON: ["autonomo", "sociedad", "farmacia"]
    is_active BOOLEAN DEFAULT 1
);
```

**Clasificacion por IA:**

```python
# El prompt recibe:
# 1. Datos extraidos de la factura (emisor, concepto, importes)
# 2. Perfil del usuario (actividad economica, CNAE)
# 3. Historial de clasificaciones previas del usuario
# 4. Top 20 cuentas PGC mas probables (pre-filtradas por keywords)
#
# El LLM devuelve:
# - Cuenta PGC sugerida (codigo + nombre)
# - Confianza (alta/media/baja)
# - Justificacion breve
# - Alternativas si confianza < alta
```

### 3C. Libro Registro

| ID | Tarea | Archivo(s) | Complejidad | Parallelizable |
|----|-------|-----------|-------------|----------------|
| 3C-B1 | Crear tabla `libro_registro` (facturas emitidas + recibidas) | `backend/app/database/turso_client.py` | Baja | Si |
| 3C-B2 | Crear `LibroRegistroService` (CRUD + generacion CSV/Excel) | `backend/app/services/libro_registro.py` (NUEVO) | Media | Tras 3C-B1 |
| 3C-B3 | Endpoint `GET /api/invoices/libro-registro?year=2026&trimestre=1` | `backend/app/routers/invoices.py` | Media | Tras 3C-B2 |
| 3C-B4 | Exportacion a formato AEAT (CSV con cabeceras estandar) | Dentro de `libro_registro.py` | Media | Tras 3C-B2 |
| 3C-B5 | Tests libro registro | `backend/tests/test_libro_registro.py` (NUEVO) | Media | Tras 3C-B3 |

**Esquema tabla `libro_registro`:**

```sql
CREATE TABLE IF NOT EXISTS libro_registro (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workspace_file_id TEXT REFERENCES workspace_files(id),
    tipo TEXT NOT NULL,              -- "emitida" | "recibida"
    numero_factura TEXT,
    fecha_factura TEXT,              -- ISO date
    fecha_operacion TEXT,            -- ISO date (puede diferir)
    emisor_nif TEXT,
    emisor_nombre TEXT,
    receptor_nif TEXT,
    receptor_nombre TEXT,
    concepto TEXT,
    base_imponible REAL NOT NULL,
    tipo_iva REAL,                   -- 21, 10, 4, 0
    cuota_iva REAL,
    tipo_re REAL,                    -- Recargo Equivalencia (si aplica)
    cuota_re REAL,
    retencion_irpf REAL,
    total REAL NOT NULL,
    cuenta_pgc TEXT,                 -- Codigo PGC clasificado
    cuenta_pgc_nombre TEXT,
    clasificacion_confianza TEXT,    -- "alta" | "media" | "baja" | "manual"
    trimestre INTEGER,              -- 1, 2, 3, 4
    year INTEGER NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
```

### 3D. Frontend Clasificador

| ID | Tarea | Archivo(s) | Complejidad | Parallelizable |
|----|-------|-----------|-------------|----------------|
| 3D-F1 | Crear `InvoiceClassifierPage.tsx` con zona de upload (drag & drop) | `frontend/src/pages/InvoiceClassifierPage.tsx` (NUEVO) | Alta | Tras 3A-B4 |
| 3D-F2 | Componente `ClassifiedInvoiceCard` (muestra datos + cuenta PGC + botones corregir) | `frontend/src/components/ClassifiedInvoiceCard.tsx` (NUEVO) | Media | Con 3D-F1 |
| 3D-F3 | Componente `LibroRegistroTable` (tabla con filtros por trimestre/tipo) | `frontend/src/components/LibroRegistroTable.tsx` (NUEVO) | Media | Tras 3C-B3 |
| 3D-F4 | CSS responsive (upload zone + table) | `frontend/src/pages/InvoiceClassifierPage.css` (NUEVO) | Baja | Con 3D-F1 |
| 3D-F5 | Registrar ruta `/clasificador-facturas` (auth + plan Autonomo required) | `frontend/src/App.tsx` | Baja | Tras 3D-F1 |
| 3D-F6 | Enlace en Header + sidebar | `frontend/src/components/Header.tsx` | Baja | Tras 3D-F5 |
| 3D-F7 | Boton exportar libro registro (CSV + Excel) | Dentro de `LibroRegistroTable.tsx` | Baja | Tras 3D-F3 |

### Dependencias Fase 3

```
3A-B1 ──> 3A-B2 ──> 3A-B3 ──> 3A-B4 ──> 3A-B5
                                  │
                                  └──> 3D-F1..F2

3B-B1 ──> 3B-B2 ──> 3B-B3 ──> 3B-B5 ──> 3B-B6 ──> 3B-B7
                      │
                      └──> 3D-F2

3C-B1 ──> 3C-B2 ──> 3C-B3 ──> 3C-B4 ──> 3C-B5
                      │
                      └──> 3D-F3 ──> 3D-F7

3D-F4..F6 (tras F1)

Paralelismo: 3A, 3B, 3C pueden avanzar en paralelo
3D depende de que los endpoints esten listos
```

---

## Impacto CCAA por Feature

La tabla siguiente documenta que features se ven afectadas por diferencias territoriales y como el sistema de territory plugins lo gestiona.

| Feature | Impacto CCAA | Como lo gestiona el plugin |
|---------|-------------|---------------------------|
| **Model Obligations** | ALTO. Cada regimen tiene modelos diferentes: 303 vs 420 (Canarias) vs F69 (Navarra) vs 300 (Gipuzkoa). IPSI en Ceuta/Melilla. | `get_model_obligations()` es un metodo abstracto en cada plugin. Cada plugin retorna la lista correcta. |
| **Calculadora Umbrales** | NINGUNO. Los umbrales LSC/PGC son estatales, no varian por CCAA. | No usa territory plugins. |
| **Perfil Farmaceutico** | MEDIO. El RE es igual en todo el territorio IVA (excluye Canarias/Ceuta/Melilla). En Canarias aplica IGIC sin RE equivalente. En Ceuta/Melilla aplica IPSI sin RE. | `get_model_obligations()` ya maneja la diferencia. Se anade un flag `aplica_recargo_equivalencia` al plugin que retorna `False` para Canarias y Ceuta/Melilla. |
| **Clasificador Facturas** | BAJO. La clasificacion PGC es la misma. Solo varia el tipo impositivo (IVA 21% vs IGIC 7% vs IPSI). | El clasificador lee el tipo impositivo de la factura. No necesita territory plugin. |
| **Libro Registro** | BAJO. El formato es el mismo. Solo cambia la columna de tipo impositivo. | Campo `tipo_iva` en la tabla almacena el valor real (21, 7, 4, etc.) independiente del regimen. |

### Territorios con logica especial

| Territorio | Modelo IVA | Modelo Renta | RE Aplicable | Notas |
|------------|-----------|-------------|-------------|-------|
| 15 CCAA comun | 303 | 100 | Si | Estandar |
| Canarias | 420 (IGIC) | 100 | No (IGIC no tiene RE) | `CanariasTerritory.aplica_RE() → False` |
| Ceuta/Melilla | IPSI | 100 | No | 6 tipos IPSI (0.5%-10%) |
| Gipuzkoa | 300 | 100 | Si (RE vasco) | Modelo 300 en vez de 303 |
| Bizkaia/Araba | 303 | 100 | Si | Estandar foral |
| Navarra | F69 | 100 | Si (RE navarro) | Modelo F69 en vez de 303 |

---

## Verificacion y Frontend Existente

### Items a verificar (ya implementados)

| Item | Que verificar | Archivo |
|------|---------------|---------|
| Cost dashboard widget | Verificar que `/admin/dashboard` muestra costes OpenAI correctamente | `frontend/src/pages/AdminDashboardPage.tsx` |
| Warmup greeting | Verificar que el chat muestra saludo personalizado al abrir | `backend/app/services/warmup_service.py` |

---

## Riesgos y Mitigaciones

| Riesgo | Impacto | Probabilidad | Mitigacion |
|--------|---------|-------------|-----------|
| Azure DI pricing para OCR masivo | Medio | Media | Limit: 50 facturas/mes plan Autonomo. Monitor usage. |
| Umbrales UE 2023/2775 aun no transpuestos a LSC | Bajo | Baja | Usar umbrales actuales con flag "pendiente transposicion". Actualizar cuando se publique en BOE. |
| RE en Canarias (IGIC no tiene RE equivalente) | Medio | Baja | Documentar que farmacias en Canarias presentan 420 normal (sin RE). Test especifico. |
| Clasificacion PGC incorrecta por IA | Alto | Media | Confianza baja → pedir confirmacion manual. Almacenar correcciones para mejorar. |
| Rate limiting en OCR endpoint | Bajo | Baja | 10 req/min para classify. Procesar async si >5 paginas. |

---

## Criterios de Exito

### Fase 1
- [ ] Endpoint `/api/irpf/model-obligations` retorna modelos correctos para 5 regimenes x 3 tipos (particular/autonomo/sociedad)
- [ ] Pagina `/modelos-obligatorios` funcional con seleccion de CCAA + situacion
- [ ] Tests: >25 para model obligations cubriendo todos los territorios
- [ ] Calculadora umbrales funcional con umbrales 2026
- [ ] Tests: >10 para company size (edge cases: exactamente en el limite, 1 ano vs 2 anos)

### Fase 2
- [ ] Perfil Farmaceutico seleccionable en wizard y settings
- [ ] RE correctamente aplicado: farmacia en Madrid no presenta 303, farmacia en Canarias SI presenta 420
- [ ] Landing `/farmacias` indexada por Google (verificar con Search Console)
- [ ] Al menos 3 documentos farmacia ingestados en RAG
- [ ] Tests: >15 cubriendo RE + deducciones + model obligations

### Fase 3
- [ ] Upload de factura (PDF/imagen) → datos extraidos correctamente (>80% campos)
- [ ] Clasificacion PGC con confianza > media en >70% de facturas
- [ ] Libro registro exportable en CSV con formato AEAT
- [ ] Sistema de correccion manual funcional (usuario corrige → se almacena)
- [ ] Tests: >30 cubriendo OCR + clasificacion + libro registro

---

## Calendario Tentativo

| Semana | Fase | Tareas |
|--------|------|--------|
| S1 (7-11 abr) | 1A + 1B | Model obligations backend + calculadora umbrales (paralelo) |
| S2 (14-18 abr) | 1A + 1B | Frontend model obligations + frontend calculadora (paralelo) |
| S3 (21-25 abr) | 2A + 2C + 2D | Pharmacy backend + landing page + RAG ingesta (paralelo) |
| S4 (28 abr - 2 may) | 2B | Pharmacy frontend wizard + integration tests |
| S5 (5-9 may) | 3A | OCR pipeline (Azure DI) + endpoint classify |
| S6 (12-16 may) | 3B | PGC classification service + seed cuentas |
| S7 (19-23 may) | 3C + 3D | Libro registro + frontend clasificador |
| S8 (26-30 may) | QA | Integration testing, regression, deploy |

---

## Archivos Nuevos (resumen)

### Backend
- `backend/app/utils/calculators/company_size.py`
- `backend/app/utils/pharmacy_constants.py`
- `backend/app/services/invoice_ocr_service.py`
- `backend/app/services/invoice_classifier.py`
- `backend/app/services/libro_registro.py`
- `backend/app/routers/invoices.py`
- `backend/scripts/seed_pgc_accounts.py`
- `backend/scripts/seed_deductions_pharmacy.py`
- `backend/tests/test_model_obligations.py`
- `backend/tests/test_company_size.py`
- `backend/tests/test_pharmacy.py`
- `backend/tests/test_invoice_ocr.py`
- `backend/tests/test_invoice_classifier.py`
- `backend/tests/test_libro_registro.py`

### Frontend
- `frontend/src/pages/ModelObligationsPage.tsx`
- `frontend/src/pages/ModelObligationsPage.css`
- `frontend/src/pages/CalculadoraUmbralesPage.tsx`
- `frontend/src/pages/CalculadoraUmbralesPage.css`
- `frontend/src/pages/FarmaciasPage.tsx`
- `frontend/src/pages/FarmaciasPage.css`
- `frontend/src/pages/InvoiceClassifierPage.tsx`
- `frontend/src/pages/InvoiceClassifierPage.css`
- `frontend/src/components/ClassifiedInvoiceCard.tsx`
- `frontend/src/components/LibroRegistroTable.tsx`

### Archivos Modificados

- `backend/app/territories/base.py` (ModelObligation dataclass + abstractmethod)
- `backend/app/territories/comun/plugin.py` (get_model_obligations)
- `backend/app/territories/canarias/plugin.py` (get_model_obligations)
- `backend/app/territories/foral_vasco/plugin.py` (get_model_obligations)
- `backend/app/territories/foral_navarra/plugin.py` (get_model_obligations)
- `backend/app/territories/ceuta_melilla/plugin.py` (get_model_obligations)
- `backend/app/routers/irpf_estimate.py` (2 nuevos endpoints)
- `backend/app/routers/fiscal_profile.py` (farmaceutico como situacion_laboral)
- `backend/app/utils/calculators/modelo_303.py` (RE logic)
- `backend/app/agents/tax_agent.py` (contexto farmacia)
- `backend/app/database/turso_client.py` (2 nuevas tablas: pgc_accounts, libro_registro)
- `backend/scripts/doc_crawler/watchlist.py` (URLs farmacia)
- `frontend/src/App.tsx` (4 nuevas rutas)
- `frontend/src/components/Header.tsx` (enlaces nuevas paginas)
- `frontend/src/pages/Home.tsx` (CTAs nuevas features)
- `frontend/src/pages/TaxGuidePage.tsx` (opcion Farmaceutico)
- `frontend/src/components/DynamicFiscalForm.tsx` (campos farmacia)
