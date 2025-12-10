"""
Debug script to verify tool registration.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.tools import ALL_TOOLS, TOOL_EXECUTORS

print("=" * 60)
print("TaxIA - Verificación de Tools")
print("=" * 60)

print(f"\n📋 Total de tools registradas: {len(ALL_TOOLS)}")
print("\n🔧 Tools disponibles:")
for i, tool in enumerate(ALL_TOOLS, 1):
    tool_name = tool['function']['name']
    tool_desc = tool['function']['description']
    print(f"\n{i}. {tool_name}")
    print(f"   Descripción: {tool_desc[:100]}...")

print(f"\n🎯 Ejecutores registrados: {len(TOOL_EXECUTORS)}")
for name in TOOL_EXECUTORS.keys():
    print(f"   - {name}")

print("\n" + "=" * 60)
