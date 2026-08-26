"""Leadbot — captador de leads para despliegues marca blanca (aislado).

Subsistema autónomo, **apagado por defecto**. Se activa poniendo
``LEADBOT_ENABLED=true``. Sustituye el típico botón flotante de WhatsApp por un
chatbot público que:

  1. Cualifica leads vía BANT-NATB (Need → Authority → Timing → Budget).
  2. Reserva citas en el Google Calendar del titular — degradación elegante si
     el OAuth aún no está concedido.
  3. Notifica por email (SMTP del dominio) al titular + confirma al lead.

No es código específico de una marca: es un captador reutilizable por cualquier
despliegue marca blanca. Por eso se gatea con su propia bandera
``LEADBOT_ENABLED`` y no con ``DEMO_MODE``, que además de encender esto relaja
capas de seguridad y no debe acabar mandando sobre módulos de producto.

Diseño AISLADO a propósito:
  - Config propia env-driven en ``leadbot/config.py`` (NO toca ``app/config.py``
    más allá de la bandera de activación).
  - Tablas propias con prefijo ``leadbot_``, creadas por ``leadbot/schema.py``
    sólo si la bandera está activa.
  - Router montado en ``main.py`` sólo si la bandera está activa (defensa en
    profundidad: con ella apagada ni siquiera se importa el módulo).

Plan de referencia: ``../IA-Melilla/plans/2026-05-26-leadbot-chatbot-captador.md``
"""
