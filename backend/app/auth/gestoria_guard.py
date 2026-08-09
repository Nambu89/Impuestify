"""Dependency: restringe endpoints a cuentas gestoría (users.account_type='gestoria')."""

from fastapi import Depends, HTTPException, status

from app.auth.jwt_handler import TokenData, get_current_user
from app.database.turso_client import TursoClient, get_db_client


async def require_gestoria(
    current_user: TokenData = Depends(get_current_user),
    db: TursoClient = Depends(get_db_client),
) -> TokenData:
    """Permite el acceso solo si el usuario es una cuenta gestoría."""
    result = await db.execute("SELECT account_type FROM users WHERE id = ?", [current_user.user_id])
    if not result.rows or result.rows[0].get("account_type") != "gestoria":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a cuentas gestoría.",
        )
    return current_user
