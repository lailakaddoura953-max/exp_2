"""
Unit tests for AugmentationEngine

Tests verify that augmentation transformations:
- Preserve image dimensions
- Generate correct ground truth labels
- Apply transformations with correct probabilities
- Work only on train/val splits (not test)
- Log statistics correctly
"""

import pytest
import torch
import numpy as np
from dl_misalignment.data.augmentation import (
    AugmentationEngine,
    create_augmentation_engine
)


class TestAugmentationEngine:
    """Test suite for AugmentationEngine."""
    
    @pytest.fixture
    def sample_image(self):
        """Create sample normalized image tensor."""
        return torch.rand(3, 640, 640)
    
    @pytest.fixture
    def sample_label(self):
        """Create sample label dictionary."""
        return {
            'is_misaligned': 0,
            'misalignment_probability': 0.0,
            'pose': torch.zeros(6),
            'sample_id': 'test_sample',
            'original_size': (1242, 375),
            'augmentation_applied': {}
        }
    
    def test_initialization(self):
        """Test AugmentationEngine initialization."""
        aug = AugmentationEngine(
            apply_probability=0.5,
            split='train',
            log_every=1000,
            seed=42
        )
        
        assert aug.apply_probability == 0.5
        assert aug.split == 'train'
        assert aug.log_every == 1000
        assert aug.call_count == 0
    
    def test_preserves_image_dimensions(self, sample_image, sample_label):
        """Test that augmentation preserves image dimensions."""
        aug = AugmentationEngine(apply_probability=1.0, split='train', seed=42)
        
        original_shape = sample_image.shape
        aug_image, _ = aug(sample_image, sample_label)
        
        assert aug_image.shape == original_shape, \
            f"Image shape changed from {original_shape} to {aug_image.shape}"
    
    def test_generates_ground_truth_labels(self, sample_image, sample_label):
        """Test that augmentation generates ground truth labels."""
        aug = AugmentationEngine(apply_probability=1.0, split='train', seed=42)
        
        _, aug_label = aug(sample_image, sample_label)
        
        # Should mark as misaligned
        assert aug_label['is_misaligned'] == 1, "Should be marked as misaligned"
        
        # Should have non-zero probability
        assert aug_label['misalignment_probability'] > 0, \
            "Should have non-zero misalignment probability"
        
        # Should have pose offset
        assert torch.any(aug_label['pose'] != 0), "Should have non-zero pose offset"
        
        # Should record transformations
        assert len(aug_label['augmentation_applied']) > 0, \
            "Should record applied transformations"
    
    def test_no_augmentation_on_test_split(self, sample_image, sample_label):
        """Test that augmentation is disabled for test split."""
        aug = AugmentationEngine(apply_probability=1.0, split='test', seed=42)
        
        original_image = sample_image.clone()
        aug_image, aug_label = aug(sample_image, sample_label)
        
        # Image should be unchanged
        assert torch.allclose(aug_image, original_image), \
            "Test split should not modify images"
        
        # Label should be unchanged
        assert aug_label['is_misaligned'] == 0, "Test split should not mark as misaligned"
    
    def test_apply_probability(self, sample_image, sample_label):
        """Test that augmentation respects apply_probability."""
        # With probability 0.0, should never apply
        aug_never = AugmentationEngine(apply_probability=0.0, split='train', seed=42)
        
        unmodified_count = 0
        for _ in range(100):
            _, label = aug_never(sample_image.clone(), sample_label.copy())
            if label['is_misaligned'] == 0:
                unmodified_count += 1
        
        assert unmodified_count == 100, "With prob=0.0, should never augment"
        
        # With probability 1.0, should always apply
        aug_always = AugmentationEngine(apply_probability=1.0, split='train', seed=42)
        
        modified_count = 0
        for _ in range(100):
            _, label = aug_always(sample_image.clone(), sample_label.copy())
            if label['is_misaligned'] == 1:
                modified_count += 1
        
        assert modified_count == 100, "With prob=1.0, should always augment"
    
    def test_rotation_transformation(self, sample_image, sample_label):
        """Test rotation transformation is applied correctly."""
        aug = AugmentationEngine(apply_probability=1.0, split='train', seed=42)
        
        # Run multiple times to ensure rotation is applied
        rotations = []
        for _ in range(50):
            _, label = aug(sample_image.clone(), sample_label.copy())
            if 'rotation' in label['augmentation_applied']:
                angle = label['augmentation_applied']['rotation']
                rotations.append(angle)
                
                # Check rotation is in range
                assert -10 <= angle <= 10, f"Rotation {angle} outside [-10, 10] range"
                
                # Check pose yaw is updated
                assert label['pose'][5] == angle, "Yaw should match rotation angle"
        
        assert len(rotations) > 0, "Should apply rotation at least once in 50 samples"
    
    def test_translation_transformation(self, sample_image, sample_label):
        """Test translation transformation is applied correctly."""
        aug = AugmentationEngine(apply_probability=1.0, split='train', seed=42)
        
        translations = []
        for _ in range(50):
            _, label = aug(sample_image.clone(), sample_label.copy())
            if 'translation' in label['augmentation_applied']:
                tx, ty = label['augmentation_applied']['translation']
                translations.append((tx, ty))
                
                # Check translation is in range
                assert -50 <= tx <= 50, f"X translation {tx} outside [-50, 50]"
                assert -50 <= ty <= 50, f"Y translation {ty} outside [-50, 50]"
        
        assert len(translations) > 0, "Should apply translation at least once"
    
    def test_brightness_transformation(self, sample_image, sample_label):
        """Test brightness transformation is applied correctly."""
        aug = AugmentationEngine(apply_probability=1.0, split='train', seed=42)
        
        brightness_factors = []
        for _ in range(50):
            _, label = aug(sample_image.clone(), sample_label.copy())
            if 'brightness' in label['augmentation_applied']:
                factor = label['augmentation_applied']['brightness']
                brightness_factors.append(factor)
                
                # Check factor is in range
                assert 0.7 <= factor <= 1.3, \
                    f"Brightness factor {factor} outside [0.7, 1.3]"
        
        assert len(brightness_factors) > 0, "Should apply brightness at least once"
    
    def test_contrast_transformation(self, sample_image, sample_label):
        """Test contrast transformation is applied correctly."""
        aug = AugmentationEngine(apply_probability=1.0, split='train', seed=42)
        
        contrast_factors = []
        for _ in range(50):
            _, label = aug(sample_image.clone(), sample_label.copy())
            if 'contrast' in label['augmentation_applied']:
                factor = label['augmentation_applied']['contrast']
                contrast_factors.append(factor)
                
                # Check factor is in range
                assert 0.8 <= factor <= 1.2, \
                    f"Contrast factor {factor} outside [0.8, 1.2]"
        
        assert len(contrast_factors) > 0, "Should apply contrast at least once"
    
    def test_gaussian_noise_transformation(self, sample_image, sample_label):
        """Test Gaussian noise is applied correctly."""
        aug = AugmentationEngine(apply_probability=1.0, split='train', seed=42)
        
        noise_count = 0
        for _ in range(50):
            _, label = aug(sample_image.clone(), sample_label.copy())
            if 'gaussian_noise' in label['augmentation_applied']:
                std = label['augmentation_applied']['gaussian_noise']
                noise_count += 1
                
                # Check noise std is correct
                assert std == 0.01, f"Noise std should be 0.01, got {std}"
        
        assert noise_count > 0, "Should apply Gaussian noise at least once"
    
    def test_horizontal_flip_transformation(self, sample_image, sample_label):
        """Test horizontal flip is applied correctly."""
        aug = AugmentationEngine(apply_probability=1.0, split='train', seed=42)
        
        flip_count = 0
        for _ in range(50):
            _, label = aug(sample_image.clone(), sample_label.copy())
            if 'horizontal_flip' in label['augmentation_applied']:
                flip_count += 1
        
        assert flip_count > 0, "Should apply horizontal flip at least once"
    
    def test_random_crop_transformation(self, sample_image, sample_label):
        """Test random crop is applied correctly."""
        aug = AugmentationEngine(apply_probability=1.0, split='train', seed=42)
        
        crop_scales = []
        for _ in range(50):
            _, label = aug(sample_image.clone(), sample_label.copy())
            if 'random_crop' in label['augmentation_applied']:
                scale = label['augmentation_applied']['random_crop']
                crop_scales.append(scale)
                
                # Check scale is in range
                assert 0.90 <= scale <= 1.0, \
                    f"Crop scale {scale} outside [0.9, 1.0]"
        
        assert len(crop_scales) > 0, "Should apply random crop at least once"
    
    def test_statistics_tracking(self, sample_image, sample_label):
        """Test that augmentation statistics are tracked correctly."""
        aug = AugmentationEngine(
            apply_probability=1.0,
            split='train',
            log_every=1000,
            seed=42
        )
        
        # Apply augmentation 10 times
        for _ in range(10):
            aug(sample_image.clone(), sample_label.copy())
        
        stats = aug.get_statistics()
        
        # Check basic stats
        assert stats['total_samples'] == 10, "Should track total samples"
        assert stats['augmented_samples'] == 10, "Should track augmented samples"
        
        # At least some transformations should have been applied
        total_transforms = (
            stats['rotation'] + stats['translation'] + stats['brightness'] +
            stats['contrast'] + stats['noise'] + stats['horizontal_flip'] +
            stats['random_crop']
        )
        assert total_transforms > 0, "Should apply at least some transformations"
    
    def test_statistics_reset(self, sample_image, sample_label):
        """Test that statistics can be reset."""
        aug = AugmentationEngine(apply_probability=1.0, split='train', seed=42)
        
        # Apply augmentation
        aug(sample_image, sample_label)
        
        # Reset
        aug.reset_statistics()
        
        stats = aug.get_statistics()
        assert stats['total_samples'] == 0, "Stats should be reset"
        assert stats['augmented_samples'] == 0, "Stats should be reset"
        assert aug.call_count == 0, "Call count should be reset"
    
    def test_factory_function(self):
        """Test create_augmentation_engine factory function."""
        # Train split should return engine
        train_aug = create_augmentation_engine('train', seed=42)
        assert train_aug is not None, "Should create engine for train"
        assert isinstance(train_aug, AugmentationEngine)
        
        # Val split should return engine
        val_aug = create_augmentation_engine('val', seed=42)
        assert val_aug is not None, "Should create engine for val"
        assert isinstance(val_aug, AugmentationEngine)
        
        # Test split should return None
        test_aug = create_augmentation_engine('test')
        assert test_aug is None, "Should return None for test split"
    
    def test_multiple_transformations_applied(self, sample_image, sample_label):
        """Test that multiple transformations can be applied to same sample."""
        aug = AugmentationEngine(apply_probability=1.0, split='train', seed=42)
        
        # Run enough times to likely get multiple transformations
        max_transforms = 0
        for _ in range(100):
            _, label = aug(sample_image.clone(), sample_label.copy())
            num_transforms = len(label['augmentation_applied'])
            max_transforms = max(max_transforms, num_transforms)
        
        # Should apply at least 3 transformations to at least one sample
        # (Requirement 21.1: at least 3 different augmentations per sample)
        assert max_transforms >= 3, \
            f"Should apply at least 3 transformations to some samples, got max {max_transforms}"
    
    def test_deterministic_with_seed(self, sample_image, sample_label):
        """Test that results are deterministic with same seed."""
        aug1 = AugmentationEngine(apply_probability=1.0, split='train', seed=42)
        aug2 = AugmentationEngine(apply_probability=1.0, split='train', seed=42)
        
        _, label1 = aug1(sample_image.clone(), sample_label.copy())
        _, label2 = aug2(sample_image.clone(), sample_label.copy())
        
        # Same seed should produce same transformations
        assert label1['augmentation_applied'].keys() == label2['augmentation_applied'].keys(), \
            "Same seed should apply same transformations"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
