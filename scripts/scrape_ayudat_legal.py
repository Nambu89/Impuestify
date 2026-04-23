"""Scrape de las paginas legales de ayudatpymes.com con Scrapling.

Localiza y descarga: aviso legal, politica de privacidad, cookies y
terminos, guarda el HTML + markdown en docs/ayudat_legal_scrape/ para
analisis y benchmark del formato legal de Ayuda T Pymes.
"""

from __future__ import annotations

import re
from pathlib import Path

from scrapling import Fetcher


BASE = "https://ayudatpymes.com"
OUT = Path(__file__).resolve().parent.parent / "docs" / "ayudat_legal_scrape"
OUT.mkdir(parents=True, exist_ok=True)

fetcher = Fetcher()


def discover_legal_links() -> list[str]:
    """Descubre las URLs legales desde el footer del home."""
    res = fetcher.get(BASE, stealthy_headers=True)
    html = res.body if isinstance(res.body, str) else res.body.decode("utf-8", errors="ignore")
    # Busca cualquier href que contenga legal, privacidad, cookies, aviso, terminos, condiciones
    patterns = [r"legal", r"privacidad", r"cookies", r"aviso", r"terminos", r"condiciones"]
    links = set()
    for match in re.finditer(r'href="([^"]+)"', html):
        url = match.group(1)
        if any(p in url.lower() for p in patterns):
            if url.startswith("/"):
                url = BASE + url
            elif not url.startswith("http"):
                continue
            if "ayudatpymes.com" in url:
                links.add(url.split("#")[0].rstrip("/"))
    return sorted(links)


def scrape_page(url: str) -> tuple[str, str]:
    """Devuelve (titulo, texto_limpio)."""
    res = fetcher.get(url, stealthy_headers=True)
    html = res.body if isinstance(res.body, str) else res.body.decode("utf-8", errors="ignore")

    title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else url

    # Extrae solo contenido visible — elimina <script>, <style>, <nav>, <header>, <footer>
    for tag in ["script", "style", "nav", "header", "footer"]:
        html = re.sub(rf"<{tag}[^>]*>.*?</{tag}>", "", html, flags=re.IGNORECASE | re.DOTALL)

    # Extrae solo el <main>/<article> si existe, sino el body
    main_match = re.search(r"<(?:main|article)[^>]*>(.*?)</(?:main|article)>", html, re.IGNORECASE | re.DOTALL)
    content = main_match.group(1) if main_match else html

    # Elimina tags HTML residuales y deja solo texto plano
    text = re.sub(r"<[^>]+>", " ", content)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&[a-z]+;", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    return title, text


def slugify(url: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", url.lower()).strip("_")[-60:]


def main() -> None:
    print(f"Descubriendo paginas legales en {BASE}...")
    links = discover_legal_links()
    # Forzar candidatos conocidos comunes
    for extra in ["/aviso-legal", "/politica-de-privacidad", "/politica-de-cookies", "/terminos-y-condiciones", "/terminos", "/legal", "/privacidad", "/cookies"]:
        links.append(BASE + extra)
    links = sorted(set(links))
    print(f"Candidatos: {len(links)}")

    results = []
    for url in links:
        try:
            title, text = scrape_page(url)
            if len(text) < 500:
                print(f"  SKIP (poco contenido) {url}")
                continue
            slug = slugify(url)
            out_path = OUT / f"{slug}.txt"
            out_path.write_text(f"URL: {url}\nTITULO: {title}\n\n{text}\n", encoding="utf-8")
            print(f"  OK   {url}  -> {out_path.name}  ({len(text)} chars)")
            results.append((url, title, text))
        except Exception as exc:
            print(f"  FAIL {url}  -> {exc}")

    print(f"\nGuardados en {OUT}")
    print(f"Total paginas extraidas: {len(results)}")


if __name__ == "__main__":
    main()
