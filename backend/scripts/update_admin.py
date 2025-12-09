"""
Script simple para marcar usuario como admin
Ejecutar desde backend/: python -m scripts.update_admin
"""
import os
import sys

# Configurar path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

async def update_admin():
    # Importar después de cargar .env
    from app.database.turso_client import TursoClient
    
    db_url = os.getenv("TURSO_DATABASE_URL")
    db_token = os.getenv("TURSO_AUTH_TOKEN")
    
    if not db_url or not db_token:
        print("❌ Variables de entorno no configuradas")
        return
    
    client = TursoClient(db_url, db_token)
    
    email = "fernando.prada@proton.me"
    
    # Verificar usuario actual
    print(f"🔍 Buscando usuario: {email}")
    result = await client.execute(
        "SELECT id, email, name, is_admin FROM users WHERE email = ?",
        [email]
    )
    
    if not result.rows:
        print(f"❌ Usuario no encontrado: {email}")
        return
    
    user = result.rows[0]
    print(f"\n📧 Usuario encontrado:")
    print(f"   Email: {user['email']}")
    print(f"   Nombre: {user.get('name', 'N/A')}")
    print(f"   Admin actual: {bool(user['is_admin'])}")
    
    # Actualizar a admin
    print(f"\n🔧 Actualizando a admin...")
    await client.execute(
        "UPDATE users SET is_admin = ? WHERE email = ?",
        [1, email]
    )
    
    # Verificar
    result = await client.execute(
        "SELECT is_admin FROM users WHERE email = ?",
        [email]
    )
    
    is_admin = bool(result.rows[0]['is_admin'])
    
    if is_admin:
        print(f"✅ Usuario {email} ahora es ADMIN")
        print(f"\n⚠️  IMPORTANTE: Debes cerrar sesión y volver a iniciar sesión")
        print(f"   para que el cambio surta efecto.")
    else:
        print(f"❌ Error al actualizar")

if __name__ == "__main__":
    asyncio.run(update_admin())
