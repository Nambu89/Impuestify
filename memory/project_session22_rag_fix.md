---
name: Session 22 RAG pipeline fix
description: Complete RAG pipeline audit and fix — 8 bugs (65-72), repo migration, system prompt rewrite with GPT-5/Claude techniques
type: project
---

Sesion 22 (2026-03-26): Auditoria y fix completo del pipeline RAG.

**Why:** El chatbot respondia "No he encontrado datos" a toda pregunta, incluso con 80K chunks en la DB.

**How to apply:** Estos fixes son permanentes. Para futuras sesiones, tener en cuenta:
- Semantic cache puede envenenar respuestas. Purgar con `railway run python backend/scripts/purge_semantic_cache.py`
- FTS5 necesita rebuild despues de cada ingesta: `python scripts/rebuild_fts5.py`
- Upstash Vector en produccion es `welcomed-katydid-49284-us1` (NO `obliging-haddock-89900-eu1` del .env local)
- System prompt del TaxAgent usa tecnicas de GPT-5/Claude/NotebookLM (etiquetas `<contexto_fiscal>`, nivel detalle 3/10, show don't tell)

## Bugs arreglados (8)

1. **Bug 65**: Repo GitHub roto → migrado a `Nambu89/Impuestify`
2. **Bug 66**: Territory mismatch (Pais Vasco vs Bizkaia) → mapping normalizacion
3. **Bug 67**: Logs invisibles en Railway → print(flush=True)
4. **Bug 68**: FTS5 siempre 0 → OR en vez de AND + rebuild 80K chunks
5. **Bug 69**: Semantic cache cacheaba respuesta mala → rechazo patrones stale
6. **Bug 70**: Indice Upstash diferente local vs Railway → usar `railway run`
7. **Bug 71**: "fuentes que has pegado" + verbosidad → system prompt rewrite
8. **Bug 72**: Frontend "(pag. 0)" → filtrar sources vacias

## Ingesta RAG

- 22 documentos nuevos ingesta dos (Azure Document Intelligence + OpenAI embeddings)
- 29 PDFs duplicados eliminados del disco (mismo hash SHA-256)
- Crawler: 8 docs nuevos (CDIs Irlanda/PaisesBajos/EEUU, ZEC Canarias, legislacion CCAA)
- 2 docs de cuarentena rescatados (Tarifas IAE 185 pag, Tributacion Autonomica 533 pag)
- FTS5 rebuild final: 84,279 chunks
- Estado final: 431 docs | 84,279 chunks | 78,446 embeddings

## Multi-agente

- **Superpowers v5.0.6** instalado (plugin oficial Anthropic)
- **3 skills GSD** adaptadas: fresh-context-execution, wave-execution, atomic-commits
- GSD completo NO instalado (conflicta con RuFlo)
- System prompts mejorados con tecnicas GPT-5/Claude/NotebookLM

## Calculadora de Retenciones IRPF 2026 (NEW)

- Algoritmo oficial AEAT 2026 (47 paginas PDF) implementado completo
- Backend: `withholding_rate.py` (28 tests PASS) + endpoint publico `POST /api/irpf/withholding`
- Frontend: `/calculadora-retenciones` (publica, sin auth, SEO lead magnet)
- Soporta: situacion familiar, descendientes/ascendientes, discapacidad, Ceuta/Melilla, hipoteca pre-2013, temporal
- Dark theme consistente con branding Impuestify
- Integrado en landing page + header nav (desktop + movil)

## Compartir Conversaciones (NEW)

- Backend: tabla `shared_conversations` + 3 endpoints (crear/ver/revocar share)
- Anonimizacion PII: DNI/NIE, telefonos, emails, IBAN, importes, nombres
- Frontend: ShareModal (toggle anonimizar + copiar link + compartir WhatsApp/Twitter/LinkedIn)
- SharedConversationPage: vista publica read-only con CTA registro
- Ruta: `/shared/:token` (publica, sin auth)

## Commits

2c06abe, 5aee9f8, 8b61be6, 2af4830, 1845e1c, f0c6e3e, 8adb0e0, 8f44c8a, 4d7f4ae, 9000c43, 2fb40ea, 01e653c, 083c2ae, 3c3a251, 293fc44, de87130, 541b24a
