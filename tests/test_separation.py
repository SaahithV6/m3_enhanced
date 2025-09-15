import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import tempfile
import os
import torch


class TestAudioSeparation(unittest.TestCase):
    """Test suite for audio source separation functionality."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_audio_file = "test_audio.wav"
        self.temp_dir = tempfile.mkdtemp()
        self.sample_rate = 44100
        self.duration = 5.0

        # Create mock audio data
        self.mock_audio_data = np.random.randn(2, int(self.sample_rate * self.duration))

    def tearDown(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    @patch('backend.separation.demucs.pretrained')
    def test_load_separation_model(self, mock_pretrained):
        """Test loading of separation model."""
        mock_model = Mock()
        mock_pretrained.get_model.return_value = mock_model

        from backend.separation import load_separation_model

        model = load_separation_model("htdemucs")

        mock_pretrained.get_model.assert_called_once_with("htdemucs")
        self.assertEqual(model, mock_model)

    @patch('backend.separation.torchaudio.load')
    def test_load_audio_file(self, mock_load):
        """Test audio file loading."""
        mock_load.return_value = (torch.tensor(self.mock_audio_data), self.sample_rate)

        from backend.separation import load_audio

        audio, sr = load_audio(self.test_audio_file)

        mock_load.assert_called_once_with(self.test_audio_file)
        self.assertEqual(sr, self.sample_rate)
        self.assertEqual(audio.shape, torch.tensor(self.mock_audio_data).shape)

    def test_load_nonexistent_audio_file(self):
        """Test loading non-existent audio file."""
        from backend.separation import load_audio

        with self.assertRaises(FileNotFoundError):
            load_audio("nonexistent_file.wav")

    @patch('backend.separation.load_separation_model')
    @patch('backend.separation.load_audio')
    @patch('backend.separation.torch.no_grad')
    def test_separate_audio_basic(self, mock_no_grad, mock_load_audio, mock_load_model):
        """Test basic audio separation functionality."""
        # Mock model and audio loading
        mock_model = Mock()
        mock_load_model.return_value = mock_model
        mock_load_audio.return_value = (torch.tensor(self.mock_audio_data), self.sample_rate)

        # Mock model output (4 sources: drums, bass, other, vocals)
        mock_separated = torch.randn(4, 2, int(self.sample_rate * self.duration))
        mock_model.return_value = mock_separated

        from backend.separation import separate_audio

        result = separate_audio(self.test_audio_file, model="htdemucs")

        # Check that all expected sources are present
        expected_sources = ["drums", "bass", "other", "vocals"]
        for source in expected_sources:
            self.assertIn(source, result)
            self.assertTrue(result[source].endswith('.wav'))

    @patch('backend.separation.load_separation_model')
    @patch('backend.separation.load_audio')
    def test_separate_audio_with_device(self, mock_load_audio, mock_load_model):
        """Test audio separation with specific device."""
        mock_model = Mock()
        mock_load_model.return_value = mock_model
        mock_load_audio.return_value = (torch.tensor(self.mock_audio_data), self.sample_rate)

        mock_separated = torch.randn(4, 2, int(self.sample_rate * self.duration))
        mock_model.return_value = mock_separated

        from backend.separation import separate_audio

        # Test with CPU device
        result = separate_audio(self.test_audio_file, device="cpu")
        self.assertIsNotNone(result)

        # Test with CUDA device (if available)
        if torch.cuda.is_available():
            result = separate_audio(self.test_audio_file, device="cuda")
            self.assertIsNotNone(result)

    def test_separation_preprocessing(self):
        """Test audio preprocessing before separation."""
        from backend.separation import preprocess_audio

        # Test stereo to mono conversion
        stereo_audio = torch.randn(2, 1000)
        mono_audio = preprocess_audio(stereo_audio, target_channels=1)
        self.assertEqual(mono_audio.shape[0], 1)

        # Test sample rate conversion
        audio_44k = torch.randn(1, 4410)  # 1 second at 44.1kHz
        audio_22k = preprocess_audio(audio_44k, original_sr=44100, target_sr=22050)
        self.assertEqual(audio_22k.shape[1], 2205)  # 1 second at 22.05kHz

    def test_separation_postprocessing(self):
        """Test audio postprocessing after separation."""
        from backend.separation import postprocess_separated_audio

        # Mock separated sources
        separated_sources = {
            "vocals": torch.randn(2, 44100),
            "drums": torch.randn(2, 44100),
            "bass": torch.randn(2, 44100),
            "other": torch.randn(2, 44100)
        }

        processed = postprocess_separated_audio(separated_sources)

        # Check that all sources are processed
        for source_name in separated_sources.keys():
            self.assertIn(source_name, processed)

    @patch('backend.separation.torchaudio.save')
    def test_save_separated_sources(self, mock_save):
        """Test saving separated audio sources to files."""
        from backend.separation import save_separated_sources

        sources = {
            "vocals": torch.randn(2, 44100),
            "drums": torch.randn(2, 44100)
        }

        output_dir = self.temp_dir
        result = save_separated_sources(sources, output_dir, self.sample_rate)

        # Check that save was called for each source
        self.assertEqual(mock_save.call_count, 2)

        # Check return value contains file paths
        for source_name in sources.keys():
            self.assertIn(source_name, result)
            self.assertTrue(result[source_name].endswith('.wav'))

    def test_separation_quality_metrics(self):
        """Test separation quality evaluation metrics."""
        from backend.separation import calculate_separation_metrics

        # Mock reference and estimated sources
        reference_vocals = torch.randn(2, 44100)
        estimated_vocals = torch.randn(2, 44100)

        metrics = calculate_separation_metrics(reference_vocals, estimated_vocals)

        # Check that standard metrics are calculated
        expected_metrics = ["sdr", "sir", "sar"]
        for metric in expected_metrics:
            self.assertIn(metric, metrics)
            self.assertIsInstance(metrics[metric], (int, float))

    def test_separation_with_different_models(self):
        """Test separation with different model architectures."""
        models_to_test = ["htdemucs", "mdx", "mdx_extra"]

        for model_name in models_to_test:
            with patch('backend.separation.load_separation_model') as mock_load_model, \
                 patch('backend.separation.load_audio') as mock_load_audio:

                mock_model = Mock()
                mock_load_model.return_value = mock_model
                mock_load_audio.return_value = (torch.tensor(self.mock_audio_data), self.sample_rate)

                mock_separated = torch.randn(4, 2, int(self.sample_rate * self.duration))
                mock_model.return_value = mock_separated

                from backend.separation import separate_audio

                result = separate_audio(self.test_audio_file, model=model_name)
                self.assertIsNotNone(result)

    def test_separation_batch_processing(self):
        """Test batch processing of multiple audio files."""
        audio_files = ["file1.wav", "file2.wav", "file3.wav"]

        with patch('backend.separation.separate_audio') as mock_separate:
            mock_separate.return_value = {
                "vocals": "vocals.wav",
                "drums": "drums.wav",
                "bass": "bass.wav",
                "other": "other.wav"
            }

            from backend.separation import separate_audio_batch

            results = separate_audio_batch(audio_files)

            self.assertEqual(len(results), 3)
            self.assertEqual(mock_separate.call_count, 3)

    def test_separation_error_handling(self):
        """Test error handling in separation process."""
        from backend.separation import separate_audio

        # Test with invalid model name
        with self.assertRaises(ValueError):
            separate_audio(self.test_audio_file, model="invalid_model")

        # Test with invalid device
        with self.assertRaises(RuntimeError):
            separate_audio(self.test_audio_file, device="invalid_device")


if __name__ == '__main__':
    unittest.main()
