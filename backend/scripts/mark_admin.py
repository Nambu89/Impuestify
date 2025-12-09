"""
Script para marcar un usuario como admin en TaxIA
"""
import asyncio
import sys
import os

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.turso_client import get_db_client


async def mark_user_as_admin(email: str):
    """Marca un usuario como administrador."""
    db = await get_db_client()
    
    # Verificar si el usuario existe
    result = await db.execute(
        "SELECT id, email, is_admin FROM users WHERE email = ?",
        [email]
    )
    
    if not result.rows:
        print(f"❌ Usuario {email} no encontrado")
        return
    
    user = result.rows[0]
    print(f"📧 Usuario encontrado: {user['email']}")
    print(f"   ID: {user['id']}")
    print(f"   Admin actual: {bool(user['is_admin'])}")
    
    # Actualizar a admin
    await db.execute(
        "UPDATE users SET is_admin = ? WHERE email = ?",
        [True, email]
    )
    
    # Verificar actualización
    result = await db.execute(
        "SELECT is_admin FROM users WHERE email = ?",
        [email]
    )
    
    is_admin = bool(result.rows[0]['is_admin'])
    
    if is_admin:
        print(f"✅ Usuario {email} marcado como ADMIN correctamente")
    else:
        print(f"❌ Error al actualizar usuario")


if __name__ == "__main__":
    email = "fernando.prada@proton.me"
    print(f"🔧 Marcando {email} como administrador...\n")
    asyncio.run(mark_user_as_admin(email))
