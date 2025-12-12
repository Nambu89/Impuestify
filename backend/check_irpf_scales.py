"""Script temporal para verificar las escalas IRPF en la BD"""
import asyncio
from dotenv import load_dotenv
from app.database.turso_client import TursoClient

# Cargar variables de entorno
load_dotenv()

async def check_scales():
    db = TursoClient()
    await db.connect()
    
    # Verificar qué escalas tenemos
    result = await db.execute(
        'SELECT DISTINCT jurisdiction, year FROM irpf_scales ORDER BY jurisdiction, year'
    )
    
    print('=' * 60)
    print('ESCALAS IRPF DISPONIBLES EN LA BASE DE DATOS:')
    print('=' * 60)
    
    if not result.rows:
        print('❌ NO HAY ESCALAS EN LA BASE DE DATOS')
    else:
        for row in result.rows:
            row_dict = dict(row)
            print(f"  ✓ {row_dict['jurisdiction']} - Año {row_dict['year']}")
    
    print('\n' + '=' * 60)
    print('BUSCANDO ESPECÍFICAMENTE MADRID 2025:')
    print('=' * 60)
    
    madrid_2025 = await db.execute(
        "SELECT * FROM irpf_scales WHERE jurisdiction = 'Madrid' AND year = 2025 LIMIT 5"
    )
    
    if not madrid_2025.rows:
        print('❌ NO SE ENCONTRÓ Madrid 2025')
        
        # Buscar variaciones
        print('\nBuscando variaciones de "Madrid":')
        madrid_any = await db.execute(
            "SELECT DISTINCT jurisdiction, year FROM irpf_scales WHERE jurisdiction LIKE '%Madrid%'"
        )
        if madrid_any.rows:
            for row in madrid_any.rows:
                row_dict = dict(row)
                print(f"  → Encontrado: '{row_dict['jurisdiction']}' - Año {row_dict['year']}")
        else:
            print('  → No se encontró ninguna variación de Madrid')
    else:
        print(f'✓ SE ENCONTRÓ Madrid 2025 ({len(madrid_2025.rows)} tramos)')
        for row in madrid_2025.rows:
            print(f"  {dict(row)}")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(check_scales())
