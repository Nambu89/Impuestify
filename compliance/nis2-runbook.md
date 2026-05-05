# NIS2 / CRA Incident Response Runbook — Impuestify

> **Deadline efectivo: 11 septiembre 2026** (EU Cyber Resilience Act).
> A partir de esa fecha cualquier vulnerabilidad **explotada activamente**
> en producción debe reportarse a las autoridades en **24 horas** (early
> warning), y reporte completo en 72 horas.

## Cuándo aplicar este runbook

Se ACTIVA si:

1. Hay evidencia de un atacante explotando un fallo en producción
   (logs sospechosos, datos exfiltrados, comportamiento del LLM
   manipulado, webhooks de Stripe forzados, etc.).
2. Una vulnerabilidad CRITICAL/HIGH reportada por scanner (Trivy,
   pip-audit, npm audit) ha sido CONFIRMADA explotable.
3. Un investigador externo nos comunica una CVE 0-day antes de
   parchearla públicamente.

NO aplica si:

- La CVE detectada no es explotable en nuestra arquitectura.
- El bug fue descubierto internamente y mitigado antes de producción.

## Cadena de notificación (24h)

| Plazo | Acción | Quién |
|---|---|---|
| **0h** | Detección + activación runbook | Owner / on-call |
| **0h–2h** | Triage técnico, preserve logs, contención | Owner |
| **2h–8h** | Early warning a CCN-CERT (España) + INCIBE-CERT | Owner |
| **8h–24h** | Notificación detallada a ENISA / autoridad nacional | Owner |
| **24h–72h** | Informe técnico completo + medidas correctivas | Owner |
| **72h+** | Si datos personales afectados → notificar AEPD (RGPD Art. 33) en 72h desde detección | Owner |

## Contactos clave

| Entidad | Función | Contacto |
|---|---|---|
| **CCN-CERT** | Centro Criptológico Nacional, equipo de respuesta español | https://www.ccn-cert.cni.es/comunicacion-de-incidentes.html · `incidentes@ccn-cert.cni.es` · Tel: +34 91 372 50 25 |
| **INCIBE-CERT** | Para entidades privadas / ciudadanos | https://www.incibe-cert.es/contacto · Tel: 017 |
| **ENISA** | Coordinador EU | https://www.enisa.europa.eu/contact-us |
| **AEPD** | Si hay datos personales | https://sedeagpd.gob.es · Tel: 901 100 099 |
| **Stripe** | Si hay impacto en pagos | security@stripe.com |
| **Resend** | Si hay abuso desde nuestro dominio | abuse@resend.com |

## Acciones de contención inmediatas

Lista de comandos / runbooks por tipo de incidente:

### Acceso comprometido (cuenta usuario o owner)

```bash
# 1. Forzar logout global del usuario afectado
python -c "
import asyncio
from app.auth.refresh_token_store import RefreshTokenStore
async def go():
    s = RefreshTokenStore()
    n = await s.revoke_all_for_user('USER_ID_HERE', reason='incident_revoke')
    print(f'Revoked {n} sessions')
asyncio.run(go())
"

# 2. Si es el owner -> rotar JWT_SECRET_KEY en Railway -> redeploy
# 3. Si la password fue robada -> reset desde admin
```

### Token Stripe / webhook comprometido

```
1. Stripe Dashboard -> API keys -> Roll secret key
2. Railway -> backend service -> Variables -> update STRIPE_SECRET_KEY
3. Stripe Dashboard -> Webhooks -> destination -> Roll signing secret
4. Railway -> update STRIPE_WEBHOOK_SECRET
5. Verifica /subscription/webhook/health responde {configured: true}
```

### Vulnerabilidad de dependencia explotable (CVE)

```
1. Identificar paquete y versión vulnerable: pip-audit / npm audit
2. Bumpear a versión parcheada en requirements.txt o package.json
3. Si no hay parche -> aplicar workaround en código + comentar CVE
4. Push -> CI ejecuta security.yml -> Trivy debe pasar
5. Forzar redeploy en Railway
```

### Prompt injection / RAG poisoning detectado en producción

```
1. Identificar el doc o user que metió el payload
2. Si es doc del RAG -> borrar de Turso + Upstash Vector + reingerir limpio:
     UPDATE documents SET trust_level = 'quarantined' WHERE id = '...'
     # luego script de re-ingesta sin ese doc
3. Si es user -> revoke sessions + check si MFA activo
4. Añadir el patrón al test_security_pipeline regression suite
5. Verificar que Promptfoo nightly captura el caso en próximo run
```

## Plantilla de notificación CCN-CERT (24h early warning)

Asunto: `[Impuestify] Incidente de seguridad — early warning NIS2`

Cuerpo:

```
Entidad afectada: Impuestify (impuestify.com)
Sector: Servicio digital (asistente fiscal IA)
Fecha y hora detección (UTC): YYYY-MM-DD HH:MM
Fecha y hora estimada inicio del incidente (UTC): YYYY-MM-DD HH:MM

Resumen del incidente:
[2-3 frases describiendo qué ocurrió]

Tipo de incidente:
[ ] Acceso no autorizado
[ ] Exfiltración de datos
[ ] Indisponibilidad del servicio (DoS)
[ ] Ransomware / cifrado
[ ] Manipulación del LLM (prompt injection)
[ ] Vulnerabilidad explotada en dependencia
[ ] Otro: ___

Vector inicial conocido o sospechado:
[descripción]

Datos afectados:
[ ] Datos personales (RGPD aplica - notificar AEPD)
[ ] Datos fiscales de usuarios
[ ] Datos internos / código
[ ] Credenciales

Número estimado de usuarios impactados: ___
Número estimado de registros afectados: ___

Acciones de contención ya aplicadas:
[lista]

Acciones pendientes:
[lista]

Persona de contacto:
Nombre: Fernando Prada
Email: fernando.prada@proton.me
Teléfono: [opcional]

Indicadores de compromiso (IoCs):
[hashes, IPs, URLs sospechosas]

Logs y evidencia preservada:
[ubicación segura — ruta de archivos JSON exportados de Railway, dumps Turso, etc.]
```

## Post-incidente

1. **Post-mortem** en `memory/incidents/YYYY-MM-DD-<slug>.md` con:
   - Timeline detallado
   - Causa raíz
   - Cómo se detectó
   - Cómo se contuvo
   - Acciones preventivas a corto/largo plazo
2. **Update memoria** del proyecto + **CLAUDE.md** si aplica nueva regla.
3. **Update tests/red-team** con el patrón del ataque para regresión.
4. **Comunicación** a usuarios afectados (email + banner en `/chat`) si:
   - Datos personales comprometidos.
   - Acción del usuario requerida (cambiar password, etc.).

## Backups y preservación de evidencia

- Antes de eliminar logs maliciosos, copiar a almacenamiento separado.
- Railway logs: exportar JSON a `Errores Reportados/incidents/YYYY-MM-DD/`.
- Turso: snapshot manual con `turso db shell impuestify-prod ".dump" > snapshot-YYYY-MM-DD.sql`.
- Upstash: NO se exporta (es cache + rate limiter, perdible).
- Stripe Dashboard: tab Logs → export CSV.

## Test de la cadena de notificación

Recomendado: **simulacro anual** (1ª semana de septiembre, antes del aniversario CRA):
- Simular incidente ficticio
- Cronometrar las 3 fases (0-2h, 2-8h, 8-24h)
- Identificar bottlenecks
- Update este runbook
