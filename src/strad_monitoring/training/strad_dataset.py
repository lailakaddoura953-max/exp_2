"""
Strad Misalignment Dataset Loader

Loads training data from the SCFootage folder structure:
- SCFootage/
  - misaligned - critical/
    - strad_id/
      - image.png or video.mp4
  - misaligned - moderate/
    - strad_id/
      - image.png or video.mp4
  - misaligned - none/
    - strad_id/
      - image.png or video.mp4
"""

import os
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import torch
from torch.utils.data import Dataset
from PIL import Image
import numpy as np
import cv2


class StradMisalignmentDataset(Dataset):
    """
    Dataset for strad misalignment classification.
    
    Supports both images (.png, .jpg, .jpeg) and videos (.mp4).
    For videos, extracts frames at regular intervals.
    """
    
    # Class name to label mapping
    CLASS_TO_LABEL = {
        'misaligned - none': 0,
        'misaligned - moderate': 1,
        'misaligned - critical': 2
    }
    
    LABEL_TO_CLASS = {
        0: 'none',
        1: 'moderate',
        2: 'critical'
    }
    
    def __init__(
        self,
        root_dir: str,
        transform=None,
        frames_per_video: int = 5,
        image_extensions: List[str] = ['.png', '.jpg', '.jpeg'],
        video_extensions: List[str] = ['.mp4', '.avi', '.mov']
    ):
        """
        Initialize dataset.
        
        Args:
            root_dir: Path to SCFootage directory
            transform: Optional transform to apply to images
            frames_per_video: Number of frames to extract per video
            image_extensions: List of valid image file extensions
            video_extensions: List of valid video file extensions
        """
        self.root_dir = Path(root_dir)
        self.transform = transform
        self.frames_per_video = frames_per_video
        self.image_extensions = image_extensions
        self.video_extensions = video_extensions
        
        # Load all samples
        self.samples: List[Tuple[Path, int, str]] = []  # (file_path, label, strad_id)
        self._load_samples()
        
        print(f"Loaded {len(self.samples)} samples from {root_dir}")
        self._print_class_distribution()
    
    def _load_samples(self):
        """Scan directory structure and load all samples."""
        for class_name in self.CLASS_TO_LABEL.keys():
            class_dir = self.root_dir / class_name
            
            if not class_dir.exists():
                print(f"Warning: Class directory not found: {class_dir}")
                continue
            
            label = self.CLASS_TO_LABEL[class_name]
            
            # Scan all strad_id subdirectories
            for strad_dir in class_dir.iterdir():
                if not strad_dir.is_dir():
                    continue
                
                strad_id = strad_dir.name
                
                # Scan for image and video files
                for file_path in strad_dir.iterdir():
                    if file_path.suffix.lower() in self.image_extensions:
                        self.samples.append((file_path, label, strad_id))
                    elif file_path.suffix.lower() in self.video_extensions:
                        # For videos, add multiple samples (one per extracted frame)
                        for frame_idx in range(self.frames_per_video):
                            self.samples.append((file_path, label, strad_id, frame_idx))
    
    def _print_class_distribution(self):
        """Print dataset statistics."""
        class_counts = {label: 0 for label in self.CLASS_TO_LABEL.values()}
        
        for sample in self.samples:
            label = sample[1]
            class_counts[label] += 1
        
        print("\nDataset class distribution:")
        for label, count in class_counts.items():
            class_name = self.LABEL_TO_CLASS[label]
            percentage = (count / len(self.samples)) * 100
            print(f"  {class_name:12s}: {count:4d} samples ({percentage:.1f}%)")
    
    def _load_image(self, path: Path) -> Image.Image:
        """Load image from file."""
        return Image.open(path).convert('RGB')
    
    def _load_video_frame(self, path: Path, frame_idx: int) -> Image.Image:
        """Extract specific frame from video."""
        cap = cv2.VideoCapture(str(path))
        
        # Get video properties
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Calculate frame position
        if total_frames <= self.frames_per_video:
            # Use actual frame index if video is short
            frame_position = min(frame_idx, total_frames - 1)
        else:
            # Sample frames evenly throughout the video
            frame_position = int((frame_idx / self.frames_per_video) * total_frames)
        
        # Set position and read frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise RuntimeError(f"Failed to read frame {frame_position} from {path}")
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return Image.fromarray(frame_rgb)
    
    def __len__(self) -> int:
        """Return number of samples."""
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int, Dict]:
        """
        Get sample by index.
        
        Returns:
            image: Transformed image tensor
            label: Class label (0=none, 1=moderate, 2=critical)
            metadata: Dict with strad_id and file_path
        """
        sample = self.samples[idx]
        
        if len(sample) == 3:
            # Image sample
            file_path, label, strad_id = sample
            image = self._load_image(file_path)
        else:
            # Video sample
            file_path, label, strad_id, frame_idx = sample
            image = self._load_video_frame(file_path, frame_idx)
        
        # Apply transforms
        if self.transform:
            image = self.transform(image)
        
        metadata = {
            'strad_id': strad_id,
            'file_path': str(file_path),
            'label_name': self.LABEL_TO_CLASS[label]
        }
        
        return image, label, metadata
    
    def get_class_weights(self) -> torch.Tensor:
        """
        Calculate class weights for handling imbalanced data.
        
        Returns:
            Tensor of weights (inverse frequency)
        """
        class_counts = torch.zeros(len(self.CLASS_TO_LABEL))
        
        for sample in self.samples:
            label = sample[1]
            class_counts[label] += 1
        
        # Calculate inverse frequency weights
        total = len(self.samples)
        weights = total / (len(self.CLASS_TO_LABEL) * class_counts)
        
        return weights


def create_strad_dataloaders(
    data_dir: str,
    batch_size: int = 16,
    train_split: float = 0.8,
    val_split: float = 0.1,
    num_workers: int = 4,
    seed: int = 42
) -> Tuple[torch.utils.data.DataLoader, torch.utils.data.DataLoader, torch.utils.data.DataLoader]:
    """
    Create train, validation, and test dataloaders.
    
    Args:
        data_dir: Path to SCFootage directory
        batch_size: Batch size for training
        train_split: Fraction of data for training
        val_split: Fraction of data for validation
        num_workers: Number of worker threads
        seed: Random seed for reproducibility
    
    Returns:
        train_loader, val_loader, test_loader
    """
    from torchvision import transforms
    
    # Define transforms
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(10),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    # Create full dataset
    full_dataset = StradMisalignmentDataset(data_dir, transform=None)
    
    # Split dataset
    dataset_size = len(full_dataset)
    indices = list(range(dataset_size))
    
    # Shuffle with fixed seed
    np.random.seed(seed)
    np.random.shuffle(indices)
    
    train_size = int(train_split * dataset_size)
    val_size = int(val_split * dataset_size)
    
    train_indices = indices[:train_size]
    val_indices = indices[train_size:train_size + val_size]
    test_indices = indices[train_size + val_size:]
    
    # Create subset datasets with appropriate transforms
    train_dataset = torch.utils.data.Subset(
        StradMisalignmentDataset(data_dir, transform=train_transform),
        train_indices
    )
    val_dataset = torch.utils.data.Subset(
        StradMisalignmentDataset(data_dir, transform=val_transform),
        val_indices
    )
    test_dataset = torch.utils.data.Subset(
        StradMisalignmentDataset(data_dir, transform=val_transform),
        test_indices
    )
    
    # Create dataloaders
    train_loader = torch.utils.data.DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True
    )
    
    val_loader = torch.utils.data.DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )
    
    test_loader = torch.utils.data.DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )
    
    print(f"\nDataset splits:")
    print(f"  Train: {len(train_indices)} samples")
    print(f"  Val:   {len(val_indices)} samples")
    print(f"  Test:  {len(test_indices)} samples")
    
    return train_loader, val_loader, test_loader
