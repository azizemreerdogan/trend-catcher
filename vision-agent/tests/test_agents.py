import sys
import os
import json
import pytest
from unittest.mock import patch, MagicMock

# vision-agent klasorunu sys.path'e ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# =============================================
# MOCK VERILER
# =============================================
MOCK_VISION_RESPONSE = json.dumps({
    "camera_style": "Selfie tarzı, Elde",
    "editing_pace": "Hızlı kesimler",
    "visual_summary": "Bir benzin istasyonunda lüks bir araba görülüyor.",
    "topic": "Lüks araba şakası",
    "target_audience": "Gen-Z",
    "emotion": "Eğlenceli",
    "hooks": ["Lüks arabanın motor bölümü", "Patlamış mısır detayı"]
})

MOCK_TRANSCRIPT_RESPONSE = json.dumps({
    "transcript": "Arkadaşlar bakın arabanın içine ne koymuşlar!",
    "language": "Türkçe",
    "keywords": ["araba", "patlamış mısır", "şaka"],
    "tone": "Enerjik"
})


# =============================================
# VISION AGENT TESTLERI
# =============================================
class TestVisionAgent:
    
    @patch("agents.vision_agent.genai")
    def test_analyze_video_strip_returns_valid_json(self, mock_genai, tmp_path):
        """Vision Agent gecerli bir JSON donmeli."""
        # Fake strip dosyasi olustur
        fake_strip = tmp_path / "test_strip.jpg"
        fake_strip.write_bytes(b"\xff\xd8\xff\xe0")  # Minimal JPEG header
        
        # Gemini client mock
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.files.upload.return_value = MagicMock()
        
        mock_response = MagicMock()
        mock_response.text = MOCK_VISION_RESPONSE
        mock_client.models.generate_content.return_value = mock_response
        
        from agents.vision_agent import analyze_video_strip
        result = analyze_video_strip(str(fake_strip))
        
        assert isinstance(result, dict)
        assert "camera_style" in result
        assert "editing_pace" in result
        assert "visual_summary" in result
        assert "topic" in result
        assert "target_audience" in result
        assert "emotion" in result
        assert "hooks" in result
        assert isinstance(result["hooks"], list)
    
    @patch("agents.vision_agent.genai")
    def test_analyze_video_strip_calls_gemini_with_correct_model(self, mock_genai, tmp_path):
        """Vision Agent dogru modeli (gemini-2.5-flash) cagirmali."""
        fake_strip = tmp_path / "test_strip.jpg"
        fake_strip.write_bytes(b"\xff\xd8\xff\xe0")
        
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.files.upload.return_value = MagicMock()
        
        mock_response = MagicMock()
        mock_response.text = MOCK_VISION_RESPONSE
        mock_client.models.generate_content.return_value = mock_response
        
        from agents.vision_agent import analyze_video_strip
        analyze_video_strip(str(fake_strip))
        
        call_kwargs = mock_client.models.generate_content.call_args
        assert call_kwargs.kwargs["model"] == "gemini-2.5-flash"
    
    def test_analyze_video_strip_raises_on_missing_file(self):
        """Dosya bulunamazsa FileNotFoundError firlatmali."""
        from agents.vision_agent import analyze_video_strip
        with pytest.raises(FileNotFoundError):
            analyze_video_strip("nonexistent_file.jpg")
    
    @patch("agents.vision_agent.genai")
    def test_analyze_video_strip_handles_invalid_json(self, mock_genai, tmp_path):
        """Gemini bozuk JSON donerse hata dict'i donmeli."""
        fake_strip = tmp_path / "test_strip.jpg"
        fake_strip.write_bytes(b"\xff\xd8\xff\xe0")
        
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.files.upload.return_value = MagicMock()
        
        mock_response = MagicMock()
        mock_response.text = "BU GECERLI JSON DEGIL!!!"
        mock_client.models.generate_content.return_value = mock_response
        
        from agents.vision_agent import analyze_video_strip
        result = analyze_video_strip(str(fake_strip))
        
        assert "error" in result
        assert "raw_text" in result


# =============================================
# TRANSCRIPT AGENT TESTLERI
# =============================================
class TestTranscriptAgent:
    
    @patch("agents.transcript_agent.genai")
    def test_analyze_audio_returns_valid_json(self, mock_genai, tmp_path):
        """Transcript Agent gecerli bir JSON donmeli."""
        fake_audio = tmp_path / "test_audio.wav"
        fake_audio.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")  # Minimal WAV header
        
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.files.upload.return_value = MagicMock()
        
        mock_response = MagicMock()
        mock_response.text = MOCK_TRANSCRIPT_RESPONSE
        mock_client.models.generate_content.return_value = mock_response
        
        from agents.transcript_agent import analyze_audio
        result = analyze_audio(str(fake_audio))
        
        assert isinstance(result, dict)
        assert "transcript" in result
        assert "language" in result
        assert "keywords" in result
        assert "tone" in result
        assert isinstance(result["keywords"], list)
    
    @patch("agents.transcript_agent.genai")
    def test_analyze_audio_calls_gemini_with_correct_model(self, mock_genai, tmp_path):
        """Transcript Agent dogru modeli (gemini-1.5-flash) cagirmali."""
        fake_audio = tmp_path / "test_audio.wav"
        fake_audio.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")
        
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.files.upload.return_value = MagicMock()
        
        mock_response = MagicMock()
        mock_response.text = MOCK_TRANSCRIPT_RESPONSE
        mock_client.models.generate_content.return_value = mock_response
        
        from agents.transcript_agent import analyze_audio
        analyze_audio(str(fake_audio))
        
        call_kwargs = mock_client.models.generate_content.call_args
        assert call_kwargs.kwargs["model"] == "gemini-2.5-flash"
    
    def test_analyze_audio_raises_on_missing_file(self):
        """Dosya bulunamazsa FileNotFoundError firlatmali."""
        from agents.transcript_agent import analyze_audio
        with pytest.raises(FileNotFoundError):
            analyze_audio("nonexistent_audio.wav")
    
    @patch("agents.transcript_agent.genai")
    def test_analyze_audio_handles_invalid_json(self, mock_genai, tmp_path):
        """Gemini bozuk JSON donerse hata dict'i donmeli."""
        fake_audio = tmp_path / "test_audio.wav"
        fake_audio.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")
        
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client
        mock_client.files.upload.return_value = MagicMock()
        
        mock_response = MagicMock()
        mock_response.text = "BOZUK CIKTI"
        mock_client.models.generate_content.return_value = mock_response
        
        from agents.transcript_agent import analyze_audio
        result = analyze_audio(str(fake_audio))
        
        assert "error" in result
        assert "raw_text" in result
