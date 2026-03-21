"""
Email service for sending notifications
"""
import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings


class EmailService:
    """Service for sending emails."""

    @staticmethod
    async def send_college_admin_credentials(
        email: str,
        admin_name: str,
        college_name: str,
        password: str,
        login_url: str = "http://localhost:5173/login",
    ) -> bool:
        if not settings.SENDER_EMAIL or not settings.SENDER_PASSWORD:
            print("Warning: Email credentials not configured in .env")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "ClassBoard - Your College Admin Account Credentials"
            msg["From"] = f"{settings.SENDER_NAME} <{settings.SENDER_EMAIL}>"
            msg["To"] = email

            html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; padding: 20px;">
                        <div style="text-align: center; margin-bottom: 30px;">
                            <h1 style="color: #1e40af;">ClassBoard</h1>
                            <p style="color: #666; margin: 0;">Academic Coordination Platform</p>
                        </div>

                        <h2 style="color: #1e40af; border-bottom: 2px solid #3b82f6; padding-bottom: 10px;">Welcome, {admin_name}</h2>

                        <p>Your college admin account has been created on ClassBoard for <strong>{college_name}</strong>.</p>

                        <div style="background-color: #f3f4f6; padding: 20px; border-radius: 6px; margin: 20px 0;">
                            <h3 style="color: #1e40af; margin-top: 0;">Login Credentials</h3>
                            <p><strong>Email:</strong> {email}</p>
                            <p><strong>Temporary Password:</strong> <code style="background-color: #e5e7eb; padding: 4px 8px; border-radius: 4px; font-family: monospace;">{password}</code></p>
                        </div>

                        <p style="margin-top: 20px;">
                            <a href="{login_url}" style="display: inline-block; background-color: #1e40af; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">
                                Login to ClassBoard
                            </a>
                        </p>

                        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px;">
                            <p><strong>Important:</strong> Please change your password immediately after logging in.</p>
                            <p>If you did not request this account, please contact the system administrator.</p>
                            <p style="margin: 10px 0 0 0; text-align: center; color: #999;">ClassBoard - Academic Coordination</p>
                        </div>
                    </div>
                </body>
            </html>
            """

            text = f"""
ClassBoard - Academic Coordination Platform

Welcome, {admin_name}

Your college admin account has been created for {college_name}.

Login Credentials:
Email: {email}
Temporary Password: {password}

Login URL: {login_url}

Important: Please change your password immediately after logging in.

If you did not request this account, please contact the system administrator.
            """

            msg.attach(MIMEText(text, "plain"))
            msg.attach(MIMEText(html, "html"))

            loop = asyncio.get_event_loop()
            loop.run_in_executor(None, EmailService._send_smtp, msg)
            return True
        except Exception as exc:
            print(f"Error sending email: {exc}")
            return False

    @staticmethod
    def _send_smtp(msg: MIMEMultipart) -> None:
        try:
            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SENDER_EMAIL, settings.SENDER_PASSWORD)
                server.send_message(msg)
        except Exception as exc:
            print(f"SMTP Error: {exc}")
