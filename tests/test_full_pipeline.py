import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import json
from pathlib import Path


class TestFullPipeline(unittest.TestCase):
    """Test suite for the complete audio processing pipeline."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_audio_file = "test_audio.wav"
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            "separation": {
                "model": "htdemucs",
                "device": "cpu"
            },
            "transcription": {
                "model": "whisper-base",
                "language": "en"
            },
            "output": {
                "format": "json",
                "include_timestamps": True
            }
        }

    def tearDown(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    @patch('backend.pipeline.AudioProcessor')
    def test_pipeline_initialization(self, mock_processor):
        """Test that the pipeline initializes correctly with configuration."""
        from backend.pipeline import FullPipeline

        pipeline = FullPipeline(self.config)
        self.assertIsNotNone(pipeline)
        self.assertEqual(pipeline.config, self.config)

    @patch('backend.separation.separate_audio')
    @patch('backend.transcription.transcribe_audio')
    def test_full_pipeline_process(self, mock_transcribe, mock_separate):
        """Test the complete pipeline processing flow."""
        # Mock separation results
        mock_separate.return_value = {
            "vocals": "vocals.wav",
            "accompaniment": "accompaniment.wav",
            "drums": "drums.wav",
            "bass": "bass.wav"
        }

        # Mock transcription results
        mock_transcribe.return_value = {
            "text": "Hello world this is a test",
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.5,
                    "text": "Hello world"
                },
                {
                    "start": 2.5,
                    "end": 5.0,
                    "text": "this is a test"
                }
            ],
            "language": "en",
            "confidence": 0.95
        }

        from backend.pipeline import FullPipeline
        pipeline = FullPipeline(self.config)

        result = pipeline.process(self.test_audio_file)

        # Verify separation was called
        mock_separate.assert_called_once_with(
            self.test_audio_file,
            model=self.config["separation"]["model"],
            device=self.config["separation"]["device"]
        )

        # Verify transcription was called for vocals
        mock_transcribe.assert_called_once_with(
            "vocals.wav",
            model=self.config["transcription"]["model"],
            language=self.config["transcription"]["language"]
        )

        # Verify result structure
        self.assertIn("separation", result)
        self.assertIn("transcription", result)
        self.assertIn("metadata", result)

    def test_pipeline_with_invalid_audio_file(self):
        """Test pipeline behavior with non-existent audio file."""
        from backend.pipeline import FullPipeline

        pipeline = FullPipeline(self.config)

        with self.assertRaises(FileNotFoundError):
            pipeline.process("nonexistent_file.wav")

    @patch('backend.separation.separate_audio')
    def test_pipeline_separation_failure(self, mock_separate):
        """Test pipeline behavior when separation fails."""
        mock_separate.side_effect = Exception("Separation failed")

        from backend.pipeline import FullPipeline
        pipeline = FullPipeline(self.config)

        with self.assertRaises(Exception) as context:
            pipeline.process(self.test_audio_file)

        self.assertIn("Separation failed", str(context.exception))

    @patch('backend.separation.separate_audio')
    @patch('backend.transcription.transcribe_audio')
    def test_pipeline_transcription_failure(self, mock_transcribe, mock_separate):
        """Test pipeline behavior when transcription fails."""
        mock_separate.return_value = {"vocals": "vocals.wav"}
        mock_transcribe.side_effect = Exception("Transcription failed")

        from backend.pipeline import FullPipeline
        pipeline = FullPipeline(self.config)

        with self.assertRaises(Exception) as context:
            pipeline.process(self.test_audio_file)

        self.assertIn("Transcription failed", str(context.exception))

    def test_pipeline_output_format_json(self):
        """Test pipeline output in JSON format."""
        with patch('backend.separation.separate_audio') as mock_separate, \
             patch('backend.transcription.transcribe_audio') as mock_transcribe:

            mock_separate.return_value = {"vocals": "vocals.wav"}
            mock_transcribe.return_value = {"text": "test text"}

            from backend.pipeline import FullPipeline
            pipeline = FullPipeline(self.config)

            result = pipeline.process(self.test_audio_file)

            # Should be JSON serializable
            json_str = json.dumps(result)
            self.assertIsInstance(json_str, str)

    def test_pipeline_with_custom_output_directory(self):
        """Test pipeline with custom output directory."""
        config_with_output = self.config.copy()
        config_with_output["output"]["directory"] = self.temp_dir

        with patch('backend.separation.separate_audio') as mock_separate, \
             patch('backend.transcription.transcribe_audio') as mock_transcribe:

            mock_separate.return_value = {"vocals": "vocals.wav"}
            mock_transcribe.return_value = {"text": "test text"}

            from backend.pipeline import FullPipeline
            pipeline = FullPipeline(config_with_output)

            result = pipeline.process(self.test_audio_file)

            self.assertIn("output_directory", result["metadata"])

    def test_pipeline_progress_callback(self):
        """Test pipeline with progress callback."""
        progress_calls = []

        def progress_callback(stage, progress):
            progress_calls.append((stage, progress))

        with patch('backend.separation.separate_audio') as mock_separate, \
             patch('backend.transcription.transcribe_audio') as mock_transcribe:

            mock_separate.return_value = {"vocals": "vocals.wav"}
            mock_transcribe.return_value = {"text": "test text"}

            from backend.pipeline import FullPipeline
            pipeline = FullPipeline(self.config)

            result = pipeline.process(self.test_audio_file, progress_callback=progress_callback)

            # Should have received progress updates
            self.assertGreater(len(progress_calls), 0)

    def test_pipeline_batch_processing(self):
        """Test pipeline batch processing multiple files."""
        audio_files = ["file1.wav", "file2.wav", "file3.wav"]

        with patch('backend.separation.separate_audio') as mock_separate, \
             patch('backend.transcription.transcribe_audio') as mock_transcribe:

            mock_separate.return_value = {"vocals": "vocals.wav"}
            mock_transcribe.return_value = {"text": "test text"}

            from backend.pipeline import FullPipeline
            pipeline = FullPipeline(self.config)

            results = pipeline.process_batch(audio_files)

            self.assertEqual(len(results), 3)
            self.assertEqual(mock_separate.call_count, 3)
            self.assertEqual(mock_transcribe.call_count, 3)


if __name__ == '__main__':
    unittest.main()
