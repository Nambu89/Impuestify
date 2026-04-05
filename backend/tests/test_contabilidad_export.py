"""Tests for ContabilidadExportService (CSV/Excel exports)."""

import csv
import io

import pytest

from app.services.contabilidad_export_service import ContabilidadExportService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def diario_entries() -> list[dict]:
    return [
        {
            "fecha": "2026-01-15",
            "num_asiento": 1,
            "cuenta": "6000000",
            "nombre_cuenta": "Compras de mercaderias",
            "debe": 1000.00,
            "haber": 0.00,
            "concepto": "Factura proveedor A",
        },
        {
            "fecha": "2026-01-15",
            "num_asiento": 1,
            "cuenta": "4720000",
            "nombre_cuenta": "H.P. IVA soportado",
            "debe": 210.00,
            "haber": 0.00,
            "concepto": "Factura proveedor A",
        },
        {
            "fecha": "2026-01-15",
            "num_asiento": 1,
            "cuenta": "4000001",
            "nombre_cuenta": "Proveedor A",
            "debe": 0.00,
            "haber": 1210.00,
            "concepto": "Factura proveedor A",
        },
    ]


@pytest.fixture
def mayor_entries() -> list[dict]:
    return [
        {
            "cuenta": "6000000",
            "nombre": "Compras de mercaderias",
            "total_debe": 5000.00,
            "total_haber": 0.00,
            "saldo": 5000.00,
        },
    ]


@pytest.fixture
def factura_registro() -> list[dict]:
    return [
        {
            "fecha": "2026-02-10",
            "num_factura": "FRA-2026-0042",
            "tipo": "recibida",
            "nif_emisor": "B12345678",
            "emisor": "Distribuciones Lopez SL",
            "nif_receptor": "12345678Z",
            "receptor": "Mi Farmacia CB",
            "base_imponible": 500.00,
            "tipo_iva": 21.0,
            "cuota_iva": 105.00,
            "retencion_irpf": 0.00,
            "total": 605.00,
            "cuenta_pgc": "6000000",
            "descripcion": "Material de oficina",
        },
    ]


# ---------------------------------------------------------------------------
# CSV tests
# ---------------------------------------------------------------------------

class TestLibroDiarioCSV:
    def test_libro_diario_csv(self, diario_entries: list[dict]):
        raw = ContabilidadExportService.libro_diario_to_csv(diario_entries)
        assert isinstance(raw, bytes)

        text = raw.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)

        # Header row
        assert rows[0] == [
            "Fecha", "N Asiento", "Cuenta", "Nombre Cuenta",
            "Debe", "Haber", "Concepto",
        ]
        # 3 data rows
        assert len(rows) == 4  # header + 3

    def test_libro_diario_csv_empty(self):
        raw = ContabilidadExportService.libro_diario_to_csv([])
        text = raw.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        assert len(rows) == 1  # header only


class TestLibroMayorCSV:
    def test_libro_mayor_csv(self, mayor_entries: list[dict]):
        raw = ContabilidadExportService.libro_mayor_to_csv(mayor_entries)
        assert isinstance(raw, bytes)

        text = raw.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)

        assert rows[0] == ["Cuenta", "Nombre", "Total Debe", "Total Haber", "Saldo"]
        assert len(rows) == 2  # header + 1


class TestLibroRegistroCSV:
    def test_libro_registro_csv(self, factura_registro: list[dict]):
        raw = ContabilidadExportService.libro_registro_to_csv(factura_registro)
        assert isinstance(raw, bytes)

        text = raw.decode("utf-8-sig")
        assert "FRA-2026-0042" in text
        assert "Distribuciones Lopez SL" in text

        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        assert rows[0][0] == "Fecha"
        assert len(rows[0]) == 14  # 14 columns
        assert len(rows) == 2  # header + 1
