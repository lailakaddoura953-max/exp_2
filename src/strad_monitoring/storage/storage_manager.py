"""
Storage Manager for Strad Carrier Monitoring System

Manages temporary and permanent snapshot storage with atomic write operations,
JPEG compression, and file verification.

Requirements: 5.1, 10.1, 10.2, 10.3, 10.4
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Manages snapshot storage for the monitoring system.
    
    Responsibilities:
    - Store snapshots in temporary memory storage during processing
    - Persist critical snapshots to permanent storage with date organization
    - Compress snapshots using JPEG quality 85
    - Verify saved files are readable before deletion
    - Use atomic write pattern (write to .tmp, verify, rename)
    """
    
    def __init__(
        self,
        temp_storage_path: str,
        permanent_storage_path: str,
        retention_days: int = 30
    ):
        """
        Initialize storage manager with paths.
        
        Args:
            temp_storage_path: Directory for temporary snapshot storage
            permanent_storage_path: Directory for permanent critical snapshot storage
            retention_days: Number of days to retain permanent snapshots (default: 30)
        """
        self.temp_storage_path = Path(temp_storage_path)
        self.permanent_storage_path = Path(permanent_storage_path)
        self.retention_days = retention_days
        
        # Create directories if they don't exist
        self.temp_storage_path.mkdir(parents=True, exist_ok=True)
        self.permanent_storage_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"StorageManager initialized: temp={self.temp_storage_path}, permanent={self.permanent_storage_path}")
    
    def store_temporary_snapshot(
        self,
        strad_id: str,
        snapshot: np.ndarray
    ) -> str:
        """
        Store snapshot in temporary storage.
        
        File naming format: {strad_id}_{uuid}.jpg
        
        Args:
            strad_id: Strad identifier in SCXXX format
            snapshot: RGB numpy array (H, W, 3)
        
        Returns:
            Temporary file path as string
        
        Requirements: 5.1
        """
        # Generate unique filename with strad_id and uuid
        unique_id = str(uuid.uuid4())
        filename = f"{strad_id}_{unique_id}.jpg"
        temp_path = self.temp_storage_path / filename
        
        try:
            # Convert numpy array to PIL Image
            if snapshot.dtype != np.uint8:
                # Normalize to 0-255 if needed
                snapshot = (snapshot * 255).astype(np.uint8)
            
            image = Image.fromarray(snapshot, mode='RGB')
            
            # Save with JPEG quality 85
            image.save(temp_path, 'JPEG', quality=85)
            
            logger.debug(f"Temporary snapshot stored: {temp_path}")
            return str(temp_path)
            
        except Exception as e:
            logger.error(f"Failed to store temporary snapshot for {strad_id}: {e}")
            raise
    
    def persist_critical_snapshot(
        self,
        strad_id: str,
        snapshot: np.ndarray,
        timestamp: datetime
    ) -> str:
        """
        Save critical snapshot to permanent storage with atomic write pattern.
        
        Directory structure: YYYY-MM-DD/{CHE_Number}_{timestamp}.jpg
        Uses atomic write: save to .tmp file, verify, then rename
        
        Args:
            strad_id: Strad identifier (CHE_Number) in SCXXX format
            snapshot: RGB numpy array (H, W, 3)
            timestamp: Timestamp for the snapshot
        
        Returns:
            Permanent file path as string
        
        Requirements: 10.1, 10.2, 10.3, 10.4
        """
        # Create date directory (YYYY-MM-DD format)
        date_str = timestamp.strftime("%Y-%m-%d")
        date_dir = self.permanent_storage_path / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename: {CHE_Number}_{timestamp}.jpg
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"{strad_id}_{timestamp_str}.jpg"
        final_path = date_dir / filename
        tmp_path = date_dir / f"{filename}.tmp"
        
        try:
            # Convert numpy array to PIL Image
            if snapshot.dtype != np.uint8:
                # Normalize to 0-255 if needed
                snapshot = (snapshot * 255).astype(np.uint8)
            
            image = Image.fromarray(snapshot, mode='RGB')
            
            # ATOMIC WRITE PATTERN: Step 1 - Write to .tmp file
            image.save(tmp_path, 'JPEG', quality=85)
            logger.debug(f"Temporary file written: {tmp_path}")
            
            # ATOMIC WRITE PATTERN: Step 2 - Verify file is readable
            try:
                with Image.open(tmp_path) as verify_img:
                    verify_img.verify()
                # Re-open for full validation (verify() closes the file)
                with Image.open(tmp_path) as verify_img:
                    _ = verify_img.size  # Ensure we can read basic properties
                logger.debug(f"File verification successful: {tmp_path}")
            except Exception as verify_error:
                logger.error(f"File verification failed: {verify_error}")
                # Clean up failed temp file
                if tmp_path.exists():
                    tmp_path.unlink()
                raise
            
            # ATOMIC WRITE PATTERN: Step 3 - Rename to final path
            tmp_path.rename(final_path)
            logger.info(f"Critical snapshot persisted: {final_path}")
            
            return str(final_path)
            
        except Exception as e:
            logger.error(f"Failed to persist critical snapshot for {strad_id}: {e}")
            # Clean up temp file if it exists
            if tmp_path.exists():
                tmp_path.unlink()
            raise
    
    def clear_temporary_snapshot(self, temp_path: str) -> None:
        """
        Remove snapshot from temporary storage.
        
        Args:
            temp_path: Path to temporary snapshot file
        
        Requirements: 5.2
        """
        try:
            path = Path(temp_path)
            if path.exists() and path.is_file():
                path.unlink()
                logger.debug(f"Temporary snapshot removed: {temp_path}")
            else:
                logger.warning(f"Temporary snapshot not found or not a file: {temp_path}")
        except Exception as e:
            logger.error(f"Failed to clear temporary snapshot {temp_path}: {e}")
            raise
    
    def clear_all_temporary(self) -> None:
        """
        Clear all temporary snapshots (end of cycle).
        
        Requirements: 5.4
        """
        try:
            count = 0
            for temp_file in self.temp_storage_path.glob("*.jpg"):
                if temp_file.is_file():
                    temp_file.unlink()
                    count += 1
            
            logger.info(f"Cleared {count} temporary snapshot(s)")
        except Exception as e:
            logger.error(f"Failed to clear all temporary snapshots: {e}")
            raise
    
    def cleanup_old_snapshots(self) -> int:
        """
        Remove snapshots older than retention period.
        
        Returns:
            Count of removed snapshots
        
        Requirements: 10.6
        """
        try:
            removed_count = 0
            current_date = datetime.now()
            
            # Iterate through date directories in permanent storage
            for date_dir in self.permanent_storage_path.iterdir():
                if not date_dir.is_dir():
                    continue
                
                # Parse directory name as date (YYYY-MM-DD)
                try:
                    dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
                    age_days = (current_date - dir_date).days
                    
                    if age_days > self.retention_days:
                        # Remove all files in the directory
                        for snapshot_file in date_dir.glob("*.jpg"):
                            if snapshot_file.is_file():
                                snapshot_file.unlink()
                                removed_count += 1
                        
                        # Remove empty directory
                        if not any(date_dir.iterdir()):
                            date_dir.rmdir()
                            logger.debug(f"Removed empty directory: {date_dir}")
                        
                except ValueError:
                    # Directory name doesn't match YYYY-MM-DD format, skip it
                    logger.warning(f"Skipping non-date directory: {date_dir.name}")
                    continue
            
            logger.info(f"Cleanup removed {removed_count} old snapshot(s)")
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old snapshots: {e}")
            raise
    
    def check_available_space(self) -> float:
        """
        Check available disk space in GB.
        
        Returns:
            Available space in gigabytes
        
        Requirements: 5.5
        """
        try:
            import shutil
            stat = shutil.disk_usage(self.permanent_storage_path)
            available_gb = stat.free / (1024 ** 3)
            logger.debug(f"Available disk space: {available_gb:.2f} GB")
            return available_gb
        except Exception as e:
            logger.error(f"Failed to check available space: {e}")
            raise
