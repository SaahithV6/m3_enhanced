from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class ModelConfig:
    """Configuration for a specific AI model"""
    name: str
    estimated_memory_gb: float
    capabilities: List[str]
    priority: int  # Lower = higher priority
    gpu_required: bool
    dependencies: List[str]

class ModelConfigs:
    """Central registry of all model configurations"""

    def __init__(self):
        self.configs = {
            # Source Separation Models
            "demucs_htdemucs": ModelConfig(
                name="Demucs HT",
                estimated_memory_gb=2.5,
                capabilities=["source_separation", "broad_separation"],
                priority=1,
                gpu_required=True,
                dependencies=["demucs"]
            ),

            "demucs_htdemucs_6s": ModelConfig(
                name="Demucs HT 6-Source",
                estimated_memory_gb=3.0,
                capabilities=["source_separation", "fine_separation"],
                priority=2,
                gpu_required=True,
                dependencies=["demucs"]
            ),

            "mvsep_mdx23": ModelConfig(
                name="MVSEP-MDX23",
                estimated_memory_gb=1.8,
                capabilities=["source_separation", "high_quality_separation"],
                priority=2,
                gpu_required=True,
                dependencies=["audio-separator"]
            ),

            # Transcription Models
            "basic_pitch": ModelConfig(
                name="Basic Pitch",
                estimated_memory_gb=1.2,
                capabilities=["polyphonic_transcription", "general_instruments"],
                priority=1,
                gpu_required=False,
                dependencies=["basic-pitch"]
            ),

            "yourmt3_plus": ModelConfig(
                name="YourMT3+",
                estimated_memory_gb=4.5,
                capabilities=["advanced_transcription", "multi_instrument", "guitar_specific"],
                priority=1,
                gpu_required=True,
                dependencies=["transformers", "torch"]
            ),

            # Classification Models
            "yamnet": ModelConfig(
                name="YAMNet",
                estimated_memory_gb=0.5,
                capabilities=["audio_classification", "instrument_detection"],
                priority=1,
                gpu_required=False,
                dependencies=["tensorflow", "tensorflow-hub"]
            ),

            "openl3": ModelConfig(
                name="OpenL3",
                estimated_memory_gb=0.8,
                capabilities=["audio_embeddings", "similarity_analysis"],
                priority=3,
                gpu_required=False,
                dependencies=["openl3"]
            ),

            # Analysis Models
            "clap": ModelConfig(
                name="CLAP",
                estimated_memory_gb=1.0,
                capabilities=["audio_text_similarity", "instrument_classification"],
                priority=3,
                gpu_required=False,
                dependencies=["laion-clap"]
            )
        }

    def get_config(self, model_name: str) -> Dict[str, Any]:
        """Get configuration for a specific model"""
        config = self.configs.get(model_name)
        if config:
            return {
                "name": config.name,
                "estimated_memory_gb": config.estimated_memory_gb,
                "capabilities": config.capabilities,
                "priority": config.priority,
                "gpu_required": config.gpu_required,
                "dependencies": config.dependencies
            }
        return {}

    def get_models_by_capability(self, capability: str) -> List[str]:
        """Get all models that have a specific capability"""
        return [
            model_name for model_name, config in self.configs.items()
            if capability in config.capabilities
        ]

    def get_separation_models(self) -> List[str]:
        """Get all source separation models ordered by priority"""
        models = self.get_models_by_capability("source_separation")
        return sorted(models, key=lambda x: self.configs[x].priority)

    def get_transcription_models(self) -> List[str]:
        """Get all transcription models ordered by priority"""
        models = [name for name, config in self.configs.items()
                 if any(cap.endswith("transcription") for cap in config.capabilities)]
        return sorted(models, key=lambda x: self.configs[x].priority)

    def get_classification_models(self) -> List[str]:
        """Get all classification models ordered by priority"""
        models = [name for name, config in self.configs.items()
                 if any(cap.endswith("classification") or cap.endswith("detection")
                       for cap in config.capabilities)]
        return sorted(models, key=lambda x: self.configs[x].priority)

    def estimate_total_memory(self, model_names: List[str]) -> float:
        """Estimate total memory usage for a list of models"""
        total = 0.0
        for model_name in model_names:
            config = self.configs.get(model_name)
            if config:
                total += config.estimated_memory_gb
        return total

    def check_dependencies(self, model_name: str) -> Dict[str, bool]:
        """Check if all dependencies for a model are satisfied"""
        config = self.configs.get(model_name)
        if not config:
            return {}

        dependency_status = {}
        for dep in config.dependencies:
            try:
                __import__(dep.replace("-", "_"))
                dependency_status[dep] = True
            except ImportError:
                dependency_status[dep] = False

        return dependency_status

    def get_recommended_separation_pipeline(self) -> List[str]:
        """Get recommended sequence of separation models for multi-pass"""
        return [
            "demucs_htdemucs",      # Pass 1: Broad separation
            "mvsep_mdx23",          # Pass 2+: High-quality refinement
        ]

    def get_recommended_transcription_pipeline(self) -> List[str]:
        """Get recommended sequence of transcription models"""
        # Check if YourMT3+ is available, otherwise fall back to Basic Pitch
        if "yourmt3_plus" in self.configs:
            dependencies = self.check_dependencies("yourmt3_plus")
            if all(dependencies.values()):
                return ["yourmt3_plus", "basic_pitch"]  # YourMT3+ primary, Basic Pitch backup

        return ["basic_pitch"]  # Fallback to Basic Pitch only
