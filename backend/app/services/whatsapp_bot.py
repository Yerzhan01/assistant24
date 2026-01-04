from __future__ import annotations
"""WhatsApp bot integration using GreenAPI.

Based on official GreenAPI documentation:
- API URL: https://api.green-api.com
- Media URL: https://media.green-api.com
"""
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.i18n import t
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai_router import AIRouter

# Configure logging
logger = logging.getLogger(__name__)


class WhatsAppBotService:
    """
    Service for managing WhatsApp interactions via GreenAPI.
    Supports multiple instances (one per tenant).
    
    API Docs: https://green-api.com/docs/api/
    """
    
    GREENAPI_BASE_URL = "https://api.green-api.com"
    GREENAPI_MEDIA_URL = "https://media.green-api.com"
    
    def __init__(self) -> None:
        self._clients: Dict[UUID, httpx.AsyncClient] = {}
    
    def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client."""
        return httpx.AsyncClient(timeout=30.0)
    
    def _build_url(self, instance_id: str, token: str, method: str, use_media: bool = False) -> str:
        """Build API URL."""
        base = self.GREENAPI_MEDIA_URL if use_media else self.GREENAPI_BASE_URL
        return f"{base}/waInstance{instance_id}/{method}/{token}"
    
    def _format_chat_id(self, phone: str, is_group: bool = False) -> str:
        """Format phone number to chat ID."""
        # Remove + and any spaces/dashes
        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
        suffix = "@g.us" if is_group else "@c.us"
        return f"{clean_phone}{suffix}"
    
    # ==================== Account Methods ====================
    
    async def get_state_instance(self, instance_id: str, token: str) -> Dict[str, Any]:
        """Get account state (authorized, notAuthorized, blocked, etc.)."""
        url = self._build_url(instance_id, token, "getStateInstance")
        
        async with self._get_client() as client:
            response = await client.get(url)
            return response.json()
    
    async def get_settings(self, instance_id: str, token: str) -> Dict[str, Any]:
        """Get account settings."""
        url = self._build_url(instance_id, token, "getSettings")
        
        async with self._get_client() as client:
            response = await client.get(url)
            return response.json()
    
    async def set_settings(
        self, 
        instance_id: str, 
        token: str,
        webhook_url: str = "",
        incoming_webhook: str = "yes",
        outgoing_webhook: str = "no"
    ) -> Dict[str, Any]:
        """Set account settings."""
        url = self._build_url(instance_id, token, "setSettings")
        
        payload = {
            "webhookUrl": webhook_url,
            "webhookUrlToken": "",
            "delaySendMessagesMilliseconds": 3000,
            "markIncomingMessagesReaded": "no",
            "markIncomingMessagesReadedOnReply": "yes",
            "outgoingWebhook": "yes",
            "outgoingMessageWebhook": "yes",
            "outgoingAPIMessageWebhook": "yes",
            "incomingWebhook": incoming_webhook,
            "stateWebhook": "yes",
            "keepOnlineStatus": "yes",
            "pollMessageWebhook": "yes",
            "incomingCallWebhook": "yes"
        }
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    async def get_qr(self, instance_id: str, token: str) -> Dict[str, Any]:
        """Get QR code for authentication."""
        url = self._build_url(instance_id, token, "qr")
        
        async with self._get_client() as client:
            response = await client.get(url)
            return response.json()
    
    async def reboot(self, instance_id: str, token: str) -> Dict[str, Any]:
        """Reboot instance."""
        url = self._build_url(instance_id, token, "reboot")
        
        async with self._get_client() as client:
            response = await client.get(url)
            return response.json()
    
    async def logout(self, instance_id: str, token: str) -> Dict[str, Any]:
        """Logout from WhatsApp."""
        url = self._build_url(instance_id, token, "logout")
        
        async with self._get_client() as client:
            response = await client.get(url)
            return response.json()
    
    # ==================== Sending Methods ====================
    
    async def send_message(
        self,
        instance_id: str,
        token: str,
        phone: str,
        message: str,
        quoted_message_id:Optional[ str ] = None,
        link_preview: bool = True
    ) -> Dict[str, Any]:
        """Send a text message."""
        url = self._build_url(instance_id, token, "sendMessage")
        chat_id = self._format_chat_id(phone)
        
        payload = {
            "chatId": chat_id,
            "message": message,
            "linkPreview": link_preview
        }
        
        if quoted_message_id:
            payload["quotedMessageId"] = quoted_message_id
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    async def send_file_by_url(
        self,
        instance_id: str,
        token: str,
        phone: str,
        url_file: str,
        file_name: str,
        caption: str = ""
    ) -> Dict[str, Any]:
        """Send file by URL."""
        url = self._build_url(instance_id, token, "sendFileByUrl")
        chat_id = self._format_chat_id(phone)
        
        payload = {
            "chatId": chat_id,
            "urlFile": url_file,
            "fileName": file_name,
            "caption": caption
        }
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    async def send_location(
        self,
        instance_id: str,
        token: str,
        phone: str,
        latitude: float,
        longitude: float,
        name_location: str = "",
        address: str = ""
    ) -> Dict[str, Any]:
        """Send location."""
        url = self._build_url(instance_id, token, "sendLocation")
        chat_id = self._format_chat_id(phone)
        
        payload = {
            "chatId": chat_id,
            "nameLocation": name_location,
            "address": address,
            "latitude": latitude,
            "longitude": longitude
        }
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    async def send_contact(
        self,
        instance_id: str,
        token: str,
        phone: str,
        contact_phone: int,
        first_name: str,
        last_name: str = "",
        middle_name: str = "",
        company: str = ""
    ) -> Dict[str, Any]:
        """Send contact."""
        url = self._build_url(instance_id, token, "sendContact")
        chat_id = self._format_chat_id(phone)
        
        payload = {
            "chatId": chat_id,
            "contact": {
                "phoneContact": contact_phone,
                "firstName": first_name,
                "lastName": last_name,
                "middleName": middle_name,
                "company": company
            }
        }
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    async def send_poll(
        self,
        instance_id: str,
        token: str,
        phone: str,
        question: str,
        options: List[str],
        multiple_answers: bool = False
    ) -> Dict[str, Any]:
        """Send a poll."""
        url = self._build_url(instance_id, token, "sendPoll")
        chat_id = self._format_chat_id(phone)
        
        payload = {
            "chatId": chat_id,
            "message": question,
            "options": [{"optionName": opt} for opt in options],
            "multipleAnswers": multiple_answers
        }
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    async def forward_messages(
        self,
        instance_id: str,
        token: str,
        to_phone: str,
        from_chat_id: str,
        message_ids: List[str]
    ) -> Dict[str, Any]:
        """Forward messages."""
        url = self._build_url(instance_id, token, "forwardMessages")
        chat_id = self._format_chat_id(to_phone)
        
        payload = {
            "chatId": chat_id,
            "chatIdFrom": from_chat_id,
            "messages": message_ids
        }
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    # ==================== Receiving Methods ====================
    
    async def receive_notification(
        self, 
        instance_id: str, 
        token: str,
        receive_timeout: int = 5
    ) ->Optional[ Dict[str, Any] ]:
        """Receive notification from queue."""
        url = self._build_url(instance_id, token, "receiveNotification")
        
        async with self._get_client() as client:
            response = await client.get(url, params={"receiveTimeout": receive_timeout})
            data = response.json()
            return data if data else None
    
    async def delete_notification(
        self, 
        instance_id: str, 
        token: str,
        receipt_id: int
    ) -> Dict[str, Any]:
        """Delete notification from queue."""
        url = f"{self.GREENAPI_BASE_URL}/waInstance{instance_id}/deleteNotification/{token}/{receipt_id}"
        
        async with self._get_client() as client:
            response = await client.delete(url)
            return response.json()
    
    async def download_file(
        self,
        instance_id: str,
        token: str,
        chat_id: str,
        id_message: str
    ) -> Dict[str, Any]:
        """Download file from incoming message."""
        url = self._build_url(instance_id, token, "downloadFile")
        
        payload = {
            "chatId": chat_id,
            "idMessage": id_message
        }
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    # ==================== Journals Methods ====================
    
    async def get_chat_history(
        self,
        instance_id: str,
        token: str,
        chat_id: str,
        count: int = 100
    ) -> List[Dict[str, Any]]:
        """Get chat history."""
        url = self._build_url(instance_id, token, "getChatHistory")
        
        payload = {
            "chatId": chat_id,
            "count": count
        }
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    async def get_message(
        self,
        instance_id: str,
        token: str,
        chat_id: str,
        id_message: str
    ) -> Dict[str, Any]:
        """Get specific message."""
        url = self._build_url(instance_id, token, "getMessage")
        
        payload = {
            "chatId": chat_id,
            "idMessage": id_message
        }
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    # ==================== Groups Methods ====================
    
    async def get_chats(
        self,
        instance_id: str,
        token: str
    ) -> List[Dict[str, Any]]:
        """Get all chats (contacts and groups).
        
        Returns list of chats with format:
        - id: chat ID (phone@c.us or groupId@g.us)
        - name: chat name
        - type: 'contact' or 'group'
        """
        url = self._build_url(instance_id, token, "getChats")
        
        async with self._get_client() as client:
            response = await client.get(url)
            data = response.json()
            
            # Filter only groups
            return data if isinstance(data, list) else []
    
    async def create_group(
        self,
        instance_id: str,
        token: str,
        group_name: str,
        chat_ids: List[str]
    ) -> Dict[str, Any]:
        """Create a new group."""
        url = self._build_url(instance_id, token, "createGroup")
        
        payload = {
            "groupName": group_name,
            "chatIds": chat_ids
        }
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    async def update_group_name(
        self,
        instance_id: str,
        token: str,
        group_id: str,
        group_name: str
    ) -> Dict[str, Any]:
        """Update group name."""
        url = self._build_url(instance_id, token, "updateGroupName")
        
        payload = {
            "groupId": group_id,
            "groupName": group_name
        }
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    async def get_group_data(
        self,
        instance_id: str,
        token: str,
        group_id: str
    ) -> Dict[str, Any]:
        """Get group info (name, participants, admins, etc.)."""
        url = self._build_url(instance_id, token, "getGroupData")
        
        payload = {"groupId": group_id}
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    async def add_group_participant(
        self,
        instance_id: str,
        token: str,
        group_id: str,
        participant_chat_id: str
    ) -> Dict[str, Any]:
        """Add participant to group."""
        url = self._build_url(instance_id, token, "addGroupParticipant")
        
        payload = {
            "groupId": group_id,
            "participantChatId": participant_chat_id
        }
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    async def remove_group_participant(
        self,
        instance_id: str,
        token: str,
        group_id: str,
        participant_chat_id: str
    ) -> Dict[str, Any]:
        """Remove participant from group."""
        url = self._build_url(instance_id, token, "removeGroupParticipant")
        
        payload = {
            "groupId": group_id,
            "participantChatId": participant_chat_id
        }
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    async def set_group_admin(
        self,
        instance_id: str,
        token: str,
        group_id: str,
        participant_chat_id: str
    ) -> Dict[str, Any]:
        """Set participant as group admin."""
        url = self._build_url(instance_id, token, "setGroupAdmin")
        
        payload = {
            "groupId": group_id,
            "participantChatId": participant_chat_id
        }
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    async def remove_admin(
        self,
        instance_id: str,
        token: str,
        group_id: str,
        participant_chat_id: str
    ) -> Dict[str, Any]:
        """Remove admin rights from participant."""
        url = self._build_url(instance_id, token, "removeAdmin")
        
        payload = {
            "groupId": group_id,
            "participantChatId": participant_chat_id
        }
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    async def set_group_picture(
        self,
        instance_id: str,
        token: str,
        group_id: str,
        file_path: str
    ) -> Dict[str, Any]:
        """Set group picture from file."""
        url = self._build_url(instance_id, token, "setGroupPicture", use_media=True)
        
        async with self._get_client() as client:
            with open(file_path, "rb") as f:
                files = {"file": f}
                data = {"groupId": group_id}
                response = await client.post(url, data=data, files=files)
                return response.json()
    
    async def leave_group(
        self,
        instance_id: str,
        token: str,
        group_id: str
    ) -> Dict[str, Any]:
        """Leave group."""
        url = self._build_url(instance_id, token, "leaveGroup")
        
        payload = {"groupId": group_id}
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    # ==================== File Upload Methods ====================
    
    async def upload_file(
        self,
        instance_id: str,
        token: str,
        file_path: str,
        content_type: str = "application/octet-stream"
    ) -> Dict[str, Any]:
        """
        Upload file to GreenAPI storage.
        Returns URL that can be used with sendFileByUrl.
        """
        url = self._build_url(instance_id, token, "uploadFile", use_media=True)
        
        async with self._get_client() as client:
            with open(file_path, "rb") as f:
                content = f.read()
                headers = {"Content-Type": content_type}
                response = await client.post(url, content=content, headers=headers)
                return response.json()
    
    async def send_file_by_upload(
        self,
        instance_id: str,
        token: str,
        phone: str,
        file_path: str,
        file_name: str,
        caption: str = ""
    ) -> Dict[str, Any]:
        """
        Send file by uploading directly.
        Uses multipart/form-data.
        """
        url = self._build_url(instance_id, token, "sendFileByUpload", use_media=True)
        chat_id = self._format_chat_id(phone)
        
        async with self._get_client() as client:
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f)}
                data = {
                    "chatId": chat_id,
                    "fileName": file_name,
                    "caption": caption
                }
                response = await client.post(url, data=data, files=files)
                return response.json()
    
    # ==================== Interactive Buttons Methods ====================
    
    async def send_interactive_buttons(
        self,
        instance_id: str,
        token: str,
        phone: str,
        body: str,
        buttons: List[Dict[str, Any]],
        header: str = "",
        footer: str = ""
    ) -> Dict[str, Any]:
        """
        Send interactive buttons (copy, call, url types).
        
        buttons format:
        [
            {"type": "copy", "buttonId": "1", "buttonText": "Copy", "copyCode": "Text to copy"},
            {"type": "call", "buttonId": "2", "buttonText": "Call", "phoneNumber": "79001234567"},
            {"type": "url", "buttonId": "3", "buttonText": "Website", "url": "https://example.com"}
        ]
        """
        url = self._build_url(instance_id, token, "sendInteractiveButtons")
        chat_id = self._format_chat_id(phone)
        
        payload = {
            "chatId": chat_id,
            "header": header,
            "body": body,
            "footer": footer,
            "buttons": buttons
        }
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    async def send_interactive_buttons_reply(
        self,
        instance_id: str,
        token: str,
        phone: str,
        body: str,
        buttons: List[Dict[str, str]],
        header: str = "",
        footer: str = ""
    ) -> Dict[str, Any]:
        """
        Send buttons with reply (max 3 buttons).
        
        buttons format:
        [
            {"buttonId": "1", "buttonText": "First Button"},
            {"buttonId": "2", "buttonText": "Second Button"},
            {"buttonId": "3", "buttonText": "Third Button"}
        ]
        """
        url = self._build_url(instance_id, token, "sendInteractiveButtonsReply")
        chat_id = self._format_chat_id(phone)
        
        payload = {
            "chatId": chat_id,
            "header": header,
            "body": body,
            "footer": footer,
            "buttons": buttons
        }
        
        async with self._get_client() as client:
            response = await client.post(url, json=payload)
            return response.json()
    
    # ==================== Group Messages Reading ====================
    
    async def get_group_messages(
        self,
        instance_id: str,
        token: str,
        group_id: str,
        count: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get messages from a group chat.
        Uses getChatHistory with group ID.
        """
        return await self.get_chat_history(instance_id, token, group_id, count)
    
    async def read_group_message(
        self,
        instance_id: str,
        token: str,
        group_id: str,
        message_id: str
    ) -> Dict[str, Any]:
        """Get specific message from group."""
        return await self.get_message(instance_id, token, group_id, message_id)
    
    # ==================== Webhook Processing ====================
    
    async def process_webhook(
        self,
        tenant_id: UUID,
        webhook_data: Dict[str, Any]
    ) ->Optional[ dict ]:
        """Process incoming GreenAPI webhook."""
        async with async_session_maker() as db:
            # Get tenant
            tenant = await db.get(Tenant, tenant_id)
            if not tenant or not tenant.greenapi_instance_id:
                logger.warning(f"Tenant {tenant_id} not found or no GreenAPI config")
                return None
            
            # Parse webhook type
            webhook_type = webhook_data.get("typeWebhook")
            
            if webhook_type == "incomingMessageReceived":
                return await self._handle_incoming_message(db, tenant, webhook_data, is_outgoing=False)
            elif webhook_type in ("outgoingMessageStatus", "outgoingAPIMessageReceived", "outgoingMessageReceived"):
                # Shadow Mode: Handle outgoing messages from user's phone
                # We process them silently (silent_response=True) to create tasks/events but NOT reply
                return await self._handle_incoming_message(db, tenant, webhook_data, is_outgoing=True)
            elif webhook_type == "stateInstanceChanged":
                return await self._handle_state_change(tenant, webhook_data)
            
            return {"status": "ignored", "type": webhook_type}
    
    async def _handle_state_change(
        self,
        tenant: Tenant,
        webhook_data: Dict[str, Any]
    ) -> dict:
        """Handle instance state change."""
        state = webhook_data.get("stateInstance")
        logger.info(f"Tenant {tenant.id} WhatsApp state: {state}")
        return {"status": "ok", "state": state}
    
    async def _handle_incoming_message(
        self,
        db: AsyncSession,
        tenant: Tenant,
        webhook_data: Dict[str, Any],
        is_outgoing: bool = False
    ) -> dict:
        """Handle incoming WhatsApp message (personal or group)."""
        message_data = webhook_data.get("messageData", {})
        sender_data = webhook_data.get("senderData", {})
        instance_data = webhook_data.get("instanceData", {})
        
        # Get chat ID to determine if group or personal message
        chat_id = sender_data.get("chatId", "")
        is_group = chat_id.endswith("@g.us")
        
        # Get message type
        message_type = message_data.get("typeMessage", "")
        message_id = webhook_data.get("idMessage", "")
        
        # Get message text based on type
        message_text = None
        
        if message_type == "textMessage":
            text_data = message_data.get("textMessageData", {})
            message_text = text_data.get("textMessage", "")
        elif message_type == "extendedTextMessage":
            ext_data = message_data.get("extendedTextMessageData", {})
            message_text = ext_data.get("text", "")
        elif message_type in ("audioMessage", "voiceMessage"):
             # 🎤 Handle Voice Message
             from app.services.voice_transcriber import get_transcriber
             
             file_id = webhook_data.get("idMessage", "") # Use ID for download
             # Actually GreenAPI has fileUrl in message data sometimes, or we use downloadFile
             # Official way: downloadFile
             
             try:
                 # Download
                 download_res = await self.download_file(
                     tenant.greenapi_instance_id,
                     tenant.greenapi_token,
                     chat_id,
                     file_id
                 )
                 
                 download_url = download_res.get("urlFile")
                 if download_url:
                     async with httpx.AsyncClient() as client:
                         audio_resp = await client.get(download_url)
                         if audio_resp.status_code == 200:
                             # Transcribe
                             transcriber = get_transcriber()
                             transcribed_text = await transcriber.transcribe(
                                 audio_resp.content,
                                 language=tenant.language or "ru"
                             )
                             if transcribed_text:
                                 message_text = f"[Voice Message]: {transcribed_text}"
                             else:
                                 message_text = "[Voice Message] (Transcription failed)"
             except Exception as e:
                 logger.error(f"Voice processing failed: {e}")
                 message_text = "[Voice Message] (Error processing)"

        elif message_type in ("imageMessage", "videoMessage"):
            # 🖼️ Handle Image/Video (Photo Accountant)
            file_id = webhook_data.get("idMessage", "")
            
            # Use caption if exists, or label as [Image]
            caption = message_data.get("caption", "")
            message_text = f"[Image] {caption}"
            
            try:
                # Always download image for analysis
                download_res = await self.download_file(
                    tenant.greenapi_instance_id,
                    tenant.greenapi_token,
                    chat_id,
                    file_id
                )
                
                download_url = download_res.get("urlFile")
                if download_url:
                    async with httpx.AsyncClient() as client:
                        img_resp = await client.get(download_url)
                        if img_resp.status_code == 200:
                            # Pass image bytes to AIRouter via `image_data`
                            image_bytes = img_resp.content
                            
                            router = AIRouter(db, api_key=tenant.gemini_api_key or settings.gemini_api_key, language=tenant.language or "ru")
                            await router.process_message(
                                message=message_text,
                                tenant_id=tenant.id,
                                user_id=user.id,
                                image_data=image_bytes
                            )
                            
                            return {"status": "ok", "mode": "photo_accountant"}
                            
            except Exception as e:
                logger.error(f"Image download failed: {e}")
                # Fallback: process just caption if image fails
                pass
        
        elif message_type == "documentMessage":
             message_text = message_data.get("caption", "[Document]")
        
        if not message_text:
            return {"status": "ignored", "reason": "no text content"}
        
        # Handle incoming/outgoing message with Shadow Mode logic
        
        # 1. Check if it's an OUTGOING message (Shadow Mode)
        is_outgoing = message_type == "outgoingMessage" or webhook_data.get("typeWebhook") in ("outgoingMessageWebhook", "outgoingAPIMessageWebhook")
        
        # If outgoing, we just want to track it for context/tasks, but NEVER reply
        if is_outgoing:
            # For outgoing messages, sender is US. 
            # We need to find the user who owns this instance (or specific user if mapped)
            # In single-tenant model, it's the tenant owner usually.
            # But let's assume the user is the one associated with this phone number or system user.
            
            # Use AIRouter in SILENT mode (analyze_only=True)
            # We treat text as user input, but router knows not to reply
            
            # Find the user (sender)
            # Ideally we map instance to user. For now use first admin or owner.
            stmt = select(User).where(User.tenant_id == tenant.id).limit(1)
            result = await db.execute(stmt)
            user = result.scalars().first()
            
            if user:
                # Log outgoing message to history
                from app.models.chat_message import ChatMessage
                chat_msg = ChatMessage(
                    tenant_id=tenant.id,
                    chat_id=str(chat_id),
                    role="user",
                    content=f"[Me]: {message_text}"
                )
                db.add(chat_msg)
                
                # Analyze silently (Shadow Mode)
                api_key = tenant.gemini_api_key or settings.gemini_api_key
                if api_key:
                    router = AIRouter(db, api_key=api_key, language=tenant.language or "ru")
                    await router.process_message(
                        message=message_text,
                        tenant_id=tenant.id,
                        user_id=user.id,
                        silent_response=True
                    )
            
            await db.commit()
            return {"status": "ok", "mode": "shadow_outgoing"}

        # 2. INCOMING Message Handling
        
        # Get sender info
        sender_phone = sender_data.get("sender", "").replace("@c.us", "").replace("@g.us", "")
        sender_name = sender_data.get("senderName", sender_phone)
        sender_contact_name = sender_data.get("senderContactName", "")
        
        # For group messages, get the actual sender (participant)
        if is_group:
            participant = sender_data.get("participant", sender_phone)
            if participant:
                sender_phone = participant.replace("@c.us", "")
        
        # Get or create user (sender)
        # Note: If this is a HOTEL reploying, we might not want to create a 'User' in the traditional sense.
        # But for now, we do create them to track role.
        
        user = await self._get_or_create_user(
            db,
            tenant.id,
            sender_phone,
            sender_contact_name or sender_name
        )
        
        # NOTIFICATION LOGIC: Forward incoming messages to Tenant Owner via Telegram
        # Only if it's a personal message (not group)
        if not is_group and not is_outgoing:
            # Find owner to notify
            stmt = select(User).where(User.tenant_id == tenant.id, User.role == "owner").limit(1)
            owner_result = await db.execute(stmt)
            owner = owner_result.scalars().first()
            
            if owner and owner.telegram_id:
                # We need to send a Telegram message.
                # To avoid circular imports, we use a lightweight approach or import inside function.
                try:
                    from aiogram import Bot
                    
                    if settings.telegram_bot_token:
                        bot = Bot(token=settings.telegram_bot_token)
                        
                        # Prepare notification
                        notify_text = f"📩 <b>WhatsApp от {sender_name} ({sender_phone}):</b>\n\n{message_text}"
                        
                        await bot.send_message(chat_id=owner.telegram_id, text=notify_text, parse_mode="HTML")
                        await bot.session.close()
                except Exception as e:
                    logger.error(f"Failed to forward WhatsApp to Telegram: {e}")
        
        # 3. Check DND (Do Not Disturb) - Only for Incoming Personal Messages (or mentions)
        
        # 3. Check DND (Do Not Disturb) - Only for Incoming Personal Messages (or mentions)
        # If DND is enabled for the TENANT owner (or main user), we reply with auto-msg
        # Find main user (owner) to check DND status
        # In a multi-user system, we need to know who the bot represents. Assuming single-family/user bot.
        stmt = select(User).where(User.tenant_id == tenant.id, User.role == "owner").limit(1)
        owner_result = await db.execute(stmt)
        owner = owner_result.scalars().first()
        
        is_dnd_active = False
        if owner and owner.dnd_enabled:
            # Check time validity
            if owner.dnd_until and owner.dnd_until > datetime.now(owner.dnd_until.tzinfo):
                is_dnd_active = True
            elif not owner.dnd_until:
                is_dnd_active = True # Enabled indefinitely
        
        if is_dnd_active and not is_outgoing:
            # Auto-reply if personal chat
            if not is_group:
                # Check if we already sent auto-reply recently (TODO: Redis cache)
                dnd_msg = t("bot.dnd_message", tenant.language or "ru")
                if owner.dnd_until:
                    formatted_time = owner.dnd_until.strftime("%H:%M")
                    dnd_msg += f" (до {formatted_time})"
                
                await self.send_message(
                    tenant.greenapi_instance_id,
                    tenant.greenapi_token,
                    sender_phone,
                    dnd_msg
                )
                
                # Still log the message but don't process AI
                # Save to history
                from app.models.chat_message import ChatMessage
                chat_msg = ChatMessage(
                    tenant_id=tenant.id,
                    chat_id=str(chat_id),
                    role="user",
                    content=message_text
                )
                db.add(chat_msg)
                await db.commit()
                return {"status": "ok", "mode": "dnd"}
        
        # 4. Handle Group Message (Passive / Mention)
        if is_group:
            return await self._handle_group_message(
                db, tenant, user, chat_id, sender_phone, sender_name,
                message_text, message_id
            )
        
        # 5. Handle Personal Message (Active AI)
        lang = user.language or tenant.language
        api_key = tenant.gemini_api_key or settings.gemini_api_key
        
        if not api_key:
            response_text = t("bot.error", lang)
        else:
            # Process via AI Router
            ai_router = AIRouter(
                db=db,
                api_key=tenant.gemini_api_key,
                language=tenant.language or "ru",
                enable_rag=True
            )
            
            # If outgoing (Shadow Mode), we MUST be silent
            # Exception: If user starts message with "/" (command), they might want a reply even if self-sent
            force_reply = message_text and message_text.startswith("/")
            silent_response = is_outgoing and not force_reply
            
            # If standard incoming message, check DND status (if implemented)
            # For now, standard behavior
            
            if message_text:
                # Refetching logic: process_message returns ModuleResponse
                response = await ai_router.process_message(
                    message=message_text,
                    tenant_id=tenant.id, 
                    source="whatsapp",
                    silent_response=silent_response
                )
                
                # === SHADOW MODE INTERACTIVE CHECKS ===
                if silent_response and is_outgoing:
                    # 🗓 Secretary-Diplomat: Check for scheduling conflicts in OUTGOING proposals
                    # "Давай завтра в 14:00" -> Parse -> Check Calendar -> Alert User if busy
                    try:
                        import re
                        from datetime import datetime, timedelta
                        
                        # Quick regex to detect time proposals (e.g. "в 14:00", "at 5pm")
                        time_match = re.search(r"(?:в|at)\s+(\d{1,2}[:.]\d{2})", message_text, re.IGNORECASE)
                        if time_match:
                            prop_time_str = time_match.group(1).replace(".", ":")
                            
                            # Simple "Tomorrow" / "Today" check
                            # This is a heuristic. Ideally use an LLM or DateParser, but for speed regular regex is good.
                            target_date = datetime.now()
                            if "завтра" in message_text.lower() or "tomorrow" in message_text.lower():
                                target_date += timedelta(days=1)
                            
                            hour, minute = map(int, prop_time_str.split(":"))
                            check_start = target_date.replace(hour=hour, minute=minute, second=0)
                            check_end = check_start + timedelta(minutes=60) # Assume 1h
                            
                            # Query DB for conflict
                            from app.models.meeting import Meeting
                            from sqlalchemy import select, and_
                            
                            stmt = select(Meeting).where(
                                and_(
                                    Meeting.tenant_id == tenant.id,
                                    Meeting.start_time < check_end, # Overlap logic
                                    Meeting.end_time > check_start
                                )
                            )
                            result = await db.execute(stmt)
                            conflict = result.scalar_one_or_none()
                            
                            if conflict:
                                conflict_time = conflict.start_time.strftime("%H:%M")
                                alert_msg = (
                                    f"⚠️ **Конфликт в расписании!**\n"
                                    f"Вы предложили **{prop_time_str}**, но у вас уже есть встреча:\n"
                                    f"📌 **{conflict.title}** в {conflict_time}.\n"
                                    f"Может, предложить 16:30?"
                                )
                                # Send ALERT to user (Self-message)
                                await self.send_message(
                                    instance_id=tenant.greenapi_instance_id,
                                    token=tenant.greenapi_token,
                                    phone=sender_data.get("chatId", "").split("@")[0],
                                    message=alert_msg
                                )
                    except Exception as e:
                        logger.error(f"Shadow Mode Conflict Check failed: {e}")

                # Normal response sending
                if not silent_response and response.success and response.message:
                    await self.send_message(
                        instance_id=tenant.greenapi_instance_id,
                        token=tenant.greenapi_token,
                        phone=sender_data.get("chatId", "").split("@")[0],
                        message=response.message
                    )

            return {"status": "ok", "processed": True}
    
    async def _handle_group_message(
        self,
        db: AsyncSession,
        tenant: Tenant,
        user: User,
        group_chat_id: str,
        sender_phone: str,
        sender_name: str,
        message_text: str,
        message_id: str
    ) -> dict:
        """Handle group message with task extraction."""
        from app.services.group_task_manager import GroupTaskManager
        
        lang = user.language or tenant.language
        api_key = tenant.gemini_api_key or settings.gemini_api_key
        
        if not api_key:
            logger.warning(f"No API key for tenant {tenant.id}")
            return {"status": "ignored", "reason": "no_api_key"}
        
        manager = GroupTaskManager(db, api_key=api_key, language=lang)
        
        result = await manager.process_group_message(
            tenant_id=tenant.id,
            group_chat_id=group_chat_id,
            sender_phone=sender_phone,
            sender_name=sender_name,
            message_text=message_text,
            message_id=message_id
        )
        
        # If action was taken and we have a response, send it to the group
        if result.get("response_message"):
            reply_to = result.get("reply_to")
            
            # Send to group (remove @g.us suffix)
            group_phone = group_chat_id.replace("@g.us", "")
            
            await self.send_message(
                tenant.greenapi_instance_id,
                tenant.greenapi_token,
                group_phone,
                result["response_message"],
                is_group=True
            )
        
        await db.commit()
        return result
    
    async def _get_or_create_user(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        phone: str,
        name: str
    ) -> User:
        """Get or create a user by WhatsApp phone."""
        stmt = select(User).where(
            User.tenant_id == tenant_id,
            User.whatsapp_phone == phone
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                tenant_id=tenant_id,
                whatsapp_phone=phone,
                name=name,
                role="user"
            )
            db.add(user)
            await db.flush()
        
        return user
    
    async def setup_webhook(
        self,
        instance_id: str,
        token: str,
        webhook_url: str
    ) -> Dict[str, Any]:
        """Configure GreenAPI webhook URL."""
        return await self.set_settings(
            instance_id,
            token,
            webhook_url=webhook_url,
            incoming_webhook="yes",
            outgoing_webhook="no"
        )


# Global service instance
whatsapp_service = WhatsAppBotService()


def get_whatsapp_service() -> WhatsAppBotService:
    """Get the global WhatsApp service."""
    return whatsapp_service
