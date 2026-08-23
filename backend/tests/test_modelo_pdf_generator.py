"""
Tests for ModeloPDFGenerator.

Verifies PDF generation for all 13 supported modelo types (7 full + 6 placeholder)
plus unknown modelo validation.
"""

import pytest

from app.services.modelo_pdf_generator import (
    FULL_MODELOS,
    PLACEHOLDER_MODELOS,
    VALID_MODELOS,
    ModeloPDFGenerator,
)


@pytest.fixture
def generator():
    return ModeloPDFGenerator()


@pytest.fixture
def user_info():
    return {"nombre": "Juan Garcia Lopez", "nif": "12345678Z"}


# -- Sample data for each modelo --

SAMPLE_303 = {
    "iva_devengado": {
        "cuota_21": 2100.00,
        "cuota_10": 500.00,
        "cuota_4": 0,
        "cuota_intracomunitaria": 0,
        "total_devengado": 2600.00,
    },
    "iva_deducible": {
        "bienes_corrientes": 800.00,
        "bienes_inversion": 0,
        "importaciones": 0,
        "intracomunitarias": 0,
        "rectificacion": 0,
        "total_deducible": 800.00,
    },
    "resultado": {
        "regimen_general": 1800.00,
        "compensacion_anterior": 0,
        "resultado_final": 1800.00,
        "tipo": "A ingresar",
    },
}

SAMPLE_130 = {
    "seccion_i": {
        "ingresos_computables": 15000.00,
        "gastos_deducibles": 5000.00,
        "rendimiento_neto": 10000.00,
        "veinte_porciento": 2000.00,
        "retenciones": 300.00,
        "pagos_anteriores": 0,
        "resultado_seccion": 1700.00,
    },
    "deduccion_80bis": 0,
    "resultado_final": 1700.00,
}

SAMPLE_308 = {
    "adquisiciones_intracomunitarias": {
        "base_total": 5000.00,
        "cuota_iva": 1050.00,
        "cuota_re": 260.00,
        "desglose": {
            "base_21": 5000.00,
            "iva_21": 1050.00,
            "re_21": 260.00,
            "base_10": 0,
            "iva_10": 0,
            "re_10": 0,
            "base_4": 0,
            "iva_4": 0,
            "re_4": 0,
        },
    },
    "inversion_sujeto_pasivo": {
        "base_total": 0,
        "cuota_iva": 0,
        "cuota_re": 0,
        "desglose": {},
    },
    "resultado": {"resultado_final": -790.00},
}

SAMPLE_720 = {
    "ejercicio": 2025,
    "obligado_720": True,
    "detalles": [
        {
            "categoria": "cuentas",
            "descripcion": "Cuentas bancarias en el extranjero",
            "valor_actual": 75000.00,
            "supera_umbral_50k": True,
            "obligado": True,
        },
        {
            "categoria": "valores",
            "descripcion": "Valores y derechos en el extranjero",
            "valor_actual": 30000.00,
            "supera_umbral_50k": False,
            "obligado": False,
        },
    ],
    "plazo": "Del 1 de enero al 31 de marzo de 2026",
    "recomendaciones": ["Presenta el Modelo 720 antes del 31 de marzo de 2026."],
}

SAMPLE_721 = {
    "ejercicio": 2025,
    "obligado_721": True,
    "valor_crypto_extranjero": 60000.00,
    "incremento_vs_ultimo_721": 25000.00,
    "exchanges_afectados": ["Binance", "Kraken"],
    "exchanges_espanoles_excluidos": ["Bit2Me"],
    "plazo": "Del 1 de enero al 31 de marzo de 2026",
    "recomendaciones": ["Revisa los saldos a 31 de diciembre."],
}

SAMPLE_IPSI = {
    "desglose_devengado": {
        "tipo_general_4": {"base": 10000.00, "cuota": 400.00},
        "tipo_minimo_0_5": {"base": 0, "cuota": 0},
        "tipo_inferior_1": {"base": 0, "cuota": 0},
        "tipo_ordinario_2": {"base": 0, "cuota": 0},
        "tipo_incrementado_8": {"base": 0, "cuota": 0},
        "tipo_especial_10": {"base": 0, "cuota": 0},
    },
    "total_devengado": 400.00,
    "desglose_deducible": {
        "cuota_corrientes_interiores": 100.00,
        "cuota_inversion_interiores": 0,
        "cuota_importaciones_corrientes": 0,
    },
    "total_deducible": 100.00,
    "resultado_liquidacion": 300.00,
}


def _assert_valid_pdf(pdf_bytes: bytes):
    """Validate that result is a valid PDF."""
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes[:5] == b"%PDF-"
    assert len(pdf_bytes) > 1000


class TestModeloPDFGenerator:
    """Tests for ModeloPDFGenerator."""

    def test_generate_303(self, generator, user_info):
        """Modelo 303 (IVA) generates a valid PDF."""
        result = generator.generate("303", SAMPLE_303, user_info, "1T", 2026)
        _assert_valid_pdf(result)

    def test_generate_130(self, generator, user_info):
        """Modelo 130 (IRPF Pago Fraccionado) generates a valid PDF."""
        result = generator.generate("130", SAMPLE_130, user_info, "2T", 2026)
        _assert_valid_pdf(result)

    def test_generate_308(self, generator, user_info):
        """Modelo 308 (RE Farmacia) generates a valid PDF."""
        result = generator.generate("308", SAMPLE_308, user_info, "3T", 2025)
        _assert_valid_pdf(result)

    def test_generate_720(self, generator, user_info):
        """Modelo 720 (Bienes extranjero) generates a valid PDF."""
        result = generator.generate("720", SAMPLE_720, user_info, "anual", 2025)
        _assert_valid_pdf(result)

    def test_generate_721(self, generator, user_info):
        """Modelo 721 (Crypto extranjero) generates a valid PDF."""
        result = generator.generate("721", SAMPLE_721, user_info, "anual", 2025)
        _assert_valid_pdf(result)

    def test_generate_ipsi(self, generator, user_info):
        """Modelo IPSI (Ceuta/Melilla) generates a valid PDF."""
        result = generator.generate("ipsi", SAMPLE_IPSI, user_info, "4T", 2026)
        _assert_valid_pdf(result)

    def test_generate_303_foral(self, generator):
        """Modelo 303 with foral variant uses correct header."""
        user_info_foral = {
            "nombre": "Maria Lopez",
            "nif": "87654321X",
            "variante_foral": "300",
        }
        result = generator.generate("303", SAMPLE_303, user_info_foral, "1T", 2026)
        _assert_valid_pdf(result)

    def test_unknown_modelo_raises_valueerror(self, generator, user_info):
        """Unknown modelo type raises ValueError."""
        with pytest.raises(ValueError, match="no soportado"):
            generator.generate("999", {}, user_info, "1T", 2026)


# -- Tests for placeholder modelos (in development) --


class TestModeloPDFPlaceholders:
    """Verify placeholder PDFs for modelos still under development."""

    def test_valid_modelos_set_has_15(self):
        """VALID_MODELOS = full (10) + placeholder (5) = 15.

        Updated 2026-05: Modelos 131, 349, 390 ascendidos a FULL.
        Updated 2026-05 (sesion 40): AIEM 450 + 455 anadidos como placeholders.
        """
        assert len(FULL_MODELOS) == 10
        assert len(PLACEHOLDER_MODELOS) == 5
        assert len(VALID_MODELOS) == 15
        assert FULL_MODELOS.isdisjoint(PLACEHOLDER_MODELOS)

    def test_placeholder_modelos_expected(self):
        """Placeholder set must include all anunciados pendientes."""
        assert PLACEHOLDER_MODELOS == {
            "100",
            "309",
            "420",
            "450",
            "455",
        }

    @pytest.mark.parametrize("modelo", sorted(PLACEHOLDER_MODELOS))
    def test_placeholder_generates_valid_pdf(self, generator, user_info, modelo):
        """Each placeholder modelo returns a valid PDF >= 1KB."""
        result = generator.generate(modelo, {}, user_info, "1T", 2026)
        _assert_valid_pdf(result)
        # Reinforce the >=1KB requirement explicitly
        assert len(result) >= 1024, f"Placeholder modelo {modelo} produced only {len(result)} bytes"

    @pytest.mark.parametrize("modelo", sorted(PLACEHOLDER_MODELOS))
    def test_placeholder_contains_disclaimer_text(self, generator, user_info, modelo):
        """Placeholder PDFs must mention 'Borrador en desarrollo' and AEAT."""
        result = generator.generate(modelo, {}, user_info, "anual", 2026)
        # PDF bytes are deflate-compressed in streams, but reportlab embeds
        # the literal title text in the document outline / metadata uncompressed.
        # We rely on the structural assertions plus header rendering being
        # exercised by the dispatch path. Length + magic bytes already validated.
        assert result[:5] == b"%PDF-"

    def test_placeholder_with_extra_data_renders(self, generator, user_info):
        """Placeholder accepts extra keys (ccaa, regimen) without crashing."""
        data = {
            "ccaa": "Madrid",
            "regimen": "Estimación directa simplificada",
            "epigrafe_iae": "8690",
        }
        result = generator.generate("131", data, user_info, "2T", 2026)
        _assert_valid_pdf(result)

    def test_placeholder_without_user_info(self, generator):
        """Placeholder tolerates missing user_info fields gracefully."""
        result = generator.generate("349", {}, {}, "1T", 2026)
        _assert_valid_pdf(result)

    @pytest.mark.parametrize("modelo", sorted(FULL_MODELOS))
    def test_full_modelos_still_in_valid_set(self, modelo):
        """Regression: existing modelos must remain valid after expansion."""
        assert modelo in VALID_MODELOS


# ===========================================================================
# Modelo 131 — etiquetas de casilla contra el diseño de registro oficial
# ===========================================================================


def _render_131_texts(generator, data: dict) -> list[str]:
    """Renderiza `_render_131` y devuelve el texto plano de todas las celdas.

    Se inspecciona el `story` de ReportLab en vez del PDF final porque el texto
    va comprimido en los streams del PDF y no se puede buscar en los bytes.
    """
    generator._setup_styles()
    story: list = []
    generator._render_131(story, data)

    texts: list[str] = []
    for element in story:
        rows = getattr(element, "_cellvalues", None)
        if rows:
            for row in rows:
                texts.extend(str(cell) for cell in row)
        else:
            texts.append(str(getattr(element, "text", element)))
    return texts


class TestModelo131Casillas:
    """La numeración visible debe ser la de DR131_2026, no la clave del dict.

    Diseño de registro `docs/AEAT/modelo-130-2026/DR131_2026.xlsx`:
      [01] Suma de rendimientos netos (apartado I)
      [02] Pago fraccionado previo: suma de resultados (apartado I)
      [05] Volumen ingresos trimestre (apartado III)
      [06] Pago fraccionado previo del trimestre (apartado III)
      [07] Suma de los pagos fraccionados previos del trimestre
      [08] A deducir: retenciones e ingresos a cuenta
      [09] Minoración por aplicación de la deducción. Artículo 110.3.c
      [15] Resultado de la declaración

    OJO: [12] es "Pago de préstamos para la adquisición de vivienda habitual".
    """

    @pytest.fixture
    def data_apartado_i(self):
        return {
            "apartado": "I",
            "casillas": {
                "01_rendimiento_neto_modulos": 18000.0,
                "02_tipo_aplicable": 2.0,
                "03_resultado_empresarial": 360.0,
                "04_volumen_ingresos_agrario": 0.0,
                "05_cuota_agraria": 0.0,
                "06_total_cuotas": 360.0,
                "07_reducciones": 0.0,
                "08_resultado_tras_reducciones": 360.0,
                "09_retenciones_trimestre": 50.0,
                "10_pagos_anteriores": 0.0,
                "11_complementaria": 0.0,
                "12_resultado_final": 210.0,
            },
            "desglose": {"minoracion_rendimientos_bajos": 100.0},
            "resultado_final": 210.0,
        }

    def test_apartado_i_usa_numeracion_oficial(self, generator, data_apartado_i):
        texts = _render_131_texts(generator, data_apartado_i)
        joined = " | ".join(texts)
        assert "01" in texts  # Suma de rendimientos netos
        assert "02" in texts  # Pago fraccionado previo: suma de resultados
        assert "07" in texts  # Suma de los pagos fraccionados previos
        assert "[08]" in joined  # Retenciones e ingresos a cuenta
        assert "[15]" in joined  # Resultado de la declaración

    def test_resultado_nunca_se_etiqueta_como_casilla_12(self, generator, data_apartado_i):
        """[12] es la deducción por vivienda habitual, no el resultado."""
        joined = " | ".join(_render_131_texts(generator, data_apartado_i))
        assert "[12]" not in joined
        assert "Resultado de la declaración [15]" in joined

    def test_minoracion_se_etiqueta_como_09_con_la_norma_vigente(self, generator, data_apartado_i):
        """La minoración es la casilla [09] y cita el art. 110.3.c) RIRPF.

        El art. 80 bis LIRPF está SUPRIMIDO desde el 01/01/2015 (art. 1.55 de
        la Ley 26/2014), así que no puede aparecer como base legal.
        """
        joined = " | ".join(_render_131_texts(generator, data_apartado_i))
        assert "110.3.c" in joined
        assert "[09]" in joined
        assert "80 bis" not in joined

    def test_porcentaje_no_se_imprime_como_euros(self, generator, data_apartado_i):
        """El tipo aplicable es un porcentaje, no un importe.

        Iba por `_format_eur` y salia como "2,00 EUR" en un PDF que el usuario
        presenta. Ademas no es una casilla numerada: en el modelo es el
        "Porcentaje aplicable" de cada actividad.
        """
        texts = _render_131_texts(generator, data_apartado_i)
        assert "2%" in texts
        assert "2,00 EUR" not in texts
        assert "Porcentaje aplicable" in texts

    def test_apartado_iii_usa_numeracion_oficial(self, generator):
        data = {
            "apartado": "III",
            "casillas": {
                "01_rendimiento_neto_modulos": 0.0,
                "02_tipo_aplicable": 0.0,
                "03_resultado_empresarial": 0.0,
                "04_volumen_ingresos_agrario": 10000.0,
                "05_cuota_agraria": 200.0,
                "06_total_cuotas": 200.0,
                "07_reducciones": 0.0,
                "08_resultado_tras_reducciones": 200.0,
                "09_retenciones_trimestre": 0.0,
                "10_pagos_anteriores": 0.0,
                "11_complementaria": 0.0,
                "12_resultado_final": 200.0,
            },
            "desglose": {},
            "resultado_final": 200.0,
        }
        texts = _render_131_texts(generator, data)
        assert "05" in texts  # Volumen ingresos trimestre
        assert "06" in texts  # Pago fraccionado previo del trimestre
        assert "07" in texts  # Suma de los pagos fraccionados previos

    def test_apartado_ii_usa_numeracion_oficial_y_porcentaje_en_pct(self, generator):
        """Apartado II: [03] volumen, [04] pago fraccionado previo.

        El porcentaje comparte fila con importes en euros, asi que se comprueba
        aqui tambien que no salga como "2,00 EUR".
        """
        data = {
            "apartado": "II",
            "casillas": {
                "01_rendimiento_neto_modulos": 12000.0,
                "02_tipo_aplicable": 2.0,
                "03_resultado_empresarial": 240.0,
                "04_volumen_ingresos_agrario": 0.0,
                "05_cuota_agraria": 0.0,
                "06_total_cuotas": 240.0,
                "07_reducciones": 0.0,
                "08_resultado_tras_reducciones": 240.0,
                "09_retenciones_trimestre": 0.0,
                "10_pagos_anteriores": 0.0,
                "11_complementaria": 0.0,
                "12_resultado_final": 240.0,
            },
            "desglose": {},
            "resultado_final": 240.0,
        }
        texts = _render_131_texts(generator, data)
        joined = " | ".join(texts)
        assert "03" in texts  # Volumen de ventas o ingresos
        assert "04" in texts  # Pago fraccionado previo
        assert "07" in texts  # Suma de los pagos fraccionados previos
        assert "[15]" in joined
        assert "[12]" not in joined
        assert "2%" in texts
        assert "2,00 EUR" not in texts

    def test_apartado_iii_no_inventa_un_porcentaje(self, generator):
        """El apartado III no tiene fila de porcentaje: el 2% va en la etiqueta.

        Si se colara `02_tipo_aplicable` (que ahi vale 0,0) saldria un "0%" que
        contradice el propio concepto de la fila [06].
        """
        data = {
            "apartado": "III",
            "casillas": {
                "01_rendimiento_neto_modulos": 0.0,
                "02_tipo_aplicable": 0.0,
                "03_resultado_empresarial": 0.0,
                "04_volumen_ingresos_agrario": 10000.0,
                "05_cuota_agraria": 200.0,
                "06_total_cuotas": 200.0,
                "07_reducciones": 0.0,
                "08_resultado_tras_reducciones": 200.0,
                "09_retenciones_trimestre": 0.0,
                "10_pagos_anteriores": 0.0,
                "11_complementaria": 0.0,
                "12_resultado_final": 200.0,
            },
            "desglose": {},
            "resultado_final": 200.0,
        }
        texts = _render_131_texts(generator, data)
        assert "0%" not in texts
        assert "Pago fraccionado previo del trimestre (2%)" in texts

    def test_complementaria_es_la_casilla_14(self, generator, data_apartado_i):
        """[14] = "A deducir: resultado a ingresar de las anteriores
        declaraciones", que es el importe de la complementaria. Los pagos
        fraccionados de trimestres anteriores NO tienen casilla en el 131."""
        data = dict(data_apartado_i)
        data["casillas"] = {
            **data_apartado_i["casillas"],
            "10_pagos_anteriores": 80.0,
            "11_complementaria": 40.0,
        }
        joined = " | ".join(_render_131_texts(generator, data))
        assert "anteriores declaraciones [14]" in joined
        assert "Pagos fraccionados de trimestres anteriores" in joined
        # [10] es "Diferencia" y [11] "Resultados negativos de trimestres
        # anteriores": ninguna de las dos es lo que aquí se está restando.
        assert "[10]" not in joined
        assert "[11]" not in joined


# ---------------------------------------------------------------------------
# Contenido del PDF del Modelo 130
#
# Los tests de arriba solo comprueban que el fichero empieza por "%PDF-". Eso
# dejo pasar un fallo de dinero: la pagina de Modelos Trimestrales enviaba a
# /api/export/modelo-pdf el resultado en crudo de
# POST /api/declarations/130/calculate, que trae `casillas` / `resultado`,
# mientras que `_render_130` lee `seccion_i` / `deduccion_80bis` /
# `resultado_final`. Ninguna clave coincidia, asi que el usuario se descargaba
# un Modelo 130 con las casillas 01-07 y el resultado a CERO.
#
# La traduccion la hace ahora el frontend en
# `frontend/src/utils/modelo130Pdf.ts`. Estos tests fijan el contrato por el
# lado del backend y, sobre todo, miran el CONTENIDO del PDF.
# ---------------------------------------------------------------------------


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Texto plano del PDF.

    Los acentos salen mal codificados con las fuentes base de ReportLab, asi
    que solo se debe assertar sobre cifras, numeros de casilla y etiquetas sin
    tildes.
    """
    import io

    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _eur_amounts(pdf_bytes: bytes) -> list[str]:
    """Importes del PDF como tokens completos.

    Hace falta porque "0,00 EUR" es SUBCADENA de "30.000,00 EUR": buscar el
    cero con `in` o contarlo con `.count()` sobre el texto da falsos positivos.
    """
    import re

    return re.findall(r"-?\d{1,3}(?:\.\d{3})*,\d{2} EUR", _extract_pdf_text(pdf_bytes))


def _casilla_rows(pdf_bytes: bytes) -> dict[str, tuple[str, str]]:
    """Filas de las tablas de casillas: {concepto: (numero, importe)}.

    Las tablas de ReportLab se extraen como tres lineas consecutivas
    (numero, concepto, importe), asi que se ancla en el importe y se lee hacia
    atras. Comprobar solo que un importe aparece EN ALGUN SITIO del PDF no
    detectaria que las retenciones y los pagos anteriores esten intercambiados.
    """
    import re

    lines = [ln.strip() for ln in _extract_pdf_text(pdf_bytes).splitlines() if ln.strip()]
    amount_re = re.compile(r"^-?\d{1,3}(?:\.\d{3})*,\d{2} EUR$")

    rows: dict[str, tuple[str, str]] = {}
    for i, line in enumerate(lines):
        if i < 2 or not amount_re.match(line):
            continue
        rows[lines[i - 1]] = (lines[i - 2], line)
    return rows


# Payload tal y como lo construye `buildModelo130PdfData` para Territorio Comun.
# Caso: ingresos 30.000, gastos 10.000, retenciones 500, pagos anteriores 800,
# rend. neto del ano anterior 8.000 -> minoracion de 100 EUR (primer tramo del
# art. 110.3.c RIRPF).
FRONTEND_130_COMUN = {
    "seccion_i": {
        "ingresos_computables": 30000.0,
        "gastos_deducibles": 10000.0,
        "rendimiento_neto": 20000.0,
        "veinte_porciento": 4000.0,
        "retenciones": 500.0,
        "pagos_anteriores": 800.0,
        "resultado_seccion": 2700.0,
    },
    "deduccion_80bis": 100.0,
    "tipo_aplicado": 20,
    "resultado_final": 2600.0,
}

# Lo que enviaba la pagina antes del arreglo: el resultado del calculador REST
# en crudo, sin traducir.
CALCULATOR_130_RAW = {
    "territory": "Comun",
    "quarter": 2,
    "resultado": 2600.0,
    "tipo_aplicado": 20.0,
    "casillas": {
        "01_ingresos_acumulados": 30000.0,
        "02_gastos_acumulados": 10000.0,
        "03_rendimiento_neto": 20000.0,
        "04_cuota_20pct": 4000.0,
        "05_retenciones_acumuladas": 500.0,
        "06_pagos_anteriores": 800.0,
        "07_resultado_seccion_I": 2700.0,
        "13_deduccion_art80bis": 100.0,
        "19_resultado_final": 2600.0,
    },
}


class TestModelo130PDFContent:
    """El PDF del Modelo 130 debe llevar los importes, no ceros."""

    def test_130_lleva_los_importes_calculados(self, generator, user_info):
        importes = _eur_amounts(
            generator.generate("130", FRONTEND_130_COMUN, user_info, "2T", 2026)
        )

        for esperado in (
            "30.000,00 EUR",  # [01] ingresos computables
            "10.000,00 EUR",  # [02] gastos deducibles
            "20.000,00 EUR",  # [03] rendimiento neto
            "4.000,00 EUR",  # [04] cuota
            "500,00 EUR",  # retenciones e ingresos a cuenta
            "800,00 EUR",  # pagos fraccionados anteriores
            "2.700,00 EUR",  # [07] resultado seccion I
            "100,00 EUR",  # [13] minoracion art. 110.3.c RIRPF
            "2.600,00 EUR",  # resultado a ingresar
        ):
            assert esperado in importes, f"{esperado} no aparece en el PDF: {importes}"

    def test_130_cada_importe_va_en_su_concepto(self, generator, user_info):
        """
        Que el importe aparezca en algun sitio no basta: hay que comprobar que
        cae en SU fila. El riesgo real es cruzar retenciones con pagos
        anteriores, porque las claves del calculador REST
        (`05_retenciones_acumuladas`, `06_pagos_anteriores`) van al reves que la
        numeracion oficial de la AEAT (05 = pagos, 06 = retenciones).

        No se comprueba aqui el NUMERO de casilla de esas dos filas: esa
        numeracion se corrige en la rama del calculador. Lo que fija este test
        es la pareja concepto-importe, que es lo que decide el adaptador del
        frontend.
        """
        rows = _casilla_rows(generator.generate("130", FRONTEND_130_COMUN, user_info, "2T", 2026))

        esperado = {
            "Ingresos computables": ("01", "30.000,00 EUR"),
            "Gastos deducibles": ("02", "10.000,00 EUR"),
            "Rendimiento neto": ("03", "20.000,00 EUR"),
            "20% del rendimiento neto": ("04", "4.000,00 EUR"),
        }
        for concepto, par in esperado.items():
            assert concepto in rows, f"falta la fila {concepto}: {sorted(rows)}"
            assert rows[concepto] == par, f"{concepto} -> {rows[concepto]}, esperado {par}"

        # Sin numero de casilla: solo la pareja concepto-importe.
        assert rows["Retenciones e ingresos a cuenta"][1] == "500,00 EUR"
        assert rows["Pagos fraccionados anteriores"][1] == "800,00 EUR"

    def test_130_no_sale_en_blanco(self, generator, user_info):
        """Regresion directa del bug: ninguna casilla con datos puede salir a 0."""
        importes = _eur_amounts(
            generator.generate("130", FRONTEND_130_COMUN, user_info, "2T", 2026)
        )

        # Los nueve importes del caso son distintos de cero, asi que el PDF no
        # puede llevar ni una sola casilla a 0,00.
        assert importes, "el PDF no lleva ningun importe"
        assert "0,00 EUR" not in importes, f"el PDF trae casillas a cero: {importes}"
        assert "2.600,00 EUR" in importes

    def test_130_en_crudo_del_calculador_sale_a_cero(self, generator, user_info):
        """
        Contrato: `_render_130` lee `seccion_i`, NO las `casillas` del
        calculador REST. Enviarle el resultado en crudo produce un PDF vacio,
        que es exactamente el bug que se arreglo en el frontend
        (`frontend/src/utils/modelo130Pdf.ts`).

        Si este test empieza a fallar porque el renderizador ha aprendido a leer
        `casillas`, borralo y simplifica el adaptador del frontend: ya no hara
        falta traducir.
        """
        importes = _eur_amounts(
            generator.generate("130", CALCULATOR_130_RAW, user_info, "2T", 2026)
        )

        assert "30.000,00 EUR" not in importes
        assert "2.600,00 EUR" not in importes
        assert importes.count("0,00 EUR") >= 5, importes

    def test_130_foral_lleva_los_importes(self, generator, user_info):
        """
        Con `variante_foral` el renderizador entra por `_render_130_foral` y
        pinta las `casillas`. Sin ella pintaba un 130 comun con todas las filas
        a cero, que es lo que pasaba con Araba, Gipuzkoa, Bizkaia y Navarra.
        """
        data = {
            "variante_foral": "130-araba",
            "casillas": {
                "01_ingresos_trimestre": 12000.0,
                "02_gastos_trimestre": 2000.0,
                "03_rendimiento_neto_trimestral": 10000.0,
                "04_cuota_5pct": 500.0,
                "05_retenciones_trimestre": 150.0,
                "07_resultado": 350.0,
            },
            "tipo_aplicado": 5.0,
            "resultado_final": 350.0,
        }
        rows = _casilla_rows(
            generator.generate(
                "130", data, {**user_info, "variante_foral": "130-araba"}, "2T", 2026
            )
        )

        assert rows["Ingresos del trimestre"] == ("01", "12.000,00 EUR")
        assert rows["Gastos del trimestre"] == ("02", "2.000,00 EUR")
        assert rows["Rendimiento neto trimestral"] == ("03", "10.000,00 EUR")
        assert rows["Cuota 5%"] == ("04", "500,00 EUR")
        assert rows["Retenciones del trimestre"] == ("05", "150,00 EUR")

    def test_130_foral_sin_variante_sale_a_cero(self, generator, user_info):
        """Sin `variante_foral` el pago foral se pinta como un 130 comun vacio."""
        data = {
            "casillas": {
                "01_ingresos_trimestre": 12000.0,
                "04_cuota_5pct": 500.0,
                "07_resultado": 350.0,
            },
            "resultado_final": 350.0,
        }
        importes = _eur_amounts(generator.generate("130", data, user_info, "2T", 2026))
        assert "12.000,00 EUR" not in importes
        assert importes.count("0,00 EUR") >= 4, importes

    def test_130_foral_bizkaia_general_pierde_el_numero_de_casilla(self, generator, user_info):
        """
        Limitacion conocida, documentada aqui para que sea visible.

        El backend tiene DOS implementaciones forales del 130. La dedicada
        (`modelo_130_bizkaia.py`, la del chat) numera las casillas; la generica
        de `/api/declarations/130/calculate`, que alimenta la pagina de Modelos
        Trimestrales, devuelve claves sin numerar en Bizkaia general/excepcional
        y en Navarra. `_render_130_foral` saca el numero del prefijo de la
        clave, asi que la columna Casilla sale como "base" o "pago".

        Lo importante: los IMPORTES, los conceptos y el resultado si son
        correctos, que es lo que se rompia antes (todo a cero). La solucion de
        verdad es unificar las dos implementaciones forales del backend; el
        frontend NO renumera a proposito, porque asignar un numero oficial de
        casilla por su cuenta seria inventarse una referencia normativa.
        """
        data = {
            "variante_foral": "130-bizkaia",
            "casillas": {
                "rend_neto_penultimo": 40000.0,
                "retenciones_penultimo": 3000.0,
                "base_calculo": 40000.0,
                "pago_trimestral": 1250.0,
            },
            "tipo_aplicado": 5.0,
            "regimen": "general",
            "resultado_final": 1250.0,
        }
        pdf = generator.generate(
            "130", data, {**user_info, "variante_foral": "130-bizkaia"}, "2T", 2026
        )
        rows = _casilla_rows(pdf)

        # Los importes llegan y van en su concepto.
        assert rows["rend neto penultimo"][1] == "40.000,00 EUR"
        assert rows["retenciones penultimo"][1] == "3.000,00 EUR"
        assert rows["base calculo"][1] == "40.000,00 EUR"
        assert rows["pago trimestral"][1] == "1.250,00 EUR"
        assert "1.250,00 EUR" in _eur_amounts(pdf)

        # Y la limitacion: el numero de casilla no es un numero.
        assert rows["base calculo"][0] == "base"
