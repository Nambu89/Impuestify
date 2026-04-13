"""Tests para el clasificador regex de documentos tributarios.

Los encabezados usados en estos tests corresponden a documentos reales del caso
David Oliva (expediente IRPF 2024 Madrid) como ground truth del caso primigenio.
"""
from app.models.defensia import TipoDocumento
from app.services.defensia_document_taxonomy import clasificar_por_texto


def test_clasifica_liquidacion_provisional_por_titulo():
    texto = "NOTIFICACIÓN DE RESOLUCIÓN CON LIQUIDACIÓN PROVISIONAL\nRef: 202410049560746N"
    assert clasificar_por_texto(texto) == TipoDocumento.LIQUIDACION_PROVISIONAL


def test_clasifica_acuerdo_sancion():
    texto = "ACUERDO DE IMPOSICIÓN DE SANCIÓN POR INFRACCIÓN TRIBUTARIA"
    assert clasificar_por_texto(texto) == TipoDocumento.ACUERDO_IMPOSICION_SANCION


def test_clasifica_requerimiento():
    texto = "REQUERIMIENTO\nEn uso de las facultades que confiere..."
    assert clasificar_por_texto(texto) == TipoDocumento.REQUERIMIENTO


def test_clasifica_propuesta_liquidacion():
    texto = "PROPUESTA DE LIQUIDACIÓN PROVISIONAL Y TRÁMITE DE ALEGACIONES"
    assert clasificar_por_texto(texto) == TipoDocumento.PROPUESTA_LIQUIDACION


def test_clasifica_escrito_reclamacion_tear_usuario():
    texto = "AL TRIBUNAL ECONÓMICO-ADMINISTRATIVO REGIONAL DE MADRID\nESCRITO DE INTERPOSICIÓN"
    assert clasificar_por_texto(texto) == TipoDocumento.ESCRITO_RECLAMACION_TEAR_USUARIO


def test_clasifica_acta_inspeccion_fuera_alcance():
    texto = "ACTA DE DISCONFORMIDAD A24-..."
    assert clasificar_por_texto(texto) == TipoDocumento.ACTA_INSPECCION


def test_clasifica_providencia_apremio():
    texto = "PROVIDENCIA DE APREMIO"
    assert clasificar_por_texto(texto) == TipoDocumento.PROVIDENCIA_APREMIO


def test_texto_ambiguo_devuelve_otros():
    texto = "Documento sin encabezado reconocible"
    assert clasificar_por_texto(texto) == TipoDocumento.OTROS
