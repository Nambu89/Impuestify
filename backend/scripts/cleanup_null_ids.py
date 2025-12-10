"""
Clean up documents with NULL IDs from Turso.
"""
import asyncio
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir.parent / ".env")

from app.database.turso_client import TursoClient

async def cleanup_null_ids():
    db = TursoClient(os.getenv('TURSO_DATABASE_URL'), os.getenv('TURSO_AUTH_TOKEN'))
    await db.connect()
    
    print("=" * 60)
    print("Limpieza de documentos con ID NULL")
    print("=" * 60)
    
    # Count NULL IDs before
    result = await db.execute("SELECT COUNT(*) as count FROM documents WHERE id IS NULL")
    null_count_before = result.rows[0]['count']
    print(f"\n📊 Documentos con ID NULL antes: {null_count_before}")
    
    if null_count_before == 0:
        print("\n✅ No hay documentos con ID NULL. Base de datos limpia.")
        await db.disconnect()
        return
    
    # Show what will be deleted
    print(f"\n🗑️  Documentos que serán eliminados:")
    result = await db.execute("SELECT filename, title, document_type FROM documents WHERE id IS NULL")
    for row in result.rows:
        print(f"  - {row['filename']} ({row['document_type']})")
    
    # Confirm deletion
    print(f"\n⚠️  ¿Estás seguro de eliminar estos {null_count_before} documentos?")
    print("   Estos documentos no tienen ID y no pueden ser referenciados.")
    print("   Es seguro eliminarlos.")
    
    # Delete NULL documents
    print(f"\n🔄 Eliminando documentos con ID NULL...")
    await db.execute("DELETE FROM documents WHERE id IS NULL")
    print("✅ Documentos eliminados")
    
    # Verify deletion
    result = await db.execute("SELECT COUNT(*) as count FROM documents WHERE id IS NULL")
    null_count_after = result.rows[0]['count']
    print(f"\n📊 Documentos con ID NULL después: {null_count_after}")
    
    # Count remaining valid documents
    result = await db.execute("SELECT COUNT(*) as count FROM documents WHERE id IS NOT NULL")
    valid_count = result.rows[0]['count']
    print(f"✅ Documentos válidos restantes: {valid_count}")
    
    await db.disconnect()
    print("\n" + "=" * 60)
    print("✅ Limpieza completada")
    print("=" * 60)

asyncio.run(cleanup_null_ids())
