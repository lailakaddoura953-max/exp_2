"""
CNN Feature Extractor with 4-Level Pyramid Architecture

This is the first component of the neural network pipeline. It takes raw images
and extracts hierarchical visual features at multiple scales.

What does a CNN Feature Extractor do?
- Converts raw pixel values into meaningful "features"
- Early layers detect simple patterns (edges, corners)
- Deeper layers detect complex patterns (shapes, textures)
- Pyramid structure processes multiple scales simultaneously

Why pyramid architecture?
- Different scales capture different information
- Coarse levels (small images) = global structure, overall motion
- Fine levels (large images) = local details, precise alignment
- Memory efficient: each level is smaller than processing full resolution

Architecture: 4-level pyramid
- Level 0 (1×):   640×640 → 64 channels   (fine details)
- Level 1 (1/2×): 320×320 → 128 channels  (medium details)
- Level 2 (1/4×): 160×160 → 256 channels  (coarse structure)
- Level 3 (1/8×): 80×80 → 512 channels    (global context)

This design is inspired by VGG and ResNet architectures, optimized for
memory efficiency on consumer GPUs.
"""

import logging
from typing import List, Tuple, Optional
import numpy as np
import matplotlib.pyplot as plt

# Try to import torch
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    nn = None
    F = None

logger = logging.getLogger(__name__)


class CNNFeatureExtractor(nn.Module if TORCH_AVAILABLE else object):
    """
    4-Level Pyramid CNN Feature Extractor.
    
    Architecture Summary:
    ┌─────────────────────────────────────────────────────────┐
    │ Input: [B, 3, H, W]  (RGB image, H and W ≤ 750)        │
    ├─────────────────────────────────────────────────────────┤
    │ Level 0 (1× scale):                                      │
    │   Conv 3→64 (3×3) → ReLU → Conv 64→64 (3×3) → ReLU     │
    │   Output: [B, 64, H, W]                                 │
    │   ↓ MaxPool 2×2                                         │
    ├─────────────────────────────────────────────────────────┤
    │ Level 1 (1/2× scale):                                    │
    │   Conv 64→128 (3×3) → ReLU → Conv 128→128 (3×3) → ReLU │
    │   Output: [B, 128, H/2, W/2]                            │
    │   ↓ MaxPool 2×2                                         │
    ├─────────────────────────────────────────────────────────┤
    │ Level 2 (1/4× scale):                                    │
    │   Conv 128→256 (3×3) → ReLU (×3 layers)                │
    │   Output: [B, 256, H/4, W/4]                            │
    │   ↓ MaxPool 2×2                                         │
    ├─────────────────────────────────────────────────────────┤
    │ Level 3 (1/8× scale):                                    │
    │   Conv 256→512 (3×3) → ReLU (×3 layers)                │
    │   Output: [B, 512, H/8, W/8]                            │
    └─────────────────────────────────────────────────────────┘
    
    Args:
        input_channels: Number of input channels (3 for RGB)
        return_intermediate: If True, return all pyramid levels
    
    Example:
        >>> model = CNNFeatureExtractor()
        >>> image = torch.randn(1, 3, 640, 640)  # Batch of 1 image
        >>> pyramid = model(image)  # Returns list of 4 feature tensors
        >>> for i, features in enumerate(pyramid):
        ...     print(f"Level {i}: {features.shape}")
        Level 0: torch.Size([1, 64, 640, 640])
        Level 1: torch.Size([1, 128, 320, 320])
        Level 2: torch.Size([1, 256, 160, 160])
        Level 3: torch.Size([1, 512, 80, 80])
    """
    
    def __init__(
        self,
        input_channels: int = 3,
        return_intermediate: bool = True
    ):
        """Initialize CNN Feature Extractor."""
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required. Install with: pip install torch")
        
        super(CNNFeatureExtractor, self).__init__()
        
        self.input_channels = input_channels
        self.return_intermediate = return_intermediate
        
        # ======================================================================
        # Level 0: Full resolution (1× scale)
        # Purpose: Capture fine details and edges
        # Resolution: H × W
        # Channels: 3 → 64 → 64
        # ======================================================================
        self.conv1_1 = nn.Conv2d(
            in_channels=input_channels,  # 3 (RGB)
            out_channels=64,
            kernel_size=3,  # 3×3 filter
            stride=1,  # Move 1 pixel at a time
            padding=1,  # Keep same size (padding=1 for kernel=3)
            bias=True
        )
        self.conv1_2 = nn.Conv2d(64, 64, kernel_size=3, stride=1, padding=1)
        # MaxPool reduces size by 2× (640 → 320 for example)
        self.pool1 = nn.MaxPool2d(kernel_size=2, stride=2)
        
        # ======================================================================
        # Level 1: Half resolution (1/2× scale)
        # Purpose: Capture medium-scale patterns and textures
        # Resolution: H/2 × W/2
        # Channels: 64 → 128 → 128
        # ======================================================================
        self.conv2_1 = nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1)
        self.conv2_2 = nn.Conv2d(128, 128, kernel_size=3, stride=1, padding=1)
        self.pool2 = nn.MaxPool2d(kernel_size=2, stride=2)
        
        # ======================================================================
        # Level 2: Quarter resolution (1/4× scale)
        # Purpose: Capture larger structures and object parts
        # Resolution: H/4 × W/4
        # Channels: 128 → 256 → 256 → 256
        # ======================================================================
        self.conv3_1 = nn.Conv2d(128, 256, kernel_size=3, stride=1, padding=1)
        self.conv3_2 = nn.Conv2d(256, 256, kernel_size=3, stride=1, padding=1)
        self.conv3_3 = nn.Conv2d(256, 256, kernel_size=3, stride=1, padding=1)
        self.pool3 = nn.MaxPool2d(kernel_size=2, stride=2)
        
        # ======================================================================
        # Level 3: Eighth resolution (1/8× scale)
        # Purpose: Capture global context and overall scene structure
        # Resolution: H/8 × W/8
        # Channels: 256 → 512 → 512 → 512
        # ======================================================================
        self.conv4_1 = nn.Conv2d(256, 512, kernel_size=3, stride=1, padding=1)
        self.conv4_2 = nn.Conv2d(512, 512, kernel_size=3, stride=1, padding=1)
        self.conv4_3 = nn.Conv2d(512, 512, kernel_size=3, stride=1, padding=1)
        
        # Initialize weights using He initialization (good for ReLU activations)
        self._initialize_weights()
    
    def _initialize_weights(self):
        """
        Initialize network weights using He initialization.
        
        He initialization (also called Kaiming initialization) is designed
        specifically for ReLU activations. It prevents vanishing/exploding
        gradients during training.
        
        Why this matters:
        - Random init with wrong scale → gradients vanish or explode
        - He init sets weights to optimal scale for ReLU
        - Results in faster training and better convergence
        """
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                # He initialization for convolutional layers
                nn.init.kaiming_normal_(
                    m.weight,
                    mode='fan_out',  # Based on output connections
                    nonlinearity='relu'  # Optimized for ReLU activation
                )
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)  # Biases initialized to 0
    
    def forward(self, x: torch.Tensor) -> List[torch.Tensor]:
        """
        Forward pass through the feature extractor.
        
        Args:
            x: Input tensor [B, 3, H, W] where B=batch size, H,W ≤ 750
        
        Returns:
            List of 4 feature tensors (pyramid levels 0-3):
            - pyramid[0]: [B, 64, H, W]      (Level 0 - finest)
            - pyramid[1]: [B, 128, H/2, W/2] (Level 1)
            - pyramid[2]: [B, 256, H/4, W/4] (Level 2)
            - pyramid[3]: [B, 512, H/8, W/8] (Level 3 - coarsest)
        
        Processing flow:
        1. Input image → Conv → ReLU → Conv → ReLU → Save Level 0 → Pool
        2. Level 0 → Conv → ReLU → Conv → ReLU → Save Level 1 → Pool
        3. Level 1 → Conv → ReLU (×3) → Save Level 2 → Pool
        4. Level 2 → Conv → ReLU (×3) → Save Level 3
        5. Return pyramid = [Level 0, Level 1, Level 2, Level 3]
        """
        pyramid = []  # Will store feature maps at each level
        
        # ======================================================================
        # Level 0: Process at full resolution
        # ======================================================================
        # Apply first convolution: 3 channels → 64 channels
        # Each of the 64 channels detects a different pattern
        x = F.relu(self.conv1_1(x))  # ReLU activation: max(0, x)
        
        # Apply second convolution: refine the features
        x = F.relu(self.conv1_2(x))
        
        # Save Level 0 features (full resolution)
        pyramid.append(x)
        
        # Downsample by 2× using max pooling
        # Max pooling takes maximum value in each 2×2 window
        # This makes the network focus on the strongest features
        x = self.pool1(x)
        
        # ======================================================================
        # Level 1: Process at half resolution
        # ======================================================================
        x = F.relu(self.conv2_1(x))  # 64 → 128 channels
        x = F.relu(self.conv2_2(x))  # Refine 128 channels
        
        pyramid.append(x)  # Save Level 1
        x = self.pool2(x)  # Downsample to 1/4 resolution
        
        # ======================================================================
        # Level 2: Process at quarter resolution
        # ======================================================================
        # Three convolutions at this level for more complex patterns
        x = F.relu(self.conv3_1(x))  # 128 → 256 channels
        x = F.relu(self.conv3_2(x))  # Refine
        x = F.relu(self.conv3_3(x))  # Refine more
        
        pyramid.append(x)  # Save Level 2
        x = self.pool3(x)  # Downsample to 1/8 resolution
        
        # ======================================================================
        # Level 3: Process at eighth resolution (coarsest)
        # ======================================================================
        # Three convolutions with most channels (512) for rich features
        x = F.relu(self.conv4_1(x))  # 256 → 512 channels
        x = F.relu(self.conv4_2(x))  # Refine
        x = F.relu(self.conv4_3(x))  # Refine more
        
        pyramid.append(x)  # Save Level 3
        
        # Return pyramid: [Level 0, Level 1, Level 2, Level 3]
        # Each level has progressively fewer spatial dimensions but more channels
        return pyramid
    
    def get_feature_stats(self, pyramid: List[torch.Tensor]) -> dict:
        """
        Compute statistics for each pyramid level.
        
        Useful for:
        - Understanding what the network learned
        - Debugging training issues
        - Visualizing feature activations
        
        Args:
            pyramid: List of feature tensors from forward()
        
        Returns:
            Dictionary with statistics for each level
        
        Example:
            >>> pyramid = model(image)
            >>> stats = model.get_feature_stats(pyramid)
            >>> print(f"Level 0 mean activation: {stats['level_0']['mean']:.3f}")
        """
        stats = {}
        
        for level, features in enumerate(pyramid):
            # Detach from computation graph and move to CPU for analysis
            features_np = features.detach().cpu().numpy()
            
            stats[f'level_{level}'] = {
                'shape': features.shape,
                'mean': float(features_np.mean()),
                'std': float(features_np.std()),
                'min': float(features_np.min()),
                'max': float(features_np.max()),
                'num_channels': features.shape[1],
                'spatial_size': (features.shape[2], features.shape[3])
            }
        
        return stats
    
    def visualize_pyramid(
        self,
        pyramid: List[torch.Tensor],
        save_path: Optional[str] = None
    ) -> plt.Figure:
        """
        Visualize the feature pyramid structure and dimensions.
        
        Creates a diagram showing:
        - Input size
        - Each pyramid level with dimensions
        - Channel progression
        - Memory usage at each level
        
        Args:
            pyramid: Feature pyramid from forward()
            save_path: Optional path to save figure
        
        Returns:
            matplotlib Figure
        
        Example:
            >>> pyramid = model(image)
            >>> fig = model.visualize_pyramid(pyramid)
            >>> plt.show()
        """
        fig, axes = plt.subplots(1, 4, figsize=(16, 4))
        
        level_names = ['Level 0\n(1×)', 'Level 1\n(1/2×)', 'Level 2\n(1/4×)', 'Level 3\n(1/8×)']
        
        for idx, (ax, features, name) in enumerate(zip(axes, pyramid, level_names)):
            # Take first image in batch, compute mean across channels
            feat_np = features[0].detach().cpu().numpy()
            mean_activation = feat_np.mean(axis=0)  # Average across all channels
            
            # Plot as heatmap
            im = ax.imshow(mean_activation, cmap='viridis', aspect='auto')
            ax.set_title(
                f'{name}\n{features.shape[1]}×{features.shape[2]}×{features.shape[3]}',
                fontsize=11,
                weight='bold'
            )
            ax.axis('off')
            plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        
        plt.suptitle(
            'CNN Feature Pyramid - Mean Activation Heatmaps',
            fontsize=14,
            weight='bold'
        )
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Pyramid visualization saved to {save_path}")
        
        return fig


