---
name: feedback_humanizer_wikipedia
description: Humanizer Wikipedia AI Cleanup — patrones a evitar al redactar copy visible al usuario en Impuestify. Aplicado en sesion 35.
type: feedback
---

# Humanizer Wikipedia AI Cleanup — reglas de estilo

**Why**: el copy de la app sonaba a IA y eso resta credibilidad. Alfredo Perez (CEO Ayudat) lo apunto indirectamente cuando pidio "contexto real". Aplicamos el humanizer basado en [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) en 40 archivos durante la sesion 35.

**How to apply**: cada vez que escribas copy visible al usuario (UI, emails, SEO meta, paginas legales), evita los patrones de abajo. No aplica al codigo, commits, system prompts del backend ni jerga tecnica fiscal.

## Patrones a eliminar

1. **Significance inflation**: "representa un compromiso con", "marca un hito", "pivotal moment", "evolving landscape", "deeply rooted".
2. **Copula avoidance**: "se erige como", "se posiciona como", "marca un X", "boasts a Y" → usa `es / tiene / hace`.
3. **Participios `-ing` superfluos** en castellano: "permitiendo identificar", "facilitando la redaccion", "garantizando la seguridad" → frases directas.
4. **Promotional language**: "vibrante", "completo", "integral", "revolucionario", "vanguardia", "vibrante", "renombrada", "incomparable", "exclusivo".
5. **Spam verbs**: "Descubre", "Explora", "Transforma", "Revoluciona", "Potencia", "Impulsa", "Desbloquea", "Eleva".
6. **Rule of three forzado**: "X, Y y Z" cuando en realidad son 2 o 4 cosas.
7. **Negative parallelism**: "No es solo X, es Y", "Mas que una herramienta".
8. **Synonym cycling / elegant variation**: misma idea repetida con palabras distintas.
9. **False ranges**: "from X to Y" cuando X y Y no estan en una escala real.
10. **Title case en headings**: "Datos Personales" → "Datos personales".
11. **Boldface mecanico** sobre frases enteras. Mantener `<strong>` solo en disclaimers legales obligatorios.
12. **Em-dashes retoricos**: "es —por decirlo asi— una herramienta" → coma o punto. Mantener em-dashes estructurales (codigo/descripcion en selects).
13. **Emojis decorativos** en headers / bullets. Iconos Lucide como UI element OK.
14. **Curly quotes** ("…") en lugar de straight ("…"). Usar straight.
15. **Vague attributions**: "Industry observers say", "Experts argue", "Several sources" sin citar nada concreto.
16. **Knowledge-cutoff disclaimers**: "as of [date]", "While specific details are limited".
17. **Sycophantic tone**: "Great question!", "You're absolutely right!", "I'd be happy to help".
18. **Filler phrases**: "In order to" → "Para", "At this point in time" → "Ahora", "Due to the fact that" → "Porque".
19. **Excessive hedging**: "could potentially possibly" → "puede".
20. **Generic positive conclusions**: "El futuro es brillante", "Comienza tu viaje hacia la excelencia".
21. **Collaborative artifacts**: "Aqui te dejo...", "Espero que esto ayude!", "Avisame si quieres mas detalles".
22. **Inline-header vertical lists**: items que empiezan con header en bold + colon.

## Como anadir alma (no solo limpiar)

- **Tener opiniones**. Reportar hechos sin tomar postura suena a Wikipedia.
- **Variar ritmo**: frase corta. Frase mas larga que se toma su tiempo. Mezclar.
- **Reconocer complejidad**: "Esto funciona bien para X pero no para Y" mejor que "Esto funciona bien".
- **Usar primera persona** cuando encaja. "Lo monte yo porque..." es mas humano que "Esta herramienta fue desarrollada porque...".
- **Dejar entrar imperfeccion**: tangentes, asides, frases medio formadas. Estructura perfecta = algoritmo.
- **Especificidad emocional**: en lugar de "esto es preocupante", "hay algo raro en que un agente este escribiendo a las 3 de la madrugada sin que nadie mire".

## Audit final obligatorio

Despues de redactar, hacerse las dos preguntas:
1. **"¿Que sigue sonando a IA aqui?"** — listar 3-4 tells si los hay.
2. **"Ahora hazlo no obvio"** — reescribir esas partes.

## Aplicabilidad

- **Aplica**: UI copy, emails transaccionales, paginas legales, SEO meta descriptions, README, manual usuario, mensajes a clientes (LinkedIn, email).
- **NO aplica**: codigo, comentarios tecnicos, commits, agent-comms, system prompts del backend (necesitan estructura), variables y nombres de campo, terminos legales obligatorios LSSI-CE/RGPD que tienen redaccion forzada.

## Casos donde el LLM falla mas en castellano

- Calques del ingles: "permitiendo" en lugar de "para que / y asi".
- "Garantizando", "asegurando", "ofreciendote": casi siempre superflu.
- "Mas alla de un simple X, es un Y": negative parallelism puro.
- "Una experiencia unica e inolvidable": frase muerta.
- "Optimizar tu experiencia": vacio.

## Referencia

[Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) — mantenido por WikiProject AI Cleanup.
