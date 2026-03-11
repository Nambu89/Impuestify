# Plan RPI: Criptomonedas, Trading y Apuestas — Alineado con XSD Modelo 100

> Fecha: 2026-03-11
> Estado: Pendiente aprobación
> Archivos XSD referencia: `docs/aeat/Renta-2025/diccionarioXSD_2024.properties`
> Plan-checker: PASS (v2 — corregidos 7 issues + 4 warnings)

## Contexto

El Modelo 100 (IRPF) tiene secciones oficiales para criptomonedas (casillas 1800-1814),
apuestas/juegos (casillas 0281-0297) y ganancias patrimoniales por acciones/fondos (casillas 0316-0354).
Nuestros campos del perfil fiscal deben alinearse con estas casillas para:
1. Mapear correctamente a la declaración
2. Usar la terminología oficial AEAT
3. Calcular correctamente base del ahorro vs base general

## Hallazgos clave del XSD

### Criptomonedas (GPOtrosCriptomonedas, casillas 1800-1814)
- **Clave contraprestación** (casilla 1803): F=fiat, N=otra cripto, O=otro activo virtual, B=bienes/servicios
- Campos por operación: denominación, valor transmisión, valor adquisición, ganancia/pérdida
- Resumen: suma pérdidas (1813) + suma ganancias (1814)
- Anexo C.1 para cobros aplazados (1858-1877)
- **Staking/mining/DeFi NO tienen casilla propia** — van como rendimiento capital mobiliario o actividad económica

### Apuestas y juegos (GPPremios, casillas 0281-0297)
- **AEAT separa**: juegos privados (0281-0290) vs loterías públicas (0291-0297)
- Privados: premios metálico (0282) + pérdidas (0287) = neto (0290)
- Públicos: premios metálico (0292), sin compensación de pérdidas
- Exención: premios loterías Estado < 40.000 EUR

### Trading acciones/fondos (casillas 0316-0354)
- Fondos inversión (GPFondos): casillas 0316-0320
- Acciones (GPAcciones): casillas 0332-0339
- Derechos/participaciones (GPDerechos): casillas 0347-0354

---

## Tareas

### Fase 1: Alinear campos del perfil fiscal (Backend)

#### T1.1 — Reestructurar sección `inversiones_digitales` en `fiscal_fields.py`

Renombrar sección a `criptomonedas`. Alinear con casillas AEAT. Tuteo informal coherente con el resto del formulario:

```python
{
    "id": "criptomonedas",
    "title": "Criptomonedas y monedas virtuales",
    "description": "Casillas 1800-1814 del Modelo 100",
    "fields": [
        {"key": "tiene_criptomonedas", "label": "¿Has transmitido monedas virtuales en el ejercicio?", "type": "bool"},
        {"key": "cripto_denominaciones", "label": "Monedas virtuales transmitidas (BTC, ETH, SOL...)", "type": "str",
         "hint": "Casilla 1802 — Denominación de la moneda virtual"},
        {"key": "cripto_clave_contraprestacion", "label": "Tipo de contraprestación recibida", "type": "select",
         "options": ["F", "N", "O", "B"],
         "option_labels": ["Moneda de curso legal (EUR, USD...)", "Otra moneda virtual (cripto a cripto)", "Otro activo virtual (NFT, token)", "Bienes o servicios"],
         "hint": "Casilla 1803"},
        {"key": "cripto_valor_transmision_total", "label": "Valor total de transmisión (EUR)", "type": "float",
         "hint": "Suma casilla 1804"},
        {"key": "cripto_valor_adquisicion_total", "label": "Valor total de adquisición (EUR)", "type": "float",
         "hint": "Suma casilla 1806"},
        {"key": "cripto_ganancia_neta", "label": "Ganancia patrimonial neta por criptomonedas (EUR)", "type": "float",
         "hint": "Casilla 1814 — suma ganancias"},
        {"key": "cripto_perdida_neta", "label": "Pérdida patrimonial neta por criptomonedas (EUR)", "type": "float",
         "hint": "Casilla 1813 — suma pérdidas"},
        {"key": "cripto_en_extranjero_50k", "label": "¿Tienes saldo en exchanges extranjeros > 50.000 EUR al 31/dic?", "type": "bool",
         "hint": "Obligación Modelo 721"},
        {"key": "tiene_staking_defi", "label": "¿Tienes ingresos por staking, DeFi, lending o minería?", "type": "bool",
         "hint": "Sin casilla propia — tributa como rendimiento de capital mobiliario o actividad económica"},
        {"key": "exchanges_utilizados", "label": "Exchanges utilizados (Binance, Coinbase...)", "type": "str"},
    ]
}
```

**Archivos**: `backend/app/routers/fiscal_fields.py`
**Verificación**: `pytest tests/test_fiscal_fields.py -v` pasa

#### T1.2 — Reestructurar sección `apuestas_juegos` separando privados/públicos

AEAT distingue juegos privados (casillas 0281-0290) de loterías públicas (0291-0297):

```python
{
    "id": "apuestas_juegos",
    "title": "Premios, apuestas y juegos",
    "description": "Casillas 0281-0297 del Modelo 100",
    "fields": [
        # --- Juegos privados (casillas 0281-0290) ---
        {"key": "tiene_ganancias_juegos_privados", "label": "¿Has tenido premios en juegos, apuestas o concursos?", "type": "bool",
         "hint": "Casillas 0281-0290 — Juegos no organizados por el Estado"},
        {"key": "premios_metalico_privados", "label": "Premios en metálico de juegos/apuestas (EUR)", "type": "float",
         "hint": "Casilla 0282"},
        {"key": "premios_especie_privados", "label": "Premios en especie — valoración (EUR)", "type": "float",
         "hint": "Casilla 0283"},
        {"key": "perdidas_juegos_privados", "label": "Pérdidas patrimoniales en juegos/apuestas (EUR)", "type": "float",
         "hint": "Casilla 0287 — compensan las ganancias del mismo tipo"},
        # --- Loterías y juegos públicos (casillas 0291-0297) ---
        {"key": "tiene_premios_loterias", "label": "¿Has tenido premios de loterías del Estado, ONCE o Cruz Roja?", "type": "bool",
         "hint": "Casillas 0291-0297 — Juegos organizados por organismos públicos"},
        {"key": "premios_metalico_publicos", "label": "Premios en metálico de loterías públicas (EUR)", "type": "float",
         "hint": "Casilla 0292 — exentos los primeros 40.000 EUR"},
        {"key": "premios_especie_publicos", "label": "Premios en especie de loterías públicas — valoración (EUR)", "type": "float",
         "hint": "Casilla 0293"},
    ]
}
```

**Archivos**: `backend/app/routers/fiscal_fields.py`

#### T1.3 — Reestructurar sección `trading` alineada con casillas

**IMPORTANTE**: El campo `ganancias_fondos` ya existe en la sección `rendimientos_ahorro` (línea 57 de fiscal_fields.py) y lo usa el simulador IRPF. Para evitar colisión, los fondos de inversión usan `ganancias_reembolso_fondos` / `perdidas_reembolso_fondos`.

```python
{
    "id": "ganancias_patrimoniales_financieras",
    "title": "Ganancias patrimoniales por inversiones financieras",
    "description": "Casillas 0316-0354 del Modelo 100",
    "fields": [
        # --- Fondos de inversión (GPFondos, casillas 0316-0320) ---
        {"key": "tiene_fondos_inversion", "label": "¿Has reembolsado participaciones en fondos de inversión?", "type": "bool",
         "hint": "Casillas 0316-0320"},
        {"key": "ganancias_reembolso_fondos", "label": "Ganancias por reembolso de fondos (EUR)", "type": "float",
         "hint": "Casilla 0320 — ganancia patrimonial"},
        {"key": "perdidas_reembolso_fondos", "label": "Pérdidas por reembolso de fondos (EUR)", "type": "float"},
        # --- Acciones y participaciones (GPAcciones, casillas 0332-0339) ---
        {"key": "tiene_acciones", "label": "¿Has vendido acciones o participaciones?", "type": "bool",
         "hint": "Casillas 0332-0339"},
        {"key": "ganancias_acciones", "label": "Ganancias por venta de acciones (EUR)", "type": "float",
         "hint": "Casilla 0338"},
        {"key": "perdidas_acciones", "label": "Pérdidas por venta de acciones (EUR)", "type": "float",
         "hint": "Casilla 0339"},
        # --- Derivados/CFDs/Forex (GPDerechos, casillas 0347-0354) ---
        {"key": "tiene_derivados", "label": "¿Has operado con derivados, CFDs o Forex?", "type": "bool",
         "hint": "Casillas 0347-0354 — Derechos y participaciones"},
        {"key": "ganancias_derivados", "label": "Ganancias por derivados/CFDs/Forex (EUR)", "type": "float",
         "hint": "Casilla 0353"},
        {"key": "perdidas_derivados", "label": "Pérdidas por derivados/CFDs/Forex (EUR)", "type": "float",
         "hint": "Casilla 0354"},
    ]
}
```

**Archivos**: `backend/app/routers/fiscal_fields.py`

#### T1.4 — Actualizar `FiscalProfileRequest` en `user_rights.py`

Campos a ELIMINAR (renombrados):
- `tiene_ganancias_apuestas` → `tiene_ganancias_juegos_privados`
- `ganancias_brutas_apuestas` → `premios_metalico_privados`
- `perdidas_apuestas` → `perdidas_juegos_privados`
- `premios_loterias_estado` → `premios_metalico_publicos`
- `tiene_premios_exentos` → eliminado (se calcula automáticamente: exento si < 40.000 EUR)
- `tiene_acciones_fondos` → `tiene_fondos_inversion` + `tiene_acciones` + `tiene_derivados`
- `ganancias_fondos_etf` → `ganancias_reembolso_fondos`
- `perdidas_fondos_etf` → `perdidas_reembolso_fondos`
- `ganancias_derivados_cfd` → `ganancias_derivados`
- `perdidas_derivados_cfd` → `perdidas_derivados`
- `mineria_cripto` → fusionado con `tiene_staking_defi`
- `tiene_nfts` → cubierto por `cripto_clave_contraprestacion = O`

Campos a AÑADIR:
- `cripto_denominaciones`, `cripto_clave_contraprestacion`, `cripto_valor_transmision_total`,
  `cripto_valor_adquisicion_total`, `cripto_ganancia_neta`, `cripto_perdida_neta`
- `premios_especie_privados`, `premios_especie_publicos`, `tiene_premios_loterias`
- `tiene_fondos_inversion`, `tiene_acciones`, `tiene_derivados`
- `ganancias_reembolso_fondos`, `perdidas_reembolso_fondos`

Actualizar `_DATOS_FISCALES_KEYS` con TODOS los campos nuevos y sin los eliminados.

**Archivos**: `backend/app/routers/user_rights.py`
**Verificación**: `pytest tests/test_api.py -v` pasa

#### T1.5 — Verificar tablas BD crypto en `turso_client.py`

Las 3 tablas ya creadas están bien alineadas. Verificar que `clave_contraprestacion` en `crypto_gains` solo acepta F/N/O/B. Sin cambios esperados.

**Archivos**: `backend/app/database/turso_client.py`

#### T1.6 — Actualizar borrado GDPR (OBLIGATORIO)

En `delete_user_account()` (user_rights.py, líneas 632-732), añadir borrado de las 3 tablas crypto ANTES de borrar el usuario:

```python
await db.execute("DELETE FROM crypto_gains WHERE user_id = ?", [user_id])
await db.execute("DELETE FROM crypto_holdings WHERE user_id = ?", [user_id])
await db.execute("DELETE FROM crypto_transactions WHERE user_id = ?", [user_id])
```

**Archivos**: `backend/app/routers/user_rights.py`

#### T1.7 — Actualizar `build_answers_from_profile()` en `deduction_service.py`

Mapear los nuevos campos de crypto/trading/apuestas para que `discover_deductions` pueda usarlos en evaluación de deducciones. Campos relevantes: `tiene_criptomonedas`, `tiene_acciones`, `tiene_derivados`.

**Archivos**: `backend/app/services/deduction_service.py`

#### T1.8 — Script de migración de campos renombrados

Crear script idempotente que actualice `datos_fiscales` JSON en `user_profiles` para renombrar keys:

```python
# Mapa de migración: key_vieja → key_nueva
MIGRATION_MAP = {
    "ganancias_brutas_apuestas": "premios_metalico_privados",
    "perdidas_apuestas": "perdidas_juegos_privados",
    "tiene_ganancias_apuestas": "tiene_ganancias_juegos_privados",
    "premios_loterias_estado": "premios_metalico_publicos",
    "ganancias_fondos_etf": "ganancias_reembolso_fondos",
    "perdidas_fondos_etf": "perdidas_reembolso_fondos",
    "ganancias_derivados_cfd": "ganancias_derivados",
    "perdidas_derivados_cfd": "perdidas_derivados",
}
```

**Archivos**: `backend/scripts/migrate_fiscal_fields_crypto.py` (nuevo)

### Fase 2: Calculadora FIFO + Tools (Backend)

#### T2.1 — Crear `crypto_fifo_calculator.py`

Calculadora FIFO (First-In-First-Out) para ganancias/pérdidas patrimoniales crypto:
- Input: lista de CryptoTransaction ordenadas por fecha
- Output: lista de CryptoGain con valor adquisición, valor transmisión, ganancia/pérdida
- Asignar `clave_contraprestacion` (F/N/O/B) según el tipo de operación
- Regla antiaplicación (2 meses para valores cotizados, 1 año para no cotizados)

**Archivos**: `backend/app/utils/calculators/crypto_fifo.py` (nuevo)
**Verificación**: `pytest tests/test_crypto_fifo.py -v` pasa

#### T2.2 — Crear tool `calculate_crypto_gains`

Tool de function calling para el TaxAgent:
- Calcula ganancias/pérdidas FIFO del usuario
- Devuelve resumen con casillas 1813 (pérdidas) y 1814 (ganancias)
- Integración con `build_answers_from_profile()` para inyectar datos cripto

**Archivos**: `backend/app/tools/crypto_gains_tool.py` (nuevo), `backend/app/tools/__init__.py`

#### T2.3 — Crear tool `parse_crypto_csv`

Tool para subir CSV de exchanges y parsear transacciones:
- Usa `crypto_parser.py` existente (650 líneas, 5 exchanges + genérico)
- Guarda en tabla `crypto_transactions`
- Devuelve resumen de transacciones importadas

**Archivos**: `backend/app/tools/crypto_csv_tool.py` (nuevo), `backend/app/tools/__init__.py`

### Fase 3: Router REST (Backend)

#### T3.1 — Crear router `/api/crypto` + registrar en main.py

Endpoints:
- `POST /api/crypto/upload` — Subir CSV/XLSX de exchange, parsear y guardar
  - Rate limit: 5/min por usuario
  - Validación: magic numbers CSV/XLSX + size limit 10 MB
- `GET /api/crypto/transactions` — Listar transacciones del usuario
- `GET /api/crypto/holdings` — Portfolio actual (cache)
- `GET /api/crypto/gains?tax_year=2025` — Ganancias/pérdidas FIFO por ejercicio
- `DELETE /api/crypto/transactions/{id}` — Eliminar transacción (ownership check)

Registrar en main.py: `app.include_router(crypto_router)`

**Archivos**: `backend/app/routers/crypto.py` (nuevo), `backend/app/main.py`
**Verificación**: `pytest tests/test_crypto_router.py -v` pasa

### Fase 4: Integración con simulador IRPF (Backend)

#### T4.1 — Añadir ganancias cripto/trading/apuestas al simulador

El `irpf_simulator.py` ya tiene `SavingsIncomeCalculator`. Añadir:
- Ganancias cripto (casillas 1813-1814) a base del ahorro
- Ganancias acciones/fondos (casillas 0316-0354) a base del ahorro
- Ganancias juegos privados (casilla 0290) a base general (NO base ahorro)
- Premios loterías públicas: exención 40.000 EUR + gravamen especial 20%

**IMPORTANTE**: Modificar también `SavingsIncomeCalculator.calculate()` en
`backend/app/utils/calculators/savings_income.py` para aceptar los nuevos parámetros
(ganancias_acciones, ganancias_derivados, cripto_ganancia_neta). Alternativa: sumar todo
en el campo existente `ganancias_fondos` antes de llamar al calculador, documentando el mapeo.

**Archivos**: `backend/app/utils/irpf_simulator.py`, `backend/app/utils/calculators/savings_income.py`
**Verificación**: `pytest tests/test_irpf_crypto_integration.py -v` pasa

### Fase 5: Tests (Backend)

#### T5.1 — Tests crypto_parser

Verificar y completar tests del parser CSV para los 5 exchanges + genérico.
Mínimo 30 tests: 5 por exchange + 5 genérico + edge cases (vacío, BOM, límite filas).

**Archivos**: `backend/tests/test_crypto_parser.py` (nuevo)
**Verificación**: `pytest tests/test_crypto_parser.py -v` — 30+ tests pasan

#### T5.2 — Tests FIFO calculator

Tests unitarios: FIFO básico, crypto-to-crypto, antiaplicación, múltiples activos, pérdidas.
Mínimo 20 tests.

**Archivos**: `backend/tests/test_crypto_fifo.py` (nuevo)
**Verificación**: `pytest tests/test_crypto_fifo.py -v` — 20+ tests pasan

#### T5.3 — Tests router crypto

Tests de integración para los 5 endpoints REST. Auth requerida, ownership checks.

**Archivos**: `backend/tests/test_crypto_router.py` (nuevo)
**Verificación**: `pytest tests/test_crypto_router.py -v` — 15+ tests pasan

#### T5.4 — Tests integración simulador

Verificar que ganancias cripto/trading/apuestas calculan correctamente en el simulador IRPF.
Casos: solo cripto, solo acciones, mixto, apuestas privadas (base general), loterías (exención).

**Archivos**: `backend/tests/test_irpf_crypto_integration.py` (nuevo)
**Verificación**: `pytest tests/test_irpf_crypto_integration.py -v` — 10+ tests pasan

### Fase 6: Frontend (React)

#### T6.1 — Sección criptomonedas en perfil fiscal

El `DynamicFiscalForm.tsx` ya renderiza desde la API. Verificar que:
- El select de `cripto_clave_contraprestacion` guarda solo el value (F/N/O/B), no el label
- Los campos se muestran condicionalmente solo si `tiene_criptomonedas=true`

**Archivos**: `frontend/src/components/DynamicFiscalForm.tsx` (verificar, cambios mínimos)

#### T6.2 — Página de gestión crypto (upload CSV + dashboard)

Nueva página `/crypto` o sección en `/declarations`:
- Upload CSV/XLSX con drag-and-drop
- Tabla de transacciones importadas con paginación
- Resumen de ganancias/pérdidas por ejercicio
- Indicador de obligación Modelo 721 si > 50.000 EUR en extranjero

**Archivos**: `frontend/src/pages/CryptoPage.tsx` (nuevo), `frontend/src/hooks/useCrypto.ts` (nuevo)

#### T6.3 — Secciones apuestas y trading en perfil fiscal

Se renderizan automáticamente desde la API de fiscal_fields. Verificar coherencia visual.

**Archivos**: Frontend automático si la API devuelve los campos correctos.

### Fase 7: Guía Fiscal — Integrar en wizard

#### T7.1 — Añadir paso de inversiones/cripto en TaxGuidePage

Nuevo paso o subsección en el wizard de 7 pasos para:
- Preguntar si tiene cripto, acciones, apuestas
- Recoger importes de ganancias/pérdidas
- Integrar en la estimación IRPF en tiempo real

**Archivos**: `frontend/src/pages/TaxGuidePage.tsx`

---

## Dependencias entre tareas

```
T1.1-T1.4 (perfil fiscal) → sin dependencias, ejecutar primero
T1.5 (BD) → verificación rápida
T1.6 (GDPR) → T1.5
T1.7 (build_answers) → T1.4
T1.8 (migración) → T1.4
T2.1 (FIFO calc) → T1.5
T2.2-T2.3 (tools) → T2.1 + crypto_parser.py existente
T3.1 (router + main.py) → T2.1 + T1.5
T4.1 (simulador + savings_income.py) → T1.4 (campos perfil)
T5.* (tests) → cada test depende de su módulo
T6.* (frontend) → T1.1-T1.3 (campos API) + T3.1 (router)
T7.1 (wizard) → T4.1 (simulador) + T6.1
```

## Delegación propuesta

| Fase | Agente | Prioridad |
|------|--------|-----------|
| Fase 1 (T1.1-T1.8, campos perfil) | backend-architect | ALTA — hacer primero |
| Fase 2 (FIFO + tools) | backend-architect | ALTA |
| Fase 3 (router REST + main.py) | backend-architect | ALTA |
| Fase 4 (simulador + savings_income) | backend-architect | MEDIA |
| Fase 5 (tests) | backend-architect | ALTA (en paralelo con cada fase) |
| Fase 6 (frontend) | frontend-dev | MEDIA — tras Fase 1+3 |
| Fase 7 (wizard) | frontend-dev | BAJA — tras Fase 4+6 |

## Archivos totales

- **Nuevos (8)**: crypto_fifo.py, crypto_gains_tool.py, crypto_csv_tool.py, crypto.py (router),
  migrate_fiscal_fields_crypto.py, CryptoPage.tsx, useCrypto.ts, 4 test files
- **Modificados (10)**: fiscal_fields.py, user_rights.py, turso_client.py, irpf_simulator.py,
  savings_income.py, deduction_service.py, tools/__init__.py, main.py, DynamicFiscalForm.tsx,
  TaxGuidePage.tsx

## Reglas de ortografía

- Keys internos: snake_case SIN tildes (`cripto_valor_transmision_total`)
- Labels visibles al usuario: CON tildes (`"Valor total de transmisión (EUR)"`)
- Tuteo informal coherente: "¿Tienes...?", "¿Has vendido...?" (NO formal "¿Ha transmitido...?")
- "Pérdida/Pérdidas" siempre con tilde en labels
- "Adquisición", "transmisión", "valoración", "inversión" siempre con tilde en labels
- "Metálico", "loterías", "públicas", "minería", "obligación", "económica" con tilde en labels
