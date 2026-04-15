"""DefensIA Writer Service (T2B-004).

Renderiza plantillas Jinja2 (autoescape=False porque el output es markdown
legal y los inputs son trusted del RAG verifier) con contexto
{expediente, argumentos, brief, fecha_hoy, disclaimer}.

Selecciona plantilla por `fase_detectada` del expediente + heurística de
importe (TEAR abreviada vs general).

Invariante #2: las plantillas NO hardcodean citas normativas. Todo viene
de los argumentos verificados por el RAG verifier.

Referencias:
- plans/2026-04-13-defensia-implementation-plan-part2.md §T2B-004
- backend/app/templates/defensia/*.j2 (9 plantillas, T2B-005)
- backend/app/services/defensia_export_service.py (consumidor, T2B-007/008)
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from app.models.defensia import (
    ArgumentoVerificado,
    Brief,
    ExpedienteEstructurado,
    Fase,
)

logger = logging.getLogger(__name__)


# Disclaimer canónico (alineado con DefensiaExportService). Replicado aquí
# para evitar import circular writer <-> export service.
DISCLAIMER_CANONICO = (
    "DefensIA es una herramienta de asistencia técnica que no constituye "
    "asesoramiento jurídico vinculante. Revisa y adapta el contenido antes "
    "de presentarlo ante cualquier administración."
)


# Umbral de cuota para distinguir TEAR abreviada vs general (6.000 EUR).
# Referencia: art. 245 LGT — procedimiento abreviado < 6.000 EUR (cuota)
# o < 72.000 EUR (base imponible). Implementamos sólo el criterio de cuota,
# que es el más común en los casos del público objetivo de DefensIA v1.
UMBRAL_TEAR_ABREVIADA_EUR = 6000.0


# Mapping fase -> plantilla por defecto. Las fases TEAR se resuelven aparte
# porque dependen de la cuota estimada.
_PLANTILLA_POR_FASE: dict[str, str] = {
    Fase.COMPROBACION_REQUERIMIENTO.value: "alegaciones_verificacion.j2",
    Fase.COMPROBACION_PROPUESTA.value: "alegaciones_verificacion.j2",
    Fase.COMPROBACION_POST_ALEGACIONES.value: "alegaciones_comprobacion_limitada.j2",
    Fase.LIQUIDACION_FIRME_PLAZO_RECURSO.value: "recurso_reposicion.j2",
    Fase.SANCIONADOR_INICIADO.value: "alegaciones_sancionador.j2",
    Fase.SANCIONADOR_PROPUESTA.value: "alegaciones_sancionador.j2",
    Fase.SANCIONADOR_IMPUESTA.value: "alegaciones_sancionador.j2",
    Fase.REPOSICION_INTERPUESTA.value: "reclamacion_tear_abreviada.j2",
    # TEAR_INTERPUESTA / TEAR_AMPLIACION_POSIBLE resuelven vía heurística.
}


class DefensiaWriterService:
    """Renderiza escritos DefensIA a partir de plantillas Jinja2.

    El writer NO toma decisiones jurídicas: sólo selecciona la plantilla
    que corresponde a la fase detectada y delega el contenido textual a
    los argumentos verificados por el motor de reglas + RAG verifier.
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        if templates_dir is None:
            templates_dir = Path(__file__).parent.parent / "templates" / "defensia"
        if not templates_dir.exists():
            raise RuntimeError(
                f"DefensIA templates dir no encontrado: {templates_dir}"
            )

        # autoescape=False: el output es markdown legal, los inputs provienen
        # del RAG verifier (trusted pipeline) y no se renderiza HTML. Escapar
        # rompería tildes, símbolos (<, >, &) y el propio markdown.
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    # ------------------------------------------------------------------
    # Selección de plantilla
    # ------------------------------------------------------------------

    def seleccionar_plantilla(
        self,
        expediente: ExpedienteEstructurado,
        cuota_estimada_eur: float = 0.0,
    ) -> str:
        """Devuelve el nombre del .j2 a usar según fase (+ heurística TEAR).

        Args:
            expediente: Expediente estructurado con `fase_detectada`.
            cuota_estimada_eur: Cuota impugnada (solo usada para TEAR).

        Returns:
            Nombre del fichero .j2 (relativo al templates_dir).
        """
        fase_valor = (
            expediente.fase_detectada.value
            if hasattr(expediente.fase_detectada, "value")
            else str(expediente.fase_detectada)
        )

        # TEAR: selección por cuota estimada (abreviada < 6.000 EUR).
        if fase_valor == Fase.TEAR_INTERPUESTA.value:
            if cuota_estimada_eur < UMBRAL_TEAR_ABREVIADA_EUR:
                return "reclamacion_tear_abreviada.j2"
            return "reclamacion_tear_general.j2"
        if fase_valor == Fase.TEAR_AMPLIACION_POSIBLE.value:
            return "ampliacion_tear.j2"

        # Mapping directo por fase.
        plantilla = _PLANTILLA_POR_FASE.get(fase_valor)
        if plantilla:
            return plantilla

        # Fallback genérico para fases fuera de alcance o indeterminadas.
        logger.info(
            "DefensIA writer fallback genérico para fase '%s'", fase_valor
        )
        return "escrito_generico.j2"

    # ------------------------------------------------------------------
    # API pública de renderizado
    # ------------------------------------------------------------------

    def render_escrito(
        self,
        expediente: ExpedienteEstructurado,
        argumentos: list[ArgumentoVerificado],
        brief: Optional[Brief] = None,
        *,
        cuota_estimada_eur: float = 0.0,
        fecha_hoy: Optional[date] = None,
        disclaimer: str = DISCLAIMER_CANONICO,
    ) -> str:
        """Renderiza el escrito principal del expediente en markdown.

        Selecciona la plantilla correspondiente a la fase y delega en
        `_render` la generación del contenido. El resultado se pasa después
        a `DefensiaExportService` para conversión a DOCX/PDF.
        """
        plantilla_nombre = self.seleccionar_plantilla(
            expediente, cuota_estimada_eur
        )
        return self._render(
            plantilla_nombre,
            expediente,
            argumentos,
            brief,
            fecha_hoy,
            disclaimer,
        )

    def render_dictamen(
        self,
        expediente: ExpedienteEstructurado,
        argumentos: list[ArgumentoVerificado],
        brief: Optional[Brief] = None,
        *,
        fecha_hoy: Optional[date] = None,
        disclaimer: str = DISCLAIMER_CANONICO,
    ) -> str:
        """Renderiza el dictamen resumen (output interno para el usuario).

        El dictamen es un análisis orientativo, no un escrito oficial. No
        lleva el disclaimer canónico en header+footer (lleva una nota al
        final dentro de la propia plantilla), pero aceptamos el parámetro
        por simetría con `render_escrito` y para permitir overrides en tests.
        """
        return self._render(
            "dictamen_resumen.md.j2",
            expediente,
            argumentos,
            brief,
            fecha_hoy,
            disclaimer,
        )

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _render(
        self,
        plantilla_nombre: str,
        expediente: ExpedienteEstructurado,
        argumentos: list[ArgumentoVerificado],
        brief: Optional[Brief],
        fecha_hoy: Optional[date],
        disclaimer: str,
    ) -> str:
        template = self._env.get_template(plantilla_nombre)
        if fecha_hoy is None:
            fecha_hoy = datetime.now(timezone.utc).date()

        rendered = template.render(
            expediente=expediente,
            argumentos=argumentos,
            brief=brief or Brief(texto=""),
            fecha_hoy=fecha_hoy,
            disclaimer=disclaimer,
        )
        return rendered
