"""
Data Augmentation Engine for Camera Misalignment Detection

This module generates synthetic misalignment examples from aligned KITTI images.
The augmentation engine applies geometric and photometric transformations to
simulate camera position shifts, lighting changes, and other real-world variations.

Why Augmentation?
- KITTI images are naturally aligned (no misalignment)
- We need misaligned examples to train the detection model
- Augmentation creates labeled training data from transformations
- Example: Rotate image by 5° → label: misaligned, pose: [0, 0, 0, 5, 0, 0]

This design follows Requirements 6 and 21:
- Geometric: rotation, translation, cropping, horizontal flip
- Photometric: brightness, contrast, Gaussian noise
- Applied with 50% probability per sample
- Only applied to train/val splits (not test)
- Generates ground truth labels from applied transformations
"""

import logging
from typing import Dict, Tuple, Optional
import numpy as np
import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class AugmentationEngine:
    """
    Applies random transformations to training images and generates ground truth labels.
    
    This is a PyTorch-compatible transform that works with the KITTIDataset.
    It modifies both the image tensor and the label dictionary.
    
    Transformation Parameters (from Requirements 6 and 21):
    - Rotation: -10° to +10°
    - Translation: -50 to +50 pixels in X and Y
    - Brightness: 0.7 to 1.3 multiplicative factor
    - Contrast: 0.8 to 1.2 multiplicative factor
    - Gaussian noise: σ = 0.01
    - Horizontal flip: 50% probability
    - Random cropping: 90-100% of original scale
    - Overall application: 50% probability per sample
    
    Args:
        apply_probability: Probability of applying augmentation to a sample (default 0.5)
        split: Dataset split ('train', 'val', 'test'). Only applies to train/val.
        log_every: Log augmentation statistics every N calls (default 1000)
        seed: Random seed for reproducibility (optional)
    
    Example:
        >>> augmentation = AugmentationEngine(split='train')
        >>> image, label = augmentation(image, label)
        >>> # image is transformed, label contains ground truth pose
    """
    
    def __init__(
        self,
        apply_probability: float = 0.5,
        split: str = 'train',
        log_every: int = 1000,
        seed: Optional[int] = None
    ):
        """Initialize augmentation engine."""
        self.apply_probability = apply_probability
        self.split = split
        self.log_every = log_every
        self.rng = np.random.RandomState(seed)
        
        # Statistics tracking
        self.call_count = 0
        self.augmentation_stats = {
            'total_samples': 0,
            'augmented_samples': 0,
            'rotation': 0,
            'translation': 0,
            'brightness': 0,
            'contrast': 0,
            'noise': 0,
            'horizontal_flip': 0,
            'random_crop': 0
        }
        
        # Transformation ranges (from requirements)
        self.rotation_range = (-10.0, 10.0)  # degrees
        self.translation_range = (-50, 50)  # pixels in X and Y
        self.brightness_range = (0.7, 1.3)  # multiplicative factor
        self.contrast_range = (0.8, 1.2)  # multiplicative factor
        self.noise_std = 0.01  # standard deviation for Gaussian noise
        self.flip_probability = 0.5
        self.crop_scale_range = (0.90, 1.0)  # 90-100% of original scale
        
        logger.info(
            f"Initialized AugmentationEngine for {split} split "
            f"(apply_prob={apply_probability})"
        )
    
    def __call__(
        self,
        image: torch.Tensor,
        label: Dict
    ) -> Tuple[torch.Tensor, Dict]:
        """
        Apply augmentation to image and update label.
        
        This is called by the dataset's __getitem__ method.
        
        Args:
            image: Image tensor [3, H, W], normalized
            label: Label dictionary from dataset
        
        Returns:
            Tuple of (augmented_image, updated_label)
        """
        self.call_count += 1
        self.augmentation_stats['total_samples'] += 1
        
        # Don't augment test split
        if self.split == 'test':
            return image, label
        
        # Apply augmentation with specified probability
        if self.rng.rand() > self.apply_probability:
            return image, label
        
        self.augmentation_stats['augmented_samples'] += 1
        
        # Track which transformations are applied
        transformations_applied = {}
        
        # Initialize pose offset (will accumulate from transformations)
        # [X, Y, Z, roll, pitch, yaw] in meters and degrees
        pose_offset = np.zeros(6, dtype=np.float32)
        
        # Apply geometric transformations
        # These affect the ground truth pose
        
        # 1. Random Rotation (-10° to +10°)
        if self.rng.rand() > 0.5:
            angle_deg = self.rng.uniform(*self.rotation_range)
            image = self._apply_rotation(image, angle_deg)
            pose_offset[5] = angle_deg  # yaw rotation
            transformations_applied['rotation'] = angle_deg
            self.augmentation_stats['rotation'] += 1
        
        # 2. Random Translation (-50 to +50 pixels in X and Y)
        if self.rng.rand() > 0.5:
            tx = self.rng.randint(*self.translation_range)
            ty = self.rng.randint(*self.translation_range)
            image = self._apply_translation(image, tx, ty)
            # Convert pixel translation to approximate meters
            # Assuming ~0.01 meters per pixel (rough estimate for KITTI)
            pose_offset[0] = tx * 0.01  # X translation
            pose_offset[1] = ty * 0.01  # Y translation
            transformations_applied['translation'] = (tx, ty)
            self.augmentation_stats['translation'] += 1
        
        # 3. Random Cropping (90-100% scale)
        if self.rng.rand() > 0.5:
            scale = self.rng.uniform(*self.crop_scale_range)
            image = self._apply_random_crop(image, scale)
            # Cropping affects Z distance (closer = larger crop)
            pose_offset[2] = (1.0 - scale) * 2.0  # Z offset in meters
            transformations_applied['random_crop'] = scale
            self.augmentation_stats['random_crop'] += 1
        
        # 4. Horizontal Flip (50% probability)
        if self.rng.rand() < self.flip_probability:
            image = self._apply_horizontal_flip(image)
            # Flip affects X axis and yaw
            pose_offset[0] = -pose_offset[0]  # Mirror X
            pose_offset[5] = -pose_offset[5]  # Mirror yaw
            transformations_applied['horizontal_flip'] = True
            self.augmentation_stats['horizontal_flip'] += 1
        
        # Apply photometric transformations
        # These don't affect pose but add realism
        
        # 5. Random Brightness (0.7 to 1.3 multiplicative)
        if self.rng.rand() > 0.5:
            brightness_factor = self.rng.uniform(*self.brightness_range)
            image = self._apply_brightness(image, brightness_factor)
            transformations_applied['brightness'] = brightness_factor
            self.augmentation_stats['brightness'] += 1
        
        # 6. Random Contrast (0.8 to 1.2 multiplicative)
        if self.rng.rand() > 0.5:
            contrast_factor = self.rng.uniform(*self.contrast_range)
            image = self._apply_contrast(image, contrast_factor)
            transformations_applied['contrast'] = contrast_factor
            self.augmentation_stats['contrast'] += 1
        
        # 7. Gaussian Noise (σ=0.01)
        if self.rng.rand() > 0.5:
            image = self._apply_gaussian_noise(image, self.noise_std)
            transformations_applied['gaussian_noise'] = self.noise_std
            self.augmentation_stats['noise'] += 1
        
        # Update label with ground truth
        label['is_misaligned'] = 1  # Mark as misaligned
        
        # Calculate misalignment probability based on magnitude of pose offset
        # Larger offsets → higher probability
        misalignment_magnitude = np.linalg.norm(pose_offset)
        label['misalignment_probability'] = min(1.0, misalignment_magnitude / 10.0)
        
        # Update pose with accumulated offset
        label['pose'] = torch.from_numpy(pose_offset)
        
        # Record transformations applied
        label['augmentation_applied'] = transformations_applied
        
        # Log statistics periodically
        if self.call_count % self.log_every == 0:
            self._log_statistics()
        
        return image, label
    
    def _apply_rotation(self, image: torch.Tensor, angle_deg: float) -> torch.Tensor:
        """
        Rotate image by specified angle.
        
        Args:
            image: [3, H, W] tensor
            angle_deg: Rotation angle in degrees (positive = counter-clockwise)
        
        Returns:
            Rotated image [3, H, W]
        """
        # Convert to radians
        angle_rad = np.deg2rad(angle_deg)
        
        # Create rotation matrix
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)
        
        # PyTorch affine_grid expects 2x3 affine matrix
        # Rotation matrix: [[cos, -sin, 0], [sin, cos, 0]]
        theta = torch.tensor([
            [cos_a, -sin_a, 0],
            [sin_a, cos_a, 0]
        ], dtype=torch.float32)
        
        # Add batch dimension: [1, 3, H, W]
        image = image.unsqueeze(0)
        
        # Create sampling grid
        grid = F.affine_grid(
            theta.unsqueeze(0),
            image.size(),
            align_corners=False
        )
        
        # Apply transformation
        image = F.grid_sample(
            image,
            grid,
            mode='bilinear',
            padding_mode='border',
            align_corners=False
        )
        
        # Remove batch dimension: [3, H, W]
        return image.squeeze(0)
    
    def _apply_translation(
        self,
        image: torch.Tensor,
        tx: int,
        ty: int
    ) -> torch.Tensor:
        """
        Translate image by specified pixels.
        
        Args:
            image: [3, H, W] tensor
            tx: Translation in X (horizontal) in pixels
            ty: Translation in Y (vertical) in pixels
        
        Returns:
            Translated image [3, H, W]
        """
        _, H, W = image.shape
        
        # Normalize translation to [-1, 1] range for affine_grid
        tx_norm = 2.0 * tx / W
        ty_norm = 2.0 * ty / H
        
        # Translation matrix: [[1, 0, tx], [0, 1, ty]]
        theta = torch.tensor([
            [1, 0, tx_norm],
            [0, 1, ty_norm]
        ], dtype=torch.float32)
        
        # Add batch dimension
        image = image.unsqueeze(0)
        
        # Create sampling grid
        grid = F.affine_grid(
            theta.unsqueeze(0),
            image.size(),
            align_corners=False
        )
        
        # Apply transformation
        image = F.grid_sample(
            image,
            grid,
            mode='bilinear',
            padding_mode='border',
            align_corners=False
        )
        
        return image.squeeze(0)
    
    def _apply_random_crop(self, image: torch.Tensor, scale: float) -> torch.Tensor:
        """
        Apply random crop at specified scale and resize back to original size.
        
        Args:
            image: [3, H, W] tensor
            scale: Crop scale (0.9 = 90% of original, 1.0 = 100%)
        
        Returns:
            Cropped and resized image [3, H, W]
        """
        _, H, W = image.shape
        
        # Calculate crop size
        crop_h = int(H * scale)
        crop_w = int(W * scale)
        
        # Random crop position
        top = self.rng.randint(0, H - crop_h + 1) if crop_h < H else 0
        left = self.rng.randint(0, W - crop_w + 1) if crop_w < W else 0
        
        # Crop
        image = image[:, top:top+crop_h, left:left+crop_w]
        
        # Resize back to original size
        image = F.interpolate(
            image.unsqueeze(0),
            size=(H, W),
            mode='bilinear',
            align_corners=False
        ).squeeze(0)
        
        return image
    
    def _apply_horizontal_flip(self, image: torch.Tensor) -> torch.Tensor:
        """
        Flip image horizontally (left-right).
        
        Args:
            image: [3, H, W] tensor
        
        Returns:
            Flipped image [3, H, W]
        """
        return torch.flip(image, dims=[2])  # Flip along width dimension
    
    def _apply_brightness(
        self,
        image: torch.Tensor,
        factor: float
    ) -> torch.Tensor:
        """
        Adjust image brightness.
        
        Args:
            image: [3, H, W] tensor (normalized)
            factor: Multiplicative brightness factor (0.7 to 1.3)
        
        Returns:
            Adjusted image [3, H, W]
        """
        # Note: Image is already normalized with ImageNet stats
        # We apply brightness in normalized space
        return image * factor
    
    def _apply_contrast(self, image: torch.Tensor, factor: float) -> torch.Tensor:
        """
        Adjust image contrast.
        
        Args:
            image: [3, H, W] tensor (normalized)
            factor: Multiplicative contrast factor (0.8 to 1.2)
        
        Returns:
            Adjusted image [3, H, W]
        """
        # Contrast adjustment: (image - mean) * factor + mean
        mean = image.mean(dim=[1, 2], keepdim=True)
        return (image - mean) * factor + mean
    
    def _apply_gaussian_noise(
        self,
        image: torch.Tensor,
        std: float
    ) -> torch.Tensor:
        """
        Add Gaussian noise to image.
        
        Args:
            image: [3, H, W] tensor (normalized)
            std: Standard deviation of noise
        
        Returns:
            Noisy image [3, H, W]
        """
        noise = torch.randn_like(image) * std
        return image + noise
    
    def _log_statistics(self):
        """Log augmentation statistics."""
        stats = self.augmentation_stats
        total = stats['total_samples']
        augmented = stats['augmented_samples']
        
        if total == 0:
            return
        
        aug_rate = augmented / total * 100
        
        logger.info(f"Augmentation Statistics (after {total} samples):")
        logger.info(f"  Augmentation rate: {aug_rate:.1f}% ({augmented}/{total})")
        
        if augmented > 0:
            logger.info(f"  Transformation frequencies:")
            logger.info(f"    Rotation: {stats['rotation']} ({stats['rotation']/augmented*100:.1f}%)")
            logger.info(f"    Translation: {stats['translation']} ({stats['translation']/augmented*100:.1f}%)")
            logger.info(f"    Random crop: {stats['random_crop']} ({stats['random_crop']/augmented*100:.1f}%)")
            logger.info(f"    Horizontal flip: {stats['horizontal_flip']} ({stats['horizontal_flip']/augmented*100:.1f}%)")
            logger.info(f"    Brightness: {stats['brightness']} ({stats['brightness']/augmented*100:.1f}%)")
            logger.info(f"    Contrast: {stats['contrast']} ({stats['contrast']/augmented*100:.1f}%)")
            logger.info(f"    Gaussian noise: {stats['noise']} ({stats['noise']/augmented*100:.1f}%)")
    
    def get_statistics(self) -> Dict:
        """
        Get current augmentation statistics.
        
        Returns:
            Dictionary with augmentation statistics
        """
        return self.augmentation_stats.copy()
    
    def reset_statistics(self):
        """Reset augmentation statistics counters."""
        for key in self.augmentation_stats:
            self.augmentation_stats[key] = 0
        self.call_count = 0
        logger.info("Augmentation statistics reset")


def create_augmentation_engine(
    split: str,
    apply_probability: float = 0.5,
    seed: Optional[int] = None
) -> Optional[AugmentationEngine]:
    """
    Factory function to create augmentation engine for a dataset split.
    
    This is a convenience function that automatically disables augmentation
    for the test split (as per requirements).
    
    Args:
        split: Dataset split ('train', 'val', 'test')
        apply_probability: Probability of applying augmentation (default 0.5)
        seed: Random seed for reproducibility
    
    Returns:
        AugmentationEngine instance for train/val, None for test
    
    Example:
        >>> train_aug = create_augmentation_engine('train')
        >>> val_aug = create_augmentation_engine('val')
        >>> test_aug = create_augmentation_engine('test')  # Returns None
    """
    if split == 'test':
        logger.info("Test split: augmentation disabled")
        return None
    
    return AugmentationEngine(
        apply_probability=apply_probability,
        split=split,
        seed=seed
    )


def main():
    """
    Demo augmentation engine.
    
    Run with: python -m dl_misalignment.data.augmentation
    """
    print("=" * 60)
    print("Augmentation Engine Demo")
    print("=" * 60)
    
    # Create dummy image
    print("\nCreating synthetic test image...")
    image = torch.rand(3, 640, 640)  # Random normalized image
    
    # Create dummy label
    label = {
        'is_misaligned': 0,
        'misalignment_probability': 0.0,
        'pose': torch.zeros(6),
        'sample_id': 'demo',
        'original_size': (1242, 375),
        'augmentation_applied': {}
    }
    
    # Create augmentation engine
    print("Creating augmentation engine...")
    aug_engine = AugmentationEngine(
        apply_probability=1.0,  # Always apply for demo
        split='train',
        log_every=1
    )
    
    # Apply augmentation
    print("\nApplying augmentation...")
    aug_image, aug_label = aug_engine(image, label)
    
    print(f"\n✓ Augmentation applied!")
    print(f"  Original pose: {label['pose'].numpy()}")
    print(f"  Augmented pose: {aug_label['pose'].numpy()}")
    print(f"  Misalignment probability: {aug_label['misalignment_probability']:.3f}")
    print(f"  Transformations: {list(aug_label['augmentation_applied'].keys())}")
    
    # Apply multiple times to test statistics
    print("\nApplying 100 augmentations to test statistics...")
    for i in range(99):  # Already did 1
        aug_engine(image.clone(), label.copy())
    
    stats = aug_engine.get_statistics()
    print(f"\nStatistics after 100 samples:")
    print(f"  Total samples: {stats['total_samples']}")
    print(f"  Augmented samples: {stats['augmented_samples']}")
    print(f"  Rotation applications: {stats['rotation']}")
    print(f"  Translation applications: {stats['translation']}")
    
    print("\n✓ Augmentation engine demo complete!")


if __name__ == "__main__":
    main()
