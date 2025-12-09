"""
Script para inicializar el esquema de la base de datos Turso.

Ejecutar desde el directorio backend:
    python scripts/init_db.py
"""
import asyncio
import os
import sys

# Añadir el directorio padre al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Cargar variables de entorno
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)

from app.database.turso_client import TursoClient


async def init_database():
    """Inicializa el esquema de la base de datos."""
    print("=" * 60)
    print("TaxIA - Inicialización de Base de Datos Turso")
    print("=" * 60)
    
    # Verificar variables de entorno
    url = os.environ.get("TURSO_DATABASE_URL")
    token = os.environ.get("TURSO_AUTH_TOKEN")
    
    if not url:
        print("❌ ERROR: TURSO_DATABASE_URL no está configurada")
        print("   Añade la variable en el archivo .env")
        return False
    
    if not token:
        print("❌ ERROR: TURSO_AUTH_TOKEN no está configurado")
        print("   Añade la variable en el archivo .env")
        return False
    
    print(f"✓ URL: {url[:50]}...")
    print(f"✓ Token: {'*' * 20}...")
    print()
    
    try:
        # Conectar a Turso
        print("📡 Conectando a Turso...")
        client = TursoClient(url=url, auth_token=token)
        await client.connect()
        print("✓ Conexión establecida")
        print()
        
        # Inicializar esquema
        print("🏗️  Creando tablas...")
        await client.init_schema()
        print("✓ Esquema inicializado correctamente")
        print()
        
        # Verificar tablas creadas
        print("📋 Verificando tablas creadas...")
        result = await client.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        
        tables = [row.get('name', row[0] if isinstance(row, (list, tuple)) else 'unknown') 
                  for row in result.rows]
        
        print(f"   Tablas encontradas: {len(tables)}")
        for table in tables:
            if not table.startswith('sqlite_'):
                print(f"   ✓ {table}")
        
        print()
        
        # Insertar categorías fiscales base
        print("📁 Insertando categorías fiscales base...")
        await insert_tax_categories(client)
        print("✓ Categorías insertadas")
        
        print()
        print("=" * 60)
        print("✅ BASE DE DATOS INICIALIZADA CORRECTAMENTE")
        print("=" * 60)
        
        await client.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def insert_tax_categories(client: TursoClient):
    """Inserta las categorías fiscales principales de España."""
    import uuid
    
    categories = [
        ("IRPF", "IRPF", "Impuesto sobre la Renta de las Personas Físicas", None),
        ("IVA", "IVA", "Impuesto sobre el Valor Añadido", None),
        ("IS", "IS", "Impuesto sobre Sociedades", None),
        ("IP", "IP", "Impuesto sobre el Patrimonio", None),
        ("ISD", "ISD", "Impuesto sobre Sucesiones y Donaciones", None),
        ("IRNR", "IRNR", "Impuesto sobre la Renta de No Residentes", None),
        ("IAE", "IAE", "Impuesto sobre Actividades Económicas", None),
        ("ITP", "ITP", "Impuesto sobre Transmisiones Patrimoniales", None),
        ("RETENCIONES", "RET", "Retenciones e Ingresos a Cuenta", None),
        ("MODELOS", "MOD", "Modelos y Formularios Tributarios", None),
        ("CALENDARIO", "CAL", "Calendario del Contribuyente", None),
        ("FACTURACION", "FAC", "Facturación y Verifactu", None),
        ("ADUANAS", "ADU", "Aduanas e Impuestos Especiales", None),
    ]
    
    for name, code, description, parent_id in categories:
        try:
            cat_id = str(uuid.uuid4())
            await client.execute(
                """
                INSERT OR IGNORE INTO tax_categories (id, code, name, description, parent_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                [cat_id, code, name, description, parent_id]
            )
        except Exception as e:
            # Ignorar si ya existe
            pass


if __name__ == "__main__":
    success = asyncio.run(init_database())
    sys.exit(0 if success else 1)
