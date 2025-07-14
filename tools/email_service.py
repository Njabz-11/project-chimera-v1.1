"""
Project Chimera - Email Service
Handles Google/Microsoft OAuth2 authentication and email operations
"""

import os
import json
import base64
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from utils.logger import ChimeraLogger

class EmailService:
    """Manages email operations with OAuth2 authentication"""
    
    def __init__(self, credentials_path: str = "data/email_credentials.json"):
        self.logger = ChimeraLogger.get_logger(__name__)
        self.credentials_path = credentials_path
        self.token_path = "data/email_token.json"
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.compose',
            'https://www.googleapis.com/auth/gmail.modify'
        ]
        self.service = None
        self.credentials = None
        
    async def initialize(self) -> bool:
        """Initialize email service with stored credentials"""
        try:
            # Load existing token if available
            if os.path.exists(self.token_path):
                self.credentials = Credentials.from_authorized_user_file(
                    self.token_path, self.scopes
                )
            
            # Refresh token if expired
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
                self._save_credentials()
            
            # Build service if credentials are valid
            if self.credentials and self.credentials.valid:
                self.service = build('gmail', 'v1', credentials=self.credentials)
                self.logger.info("✅ Email service initialized successfully")
                return True
            else:
                self.logger.warning("⚠️ Email service requires authentication")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize email service: {e}")
            return False
    
    def get_auth_url(self) -> str:
        """Get OAuth2 authorization URL for manual authentication"""
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(f"Credentials file not found: {self.credentials_path}")
        
        flow = Flow.from_client_secrets_file(
            self.credentials_path,
            scopes=self.scopes,
            redirect_uri='http://localhost:8080/callback'
        )
        
        auth_url, _ = flow.authorization_url(prompt='consent')
        return auth_url
    
    def complete_auth(self, authorization_code: str) -> bool:
        """Complete OAuth2 flow with authorization code"""
        try:
            flow = Flow.from_client_secrets_file(
                self.credentials_path,
                scopes=self.scopes,
                redirect_uri='http://localhost:8080/callback'
            )
            
            flow.fetch_token(code=authorization_code)
            self.credentials = flow.credentials
            self._save_credentials()
            
            # Initialize service
            self.service = build('gmail', 'v1', credentials=self.credentials)
            self.logger.info("✅ Email authentication completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to complete authentication: {e}")
            return False
    
    def _save_credentials(self):
        """Save credentials to file"""
        os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
        with open(self.token_path, 'w') as token_file:
            token_file.write(self.credentials.to_json())
    
    async def list_new_messages(self, query: str = "is:unread", max_results: int = 10) -> List[Dict]:
        """List new/unread messages"""
        if not self.service:
            raise RuntimeError("Email service not initialized")
        
        try:
            # Search for messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            message_details = []
            
            for message in messages:
                # Get full message details
                msg = self.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()
                
                # Extract relevant information
                headers = msg['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                # Get message body
                body = self._extract_message_body(msg['payload'])
                
                message_details.append({
                    'id': message['id'],
                    'thread_id': msg['threadId'],
                    'subject': subject,
                    'sender': sender,
                    'date': date,
                    'body': body,
                    'snippet': msg.get('snippet', '')
                })
            
            self.logger.info(f"📧 Retrieved {len(message_details)} new messages")
            return message_details
            
        except HttpError as e:
            self.logger.error(f"❌ Failed to list messages: {e}")
            return []
    
    async def get_full_conversation_thread(self, thread_id: str) -> List[Dict]:
        """Get full conversation thread by thread ID"""
        if not self.service:
            raise RuntimeError("Email service not initialized")
        
        try:
            # Get thread details
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id,
                format='full'
            ).execute()
            
            messages = []
            for message in thread['messages']:
                headers = message['payload'].get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                body = self._extract_message_body(message['payload'])
                
                messages.append({
                    'id': message['id'],
                    'subject': subject,
                    'sender': sender,
                    'date': date,
                    'body': body,
                    'snippet': message.get('snippet', '')
                })
            
            self.logger.info(f"📧 Retrieved conversation thread with {len(messages)} messages")
            return messages
            
        except HttpError as e:
            self.logger.error(f"❌ Failed to get conversation thread: {e}")
            return []
    
    def _extract_message_body(self, payload: Dict) -> str:
        """Extract message body from payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
        elif payload['mimeType'] == 'text/plain':
            data = payload['body'].get('data', '')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return body
    
    async def create_draft(self, to: str, subject: str, body: str, 
                          reply_to_message_id: Optional[str] = None) -> Optional[str]:
        """Create email draft"""
        if not self.service:
            raise RuntimeError("Email service not initialized")
        
        try:
            # Create message
            message = {
                'raw': self._create_message_raw(to, subject, body, reply_to_message_id)
            }
            
            # Create draft
            draft = self.service.users().drafts().create(
                userId='me',
                body={'message': message}
            ).execute()
            
            draft_id = draft['id']
            self.logger.info(f"📝 Created email draft {draft_id}")
            return draft_id
            
        except HttpError as e:
            self.logger.error(f"❌ Failed to create draft: {e}")
            return None
    
    async def send_email(self, to: str, subject: str, body: str,
                        reply_to_message_id: Optional[str] = None) -> bool:
        """Send email directly (use with caution)"""
        if not self.service:
            raise RuntimeError("Email service not initialized")
        
        try:
            # Create message
            message = {
                'raw': self._create_message_raw(to, subject, body, reply_to_message_id)
            }
            
            # Send message
            sent_message = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            
            self.logger.info(f"📤 Sent email {sent_message['id']}")
            return True
            
        except HttpError as e:
            self.logger.error(f"❌ Failed to send email: {e}")
            return False
    
    def _create_message_raw(self, to: str, subject: str, body: str, 
                           reply_to_message_id: Optional[str] = None) -> str:
        """Create raw email message"""
        import email.mime.text
        import email.mime.multipart
        
        message = email.mime.text.MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        
        if reply_to_message_id:
            message['In-Reply-To'] = reply_to_message_id
            message['References'] = reply_to_message_id
        
        return base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    async def mark_as_read(self, message_id: str) -> bool:
        """Mark message as read"""
        if not self.service:
            raise RuntimeError("Email service not initialized")
        
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            self.logger.debug(f"✅ Marked message {message_id} as read")
            return True
            
        except HttpError as e:
            self.logger.error(f"❌ Failed to mark message as read: {e}")
            return False
