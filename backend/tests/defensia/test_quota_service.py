"""Tests T2B-010 — DefensIA Quota Service (reserve-commit-release).

El patron reserve-commit-release evita el DoS intra-ventana (H8 del plan-checker):
un usuario del plan Particular (1 expediente/mes) no puede lanzar 5 analyze en
paralelo y que los 5 consuman cuota solo al completar. `reserve()` reclama la
plaza antes de iniciar el analisis; `commit()` la confirma al terminar;
`release()` la libera si el analisis falla.

Limites por plan (decisi de producto cerrada):
- Particular: 1 expediente/mes, +15 EUR por extra.
- Autonomo:   3 expedientes/mes, +12 EUR por extra.
- Creator:    5 expedientes/mes, +10 EUR por extra.

Los tests usan un fake async DB in-memory (con `asyncio.Lock` para el test de
concurrencia) para no hitear Turso real.
"""
from __future__ import annotations

import asyncio

import pytest

from app.services.defensia_quota_service import (
    LIMITES_POR_PLAN,
    PRECIO_EXTRA_POR_PLAN,
    DefensiaQuotaService,
    QuotaExcedida,
)


# --------------------------------------------------------------------------- #
# Fake async DB — mantiene estado compartido entre llamadas
# --------------------------------------------------------------------------- #


class FakeResult:
    """Mimics la interfaz de `QueryResult` de turso_client."""

    def __init__(self, rows):
        self.rows = rows


class FakeQuotaDB:
    """Fake async DB con estado in-memory y lock para tests concurrentes.

    El lock simula el comportamiento secuencial de SQLite (una unica
    transaccion a la vez) y permite testear correctamente la condicion
    de carrera del test H8.
    """

    def __init__(self, creados: int = 0, en_curso: int = 0):
        self._estado = {"expedientes_creados": creados, "en_curso": en_curso}
        self._lock = asyncio.Lock()
        self.calls: list[tuple[str, list]] = []  # log para asserts

    async def execute(self, sql: str, params: list | None = None):
        async with self._lock:
            self.calls.append((sql, list(params or [])))
            sql_upper = sql.upper()

            # SELECT creados / en_curso
            if sql_upper.startswith("SELECT"):
                return FakeResult([dict(self._estado)])

            # INSERT ... ON CONFLICT -> upsert que incrementa en_curso
            if "INSERT" in sql_upper and "ON CONFLICT" in sql_upper:
                self._estado["en_curso"] += 1
                return FakeResult([])

            # UPDATE commit: creados++, en_curso--
            if "UPDATE" in sql_upper and "expedientes_creados + 1" in sql.lower():
                self._estado["expedientes_creados"] += 1
                self._estado["en_curso"] = max(0, self._estado["en_curso"] - 1)
                return FakeResult([])

            # UPDATE release: solo en_curso--
            if "UPDATE" in sql_upper:
                self._estado["en_curso"] = max(0, self._estado["en_curso"] - 1)
                return FakeResult([])

            raise AssertionError(f"Unexpected SQL in fake DB: {sql}")


# --------------------------------------------------------------------------- #
# Constantes de plan
# --------------------------------------------------------------------------- #


def test_limites_por_plan_constantes():
    """Producto cerro: 1/3/5 para Particular/Autonomo/Creator."""
    assert LIMITES_POR_PLAN["particular"] == 1
    assert LIMITES_POR_PLAN["autonomo"] == 3
    assert LIMITES_POR_PLAN["creator"] == 5


def test_precios_extra_constantes():
    """Precios extra cerrados: 15/12/10 EUR por expediente adicional."""
    assert PRECIO_EXTRA_POR_PLAN["particular"] == 15.0
    assert PRECIO_EXTRA_POR_PLAN["autonomo"] == 12.0
    assert PRECIO_EXTRA_POR_PLAN["creator"] == 10.0


# --------------------------------------------------------------------------- #
# puede_consumir
# --------------------------------------------------------------------------- #


async def test_puede_consumir_plan_particular_vacio():
    db = FakeQuotaDB(creados=0, en_curso=0)
    svc = DefensiaQuotaService(db)
    assert await svc.puede_consumir("u1", "particular") is True


async def test_puede_consumir_plan_particular_lleno():
    """Particular con 1 creado ya ha consumido su cuota mensual."""
    db = FakeQuotaDB(creados=1, en_curso=0)
    svc = DefensiaQuotaService(db)
    assert await svc.puede_consumir("u1", "particular") is False


async def test_puede_consumir_plan_autonomo_parcial():
    """Autonomo con 2/3 usados -> True; con 3/3 -> False."""
    svc2 = DefensiaQuotaService(FakeQuotaDB(creados=2, en_curso=0))
    assert await svc2.puede_consumir("u1", "autonomo") is True

    svc3 = DefensiaQuotaService(FakeQuotaDB(creados=3, en_curso=0))
    assert await svc3.puede_consumir("u1", "autonomo") is False


async def test_puede_consumir_plan_desconocido():
    """Un plan que no existe devuelve False (fail-closed)."""
    svc = DefensiaQuotaService(FakeQuotaDB())
    assert await svc.puede_consumir("u1", "freeloader") is False


# --------------------------------------------------------------------------- #
# reserve
# --------------------------------------------------------------------------- #


async def test_reserve_exitosa():
    """Plan particular vacio -> reserve() devuelve un reserva_id y hace UPSERT."""
    db = FakeQuotaDB(creados=0, en_curso=0)
    svc = DefensiaQuotaService(db)

    reserva_id = await svc.reserve("u1", "particular")

    assert reserva_id.startswith("res_")
    assert db._estado["en_curso"] == 1
    # Al menos una llamada con INSERT ON CONFLICT
    upserts = [sql for sql, _ in db.calls if "INSERT" in sql.upper() and "ON CONFLICT" in sql.upper()]
    assert len(upserts) == 1


async def test_reserve_quota_excedida():
    """Plan particular con 1 creado -> reserve() lanza QuotaExcedida."""
    db = FakeQuotaDB(creados=1, en_curso=0)
    svc = DefensiaQuotaService(db)

    with pytest.raises(QuotaExcedida):
        await svc.reserve("u1", "particular")

    # Ninguna reserva concedida -> en_curso intacto
    assert db._estado["en_curso"] == 0


async def test_reserve_plan_desconocido_lanza_quota_excedida():
    """Plan inexistente -> no se reserva, se lanza QuotaExcedida."""
    db = FakeQuotaDB()
    svc = DefensiaQuotaService(db)
    with pytest.raises(QuotaExcedida):
        await svc.reserve("u1", "plan_inventado")


# --------------------------------------------------------------------------- #
# Concurrencia H8 — el test critico
# --------------------------------------------------------------------------- #


async def test_reserve_concurrencia_5_paralelas_plan_autonomo():
    """5 reservas paralelas para plan autonomo (limite 3) -> exactamente 3 ok + 2 fallos.

    Este es el test que hace fallar al DoS intra-ventana. Sin el patron
    reserve-commit-release, el contador `expedientes_creados` no se
    actualizaria hasta `commit()`, y las 5 reservas pasarian el check.
    """
    db = FakeQuotaDB(creados=0, en_curso=0)
    svc = DefensiaQuotaService(db)

    async def intentar():
        try:
            return await svc.reserve("u1", "autonomo")
        except QuotaExcedida:
            return None

    resultados = await asyncio.gather(*(intentar() for _ in range(5)))

    exitosas = [r for r in resultados if r is not None]
    fallidas = [r for r in resultados if r is None]

    assert len(exitosas) == 3, f"esperadas 3 reservas, obtenidas {len(exitosas)}"
    assert len(fallidas) == 2, f"esperados 2 rechazos, obtenidos {len(fallidas)}"
    # Todos los reserva_id son distintos (no hay colisiones)
    assert len(set(exitosas)) == 3
    assert db._estado["en_curso"] == 3
    assert db._estado["expedientes_creados"] == 0


# --------------------------------------------------------------------------- #
# commit
# --------------------------------------------------------------------------- #


async def test_commit_decrementa_en_curso_incrementa_creados():
    """commit() aplica: creados+=1, en_curso-=1."""
    db = FakeQuotaDB(creados=0, en_curso=1)
    svc = DefensiaQuotaService(db)

    await svc.commit("u1", "res_fake123")

    assert db._estado["expedientes_creados"] == 1
    assert db._estado["en_curso"] == 0


# --------------------------------------------------------------------------- #
# release
# --------------------------------------------------------------------------- #


async def test_release_decrementa_solo_en_curso():
    """release() solo libera la reserva, no incrementa creados."""
    db = FakeQuotaDB(creados=0, en_curso=2)
    svc = DefensiaQuotaService(db)

    await svc.release("u1", "res_fake123")

    assert db._estado["expedientes_creados"] == 0
    assert db._estado["en_curso"] == 1
