"""
LiteFlowNet2: Memory-Efficient Optical Flow Network (Architecture A)

Optical flow = estimating how pixels move between consecutive frames
This helps detect camera movement by tracking how the entire scene shifts.

What is optical flow?
- Measures motion of each pixel between frame t and frame t+1
- Output: 2D vector field (u, v) for each pixel
- u = horizontal displacement, v = vertical displacement
- Example: If pixel at (100, 50) moves to (102, 48), flow = (2, -2)

Why LiteFlowNet2?
- Memory efficient: Uses pyramid coarse-to-fine approach
- Fast: Processes multiple scales in parallel
- Accurate: Refines flow iteratively from coarse to fine
- Suitable for consumer GPUs (4-8GB VRAM)

Architecture Approach:
1. Start at coarsest level (Level 3: 1/8 resolution) - estimate global motion
2. Upsample to Level 2, warp features, refine flow
3. Upsample to Level 1, warp features, refine flow
4. Upsample to Level 0, warp features, produce final flow

This is MUCH more memory efficient than processing full resolution directly!

Task 5 Implementation: Architecture A Primary Optical Flow Network
Requirements: 2.1-2.6, 24.4, 24.6, 24.7
"""

import logging
from typing import List, Tuple

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


# ==============================================================================
# Task 5.1: Feature Warping Module
# ==============================================================================

class FeatureWarping(nn.Module if TORCH_AVAILABLE else object):
    """
    Warp features from frame t+1 to align with frame t using optical flow.
    
    What is feature warping?
    - Given: Features from frame t+1 and estimated flow
    - Output: Features from t+1 warped/shifted to match t
    - Purpose: Align features so we can compare and refine flow
    
    Example:
        If flow says a pixel moved 2 pixels right, we shift the feature 
        2 pixels left to align it back to the original position.
    
    How it works:
    1. Create sampling grid from flow vectors
    2. Normalize coordinates to [-1, 1] range (required by grid_sample)
    3. Use bilinear interpolation to sample warped features
    
    Requirements: 2.1, 2.2
    """
    
    def __init__(self):
        """Initialize feature warping module."""
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required")
        super(FeatureWarping, self).__init__()
    
    def forward(
        self,
        features: torch.Tensor,
        flow: torch.Tensor
    ) -> torch.Tensor:
        """
        Warp features from frame t+1 using optical flow.
        
        Args:
            features: Features from frame t+1, shape [B, C, H, W]
            flow: Optical flow from t to t+1, shape [B, 2, H, W]
                  flow[:, 0] = horizontal displacement (u)
                  flow[:, 1] = vertical displacement (v)
        
        Returns:
            Warped features, shape [B, C, H, W]
        
        Example:
            >>> warper = FeatureWarping()
            >>> feat = torch.randn(1, 128, 80, 80)  # Features from frame t+1
            >>> flow = torch.randn(1, 2, 80, 80)    # Estimated flow
            >>> warped = warper(feat, flow)         # Align t+1 to t
            >>> warped.shape
            torch.Size([1, 128, 80, 80])
        """
        B, C, H, W = features.shape
        
        # ======================================================================
        # Step 1: Create base coordinate grid
        # ======================================================================
        # Create mesh grid of pixel coordinates
        # xx: [[0, 1, 2, ..., W-1], [0, 1, 2, ..., W-1], ...]  (H rows)
        # yy: [[0, 0, 0, ..., 0], [1, 1, 1, ..., 1], ...]      (H rows)
        xx = torch.arange(0, W, device=features.device, dtype=features.dtype)
        yy = torch.arange(0, H, device=features.device, dtype=features.dtype)
        
        # Create 2D grid: yy is vertical, xx is horizontal
        yy, xx = torch.meshgrid(yy, xx, indexing='ij')
        
        # Add batch dimension: [1, H, W] -> [B, H, W] (repeat for each image in batch)
        xx = xx.unsqueeze(0).expand(B, -1, -1)
        yy = yy.unsqueeze(0).expand(B, -1, -1)
        
        # ======================================================================
        # Step 2: Add flow to base coordinates
        # ======================================================================
        # flow[:, 0] = u (horizontal displacement)
        # flow[:, 1] = v (vertical displacement)
        # New position = original position + flow
        grid_x = xx + flow[:, 0]  # Add horizontal displacement
        grid_y = yy + flow[:, 1]  # Add vertical displacement
        
        # ======================================================================
        # Step 3: Normalize coordinates to [-1, 1] range
        # ======================================================================
        # grid_sample requires coordinates in range [-1, 1]
        # -1 = left/top edge, +1 = right/bottom edge, 0 = center
        # Formula: normalized = 2 * (coord / (size - 1)) - 1
        grid_x = 2.0 * grid_x / (W - 1) - 1.0
        grid_y = 2.0 * grid_y / (H - 1) - 1.0
        
        # Stack into grid: [B, H, W, 2] where last dim is (x, y)
        grid = torch.stack([grid_x, grid_y], dim=3)
        
        # ======================================================================
        # Step 4: Sample features using bilinear interpolation
        # ======================================================================
        # Bilinear interpolation: smooth sampling between grid points
        # If we sample at (10.5, 20.5), interpolate between 4 neighbors
        # Mode 'border': use edge pixels for out-of-bounds coordinates
        warped = F.grid_sample(
            features,
            grid,
            mode='bilinear',
            padding_mode='border',  # Clamp out-of-bounds to border
            align_corners=True  # Align corners for proper scaling
        )
        
        return warped


# ==============================================================================
# Task 5.2: Flow Estimator Module
# ==============================================================================

class FlowEstimator(nn.Module if TORCH_AVAILABLE else object):
    """
    Estimate optical flow from concatenated features.
    
    What does this do?
    - Takes concatenated features from frame t and frame t+1
    - Processes through convolutional layers
    - Outputs 2-channel flow field (u, v)
    
    Architecture: 6 convolutional layers with progressive channel reduction
    Input: Concatenated features (varies by pyramid level)
    Output: 2-channel flow (horizontal and vertical displacement)
    
    Layer progression:
    128 → 128 → 96 → 64 → 32 → 2 channels
    
    Why this works:
    - Early layers: Learn to match similar features
    - Middle layers: Estimate rough flow
    - Later layers: Refine to precise 2D vectors
    
    Requirements: 2.2, 2.3
    """
    
    def __init__(self, in_channels: int):
        """
        Initialize flow estimator.
        
        Args:
            in_channels: Number of input channels (concatenated features)
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required")
        super(FlowEstimator, self).__init__()
        
        # Progressive channel reduction: in_channels → 128 → 96 → 64 → 32 → 2
        self.conv1 = nn.Conv2d(in_channels, 128, kernel_size=3, stride=1, padding=1)
        self.conv2 = nn.Conv2d(128, 128, kernel_size=3, stride=1, padding=1)
        self.conv3 = nn.Conv2d(128, 96, kernel_size=3, stride=1, padding=1)
        self.conv4 = nn.Conv2d(96, 64, kernel_size=3, stride=1, padding=1)
        self.conv5 = nn.Conv2d(64, 32, kernel_size=3, stride=1, padding=1)
        
        # Final layer: output 2 channels (u and v flow components)
        self.conv6 = nn.Conv2d(32, 2, kernel_size=3, stride=1, padding=1)
        
        # LeakyReLU: allows small negative values (better for flow estimation)
        # negative_slope=0.1 means: f(x) = x if x > 0, else f(x) = 0.1*x
        self.leaky_relu = nn.LeakyReLU(negative_slope=0.1, inplace=True)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Estimate optical flow from concatenated features.
        
        Args:
            x: Concatenated features [B, in_channels, H, W]
        
        Returns:
            flow: Estimated optical flow [B, 2, H, W]
                  flow[:, 0] = horizontal displacement (u)
                  flow[:, 1] = vertical displacement (v)
        
        Example:
            >>> estimator = FlowEstimator(in_channels=1024)
            >>> features = torch.randn(1, 1024, 80, 80)
            >>> flow = estimator(features)
            >>> flow.shape
            torch.Size([1, 2, 80, 80])
        """
        # Process through 6 layers with LeakyReLU activation
        x = self.leaky_relu(self.conv1(x))
        x = self.leaky_relu(self.conv2(x))
        x = self.leaky_relu(self.conv3(x))
        x = self.leaky_relu(self.conv4(x))
        x = self.leaky_relu(self.conv5(x))
        
        # Final layer: no activation (flow can be positive or negative)
        flow = self.conv6(x)
        
        return flow


# ==============================================================================
# Task 5.3: Flow Refiner Module
# ==============================================================================

class FlowRefiner(nn.Module if TORCH_AVAILABLE else object):
    """
    Refine optical flow using residual learning.
    
    What is residual flow refinement?
    - Given: Current flow estimate + features
    - Output: Refined flow = current flow + residual correction
    - Purpose: Make small adjustments to improve accuracy
    
    Why residual learning?
    - Easier to learn small corrections than full flow
    - Previous estimate is already close, just needs fine-tuning
    - Helps network converge faster during training
    
    Architecture: 4 convolutional layers
    Input: Concatenated [current_flow, features]
    Output: Residual flow (correction to add)
    Final: refined_flow = current_flow + residual
    
    Requirements: 2.2, 2.3
    """
    
    def __init__(self, in_channels: int):
        """
        Initialize flow refiner.
        
        Args:
            in_channels: Number of input channels (flow + features)
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required")
        super(FlowRefiner, self).__init__()
        
        # 4 convolutional layers with channel reduction
        self.conv1 = nn.Conv2d(in_channels, 128, kernel_size=3, stride=1, padding=1)
        self.conv2 = nn.Conv2d(128, 64, kernel_size=3, stride=1, padding=1)
        self.conv3 = nn.Conv2d(64, 32, kernel_size=3, stride=1, padding=1)
        
        # Output residual flow (2 channels: u and v corrections)
        self.conv4 = nn.Conv2d(32, 2, kernel_size=3, stride=1, padding=1)
        
        self.leaky_relu = nn.LeakyReLU(negative_slope=0.1, inplace=True)
    
    def forward(
        self,
        flow: torch.Tensor,
        features: torch.Tensor
    ) -> torch.Tensor:
        """
        Refine optical flow by adding learned residual.
        
        Args:
            flow: Current flow estimate [B, 2, H, W]
            features: Features for this level [B, C, H, W]
        
        Returns:
            Refined flow [B, 2, H, W]
        
        Example:
            >>> refiner = FlowRefiner(in_channels=130)  # 2 (flow) + 128 (features)
            >>> flow = torch.randn(1, 2, 160, 160)
            >>> features = torch.randn(1, 128, 160, 160)
            >>> refined_flow = refiner(flow, features)
            >>> refined_flow.shape
            torch.Size([1, 2, 160, 160])
        """
        # Concatenate current flow with features
        x = torch.cat([flow, features], dim=1)
        
        # Process through convolutional layers
        x = self.leaky_relu(self.conv1(x))
        x = self.leaky_relu(self.conv2(x))
        x = self.leaky_relu(self.conv3(x))
        
        # Compute residual (no activation)
        residual = self.conv4(x)
        
        # Add residual to current flow
        refined_flow = flow + residual
        
        return refined_flow


# ==============================================================================
# Task 5.4: Complete LiteFlowNet2 Architecture
# ==============================================================================

class LiteFlowNet2(nn.Module if TORCH_AVAILABLE else object):
    """
    LiteFlowNet2: Memory-Efficient Optical Flow Network.
    
    Complete coarse-to-fine optical flow estimation using feature pyramids.
    
    Architecture Overview:
    ┌─────────────────────────────────────────────────────────────────┐
    │ Input: Two feature pyramids from CNNFeatureExtractor            │
    │   - pyramid1: Features from frame t                             │
    │   - pyramid2: Features from frame t+1                           │
    │   - Each pyramid has 4 levels: [Level 0, 1, 2, 3]              │
    ├─────────────────────────────────────────────────────────────────┤
    │ Level 3 (coarsest, 1/8 resolution):                             │
    │   1. Concatenate feat1[3] and feat2[3]                          │
    │   2. FlowEstimator → initial_flow                               │
    ├─────────────────────────────────────────────────────────────────┤
    │ Level 2 (1/4 resolution):                                        │
    │   1. Upsample flow from Level 3 (×2)                            │
    │   2. Warp feat2[2] using upsampled flow                         │
    │   3. Concatenate feat1[2] and warped_feat2[2]                   │
    │   4. FlowEstimator → flow_update                                │
    │   5. FlowRefiner → refined_flow                                 │
    ├─────────────────────────────────────────────────────────────────┤
    │ Level 1 (1/2 resolution):                                        │
    │   (Same process as Level 2)                                     │
    ├─────────────────────────────────────────────────────────────────┤
    │ Level 0 (full resolution):                                       │
    │   (Same process as Level 2)                                     │
    │   Output: Final optical flow field [B, 2, H, W]                │
    └─────────────────────────────────────────────────────────────────┘
    
    Why coarse-to-fine?
    - Coarse levels capture large motions (e.g., camera rotation)
    - Fine levels refine to pixel-accurate flow
    - Much faster and less memory than processing full resolution directly
    
    Memory efficiency:
    - Level 3: 80×80 pixels = 6,400 pixels per image
    - Full resolution: 640×640 = 409,600 pixels
    - Processing coarse first = 64× memory reduction initially!
    
    Requirements: 2.1, 2.2, 2.3, 24.4, 24.6, 24.7
    """
    
    def __init__(self):
        """Initialize LiteFlowNet2."""
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required")
        super(LiteFlowNet2, self).__init__()
        
        # Feature warping module (shared across all levels)
        self.warp = FeatureWarping()
        
        # ======================================================================
        # Flow estimators for each pyramid level
        # ======================================================================
        # Level 3 (1/8 resolution): Concatenate 512+512 channels
        self.estimator_level3 = FlowEstimator(in_channels=512 + 512)
        
        # Level 2 (1/4 resolution): Concatenate 256+256 channels
        self.estimator_level2 = FlowEstimator(in_channels=256 + 256)
        
        # Level 1 (1/2 resolution): Concatenate 128+128 channels
        self.estimator_level1 = FlowEstimator(in_channels=128 + 128)
        
        # Level 0 (full resolution): Concatenate 64+64 channels
        self.estimator_level0 = FlowEstimator(in_channels=64 + 64)
        
        # ======================================================================
        # Flow refiners for each level (except Level 3)
        # ======================================================================
        # Level 2 refiner: 2 (flow) + 256 (features) channels
        self.refiner_level2 = FlowRefiner(in_channels=2 + 256)
        
        # Level 1 refiner: 2 (flow) + 128 (features) channels
        self.refiner_level1 = FlowRefiner(in_channels=2 + 128)
        
        # Level 0 refiner: 2 (flow) + 64 (features) channels
        self.refiner_level0 = FlowRefiner(in_channels=2 + 64)
        
        logger.info("LiteFlowNet2 initialized with coarse-to-fine architecture")
    
    def forward(
        self,
        pyramid1: List[torch.Tensor],
        pyramid2: List[torch.Tensor]
    ) -> torch.Tensor:
        """
        Estimate optical flow from frame t to frame t+1.
        
        Args:
            pyramid1: Feature pyramid from frame t
                     [Level 0, 1, 2, 3] with shapes:
                     - Level 0: [B, 64, H, W]
                     - Level 1: [B, 128, H/2, W/2]
                     - Level 2: [B, 256, H/4, W/4]
                     - Level 3: [B, 512, H/8, W/8]
            
            pyramid2: Feature pyramid from frame t+1 (same structure)
        
        Returns:
            flow: Optical flow field [B, 2, H, W] at full resolution
                 flow[:, 0] = horizontal displacement (u)
                 flow[:, 1] = vertical displacement (v)
        
        Example:
            >>> from cnn_feature_extractor import CNNFeatureExtractor
            >>> cnn = CNNFeatureExtractor()
            >>> flow_net = LiteFlowNet2()
            >>> 
            >>> frame_t = torch.randn(1, 3, 640, 640)
            >>> frame_t1 = torch.randn(1, 3, 640, 640)
            >>> 
            >>> pyramid1 = cnn(frame_t)
            >>> pyramid2 = cnn(frame_t1)
            >>> flow = flow_net(pyramid1, pyramid2)
            >>> 
            >>> flow.shape
            torch.Size([1, 2, 640, 640])
        """
        # ======================================================================
        # Level 3: Coarsest level (1/8 resolution) - Initial flow estimation
        # ======================================================================
        # Extract Level 3 features (512 channels at 1/8 resolution)
        feat1_level3 = pyramid1[3]  # Frame t, Level 3
        feat2_level3 = pyramid2[3]  # Frame t+1, Level 3
        
        # Concatenate features from both frames
        # Shape: [B, 1024, H/8, W/8] (512 + 512 channels)
        concat_level3 = torch.cat([feat1_level3, feat2_level3], dim=1)
        
        # Estimate initial flow at coarse resolution
        # This captures large-scale motion (e.g., overall camera movement)
        flow_level3 = self.estimator_level3(concat_level3)
        # Shape: [B, 2, H/8, W/8]
        
        # ======================================================================
        # Level 2: 1/4 resolution - Refine with warping
        # ======================================================================
        # Extract Level 2 features (256 channels at 1/4 resolution)
        feat1_level2 = pyramid1[2]
        feat2_level2 = pyramid2[2]
        
        # Upsample flow from Level 3 to Level 2 (×2 in each dimension)
        # Also scale flow values by 2 (pixels move 2× distance at 2× resolution)
        flow_level2_upsampled = F.interpolate(
            flow_level3,
            scale_factor=2,
            mode='bilinear',
            align_corners=True
        ) * 2.0
        
        # Warp frame t+1 features to align with frame t
        feat2_level2_warped = self.warp(feat2_level2, flow_level2_upsampled)
        
        # Concatenate features and estimate flow
        concat_level2 = torch.cat([feat1_level2, feat2_level2_warped], dim=1)
        flow_level2 = self.estimator_level2(concat_level2)
        
        # Refine flow using residual learning
        flow_level2 = self.refiner_level2(flow_level2, feat1_level2)
        # Shape: [B, 2, H/4, W/4]
        
        # ======================================================================
        # Level 1: 1/2 resolution - Further refinement
        # ======================================================================
        feat1_level1 = pyramid1[1]
        feat2_level1 = pyramid2[1]
        
        # Upsample flow from Level 2 to Level 1
        flow_level1_upsampled = F.interpolate(
            flow_level2,
            scale_factor=2,
            mode='bilinear',
            align_corners=True
        ) * 2.0
        
        # Warp and estimate
        feat2_level1_warped = self.warp(feat2_level1, flow_level1_upsampled)
        concat_level1 = torch.cat([feat1_level1, feat2_level1_warped], dim=1)
        flow_level1 = self.estimator_level1(concat_level1)
        
        # Refine
        flow_level1 = self.refiner_level1(flow_level1, feat1_level1)
        # Shape: [B, 2, H/2, W/2]
        
        # ======================================================================
        # Level 0: Full resolution - Final refinement
        # ======================================================================
        feat1_level0 = pyramid1[0]
        feat2_level0 = pyramid2[0]
        
        # Upsample flow from Level 1 to Level 0 (full resolution)
        flow_level0_upsampled = F.interpolate(
            flow_level1,
            scale_factor=2,
            mode='bilinear',
            align_corners=True
        ) * 2.0
        
        # Warp and estimate
        feat2_level0_warped = self.warp(feat2_level0, flow_level0_upsampled)
        concat_level0 = torch.cat([feat1_level0, feat2_level0_warped], dim=1)
        flow_level0 = self.estimator_level0(concat_level0)
        
        # Final refinement
        flow_final = self.refiner_level0(flow_level0, feat1_level0)
        # Shape: [B, 2, H, W] - full resolution flow field
        
        return flow_final
    
    def get_pyramid_flows(
        self,
        pyramid1: List[torch.Tensor],
        pyramid2: List[torch.Tensor]
    ) -> List[torch.Tensor]:
        """
        Get flow estimates at all pyramid levels (for visualization/debugging).
        
        Args:
            pyramid1: Feature pyramid from frame t
            pyramid2: Feature pyramid from frame t+1
        
        Returns:
            List of flow tensors [flow_level3, flow_level2, flow_level1, flow_level0]
        
        Example:
            >>> flows = flow_net.get_pyramid_flows(pyramid1, pyramid2)
            >>> for i, flow in enumerate(flows):
            ...     print(f"Level {3-i} flow: {flow.shape}")
        """
        flows = []
        
        # Level 3
        feat1_level3 = pyramid1[3]
        feat2_level3 = pyramid2[3]
        concat_level3 = torch.cat([feat1_level3, feat2_level3], dim=1)
        flow_level3 = self.estimator_level3(concat_level3)
        flows.append(flow_level3)
        
        # Level 2
        feat1_level2 = pyramid1[2]
        feat2_level2 = pyramid2[2]
        flow_level2_up = F.interpolate(flow_level3, scale_factor=2, mode='bilinear', align_corners=True) * 2.0
        feat2_level2_warped = self.warp(feat2_level2, flow_level2_up)
        concat_level2 = torch.cat([feat1_level2, feat2_level2_warped], dim=1)
        flow_level2 = self.estimator_level2(concat_level2)
        flow_level2 = self.refiner_level2(flow_level2, feat1_level2)
        flows.append(flow_level2)
        
        # Level 1
        feat1_level1 = pyramid1[1]
        feat2_level1 = pyramid2[1]
        flow_level1_up = F.interpolate(flow_level2, scale_factor=2, mode='bilinear', align_corners=True) * 2.0
        feat2_level1_warped = self.warp(feat2_level1, flow_level1_up)
        concat_level1 = torch.cat([feat1_level1, feat2_level1_warped], dim=1)
        flow_level1 = self.estimator_level1(concat_level1)
        flow_level1 = self.refiner_level1(flow_level1, feat1_level1)
        flows.append(flow_level1)
        
        # Level 0
        feat1_level0 = pyramid1[0]
        feat2_level0 = pyramid2[0]
        flow_level0_up = F.interpolate(flow_level1, scale_factor=2, mode='bilinear', align_corners=True) * 2.0
        feat2_level0_warped = self.warp(feat2_level0, flow_level0_up)
        concat_level0 = torch.cat([feat1_level0, feat2_level0_warped], dim=1)
        flow_level0 = self.estimator_level0(concat_level0)
        flow_level0 = self.refiner_level0(flow_level0, feat1_level0)
        flows.append(flow_level0)
        
        return flows
