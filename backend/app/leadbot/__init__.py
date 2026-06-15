"""Leadbot — captador de leads (demo IA Melilla, aislado).

Subsistema autónomo que vive SOLO en la rama ``demo/fiscal-ia-melilla`` y se
activa únicamente cuando ``settings.DEMO_MODE`` es ``True``. Reemplaza el botón
flotante de WhatsApp por un chatbot público que:

  1. Cualifica leads vía BANT-NATB (Need → Authority → Timing → Budget).
  2. Reserva citas en el Google Calendar del titular (Joaquín) — degradación
     elegante si OAuth aún no está concedido.
  3. Notifica por email (SMTP del dominio) al titular + confirma al lead.

Diseño AISLADO a propósito (petición del usuario: "no mezclar con Impuestify"):
  - Config propia env-driven en ``leadbot/config.py`` (NO toca ``app/config.py``).
  - Tablas propias creadas por ``leadbot/schema.py`` sólo en DEMO_MODE.
  - Router montado en ``main.py`` sólo si DEMO_MODE (defensa en profundidad: no
    puede exponerse en el despliegue principal de Impuestify).

Plan de referencia: ``../IA-Melilla/plans/2026-05-26-leadbot-chatbot-captador.md``
"""
