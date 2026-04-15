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

NOTA sobre atomicidad: SQLite/libsql ejecutan las sentencias de forma
secuencial, pero el check de capacidad (SELECT) y la mutacion (INSERT/UPSERT)
son dos round-trips. Para cerrar la ventana de carrera usamos un `asyncio.Lock`
a nivel de servicio, que fuerza serializacion incluso cuando hay varios
`analyze` paralelos en el mismo worker. En multi-worker la serializacion
final la da el UNIQUE(user_id, ano_mes) de la tabla + el decremento
defensivo a cero en `release`/`commit`.

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
        # Lock de proceso: cierra la ventana de carrera entre SELECT y UPSERT
        # dentro del mismo worker. Para serializacion entre workers Railway
        # ejecuta con --workers 1, asi que este lock es suficiente.
        self._lock = asyncio.Lock()

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

        # Serializamos SELECT + UPSERT con el lock del servicio para
        # cerrar la ventana de carrera intra-worker.
        async with self._lock:
            estado = await self._get_estado(user_id)
            usado = estado["expedientes_creados"] + estado["en_curso"]
            if usado >= limite:
                raise QuotaExcedida(
                    f"Cuota mensual agotada para plan {plan_key}: "
                    f"{limite} expediente(s)/mes"
                )

            ano_mes = self._ano_mes_actual()
            await self.db.execute(
                "INSERT INTO defensia_cuotas_mensuales "
                "(user_id, ano_mes, expedientes_creados, en_curso) "
                "VALUES (?, ?, 0, 1) "
                "ON CONFLICT(user_id, ano_mes) DO UPDATE SET "
                "en_curso = en_curso + 1",
                [user_id, ano_mes],
            )

        reserva_id = f"res_{secrets.token_urlsafe(12)}"
        logger.info(
            "defensia quota reserve user=%s plan=%s reserva=%s",
            user_id,
            plan_key,
            reserva_id,
        )
        return reserva_id

    async def commit(self, user_id: str, reserva_id: str) -> None:
        """Confirma la reserva al terminar el analisis con exito.

        Efecto: `expedientes_creados += 1`, `en_curso -= 1`.
        """
        ano_mes = self._ano_mes_actual()
        async with self._lock:
            await self.db.execute(
                "UPDATE defensia_cuotas_mensuales "
                "SET expedientes_creados = expedientes_creados + 1, "
                "    en_curso = MAX(0, en_curso - 1) "
                "WHERE user_id = ? AND ano_mes = ?",
                [user_id, ano_mes],
            )
        logger.info(
            "defensia quota commit user=%s reserva=%s", user_id, reserva_id
        )

    async def release(self, user_id: str, reserva_id: str) -> None:
        """Libera la reserva sin confirmarla (analyze fallo antes de dictar).

        Efecto: `en_curso -= 1`. No toca `expedientes_creados`.
        """
        ano_mes = self._ano_mes_actual()
        async with self._lock:
            await self.db.execute(
                "UPDATE defensia_cuotas_mensuales "
                "SET en_curso = MAX(0, en_curso - 1) "
                "WHERE user_id = ? AND ano_mes = ?",
                [user_id, ano_mes],
            )
        logger.info(
            "defensia quota release user=%s reserva=%s", user_id, reserva_id
        )
