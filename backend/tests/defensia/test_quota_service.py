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

    def __init__(self, rows, rowcount: int = 0):
        self.rows = rows
        self.rowcount = rowcount


class FakeQuotaDB:
    """Fake async DB con estado in-memory y lock para tests concurrentes.

    El lock simula el comportamiento secuencial de SQLite (una unica
    transaccion a la vez) y permite testear correctamente la condicion
    de carrera del test H8. Expone ``rowcount`` en el FakeResult para
    soportar el patron check-and-increment atomico del UPDATE condicional
    que usa ``reserve()`` (Copilot review #9).
    """

    def __init__(self, creados: int = 0, en_curso: int = 0):
        self._estado = {"expedientes_creados": creados, "en_curso": en_curso}
        self._row_exists = True  # despues del primer INSERT OR IGNORE
        self._lock = asyncio.Lock()
        self.calls: list[tuple[str, list]] = []  # log para asserts

    async def execute(self, sql: str, params: list | None = None):
        async with self._lock:
            self.calls.append((sql, list(params or [])))
            sql_upper = sql.upper()
            sql_lower = sql.lower()

            # SELECT creados / en_curso
            if sql_upper.startswith("SELECT"):
                return FakeResult([dict(self._estado)], rowcount=0)

            # INSERT OR IGNORE -> crea la fila si no existe (no-op si existe)
            if "INSERT OR IGNORE" in sql_upper:
                # la fila ya existe con los valores iniciales del fixture
                return FakeResult([], rowcount=1)

            # INSERT ... ON CONFLICT -> upsert legacy (test old-path)
            if "INSERT" in sql_upper and "ON CONFLICT" in sql_upper:
                self._estado["en_curso"] += 1
                return FakeResult([], rowcount=1)

            # UPDATE condicional: check-and-increment atomico (nuevo reserve)
            if (
                "UPDATE" in sql_upper
                and "en_curso = en_curso + 1" in sql_lower
                and "(expedientes_creados + en_curso) <" in sql_lower
            ):
                # Leer el limite del parametro (ultimo)
                limite = (params or [None, None, None])[-1]
                capacidad = self._estado["expedientes_creados"] + self._estado["en_curso"]
                if capacidad < limite:
                    self._estado["en_curso"] += 1
                    return FakeResult([], rowcount=1)
                return FakeResult([], rowcount=0)  # capacidad agotada

            # UPDATE commit: creados++, en_curso--
            if "UPDATE" in sql_upper and "expedientes_creados + 1" in sql_lower:
                self._estado["expedientes_creados"] += 1
                self._estado["en_curso"] = max(0, self._estado["en_curso"] - 1)
                return FakeResult([], rowcount=1)

            # UPDATE release: solo en_curso--
            if "UPDATE" in sql_upper:
                self._estado["en_curso"] = max(0, self._estado["en_curso"] - 1)
                return FakeResult([], rowcount=1)

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
    """Plan particular vacio -> reserve() devuelve un reserva_id y usa el
    patron INSERT OR IGNORE + UPDATE condicional atomico."""
    db = FakeQuotaDB(creados=0, en_curso=0)
    svc = DefensiaQuotaService(db)

    reserva_id = await svc.reserve("u1", "particular")

    assert reserva_id.startswith("res_")
    assert db._estado["en_curso"] == 1
    # Al menos una llamada con INSERT OR IGNORE + un UPDATE condicional
    inserts = [sql for sql, _ in db.calls if "INSERT OR IGNORE" in sql.upper()]
    atomic_updates = [
        sql
        for sql, _ in db.calls
        if "UPDATE" in sql.upper() and "(expedientes_creados + en_curso) <" in sql.lower()
    ]
    assert len(inserts) == 1
    assert len(atomic_updates) == 1


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
    """commit() aplica: creados+=1, en_curso-=1. La reserva debe venir
    de una llamada previa a reserve() — un reserva_id fabricado a mano no
    es valido (Copilot review #8 - idempotencia por token)."""
    db = FakeQuotaDB(creados=0, en_curso=0)
    svc = DefensiaQuotaService(db)

    reserva_id = await svc.reserve("u1", "particular")
    assert db._estado["en_curso"] == 1

    await svc.commit("u1", reserva_id)

    assert db._estado["expedientes_creados"] == 1
    assert db._estado["en_curso"] == 0


async def test_commit_doble_no_duplica_contadores():
    """Copilot review #8: un segundo commit con el mismo reserva_id debe ser
    un no-op. Antes, doble commit incrementaba creados dos veces."""
    db = FakeQuotaDB(creados=0, en_curso=0)
    svc = DefensiaQuotaService(db)

    reserva_id = await svc.reserve("u1", "autonomo")
    await svc.commit("u1", reserva_id)
    await svc.commit("u1", reserva_id)  # doble commit

    assert db._estado["expedientes_creados"] == 1
    assert db._estado["en_curso"] == 0


# --------------------------------------------------------------------------- #
# release
# --------------------------------------------------------------------------- #


async def test_release_decrementa_solo_en_curso():
    """release() solo libera la reserva, no incrementa creados."""
    db = FakeQuotaDB(creados=0, en_curso=0)
    svc = DefensiaQuotaService(db)

    r1 = await svc.reserve("u1", "autonomo")
    _r2 = await svc.reserve("u1", "autonomo")
    assert db._estado["en_curso"] == 2

    await svc.release("u1", r1)

    assert db._estado["expedientes_creados"] == 0
    assert db._estado["en_curso"] == 1


async def test_release_doble_no_duplica():
    """Copilot #8: segundo release con mismo token debe ser no-op."""
    db = FakeQuotaDB(creados=0, en_curso=0)
    svc = DefensiaQuotaService(db)

    reserva_id = await svc.reserve("u1", "autonomo")
    await svc.release("u1", reserva_id)
    await svc.release("u1", reserva_id)  # doble release

    assert db._estado["en_curso"] == 0


async def test_commit_tras_release_no_mueve_contador():
    """Copilot #8: un commit posterior a release con el mismo token es no-op."""
    db = FakeQuotaDB(creados=0, en_curso=0)
    svc = DefensiaQuotaService(db)

    reserva_id = await svc.reserve("u1", "particular")
    await svc.release("u1", reserva_id)
    await svc.commit("u1", reserva_id)  # ya consumida en release

    assert db._estado["expedientes_creados"] == 0
    assert db._estado["en_curso"] == 0
