# Auditoría técnica — Modelo 303 (IVA trimestral)

- **Fecha**: 2026-05-10
- **Auditor**: Auditoría documental TaxIA (AI)
- **Producto**: Impuestify (TaxIA)
- **Componentes auditados**:
  - `backend/app/tools/modelo_303_tool.py` — function-calling tool del LLM (en producción).
  - `backend/app/utils/calculators/modelo_303.py` — calculador "canónico" usado en tests y wizards internos.
  - `backend/tests/test_modelo_303.py` — 14 tests, todos contra `Modelo303Calculator` (NO contra el tool).
  - `backend/app/services/modelo_pdf_generator.py` — generador PDF informativo (`_render_303`).
- **Variantes forales detectadas**:
  - Mod. 300 (Gipuzkoa), F69 (Navarra), 303 foral (Bizkaia/Araba) — **anotadas como labels** en `_FORAL_IVA_CONFIG`, sin lógica diferencial.
  - Mod. 420 (IGIC Canarias) — delegado a `Modelo420Calculator` (fuera del alcance de esta auditoría).
- **Normativa contrastada**: Ley 37/1992 IVA (Arts. 84, 90-91, 154-163, 163 decies); RD 1624/1992 (Reglamento IVA, Art. 71 plazos, Art. 62.6 SII); Orden HFP/2367/2013 y modificativas (modelo 303 vigente con casillas 80-95 SII y casillas 122-126 criterio caja).

> **Nota metodológica**: Los WebFetch a `sede.agenciatributaria.gob.es/.../modelo-303.html`, al BOE (Orden HFP/1124/2022), y a `agenciatributaria.es/.../Plazos...303_y_390...` devolvieron 404/contenido distinto el día de la auditoría. La auditoría se basa en (a) cross-check de la Ley 37/1992 (BOE consolidado) y (b) conocimiento normativo vigente del modelo 303 versión 2024-2026. Donde haya duda, se recomienda re-verificar contra el manual práctico AEAT del ejercicio.

---

## 1. Inventario de cobertura

| Materia | Estado en `modelo_303_tool.py` | Estado en `modelo_303.py` (calculator) | Veredicto |
|---|---|---|---|
| Tipo general 21% | Sí (hardcoded 0.21) | Sí (constante `_TIPO_GENERAL`) | OK |
| Tipo reducido 10% | Sí (0.10) | Sí | OK |
| Tipo superreducido 4% | Sí (0.04) | Sí | OK |
| Tipo 0% productos básicos (RDL 20/2022, prorrogado 2024-2025) | **NO** | **NO** | GAP |
| Tipo 5% pasta/aceites (RDL 4/2022 transitorio) | **NO** | **NO** | GAP |
| Adquisiciones intracomunitarias (cas. 10-12) | Sí (1 tipo) | Sí (1 tipo) | OK parcial — solo permite UN tipo |
| Inversión Sujeto Pasivo (cas. 13-14, Art. 84 LIVA) | **NO** | Sí | DRIFT |
| Modificación bases/cuotas anteriores (cas. 15-16) | **NO** | Sí | DRIFT |
| Bienes de inversión deducible (cas. 30-31) | Sí (cuota) | Sí (base+cuota) | OK |
| Importaciones bienes inversión (cas. 34-35) | **NO** | Sí | GAP |
| Intracom. de inversión (cas. 38-39) | **NO** | Sí | GAP |
| Compensación REAGyP (cas. 42, Art. 130 LIVA) | **NO** | Sí | GAP |
| Regularización bienes inversión / prorrata (cas. 43-44) | **NO** | Sí | GAP |
| Prorrata general / especial | **NO** | Solo cas. 44 (regularización 4T) | GAP |
| % atribución al Estado (cas. 65) | Sí | Sí | OK |
| IVA Aduana diferido (cas. 77, RD 1073/2014) | **NO** | Sí | GAP |
| Cuotas a compensar anteriores | Sí (mal numerada como 71) | Sí (cas. 78) | **BUG** |
| Regularización anual 4T (cas. 68) | **NO** | Sí (gated por quarter==4) | GAP |
| Declaración complementaria (cas. 70) | **NO** | Sí | GAP |
| Resultado liquidación (cas. 71) | Numerada como compensación | Sí (cas. 71) | **BUG numeración** |
| Régimen criterio de caja (Art. 163 decies, casillas 122-126) | **NO** | **NO** | GAP funcional |
| SII obligatorio >6.010.121,04 € (Art. 62.6 RIVA) | **NO** detectado/avisado | **NO** | GAP funcional |
| Recargo equivalencia (Arts. 154-163) | **NO** | Detector + tabla `RE_RATES`, **sin integrar** | GAP funcional |
| Régimen simplificado (módulos) | **NO** (excluido en disclaimer) | Excluido | OK declarado |
| REBU bienes usados | **NO** | **NO** | Fuera de alcance |
| RECC (criterio caja) | **NO** | **NO** | GAP funcional |
| Plazos T1-T4 | **Mal redactados** | n/a | **BUG** |
| Variante 300 Gipuzkoa | Solo etiqueta texto | Solo flag `territory` | DRIFT semántico |
| Variante F69 Navarra | Solo etiqueta texto | Solo flag `territory` | DRIFT semántico |
| Variante 303 foral Bizkaia/Araba (BATUZ/TicketBAI) | Solo nota textual | Solo flag | DRIFT semántico |

---

## 2. Bugs críticos y discrepancias normativas

### BUG-303-01 (CRÍTICO) — Numeración casillas resultado en `modelo_303_tool.py`
- **Archivo**: `backend/app/tools/modelo_303_tool.py:325-341`.
- **Problema**: el tool computa `casilla_71 = compensacion_periodos_anteriores` y `resultado_final = casilla_69 - casilla_71`. En el modelo 303 vigente:
  - **Casilla 78** = cuotas a compensar de periodos anteriores (no 71).
  - **Casilla 71** = resultado liquidación (no la compensación).
  - **Casilla 69** = `66 + 77 - 78 + 68` (no `= casilla_66`).
- **Impacto**: el JSON expuesto al frontend y al PDF rotula mal las casillas y el usuario no podría trasladar el resultado del tool al formulario AEAT real. El cálculo aritmético del **resultado final** es correcto (devengado − deducible − compensación), pero las **etiquetas de casillas son incorrectas**.
- **Cross-check OK**: en `backend/app/utils/calculators/modelo_303.py:319-339` la numeración está bien (`casilla_78` compensación, `casilla_71` resultado liquidación).

### BUG-303-02 (CRÍTICO) — Plazos de presentación incorrectos
- **Archivo**: `modelo_303_tool.py:426`, `modelo_303_tool.py:583`.
- **Texto**: *"antes del dia 20 del mes siguiente al trimestre (o 30 de enero para el 4T)"*.
- **Norma vigente** (Art. 71.4 RIVA + calendario AEAT 2025/2026):
  - T1 → **1-20 abril** (con domiciliación: hasta **15 abril**).
  - T2 → **1-20 julio** (con domiciliación: hasta **15 julio**).
  - T3 → **1-20 octubre** (con domiciliación: hasta **15 octubre**).
  - T4 → **1-30 enero** del año siguiente (con domiciliación: hasta **25 enero**).
- **Errores reales**:
  1. T4 NO es alternativo ("o 30 enero"): es **siempre el 30 de enero**, no el 20.
  2. No menciona la domiciliación bancaria (5 días antes), que es relevante para 100% de usuarios SaaS.
  3. Si el día 20/30 cae en sábado/domingo/festivo, se traslada al siguiente hábil — sin mencionar.

### BUG-303-03 (ALTO) — `casilla_45` (total deducible) incompleta en el tool
- **Archivo**: `modelo_303_tool.py:319-322`.
- **Suma actual**: `cas_29 + cas_31 + cas_33 + cas_37 + cas_41`.
- **Suma correcta** (Modelo 303 vigente): `29 + 31 + 33 + 35 + 37 + 39 + 41 + 42 + 43 + 44`. El calculator interno lo hace bien (ver `modelo_303.py:289-301`).
- **Impacto**: usuarios con bienes de inversión importados, intracom. de inversión, REAGyP o regularización de prorrata van a infrarrepresentar el deducible y, en consecuencia, sobreestimar el resultado a ingresar.

### BUG-303-04 (ALTO) — Régimen Criterio de Caja no soportado (Art. 163 decies LIVA)
- **Cobertura**: ningún módulo trata el RECC. El RECC altera el devengo (a cobro) y el derecho a deducir (a pago). En Modelo 303 hay **casillas 74-76** (información adicional RECC) y **casillas 122-126** (RECC en cuotas). Ningún input las contempla.
- **Impacto en negocio**: Plan Autónomo (39 €/mes IVA incl.) y Creator (49 €/mes) declaran público objetivo **freelance < 2M €** — segmento donde RECC es elegible. Riesgo: cliente acogido a RECC obtiene un cálculo inválido sin advertencia.
- **Acción mínima**: bandera `regimen_caja: bool` que (1) bloquee el cálculo con un mensaje "no soportado", o (2) avise al usuario y derive a fiscalista.

### BUG-303-05 (ALTO) — Recargo de equivalencia: detector huérfano
- **Archivos**: `modelo_303.py:39-65` define `RE_RATES = {21: 5.2, 10: 1.4, 4: 0.5}` y `is_recargo_equivalencia()` (solo detecta `farmaceutico`). No se invocan desde el cálculo.
- **Norma**: Arts. 154-163 LIVA — los acogidos a RE **NO presentan Modelo 303 ordinario** (presentan 308 si hay devolución por intracom./ISP). El tool actual **calcula 303 igualmente** sin detectar y sin redirigir a 308.
- **Acción**: si `is_recargo_equivalencia()==True` → redirigir a `_render_308` y bloquear cálculo de 303.
- **Adicional**: tipos RE actuales son **5,2 / 1,4 / 0,5 / 1,75** (este último para tabaco/labores) y deben **incluirse explícitamente** en compras del minorista (no son ingresos del minorista). El detector solo cubre `farmaceutico` — ignora el resto del comercio minorista persona física.

### BUG-303-06 (MEDIO) — SII no contemplado (Art. 62.6 RIVA)
- **Norma**: obligados a SII (facturación >6.010.121,04 €, gran empresa, REDEME, grupo IVA, RECC) NO presentan Modelo 390 anual y deben llevar libros vía Sede AEAT. El plazo del 303 es el **30 día siguiente** al trimestre (no 20).
- **Cobertura actual**: ninguna detección, ningún aviso.
- **Acción**: bandera `sii: bool` y aviso de plazo distinto.

### BUG-303-07 (MEDIO) — Inversión Sujeto Pasivo (Art. 84 LIVA) ausente del tool
- **Archivo**: `modelo_303_tool.py` no expone parámetro alguno para casillas 13-14 (ISP). Sí lo hace el calculator (`base_inversion_sp`, `tipo_inversion_sp`).
- **Casuística**: ISP es muy frecuente en construcción, chatarra, productos electrónicos, gas natural, e importaciones de servicios B2B intracomunitarios. El usuario LLM no puede declararlo.

### BUG-303-08 (MEDIO) — Modificaciones de bases/cuotas (cas. 15-16) ausentes del tool
- Mismo problema: el tool no permite reflejar rectificaciones del Art. 80 LIVA (impagados, devoluciones, descuentos), pero el calculator sí.

### BUG-303-09 (MEDIO) — Drift entre `tool` y `calculator`
- Existen **dos** implementaciones del Modelo 303 con cobertura distinta. El LLM usa el `tool` (incompleto y con casillas mal numeradas). Los tests cubren el `calculator` (correcto). **Los tests no protegen el código que usan los usuarios reales**. Bug latente: cualquier fix en el calculator no se propaga al tool.
- **Acción recomendada**: refactor — el tool debe delegar en `Modelo303Calculator.calculate()` (igual que ya hace con `Modelo420Calculator` para Canarias).

### BUG-303-10 (MEDIO) — Intracomunitarias: solo un tipo aplicable
- Tanto el tool como el calculator aceptan **un único** `tipo_intracomunitarias`. En la práctica, un freelancer puede tener compras intracom. al 21% (servicios SaaS Google) y al 10% (libros, cultura) en el mismo trimestre. La casilla 10-12 admite mezcla.

### BUG-303-11 (BAJO) — Tipos transitorios 0% y 5% no soportados
- **Norma**: RDL 20/2022 + RDL 5/2023 + RDL 4/2024 — pan, harina, leche, queso, huevos, frutas, verduras, legumbres, cereales: **0% IVA** durante 2024 (subido al 2% en 2025 y 4% definitivo desde 1-oct-2025); aceites de oliva y semillas + pasta: **5%** transitorio (al 7,5% mid-2024 → 10% definitivo). Casilla 152-155 introducidas por Orden HFP/1124/2022.
- **Cobertura**: ninguna.
- **Impacto**: bajo en cliente típico (creator/freelance digital) pero **alto** en caso de uso "comercio minorista alimentación" (Recargo Equivalencia) — y aquí se cruza con BUG-303-05.

### BUG-303-12 (BAJO) — Variantes forales solo cosméticas
- `_FORAL_IVA_CONFIG` cambia el label ("Modelo 300", "F69"), `donde_presentar` y añade nota TicketBAI/BATUZ — pero el cálculo es idéntico al de territorio común. Esto **es correcto numéricamente** (los tipos son iguales) pero:
  - El **modelo 300 (Gipuzkoa)** tiene casillas distintas (no 78 ni 71).
  - El **F69 (Navarra)** usa casillas propias (`Tarifa de IVA Hacienda Foral`).
  - El **303 foral (Bizkaia/Araba)** comparte casillas con AEAT pero el envío es por BATUZ.
  - El PDF generado etiqueta como "Modelo 303 — AEAT" aunque sea Gipuzkoa.

### BUG-303-13 (BAJO) — Resultado "Sin actividad" pero >0 con base 0
- En el tool, si `base_21=0` y `iva_deducible_bienes_corrientes=0` el cálculo devuelve "Sin actividad", pero **un autónomo con resultado 0,00 sigue obligado a presentar 303**. Falta avisar de la obligación de presentación con cuota cero (declaración a no actividad / sin actividad — **casilla específica** "Sin actividad").

---

## 3. Casos prácticos (Manual IVA AEAT) — sample comparativo

> Recreados con valores estándar del Manual Práctico IVA. El cálculo se ejecuta mentalmente sobre `Modelo303Calculator.calculate()` (no sobre el tool, que tiene los bugs descritos).

| # | Caso | Inputs | Resultado calculator | Resultado AEAT esperado | OK/KO |
|---|---|---|---|---|---|
| 1 | Freelance T1 ingresos 10.000 €, sin gastos | base_21=10000 | `cas. 71 = 2.100,00` | 2.100,00 a ingresar | OK |
| 2 | Freelance T1 con compras 14.000 €, IVA soportado 2.940 € | base_21=10000, cuota_corr=2940 | `cas. 71 = -840,00` | 840 a compensar | OK |
| 3 | Restaurante T2: menús 21% (5.000), bebidas 10% (3.000), pan 4% (2.000) | base_21=5000, base_10=3000, base_4=2000 | devengado 1.430 | 1.430 (1.050 + 300 + 80) | OK |
| 4 | SaaS factura a Google Ireland (intracom inversa servicios) y compra IVA 800 € | base_21=10000, base_intra=2000@21, cuota_corr=800, cuota_intra=420 | dev=2.520, ded=1.220, res=1.300 | 1.300 a ingresar | OK |
| 5 | Constructora subcontrata (ISP Art. 84 cinco LIVA) base 8.000 | base_inversion_sp=8000 | dev=1.680, ded=0, res=1.680 | 1.680 a ingresar | OK calculator / **KO tool** (no acepta ISP) |
| 6 | Empresa con prorrata 70% — regularización 4T por bienes inversión | regularizacion_inversion=-300, quarter=4 | cas. 43 = -300, deducible se reduce | reducción correcta | OK calculator / **KO tool** (no soporta) |
| 7 | Farmacia (RE) — facturación 50.000 € | situacion_laboral=farmaceutico | tool calcula 303 y devuelve 10.500 a ingresar | **NO debe presentarse 303** — solo 308 si hay intracom./ISP | **KO en ambos** |

---

## 4. Simulador / fuentes de validación

- **AEAT no expone simulador público** del Modelo 303. Validación posible vía:
  1. Manual Práctico IVA (descarga PDF anual desde Sede AEAT).
  2. Servicio de ayuda Pre303 (área autenticada — no scrapable).
  3. Cálculos publicados por el Manual y por la Cámara de Comercio.
- **Recomendación**: incluir 7-10 casos del Manual IVA como **regression tests** del tool (no solo del calculator), versionados por año (`tests/test_modelo_303_manual_aeat_2025.py`).

---

## 5. Riesgos legales / reputacionales

| Riesgo | Probabilidad | Impacto |
|---|---|---|
| Usuario rellena 303 AEAT con casillas mal numeradas (BUG-01) | Alta | Alto — declaración rechazada o multa por error formal |
| Usuario RE (farmacia) presenta 303 indebidamente (BUG-05) | Media | Medio — sanción y obligación de rectificar con 308 |
| Usuario RECC con cálculo erróneo (BUG-04) | Media | Alto — divergencia entre devengado SII y autoliquidación |
| Plazo equivocado en T4 (BUG-02) | Alta | Alto — recargo Art. 27 LGT (1% mensual + 15% si > 1 año) |
| Discrepancia tool vs. calculator (BUG-09) | Cierta | Medio — mantenimiento, doble verdad |

**Disclaimer presente en PDF** (`modelo_pdf_generator.py:353`): suficiente para producto orientativo, pero **no exime** de la obligación de no inducir a error en cálculos básicos.

---

## 6. Acciones recomendadas (priorizadas)

### P0 — Antes del próximo cierre trimestral (T2 2026, plazo 20-jul-2026)
1. **BUG-303-01**: renombrar casillas en `modelo_303_tool.py` para alinear con AEAT (78 = compensación, 71 = resultado liquidación, 69 = previo, 77 = aduana, 68 = regularización 4T).
2. **BUG-303-02**: corregir texto de plazos en `modelo_303_tool.py:426` y `:583` con la tabla T1-T4 + domiciliación + festivos.
3. **BUG-303-03**: completar suma de `casilla_45` con casillas 35, 39, 42, 43, 44.
4. **BUG-303-09**: refactor — el tool delega en `Modelo303Calculator.calculate()`. Eliminar duplicidad.

### P1 — Próximo sprint
5. **BUG-303-04**: introducir flag `regimen_caja` en perfil fiscal y bloquear cálculo / advertir.
6. **BUG-303-05**: detector RE ampliado (CNAE 47.x, IAE 64x-65x) + redirección automática a Modelo 308.
7. **BUG-303-07** y **BUG-303-08**: añadir parámetros `base_inversion_sp`, `mod_bases`, `mod_cuotas` al tool.
8. **Tests del tool**: portar los 14 tests del calculator al tool (paridad).

### P2 — Roadmap Q3 2026
9. **BUG-303-06**: detector SII y aviso de plazos especiales.
10. **BUG-303-10**: permitir múltiples tipos de intracom. (lista de `{base, tipo}`).
11. **BUG-303-11**: tipos transitorios 0% y 5% (alimentación + aceites) hasta que la prórroga termine (probable 31-dic-2025 según RDL vigente).
12. **BUG-303-12**: PDF debe rotular correctamente cuando `variante_foral in {300, F69, 303 foral}`. El generador ya tiene `FORAL_NAMES` — usarlo.
13. **BUG-303-13**: detección "sin actividad" → mostrar aviso de obligación de presentar declaración cero.

### P3 — Producto
14. Casos prácticos versionados como tests anuales (Manual IVA AEAT).
15. Banner UI en `/calculadora` advirtiendo regímenes no cubiertos (RE, simplificado, REBU, REAGyP).

---

## 7. Resumen ejecutivo

- **Cobertura aritmética del régimen general**: correcta en `Modelo303Calculator` (la usada por tests).
- **Cobertura del LLM tool** (la usada por usuarios): **incompleta y con bugs de numeración de casillas**.
- **3 bugs críticos** (numeración casillas, plazos T4, suma deducible incompleta) afectan a **todos los usuarios** del segmento Autónomo y Creator.
- **Regímenes especiales** (Criterio Caja, RE, REAGyP, REBU, simplificado): no cubiertos. Solo el disclaimer textual los menciona, sin detección automática.
- **Variantes forales**: solo cosméticas (label + presentación), no afectan al cálculo, pero el PDF las rotula mal.
- **Tipos transitorios 0%/5%**: ausentes — bajo impacto en el cliente medio TaxIA pero crítico si se entra en alimentación / RE.
- **Test coverage**: 14 tests, todos sobre el calculator. **Cero tests sobre el tool de producción**.

Recomendación final: **freezar nuevas features de IVA** y abordar P0 antes del cierre T2 2026 (julio 2026). Documentar en `memory/bugfixes-2026-05.md` cuando se ejecute.
