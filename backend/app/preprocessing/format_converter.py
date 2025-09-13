import subprocess
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import json
import tempfile
import shutil
import yt_dlp
from concurrent.futures import ThreadPoolExecutor
import time

from ..core.config import config
from ..utils.audio_utils import AudioUtils

class FormatConverter:
    """
    Production-grade format converter with FFmpeg integration.
    Supports hardware acceleration, batch processing, and format optimization.
    """

    def __init__(self):
        self.audio_utils = AudioUtils()

        # FFmpeg binary path
        self.ffmpeg_path = self._find_ffmpeg()
        self.ffprobe_path = self._find_ffprobe()

        # Hardware acceleration detection
        self.hw_accel = self._detect_hardware_acceleration()

        # Optimal format configurations
        self.format_configs = {
            "wav": {
                "codec": "pcm_s24le",
                "sample_rate": 44100,
                "bit_depth": 24,
                "channels": 2,
                "quality": "lossless"
            },
            "flac": {
                "codec": "flac",
                "sample_rate": 44100,
                "compression_level": 8,
                "channels": 2,
                "quality": "lossless"
            },
            "mp3": {
                "codec": "libmp3lame",
                "sample_rate": 44100,
                "bitrate": "320k",
                "channels": 2,
                "quality": "high"
            },
            "aac": {
                "codec": "aac",
                "sample_rate": 44100,
                "bitrate": "256k",
                "channels": 2,
                "quality": "high"
            },
            "processing": {
                "codec": "pcm_f32le",
                "sample_rate": 44100,
                "bit_depth": 32,
                "channels": 2,
                "quality": "processing"
            }
        }

        # yt-dlp configuration for URL downloads
        self.ytdl_opts = {
            'format': 'bestaudio/best',
            'extractaudio': True,
            'audioformat': 'wav',
            'audioquality': '0',  # Best quality
            'embed_subs': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ignoreerrors': True,
            'no_warnings': True,
            'quiet': True,
            'outtmpl': str(config.TEMP_DIR / '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }]
        }

    def _find_ffmpeg(self) -> str:
        """Find FFmpeg binary path"""
        try:
            result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                # Try common locations
                common_paths = [
                    '/usr/bin/ffmpeg',
                    '/usr/local/bin/ffmpeg',
                    '/opt/homebrew/bin/ffmpeg',
                    'ffmpeg'  # Assume it's in PATH
                ]

                for path in common_paths:
                    try:
                        subprocess.run([path, '-version'], capture_output=True, check=True)
                        return path
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue

                raise FileNotFoundError("FFmpeg not found")

        except Exception as e:
            print(f"FFmpeg detection failed: {e}")
            return "ffmpeg"  # Fallback

    def _find_ffprobe(self) -> str:
        """Find FFprobe binary path"""
        return self.ffmpeg_path.replace('ffmpeg', 'ffprobe')

    def _detect_hardware_acceleration(self) -> Dict[str, bool]:
        """Detect available hardware acceleration"""
        hw_accel = {
            'nvidia': False,
            'intel': False,
            'amd': False,
            'apple': False
        }

        try:
            # Check for NVIDIA NVENC
            result = subprocess.run([
                self.ffmpeg_path, '-hide_banner', '-encoders'
            ], capture_output=True, text=True)

            if 'h264_nvenc' in result.stdout:
                hw_accel['nvidia'] = True
            if 'h264_qsv' in result.stdout:
                hw_accel['intel'] = True
            if 'h264_amf' in result.stdout:
                hw_accel['amd'] = True
            if 'h264_videotoolbox' in result.stdout:
                hw_accel['apple'] = True

        except Exception as e:
            print(f"Hardware acceleration detection failed: {e}")

        return hw_accel

    def convert_to_optimal_format(self, input_path: Path, job_id: str) -> Path:
        """
        Convert audio to optimal format for processing.
        Returns path to converted file.
        """
        try:
            # Create conversion directory
            convert_dir = config.TEMP_DIR / job_id / "conversion"
            convert_dir.mkdir(parents=True, exist_ok=True)

            # Analyze input file
            input_info = self.analyze_audio_file(input_path)
            print(f"Input analysis: {input_info}")

            # Determine optimal conversion
            target_format = self._determine_optimal_format(input_info)

            # Generate output path
            output_path = convert_dir / f"converted_{input_path.stem}.{target_format}"

            # Convert file
            success = self._convert_file(input_path, output_path, target_format, input_info)

            if success:
                print(f"Conversion successful: {output_path}")
                return output_path
            else:
                print("Conversion failed, returning original file")
                return input_path

        except Exception as e:
            print(f"Format conversion failed: {e}")
            return input_path

    def analyze_audio_file(self, file_path: Path) -> Dict:
        """Analyze audio file properties using FFprobe"""
        try:
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(file_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            probe_data = json.loads(result.stdout)

            # Extract audio stream info
            audio_streams = [s for s in probe_data['streams'] if s['codec_type'] == 'audio']

            if not audio_streams:
                raise ValueError("No audio stream found")

            stream = audio_streams[0]  # Use first audio stream
            format_info = probe_data['format']

            return {
                'codec': stream.get('codec_name', 'unknown'),
                'sample_rate': int(stream.get('sample_rate', 0)),
                'channels': int(stream.get('channels', 0)),
                'bit_rate': int(stream.get('bit_rate', 0)) if stream.get('bit_rate') else None,
                'duration': float(format_info.get('duration', 0)),
                'size': int(format_info.get('size', 0)),
                'format': format_info.get('format_name', 'unknown'),
                'bit_depth': self._extract_bit_depth(stream),
                'channel_layout': stream.get('channel_layout', 'unknown')
            }

        except Exception as e:
            print(f"Audio analysis failed: {e}")
            return {
                'codec': 'unknown',
                'sample_rate': 44100,
                'channels': 2,
                'duration': 0,
                'format': 'unknown'
            }

    def _extract_bit_depth(self, stream: Dict) -> int:
        """Extract bit depth from stream info"""
        try:
            sample_fmt = stream.get('sample_fmt', '')

            if 's16' in sample_fmt:
                return 16
            elif 's24' in sample_fmt:
                return 24
            elif 's32' in sample_fmt or 'f32' in sample_fmt:
                return 32
            elif 'f64' in sample_fmt:
                return 64
            else:
                return 16  # Default

        except Exception:
            return 16

    def _determine_optimal_format(self, input_info: Dict) -> str:
        """Determine optimal output format based on input characteristics"""

        # For processing, always use high-quality uncompressed format
        current_sample_rate = input_info.get('sample_rate', 44100)
        current_channels = input_info.get('channels', 2)
        current_format = input_info.get('format', '').lower()

        # If already in optimal format, no conversion needed
        if (current_sample_rate == 44100 and
            current_channels == 2 and
            'wav' in current_format):
            return 'wav'

        # For processing, use 32-bit float WAV
        return 'wav'

    def _convert_file(self,
                     input_path: Path,
                     output_path: Path,
                     target_format: str,
                     input_info: Dict) -> bool:
        """Convert file using FFmpeg with optimal settings"""
        try:
            config_key = target_format if target_format in self.format_configs else 'processing'
            format_config = self.format_configs[config_key]

            # Build FFmpeg command
            cmd = [self.ffmpeg_path, '-y', '-i', str(input_path)]

            # Add hardware acceleration if available
            if self.hw_accel['nvidia']:
                cmd.extend(['-hwaccel', 'cuda'])
            elif self.hw_accel['intel']:
                cmd.extend(['-hwaccel', 'qsv'])

            # Audio codec and quality settings
            cmd.extend(['-c:a', format_config['codec']])

            # Sample rate
            cmd.extend(['-ar', str(format_config['sample_rate'])])

            # Channels
            cmd.extend(['-ac', str(format_config['channels'])])

            # Format-specific settings
            if target_format == 'wav':
                # High-quality WAV for processing
                cmd.extend(['-sample_fmt', 's24'])
                cmd.extend(['-f', 'wav'])

            elif target_format == 'flac':
                cmd.extend(['-compression_level', str(format_config['compression_level'])])

            elif target_format == 'mp3':
                cmd.extend(['-b:a', format_config['bitrate']])
                cmd.extend(['-q:a', '0'])  # Highest quality

            elif target_format == 'aac':
                cmd.extend(['-b:a', format_config['bitrate']])
                cmd.extend(['-profile:a', 'aac_low'])

            # Audio filters for enhancement
            filters = []

            # Volume normalization
            filters.append('loudnorm=I=-16:TP=-1.5:LRA=11')

            # High-quality resampling if needed
            target_sr = format_config['sample_rate']
            current_sr = input_info.get('sample_rate', 44100)

            if current_sr != target_sr:
                filters.append(f'aresample={target_sr}:resampler=soxr:precision=28')

            # Apply filters
            if filters:
                cmd.extend(['-af', ','.join(filters)])

            # Output file
            cmd.append(str(output_path))

            print(f"Running FFmpeg: {' '.join(cmd)}")

            # Execute conversion
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            if result.returncode == 0:
                print("Conversion successful")
                return True
            else:
                print(f"FFmpeg error: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("Conversion timeout")
            return False
        except Exception as e:
            print(f"Conversion failed: {e}")
            return False

    async def download_from_url(self, url: str, format_preference: str = "wav") -> Path:
        """Download audio from URL using yt-dlp"""
        try:
            # Create download directory
            download_dir = config.TEMP_DIR / "downloads"
            download_dir.mkdir(parents=True, exist_ok=True)

            # Configure yt-dlp options
            opts = self.ytdl_opts.copy()
            opts['outtmpl'] = str(download_dir / '%(title)s.%(ext)s')

            # Run download in thread pool to avoid blocking
            with ThreadPoolExecutor(max_workers=1) as executor:
                loop = asyncio.get_event_loop()
                downloaded_path = await loop.run_in_executor(
                    executor, self._download_with_ytdlp, url, opts
                )

            if downloaded_path and downloaded_path.exists():
                # Convert to desired format if needed
                if format_preference != "wav":
                    converted_path = await self._convert_downloaded_file(
                        downloaded_path, format_preference
                    )
                    # Clean up original
                    downloaded_path.unlink()
                    return converted_path

                return downloaded_path
            else:
                raise Exception("Download failed or file not found")

        except Exception as e:
            print(f"URL download failed: {e}")
            raise

    def _download_with_ytdlp(self, url: str, opts: Dict) -> Optional[Path]:
        """Download using yt-dlp (blocking operation)"""
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                # Extract info first
                info = ydl.extract_info(url, download=False)

                # Sanitize filename
                title = info.get('title', 'audio')
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_title = safe_title[:50]  # Limit length

                # Update output template
                download_dir = Path(opts['outtmpl']).parent
                opts['outtmpl'] = str(download_dir / f"{safe_title}.%(ext)s")

                # Download
                ydl.download([url])

                # Find downloaded file
                possible_files = list(download_dir.glob(f"{safe_title}.*"))
                audio_files = [f for f in possible_files if f.suffix.lower() in ['.wav', '.mp3', '.m4a', '.webm']]

                if audio_files:
                    return audio_files[0]
                else:
                    print(f"No audio file found in {download_dir}")
                    return None

        except Exception as e:
            print(f"yt-dlp download failed: {e}")
            return None

    async def _convert_downloaded_file(self, input_path: Path, target_format: str) -> Path:
        """Convert downloaded file to target format"""
        try:
            output_path = input_path.with_suffix(f'.{target_format}')

            # Run conversion in thread pool
            with ThreadPoolExecutor(max_workers=1) as executor:
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(
                    executor, self._convert_file, input_path, output_path, target_format, {}
                )

            if success:
                return output_path
            else:
                return input_path

        except Exception as e:
            print(f"Downloaded file conversion failed: {e}")
            return input_path

    def batch_convert(self, input_files: List[Path], target_format: str, job_id: str) -> Dict[Path, Path]:
        """Convert multiple files in parallel"""
        try:
            results = {}

            with ThreadPoolExecutor(max_workers=4) as executor:
                # Submit all conversion tasks
                future_to_file = {
                    executor.submit(self.convert_to_optimal_format, file_path, f"{job_id}_{i}"): file_path
                    for i, file_path in enumerate(input_files)
                }

                # Collect results
                for future in future_to_file:
                    input_file = future_to_file[future]
                    try:
                        output_file = future.result(timeout=600)
                        results[input_file] = output_file
                    except Exception as e:
                        print(f"Batch conversion failed for {input_file}: {e}")
                        results[input_file] = input_file  # Return original on failure

            return results

        except Exception as e:
            print(f"Batch conversion failed: {e}")
            return {f: f for f in input_files}  # Return originals on failure

    def optimize_for_separation(self, input_path: Path, job_id: str) -> Path:
        """Optimize audio specifically for separation algorithms"""
        try:
            # Create optimization directory
            opt_dir = config.TEMP_DIR / job_id / "optimization"
            opt_dir.mkdir(parents=True, exist_ok=True)

            output_path = opt_dir / f"optimized_{input_path.stem}.wav"

            # Build optimization command
            cmd = [
                self.ffmpeg_path, '-y', '-i', str(input_path),

                # Audio codec - 32-bit float for best quality
                '-c:a', 'pcm_f32le',

                # Standard sample rate for separation models
                '-ar', '44100',

                # Stereo output
                '-ac', '2',

                # Audio filters for separation optimization
                '-af', ','.join([
                    'loudnorm=I=-16:TP=-1.5:LRA=11',  # Loudness normalization
                    'highpass=f=20',  # Remove sub-bass rumble
                    'lowpass=f=20000',  # Remove ultra-high frequencies
                    'aresample=44100:resampler=soxr:precision=28'  # High-quality resampling
                ]),

                str(output_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                return output_path
            else:
                print(f"Optimization failed: {result.stderr}")
                return input_path

        except Exception as e:
            print(f"Separation optimization failed: {e}")
            return input_path

    def extract_metadata(self, file_path: Path) -> Dict:
        """Extract comprehensive metadata from audio file"""
        try:
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(file_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            probe_data = json.loads(result.stdout)

            metadata = {}

            # Format metadata
            if 'format' in probe_data:
                format_tags = probe_data['format'].get('tags', {})
                metadata.update({
                    'title': format_tags.get('title', ''),
                    'artist': format_tags.get('artist', ''),
                    'album': format_tags.get('album', ''),
                    'genre': format_tags.get('genre', ''),
                    'year': format_tags.get('date', ''),
                    'duration': float(probe_data['format'].get('duration', 0)),
                    'bit_rate': int(probe_data['format'].get('bit_rate', 0)) if probe_data['format'].get('bit_rate') else 0
                })

            # Stream metadata
            audio_streams = [s for s in probe_data['streams'] if s['codec_type'] == 'audio']
            if audio_streams:
                stream = audio_streams[0]
                metadata.update({
                    'codec': stream.get('codec_name', ''),
                    'sample_rate': int(stream.get('sample_rate', 0)),
                    'channels': int(stream.get('channels', 0)),
                    'channel_layout': stream.get('channel_layout', ''),
                    'bit_depth': self._extract_bit_depth(stream)
                })

            return metadata

        except Exception as e:
            print(f"Metadata extraction failed: {e}")
            return {}

# Global converter instance
format_converter = FormatConverter()
