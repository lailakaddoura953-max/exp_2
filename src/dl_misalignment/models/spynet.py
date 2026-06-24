"""
SpyNet: Lightweight Optical Flow Network (Architecture B)

SpyNet is a simpler, faster alternative to LiteFlowNet2 for optical flow estimation.
It uses the same coarse-to-fine pyramid approach but with a more lightweight architecture.

What makes SpyNet "lightweight"?
- Simpler convolutional layers (fewer parameters)
- Larger kernel sizes (7×7 vs 3×3) capture more context per layer
- Fewer layers per pyramid level
- No separate refinement stage (refinement built into flow estimation)

Performance targets for Architecture B:
- Training VRAM: ≤6GB (vs ≤8GB for LiteFlowNet2)
- Inference VRAM: ≤3GB (vs ≤4GB for LiteFlowNet2)
- Inference latency: ≤30ms per frame pair (vs ≤50ms for LiteFlowNet2)

Why use SpyNet instead of LiteFlowNet2?
- Faster inference for real-time applications
- Lower memory footprint for resource-constrained devices
- Simpler architecture easier to understand and modify
- Good accuracy/speed tradeoff for many scenarios

Trade-offs:
- Slightly lower accuracy than LiteFlowNet2
- Larger kernels = more computation per layer (but fewer layers overall)
- Less fine-grained refinement

Task 6 Implementation: Architecture B Alternative Optical Flow Network
Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 24.5, 24.6, 24.7
"""

import logging
from typing import List

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

# Import FeatureWarping from LiteFlowNet2 (we'll reuse it!)
from .liteflownet2 import FeatureWarping

logger = logging.getLogger(__name__)


# ==============================================================================
# Task 6.1: Basic Flow Module
# ==============================================================================

class BasicFlowModule(nn.Module if TORCH_AVAILABLE else object):
    """
    Basic flow estimation module for SpyNet.
    
    This is the core building block of SpyNet. Each pyramid level uses one
    BasicFlowModule to estimate or refine optical flow.
    
    What does it do?
    - Takes concatenated features from frame t and frame t+1
    - Also takes current flow estimate (from coarser level)
    - Outputs a flow residual (correction to add to current flow)
    
    Architecture: 4 convolutional layers with 7×7 kernels
    Why 7×7 kernels?
    - Larger receptive field captures more context
    - Each layer sees 7×7 = 49 pixels at once (vs 3×3 = 9 pixels)
    - Fewer layers needed to capture motion patterns
    
    Channel progression:
    Input → 32 → 16 → 8 → 2 channels (flow residual)
    
    Comparison to LiteFlowNet2:
    - LiteFlowNet2: 6 layers with 3×3 kernels (more layers, smaller kernels)
    - SpyNet: 4 layers with 7×7 kernels (fewer layers, larger kernels)
    - Result: Similar receptive field, fewer parameters!
    
    Requirements: 3.1, 3.2, 3.6
    """
    
    def __init__(self, in_channels: int):
        """
        Initialize basic flow module.
        
        Args:
            in_channels: Number of input channels
                        Typically: 2 (current_flow) + C (features from t) + C (features from t+1)
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required")
        super(BasicFlowModule, self).__init__()
        
        # 4 convolutional layers with 7×7 kernels
        # Padding=3 ensures output size matches input (7×7 kernel needs padding=3)
        self.conv1 = nn.Conv2d(in_channels, 32, kernel_size=7, stride=1, padding=3)
        self.conv2 = nn.Conv2d(32, 16, kernel_size=7, stride=1, padding=3)
        self.conv3 = nn.Conv2d(16, 8, kernel_size=7, stride=1, padding=3)
        
        # Final layer: output 2 channels (u and v flow residual)
        self.conv4 = nn.Conv2d(8, 2, kernel_size=7, stride=1, padding=3)
        
        # ReLU activation (simpler than LeakyReLU used in LiteFlowNet2)
        self.relu = nn.ReLU(inplace=True)
    
    def forward(
        self,
        feat1: torch.Tensor,
        feat2_warped: torch.Tensor,
        flow: torch.Tensor
    ) -> torch.Tensor:
        """
        Estimate flow residual from features and current flow.
        
        Args:
            feat1: Features from frame t [B, C, H, W]
            feat2_warped: Warped features from frame t+1 [B, C, H, W]
            flow: Current flow estimate [B, 2, H, W]
        
        Returns:
            flow_residual: Correction to add to current flow [B, 2, H, W]
        
        Processing:
        1. Concatenate [feat1, feat2_warped, flow]
        2. Process through 4 conv layers with ReLU
        3. Output residual (no activation on final layer)
        
        Example:
            >>> module = BasicFlowModule(in_channels=130)  # 64 + 64 + 2
            >>> feat1 = torch.randn(1, 64, 80, 80)
            >>> feat2_warped = torch.randn(1, 64, 80, 80)
            >>> flow = torch.randn(1, 2, 80, 80)
            >>> residual = module(feat1, feat2_warped, flow)
            >>> residual.shape
            torch.Size([1, 2, 80, 80])
        """
        # Concatenate all inputs: features from both frames + current flow
        # Shape: [B, C + C + 2, H, W]
        x = torch.cat([feat1, feat2_warped, flow], dim=1)
        
        # Process through convolutional layers with ReLU activation
        x = self.relu(self.conv1(x))  # in_channels → 32
        x = self.relu(self.conv2(x))  # 32 → 16
        x = self.relu(self.conv3(x))  # 16 → 8
        
        # Final layer: no activation (residual can be positive or negative)
        residual = self.conv4(x)  # 8 → 2
        
        return residual


# ==============================================================================
# Task 6.2: Complete SpyNet Architecture
# ==============================================================================

class SpyNet(nn.Module if TORCH_AVAILABLE else object):
    """
    SpyNet: Lightweight Optical Flow Network.
    
    Complete coarse-to-fine optical flow estimation with lightweight architecture.
    
    Architecture Overview:
    ┌─────────────────────────────────────────────────────────────────┐
    │ Input: Two feature pyramids from CNNFeatureExtractor            │
    │   - pyramid1: Features from frame t                             │
    │   - pyramid2: Features from frame t+1                           │
    │   - Each pyramid has 4 levels: [Level 0, 1, 2, 3]              │
    ├─────────────────────────────────────────────────────────────────┤
    │ Level 3 (coarsest, 1/8 resolution, 512 channels):               │
    │   1. Initialize flow to zeros                                   │
    │   2. Warp feat2[3] with zero flow (no-op initially)            │
    │   3. BasicFlowModule(feat1, feat2_warped, flow) → residual     │
    │   4. flow = flow + residual                                     │
    ├─────────────────────────────────────────────────────────────────┤
    │ Level 2 (1/4 resolution, 256 channels):                         │
    │   1. Upsample flow from Level 3 (×2, scale values ×2)          │
    │   2. Warp feat2[2] using upsampled flow                         │
    │   3. BasicFlowModule → residual                                 │
    │   4. flow = upsampled_flow + residual                           │
    ├─────────────────────────────────────────────────────────────────┤
    │ Level 1 (1/2 resolution, 128 channels):                         │
    │   └─ (Same process as Level 2)                                  │
    ├─────────────────────────────────────────────────────────────────┤
    │ Level 0 (full resolution, 64 channels):                         │
    │   └─ (Same process as Level 2)                                  │
    │   └─ Output: Final optical flow field [B, 2, H, W]             │
    └─────────────────────────────────────────────────────────────────┘
    
    Key Differences from LiteFlowNet2:
    1. Simpler modules (BasicFlowModule vs FlowEstimator + FlowRefiner)
    2. No separate refinement stage (refinement built into each module)
    3. Larger kernels (7×7 vs 3×3) for efficiency
    4. Fewer parameters overall = faster + less memory
    
    Memory Efficiency:
    - SpyNet uses ~30% fewer parameters than LiteFlowNet2
    - Target: ≤3GB VRAM during inference (vs ≤4GB for LiteFlowNet2)
    - Target: ≤6GB VRAM during training (vs ≤8GB for LiteFlowNet2)
    
    Speed:
    - Fewer layers = faster forward pass
    - Target: ≤30ms per frame pair (vs ≤50ms for LiteFlowNet2)
    
    Requirements: 3.1, 3.2, 24.5, 24.6, 24.7
    """
    
    def __init__(self):
        """Initialize SpyNet."""
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required")
        super(SpyNet, self).__init__()
        
        # Feature warping module (reused from LiteFlowNet2)
        # Same warping logic works for both architectures!
        self.warp = FeatureWarping()
        
        # ======================================================================
        # Basic flow modules for each pyramid level
        # ======================================================================
        # Each module takes: feat1 + feat2_warped + flow
        # Channel counts: C (feat1) + C (feat2) + 2 (flow)
        
        # Level 3 (1/8 resolution): 512 + 512 + 2 = 1026 channels
        self.flow_module_level3 = BasicFlowModule(in_channels=512 + 512 + 2)
        
        # Level 2 (1/4 resolution): 256 + 256 + 2 = 514 channels
        self.flow_module_level2 = BasicFlowModule(in_channels=256 + 256 + 2)
        
        # Level 1 (1/2 resolution): 128 + 128 + 2 = 258 channels
        self.flow_module_level1 = BasicFlowModule(in_channels=128 + 128 + 2)
        
        # Level 0 (full resolution): 64 + 64 + 2 = 130 channels
        self.flow_module_level0 = BasicFlowModule(in_channels=64 + 64 + 2)
        
        logger.info("SpyNet initialized with lightweight coarse-to-fine architecture")
    
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
            >>> spynet = SpyNet()
            >>> 
            >>> frame_t = torch.randn(1, 3, 640, 640)
            >>> frame_t1 = torch.randn(1, 3, 640, 640)
            >>> 
            >>> pyramid1 = cnn(frame_t)
            >>> pyramid2 = cnn(frame_t1)
            >>> flow = spynet(pyramid1, pyramid2)
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
        
        B, C, H, W = feat1_level3.shape
        
        # Initialize flow to zeros at coarsest level
        # We start with no motion estimate and build up from there
        flow_level3 = torch.zeros(B, 2, H, W, device=feat1_level3.device, dtype=feat1_level3.dtype)
        
        # Warp feat2 with zero flow (initially this does nothing)
        # As we iterate/refine, this becomes meaningful
        feat2_level3_warped = self.warp(feat2_level3, flow_level3)
        
        # Estimate flow residual and add to current flow
        residual = self.flow_module_level3(feat1_level3, feat2_level3_warped, flow_level3)
        flow_level3 = flow_level3 + residual
        # Shape: [B, 2, H/8, W/8]
        
        # ======================================================================
        # Level 2: 1/4 resolution - Refine with upsampling
        # ======================================================================
        # Extract Level 2 features (256 channels at 1/4 resolution)
        feat1_level2 = pyramid1[2]
        feat2_level2 = pyramid2[2]
        
        # Upsample flow from Level 3 to Level 2 (×2 in each dimension)
        # Scale flow values by 2 (pixels move 2× distance at 2× resolution)
        flow_level2 = F.interpolate(
            flow_level3,
            scale_factor=2,
            mode='bilinear',
            align_corners=True
        ) * 2.0
        
        # Warp frame t+1 features to align with frame t
        feat2_level2_warped = self.warp(feat2_level2, flow_level2)
        
        # Estimate residual and update flow
        residual = self.flow_module_level2(feat1_level2, feat2_level2_warped, flow_level2)
        flow_level2 = flow_level2 + residual
        # Shape: [B, 2, H/4, W/4]
        
        # ======================================================================
        # Level 1: 1/2 resolution - Further refinement
        # ======================================================================
        feat1_level1 = pyramid1[1]
        feat2_level1 = pyramid2[1]
        
        # Upsample flow from Level 2 to Level 1
        flow_level1 = F.interpolate(
            flow_level2,
            scale_factor=2,
            mode='bilinear',
            align_corners=True
        ) * 2.0
        
        # Warp and refine
        feat2_level1_warped = self.warp(feat2_level1, flow_level1)
        residual = self.flow_module_level1(feat1_level1, feat2_level1_warped, flow_level1)
        flow_level1 = flow_level1 + residual
        # Shape: [B, 2, H/2, W/2]
        
        # ======================================================================
        # Level 0: Full resolution - Final refinement
        # ======================================================================
        feat1_level0 = pyramid1[0]
        feat2_level0 = pyramid2[0]
        
        # Upsample flow from Level 1 to Level 0 (full resolution)
        flow_level0 = F.interpolate(
            flow_level1,
            scale_factor=2,
            mode='bilinear',
            align_corners=True
        ) * 2.0
        
        # Warp and refine
        feat2_level0_warped = self.warp(feat2_level0, flow_level0)
        residual = self.flow_module_level0(feat1_level0, feat2_level0_warped, flow_level0)
        flow_final = flow_level0 + residual
        # Shape: [B, 2, H, W] - full resolution flow field
        
        return flow_final
    
    def get_pyramid_flows(
        self,
        pyramid1: List[torch.Tensor],
        pyramid2: List[torch.Tensor]
    ) -> List[torch.Tensor]:
        """
        Get flow estimates at all pyramid levels (for visualization/debugging).
        
        Useful for:
        - Understanding how flow evolves from coarse to fine
        - Debugging flow estimation issues
        - Visualizing multi-scale motion
        
        Args:
            pyramid1: Feature pyramid from frame t
            pyramid2: Feature pyramid from frame t+1
        
        Returns:
            List of flow tensors [flow_level3, flow_level2, flow_level1, flow_level0]
        
        Example:
            >>> flows = spynet.get_pyramid_flows(pyramid1, pyramid2)
            >>> for i, flow in enumerate(flows):
            ...     print(f"Level {3-i} flow: {flow.shape}")
            Level 3 flow: torch.Size([1, 2, 80, 80])
            Level 2 flow: torch.Size([1, 2, 160, 160])
            Level 1 flow: torch.Size([1, 2, 320, 320])
            Level 0 flow: torch.Size([1, 2, 640, 640])
        """
        flows = []
        
        # Level 3
        feat1_level3 = pyramid1[3]
        feat2_level3 = pyramid2[3]
        B, C, H, W = feat1_level3.shape
        flow_level3 = torch.zeros(B, 2, H, W, device=feat1_level3.device, dtype=feat1_level3.dtype)
        feat2_level3_warped = self.warp(feat2_level3, flow_level3)
        residual = self.flow_module_level3(feat1_level3, feat2_level3_warped, flow_level3)
        flow_level3 = flow_level3 + residual
        flows.append(flow_level3)
        
        # Level 2
        feat1_level2 = pyramid1[2]
        feat2_level2 = pyramid2[2]
        flow_level2 = F.interpolate(flow_level3, scale_factor=2, mode='bilinear', align_corners=True) * 2.0
        feat2_level2_warped = self.warp(feat2_level2, flow_level2)
        residual = self.flow_module_level2(feat1_level2, feat2_level2_warped, flow_level2)
        flow_level2 = flow_level2 + residual
        flows.append(flow_level2)
        
        # Level 1
        feat1_level1 = pyramid1[1]
        feat2_level1 = pyramid2[1]
        flow_level1 = F.interpolate(flow_level2, scale_factor=2, mode='bilinear', align_corners=True) * 2.0
        feat2_level1_warped = self.warp(feat2_level1, flow_level1)
        residual = self.flow_module_level1(feat1_level1, feat2_level1_warped, flow_level1)
        flow_level1 = flow_level1 + residual
        flows.append(flow_level1)
        
        # Level 0
        feat1_level0 = pyramid1[0]
        feat2_level0 = pyramid2[0]
        flow_level0 = F.interpolate(flow_level1, scale_factor=2, mode='bilinear', align_corners=True) * 2.0
        feat2_level0_warped = self.warp(feat2_level0, flow_level0)
        residual = self.flow_module_level0(feat1_level0, feat2_level0_warped, flow_level0)
        flow_level0 = flow_level0 + residual
        flows.append(flow_level0)
        
        return flows
    
    def count_parameters(self) -> int:
        """
        Count total number of trainable parameters in the network.
        
        Useful for:
        - Comparing model complexity with LiteFlowNet2
        - Understanding memory requirements
        - Model size estimation
        
        Returns:
            Number of trainable parameters
        
        Example:
            >>> spynet = SpyNet()
            >>> num_params = spynet.count_parameters()
            >>> print(f"SpyNet parameters: {num_params:,}")
            >>> 
            >>> # Compare with LiteFlowNet2
            >>> liteflow = LiteFlowNet2()
            >>> liteflow_params = sum(p.numel() for p in liteflow.parameters() if p.requires_grad)
            >>> print(f"LiteFlowNet2 parameters: {liteflow_params:,}")
            >>> print(f"SpyNet is {(1 - num_params/liteflow_params)*100:.1f}% smaller")
        """
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
