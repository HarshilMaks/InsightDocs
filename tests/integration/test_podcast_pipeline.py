"""
Integration tests for podcast/TTS generation paths.
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.models.schemas import Document, Task, TaskStatus
from backend.utils.podcast_generator import PodcastGenerator, TTSEngine


class TestPodcastScriptGeneration:
    @pytest.mark.asyncio
    async def test_generate_podcast_script_uses_llm_response(self):
        with patch("backend.utils.llm_client.genai.GenerativeModel") as mock_model_cls:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = MagicMock(text="Podcast script here")
            mock_model_cls.return_value = mock_model

            from backend.utils.llm_client import LLMClient

            llm = LLMClient(api_key="AIzaSyC_test_key_for_script_generation_123")
            script = await llm.generate_podcast_script("Doc summary", "Research Paper")

        assert script == "Podcast script here"


class TestTTSGeneration:
    def test_generate_audio_prefers_google_when_available(self):
        with patch.object(PodcastGenerator, "is_google_tts_available", return_value=True), patch.object(
            PodcastGenerator, "_generate_google_tts", return_value=(b"mp3", 12.5)
        ) as mock_google:
            audio, duration = PodcastGenerator.generate_podcast_from_text("hello world", engine=None)

        assert audio == b"mp3"
        assert duration == 12.5
        mock_google.assert_called_once()

    def test_generate_audio_falls_back_to_pyttsx3(self):
        with patch.object(PodcastGenerator, "is_google_tts_available", return_value=False), patch.object(
            PodcastGenerator, "is_pyttsx3_available", return_value=True
        ), patch.object(PodcastGenerator, "_generate_pyttsx3", return_value=(b"wav", 8.0)) as mock_offline:
            audio, duration = PodcastGenerator.generate_podcast_from_text("offline text", engine=None)

        assert audio == b"wav"
        assert duration == 8.0
        mock_offline.assert_called_once()

    def test_estimate_duration_reasonable(self):
        text = "word " * 300
        dur = PodcastGenerator.estimate_duration(text, speaking_rate=1.0)
        assert 100 <= dur <= 140  # 300 words at ~2.5 words/s


class TestPodcastStorageAndModels:
    def test_document_model_podcast_fields(self):
        doc = Document(
            id="doc-123",
            filename="research.pdf",
            file_type=".pdf",
            file_size=1000,
            s3_bucket="test-bucket",
            s3_key="uploads/research.pdf",
            user_id="user1",
            status=TaskStatus.COMPLETED,
            has_podcast=True,
            podcast_s3_key="podcasts/user1/doc-123.mp3",
            podcast_duration=300,
        )
        assert doc.has_podcast is True
        assert doc.podcast_s3_key.endswith(".mp3")
        assert doc.podcast_duration == 300

    def test_task_progress_updates(self):
        task = Task(
            id="podcast-task-1",
            task_type="podcast_generation",
            status=TaskStatus.PENDING,
            progress=0.0,
            user_id="user1",
            document_id="doc1",
        )
        task.progress = 50.0
        assert task.progress == 50.0
        task.progress = 100.0
        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED

    def test_presigned_url_generation(self):
        with patch("backend.storage.file_storage.boto3.client") as mock_boto_client:
            mock_client = MagicMock()
            mock_client.head_bucket.return_value = {}
            mock_client.generate_presigned_url.return_value = "https://s3.example.com/podcasts/u/doc.mp3?sig=1"
            mock_boto_client.return_value = mock_client

            from backend.storage.file_storage import FileStorage

            storage = FileStorage()
            url = storage.get_file_url("podcasts/u/doc.mp3")

        assert url.startswith("https://")
        assert "doc.mp3" in url


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
