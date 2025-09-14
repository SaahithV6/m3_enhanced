"""
M3 Enhanced Model Benchmarking Suite
Comprehensive performance testing and optimization analysis
"""

import time
import gc
import json
import statistics
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import logging
import psutil
import threading
from contextlib import contextmanager
import numpy as np
import sys

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import config
from app.models.model_manager import ModelManager
from app.utils.audio_utils import AudioUtils
from app.core.quality_metrics import QualityAssessment

# GPU monitoring imports
try:
    import GPUtil
    import pynvml
    pynvml.nvmlInit()
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class BenchmarkResult:
    """Container for benchmark results"""
    model_name: str
    task_type: str
    execution_time: float
    memory_usage_mb: float
    gpu_memory_mb: Optional[float]
    cpu_usage_percent: float
    throughput_factor: float  # Processing speed vs real-time
    quality_score: Optional[float]
    success: bool
    error_message: Optional[str]

@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    gpu_memory_mb: Optional[float]
    gpu_utilization: Optional[float]

class PerformanceMonitor:
    """Real-time performance monitoring"""

    def __init__(self):
        self.monitoring = False
        self.metrics: List[SystemMetrics] = []
        self.monitor_thread = None

    def start_monitoring(self):
        """Start performance monitoring"""
        self.monitoring = True
        self.metrics = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.start()

    def stop_monitoring(self) -> List[SystemMetrics]:
        """Stop monitoring and return collected metrics"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        return self.metrics

    def _monitor_loop(self):
        """Monitoring loop"""
        while self.monitoring:
            try:
                # CPU and memory
                cpu_percent = psutil.cpu_percent()
                memory_mb = psutil.virtual_memory().used / (1024**2)

                # GPU metrics
                gpu_memory_mb = None
                gpu_utilization = None

                if GPU_AVAILABLE:
                    try:
                        gpus = GPUtil.getGPUs()
                        if gpus:
                            gpu = gpus[0]
                            gpu_memory_mb = gpu.memoryUsed
                            gpu_utilization = gpu.load * 100
                    except:
                        pass

                metric = SystemMetrics(
                    timestamp=time.time(),
                    cpu_percent=cpu_percent,
                    memory_mb=memory_mb,
                    gpu_memory_mb=gpu_memory_mb,
                    gpu_utilization=gpu_utilization
                )

                self.metrics.append(metric)
                time.sleep(0.5)  # Sample every 500ms

            except Exception as e:
                logger.warning(f"Monitoring error: {str(e)}")

class ModelBenchmark:
    """Comprehensive model benchmarking system"""

    def __init__(self):
        self.model_manager = ModelManager()
        self.audio_utils = AudioUtils()
        self.quality_assessment = QualityAssessment()
        self.monitor = PerformanceMonitor()

        # Test audio configurations
        self.test_configs = [
            {"duration": 30, "sample_rate": 44100, "description": "30s test"},
            {"duration": 60, "sample_rate": 44100, "description": "1min test"},
            {"duration": 180, "sample_rate": 44100, "description": "3min test"},
        ]

        # Models to benchmark
        self.models_to_test = [
            "demucs_htdemucs",
            "basic_pitch",
            "yamnet",
            "mvsep_mdx23"
        ]

    def run_full_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive benchmark suite"""

        logger.info("🚀 Starting M3 Enhanced benchmark suite")

        results = {
            "benchmark_info": {
                "timestamp": time.time(),
                "system_info": self._get_system_info(),
                "test_configurations": self.test_configs
            },
            "model_results": {},
            "performance_analysis": {},
            "recommendations": []
        }

        # Generate test audio files
        test_audio_paths = self._generate_test_audio()

        # Benchmark each model
        for model_name in self.models_to_test:
            logger.info(f"📊 Benchmarking {model_name}")

            model_results = []

            for config in self.test_configs:
                result = self._benchmark_model(
                    model_name,
                    test_audio_paths[config["duration"]],
                    config
                )
                model_results.append(result)

            results["model_results"][model_name] = model_results

        # Analyze performance patterns
        results["performance_analysis"] = self._analyze_performance(results["model_results"])

        # Generate recommendations
        results["recommendations"] = self._generate_recommendations(results)

        # Save results
        self._save_benchmark_results(results)

        logger.info("✅ Benchmark suite completed")
        return results

    def _get_system_info(self) -> Dict[str, Any]:
        """Get detailed system information"""

        info = {
            "cpu_count": psutil.cpu_count(logical=False),
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "memory_total_gb": psutil.virtual_memory().total / (1024**3),
            "python_version": sys.version,
            "platform": sys.platform
        }

        if GPU_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    info.update({
                        "gpu_name": gpu.name,
                        "gpu_memory_total_mb": gpu.memoryTotal,
                        "gpu_driver": gpu.driver
                    })
            except:
                pass

        return info

    def _generate_test_audio(self) -> Dict[int, Path]:
        """Generate synthetic test audio files"""

        logger.info("🎵 Generating test audio files")

        test_audio_dir = Path(config.TEMP_DIR) / "benchmark_audio"
        test_audio_dir.mkdir(parents=True, exist_ok=True)

        audio_paths = {}

        for config in self.test_configs:
            duration = config["duration"]
            sample_rate = config["sample_rate"]

            # Generate complex synthetic audio (mix of tones, noise, and harmonics)
            t = np.linspace(0, duration, int(duration * sample_rate))

            # Base frequency and harmonics
            audio = 0.3 * np.sin(2 * np.pi * 440 * t)  # A4
            audio += 0.2 * np.sin(2 * np.pi * 880 * t)  # A5
            audio += 0.1 * np.sin(2 * np.pi * 1320 * t) # E6

            # Add bass line
            audio += 0.4 * np.sin(2 * np.pi * 110 * t)  # A2

            # Add percussion-like transients
            for i in range(0, duration, 1):
                if i < len(t):
                    start_idx = int(i * sample_rate)
                    end_idx = min(start_idx + int(0.1 * sample_rate), len(audio))
                    audio[start_idx:end_idx] += 0.3 * np.exp(-10 * np.linspace(0, 0.1, end_idx - start_idx))

            # Add some noise for realism
            audio += 0.05 * np.random.normal(0, 1, len(audio))

            # Normalize
            audio = audio / np.max(np.abs(audio)) * 0.8

            # Save audio file
            audio_path = test_audio_dir / f"test_{duration}s.wav"
            self.audio_utils.save_audio(audio, audio_path, sample_rate)

            audio_paths[duration] = audio_path
            logger.debug(f"Generated {duration}s test audio: {audio_path}")

        return audio_paths

    def _benchmark_model(self, model_name: str, audio_path: Path, config: Dict) -> BenchmarkResult:
        """Benchmark a single model with specific configuration"""

        logger.info(f"  Testing {model_name} with {config['description']}")

        try:
            # Clear memory before test
            gc.collect()
            if GPU_AVAILABLE:
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except:
                    pass

            # Start monitoring
            self.monitor.start_monitoring()

            # Record initial state
            initial_memory = psutil.virtual_memory().used / (1024**2)
            initial_gpu_memory = None

            if GPU_AVAILABLE:
                try:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        initial_gpu_memory = gpus[0].memoryUsed
                except:
                    pass

            # Load audio
            audio, sr = self.audio_utils.load_audio(audio_path)
            audio_duration = len(audio) / sr

            # Execute model
            start_time = time.time()

            with self.model_manager.model_context(model_name) as model:
                if model is None:
                    raise ValueError(f"Failed to load model: {model_name}")

                # Simulate model processing (replace with actual model calls)
                result = self._execute_model_task(model, model_name, audio, sr)

            execution_time = time.time() - start_time

            # Stop monitoring
            metrics = self.monitor.stop_monitoring()

            # Calculate performance metrics
            final_memory = psutil.virtual_memory().used / (1024**2)
            memory_usage = final_memory - initial_memory

            final_gpu_memory = None
            gpu_memory_usage = None

            if GPU_AVAILABLE and initial_gpu_memory is not None:
                try:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        final_gpu_memory = gpus[0].memoryUsed
                        gpu_memory_usage = final_gpu_memory - initial_gpu_memory
                except:
                    pass

            # Calculate average CPU usage during test
            cpu_usage = statistics.mean([m.cpu_percent for m in metrics]) if metrics else 0

            # Calculate throughput factor (how fast vs real-time)
            throughput_factor = audio_duration / execution_time if execution_time > 0 else 0

            # Assess quality if applicable
            quality_score = None
            if result is not None:
                try:
                    quality_score = self._assess_result_quality(result, model_name)
                except:
                    pass

            return BenchmarkResult(
                model_name=model_name,
                task_type=config["description"],
                execution_time=execution_time,
                memory_usage_mb=memory_usage,
                gpu_memory_mb=gpu_memory_usage,
                cpu_usage_percent=cpu_usage,
                throughput_factor=throughput_factor,
                quality_score=quality_score,
                success=True,
                error_message=None
            )

        except Exception as e:
            # Stop monitoring in case of error
            self.monitor.stop_monitoring()

            logger.error(f"Benchmark failed for {model_name}: {str(e)}")

            return BenchmarkResult(
                model_name=model_name,
                task_type=config["description"],
                execution_time=0,
                memory_usage_mb=0,
                gpu_memory_mb=None,
                cpu_usage_percent=0,
                throughput_factor=0,
                quality_score=None,
                success=False,
                error_message=str(e)
            )

    def _execute_model_task(self, model: Any, model_name: str, audio: np.ndarray, sr: int) -> Any:
        """Execute model-specific task (placeholder for actual implementation)"""

        # This is a placeholder - in the real implementation, you would call
        # the specific model inference functions here

        if "demucs" in model_name:
            # Simulate source separation
            time.sleep(len(audio) / sr * 0.1)  # Simulate processing time
            return {"separated_stems": ["vocals", "drums", "bass", "other"]}

        elif "basic_pitch" in model_name:
            # Simulate transcription
            time.sleep(len(audio) / sr * 0.05)
            return {"notes": [], "confidence": 0.85}

        elif "yamnet" in model_name:
            # Simulate classification
            time.sleep(len(audio) / sr * 0.02)
            return {"classifications": ["music", "guitar"], "confidence": 0.9}

        else:
            # Generic processing
            time.sleep(len(audio) / sr * 0.03)
            return {"processed": True}

    def _assess_result_quality(self, result: Any, model_name: str) -> float:
        """Assess quality of model results"""

        # Placeholder quality assessment
        if isinstance(result, dict):
            if "confidence" in result:
                return result["confidence"]
            elif "separated_stems" in result:
                return 0.8  # Simulated separation quality

        return 0.75  # Default quality score

    def _analyze_performance(self, model_results: Dict[str, List[BenchmarkResult]]) -> Dict[str, Any]:
        """Analyze performance patterns across models"""

        analysis = {
            "fastest_models": [],
            "most_efficient_memory": [],
            "best_throughput": [],
            "performance_scaling": {}
        }

        # Find fastest models for each test duration
        for duration in [30, 60, 180]:
            duration_results = []
            for model_name, results in model_results.items():
                for result in results:
                    if f"{duration}s" in result.task_type and result.success:
                        duration_results.append((model_name, result.execution_time))

            if duration_results:
                fastest = min(duration_results, key=lambda x: x[1])
                analysis["fastest_models"].append({
                    "duration": duration,
                    "model": fastest[0],
                    "time": fastest[1]
                })

        # Analyze memory efficiency
        memory_efficiency = []
        for model_name, results in model_results.items():
            avg_memory = statistics.mean([r.memory_usage_mb for r in results if r.success])
            memory_efficiency.append((model_name, avg_memory))

        analysis["most_efficient_memory"] = sorted(memory_efficiency, key=lambda x: x[1])[:3]

        # Analyze throughput
        throughput_analysis = []
        for model_name, results in model_results.items():
            avg_throughput = statistics.mean([r.throughput_factor for r in results if r.success])
            throughput_analysis.append((model_name, avg_throughput))

        analysis["best_throughput"] = sorted(throughput_analysis, key=lambda x: x[1], reverse=True)[:3]

        return analysis

    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations"""

        recommendations = []

        # Check GPU utilization
        if not GPU_AVAILABLE:
            recommendations.append("🎮 Consider using GPU runtime for significantly better performance")

        # Memory recommendations
        system_memory = results["benchmark_info"]["system_info"]["memory_total_gb"]
        if system_memory < 8:
            recommendations.append("💾 Consider increasing RAM to at least 8GB for optimal performance")

        # Model-specific recommendations
        model_results = results["model_results"]

        for model_name, model_data in model_results.items():
            failed_tests = [r for r in model_data if not r.success]
            if failed_tests:
                recommendations.append(f"⚠️  {model_name} failed on some tests - check dependencies")

        # Performance recommendations
        performance = results["performance_analysis"]
        if performance["best_throughput"]:
            best_model = performance["best_throughput"][0][0]
            recommendations.append(f"🚀 {best_model} shows best throughput for real-time processing")

        return recommendations

    def _save_benchmark_results(self, results: Dict[str, Any]):
        """Save benchmark results to file"""

        # Convert dataclasses to dictionaries for JSON serialization
        serializable_results = results.copy()

        for model_name, model_data in serializable_results["model_results"].items():
            serializable_results["model_results"][model_name] = [
                asdict(result) for result in model_data
            ]

        # Save to file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results_path = Path(config.RESULTS_DIR) / f"benchmark_results_{timestamp}.json"

        with open(results_path, 'w') as f:
            json.dump(serializable_results, f, indent=2, default=str)

        logger.info(f"📊 Benchmark results saved to: {results_path}")

        # Also save a summary report
        self._save_summary_report(results, results_path.with_suffix('.txt'))

    def _save_summary_report(self, results: Dict[str, Any], report_path: Path):
        """Save human-readable summary report"""

        with open(report_path, 'w') as f:
            f.write("M3 ENHANCED - BENCHMARK REPORT\n")
            f.write("=" * 50 + "\n\n")

            # System info
            system_info = results["benchmark_info"]["system_info"]
            f.write("SYSTEM INFORMATION:\n")
            f.write(f"CPU Cores: {system_info['cpu_count']}\n")
            f.write(f"Memory: {system_info['memory_total_gb']:.1f} GB\n")
            if "gpu_name" in system_info:
                f.write(f"GPU: {system_info['gpu_name']}\n")
            f.write("\n")

            # Performance summary
            f.write("PERFORMANCE SUMMARY:\n")

            for model_name, model_data in results["model_results"].items():
                f.write(f"\n{model_name}:\n")
                for result in model_data:
                    if result.success:
                        f.write(f"  {result.task_type}: {result.execution_time:.2f}s ")
                        f.write(f"({result.throughput_factor:.1f}x real-time)\n")
                    else:
                        f.write(f"  {result.task_type}: FAILED - {result.error_message}\n")

            # Recommendations
            f.write("\nRECOMMENDATIONS:\n")
            for rec in results["recommendations"]:
                f.write(f"- {rec}\n")

        logger.info(f"📋 Summary report saved to: {report_path}")

def main():
    """Main benchmark function"""

    import argparse

    parser = argparse.ArgumentParser(description="M3 Enhanced Model Benchmarking")
    parser.add_argument("--models", nargs="+", help="Specific models to benchmark")
    parser.add_argument("--quick", action="store_true", help="Run quick benchmark (30s test only)")

    args = parser.parse_args()

    benchmark = ModelBenchmark()

    if args.models:
        benchmark.models_to_test = args.models

    if args.quick:
        benchmark.test_configs = [benchmark.test_configs[0]]  # Only 30s test

    try:
        results = benchmark.run_full_benchmark()

        print("\n🎉 Benchmark completed successfully!")
        print(f"📊 Results saved to: {config.RESULTS_DIR}")

        # Display quick summary
        print("\n📈 QUICK SUMMARY:")
        for recommendation in results["recommendations"][:3]:
            print(f"  {recommendation}")

    except KeyboardInterrupt:
        print("\n⚠️  Benchmark interrupted by user")
    except Exception as e:
        print(f"\n❌ Benchmark failed: {str(e)}")
        logger.error(f"Benchmark error: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
