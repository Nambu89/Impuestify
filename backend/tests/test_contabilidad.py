"""
Tests for ContabilidadService — double-entry journal entries and accounting books.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import asdict

from app.services.contabilidad_service import ContabilidadService, AsientoLine


# ---------------------------------------------------------------------------
# Test 1: Factura recibida (gasto) — 3 lines: gasto + IVA soportado + proveedor
# ---------------------------------------------------------------------------
class TestGenerateAsientoFacturaRecibida:
    def test_factura_recibida_compra(self):
        """Factura recibida de compra (cuenta 60x) -> proveedor 400."""
        lines = ContabilidadService.generate_asiento_lines(
            tipo="recibida",
            cuenta_pgc_code="600",
            cuenta_pgc_nombre="Compras de mercaderias",
            base_imponible=1000.0,
            cuota_iva=210.0,
            total=1210.0,
            retencion_irpf=0.0,
            concepto="Compra material oficina",
        )

        assert len(lines) == 3

        # Debe: gasto
        assert lines[0].cuenta_code == "600"
        assert lines[0].debe == 1000.0
        assert lines[0].haber == 0.0

        # Debe: IVA soportado
        assert lines[1].cuenta_code == "472"
        assert lines[1].debe == 210.0
        assert lines[1].haber == 0.0

        # Haber: proveedor (cuenta empieza por 60 -> 400)
        assert lines[2].cuenta_code == "400"
        assert lines[2].haber == 1210.0
        assert lines[2].debe == 0.0

    def test_factura_recibida_servicio(self):
        """Factura recibida de servicio (cuenta 62x) -> acreedor 410."""
        lines = ContabilidadService.generate_asiento_lines(
            tipo="recibida",
            cuenta_pgc_code="629",
            cuenta_pgc_nombre="Otros servicios",
            base_imponible=500.0,
            cuota_iva=105.0,
            total=605.0,
            retencion_irpf=0.0,
            concepto="Servicio limpieza",
        )

        assert len(lines) == 3
        # Acreedor (no empieza por 60)
        assert lines[2].cuenta_code == "410"
        assert lines[2].haber == 605.0

    def test_factura_recibida_sin_iva(self):
        """Factura recibida exenta de IVA -> solo 2 lines."""
        lines = ContabilidadService.generate_asiento_lines(
            tipo="recibida",
            cuenta_pgc_code="600",
            cuenta_pgc_nombre="Compras de mercaderias",
            base_imponible=1000.0,
            cuota_iva=0.0,
            total=1000.0,
            retencion_irpf=0.0,
            concepto="Compra exenta IVA",
        )

        assert len(lines) == 2
        # No line for 472
        codes = [l.cuenta_code for l in lines]
        assert "472" not in codes


# ---------------------------------------------------------------------------
# Test 2: Factura emitida (ingreso) — 3 lines: cliente + ingreso + IVA repercutido
# ---------------------------------------------------------------------------
class TestGenerateAsientoFacturaEmitida:
    def test_factura_emitida_basica(self):
        """Factura emitida standard -> cliente 430 + ingreso + IVA 477."""
        lines = ContabilidadService.generate_asiento_lines(
            tipo="emitida",
            cuenta_pgc_code="705",
            cuenta_pgc_nombre="Prestaciones de servicios",
            base_imponible=2000.0,
            cuota_iva=420.0,
            total=2420.0,
            retencion_irpf=0.0,
            concepto="Factura consultoria",
        )

        assert len(lines) == 3

        # Debe: cliente
        assert lines[0].cuenta_code == "430"
        assert lines[0].debe == 2420.0
        assert lines[0].haber == 0.0

        # Haber: ingreso
        assert lines[1].cuenta_code == "705"
        assert lines[1].haber == 2000.0
        assert lines[1].debe == 0.0

        # Haber: IVA repercutido
        assert lines[2].cuenta_code == "477"
        assert lines[2].haber == 420.0
        assert lines[2].debe == 0.0

    def test_factura_emitida_sin_iva(self):
        """Factura emitida sin IVA -> solo 2 lines (cliente + ingreso)."""
        lines = ContabilidadService.generate_asiento_lines(
            tipo="emitida",
            cuenta_pgc_code="700",
            cuenta_pgc_nombre="Ventas de mercaderias",
            base_imponible=500.0,
            cuota_iva=0.0,
            total=500.0,
            retencion_irpf=0.0,
            concepto="Venta exenta",
        )

        assert len(lines) == 2
        codes = [l.cuenta_code for l in lines]
        assert "477" not in codes


# ---------------------------------------------------------------------------
# Test 3: Factura emitida con retencion IRPF — 4 lines
# ---------------------------------------------------------------------------
class TestGenerateAsientoConIRPF:
    def test_factura_emitida_con_retencion(self):
        """Factura emitida con IRPF -> 4 lines: cliente + retenciones + ingreso + IVA."""
        lines = ContabilidadService.generate_asiento_lines(
            tipo="emitida",
            cuenta_pgc_code="705",
            cuenta_pgc_nombre="Prestaciones de servicios",
            base_imponible=1000.0,
            cuota_iva=210.0,
            total=1060.0,  # 1000 + 210 - 150
            retencion_irpf=150.0,
            concepto="Factura con retencion 15%",
        )

        assert len(lines) == 4

        # Debe: cliente (total = base + iva - retencion)
        assert lines[0].cuenta_code == "430"
        assert lines[0].debe == 1060.0

        # Debe: retenciones
        assert lines[1].cuenta_code == "473"
        assert lines[1].debe == 150.0

        # Haber: ingreso
        assert lines[2].cuenta_code == "705"
        assert lines[2].haber == 1000.0

        # Haber: IVA repercutido
        assert lines[3].cuenta_code == "477"
        assert lines[3].haber == 210.0


# ---------------------------------------------------------------------------
# Test 4: Parametric — debe == haber for various combos
# ---------------------------------------------------------------------------
class TestAsientoDebeEqualsHaber:
    @pytest.mark.parametrize(
        "tipo,cuenta,base,iva,total,irpf",
        [
            ("recibida", "600", 1000, 210, 1210, 0),
            ("recibida", "629", 500, 105, 605, 0),
            ("recibida", "600", 300, 0, 300, 0),
            ("emitida", "705", 2000, 420, 2420, 0),
            ("emitida", "700", 800, 168, 968, 0),
            ("emitida", "705", 1000, 210, 1060, 150),
            ("emitida", "700", 5000, 1050, 5300, 750),
            ("emitida", "705", 100, 0, 100, 0),
            ("recibida", "621", 1500, 315, 1815, 0),
        ],
    )
    def test_debe_equals_haber(self, tipo, cuenta, base, iva, total, irpf):
        lines = ContabilidadService.generate_asiento_lines(
            tipo=tipo,
            cuenta_pgc_code=cuenta,
            cuenta_pgc_nombre="Test",
            base_imponible=base,
            cuota_iva=iva,
            total=total,
            retencion_irpf=irpf,
            concepto="Test balance",
        )

        total_debe = sum(l.debe for l in lines)
        total_haber = sum(l.haber for l in lines)
        assert abs(total_debe - total_haber) < 0.01, (
            f"Desbalance: debe={total_debe}, haber={total_haber}"
        )


# ---------------------------------------------------------------------------
# Test 5: get_libro_diario — mock DB, verify query returns entries
# ---------------------------------------------------------------------------
class TestGetLibroDiario:
    @pytest.mark.asyncio
    async def test_get_libro_diario_returns_entries(self):
        """get_libro_diario queries DB and returns formatted entries."""
        mock_rows = [
            {
                "id": "a1",
                "fecha": "2026-01-15",
                "numero_asiento": 1,
                "cuenta_code": "430",
                "cuenta_nombre": "Clientes",
                "debe": 1210.0,
                "haber": 0.0,
                "concepto": "Factura 001",
                "trimestre": 1,
            },
            {
                "id": "a2",
                "fecha": "2026-01-15",
                "numero_asiento": 1,
                "cuenta_code": "705",
                "cuenta_nombre": "Prestaciones de servicios",
                "debe": 0.0,
                "haber": 1000.0,
                "concepto": "Factura 001",
                "trimestre": 1,
            },
            {
                "id": "a3",
                "fecha": "2026-01-15",
                "numero_asiento": 1,
                "cuenta_code": "477",
                "cuenta_nombre": "HP IVA repercutido",
                "debe": 0.0,
                "haber": 210.0,
                "concepto": "Factura 001",
                "trimestre": 1,
            },
        ]

        mock_result = MagicMock()
        mock_result.rows = mock_rows

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = ContabilidadService(db=mock_db)
        entries = await service.get_libro_diario(user_id="user-1", year=2026, trimestre=1)

        assert len(entries) == 3
        assert entries[0]["cuenta_code"] == "430"
        assert entries[2]["cuenta_code"] == "477"

        # Verify parameterized query was called
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert "?" in sql  # Parameterized, not f-string
        assert "user-1" not in sql  # Actual value not injected into SQL
        assert "user-1" in params  # Value passed as parameter

    @pytest.mark.asyncio
    async def test_get_libro_diario_without_trimestre(self):
        """get_libro_diario without trimestre returns all entries for the year."""
        mock_result = MagicMock()
        mock_result.rows = []

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = ContabilidadService(db=mock_db)
        entries = await service.get_libro_diario(user_id="user-1", year=2026)

        assert entries == []
        call_sql = mock_db.execute.call_args[0][0].lower()
        # WHERE clause should NOT filter by trimestre when not provided
        where_clause = call_sql.split("where")[1].split("order")[0]
        assert "trimestre = ?" not in where_clause


# ---------------------------------------------------------------------------
# Test 6: get_libro_mayor — grouped accounts with saldo
# ---------------------------------------------------------------------------
class TestGetLibroMayor:
    @pytest.mark.asyncio
    async def test_get_libro_mayor(self):
        mock_rows = [
            {"cuenta_code": "430", "cuenta_nombre": "Clientes", "total_debe": 5000.0, "total_haber": 0.0},
            {"cuenta_code": "477", "cuenta_nombre": "HP IVA repercutido", "total_debe": 0.0, "total_haber": 1050.0},
            {"cuenta_code": "705", "cuenta_nombre": "Prestaciones", "total_debe": 0.0, "total_haber": 3950.0},
        ]
        mock_result = MagicMock()
        mock_result.rows = mock_rows

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = ContabilidadService(db=mock_db)
        result = await service.get_libro_mayor(user_id="user-1", year=2026)

        assert len(result) == 3
        assert result[0]["saldo"] == 5000.0  # 5000 - 0
        assert result[1]["saldo"] == -1050.0  # 0 - 1050


# ---------------------------------------------------------------------------
# Test 7: save_asiento — inserts lines into DB
# ---------------------------------------------------------------------------
class TestSaveAsiento:
    @pytest.mark.asyncio
    async def test_save_asiento_inserts_lines(self):
        lines = ContabilidadService.generate_asiento_lines(
            tipo="emitida",
            cuenta_pgc_code="705",
            cuenta_pgc_nombre="Prestaciones de servicios",
            base_imponible=1000.0,
            cuota_iva=210.0,
            total=1210.0,
            retencion_irpf=0.0,
            concepto="Test",
        )

        # Mock: MAX returns None (first asiento)
        mock_max_result = MagicMock()
        mock_max_result.rows = [{"max_num": None}]

        mock_insert_result = MagicMock()
        mock_insert_result.rows = []

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=[mock_max_result, mock_insert_result, mock_insert_result, mock_insert_result])

        service = ContabilidadService(db=mock_db)
        ids = await service.save_asiento(
            user_id="user-1",
            libro_registro_id="lr-1",
            fecha="2026-01-15",
            lines=lines,
            year=2026,
            trimestre=1,
        )

        assert len(ids) == 3
        # 1 MAX query + 3 inserts = 4 calls
        assert mock_db.execute.call_count == 4


# ---------------------------------------------------------------------------
# Test 8: get_balance_sumas_saldos
# ---------------------------------------------------------------------------
class TestBalanceSumasSaldos:
    @pytest.mark.asyncio
    async def test_balance_sumas_saldos(self):
        mock_rows = [
            {"cuenta_code": "430", "cuenta_nombre": "Clientes", "total_debe": 5000.0, "total_haber": 0.0},
            {"cuenta_code": "705", "cuenta_nombre": "Prestaciones", "total_debe": 0.0, "total_haber": 5000.0},
        ]
        mock_result = MagicMock()
        mock_result.rows = mock_rows

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = ContabilidadService(db=mock_db)
        balance = await service.get_balance_sumas_saldos(user_id="user-1", year=2026)

        assert balance["total_debe"] == 5000.0
        assert balance["total_haber"] == 5000.0
        assert balance["diferencia"] == 0.0
        assert balance["year"] == 2026
        assert len(balance["cuentas"]) == 2


# ---------------------------------------------------------------------------
# Test 9: get_pyg — profit & loss statement
# ---------------------------------------------------------------------------
class TestPyG:
    @pytest.mark.asyncio
    async def test_pyg_resultado(self):
        mock_rows = [
            {"cuenta_code": "600", "cuenta_nombre": "Compras", "total_debe": 3000.0, "total_haber": 0.0},
            {"cuenta_code": "629", "cuenta_nombre": "Otros servicios", "total_debe": 500.0, "total_haber": 0.0},
            {"cuenta_code": "705", "cuenta_nombre": "Prestaciones", "total_debe": 0.0, "total_haber": 6000.0},
        ]
        mock_result = MagicMock()
        mock_result.rows = mock_rows

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = ContabilidadService(db=mock_db)
        pyg = await service.get_pyg(user_id="user-1", year=2026)

        assert pyg["total_gastos"] == 3500.0  # 3000 + 500
        assert pyg["total_ingresos"] == 6000.0
        assert pyg["resultado"] == 2500.0  # 6000 - 3500
        assert "disclaimer" in pyg
