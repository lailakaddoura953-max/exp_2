"""
Image Preprocessing Pipeline for Inference

This module handles preprocessing of raw camera images before feeding them
to the neural network for inference.

Key Operations:
1. Resize to target resolution (≤750×750 pixels)
2. Normalize using ImageNet statistics
3. Form batches for 4-camera processing
4. Validate input dimensions

Task 11.1: Preprocessing and Batch Formation
Requirements: 9.1, 22.1
"""

import logging
from typing import List, Tuple, Optional, Union
import numpy as np

try:
    import torch
    import torchvision.transforms.functional as TF
    from PIL import Image
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    TF = None
    Image = None

logger = logging.getLogger(__name__)


# ==============================================================================
# Constants
# ==============================================================================

# Maximum allowed resolution (memory constraint)
MAX_RESOLUTION = 750

# Default ImageNet normalization statistics
DEFAULT_MEAN = [0.485, 0.456, 0.406]
DEFAULT_STD = [0.229, 0.224, 0.225]


# ==============================================================================
# Task 11.1: Image Preprocessing Pipeline
# ==============================================================================

class ImagePreprocessor:
    """
    Preprocesses camera images for neural network inference.
    
    What does preprocessing do?
    1. Resize: Scale images to target resolution (e.g., 640×640)
    2. Normalize: Standardize pixel values using mean/std statistics
    3. Convert: Transform to PyTorch tensor format
    
    Why normalize?
    - Neural networks train on normalized data
    - ImageNet statistics are standard for CNN models
    - Normalization improves training stability and accuracy
    
    Why resize?
    - Consistent input size for neural network
    - Balance between detail and computational cost
    - Memory constraints (≤750×750 pixels)
    
    Requirements: 9.1, 22.1
    """
    
    def __init__(
        self,
        target_resolution: Tuple[int, int] = (640, 640),
        normalization_mean: List[float] = None,
        normalization_std: List[float] = None,
        device: str = 'cuda'
    ):
        """
        Initialize preprocessor.
        
        Args:
            target_resolution: Target (height, width) in pixels
            normalization_mean: RGB mean values for normalization
            normalization_std: RGB std values for normalization
            device: 'cuda' or 'cpu'
        
        Raises:
            ValueError: If target_resolution exceeds maximum (750×750)
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch required for preprocessing")
        
        # Validate resolution constraint
        height, width = target_resolution
        if height > MAX_RESOLUTION or width > MAX_RESOLUTION:
            raise ValueError(
                f"Target resolution {target_resolution} exceeds maximum "
                f"allowed resolution {MAX_RESOLUTION}×{MAX_RESOLUTION}"
            )
        
        self.target_resolution = target_resolution
        self.device = device
        
        # Use ImageNet defaults if not specified
        self.mean = normalization_mean or DEFAULT_MEAN
        self.std = normalization_std or DEFAULT_STD
        
        # Convert to tensors for GPU operations
        self.mean_tensor = torch.tensor(self.mean, device=device).view(3, 1, 1)
        self.std_tensor = torch.tensor(self.std, device=device).view(3, 1, 1)
        
        logger.info(
            f"ImagePreprocessor initialized: "
            f"resolution={target_resolution}, device={device}"
        )
    
    def preprocess_image(
        self,
        image: Union[np.ndarray, Image.Image, torch.Tensor]
    ) -> torch.Tensor:
        """
        Preprocess single image.
        
        Args:
            image: Input image as numpy array [H,W,C], PIL Image, or tensor
        
        Returns:
            Preprocessed tensor [1, 3, H, W] on target device
        
        Requirements: 9.1
        
        Example:
            >>> preprocessor = ImagePreprocessor(target_resolution=(640, 640))
            >>> image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            >>> tensor = preprocessor.preprocess_image(image)
            >>> tensor.shape
            torch.Size([1, 3, 640, 640])
        """
        # ======================================================================
        # Step 1: Convert to PIL Image for standardized processing
        # ======================================================================
        if isinstance(image, np.ndarray):
            # NumPy array: [H, W, C] with values 0-255
            image = Image.fromarray(image)
        elif isinstance(image, torch.Tensor):
            # Tensor: convert to numpy then PIL
            if image.dim() == 3:
                # [C, H, W] → [H, W, C]
                image = image.permute(1, 2, 0).cpu().numpy()
            else:
                # [H, W, C]
                image = image.cpu().numpy()
            
            # Convert to uint8 if needed
            if image.dtype != np.uint8:
                image = (image * 255).astype(np.uint8)
            
            image = Image.fromarray(image)
        
        # ======================================================================
        # Step 2: Resize to target resolution
        # ======================================================================
        image = TF.resize(image, self.target_resolution)
        
        # ======================================================================
        # Step 3: Convert to tensor [C, H, W] with values [0, 1]
        # ======================================================================
        tensor = TF.to_tensor(image)  # Converts to [C, H, W] and normalizes to [0, 1]
        
        # ======================================================================
        # Step 4: Normalize using mean and std
        # ======================================================================
        tensor = tensor.to(self.device)
        tensor = (tensor - self.mean_tensor) / self.std_tensor
        
        # ======================================================================
        # Step 5: Add batch dimension
        # ======================================================================
        tensor = tensor.unsqueeze(0)  # [C, H, W] → [1, C, H, W]
        
        return tensor
    
    def preprocess_batch(
        self,
        images: List[Union[np.ndarray, Image.Image, torch.Tensor]]
    ) -> torch.Tensor:
        """
        Preprocess batch of images.
        
        Args:
            images: List of images (numpy arrays, PIL Images, or tensors)
        
        Returns:
            Batched tensor [B, 3, H, W] on target device
        
        Requirements: 22.1
        
        Example:
            >>> preprocessor = ImagePreprocessor(target_resolution=(640, 640))
            >>> images = [np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8) 
            ...           for _ in range(4)]
            >>> batch = preprocessor.preprocess_batch(images)
            >>> batch.shape
            torch.Size([4, 3, 640, 640])
        """
        # Preprocess each image individually
        tensors = [self.preprocess_image(img) for img in images]
        
        # Concatenate into batch
        batch = torch.cat(tensors, dim=0)  # [B, 3, H, W]
        
        return batch
    
    def validate_input_dimensions(
        self,
        image: Union[np.ndarray, Image.Image, torch.Tensor]
    ) -> Tuple[int, int]:
        """
        Validate input image dimensions.
        
        Args:
            image: Input image
        
        Returns:
            Tuple of (height, width)
        
        Raises:
            ValueError: If dimensions are invalid
        """
        if isinstance(image, np.ndarray):
            if image.ndim != 3:
                raise ValueError(f"Expected 3D numpy array, got shape {image.shape}")
            height, width, channels = image.shape
            if channels != 3:
                raise ValueError(f"Expected 3 channels (RGB), got {channels}")
        
        elif isinstance(image, Image.Image):
            width, height = image.size
        
        elif isinstance(image, torch.Tensor):
            if image.dim() == 3:
                channels, height, width = image.shape
            elif image.dim() == 2:
                raise ValueError("Expected color image, got grayscale")
            else:
                raise ValueError(f"Expected 2D or 3D tensor, got {image.dim()}D")
            
            if channels != 3:
                raise ValueError(f"Expected 3 channels (RGB), got {channels}")
        
        else:
            raise TypeError(
                f"Unsupported image type: {type(image)}. "
                "Expected numpy array, PIL Image, or torch Tensor"
            )
        
        return height, width


# ==============================================================================
# Task 11.1: Four-Camera Batch Formation
# ==============================================================================

class FourCameraBatchBuilder:
    """
    Forms batches for 4-camera inference.
    
    What is a 4-camera batch?
    - Synchronized frames from 4 vehicle-mounted cameras
    - Processed as single tensor [4, 3, H, W]
    - More efficient than processing cameras sequentially
    
    Why batch processing?
    - GPU parallelism: process all 4 cameras simultaneously
    - Reduced overhead: single inference call instead of 4
    - Better GPU utilization: keeps GPU busy with work
    - Faster: ~1.5× single-camera time vs 4× for sequential
    
    Requirements: 22.1
    """
    
    def __init__(
        self,
        preprocessor: ImagePreprocessor,
        camera_ids: List[str] = None
    ):
        """
        Initialize batch builder.
        
        Args:
            preprocessor: ImagePreprocessor instance
            camera_ids: List of camera identifiers (default: ['front', 'left', 'right', 'rear'])
        """
        self.preprocessor = preprocessor
        self.camera_ids = camera_ids or ['front', 'left', 'right', 'rear']
        
        if len(self.camera_ids) != 4:
            raise ValueError(f"Expected 4 cameras, got {len(self.camera_ids)}")
        
        logger.info(f"FourCameraBatchBuilder initialized: cameras={self.camera_ids}")
    
    def build_batch(
        self,
        camera_frames: dict
    ) -> Tuple[torch.Tensor, List[str]]:
        """
        Build 4-camera batch from camera frames.
        
        Args:
            camera_frames: Dictionary mapping camera_id → image
                          Example: {'front': img1, 'left': img2, ...}
        
        Returns:
            Tuple of (batch_tensor, camera_order):
            - batch_tensor: [4, 3, H, W] tensor
            - camera_order: List of camera IDs in batch order
        
        Raises:
            ValueError: If not exactly 4 cameras provided
        
        Requirements: 22.1
        
        Example:
            >>> preprocessor = ImagePreprocessor(target_resolution=(640, 640))
            >>> builder = FourCameraBatchBuilder(preprocessor)
            >>> frames = {
            ...     'front': np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8),
            ...     'left': np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8),
            ...     'right': np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8),
            ...     'rear': np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            ... }
            >>> batch, order = builder.build_batch(frames)
            >>> batch.shape
            torch.Size([4, 3, 640, 640])
        """
        # Validate we have exactly 4 cameras
        if len(camera_frames) != 4:
            raise ValueError(
                f"Expected 4 camera frames, got {len(camera_frames)}. "
                f"Required cameras: {self.camera_ids}"
            )
        
        # Check all required cameras are present
        missing_cameras = set(self.camera_ids) - set(camera_frames.keys())
        if missing_cameras:
            raise ValueError(f"Missing camera frames: {missing_cameras}")
        
        # Build batch in consistent order
        images = [camera_frames[camera_id] for camera_id in self.camera_ids]
        
        # Preprocess all images
        batch = self.preprocessor.preprocess_batch(images)
        
        return batch, self.camera_ids
    
    def build_single_camera_batch(
        self,
        camera_id: str,
        image: Union[np.ndarray, Image.Image, torch.Tensor]
    ) -> Tuple[torch.Tensor, List[str]]:
        """
        Build single-camera batch (for testing or single-camera mode).
        
        Args:
            camera_id: Camera identifier
            image: Camera image
        
        Returns:
            Tuple of (batch_tensor, camera_order):
            - batch_tensor: [1, 3, H, W] tensor
            - camera_order: List with single camera ID
        
        Requirements: 22.1
        """
        tensor = self.preprocessor.preprocess_image(image)
        return tensor, [camera_id]


# ==============================================================================
# Utility Functions
# ==============================================================================

def denormalize_image(
    tensor: torch.Tensor,
    mean: List[float] = None,
    std: List[float] = None
) -> torch.Tensor:
    """
    Denormalize image tensor for visualization.
    
    Args:
        tensor: Normalized tensor [C, H, W] or [B, C, H, W]
        mean: Normalization mean (default: ImageNet)
        std: Normalization std (default: ImageNet)
    
    Returns:
        Denormalized tensor with values in [0, 1]
    
    Example:
        >>> normalized = torch.randn(3, 640, 640)
        >>> original = denormalize_image(normalized)
        >>> original.min() >= 0 and original.max() <= 1
        True
    """
    mean = mean or DEFAULT_MEAN
    std = std or DEFAULT_STD
    
    mean_tensor = torch.tensor(mean, device=tensor.device)
    std_tensor = torch.tensor(std, device=tensor.device)
    
    if tensor.dim() == 4:
        # Batch: [B, C, H, W]
        mean_tensor = mean_tensor.view(1, 3, 1, 1)
        std_tensor = std_tensor.view(1, 3, 1, 1)
    else:
        # Single image: [C, H, W]
        mean_tensor = mean_tensor.view(3, 1, 1)
        std_tensor = std_tensor.view(3, 1, 1)
    
    # Reverse normalization: x_original = x_normalized * std + mean
    denormalized = tensor * std_tensor + mean_tensor
    
    # Clamp to [0, 1] range
    denormalized = torch.clamp(denormalized, 0, 1)
    
    return denormalized


def validate_batch_size(batch_size: int, available_vram_gb: float) -> int:
    """
    Validate and adjust batch size based on available VRAM.
    
    Args:
        batch_size: Requested batch size
        available_vram_gb: Available VRAM in GB
    
    Returns:
        Validated batch size (may be reduced if insufficient VRAM)
    
    Example:
        >>> validate_batch_size(4, 8.0)
        4
        >>> validate_batch_size(8, 4.0)
        4
    """
    # Approximate VRAM requirements:
    # - batch_size=1: ~1GB
    # - batch_size=4: ~4GB
    # - batch_size=8: ~8GB
    
    if available_vram_gb >= 8 and batch_size <= 8:
        return batch_size
    elif available_vram_gb >= 4 and batch_size <= 4:
        return batch_size
    elif available_vram_gb >= 2 and batch_size <= 2:
        return batch_size
    else:
        # Insufficient VRAM, reduce batch size
        recommended = max(1, int(available_vram_gb / 2))
        logger.warning(
            f"Requested batch_size={batch_size} may exceed available VRAM "
            f"({available_vram_gb:.1f}GB). Recommending batch_size={recommended}"
        )
        return min(batch_size, recommended)
