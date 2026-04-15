"""Tests para el extractor de libro registro Excel (sin LLM)."""
from io import BytesIO
from openpyxl import Workbook
from app.services.defensia_data_extractor import extract_libro_registro_xlsx


def _fake_libro() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["Fecha", "Numero", "Cliente", "Base", "IVA", "Total"])
    ws.append(["2024-03-15", "F001", "Cliente A", 1000, 210, 1210])
    ws.append(["2024-06-30", "F002", "Cliente B", 2000, 420, 2420])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_extract_libro_registro_lee_filas():
    datos = extract_libro_registro_xlsx(_fake_libro(), "libro.xlsx")
    assert datos["hojas"][0]["num_filas"] == 2
    assert datos["hojas"][0]["columnas"] == ["Fecha", "Numero", "Cliente", "Base", "IVA", "Total"]
    assert datos["hojas"][0]["filas"][0]["Total"] == 1210
    assert datos["total_importe_bases"] == 3000
    assert datos["total_importe_iva"] == 630


def test_extract_libro_registro_archivo_invalido():
    datos = extract_libro_registro_xlsx(b"not an xlsx", "bad.xlsx")
    assert "error" in datos
    assert datos["nombre"] == "bad.xlsx"
