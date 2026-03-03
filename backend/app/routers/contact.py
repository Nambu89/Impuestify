"""
Contact Router for TaxIA/Impuestify

Handles contact form submissions (e.g. autonomo service interest).
Submissions are stored in DB for the owner to review.
"""
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.auth.jwt_handler import get_current_user, TokenData
from app.database.turso_client import get_db_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contact", tags=["contact"])


class ContactFormRequest(BaseModel):
    name: Optional[str] = None
    email: EmailStr
    message: Optional[str] = None
    request_type: str = "autonomo_interest"


class ContactFormResponse(BaseModel):
    success: bool
    message: str


@router.post("/", response_model=ContactFormResponse)
async def submit_contact_form(
    form: ContactFormRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Submit a contact form request.

    Stores the request in the database for the owner to review.
    The recipient email is never exposed to the user.
    """
    db = await get_db_client()

    try:
        request_id = str(uuid.uuid4())
        await db.execute(
            """
            INSERT INTO contact_requests (id, user_id, email, name, message, request_type)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                request_id,
                current_user.user_id,
                form.email,
                form.name,
                form.message,
                form.request_type,
            ],
        )

        logger.info(
            "Contact form submitted",
            extra={
                "user_id": current_user.user_id,
                "request_type": form.request_type,
            },
        )

        return ContactFormResponse(
            success=True,
            message="Tu solicitud ha sido enviada. Te contactaremos pronto.",
        )
    except Exception as e:
        logger.error("Error saving contact request", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al enviar la solicitud.")
