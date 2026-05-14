#!/usr/bin/env python3
"""Send winback promo email to re-engage old customers."""

import asyncio
import sys

sys.path.insert(0, "/Users/alexnguyen/Desktop/Nut/mealtrack_backend")

import resend

from src.infra.services.email_template_renderer import EmailTemplateRenderer


async def send_winback_promo(
    from_email: str,
    to_email: str,
    first_name: str = "bạn",
    promo_code: str = "COMEBACK55",
    days_left: int = 3,
):
    """Send winback promo email with psychological sales copy."""
    resend.api_key = "re_K3woYMV2_Mpu6189Pjy33UXYVpiEpquDE"

    renderer = EmailTemplateRenderer()
    html_body = renderer.render(
        "winback_promo",
        {
            "first_name": first_name,
            "promo_code": promo_code,
            "days_left": days_left,
        },
    )

    try:
        result = resend.Emails.send({
            "from": from_email,
            "to": [to_email],
            "subject": f"Mình đang giữ ưu đãi này cho bạn — còn {days_left} ngày 🌿",
            "html": html_body,
        })
        message_id = result.get("id") if isinstance(result, dict) else str(result)
        print(f"Email sent successfully! Message ID: {message_id}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


if __name__ == "__main__":
    # Configuration
    FROM_EMAIL = "Alex từ Nutree <alex.nguyen@nutreeai.com>"
    TO_EMAIL = "cutung2002bk@gmail.com"
    FIRST_NAME = "Tu"
    PROMO_CODE = "COMEBACK55"
    DAYS_LEFT = 3

    print(f"Sending winback promo email...")
    print(f"  From: {FROM_EMAIL}")
    print(f"  To: {TO_EMAIL}")
    print(f"  Promo Code: {PROMO_CODE}")
    print(f"  Days Left: {DAYS_LEFT}")
    print()

    asyncio.run(send_winback_promo(
        from_email=FROM_EMAIL,
        to_email=TO_EMAIL,
        first_name=FIRST_NAME,
        promo_code=PROMO_CODE,
        days_left=DAYS_LEFT,
    ))
