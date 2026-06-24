"""
Unit tests for KITTI Data Loader Module

Tests KITTI dataset loading and integration with pipeline
"""

import pytest
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.data.kitti_loader import (
    KITTIDataLoader,
    KITTISample,
    KITTIConfig,
    KITTIPointCloudLoader,
    create_mock_kitti_sample,
    DATASETS_AVAILABLE,
    OPEN3D_AVAILABLE
)


class TestKITTIConfig:
    """Test KITTIConfig dataclass"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = KITTIConfig()
        
        assert config.dataset_name == "galilai-group/kitti-stereo2012"
        assert config.streaming is True
        assert config.split == "train"
        assert config.max_samples is None
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = KITTIConfig(
            dataset_name="custom/dataset",
            streaming=False,
            split="test",
            max_samples=100
        )
        
        assert config.dataset_name == "custom/dataset"
        assert config.streaming is False
        assert config.split == "test"
        assert config.max_samples == 100
    
    def test_invalid_split(self):
        """Test error on invalid split"""
        with pytest.raises(ValueError, match="Invalid split"):
            KITTIConfig(split="invalid")


class TestKITTISample:
    """Test KITTISample dataclass"""
    
    def test_valid_sample(self):
        """Test creating valid sample"""
        image_left = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        sample = KITTISample(
            sample_id="test_001",
            image_left=image_left,
            image_right=None,
            disparity_map=None,
            timestamp=datetime.now(),
            metadata={}
        )
        
        assert sample.sample_id == "test_001"
        assert sample.image_left.shape == (480, 640, 3)
        assert sample.image_right is None

    
    def test_sample_with_stereo(self):
        """Test sample with stereo images"""
        image_left = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        image_right = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        sample = KITTISample(
            sample_id="test_002",
            image_left=image_left,
            image_right=image_right,
            disparity_map=None,
            timestamp=datetime.now(),
            metadata={'stereo': True}
        )
        
        assert sample.image_right is not None
        assert sample.image_right.shape == (480, 640, 3)
        assert sample.metadata['stereo'] is True
    
    def test_sample_with_disparity(self):
        """Test sample with disparity map"""
        image_left = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        disparity = np.random.rand(480, 640).astype(np.float32) * 50
        
        sample = KITTISample(
            sample_id="test_003",
            image_left=image_left,
            image_right=None,
            disparity_map=disparity,
            timestamp=datetime.now(),
            metadata={}
        )
        
        assert sample.disparity_map is not None
        assert sample.disparity_map.shape == (480, 640)
    
    def test_invalid_sample_no_image(self):
        """Test error when image_left is None"""
        with pytest.raises(ValueError, match="image_left cannot be None"):
            KITTISample(
                sample_id="test_004",
                image_left=None,
                image_right=None,
                disparity_map=None,
                timestamp=datetime.now(),
                metadata={}
            )
    
    def test_invalid_sample_wrong_dims(self):
        """Test error when image has wrong dimensions"""
        image_1d = np.array([1, 2, 3])
        
        with pytest.raises(ValueError, match="must be 2D or 3D"):
            KITTISample(
                sample_id="test_005",
                image_left=image_1d,
                image_right=None,
                disparity_map=None,
                timestamp=datetime.now(),
                metadata={}
            )


@pytest.mark.skipif(not DATASETS_AVAILABLE, reason="datasets library not installed")
class TestKITTIDataLoader:
    """Test KITTIDataLoader (requires datasets library)"""
    
    def test_init_with_default_config(self):
        """Test initialization with default config"""
        loader = KITTIDataLoader()
        
        assert loader.config.dataset_name == "galilai-group/kitti-stereo2012"
        assert loader.config.streaming is True
        assert loader._sample_count == 0
    
    def test_init_with_custom_config(self):
        """Test initialization with custom config"""
        config = KITTIConfig(max_samples=10)
        loader = KITTIDataLoader(config)
        
        assert loader.config.max_samples == 10
    
    @patch('src.data.kitti_loader.load_dataset')
    def test_initialize(self, mock_load_dataset):
        """Test dataset initialization"""
        # Mock dataset response
        mock_dataset = {
            'train': [{'image_left': np.zeros((10, 10, 3))}]
        }
        mock_load_dataset.return_value = mock_dataset
        
        loader = KITTIDataLoader()
        loader.initialize()
        
        mock_load_dataset.assert_called_once()
        assert loader._dataset is not None

    
    @patch('src.data.kitti_loader.load_dataset')
    def test_initialize_invalid_split(self, mock_load_dataset):
        """Test error when split doesn't exist"""
        mock_dataset = {'train': []}
        mock_load_dataset.return_value = mock_dataset
        
        config = KITTIConfig(split="invalid_split")
        loader = KITTIDataLoader(config)
        
        with pytest.raises(ValueError, match="Split 'invalid_split' not found"):
            loader.initialize()
    
    @patch('src.data.kitti_loader.load_dataset')
    def test_get_next_sample_without_initialize(self, mock_load_dataset):
        """Test error when calling get_next_sample before initialize"""
        loader = KITTIDataLoader()
        
        with pytest.raises(RuntimeError, match="Call initialize"):
            loader.get_next_sample()
    
    @patch('src.data.kitti_loader.load_dataset')
    def test_get_next_sample(self, mock_load_dataset):
        """Test getting next sample"""
        # Create mock image
        mock_image = MagicMock()
        mock_image.convert = Mock(return_value=MagicMock())
        mock_image.convert.return_value = Mock()
        
        # Mock the conversion to numpy
        with patch('numpy.array') as mock_array:
            mock_array.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
            
            mock_sample = {
                'image_left': mock_image,
                'id': 'sample_001'
            }
            
            mock_dataset = {
                'train': iter([mock_sample])
            }
            mock_load_dataset.return_value = mock_dataset
            
            loader = KITTIDataLoader()
            loader.initialize()
            
            sample = loader.get_next_sample()
            
            assert sample is not None
            assert sample.sample_id == 'sample_001'
    
    @patch('src.data.kitti_loader.load_dataset')
    def test_get_next_sample_max_samples(self, mock_load_dataset):
        """Test max_samples limit"""
        mock_samples = [
            {'image_left': np.zeros((10, 10, 3)), 'id': f'sample_{i:03d}'}
            for i in range(5)
        ]
        
        mock_dataset = {
            'train': iter(mock_samples)
        }
        mock_load_dataset.return_value = mock_dataset
        
        config = KITTIConfig(max_samples=2)
        loader = KITTIDataLoader(config)
        loader.initialize()
        
        # Should get 2 samples
        sample1 = loader.get_next_sample()
        sample2 = loader.get_next_sample()
        sample3 = loader.get_next_sample()  # Should be None
        
        assert sample1 is not None
        assert sample2 is not None
        assert sample3 is None
    
    @patch('src.data.kitti_loader.load_dataset')
    def test_get_sample_iterator(self, mock_load_dataset):
        """Test sample iterator"""
        mock_samples = [
            {'image_left': np.zeros((10, 10, 3)), 'id': f'sample_{i:03d}'}
            for i in range(3)
        ]
        
        mock_dataset = {
            'train': iter(mock_samples)
        }
        mock_load_dataset.return_value = mock_dataset
        
        loader = KITTIDataLoader()
        loader.initialize()
        
        samples = list(loader.get_sample_iterator())
        
        assert len(samples) == 3
        assert all(isinstance(s, KITTISample) for s in samples)
    
    def test_get_statistics(self):
        """Test getting loader statistics"""
        config = KITTIConfig(max_samples=100)
        loader = KITTIDataLoader(config)
        loader._sample_count = 42
        
        stats = loader.get_statistics()
        
        assert stats['samples_loaded'] == 42
        assert stats['max_samples'] == 100
    
    @patch('src.data.kitti_loader.load_dataset')
    def test_reset(self, mock_load_dataset):
        """Test resetting loader"""
        mock_dataset = {
            'train': iter([{'image_left': np.zeros((10, 10, 3))}])
        }
        mock_load_dataset.return_value = mock_dataset
        
        loader = KITTIDataLoader()
        loader.initialize()
        loader._sample_count = 10
        
        loader.reset()
        
        assert loader._sample_count == 0



class TestKITTIDataLoaderWithoutDependency:
    """Test KITTIDataLoader behavior when datasets not installed"""
    
    @patch('src.data.kitti_loader.DATASETS_AVAILABLE', False)
    def test_init_without_datasets(self):
        """Test error when datasets library not available"""
        with pytest.raises(RuntimeError, match="datasets library not available"):
            KITTIDataLoader()


@pytest.mark.skipif(not OPEN3D_AVAILABLE, reason="Open3D not installed")
class TestKITTIPointCloudLoader:
    """Test KITTIPointCloudLoader (requires Open3D)"""
    
    def test_load_point_cloud(self, tmp_path):
        """Test loading point cloud from binary file"""
        # Create mock binary point cloud file
        points = np.random.rand(100, 4).astype(np.float32)
        bin_file = tmp_path / "test_cloud.bin"
        points.tofile(bin_file)
        
        pcd = KITTIPointCloudLoader.load_point_cloud(str(bin_file))
        
        assert pcd is not None
        loaded_points = np.asarray(pcd.points)
        assert loaded_points.shape == (100, 3)  # x, y, z (reflectance excluded)
    
    def test_load_point_cloud_file_not_found(self):
        """Test error when file doesn't exist"""
        with pytest.raises(FileNotFoundError):
            KITTIPointCloudLoader.load_point_cloud("nonexistent.bin")
    
    def test_compute_scene_flow(self):
        """Test computing scene flow between frames"""
        # Create mock point clouds
        points1 = np.random.rand(100, 3).astype(np.float32)
        points2 = np.random.rand(100, 3).astype(np.float32)
        
        import open3d as o3d
        pcd1 = o3d.geometry.PointCloud()
        pcd1.points = o3d.utility.Vector3dVector(points1)
        
        pcd2 = o3d.geometry.PointCloud()
        pcd2.points = o3d.utility.Vector3dVector(points2)
        
        flow = KITTIPointCloudLoader.compute_scene_flow(pcd1, pcd2)
        
        assert flow is not None
        assert flow.shape == (100, 3)


class TestKITTIPointCloudLoaderWithoutDependency:
    """Test KITTIPointCloudLoader behavior when Open3D not installed"""
    
    @patch('src.data.kitti_loader.OPEN3D_AVAILABLE', False)
    def test_load_without_open3d(self):
        """Test error when Open3D not available"""
        with pytest.raises(RuntimeError, match="Open3D not available"):
            KITTIPointCloudLoader.load_point_cloud("test.bin")
    
    @patch('src.data.kitti_loader.OPEN3D_AVAILABLE', False)
    def test_compute_flow_without_open3d(self):
        """Test error when Open3D not available"""
        with pytest.raises(RuntimeError, match="Open3D not available"):
            KITTIPointCloudLoader.compute_scene_flow(None, None)


class TestCreateMockKITTISample:
    """Test mock KITTI sample creation"""
    
    def test_create_default_mock(self):
        """Test creating mock sample with default parameters"""
        sample = create_mock_kitti_sample()
        
        assert isinstance(sample, KITTISample)
        assert sample.image_left.shape == (480, 640, 3)
        assert sample.image_right.shape == (480, 640, 3)
        assert sample.disparity_map.shape == (480, 640)
        assert sample.sample_id == "mock_000000"
        assert sample.metadata['mock'] is True
    
    def test_create_custom_size_mock(self):
        """Test creating mock sample with custom size"""
        sample = create_mock_kitti_sample(
            width=1024,
            height=768,
            sample_id="custom_mock"
        )
        
        assert sample.image_left.shape == (768, 1024, 3)
        assert sample.image_right.shape == (768, 1024, 3)
        assert sample.disparity_map.shape == (768, 1024)
        assert sample.sample_id == "custom_mock"
    
    def test_mock_images_are_valid(self):
        """Test that mock images have valid pixel values"""
        sample = create_mock_kitti_sample()
        
        # Check left image
        assert sample.image_left.dtype == np.uint8
        assert sample.image_left.min() >= 0
        assert sample.image_left.max() <= 255
        
        # Check right image
        assert sample.image_right.dtype == np.uint8
        assert sample.image_right.min() >= 0
        assert sample.image_right.max() <= 255
    
    def test_mock_disparity_is_valid(self):
        """Test that mock disparity has valid values"""
        sample = create_mock_kitti_sample()
        
        assert sample.disparity_map.dtype == np.float32
        assert sample.disparity_map.min() >= 0
        assert sample.disparity_map.max() <= 50
    
    def test_multiple_mocks_are_different(self):
        """Test that multiple mock samples are different"""
        sample1 = create_mock_kitti_sample()
        sample2 = create_mock_kitti_sample()
        
        # Images should be different (random)
        assert not np.array_equal(sample1.image_left, sample2.image_left)
