"""
Email Service for TaxIA using Resend.

Provides email sending capabilities for sharing reports with advisors.
"""
import base64
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EmailService:
    """Wrapper around Resend API for sending emails."""

    def __init__(self):
        self._resend = None
        self._from_email = None

    def _init_client(self):
        """Lazy initialization of Resend client."""
        if self._resend is not None:
            return

        from app.config import settings

        if not settings.is_resend_configured:
            raise RuntimeError("Resend is not configured. Set RESEND_API_KEY.")

        import resend
        resend.api_key = settings.RESEND_API_KEY
        self._resend = resend
        self._from_email = settings.RESEND_FROM_EMAIL

    async def send_email(
        self,
        to: str,
        subject: str,
        html: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Send an email via Resend.

        Args:
            to: Recipient email
            subject: Email subject
            html: HTML body
            attachments: List of dicts with 'filename' and 'content' (bytes)

        Returns:
            Dict with send result
        """
        self._init_client()

        params = {
            "from_": self._from_email,
            "to": [to],
            "subject": subject,
            "html": html,
        }

        if attachments:
            resend_attachments = []
            for att in attachments:
                resend_attachments.append({
                    "filename": att["filename"],
                    "content": list(att["content"]),  # Resend expects list of bytes
                })
            params["attachments"] = resend_attachments

        try:
            result = self._resend.Emails.send(params)
            logger.info("Email sent", to=to, subject=subject)
            return {"success": True, "id": getattr(result, "id", str(result))}
        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def send_report_to_advisor(
        self,
        advisor_email: str,
        user_name: str,
        report_title: str,
        pdf_bytes: bytes,
    ) -> Dict[str, Any]:
        """
        Send an IRPF report PDF to a tax advisor.

        Args:
            advisor_email: Advisor's email address
            user_name: Name of the user sharing the report
            report_title: Title for the report
            pdf_bytes: PDF file content

        Returns:
            Dict with send result
        """
        subject = f"Informe fiscal de {user_name} — {report_title}"

        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1a56db; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0; font-size: 20px;">Impuestify</h1>
                <p style="margin: 5px 0 0 0; opacity: 0.9; font-size: 14px;">Informe fiscal compartido</p>
            </div>
            <div style="background: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px;">
                <p>Hola,</p>
                <p><strong>{user_name}</strong> ha compartido contigo un informe fiscal generado con Impuestify:</p>
                <div style="background: white; border: 1px solid #e0e0e0; border-radius: 6px; padding: 15px; margin: 15px 0;">
                    <p style="margin: 0; font-weight: 600;">{report_title}</p>
                </div>
                <p>Encontrarás el informe en PDF adjunto a este email.</p>
                <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
                <p style="color: #666; font-size: 12px;">
                    Este informe ha sido generado automáticamente por Impuestify y tiene carácter
                    meramente orientativo. No constituye asesoramiento fiscal profesional.
                </p>
            </div>
        </div>
        """

        return await self.send_email(
            to=advisor_email,
            subject=subject,
            html=html,
            attachments=[{
                "filename": f"informe_irpf_{user_name.replace(' ', '_')}.pdf",
                "content": pdf_bytes,
            }],
        )


# Singleton
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get global EmailService instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
