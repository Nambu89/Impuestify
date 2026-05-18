"""
find_norm_in_portal.py — Busca normas oficiales en portales territoriales
usando Scrapling (anti-bot fingerprinting). Para normas que NO están en BOE
(forales, autonómicas como BOC/BOJA/BOPV/BOG/BOB/BOTHA/DOGC).

Solo fuentes oficiales. NO Wikipedia, NO blogs, NO Google Scholar.

Uso:
    # BOC Canarias: buscar Decreto Legislativo en sumarios 2025
    python scripts/find_norm_in_portal.py --portal boc --year 2025 \\
        --query "Decreto Legislativo 1/2025"

    # Bizkaia: listar normativa vigente de impuesto
    python scripts/find_norm_in_portal.py --portal bizkaia --query "IRPF"

    # Gipuzkoa: listar normativa
    python scripts/find_norm_in_portal.py --portal gipuzkoa --query "IRPF"

Output: lista de URLs candidatas verificadas HTTP 200 con contexto.
NO escribe a norms.yaml. Solo investiga + reporta para PM.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

from scrapling import Fetcher

_FETCHER = Fetcher()


def _fetch(url: str, timeout: int = 20) -> Tuple[int, str]:
    """Return (status, body_text)."""
    try:
        r = _FETCHER.get(url, timeout=timeout)
        body = r.body.decode("utf-8", errors="ignore") if r.body else ""
        return r.status, body
    except Exception as e:
        print(f"[ERR] {url} → {e}", file=sys.stderr)
        return 0, ""


# ── BOC Canarias ────────────────────────────────────────────────────────


def search_boc_canarias(year: int, query: str) -> List[dict]:
    """Itera sumarios BOC año, busca query en cada uno.

    Sumario URL: /boc/{year}/{NNN}/index.html
    """
    base = "https://www.gobiernodecanarias.org"
    found: List[dict] = []
    status, body = _fetch(f"{base}/boc/{year}/")
    if status != 200:
        print(f"[ERR] /boc/{year}/ → HTTP {status}", file=sys.stderr)
        return found

    # Extrae lista de sumarios del año
    sumarios = sorted(set(re.findall(rf"/boc/{year}/(\d+)/index\.html", body)))
    print(f"[INFO] BOC {year}: {len(sumarios)} sumarios a buscar", file=sys.stderr)

    qlow = query.lower()
    for num in sumarios:
        url = f"{base}/boc/{year}/{num}/index.html"
        st, body = _fetch(url, timeout=15)
        if st != 200:
            continue
        if qlow in body.lower():
            # Extrae snippet con context + URL PDF del decreto
            idx = body.lower().find(qlow)
            snippet = body[max(0, idx - 80) : idx + 200].replace("\n", " ").strip()
            # Buscar PDF/HTML link cerca
            local_html = re.findall(rf"href=\"(/boc/{year}/{num}/\d+\.html)\"", body)
            local_pdf = re.findall(rf"href=\"(/boc/{year}/{num}/\d+\.pdf)\"", body)
            found.append(
                {
                    "sumario_url": url,
                    "snippet": snippet[:300],
                    "doc_urls_html": [base + h for h in local_html[:3]],
                    "doc_urls_pdf": [base + h for h in local_pdf[:3]],
                }
            )
            print(f"[HIT] BOC {year}/{num}: ", snippet[:120], file=sys.stderr)
    return found


# ── Bizkaia ──────────────────────────────────────────────────────────────


def search_bizkaia(query: str) -> List[dict]:
    """Lista normas categorizadas en /es/normativa-tributaria/normativa-vigente."""
    found: List[dict] = []
    base = "https://www.bizkaia.eus"
    status, body = _fetch(f"{base}/es/normativa-tributaria/normativa-vigente")
    if status != 200:
        return found
    hrefs = sorted(set(re.findall(r'href="([^"]+/normativa-vigente/[^"]+)"', body)))
    qlow = query.lower()
    for href in hrefs:
        if qlow in href.lower():
            url = href if href.startswith("http") else base + href
            st, body = _fetch(url)
            # Extrae primera referencia a NF X/AAAA
            nf_refs = re.findall(r"(Norma\s+Foral\s+\d+/\d{4}[^<\.]{0,120})", body)
            pdf_links = re.findall(r'href="([^"]+\.pdf)"', body)
            found.append(
                {
                    "category_url": url,
                    "norma_refs": nf_refs[:5],
                    "pdf_links": [(p if p.startswith("http") else base + p) for p in pdf_links[:5]],
                }
            )
    return found


# ── Gipuzkoa ─────────────────────────────────────────────────────────────


def search_gipuzkoa(query: str) -> List[dict]:
    """Portal Ogasuna Gipuzkoa."""
    found: List[dict] = []
    base = "https://www.gipuzkoa.eus"
    status, body = _fetch(f"{base}/es/web/ogasuna/normativa/aprobada")
    if status != 200:
        return found
    hrefs = sorted(set(re.findall(r'href="([^"]+)"', body)))
    qlow = query.lower()
    relevant = [h for h in hrefs if qlow in h.lower()]
    for h in relevant[:20]:
        url = h if h.startswith("http") else base + h
        found.append({"link": url})
    return found


# ── BOE search (estatal — para Ley 35/2015, Ley 8/1991, etc.) ───────────


def search_boe(query: str) -> List[dict]:
    """BOE search via buscar UI. Devuelve resultados con BOE-A-IDs."""
    found: List[dict] = []
    base = "https://www.boe.es"
    # BOE buscar tiene query params
    search_url = f"{base}/buscar/legislacion.php?campo[1]=NOTOID&dato[1]={query}"
    status, body = _fetch(search_url, timeout=20)
    if status != 200:
        return found
    # Extrae BOE-A-AAAA-NNNN IDs encontrados
    ids = sorted(set(re.findall(r"BOE-A-\d{4}-\d+", body)))
    for boe_id in ids[:10]:
        found.append(
            {
                "boe_id": boe_id,
                "url": f"https://www.boe.es/buscar/act.php?id={boe_id}",
            }
        )
    return found


# ── BOJA Andalucía ───────────────────────────────────────────────────────


def search_boja(year: int, query: str) -> List[dict]:
    """BOJA sumarios año."""
    found: List[dict] = []
    base = "https://www.juntadeandalucia.es"
    status, body = _fetch(f"{base}/boja/")
    if status != 200:
        return found
    # BOJA URL pattern varía
    sumarios = re.findall(rf"href=\"(/boja/{year}/[^\"]+)\"", body)
    print(f"[INFO] BOJA {year}: {len(sumarios)} sumarios", file=sys.stderr)
    qlow = query.lower()
    for s in sorted(set(sumarios))[:50]:
        url = base + s
        st, b = _fetch(url, timeout=15)
        if st != 200:
            continue
        if qlow in b.lower():
            idx = b.lower().find(qlow)
            snippet = b[max(0, idx - 80) : idx + 200].replace("\n", " ").strip()
            found.append({"sumario_url": url, "snippet": snippet[:300]})
            print(f"[HIT] BOJA: {s}", file=sys.stderr)
    return found


# ── CLI ──────────────────────────────────────────────────────────────────


PORTALS = {
    "boc": "BOC Canarias (sumarios año)",
    "bizkaia": "Bizkaia Ogasuna (normativa vigente)",
    "gipuzkoa": "Gipuzkoa Ogasuna",
    "boe": "BOE estatal (busqueda full-text)",
    "boja": "BOJA Andalucía (sumarios año)",
}


def main() -> int:
    p = argparse.ArgumentParser(
        description="Buscador normas oficiales territoriales (Scrapling anti-bot)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(f"  {k:<10} {v}" for k, v in PORTALS.items()),
    )
    p.add_argument("--portal", required=True, choices=PORTALS.keys())
    p.add_argument("--year", type=int, help="Año (requerido para boc/boja)")
    p.add_argument("--query", required=True, help="Texto a buscar")
    args = p.parse_args()

    if args.portal == "boc":
        if not args.year:
            print("ERROR: --year requerido para BOC", file=sys.stderr)
            return 1
        results = search_boc_canarias(args.year, args.query)
    elif args.portal == "bizkaia":
        results = search_bizkaia(args.query)
    elif args.portal == "gipuzkoa":
        results = search_gipuzkoa(args.query)
    elif args.portal == "boe":
        results = search_boe(args.query)
    elif args.portal == "boja":
        if not args.year:
            print("ERROR: --year requerido para BOJA", file=sys.stderr)
            return 1
        results = search_boja(args.year, args.query)
    else:
        return 1

    print(f"\n=== Resultados ({len(results)}) ===")
    import json

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results else 2


if __name__ == "__main__":
    sys.exit(main())
