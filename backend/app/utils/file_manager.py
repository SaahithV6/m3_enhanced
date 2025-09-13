"""
File Manager for M3 Enhanced
Comprehensive file system operations, validation, and management
"""

import os
import shutil
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
import logging
from datetime import datetime, timedelta
import tempfile
import aiofiles
import aiofiles.os
from dataclasses import dataclass
import magic  # python-magic for file type detection
import uuid

from ..core.config import config

logger = logging.getLogger(__name__)

@dataclass
class FileInfo:
    """Container for file information"""
    path: Path
    size: int
    created: datetime
    modified: datetime
    mime_type: str
    file_hash: str
    is_valid: bool

@dataclass
class StorageStats:
    """Storage usage statistics"""
    total_files: int
    total_size: int
    uploads_size: int
    results_size: int
    temp_size: int
    available_space: int

class FileManager:
    """Comprehensive file system management for M3 Enhanced"""

    # Supported audio formats
    SUPPORTED_AUDIO_FORMATS = {
        '.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg', '.wma', '.aiff', '.au'
    }

    # Supported video formats (for audio extraction)
    SUPPORTED_VIDEO_FORMATS = {
        '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'
    }

    # Maximum file sizes
    MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500MB
    MAX_TEMP_SIZE = 2 * 1024 * 1024 * 1024  # 2GB total temp storage

    def __init__(self):
        self.ensure_directories()

        # Initialize magic for file type detection
        try:
            self.magic = magic.Magic(mime=True)
        except Exception as e:
            logger.warning(f"Failed to initialize python-magic: {str(e)}")
            self.magic = None

    def ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            config.UPLOADS_DIR,
            config.RESULTS_DIR,
            config.TEMP_DIR,
            config.MODELS_DIR,
            config.LOGS_DIR
        ]

        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Ensured directory exists: {directory}")
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {str(e)}")
                raise

    def generate_unique_filename(self, original_filename: str) -> str:
        """
        Generate unique filename with timestamp and UUID

        Args:
            original_filename: Original file name

        Returns:
            Unique filename string
        """
        try:
            original_path = Path(original_filename)
            name_part = original_path.stem
            ext_part = original_path.suffix.lower()

            # Sanitize filename
            safe_name = self._sanitize_filename(name_part)

            # Generate unique identifier
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]

            unique_filename = f"{safe_name}_{timestamp}_{unique_id}{ext_part}"

            logger.debug(f"Generated unique filename: {unique_filename}")
            return unique_filename

        except Exception as e:
            logger.error(f"Failed to generate unique filename: {str(e)}")
            # Fallback to UUID-based name
            return f"file_{uuid.uuid4().hex[:12]}.tmp"

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe filesystem operations"""
        # Remove or replace unsafe characters
        unsafe_chars = '<>:"/\\|?*'
        safe_name = filename

        for char in unsafe_chars:
            safe_name = safe_name.replace(char, '_')

        # Remove extra spaces and dots
        safe_name = '_'.join(safe_name.split())
        safe_name = safe_name.strip('.')

        # Ensure reasonable length
        if len(safe_name) > 100:
            safe_name = safe_name[:100]

        # Ensure not empty
        if not safe_name:
            safe_name = "unnamed"

        return safe_name

    def validate_audio_file(self, file_path: Union[str, Path]) -> bool:
        """
        Validate audio file format and integrity

        Args:
            file_path: Path to file to validate

        Returns:
            True if valid audio file
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                logger.warning(f"File does not exist: {file_path}")
                return False

            # Check file size
            file_size = file_path.stat().st_size
            if file_size == 0:
                logger.warning(f"File is empty: {file_path}")
                return False

            if file_size > self.MAX_UPLOAD_SIZE:
                logger.warning(f"File too large: {file_path} ({file_size} bytes)")
                return False

            # Check file extension
            ext = file_path.suffix.lower()
            if ext not in self.SUPPORTED_AUDIO_FORMATS:
                logger.warning(f"Unsupported audio format: {ext}")
                return False

            # Check MIME type if magic is available
            if self.magic:
                try:
                    mime_type = self.magic.from_file(str(file_path))
                    if not mime_type.startswith('audio/'):
                        logger.warning(f"Invalid MIME type: {mime_type}")
                        return False
                except Exception as e:
                    logger.warning(f"Failed to check MIME type: {str(e)}")

            # Try to validate with librosa (basic audio integrity check)
            try:
                import librosa
                y, sr = librosa.load(str(file_path), duration=1.0)  # Load first second
                if len(y) == 0 or sr <= 0:
                    logger.warning(f"Invalid audio data: {file_path}")
                    return False
            except Exception as e:
                logger.warning(f"Audio validation failed: {str(e)}")
                return False

            logger.debug(f"Audio file validation passed: {file_path}")
            return True

        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            return False

    def get_file_info(self, file_path: Union[str, Path]) -> FileInfo:
        """Get comprehensive file information"""
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            stat_info = file_path.stat()

            # Get MIME type
            mime_type = "application/octet-stream"  # Default
            if self.magic:
                try:
                    mime_type = self.magic.from_file(str(file_path))
                except Exception:
                    pass

            if not mime_type:
                mime_type, _ = mimetypes.guess_type(str(file_path))
                mime_type = mime_type or "application/octet-stream"

            # Calculate file hash
            file_hash = self._calculate_file_hash(file_path)

            # Validate if it's an audio file
            is_valid = True
            if file_path.suffix.lower() in self.SUPPORTED_AUDIO_FORMATS:
                is_valid = self.validate_audio_file(file_path)

            return FileInfo(
                path=file_path,
                size=stat_info.st_size,
                created=datetime.fromtimestamp(stat_info.st_ctime),
                modified=datetime.fromtimestamp(stat_info.st_mtime),
                mime_type=mime_type,
                file_hash=file_hash,
                is_valid=is_valid
            )

        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {str(e)}")
            raise

    def _calculate_file_hash(self, file_path: Path, algorithm: str = "sha256") -> str:
        """Calculate file hash for integrity checking"""
        try:
            hash_obj = hashlib.new(algorithm)

            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_obj.update(chunk)

            return hash_obj.hexdigest()

        except Exception as e:
            logger.warning(f"Failed to calculate hash for {file_path}: {str(e)}")
            return ""

    async def copy_file_async(
        self,
        source: Union[str, Path],
        destination: Union[str, Path],
        overwrite: bool = False
    ) -> Path:
        """Asynchronously copy file"""
        try:
            source = Path(source)
            destination = Path(destination)

            if not source.exists():
                raise FileNotFoundError(f"Source file not found: {source}")

            destination.parent.mkdir(parents=True, exist_ok=True)

            if destination.exists() and not overwrite:
                raise FileExistsError(f"Destination exists: {destination}")

            # Use async file operations for large files
            async with aiofiles.open(source, 'rb') as src:
                async with aiofiles.open(destination, 'wb') as dst:
                    while True:
                        chunk = await src.read(64 * 1024)  # 64KB chunks
                        if not chunk:
                            break
                        await dst.write(chunk)

            logger.debug(f"Copied file: {source} -> {destination}")
            return destination

        except Exception as e:
            logger.error(f"Failed to copy file {source} -> {destination}: {str(e)}")
            raise

    def move_file(
        self,
        source: Union[str, Path],
        destination: Union[str, Path],
        overwrite: bool = False
    ) -> Path:
        """Move file to new location"""
        try:
            source = Path(source)
            destination = Path(destination)

            if not source.exists():
                raise FileNotFoundError(f"Source file not found: {source}")

            destination.parent.mkdir(parents=True, exist_ok=True)

            if destination.exists() and not overwrite:
                raise FileExistsError(f"Destination exists: {destination}")

            shutil.move(str(source), str(destination))

            logger.debug(f"Moved file: {source} -> {destination}")
            return destination

        except Exception as e:
            logger.error(f"Failed to move file {source} -> {destination}: {str(e)}")
            raise

    def delete_file(self, file_path: Union[str, Path], safe: bool = True) -> bool:
        """
        Delete file with optional safety checks

        Args:
            file_path: Path to file to delete
            safe: If True, perform safety checks

        Returns:
            True if file was deleted
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                logger.debug(f"File already deleted: {file_path}")
                return True

            # Safety checks
            if safe:
                # Don't delete files outside of managed directories
                managed_dirs = [
                    config.UPLOADS_DIR,
                    config.RESULTS_DIR,
                    config.TEMP_DIR
                ]

                is_managed = any(
                    file_path.is_relative_to(managed_dir)
                    for managed_dir in managed_dirs
                )

                if not is_managed:
                    logger.warning(f"Refusing to delete file outside managed directories: {file_path}")
                    return False

            file_path.unlink()
            logger.debug(f"Deleted file: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {str(e)}")
            return False

    def cleanup_old_files(self, days: int = 7) -> int:
        """
        Clean up old files from managed directories

        Args:
            days: Delete files older than this many days

        Returns:
            Number of files deleted
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0

            # Directories to clean
            cleanup_dirs = [
                config.UPLOADS_DIR,
                config.RESULTS_DIR,
                config.TEMP_DIR
            ]

            for directory in cleanup_dirs:
                if not directory.exists():
                    continue

                for file_path in directory.rglob('*'):
                    if file_path.is_file():
                        try:
                            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)

                            if file_time < cutoff_date:
                                file_path.unlink()
                                deleted_count += 1
                                logger.debug(f"Deleted old file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to delete old file {file_path}: {str(e)}")

            logger.info(f"Cleanup completed: deleted {deleted_count} files older than {days} days")
            return deleted_count

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            return 0

    def get_storage_stats(self) -> StorageStats:
        """Get storage usage statistics"""
        try:
            def get_dir_size(directory: Path) -> int:
                """Calculate total size of directory"""
                total = 0
                try:
                    for file_path in directory.rglob('*'):
                        if file_path.is_file():
                            total += file_path.stat().st_size
                except Exception as e:
                    logger.warning(f"Error calculating size for {directory}: {str(e)}")
                return total

            # Count files and sizes
            total_files = 0
            uploads_size = 0
            results_size = 0
            temp_size = 0

            if config.UPLOADS_DIR.exists():
                uploads_size = get_dir_size(config.UPLOADS_DIR)
                total_files += len(list(config.UPLOADS_DIR.rglob('*')))

            if config.RESULTS_DIR.exists():
                results_size = get_dir_size(config.RESULTS_DIR)
                total_files += len(list(config.RESULTS_DIR.rglob('*')))

            if config.TEMP_DIR.exists():
                temp_size = get_dir_size(config.TEMP_DIR)
                total_files += len(list(config.TEMP_DIR.rglob('*')))

            total_size = uploads_size + results_size + temp_size

            # Get available disk space
            available_space = shutil.disk_usage(config.UPLOADS_DIR.parent)[2]

            return StorageStats(
                total_files=total_files,
                total_size=total_size,
                uploads_size=uploads_size,
                results_size=results_size,
                temp_size=temp_size,
                available_space=available_space
            )

        except Exception as e:
            logger.error(f"Failed to get storage stats: {str(e)}")
            return StorageStats(0, 0, 0, 0, 0, 0)

    def create_temp_file(
        self,
        suffix: str = ".tmp",
        prefix: str = "m3_",
        content: Optional[bytes] = None
    ) -> Path:
        """Create temporary file in managed temp directory"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(
                suffix=suffix,
                prefix=prefix,
                dir=config.TEMP_DIR,
                delete=False
            ) as tmp_file:
                if content:
                    tmp_file.write(content)

                temp_path = Path(tmp_file.name)

            logger.debug(f"Created temp file: {temp_path}")
            return temp_path

        except Exception as e:
            logger.error(f"Failed to create temp file: {str(e)}")
            raise

    def is_safe_path(self, file_path: Union[str, Path]) -> bool:
        """Check if path is safe for operations (prevents directory traversal)"""
        try:
            file_path = Path(file_path).resolve()

            # Check if path is within managed directories
            managed_dirs = [
                config.UPLOADS_DIR.resolve(),
                config.RESULTS_DIR.resolve(),
                config.TEMP_DIR.resolve(),
                config.MODELS_DIR.resolve()
            ]

            return any(
                file_path.is_relative_to(managed_dir)
                for managed_dir in managed_dirs
            )

        except Exception as e:
            logger.warning(f"Path safety check failed for {file_path}: {str(e)}")
            return False

    def get_free_space(self) -> int:
        """Get available free space in bytes"""
        try:
            return shutil.disk_usage(config.UPLOADS_DIR.parent)[2]
        except Exception as e:
            logger.error(f"Failed to get free space: {str(e)}")
            return 0

    def check_space_available(self, required_bytes: int) -> bool:
        """Check if enough space is available for operation"""
        try:
            available = self.get_free_space()
            # Add 10% safety margin
            required_with_margin = int(required_bytes * 1.1)
            return available >= required_with_margin
        except Exception:
            return False
