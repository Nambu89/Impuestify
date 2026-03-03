# Agent Communication Log - TaxIA
# =================================
# Este archivo actúa como "canal de comunicación" entre agentes.
# Cada agente debe leerlo al inicio y escribir al terminar una tarea.
# 
# Formato:
# [TIMESTAMP] [AGENT] [STATUS] - Mensaje
# STATUS: 🟢 DONE | 🟡 IN_PROGRESS | 🔴 BLOCKED | 📢 NEEDS_REVIEW

## Mensajes Activos
---

[2026-03-04] [FRONTEND] [🟢 DONE] - Ceuta/Melilla UI + precio suscripción 15→5 EUR

### Cambios realizados

**1. Ceuta/Melilla en Settings (instrucciones del backend agent)**

- `hooks/useFiscalProfile.ts` — +campo `ceuta_melilla: boolean` en interface FiscalProfile y EMPTY_PROFILE
- `pages/SettingsPage.tsx`:
  - Checkbox "Residente en Ceuta o Melilla" después de Pluriactividad
  - Hint descriptivo: "Deducción del 60% en IRPF + bonificación 50% cuota SS + IPSI en lugar de IVA"
  - Opción "IPSI (Ceuta/Melilla)" añadida al select de Régimen IVA
  - Auto-toggle: marcar ceuta_melilla cambia regimen_iva a "ipsi" (si era "general" o vacío); desmarcar revierte a "general"
- `pages/SettingsPage.css` — +clase `.field-hint` para el hint del checkbox

**2. Precio suscripción: 15 EUR → 5 EUR**

- `pages/Home.tsx` — pricing-value: 15→5
- `pages/SubscribePage.tsx` — subscribe-price-value: 15→5
- `pages/SettingsPage.tsx` — botón "Suscribirme - 5 EUR/mes"

**Build:** ✅ Exitoso (npm run build sin errores)

---

[2026-03-04] [BACKEND] [🟢 DONE] - Soporte fiscal Ceuta/Melilla para autónomos

### Resumen de Cambios Backend

**Contexto fiscal:** Los autónomos en Ceuta y Melilla tienen ventajas fiscales significativas:
- **IRPF**: Deducción del 60% en cuota íntegra (Art. 68.4 Ley 35/2006)
- **Seguridad Social**: Bonificación del 50% en contingencias comunes (Art. 36 Ley 20/2007)
- **Impuesto indirecto**: Pagan IPSI (0,5%-10%) en lugar de IVA (21%)

**Archivos modificados (7):**
1. `backend/app/routers/user_rights.py` — +campo `ceuta_melilla: Optional[bool]`, regimen_iva acepta `"ipsi"`, +key en `_DATOS_FISCALES_KEYS`
2. `backend/app/tools/web_scraper_tool.py` — +Ceuta/Melilla en `CCAA_NORMALIZATION`
3. `backend/app/agents/tax_agent.py` — +`ceuta_melilla` en `label_map`
4. `backend/app/agents/workspace_agent.py` — +`ceuta_melilla` en `label_map`
5. `backend/app/tools/irpf_simulator_tool.py` — +param `ceuta_melilla: bool`, auto-detección por CCAA, formato muestra deducción
6. `backend/app/utils/irpf_simulator.py` — Implementada deducción 60% cuota íntegra (Art. 68.4 LIRPF)
7. `backend/app/security/content_restriction.py` — +keywords IPSI

**Archivo creado (1):**
- `backend/tests/test_ceuta_melilla.py` — 25 tests (todos pasan, 0 regresiones)

**Lógica de la deducción 60% IRPF:**
- Se aplica sobre la cuota íntegra total (general + ahorro)
- Se descuenta de cuota líquida general primero, luego de ahorro si queda remanente
- La cuota nunca puede ser negativa (max(0, ...))
- Se auto-activa si ccaa_residencia es "Ceuta" o "Melilla"
- Campo `ceuta_melilla` en datos_fiscales permite control manual

**Cuotas autónomos:** Ya estaba implementado (`region: "ceuta"|"melilla"` en autonomous_quota_tool con 50% bonificación). No requiere cambios.

### Para FRONTEND agent: Cambios necesarios en Settings

**1. Nuevo checkbox "Ceuta/Melilla" en sección "Datos de autónomo"**

Ubicación: Después del checkbox de "Pluriactividad" en `SettingsPage.tsx`.

```tsx
{/* Ceuta/Melilla */}
<div className="settings-field">
  <label className="settings-checkbox-label">
    <input
      type="checkbox"
      checked={fiscalProfile.ceuta_melilla || false}
      onChange={(e) => handleFiscalChange('ceuta_melilla', e.target.checked)}
    />
    Residente en Ceuta o Melilla
  </label>
  <small className="settings-field-hint">
    Deducción del 60% en IRPF + bonificación 50% cuota SS + IPSI en lugar de IVA
  </small>
</div>
```

**2. Actualizar régimen IVA: añadir opción "IPSI"**

En el `<select>` de `regimen_iva`, añadir una opción más:

```tsx
<option value="ipsi">IPSI (Ceuta/Melilla)</option>
```

Ubicación: Después de `<option value="exento">Exento</option>`

**3. Condicionar visibilidad del checkbox**

El checkbox de `ceuta_melilla` solo debe ser visible cuando:
- `subscription.planType === 'autonomo'` o `subscription.isOwner` (igual que los demás campos de autónomo)

**4. Auto-seleccionar IPSI cuando ceuta_melilla=true**

Lógica sugerida (opcional pero mejora UX):
- Cuando el usuario marca `ceuta_melilla = true`:
  - Si `regimen_iva` es "general", cambiar automáticamente a "ipsi"
  - Mostrar nota: "En Ceuta/Melilla se aplica IPSI en lugar de IVA"
- Cuando desmarca `ceuta_melilla`:
  - Si `regimen_iva` es "ipsi", cambiar a "general"

**5. Actualizar interface `FiscalProfile` en `useFiscalProfile.ts`**

```typescript
// Añadir al interface FiscalProfile:
ceuta_melilla?: boolean;
```

Y en `EMPTY_PROFILE`:
```typescript
ceuta_melilla: false,
```

**6. No se necesitan cambios en endpoints**

El backend ya acepta `ceuta_melilla` como campo de `FiscalProfileRequest`. El `PUT /api/users/me/fiscal-profile` lo guarda automáticamente en `datos_fiscales` JSON.

**Build:** ✅ Backend sin errores
**Tests:** 25 nuevos + 14 existentes = 39 total (0 regresiones)

---

[2026-03-04] [COMPETITIVE] [🟢 DONE] - Comparativa Impuestify vs TaxDown + Analisis Rita (motor deducciones)

### Reporte completo
Ver `docs/competitive/taxdown_comparison.md`

---

## 📢 ROADMAP BACKEND — Motor de Deducciones (prioridad competitiva)

> **Contexto**: TaxDown usa "Rita", un rules engine + decision tree que cruza ~3,000 preguntas con ~338 deducciones IRPF (16 estatales + 322 autonomicas). NO es IA generativa. Depende de importar datos via Cl@ve (que no tenemos). Solo el 33% de usuarios consigue ahorro real (dato BBVA). **Rita NO cubre territorios forales (PV/Navarra).**
>
> Nuestro sistema actual tiene CERO identificacion de deducciones. El IRPFSimulator solo aplica deducciones estructurales (SS, gastos trabajo, MPYF, reduccion alquiler). El TaxAgent no pregunta proactivamente.
>
> **Objetivo**: Construir un Motor de Deducciones Conversacional que compita con Rita pero sea MEJOR en:
> 1. Cobertura de territorios forales (unico en el mercado)
> 2. Transparencia (cita fuentes legales exactas)
> 3. Formato conversacional (no wizard cerrado)
> 4. Actualizable via RAG (no hardcodeado)

### FASE 1 — Deduction Registry (CRITICA — hacer primero)

**Objetivo**: Crear base de datos estructurada con TODAS las deducciones IRPF de Espana.

**1.1 Crear tabla `deductions` en Turso**

```sql
CREATE TABLE IF NOT EXISTS deductions (
  id TEXT PRIMARY KEY,
  code TEXT NOT NULL,              -- 'EST_MATERNIDAD', 'MAD_ALQUILER_JOVEN', 'BIZ_VIVIENDA'
  name TEXT NOT NULL,              -- 'Deduccion por maternidad'
  type TEXT NOT NULL,              -- 'estatal' | 'autonomica' | 'foral'
  territory TEXT NOT NULL,         -- 'estatal', 'madrid', 'cataluna', 'bizkaia', 'navarra'...
  tax_year INTEGER NOT NULL,       -- 2025
  description TEXT,                -- Descripcion breve legible
  legal_reference TEXT,            -- 'Art. 81 Ley 35/2006' o 'NF 33/2013 Araba Art. 89'
  percentage REAL,                 -- Porcentaje deduccion (ej: 20.0 para 20%)
  max_amount REAL,                 -- Limite maximo en EUR
  min_amount REAL,                 -- Minimo (si aplica)
  base_type TEXT,                  -- 'cuota' | 'base' | 'gasto' (sobre que se aplica)
  requirements_json TEXT,          -- JSON con condiciones booleanas
  questions_json TEXT,             -- JSON con preguntas necesarias para verificar elegibilidad
  category TEXT,                   -- 'familia', 'vivienda', 'donaciones', 'energia', 'salud'...
  is_active BOOLEAN DEFAULT 1,
  source_pdf TEXT,                 -- Ruta al PDF fuente en docs/
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_deductions_territory ON deductions(territory, tax_year);
CREATE INDEX IF NOT EXISTS idx_deductions_type ON deductions(type, tax_year);
CREATE INDEX IF NOT EXISTS idx_deductions_category ON deductions(category);
```

**1.2 Poblar con deducciones estatales (16) — datos hardcodeados, no necesitan PDF**

Deducciones estatales IRPF 2025 a incluir:

| Code | Nombre | % | Limite | Base legal |
|------|--------|---|--------|------------|
| EST_MATERNIDAD | Maternidad (hijos <3) | 100% | 1,200 EUR/hijo | Art. 81 Ley 35/2006 |
| EST_FAMILIA_NUMEROSA | Familia numerosa | 100% | 1,200-2,400 EUR | Art. 81 bis |
| EST_DISCAPACIDAD_CARGO | Discapacidad a cargo | 100% | 1,200 EUR | Art. 81 bis |
| EST_ASCENDIENTE_SEPARADO | Ascendiente separado | 100% | 1,200 EUR | Art. 81 bis |
| EST_INVERSION_VIVIENDA | Vivienda habitual (transitoria pre-2013) | 15% | 9,040 EUR base | DT 18 |
| EST_ALQUILER_VIVIENDA | Alquiler vivienda (transitoria pre-2015) | 10.05% | Renta < 24,107 EUR | DT 15 |
| EST_DONACIONES_80 | Donaciones (primeros 250 EUR) | 80% | 250 EUR base | Art. 68.3 |
| EST_DONACIONES_40 | Donaciones (resto) | 40% | 10% base liquidable | Art. 68.3 |
| EST_EMPRESA_NUEVA | Inversion empresa nueva creacion | 50% | 12,372 EUR base (antes 100K) | Art. 68.1 |
| EST_PATRIMONIO_HISTORICO | Patrimonio historico | 15% | — | Art. 68.5 |
| EST_CEUTA_MELILLA | Rentas Ceuta/Melilla | 60% | Cuota integra | Art. 68.4 |
| EST_EV_ELECTRICO | Vehiculo electrico enchufable | 15% | 3,000 EUR (base 20K) | DA 58 |
| EST_PUNTO_RECARGA | Punto recarga VE | 15% | 4,000 EUR base | DA 58 |
| EST_EFICIENCIA_1 | Eficiencia energetica demanda | 20% | 5,000 EUR base | DA 50 |
| EST_EFICIENCIA_2 | Eficiencia energetica consumo | 40% | 7,500 EUR base | DA 50 |
| EST_EFICIENCIA_3 | Rehabilitacion edificios | 60% | 15,000 EUR base | DA 50 |

**1.3 Extraer deducciones autonomicas de PDFs prioritarios**

Fuentes ya disponibles en `docs/`:
- **REAF Panorama 2025** (7.5 MB) — TODAS las deducciones autonomicas en un solo documento
- **Cap I-IV Tributacion Autonomica 2025** — referencia cruzada
- **DLeg/Leyes consolidadas por CCAA** — detalle legal

Empezar por las CCAA con mas deducciones:
1. **Comunidad Valenciana** (~37-40 deducciones) — la que mas tiene
2. **Madrid** (~23) — mas usuarios potenciales
3. **Cataluna** (~11) — segundo mercado
4. **Andalucia** (~14) — tercer mercado
5. Resto de CCAA (ir completando)

**1.4 Extraer deducciones forales (DIFERENCIADOR UNICO)**

Fuentes en `docs/`:
- `Araba/IRPF/NF_33_2013_IRPF_consolidada.pdf` — deducciones IRPF Araba
- `Gipuzkoa/IRPF/NF_3_2014_*.pdf` + `NF_1_2025_reforma.pdf` — deducciones Gipuzkoa
- `Bizkaia/IRPF/` — deducciones Bizkaia
- `Navarra/IRPF/LF_26_2016_*.pdf` — deducciones Navarra

**Rita de TaxDown NO cubre forales.** Esta es nuestra ventaja competitiva principal.

### FASE 2 — Deduction Discovery Tool (1 semana)

**2.1 Crear `backend/app/tools/deduction_discovery_tool.py`**

```python
# Tool definition para OpenAI function calling
DISCOVER_DEDUCTIONS_TOOL = {
    "type": "function",
    "function": {
        "name": "discover_deductions",
        "description": "Identifica deducciones IRPF aplicables al usuario segun su perfil fiscal y situacion personal. Busca en la base de datos de ~338 deducciones (estatales + autonomicas + forales).",
        "parameters": {
            "type": "object",
            "properties": {
                "ccaa": {"type": "string", "description": "CCAA de residencia"},
                "tax_year": {"type": "integer", "description": "Ejercicio fiscal (default 2025)"},
                "answers": {
                    "type": "object",
                    "description": "Respuestas del usuario sobre su situacion",
                    "properties": {
                        "tiene_hijos_menores_3": {"type": "boolean"},
                        "tiene_hijos_menores_25": {"type": "boolean"},
                        "num_hijos": {"type": "integer"},
                        "familia_numerosa": {"type": "boolean"},
                        "discapacidad_contribuyente": {"type": "integer", "description": "0, 33, 65"},
                        "discapacidad_familiar": {"type": "boolean"},
                        "alquila_vivienda": {"type": "boolean"},
                        "compro_vivienda_pre_2013": {"type": "boolean"},
                        "hizo_donaciones": {"type": "boolean"},
                        "importe_donaciones": {"type": "number"},
                        "vehiculo_electrico": {"type": "boolean"},
                        "reforma_energetica": {"type": "boolean"},
                        "renta_anual": {"type": "number"},
                        "edad": {"type": "integer"},
                        "es_autonomo": {"type": "boolean"},
                        # ... mas campos segun necesidad
                    }
                }
            },
            "required": ["ccaa"]
        }
    }
}
```

**2.2 Logica del tool**: Query a tabla `deductions` filtrado por territory + tax_year, evaluar `requirements_json` contra `answers`, devolver lista de deducciones aplicables con ahorro estimado.

**2.3 Formato de respuesta esperado**:
```json
{
  "deductions_found": 7,
  "estimated_savings": 2340.50,
  "deductions": [
    {
      "name": "Deduccion por maternidad",
      "amount": 1200.00,
      "legal_ref": "Art. 81 Ley 35/2006",
      "source_pdf": "docs/AEAT/...",
      "confidence": "alta"
    }
  ],
  "questions_needed": [
    "¿Hiciste donaciones a ONGs en 2025?",
    "¿Tu vivienda tiene certificado energetico?"
  ]
}
```

### FASE 3 — TaxAgent Proactivo (2-3 dias)

**3.1 Modificar system prompt de `tax_agent.py`**:
Anadir instruccion para que, cuando el usuario pregunte sobre IRPF/Renta/deducciones, el agente:
1. Consulte el perfil fiscal guardado (ya tenemos fiscal_profile)
2. Llame a `discover_deductions` con los datos que tiene
3. Identifique `questions_needed` (datos que le faltan)
4. Pregunte proactivamente al usuario: "Para identificar todas tus deducciones, necesito saber: ¿tienes hijos? ¿alquilas tu vivienda? ¿hiciste donaciones?"
5. Con cada nueva respuesta, re-ejecute `discover_deductions` con mas datos

**3.2 Guardar respuestas en perfil fiscal**: Las respuestas del usuario sobre deducciones se persisten en `datos_fiscales` JSON para no volver a preguntar en futuras sesiones.

### FASE 4 — Integrar en IRPFSimulator (1 semana)

**4.1 Ampliar `irpf_simulator.py`**: Actualmente solo aplica deducciones estructurales (MPYF, SS, trabajo). Anadir parametro `deductions_list` que reciba la salida de `discover_deductions` y las aplique sobre cuota integra:

- Deducciones estatales sobre cuota estatal
- Deducciones autonomicas sobre cuota autonomica
- Mostrar desglose completo: cuota integra → deducciones → cuota liquida

**4.2 Formato de salida mejorado**:
```
IRPF 2025 — Madrid
  Base imponible: 35,000 EUR
  Cuota integra: 7,245 EUR (estatal 3,855 + autonomica 3,390)
  Deducciones encontradas:
    - Maternidad: -1,200 EUR (Art. 81 LIRPF)
    - Alquiler joven Madrid: -1,000 EUR (Art. 4.1 DLeg 1/2010)
    - Donaciones: -200 EUR (Art. 68.3 LIRPF)
  Total deducciones: -2,400 EUR
  Cuota liquida: 4,845 EUR
  Tipo efectivo: 13.84% (vs 20.70% sin deducciones)
  AHORRO IDENTIFICADO: 2,400 EUR
```

### FASE 5 — Deducciones forales PV/Navarra (DIFERENCIADOR — 1 semana)

Extraer y estructurar deducciones de:
- **Araba**: NF 33/2013 consolidada (ya en docs/)
- **Bizkaia**: Normativa foral IRPF (ya en docs/)
- **Gipuzkoa**: NF 3/2014 + NF 1/2025 reforma (ya en docs/)
- **Navarra**: LF 26/2016 + modificaciones (ya en docs/)

Estas deducciones son DISTINTAS a las autonomicas de regimen comun. TaxDown NO las cubre. Impuestify sera el UNICO que las tenga.

### FASE 6 — Export + Compartir con asesor/gestoria (ALTA PRIORIDAD)

> **Estrategia**: NO queremos presentacion telematica. Impuestify es el complemento del asesor: prepara todo para que el gestor solo tenga que presentar. El usuario puede descargarse un informe o enviarlo directamente a su gestoria.

**6.1 Endpoint `POST /api/export/irpf-report`** (auth requerida)

Genera un informe PDF/JSON con:
- Datos del contribuyente (nombre, NIF, CCAA)
- Simulacion IRPF completa (base imponible, cuota integra, deducciones, cuota liquida)
- Lista de deducciones identificadas con base legal y ahorro estimado
- Checklist de documentos necesarios para aplicar cada deduccion
- Disclaimer: "Este informe es orientativo. Consulte con su asesor fiscal."

Formato de salida:
```json
{
  "report_url": "/api/export/irpf-report/abc123.pdf",  // PDF descargable
  "report_json": { ... },                                // JSON estructurado
  "share_token": "tok_xyz",                              // Token para compartir (expira 7 dias)
  "share_url": "https://impuestify.es/report/tok_xyz"    // URL publica temporal
}
```

**6.2 Endpoint `POST /api/export/share-with-advisor`** (auth requerida)

Envia el informe por email a la gestoria del usuario:
```json
{
  "advisor_email": "migestor@gestoria.com",
  "advisor_name": "Gestoria Lopez",
  "report_id": "abc123",
  "message": "Adjunto mi simulacion IRPF 2025 con las deducciones identificadas."
}
```

**6.3 Informe de deducciones** (formato legible para gestores)

```
═══════════════════════════════════════════════
   INFORME FISCAL — Impuestify
   Ejercicio: 2025 | Generado: 04/03/2026
═══════════════════════════════════════════════

CONTRIBUYENTE
  Nombre: Juan Garcia Lopez
  CCAA: Madrid

SIMULACION IRPF 2025
  Rendimientos del trabajo: 35,000 EUR
  Base imponible general: 28,450 EUR
  Cuota integra: 7,245 EUR

DEDUCCIONES IDENTIFICADAS (7)
  1. Maternidad (Art. 81 LIRPF)           -1,200 EUR
  2. Alquiler joven Madrid (DLeg 1/2010)  -1,000 EUR
  3. Donaciones ONG (Art. 68.3 LIRPF)       -200 EUR
  ...
  Total deducciones:                       -2,400 EUR

RESULTADO
  Cuota liquida estimada: 4,845 EUR
  Tipo efectivo: 13.84%
  AHORRO IDENTIFICADO: 2,400 EUR

DOCUMENTOS A APORTAR
  [ ] Libro de familia (deduccion maternidad)
  [ ] Contrato de alquiler + recibos (deduccion alquiler)
  [ ] Certificado de donacion (deduccion donaciones)

⚠️ Este informe es orientativo y no constituye
   asesoramiento fiscal profesional.

   Generado por Impuestify — impuestify.es
═══════════════════════════════════════════════
```

**6.4 Libreria para PDF**: Usar `reportlab` (Python, ya madura) o `weasyprint` (HTML→PDF).

### Prioridad de ejecucion

| Orden | Fase | Esfuerzo | Impacto | Justificacion |
|-------|------|----------|---------|---------------|
| **1** | Fase 1.1-1.2 (tabla + estatales) | 1-2 dias | Base | Sin esto nada funciona |
| **2** | Fase 2 (Discovery Tool) | 3-5 dias | Alto | El usuario empieza a ver deducciones |
| **3** | Fase 3 (TaxAgent proactivo) | 2-3 dias | Muy alto | Diferencia la experiencia vs AsesorIA |
| **4** | Fase 1.4 (forales) | 1 semana | **MAXIMO** | Diferenciador unico vs TaxDown |
| **5** | Fase 6 (Export + compartir asesor) | 1 semana | **Muy alto** | Da utilidad tangible al usuario |
| **6** | Fase 1.3 (autonomicas top 5 CCAA) | 1-2 semanas | Alto | Completar cobertura |
| **7** | Fase 4 (integrar en simulator) | 1 semana | Alto | Calculo preciso end-to-end |

### DESCARTADO
- ~~APImpuestos~~ — no queremos presentacion telematica
- ~~Colaborador Social AEAT~~ — no es prioritario
- Impuestify complementa al asesor, no lo sustituye

### Para FRONTEND agent:
- Implementar PWA (service worker + manifest.json) en lugar de app nativa
- Landing diferenciada: "El unico asistente fiscal con IA que cubre territorios forales"
- Mostrar deducciones encontradas con formato visual en el chat (cards con ahorro estimado)
- Boton "Descargar informe PDF" y "Enviar a mi asesor" en resultados de simulacion
- Formulario simple para email del asesor/gestoria

[2026-03-03] [FRONTEND] [🟢 DONE] - Panel Admin de Usuarios (owner-only)

### Cambios realizados

**Archivos creados (2):**
- `pages/AdminUsersPage.tsx` — Tabla de usuarios con gestión de planes (owner-only)
- `pages/AdminUsersPage.css` — Estilos mobile-first (cards en móvil, tabla en desktop)

**Archivos modificados (2):**
- `App.tsx` — +import AdminUsersPage, +ruta `/admin/users` con ProtectedRoute (requireSubscription=false)
- `components/Header.tsx` — +import useSubscription/Shield, +link "Admin" visible solo si isOwner

**Funcionalidades:**
1. Tabla de usuarios: email, nombre, plan_type, status, fecha registro
2. Botón "Cambiar a Autónomo" / "Cambiar a Particular" por fila
3. Confirmación con window.confirm antes de ejecutar cambio
4. Feedback visual (banner success/error con auto-dismiss 5s)
5. Botón refresh para recargar lista
6. Redirige a /chat si el usuario no es owner
7. Layout responsive: cards en móvil (<1024px), tabla en desktop (>=1024px)
8. Badges de colores para plan (owner/autonomo/particular) y status (active/grace/inactive)
9. Icono Crown junto al email del owner
10. Spinner en botones durante cambio de plan

**Endpoints consumidos:**
- `GET /api/admin/users` → lista de usuarios
- `PUT /api/admin/users/{id}/plan` → cambio de plan

**Build:** ✅ Exitoso (npm run build sin errores)

---

[2026-03-03] [BACKEND] [🟢 DONE] - Perfil Fiscal de Autónomos + Integración Workspace-Tools + Alta Admin

### Cambios realizados

**1. Backend — 12 campos nuevos para perfil fiscal de autónomo**
- Archivo: `backend/app/routers/user_rights.py`
- Nuevos campos en `FiscalProfileRequest` y `_DATOS_FISCALES_KEYS`:
  - `epigrafe_iae` (str) — Código IAE del Modelo 036
  - `tipo_actividad` (str) — "profesional" | "empresarial" | "artistica"
  - `fecha_alta_autonomo` (str) — Fecha ISO de alta
  - `metodo_estimacion_irpf` (str) — "directa_normal" | "directa_simplificada" | "objetiva"
  - `regimen_iva` (str) — "general" | "simplificado" | "recargo_equivalencia" | "exento"
  - `rendimientos_netos_mensuales` (float) — Para cálculo RETA
  - `base_cotizacion_reta` (float) — Base elegida
  - `territorio_foral` (bool) — PV/Navarra
  - `territorio_historico` (str) — "bizkaia" | "gipuzkoa" | "araba" | "navarra"
  - `tipo_retencion_facturas` (float) — 15.0 o 7.0
  - `tarifa_plana` (bool)
  - `pluriactividad` (bool)
- **No requiere migración BD** — todo va al JSON `datos_fiscales` existente.

**2. Backend — Endpoint admin (owner-only)**
- Archivo nuevo: `backend/app/routers/admin.py`
- `GET /api/admin/users` — Lista usuarios con plan_type, status, email, nombre
- `PUT /api/admin/users/{user_id}/plan` — Cambia plan_type ("particular" | "autonomo")
  - Si autonomo: también actualiza `user_profiles.situacion_laboral`
  - Crea subscription si no existe (admin_granted)
- Solo accesible por owner (verificado via SubscriptionAccess.is_owner)
- Registrado en `backend/app/main.py`

**3. Backend — Integración fiscal_profile → agentes**
- `chat_stream.py`: Carga `datos_fiscales` + `ccaa_residencia` + `situacion_laboral` del user_profiles
  y lo pasa como `fiscal_profile` dict a ambos agentes.
- `WorkspaceAgent`: Acepta `fiscal_profile`, lo inyecta en system prompt, tiene tools
  `calculate_modelo_303` y `calculate_modelo_130` delegados al registry central.
- `TaxAgent`: Acepta `fiscal_profile`, lo inyecta como contexto adicional antes del memory.

**4. Frontend — Formulario de autónomo en Settings**
- `hooks/useFiscalProfile.ts`: +12 campos en `FiscalProfile` interface + `EMPTY_PROFILE`
- `pages/SettingsPage.tsx`: Sección colapsable "Datos de autónomo" en tab Fiscal
  - Solo visible si `subscription.planType === 'autonomo'` o `subscription.isOwner`
  - 12 campos: epígrafe, tipo actividad, fecha alta, estimación, régimen IVA, retención,
    rendimientos netos, base RETA, territorio foral/histórico, tarifa plana, pluriactividad

**5. Tests — 23 tests nuevos**
- `backend/tests/test_admin.py` (9 tests) — Modelos, acceso owner, lógica plan change
- `backend/tests/test_fiscal_profile_autonomo.py` (14 tests) — Campos, keys, save logic, formato agentes

### Para FRONTEND agent: Pendiente panel admin de usuarios

El frontend necesita una nueva página para que el owner gestione usuarios.

**Endpoints backend (ya implementados, auth via Bearer token):**

```
GET /api/admin/users → UserListItem[]

interface UserListItem {
  id: string
  email: string
  name: string | null
  is_owner: boolean
  plan_type: string | null     // "particular" | "autonomo" | "owner" | null
  subscription_status: string | null  // "active" | "grace_period" | "inactive" | null
  created_at: string | null
}
```

```
PUT /api/admin/users/{user_id}/plan
Body: { "plan_type": "autonomo" }   // o "particular"
→ { message: string, user_id: string, plan_type: string }
```

**Ambos devuelven 403 si el caller NO es owner.**

**Requisitos UI:**
1. Nueva página `AdminUsersPage.tsx` (ruta `/admin/users`) o pestaña en Dashboard
2. Solo visible/accesible si `subscription.isOwner === true` (usar `useSubscription()`)
3. Tabla con columnas: email, nombre, plan_type, status, acciones
4. Botón "Cambiar a Autónomo" por fila (confirm antes de ejecutar)
5. Feedback visual (toast o banner) tras cambio exitoso o error
6. Botón refresh para recargar lista
7. Ruta protegida en `App.tsx` con check `isOwner`
8. Hook API: usar `useApi()` → `apiRequest('/api/admin/users')` etc.

---

[2026-01-11 16:30] [SYSTEM] [🟢 DONE] - Sistema de comunicación entre agentes inicializado

[2026-01-11] [FRONTEND] [🟢 DONE] - CSS Responsive Mobile-First Refactoring

### Resumen de Cambios CSS

**Archivos modificados:** 13 archivos CSS

#### 1. Conversión a Mobile-First (min-width en lugar de max-width)
| Archivo | Estado Anterior | Estado Actual |
|---------|-----------------|---------------|
| `global.css` | max-width: 768px | Mobile-first (comentarios) |
| `Footer.css` | max-width: 768px | min-width: 768px |
| `Auth.css` | max-width: 480px | min-width: 480px |
| `Home.css` | max-width: 1024px/768px | min-width: 768px/1024px |
| `Dashboard.css` | max-width: 1024px/768px | min-width: 768px/1024px |
| `LegalPage.css` | max-width: 768px | min-width: 768px |

#### 2. Variables CSS Consistentes
Todos los archivos ahora usan las variables de `global.css`:
- Colores: `--color-primary`, `--color-gray-*`, `--color-error`, `--color-success`
- Espaciado: `--spacing-*`
- Bordes: `--radius-*`
- Sombras: `--shadow-*`
- Transiciones: `--transition-*`
- Z-index: `--z-*`

**Archivos actualizados con variables CSS:**
- `Header.css` - eliminados ~15 colores hardcodeados
- `Footer.css` - eliminados ~20 colores hardcodeados
- `ConversationSidebar.css` - eliminados ~12 colores hardcodeados
- `AITransparencyModal.css` - eliminados ~15 colores hardcodeados
- `ThinkingIndicator.css` - eliminados ~5 colores hardcodeados
- `Chat.css` - eliminados ~25 colores hardcodeados
- `SettingsPage.css` - eliminado :root duplicado

#### 3. Breakpoints Consistentes
- **Mobile:** 320px+ (estilos base)
- **Tablet:** 768px+ (`@media (min-width: 768px)`)
- **Desktop:** 1024px+ (`@media (min-width: 1024px)`)

#### 4. Verificación
- Build: ✅ Exitoso (`npm run build` sin errores)
- Tamaño CSS: 44.56 kB (gzip: 7.23 kB)

#### Notas para otros agentes
- La paleta de colores está en `frontend/src/styles/global.css`
- Usar siempre variables CSS en lugar de valores hardcodeados
- Seguir patrón mobile-first: estilos base para móvil, media queries para pantallas más grandes

## Estado Biblioteca RAG — Para todos los agentes
---
> Última actualización: 2026-03-03 | **419 PDFs + 9 Excel = 428 archivos** en `docs/`

### ✅ Cobertura actual (lo que el RAG tiene disponible para ingestar)

**Normativa foral (Bizkaia/Gipuzkoa/Araba/Navarra):**
- Reforma Fiscal 2025 completa: Gipuzkoa NF 1/2025 + Araba NF 3/2025 + Bizkaia NF 2/2025 ← CRÍTICO
- Impuesto Complementario Global (Pilar 2 OCDE): los 3 territorios cubiertos
- IRPF + IVA + IS + ISD + Autónomos forales: completo

**CCAA régimen común:**
- Todos los territorios con DLeg tributos cedidos + ley de medidas 2025
- Novedades 2025 destacadas: Murcia ITP→7.75%, Galicia Ley 5/2025, Madrid consolidado 2025, CyL dic 2025

**AEAT y Estatal:**
- Manual IVA **2025** (6.1 MB) ← actualizado
- Instrucciones Modelos 303/390 IVA 2025 + Modelo 190 retenciones
- Cuadros retenciones IRPF 2025 y 2026
- **RDL 2/2026** ← CRÍTICO para Renta 2025: imputación inmobiliaria, EV, DANA, SEPE
- **Ley 5/2025** ← deducción 340€ para SMI
- **REAF Panorama 2025** (7.5 MB) ← deducciones autonómicas completas
- Cap I-IV Tributación Autonómica 2025 (Ministerio Hacienda)
- Módulos EO 2026 (Orden HAC/1425/2025)

### 📅 Pendiente — disponible ~marzo/abril 2026
- Manual Práctico Renta 2025 Tomo 1 + Tomo 2 (AEAT) — aún no publicados
- Orden HAC Modelo 100 ejercicio 2025 — antes del 8 abril 2026

### ⚠️ Acción recomendada para Backend
**RE-INGESTA RAG necesaria** con los nuevos PDFs de sesiones 7-10 (39 documentos nuevos).
Prioridad de ingesta:
1. Reforma Fiscal 2025 forales (NF Gipuzkoa/Araba/Bizkaia) — afecta IS/IRPF/IVA
2. RDL 2/2026 y Ley 5/2025 — afectan respuestas sobre Renta 2025
3. Manual IVA 2025 + Modelos 303/390 — actualización anual IVA
4. REAF Panorama 2025 — deducciones autonómicas actualizadas

[2026-03-02 23:30] [BACKEND] [🟢 DONE] - Sistema de suscripciones Stripe COMPLETO (backend)

### Resumen de Cambios Backend — Suscripciones Stripe

**Producto Stripe:** `prod_U4lJ9l8NhKvFHZ` | **Precio:** 5 EUR/mes (cambiado de 15 EUR el 2026-03-04) | **Price ID:** verificar en Stripe Dashboard

**Archivos creados (6):**
- `app/services/subscription_service.py` — Stripe integration + access control
- `app/auth/subscription_guard.py` — FastAPI deps: require_active_subscription (403)
- `app/security/content_restriction.py` — Detección queries autónomos (~30 keywords)
- `app/routers/subscription.py` — Endpoints: create-checkout, status, create-portal, webhook
- `app/routers/contact.py` — POST /api/contact (formulario autónomos interesados)
- `scripts/migrate_subscriptions.py` — Migración usuarios existentes

**Archivos modificados (14):** requirements.txt, config.py, .env.example, turso_client.py, models.py, main.py, auth.py, chat_stream.py, chat.py, notifications.py, payslips.py, workspaces.py, tax_agent.py, workspace_agent.py, autonomous_quota_tool.py

**Lógica de acceso:**
- Owner (fernando.prada@proton.me) → acceso total sin restricciones
- Suscripción activa → acceso (solo contenido asalariados)
- Grace period (hasta 31/12/2026) → acceso (solo contenido asalariados)
- Sin suscripción → 403

**Restricción de contenido (3 capas):**
1. Router: detect_autonomo_query() bloquea antes del agente
2. Agent: restricted_mode filtra tools (calculate_autonomous_quota, calculate_vat_balance)
3. Tool: safety net en autonomous_quota_tool

**Migración ejecutada:** 14 usuarios, 14 Stripe customers reales (cus_...), owner=active, 13 users=grace_period

**Tests:** 35 tests en test_subscription.py (todos pasan)

**API Endpoints nuevos:**
| Endpoint | Auth | Propósito |
|----------|------|-----------|
| `POST /subscription/create-checkout` | JWT | Crea Checkout Session → retorna checkout_url |
| `GET /subscription/status` | JWT | Estado de suscripción del usuario |
| `POST /subscription/create-portal` | JWT | Stripe Customer Portal → retorna portal_url |
| `POST /subscription/webhook` | Stripe Sig | Procesa webhooks (público) |
| `POST /api/contact` | JWT | Formulario de contacto |

**UserResponse ampliado:** ahora incluye `is_owner: bool` y `subscription_status: str` en login/register/me

#### Notas para Frontend
- Cuando `subscription_status != "active" && subscription_status != "grace_period" && !is_owner` → redirigir a paywall
- Paywall: llamar `POST /subscription/create-checkout` con `{success_url, cancel_url}` → redirigir a `checkout_url`
- Gestionar suscripción: `POST /subscription/create-portal` con `{return_url}` → redirigir a `portal_url`
- Página contacto: `POST /api/contact` con `{name, email, message, request_type: "autonomo_interest"}`
- Variables Railway nuevas: STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_ID

[2026-03-03 12:00] [FRONTEND] [🟢 DONE] - Cumplimiento Cookies LSSI-CE + RGPD

### Resumen — Cookie Consent (LSSI-CE + RGPD + AEPD)

**Librería:** `vanilla-cookieconsent` v3 (~10KB gzip, MIT)

**Archivos creados (2):**
- `components/CookieConsent.tsx` — Wrapper React, exporta `showCookiePreferences()`
- `pages/CookiePolicyPage.tsx` — Página legal `/politica-cookies` (usa LegalPage.css)

**Archivos modificados (4):**
- `App.tsx` — +CookieConsentBanner component + ruta /politica-cookies
- `Footer.tsx` — +Link Política de Cookies (Legal) + botón Configurar Cookies (Soporte) + badge LSSI-CE
- `Footer.css` — +clase `.footer-cookie-btn`
- `PrivacyPolicyPage.tsx` — +sección 7 referencia a Política de Cookies (renumerada 8→9)

**Configuración del banner:**
- Layout: `bar` bottom, botones equiparados (AEPD, sin dark patterns)
- Categorías: `necessary` (readOnly) + `analytics` (OFF por defecto, futuro)
- Cookie: `cc_cookie`, 6 meses (AEPD max 13 meses)
- Textos: 100% español

**Para añadir analytics en el futuro:**
Solo configurar scripts en la categoría `analytics` de `CookieConsent.tsx`. No requiere más cambios.

#### Notas para otros agentes
- Importar `showCookiePreferences` de `components/CookieConsent` para reabrir el panel
- Si se añade nueva cookie → actualizar tabla en CookieConsent.tsx Y en CookiePolicyPage.tsx
- NO cambiar `equalWeightButtons: true` — es requisito AEPD
- Build verificado: ✅ sin errores

[2026-03-03] [FRONTEND] [🟢 DONE] - Frontend adaptado al sistema de suscripciones Stripe

### Resumen de Cambios Frontend — Suscripciones + Legal

**Archivos creados (6):**
- `hooks/useSubscription.ts` — Hook para estado de suscripcion (status, createCheckout, openPortal)
- `pages/SubscribePage.tsx` + `.css` — Paywall con boton de Stripe Checkout
- `pages/ContactPage.tsx` + `.css` — Formulario contacto (/contact?type=autonomo)
- `pages/TermsPage.tsx` — Terminos y Condiciones (adaptado de TERMS_OF_SERVICE.md)
- `pages/DataRetentionPage.tsx` — Politica de Retencion de Datos (adaptado de DATA_RETENTION.md)

**Archivos modificados (7):**
- `App.tsx` — ProtectedRoute con subscription guard, nuevas rutas (/subscribe, /contact, /terms, /data-retention), eliminados placeholders
- `hooks/useAuth.tsx` — User interface +is_owner, +subscription_status
- `pages/Home.tsx` — Eliminado "Gratis", seccion pricing 15EUR/mes, link autonomos a /contact
- `pages/Home.css` — CSS pricing section responsive
- `pages/SettingsPage.tsx` — Tab "Suscripcion" con estado, portal Stripe, y checkout
- `pages/SettingsPage.css` — CSS subscription section
- `pages/AITransparencyPage.tsx` — Eliminados emojis (reemplazados por Lucide icons), eliminado link GitHub
- `pages/PrivacyPolicyPage.tsx` — Eliminado link GitHub
- `pages/LegalPage.css` — Clase inline-icon para legal pages
- `components/Footer.tsx` — /security ahora es mailto (no teniamos pagina dedicada)

**Logica de acceso (ProtectedRoute):**
- Auth requerido → si no → /login
- Suscripcion requerida (configurable) → si no → /subscribe
- Settings NO requiere suscripcion (para poder gestionar la propia suscripcion)

**Eliminados:**
- Todas las referencias a "gratis", "free", "gratuito"
- Todos los links a GitHub (PrivacyPolicy, AITransparency)
- Emojis en AITransparencyPage (sustituidos por Lucide icons)
- Placeholders en rutas legales (/terms, /data-retention apuntaban a PrivacyPolicyPage)

**Build:** ✅ Exitoso (npm run build sin errores)

#### Notas para otros agentes
- `useSubscription()` hook disponible para cualquier componente que necesite verificar acceso
- ProtectedRoute acepta prop `requireSubscription={false}` para rutas que solo necesitan auth
- Checkout redirect URLs: success→/chat?subscription=success, cancel→/subscribe?canceled=true
- Portal return URL: /settings

[2026-03-03 20:05] [CRAWLER] [🟢 DONE] - Sesión 12 completada. +19 archivos (10 PDFs + 9 Excel). La Rioja actualizada (+4 docs: consolidado 2026 + Leyes 6/2024 + 9/2025 + 5/2025). Diseños de Registro AEAT descargados (15 archivos: Modelos 111/115/130/131/190/200/202/303/347/349/390/714/720 + Instrucciones 650/651). Total: 428 archivos. CLM verificado: sin cambios significativos. ⚠️ BACKEND: ver instrucciones detalladas abajo sobre Diseños de Registro para implementación de herramientas.

---

## 📢 INSTRUCCIONES PARA BACKEND — Diseños de Registro / Modelos AEAT (Sesión 12)

> **Contexto**: El usuario pidió investigar los XSD de los modelos AEAT. Resultado: **NO hay XSD** (excepto Modelo 200). AEAT usa ficheros planos de posiciones fijas. Los diseños de registro están en `docs/AEAT/Modelos/DisenosRegistro/`.

### Hallazgo clave: NO son XSD, son Diseños de Registro (flat-file)

La AEAT **NO usa XSD** para la mayoría de modelos. Los modelos se presentan mediante **ficheros planos de texto** con campos en **posiciones fijas** (fixed-width records). Los diseños de registro (Excel/PDF) describen:
- Posición inicial y longitud de cada campo
- Tipo de dato (numérico, alfanumérico)
- Registros de tipo 1 (declarante) y tipo 2 (detalle)

**Excepciones:**
- **Modelo 200 (IS)**: Sí tiene XSD (`mod2002024.xsd`) para importar datos contables via XML en Sociedades WEB
- **Modelos 650/651 (ISD)**: NO tienen diseño de registro — solo formulario web
- **Transición XML/XSD**: Orden HAC/747/2025 → a partir de enero 2027 para ejercicio 2026

### Archivos disponibles en `docs/AEAT/Modelos/DisenosRegistro/`

| Archivo | Modelo | Formato | Prioridad Backend |
|---------|--------|---------|-------------------|
| `DR303_e2026.xlsx` | 303 - IVA trimestral | Excel flat-file | **ALTA** (autónomos trimestrales) |
| `DR130_e2019.xls` | 130 - Pagos fraccionados IRPF ED | Excel flat-file | **ALTA** (autónomos) |
| `DR131_e2025.xlsx` | 131 - Pagos fraccionados IRPF EO | Excel flat-file | **MEDIA** (módulos) |
| `DR111_e2019.xls` | 111 - Retenciones trabajo/prof. | Excel flat-file | **MEDIA** (empresas) |
| `DR115_e2019.xls` | 115 - Retenciones alquileres | Excel flat-file | **BAJA** |
| `DR190_e2025.pdf` | 190 - Resumen anual retenciones | PDF diseño lógico | **MEDIA** |
| `DR200_e2024.xls` | 200 - IS (TIENE XSD) | Excel + XSD | **ALTA** (sociedades) |
| `DR202_e2025.xlsx` | 202 - Pagos fraccionados IS | Excel flat-file | **MEDIA** |
| `DR390_e2025.xlsx` | 390 - Resumen anual IVA | Excel flat-file | **MEDIA** |
| `DR347_e2025.pdf` | 347 - Operaciones con terceros | PDF diseño lógico | **BAJA** |
| `DR349_e2020.pdf` | 349 - Operaciones intracomunitarias | PDF diseño lógico | **BAJA** |
| `DR714_e2024.xls` | 714 - Patrimonio | Excel flat-file | **BAJA** |
| `DR720.pdf` | 720 - Bienes extranjero | PDF diseño lógico | **BAJA** |
| `Instrucciones_Modelo650_ISD.pdf` | 650 - ISD Sucesiones | PDF instrucciones | **MEDIA** (referencia) |
| `Instrucciones_Modelo651_ISD.pdf` | 651 - ISD Donaciones | PDF instrucciones | **MEDIA** (referencia) |

### Recomendación de implementación para Backend

**Opción A (recomendada): Tools de cálculo/simulación** — como el ya existente `irpf_calculator_tool.py`
- Crear tools que **calculen** los campos del modelo (no que generen el fichero)
- Ejemplo: `calculate_modelo_303(base_imponible, iva_deducible, ...)` → devuelve casillas 01-89
- Los diseños de registro sirven como **especificación de campos** (qué casillas hay, qué significan)

**Opción B: Generación de ficheros** — más complejo, futuro
- Generar ficheros planos de texto conformes al diseño de registro
- Útil para autónomos que quieran pre-rellenar sus declaraciones
- Requiere parsear los Excel para extraer posiciones/longitudes

**Para Modelo 200 (único con XSD):**
- Se puede implementar importación/exportación XML usando el XSD
- URL del XSD: buscar en la página de información del modelo 200 en sede AEAT

**Prioridad sugerida:**
1. **Modelo 303 IVA** → tool de cálculo de casillas IVA trimestral (complementa al TaxAgent)
2. **Modelo 130** → tool de cálculo pago fraccionado IRPF (autónomos estimación directa)
3. **Modelo 200 IS** → parser XSD para simulación IS

### URLs de referencia
- Diseños de registro: https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro.html
- Modelo 303 ayuda técnica: https://sede.agenciatributaria.gob.es/Sede/ayuda/consultas-informaticas/presentacion-declaraciones-ayuda-tecnica/modelo-303.html
- Modelo 200 importar datos: https://sede.agenciatributaria.gob.es/Sede/ayuda/consultas-informaticas/impuesto-sobre-sociedades-ayuda-tecnica/sociedades-web/importar-datos-contables-modelo-200.html
- Portal desarrolladores AEAT: https://www.agenciatributaria.es/AEAT.desarrolladores/

---

## Dependencias Pendientes
---
# Aquí los agentes registran cuando necesitan que otro complete algo primero
# Formato: [AGENT_ESPERANDO] espera a [AGENT_TRABAJANDO] para [TAREA]

## Conflictos Detectados
---
# Si un agente detecta que otro modificó el mismo archivo, lo registra aquí

## Instrucciones para Agentes
---
1. Al INICIAR una tarea: Añade línea con 🟡 IN_PROGRESS
2. Si estás BLOQUEADO esperando a otro: Añade línea con 🔴 BLOCKED
3. Al TERMINAR: Cambia tu línea a 🟢 DONE
4. Si necesitas review: Añade 📢 NEEDS_REVIEW
5. SIEMPRE haz `git pull` antes de empezar para ver cambios de otros agentes

[2026-02-22 00:00] [CRAWLER] [🟡 IN_PROGRESS] - Iniciando rastreo completo: Organización Bizkaia + descarga de docs Navarra, Gipuzkoa, Araba, CCAA régimen común y AEAT
[2026-02-23 10:00] [CRAWLER] [🟢 DONE] - Sesión 3 completada. +9 PDFs (Gipuzkoa Manual+NF3/2014+NF1/2025+DF33, Araba Manual+Instrucción, Bizkaia Instrucciones 1/2025+2/2024+2/2023). Total: 313 PDFs. Instrucciones actualizadas: nueva prioridad IS y Autónomos — iniciando descarga.
[2026-02-23 11:00] [CRAWLER] [🟢 DONE] - Sesion 4 completada. +5 PDFs (IS estatal Ley27/2014+RD634/2015, Autonomos Ley20/2007, Bizkaia IS NF11/2013+DF203/2013). Total: 318 PDFs. Pendiente: IS foral Gipuzkoa+Araba+Navarra (portales AJAX), RDL 13/2022, tablas RETA 2025. Backend: re-ingesta RAG recomendada para nuevos PDFs IS+Autonomos.
[2026-02-23 11:30] [CRAWLER] [🟢 DONE] - Sesion 4 ampliada. +3 adicionales (RDL13/2022 autonomos, Gipuzkoa IS Novedades+Modelo200). Total final: 321 PDFs. Pendiente sesion 5: IS foral Gipuzkoa(NF2/2014)+Araba(NF37/2013)+Navarra(LF26/2016) via navegador, RETA2025, Orden modulos EO.
[2026-02-23 12:00] [CRAWLER] [🟢 DONE] - Sesion 5 completada. +23 PDFs únicos (IS forales: Gipuzkoa NF2/2014+DF17/2015+OF252/2025, Araba NF37/2013+DF40/2014+Medidas2025, Navarra LF26/2016+LF22/2023+LF20/2024, Bizkaia Instrucciones IS 3+4/2023, Estatal OrdenHAC 1347+1425 modulos EO, Libro Normativa ene/mar 2025+CapII+CapIV, REAF 2024, RETA 2025). Total: 345 PDFs. IS foral 4 territorios COMPLETADO. Iniciando sesion 6: ITP-AJD autonómico + IP autonómico CCAA.
[2026-02-23 13:00] [CRAWLER] [🟢 DONE] - Sesion 6 completada. +9 PDFs (Cap I+III Tributacion Autonomica 2025, Orden HAC/242/2025 Modelos IRPF+IP, Tabla ITP CCAA, Cataluna DLeg1/2024 tributos cedidos COMPLETO, Andalucia Ley5/2021 actual, Baleares+Galicia consolidados 2024, Valencia Catedra Notarial 2025). Total: 354 PDFs. Cobertura ITP-AJD+IP+IRPF autonómico muy alta. Sesion completa — re-ingesta RAG recomendada para todos los nuevos PDFs.
[2026-02-25 09:00] [CRAWLER] [🟡 IN_PROGRESS] - Iniciando sesión 7 (rastreo completo). Objetivos: CCAA rezagadas (Aragón/Asturias/Cantabria/CyL/CLM/Extremadura/Murcia modificaciones 2023-2025), Galicia Leyes 10/2023+5/2024, Canarias ZEC+REF, Gipuzkoa IS NF2/2014 versión reciente + Reglamento IVA, Araba NF33/2013 actualizada, Estatal RD1624/1992 IVA.
[2026-02-25 16:00] [CRAWLER] [🟢 DONE] - Sesión 10 completada. +1 PDF. REAF Panorama Fiscalidad Autonómica y Foral 2025 (7.5 MB) — actualización del 2024. Deducciones autonómicas para Renta 2025: COBERTURA COMPLETA (Cap I-IV Tributación Autonómica 2025 + REAF 2025 + leyes 2025 de cada CCAA). Pendiente ~abril 2026: Manual Renta 2025 Tomo 2 Deducciones Autonómicas (AEAT, aún no publicado). Total: 394 PDFs.
[2026-02-25 15:00] [CRAWLER] [🟡 IN_PROGRESS] - Sesión 9: investigación campaña Renta 2025 (abr2026) — modelos 303/390/190, Manual IVA 2025, RDL 2/2026, Ley 5/2025.
[2026-02-25 15:30] [CRAWLER] [🟢 DONE] - Sesión 9 completada. +8 PDFs. AEAT: Manual IVA 2025(6.1MB)+Mod303 instrucciones+Mod390+Mod190 retenciones+Cuadros retenciones 2025+2026. BOE: RDL 2/2026(novedades IRPF 2025: imputación inmobiliaria 1,1% ampliada, EV/energía prorrogadas, desempleo no obliga)+Ley 5/2025(DA61 deducción 340€ SMI). Total: 393 PDFs. Pendiente ~marzo2026: Manual Renta 2025 + Orden HAC Modelo 100 ej.2025. ⚠️ IMPORTANTE para RAG: RDL 2/2026 es CRÍTICO para responder preguntas sobre Renta 2025.
[2026-02-25 14:00] [CRAWLER] [🟡 IN_PROGRESS] - Sesión 8: Araba NF 21/2025 (encontrada BOTHA 147) + CCAA rezagadas (Aragón/Asturias/Cantabria/CyL/Extremadura/Murcia leyes 2025).
[2026-02-25 14:30] [CRAWLER] [🟢 DONE] - Sesión 8 completada. +8 PDFs. Araba: NF21/2025(529KB)+DFN2/2025(390KB). CCAA: Aragón Ley3/2025 empresa familiar, Asturias Ley3/2025 mod.DLeg(dic2025), Cantabria Ley3/2024 medidas2025, CyL BOE-A-2025-27120(dic2025), Extremadura Ley1/2025, Murcia Ley3/2025 Presupuestos(ITP→7.75%). Total: 385 PDFs. Cobertura CCAA régimen común: COMPLETA. ⚠️ RE-INGESTA RAG: especialmente Murcia(ITP), CyL+Asturias(dic2025 no en consolidados).
[2026-02-25 13:00] [CRAWLER] [🟢 DONE] - Sesión 7 completada. +21 PDFs. REFORMA FISCAL 2025 FORALES: Gipuzkoa NF1/2025(integral may2025)+NF2+3(Pilar2)+4/2025+DFN1/2025, Araba NF3/2025(abr2025)+NF16(Pilar2)+17(IMIC)+26/2025, Bizkaia NF2/2025(abr2025)+NF_dic2025. CCAA: Galicia Ley10/2023+5/2024+5/2025(pub feb2026 MUY RECIENTE), Canarias REF Ley19/1994+RD1758/2007 ZEC, Madrid DLeg1/2010_2025+Ley5/2024, Andalucía Ley8/2025(Presupuestos2026)+Ley5/2021consolidado2026, Estatal RD1624/1992 ReglamentoIVA(pendiente histórico cerrado). Total: 375 PDFs. ⚠️ RE-INGESTA RAG CRÍTICA: normas reforma fiscal 2025 forales son fundamentales para consultas IS/IRPF/IVA actualizadas.
[2026-03-02 10:00] [CRAWLER] [🟢 DONE] - Sesión 11 completada. +17 PDFs — ARABA RASTREO COMPLETO. Textos consolidados del portal (11): NF33/2013 IRPF consolidada(1572KB), DF40/2014 Reglamento IRPF(968KB), NF9/2013 IP Patrimonio(304KB), NF11/2003 ITP-AJD(432KB)+DF66/2003 Reglamento(252KB), NF11/2005 ISD consolidada+DF74/2006 Reglamento(392KB), NF37/2013 IS consolidada(1556KB)+DF41/2014 Reglamento IS(524KB), DFN12/1993 IVA consolidado portal(1572KB)+DF124/1993 Reglamento IVA portal(848KB). BOTHA(6): DF23/2025 retenciones, DF42/2025 IRPF+corrección, DF41/2025 coeficientes, NF9/2024 cultura, DF5/2025 ITP-AJD(8.6MB). Total: 409 PDFs. Cobertura Araba: COMPLETA (IRPF+IS+IVA+ISD+IP+ITP-AJD todos consolidados). ⚠️ RE-INGESTA RAG recomendada: NF33/2013 IRPF consolidada es CRÍTICA + nuevos impuestos IP/ITP-AJD. Erratum: IS/Araba-DF_40_2014_ReglamentoIS.pdf era en realidad Reglamento IRPF.
