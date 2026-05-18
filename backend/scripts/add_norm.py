"""Add a new norm to `data/legal/norms.yaml` after live verification.

Hard rule: NEVER invent identifiers. The CLI fetches the official source
in real time, parses the response, and writes the entry with metadata
returned by the server. If the source rejects the identifier, the script
exits without writing anything.

Usage:

    # By BOE id (estatal):
    python scripts/add_norm.py --boe BOE-A-2022-17101 \\
                               --sigla LEY_22_2022_CONVENIO_NAV \\
                               --aliases "ley 22/2022"

    # By BOPV id (autonómico Euskadi):
    python scripts/add_norm.py --bopv 2024/12/5380 \\
                               --sigla DECRETO_X_2024 \\
                               --aliases "decreto 200/2024"

    # By raw URL (boletines sin API — el script verifica HTTP 200):
    python scripts/add_norm.py --url https://www.bizkaia.eus/... \\
                               --sigla NF_X_BIZKAIA \\
                               --full-id "Norma Foral 13/2013" \\
                               --name "IRPF de Bizkaia" \\
                               --vigent-from 2014-01-01 \\
                               --norm-type norma_foral

Por seguridad NO sobrescribe entradas existentes. Si la sigla ya existe
en norms.yaml → exit. Modifica el YAML manualmente para reemplazar.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

# Local imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.legal.loader import load_norms  # noqa: E402

NORMS_YAML = Path(__file__).resolve().parents[1] / "data" / "legal" / "norms.yaml"


# ── Verifiers ────────────────────────────────────────────────────────────


async def verify_boe(boe_id: str) -> dict:
    """Fetches the BOE consolidada API. Returns parsed metadata or raises."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/{boe_id}",
            headers={"Accept": "application/xml"},
        )
    if resp.status_code != 200:
        raise RuntimeError(f"BOE API HTTP {resp.status_code} for {boe_id}")
    body = resp.text
    if "<code>200</code>" not in body:
        raise RuntimeError(f"{boe_id} no existe en BOE (status no 200 en body)")

    def _x(tag: str) -> Optional[str]:
        m = re.search(rf"<{tag}>([^<]+)</{tag}>", body)
        return m.group(1).strip() if m else None

    titulo = _x("titulo") or ""
    fecha_disposicion = _x("fecha_disposicion")  # YYYYMMDD
    fecha_vigencia = _x("fecha_vigencia")
    url_html = _x("url_html_consolidada")
    full_id_match = re.search(r"^([^,]+),", titulo)
    full_id_guess = full_id_match.group(1).strip() if full_id_match else titulo[:50]
    return {
        "boe_id": boe_id,
        "titulo": titulo,
        "full_id": full_id_guess,
        "fecha_disposicion": _parse_yyyymmdd(fecha_disposicion),
        "fecha_vigencia": _parse_yyyymmdd(fecha_vigencia),
        "url_html": url_html or f"https://www.boe.es/buscar/act.php?id={boe_id}",
    }


async def verify_bopv(norm_id: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"https://api.euskadi.eus/bopv/administrative-acts/{norm_id}",
            headers={"Accept": "application/json"},
        )
    if resp.status_code != 200:
        raise RuntimeError(f"BOPV API HTTP {resp.status_code} for {norm_id}")
    data = resp.json()
    if not data.get("id"):
        raise RuntimeError(f"BOPV {norm_id} sin id en respuesta")
    return {
        "norm_id": data["id"],
        "titulo": data.get("name") or "",
        "fecha_disposicion": _iso_to_date(data.get("disposalDate")),
        "fecha_vigencia": _iso_to_date(data.get("publishDate")),
        "url_html": f"https://api.euskadi.eus/bopv/administrative-acts/{data['id']}",
    }


async def verify_url(url: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.head(url, follow_redirects=True)
            if resp.status_code == 405:
                resp = await client.get(url, follow_redirects=True)
        except httpx.HTTPError as exc:
            raise RuntimeError(f"URL no accesible: {exc}")
    if not (200 <= resp.status_code < 400):
        raise RuntimeError(f"URL devolvió HTTP {resp.status_code}")
    return {"url_html": url}


def _parse_yyyymmdd(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def _iso_to_date(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


# ── YAML writer ──────────────────────────────────────────────────────────


def _format_entry(entry: dict) -> str:
    """Serialize a norm entry as YAML preserving the file's style."""
    lines = [f"  - sigla: {entry['sigla']}"]
    lines.append(f"    full_id: {_q(entry['full_id'])}")
    lines.append(f"    name: {_q(entry['name'])}")
    lines.append(f"    norm_type: {entry['norm_type']}")
    lines.append(f"    vigent_from: \"{entry['vigent_from']}\"")
    lines.append(f"    vigent_until: {entry.get('vigent_until') or 'null'}")
    if entry.get("aliases"):
        lines.append("    aliases:")
        for a in entry["aliases"]:
            lines.append(f"      - {_q(a)}")
    if entry.get("boe_id"):
        lines.append(f"    boe_id: \"{entry['boe_id']}\"")
    if entry.get("source_id"):
        lines.append(f"    source_id: {entry['source_id']}")
    if entry.get("source_norm_id"):
        lines.append(f"    source_norm_id: {_q(entry['source_norm_id'])}")
    if entry.get("url_html"):
        lines.append(f"    url_html_consolidada: {_q(entry['url_html'])}")
    return "\n".join(lines)


def _q(s: str) -> str:
    """YAML-safe string quoting."""
    if any(ch in s for ch in ':#"\\\n'):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return f'"{s}"'


def _append_to_yaml(yaml_text: str) -> None:
    existing = NORMS_YAML.read_text(encoding="utf-8")
    if not existing.endswith("\n"):
        existing += "\n"
    existing += "\n" + yaml_text + "\n"
    NORMS_YAML.write_text(existing, encoding="utf-8")


def _sigla_exists(sigla: str) -> bool:
    catalog = load_norms()
    return any(n.sigla.upper() == sigla.upper() for n in catalog.norms)


# ── CLI ──────────────────────────────────────────────────────────────────


async def main_async(args) -> int:
    if _sigla_exists(args.sigla):
        print(
            f"ERROR: sigla '{args.sigla}' ya existe en norms.yaml. Edita manualmente o usa otra.",
            file=sys.stderr,
        )
        return 2

    if args.boe:
        try:
            data = await verify_boe(args.boe)
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 3
        entry = {
            "sigla": args.sigla,
            "full_id": args.full_id or data["full_id"],
            "name": args.name or data["titulo"],
            "norm_type": args.norm_type or "ley",
            "vigent_from": args.vigent_from or data["fecha_vigencia"] or data["fecha_disposicion"],
            "aliases": args.aliases or [],
            "boe_id": data["boe_id"],
            "url_html": data["url_html"],
        }
    elif args.bopv:
        try:
            data = await verify_bopv(args.bopv)
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 3
        if not args.full_id or not args.name:
            print(
                "ERROR: --full-id y --name son obligatorios para BOPV (la API no devuelve full_id).",
                file=sys.stderr,
            )
            return 4
        entry = {
            "sigla": args.sigla,
            "full_id": args.full_id,
            "name": args.name,
            "norm_type": args.norm_type or "ley",
            "vigent_from": args.vigent_from or data["fecha_vigencia"],
            "aliases": args.aliases or [],
            "source_id": "bopv",
            "source_norm_id": data["norm_id"],
            "url_html": data["url_html"],
        }
    elif args.url:
        try:
            data = await verify_url(args.url)
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 3
        if not all([args.full_id, args.name, args.vigent_from, args.norm_type]):
            print(
                "ERROR: --full-id, --name, --vigent-from y --norm-type obligatorios para --url",
                file=sys.stderr,
            )
            return 4
        entry = {
            "sigla": args.sigla,
            "full_id": args.full_id,
            "name": args.name,
            "norm_type": args.norm_type,
            "vigent_from": args.vigent_from,
            "aliases": args.aliases or [],
            "source_id": "static_url",
            "source_norm_id": data["url_html"],
            "url_html": data["url_html"],
        }
    else:
        print("ERROR: especifica una de --boe, --bopv o --url", file=sys.stderr)
        return 1

    yaml_text = _format_entry(entry)
    print("\n--- Nueva entrada (revisa antes de confirmar) ---")
    print(yaml_text)
    print()
    if not args.yes:
        answer = input("Añadir a norms.yaml? [y/N] ").strip().lower()
        if answer not in {"y", "yes", "s", "si", "sí"}:
            print("Cancelado.")
            return 0
    _append_to_yaml(yaml_text)
    print(f"OK: añadida sigla '{args.sigla}' a {NORMS_YAML.name}")
    print("Recuerda correr: python scripts/validate_norms.py")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--sigla", required=True, help="Identificador interno único en MAYÚSCULAS")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--boe", help="BOE-A-NNNN-NNNN")
    src.add_argument("--bopv", help="ID BOPV formato YYYY/MM/numOrder")
    src.add_argument("--url", help="URL completa (boletines sin API)")
    parser.add_argument("--full-id", help='"Tipo Numero/Año" — opcional para --boe (se infiere)')
    parser.add_argument(
        "--name", help="Nombre completo — opcional para --boe (se infiere del titulo)"
    )
    parser.add_argument(
        "--norm-type", help="ley | rd | rd_legislativo | norma_foral | decreto_foral"
    )
    parser.add_argument("--vigent-from", help="YYYY-MM-DD — opcional para --boe (se infiere)")
    parser.add_argument(
        "--aliases", nargs="*", help="Alias adicionales por los que el LLM puede citarla"
    )
    parser.add_argument("--yes", action="store_true", help="No pedir confirmación")
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
