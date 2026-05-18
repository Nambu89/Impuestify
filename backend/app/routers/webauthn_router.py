"""
WebAuthn / Passkey HTTP endpoints for Impuestify.

Mounted at /auth/webauthn/* in main.py.
"""

import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

from app.auth.jwt_handler import (
    TokenData,
    create_access_token,
    create_refresh_token,
    get_current_user,
)
from app.auth.webauthn_handler import WebAuthnService
from app.security.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/webauthn", tags=["webauthn"])


def _get_service(request: Request) -> WebAuthnService:
    redis = getattr(request.app.state, "upstash_client", None)
    return WebAuthnService(redis=redis)


# ── Schemas ─────────────────────────────────────────────────────────────────


class RegisterCompleteBody(BaseModel):
    credential: dict
    label: str | None = None


class LoginBeginBody(BaseModel):
    email: EmailStr


class LoginCompleteBody(BaseModel):
    email: EmailStr
    credential: dict


# ── Registration (must be authenticated) ────────────────────────────────────


@router.post("/register/begin")
@limiter.limit("10/minute")
async def webauthn_register_begin(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Returns options for navigator.credentials.create()."""
    svc = _get_service(request)
    opts = await svc.begin_registration(
        user_id=current_user.user_id,
        user_email=current_user.email,
    )
    return asdict(opts)


@router.post("/register/complete")
@limiter.limit("10/minute")
async def webauthn_register_complete(
    request: Request,
    body: RegisterCompleteBody,
    current_user: TokenData = Depends(get_current_user),
):
    svc = _get_service(request)
    try:
        cred_id = await svc.complete_registration(
            user_id=current_user.user_id,
            credential_response=body.credential,
            label=body.label,
        )
        return {"success": True, "credential_id": cred_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"WebAuthn registration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="No se pudo registrar la passkey.")


# ── Login (no auth — credential proves identity) ────────────────────────────


@router.post("/login/begin")
@limiter.limit("20/minute")
async def webauthn_login_begin(request: Request, body: LoginBeginBody):
    """Returns options for navigator.credentials.get()."""
    svc = _get_service(request)
    opts = await svc.begin_login(user_email=body.email)
    return asdict(opts)


@router.post("/login/complete")
@limiter.limit("10/minute")
async def webauthn_login_complete(request: Request, body: LoginCompleteBody):
    svc = _get_service(request)
    try:
        user_id = await svc.complete_login(
            user_email=body.email, credential_response=body.credential
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.warning(f"WebAuthn login failed: {e}")
        raise HTTPException(status_code=401, detail="Credencial no válida.")

    # Issue tokens — same shape as /auth/login
    from app.database.turso_client import get_db_client

    db = await get_db_client()
    user_row = await db.execute(
        "SELECT id, email, name, is_admin, is_owner, is_active " "FROM users WHERE id = ? LIMIT 1",
        [user_id],
    )
    if not user_row.rows:
        raise HTTPException(status_code=401, detail="Usuario no encontrado.")
    u = dict(user_row.rows[0])
    if not u.get("is_active", True):
        raise HTTPException(status_code=403, detail="Cuenta desactivada.")

    access_token = create_access_token(data={"sub": u["id"], "email": u["email"]})
    refresh_token = create_refresh_token(data={"sub": u["id"], "email": u["email"]})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": u["id"],
            "email": u["email"],
            "name": u.get("name"),
            "is_admin": bool(u.get("is_admin")),
            "is_owner": bool(u.get("is_owner")),
        },
    }


# ── Management ──────────────────────────────────────────────────────────────


@router.get("/credentials")
async def webauthn_list_credentials(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    svc = _get_service(request)
    return {"credentials": await svc.list_credentials(current_user.user_id)}


@router.delete("/credentials/{cred_id}")
async def webauthn_delete_credential(
    request: Request,
    cred_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    svc = _get_service(request)
    await svc.delete_credential(current_user.user_id, cred_id)
    return {"success": True}
