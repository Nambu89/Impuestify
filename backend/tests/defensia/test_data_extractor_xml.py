"""Tests para el extractor de XML/XSIG de notificaciones firmadas AEAT."""
from app.services.defensia_data_extractor import extract_notificacion_xml


FAKE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<notificacion>
  <referencia>2026RSC49560055BG</referencia>
  <fecha>2026-04-07</fecha>
  <concepto>IRPF Sancion 2024</concepto>
  <importe>3393.52</importe>
</notificacion>
"""


def test_extract_xml_campos_basicos():
    datos = extract_notificacion_xml(FAKE_XML, "notif.xml")
    assert datos["referencia"] == "2026RSC49560055BG"
    assert datos["fecha"] == "2026-04-07"
    assert datos["importe"] == 3393.52


def test_extract_xml_invalido_devuelve_error():
    datos = extract_notificacion_xml(b"not xml", "bad.xml")
    assert "error" in datos
    assert datos["nombre"] == "bad.xml"
