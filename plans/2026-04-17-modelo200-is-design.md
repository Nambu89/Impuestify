# Modelo 200 — Simulador Impuesto sobre Sociedades (IS)

> **Fecha**: 2026-04-17
> **Estado**: Aprobado por el usuario
> **Rama**: se creara `claude/modelo-200-v1` desde `main`
> **Sesion origen**: 34 (brainstorming)

---

## 1. Objetivo

Implementar un simulador del Impuesto sobre Sociedades (Modelo 200) con dos modos de entrada:

1. **Modo manual** (sin auth, publico) — el usuario introduce datos manualmente. Lead magnet SEO en `/modelo-200`.
2. **Modo workspace** (con auth) — el formulario se pre-rellena automaticamente desde el PyG/Balance del workspace del usuario. Experiencia premium.

Adicionalmente, incluir el calculo de pagos fraccionados (Modelo 202) como derivada del Modelo 200.

**Fuera de scope v1**: plan de suscripcion "Empresa", perfil fiscal de empresa, presentacion ante AEAT, regimenes especiales (cooperativas, asociaciones, entidades parcialmente exentas), ingesta RAG del Manual de Sociedades (se hara aparte).

---

## 2. Entidades cubiertas

| Tipo entidad | Descripcion | Tipo IS |
|---|---|---|
| SL / SLP | Sociedad Limitada (comun y profesional) | General 25% o pyme 23% |
| SA | Sociedad Anonima | General 25% |
| Nueva creacion | SL/SA en primeros 2 ejercicios con BI positiva | 15% (primeros 50k) |

---

## 3. Territorios y escalas

### 3.1 Regimen comun

| Tramo | Base hasta | Tipo |
|---|---|---|
| General | ilimitado | 25% |
| Pyme (fact. <1M EUR) | primeros 50.000 EUR | 23% |
| Pyme (fact. <1M EUR) | resto | 25% |
| Nueva creacion | primeros 50.000 EUR | 15% |
| Nueva creacion | resto | 20% |

Fuente: Art. 29 LIS (Ley 27/2014) actualizado por Ley 7/2024.

### 3.2 Territorios forales

| Territorio | Tipo general | Tipo pyme (primeros 50k) | Nueva creacion (primeros 50k) | Norma |
|---|---|---|---|---|
| Alava | 24% | 20% | 19% | NF 37/2013 |
| Bizkaia | 24% | 20% | 19% | NF 11/2013 |
| Gipuzkoa | 24% | 20% | 19% | NF 2/2014 |
| Navarra | 28% | 23% | 15% (3 ejercicios) | LF 26/2016 |

**Concierto/Convenio**: si cifra de negocio <10M EUR, tributa 100% en el territorio foral. Si >=10M, reparto proporcional entre territorios segun volumen de operaciones. En v1 asumimos 100% foral (pymes).

### 3.3 Regimenes especiales territoriales

| Territorio | Mecanismo | Detalle |
|---|---|---|
| Canarias ZEC | Tipo reducido 4% | Requiere inscripcion ZEC + actividad Art. 43 Ley 19/1994 |
| Canarias RIC | Reduccion base imponible | Reserva para Inversiones en Canarias (dotacion sobre beneficio no distribuido) |
| Ceuta y Melilla | Bonificacion 50% cuota | Art. 33.6 LIS, sobre rentas obtenidas en el territorio |

---

## 4. Motor de calculo (`is_simulator.py`)

### 4.1 Arquitectura

Clase `ISSimulator` con sub-calculadoras, mismo patron que `irpf_simulator.py`:

```
ISSimulator
  ├── BaseImponibleCalculator  — resultado contable +/- ajustes
  ├── BINCompensator           — bases imponibles negativas (Art. 26 LIS)
  ├── TipoGravamenClassifier   — selecciona escala por territorio + tipo entidad
  ├── CuotaCalculator          — aplica escala, calcula cuota integra
  ├── DeduccionesISCalculator   — I+D/IT, reserva capitalizacion, donativos, empleo
  ├── BonificacionCalculator   — Ceuta/Melilla 50%, Canarias
  └── PagosFraccionadosCalc    — Modelo 202 (Art. 40.2 y 40.3 LIS)
```

### 4.2 Flujo de calculo

```
1. Resultado contable (desde PyG o manual)
2. + Ajustes extracontables positivos (gastos no deducibles Art. 15 LIS)
3. - Ajustes extracontables negativos (libertad amortizacion, etc.)
4. = Base imponible previa
5. - Compensacion BINs (limite 70% si fact >20M, 100% si <1M)
6. = Base imponible
7. x Tipo gravamen (segun territorio + tipo entidad + tramo)
8. = Cuota integra
9. - Deducciones (I+D 25%, IT 12%, reserva capitalizacion 10%, donativos, empleo)
10. - Bonificaciones (Ceuta/Melilla 50%, Canarias)
11. = Cuota liquida
12. - Retenciones e ingresos a cuenta
13. - Pagos fraccionados realizados
14. = Resultado (a ingresar / a devolver)
```

### 4.3 Ajustes extracontables (gastos no deducibles Art. 15 LIS)

Gastos tipicos no deducibles que el simulador debe listar como opciones:

- Contabilizacion del propio IS
- Multas, sanciones y recargos
- Perdidas de juego
- Donativos y liberalidades (salvo los del Art. 68.3)
- Gastos con personas o entidades residentes en paraisos fiscales
- Retribucion FFPP (dividendos)
- Amortizacion no deducible (exceso sobre tablas Art. 12 LIS)
- Deterioro participaciones (Art. 13.2 LIS)

### 4.4 Deducciones IS

| Deduccion | Porcentaje | Limite | Base legal |
|---|---|---|---|
| I+D (investigacion) | 25% (42% si >media 2 anos) | 25-50% cuota integra | Art. 35.1 LIS |
| IT (innovacion tecnologica) | 12% | 25-50% cuota integra | Art. 35.2 LIS |
| Reserva capitalizacion | 10% incremento FFPP | 10% BI | Art. 25 LIS |
| Donativos mecenazgo | 35% (40% si recurrente) | 10% BI | Ley 49/2002 |
| Creacion empleo discapacitados | 9.000/12.000 EUR/persona | sin limite | Art. 38 LIS |
| Canarias RIC | reduccion BI | 90% beneficio no distribuido | Art. 27 Ley 19/1994 |

**Forales**: Bizkaia/Gipuzkoa tienen I+D al 30% y limites distintos. Navarra tiene reserva especial. Se parametrizan en `IS_DEDUCTIONS_BY_TERRITORY`.

### 4.5 Pagos fraccionados (Modelo 202)

Dos modalidades:

**Art. 40.2 LIS (por defecto)**:
- 18% de la cuota integra del ultimo Modelo 200 presentado
- Menos deducciones, bonificaciones y retenciones del ejercicio anterior
- 3 pagos: abril (1-20), octubre (1-20), diciembre (1-20)

**Art. 40.3 LIS (opcional, grandes empresas obligatorio si fact >6M)**:
- Base imponible del periodo x 17% (o 24% si fact >10M)
- Sobre los 3/9/11 primeros meses del ejercicio

En v1 implementamos ambas modalidades. El usuario elige cual aplicar.

---

## 5. Request/Response

### 5.1 POST `/api/irpf/is-estimate`

**Request**:
```python
class ISEstimateRequest(BaseModel):
    # Modo workspace (opcional)
    workspace_id: str | None = None
    ejercicio: int = 2025

    # Datos entidad
    tipo_entidad: Literal["sl", "slp", "sa", "nueva_creacion"] = "sl"
    territorio: str = "Madrid"
    facturacion_anual: float = 0
    ejercicios_con_bi_positiva: int = 10  # para nueva creacion

    # Resultado contable (override manual o auto desde workspace)
    ingresos_explotacion: float | None = None
    gastos_explotacion: float | None = None
    resultado_contable: float | None = None  # si se da, ignora ingresos-gastos
    amortizacion_contable: float = 0
    amortizacion_fiscal: float | None = None  # si difiere de contable

    # Ajustes
    gastos_no_deducibles: float = 0
    ajustes_negativos: float = 0

    # BINs
    bins_pendientes: float = 0

    # Deducciones
    gasto_id: float = 0         # investigacion
    gasto_it: float = 0         # innovacion tecnologica
    incremento_ffpp: float = 0  # para reserva capitalizacion
    donativos: float = 0
    empleados_discapacidad_33: int = 0   # 9.000 EUR/persona
    empleados_discapacidad_65: int = 0   # 12.000 EUR/persona
    dotacion_ric: float = 0     # Canarias RIC

    # Bonificaciones
    es_zec: bool = False
    rentas_ceuta_melilla: float = 0

    # Retenciones y pagos previos
    retenciones_ingresos_cuenta: float = 0
    pagos_fraccionados_realizados: float = 0
```

**Response**:
```python
class ISEstimateResponse(BaseModel):
    # Desglose
    resultado_contable: float
    ajustes_positivos: float
    ajustes_negativos: float
    base_imponible_previa: float
    compensacion_bins: float
    base_imponible: float

    # Cuota
    tipo_gravamen_aplicado: str  # "25%", "23%/25% (pyme)", "15%/20% (nueva creacion)"
    cuota_integra: float
    deducciones_total: float
    deducciones_detalle: dict[str, float]  # {"id": 1000, "it": 500, ...}
    bonificaciones_total: float
    cuota_liquida: float

    # Resultado
    retenciones: float
    pagos_fraccionados: float
    resultado_liquidacion: float
    tipo: Literal["a_ingresar", "a_devolver"]
    tipo_efectivo: float  # porcentaje real sobre resultado contable

    # Pagos fraccionados 202
    pago_fraccionado_202_art40_2: float | None  # modalidad cuota
    pago_fraccionado_202_art40_3: float | None  # modalidad base

    # Metadata
    territorio: str
    regimen: str  # "comun", "foral_bizkaia", "navarra", "zec", "ceuta_melilla"
    ejercicio: int
    prefilled_from_workspace: bool

    # Disclaimer
    disclaimer: str
```

### 5.2 GET `/api/workspaces/{id}/is-prefill?ejercicio=2025`

Devuelve los campos del formulario pre-rellenados desde el PyG/Balance:

```python
class ISPrefillResponse(BaseModel):
    workspace_name: str
    ejercicio: int
    ingresos_explotacion: float
    gastos_explotacion: float
    resultado_contable: float
    amortizacion_contable: float
    num_facturas: int
    periodo_cubierto: str  # "enero-diciembre 2025"
    cuentas_desglose: list[dict]  # [{cuenta: "600", nombre: "Compras", importe: 1234}, ...]
```

Requiere auth + ownership del workspace.

### 5.3 POST `/api/irpf/is-202`

Calculo standalone de pagos fraccionados:

```python
class IS202Request(BaseModel):
    modalidad: Literal["art40_2", "art40_3"]
    # Art 40.2
    cuota_integra_ultimo_200: float = 0
    deducciones_bonificaciones_ultimo: float = 0
    retenciones_ultimo: float = 0
    # Art 40.3
    base_imponible_periodo: float = 0
    facturacion_anual: float = 0
    territorio: str = "Madrid"
```

---

## 6. Frontend

### 6.1 Pagina `/modelo-200` — Wizard 4 pasos

**Paso 1: Datos de la entidad**
- Tipo entidad: SL / SLP / SA / Nueva creacion (select)
- Territorio fiscal: dropdown existente (ccaa + forales + Ceuta/Melilla + Canarias ZEC)
- Facturacion anual aproximada: input numerico
- Ejercicio: select (2024/2025)
- Selector workspace: dropdown opcional ("Cargar datos desde workspace" o "Introducir manualmente"). Muestra nombre + num facturas de cada workspace del usuario.

**Paso 2: Resultado contable**
- Sin workspace: inputs manuales (ingresos explotacion, gastos explotacion, resultado contable)
- Con workspace: tabla pre-rellenada desde PyG con desglose por cuenta PGC, resultado contable calculado automaticamente. El usuario puede editar/ajustar cifras.
- Campo amortizacion contable + fiscal si difieren

**Paso 3: Ajustes y deducciones**
- Gastos no deducibles: checkboxes con los tipicos (Art. 15 LIS) + campo libre
- BINs pendientes de ejercicios anteriores
- Deducciones: I+D, IT, reserva capitalizacion, donativos, empleo discapacitados
- Bonificaciones: Ceuta/Melilla (importe rentas en territorio), Canarias RIC/ZEC

**Paso 4: Resultado**
- Desglose completo del calculo (paso a paso visual)
- Cuota liquida + tipo efectivo
- Resultado: a ingresar / a devolver (verde/rojo como en guia fiscal)
- Estimacion pagos fraccionados 202 (ambas modalidades)
- Boton "Descargar PDF borrador"
- LiveEstimatorBar sticky con cuota en tiempo real

### 6.2 Pagina `/modelo-202` — Formulario simple

- Selector modalidad (Art. 40.2 o 40.3)
- Inputs segun modalidad
- Resultado: 3 importes trimestrales (abril, octubre, diciembre)
- Link desde resultado del Modelo 200

### 6.3 Navegacion

- Entrada en Header.tsx: dropdown "Herramientas" (junto a DefensIA) o en "Calculadoras"
- Ruta publica (sin auth) para el modo manual
- Con auth: acceso a selector workspace
- SEO: useSEO con schema JSON-LD `WebApplication` + `FAQPage`

---

## 7. Generador PDF Modelo 200

Mismo patron que `modelo_pdf_generator.py`. Genera un borrador PDF con las casillas principales:

- Casilla 552: Base imponible
- Casilla 558: Tipo gravamen
- Casilla 560: Cuota integra
- Casilla 582: Deducciones
- Casilla 592: Cuota liquida
- Casilla 595: Retenciones
- Casilla 599: Resultado liquidacion
- Casilla 600: A ingresar / Casilla 601: A devolver

No es el formulario oficial AEAT (que usa XSD propio), sino un resumen visual con los importes calculados, util para el asesor del usuario.

---

## 8. Integracion con TaxAgent

No se crea un agente nuevo. Se anade el tool `simulate_is` al `TaxAgent` existente:

```python
SIMULATE_IS_TOOL = {
    "name": "simulate_is",
    "description": "Calcula el Impuesto sobre Sociedades (Modelo 200) para una empresa",
    "parameters": { ... }  # subset del ISEstimateRequest
}
```

System prompt del TaxAgent actualizado con reglas:
- Si el usuario menciona "mi empresa", "SL", "sociedades", "modelo 200", "impuesto de sociedades" → usar `simulate_is`
- Si tiene workspace con facturas de empresa → sugerir pre-rellenar desde ahi

---

## 9. Tests

### 9.1 Backend (~45 tests)

**Simulador IS (25 tests)**:
- Caso basico SL regimen comun 25%
- Pyme <1M facturacion (23%/25% tramos)
- Nueva creacion (15%/20% tramos)
- Cada territorio foral (Alava, Bizkaia, Gipuzkoa, Navarra)
- ZEC Canarias 4%
- Ceuta/Melilla bonificacion 50%
- BINs con limite 70% (>20M) y sin limite (<1M)
- Deducciones I+D, IT, reserva capitalizacion, donativos, empleo
- Combinacion deducciones + bonificaciones
- Resultado negativo (a devolver)

**Pagos fraccionados 202 (8 tests)**:
- Art. 40.2 basico
- Art. 40.3 basico
- Cada territorio foral
- Caso con retenciones previas

**Prefill workspace (6 tests)**:
- Workspace con PyG completo
- Workspace sin datos suficientes
- Workspace de otro usuario (403)
- Ejercicio sin facturas

**Endpoint (6 tests)**:
- Request valido modo manual
- Request valido modo workspace
- Validacion campos
- Territorio invalido

### 9.2 Frontend (~12 tests Vitest)

- Wizard renderiza 4 pasos
- Selector workspace muestra opciones
- Pre-fill rellena campos
- Resultado muestra desglose
- LiveEstimatorBar actualiza en cambio
- Modo sin auth (manual) funciona

---

## 10. Decisiones explicitas

1. **Sin plan "Empresa"** en v1 — el simulador es una herramienta publica/premium, no requiere plan nuevo.
2. **Sin ingesta RAG** en v1 — se hara cuando el usuario lo pida. El Manual de Sociedades existe en `docs/AEAT/Sociedades/`.
3. **Endpoint bajo `/api/irpf/`** — consistente con los demas estimadores. El prefix es legacy pero funcional.
4. **Sin presentacion AEAT** — solo calculo + PDF borrador informativo.
5. **Disclaimer obligatorio** en toda superficie (resultado, PDF, chat) — "Este calculo es orientativo y no sustituye asesoramiento profesional".
6. **Concierto/Convenio simplificado** — en v1 asumimos 100% tributacion foral para pymes <10M. El reparto proporcional multi-territorio queda fuera.
