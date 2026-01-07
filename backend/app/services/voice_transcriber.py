from __future__ import annotations
"""Voice transcription service using ElevenLabs or OpenAI Whisper."""
import io
from typing import BinaryIO, Optional

import httpx

from app.core.config import settings


class VoiceTranscriber:
    """
    Service for transcribing voice messages to text.
    Supports ElevenLabs and can fallback to OpenAI Whisper.
    """
    
    ELEVENLABS_URL = "https://api.elevenlabs.io/v1/speech-to-text"
    
    def __init__(self, api_key:Optional[ str ] = None):
        self.api_key = api_key or settings.elevenlabs_api_key
    
    async def transcribe(
        self, 
        audio_data: bytes | BinaryIO,
        language: str = "ru"
    ) ->Optional[ str ]:
        """
        Transcribe audio to text.
        
        Args:
            audio_data: Audio file bytes or file-like object
            language: Language hint ("ru" or "kk" for Kazakh)
        
        Returns:
            Transcribed text or None on failure
        """
        if not self.api_key and not settings.gemini_api_key:
            return None
        
        # Convert to bytes if needed
        if hasattr(audio_data, 'read'):
            audio_bytes = audio_data.read()
            if hasattr(audio_data, 'seek'):
                audio_data.seek(0)
        else:
            audio_bytes = audio_data
        
        # Try Gemini First (Fast & Multi-modal)
        text = await self._transcribe_gemini(audio_bytes, language)
        if text:
            return text
            
        # Fallback to ElevenLabs
        if self.api_key:
            try:
                return await self._transcribe_elevenlabs(audio_bytes, language)
            except Exception as e:
                print(f"ElevenLabs transcription failed: {e}")
                
        return None
    
    async def _transcribe_elevenlabs(
        self, 
        audio_bytes: bytes, 
        language: str
    ) ->Optional[ str ]:
        """Transcribe using ElevenLabs API."""
        # Map language codes
        lang_code = "kk" if language == "kz" else language
        
        headers = {
            "xi-api-key": self.api_key,
        }
        
        # ElevenLabs Scribe expects 'file' parameter
        files = {
            "file": ("audio.ogg", io.BytesIO(audio_bytes), "audio/ogg"),
        }
        
        data = {
            "model_id": "scribe_v1",
            # "language_code": lang_code, # Scribe v1 auto-detects or doesn't use this param the same way? 
            # Check docs: usually just model_id and file. Tagging language might need specific param.
            # But let's keep it if it was there, or remove if causing error. 
            # The error was "Must provide either file...", so file param name was the main issue.
        }
        if lang_code:
             data["language_code"] = lang_code
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.ELEVENLABS_URL,
                headers=headers,
                files=files,
                data=data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("text")
            else:
                print(f"ElevenLabs API error: {response.status_code} {response.text}")
                return None

    async def _transcribe_gemini(
        self, 
        audio_bytes: bytes,
        language: str
    ) -> Optional[str]:
        """Transcribe using Gemini Flash."""
        try:
            import google.generativeai as genai
            if not settings.gemini_api_key:
                return None
                
            genai.configure(api_key=settings.gemini_api_key)
            # Try specific version
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            prompt = "Transcribe this audio message exactly. Return only the text."
            if language in ["kk", "kz"]:
                prompt += " The language is likely Kazakh."
            elif language == "ru":
                prompt += " The language is likely Russian."
                
            response = await model.generate_content_async([
                prompt,
                {
                    "mime_type": "audio/ogg", # WhatsApp usually OGG
                    "data": audio_bytes
                }
            ])
            return response.text
        except Exception as e:
            print(f"Gemini transcription failed: {e}")
            return None
    
    async def transcribe_telegram_voice(
        self,
        bot_token: str,
        file_id: str,
        language: str = "ru"
    ) ->Optional[ str ]:
        """
        Download and transcribe a Telegram voice message.
        
        Args:
            bot_token: Telegram bot token
            file_id: Telegram file ID
            language: Language hint
        
        Returns:
            Transcribed text or None
        """
        async with httpx.AsyncClient() as client:
            # Get file path from Telegram
            file_info_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
            file_info = await client.get(file_info_url)
            
            if file_info.status_code != 200:
                return None
            
            file_path = file_info.json().get("result", {}).get("file_path")
            if not file_path:
                return None
            
            # Download file
            download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
            audio_response = await client.get(download_url)
            
            if audio_response.status_code != 200:
                return None
            
            # Transcribe
            return await self.transcribe(audio_response.content, language)


# Singleton instance
_transcriber:Optional[ VoiceTranscriber ] = None


def get_transcriber() -> VoiceTranscriber:
    """Get or create transcriber instance."""
    global _transcriber
    if _transcriber is None:
        _transcriber = VoiceTranscriber()
    return _transcriber
