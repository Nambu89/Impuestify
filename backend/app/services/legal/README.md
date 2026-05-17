# Legal Norms Registry — Data-Driven Citation Verification

Sustituye los antiguos whitelists hardcoded de `citation_verifier.py`
(`_FUNDAMENTAL_LAWS_WHITELIST`, `_CANONICAL_ARTICLES_WHITELIST`) por un
registro **data-driven** cargado desde YAMLs en `backend/data/legal/`.

## Por qué

El antipatrón anterior tenía dos problemas serios:

1. **Mantenibilidad**: añadir una nueva ley (p. ej. tras reforma AEAT)
   requería modificar Python y redesplegar. Un fiscalista no-developer
   no podía mantenerlo.
2. **Escalabilidad**: la lista de artículos canónicos creció con cada
   plantilla nueva en el prompt. Hardcodear cientos de artículos era
   inviable.

La solución sigue el patrón **Repository + Protocol** de DDD: una
interfaz abstracta (`LegalNormsRegistry`) con una implementación
concreta (`YamlLegalNormsRegistry`). Migrar a SQL en el futuro requiere
únicamente añadir `SqlLegalNormsRegistry` — los callers (verifier,
prompt) no cambian.

## Estructura de archivos

```
backend/
├── data/legal/                         ← Fuente de verdad (versionada)
│   ├── norms.yaml                      ← Leyes vigentes
│   ├── articles.yaml                   ← Artículos canónicos citados
│   └── invoice_templates.yaml          ← Plantillas factura
├── app/services/legal/
│   ├── __init__.py                     ← API pública
│   ├── models.py                       ← Pydantic models (validación)
│   ├── loader.py                       ← YAML → models
│   ├── citation_parser.py              ← Parse "Art. 69.Dos.d LIVA" → tupla
│   ├── registry.py                     ← Protocol + Yaml impl + singleton
│   └── README.md                       ← Este archivo
└── tests/legal/
    ├── test_citation_parser.py         ← Tests del parser
    └── test_registry.py                ← Tests integridad YAML + lookup
```

## Añadir una nueva ley

1. Editar `backend/data/legal/norms.yaml`:
   ```yaml
   - sigla: NUEVA_SIGLA
     full_id: "Ley X/AAAA"
     name: "Nombre completo"
     norm_type: ley
     vigent_from: "AAAA-MM-DD"
     vigent_until: null
     aliases: ["alias1", "alias2"]
   ```
2. Si la ley tiene artículos que el system prompt va a citar
   habitualmente, añadirlos a `articles.yaml`.
3. Commit:
   `git commit -m "feat(legal): añadir Ley X/AAAA tras reforma AEAT"`
4. Tests de integridad correrán en CI (`test_yamls_load_without_errors`,
   `test_all_articles_reference_existing_norms`).
5. Deploy. El singleton se recarga en próximo start de la app.

## Añadir una nueva plantilla de factura

Editar `backend/data/legal/invoice_templates.yaml`:

```yaml
- key: nuevo_caso
  scenario: "Descripción humanizada"
  legal_basis: "Art. X LIVA"
  triggers:
    - "palabra clave 1"
    - "palabra clave 2"
  text: |
    Texto literal que se pondrá en la factura.
  notes: |
    Observaciones para el LLM sobre cuándo usar esta plantilla.
```

El system prompt de `tax_agent.py` renderiza automáticamente la sección
"Plantillas copy-paste para casos comunes" desde este YAML — sin tocar
código.

## Modificar un artículo (reforma)

Si AEAT modifica un artículo:

1. Localizar el artículo en `articles.yaml`.
2. Si la reforma cambia la numeración/letra, **NO eliminar** la entrada
   antigua: cerrarla con `vigent_until: "AAAA-MM-DD"` y añadir una
   nueva entrada con `vigent_from` y el contenido actualizado. Esto
   permite que el verifier siga aceptando citas de declaraciones
   anteriores a la reforma (importante para Renta de años pasados).

Ejemplo (Art. 7.p LIRPF derogado y sustituido):
```yaml
- law: LIRPF
  article: "7"
  subarticle: "p"
  topic: "Exención rentas trabajo realizado en extranjero (DEROGADO)"
  vigent_from: "2007-01-01"
  vigent_until: "2024-12-31"

- law: LIRPF
  article: "7"
  subarticle: "p"
  topic: "Exención rentas trabajo realizado en extranjero (nueva redacción)"
  vigent_from: "2025-01-01"
  vigent_until: null
```

## Tests y CI

Los tests en `tests/legal/` actúan como **gate de calidad** del YAML:

- `test_yamls_load_without_errors` — falla si la estructura YAML es
  inválida (campos missing, tipos incorrectos).
- `test_all_articles_reference_existing_norms` — falla si `articles.yaml`
  referencia una `law:` que no existe en `norms.yaml` (integridad
  referencial).
- `test_is_known_norm_*` — verifica que las leyes esperadas se
  reconocen correctamente.

Si AEAT publica una reforma y editar el YAML rompe estos tests, CI
bloquea el merge antes del deploy.

## Migración futura a SQL

Cuando el catálogo crezca (cientos de leyes históricas, miles de
artículos), migrar a Turso es trivial:

1. Crear tabla `legal_norms` y `legal_articles` en `init_schema()`.
2. Implementar `SqlLegalNormsRegistry(LegalNormsRegistry)` que
   consulte por SQL.
3. Cambiar el singleton en `get_legal_registry()` para devolver la
   nueva impl.
4. Migrar el YAML actual a la tabla con un script one-shot.

Los callers (`citation_verifier`, `tax_agent`) no cambian. Eso es lo
que conseguimos con el Protocol pattern.

## Decisiones de diseño documentadas

- **Vigencia explícita** (`vigent_from`/`vigent_until`): permite citar
  derecho histórico (declaraciones de años pasados) sin falsos
  positivos.
- **Fallback graceful**: si los YAMLs faltan o son inválidos, el
  registry devuelve un registry vacío. El verifier sigue funcionando
  (todo pasa a requerir RAG chunk evidence). Mejor que crashear en
  producción.
- **Singleton via `lru_cache`**: catálogo en memoria, lookups O(1)
  via dict. Reload manual con `reset_legal_registry()`.
- **Pydantic v2 para validación**: errores claros en startup vs
  fallar silenciosamente en tiempo de query.

## Referencias

- Inspiración: HalluGraph (arXiv 2025) — usamos lookup contra catálogo
  authoritative en lugar de grafos por simplicidad y latencia.
- Stanford 2025: "Legal RAG Hallucinations" — 17-33% hallucination rate
  en LexisNexis/Westlaw. La verificación contra catálogo authoritative
  es una de las mitigaciones recomendadas.

## Integración BOE API Datos Abiertos (sesión 42)

`backend/app/services/legal/boe_client.py` añade verificación de
vigencia y enriquecimiento de links contra la API oficial:
`https://www.boe.es/datosabiertos/api/`.

### Componentes

- **`BoeApiClient`**: HTTP client async con cache Turso 30 días
  (UPSERT race-safe). Devuelve `NormaBoeMetadata` con
  `estatus_derogacion`, `vigencia_agotada`, `url_html_consolidada`,
  `url_eli`, fechas. Accept solo `application/xml` (la API rechaza JSON).
- **`CitationEnricher`**: detecta citas en markdown (`Ley 37/1992`,
  `RD 1624/1992`, `Art. 69 LIVA`, …) y las sustituye por markdown links
  a la URL `boe.es/buscar/act.php?id={boe_id}` del registry. Citas no
  registradas se dejan intactas. Idempotente. No toca código existente
  ni bloques fenced.
- **Verifier**: opcional vía env `BOE_VERIFY_VIGENCIA=true`. Consulta
  la API por cada norma citada; si BOE confirma derogada, añade un
  footer específico `⚠ Según la API oficial del BOE, esta norma figura
  como derogada`. Default off para evitar latencia 1.5s primera vez.

### Tabla cache

```sql
CREATE TABLE boe_cache (
    boe_id TEXT PRIMARY KEY,
    metadata_json TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX idx_boe_cache_expires ON boe_cache(expires_at);
```

Escritura via UPSERT `ON CONFLICT(boe_id) DO UPDATE` — race-safe bajo
N workers Railway futuros.

### Mapping `boe_id` en `norms.yaml`

Cada norma del catálogo debe llevar `boe_id` (formato
`BOE-A-NNNN-NNNN`) verificable contra
`https://www.boe.es/buscar/act.php?id={boe_id}`. Test
`test_all_norms_have_boe_id` lo garantiza como gate CI.

### Cuándo añadir nuevas normas

1. Editar `norms.yaml` añadiendo entrada con `boe_id`.
2. Validar el `boe_id` con curl:
   ```
   curl -H "Accept: application/xml" \
     https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/{boe_id}
   ```
3. Confirmar `<status><code>200</code>` y `<titulo>` esperado.
4. Commit.

### Documentación oficial BOE

- Datos Abiertos: https://www.boe.es/datosabiertos/api/api.php
- FAQ Consolidada: https://www.boe.es/datosabiertos/faq/consolidada.php
- PDF API: https://www.boe.es/datosabiertos/documentos/APIconsolidada.pdf
