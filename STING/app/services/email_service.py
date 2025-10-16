#!/usr/bin/env python3
"""
Email Notification Service for STING Platform
Handles sending notifications for document approvals, system alerts, and other events
"""

import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from flask import current_app
from jinja2 import Template
from typing import Dict, List, Optional, Any


class EmailService:
    """Service for sending email notifications with templating support"""
    
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'localhost')
        self.smtp_port = int(os.getenv('SMTP_PORT', '1025'))  # Default to Mailpit
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.smtp_use_tls = os.getenv('SMTP_USE_TLS', 'false').lower() == 'true'
        self.from_address = os.getenv('FROM_EMAIL', 'noreply@sting.local')
        self.from_name = os.getenv('FROM_NAME', 'STING Platform')
        
        current_app.logger.info(f"Email service initialized - SMTP: {self.smtp_server}:{self.smtp_port}")
    
    def send_document_approval_notification(self, 
                                          recipient_email: str, 
                                          document_name: str, 
                                          honey_jar_name: str, 
                                          approver_name: str) -> bool:
        """Send notification when document is approved"""
        
        html_content = self._get_approval_template(document_name, honey_jar_name, approver_name)
        
        return self._send_email(
            to_addresses=[recipient_email],
            subject=f"✅ Document Approved: {document_name}",
            html_content=html_content
        )
    
    def send_document_rejection_notification(self, 
                                           recipient_email: str, 
                                           document_name: str, 
                                           honey_jar_name: str, 
                                           reviewer_name: str, 
                                           rejection_reason: str = None) -> bool:
        """Send notification when document is rejected"""
        
        html_content = self._get_rejection_template(
            document_name, honey_jar_name, reviewer_name, rejection_reason
        )
        
        return self._send_email(
            to_addresses=[recipient_email],
            subject=f"📋 Document Rejected: {document_name}",
            html_content=html_content
        )
    
    def send_pending_approval_notification(self, 
                                         admin_emails: List[str], 
                                         document_name: str, 
                                         honey_jar_name: str, 
                                         uploader_name: str) -> bool:
        """Notify admins when document needs approval"""
        
        html_content = self._get_pending_template(document_name, honey_jar_name, uploader_name)
        
        return self._send_email(
            to_addresses=admin_emails,
            subject=f"📄 Document Pending Approval: {document_name}",
            html_content=html_content
        )
    
    def send_system_alert(self, 
                         admin_emails: List[str], 
                         alert_type: str, 
                         alert_message: str, 
                         severity: str = 'medium') -> bool:
        """Send system alert notifications"""
        
        html_content = self._get_alert_template(alert_type, alert_message, severity)
        subject = f"🚨 STING Alert [{severity.upper()}]: {alert_type}"
        
        return self._send_email(
            to_addresses=admin_emails,
            subject=subject,
            html_content=html_content
        )
    
    def send_admin_invitation(self, to_email: str, from_admin: str, 
                             invitation_url: str, expires_at: datetime) -> bool:
        """Send admin invitation email"""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #FFD700; color: #333; padding: 20px; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 20px; margin: 20px 0; }}
                .button {{ 
                    background: #FFD700; 
                    color: #333; 
                    padding: 12px 30px; 
                    text-decoration: none; 
                    border-radius: 5px; 
                    display: inline-block;
                    font-weight: bold;
                    margin: 20px 0;
                }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
                .warning {{ background: #fff3cd; border: 1px solid #ffc107; padding: 10px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🐝 STING Admin Invitation</h1>
                </div>
                
                <div class="content">
                    <h2>You've been invited to become a STING administrator</h2>
                    
                    <p>Hello,</p>
                    
                    <p><strong>{from_admin}</strong> has invited you to join STING as an administrator.</p>
                    
                    <p>As an admin, you will have:</p>
                    <ul>
                        <li>Full access to all platform features</li>
                        <li>Ability to manage users and permissions</li>
                        <li>Access to system configuration and monitoring</li>
                        <li>Enhanced security requirements (2FA mandatory)</li>
                    </ul>
                    
                    <div class="warning">
                        <strong>⚠️ Security Notice:</strong><br>
                        Admin accounts require both TOTP and Passkey enrollment for security.
                        You'll be guided through this setup after registration.
                    </div>
                    
                    <center>
                        <a href="{invitation_url}" class="button">Accept Invitation</a>
                    </center>
                    
                    <p><strong>This invitation expires:</strong> {expires_at.strftime('%Y-%m-%d %H:%M UTC')}</p>
                    
                    <p>If you didn't expect this invitation, please ignore this email.</p>
                    
                    <p>For security reasons:</p>
                    <ul>
                        <li>This invitation link can only be used once</li>
                        <li>It will expire in 24 hours</li>
                        <li>You must use the same email address to register</li>
                    </ul>
                </div>
                
                <div class="footer">
                    <p>STING - Secure Trusted Intelligence and Networking Guardian</p>
                    <p>This is an automated message from the STING platform</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(
            to_addresses=[to_email],
            subject="🐝 STING Administrator Invitation",
            html_content=html_content
        )
    
    def _send_email(self, to_addresses: List[str], subject: str, html_content: str) -> bool:
        """Send email via SMTP"""
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = f"{self.from_name} <{self.from_address}>"
            message['To'] = ', '.join(to_addresses)
            message['X-Mailer'] = 'STING Platform Email Service'
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html', 'utf-8')
            message.attach(html_part)
            
            # Send via SMTP
            if self.smtp_use_tls:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            # Authenticate if credentials provided
            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)
            
            # Send email
            text = message.as_string()
            server.sendmail(self.from_address, to_addresses, text)
            server.quit()
            
            current_app.logger.info(f"Email sent successfully to {', '.join(to_addresses)}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Email send failed: {str(e)}")
            return False
    
    def _get_base_style(self) -> str:
        """Base CSS styles for email templates"""
        return """
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                margin: 0; padding: 20px; background-color: #0f172a; color: #e2e8f0;
            }
            .container { 
                max-width: 600px; margin: 0 auto; background: linear-gradient(135deg, #1e293b, #334155); 
                border-radius: 12px; overflow: hidden; box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
                border: 1px solid #334155;
            }
            .header { 
                background: linear-gradient(135deg, #fbbf24, #f59e0b); color: #000; 
                padding: 30px 40px; text-align: center; 
            }
            .content { padding: 40px; color: #e2e8f0; }
            .footer { 
                background: #0f172a; color: #64748b; padding: 20px 40px; 
                font-size: 14px; border-top: 1px solid #334155; 
            }
            .btn { 
                display: inline-block; background: #fbbf24; color: #000; 
                padding: 12px 24px; text-decoration: none; border-radius: 8px; 
                font-weight: 600; margin: 20px 0; 
            }
            .alert { padding: 16px; border-radius: 8px; margin: 20px 0; }
            .alert-success { background: #064e3b; border: 1px solid #10b981; color: #6ee7b7; }
            .alert-warning { background: #78350f; border: 1px solid #f59e0b; color: #fbbf24; }
            .alert-error { background: #7f1d1d; border: 1px solid #ef4444; color: #f87171; }
            .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }
            .info-item { background: #1e293b; padding: 15px; border-radius: 8px; border-left: 3px solid #fbbf24; }
            .info-label { font-weight: 600; color: #fbbf24; margin-bottom: 5px; }
            .info-value { color: #e2e8f0; }
        </style>
        """
    
    def _get_approval_template(self, document_name: str, honey_jar_name: str, approver_name: str) -> str:
        """Email template for document approval"""
        approval_date = datetime.now().strftime('%B %d, %Y at %I:%M %p')
        dashboard_url = self._get_dashboard_url()
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>{self._get_base_style()}</head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Document Approved!</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">Your document has been approved and is now available</p>
                </div>
                <div class="content">
                    <div class="alert alert-success">
                        <strong>Great news!</strong> Your document has been approved and added to the knowledge base.
                    </div>
                    
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Document</div>
                            <div class="info-value">{document_name}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Honey Jar</div>
                            <div class="info-value">{honey_jar_name}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Approved by</div>
                            <div class="info-value">{approver_name}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Approval Date</div>
                            <div class="info-value">{approval_date}</div>
                        </div>
                    </div>
                    
                    <p>Your document is now searchable through Bee Chat and available to authorized users. Thank you for contributing to the knowledge base!</p>
                    
                    <a href="{dashboard_url}" class="btn">View Dashboard</a>
                </div>
                <div class="footer">
                    <p>🐝 This is an automated message from the STING Platform</p>
                    <p>© 2025 STING Community Edition</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_rejection_template(self, document_name: str, honey_jar_name: str, reviewer_name: str, reason: str) -> str:
        """Email template for document rejection"""
        rejection_date = datetime.now().strftime('%B %d, %Y at %I:%M %p')
        dashboard_url = self._get_dashboard_url()
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>{self._get_base_style()}</head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 Document Review Complete</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">Your document needs revisions before approval</p>
                </div>
                <div class="content">
                    <div class="alert alert-warning">
                        Your document requires some changes before it can be approved for the knowledge base.
                    </div>
                    
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Document</div>
                            <div class="info-value">{document_name}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Honey Jar</div>
                            <div class="info-value">{honey_jar_name}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Reviewed by</div>
                            <div class="info-value">{reviewer_name}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Review Date</div>
                            <div class="info-value">{rejection_date}</div>
                        </div>
                    </div>
                    
                    <div style="background: #78350f; padding: 20px; border-radius: 8px; border-left: 3px solid #f59e0b; margin: 20px 0;">
                        <div class="info-label">Feedback:</div>
                        <div style="margin-top: 10px; color: #fbbf24;">{reason or 'Please review and resubmit with any necessary changes.'}</div>
                    </div>
                    
                    <p>Please make the necessary adjustments and resubmit your document for review. We appreciate your contribution!</p>
                    
                    <a href="{dashboard_url}" class="btn">View Dashboard</a>
                </div>
                <div class="footer">
                    <p>🐝 This is an automated message from the STING Platform</p>
                    <p>© 2025 STING Community Edition</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_pending_template(self, document_name: str, honey_jar_name: str, uploader_name: str) -> str:
        """Email template for pending approval notification"""
        upload_date = datetime.now().strftime('%B %d, %Y at %I:%M %p')
        admin_url = self._get_dashboard_url() + '/admin'
        pending_count = self._get_pending_document_count()
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>{self._get_base_style()}</head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📄 Document Awaiting Approval</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">Admin action required</p>
                </div>
                <div class="content">
                    <div class="alert alert-warning">
                        A new document has been uploaded and requires your review and approval.
                    </div>
                    
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Document</div>
                            <div class="info-value">{document_name}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Honey Jar</div>
                            <div class="info-value">{honey_jar_name}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Uploaded by</div>
                            <div class="info-value">{uploader_name}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Upload Date</div>
                            <div class="info-value">{upload_date}</div>
                        </div>
                    </div>
                    
                    {f'<p><strong>📊 You have {pending_count} document(s) awaiting review</strong></p>' if pending_count > 1 else ''}
                    
                    <p>Please review this document and approve or reject it with feedback. Quick action helps maintain the knowledge base quality.</p>
                    
                    <a href="{admin_url}" class="btn">Review Document</a>
                </div>
                <div class="footer">
                    <p>🐝 This is an automated message from the STING Platform</p>
                    <p>© 2025 STING Community Edition</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_alert_template(self, alert_type: str, alert_message: str, severity: str) -> str:
        """Email template for system alerts"""
        alert_time = datetime.now().strftime('%B %d, %Y at %I:%M %p')
        dashboard_url = self._get_dashboard_url()
        
        severity_colors = {
            'low': '#10b981',
            'medium': '#f59e0b', 
            'high': '#ef4444',
            'critical': '#dc2626'
        }
        
        severity_icons = {
            'low': '💚',
            'medium': '🟡',
            'high': '🔴', 
            'critical': '🚨'
        }
        
        color = severity_colors.get(severity, '#f59e0b')
        icon = severity_icons.get(severity, '⚠️')
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>{self._get_base_style()}</head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{icon} System Alert</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9;">STING Platform Notification</p>
                </div>
                <div class="content">
                    <div class="alert alert-error">
                        <strong>{severity.upper()} Priority:</strong> {alert_type}
                    </div>
                    
                    <div style="background: #1e293b; padding: 20px; border-radius: 8px; border-left: 3px solid {color}; margin: 20px 0;">
                        <div class="info-label">Alert Details:</div>
                        <div style="margin-top: 10px; color: #e2e8f0; line-height: 1.6;">{alert_message}</div>
                    </div>
                    
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Severity Level</div>
                            <div class="info-value" style="color: {color};">{severity.title()}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Alert Time</div>
                            <div class="info-value">{alert_time}</div>
                        </div>
                    </div>
                    
                    <p>Please review the system status and take appropriate action if necessary.</p>
                    
                    <a href="{dashboard_url}" class="btn">View Dashboard</a>
                </div>
                <div class="footer">
                    <p>🐝 This is an automated message from the STING Platform</p>
                    <p>© 2025 STING Community Edition</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_dashboard_url(self) -> str:
        """Get base dashboard URL"""
        base_url = os.getenv('BASE_URL', 'https://localhost:8443')
        return f"{base_url}/dashboard"
    
    def _get_pending_document_count(self) -> int:
        """Get count of documents pending approval"""
        try:
            from app.models import Document
            from app.models import db
            count = db.session.query(Document).filter(Document.status == 'pending').count()
            return count
        except Exception:
            return 0


# Convenience function for easy import
def get_email_service() -> EmailService:
    """Get configured email service instance"""
    return EmailService()
