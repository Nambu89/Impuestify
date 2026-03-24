# Auditoria XSD Modelo 100 vs IRPFSimulator — Gaps Identificados

> Fecha: 2026-03-24 (Sesion 20)
> Metodologia: Cruce de 2064 casillas XSD AEAT contra codebase simulador

## HIGH Priority (7 items)

1. **GP transmision inmuebles** (casillas 0355-0370) — Venta de vivienda/propiedad. Incluye reinversion vivienda habitual (Art. 38), coeficientes abatimiento pre-2006 (DT 9a). Esfuerzo: L
2. **Pension compensatoria ex-conyuge** (casilla 0475) — Art. 55 LIRPF. Reduce base general. Esfuerzo: S
3. **Anualidades por alimentos a hijos** (casillas 0476-0478) — Art. 64 LIRPF. Tributacion separada a escala. Esfuerzo: M
4. **Doble imposicion internacional** (casilla 0588) — Art. 80 LIRPF. Deduccion impuestos pagados extranjero. Esfuerzo: M
5. **Discapacidad descendientes MPYF** (casilla 0519) — Art. 60.2 LIRPF. 3000-9000 EUR minimo adicional. Esfuerzo: S
6. **Discapacidad ascendientes MPYF** (casilla 0520) — Art. 60.3 LIRPF. Mismos importes. Esfuerzo: S
7. **Declaracion conjunta — 2o declarante** — Actualmente solo aplica reduccion pero ignora ingresos del conyuge. Esfuerzo: L

## MEDIUM Priority (14 items)

1. Rendimientos irregulares >2 anos (Art. 18.2): reduccion 30% sobre max 300K EUR
2. Cobros/rescates planes pensiones como rend. trabajo (Art. 17.2.a.3)
3. Seguros vida/invalidez RCM (Art. 25.3)
4. RCM base general (Art. 25.4): arrendamiento negocios, PI, asistencia tecnica
5. Imputacion derechos imagen (Art. 92) — relevante para creadores
6. GP general: subvenciones, indemnizaciones, premios concursos
7. Mutualidades obligatorias funcionarios (Art. 51.7)
8. Reduccion rendimiento irregular RCM >2 anos (Art. 26.2)
9. Reduccion rendimiento irregular alquiler >2 anos (Art. 23.3)
10. Rendimiento negativo alquiler (no truncar a 0 por inmueble)
11. Deduccion descendiente discapacidad Art. 81bis (separada de MPYF, 1200 EUR)
12. Deduccion ascendiente discapacidad Art. 81bis (1200 EUR)
13. Deduccion familia monoparental 2+ hijos Art. 81bis (1200 EUR)
14. Empresas nueva creacion (Art. 68.1): 50% deduccion max 100K EUR base

## LOW Priority (12 items)

- Retribuciones especie por sub-tipo
- EO modulos detalle completo
- GP otros elementos patrimoniales
- Transparencia fiscal internacional (Art. 91)
- AIE/UTE (Art. 89-90)
- IIC extranjeras paraisos fiscales (Art. 95bis)
- Proteccion patrimonio historico
- Ceuta no residentes
- Retenciones premios
- Intereses demora contribuyente
- Perdida beneficio DT por incumplimiento
- Regularizacion Art. 103bis

## Orden Recomendado de Implementacion

1. Pension compensatoria + anualidades alimentos (S+M, HIGH)
2. Discapacidad descendientes/ascendientes MPYF (S, HIGH)
3. Doble imposicion internacional (M, HIGH)
4. GP transmision inmuebles (L, HIGH)
5. Art. 81bis deducciones discapacidad familiar (S, MEDIUM)
6. Rendimientos irregulares >2 anos (S, MEDIUM)
7. 2o declarante conjunta (L, HIGH)
