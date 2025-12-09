"""Script para recrear la tabla embeddings con TEXT en lugar de BLOB."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)

from app.database.turso_client import TursoClient


async def fix_embeddings_table():
    """Recrea la tabla embeddings con TEXT para compatibilidad con libsql."""
    print("Conectando a Turso...")
    client = TursoClient()
    await client.connect()
    print("Conectado")
    
    try:
        # Eliminar tabla existente
        print("Eliminando tabla embeddings...")
        await client.execute("DROP TABLE IF EXISTS embeddings")
        
        # Crear nueva tabla con TEXT
        print("Creando tabla embeddings con TEXT...")
        await client.execute("""
            CREATE TABLE embeddings (
                id TEXT PRIMARY KEY,
                chunk_id TEXT NOT NULL UNIQUE,
                embedding TEXT NOT NULL,
                model_name TEXT DEFAULT 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                dimensions INTEGER DEFAULT 384,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (chunk_id) REFERENCES document_chunks(id) ON DELETE CASCADE
            )
        """)
        
        # Crear índice
        await client.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_chunk ON embeddings(chunk_id)")
        
        print("Tabla embeddings recreada correctamente con TEXT")
        
        # También limpiar datos existentes para reprocesar
        print("Limpiando documentos y chunks existentes...")
        await client.execute("DELETE FROM document_chunks")
        await client.execute("DELETE FROM documents")
        print("Datos limpiados - listo para reprocesar PDFs")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(fix_embeddings_table())
