"""
KITTI Dataset Loader for Camera Misalignment Detection

The KITTI Vision Benchmark Suite is a standard dataset for autonomous driving
research. It contains stereo camera imagery from real-world driving scenarios.

What is KITTI?
- Real-world driving data from Karlsruhe, Germany
- High-quality stereo camera images (left and right cameras)
- Various scenarios: urban, rural, highways
- Perfect for training optical flow and misalignment detection

This module:
1. Loads stereo image pairs from KITTI dataset
2. Splits data into 70% train, 15% validation, 15% test
3. Applies preprocessing (resize, normalize)
4. Generates synthetic misalignment labels (via augmentation)

For developers new to datasets:
- A "dataset" is a collection of examples for training
- Each example has input (image) and output (label)
- We split data so the model never sees test data during training
- This tests if the model can generalize to new, unseen data
"""

import logging
from pathlib import Path
from typing import Tuple, Optional, List, Dict
import numpy as np
from PIL import Image

# Try to import torch (might not be installed yet)
try:
    import torch
    from torch.utils.data import Dataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    Dataset = object  # Dummy base class

logger = logging.getLogger(__name__)


class KITTIDataset(Dataset):
    """
    PyTorch Dataset for KITTI stereo imagery.
    
    This class handles loading images from disk, preprocessing them,
    and providing them to the training pipeline in batches.
    
    PyTorch Dataset API requires:
    - __len__(): Return number of samples
    - __getitem__(idx): Return a single sample (image, label) at index idx
    
    Args:
        root_dir: Path to KITTI dataset root directory
        split: Which split to load ('train', 'val', or 'test')
        transform: Optional image transformations (augmentation)
        target_resolution: Target size for images (H, W), max 750×750
        use_left_camera: If True, use left camera images; if False, use right
    
    Example:
        >>> dataset = KITTIDataset(
        ...     root_dir="kitti_data/",
        ...     split='train',
        ...     target_resolution=(640, 640)
        ... )
        >>> print(f"Dataset size: {len(dataset)}")
        >>> image, label = dataset[0]  # Get first sample
        >>> print(f"Image shape: {image.shape}")  # [3, 640, 640]
    """
    
    def __init__(
        self,
        root_dir: str,
        split: str = 'train',
        transform: Optional[any] = None,
        target_resolution: Tuple[int, int] = (640, 640),
        use_left_camera: bool = True,
        normalization_mean: Tuple[float, float, float] = (0.485, 0.456, 0.406),
        normalization_std: Tuple[float, float, float] = (0.229, 0.224, 0.225)
    ):
        """Initialize KITTI dataset."""
        if not TORCH_AVAILABLE:
            raise ImportError(
                "PyTorch is required for dataset loading. "
                "Install it with: pip install torch torchvision"
            )
        
        self.root_dir = Path(root_dir)
        self.split = split
        self.transform = transform
        self.target_resolution = target_resolution
        self.use_left_camera = use_left_camera
        self.normalization_mean = torch.tensor(normalization_mean).view(3, 1, 1)
        self.normalization_std = torch.tensor(normalization_std).view(3, 1, 1)
        
        # Validate target resolution (max 750×750 from requirements)
        if target_resolution[0] > 750 or target_resolution[1] > 750:
            raise ValueError(
                f"Target resolution {target_resolution} exceeds maximum 750×750. "
                f"This constraint ensures the system runs on consumer GPUs."
            )
        
        # Load dataset file paths
        self.image_paths = self._load_image_paths()
        
        # Load or create split indices
        self.split_indices = self._load_split_indices()
        
        # Filter to only this split's indices
        if split in self.split_indices:
            split_idx = self.split_indices[split]
            self.image_paths = [self.image_paths[i] for i in split_idx]
        
        logger.info(f"Loaded {split} split: {len(self.image_paths)} samples")
    
    def _load_image_paths(self) -> List[Path]:
        """
        Discover all image files in the KITTI directory.
        
        KITTI directory structure:
        kitti_data/
        ├── 2011_09_26/
        │   ├── 2011_09_26_drive_0001_sync/
        │   │   ├── image_02/  (left camera)
        │   │   │   └── data/
        │   │   │       ├── 0000000000.png
        │   │   │       ├── 0000000001.png
        │   │   │       └── ...
        │   │   └── image_03/  (right camera)
        │   │       └── data/
        │   └── 2011_09_26_drive_0002_sync/
        │   └── ...
        └── ...
        
        Returns:
            List of Path objects pointing to image files
        """
        image_paths = []
        
        # Check if root directory exists
        if not self.root_dir.exists():
            raise FileNotFoundError(
                f"KITTI dataset not found at {self.root_dir}. "
                f"Please download KITTI dataset and extract it to this directory. "
                f"See INSTALLATION.md for download instructions."
            )
        
        # Look for images in the expected structure
        # KITTI uses image_02 for left camera, image_03 for right camera
        camera_dir = "image_02" if self.use_left_camera else "image_03"
        
        # Search for all image files
        # Pattern: */*/image_02/data/*.png or */*/image_03/data/*.png
        search_pattern = f"*/*/{camera_dir}/data/*.png"
        image_paths = sorted(self.root_dir.glob(search_pattern))
        
        if len(image_paths) == 0:
            logger.warning(
                f"No images found in {self.root_dir} with pattern {search_pattern}. "
                f"Please check KITTI dataset structure."
            )
        else:
            logger.info(f"Found {len(image_paths)} images in KITTI dataset")
        
        return image_paths
    
    def _load_split_indices(self) -> Dict[str, List[int]]:
        """
        Load or create train/val/test split indices.
        
        Split ratios (from requirements):
        - Training: 70% ± 2%
        - Validation: 15% ± 2%
        - Test: 15% ± 2%
        
        The split is deterministic (same random seed) so it's reproducible.
        We save the split indices to disk so they're consistent across runs.
        
        Returns:
            Dictionary with keys 'train', 'val', 'test' and lists of indices
        """
        split_file = self.root_dir / "split_indices.npz"
        
        # Try to load existing split
        if split_file.exists():
            logger.info(f"Loading existing split from {split_file}")
            data = np.load(split_file)
            splits = {
                'train': data['train'].tolist(),
                'val': data['val'].tolist(),
                'test': data['test'].tolist()
            }
            
            # Verify split ratios
            total = len(self.image_paths)
            train_pct = len(splits['train']) / total * 100
            val_pct = len(splits['val']) / total * 100
            test_pct = len(splits['test']) / total * 100
            
            logger.info(f"Split ratios: Train={train_pct:.1f}%, Val={val_pct:.1f}%, Test={test_pct:.1f}%")
            
            return splits
        
        # Create new split
        logger.info("Creating new train/val/test split...")
        
        n_samples = len(self.image_paths)
        indices = np.arange(n_samples)
        
        # Shuffle with fixed seed for reproducibility
        rng = np.random.RandomState(42)
        rng.shuffle(indices)
        
        # Calculate split sizes (70/15/15)
        train_size = int(0.70 * n_samples)
        val_size = int(0.15 * n_samples)
        # test_size is the remainder to ensure all samples are used
        
        splits = {
            'train': indices[:train_size].tolist(),
            'val': indices[train_size:train_size + val_size].tolist(),
            'test': indices[train_size + val_size:].tolist()
        }
        
        # Verify no overlap
        train_set = set(splits['train'])
        val_set = set(splits['val'])
        test_set = set(splits['test'])
        
        assert len(train_set & val_set) == 0, "Train and val sets overlap!"
        assert len(train_set & test_set) == 0, "Train and test sets overlap!"
        assert len(val_set & test_set) == 0, "Val and test sets overlap!"
        
        # Verify ratios are within tolerance (±2%)
        train_pct = len(splits['train']) / n_samples * 100
        val_pct = len(splits['val']) / n_samples * 100
        test_pct = len(splits['test']) / n_samples * 100
        
        assert 68 <= train_pct <= 72, f"Train split {train_pct:.1f}% outside 70%±2%"
        assert 13 <= val_pct <= 17, f"Val split {val_pct:.1f}% outside 15%±2%"
        assert 13 <= test_pct <= 17, f"Test split {test_pct:.1f}% outside 15%±2%"
        
        logger.info(f"Created split: Train={train_pct:.1f}%, Val={val_pct:.1f}%, Test={test_pct:.1f}%")
        logger.info(f"  Train: {len(splits['train'])} samples")
        logger.info(f"  Val: {len(splits['val'])} samples")
        logger.info(f"  Test: {len(splits['test'])} samples")
        
        # Save split for future use
        np.savez(
            split_file,
            train=np.array(splits['train']),
            val=np.array(splits['val']),
            test=np.array(splits['test'])
        )
        logger.info(f"Saved split indices to {split_file}")
        
        return splits
    
    def __len__(self) -> int:
        """Return the number of samples in this dataset split."""
        return len(self.image_paths)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, Dict]:
        """
        Get a single sample from the dataset.
        
        This function is called by PyTorch's DataLoader to fetch batches.
        
        Args:
            idx: Index of the sample to retrieve
        
        Returns:
            Tuple of (image, label_dict) where:
            - image: Preprocessed image tensor [3, H, W]
            - label_dict: Dictionary with labels and metadata
        
        Processing steps:
        1. Load image from disk (PNG file)
        2. Resize to target resolution
        3. Convert to tensor
        4. Normalize using ImageNet statistics
        5. Apply augmentation if specified
        6. Generate label (initially all "aligned", augmentation creates "misaligned")
        """
        # Load image
        img_path = self.image_paths[idx]
        image = Image.open(img_path).convert('RGB')
        
        original_size = image.size  # (W, H)
        
        # Resize to target resolution
        # PIL uses (W, H), we use (H, W), so reverse
        image = image.resize(
            (self.target_resolution[1], self.target_resolution[0]),
            Image.BILINEAR
        )
        
        # Convert to tensor [3, H, W] and normalize to [0, 1]
        image = torch.from_numpy(np.array(image)).permute(2, 0, 1).float() / 255.0
        
        # Apply normalization (ImageNet statistics)
        # This standardizes the input: (x - mean) / std
        # Makes training more stable and faster to converge
        image = (image - self.normalization_mean) / self.normalization_std
        
        # Create label dictionary
        # Initially, all images are "aligned" (no misalignment)
        # Augmentation will create "misaligned" examples
        label = {
            'is_misaligned': 0,  # 0 = aligned, 1 = misaligned
            'misalignment_probability': 0.0,  # Ground truth probability
            'pose': torch.zeros(6),  # [X, Y, Z, roll, pitch, yaw] - no offset initially
            'sample_id': str(img_path.stem),  # Filename for tracking
            'original_size': original_size,
            'augmentation_applied': {}  # Will be populated by augmentation
        }
        
        # Apply augmentation/transformation if specified
        if self.transform is not None:
            image, label = self.transform(image, label)
        
        return image, label
    
    def get_sample_images(self, indices: List[int]) -> List[torch.Tensor]:
        """
        Get multiple images without labels (for visualization).
        
        Args:
            indices: List of sample indices to retrieve
        
        Returns:
            List of image tensors
        
        Example:
            >>> images = dataset.get_sample_images([0, 1, 2, 3])
            >>> # Visualize with visualization.visualize_sample_grid(images)
        """
        images = []
        for idx in indices:
            image, _ = self.__getitem__(idx)
            images.append(image)
        return images
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Calculate dataset statistics.
        
        Returns:
            Dictionary with:
            - n_samples: Number of samples
            - image_resolution: Target resolution
            - original_resolutions: List of original image sizes
            - mean_original_size: Average original image size
        
        Useful for understanding the dataset and verifying preprocessing.
        """
        stats = {
            'n_samples': len(self),
            'image_resolution': self.target_resolution,
            'split': self.split,
            'camera': 'left' if self.use_left_camera else 'right'
        }
        
        # Sample a few images to get original sizes
        sample_indices = np.random.choice(
            len(self),
            size=min(100, len(self)),
            replace=False
        )
        
        original_sizes = []
        for idx in sample_indices:
            img_path = self.image_paths[idx]
            with Image.open(img_path) as img:
                original_sizes.append(img.size)  # (W, H)
        
        stats['sampled_original_sizes'] = original_sizes
        stats['mean_original_width'] = np.mean([s[0] for s in original_sizes])
        stats['mean_original_height'] = np.mean([s[1] for s in original_sizes])
        
        return stats


def create_dataloaders(
    root_dir: str,
    batch_size: int = 4,
    target_resolution: Tuple[int, int] = (640, 640),
    num_workers: int = 2,
    train_transform: Optional[any] = None,
    val_transform: Optional[any] = None
) -> Tuple[any, any, any]:
    """
    Create PyTorch DataLoaders for train, validation, and test splits.
    
    DataLoaders handle:
    - Batching: Group multiple samples into batches
    - Shuffling: Randomize order (important for training)
    - Parallel loading: Use multiple workers to load data faster
    
    Args:
        root_dir: Path to KITTI dataset
        batch_size: Number of samples per batch (typically 4 for 4-camera systems)
        target_resolution: Image size (H, W), max 750×750
        num_workers: Number of parallel data loading workers (0 = main thread)
        train_transform: Augmentation for training set
        val_transform: Optional different transform for val/test
    
    Returns:
        Tuple of (train_loader, val_loader, test_loader)
    
    Example:
        >>> train_loader, val_loader, test_loader = create_dataloaders(
        ...     "kitti_data/",
        ...     batch_size=4,
        ...     target_resolution=(640, 640)
        ... )
        >>> # Training loop
        >>> for images, labels in train_loader:
        ...     # images shape: [batch_size, 3, 640, 640]
        ...     # Train model on this batch
        ...     pass
    """
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch required for DataLoader")
    
    from torch.utils.data import DataLoader
    
    # Create datasets for each split
    train_dataset = KITTIDataset(
        root_dir=root_dir,
        split='train',
        transform=train_transform,
        target_resolution=target_resolution
    )
    
    val_dataset = KITTIDataset(
        root_dir=root_dir,
        split='val',
        transform=val_transform,
        target_resolution=target_resolution
    )
    
    test_dataset = KITTIDataset(
        root_dir=root_dir,
        split='test',
        transform=None,  # No augmentation on test set
        target_resolution=target_resolution
    )
    
    # Create DataLoaders
    # Training: shuffle=True (randomize order each epoch)
    # Val/Test: shuffle=False (consistent order for reproducibility)
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True  # Faster GPU transfer
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )
    
    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )
    
    logger.info("DataLoaders created:")
    logger.info(f"  Train: {len(train_dataset)} samples, {len(train_loader)} batches")
    logger.info(f"  Val:   {len(val_dataset)} samples, {len(val_loader)} batches")
    logger.info(f"  Test:  {len(test_dataset)} samples, {len(test_loader)} batches")
    
    return train_loader, val_loader, test_loader


def main():
    """
    Demo KITTI dataset loading.
    
    Run with: python -m dl_misalignment.data.kitti_dataset
    """
    import sys
    
    print("=" * 60)
    print("KITTI Dataset Loader Demo")
    print("=" * 60)
    
    # Check if KITTI directory exists
    kitti_dir = "kitti_data"
    if not Path(kitti_dir).exists():
        print(f"\n❌ KITTI dataset not found at {kitti_dir}/")
        print("Please download KITTI dataset first.")
        print("See INSTALLATION.md for instructions.")
        sys.exit(1)
    
    # Create dataset
    print(f"\nLoading KITTI dataset from {kitti_dir}/...")
    try:
        dataset = KITTIDataset(
            root_dir=kitti_dir,
            split='train',
            target_resolution=(640, 640)
        )
        
        print(f"\n✓ Dataset loaded successfully!")
        print(f"  Split: {dataset.split}")
        print(f"  Samples: {len(dataset)}")
        print(f"  Target resolution: {dataset.target_resolution}")
        
        # Get statistics
        stats = dataset.get_statistics()
        print(f"\nDataset Statistics:")
        print(f"  Mean original size: {stats['mean_original_width']:.0f}×{stats['mean_original_height']:.0f}")
        
        # Load a sample
        print(f"\nLoading sample image...")
        image, label = dataset[0]
        print(f"  Image shape: {image.shape}")
        print(f"  Label: {label}")
        
        print("\n✓ KITTI dataset demo complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
