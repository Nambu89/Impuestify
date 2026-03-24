# Auditoria Deducciones Autonomicas — AEAT 2025 vs Impuestify

> Fecha: 2026-03-24 (Sesion 20)
> Fuente: AEAT Manual Renta 2025 Parte 2 - Deducciones Autonomicas
> Gap global: 260 de 349 deducciones faltan (74.5%)

## Resumen por CCAA (Regimen Comun)

| CCAA | AEAT 2025 | Tenemos | Faltan | Gap % |
|------|-----------|---------|--------|-------|
| Valencia | 40 | 6 | 34 | 85% |
| Castilla-La Mancha | 25 | 5 | 20 | 80% |
| Murcia | 28 | 6 | 22 | 79% |
| Asturias | 26 | 6 | 20 | 77% |
| Cantabria | 21 | 5 | 16 | 76% |
| Canarias | 28 | 7 | 21 | 75% |
| Baleares | 24 | 6 | 18 | 75% |
| La Rioja | 24 | 6 | 18 | 75% |
| Extremadura | 19 | 5 | 14 | 74% |
| Andalucia | 17 | 5 | 12 | 71% |
| Madrid | 23 | 7 | 16 | 70% |
| Galicia | 25 | 8 | 17 | 68% |
| Castilla y Leon | 17 | 6 | 11 | 65% |
| Cataluna | 13 | 5 | 8 | 62% |
| Aragon | 19 | 8 | 11 | 58% |
| **TOTAL** | **349** | **89** | **260** | **74.5%** |

## Forales + Ceuta/Melilla

| Territorio | Tenemos | Estado |
|------------|---------|--------|
| Araba | 14 | Cobertura razonable |
| Bizkaia | 11 | Faltan: edad, cuidado menores, eficiencia energetica |
| Gipuzkoa | 10 | Faltan: vehiculo electrico, eficiencia energetica |
| Navarra | 12 | Razonablemente completo |
| Ceuta | 1 (60% estatal) | CORRECTO — 0 autonomicas |
| Melilla | 1 (60% estatal) | CORRECTO — 0 autonomicas |

## Categorias mas comunes que faltan (transversales)

1. **Despoblacion/municipios rurales** — Madrid, Cantabria, CLM, CyL, Extremadura, Aragon, La Rioja
2. **ELA / Esclerosis Lateral Amiotrofica** — Asturias, Extremadura, Baleares, La Rioja, Galicia
3. **Enfermedad celiaca** — Andalucia, Asturias, La Rioja
4. **Practica deportiva** — Andalucia, La Rioja, Murcia, Valencia
5. **Vehiculos electricos** — Asturias, La Rioja, Murcia, Valencia
6. **Gastos veterinarios** — Andalucia, Murcia
7. **Viviendas vacias (arrendador)** — Madrid, Asturias, Cantabria, Extremadura, Galicia
8. **Inversion entidades nuevas** — Presente en ~12 CCAA, solo seeded en ~3

## Prioridad de implementacion (por poblacion + gap)

### Fase 1 — CRITICA
1. **Valencia** (5M hab, 34 faltan) — incluye DANA 2024
2. **Madrid** (6.7M hab, 16 faltan)
3. **Andalucia** (8.5M hab, 12 faltan)

### Fase 2 — ALTA
4. Canarias (2.2M, 21 faltan)
5. Galicia (2.7M, 17 faltan)
6. Murcia (1.5M, 22 faltan)
7. Castilla-La Mancha (2M, 20 faltan)

### Fase 3 — MEDIA
8-15. Resto de CCAA

## Archivos de seed relevantes

- `seed_deductions.py` — 16 estatales
- `seed_deductions_territorial.py` — ~54 (v1)
- `seed_deductions_territorial_v2.py` — ~62 (v2)
- `seed_deductions_xsd.py` — 339 casilla-level (no curadas)
- `seed_deductions_forales_v2.py` — 19 forales
