import boto3
from botocore.exceptions import ClientError
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from app.core.config import settings
from app.models.workflow import EmailLog
from sqlalchemy.orm import Session


class EmailService:
    """Service for sending emails via AWS SES or SMTP"""
    
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.ses_client = self._setup_ses_client()
        self.email_provider = settings.EMAIL_PROVIDER  # 'ses' or 'smtp'
    
    def _setup_ses_client(self):
        """Setup AWS SES client"""
        try:
            if settings.AWS_SES_ACCESS_KEY_ID and settings.AWS_SES_SECRET_ACCESS_KEY:
                return boto3.client(
                    'ses',
                    aws_access_key_id=settings.AWS_SES_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SES_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_SES_REGION
                )
            return None
        except Exception as e:
            self.logger.error(f"Failed to setup SES client: {str(e)}")
            return None
    
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        body: str, 
        to_name: Optional[str] = None,
        email_type: str = "general",
        candidate_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        is_html: bool = False
    ) -> Dict[str, Any]:
        """Send email using AWS SES or SMTP fallback"""
        
        # Choose email provider
        if self.email_provider == "ses" and self.ses_client:
            return await self._send_via_ses(
                to_email=to_email,
                subject=subject,
                body=body,
                to_name=to_name,
                email_type=email_type,
                candidate_id=candidate_id,
                workflow_id=workflow_id,
                cc_emails=cc_emails,
                bcc_emails=bcc_emails,
                is_html=is_html
            )
        else:
            return await self._send_via_smtp(
                to_email=to_email,
                subject=subject,
                body=body,
                to_name=to_name,
                email_type=email_type,
                candidate_id=candidate_id,
                workflow_id=workflow_id,
                cc_emails=cc_emails,
                bcc_emails=bcc_emails,
                attachments=attachments
            )
    
    async def _send_via_ses(
        self,
        to_email: str,
        subject: str,
        body: str,
        to_name: Optional[str] = None,
        email_type: str = "general",
        candidate_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        is_html: bool = False
    ) -> Dict[str, Any]:
        """Send email via AWS SES"""
        try:
            # Prepare recipient
            if to_name:
                destination_to = [f"{to_name} <{to_email}>"]
            else:
                destination_to = [to_email]
            
            # Prepare email destinations
            destinations = {
                'ToAddresses': destination_to
            }
            
            if cc_emails:
                destinations['CcAddresses'] = cc_emails
            
            if bcc_emails:
                destinations['BccAddresses'] = bcc_emails
            
            # Prepare email content
            email_content = {
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                }
            }
            
            if is_html:
                email_content['Body'] = {
                    'Html': {
                        'Data': body,
                        'Charset': 'UTF-8'
                    },
                    'Text': {
                        'Data': self._html_to_text(body),
                        'Charset': 'UTF-8'
                    }
                }
            else:
                email_content['Body'] = {
                    'Text': {
                        'Data': body,
                        'Charset': 'UTF-8'
                    }
                }
            
            # Send email
            response = self.ses_client.send_email(
                Source=settings.COMPANY_EMAIL,
                Destination=destinations,
                Message=email_content,
                ReplyToAddresses=[settings.COMPANY_EMAIL],
                Tags=[
                    {
                        'Name': 'EmailType',
                        'Value': email_type
                    },
                    {
                        'Name': 'System',
                        'Value': 'HiringAgent'
                    }
                ]
            )
            
            message_id = response.get('MessageId', '')
            
            # Log successful send
            await self._log_email(
                email_type=email_type,
                recipient_email=to_email,
                recipient_name=to_name,
                subject=subject,
                body=body,
                sent_successfully=True,
                candidate_id=candidate_id,
                workflow_id=workflow_id,
                message_id=message_id,
                provider="ses"
            )
            
            self.logger.info(f"Email sent successfully via SES: {message_id}")
            return {
                "success": True, 
                "message": "Email sent successfully via SES",
                "message_id": message_id,
                "provider": "ses"
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            error_msg = f"SES Error [{error_code}]: {error_message}"
            
            self.logger.error(error_msg)
            
            # Log failed send
            await self._log_email(
                email_type=email_type,
                recipient_email=to_email,
                recipient_name=to_name,
                subject=subject,
                body=body,
                sent_successfully=False,
                error_message=error_msg,
                candidate_id=candidate_id,
                workflow_id=workflow_id,
                provider="ses"
            )
            
            return {"success": False, "error": error_msg, "provider": "ses"}
            
        except Exception as e:
            error_msg = f"SES sending failed: {str(e)}"
            self.logger.error(error_msg)
            
            # Log failed send
            await self._log_email(
                email_type=email_type,
                recipient_email=to_email,
                recipient_name=to_name,
                subject=subject,
                body=body,
                sent_successfully=False,
                error_message=error_msg,
                candidate_id=candidate_id,
                workflow_id=workflow_id,
                provider="ses"
            )
            
            return {"success": False, "error": error_msg, "provider": "ses"}
    
    async def _send_via_smtp(
        self,
        to_email: str,
        subject: str,
        body: str,
        to_name: Optional[str] = None,
        email_type: str = "general",
        candidate_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send email via SMTP (fallback method)"""
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = settings.COMPANY_EMAIL
            msg['To'] = f"{to_name} <{to_email}>" if to_name else to_email
            msg['Subject'] = subject
            
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Add attachments if any
            if attachments:
                for attachment in attachments:
                    self._add_attachment(msg, attachment)
            
            # Prepare recipient list
            recipients = [to_email]
            if cc_emails:
                recipients.extend(cc_emails)
            if bcc_emails:
                recipients.extend(bcc_emails)
            
            # Send email
            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            text = msg.as_string()
            server.sendmail(settings.SMTP_USERNAME, recipients, text)
            server.quit()
            
            # Log successful send
            await self._log_email(
                email_type=email_type,
                recipient_email=to_email,
                recipient_name=to_name,
                subject=subject,
                body=body,
                sent_successfully=True,
                candidate_id=candidate_id,
                workflow_id=workflow_id,
                provider="smtp"
            )
            
            return {
                "success": True, 
                "message": "Email sent successfully via SMTP",
                "provider": "smtp"
            }
            
        except Exception as e:
            error_msg = f"SMTP sending failed: {str(e)}"
            self.logger.error(error_msg)
            
            # Log failed send
            await self._log_email(
                email_type=email_type,
                recipient_email=to_email,
                recipient_name=to_name,
                subject=subject,
                body=body,
                sent_successfully=False,
                error_message=error_msg,
                candidate_id=candidate_id,
                workflow_id=workflow_id,
                provider="smtp"
            )
            
            return {"success": False, "error": error_msg, "provider": "smtp"}
    
    def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """Add attachment to email message"""
        try:
            with open(attachment['file_path'], "rb") as attachment_file:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment_file.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {attachment["filename"]}'
            )
            msg.attach(part)
        except Exception as e:
            self.logger.error(f"Failed to add attachment: {str(e)}")
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML content to plain text"""
        # Simple HTML to text conversion
        # For production, consider using libraries like BeautifulSoup
        import re
        text = re.sub('<[^<]+?>', '', html_content)
        return text.strip()
    
    async def _log_email(
        self,
        email_type: str,
        recipient_email: str,
        subject: str,
        body: str,
        sent_successfully: bool,
        recipient_name: Optional[str] = None,
        error_message: Optional[str] = None,
        candidate_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        message_id: Optional[str] = None,
        provider: str = "smtp"
    ):
        """Log email to database"""
        try:
            from uuid import UUID
            
            email_log = EmailLog(
                candidate_id=UUID(candidate_id) if candidate_id else None,
                workflow_id=UUID(workflow_id) if workflow_id else None,
                email_type=email_type,
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                subject=subject,
                body=body,
                sent_at=datetime.now() if sent_successfully else None,
                sent_successfully=sent_successfully,
                error_message=error_message,
                message_id=message_id,
                provider=provider
            )
            
            self.db.add(email_log)
            self.db.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to log email: {str(e)}")
            self.db.rollback()
    
    async def verify_email_address(self, email: str) -> Dict[str, Any]:
        """Verify email address with SES (for production use)"""
        if not self.ses_client:
            return {"success": False, "error": "SES client not configured"}
        
        try:
            response = self.ses_client.get_identity_verification_attributes(
                Identities=[email]
            )
            
            verification_attrs = response.get('VerificationAttributes', {})
            email_status = verification_attrs.get(email, {})
            
            return {
                "success": True,
                "email": email,
                "verification_status": email_status.get('VerificationStatus', 'NotStarted'),
                "verification_token": email_status.get('VerificationToken', '')
            }
            
        except ClientError as e:
            return {
                "success": False,
                "error": f"SES verification error: {e.response['Error']['Message']}"
            }
    
    async def get_send_statistics(self) -> Dict[str, Any]:
        """Get SES send statistics"""
        if not self.ses_client:
            return {"success": False, "error": "SES client not configured"}
        
        try:
            response = self.ses_client.get_send_statistics()
            return {
                "success": True,
                "statistics": response.get('SendDataPoints', []),
                "reputation": {
                    "bounce_rate": "N/A",  # Calculate from statistics if needed
                    "complaint_rate": "N/A"
                }
            }
        except ClientError as e:
            return {
                "success": False,
                "error": f"Failed to get statistics: {e.response['Error']['Message']}"
            }
    
    async def send_bulk_email(
        self,
        recipients: List[Dict[str, str]],  # [{"email": "...", "name": "..."}]
        subject: str,
        body: str,
        email_type: str = "bulk",
        is_html: bool = False
    ) -> Dict[str, Any]:
        """Send bulk emails using SES (more efficient for multiple recipients)"""
        if not self.ses_client:
            return await self._send_bulk_via_smtp(recipients, subject, body, email_type)
        
        try:
            successful_sends = []
            failed_sends = []
            
            # SES has a limit of 50 recipients per call, so we batch them
            batch_size = 50
            for i in range(0, len(recipients), batch_size):
                batch = recipients[i:i + batch_size]
                
                destinations = [
                    {
                        'Destination': {
                            'ToAddresses': [f"{recipient['name']} <{recipient['email']}>" if recipient.get('name') else recipient['email']]
                        },
                        'ReplacementTags': [
                            {
                                'Name': 'name',
                                'Value': recipient.get('name', 'Candidate')
                            }
                        ]
                    }
                    for recipient in batch
                ]
                
                # Prepare template data
                email_content = {
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8'
                    }
                }
                
                if is_html:
                    email_content['Body'] = {
                        'Html': {
                            'Data': body,
                            'Charset': 'UTF-8'
                        }
                    }
                else:
                    email_content['Body'] = {
                        'Text': {
                            'Data': body,
                            'Charset': 'UTF-8'
                        }
                    }
                
                # Send batch
                response = self.ses_client.send_bulk_templated_email(
                    Source=settings.COMPANY_EMAIL,
                    Template='DefaultTemplate',  # You'd need to create this template in SES
                    DefaultTemplateData='{}',
                    Destinations=destinations
                )
                
                # Process response
                for idx, status in enumerate(response.get('Status', [])):
                    recipient = batch[idx]
                    if status.get('Status') == 'Success':
                        successful_sends.append({
                            'email': recipient['email'],
                            'message_id': status.get('MessageId', '')
                        })
                    else:
                        failed_sends.append({
                            'email': recipient['email'],
                            'error': status.get('Error', 'Unknown error')
                        })
            
            return {
                "success": True,
                "total_recipients": len(recipients),
                "successful_sends": len(successful_sends),
                "failed_sends": len(failed_sends),
                "details": {
                    "successful": successful_sends,
                    "failed": failed_sends
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Bulk email sending failed: {str(e)}"
            }
    
    async def _send_bulk_via_smtp(
        self,
        recipients: List[Dict[str, str]],
        subject: str,
        body: str,
        email_type: str = "bulk"
    ) -> Dict[str, Any]:
        """Send bulk emails via SMTP (fallback)"""
        successful_sends = []
        failed_sends = []
        
        for recipient in recipients:
            result = await self._send_via_smtp(
                to_email=recipient['email'],
                to_name=recipient.get('name'),
                subject=subject,
                body=body,
                email_type=email_type
            )
            
            if result['success']:
                successful_sends.append(recipient['email'])
            else:
                failed_sends.append({
                    'email': recipient['email'],
                    'error': result['error']
                })
        
        return {
            "success": True,
            "total_recipients": len(recipients),
            "successful_sends": len(successful_sends),
            "failed_sends": len(failed_sends),
            "details": {
                "successful": successful_sends,
                "failed": failed_sends
            }
        }
