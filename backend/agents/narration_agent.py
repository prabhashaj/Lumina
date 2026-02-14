"""
Narration Agent - Handles text-to-speech generation for slide narration.
Uses ElevenLabs when available, otherwise falls back to browser TTS signaling.
"""
import io
import base64
from typing import List, Optional, Tuple
from loguru import logger

from config.settings import settings


class NarrationAgent:
    """Generates audio narration for presentation slides"""

    def __init__(self):
        self.has_elevenlabs = bool(settings.elevenlabs_api_key)
        self.voice_id = settings.tts_voice_id
        self.model_id = settings.tts_model

    async def generate_slide_audio(self, text: str) -> dict:
        """
        Generate audio for a single slide's narration.

        Returns:
            dict with keys:
                - audio_base64: base64 encoded mp3 (or empty if fallback)
                - use_browser_tts: whether frontend should use Web Speech API
                - text: the narration text for browser TTS / transcript
                - duration_estimate: estimated seconds
        """
        duration_estimate = max(3, len(text.split()) / 2.5)  # ~150 wpm

        if not self.has_elevenlabs:
            return {
                "audio_base64": "",
                "use_browser_tts": True,
                "text": text,
                "duration_estimate": duration_estimate,
            }

        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}",
                    headers={
                        "xi-api-key": settings.elevenlabs_api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": text,
                        "model_id": self.model_id,
                        "voice_settings": {
                            "stability": 0.82,
                            "similarity_boost": 0.88,
                            "style": 0.08,
                            "use_speaker_boost": True,
                        },
                    },
                )

                if response.status_code != 200:
                    logger.warning(f"ElevenLabs error {response.status_code}, falling back")
                    return {
                        "audio_base64": "",
                        "use_browser_tts": True,
                        "text": text,
                        "duration_estimate": duration_estimate,
                    }

                audio_b64 = base64.b64encode(response.content).decode("utf-8")
                return {
                    "audio_base64": audio_b64,
                    "use_browser_tts": False,
                    "text": text,
                    "duration_estimate": duration_estimate,
                }

        except Exception as e:
            logger.error(f"Narration audio error: {e}")
            return {
                "audio_base64": "",
                "use_browser_tts": True,
                "text": text,
                "duration_estimate": duration_estimate,
            }

    async def generate_all_narrations(self, narration_scripts: List[dict]) -> List[dict]:
        """
        Generate audio for all slides.

        Args:
            narration_scripts: list of {slide_number, narration}

        Returns:
            list of {slide_number, audio_base64, use_browser_tts, text, duration_estimate}
        """
        results = []
        for script in narration_scripts:
            audio_data = await self.generate_slide_audio(script["narration"])
            results.append({
                "slide_number": script["slide_number"],
                **audio_data,
            })
        return results
