---
name: Crawler state — AEAT URLs rotas sesion 32
description: Estado del doc_crawler, watchlist actual, 18 URLs AEAT fallidas tras reorganizacion de sede, dependencias runtime
type: project
---

# Crawler state (actualizado 2026-04-13, sesion 32)

## Resumen

El `backend/scripts/doc_crawler/` (Scrapling-based) es la herramienta que monitoriza fuentes fiscales oficiales (AEAT, BOE, 23 CCAA/forales) y descarga PDFs/Excels cuando cambian. Ejecuta reintentos multi-ciclo y reporta en `docs/_crawler_report.md`.

## Stats actuales (sesion 32)

- **Total URLs monitorizadas**: 98
- **Por status**: active=67, future=9, deprecated=20, html_only=2
- **Territorios**: 23 (AEAT, Estatal, 17 CCAA, 4 forales + Ceuta/Melilla)
- **Documentos indexados en inventario**: 56
- **AEAT URLs**: 27 (de las cuales 18 HTTP 404 en sesion 32)

## Dependencias runtime (commit 718d5c8 en main)

Añadidas al `backend/requirements.txt` tras la sesion 32 porque no estaban pinneadas y cada sesion nueva tropezaba con los `ModuleNotFoundError`:

- `scrapling==0.4.6` (+ transitivas: cssselect, tld, w3lib, orjson>=3.11.8, lxml>=6.0.4)
- `curl_cffi==0.15.0`
- `playwright==1.58.0` (+ pyee)
- `browserforge==1.2.4` (+ apify_fingerprint_datapoints)

**Lateral upgrade importante**: scrapling fuerza `lxml 6.0.4` (proyecto estaba en 5.3.0). Los 58 tests de DefensIA Parte 1 siguen pasando con lxml 6.0.4 (verificado en sesion 32 antes del commit).

## Invocacion

```bash
# Stats
python -m backend.scripts.doc_crawler --stats

# Verificar URLs (sin descargar)
python -m backend.scripts.doc_crawler --territory AEAT --verify-urls

# Crawl completo con reintentos
python -m backend.scripts.doc_crawler --territory AEAT --check-new --max-cycles 3

# Dry run
python -m backend.scripts.doc_crawler --dry-run

# Listar pending
python -m backend.scripts.doc_crawler --pending
```

## 18 URLs fallidas en verify-urls (2026-04-13)

**IMPORTANTE — diagnostico corregido tras leer notas del watchlist:**

Mi diagnostico inicial decia "AEAT reorganizo sede electronica". **ERROR**. El watchlist ya tenia notas "TIPO A: Pendiente publicacion AEAT" en la mayoria de estos URLs antes de que yo los probara. El crawler los reintenta en cada ejecucion esperando que AEAT publique. Reclasificacion real:

### 🟡 ESPERADO — Pendiente publicacion AEAT (14 de 18)

Son docs que AEAT aun no ha publicado para la campana renta 2025/2026. El crawler los prueba en cada run. Cuando AEAT publique, se descargaran automaticamente. **NO REQUIEREN ACCION.**

- Retenciones: `Cuadro_tipos_retenciones_IRPF_2025.pdf`, `Cuadro_tipos_retenciones_IRPF_2026.pdf`, `Algoritmo_2025.pdf`, `Algoritmo_2026.pdf`
- Modelos: `Modelo303_IVA_Instrucciones_2025`, `Modelo390_IVA_Instrucciones_2025`, `Modelo190_Retenciones_Instrucciones`, `Modelo720_BienesExtranjero_Instrucciones`, `Modelo349_OperacionesIntracomunitarias_Instrucciones`, `Modelo036_AltaCensal_Instrucciones`
- Disenos de registro: `DR303_e2026.xlsx`, `DR390_e2025.xlsx`, `DR131_e2025.xlsx`
- BOE futuro: `Influencers/Estatal/Influencers-Resolucion_AEAT_PlanTributario_2026.pdf`

### 🔴 HISTORICO REMOVIDO (1 de 18)

- `AEAT/DisenosRegistro/DR130_e2019.xls` — nota: "Historico (2019). Buscar version actualizada 2025 o posterior"
- **Accion**: buscar el diseno de registro del Modelo 130 actual en `sede.agenciatributaria.gob.es`. Renombrar a `DR130_e2025.xlsx` o similar si existe

### ✅ SIN NOTA — RESUELTO en sesion 32 (3 de 18)

**Causa real**: AEAT cambio la nomenclatura de los manuales practicos en la campana renta 2025:
- `Tomo1` → `Parte1`, `Tomo2` → `Parte2`
- Parte2 movida a subdirectorio `IRPF-{year}-Deducciones-autonomicas/` (antes mismo subdir que Parte1)
- Manual_IVA paso de `Manual_IVA.pdf` (sin ano) a `Manual_IVA_{year}.pdf` (con ano versionado)

**Verificado empiricamente con curl + Scrapling en sesion 32**:

| # | URL nueva | Status | Tamano |
|---|---|---|---|
| 1 | `https://sede.agenciatributaria.gob.es/static_files/Sede/Biblioteca/Manual/Practicos/IRPF/IRPF-2025/ManualRenta2025Parte1_es_es.pdf` | HTTP 200 | 7.54 MB (publicado 2026-03-27) |
| 2 | `https://sede.agenciatributaria.gob.es/static_files/Sede/Biblioteca/Manual/Practicos/IRPF/IRPF-2025-Deducciones-autonomicas/ManualRenta2025Parte2_es_es.pdf` | HTTP 200 | 3.80 MB |
| 3 | `https://sede.agenciatributaria.gob.es/static_files/Sede/Biblioteca/Manual/Practicos/IVA/Manual_IVA_2025.pdf` | HTTP 200 | 6.30 MB |

**Fix commiteado en `main` (commit `100deb2`)**: actualizado `backend/scripts/doc_crawler/watchlist.py` con las 3 URLs correctas, pattern template `{BASE}/Manual/Practicos/Renta/IRPF/IRPF-{year}/ManualRenta{year}Parte1_es_es.pdf` para rotado anual, y `notes` con fecha + descripcion del cambio. `dest` renombrado de `_Tomo1.pdf` a `_Parte1.pdf` para reflejar nomenclatura AEAT.

**Manuales descargados localmente**:
- `docs/AEAT/IRPF/AEAT-Manual_Practico_IRPF_2025_Parte1.pdf` (7.54 MB)
- `docs/AEAT/IRPF/AEAT-Manual_Practico_IRPF_2025_Parte2.pdf` (3.80 MB)
- `docs/AEAT/IVA/AEAT-Manual_Practico_IVA_2025.pdf` (6.30 MB)

**Nota sobre Scrapling anti-bot**: el crawler de Scrapling devuelve HTTP 404 al intentar descargar (pero OK al verificar con `check_url_exists`). Probablemente detecta volumen de requests como bot. `curl` directo con User-Agent estandar descarga sin problema. **TODO en sesion dedicada**: investigar por que Scrapling falla en download para estos URLs concretos o anadir fallback a urllib/httpx para AEAT si los patrones del fetcher son rechazados.

**Duplicado detectado (no limpiado)**: `docs/AEAT/IVA/AEAT-Manual_IVA_2025.pdf` existia previamente (Mar 27, 6.3 MB). Mismo hash SHA256 que la version descargada hoy (`e4f800972e06466a`). Ocupa 6 MB duplicados pero no afecta nada funcional. Candidato a limpieza manual en futuro.

**Pendiente de ingesta RAG**: los 3 manuales nuevos (~17.6 MB) no han sido ingestados aun al Turso + Upstash Vector. Ejecutar `backend/scripts/reingest_aeat.py` en una proxima sesion dedicada (o invocar ingesta selectiva de los 3 ficheros).

## Blocked por robots.txt

- `AEAT/Farmacias/AEAT-Tarifas_IAE_Completas.pdf` — `https://www2.agenciatributaria.gob.es/ADUA/internet/es/aeat/dit/adu/adws/certificados/Tabla_de_epigrafes_IAE.pdf` (ya conocido, aceptado)

## Plan A — investigar los 3 manuales practicos (accion real, proxima sesion dedicada)

Scope muy reducido tras el mapa completo. Solo hay que investigar 3 URLs, no 18:

1. `WebFetch` a `https://sede.agenciatributaria.gob.es/Sede/biblioteca-virtual/manuales-practicos.html` (pagina indice)
2. Localizar los links al Manual Renta 2025 Tomos 1+2 y Manual IVA 2025
3. Si estan publicados: actualizar el watchlist con las URLs correctas
4. Si NO estan publicados: anadir nota "TIPO A: Pendiente publicacion AEAT" y considerar aceptable
5. Bonus: buscar version actualizada del DR130 (Historico 2019)
6. Re-ejecutar `--verify-urls` para confirmar

Estimado: 15-30 minutos, no 60.

## Docs verificados sin cambios en sesion 32 (8)

El crawler confirmo que los siguientes 8 docs siguen accesibles y sin actualizacion:

- (ver `docs/_crawler_log.json` para detalle)

## Nota

Ya existia previamente `_crawler_index.json`, `_crawler_report.md`, `_crawler_log.json` en `docs/`. El reporte de la sesion 32 se encuentra en `docs/_crawler_report.md` (sobreescrito cada ejecucion).
