"""Detect recent BOE updates affecting norms already in our YAML.

NOT a bulk-import script (the BOE API does not list the entire current
corpus in one call — it only returns norms whose CONSOLIDATED text was
updated in the requested date range).

Useful workflow:
    1. Cron weekly: `python scripts/sync_boe_recent.py --days 7`
    2. Outputs a table: norms in `norms.yaml` whose consolidada has
       been updated in the last N days. Maintainer reviews and decides
       if our metadata needs refresh (e.g. vigent_until set when a law
       gets fully derogated by a newer one).

Output:
    --- Normas en YAML modificadas en BOE en los últimos 7 días ---
    [UPDATED] LIRPF   BOE-A-2006-20764  fecha_actualizacion=20260514
              Cambio: "Modificada por Ley X/2026..."

Exit codes:
    0 — sin cambios
    10 — cambios detectados (CI puede abrir issue/PR)

Future evolution: open an automated PR with proposed YAML changes.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.legal.loader import load_norms  # noqa: E402


async def fetch_recent_updates(days: int) -> list[dict]:
    """Fetch BOE consolidada updates in the last N days."""
    end = date.today()
    start = end - timedelta(days=days)
    url = (
        f"https://www.boe.es/datosabiertos/api/legislacion-consolidada"
        f"?from={start.strftime('%Y%m%d')}&to={end.strftime('%Y%m%d')}&limit=-1"
    )
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url, headers={"Accept": "application/xml"})
    if resp.status_code != 200:
        print(f"ERROR: BOE API HTTP {resp.status_code}", file=sys.stderr)
        return []
    body = resp.text
    # Quick-and-dirty XML parsing: enough for the list endpoint shape.
    items: list[dict] = []
    for m in re.finditer(r"<item>(.*?)</item>", body, re.DOTALL):
        chunk = m.group(1)
        item = {}
        for tag in ("identificador", "titulo", "fecha_actualizacion", "rango"):
            mt = re.search(rf"<{tag}[^>]*>([^<]+)</{tag}>", chunk)
            if mt:
                item[tag] = mt.group(1).strip()
        items.append(item)
    return items


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--days", type=int, default=7, help="Ventana en días hacia atrás (default: 7)"
    )
    args = parser.parse_args()

    catalog = load_norms()
    our_ids = {n.boe_id for n in catalog.norms if n.boe_id}
    sigla_by_id = {n.boe_id: n.sigla for n in catalog.norms if n.boe_id}

    print(f"Consultando BOE API para cambios en los últimos {args.days} días...\n")
    updates = asyncio.run(fetch_recent_updates(args.days))

    matching = [u for u in updates if u.get("identificador") in our_ids]
    print(f"Total normas con cambios en BOE: {len(updates)}")
    print(f"Que tengamos en norms.yaml:     {len(matching)}\n")

    if not matching:
        print("Sin cambios afectando nuestro catálogo.")
        return 0

    print("--- Normas en YAML modificadas en BOE ---")
    for item in matching:
        boe_id = item.get("identificador", "?")
        sigla = sigla_by_id.get(boe_id, "?")
        fecha = item.get("fecha_actualizacion", "?")
        titulo = (item.get("titulo") or "")[:80]
        print(f"[UPDATED] {sigla:<20} {boe_id:<25} {fecha}")
        print(f"          {titulo}...")
    return 10


if __name__ == "__main__":
    sys.exit(main())
