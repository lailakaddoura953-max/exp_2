"""
Unit tests for Deep Learning KITTI Dataset Module (Task 2.1)

Tests the KITTIDataset implementation for the deep learning misalignment detection system.
This is separate from the rule-based system's KITTI loader (test_kitti_loader.py).
"""

import pytest
import numpy as np
from pathlib import Path
from PIL import Image
import tempfile

# Try to import torch
try:
    import torch
    from torch.utils.data import Dataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    Dataset = object

# Import the module under test
pytestmark = pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not installed")

if TORCH_AVAILABLE:
    import sys
    sys.path.insert(0, 'src')
    from dl_misalignment.data.kitti_dataset import KITTIDataset, create_dataloaders


class TestKITTIDatasetClass:
    """Test KITTIDataset class structure and initialization"""
    
    def test_inherits_from_torch_dataset(self):
        """Test that KITTIDataset inherits from torch.utils.data.Dataset"""
        assert issubclass(KITTIDataset, Dataset), "KITTIDataset must inherit from Dataset"
    
    def test_has_required_methods(self):
        """Test that KITTIDataset implements required Dataset methods"""
        assert hasattr(KITTIDataset, '__len__'), "Missing __len__ method"
        assert hasattr(KITTIDataset, '__getitem__'), "Missing __getitem__ method"
    
    def test_resolution_constraint_enforcement(self):
        """Test that resolution constraint (≤750×750) is enforced"""
        # Should raise ValueError for resolution > 750×750
        with pytest.raises(ValueError, match="750"):
            KITTIDataset(
                root_dir="kitti_data",
                target_resolution=(800, 800)
            )
        
        # Should raise ValueError for either dimension > 750
        with pytest.raises(ValueError, match="750"):
            KITTIDataset(
                root_dir="kitti_data",
                target_resolution=(640, 800)
            )
        
        with pytest.raises(ValueError, match="750"):
            KITTIDataset(
                root_dir="kitti_data",
                target_resolution=(800, 640)
            )
    
    def test_valid_resolutions_accepted(self):
        """Test that valid resolutions (≤750×750) are accepted"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal KITTI structure
            img_dir = Path(tmpdir) / "2011_09_26" / "2011_09_26_drive_0001_sync" / "image_02" / "data"
            img_dir.mkdir(parents=True, exist_ok=True)
            
            # Create dummy image
            dummy_img = Image.fromarray(np.random.randint(0, 255, (375, 1242, 3), dtype=np.uint8))
            dummy_img.save(img_dir / "0000000000.png")
            
            # These should all work
            valid_resolutions = [
                (256, 256),
                (640, 640),
                (750, 750),
                (640, 480),
                (375, 1242)
            ]
            
            for res in valid_resolutions:
                dataset = KITTIDataset(
                    root_dir=tmpdir,
                    target_resolution=res
                )
                assert dataset.target_resolution == res


class TestKITTIDatasetLoading:
    """Test KITTI dataset loading and preprocessing"""
    
    def create_mock_kitti_structure(self, tmpdir, n_images=5):
        """Helper to create mock KITTI directory structure"""
        img_dir = Path(tmpdir) / "2011_09_26" / "2011_09_26_drive_0001_sync" / "image_02" / "data"
        img_dir.mkdir(parents=True, exist_ok=True)
        
        for i in range(n_images):
            dummy_img = Image.fromarray(np.random.randint(0, 255, (375, 1242, 3), dtype=np.uint8))
            dummy_img.save(img_dir / f"{i:010d}.png")
        
        return tmpdir
    
    def test_loads_images_from_kitti_structure(self):
        """Test that images are loaded from KITTI directory structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.create_mock_kitti_structure(tmpdir, n_images=3)
            
            dataset = KITTIDataset(root_dir=tmpdir, split='train')
            
            # Should find images
            assert len(dataset) > 0, "No images loaded"
    
    def test_preprocessing_resize(self):
        """Test that images are resized to target resolution"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.create_mock_kitti_structure(tmpdir, n_images=1)
            
            target_res = (640, 640)
            dataset = KITTIDataset(
                root_dir=tmpdir,
                target_resolution=target_res
            )
            
            image, label = dataset[0]
            
            # Image should be [C, H, W]
            assert image.shape == (3, 640, 640), f"Expected (3, 640, 640), got {image.shape}"
    
    def test_imagenet_normalization(self):
        """Test that ImageNet normalization statistics are used"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.create_mock_kitti_structure(tmpdir, n_images=1)
            
            dataset = KITTIDataset(root_dir=tmpdir)
            
            expected_mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
            expected_std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
            
            assert torch.allclose(dataset.normalization_mean, expected_mean), \
                f"Mean mismatch: {dataset.normalization_mean.squeeze()} vs {expected_mean.squeeze()}"
            
            assert torch.allclose(dataset.normalization_std, expected_std), \
                f"Std mismatch: {dataset.normalization_std.squeeze()} vs {expected_std.squeeze()}"
    
    def test_preserves_original_resolution_metadata(self):
        """Test that original image resolution is preserved in metadata"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.create_mock_kitti_structure(tmpdir, n_images=1)
            
            dataset = KITTIDataset(
                root_dir=tmpdir,
                target_resolution=(640, 640)
            )
            
            image, label = dataset[0]
            
            # Check metadata includes original size
            assert 'original_size' in label, "Original size not preserved"
            assert label['original_size'] == (1242, 375), \
                f"Original size mismatch: {label['original_size']}"
    
    def test_preserves_color_channels(self):
        """Test that RGB color channels are preserved"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.create_mock_kitti_structure(tmpdir, n_images=1)
            
            dataset = KITTIDataset(root_dir=tmpdir)
            
            image, label = dataset[0]
            
            # Should have 3 color channels (RGB)
            assert image.shape[0] == 3, f"Expected 3 channels, got {image.shape[0]}"
    
    def test_label_structure(self):
        """Test that labels have correct structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.create_mock_kitti_structure(tmpdir, n_images=1)
            
            dataset = KITTIDataset(root_dir=tmpdir)
            
            image, label = dataset[0]
            
            # Check required label keys
            required_keys = [
                'is_misaligned',
                'misalignment_probability',
                'pose',
                'sample_id',
                'original_size',
                'augmentation_applied'
            ]
            
            for key in required_keys:
                assert key in label, f"Missing label key: {key}"
            
            # Check label types/values
            assert isinstance(label['is_misaligned'], (int, bool))
            assert isinstance(label['misalignment_probability'], float)
            assert isinstance(label['pose'], torch.Tensor)
            assert label['pose'].shape == (6,), "Pose should be 6-DOF"
            assert isinstance(label['sample_id'], str)
            assert isinstance(label['augmentation_applied'], dict)


class TestKITTIDatasetSplitting:
    """Test dataset splitting (70/15/15 ±2%)"""
    
    def test_split_ratios(self):
        """Test that dataset is split into 70/15/15 with ±2% tolerance"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create 100 images for testing
            img_dir = Path(tmpdir) / "2011_09_26" / "2011_09_26_drive_0001_sync" / "image_02" / "data"
            img_dir.mkdir(parents=True, exist_ok=True)
            
            for i in range(100):
                dummy_img = Image.fromarray(np.random.randint(0, 255, (375, 1242, 3), dtype=np.uint8))
                dummy_img.save(img_dir / f"{i:010d}.png")
            
            # Create datasets for each split
            train_dataset = KITTIDataset(root_dir=tmpdir, split='train')
            val_dataset = KITTIDataset(root_dir=tmpdir, split='val')
            test_dataset = KITTIDataset(root_dir=tmpdir, split='test')
            
            # Calculate percentages
            total = len(train_dataset) + len(val_dataset) + len(test_dataset)
            train_pct = len(train_dataset) / total * 100
            val_pct = len(val_dataset) / total * 100
            test_pct = len(test_dataset) / total * 100
            
            # Verify ratios within tolerance
            assert 68 <= train_pct <= 72, f"Train split {train_pct:.1f}% outside 70%±2%"
            assert 13 <= val_pct <= 17, f"Val split {val_pct:.1f}% outside 15%±2%"
            assert 13 <= test_pct <= 17, f"Test split {test_pct:.1f}% outside 15%±2%"
    
    def test_no_overlap_between_splits(self):
        """Test that train/val/test splits have no overlap"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create images
            img_dir = Path(tmpdir) / "2011_09_26" / "2011_09_26_drive_0001_sync" / "image_02" / "data"
            img_dir.mkdir(parents=True, exist_ok=True)
            
            for i in range(50):
                dummy_img = Image.fromarray(np.random.randint(0, 255, (375, 1242, 3), dtype=np.uint8))
                dummy_img.save(img_dir / f"{i:010d}.png")
            
            # Create datasets
            train_dataset = KITTIDataset(root_dir=tmpdir, split='train')
            val_dataset = KITTIDataset(root_dir=tmpdir, split='val')
            test_dataset = KITTIDataset(root_dir=tmpdir, split='test')
            
            # Get sample IDs from each split
            train_ids = set([train_dataset[i][1]['sample_id'] for i in range(len(train_dataset))])
            val_ids = set([val_dataset[i][1]['sample_id'] for i in range(len(val_dataset))])
            test_ids = set([test_dataset[i][1]['sample_id'] for i in range(len(test_dataset))])
            
            # Check no overlap
            assert len(train_ids & val_ids) == 0, "Train and val sets overlap"
            assert len(train_ids & test_ids) == 0, "Train and test sets overlap"
            assert len(val_ids & test_ids) == 0, "Val and test sets overlap"
    
    def test_split_reproducibility(self):
        """Test that split is deterministic (same random seed)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create images
            img_dir = Path(tmpdir) / "2011_09_26" / "2011_09_26_drive_0001_sync" / "image_02" / "data"
            img_dir.mkdir(parents=True, exist_ok=True)
            
            for i in range(30):
                dummy_img = Image.fromarray(np.random.randint(0, 255, (375, 1242, 3), dtype=np.uint8))
                dummy_img.save(img_dir / f"{i:010d}.png")
            
            # Create dataset twice
            dataset1 = KITTIDataset(root_dir=tmpdir, split='train')
            dataset2 = KITTIDataset(root_dir=tmpdir, split='train')
            
            # Should have same samples
            ids1 = [dataset1[i][1]['sample_id'] for i in range(len(dataset1))]
            ids2 = [dataset2[i][1]['sample_id'] for i in range(len(dataset2))]
            
            assert ids1 == ids2, "Split not reproducible"


class TestDataLoaderCreation:
    """Test DataLoader creation and batching"""
    
    def test_create_dataloaders_function_exists(self):
        """Test that create_dataloaders function is available"""
        assert callable(create_dataloaders), "create_dataloaders must be callable"
    
    def test_create_dataloaders_signature(self):
        """Test that create_dataloaders has correct parameters"""
        import inspect
        sig = inspect.signature(create_dataloaders)
        
        expected_params = ['root_dir', 'batch_size', 'target_resolution', 'num_workers']
        for param in expected_params:
            assert param in sig.parameters, f"Missing parameter: {param}"
    
    def test_create_dataloaders_returns_three_loaders(self):
        """Test that create_dataloaders returns train, val, test loaders"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal dataset
            img_dir = Path(tmpdir) / "2011_09_26" / "2011_09_26_drive_0001_sync" / "image_02" / "data"
            img_dir.mkdir(parents=True, exist_ok=True)
            
            for i in range(20):
                dummy_img = Image.fromarray(np.random.randint(0, 255, (375, 1242, 3), dtype=np.uint8))
                dummy_img.save(img_dir / f"{i:010d}.png")
            
            # Create dataloaders
            train_loader, val_loader, test_loader = create_dataloaders(
                root_dir=tmpdir,
                batch_size=2,
                target_resolution=(320, 320),
                num_workers=0  # Use 0 for testing to avoid multiprocessing issues
            )
            
            # Verify loaders exist
            assert train_loader is not None
            assert val_loader is not None
            assert test_loader is not None
            
            # Verify they're DataLoaders
            from torch.utils.data import DataLoader
            assert isinstance(train_loader, DataLoader)
            assert isinstance(val_loader, DataLoader)
            assert isinstance(test_loader, DataLoader)
    
    def test_dataloader_batching(self):
        """Test that DataLoader creates correct batch sizes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal dataset
            img_dir = Path(tmpdir) / "2011_09_26" / "2011_09_26_drive_0001_sync" / "image_02" / "data"
            img_dir.mkdir(parents=True, exist_ok=True)
            
            for i in range(20):
                dummy_img = Image.fromarray(np.random.randint(0, 255, (375, 1242, 3), dtype=np.uint8))
                dummy_img.save(img_dir / f"{i:010d}.png")
            
            # Create dataloaders with batch size 4
            train_loader, _, _ = create_dataloaders(
                root_dir=tmpdir,
                batch_size=4,
                target_resolution=(320, 320),
                num_workers=0
            )
            
            # Get a batch
            images, labels = next(iter(train_loader))
            
            # Verify batch shape
            # Should be [batch_size, channels, height, width]
            assert images.shape[0] <= 4, f"Batch size too large: {images.shape[0]}"
            assert images.shape[1] == 3, f"Wrong number of channels: {images.shape[1]}"
            assert images.shape[2] == 320, f"Wrong height: {images.shape[2]}"
            assert images.shape[3] == 320, f"Wrong width: {images.shape[3]}"


class TestKITTIDatasetErrorHandling:
    """Test error handling for various edge cases"""
    
    def test_missing_directory_error(self):
        """Test error when KITTI directory doesn't exist"""
        with pytest.raises(FileNotFoundError, match="KITTI dataset not found"):
            dataset = KITTIDataset(root_dir="/nonexistent/path")
    
    def test_empty_directory_warning(self):
        """Test handling of empty KITTI directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create structure but no images
            img_dir = Path(tmpdir) / "2011_09_26" / "2011_09_26_drive_0001_sync" / "image_02" / "data"
            img_dir.mkdir(parents=True, exist_ok=True)
            
            # Should create dataset but with 0 samples
            dataset = KITTIDataset(root_dir=tmpdir)
            assert len(dataset) == 0


class TestRequirementsCompliance:
    """Test compliance with Requirements 5.1, 5.7, 1.1 from spec"""
    
    def test_requirement_5_1_stereo_image_loading(self):
        """
        Requirement 5.1: THE Training_Pipeline SHALL load stereo image pairs from KITTI_Dataset
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create both left (image_02) and right (image_03) cameras
            left_dir = Path(tmpdir) / "2011_09_26" / "2011_09_26_drive_0001_sync" / "image_02" / "data"
            right_dir = Path(tmpdir) / "2011_09_26" / "2011_09_26_drive_0001_sync" / "image_03" / "data"
            left_dir.mkdir(parents=True, exist_ok=True)
            right_dir.mkdir(parents=True, exist_ok=True)
            
            # Create images
            for i in range(3):
                dummy_img = Image.fromarray(np.random.randint(0, 255, (375, 1242, 3), dtype=np.uint8))
                dummy_img.save(left_dir / f"{i:010d}.png")
                dummy_img.save(right_dir / f"{i:010d}.png")
            
            # Test left camera
            dataset_left = KITTIDataset(root_dir=tmpdir, use_left_camera=True)
            assert len(dataset_left) > 0, "Left camera images not loaded"
            
            # Test right camera
            dataset_right = KITTIDataset(root_dir=tmpdir, use_left_camera=False)
            assert len(dataset_right) > 0, "Right camera images not loaded"
    
    def test_requirement_5_7_preserve_color_channels(self):
        """
        Requirement 5.7: THE Training_Pipeline SHALL preserve original image resolution and color channels
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            img_dir = Path(tmpdir) / "2011_09_26" / "2011_09_26_drive_0001_sync" / "image_02" / "data"
            img_dir.mkdir(parents=True, exist_ok=True)
            
            # Create RGB image
            dummy_img = Image.fromarray(np.random.randint(0, 255, (375, 1242, 3), dtype=np.uint8))
            dummy_img.save(img_dir / "0000000000.png")
            
            dataset = KITTIDataset(root_dir=tmpdir)
            image, label = dataset[0]
            
            # Verify 3 color channels preserved
            assert image.shape[0] == 3, "Color channels not preserved"
            
            # Verify original resolution in metadata
            assert 'original_size' in label, "Original resolution not preserved"
            assert label['original_size'] == (1242, 375), "Original resolution metadata incorrect"
    
    def test_requirement_1_1_input_resolution_range(self):
        """
        Requirement 1.1: THE CNN_Feature_Extractor SHALL accept input images 
        with dimensions between 256x256 and 1024x1024 pixels
        
        However, design constrains to ≤750×750 for memory efficiency.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            img_dir = Path(tmpdir) / "2011_09_26" / "2011_09_26_drive_0001_sync" / "image_02" / "data"
            img_dir.mkdir(parents=True, exist_ok=True)
            
            dummy_img = Image.fromarray(np.random.randint(0, 255, (375, 1242, 3), dtype=np.uint8))
            dummy_img.save(img_dir / "0000000000.png")
            
            # Test various resolutions within range
            valid_resolutions = [
                (256, 256),  # Minimum
                (640, 640),  # Common
                (750, 750),  # Maximum (constrained by design)
            ]
            
            for res in valid_resolutions:
                dataset = KITTIDataset(root_dir=tmpdir, target_resolution=res)
                image, label = dataset[0]
                assert image.shape == (3, res[0], res[1]), \
                    f"Resolution {res} not handled correctly"
