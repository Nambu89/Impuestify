"""Send apology + activation email to Gabriel via Resend.

Resend lets you send from any address on a verified domain. The Impuestify
domain `impuestify.com` is verified in Resend, so we use `soporte@impuestify.com`
as the From address — Cloudflare Email Routing already forwards inbound mail
on that alias to the project owner's inbox, so replies arrive automatically.

Run:
  PYTHONUTF8=1 python scripts/send_email_to_gabriel.py [--dry-run]

Requires RESEND_API_KEY to be present in the environment (loaded from .env).
If you don't have it locally, copy the value from Railway → Variables.
"""
import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
env_path = backend_dir.parent / ".env"
load_dotenv(env_path)


GABRIEL_EMAIL = "gabriel.demacedo1@gmail.com"
GABRIEL_NAME = "Gabriel"

FROM_ADDRESS = "Fernando (Impuestify) <soporte@impuestify.com>"
REPLY_TO = "soporte@impuestify.com"  # Cloudflare forwards to fernando.prada@proton.me

SUBJECT = "Tu cuenta de Impuestify ya está activa — disculpa por las molestias"

TEXT_BODY = f"""Hola {GABRIEL_NAME},

Soy Fernando, el desarrollador de Impuestify. Gracias por avisarnos del problema y disculpa el mal rato.

Tras tu pago hubo un fallo en la activación que dejó tu cuenta sin acceso aunque el cobro sí se procesó. Ya está corregido.

Esto es lo que hemos hecho:

- Tu cuenta queda activa de inmediato. Puedes entrar en https://impuestify.com con tu cuenta de Google y empezar a usarla.
- Te devolvemos los dos pagos de 5 €. Verás los reembolsos en tu tarjeta en los próximos 5-7 días laborables.
- Te regalamos un mes completo de acceso gratuito como compensación. No se renovará automáticamente, así que no tendrás más cargos: si pasado el mes te resulta útil, podrás suscribirte de nuevo cuando quieras.

Si encuentras cualquier otro problema o tienes dudas, responde a este correo y te atiendo personalmente. Si quieres mandarme feedback (sugerencias, cosas que cambiarías, lo que sea), también vale a este mismo correo: me llega directo a mí.

Disculpa de nuevo y gracias por la paciencia.

Un saludo,
Fernando
Impuestify · https://impuestify.com
"""

HTML_BODY = f"""<!doctype html>
<html lang="es">
<body style="margin:0;padding:0;background:#f5f7fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#1f2937;">
  <div style="max-width:560px;margin:0 auto;padding:24px 16px;">
    <div style="background:#1a56db;color:#fff;padding:18px 22px;border-radius:8px 8px 0 0;">
      <h1 style="margin:0;font-size:18px;font-weight:600;">Impuestify</h1>
      <p style="margin:4px 0 0 0;opacity:0.9;font-size:13px;">Tu cuenta ya está activa</p>
    </div>
    <div style="background:#ffffff;padding:24px 22px;border-radius:0 0 8px 8px;border:1px solid #e5e7eb;border-top:0;line-height:1.55;">
      <p>Hola {GABRIEL_NAME},</p>
      <p>Soy Fernando, el desarrollador de Impuestify. Gracias por avisarnos del problema y disculpa el mal rato.</p>
      <p>Tras tu pago hubo un fallo en la activación que dejó tu cuenta sin acceso aunque el cobro sí se procesó. Ya está corregido.</p>
      <p style="margin-bottom:8px;"><strong>Esto es lo que hemos hecho:</strong></p>
      <ul style="margin:0 0 16px 18px;padding:0;">
        <li>Tu cuenta queda activa de inmediato. Puedes entrar en
          <a href="https://impuestify.com" style="color:#1a56db;text-decoration:none;">impuestify.com</a>
          con tu cuenta de Google.</li>
        <li>Te devolvemos los dos pagos de 5 €. Los verás reflejados en tu tarjeta en 5-7 días laborables.</li>
        <li>Te regalamos un mes completo de acceso gratuito como compensación.
          No se renovará automáticamente, así que no tendrás más cargos.</li>
      </ul>
      <p>Si encuentras cualquier otro problema o tienes dudas, responde a este correo y te atiendo personalmente. Si quieres mandarme feedback (sugerencias, cosas que cambiarías, lo que sea), también vale a este mismo correo: me llega directo a mí.</p>
      <p>Disculpa de nuevo y gracias por la paciencia.</p>
      <p style="margin-top:18px;">Un saludo,<br><strong>Fernando</strong><br>Desarrollador de Impuestify</p>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0;">
      <p style="color:#6b7280;font-size:12px;margin:0;">Impuestify · <a href="https://impuestify.com" style="color:#6b7280;">impuestify.com</a></p>
    </div>
  </div>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print payload, do not send")
    args = parser.parse_args()

    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key and not args.dry_run:
        print("ERROR: RESEND_API_KEY not found in environment.")
        print("Copy the value from Railway -> Variables -> RESEND_API_KEY into")
        print(f"  {env_path}")
        print("or export it in this shell:  export RESEND_API_KEY=re_...")
        sys.exit(1)

    payload = {
        "from": FROM_ADDRESS,
        "to": [GABRIEL_EMAIL],
        "subject": SUBJECT,
        "text": TEXT_BODY,
        "html": HTML_BODY,
        "reply_to": REPLY_TO,
    }

    print(f"From:     {payload['from']}")
    print(f"To:       {payload['to'][0]}")
    print(f"Reply-To: {payload['reply_to']}")
    print(f"Subject:  {payload['subject']}")
    print(f"Text length: {len(payload['text'])} chars")

    if args.dry_run:
        print("\n[dry-run] not sending.")
        return

    import resend
    resend.api_key = api_key

    result = resend.Emails.send(payload)
    print("\nSent. Resend response:")
    print(result)


if __name__ == "__main__":
    main()
