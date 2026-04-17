"""DefensIA Quota Service (T2B-010).

Patron reserve-commit-release atomico para evitar el DoS intra-ventana
identificado en H8 del plan-checker: sin este patron, un usuario del plan
Particular (1 expediente/mes) podria lanzar 5 analyze en paralelo antes de
que el contador `expedientes_creados` se incrementase, y los 5 pasarian el
check de cuota.

Flujo:
    reserve(user, plan) -> reserva_id  (incrementa en_curso atomicamente)
        analyze...
    commit(user, reserva_id)           (creados++, en_curso--)
        o si falla:
    release(user, reserva_id)          (en_curso--)

Limites y precios cerrados por producto (spec Parte 2, seccion Monetizacion):
    Particular: 1 expediente/mes, +15 EUR por extra
    Autonomo:   3 expedientes/mes, +12 EUR por extra
    Creator:    5 expedientes/mes, +10 EUR por extra

Estado persistente en tabla `defensia_cuotas_mensuales` con columnas
`(user_id, ano_mes, expedientes_creados, en_curso)`. La columna `en_curso`
la anade la migracion `20260414_defensia_quota_encurso.sql`.

NOTA sobre atomicidad (Copilot review #9):

- **Intra-worker**: un `asyncio.Lock` cierra la ventana de carrera entre el
  check de capacidad y la reserva.
- **Multi-worker / multi-proceso**: ``reserve()`` usa un UPDATE condicional
  atomico en una sola sentencia (``WHERE ... AND (creados + en_curso) <
  limite``) que se apoya en ``rowcount`` para detectar capacidad agotada
  sin TOCTOU. El ``UNIQUE(user_id, ano_mes)`` de la tabla solo evita filas
  duplicadas; es el UPDATE condicional el que garantiza el limite real.

NOTA sobre idempotencia (Copilot review #8): ``reserva_id`` es un token
opaco registrado en memoria en `_reservas_activas`. ``commit()`` y
``release()`` solo mutan el contador si el token esta activo, y lo
desregistran en la misma operacion. Un segundo ``commit()`` o
``release()`` con el mismo token es un no-op. Limitacion: las reservas
no sobreviven a un reinicio del worker (caso raro, porque analyze dura
~60s). Una version Parte 3 puede persistir reservas en tabla para
supervivencia cross-restart — marcado como TODO en el plan.

Reservas huerfanas (reserva sin commit/release tras >10 min) se limpian
via cron fuera del scope v1 — marcado como TODO en el plan.
"""
from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# Limites mensuales por plan. Fail-closed para planes desconocidos.
LIMITES_POR_PLAN: dict[str, int] = {
    "particular": 1,
    "autonomo": 3,
    "creator": 5,
}

# Precio en EUR por expediente adicional una vez agotada la cuota mensual.
PRECIO_EXTRA_POR_PLAN: dict[str, float] = {
    "particular": 15.0,
    "autonomo": 12.0,
    "creator": 10.0,
}


class QuotaExcedida(RuntimeError):
    """Se lanza cuando el usuario intenta reservar mas alla de su cuota mensual.

    El router debe traducirlo a HTTP 402 "Payment Required" (cuota agotada),
    no a 429.
    """


class DefensiaQuotaService:
    """Reserve-commit-release para cuotas mensuales DefensIA."""

    def __init__(self, db_client):
        self.db = db_client
        # Lock de proceso: cierra la ventana de carrera intra-worker.
        # Cross-worker la atomicidad la da el UPDATE condicional en reserve().
        self._lock = asyncio.Lock()
        # Registro en memoria de reservas activas (Copilot review #8):
        # garantiza idempotencia de commit/release frente a llamadas
        # repetidas con el mismo token.
        #   {reserva_id: (user_id, ano_mes)}
        self._reservas_activas: dict[str, tuple[str, str]] = {}

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _ano_mes_actual(self) -> str:
        """Formato `YYYY-MM` en UTC (consistente con el resto del backend)."""
        now = datetime.now(timezone.utc)
        return f"{now.year:04d}-{now.month:02d}"

    async def _get_estado(self, user_id: str) -> dict:
        """Lee `(expedientes_creados, en_curso)` para el mes actual.

        Si la fila aun no existe, devuelve ceros sin insertarla — el INSERT
        se hace en `reserve()` via UPSERT.
        """
        ano_mes = self._ano_mes_actual()
        result = await self.db.execute(
            "SELECT expedientes_creados, en_curso "
            "FROM defensia_cuotas_mensuales "
            "WHERE user_id = ? AND ano_mes = ?",
            [user_id, ano_mes],
        )
        if result and getattr(result, "rows", None):
            row = result.rows[0]
            return {
                "expedientes_creados": row.get("expedientes_creados", 0) or 0,
                "en_curso": row.get("en_curso", 0) or 0,
            }
        return {"expedientes_creados": 0, "en_curso": 0}

    # ------------------------------------------------------------------ #
    # API publica
    # ------------------------------------------------------------------ #

    async def puede_consumir(self, user_id: str, plan: str) -> bool:
        """True si el usuario puede reservar una nueva plaza este mes."""
        limite = LIMITES_POR_PLAN.get((plan or "").lower())
        if limite is None:
            return False
        estado = await self._get_estado(user_id)
        usado = estado["expedientes_creados"] + estado["en_curso"]
        return usado < limite

    async def reserve(self, user_id: str, plan: str) -> str:
        """Reserva atomica de una plaza mensual.

        Usa un UPDATE condicional en una sola sentencia para evitar el
        TOCTOU cross-worker: solo incrementa ``en_curso`` si
        ``(expedientes_creados + en_curso) < limite``. El ``rowcount``
        del UPDATE distingue exito (1) de capacidad agotada (0).

        Returns:
            reserva_id (str): token opaco para usar en `commit`/`release`.

        Raises:
            QuotaExcedida: si el plan es desconocido o el usuario ha agotado
                su cuota mensual (incluyendo reservas en curso).
        """
        plan_key = (plan or "").lower()
        limite = LIMITES_POR_PLAN.get(plan_key)
        if limite is None:
            raise QuotaExcedida(f"Plan desconocido: {plan}")

        ano_mes = self._ano_mes_actual()

        async with self._lock:
            # Paso 1: asegura que la fila del mes existe (idempotente).
            # INSERT OR IGNORE es atomico por la restriccion UNIQUE de tabla.
            await self.db.execute(
                "INSERT OR IGNORE INTO defensia_cuotas_mensuales "
                "(user_id, ano_mes, expedientes_creados, en_curso) "
                "VALUES (?, ?, 0, 0)",
                [user_id, ano_mes],
            )
            # Paso 2: check-and-increment atomico cross-worker via WHERE.
            # Si la capacidad esta agotada, rowcount = 0 y abortamos.
            result = await self.db.execute(
                "UPDATE defensia_cuotas_mensuales "
                "SET en_curso = en_curso + 1 "
                "WHERE user_id = ? AND ano_mes = ? "
                "  AND (expedientes_creados + en_curso) < ?",
                [user_id, ano_mes, limite],
            )
            rowcount = getattr(result, "rowcount", None)
            if rowcount == 0:
                raise QuotaExcedida(
                    f"Cuota mensual agotada para plan {plan_key}: "
                    f"{limite} expediente(s)/mes"
                )

            reserva_id = f"res_{secrets.token_urlsafe(12)}"
            self._reservas_activas[reserva_id] = (user_id, ano_mes)

        logger.info(
            "defensia quota reserve user=%s plan=%s reserva=%s",
            user_id,
            plan_key,
            reserva_id,
        )
        return reserva_id

    async def commit(self, user_id: str, reserva_id: str) -> None:
        """Confirma la reserva al terminar el analisis con exito.

        Efecto: ``expedientes_creados += 1``, ``en_curso -= 1``.

        Idempotente: si ``reserva_id`` ya fue consumida (por un commit o
        release previo, o por reinicio del worker), es un no-op silencioso.

        Validacion user-binding (Copilot review round 2 #2): el ``user_id``
        argumento DEBE coincidir con el usuario que creo la reserva. Si no
        coincide, es un no-op sin consumir el token — no queremos que un
        usuario pueda consumir reservas de otro.
        """
        async with self._lock:
            entry = self._reservas_activas.get(reserva_id)
            if entry is None:
                logger.warning(
                    "defensia quota commit no-op: reserva desconocida user=%s reserva=%s",
                    user_id,
                    reserva_id,
                )
                return
            stored_user, ano_mes = entry
            if stored_user != user_id:
                logger.warning(
                    "defensia quota commit no-op: user mismatch esperado=%s recibido=%s reserva=%s",
                    stored_user,
                    user_id,
                    reserva_id,
                )
                return
            # Solo ahora consumimos el token (pop) y aplicamos el UPDATE
            # usando el user_id almacenado (que es el mismo).
            self._reservas_activas.pop(reserva_id, None)
            await self.db.execute(
                "UPDATE defensia_cuotas_mensuales "
                "SET expedientes_creados = expedientes_creados + 1, "
                "    en_curso = MAX(0, en_curso - 1) "
                "WHERE user_id = ? AND ano_mes = ?",
                [stored_user, ano_mes],
            )
        logger.info(
            "defensia quota commit user=%s reserva=%s", stored_user, reserva_id
        )

    async def release(self, user_id: str, reserva_id: str) -> None:
        """Libera la reserva sin confirmarla (analyze fallo antes de dictar).

        Efecto: ``en_curso -= 1``. No toca ``expedientes_creados``.

        Idempotente + user-binding identico a ``commit()``. Un release con
        ``user_id`` distinto del original es un no-op sin consumir el token.
        """
        async with self._lock:
            entry = self._reservas_activas.get(reserva_id)
            if entry is None:
                logger.warning(
                    "defensia quota release no-op: reserva desconocida user=%s reserva=%s",
                    user_id,
                    reserva_id,
                )
                return
            stored_user, ano_mes = entry
            if stored_user != user_id:
                logger.warning(
                    "defensia quota release no-op: user mismatch esperado=%s recibido=%s reserva=%s",
                    stored_user,
                    user_id,
                    reserva_id,
                )
                return
            self._reservas_activas.pop(reserva_id, None)
            await self.db.execute(
                "UPDATE defensia_cuotas_mensuales "
                "SET en_curso = MAX(0, en_curso - 1) "
                "WHERE user_id = ? AND ano_mes = ?",
                [stored_user, ano_mes],
            )
        logger.info(
            "defensia quota release user=%s reserva=%s", stored_user, reserva_id
        )
