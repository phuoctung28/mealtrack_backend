"""
Service for sending email notifications.
"""
import logging
from typing import Optional
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from src.domain.model.notification import Notification, get_notification_template
from src.infra.repositories.notification_repository import NotificationLogRepository

logger = logging.getLogger(__name__)


class EmailNotificationService:
    """Service for sending email notifications"""
    
    def __init__(
        self,
        notification_repository: NotificationLogRepository,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_use_tls: bool = True,
        from_email: Optional[str] = None,
        from_name: str = "Nutree AI"
    ):
        self.notification_repository = notification_repository
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.smtp_use_tls = smtp_use_tls
        self.from_email = from_email or smtp_username
        self.from_name = from_name
        self.email_enabled = bool(smtp_host and smtp_username and smtp_password)
        
        if not self.email_enabled:
            logger.warning("Email service not configured - email notifications disabled")
    
    async def send_email_notification(
        self,
        user_email: str,
        user_name: str,
        notification: Notification
    ) -> str:
        """
        Send email notification to user
        
        Args:
            user_email: User's email address
            user_name: User's display name
            notification: Notification to send
            
        Returns:
            Notification log ID
            
        Raises:
            ValueError: If email service not configured or email address invalid
            RuntimeError: If email sending fails
        """
        if not self.email_enabled:
            raise RuntimeError("Email service not configured")
        
        if not user_email or '@' not in user_email:
            raise ValueError(f"Invalid email address: {user_email}")
        
        # Create notification log
        log_id = await self.notification_repository.create_log(
            user_id=notification.user_id,
            notification=notification,
            device_token_id=None
        )
        
        try:
            # Generate email HTML content
            html_content = self._render_email_template(
                notification.notification_type,
                user_name,
                notification.title,
                notification.body,
                notification.data
            )
            
            # Send email
            await self._send_email(
                to_email=user_email,
                subject=notification.title,
                html_content=html_content
            )
            
            # Update log status
            await self.notification_repository.update_status(
                log_id, 'sent', sent_at=datetime.utcnow()
            )
            
            logger.info(f"Sent email notification to {user_email}")
            return log_id
            
        except Exception as e:
            logger.error(f"Failed to send email to {user_email}: {e}")
            await self.notification_repository.update_status(
                log_id, 'failed', error_message=str(e)
            )
            raise
    
    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str
    ):
        """
        Send email via SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                
                server.send_message(msg)
            
            logger.debug(f"Email sent successfully to {to_email}")
            
        except Exception as e:
            logger.error(f"SMTP error sending to {to_email}: {e}")
            raise
    
    def _render_email_template(
        self,
        notification_type: str,
        user_name: str,
        title: str,
        body: str,
        data: dict
    ) -> str:
        """
        Render email HTML template
        
        Args:
            notification_type: Type of notification
            user_name: User's display name
            title: Notification title
            body: Notification body
            data: Additional data
            
        Returns:
            HTML string
        """
        # Basic HTML email template
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    background-color: #ffffff;
                    border-radius: 8px;
                    padding: 30px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                    padding-bottom: 20px;
                    border-bottom: 2px solid #4CAF50;
                }}
                .header h1 {{
                    color: #4CAF50;
                    margin: 0;
                    font-size: 28px;
                }}
                .content {{
                    margin-bottom: 30px;
                }}
                .title {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #333;
                    margin-bottom: 15px;
                }}
                .body {{
                    font-size: 16px;
                    color: #666;
                    margin-bottom: 20px;
                }}
                .cta-button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background-color: #4CAF50;
                    color: #ffffff !important;
                    text-decoration: none;
                    border-radius: 4px;
                    font-weight: bold;
                    text-align: center;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    font-size: 14px;
                    color: #999;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                }}
                .greeting {{
                    font-size: 18px;
                    margin-bottom: 20px;
                    color: #333;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🥗 Nutree AI</h1>
                </div>
                <div class="content">
                    <div class="greeting">Hi {user_name},</div>
                    <div class="title">{title}</div>
                    <div class="body">{body}</div>
                    {self._get_cta_button(notification_type)}
                </div>
                <div class="footer">
                    <p>You received this email because you have notifications enabled in your Nutree AI app.</p>
                    <p>To manage your notification preferences, open the app and go to Settings > Notifications.</p>
                    <p>&copy; 2025 Nutree AI. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    def _get_cta_button(self, notification_type: str) -> str:
        """Get call-to-action button HTML for notification type"""
        cta_map = {
            'weight_reminder': '<a href="nutreeai://profile/weight" class="cta-button">Update Weight Now</a>',
            'meal_reminder': '<a href="nutreeai://scan" class="cta-button">Log Meal</a>',
            'achievement': '<a href="nutreeai://achievements" class="cta-button">View Achievements</a>',
            'goal_progress': '<a href="nutreeai://dashboard" class="cta-button">View Progress</a>',
        }
        return cta_map.get(notification_type, '')

