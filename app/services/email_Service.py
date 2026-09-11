# app/services/email_service.py

import smtplib
from email.message import EmailMessage

from app.core.config import settings

def send_clinic_admin_welcome_email(
    admin_email: str,
    admin_name: str,
    clinic_name: str,
    temp_password: str,
):
    message = EmailMessage()

    message["Subject"] = f"Welcome to ClinicFlow AI - {clinic_name}"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = admin_email

    message.set_content(
        f"""
Hello {admin_name},

Your ClinicFlow AI clinic admin account has been created.

Clinic:
{clinic_name}

Email:
{admin_email}

Temporary Password:
{temp_password}

Please log in and change your password after your first login.

Login:
https://app.clinicflowai.com/login

Regards,
ClinicFlow AI
"""
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(
            settings.SMTP_USERNAME,
            settings.SMTP_PASSWORD,
        )

        server.send_message(message)

def send_doctor_invite_email(
    email: str,
    token: str,
    clinic_name: str,
):
    invite_url = f"{settings.FRONTEND_URL}/invite/{token}"

    message = EmailMessage()

    message["Subject"] = f"You've been invited to {clinic_name} - ClinicFlow AI"
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = email

    message.set_content(
        f"""
Hello Doctor,

You have been invited to join {clinic_name} as a doctor on ClinicFlow AI.

Please use the link below to accept your invitation and create your account:

{invite_url}

This invitation will expire in 7 days.

If you did not expect this invitation, you can safely ignore this email.

Regards,
ClinicFlow AI
"""
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(
            settings.SMTP_USERNAME,
            settings.SMTP_PASSWORD,
        )
        server.send_message(message)