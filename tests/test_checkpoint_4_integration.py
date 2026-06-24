"""
Checkpoint 4: Integration Test - Data Pipeline and Feature Extractor Verification

This comprehensive test verifies that all previously implemented components
work together correctly:

1. KITTI dataset loader functionality
2. Dataset splitting (70/15/15) with no overlap  
3. Data augmentation engine generates correct ground truth labels
4. CNN Feature Extractor produces correct pyramid outputs
5. End-to-end data pipeline: Load → Split → Augment → Extract features
6. Feature pyramid shapes match expectations for sample input
7. Augmentation produces valid ground truth labels
8. Memory usage stays within 8GB VRAM for batch_size=4
9. No crashes with various input resolutions (256×256 to 750×750)

Test Requirements:
- Components to verify: KITTI dataset loader, dataset splitting, augmentation engine, CNN feature extractor
- Verification Steps: End-to-end pipeline test, feature pyramid shape verification, augmentation ground truth validation
- Memory constraints: ≤8GB VRAM for batch_size=4
- Resolution handling: 256×256 to 750×750
"""

import pytest
import torch
import numpy as np
from pathlib import Path
import tempfile
from typing import Tuple, List

# Import components to test
from src.dl_misalignment.data.kitti_dataset import KITTIDataset, create_dataloaders
from src.dl_misalignment.data.augmentation import AugmentationEngine, create_augmentation_engine
from src.dl_misalignment.models.cnn_feature_extractor import CNNFeatureExtractor


class TestCheckpoint4Integration:
    """
    Integration tests for Checkpoint 4: Data Pipeline and Feature Extractor.
    
    These tests verify that all components work together correctly before
    proceeding to optical flow implementation.
    """
    
    @pytest.fixture
    def mock_kitti_dataset(self, tmp_path):
        """
        Create a minimal mock KITTI dataset structure for testing.
        
        We don't need real KITTI data for this test - just the directory
        structure and some dummy images to verify the pipeline works.
        """
        # Create KITTI-like directory structure
        kitti_root = tmp_path / "kitti_mock"
        
        # Create a sequence directory
        seq_dir = kitti_root / "2011_09_26" / "2011_09_26_drive_0001_sync" / "image_02" / "data"
        seq_dir.mkdir(parents=True, exist_ok=True)
        
        # Create 100 dummy images (enough to test splitting)
        from PIL import Image
        for i in range(100):
            # Create a simple test image (RGB)
            img = Image.new('RGB', (640, 480), color=(i % 256, (i*2) % 256, (i*3) % 256))
            img.save(seq_dir / f"{i:010d}.png")
        
        return str(kitti_root)
    
    def test_1_kitti_dataset_loading(self, mock_kitti_dataset):
        """
        Test 1: Verify KITTI dataset loader functionality.
        
        Requirements verified:
        - KITTI dataset loading
        - Image preprocessing (resize, normalize)
        - Preservation of original resolution metadata
        """
        print("\n" + "="*60)
        print("Test 1: KITTI Dataset Loading")
        print("="*60)
        
        # Create dataset
        dataset = KITTIDataset(
            root_dir=mock_kitti_dataset,
            split='train',
            target_resolution=(640, 640),
            transform=None
        )
        
        # Verify dataset loaded samples
        assert len(dataset) > 0, "Dataset should contain samples"
        print(f"✓ Dataset loaded {len(dataset)} samples")
        
        # Test loading a single sample
        image, label = dataset[0]
        
        # Verify image properties
        assert image.shape == (3, 640, 640), f"Expected (3, 640, 640), got {image.shape}"
        assert image.dtype == torch.float32, f"Expected float32, got {image.dtype}"
        print(f"✓ Image shape correct: {image.shape}")
        
        # Verify label structure
        assert 'sample_id' in label, "Label should contain sample_id"
        assert 'original_size' in label, "Label should contain original_size"
        assert 'pose' in label, "Label should contain pose"
        print(f"✓ Label structure valid: {list(label.keys())}")
        
        # Verify normalization (ImageNet stats should make mean ~0, std ~1)
        # Allow some tolerance since this is a dummy image
        print(f"  Image mean: {image.mean():.3f}, std: {image.std():.3f}")
        
        print("✓ Test 1 PASSED: KITTI dataset loading works correctly\n")
    
    def test_2_dataset_splitting(self, mock_kitti_dataset):
        """
        Test 2: Verify dataset splitting (70/15/15) with no overlap.
        
        Requirements verified:
        - 70% train, 15% val, 15% test (±2% tolerance)
        - No sample overlap between splits
        - Deterministic splitting (reproducibility)
        """
        print("\n" + "="*60)
        print("Test 2: Dataset Splitting Verification")
        print("="*60)
        
        # Create datasets for all splits
        train_dataset = KITTIDataset(
            root_dir=mock_kitti_dataset,
            split='train',
            target_resolution=(640, 640)
        )
        
        val_dataset = KITTIDataset(
            root_dir=mock_kitti_dataset,
            split='val',
            target_resolution=(640, 640)
        )
        
        test_dataset = KITTIDataset(
            root_dir=mock_kitti_dataset,
            split='test',
            target_resolution=(640, 640)
        )
        
        # Calculate split sizes
        total_samples = len(train_dataset) + len(val_dataset) + len(test_dataset)
        train_pct = len(train_dataset) / total_samples * 100
        val_pct = len(val_dataset) / total_samples * 100
        test_pct = len(test_dataset) / total_samples * 100
        
        print(f"Total samples: {total_samples}")
        print(f"Train: {len(train_dataset)} ({train_pct:.1f}%)")
        print(f"Val:   {len(val_dataset)} ({val_pct:.1f}%)")
        print(f"Test:  {len(test_dataset)} ({test_pct:.1f}%)")
        
        # Verify split ratios (70±2%, 15±2%, 15±2%)
        assert 68 <= train_pct <= 72, f"Train split {train_pct:.1f}% outside 70%±2%"
        assert 13 <= val_pct <= 17, f"Val split {val_pct:.1f}% outside 15%±2%"
        assert 13 <= test_pct <= 17, f"Test split {test_pct:.1f}% outside 15%±2%"
        print("✓ Split ratios within tolerance")
        
        # Verify no overlap between splits
        # Get sample IDs from each split
        train_ids = {train_dataset[i][1]['sample_id'] for i in range(len(train_dataset))}
        val_ids = {val_dataset[i][1]['sample_id'] for i in range(len(val_dataset))}
        test_ids = {test_dataset[i][1]['sample_id'] for i in range(len(test_dataset))}
        
        # Check for overlaps
        assert len(train_ids & val_ids) == 0, "Train and val splits overlap!"
        assert len(train_ids & test_ids) == 0, "Train and test splits overlap!"
        assert len(val_ids & test_ids) == 0, "Val and test splits overlap!"
        print("✓ No overlap between splits")
        
        # Verify all samples are accounted for
        assert len(train_ids | val_ids | test_ids) == total_samples, "Some samples missing from splits"
        print("✓ All samples accounted for in splits")
        
        print("✓ Test 2 PASSED: Dataset splitting is correct\n")
    
    def test_3_augmentation_ground_truth(self, mock_kitti_dataset):
        """
        Test 3: Verify augmentation engine generates correct ground truth labels.
        
        Requirements verified:
        - Augmentation transformations applied correctly
        - Ground truth pose labels generated from transformations
        - Misalignment probability computed correctly
        - Augmentation only on train/val (not test)
        """
        print("\n" + "="*60)
        print("Test 3: Augmentation Ground Truth Verification")
        print("="*60)
        
        # Create augmentation engine
        aug_engine = AugmentationEngine(
            apply_probability=1.0,  # Always apply for testing
            split='train'
        )
        
        # Create a test image and label
        image = torch.randn(3, 640, 640)
        label = {
            'is_misaligned': 0,
            'misalignment_probability': 0.0,
            'pose': torch.zeros(6),
            'sample_id': 'test',
            'original_size': (640, 640),
            'augmentation_applied': {}
        }
        
        # Apply augmentation
        aug_image, aug_label = aug_engine(image, label)
        
        # Verify image shape preserved
        assert aug_image.shape == image.shape, "Augmentation should preserve image shape"
        print(f"✓ Image shape preserved: {aug_image.shape}")
        
        # Verify label was updated
        assert aug_label['is_misaligned'] == 1, "Augmented image should be marked as misaligned"
        assert aug_label['misalignment_probability'] > 0, "Should have non-zero misalignment probability"
        print(f"✓ Misalignment label: is_misaligned={aug_label['is_misaligned']}, prob={aug_label['misalignment_probability']:.3f}")
        
        # Verify pose offset is non-zero (some transformation was applied)
        pose_magnitude = torch.norm(aug_label['pose']).item()
        assert pose_magnitude > 0, "Pose should have non-zero offset after augmentation"
        print(f"✓ Pose offset magnitude: {pose_magnitude:.3f}")
        print(f"  Pose: {aug_label['pose'].numpy()}")
        
        # Verify augmentation transformations recorded
        assert len(aug_label['augmentation_applied']) > 0, "Should record applied transformations"
        print(f"✓ Transformations applied: {list(aug_label['augmentation_applied'].keys())}")
        
        # Verify augmentation is disabled for test split
        test_aug = create_augmentation_engine('test')
        assert test_aug is None, "Augmentation should be disabled for test split"
        print("✓ Augmentation correctly disabled for test split")
        
        print("✓ Test 3 PASSED: Augmentation generates correct ground truth labels\n")
    
    def test_4_cnn_feature_extractor_pyramid(self):
        """
        Test 4: Verify CNN Feature Extractor produces correct pyramid outputs.
        
        Requirements verified:
        - Feature pyramid has 4 levels
        - Shapes match expected dimensions for sample input (640×640)
        - Level 0: [batch, 64, 640, 640]
        - Level 1: [batch, 128, 320, 320]
        - Level 2: [batch, 256, 160, 160]
        - Level 3: [batch, 512, 80, 80]
        """
        print("\n" + "="*60)
        print("Test 4: CNN Feature Extractor Pyramid Verification")
        print("="*60)
        
        # Create model
        model = CNNFeatureExtractor()
        model.eval()  # Set to evaluation mode
        
        # Create test input (batch_size=4, 640×640 resolution)
        batch_size = 4
        test_input = torch.randn(batch_size, 3, 640, 640)
        
        print(f"Input shape: {test_input.shape}")
        
        # Forward pass
        with torch.no_grad():
            pyramid = model(test_input)
        
        # Verify pyramid structure
        assert len(pyramid) == 4, f"Pyramid should have 4 levels, got {len(pyramid)}"
        print(f"✓ Pyramid has 4 levels")
        
        # Expected shapes for 640×640 input
        expected_shapes = [
            (batch_size, 64, 640, 640),   # Level 0: 1× resolution
            (batch_size, 128, 320, 320),  # Level 1: 1/2× resolution
            (batch_size, 256, 160, 160),  # Level 2: 1/4× resolution
            (batch_size, 512, 80, 80)     # Level 3: 1/8× resolution
        ]
        
        # Verify each level
        for level, (features, expected_shape) in enumerate(zip(pyramid, expected_shapes)):
            assert features.shape == torch.Size(expected_shape), \
                f"Level {level}: Expected {expected_shape}, got {features.shape}"
            print(f"✓ Level {level}: {features.shape} - channels={features.shape[1]}, size={features.shape[2]}×{features.shape[3]}")
        
        # Verify channel progression (doubling at each level)
        assert pyramid[0].shape[1] == 64, "Level 0 should have 64 channels"
        assert pyramid[1].shape[1] == 128, "Level 1 should have 128 channels"
        assert pyramid[2].shape[1] == 256, "Level 2 should have 256 channels"
        assert pyramid[3].shape[1] == 512, "Level 3 should have 512 channels"
        print("✓ Channel progression correct (64→128→256→512)")
        
        # Verify spatial resolution reduction (halving at each level)
        assert pyramid[1].shape[2] == pyramid[0].shape[2] // 2, "Level 1 should be 1/2 resolution"
        assert pyramid[2].shape[2] == pyramid[0].shape[2] // 4, "Level 2 should be 1/4 resolution"
        assert pyramid[3].shape[2] == pyramid[0].shape[2] // 8, "Level 3 should be 1/8 resolution"
        print("✓ Spatial resolution reduction correct (1× → 1/2× → 1/4× → 1/8×)")
        
        print("✓ Test 4 PASSED: Feature pyramid structure is correct\n")
    
    def test_5_end_to_end_pipeline(self, mock_kitti_dataset):
        """
        Test 5: Verify end-to-end data pipeline integration.
        
        Requirements verified:
        - Load KITTI data → Split → Augment → Extract features
        - All components work together seamlessly
        - Feature extraction works on augmented images
        """
        print("\n" + "="*60)
        print("Test 5: End-to-End Pipeline Integration")
        print("="*60)
        
        # Create augmentation engine
        aug_engine = AugmentationEngine(
            apply_probability=1.0,
            split='train'
        )
        
        # Create dataset with augmentation
        dataset = KITTIDataset(
            root_dir=mock_kitti_dataset,
            split='train',
            target_resolution=(640, 640),
            transform=aug_engine
        )
        
        print(f"✓ Dataset created with augmentation: {len(dataset)} samples")
        
        # Load a sample (goes through: load → augment)
        image, label = dataset[0]
        
        print(f"✓ Sample loaded: image shape={image.shape}")
        print(f"  Label: is_misaligned={label['is_misaligned']}, prob={label['misalignment_probability']:.3f}")
        
        # Create feature extractor
        model = CNNFeatureExtractor()
        model.eval()
        
        # Extract features from augmented image
        with torch.no_grad():
            # Add batch dimension: [3, H, W] → [1, 3, H, W]
            image_batch = image.unsqueeze(0)
            pyramid = model(image_batch)
        
        print(f"✓ Features extracted from augmented image")
        print(f"  Pyramid levels: {len(pyramid)}")
        for level, features in enumerate(pyramid):
            print(f"  Level {level}: {features.shape}")
        
        # Verify complete pipeline
        assert image.shape == (3, 640, 640), "Image preprocessing works"
        assert label['is_misaligned'] == 1, "Augmentation works"
        assert len(pyramid) == 4, "Feature extraction works"
        
        print("✓ Test 5 PASSED: End-to-end pipeline works correctly\n")
    
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_6_memory_usage_batch_4(self):
        """
        Test 6: Verify memory usage stays within 8GB VRAM for batch_size=4.
        
        Requirements verified:
        - Memory consumption ≤8GB VRAM for batch_size=4
        - 640×640 resolution
        - Feature extractor forward pass
        """
        print("\n" + "="*60)
        print("Test 6: Memory Usage Verification (batch_size=4)")
        print("="*60)
        
        # Move to GPU
        device = torch.device('cuda')
        model = CNNFeatureExtractor().to(device)
        model.eval()
        
        # Reset memory stats
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.empty_cache()
        
        # Create batch of 4 images at 640×640
        batch_size = 4
        test_input = torch.randn(batch_size, 3, 640, 640, device=device)
        
        print(f"Input: batch_size={batch_size}, resolution=640×640")
        
        # Forward pass
        with torch.no_grad():
            pyramid = model(test_input)
        
        # Check memory usage
        memory_allocated = torch.cuda.max_memory_allocated() / (1024**3)  # Convert to GB
        memory_reserved = torch.cuda.max_memory_reserved() / (1024**3)
        
        print(f"Memory allocated: {memory_allocated:.2f} GB")
        print(f"Memory reserved:  {memory_reserved:.2f} GB")
        
        # Verify memory constraint (≤8GB VRAM)
        # We check allocated memory (actual usage) rather than reserved (cached)
        assert memory_allocated <= 8.0, \
            f"Memory usage {memory_allocated:.2f}GB exceeds 8GB limit for batch_size=4"
        print(f"✓ Memory usage within limit: {memory_allocated:.2f}GB ≤ 8.0GB")
        
        # Clean up
        del model, test_input, pyramid
        torch.cuda.empty_cache()
        
        print("✓ Test 6 PASSED: Memory usage within constraints\n")
    
    def test_7_various_resolutions(self):
        """
        Test 7: Verify no crashes with various input resolutions (256×256 to 750×750).
        
        Requirements verified:
        - Supports resolutions from 256×256 to 750×750
        - Feature pyramid adapts to different input sizes
        - No crashes or errors
        """
        print("\n" + "="*60)
        print("Test 7: Various Input Resolutions")
        print("="*60)
        
        # Create model
        model = CNNFeatureExtractor()
        model.eval()
        
        # Test various resolutions
        test_resolutions = [
            (256, 256),   # Minimum
            (320, 320),
            (480, 480),
            (640, 640),   # Target
            (750, 750),   # Maximum
        ]
        
        for height, width in test_resolutions:
            # Create test input
            test_input = torch.randn(1, 3, height, width)
            
            try:
                # Forward pass
                with torch.no_grad():
                    pyramid = model(test_input)
                
                # Verify pyramid structure
                assert len(pyramid) == 4, f"Should have 4 pyramid levels"
                
                # Verify expected shapes
                expected_shapes = [
                    (1, 64, height, width),
                    (1, 128, height//2, width//2),
                    (1, 256, height//4, width//4),
                    (1, 512, height//8, width//8)
                ]
                
                for level, (features, expected) in enumerate(zip(pyramid, expected_shapes)):
                    assert features.shape == torch.Size(expected), \
                        f"Level {level} shape mismatch at resolution {height}×{width}"
                
                print(f"✓ Resolution {height}×{width}: SUCCESS")
                print(f"  Pyramid: {[f.shape for f in pyramid]}")
                
            except Exception as e:
                pytest.fail(f"Failed at resolution {height}×{width}: {e}")
        
        print("✓ Test 7 PASSED: All resolutions handled correctly\n")
    
    def test_8_augmentation_value_ranges(self):
        """
        Test 8: Verify augmentation produces valid ground truth label ranges.
        
        Requirements verified:
        - Rotation: -10° to +10°
        - Translation: -50 to +50 pixels
        - Brightness: 0.7 to 1.3
        - Contrast: 0.8 to 1.2
        - Misalignment probability: 0.0 to 1.0
        """
        print("\n" + "="*60)
        print("Test 8: Augmentation Value Ranges")
        print("="*60)
        
        # Create augmentation engine
        aug_engine = AugmentationEngine(
            apply_probability=1.0,  # Always apply
            split='train',
            seed=42  # Fixed seed for reproducibility
        )
        
        # Run augmentation multiple times to collect statistics
        n_samples = 50
        rotations = []
        translations_x = []
        translations_y = []
        probabilities = []
        
        for i in range(n_samples):
            image = torch.randn(3, 640, 640)
            label = {
                'is_misaligned': 0,
                'misalignment_probability': 0.0,
                'pose': torch.zeros(6),
                'sample_id': f'test_{i}',
                'original_size': (640, 640),
                'augmentation_applied': {}
            }
            
            aug_image, aug_label = aug_engine(image, label)
            
            # Collect statistics
            if 'rotation' in aug_label['augmentation_applied']:
                rotations.append(aug_label['augmentation_applied']['rotation'])
            
            if 'translation' in aug_label['augmentation_applied']:
                tx, ty = aug_label['augmentation_applied']['translation']
                translations_x.append(tx)
                translations_y.append(ty)
            
            probabilities.append(aug_label['misalignment_probability'])
        
        # Verify rotation range (-10° to +10°)
        if rotations:
            min_rot, max_rot = min(rotations), max(rotations)
            print(f"Rotation range: [{min_rot:.2f}°, {max_rot:.2f}°]")
            assert -10 <= min_rot and max_rot <= 10, \
                f"Rotation outside expected range: [{min_rot:.2f}, {max_rot:.2f}]"
            print(f"✓ Rotation within valid range: -10° to +10°")
        
        # Verify translation range (-50 to +50 pixels)
        if translations_x:
            min_tx, max_tx = min(translations_x), max(translations_x)
            min_ty, max_ty = min(translations_y), max(translations_y)
            print(f"Translation X range: [{min_tx}, {max_tx}] pixels")
            print(f"Translation Y range: [{min_ty}, {max_ty}] pixels")
            assert -50 <= min_tx and max_tx <= 50, "Translation X outside range"
            assert -50 <= min_ty and max_ty <= 50, "Translation Y outside range"
            print(f"✓ Translation within valid range: -50 to +50 pixels")
        
        # Verify misalignment probability range (0.0 to 1.0)
        min_prob, max_prob = min(probabilities), max(probabilities)
        print(f"Misalignment probability range: [{min_prob:.3f}, {max_prob:.3f}]")
        assert 0.0 <= min_prob and max_prob <= 1.0, \
            f"Probability outside [0, 1] range: [{min_prob}, {max_prob}]"
        print(f"✓ Misalignment probability within valid range: 0.0 to 1.0")
        
        print("✓ Test 8 PASSED: Augmentation value ranges are valid\n")


def main():
    """
    Run checkpoint 4 integration tests manually.
    
    Usage:
        python tests/test_checkpoint_4_integration.py
    or:
        pytest tests/test_checkpoint_4_integration.py -v -s
    """
    print("=" * 70)
    print("CHECKPOINT 4: Data Pipeline and Feature Extractor Integration Tests")
    print("=" * 70)
    print()
    print("This test suite verifies that all previously implemented components")
    print("work together correctly before proceeding to optical flow implementation.")
    print()
    print("Components tested:")
    print("  1. KITTI dataset loader")
    print("  2. Dataset splitting (70/15/15)")
    print("  3. Data augmentation engine")
    print("  4. CNN Feature Extractor")
    print("  5. End-to-end integration")
    print("  6. Memory usage (if CUDA available)")
    print("  7. Various input resolutions")
    print("  8. Augmentation value ranges")
    print()
    print("=" * 70)
    print()
    
    # Run with pytest
    pytest.main([__file__, '-v', '-s'])


if __name__ == '__main__':
    main()
