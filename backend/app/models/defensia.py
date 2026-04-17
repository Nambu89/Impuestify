"""DefensIA — Pydantic models y enums.

Spec: plans/2026-04-13-defensia-design.md §5.2, §7.4
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class Tributo(str, Enum):
    IRPF = "IRPF"
    IVA = "IVA"
    ISD = "ISD"
    ITP = "ITP"
    PLUSVALIA = "PLUSVALIA"


class Fase(str, Enum):
    COMPROBACION_REQUERIMIENTO = "COMPROBACION_REQUERIMIENTO"
    COMPROBACION_PROPUESTA = "COMPROBACION_PROPUESTA"
    COMPROBACION_POST_ALEGACIONES = "COMPROBACION_POST_ALEGACIONES"
    LIQUIDACION_FIRME_PLAZO_RECURSO = "LIQUIDACION_FIRME_PLAZO_RECURSO"
    SANCIONADOR_INICIADO = "SANCIONADOR_INICIADO"
    SANCIONADOR_PROPUESTA = "SANCIONADOR_PROPUESTA"
    SANCIONADOR_IMPUESTA = "SANCIONADOR_IMPUESTA"
    REPOSICION_INTERPUESTA = "REPOSICION_INTERPUESTA"
    TEAR_INTERPUESTA = "TEAR_INTERPUESTA"
    TEAR_AMPLIACION_POSIBLE = "TEAR_AMPLIACION_POSIBLE"
    FUERA_DE_ALCANCE = "FUERA_DE_ALCANCE"
    INDETERMINADA = "INDETERMINADA"


class TipoDocumento(str, Enum):
    REQUERIMIENTO = "REQUERIMIENTO"
    PROPUESTA_LIQUIDACION = "PROPUESTA_LIQUIDACION"
    LIQUIDACION_PROVISIONAL = "LIQUIDACION_PROVISIONAL"
    ACUERDO_INICIO_SANCIONADOR = "ACUERDO_INICIO_SANCIONADOR"
    PROPUESTA_SANCION = "PROPUESTA_SANCION"
    ACUERDO_IMPOSICION_SANCION = "ACUERDO_IMPOSICION_SANCION"
    ESCRITO_ALEGACIONES_USUARIO = "ESCRITO_ALEGACIONES_USUARIO"
    ESCRITO_REPOSICION_USUARIO = "ESCRITO_REPOSICION_USUARIO"
    ESCRITO_RECLAMACION_TEAR_USUARIO = "ESCRITO_RECLAMACION_TEAR_USUARIO"
    ACTA_INSPECCION = "ACTA_INSPECCION"
    PROVIDENCIA_APREMIO = "PROVIDENCIA_APREMIO"
    RESOLUCION_TEAR = "RESOLUCION_TEAR"
    RESOLUCION_TEAC = "RESOLUCION_TEAC"
    SENTENCIA_JUDICIAL = "SENTENCIA_JUDICIAL"
    JUSTIFICANTE_PAGO = "JUSTIFICANTE_PAGO"
    FACTURA = "FACTURA"
    ESCRITURA = "ESCRITURA"
    LIBRO_REGISTRO = "LIBRO_REGISTRO"
    OTROS = "OTROS"


class EstadoExpediente(str, Enum):
    BORRADOR = "borrador"
    EN_ANALISIS = "en_analisis"
    DICTAMEN_LISTO = "dictamen_listo"
    ARCHIVADO = "archivado"


class DocumentoEstructurado(BaseModel):
    model_config = ConfigDict(use_enum_values=False)

    id: str
    nombre_original: str
    tipo_documento: TipoDocumento
    fecha_acto: Optional[datetime] = None
    datos: dict[str, Any] = Field(default_factory=dict)
    clasificacion_confianza: float = 1.0


class Brief(BaseModel):
    id: Optional[str] = None
    texto: str
    chat_history: list[dict[str, str]] = Field(default_factory=list)


class ExpedienteEstructurado(BaseModel):
    model_config = ConfigDict(use_enum_values=False)

    id: str
    tributo: Tributo
    ccaa: str
    documentos: list[DocumentoEstructurado] = Field(default_factory=list)
    fase_detectada: Fase = Fase.INDETERMINADA
    fase_confianza: float = 0.0

    def timeline_ordenado(self) -> list[DocumentoEstructurado]:
        """Devuelve documentos ordenados ASC por fecha_acto.

        Los documentos sin fecha_acto se colocan al final preservando el orden
        relativo de entrada (sort estable). Normaliza naive→UTC para evitar
        TypeError al mezclar fechas naive/aware (Gemini/parseo PDF puede
        devolver ambos). NO muta los documentos originales.
        """
        from datetime import timezone as _tz

        def _aware_key(d: DocumentoEstructurado):
            f = d.fecha_acto
            if f is None:
                return datetime.max.replace(tzinfo=_tz.utc)
            if f.tzinfo is None:
                return f.replace(tzinfo=_tz.utc)
            return f

        return sorted(self.documentos, key=_aware_key)


class ArgumentoCandidato(BaseModel):
    regla_id: str
    descripcion: str
    cita_normativa_propuesta: str
    datos_disparo: dict[str, Any]
    impacto_estimado: Optional[str] = None


class ArgumentoVerificado(BaseModel):
    regla_id: str
    descripcion: str
    cita_verificada: str
    referencia_normativa_canonica: str
    confianza: float = Field(ge=0.0, le=1.0)
    datos_disparo: dict[str, Any]
    impacto_estimado: Optional[str] = None
