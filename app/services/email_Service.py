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
    print("=" * 60)
    print("📧 STARTING CLINIC ADMIN EMAIL")
    print(f"Admin Email: {admin_email}")
    print(f"Admin Name: {admin_name}")
    print(f"Clinic: {clinic_name}")
    print(f"SMTP Host: {settings.SMTP_HOST}")
    print(f"SMTP Port: {settings.SMTP_PORT}")
    print(f"SMTP Username: {settings.SMTP_USERNAME}")
    print(f"SMTP From: {settings.SMTP_FROM_EMAIL}")
    print("=" * 60)

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

    try:
        print("📧 Connecting to SMTP server...")

        with smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT
        ) as server:

            print("✅ SMTP connection established")

            print("🔐 Starting TLS...")
            server.starttls()

            print("🔐 Logging into SMTP...")
            server.login(
                settings.SMTP_USERNAME,
                settings.SMTP_PASSWORD,
            )

            print("✅ SMTP login successful")

            print(f"📨 Sending email to {admin_email}...")

            server.send_message(message)

            print("✅ EMAIL SENT SUCCESSFULLY")
            print(f"📩 Recipient: {admin_email}")

        print("=" * 60)

        return True

    except smtplib.SMTPAuthenticationError as e:
        print("❌ SMTP AUTHENTICATION FAILED")
        print(f"Error: {e}")
        raise

    except smtplib.SMTPException as e:
        print("❌ SMTP ERROR")
        print(f"Error: {e}")
        raise

    except Exception as e:
        print("❌ EMAIL SENDING FAILED")
        print(f"Error type: {type(e).__name__}")
        print(f"Error: {e}")
        raise
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

        print(f"📧 Sending doctor invite email to: {email}")
        print(f"📨 SMTP server: {settings.SMTP_HOST}:{settings.SMTP_PORT}")

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                print("🔌 Connected to SMTP server")

                server.starttls()
                print("🔐 STARTTLS successful")

                server.login(
                    settings.SMTP_USERNAME,
                    settings.SMTP_PASSWORD,
                )
                print("✅ SMTP login successful")

                response = server.send_message(message)

                print(f"📤 Email sent successfully to: {email}")
                print(f"📨 SMTP response: {response}")

        except Exception as e:
            print(f"❌ Failed to send email to {email}")
            print(f"❌ Email error: {e}")

            raise