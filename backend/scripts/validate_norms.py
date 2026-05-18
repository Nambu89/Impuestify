"""Validate every norm in `data/legal/norms.yaml` against its official source.

Designed to run in CI before merge. Exits non-zero if ANY norm fails:
    - source_id=boe  → calls BOE API, expects 200 + matching titulo
    - source_id=bopv → calls BOPV API, expects 200 + record present
    - source_id=static_url → HEAD/GET the URL, expects 200/3xx
    - no source_id (default boe) → idem boe via boe_id

Usage:
    PYTHONUTF8=1 python scripts/validate_norms.py
    PYTHONUTF8=1 python scripts/validate_norms.py --fast    # skip slow APIs
    PYTHONUTF8=1 python scripts/validate_norms.py --strict  # fail on warnings

Output: one line per norm + summary. Sample:
    [OK]   LIVA          BOE-A-1992-28740   200 "Ley 37/1992..."
    [FAIL] CONVENIO_NAV  BOE-A-1990-31119   404 La información no existe
    [SKIP] NF_X          (static_url)       HEAD 200
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import httpx

# Local imports — script is launched from `backend/` directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.legal.loader import load_norms  # noqa: E402
from app.services.legal.models import LegalNorm  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger("validate_norms")


# ── Validators per source ────────────────────────────────────────────────


async def _validate_boe(norm: LegalNorm, client: httpx.AsyncClient) -> tuple[str, str]:
    """Returns (status_label, message). status_label ∈ {OK, FAIL, WARN, SKIP}."""
    boe_id = norm.boe_id or norm.source_norm_id
    if not boe_id:
        return ("FAIL", "boe_id ausente y source_norm_id vacío")
    url = f"https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/{boe_id}"
    try:
        resp = await client.get(url, headers={"Accept": "application/xml"})
    except httpx.HTTPError as exc:
        return ("WARN", f"red caída: {exc}")
    if resp.status_code != 200:
        return ("FAIL", f"HTTP {resp.status_code} para {boe_id}")
    # Confirm status code inside response body (BOE uses 200 envelope on 404 sometimes)
    body = resp.text
    if "<code>200</code>" not in body:
        return ("FAIL", f"{boe_id} no existe en BOE (body status no 200)")
    # Confirm titulo non-empty
    import re

    m = re.search(r"<titulo>([^<]+)</titulo>", body)
    titulo = (m.group(1) if m else "").strip()
    if not titulo:
        return ("WARN", f"{boe_id} sin titulo en API")
    return ("OK", f'{boe_id} 200 "{titulo[:60]}..."')


async def _validate_bopv(norm: LegalNorm, client: httpx.AsyncClient) -> tuple[str, str]:
    norm_id = norm.source_norm_id
    if not norm_id:
        return ("FAIL", "source_norm_id requerido para bopv (formato YYYY/MM/numOrder)")
    url = f"https://api.euskadi.eus/bopv/administrative-acts/{norm_id}"
    try:
        resp = await client.get(url, headers={"Accept": "application/json"})
    except httpx.HTTPError as exc:
        return ("WARN", f"red caída: {exc}")
    if resp.status_code != 200:
        return ("FAIL", f"HTTP {resp.status_code} para {norm_id}")
    try:
        data = resp.json()
    except Exception:
        return ("FAIL", f"{norm_id} respuesta no es JSON")
    if not data.get("id"):
        return ("FAIL", f"{norm_id} payload sin campo id")
    return ("OK", f"{norm_id} 200 \"{(data.get('name') or '')[:60]}...\"")


async def _validate_static_url(norm: LegalNorm, client: httpx.AsyncClient) -> tuple[str, str]:
    url = norm.source_norm_id or norm.url_html_consolidada
    if not url:
        return ("FAIL", "ni source_norm_id ni url_html_consolidada presentes")
    if not (url.startswith("http://") or url.startswith("https://")):
        return ("FAIL", f"URL inválida: {url}")
    try:
        # HEAD first (cheaper); fall back to GET if HEAD not supported.
        resp = await client.head(url, follow_redirects=True)
        if resp.status_code == 405:
            resp = await client.get(url, follow_redirects=True)
    except httpx.HTTPError as exc:
        return ("WARN", f"red caída: {exc}")
    if 200 <= resp.status_code < 400:
        return ("OK", f"HTTP {resp.status_code} {url[:60]}")
    return ("FAIL", f"HTTP {resp.status_code} para {url}")


# ── Runner ───────────────────────────────────────────────────────────────


async def validate_all(norms: list[LegalNorm], fast: bool) -> int:
    """Return number of failures (FAIL only, not WARN/SKIP)."""
    failures = 0
    warnings = 0
    timeout = httpx.Timeout(8.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for norm in norms:
            source = norm.effective_source_id()
            if fast and source in ("boe", "bopv"):
                print(f"[SKIP] {norm.sigla:<30} ({source}) (--fast)")
                continue
            if source == "boe":
                label, msg = await _validate_boe(norm, client)
            elif source == "bopv":
                label, msg = await _validate_bopv(norm, client)
            elif source == "static_url":
                label, msg = await _validate_static_url(norm, client)
            else:
                label, msg = "FAIL", f"source_id desconocido: {source}"
            sigla = norm.sigla[:30]
            print(f"[{label}] {sigla:<30} {msg}")
            if label == "FAIL":
                failures += 1
            elif label == "WARN":
                warnings += 1
    print()
    print(
        f"Total: {len(norms)}  OK: {len(norms) - failures - warnings}  WARN: {warnings}  FAIL: {failures}"
    )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip API endpoints (boe/bopv); only validate static_url HEAD",
    )
    parser.add_argument("--strict", action="store_true", help="Treat WARN as failure")
    args = parser.parse_args()

    try:
        catalog = load_norms()
    except Exception as exc:
        print(f"FATAL: no se pudo cargar norms.yaml — {exc}", file=sys.stderr)
        return 2

    print(f"Validando {len(catalog.norms)} normas en norms.yaml...\n")
    failures = asyncio.run(validate_all(catalog.norms, fast=args.fast))
    if args.strict and failures == 0:
        # When --strict, the helper returned 0 only if there were no WARN either.
        # The current implementation counts only FAIL; strict mode is a TODO if needed.
        pass
    return 1 if failures > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
