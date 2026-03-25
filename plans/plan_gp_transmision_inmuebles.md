# Plan: GP Transmision Inmuebles (Venta de Propiedad)

> Fecha: 2026-03-25 (Sesion 21)
> Prioridad: HIGH (XSD gap #1)
> Esfuerzo estimado: L (~22h)
> Estado: PLANIFICADO

## Contexto

La venta de inmuebles genera ganancia patrimonial que tributa en base del ahorro (Art. 33+ LIRPF).
Actualmente el simulador NO cubre este caso. Casillas 0355-0370 del Modelo 100.

Reglas clave:
- **Art. 38 LIRPF**: Exencion por reinversion en vivienda habitual (plazo 2 anos)
- **DT 9a LIRPF**: Coeficientes de abatimiento para inmuebles adquiridos antes de 31/12/1994
- **Art. 35 LIRPF**: Valor de adquisicion = precio + gastos + mejoras - amortizaciones
- **Limite DT 9a**: Solo aplica si valor transmision total (todas las ventas desde 2015) <= 400.000 EUR

## Fase 1: Calculator backend (L)

### 1.1 Crear `backend/app/utils/calculators/capital_gains_property.py`
- Input: precio_venta, precio_adquisicion, fecha_adquisicion, fecha_venta, gastos_adquisicion, gastos_venta, mejoras, amortizaciones
- Calculo ganancia bruta: (venta + gastos_venta) - (adquisicion + gastos_adq + mejoras - amortizaciones)
- Aplicar coeficientes abatimiento DT 9a si fecha_adquisicion < 1995-01-01
- Coeficientes: 11.11% por ano de tenencia desde adquisicion hasta 19/01/2006 (max 100% reduccion)
- Limite: solo si valor_transmision_acumulado <= 400.000 EUR

### 1.2 Reinversion vivienda habitual (Art. 38)
- Si es vivienda habitual Y reinvierte en nueva vivienda habitual en plazo <= 24 meses
- Exencion proporcional: si reinvierte todo = 100% exento, si reinvierte parcial = proporcional
- Formula: ganancia_exenta = ganancia * (importe_reinvertido / precio_venta)

### 1.3 Coeficientes abatimiento (DT 9a)
- Solo inmuebles adquiridos antes 31/12/1994
- Reduccion: 11.11% por cada ano de tenencia que exceda de 2 (redondeando por exceso)
- Aplicable sobre ganancia generada hasta 20/01/2006
- Limite acumulado transmisiones desde 01/01/2015: 400.000 EUR

## Fase 2: Modelo de datos (S)

### 2.1 Campos `IRPFEstimateRequest`
```python
# Venta inmuebles
ventas_inmuebles: Optional[List[VentaInmueble]] = None

class VentaInmueble(BaseModel):
    tipo: str = "otro"  # "vivienda_habitual" | "otro"
    precio_venta: float = 0
    precio_adquisicion: float = 0
    fecha_adquisicion: Optional[str] = None  # YYYY-MM-DD
    fecha_venta: Optional[str] = None
    gastos_adquisicion: float = 0  # notaria, registro, ITP
    gastos_venta: float = 0  # plusvalia municipal, agencia
    mejoras: float = 0
    amortizaciones: float = 0  # si estuvo alquilado
    reinversion_vivienda_habitual: bool = False
    importe_reinversion: float = 0
```

## Fase 3: Integracion simulador (M)

- Invocar calculator desde `_simulate_comun()` y `_simulate_foral()`
- Resultado va a base del ahorro (GP derivadas de transmision = ahorro, Art. 46 LIRPF)
- Sumar a `base_imponible_ahorro` existente (junto con dividendos, intereses, cripto)
- Devolver desglose en response: ganancia_bruta, abatimiento, exencion_reinversion, ganancia_neta

## Fase 4: Frontend (M)

- Nuevo paso o seccion en TaxGuidePage: "Venta de inmuebles"
- Formulario: tipo inmueble, precios, fechas, gastos
- Condicional: si vivienda habitual, mostrar campos reinversion
- Resultado: mostrar ganancia neta + ahorro fiscal por reinversion/abatimiento

## Fase 5: Tests (M)

Tests minimos:
1. Venta sin exencion ni abatimiento (caso base)
2. Art. 38 reinversion total (ganancia 100% exenta)
3. Art. 38 reinversion parcial (proporcional)
4. DT 9a inmueble pre-1994 (reduccion por abatimiento)
5. DT 9a limite 400K EUR
6. Inmueble post-2006 (sin abatimiento)
7. Multiple ventas (agregacion)
8. Foral: tratamiento Pais Vasco/Navarra

## Dependencias

- No bloquea ni es bloqueado por las tareas de seeds CCAA
- Requiere que loss_compensation.py soporte GP de inmuebles (ya existe para ahorro)
- Territorios forales tienen reglas propias (fase posterior)

## Orden de ejecucion

1. Calculator + tests unitarios
2. Modelo de datos (request + response)
3. Integracion simulador
4. Frontend
5. Tests E2E
