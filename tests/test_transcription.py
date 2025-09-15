import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import json


class TestTranscription(unittest.TestCase):
    """Test suite for audio transcription functionality."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_audio_file = "test_audio.wav"
        self.temp_dir = tempfile.mkdtemp()
        self.sample_transcription = {
            "text": "Hello world, this is a test transcription.",
            "segments": [
                {
                    "id": 0,
                    "start": 0.0,
                    "end": 2.5,
                    "text": "Hello world,",
                    "confidence": 0.95
                },
                {
                    "id": 1,
                    "start": 2.5,
                    "end": 5.0,
                    "text": "this is a test transcription.",
                    "confidence": 0.92
                }
            ],
            "language": "en"
        }

    def tearDown(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    @patch('backend.transcription.whisper.load_model')
    def test_load_transcription_model(self, mock_load_model):
        """Test loading of transcription model."""
        mock_model = Mock()
        mock_load_model.return_value = mock_model

        from backend.transcription import load_transcription_model

        model = load_transcription_model("base")

        mock_load_model.assert_called_once_with("base")
        self.assertEqual(model, mock_model)

    def test_load_invalid_transcription_model(self):
        """Test loading invalid transcription model."""
        from backend.transcription import load_transcription_model

        with self.assertRaises(ValueError):
            load_transcription_model("invalid_model")

    @patch('backend.transcription.load_transcription_model')
    def test_transcribe_audio_basic(self, mock_load_model):
        """Test basic audio transcription functionality."""
        mock_model = Mock()
        mock_model.transcribe.return_value = self.sample_transcription
        mock_load_model.return_value = mock_model

        from backend.transcription import transcribe_audio

        result = transcribe_audio(self.test_audio_file)

        mock_model.transcribe.assert_called_once()
        self.assertEqual(result["text"], self.sample_transcription["text"])
        self.assertEqual(len(result["segments"]), 2)

    @patch('backend.transcription.load_transcription_model')
    def test_transcribe_with_language_detection(self, mock_load_model):
        """Test transcription with automatic language detection."""
        mock_model = Mock()
        mock_model.transcribe.return_value = self.sample_transcription
        mock_load_model.return_value = mock_model

        from backend.transcription import transcribe_audio

        result = transcribe_audio(self.test_audio_file, language=None)

        # Should call transcribe without language parameter for auto-detection
        mock_model.transcribe.assert_called_once()
        self.assertIn("language", result)

    @patch('backend.transcription.load_transcription_model')
    def test_transcribe_with_specific_language(self, mock_load_model):
        """Test transcription with specific language."""
        mock_model = Mock()
        mock_model.transcribe.return_value = self.sample_transcription
        mock_load_model.return_value = mock_model

        from backend.transcription import transcribe_audio

        result = transcribe_audio(self.test_audio_file, language="es")

        mock_model.transcribe.assert_called_once()
        # Check that language parameter was passed
        call_args = mock_model.transcribe.call_args
        self.assertIn("language", call_args[1])
        self.assertEqual(call_args[1]["language"], "es")

    def test_transcribe_nonexistent_file(self):
        """Test transcription of non-existent audio file."""
        from backend.transcription import transcribe_audio

        with self.assertRaises(FileNotFoundError):
            transcribe_audio("nonexistent_file.wav")

    @patch('backend.transcription.load_transcription_model')
    def test_transcribe_with_timestamps(self, mock_load_model):
        """Test transcription with timestamp extraction."""
        mock_model = Mock()
        mock_model.transcribe.return_value = self.sample_transcription
        mock_load_model.return_value = mock_model

        from backend.transcription import transcribe_audio

        result = transcribe_audio(self.test_audio_file, include_timestamps=True)

        # Check that segments contain timing information
        for segment in result["segments"]:
            self.assertIn("start", segment)
            self.assertIn("end", segment)
            self.assertIsInstance(segment["start"], (int, float))
            self.assertIsInstance(segment["end"], (int, float))

    @patch('backend.transcription.load_transcription_model')
    def test_transcribe_without_timestamps(self, mock_load_model):
        """Test transcription without timestamp extraction."""
        mock_model = Mock()
        mock_transcription_no_segments = {
            "text": "Hello world, this is a test transcription.",
            "language": "en"
        }
        mock_model.transcribe.return_value = mock_transcription_no_segments
        mock_load_model.return_value = mock_model

        from backend.transcription import transcribe_audio

        result = transcribe_audio(self.test_audio_file, include_timestamps=False)

        self.assertIn("text", result)
        self.assertNotIn("segments", result)

    def test_transcription_confidence_filtering(self):
        """Test filtering transcription segments by confidence."""
        from backend.transcription import filter_by_confidence

        segments = [
            {"text": "high confidence", "confidence": 0.95},
            {"text": "low confidence", "confidence": 0.3},
            {"text": "medium confidence", "confidence": 0.75}
        ]

        filtered = filter_by_confidence(segments, min_confidence=0.7)

        self.assertEqual(len(filtered), 2)
        for segment in filtered:
            self.assertGreaterEqual(segment["confidence"], 0.7)

    def test_transcription_text_cleaning(self):
        """Test text cleaning and normalization."""
        from backend.transcription import clean_transcription_text

        dirty_text = "  Hello,,,   world!!!  This is   a test.  "
        cleaned = clean_transcription_text(dirty_text)

        expected = "Hello, world! This is a test."
        self.assertEqual(cleaned, expected)

    def test_transcription_output_formats(self):
        """Test different transcription output formats."""
        from backend.transcription import format_transcription_output

        # Test SRT format
        srt_output = format_transcription_output(self.sample_transcription, format="srt")
        self.assertIn("-->", srt_output)
        self.assertIn("00:00:00,000", srt_output)

        # Test VTT format
        vtt_output = format_transcription_output(self.sample_transcription, format="vtt")
        self.assertIn("WEBVTT", vtt_output)
        self.assertIn("00:00:00.000", vtt_output)

        # Test JSON format
        json_output = format_transcription_output(self.sample_transcription, format="json")
        parsed_json = json.loads(json_output)
        self.assertIn("text", parsed_json)
        self.assertIn("segments", parsed_json)

    @patch('backend.transcription.load_transcription_model')
    def test_transcribe_long_audio(self, mock_load_model):
        """Test transcription of long audio files with chunking."""
        mock_model = Mock()

        # Simulate long audio transcription with multiple chunks
        long_transcription = {
            "text": "This is a very long transcription " * 100,
            "segments": [
                {"start": i, "end": i+1, "text": f"Segment {i}"}
                for i in range(100)
            ],
            "language": "en"
        }
        mock_model.transcribe.return_value = long_transcription
        mock_load_model.return_value = mock_model

        from backend.transcription import transcribe_audio

        result = transcribe_audio(self.test_audio_file, chunk_length=30)

        self.assertIn("text", result)
        self.assertGreater(len(result["text"]), 1000)  # Long text

    @patch('backend.transcription.load_transcription_model')
    def test_transcribe_with_different_models(self, mock_load_model):
        """Test transcription with different Whisper model sizes."""
        models_to_test = ["tiny", "base", "small", "medium", "large"]

        for model_name in models_to_test:
            mock_model = Mock()
            mock_model.transcribe.return_value = self.sample_transcription
            mock_load_model.return_value = mock_model

            from backend.transcription import transcribe_audio

            result = transcribe_audio(self.test_audio_file, model=model_name)
            self.assertIsNotNone(result)
            self.assertIn("text", result)

    def test_transcription_batch_processing(self):
        """Test batch transcription of multiple audio files."""
        audio_files = ["file1.wav", "file2.wav", "file3.wav"]

        with patch('backend.transcription.transcribe_audio') as mock_transcribe:
            mock_transcribe.return_value = self.sample_transcription

            from backend.transcription import transcribe_audio_batch

            results = transcribe_audio_batch(audio_files)

            self.assertEqual(len(results), 3)
            self.assertEqual(mock_transcribe.call_count, 3)

    def test_transcription_word_level_timestamps(self):
        """Test word-level timestamp extraction."""
        from backend.transcription import extract_word_timestamps

        segment_with_words = {
            "text": "Hello world",
            "words": [
                {"word": "Hello", "start": 0.0, "end": 0.5, "confidence": 0.95},
                {"word": "world", "start": 0.6, "end": 1.0, "confidence": 0.92}
            ]
        }

        word_timestamps = extract_word_timestamps([segment_with_words])

        self.assertEqual(len(word_timestamps), 2)
        self.assertEqual(word_timestamps[0]["word"], "Hello")
        self.assertEqual(word_timestamps[1]["word"], "world")

    def test_transcription_speaker_diarization(self):
        """Test speaker diarization functionality."""
        from backend.transcription import perform_speaker_diarization

        # Mock diarization result
        diarization_result = [
            {"speaker": "SPEAKER_00", "start": 0.0, "end": 2.5},
            {"speaker": "SPEAKER_01", "start": 2.5, "end": 5.0}
        ]

        with patch('backend.transcription.diarize_audio') as mock_diarize:
            mock_diarize.return_value = diarization_result

            result = perform_speaker_diarization(self.test_audio_file)

            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["speaker"], "SPEAKER_00")

    def test_transcription_error_handling(self):
        """Test error handling in transcription process."""
        from backend.transcription import transcribe_audio

        # Test with unsupported audio format
        with self.assertRaises(ValueError):
            transcribe_audio("test.txt")  # Not an audio file

        # Test with corrupted audio file
        with patch('backend.transcription.load_transcription_model') as mock_load_model:
            mock_model = Mock()
            mock_model.transcribe.side_effect = Exception("Transcription failed")
            mock_load_model.return_value = mock_model

            with self.assertRaises(Exception):
                transcribe_audio(self.test_audio_file)


if __name__ == '__main__':
    unittest.main()
