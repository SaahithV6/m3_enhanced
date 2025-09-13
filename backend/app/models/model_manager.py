import torch
import gc
import threading
from pathlib import Path
from typing import Dict, Optional, Any, List
from contextlib import contextmanager
import subprocess
import sys

from ..core.config import config, model_paths
from .model_configs import ModelConfigs

class ModelManager:
    """
    Centralized AI model management system.
    Replaces the scattered model loading in your current implementation.
    Handles memory management, GPU allocation, and model lifecycle.
    """

    def __init__(self):
        self.loaded_models: Dict[str, Any] = {}
        self.model_configs = ModelConfigs()
        self.gpu_memory_limit = self._get_gpu_memory_limit()
        self.lock = threading.Lock()

        # Priority loading order (most important models first)
        self.loading_priority = [
            "demucs_htdemucs",
            "basic_pitch",
            "yamnet",
            "mvsep_mdx23"
        ]

    def _get_gpu_memory_limit(self) -> float:
        """Get available GPU memory in GB"""
        if torch.cuda.is_available():
            return torch.cuda.get_device_properties(0).total_memory / (1024**3)
        return 0.0

    @contextmanager
    def model_context(self, model_name: str):
        """Context manager for safe model usage with automatic cleanup"""
        model = self.load_model(model_name)
        try:
            yield model
        finally:
            # Keep model loaded for reuse, but clear cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    def load_model(self, model_name: str, force_reload: bool = False) -> Any:
        """Load a specific model with memory management"""
        with self.lock:
            if model_name in self.loaded_models and not force_reload:
                return self.loaded_models[model_name]

            # Check if we need to free memory for the new model
            self._manage_memory_for_model(model_name)

            print(f"Loading model: {model_name}")
            model = self._load_specific_model(model_name)

            if model is not None:
                self.loaded_models[model_name] = model
                print(f"Successfully loaded {model_name}")
            else:
                print(f"Failed to load {model_name}")

            return model

    def _manage_memory_for_model(self, model_name: str):
        """Free memory if needed before loading a new model"""
        config = self.model_configs.get_config(model_name)
        estimated_memory = config.get('estimated_memory_gb', 2.0)

        # If we're running low on memory, unload less important models
        if self.gpu_memory_limit > 0:
            available_memory = self._get_available_gpu_memory()

            if available_memory < estimated_memory:
                self._free_memory_for_space(estimated_memory - available_memory)

    def _get_available_gpu_memory(self) -> float:
        """Get currently available GPU memory in GB"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            return (torch.cuda.get_device_properties(0).total_memory -
                   torch.cuda.memory_allocated()) / (1024**3)
        return float('inf')

    def _free_memory_for_space(self, needed_gb: float):
        """Free up GPU memory by unloading models"""
        # Unload models in reverse priority order
        for model_name in reversed(self.loading_priority):
            if model_name in self.loaded_models:
                print(f"Unloading {model_name} to free memory")
                del self.loaded_models[model_name]
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

                if self._get_available_gpu_memory() >= needed_gb:
                    break

    def _load_specific_model(self, model_name: str) -> Optional[Any]:
        """Load a specific model based on its type"""
        try:
            if model_name.startswith("demucs_"):
                return self._load_demucs_model(model_name)
            elif model_name == "basic_pitch":
                return self._load_basic_pitch_model()
            elif model_name == "yamnet":
                return self._load_yamnet_model()
            elif model_name.startswith("mvsep_"):
                return self._load_mvsep_model(model_name)
            elif model_name == "yourmt3_plus":
                return self._load_yourmt3_model()
            elif model_name == "openl3":
                return self._load_openl3_model()
            else:
                print(f"Unknown model type: {model_name}")
                return None

        except Exception as e:
            print(f"Failed to load {model_name}: {e}")
            return None

    def _load_demucs_model(self, model_name: str):
        """Load Demucs separation model"""
        from demucs.pretrained import get_model

        model_type = model_name.split("_", 1)[1]  # e.g., "htdemucs" from "demucs_htdemucs"
        return get_model(model_type)

    def _load_basic_pitch_model(self):
        """Load Basic Pitch transcription model"""
        import basic_pitch
        from basic_pitch.inference import predict

        # Basic Pitch loads automatically when used
        return {"predict": predict, "loaded": True}

    def _load_yamnet_model(self):
        """Load YAMNet audio classification model"""
        try:
            import tensorflow as tf
            import tensorflow_hub as hub

            model = hub.load('https://tfhub.dev/google/yamnet/1')
            return model
        except ImportError:
            print("TensorFlow not available for YAMNet. Install with: pip install tensorflow tensorflow-hub")
            return None

    def _load_mvsep_model(self, model_name: str):
        """Load MVSEP-MDX23 model using audio-separator"""
        try:
            from audio_separator.separator import Separator

            model_type = model_name.split("_", 1)[1]  # e.g., "mdx23" from "mvsep_mdx23"
            separator = Separator(
                model_file_dir=str(model_paths.mvsep_dir),
                output_dir=str(config.TEMP_DIR)
            )

            return separator
        except ImportError:
            print("audio-separator not available. Install with: pip install audio-separator")
            return None

    def _load_yourmt3_model(self):
        """Load YourMT3+ model (when available)"""
        # This would be implemented when YourMT3+ becomes available
        print("YourMT3+ not yet available. Falling back to Basic Pitch.")
        return self._load_basic_pitch_model()

    def _load_openl3_model(self):
        """Load OpenL3 audio embedding model"""
        try:
            import openl3
            return openl3
        except ImportError:
            print("OpenL3 not available. Install with: pip install openl3")
            return None

    def preload_essential_models(self):
        """Preload the most critical models for fast processing"""
        essential_models = ["demucs_htdemucs", "basic_pitch", "yamnet"]

        for model_name in essential_models:
            try:
                self.load_model(model_name)
            except Exception as e:
                print(f"Failed to preload {model_name}: {e}")

    def get_model_info(self) -> Dict[str, Dict]:
        """Get information about all loaded models"""
        info = {}
        for model_name, model in self.loaded_models.items():
            config = self.model_configs.get_config(model_name)
            info[model_name] = {
                "loaded": True,
                "memory_usage_gb": config.get('estimated_memory_gb', 'unknown'),
                "capabilities": config.get('capabilities', [])
            }
        return info

    def cleanup_all_models(self):
        """Clean up all loaded models and free memory"""
        with self.lock:
            for model_name in list(self.loaded_models.keys()):
                del self.loaded_models[model_name]

            self.loaded_models.clear()
            gc.collect()

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            print("All models cleaned up and memory freed")

# Global model manager instance
model_manager = ModelManager()
