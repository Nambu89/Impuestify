import sys
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Load .env from project root
env_path = backend_dir.parent / ".env"
print(f"Cargando .env desde: {env_path}")
load_dotenv(env_path)

from app.database.turso_client import TursoClient

async def check_documents():
    print("Conectando a Turso...")
    client = TursoClient()
    await client.connect()
    
    try:
        print("\nBuscando documentos en la base de datos...")
        # Query documents
        result = await client.execute("SELECT id, title, filename FROM documents")
        
        if not result.rows:
            print("No se encontraron documentos en la tabla 'documents'.")
            return

        print(f"Se encontraron {len(result.rows)} documentos:\n")
        
        manuals_found = []
        for row in result.rows:
            print(f"- {row['title']} (Archivo: {row['filename']})")
            if "Manual" in row['title'] or "Manual" in row['filename']:
                manuals_found.append(row['title'])
        
        print("\n" + "="*50)
        if manuals_found:
            print(f"CONCLUSION: SI tenemos manuales indexados ({len(manuals_found)} encontrados).")
        else:
            print("CONCLUSION: NO parece haber manuales indexados.")
            
    except Exception as e:
        print(f"Error al consultar: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_documents())
