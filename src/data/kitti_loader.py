"""
KITTI Dataset Loader

Loads KITTI Stereo/Flow benchmark data for testing camera misalignment detection.

Features:
- Streaming dataset loading (no disk filling)
- Stereo image pair loading
- Point cloud frame loading (LiDAR)
- Integration with pipeline components
"""

from dataclasses import dataclass
from typing import Iterator, Optional, Tuple, Dict, Any
import numpy as np
from datetime import datetime

try:
    from datasets import load_dataset
    from PIL import Image
    DATASETS_AVAILABLE = True
except ImportError:
    DATASETS_AVAILABLE = False

try:
    import open3d as o3d
    OPEN3D_AVAILABLE = True
except ImportError:
    OPEN3D_AVAILABLE = False


@dataclass
class KITTIConfig:
    """Configuration for KITTI data loading"""
    dataset_name: str = "galilai-group/kitti-stereo2012"
    streaming: bool = True
    split: str = "train"
    max_samples: Optional[int] = None  # None = load all
    
    def __post_init__(self):
        """Validate configuration"""
        if self.split not in ["train", "test", "validation"]:
            raise ValueError(f"Invalid split: {self.split}")


@dataclass
class KITTISample:
    """
    Single KITTI data sample
    
    Contains stereo images and metadata for one frame
    """
    sample_id: str
    image_left: np.ndarray  # Left camera image
    image_right: Optional[np.ndarray]  # Right camera image (if available)
    disparity_map: Optional[np.ndarray]  # Disparity (if available)
    timestamp: datetime
    metadata: Dict[str, Any]
    
    def __post_init__(self):
        """Validate sample data"""
        if self.image_left is None:
            raise ValueError("image_left cannot be None")
        
        if self.image_left.ndim not in [2, 3]:
            raise ValueError(f"image_left must be 2D or 3D, got {self.image_left.ndim}D")


class KITTIDataLoader:

    """
    KITTI Dataset Loader
    
    Loads KITTI Stereo/Flow benchmark data in streaming mode
    """
    
    def __init__(self, config: Optional[KITTIConfig] = None):
        """
        Initialize KITTI data loader
        
        Args:
            config: Loader configuration (uses defaults if None)
        
        Raises:
            RuntimeError: If datasets library not available
        """
        if not DATASETS_AVAILABLE:
            raise RuntimeError(
                "datasets library not available. "
                "Install with: pip install datasets pillow"
            )
        
        self.config = config or KITTIConfig()
        self._dataset = None
        self._iterator = None
        self._sample_count = 0
    
    def initialize(self):
        """
        Initialize dataset connection
        
        Loads dataset in streaming mode (doesn't fill disk)
        """
        self._dataset = load_dataset(
            self.config.dataset_name,
            streaming=self.config.streaming
        )
        
        # Get the requested split
        if self.config.split not in self._dataset:
            available = list(self._dataset.keys())
            raise ValueError(
                f"Split '{self.config.split}' not found. "
                f"Available: {available}"
            )
        
        self._iterator = iter(self._dataset[self.config.split])
        self._sample_count = 0
    
    def get_next_sample(self) -> Optional[KITTISample]:
        """
        Get next sample from dataset
        
        Returns:
            KITTISample or None if no more samples
        """
        if self._iterator is None:
            raise RuntimeError("Call initialize() before get_next_sample()")
        
        # Check if we've reached max_samples
        if (self.config.max_samples is not None and 
            self._sample_count >= self.config.max_samples):
            return None
        
        try:
            raw_sample = next(self._iterator)
            self._sample_count += 1
            
            return self._convert_to_kitti_sample(raw_sample)
        
        except StopIteration:
            return None

    
    def get_sample_iterator(self) -> Iterator[KITTISample]:
        """
        Get iterator over all samples
        
        Yields:
            KITTISample objects
        """
        if self._iterator is None:
            self.initialize()
        
        while True:
            sample = self.get_next_sample()
            if sample is None:
                break
            yield sample
    
    def _convert_to_kitti_sample(self, raw_sample: Dict) -> KITTISample:
        """
        Convert raw dataset sample to KITTISample
        
        Args:
            raw_sample: Raw sample from datasets library
        
        Returns:
            Converted KITTISample
        """
        # Extract image_left (required)
        image_left = self._extract_image(raw_sample, 'image_left', 'image_0')
        
        # Extract image_right (optional)
        image_right = self._extract_image(raw_sample, 'image_right', 'image_1')
        
        # Extract disparity map (optional)
        disparity_map = self._extract_disparity(raw_sample)
        
        # Generate sample ID
        sample_id = raw_sample.get('id', f"sample_{self._sample_count:06d}")
        
        # Extract metadata
        metadata = {
            key: value for key, value in raw_sample.items()
            if key not in ['image_left', 'image_right', 'image_0', 
                          'image_1', 'disparity_map', 'disparity']
        }
        
        return KITTISample(
            sample_id=sample_id,
            image_left=image_left,
            image_right=image_right,
            disparity_map=disparity_map,
            timestamp=datetime.now(),  # Use current time for now
            metadata=metadata
        )
    
    def _extract_image(self, raw_sample: Dict, *keys) -> Optional[np.ndarray]:
        """
        Extract image from raw sample using multiple possible keys
        
        Args:
            raw_sample: Raw sample dict
            *keys: Possible keys to try
        
        Returns:
            Image as numpy array or None
        """
        for key in keys:
            if key in raw_sample:
                img = raw_sample[key]
                
                # Convert PIL Image to numpy if needed
                if hasattr(img, 'convert'):  # PIL Image
                    img = np.array(img.convert('RGB'))
                
                return img
        
        return None

    
    def _extract_disparity(self, raw_sample: Dict) -> Optional[np.ndarray]:
        """
        Extract disparity map from raw sample
        
        Args:
            raw_sample: Raw sample dict
        
        Returns:
            Disparity map as numpy array or None
        """
        for key in ['disparity_map', 'disparity', 'disp']:
            if key in raw_sample:
                disp = raw_sample[key]
                
                # Convert PIL Image to numpy if needed
                if hasattr(disp, 'convert'):  # PIL Image
                    disp = np.array(disp)
                
                return disp
        
        return None
    
    def get_statistics(self) -> Dict[str, int]:
        """Get loader statistics"""
        return {
            'samples_loaded': self._sample_count,
            'max_samples': self.config.max_samples or -1
        }
    
    def reset(self):
        """Reset iterator to beginning"""
        self._iterator = None
        self._sample_count = 0
        if self._dataset is not None:
            self._iterator = iter(self._dataset[self.config.split])


class KITTIPointCloudLoader:
    """
    Load KITTI LiDAR point cloud frames
    
    Reads raw binary point clouds from KITTI format
    """
    
    @staticmethod
    def load_point_cloud(velo_bin_path: str) -> Optional['o3d.geometry.PointCloud']:
        """
        Load KITTI point cloud from binary file
        
        Args:
            velo_bin_path: Path to .bin file
        
        Returns:
            Open3D point cloud or None if Open3D not available
        
        Raises:
            RuntimeError: If Open3D not available
            FileNotFoundError: If file doesn't exist
        """
        if not OPEN3D_AVAILABLE:
            raise RuntimeError(
                "Open3D not available. "
                "Install with: pip install open3d"
            )
        
        # KITTI LiDAR: float32 arrays [x, y, z, reflectance]
        scan = np.fromfile(velo_bin_path, dtype=np.float32).reshape(-1, 4)
        points = scan[:, :3]  # Extract 3D spatial points
        
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        
        return pcd
    
    @staticmethod
    def compute_scene_flow(
        frame_t: 'o3d.geometry.PointCloud',
        frame_t1: 'o3d.geometry.PointCloud'
    ) -> np.ndarray:
        """
        Compute 3D scene flow between consecutive frames
        
        Args:
            frame_t: Point cloud at time t
            frame_t1: Point cloud at time t+1
        
        Returns:
            Flow vectors (Nx3 array)
        """
        if not OPEN3D_AVAILABLE:
            raise RuntimeError("Open3D not available")
        
        # Simple nearest-neighbor flow estimation
        # (In production, use proper scene flow algorithm)
        points_t = np.asarray(frame_t.points)
        points_t1 = np.asarray(frame_t1.points)
        
        # For now, return zero flow (placeholder)
        # Real implementation would use ICP or scene flow algorithms
        return np.zeros_like(points_t)


def create_mock_kitti_sample(
    width: int = 640,
    height: int = 480,
    sample_id: str = "mock_000000"
) -> KITTISample:
    """
    Create mock KITTI sample for testing
    
    Args:
        width: Image width
        height: Image height
        sample_id: Sample identifier
    
    Returns:
        Mock KITTISample
    """
    # Create mock stereo images
    image_left = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    image_right = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    
    # Create mock disparity map
    disparity_map = np.random.rand(height, width).astype(np.float32) * 50
    
    return KITTISample(
        sample_id=sample_id,
        image_left=image_left,
        image_right=image_right,
        disparity_map=disparity_map,
        timestamp=datetime.now(),
        metadata={'mock': True}
    )
