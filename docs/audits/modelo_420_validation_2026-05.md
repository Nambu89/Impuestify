# Modelo 420 (IGIC trimestral — Canarias) — Validación 2026-05

**Auditor**: TaxIA research agent
**Fecha**: 2026-05-10
**Alcance**: `backend/app/utils/calculators/modelo_420.py` + `backend/app/territories/canarias/plugin.py` + `backend/tests/test_modelo_420.py`
**Comparado contra**: ATC (Agencia Tributaria Canaria), Ley 4/2012 (derogada parcialmente), Decreto Legislativo 1/2025 (texto refundido vigente desde 2025-10-21), Decreto 268/2011 (RIGC)

---

## Veredicto global

**ESTADO**: ❌ **CRITICAL — Tipos impositivos desactualizados, normativa derogada**

El cálculo aritmético es correcto y la estructura del modelo (devengado / deducible / resultado / complementaria) es coherente con el Modelo 420 oficial. Sin embargo:

1. La tabla de tipos hardcoded refleja un esquema **derogado en octubre 2025** por el Decreto Legislativo 1/2025.
2. Se incluyen dos tipos (**13,5 % y 35 %**) que **no aparecen en la normativa vigente** ni en la documentación pública de la ATC.
3. Falta el **tipo reducido del 5 %** (renombrado en el TR 2025) y el **tipo del 1 %** (energéticos, art. 33 bis).
4. Falta cualquier referencia al **REPEP** (Régimen Especial Pequeño Empresario y Profesional) — exención IGIC umbral 30 000 € que dispensa de presentar el 420.

Riesgo legal: cuotas calculadas al 13,5 % o 35 % son **no devengables** — la ATC rechazaría la autoliquidación o exigiría rectificación.

---

## 1 · Inventario código TaxIA

### 1.1 Tipos hardcoded (`modelo_420.py:46-52`)

| Constante | Valor | Comentario código |
|-----------|-------|-------------------|
| `TIPO_CERO` | 0 % | Alimentos básicos, medicamentos, agua, transporte público, VPO, sanidad, educación |
| `TIPO_REDUCIDO` | 3 % | Suministros industriales, químicos, textiles, minerales, madera, papel, caucho |
| `TIPO_GENERAL` | 7 % | Tipo residual |
| `TIPO_INCREMENTADO_1` | 9,5 % | Vehículos, embarcaciones, joyería |
| `TIPO_INCREMENTADO_2` | **13,5 %** | Bebidas alcohólicas, perfumería, piel, electrónica |
| `TIPO_ESPECIAL_1` | 20 % | Tabaco negro |
| `TIPO_ESPECIAL_2` | **35 %** | Tabaco rubio / Virginia |

### 1.2 Estructura del cálculo

- IGIC devengado por tipo + adquisiciones extracanarias (tipo variable) + inversión sujeto pasivo (tipo general 7 %) + modificaciones bases/cuotas.
- IGIC deducible: 6 conceptos de cuotas soportadas + rectificación + REAGP + regularización inversión + regularización prorrata.
- Resultado = devengado − deducible − cuotas a compensar anteriores + regularización anual (solo 4T).
- Complementaria: diferencia con resultado anterior.

### 1.3 Plugin territorio Canarias (`canarias/plugin.py`)

- `get_indirect_tax_model()` retorna `"420"` ✅
- `get_model_obligations()` añade `Modelo 420 — IGIC trimestral` con organismo "ATC" ✅
- Añade `Modelo 425` (resumen anual IGIC) para autónomos/sociedades con plazo `2026-01-30` ✅
- Fuerza `tiene_ops_intracomunitarias=False` (Modelo 349 NO aplica) ✅
- AIEM (Arbitrio sobre Importaciones y Entregas, Modelos 450/455) **mencionado en docstring pero no implementado** ⚠️

### 1.4 Tests (`test_modelo_420.py`)

15 tests, todos pasan. Cubren los 7 tipos, extracanarias, inversión SP, complementaria, regularización 4T, clamp negativo de compensación. **No hay tests negativos** (e.g. rechazar el 13,5 %/35 % derogados) ni tests del REPEP.

---

## 2 · Normativa vigente 2025-2026

### 2.1 Decreto Legislativo 1/2025 (BOC 2025-10-13, vigor 2025-10-21)

**Aprueba el texto refundido del IGIC + AIEM** y **deroga los artículos 50, 51, 52, 54, 55, 56, 57, 58, 59, 60 y 61 de la Ley 4/2012**. La referencia legal del docstring (`Ley 4/2012, art. 27`) está obsoleta — el art. 27 nunca reguló los tipos, y los arts. 51-61 que sí lo hacían están derogados.

### 2.2 Tipos IGIC vigentes 2025 (texto refundido + Decreto Ley 3/2026)

| Tipo | Valor | Concepto | Norma vigente |
|------|-------|----------|---------------|
| Tipo cero | 0 % | Alimentos básicos, agua, medicamentos, libros, energía eléctrica residencial (temporal) | Art. 33 TR |
| Tipo específico energéticos | **1 %** | Determinados productos energéticos (gas, etc.) | Art. 33 bis TR |
| Tipo superreducido | 3 % | Bienes y servicios del art. 34 (antes "tipo reducido") | Art. 34 TR |
| Tipo reducido | **5 %** | Renombrado: bienes y servicios del art. 35 | Art. 35 TR |
| Tipo general | 7 % | Residual | Art. 36 TR |
| Tipo incrementado | 9,5 % | Vehículos, embarcaciones, joyería | Arts. 39-41 TR |
| Tipo incrementado | 15 % | Perfumería, joyería de lujo, peletería, etc. | Art. 36 / 38 TR |
| Tipo especial | 20 % | Labores del tabaco rubio (sustituye al esquema 20/35) | Art. 37 TR |

**Confirmado por ATC, Iberley, Garrigues y Colegio Gestores Las Palmas: NO existen los tipos 13,5 % ni 35 % en 2025.**

### 2.3 REPEP (Régimen Especial Pequeño Empresario y Profesional)

- **Umbral**: volumen de operaciones año anterior ≤ **30 000 €** (sin prorrateo).
- Efecto: exención de IGIC en facturas + **dispensa de presentar Modelo 420 trimestral** + dispensa de libros IGIC.
- Única obligación formal: **Modelo 425 anual informativo**.
- Aplicable desde 2025 a personas físicas y jurídicas que cumplan el umbral.

### 2.4 Casillas y estructura Modelo 420 oficial

Estructura ATC actual (programa de ayuda + sede electrónica):
- **Régimen general**: bases por tipo (3, 5, 7, 9.5, 15, 20) + adquisiciones extracanarias + inversión SP + modificaciones.
- **Deducible**: corrientes interiores, importaciones, extracanarias, inversión, REAGP, rectificación, regularización inversión, regularización prorrata anual.
- **Resultado**: compensación trimestres anteriores, regularización anual prorrata (4T), resultado a ingresar / compensar / devolver.

Plazos: **20 abril (1T), 20 julio (2T), 20 octubre (3T), 30 enero (4T)**. El docstring no menciona plazos.

---

## 3 · Cross-check normativa vs código

| Concepto | Código TaxIA | Norma vigente 2025 | Estado |
|----------|--------------|--------------------|--------|
| Tipo 0 % | ✅ Implementado | Art. 33 TR | OK |
| Tipo 1 % energéticos | ❌ Falta | Art. 33 bis TR | **MISSING** |
| Tipo 3 % "reducido" | ✅ Pero etiquetado mal | Renombrado a "superreducido" | LABEL OBSOLETE |
| Tipo 5 % reducido | ❌ Falta | Art. 35 TR (nuevo nombre) | **MISSING** |
| Tipo 7 % general | ✅ | Art. 36 TR | OK |
| Tipo 9,5 % incrementado | ✅ | Arts. 39-41 TR | OK |
| Tipo 13,5 % | ❌ **Hardcoded inexistente** | NO existe | **CRITICAL** |
| Tipo 15 % incrementado | ❌ Falta | Art. 36/38 TR | **MISSING** |
| Tipo 20 % especial | ✅ | Art. 37 TR | OK |
| Tipo 35 % "tabaco rubio" | ❌ **Hardcoded inexistente** | Sustituido por 20 % | **CRITICAL** |
| REPEP exención < 30 000 € | ❌ No mencionado | Vigente, dispensa 420 | **MISSING** |
| Modelo 425 resumen anual | ✅ Plugin canarias | Vigente | OK |
| Modelo 349 NO aplica | ✅ Forzado en plugin | Correcto | OK |
| AIEM (Modelos 450/455) | ⚠️ Solo en docstring | Vigente para importadores | INCOMPLETE |
| Plazos trimestrales | ❌ Sin documentar | 20-abr/jul/oct + 30-ene | **MISSING** |
| Recargo equivalencia IGIC minorista | ❌ Falta | REM (régimen especial minoristas) | NOT IMPLEMENTED |
| ZEC (Zona Especial Canaria) | ❌ Falta | Régimen específico IS no IGIC, fuera scope 420 | OK (fuera scope) |
| Referencia legal `Ley 4/2012 art. 27` | ❌ Falsa | Arts. 51-61 derogados, art. 27 nunca reguló tipos | **WRONG REF** |

---

## 4 · Casos prácticos validados

Sin acceso a simulador público (la ATC no ofrece uno). Casos manuales:

### Caso A — Autónomo régimen general, ingresos 10 000 € al 7 %

- Devengado: 10 000 × 0,07 = 700 €
- Test `test_basic_general_7pct` ✅ — coincide con TaxIA.

### Caso B — Pequeño empresario factura 25 000 €/año (REPEP)

- **Norma**: NO debe presentar Modelo 420 (exento por franquicia). Solo Modelo 425.
- **TaxIA actual**: el plugin Canarias añade el Modelo 420 a las obligaciones sin verificar el umbral. ❌ FALSO POSITIVO de obligación.

### Caso C — Venta de perfumería / electrónica (anterior 13,5 %)

- **Norma vigente**: 15 % (incrementado, art. 36/38 TR).
- **TaxIA actual**: aplica 13,5 %. ❌ Cuota infravalorada en 1,5 puntos.

### Caso D — Venta de tabaco rubio

- **Norma vigente**: 20 % (tipo especial unificado).
- **TaxIA actual**: aplica 35 %. ❌ Cuota sobrevalorada en 15 puntos.

### Caso E — Suministro de gas residencial

- **Norma vigente**: 1 % (art. 33 bis TR).
- **TaxIA actual**: no contempla este tipo. ❌ El usuario lo metería al 7 % por defecto.

---

## 5 · Issues priorizados

### 🔴 P0 — Bloqueantes legales

1. **Eliminar tipos 13,5 % y 35 %** (`TIPO_INCREMENTADO_2`, `TIPO_ESPECIAL_2`). Sustituir por **15 %** y **20 %** con concepto unificado de "tabaco labores" si procede.
2. **Añadir tipo 5 %** (`TIPO_REDUCIDO` actual debe pasar a `TIPO_SUPERREDUCIDO` 3 % + nuevo `TIPO_REDUCIDO` 5 %).
3. **Actualizar referencia legal**: Decreto Legislativo 1/2025 (TR), no Ley 4/2012 art. 27.
4. **Documentar y aplicar REPEP**: si `volumen_operaciones_anterior <= 30000` → no obligación de Modelo 420, solo Modelo 425.

### 🟠 P1 — Cumplimiento parcial

5. Añadir **tipo 1 %** específico energéticos (art. 33 bis TR).
6. Añadir **plazos trimestrales** en docstring + plugin: 20-abr / 20-jul / 20-oct / 30-ene.
7. Implementar (al menos en docstring + tests) el **recargo de equivalencia IGIC** para minoristas.
8. Añadir tests negativos: rechazar bases con tipos 13,5 %/35 % o avisar deprecación.

### 🟡 P2 — Mejoras

9. AIEM (Modelos 450/455) — mencionar como obligación separada del 420 en `get_model_obligations()` cuando el perfil indique importaciones de mercancías.
10. Etiquetar el tipo 0 % con la lista actual del art. 33 TR (más extensa que la del docstring: incluye libros, prensa, energía residencial temporal).
11. Verificar que `compensacion_agricultura` (REAGP) refleja el porcentaje vigente (Decreto 268/2011 modificado).

---

## 6 · Recomendación de fix (resumen)

```python
# Reemplazar bloque de constantes
TIPO_CERO = 0.00
TIPO_ESPECIFICO_ENERGETICOS = 0.01    # Art. 33 bis TR (NUEVO)
TIPO_SUPERREDUCIDO = 0.03             # Art. 34 TR (renombrado)
TIPO_REDUCIDO = 0.05                  # Art. 35 TR (NUEVO)
TIPO_GENERAL = 0.07                   # Art. 36 TR
TIPO_INCREMENTADO_1 = 0.095           # Arts. 39-41 TR
TIPO_INCREMENTADO_2 = 0.15            # Art. 36/38 TR (CORREGIDO de 0.135)
TIPO_ESPECIAL = 0.20                  # Art. 37 TR (unifica anteriores 20/35)
# ELIMINAR: TIPO_ESPECIAL_2 = 0.35
```

Y añadir guard REPEP en `canarias/plugin.py:get_model_obligations()`:

```python
volumen = profile.get("volumen_operaciones_anterior", 0)
if volumen <= 30000:
    obligations = [o for o in obligations if o.modelo != "420"]
    # Mantener solo Modelo 425 anual informativo
```

---

## 7 · Fuentes

- [Decreto Legislativo 1/2025 — BOC](https://www.boe.es/buscar/doc.php?id=BOC-j-2025-90249)
- [ATC — Modelo 420 (sede oficial)](https://www3.gobiernodecanarias.org/tributos/atc/en/w/modelo-420)
- [ATC — Tipos IGIC para DIGIC (PDF)](https://www3.gobiernodecanarias.org/tributos/atc/documents/65729/215145/Tipos_IGIC_para_DIGIC.pdf)
- [ATC — Texto refundido IGIC y AIEM](https://www3.gobiernodecanarias.org/tributos/atc/en/w/nuevo-texto-refundido-ccaa-igic-y-aiem)
- [Garrigues — Modificaciones IGIC e IRPF 2025](https://www.garrigues.com/es_ES/noticia/canarias-introducen-modificaciones-igic-irpf-efectos-2025)
- [Garrigues — Texto refundido IGIC y AIEM](https://www.garrigues.com/es_ES/noticia/canarias-refunden-numerosas-normas-igic-aiem-decreto-legislativo-12025)
- [Iberley — Tipos impositivos IGIC](https://www.iberley.es/temas/tipos-impositivos-igic-canarias-22301)
- [GSM Abogados — REPEP exención 30 000 €](https://gsmabogados.com/derecho-tributario/exencion-igic-empresarios-con-ingresos-no-superiores-a-30-000e/)
- [DG Group — REPEP](https://dgcanariasgroup.com/2025/06/06/que-es-el-repep-y-cuando-se-puede-salir-de-el/)
- [BOE Ley 20/1991 (REF Canarias)](https://www.boe.es/buscar/act.php?id=BOE-A-1991-15036)

---

**Próximo paso**: abrir incidencia P0 en `agent-comms.md` para corregir tipos 13,5 % y 35 % antes de Q3 2026 (presentaciones 2T por usuarios canarios). Bloquear despliegue del cálculo IGIC en producción hasta el fix.
