"""
Podcast/TTS Generation Module for InsightDocs

Converts document summaries and content into audio using Google Cloud TTS
or offline pyttsx3, with optional podcast script generation via LLM.
"""

import logging
from typing import Optional, Tuple
import io
import os
from pathlib import Path
from enum import Enum

try:
    from google.cloud import texttospeech
    GOOGLE_TTS_AVAILABLE = True
except ImportError:
    GOOGLE_TTS_AVAILABLE = False
    logging.warning("google-cloud-texttospeech not available. Will fall back to pyttsx3.")

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    logging.warning("pyttsx3 not available. Offline TTS will be disabled.")

logger = logging.getLogger(__name__)


class TTSEngine(str, Enum):
    """Available TTS engines."""
    GOOGLE = "google"
    PYTTSX3 = "pyttsx3"


class PodcastGenerator:
    """
    Generate podcasts from document content and summaries.
    Supports multiple TTS engines and podcast script customization.
    """

    # Default TTS engine (fallback chain: Google -> pyttsx3)
    DEFAULT_ENGINE = TTSEngine.GOOGLE if GOOGLE_TTS_AVAILABLE else TTSEngine.PYTTSX3
    
    # Podcast parameters
    DEFAULT_VOICE_GENDER = texttospeech.SsmlVoiceGender.NEUTRAL if GOOGLE_TTS_AVAILABLE else None
    DEFAULT_LANGUAGE = "en-US"
    DEFAULT_SPEAKING_RATE = 1.0
    DEFAULT_PITCH = 0.0

    @staticmethod
    def is_google_tts_available() -> bool:
        """Check if Google Cloud TTS is available."""
        if not GOOGLE_TTS_AVAILABLE:
            return False
        # Try to verify credentials
        try:
            client = texttospeech.TextToSpeechClient()
            return True
        except Exception as e:
            logger.warning(f"Google Cloud TTS not properly configured: {e}")
            return False

    @staticmethod
    def is_pyttsx3_available() -> bool:
        """Check if pyttsx3 is available."""
        if not PYTTSX3_AVAILABLE:
            return False
        try:
            engine = pyttsx3.init()
            return True
        except Exception as e:
            logger.warning(f"pyttsx3 not available: {e}")
            return False

    @staticmethod
    def generate_podcast_from_text(
        text: str,
        engine: Optional[TTSEngine] = None,
        output_path: Optional[str] = None,
        **kwargs
    ) -> Tuple[Optional[bytes], float]:
        """
        Generate podcast audio from text content.
        
        Args:
            text: Text to convert to speech
            engine: TTS engine to use (default: auto-detect)
            output_path: Optional file path to save audio (mp3 format)
            **kwargs: Additional parameters:
                - speaking_rate (float): 0.25-4.0, default 1.0
                - pitch (float): -20.0 to 20.0, default 0.0
                - language (str): Language code, default "en-US"
                - voice_name (str): Specific voice name for Google TTS
        
        Returns:
            Tuple of (audio_bytes, duration_seconds)
            - audio_bytes: MP3 audio content (None if failed)
            - duration_seconds: Estimated audio duration
        """
        if not text or not text.strip():
            logger.error("Cannot generate podcast from empty text")
            return None, 0.0

        # Auto-select engine if not specified
        if engine is None:
            engine = (
                TTSEngine.GOOGLE if PodcastGenerator.is_google_tts_available()
                else TTSEngine.PYTTSX3 if PodcastGenerator.is_pyttsx3_available()
                else None
            )

        if engine is None:
            logger.error("No TTS engine available")
            return None, 0.0

        try:
            if engine == TTSEngine.GOOGLE:
                return PodcastGenerator._generate_google_tts(text, output_path, **kwargs)
            elif engine == TTSEngine.PYTTSX3:
                return PodcastGenerator._generate_pyttsx3(text, output_path, **kwargs)
        except Exception as e:
            logger.error(f"Error generating podcast: {e}")
            return None, 0.0

        return None, 0.0

    @staticmethod
    def _generate_google_tts(
        text: str,
        output_path: Optional[str] = None,
        **kwargs
    ) -> Tuple[Optional[bytes], float]:
        """
        Generate audio using Google Cloud Text-to-Speech.
        
        Requires GOOGLE_APPLICATION_CREDENTIALS environment variable.
        """
        if not GOOGLE_TTS_AVAILABLE:
            logger.error("Google Cloud TTS not available")
            return None, 0.0

        try:
            client = texttospeech.TextToSpeechClient()
            
            # Build synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Configure voice
            voice = texttospeech.VoiceSelectionParams(
                language_code=kwargs.get("language", "en-US"),
                name=kwargs.get("voice_name", "en-US-Neural2-C"),  # Nice neutral voice
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
            )
            
            # Configure audio encoding
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=kwargs.get("speaking_rate", 1.0),
                pitch=kwargs.get("pitch", 0.0),
            )
            
            # Request synthesis
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )
            
            # Write to file if path provided
            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(response.audio_content)
                logger.info(f"Podcast saved to {output_path}")
            
            # Estimate duration: ~150 words per minute = 2.5 words/sec
            word_count = len(text.split())
            estimated_duration = (word_count / 2.5) * (1.0 / kwargs.get("speaking_rate", 1.0))
            
            return response.audio_content, estimated_duration
            
        except Exception as e:
            logger.error(f"Google TTS error: {e}")
            return None, 0.0

    @staticmethod
    def _generate_pyttsx3(
        text: str,
        output_path: Optional[str] = None,
        **kwargs
    ) -> Tuple[Optional[bytes], float]:
        """
        Generate audio using offline pyttsx3.
        
        Note: pyttsx3 generates WAV, not MP3. For production, convert to MP3.
        """
        if not PYTTSX3_AVAILABLE:
            logger.error("pyttsx3 not available")
            return None, 0.0

        try:
            engine = pyttsx3.init()
            
            # Configure voice properties
            engine.setProperty('rate', kwargs.get("speaking_rate", 1.0) * 150)  # Default 150 wpm
            engine.setProperty('volume', 1.0)
            
            # If output path provided, save WAV (pyttsx3 limitation)
            if output_path:
                # Replace .mp3 with .wav since pyttsx3 doesn't support MP3
                wav_path = output_path.replace('.mp3', '.wav')
                engine.save_to_file(text, wav_path)
                engine.runAndWait()
                logger.info(f"Podcast saved to {wav_path} (WAV format)")
                
                # Estimate duration
                word_count = len(text.split())
                speaking_rate = kwargs.get("speaking_rate", 1.0)
                estimated_duration = (word_count / 2.5) * (1.0 / speaking_rate)
                
                # Try to read WAV file and return bytes
                try:
                    with open(wav_path, 'rb') as f:
                        audio_bytes = f.read()
                    return audio_bytes, estimated_duration
                except Exception as e:
                    logger.error(f"Error reading generated WAV: {e}")
                    return None, estimated_duration
            else:
                # Generate in memory (trickier with pyttsx3)
                logger.warning("pyttsx3 in-memory generation not fully supported")
                return None, 0.0
                
        except Exception as e:
            logger.error(f"pyttsx3 error: {e}")
            return None, 0.0

    @staticmethod
    def generate_podcast_script(summary: str, doc_title: str = "Document") -> str:
        """
        Generate a podcast script from a document summary.
        
        This should be called with LLMClient.generate_podcast_script()
        to include Gemini AI enhancements. This is a simple template fallback.
        
        Args:
            summary: Document summary text
            doc_title: Title of the document
            
        Returns:
            Formatted podcast script
        """
        script = f"""
Welcome to InsightDocs podcast. Today we're discussing '{doc_title}'.

{summary}

Thank you for listening. For more details, visit InsightDocs.
""".strip()
        
        return script

    @staticmethod
    def estimate_duration(text: str, speaking_rate: float = 1.0) -> float:
        """
        Estimate audio duration in seconds.
        
        Uses rough heuristic: 150 words per minute at normal speaking rate.
        
        Args:
            text: Text content
            speaking_rate: Relative speaking rate (1.0 = normal)
            
        Returns:
            Estimated duration in seconds
        """
        word_count = len(text.split())
        # 150 wpm = 2.5 words/sec
        base_duration = word_count / 2.5
        # Adjust for speaking rate
        adjusted_duration = base_duration * (1.0 / speaking_rate)
        return adjusted_duration
