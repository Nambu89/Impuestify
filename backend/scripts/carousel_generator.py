"""
carousel_generator.py — Generador de carruseles para Instagram y LinkedIn.

Genera slides PNG de calidad profesional usando Pillow.
Paleta de marca Impuestify: azul #1a56db, cyan #06b6d4, fondo oscuro #0f172a.

Usage:
    from carousel_generator import CarouselGenerator
    gen = CarouselGenerator(platform="linkedin")
    slides = gen.create_carousel(title=..., content_slides=[...], ...)

    python carousel_generator.py  # genera los 4 carruseles del plan
"""

from __future__ import annotations

import os
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont


# ---------------------------------------------------------------------------
# Paleta de colores
# ---------------------------------------------------------------------------

class Colors:
    PRIMARY       = (26,  86, 219)   # #1a56db
    PRIMARY_DARK  = (30,  64, 175)   # #1e40af
    PRIMARY_LIGHT = (59, 130, 246)   # #3b82f6
    ACCENT        = ( 6, 182, 212)   # #06b6d4
    SECONDARY     = (15,  23,  42)   # #0f172a  (fondo oscuro)
    GRAY800       = (30,  41,  59)   # #1e293b
    GRAY700       = (51,  65,  85)   # #334155
    GRAY400       = (148, 163, 184)  # #94a3b8
    WHITE         = (255, 255, 255)
    SUCCESS       = (16, 185, 129)   # #10b981
    WARNING       = (245, 158,  11)  # #f59e0b
    ERROR         = (239,  68,  68)  # #ef4444


# ---------------------------------------------------------------------------
# Helpers de fuentes
# ---------------------------------------------------------------------------

_FONT_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}

def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = (("bold" if bold else "regular"), size)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    candidates_bold = [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    candidates_regular = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    candidates = candidates_bold if bold else candidates_regular

    font = None
    for path in candidates:
        if Path(path).exists():
            font = ImageFont.truetype(path, size)
            break
    if font is None:
        font = ImageFont.load_default()

    _FONT_CACHE[key] = font
    return font


# ---------------------------------------------------------------------------
# Utilidades de dibujo
# ---------------------------------------------------------------------------

def _draw_gradient(
    img: Image.Image,
    color_top: tuple[int, int, int],
    color_bottom: tuple[int, int, int],
) -> None:
    """Dibuja un gradiente vertical sobre toda la imagen."""
    width, height = img.size
    draw = ImageDraw.Draw(img)
    for y in range(height):
        t = y / (height - 1)
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * t)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * t)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * t)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def _draw_gradient_rect(
    draw: ImageDraw.ImageDraw,
    x0: int, y0: int, x1: int, y1: int,
    color_left: tuple[int, int, int],
    color_right: tuple[int, int, int],
) -> None:
    """Gradiente horizontal en un rectangulo."""
    for x in range(x0, x1):
        t = (x - x0) / max(x1 - x0 - 1, 1)
        r = int(color_left[0] + (color_right[0] - color_left[0]) * t)
        g = int(color_left[1] + (color_right[1] - color_left[1]) * t)
        b = int(color_left[2] + (color_right[2] - color_left[2]) * t)
        draw.line([(x, y0), (x, y1)], fill=(r, g, b))


def _draw_rounded_rect(
    img: Image.Image,
    box: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int],
    alpha: int = 255,
) -> None:
    """Dibuja un rectangulo redondeado con alpha."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    d.rounded_rectangle(box, radius=radius, fill=(*fill, alpha))
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))


def _multiline_text_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    x: int,
    y: int,
    max_width: int,
    line_spacing: int = 10,
    align: str = "left",
) -> int:
    """
    Dibuja texto con wrapping manual. Devuelve la Y final tras el ultimo renglon.
    """
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    cursor_y = y
    for line in lines:
        if align == "center":
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
            draw.text((x - text_w // 2, cursor_y), line, font=font, fill=fill)
        else:
            draw.text((x, cursor_y), line, font=font, fill=fill)
        h = draw.textbbox((0, 0), line, font=font)[3]
        cursor_y += h + line_spacing

    return cursor_y


def _text_height(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    line_spacing: int = 10,
) -> int:
    """Calcula la altura total del texto con wrapping."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    total = 0
    for line in lines:
        h = draw.textbbox((0, 0), line, font=font)[3]
        total += h + line_spacing
    return max(total - line_spacing, 0)


def _paste_logo(
    img: Image.Image,
    logo: Image.Image,
    target_width: int,
    cx: int,
    cy: int,
    on_dark: bool = True,
) -> None:
    """
    Pega el logo centrado en (cx, cy) reescalando a target_width.

    El logo PNG es RGB sin canal alpha — tiene un fondo oscuro con patron
    de tablero de ajedrez baked-in. Creamos una mascara de luminosidad
    para extraer solo el contenido util (shield + texto).
    """
    ratio = target_width / logo.width
    new_h = int(logo.height * ratio)
    resized = logo.resize((target_width, new_h), Image.LANCZOS)

    # Recortar bounding box del contenido util del logo
    iw, ih = resized.size
    margin_x = int(iw * 0.12)
    margin_y = int(ih * 0.38)
    cropped = resized.crop((margin_x, margin_y, iw - margin_x, ih - margin_y))
    cw, ch = cropped.size

    x = cx - cw // 2
    y = cy - ch // 2

    # Convertir a RGBA y crear mascara de luminosidad
    # El fondo del logo tiene brillo ~15-47 (tablero ajedrez), contenido real >55
    if cropped.mode != "RGBA":
        cropped = cropped.convert("RGBA")

    gray = cropped.convert("L")

    if on_dark:
        # En fondo oscuro: umbral bajo, el tablero se funde con el fondo
        lo, hi = 40, 70
    else:
        # En fondo brillante (CTA azul): umbral alto para eliminar todo
        # el tablero. Solo pasa el contenido mas brillante del logo.
        lo, hi = 60, 95

    alpha = gray.point(
        lambda p: min(255, max(0, int((p - lo) * (255 / max(hi - lo, 1))))), "L"
    )
    alpha = alpha.filter(ImageFilter.GaussianBlur(1.2))

    r, g, b, _ = cropped.split()
    cropped_masked = Image.merge("RGBA", (r, g, b, alpha))

    # Compositar sobre el fondo
    base_rgba = img.convert("RGBA")
    logo_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    logo_layer.paste(cropped_masked, (x, y))

    result = Image.alpha_composite(base_rgba, logo_layer)
    img.paste(result.convert("RGB"))


def _draw_noise_texture(img: Image.Image, intensity: int = 8) -> None:
    """Agrega micro-textura sutil para profundidad."""
    import random
    pixels = img.load()
    w, h = img.size
    for _ in range(w * h // 20):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)
        r, g, b = pixels[x, y]
        delta = random.randint(-intensity, intensity)
        pixels[x, y] = (
            max(0, min(255, r + delta)),
            max(0, min(255, g + delta)),
            max(0, min(255, b + delta)),
        )


# ---------------------------------------------------------------------------
# Dataclasses de contenido
# ---------------------------------------------------------------------------

BulletType = str  # "check" | "cross" | "arrow" | "warning" | "star" | "number"

@dataclass
class Bullet:
    icon: BulletType
    text: str

@dataclass
class ContentSlide:
    title: str
    bullets: list[tuple[BulletType, str]] = field(default_factory=list)
    stat_number: str | None = None
    stat_label: str | None = None
    stat_sublabel: str | None = None
    highlight: str | None = None  # texto en caja destacada

@dataclass
class CarouselConfig:
    title: str
    subtitle: str
    content_slides: list[ContentSlide]
    cta_text: str = "Calcula tu IRPF gratis"
    cta_url: str = "impuestify.com/guia-fiscal"
    output_dir: str = "social_media/carruseles/carrusel"
    platform: str = "linkedin"  # "instagram" | "linkedin"


# ---------------------------------------------------------------------------
# Clase principal
# ---------------------------------------------------------------------------

class CarouselGenerator:
    """
    Genera carruseles de marca para Instagram (1080x1080) y LinkedIn (1080x1350).

    Args:
        platform: "instagram" o "linkedin"
        logo_path: ruta al PNG del logo (por defecto busca en frontend/public/images/)
    """

    PLATFORMS: dict[str, tuple[int, int]] = {
        "instagram": (1080, 1080),
        "linkedin":  (1080, 1350),
    }

    def __init__(
        self,
        platform: str = "linkedin",
        logo_path: str | None = None,
    ) -> None:
        if platform not in self.PLATFORMS:
            raise ValueError(f"platform debe ser 'instagram' o 'linkedin', no '{platform}'")
        self.platform = platform
        self.W, self.H = self.PLATFORMS[platform]

        # Buscar logo
        if logo_path is None:
            candidates = [
                Path(__file__).parents[2] / "frontend" / "public" / "images" / "logo-impuestify.png",
                Path("frontend/public/images/logo-impuestify.png"),
            ]
            logo_path = next((str(p) for p in candidates if p.exists()), None)

        if logo_path and Path(logo_path).exists():
            # Mantener RGBA para usar el canal alpha como mascara
            self._logo = Image.open(logo_path).convert("RGBA")
        else:
            self._logo = None

        # Tamaños de fuente segun plataforma
        scale = 1.0 if platform == "instagram" else 0.92
        self._fs_title    = int(64 * scale)
        self._fs_subtitle = int(36 * scale)
        self._fs_body     = int(30 * scale)
        self._fs_footer   = int(22 * scale)
        self._fs_stat     = int(140 * scale)
        self._fs_badge    = int(28 * scale)

        # Margenes
        self._mx = 80   # margen horizontal
        self._my = 70   # margen vertical

    # -----------------------------------------------------------------------
    # API publica
    # -----------------------------------------------------------------------

    def create_carousel(
        self,
        title: str,
        subtitle: str,
        content_slides: list[dict[str, Any]],
        cta_text: str = "Calcula tu IRPF gratis",
        cta_url: str = "impuestify.com/guia-fiscal",
        output_dir: str = "social_media/carruseles/carrusel",
    ) -> list[Path]:
        """
        Genera todas las slides del carrusel y las guarda en output_dir.

        Args:
            title: titulo del carrusel (slide cover)
            subtitle: subtitulo (slide cover)
            content_slides: lista de dicts con keys title, bullets, stat_number, etc.
            cta_text: texto del call-to-action (ultima slide)
            cta_url: URL del CTA
            output_dir: directorio de salida

        Returns:
            Lista de Path a los archivos PNG generados
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        slides_data = self._parse_content_slides(content_slides)
        total = len(slides_data) + 2  # cover + contenido + CTA
        generated: list[Path] = []

        # Slide 1: cover
        cover = self._render_cover(title, subtitle, slide_num=1, total=total)
        path = out / "slide_01.png"
        cover.save(path, "PNG", optimize=True)
        generated.append(path)

        # Slides de contenido
        for idx, slide_data in enumerate(slides_data, start=2):
            img = self._render_content_slide(slide_data, slide_num=idx, total=total)
            path = out / f"slide_{idx:02d}.png"
            img.save(path, "PNG", optimize=True)
            generated.append(path)

        # Ultima slide: CTA
        cta_img = self._render_cta(cta_text, cta_url)
        path = out / f"slide_{total:02d}.png"
        cta_img.save(path, "PNG", optimize=True)
        generated.append(path)

        # PDF para LinkedIn
        if self.platform == "linkedin":
            pdf_path = out / "carrusel.pdf"
            imgs = [Image.open(p).convert("RGB") for p in generated]
            imgs[0].save(
                pdf_path,
                "PDF",
                save_all=True,
                append_images=imgs[1:],
                resolution=150,
            )
            print(f"  PDF: {pdf_path}")

        print(f"Carrusel generado: {out} ({len(generated)} slides)")
        return generated

    def create_stat_slide(
        self,
        number: str,
        label: str,
        sublabel: str = "",
        output_path: str = "social_media/stats/stat.png",
    ) -> Path:
        """
        Genera una slide de estadistica con numero grande centrado.

        Args:
            number: valor destacado, ej "600+" o "73%"
            label: texto descriptivo bajo el numero
            sublabel: texto secundario opcional
            output_path: ruta de salida

        Returns:
            Path al archivo PNG generado
        """
        slide = ContentSlide(
            title="",
            stat_number=number,
            stat_label=label,
            stat_sublabel=sublabel,
        )
        img = self._render_stat_slide(slide)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out, "PNG", optimize=True)
        return out

    # -----------------------------------------------------------------------
    # Parsing
    # -----------------------------------------------------------------------

    def _parse_content_slides(
        self, raw: list[dict[str, Any]]
    ) -> list[ContentSlide]:
        result = []
        for item in raw:
            bullets = []
            for b in item.get("bullets", []):
                if isinstance(b, (list, tuple)) and len(b) == 2:
                    bullets.append((str(b[0]), str(b[1])))
                elif isinstance(b, dict):
                    bullets.append((b.get("icon", "arrow"), b.get("text", "")))
            result.append(ContentSlide(
                title=item.get("title", ""),
                bullets=bullets,
                stat_number=item.get("stat_number"),
                stat_label=item.get("stat_label"),
                stat_sublabel=item.get("stat_sublabel"),
                highlight=item.get("highlight"),
            ))
        return result

    # -----------------------------------------------------------------------
    # Canvas base
    # -----------------------------------------------------------------------

    def _new_canvas(self) -> Image.Image:
        img = Image.new("RGB", (self.W, self.H))
        _draw_gradient(img, Colors.SECONDARY, Colors.GRAY800)
        return img

    def _new_canvas_primary(self) -> Image.Image:
        img = Image.new("RGB", (self.W, self.H))
        _draw_gradient(img, Colors.PRIMARY_DARK, Colors.ACCENT)
        return img

    def _add_decorative_elements(self, img: Image.Image) -> None:
        """Agrega circulo decorativo semi-transparente y linea accent."""
        draw = ImageDraw.Draw(img)

        # Circulo grande decorativo en esquina superior derecha
        cx, cy = self.W + 150, -150
        r = 450
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=(*Colors.PRIMARY_LIGHT, 25),
            width=2,
        )
        od.ellipse(
            [cx - r + 40, cy - r + 40, cx + r - 40, cy + r - 40],
            outline=(*Colors.ACCENT, 15),
            width=1,
        )
        img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))

        # Linea accent en header
        draw.rectangle([0, 0, self.W, 6], fill=Colors.ACCENT)

        # Linea sutil en footer
        draw.rectangle([self._mx, self.H - self._my - 2, self.W - self._mx, self.H - self._my], fill=Colors.GRAY700)

    def _draw_footer(self, draw: ImageDraw.ImageDraw, img: Image.Image) -> None:
        """Footer: logo mini + impuestify.com a la izquierda, icono a la derecha."""
        font_footer = _load_font(self._fs_footer)
        font_footer_b = _load_font(self._fs_footer, bold=True)

        y_footer = self.H - self._my + 12

        # Logo mini en footer
        if self._logo:
            logo_w = 110
            _paste_logo(img, self._logo, logo_w, self._mx + logo_w // 2 + 10, y_footer + 12)
            draw.text(
                (self._mx + logo_w + 24, y_footer + 4),
                "impuestify.com",
                font=font_footer,
                fill=Colors.GRAY400,
            )
        else:
            draw.text(
                (self._mx, y_footer + 4),
                "impuestify.com",
                font=font_footer_b,
                fill=Colors.ACCENT,
            )

    # -----------------------------------------------------------------------
    # Slide: Cover
    # -----------------------------------------------------------------------

    def _render_cover(
        self, title: str, subtitle: str, slide_num: int, total: int
    ) -> Image.Image:
        img = self._new_canvas()
        self._add_decorative_elements(img)
        draw = ImageDraw.Draw(img)

        # Logo centrado arriba
        logo_y = self._my + 70
        if self._logo:
            _paste_logo(img, self._logo, 220, self.W // 2, logo_y)

        # Linea separadora debajo del logo
        sep_y = logo_y + 100
        _draw_gradient_rect(
            draw,
            self.W // 2 - 180, sep_y,
            self.W // 2 + 180, sep_y + 3,
            Colors.PRIMARY,
            Colors.ACCENT,
        )

        # Titulo grande
        font_title = _load_font(self._fs_title, bold=True)
        font_sub   = _load_font(self._fs_subtitle)

        title_y = sep_y + 28
        text_w = self.W - self._mx * 2
        title_h = _text_height(draw, title, font_title, text_w, line_spacing=14)

        # Calcular bloque total para centrar verticalmente en la zona media
        zone_top = sep_y + 28
        zone_bot = self.H - self._my - 90  # encima del footer
        total_h = title_h + 30 + 40 + 20 + 40  # titulo + gap + accent line + gap + subtitle
        start_y = zone_top + (zone_bot - zone_top - total_h) // 2

        # Titulo
        end_y = _multiline_text_wrapped(
            draw, title, font_title, Colors.WHITE,
            self.W // 2, start_y, text_w,
            line_spacing=14, align="center",
        )

        # Linea accent bajo el titulo
        line_y = end_y + 18
        _draw_gradient_rect(
            draw,
            self.W // 2 - 120, line_y,
            self.W // 2 + 120, line_y + 4,
            Colors.ACCENT,
            Colors.PRIMARY_LIGHT,
        )

        # Subtitulo
        sub_y = line_y + 22
        _multiline_text_wrapped(
            draw, subtitle, font_sub, Colors.ACCENT,
            self.W // 2, sub_y, text_w,
            line_spacing=10, align="center",
        )

        # "Desliza →" en footer
        font_nav = _load_font(self._fs_footer)
        nav_text = "Desliza  →"
        bbox = draw.textbbox((0, 0), nav_text, font=font_nav)
        nav_w = bbox[2] - bbox[0]
        draw.text(
            (self.W - self._mx - nav_w, self.H - self._my + 12),
            nav_text,
            font=font_nav,
            fill=Colors.GRAY400,
        )

        self._draw_footer(draw, img)
        return img

    # -----------------------------------------------------------------------
    # Slide: Contenido con bullets
    # -----------------------------------------------------------------------

    def _render_content_slide(
        self, slide: ContentSlide, slide_num: int, total: int
    ) -> Image.Image:
        """Decide entre stat slide y bullet slide segun contenido."""
        if slide.stat_number:
            return self._render_stat_slide(slide, slide_num=slide_num, total=total)
        return self._render_bullet_slide(slide, slide_num=slide_num, total=total)

    def _render_bullet_slide(
        self,
        slide: ContentSlide,
        slide_num: int = 0,
        total: int = 0,
    ) -> Image.Image:
        img = self._new_canvas()
        self._add_decorative_elements(img)
        draw = ImageDraw.Draw(img)

        # Badge numerado (esquina superior derecha)
        if slide_num:
            self._draw_slide_badge(draw, slide_num, total)

        # Titulo
        font_title = _load_font(self._fs_title - 6, bold=True)
        font_body  = _load_font(self._fs_body)

        text_w = self.W - self._mx * 2
        title_y = self._my + 30

        end_y = _multiline_text_wrapped(
            draw, slide.title, font_title, Colors.WHITE,
            self._mx, title_y, text_w - 80,
            line_spacing=12,
        )

        # Linea bajo titulo
        sep_y = end_y + 14
        draw.rectangle([self._mx, sep_y, self._mx + 60, sep_y + 4], fill=Colors.ACCENT)

        # Caja de highlight si existe
        bullet_start_y = sep_y + 30
        if slide.highlight:
            bullet_start_y = self._draw_highlight_box(img, draw, slide.highlight, bullet_start_y)
            bullet_start_y += 20

        # Distribucion vertical uniforme de bullets
        # Espacio disponible: desde bullet_start_y hasta encima del footer
        footer_top = self.H - self._my - 10
        available_h = footer_top - bullet_start_y

        if slide.bullets:
            n = len(slide.bullets)

            # Calcular la altura real de cada bullet
            bullet_heights: list[int] = []
            for icon, text in slide.bullets:
                avail_w = text_w - 55 - 20
                th = _text_height(draw, text, font_body, avail_w, line_spacing=8)
                bh = max(th + 4, 52)  # minimo 52px (igual que _draw_bullet)
                bullet_heights.append(bh)

            total_bullets_h = sum(bullet_heights)

            if n == 1:
                # Un solo bullet: centrarlo
                gap = 0
                start_offset = (available_h - bullet_heights[0]) // 2
            elif total_bullets_h >= available_h:
                # No cabe con margen: apretar uniformemente sin gap
                gap = max(4, (available_h - total_bullets_h) // max(n - 1, 1))
                start_offset = 0
            else:
                # Distribuir con espacio uniforme entre bullets
                slack = available_h - total_bullets_h
                # Limitar gap a 60px para evitar demasiado espacio con pocos bullets
                gap = min(60, slack // max(n - 1, 1))
                # Centrar el bloque entero verticalmente
                block_h = total_bullets_h + gap * (n - 1)
                start_offset = (available_h - block_h) // 2

            bullet_y = bullet_start_y + start_offset
            for i, (icon, text) in enumerate(slide.bullets):
                end_y = self._draw_bullet(draw, img, icon, text, bullet_y, font_body, text_w)
                draw = ImageDraw.Draw(img)  # _draw_bullet puede regenerar el draw
                bullet_y = bullet_y + bullet_heights[i] + gap

        self._draw_footer(draw, img)
        return img

    def _draw_slide_badge(
        self, draw: ImageDraw.ImageDraw, num: int, total: int
    ) -> None:
        """Circulo con numero de slide en esquina superior derecha."""
        r = 36
        cx = self.W - self._mx - r + 20
        cy = self._my + r + 8
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=Colors.ACCENT,
        )
        font_badge = _load_font(self._fs_badge, bold=True)
        text = str(num)
        bbox = draw.textbbox((0, 0), text, font=font_badge)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            (cx - tw // 2, cy - th // 2 - 2),
            text,
            font=font_badge,
            fill=Colors.SECONDARY,
        )

    def _draw_highlight_box(
        self,
        img: Image.Image,
        draw: ImageDraw.ImageDraw,
        text: str,
        y: int,
    ) -> int:
        """Caja con fondo accent semi-transparente para texto destacado."""
        font = _load_font(self._fs_body - 2)
        text_w = self.W - self._mx * 2 - 40
        h = _text_height(draw, text, font, text_w, line_spacing=8) + 30
        box = (self._mx, y, self.W - self._mx, y + h)
        _draw_rounded_rect(img, box, radius=12, fill=Colors.PRIMARY, alpha=90)
        draw = ImageDraw.Draw(img)
        _multiline_text_wrapped(
            draw, text, font, Colors.WHITE,
            self._mx + 20, y + 14, text_w,
            line_spacing=8,
        )
        return y + h

    BULLET_COLORS: dict[str, tuple[int, int, int]] = {
        "check":   Colors.SUCCESS,
        "cross":   Colors.ERROR,
        "arrow":   Colors.ACCENT,
        "warning": Colors.WARNING,
        "star":    Colors.WARNING,
        "number":  Colors.PRIMARY_LIGHT,
        "info":    Colors.ACCENT,
    }

    def _draw_bullet_icon(
        self,
        img: Image.Image,
        icon: str,
        icon_color: tuple[int, int, int],
        cx: int,
        cy: int,
        r: int,
    ) -> None:
        """Dibuja el icono geometrico de un bullet centrado en (cx, cy)."""
        # Circulo de fondo semi-transparente
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(*icon_color, 35),
        )
        img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))

        draw = ImageDraw.Draw(img)
        lw = max(2, r // 5)  # grosor de linea proporcional al radio

        if icon == "check":
            # Checkmark: V con punta izquierda baja, punta media y brazo derecho largo
            x0, y0 = cx - r // 2, cy
            xm, ym = cx - r // 8, cy + r // 2
            x1, y1 = cx + r // 2, cy - r // 2
            draw.line([x0, y0, xm, ym, x1, y1], fill=icon_color, width=lw)

        elif icon == "cross":
            # X: dos lineas diagonales
            pad = r // 2
            draw.line([cx - pad, cy - pad, cx + pad, cy + pad], fill=icon_color, width=lw)
            draw.line([cx + pad, cy - pad, cx - pad, cy + pad], fill=icon_color, width=lw)

        elif icon == "arrow":
            # Flecha →: linea horizontal + punta triangular derecha
            tail_x = cx - r // 2
            head_x = cx + r // 2
            draw.line([tail_x, cy, head_x, cy], fill=icon_color, width=lw)
            tip = r // 3
            draw.polygon(
                [head_x, cy, head_x - tip, cy - tip, head_x - tip, cy + tip],
                fill=icon_color,
            )

        elif icon == "warning":
            # Triangulo con ! dentro
            pad = r // 2
            pts = [cx, cy - pad, cx - pad, cy + pad // 2, cx + pad, cy + pad // 2]
            draw.polygon(pts, outline=icon_color, width=lw)
            # Punto de exclamacion
            draw.line([cx, cy - pad // 4, cx, cy + pad // 4 - 2], fill=icon_color, width=lw)
            draw.ellipse([cx - 1, cy + pad // 4, cx + 1, cy + pad // 4 + 2], fill=icon_color)

        elif icon == "star":
            # Circulo relleno amarillo (estrella simplificada)
            star_r = r // 2
            draw.ellipse(
                [cx - star_r, cy - star_r, cx + star_r, cy + star_r],
                fill=icon_color,
            )

        elif icon in ("number", "info"):
            # Punto/circulo relleno azul
            dot_r = r // 3
            draw.ellipse(
                [cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r],
                fill=icon_color,
            )

        else:
            # Fallback: circulo relleno
            dot_r = r // 3
            draw.ellipse(
                [cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r],
                fill=icon_color,
            )

    def _draw_bullet(
        self,
        draw: ImageDraw.ImageDraw,
        img: Image.Image,
        icon: str,
        text: str,
        y: int,
        font: ImageFont.FreeTypeFont,
        text_w: int,
    ) -> int:
        """Dibuja un bullet point. Devuelve la Y tras el bullet."""
        icon_color = self.BULLET_COLORS.get(icon, Colors.PRIMARY_LIGHT)

        icon_cx = self._mx + 22
        icon_cy = y + 22
        icon_r = 20

        self._draw_bullet_icon(img, icon, icon_color, icon_cx, icon_cy, icon_r)
        draw = ImageDraw.Draw(img)

        # Texto del bullet
        text_x = self._mx + 55
        avail_w = text_w - 55 - 20
        end_y = _multiline_text_wrapped(
            draw, text, font, Colors.WHITE,
            text_x, y + 4, avail_w,
            line_spacing=8,
        )
        return max(end_y, y + 52)

    # -----------------------------------------------------------------------
    # Slide: Stat
    # -----------------------------------------------------------------------

    def _render_stat_slide(
        self,
        slide: ContentSlide,
        slide_num: int = 0,
        total: int = 0,
    ) -> Image.Image:
        img = self._new_canvas()
        self._add_decorative_elements(img)
        draw = ImageDraw.Draw(img)

        if slide_num:
            self._draw_slide_badge(draw, slide_num, total)

        font_stat  = _load_font(self._fs_stat, bold=True)
        font_label = _load_font(self._fs_subtitle, bold=False)
        font_sub   = _load_font(self._fs_body - 4)
        text_w = self.W - self._mx * 2

        # Medir altura de todos los bloques para centrar verticalmente
        number = slide.stat_number or ""
        stat_bbox = draw.textbbox((0, 0), number, font=font_stat)
        stat_h = int((stat_bbox[3] - stat_bbox[1]) * 1.45)  # compensar ascenders/descenders en fuentes grandes
        stat_w = stat_bbox[2] - stat_bbox[0]

        title_h = 0
        if slide.title:
            font_title = _load_font(self._fs_title - 8, bold=True)
            title_h = _text_height(draw, slide.title, font_title, text_w, 12)

        label_h = 0
        if slide.stat_label:
            label_h = _text_height(draw, slide.stat_label, font_label, text_w, 8)

        sub_h = 0
        if slide.stat_sublabel:
            sub_h = _text_height(draw, slide.stat_sublabel, font_sub, text_w, 8)

        # Espaciados entre bloques
        gap_title_stat = 50 if title_h else 0
        gap_stat_label = 30
        gap_label_sub = 20 if sub_h else 0

        total_block = (
            title_h + gap_title_stat +
            stat_h + gap_stat_label +
            label_h + gap_label_sub + sub_h
        )

        # Centrar el bloque completo verticalmente
        start_y = (self.H - total_block) // 2
        cursor_y = start_y

        # Titulo
        if slide.title:
            _multiline_text_wrapped(
                draw, slide.title, font_title, Colors.WHITE,
                self.W // 2, cursor_y, text_w, 12, align="center",
            )
            cursor_y += title_h + gap_title_stat

        # Numero grande
        nx = (self.W - stat_w) // 2
        draw.text((nx + 3, cursor_y + 3), number, font=font_stat, fill=(6, 50, 80))
        draw.text((nx, cursor_y), number, font=font_stat, fill=Colors.WHITE)
        cursor_y += stat_h + gap_stat_label

        # Label
        if slide.stat_label:
            _multiline_text_wrapped(
                draw, slide.stat_label, font_label, Colors.ACCENT,
                self.W // 2, cursor_y, text_w, 8, align="center",
            )
            cursor_y += label_h + gap_label_sub

        # Sublabel
        if slide.stat_sublabel:
            _multiline_text_wrapped(
                draw, slide.stat_sublabel, font_sub, Colors.GRAY400,
                self.W // 2, cursor_y, text_w, 8, align="center",
            )

        self._draw_footer(draw, img)
        return img

    # -----------------------------------------------------------------------
    # Slide: CTA
    # -----------------------------------------------------------------------

    def _render_cta(self, cta_text: str, cta_url: str) -> Image.Image:
        img = self._new_canvas_primary()
        draw = ImageDraw.Draw(img)

        # Elementos decorativos sobre gradiente primary
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.ellipse([-100, -100, 500, 500], outline=(255, 255, 255, 20), width=2)
        od.ellipse([self.W - 400, self.H - 400, self.W + 100, self.H + 100],
                   outline=(255, 255, 255, 15), width=2)
        img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))
        draw = ImageDraw.Draw(img)

        font_cta  = _load_font(self._fs_title, bold=True)
        font_url  = _load_font(self._fs_subtitle, bold=True)
        font_tag  = _load_font(self._fs_body)

        text_w = self.W - self._mx * 2
        cta_h = _text_height(draw, cta_text, font_cta, text_w, 14)
        logo_h = 130 if self._logo else 0
        total_block = logo_h + 30 + cta_h + 40 + 60 + 30 + 40
        start_y = (self.H - total_block) // 2

        # Logo centrado (on_dark=False porque el fondo CTA es azul brillante)
        if self._logo:
            _paste_logo(img, self._logo, 200, self.W // 2, start_y + logo_h // 2, on_dark=False)
            draw = ImageDraw.Draw(img)

        # Texto CTA
        text_y = start_y + logo_h + 30
        end_y = _multiline_text_wrapped(
            draw, cta_text, font_cta, Colors.WHITE,
            self.W // 2, text_y, text_w, 14, align="center",
        )

        # Caja URL
        box_y = end_y + 30
        box_h = 68
        box_pad = 50
        url_bbox = draw.textbbox((0, 0), cta_url, font=font_url)
        url_w = url_bbox[2] - url_bbox[0]
        box_x0 = (self.W - url_w - box_pad * 2) // 2
        box_x1 = box_x0 + url_w + box_pad * 2

        # Caja blanca redondeada
        overlay2 = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od2 = ImageDraw.Draw(overlay2)
        od2.rounded_rectangle(
            [box_x0, box_y, box_x1, box_y + box_h],
            radius=34,
            fill=(255, 255, 255, 230),
        )
        img.paste(Image.alpha_composite(img.convert("RGBA"), overlay2).convert("RGB"))
        draw = ImageDraw.Draw(img)

        draw.text(
            (self.W // 2 - url_w // 2, box_y + (box_h - (url_bbox[3] - url_bbox[1])) // 2),
            cta_url,
            font=font_url,
            fill=Colors.PRIMARY_DARK,
        )

        # Tag "Link en bio"
        tag_y = box_y + box_h + 28
        tag_text = "🔗 Link en bio"
        tag_bbox = draw.textbbox((0, 0), tag_text, font=font_tag)
        tag_w = tag_bbox[2] - tag_bbox[0]
        draw.text(
            ((self.W - tag_w) // 2, tag_y),
            tag_text,
            font=font_tag,
            fill=(255, 255, 255, 200) if False else Colors.WHITE,
        )

        return img


# ---------------------------------------------------------------------------
# Generacion de los 4 carruseles del plan social media
# ---------------------------------------------------------------------------

def _generate_l2_deducciones_autonomos(gen: CarouselGenerator) -> None:
    """L2: 7 deducciones que el 90% de autónomos no conoce."""
    gen.create_carousel(
        title="7 deducciones que el 90% de autónomos no conoce",
        subtitle="Guía completa para reducir tu factura fiscal",
        content_slides=[
            {
                "title": "1. Gastos de suministros",
                "bullets": [
                    ("check", "Luz, agua, gas e internet de tu vivienda"),
                    ("check", "30% del espacio dedicado a trabajo"),
                    ("arrow", "Requiere afectación parcial del inmueble"),
                    ("warning", "Documenta con planos y factura del autónomo"),
                ],
            },
            {
                "title": "2. Seguro de salud privado",
                "bullets": [
                    ("check", "Hasta 500 EUR por persona al año"),
                    ("check", "Incluye cónyuge e hijos menores de 25"),
                    ("check", "Deducible directamente en rendimientos"),
                    ("warning", "Solo para autónomos persona física"),
                ],
            },
            {
                "title": "3. Dietas y gastos de manutención",
                "bullets": [
                    ("check", "Hasta 26,67 EUR/día en España"),
                    ("check", "Hasta 48,08 EUR/día en extranjero"),
                    ("arrow", "Exige desplazamiento fuera del municipio"),
                    ("warning", "Necesitas factura y justificación del viaje"),
                ],
            },
            {
                "title": "4. Vehículo y gastos de transporte",
                "bullets": [
                    ("check", "Amortización del vehículo afecto a actividad"),
                    ("check", "Combustible, ITV, seguros, reparaciones"),
                    ("arrow", "Uso exclusivo para la actividad (ideal)"),
                    ("warning", "Uso mixto: solo la parte proporcional"),
                ],
            },
            {
                "title": "5. Formacion y desarrollo profesional",
                "bullets": [
                    ("check", "Cursos, masters y certificaciones"),
                    ("check", "Libros, suscripciones y software profesional"),
                    ("check", "Asistencia a congresos y eventos del sector"),
                    ("arrow", "Debe tener relación directa con tu actividad"),
                ],
            },
            {
                "title": "6. Cuotas profesionales y colegios",
                "bullets": [
                    ("check", "Cuota de autónomos (RETA) 100% deducible"),
                    ("check", "Colegio profesional si es obligatorio"),
                    ("check", "Asociaciones y sindicatos profesionales"),
                    ("arrow", "También la mutualidad alternativa al RETA"),
                ],
            },
            {
                "title": "7. Amortización de equipos",
                "bullets": [
                    ("check", "Ordenadores, monitores, impresoras"),
                    ("check", "Móviles y tablets usados para el negocio"),
                    ("check", "Mobiliario de oficina en casa"),
                    ("arrow", "Libertad de amortización para empresas de reducida dimensión"),
                ],
            },
            {
                "title": "Cuánto puedes ahorrarte",
                "stat_number": "3.200€",
                "stat_label": "ahorro medio anual aplicando todas las deducciones",
                "stat_sublabel": "Según simulaciones de Impuestify con perfil autónomo medio",
            },
        ],
        cta_text="Descubre todas tus deducciones",
        cta_url="impuestify.com/guia-fiscal",
        output_dir="social_media/carruseles/L2_deducciones_autonomos",
    )


def _generate_l4_guia_irpf(gen: CarouselGenerator) -> None:
    """L4: Guia IRPF en 8 pasos."""
    gen.create_carousel(
        title="Guía IRPF en 8 pasos",
        subtitle="Todo lo que necesitas saber para hacer la renta bien",
        content_slides=[
            {
                "title": "Paso 1: Rendimientos del trabajo",
                "bullets": [
                    ("arrow", "Suma todas las nóminas, pensiones y prestaciones"),
                    ("check", "Aplica la reducción por rendimientos del trabajo"),
                    ("check", "Resta las cotizaciones a la Seguridad Social"),
                    ("info", "Casillas 001 a 014 del modelo 100"),
                ],
            },
            {
                "title": "Paso 2: Rendimientos del capital",
                "bullets": [
                    ("arrow", "Capital inmobiliario: alquileres percibidos"),
                    ("arrow", "Capital mobiliario: dividendos, intereses, seguros"),
                    ("check", "Inmobiliario: deduce el 60% por alquiler habitual"),
                    ("warning", "Inmueble vacío: imputación de rentas del 2%"),
                ],
            },
            {
                "title": "Paso 3: Ganancias y pérdidas patrimoniales",
                "bullets": [
                    ("arrow", "Venta de acciones, fondos, inmuebles o criptos"),
                    ("check", "Se integran en la base del ahorro"),
                    ("check", "Compensación de pérdidas con ganancias (4 años)"),
                    ("warning", "FIFO obligatorio para acciones identicas"),
                ],
            },
            {
                "title": "Paso 4: Base imponible general y del ahorro",
                "bullets": [
                    ("arrow", "Base general: trabajo + inmobiliario + actividades"),
                    ("arrow", "Base ahorro: capital mobiliario + ganancias"),
                    ("check", "Se gravan a tipos distintos"),
                    ("info", "Base ahorro: 19% hasta 6.000 € / 21% hasta 50.000 € / 23% hasta 200.000 € / 27% más"),
                ],
            },
            {
                "title": "Paso 5: Reducciones de la base imponible",
                "bullets": [
                    ("check", "Plan de pensiones: hasta 1.500 EUR/año"),
                    ("check", "Empresa: aportación empresa hasta 8.500 EUR"),
                    ("check", "Tributación conjunta: 3.400 EUR"),
                    ("arrow", "Reducciones por discapacidad y dependencia"),
                ],
            },
            {
                "title": "Paso 6: Cuota íntegra estatal y autonómica",
                "bullets": [
                    ("arrow", "Se aplica la escala progresiva de IRPF"),
                    ("check", "Escala estatal + escala de tu CCAA"),
                    ("info", "Tipo marginal máximo: 47% estatal + auton."),
                    ("warning", "País Vasco y Navarra: tarifa foral propia"),
                ],
            },
            {
                "title": "Paso 7: Deducciones de la cuota",
                "bullets": [
                    ("check", "Inversión en vivienda habitual (pre-2013)"),
                    ("check", "Donaciones a ONG: 80% primeros 250 EUR"),
                    ("check", "Maternidad, familia numerosa, discapacidad"),
                    ("arrow", "Deducciones autonómicas adicionales por CCAA"),
                ],
            },
            {
                "title": "Paso 8: Resultado final de la declaración",
                "bullets": [
                    ("arrow", "Cuota liquida - retenciones - pagos a cuenta"),
                    ("check", "A devolver: Hacienda te reembolsa la diferencia"),
                    ("check", "A pagar: puedes fraccionar en 2 plazos (60/40)"),
                    ("info", "Fecha límite: 30 de junio de 2026"),
                ],
            },
        ],
        cta_text="Calcula tu resultado de la renta",
        cta_url="impuestify.com/guia-fiscal",
        output_dir="social_media/carruseles/L4_guia_irpf_8_pasos",
    )


def _generate_l7_errores_renta(gen: CarouselGenerator) -> None:
    """L7: 5 errores que cuestan dinero en la Renta."""
    gen.create_carousel(
        title="5 errores que cuestan dinero en la Renta",
        subtitle="Evitalos antes del 30 de junio",
        content_slides=[
            {
                "title": "Error 1: Aceptar el borrador sin revisar",
                "bullets": [
                    ("cross", "El borrador de Hacienda suele estar incompleto"),
                    ("cross", "No incluye deducciones autonómicas ni hipoteca"),
                    ("cross", "Puede faltar la reducción por alquiler del 60%"),
                    ("arrow", "Revísalo siempre antes de confirmar"),
                ],
            },
            {
                "title": "Error 2: No declarar criptomonedas",
                "bullets": [
                    ("cross", "Hacienda cruza datos con exchanges desde 2024"),
                    ("cross", "Sanción: 150€ a 250€ por información no declarada"),
                    ("check", "Todas las ventas y swaps son ganancias o pérdidas"),
                    ("arrow", "Usa el método FIFO obligatoriamente"),
                ],
            },
            {
                "title": "Error 3: Olvidar deducciones autonómicas",
                "bullets": [
                    ("cross", "Cada CCAA tiene sus propias deducciones exclusivas"),
                    ("cross", "Madrid: 20% guardia, 25% arrendamiento joven"),
                    ("cross", "Andalucía: inversión vivienda habitual"),
                    ("arrow", "Impuestify tiene 600+ deducciones por territorio"),
                ],
            },
            {
                "title": "Error 4: Ignorar la tributación conjunta",
                "bullets": [
                    ("cross", "No siempre es mejor declarar por separado"),
                    ("check", "Conjunta puede ahorrar miles si hay desigualdad de rentas"),
                    ("check", "Reducción de 3.400 EUR adicional"),
                    ("arrow", "Compara ambas opciones antes de decidir"),
                ],
            },
            {
                "title": "Error 5: No compensar pérdidas pasadas",
                "bullets": [
                    ("cross", "Las pérdidas de bolsa caducan a los 4 años"),
                    ("cross", "Muchos no saben que pueden aplicarlas"),
                    ("check", "Compensan ganancias patrimoniales y capital"),
                    ("arrow", "Revisa tus declaraciones de 2022 a 2025"),
                ],
            },
            {
                "title": "Cómo evitar todos estos errores",
                "bullets": [
                    ("check", "Usa el simulador IRPF de Impuestify antes de declarar"),
                    ("check", "Revisa las deducciones de tu CCAA específicas"),
                    ("check", "Consulta el calendario de fechas clave"),
                    ("arrow", "Empieza ahora: guía de 7 pasos gratuita"),
                ],
            },
        ],
        cta_text="Evita errores en tu declaración",
        cta_url="impuestify.com/guia-fiscal",
        output_dir="social_media/carruseles/L7_errores_renta",
    )


def _generate_l8_calendario_fiscal(gen: CarouselGenerator) -> None:
    """L8: Calendario fiscal 2026."""
    gen.create_carousel(
        title="Calendario fiscal 2026",
        subtitle="No te pierdas ninguna fecha clave",
        content_slides=[
            {
                "title": "Enero — Inicio del ejercicio",
                "bullets": [
                    ("arrow", "Modelo 303 (IVA 4T): hasta el 30 de enero"),
                    ("arrow", "Modelo 390 (resumen anual IVA): 30 enero"),
                    ("arrow", "Modelo 111/115 (retenciones 4T): 20 enero"),
                    ("info",  "Modelo 720: bienes en el extranjero (hasta 31 marzo)"),
                ],
            },
            {
                "title": "Abril — Comienza la Renta",
                "bullets": [
                    ("check", "1 abril: Hacienda habilita el borrador de IRPF"),
                    ("check", "Acceso a Renta Web desde la Sede Electrónica"),
                    ("arrow", "Primer trimestre IRPF: modelo 130/131"),
                    ("warning", "Fechas 1T: pagos fraccionados autónomos hasta 22 abril"),
                ],
            },
            {
                "title": "Mayo — Campaña de la Renta",
                "bullets": [
                    ("arrow", "Desde 6 mayo: atención por teléfono (plan Le Llamamos)"),
                    ("check", "Puedes modificar el borrador todas las veces que necesites"),
                    ("warning", "Primer plazo domiciliacion: hasta 25 junio"),
                    ("info",  "Modelos trimestrales: 303 (1T) hasta 20 mayo"),
                ],
            },
            {
                "title": "Junio — Fin de la Renta",
                "bullets": [
                    ("cross",   "30 junio: CIERRE de la campaña de la Renta 2025"),
                    ("warning", "A pagar con domiciliación: hasta 25 junio"),
                    ("check",   "A pagar sin domiciliación: hasta 30 junio"),
                    ("arrow",   "Fraccionamiento 60/40: segundo plazo 5 noviembre"),
                ],
            },
            {
                "title": "Julio — Verano fiscal",
                "bullets": [
                    ("arrow", "Modelo 303 (IVA 2T): hasta 20 julio"),
                    ("arrow", "Modelo 130/131 (2T IRPF): hasta 22 julio"),
                    ("check", "Rectificación de autoliquidaciones presentadas"),
                    ("info",  "Agosto: periodo de escasa actividad de la AEAT"),
                ],
            },
            {
                "title": "Octubre — Tercer trimestre",
                "bullets": [
                    ("arrow", "Modelo 303 (IVA 3T): hasta 20 octubre"),
                    ("arrow", "Modelo 130/131 (3T IRPF): hasta 22 octubre"),
                    ("check", "Modelo 111/115 (retenciones 3T): 20 octubre"),
                    ("warning", "Verificar pagos fraccionados sociedades (IS)"),
                ],
            },
            {
                "title": "Noviembre — Cierre del año",
                "bullets": [
                    ("arrow",   "5 noviembre: 2.° plazo fraccionamiento Renta 2025"),
                    ("check",   "Planificación fiscal de cierre de ejercicio"),
                    ("check",   "Aportaciones a plan de pensiones antes de 31 dic"),
                    ("warning", "Operaciones vinculadas: documentación obligatoria"),
                ],
            },
            {
                "title": "Diciembre — Cierre del ejercicio",
                "bullets": [
                    ("check",   "31 dic: último día para aportaciones a pensiones"),
                    ("check",   "31 dic: último día para donaciones deducibles"),
                    ("check",   "Revisar retenciones acumuladas del año"),
                    ("arrow",   "Preparar documentación para la Renta 2026"),
                ],
            },
            {
                "title": "Fechas clave resumidas",
                "bullets": [
                    ("check",   "1 abr: apertura Renta 2025"),
                    ("check",   "30 jun: cierre Renta 2025"),
                    ("check",   "20 ene/abr/jul/oct: IVA trimestral"),
                    ("check",   "22 ene/abr/jul/oct: IRPF autónomos"),
                ],
            },
            {
                "title": "No pierdas ninguna fecha",
                "stat_number": "58",
                "stat_label": "fechas fiscales clave en 2026",
                "stat_sublabel": "Activa alertas gratis en Impuestify",
            },
        ],
        cta_text="Activa tu calendario fiscal",
        cta_url="impuestify.com",
        output_dir="social_media/carruseles/L8_calendario_fiscal_2026",
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    base_dir = Path(__file__).parents[2]
    os.chdir(base_dir)

    print("=" * 60)
    print("CarouselGenerator — Impuestify")
    print("=" * 60)

    gen = CarouselGenerator(platform="linkedin")

    print("\n[1/4] L2: Deducciones autónomos...")
    _generate_l2_deducciones_autonomos(gen)

    print("\n[2/4] L4: Guía IRPF 8 pasos...")
    _generate_l4_guia_irpf(gen)

    print("\n[3/4] L7: Errores en la Renta...")
    _generate_l7_errores_renta(gen)

    print("\n[4/4] L8: Calendario fiscal 2026...")
    _generate_l8_calendario_fiscal(gen)

    print("\n" + "=" * 60)
    print("Todos los carruseles generados en social_media/carruseles/")
    print("=" * 60)
