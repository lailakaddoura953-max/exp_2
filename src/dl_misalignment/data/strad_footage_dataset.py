"""
Strad Footage Dataset Loader

This module provides a PyTorch Dataset class for loading strad footage
organized in a hierarchical folder structure with class labels.

Expected folder structure:
    SCFootage/
        misaligned - critical/
            STRAD_001/
                image1.png
                video1.mp4
            STRAD_002/
                ...
        misaligned - moderate/
            STRAD_003/
                ...
        misaligned - none/
            STRAD_004/
                ...

The dataset automatically:
- Maps folder names to class labels (critical=2, moderate=1, none=0)
- Extracts frames from MP4 videos
- Loads PNG images directly
- Applies optional data augmentation
"""

import os
from pathlib import Path
from typing import Tuple, Optional, List, Callable
import cv2
import numpy as np
from PIL import Image
import torch
from torch.utils.data import Dataset


class StradFootageDataset(Dataset):
    """
    PyTorch Dataset for strad footage with class-based folder organization.
    
    Supports:
    - Three severity classes: none (0), moderate (1), critical (2)
    - PNG image files
    - MP4 video files (extracts frames)
    - Optional data augmentation
    """
    
    # Map folder names to numeric labels
    CLASS_MAPPING = {
        'misaligned - none': 0,
        'misaligned - moderate': 1,
        'misaligned - critical': 2,
        'none': 0,
        'moderate': 1,
        'critical': 2
    }
    
    # Reverse mapping for displaying class names
    LABEL_TO_CLASS = {
        0: 'none',
        1: 'moderate',
        2: 'critical'
    }
    
    def __init__(
        self,
        root_dir: str,
        transform: Optional[Callable] = None,
        video_frame_count: int = 10,
        image_size: Tuple[int, int] = (640, 640)
    ):
        """
        Initialize StradFootageDataset.
        
        Args:
            root_dir: Path to SCFootage directory
            transform: Optional torchvision transforms to apply
            video_frame_count: Number of frames to extract per video
            image_size: Target size for images (width, height)
        """
        self.root_dir = Path(root_dir)
        self.transform = transform
        self.video_frame_count = video_frame_count
        self.image_size = image_size
        
        # Build dataset index
        self.samples = []
        self._build_dataset_index()
        
        if len(self.samples) == 0:
            raise ValueError(f"No valid samples found in {root_dir}")
        
        # Calculate class distribution
        self.class_counts = {0: 0, 1: 0, 2: 0}
        for _, label in self.samples:
            self.class_counts[label] += 1
    
    def _build_dataset_index(self):
        """
        Scan folder structure and build index of all images/videos.
        
        Populates self.samples with (file_path, label) tuples.
        """
        print(f"Building dataset index from: {self.root_dir}")
        
        # Check if root directory exists
        if not self.root_dir.exists():
            raise FileNotFoundError(f"Dataset root not found: {self.root_dir}")
        
        # Iterate through class folders
        for class_folder in self.root_dir.iterdir():
            if not class_folder.is_dir():
                continue
            
            # Get class label from folder name
            class_name = class_folder.name.lower()
            if class_name not in self.CLASS_MAPPING:
                print(f"Warning: Unknown class folder '{class_folder.name}' - skipping")
                continue
            
            label = self.CLASS_MAPPING[class_name]
            print(f"  Processing class: {class_folder.name} (label={label})")
            
            # Iterate through strad ID folders
            strad_count = 0
            file_count = 0
            
            for strad_folder in class_folder.iterdir():
                if not strad_folder.is_dir():
                    continue
                
                strad_count += 1
                
                # Find all images and videos in strad folder
                for file_path in strad_folder.iterdir():
                    if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                        self.samples.append((str(file_path), label))
                        file_count += 1
                    elif file_path.suffix.lower() in ['.mp4', '.avi', '.mov']:
                        # For videos, each video becomes one sample
                        # Frames will be extracted in __getitem__
                        self.samples.append((str(file_path), label))
                        file_count += 1
            
            print(f"    Found {strad_count} strad folders, {file_count} files")
        
        print(f"\nTotal samples: {len(self.samples)}")
        print(f"Class distribution:")
        for label_val, class_name in self.LABEL_TO_CLASS.items():
            count = sum(1 for _, lbl in self.samples if lbl == label_val)
            print(f"  {class_name}: {count} samples")
    
    def _extract_video_frame(self, video_path: str, frame_index: int = -1) -> np.ndarray:
        """
        Extract a single frame from video.
        
        Args:
            video_path: Path to video file
            frame_index: Frame to extract (-1 for middle frame)
            
        Returns:
            Frame as numpy array (H, W, C)
        """
        cap = cv2.VideoCapture(video_path)
        
        try:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if frame_index < 0:
                # Extract middle frame by default
                frame_index = total_frames // 2
            
            # Set frame position
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            
            # Read frame
            ret, frame = cap.read()
            
            if not ret:
                raise ValueError(f"Failed to read frame {frame_index} from {video_path}")
            
            # Convert BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            return frame
        
        finally:
            cap.release()
    
    def _load_image(self, image_path: str) -> np.ndarray:
        """
        Load image from file.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Image as numpy array (H, W, C)
        """
        image = Image.open(image_path).convert('RGB')
        return np.array(image)
    
    def __len__(self) -> int:
        """Return number of samples in dataset."""
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        """
        Get a single sample from dataset.
        
        Args:
            idx: Sample index
            
        Returns:
            (image_tensor, label) tuple
        """
        file_path, label = self.samples[idx]
        
        # Load image or extract video frame
        if file_path.endswith('.mp4') or file_path.endswith('.avi') or file_path.endswith('.mov'):
            image = self._extract_video_frame(file_path)
        else:
            image = self._load_image(file_path)
        
        # Resize to target size
        image = cv2.resize(image, self.image_size)
        
        # Convert to PIL Image for transforms
        image = Image.fromarray(image)
        
        # Apply transforms if provided
        if self.transform:
            image = self.transform(image)
        else:
            # Default: convert to tensor and normalize
            image = torch.from_numpy(np.array(image)).permute(2, 0, 1).float() / 255.0
        
        return image, label
    
    def get_class_weights(self) -> torch.Tensor:
        """
        Calculate class weights for imbalanced dataset.
        
        Returns:
            Tensor of weights for each class (inverse frequency)
        """
        total = len(self.samples)
        weights = []
        
        for class_idx in range(3):
            count = self.class_counts[class_idx]
            if count > 0:
                weight = total / (3.0 * count)
            else:
                weight = 0.0
            weights.append(weight)
        
        return torch.tensor(weights, dtype=torch.float32)
    
    def get_sample_info(self, idx: int) -> dict:
        """
        Get metadata about a sample without loading the image.
        
        Args:
            idx: Sample index
            
        Returns:
            Dictionary with file_path, label, class_name
        """
        file_path, label = self.samples[idx]
        return {
            'file_path': file_path,
            'label': label,
            'class_name': self.LABEL_TO_CLASS[label],
            'is_video': file_path.endswith(('.mp4', '.avi', '.mov'))
        }


def create_strad_dataloaders(
    root_dir: str,
    batch_size: int = 16,
    train_split: float = 0.8,
    num_workers: int = 4,
    transform_train: Optional[Callable] = None,
    transform_val: Optional[Callable] = None,
    image_size: Tuple[int, int] = (640, 640),
    seed: int = 42
):
    """
    Create train and validation dataloaders from strad footage.
    
    Args:
        root_dir: Path to SCFootage directory
        batch_size: Batch size for training
        train_split: Fraction of data for training (rest for validation)
        num_workers: Number of workers for data loading
        transform_train: Transforms for training set
        transform_val: Transforms for validation set
        image_size: Target image size
        seed: Random seed for reproducibility
        
    Returns:
        (train_loader, val_loader, dataset_info) tuple
    """
    from torch.utils.data import DataLoader, random_split
    
    # Create full dataset
    full_dataset = StradFootageDataset(
        root_dir=root_dir,
        transform=None,  # We'll apply transforms after split
        image_size=image_size
    )
    
    # Split into train and validation
    train_size = int(train_split * len(full_dataset))
    val_size = len(full_dataset) - train_size
    
    torch.manual_seed(seed)
    train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size])
    
    # Apply transforms to subsets
    if transform_train:
        train_dataset.dataset.transform = transform_train
    if transform_val:
        val_dataset.dataset.transform = transform_val
    
    # Create dataloaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )
    
    # Dataset info
    dataset_info = {
        'total_samples': len(full_dataset),
        'train_samples': train_size,
        'val_samples': val_size,
        'class_counts': full_dataset.class_counts,
        'class_weights': full_dataset.get_class_weights(),
        'num_classes': 3
    }
    
    return train_loader, val_loader, dataset_info
