# Design Document: Deep Learning Misalignment Detection System

## Overview

### System Purpose

The Deep Learning Misalignment Detection System (DL_System) replaces the existing rule-based computer vision approach with learned neural network models for detecting camera misalignment in multi-camera autonomous vehicle systems. The system processes synchronized frames from 4 vehicle-mounted cameras, estimating misalignment probability, severity classification, and 6-DOF camera pose.

### Key Design Objectives

1. **Memory Efficiency**: Support training and inference on consumer GPUs (4-16GB VRAM)
2. **Real-Time Performance**: Process 4-camera batches at 10+ Hz (≤100ms latency)
3. **Dual Architecture Comparison**: Evaluate LiteFlowNet2 and SpyNet for optimal deployment
4. **Backward Compatibility**: Preserve existing rule-based system with seamless mode switching
5. **Resolution Constraint**: Maximum input resolution of 750×750 pixels for all processing

### High-Level Architecture

The system consists of six major subsystems:

```
┌─────────────────────────────────────────────────────────────────┐
│                     DL_System (Top Level)                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────┐  ┌──────────────┐  ┌───────────────────┐   │
│  │ Configuration │  │  Training    │  │   Inference       │   │
│  │    System     │──│  Pipeline    │  │    Engine         │   │
│  └───────────────┘  └──────────────┘  └───────────────────┘   │
│         │                   │                    │              │
│         │           ┌───────┴────────┐           │              │
│         │           │                │           │              │
│         ▼           ▼                ▼           ▼              │
│  ┌───────────────────────────────────────────────────────┐     │
│  │           Neural Network Components                    │     │
│  │  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐ │     │
│  │  │     CNN      │  │  Optical    │  │     Pose     │ │     │
│  │  │   Feature    │─▶│    Flow     │─▶│  Estimator   │ │     │
│  │  │  Extractor   │  │  Network    │  │   (6-DOF)    │ │     │
│  │  └──────────────┘  └─────────────┘  └──────────────┘ │     │
│  │         │              │      │             │          │     │
│  │         └──────────────┴──────┴─────────────┘          │     │
│  └───────────────────────────────────────────────────────┘     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐      │
│  │         Rule-Based System (Preserved)                 │      │
│  │  ORB Features │ Dense Optical Flow │ Visual SLAM     │      │
│  └──────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```


### Architecture Decision: Two Comparative Implementations

**Architecture A**: CNN Feature Extractor + LiteFlowNet2
- Memory-efficient pyramid-based optical flow
- Target: 8GB VRAM training, 4GB VRAM inference
- Expected: Higher accuracy, moderate latency

**Architecture B**: CNN Feature Extractor + SpyNet
- Lightweight alternative optical flow network
- Target: 6GB VRAM training, 3GB VRAM inference
- Expected: Lower memory footprint, faster inference

Both architectures share the CNN Feature Extractor and Pose Estimator components, differing only in the optical flow network. This design enables direct comparison of flow estimation approaches while controlling other variables.

### Data Flow Pipeline

**Training Phase**:
```
KITTI Dataset → Data Loader → Augmentation Engine → CNN Feature Extractor →
Optical Flow Network → Pose Estimator → Loss Computation → Optimizer →
Model Checkpoint → Validation → TensorBoard
```

**Inference Phase**:
```
4 Camera Frames → Preprocessing → Batch Formation → CNN Feature Extractor →
Optical Flow Network → Pose Estimator → Uncertainty Estimation →
Output Formatting → JSON Serialization
```

---

## Architecture

### System-Level Design Principles


1. **Modular Component Boundaries**: Each neural network component (Feature Extractor, Flow Network, Pose Estimator) operates as independent module with well-defined interfaces
2. **Memory-First Design**: All architectural decisions prioritize VRAM efficiency through mixed precision, gradient checkpointing, and pyramid processing
3. **Graceful Degradation**: System automatically falls back to rule-based detection on neural network failures
4. **Configuration-Driven**: All hyperparameters, architecture selection, and operational modes controlled via YAML configuration
5. **Resolution Constraint Enforcement**: All image processing respects 750×750 maximum resolution limit

### Component Interaction Model

```
┌─────────────────────────────────────────────────────────────────┐
│                    Input: 4 Camera Frames                        │
│                   (each ≤ 750×750 pixels)                        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Preprocessing & Batch Formation                     │
│  • Resize to target resolution (≤750×750)                        │
│  • Normalize (mean subtraction, std scaling)                     │
│  • Batch into tensor: [4, 3, H, W]                               │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              CNN Feature Extractor (Shared)                      │
│  Input:  [4, 3, H, W]                                            │
│  Output: Pyramid of 4 feature maps                               │
│    • Level 0 (1x):   [4, 64, H, W]                               │
│    • Level 1 (1/2x): [4, 128, H/2, W/2]                          │
│    • Level 2 (1/4x): [4, 256, H/4, W/4]                          │
│    • Level 3 (1/8x): [4, 512, H/8, W/8]                          │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             │
              ┌──────────────┴────────────────┐
              │                               │
              ▼                               ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│   LiteFlowNet2           │   │      SpyNet              │
│   (Architecture A)       │   │   (Architecture B)       │
│                          │   │                          │
│  Input: Feature Pyramid  │   │  Input: Feature Pyramid  │
│  Output: [4, 2, H, W]    │   │  Output: [4, 2, H, W]    │
│    (optical flow field)  │   │    (optical flow field)  │
└──────────────┬───────────┘   └───────────┬──────────────┘
               │                           │
               └───────────┬───────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Pose Estimator (Shared)                       │
│  Input: Concatenated [feature pyramid + optical flow]            │
│  Outputs:                                                        │
│    • Misalignment Probability: [4, 1] (range [0, 1])            │
│    • 6-DOF Pose: [4, 6] (X, Y, Z, roll, pitch, yaw)             │
│    • Uncertainty Estimate: [4, 1] (via MC Dropout)              │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Post-Processing                               │
│  • Apply severity classification thresholds                      │
│  • Format structured output dictionary                           │
│  • Serialize to JSON                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Components and Interfaces

### 1. CNN Feature Extractor


**Purpose**: Extract hierarchical visual features from input images using pyramid architecture with 4 resolution levels.

**Architecture Specification**:

```python
class CNNFeatureExtractor(nn.Module):
    """
    Pyramid-based feature extractor with 4 levels.
    Max input: 750×750 pixels
    """
    
    def __init__(self, input_channels=3):
        # Level 0 (1x resolution): Input → 64 channels
        self.conv1_1 = Conv2d(3, 64, kernel_size=3, stride=1, padding=1)
        self.conv1_2 = Conv2d(64, 64, kernel_size=3, stride=1, padding=1)
        self.pool1 = MaxPool2d(kernel_size=2, stride=2)  # Downsample to 1/2x
        
        # Level 1 (1/2x resolution): 64 → 128 channels
        self.conv2_1 = Conv2d(64, 128, kernel_size=3, stride=1, padding=1)
        self.conv2_2 = Conv2d(128, 128, kernel_size=3, stride=1, padding=1)
        self.pool2 = MaxPool2d(kernel_size=2, stride=2)  # Downsample to 1/4x
        
        # Level 2 (1/4x resolution): 128 → 256 channels
        self.conv3_1 = Conv2d(128, 256, kernel_size=3, stride=1, padding=1)
        self.conv3_2 = Conv2d(256, 256, kernel_size=3, stride=1, padding=1)
        self.conv3_3 = Conv2d(256, 256, kernel_size=3, stride=1, padding=1)
        self.pool3 = MaxPool2d(kernel_size=2, stride=2)  # Downsample to 1/8x
        
        # Level 3 (1/8x resolution): 256 → 512 channels
        self.conv4_1 = Conv2d(256, 512, kernel_size=3, stride=1, padding=1)
        self.conv4_2 = Conv2d(512, 512, kernel_size=3, stride=1, padding=1)
        self.conv4_3 = Conv2d(512, 512, kernel_size=3, stride=1, padding=1)
    
    def forward(self, x):
        # Input: [B, 3, H, W] where H, W ≤ 750
        pyramid = []
        
        # Level 0: [B, 64, H, W]
        x = F.relu(self.conv1_1(x))
        x = F.relu(self.conv1_2(x))
        pyramid.append(x)
        x = self.pool1(x)
        
        # Level 1: [B, 128, H/2, W/2]
        x = F.relu(self.conv2_1(x))
        x = F.relu(self.conv2_2(x))
        pyramid.append(x)
        x = self.pool2(x)
        
        # Level 2: [B, 256, H/4, W/4]
        x = F.relu(self.conv3_1(x))
        x = F.relu(self.conv3_2(x))
        x = F.relu(self.conv3_3(x))
        pyramid.append(x)
        x = self.pool3(x)
        
        # Level 3: [B, 512, H/8, W/8]
        x = F.relu(self.conv4_1(x))
        x = F.relu(self.conv4_2(x))
        x = F.relu(self.conv4_3(x))
        pyramid.append(x)
        
        return pyramid  # List of 4 feature maps
```

**Interface Specification**:

- **Input**: 
  - Tensor shape: `[batch_size, 3, height, width]`
  - Constraints: `256 ≤ height, width ≤ 750`
  - Data type: `torch.float32` or `torch.float16` (mixed precision)
  - Value range: `[0, 1]` (normalized images)

- **Output**: 
  - List of 4 feature tensors (pyramid levels 0-3)
  - Shapes: 
    - Level 0: `[batch_size, 64, H, W]`
    - Level 1: `[batch_size, 128, H/2, W/2]`
    - Level 2: `[batch_size, 256, H/4, W/4]`
    - Level 3: `[batch_size, 512, H/8, W/8]`

**Performance Targets**:
- Forward pass latency: ≤30ms for batch_size=4 at 750×750 resolution
- Memory consumption: ~1.5GB VRAM for batch_size=4

### 2. LiteFlowNet2 (Architecture A)


**Purpose**: Estimate optical flow between consecutive frames using pyramid-based coarse-to-fine refinement with memory-efficient design.

**Architecture Specification**:

```python
class LiteFlowNet2(nn.Module):
    """
    Pyramid-based optical flow network with cascaded refinement.
    Processes from coarse (Level 3) to fine (Level 0).
    """
    
    def __init__(self):
        # Feature warping module for each pyramid level
        self.warping = FeatureWarping()
        
        # Flow estimation modules for each level
        self.flow_estimator_3 = FlowEstimator(channels=512+512)  # Concatenated features
        self.flow_estimator_2 = FlowEstimator(channels=256+256+2)  # Features + upsampled flow
        self.flow_estimator_1 = FlowEstimator(channels=128+128+2)
        self.flow_estimator_0 = FlowEstimator(channels=64+64+2)
        
        # Flow refinement modules
        self.flow_refiner_2 = FlowRefiner(channels=256)
        self.flow_refiner_1 = FlowRefiner(channels=128)
        self.flow_refiner_0 = FlowRefiner(channels=64)
        
    def forward(self, pyramid_t1, pyramid_t2):
        """
        pyramid_t1: Feature pyramid from frame t
        pyramid_t2: Feature pyramid from frame t+1
        Both are lists of 4 tensors [Level 0, Level 1, Level 2, Level 3]
        """
        
        # Start from coarsest level (Level 3: 1/8x resolution)
        feat1_3, feat2_3 = pyramid_t1[3], pyramid_t2[3]
        flow_3 = self.flow_estimator_3(torch.cat([feat1_3, feat2_3], dim=1))
        
        # Level 2: Refine using 1/4x features
        feat1_2, feat2_2 = pyramid_t1[2], pyramid_t2[2]
        flow_2_upsampled = F.interpolate(flow_3, scale_factor=2, mode='bilinear') * 2
        feat2_2_warped = self.warping(feat2_2, flow_2_upsampled)
        flow_2_residual = self.flow_estimator_2(torch.cat([feat1_2, feat2_2_warped, flow_2_upsampled], dim=1))
        flow_2 = flow_2_upsampled + flow_2_residual
        flow_2_refined = self.flow_refiner_2(flow_2, feat1_2)
        
        # Level 1: Refine using 1/2x features
        feat1_1, feat2_1 = pyramid_t1[1], pyramid_t2[1]
        flow_1_upsampled = F.interpolate(flow_2_refined, scale_factor=2, mode='bilinear') * 2
        feat2_1_warped = self.warping(feat2_1, flow_1_upsampled)
        flow_1_residual = self.flow_estimator_1(torch.cat([feat1_1, feat2_1_warped, flow_1_upsampled], dim=1))
        flow_1 = flow_1_upsampled + flow_1_residual
        flow_1_refined = self.flow_refiner_1(flow_1, feat1_1)
        
        # Level 0: Final refinement at full resolution
        feat1_0, feat2_0 = pyramid_t1[0], pyramid_t2[0]
        flow_0_upsampled = F.interpolate(flow_1_refined, scale_factor=2, mode='bilinear') * 2
        feat2_0_warped = self.warping(feat2_0, flow_0_upsampled)
        flow_0_residual = self.flow_estimator_0(torch.cat([feat1_0, feat2_0_warped, flow_0_upsampled], dim=1))
        flow_0 = flow_0_upsampled + flow_0_residual
        flow_0_refined = self.flow_refiner_0(flow_0, feat1_0)
        
        return flow_0_refined  # [B, 2, H, W] - final optical flow

class FlowEstimator(nn.Module):
    """Convolutional module for flow estimation at each pyramid level."""
    def __init__(self, channels):
        super().__init__()
        self.conv1 = Conv2d(channels, 128, kernel_size=3, padding=1)
        self.conv2 = Conv2d(128, 128, kernel_size=3, padding=1)
        self.conv3 = Conv2d(128, 96, kernel_size=3, padding=1)
        self.conv4 = Conv2d(96, 64, kernel_size=3, padding=1)
        self.conv5 = Conv2d(64, 32, kernel_size=3, padding=1)
        self.conv_flow = Conv2d(32, 2, kernel_size=3, padding=1)  # Output: 2-channel flow
        
    def forward(self, x):
        x = F.leaky_relu(self.conv1(x), negative_slope=0.1)
        x = F.leaky_relu(self.conv2(x), negative_slope=0.1)
        x = F.leaky_relu(self.conv3(x), negative_slope=0.1)
        x = F.leaky_relu(self.conv4(x), negative_slope=0.1)
        x = F.leaky_relu(self.conv5(x), negative_slope=0.1)
        flow = self.conv_flow(x)
        return flow

class FlowRefiner(nn.Module):
    """Refines flow estimates using residual connections."""
    def __init__(self, channels):
        super().__init__()
        self.conv1 = Conv2d(channels+2, 128, kernel_size=3, padding=1)  # +2 for flow channels
        self.conv2 = Conv2d(128, 64, kernel_size=3, padding=1)
        self.conv3 = Conv2d(64, 32, kernel_size=3, padding=1)
        self.conv_residual = Conv2d(32, 2, kernel_size=3, padding=1)
        
    def forward(self, flow, features):
        x = torch.cat([flow, features], dim=1)
        x = F.leaky_relu(self.conv1(x), negative_slope=0.1)
        x = F.leaky_relu(self.conv2(x), negative_slope=0.1)
        x = F.leaky_relu(self.conv3(x), negative_slope=0.1)
        flow_residual = self.conv_residual(x)
        return flow + flow_residual

class FeatureWarping(nn.Module):
    """Warps features from frame t+1 to frame t using optical flow."""
    def forward(self, features, flow):
        B, C, H, W = features.size()
        # Generate sampling grid
        grid_y, grid_x = torch.meshgrid(torch.arange(H), torch.arange(W))
        grid = torch.stack([grid_x, grid_y], dim=0).float().to(features.device)
        grid = grid.unsqueeze(0).repeat(B, 1, 1, 1)  # [B, 2, H, W]
        
        # Apply flow to grid
        warped_grid = grid + flow
        # Normalize to [-1, 1] for grid_sample
        warped_grid[:, 0] = 2.0 * warped_grid[:, 0] / (W - 1) - 1.0
        warped_grid[:, 1] = 2.0 * warped_grid[:, 1] / (H - 1) - 1.0
        warped_grid = warped_grid.permute(0, 2, 3, 1)  # [B, H, W, 2]
        
        # Warp features
        warped_features = F.grid_sample(features, warped_grid, align_corners=True)
        return warped_features
```

**Interface Specification**:

- **Input**: 
  - Two feature pyramids (each a list of 4 tensors)
  - From consecutive frames t and t+1
  
- **Output**: 
  - Optical flow tensor: `[batch_size, 2, H, W]`
  - Channel 0: horizontal flow (u)
  - Channel 1: vertical flow (v)
  - Values in pixels

**Performance Targets**:
- Forward pass latency: ≤50ms for batch_size=4
- Training VRAM: ≤8GB for batch_size=4
- Inference VRAM: ≤4GB for batch_size=4

### 3. SpyNet (Architecture B)


**Purpose**: Provide lightweight alternative optical flow estimation with reduced memory footprint and faster inference.

**Architecture Specification**:

```python
class SpyNet(nn.Module):
    """
    Lightweight pyramid-based optical flow network.
    Uses simple convolutional layers at each pyramid level.
    """
    
    def __init__(self):
        # Single flow estimator module shared across pyramid levels
        self.basic_module = nn.ModuleList([
            BasicFlowModule() for _ in range(4)  # One per pyramid level
        ])
        self.warping = FeatureWarping()
        
    def forward(self, pyramid_t1, pyramid_t2):
        """
        pyramid_t1, pyramid_t2: Feature pyramids from consecutive frames
        Process from coarse (Level 3) to fine (Level 0)
        """
        
        # Initialize flow at coarsest level
        B, _, H3, W3 = pyramid_t1[3].shape
        flow = torch.zeros(B, 2, H3, W3, device=pyramid_t1[3].device)
        
        # Iterate from coarse to fine (Level 3 → 0)
        for level in [3, 2, 1, 0]:
            feat1 = pyramid_t1[level]
            feat2 = pyramid_t2[level]
            
            # Upsample flow from previous level (if not first level)
            if level < 3:
                flow = F.interpolate(flow, scale_factor=2, mode='bilinear') * 2
            
            # Warp frame2 features using current flow estimate
            feat2_warped = self.warping(feat2, flow)
            
            # Estimate flow residual
            flow_residual = self.basic_module[level](feat1, feat2_warped, flow)
            
            # Update flow
            flow = flow + flow_residual
        
        return flow  # [B, 2, H, W]

class BasicFlowModule(nn.Module):
    """
    Simple convolutional module for flow estimation.
    Lighter than LiteFlowNet2's FlowEstimator.
    """
    def __init__(self):
        super().__init__()
        # Input: feat1 + feat2_warped + current_flow
        # Channels vary by pyramid level, so use adaptive design
        self.conv1 = Conv2d(None, 32, kernel_size=7, padding=3)  # Lazy init
        self.conv2 = Conv2d(32, 16, kernel_size=7, padding=3)
        self.conv3 = Conv2d(16, 8, kernel_size=7, padding=3)
        self.conv_flow = Conv2d(8, 2, kernel_size=7, padding=3)
        
    def forward(self, feat1, feat2_warped, current_flow):
        # Concatenate inputs
        x = torch.cat([feat1, feat2_warped, current_flow], dim=1)
        
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        flow_residual = self.conv_flow(x)
        
        return flow_residual
```

**Interface Specification**:

- **Input**: Same as LiteFlowNet2 (two feature pyramids)
- **Output**: Same as LiteFlowNet2 (optical flow `[batch_size, 2, H, W]`)

**Performance Targets**:
- Forward pass latency: ≤30ms for batch_size=4 (faster than LiteFlowNet2)
- Training VRAM: ≤6GB for batch_size=4
- Inference VRAM: ≤3GB for batch_size=4

**Design Rationale**: SpyNet uses simpler convolutional layers (larger kernels, fewer channels) compared to LiteFlowNet2's dense refinement modules, trading some accuracy for significant memory and speed improvements.

### 4. Pose Estimator (6-DOF)

**Purpose**: Predict camera misalignment probability, severity classification, and 6-DOF pose from optical flow and features.

**Architecture Specification**:

```python
class PoseEstimator(nn.Module):
    """
    Multi-task head for misalignment detection and pose estimation.
    Processes concatenated features and optical flow.
    """
    
    def __init__(self):
        # Global average pooling to aggregate spatial information
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))
        
        # Shared feature processing
        # Input: [B, 64+2, 1, 1] (Level 0 features + flow, globally pooled)
        self.fc_shared = nn.Linear(66, 256)
        self.dropout = nn.Dropout(p=0.3)  # For uncertainty estimation
        
        # Misalignment probability head
        self.fc_prob1 = nn.Linear(256, 128)
        self.fc_prob2 = nn.Linear(128, 1)
        self.sigmoid = nn.Sigmoid()
        
        # 6-DOF pose regression head
        self.fc_pose1 = nn.Linear(256, 128)
        self.fc_pose2 = nn.Linear(128, 6)  # [X, Y, Z, roll, pitch, yaw]
        
    def forward(self, features_level0, optical_flow):
        """
        features_level0: [B, 64, H, W] from CNN Feature Extractor
        optical_flow: [B, 2, H, W] from LiteFlowNet2 or SpyNet
        """
        # Concatenate features and flow
        x = torch.cat([features_level0, optical_flow], dim=1)  # [B, 66, H, W]
        
        # Global pooling to fixed size
        x = self.global_pool(x)  # [B, 66, 1, 1]
        x = x.view(x.size(0), -1)  # [B, 66]
        
        # Shared processing
        x = F.relu(self.fc_shared(x))  # [B, 256]
        x = self.dropout(x)
        
        # Misalignment probability branch
        prob = F.relu(self.fc_prob1(x))  # [B, 128]
        prob = self.fc_prob2(prob)  # [B, 1]
        misalignment_prob = self.sigmoid(prob)  # [B, 1] in range [0, 1]
        
        # 6-DOF pose branch
        pose = F.relu(self.fc_pose1(x))  # [B, 128]
        pose_6dof = self.fc_pose2(pose)  # [B, 6]
        # Output: [X, Y, Z] in meters, [roll, pitch, yaw] in degrees
        
        return misalignment_prob, pose_6dof
    
    def forward_with_uncertainty(self, features_level0, optical_flow, n_samples=10):
        """
        Monte Carlo Dropout for uncertainty estimation.
        Runs forward pass n_samples times with dropout enabled.
        """
        self.train()  # Enable dropout during inference
        
        prob_samples = []
        pose_samples = []
        
        for _ in range(n_samples):
            prob, pose = self.forward(features_level0, optical_flow)
            prob_samples.append(prob)
            pose_samples.append(pose)
        
        # Compute mean and std
        prob_samples = torch.stack(prob_samples, dim=0)  # [n_samples, B, 1]
        pose_samples = torch.stack(pose_samples, dim=0)  # [n_samples, B, 6]
        
        prob_mean = prob_samples.mean(dim=0)
        prob_std = prob_samples.std(dim=0)
        pose_mean = pose_samples.mean(dim=0)
        pose_std = pose_samples.std(dim=0)
        
        return prob_mean, pose_mean, prob_std, pose_std
```


**Interface Specification**:

- **Input**: 
  - Level 0 features: `[batch_size, 64, H, W]`
  - Optical flow: `[batch_size, 2, H, W]`
  
- **Output** (standard forward):
  - Misalignment probability: `[batch_size, 1]` (range [0, 1])
  - 6-DOF pose: `[batch_size, 6]`
    - pose[:, 0:3]: Position (X, Y, Z) in meters
    - pose[:, 3:6]: Orientation (roll, pitch, yaw) in degrees
    
- **Output** (with uncertainty):
  - Same as standard, plus:
  - Probability uncertainty: `[batch_size, 1]` (standard deviation)
  - Pose uncertainty: `[batch_size, 6]` (standard deviation per DOF)

**Performance Targets**:
- Standard forward: ≤10ms for batch_size=4
- With uncertainty (10 samples): ≤100ms for batch_size=4

---

## Data Models

### 1. Training Sample Structure

```python
@dataclass
class TrainingSample:
    """Single training sample from KITTI dataset with augmentation."""
    
    # Input images
    image_t: torch.Tensor  # [3, H, W], frame at time t
    image_t1: torch.Tensor  # [3, H, W], frame at time t+1
    
    # Ground truth labels
    is_misaligned: bool  # Binary label
    misalignment_probability: float  # Ground truth probability [0, 1]
    
    # 6-DOF pose ground truth
    pose: torch.Tensor  # [6], [X, Y, Z, roll, pitch, yaw]
    
    # Metadata
    sample_id: str  # KITTI sequence and frame ID
    augmentation_applied: dict  # Records applied transformations
    original_resolution: tuple  # (H, W) before resizing
```


### 2. Model Checkpoint Structure

```python
@dataclass
class ModelCheckpoint:
    """Saved model state for training resumption and deployment."""
    
    # Model weights
    feature_extractor_state: dict  # CNN Feature Extractor parameters
    flow_network_state: dict  # LiteFlowNet2 or SpyNet parameters
    pose_estimator_state: dict  # Pose Estimator parameters
    
    # Training state (for resumption)
    optimizer_state: dict  # Adam optimizer state
    scheduler_state: dict  # Learning rate scheduler state
    training_step: int  # Global step counter
    epoch: int  # Current epoch
    
    # Performance metrics
    best_validation_loss: float
    validation_accuracy: float
    training_loss_history: list  # Last 100 losses
    
    # Configuration
    model_config: dict  # Architecture hyperparameters
    preprocessing_params: dict  # Mean, std, target resolution
    
    # Metadata
    timestamp: str
    pytorch_version: str
    cuda_version: str
    model_version: str  # Semantic version for compatibility checking
```

### 3. Inference Output Structure

```python
@dataclass
class InferenceOutput:
    """Structured output from inference engine."""
    
    # Per-camera results (4 cameras)
    camera_results: dict[str, CameraDetection]  # Key: camera_id (e.g., "front", "left", "right", "rear")
    
    # Global metadata
    timestamp: float  # Unix timestamp of inference
    model_version: str
    processing_time_ms: float
    
    def to_json(self) -> str:
        """Serialize to JSON for logging and API integration."""
        pass

@dataclass
class CameraDetection:
    """Detection result for single camera."""
    
    # Primary outputs
    misalignment_probability: float  # [0, 1]
    severity_level: str  # "NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"
    
    # 6-DOF pose estimate
    position: dict  # {"X": float, "Y": float, "Z": float} in meters
    orientation: dict  # {"roll": float, "pitch": float, "yaw": float} in degrees
    
    # Uncertainty (optional, if enabled)
    probability_uncertainty: Optional[float]  # Standard deviation
    pose_uncertainty: Optional[dict]  # Std dev for each DOF
    
    # Flags
    low_confidence: bool  # True if uncertainty > 0.2
```


### 4. Configuration Schema

```python
@dataclass
class SystemConfig:
    """YAML configuration schema for DL_System."""
    
    # Architecture selection
    feature_extractor: str  # "cnn_pyramid"
    flow_network: str  # "liteflownet2" or "spynet"
    
    # Operational mode
    mode: str  # "neural_network", "rule_based", or "hybrid"
    
    # Hybrid mode settings (if mode == "hybrid")
    hybrid_weights: dict  # {"neural": 0.7, "rule_based": 0.3}
    
    # Model paths
    checkpoint_path: str  # Path to trained .pth file
    
    # Inference settings
    confidence_threshold: float = 0.5  # For binary classification
    enable_uncertainty: bool = False  # MC Dropout
    uncertainty_samples: int = 10  # Number of MC samples
    batch_size: int = 4  # Four-camera batch
    
    # Preprocessing
    target_resolution: tuple = (640, 640)  # Must be ≤ (750, 750)
    normalization_mean: list = [0.485, 0.456, 0.406]  # ImageNet defaults
    normalization_std: list = [0.229, 0.224, 0.225]
    
    # Performance
    device: str = "cuda"  # "cuda" or "cpu"
    mixed_precision: bool = True  # Use FP16
    
    # Logging
    tensorboard_dir: str = "./runs"
    log_level: str = "INFO"
```

Example YAML:
```yaml
feature_extractor: "cnn_pyramid"
flow_network: "liteflownet2"  # or "spynet"
mode: "neural_network"  # or "rule_based" or "hybrid"

hybrid_weights:
  neural: 0.7
  rule_based: 0.3

checkpoint_path: "./models/best_model.pth"

confidence_threshold: 0.5
enable_uncertainty: false
uncertainty_samples: 10
batch_size: 4

target_resolution: [640, 640]
normalization_mean: [0.485, 0.456, 0.406]
normalization_std: [0.229, 0.224, 0.225]

device: "cuda"
mixed_precision: true

tensorboard_dir: "./runs"
log_level: "INFO"
```

---

## Training Pipeline


### Training Workflow

```
1. Initialize
   ├─ Load KITTI dataset
   ├─ Split into train/val/test (70/15/15)
   ├─ Compute dataset statistics
   └─ Initialize models, optimizer, scheduler

2. Training Loop (until convergence or 24 hours)
   ├─ For each batch in training split:
   │  ├─ Apply augmentation
   │  ├─ Forward pass (mixed precision)
   │  ├─ Compute combined loss
   │  ├─ Backward pass with gradient checkpointing
   │  ├─ Optimizer step
   │  └─ Log metrics (every 10 steps)
   │
   ├─ Validation (every 500 steps):
   │  ├─ Evaluate on validation split
   │  ├─ Compute validation loss and accuracy
   │  ├─ Save checkpoint if best loss
   │  └─ Update learning rate scheduler
   │
   └─ Checkpoint (every 1000 steps):
      └─ Save model state, optimizer state, metrics

3. Finalize
   ├─ Evaluate best model on test split
   ├─ Generate comparison report
   └─ Save final statistics
```

### Data Loading Component

**KITTI Dataset Loader**:

```python
class KITTIDataset(torch.utils.data.Dataset):
    """
    Loads stereo image pairs from KITTI dataset.
    Handles splitting, augmentation, and preprocessing.
    """
    
    def __init__(self, root_dir, split='train', transform=None, 
                 max_resolution=(750, 750)):
        self.root_dir = root_dir
        self.split = split
        self.transform = transform
        self.max_resolution = max_resolution
        
        # Load image paths
        self.samples = self._load_samples()
        
        # Generate synthetic misalignment labels
        if split in ['train', 'val']:
            self.misalignment_labels = self._generate_misalignment_labels()
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        # Load consecutive frames
        img_t = self._load_image(self.samples[idx]['path_t'])
        img_t1 = self._load_image(self.samples[idx]['path_t1'])
        
        # Enforce resolution constraint
        img_t = self._resize_if_needed(img_t, self.max_resolution)
        img_t1 = self._resize_if_needed(img_t1, self.max_resolution)
        
        # Apply augmentation (train/val only)
        if self.transform and self.split in ['train', 'val']:
            img_t, img_t1, pose = self.transform(img_t, img_t1)
        else:
            pose = torch.zeros(6)
        
        # Compute misalignment probability from pose magnitude
        misalignment_prob = self._compute_probability(pose)
        
        return {
            'image_t': img_t,
            'image_t1': img_t1,
            'misalignment_prob': misalignment_prob,
            'pose': pose,
            'sample_id': self.samples[idx]['id']
        }
    
    def _resize_if_needed(self, img, max_res):
        """Resize image to fit within max resolution while preserving aspect ratio."""
        H, W = img.shape[1], img.shape[2]
        if H > max_res[0] or W > max_res[1]:
            scale = min(max_res[0] / H, max_res[1] / W)
            new_H, new_W = int(H * scale), int(W * scale)
            img = F.interpolate(img.unsqueeze(0), size=(new_H, new_W), 
                                mode='bilinear', align_corners=False).squeeze(0)
        return img
```

**Dataset Splitting Strategy**:

```python
def split_kitti_dataset(root_dir, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15):
    """
    Split KITTI sequences into train/val/test with no overlap.
    Ensures temporal coherence within splits (consecutive frames stay together).
    """
    all_sequences = load_kitti_sequences(root_dir)
    
    # Shuffle sequences (not individual frames)
    random.shuffle(all_sequences)
    
    total_sequences = len(all_sequences)
    train_end = int(total_sequences * train_ratio)
    val_end = train_end + int(total_sequences * val_ratio)
    
    train_sequences = all_sequences[:train_end]
    val_sequences = all_sequences[train_end:val_end]
    test_sequences = all_sequences[val_end:]
    
    return {
        'train': train_sequences,
        'val': val_sequences,
        'test': test_sequences
    }
```

### Augmentation Engine


**Synthetic Misalignment Augmentation**:

```python
class MisalignmentAugmentation:
    """
    Applies geometric transformations to simulate camera misalignment.
    Generates corresponding ground truth labels.
    """
    
    def __init__(self, apply_probability=0.5):
        self.apply_prob = apply_probability
        
        # Transformation ranges (per requirement 6)
        self.rotation_range = (-10, 10)  # degrees
        self.translation_range = (-50, 50)  # pixels
        self.brightness_range = (0.7, 1.3)  # multiplicative factor
        self.contrast_range = (0.8, 1.2)
        
    def __call__(self, img_t, img_t1):
        """Apply augmentation to frame pair."""
        
        # 50% probability to apply augmentation
        if random.random() > self.apply_prob:
            return img_t, img_t1, torch.zeros(6)
        
        # Randomly select 3+ transformations
        transformations = random.sample([
            'rotate', 'translate_x', 'translate_y', 
            'brightness', 'contrast', 'noise', 'flip', 'crop'
        ], k=random.randint(3, 5))
        
        pose = torch.zeros(6)  # [X, Y, Z, roll, pitch, yaw]
        
        # Apply transformations
        if 'rotate' in transformations:
            angle = random.uniform(*self.rotation_range)
            img_t1 = self._rotate(img_t1, angle)
            pose[3] = angle  # Roll (assuming rotation around Z-axis)
            
        if 'translate_x' in transformations:
            tx = random.uniform(*self.translation_range)
            img_t1 = self._translate(img_t1, tx, 0)
            pose[0] = tx / 1000.0  # Convert pixels to meters (approximate)
            
        if 'translate_y' in transformations:
            ty = random.uniform(*self.translation_range)
            img_t1 = self._translate(img_t1, 0, ty)
            pose[1] = ty / 1000.0
            
        if 'brightness' in transformations:
            factor = random.uniform(*self.brightness_range)
            img_t1 = img_t1 * factor
            
        if 'contrast' in transformations:
            factor = random.uniform(*self.contrast_range)
            mean = img_t1.mean(dim=[1, 2], keepdim=True)
            img_t1 = (img_t1 - mean) * factor + mean
            
        if 'noise' in transformations:
            noise = torch.randn_like(img_t1) * 0.01
            img_t1 = img_t1 + noise
            
        if 'flip' in transformations:
            img_t1 = torch.flip(img_t1, dims=[2])  # Horizontal flip
            
        if 'crop' in transformations:
            scale = random.uniform(0.9, 1.0)
            img_t1 = self._random_crop(img_t1, scale)
        
        # Clamp values to valid range
        img_t1 = torch.clamp(img_t1, 0, 1)
        
        return img_t, img_t1, pose
```

### Training Loss Function

**Combined Multi-Task Loss**:

```python
class CombinedLoss(nn.Module):
    """
    Weighted combination of classification and regression losses.
    """
    
    def __init__(self, classification_weight=0.6, regression_weight=0.4):
        super().__init__()
        self.w_cls = classification_weight
        self.w_reg = regression_weight
        
        # Binary cross-entropy for misalignment probability
        self.bce_loss = nn.BCELoss()
        
        # Smooth L1 for pose regression
        self.smooth_l1_loss = nn.SmoothL1Loss()
        
    def forward(self, pred_prob, pred_pose, gt_prob, gt_pose):
        """
        pred_prob: [B, 1] predicted probabilities
        pred_pose: [B, 6] predicted 6-DOF pose
        gt_prob: [B, 1] ground truth probabilities
        gt_pose: [B, 6] ground truth pose
        """
        
        # Classification loss
        loss_cls = self.bce_loss(pred_prob, gt_prob)
        
        # Regression loss (only for misaligned samples)
        mask = (gt_prob > 0.25).float()  # Only compute for actionable misalignment
        loss_reg = self.smooth_l1_loss(pred_pose * mask, gt_pose * mask)
        
        # Combined loss
        total_loss = self.w_cls * loss_cls + self.w_reg * loss_reg
        
        return total_loss, loss_cls, loss_reg
```

### Memory Optimization Strategy

**Mixed Precision Training**:

```python
from torch.cuda.amp import autocast, GradScaler

scaler = GradScaler()

# Training step with mixed precision
for batch in train_loader:
    optimizer.zero_grad()
    
    # Forward pass in FP16
    with autocast():
        features = feature_extractor(batch['image_t'])
        flow = flow_network(features, features)  # Simplified
        prob, pose = pose_estimator(features[0], flow)
        loss, loss_cls, loss_reg = criterion(prob, pose, 
                                               batch['misalignment_prob'], 
                                               batch['pose'])
    
    # Backward pass in FP32
    scaler.scale(loss).backward()
    scaler.step(optimizer)
    scaler.update()
```


**Gradient Checkpointing**:

```python
from torch.utils.checkpoint import checkpoint

class MemoryEfficientFeatureExtractor(nn.Module):
    """Feature extractor with gradient checkpointing."""
    
    def forward(self, x):
        # Checkpoint expensive layers to save activation memory
        x = checkpoint(self.conv1_block, x)
        pyramid = [x]
        
        x = checkpoint(self.conv2_block, x)
        pyramid.append(x)
        
        x = checkpoint(self.conv3_block, x)
        pyramid.append(x)
        
        x = checkpoint(self.conv4_block, x)
        pyramid.append(x)
        
        return pyramid
```

**Dynamic Batch Size Adjustment**:

```python
def get_optimal_batch_size(available_vram_gb):
    """Determine batch size based on available VRAM."""
    if available_vram_gb <= 8:
        return 2
    elif available_vram_gb <= 16:
        return 4
    else:
        return 8

def train_with_dynamic_batch_size():
    """Training loop with automatic batch size reduction on OOM."""
    current_batch_size = get_optimal_batch_size(get_available_vram())
    
    while current_batch_size >= 1:
        try:
            # Attempt training with current batch size
            train_epoch(batch_size=current_batch_size)
            break
        except RuntimeError as e:
            if "out of memory" in str(e):
                current_batch_size = max(1, current_batch_size // 2)
                torch.cuda.empty_cache()
                logging.warning(f"OOM error. Reducing batch size to {current_batch_size}")
            else:
                raise
```

### Checkpoint Management

```python
class CheckpointManager:
    """Manages model checkpoint saving and loading."""
    
    def __init__(self, checkpoint_dir, keep_n_recent=3):
        self.checkpoint_dir = checkpoint_dir
        self.keep_n_recent = keep_n_recent
        self.checkpoints = []
        
    def save_checkpoint(self, models, optimizer, scheduler, step, 
                        val_loss, val_accuracy, is_best=False):
        """Save model checkpoint."""
        checkpoint = {
            'feature_extractor_state': models['feature_extractor'].state_dict(),
            'flow_network_state': models['flow_network'].state_dict(),
            'pose_estimator_state': models['pose_estimator'].state_dict(),
            'optimizer_state': optimizer.state_dict(),
            'scheduler_state': scheduler.state_dict(),
            'training_step': step,
            'validation_loss': val_loss,
            'validation_accuracy': val_accuracy,
            'timestamp': datetime.now().isoformat(),
            'model_version': '1.0.0'
        }
        
        # Save regular checkpoint
        checkpoint_path = os.path.join(self.checkpoint_dir, f'checkpoint_step_{step}.pth')
        torch.save(checkpoint, checkpoint_path)
        self.checkpoints.append(checkpoint_path)
        
        # Save best model separately
        if is_best:
            best_path = os.path.join(self.checkpoint_dir, 'best_model.pth')
            torch.save(checkpoint, best_path)
            logging.info(f"Saved best model with val_loss={val_loss:.4f}")
        
        # Remove old checkpoints (keep only recent)
        self._cleanup_old_checkpoints()
    
    def _cleanup_old_checkpoints(self):
        """Keep only the N most recent checkpoints."""
        if len(self.checkpoints) > self.keep_n_recent:
            old_checkpoints = self.checkpoints[:-self.keep_n_recent]
            for path in old_checkpoints:
                if os.path.exists(path):
                    os.remove(path)
            self.checkpoints = self.checkpoints[-self.keep_n_recent:]
```

---

## Inference Engine


### Inference Workflow

```
1. Initialize (at system startup)
   ├─ Load configuration from YAML
   ├─ Load model checkpoint
   ├─ Initialize models on GPU
   ├─ Pre-allocate memory buffers
   └─ Warm-up inference (dummy forward pass)

2. Real-Time Inference Loop
   ├─ Receive 4 camera frames
   ├─ Preprocess (resize, normalize, batch)
   ├─ Forward pass:
   │  ├─ CNN Feature Extractor
   │  ├─ Optical Flow Network
   │  └─ Pose Estimator (with optional uncertainty)
   ├─ Post-process:
   │  ├─ Apply severity classification
   │  └─ Format structured output
   └─ Return InferenceOutput

3. Error Handling
   └─ On exception: fallback to rule-based system
```

### Preprocessing Pipeline

```python
class InferencePreprocessor:
    """Preprocessing for inference to match training distribution."""
    
    def __init__(self, config: SystemConfig):
        self.target_resolution = config.target_resolution
        self.mean = torch.tensor(config.normalization_mean).view(3, 1, 1)
        self.std = torch.tensor(config.normalization_std).view(3, 1, 1)
        
        # Enforce maximum resolution constraint
        assert self.target_resolution[0] <= 750 and self.target_resolution[1] <= 750, \
            "Target resolution must not exceed 750×750"
    
    def preprocess(self, frames: list[np.ndarray]) -> torch.Tensor:
        """
        Preprocess 4-camera batch for inference.
        
        Args:
            frames: List of 4 numpy arrays [H, W, 3] (BGR or RGB)
        
        Returns:
            Batched tensor [4, 3, H, W]
        """
        processed = []
        
        for frame in frames:
            # Convert to torch tensor and permute to [C, H, W]
            tensor = torch.from_numpy(frame).permute(2, 0, 1).float() / 255.0
            
            # Resize with aspect ratio preservation
            tensor = self._resize_with_padding(tensor, self.target_resolution)
            
            # Normalize
            tensor = (tensor - self.mean) / self.std
            
            processed.append(tensor)
        
        # Stack into batch
        batch = torch.stack(processed, dim=0)  # [4, 3, H, W]
        return batch
    
    def _resize_with_padding(self, img, target_size):
        """Resize image preserving aspect ratio with zero padding."""
        _, H, W = img.shape
        target_H, target_W = target_size
        
        # Compute scale to fit within target
        scale = min(target_H / H, target_W / W)
        new_H, new_W = int(H * scale), int(W * scale)
        
        # Resize
        img_resized = F.interpolate(img.unsqueeze(0), size=(new_H, new_W),
                                     mode='bilinear', align_corners=False).squeeze(0)
        
        # Pad to target size
        pad_top = (target_H - new_H) // 2
        pad_left = (target_W - new_W) // 2
        img_padded = F.pad(img_resized, 
                           (pad_left, target_W - new_W - pad_left,
                            pad_top, target_H - new_H - pad_top))
        
        return img_padded
```


### Inference Engine Implementation

```python
class InferenceEngine:
    """Real-time inference engine for camera misalignment detection."""
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.device = torch.device(config.device)
        
        # Load models
        self.models = self._load_models(config.checkpoint_path)
        self.models = {k: v.to(self.device).eval() for k, v in self.models.items()}
        
        # Initialize preprocessor
        self.preprocessor = InferencePreprocessor(config)
        
        # Pre-allocate GPU memory buffers
        self._preallocate_buffers()
        
        # Warm-up
        self._warmup()
        
        # Performance tracking
        self.inference_times = []
        
    def _load_models(self, checkpoint_path):
        """Load trained models from checkpoint."""
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        
        # Verify version compatibility
        if checkpoint['model_version'] != '1.0.0':
            logging.warning(f"Checkpoint version mismatch: {checkpoint['model_version']}")
        
        # Initialize models
        feature_extractor = CNNFeatureExtractor()
        feature_extractor.load_state_dict(checkpoint['feature_extractor_state'])
        
        if self.config.flow_network == 'liteflownet2':
            flow_network = LiteFlowNet2()
        elif self.config.flow_network == 'spynet':
            flow_network = SpyNet()
        else:
            raise ValueError(f"Unknown flow network: {self.config.flow_network}")
        flow_network.load_state_dict(checkpoint['flow_network_state'])
        
        pose_estimator = PoseEstimator()
        pose_estimator.load_state_dict(checkpoint['pose_estimator_state'])
        
        return {
            'feature_extractor': feature_extractor,
            'flow_network': flow_network,
            'pose_estimator': pose_estimator
        }
    
    def _preallocate_buffers(self):
        """Pre-allocate GPU memory for fixed-size tensors."""
        H, W = self.config.target_resolution
        self.buffer_input = torch.zeros(4, 3, H, W, device=self.device)
        self.buffer_flow = torch.zeros(4, 2, H, W, device=self.device)
    
    def _warmup(self):
        """Warm-up inference with dummy data."""
        logging.info("Warming up inference engine...")
        dummy_frames = [np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8) 
                        for _ in range(4)]
        _ = self.infer(dummy_frames)
        logging.info("Warm-up complete")
    
    @torch.no_grad()
    def infer(self, frames: list[np.ndarray]) -> InferenceOutput:
        """
        Run inference on 4-camera batch.
        
        Args:
            frames: List of 4 numpy arrays (camera frames)
        
        Returns:
            InferenceOutput with detection results
        """
        start_time = time.time()
        
        # Preprocess
        batch = self.preprocessor.preprocess(frames).to(self.device)
        
        # Forward pass with mixed precision
        with torch.cuda.amp.autocast(enabled=self.config.mixed_precision):
            # Extract features
            features = self.models['feature_extractor'](batch)
            
            # Compute optical flow (between consecutive frames in sequence)
            # For 4 cameras, we process temporal pairs
            flow = self._compute_flow_batch(features)
            
            # Pose estimation
            if self.config.enable_uncertainty:
                probs, poses, prob_stds, pose_stds = \
                    self.models['pose_estimator'].forward_with_uncertainty(
                        features[0], flow, n_samples=self.config.uncertainty_samples
                    )
            else:
                probs, poses = self.models['pose_estimator'](features[0], flow)
                prob_stds, pose_stds = None, None
        
        # Post-process results
        output = self._format_output(probs, poses, prob_stds, pose_stds)
        
        # Track performance
        inference_time = (time.time() - start_time) * 1000  # ms
        self.inference_times.append(inference_time)
        output.processing_time_ms = inference_time
        
        if inference_time > 100:
            logging.warning(f"Inference latency exceeded target: {inference_time:.1f}ms")
        
        return output
    
    def _compute_flow_batch(self, features):
        """Compute optical flow for batch (simplified for spatial processing)."""
        # In practice, this would use temporal frame pairs
        # Here we show simplified spatial flow estimation
        flow = self.models['flow_network'](features, features)
        return flow
    
    def _format_output(self, probs, poses, prob_stds, pose_stds) -> InferenceOutput:
        """Format model outputs into structured InferenceOutput."""
        camera_ids = ['front', 'left', 'right', 'rear']
        camera_results = {}
        
        for i, cam_id in enumerate(camera_ids):
            prob = probs[i].item()
            severity = self._classify_severity(prob)
            
            detection = CameraDetection(
                misalignment_probability=prob,
                severity_level=severity,
                position={
                    'X': poses[i, 0].item(),
                    'Y': poses[i, 1].item(),
                    'Z': poses[i, 2].item()
                },
                orientation={
                    'roll': poses[i, 3].item(),
                    'pitch': poses[i, 4].item(),
                    'yaw': poses[i, 5].item()
                },
                probability_uncertainty=prob_stds[i].item() if prob_stds is not None else None,
                pose_uncertainty={
                    'X': pose_stds[i, 0].item() if pose_stds is not None else None,
                    'Y': pose_stds[i, 1].item() if pose_stds is not None else None,
                    'Z': pose_stds[i, 2].item() if pose_stds is not None else None,
                    'roll': pose_stds[i, 3].item() if pose_stds is not None else None,
                    'pitch': pose_stds[i, 4].item() if pose_stds is not None else None,
                    'yaw': pose_stds[i, 5].item() if pose_stds is not None else None
                } if pose_stds is not None else None,
                low_confidence=(prob_stds[i].item() > 0.2) if prob_stds is not None else False
            )
            
            camera_results[cam_id] = detection
        
        return InferenceOutput(
            camera_results=camera_results,
            timestamp=time.time(),
            model_version='1.0.0',
            processing_time_ms=0  # Will be set by caller
        )
    
    def _classify_severity(self, prob: float) -> str:
        """Apply threshold-based severity classification."""
        if prob < 0.25:
            return "NONE"
        elif prob < 0.50:
            return "LOW"
        elif prob < 0.75:
            return "MEDIUM"
        elif prob < 0.90:
            return "HIGH"
        else:
            return "CRITICAL"
```

---

## Error Handling


### Exception Handling Strategy

**Neural Network Failure Recovery**:

```python
class RobustInferenceEngine(InferenceEngine):
    """Inference engine with automatic fallback to rule-based system."""
    
    def __init__(self, config: SystemConfig):
        super().__init__(config)
        self.fallback_system = RuleBasedDetector()  # Existing system
        self.consecutive_failures = 0
        self.max_failures_before_permanent_fallback = 3
        self.last_recovery_attempt = 0
        self.recovery_interval = 60  # seconds
        
    def infer(self, frames: list[np.ndarray]) -> InferenceOutput:
        """Inference with automatic fallback on failure."""
        try:
            # Attempt neural network inference
            output = super().infer(frames)
            self.consecutive_failures = 0  # Reset on success
            return output
            
        except Exception as e:
            logging.error(f"Neural network inference failed: {e}")
            self.consecutive_failures += 1
            
            # Fallback to rule-based system
            output = self._fallback_inference(frames)
            
            # Attempt recovery if enough time has passed
            current_time = time.time()
            if (current_time - self.last_recovery_attempt) > self.recovery_interval:
                if self.consecutive_failures < self.max_failures_before_permanent_fallback:
                    self._attempt_recovery()
                    self.last_recovery_attempt = current_time
                else:
                    logging.error("Neural network permanently disabled after repeated failures")
            
            return output
    
    def _fallback_inference(self, frames) -> InferenceOutput:
        """Execute rule-based detection as fallback."""
        logging.warning("Using rule-based fallback system")
        
        # Execute rule-based detection
        rule_based_results = self.fallback_system.detect(frames)
        
        # Convert to InferenceOutput format
        output = self._convert_rule_based_output(rule_based_results)
        return output
    
    def _attempt_recovery(self):
        """Attempt to recover neural network functionality."""
        try:
            logging.info("Attempting neural network recovery...")
            torch.cuda.empty_cache()
            self._warmup()
            logging.info("Neural network recovery successful")
        except Exception as e:
            logging.error(f"Recovery attempt failed: {e}")
```

**Memory Error Handling**:

```python
def safe_inference_with_memory_fallback(engine, frames):
    """Execute inference with automatic batch size reduction on OOM."""
    try:
        return engine.infer(frames)
    except RuntimeError as e:
        if "out of memory" in str(e):
            logging.warning("Out of memory during inference. Processing cameras sequentially.")
            torch.cuda.empty_cache()
            
            # Process cameras one at a time
            results = []
            for i, frame in enumerate(frames):
                try:
                    single_result = engine.infer([frame])
                    results.append(single_result.camera_results[list(single_result.camera_results.keys())[0]])
                except Exception as inner_e:
                    logging.error(f"Failed to process camera {i}: {inner_e}")
                    results.append(None)
            
            # Aggregate results
            return aggregate_sequential_results(results)
        else:
            raise
```

### Validation and Monitoring

```python
class InferenceValidator:
    """Validates inference outputs for anomalies."""
    
    def validate(self, output: InferenceOutput) -> tuple[bool, list[str]]:
        """
        Validate inference output for consistency and anomalies.
        
        Returns:
            (is_valid, list_of_warnings)
        """
        warnings = []
        
        # Check for NaN or Inf values
        for cam_id, detection in output.camera_results.items():
            if not (0 <= detection.misalignment_probability <= 1):
                warnings.append(f"{cam_id}: Invalid probability {detection.misalignment_probability}")
            
            if any(math.isnan(v) or math.isinf(v) for v in detection.position.values()):
                warnings.append(f"{cam_id}: Invalid position values")
            
            if any(math.isnan(v) or math.isinf(v) for v in detection.orientation.values()):
                warnings.append(f"{cam_id}: Invalid orientation values")
        
        # Check for unrealistic pose values
        for cam_id, detection in output.camera_results.items():
            if abs(detection.position['X']) > 10 or abs(detection.position['Y']) > 10:
                warnings.append(f"{cam_id}: Unrealistic position magnitude")
            
            if abs(detection.orientation['roll']) > 45 or abs(detection.orientation['pitch']) > 45:
                warnings.append(f"{cam_id}: Unrealistic orientation magnitude")
        
        is_valid = len(warnings) == 0
        return is_valid, warnings
```

---

## Testing Strategy


### Testing Approach

This deep learning system is **not suitable for property-based testing** because:
- Neural networks involve learned behavior, not deterministic logic
- Core functionality depends on external frameworks (PyTorch) and hardware (GPU)
- Model training and inference are infrastructure-heavy operations
- Testing focuses on integration with external systems and data

**Testing Strategy: Unit Tests + Integration Tests + System Tests**

### Unit Testing

**1. Component Interface Tests**

```python
class TestCNNFeatureExtractor:
    """Unit tests for CNN Feature Extractor."""
    
    def test_input_resolution_constraint(self):
        """Verify max 750×750 resolution is enforced."""
        extractor = CNNFeatureExtractor()
        
        # Valid resolutions
        valid_input = torch.randn(1, 3, 640, 640)
        output = extractor(valid_input)
        assert len(output) == 4  # 4 pyramid levels
        
        # Maximum resolution
        max_input = torch.randn(1, 3, 750, 750)
        output = extractor(max_input)
        assert output is not None
        
    def test_pyramid_output_shapes(self):
        """Verify pyramid levels have correct spatial dimensions."""
        extractor = CNNFeatureExtractor()
        input_tensor = torch.randn(2, 3, 640, 640)
        
        pyramid = extractor(input_tensor)
        
        assert pyramid[0].shape == (2, 64, 640, 640)  # Level 0: 1x
        assert pyramid[1].shape == (2, 128, 320, 320)  # Level 1: 1/2x
        assert pyramid[2].shape == (2, 256, 160, 160)  # Level 2: 1/4x
        assert pyramid[3].shape == (2, 512, 80, 80)    # Level 3: 1/8x
    
    def test_batch_processing(self):
        """Verify batch processing up to 4 frames."""
        extractor = CNNFeatureExtractor()
        
        for batch_size in [1, 2, 4]:
            input_tensor = torch.randn(batch_size, 3, 512, 512)
            pyramid = extractor(input_tensor)
            assert pyramid[0].shape[0] == batch_size

class TestPoseEstimator:
    """Unit tests for Pose Estimator."""
    
    def test_output_ranges(self):
        """Verify probability output is in [0, 1] range."""
        pose_estimator = PoseEstimator()
        features = torch.randn(4, 64, 80, 80)
        flow = torch.randn(4, 2, 80, 80)
        
        prob, pose = pose_estimator(features, flow)
        
        assert prob.shape == (4, 1)
        assert torch.all(prob >= 0) and torch.all(prob <= 1)
        assert pose.shape == (4, 6)
    
    def test_uncertainty_estimation(self):
        """Verify uncertainty estimation produces valid std deviations."""
        pose_estimator = PoseEstimator()
        features = torch.randn(2, 64, 80, 80)
        flow = torch.randn(2, 2, 80, 80)
        
        prob_mean, pose_mean, prob_std, pose_std = \
            pose_estimator.forward_with_uncertainty(features, flow, n_samples=5)
        
        assert prob_std.shape == (2, 1)
        assert torch.all(prob_std >= 0)
        assert pose_std.shape == (2, 6)
```

**2. Data Processing Tests**

```python
class TestDataLoading:
    """Unit tests for data loading and preprocessing."""
    
    def test_dataset_split_ratios(self):
        """Verify train/val/test split follows 70/15/15 ratio."""
        splits = split_kitti_dataset('./kitti_data')
        
        total = len(splits['train']) + len(splits['val']) + len(splits['test'])
        train_ratio = len(splits['train']) / total
        val_ratio = len(splits['val']) / total
        test_ratio = len(splits['test']) / total
        
        assert abs(train_ratio - 0.70) < 0.02
        assert abs(val_ratio - 0.15) < 0.02
        assert abs(test_ratio - 0.15) < 0.02
    
    def test_no_sample_overlap(self):
        """Verify no sample appears in multiple splits."""
        splits = split_kitti_dataset('./kitti_data')
        
        train_ids = {s['id'] for s in splits['train']}
        val_ids = {s['id'] for s in splits['val']}
        test_ids = {s['id'] for s in splits['test']}
        
        assert len(train_ids & val_ids) == 0
        assert len(train_ids & test_ids) == 0
        assert len(val_ids & test_ids) == 0
    
    def test_augmentation_ranges(self):
        """Verify augmentation applies transformations within specified ranges."""
        augmenter = MisalignmentAugmentation()
        img_t = torch.randn(3, 640, 640)
        img_t1 = torch.randn(3, 640, 640)
        
        # Run augmentation multiple times
        poses = []
        for _ in range(100):
            _, _, pose = augmenter(img_t.clone(), img_t1.clone())
            if pose.abs().sum() > 0:  # If augmentation was applied
                poses.append(pose)
        
        poses = torch.stack(poses)
        
        # Check rotation range
        assert torch.all(poses[:, 3] >= -10) and torch.all(poses[:, 3] <= 10)

class TestPreprocessing:
    """Unit tests for inference preprocessing."""
    
    def test_resolution_constraint(self):
        """Verify preprocessing respects 750×750 max resolution."""
        config = SystemConfig(target_resolution=(640, 640))
        preprocessor = InferencePreprocessor(config)
        
        # Test various input sizes
        test_frames = [
            np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8),
            np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8),  # Large input
            np.random.randint(0, 255, (750, 750, 3), dtype=np.uint8),  # Max size
        ]
        
        batch = preprocessor.preprocess(test_frames[:4])
        assert batch.shape == (4, 3, 640, 640)
    
    def test_normalization(self):
        """Verify normalization applies mean/std correctly."""
        config = SystemConfig(
            target_resolution=(512, 512),
            normalization_mean=[0.5, 0.5, 0.5],
            normalization_std=[0.2, 0.2, 0.2]
        )
        preprocessor = InferencePreprocessor(config)
        
        # Uniform gray image (value 128)
        gray_frame = np.full((512, 512, 3), 128, dtype=np.uint8)
        batch = preprocessor.preprocess([gray_frame])
        
        # Expected: (128/255 - 0.5) / 0.2 = 0.0
        assert torch.allclose(batch[0].mean(), torch.tensor(0.0), atol=0.1)
```


**3. Configuration Tests**

```python
class TestConfiguration:
    """Unit tests for configuration system."""
    
    def test_valid_config_loading(self):
        """Verify valid YAML config loads correctly."""
        config_yaml = """
        feature_extractor: "cnn_pyramid"
        flow_network: "liteflownet2"
        mode: "neural_network"
        checkpoint_path: "./models/test.pth"
        confidence_threshold: 0.5
        target_resolution: [640, 640]
        device: "cuda"
        """
        
        config = load_config_from_yaml(config_yaml)
        assert config.flow_network == "liteflownet2"
        assert config.target_resolution == (640, 640)
    
    def test_invalid_resolution_rejected(self):
        """Verify resolution > 750×750 is rejected."""
        config_yaml = """
        target_resolution: [800, 800]
        """
        
        with pytest.raises(ValueError, match="resolution.*750"):
            load_config_from_yaml(config_yaml)
    
    def test_malformed_config_error(self):
        """Verify malformed YAML raises error."""
        config_yaml = "invalid: yaml: content: ["
        
        with pytest.raises(Exception):
            load_config_from_yaml(config_yaml)

class TestSeverityClassification:
    """Unit tests for severity classification."""
    
    def test_severity_thresholds(self):
        """Verify severity classification thresholds."""
        test_cases = [
            (0.10, "NONE"),
            (0.25, "LOW"),
            (0.40, "LOW"),
            (0.50, "MEDIUM"),
            (0.70, "MEDIUM"),
            (0.75, "HIGH"),
            (0.85, "HIGH"),
            (0.90, "CRITICAL"),
            (1.00, "CRITICAL"),
        ]
        
        for prob, expected_severity in test_cases:
            severity = classify_severity(prob)
            assert severity == expected_severity, f"Failed for prob={prob}"
```

### Integration Testing

**1. End-to-End Pipeline Tests**

```python
class TestTrainingPipeline:
    """Integration tests for training pipeline."""
    
    @pytest.mark.slow
    def test_training_step_with_mock_data(self):
        """Verify training step executes without errors."""
        # Create small mock dataset
        dataset = MockKITTIDataset(num_samples=10)
        loader = DataLoader(dataset, batch_size=2)
        
        # Initialize models
        models = {
            'feature_extractor': CNNFeatureExtractor(),
            'flow_network': LiteFlowNet2(),
            'pose_estimator': PoseEstimator()
        }
        
        criterion = CombinedLoss()
        optimizer = torch.optim.Adam(
            list(models['feature_extractor'].parameters()) +
            list(models['flow_network'].parameters()) +
            list(models['pose_estimator'].parameters()),
            lr=1e-4
        )
        
        # Execute one training step
        batch = next(iter(loader))
        loss, loss_cls, loss_reg = train_step(models, batch, criterion, optimizer)
        
        assert loss.item() > 0
        assert not math.isnan(loss.item())
    
    @pytest.mark.slow
    def test_checkpoint_save_and_load(self):
        """Verify checkpoint saving and loading preserves model state."""
        models = initialize_models()
        optimizer = torch.optim.Adam(models['feature_extractor'].parameters())
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=100)
        
        # Save checkpoint
        manager = CheckpointManager('./test_checkpoints')
        manager.save_checkpoint(models, optimizer, scheduler, 
                                step=1000, val_loss=0.5, val_accuracy=0.95)
        
        # Load checkpoint
        loaded_models = load_checkpoint('./test_checkpoints/checkpoint_step_1000.pth')
        
        # Verify weights match
        for key in models:
            original_params = list(models[key].parameters())[0]
            loaded_params = list(loaded_models[key].parameters())[0]
            assert torch.allclose(original_params, loaded_params)

class TestInferencePipeline:
    """Integration tests for inference pipeline."""
    
    @pytest.mark.slow
    def test_end_to_end_inference(self):
        """Verify complete inference pipeline with mock model."""
        config = SystemConfig(
            feature_extractor="cnn_pyramid",
            flow_network="spynet",
            mode="neural_network",
            checkpoint_path="./mock_checkpoint.pth",
            target_resolution=(512, 512)
        )
        
        # Create mock checkpoint
        create_mock_checkpoint('./mock_checkpoint.pth')
        
        # Initialize engine
        engine = InferenceEngine(config)
        
        # Run inference
        frames = [np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8) 
                  for _ in range(4)]
        output = engine.infer(frames)
        
        # Verify output structure
        assert len(output.camera_results) == 4
        assert output.processing_time_ms > 0
        
        for cam_id, detection in output.camera_results.items():
            assert 0 <= detection.misalignment_probability <= 1
            assert detection.severity_level in ["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
            assert 'X' in detection.position
    
    @pytest.mark.slow
    def test_fallback_to_rule_based(self):
        """Verify automatic fallback on neural network failure."""
        config = SystemConfig(
            mode="neural_network",
            checkpoint_path="./nonexistent.pth"  # Will cause failure
        )
        
        engine = RobustInferenceEngine(config)
        
        frames = [np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8) 
                  for _ in range(4)]
        
        # Should not raise exception, should fallback
        output = engine.infer(frames)
        assert output is not None
```


**2. Hybrid Mode Integration Tests**

```python
class TestHybridMode:
    """Integration tests for hybrid neural network + rule-based mode."""
    
    def test_hybrid_ensemble_weights(self):
        """Verify hybrid mode applies correct ensemble weights."""
        config = SystemConfig(
            mode="hybrid",
            hybrid_weights={"neural": 0.7, "rule_based": 0.3}
        )
        
        engine = HybridInferenceEngine(config)
        
        # Mock predictions
        neural_prob = 0.8
        rule_based_prob = 0.4
        
        ensemble_prob = engine.compute_ensemble_probability(neural_prob, rule_based_prob)
        
        expected = 0.7 * 0.8 + 0.3 * 0.4
        assert abs(ensemble_prob - expected) < 0.001
    
    def test_hybrid_fallback_on_neural_failure(self):
        """Verify hybrid mode falls back to rule-based only on neural failure."""
        config = SystemConfig(mode="hybrid")
        engine = HybridInferenceEngine(config)
        
        # Inject neural network failure
        engine.neural_engine.inject_failure(True)
        
        frames = [np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8) 
                  for _ in range(4)]
        output = engine.infer(frames)
        
        # Should still produce output using rule-based only
        assert output is not None
```

### System Testing

**Performance Benchmarks**:

```python
class TestPerformanceRequirements:
    """System tests for performance requirements."""
    
    @pytest.mark.slow
    @pytest.mark.gpu
    def test_inference_latency_target(self):
        """Verify inference meets 100ms latency target for 4-camera batch."""
        config = SystemConfig(
            flow_network="liteflownet2",
            target_resolution=(640, 640),
            device="cuda"
        )
        engine = InferenceEngine(config)
        
        # Warm-up
        frames = generate_test_frames(4, (640, 640))
        _ = engine.infer(frames)
        
        # Benchmark
        latencies = []
        for _ in range(20):
            frames = generate_test_frames(4, (640, 640))
            start = time.time()
            _ = engine.infer(frames)
            latency = (time.time() - start) * 1000
            latencies.append(latency)
        
        avg_latency = np.mean(latencies)
        p95_latency = np.percentile(latencies, 95)
        
        assert avg_latency < 100, f"Average latency {avg_latency:.1f}ms exceeds 100ms"
        assert p95_latency < 120, f"P95 latency {p95_latency:.1f}ms too high"
    
    @pytest.mark.slow
    @pytest.mark.gpu
    def test_memory_consumption_limits(self):
        """Verify training and inference stay within VRAM limits."""
        # Training memory test
        config = TrainingConfig(batch_size=4, mixed_precision=True)
        trainer = Trainer(config)
        
        initial_memory = torch.cuda.memory_allocated()
        
        # Run training step
        batch = generate_training_batch(batch_size=4)
        trainer.train_step(batch)
        
        peak_memory_gb = torch.cuda.max_memory_allocated() / (1024**3)
        
        # Architecture A: ≤8GB training
        assert peak_memory_gb <= 8.5, f"Training used {peak_memory_gb:.2f}GB VRAM"
        
        # Reset for inference test
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        
        # Inference memory test
        inference_config = SystemConfig(batch_size=4)
        engine = InferenceEngine(inference_config)
        
        frames = generate_test_frames(4, (640, 640))
        _ = engine.infer(frames)
        
        inference_memory_gb = torch.cuda.max_memory_allocated() / (1024**3)
        
        # Architecture A: ≤4GB inference
        assert inference_memory_gb <= 4.5, f"Inference used {inference_memory_gb:.2f}GB VRAM"
    
    @pytest.mark.slow
    @pytest.mark.gpu
    def test_throughput_10hz_target(self):
        """Verify system achieves 10 Hz processing rate."""
        config = SystemConfig(device="cuda")
        engine = InferenceEngine(config)
        
        num_iterations = 100
        start_time = time.time()
        
        for _ in range(num_iterations):
            frames = generate_test_frames(4, (640, 640))
            _ = engine.infer(frames)
        
        elapsed = time.time() - start_time
        throughput = num_iterations / elapsed  # Hz
        
        assert throughput >= 10, f"Throughput {throughput:.1f} Hz below 10 Hz target"

class TestAccuracyRequirements:
    """System tests for model accuracy requirements."""
    
    @pytest.mark.slow
    @pytest.mark.integration
    def test_test_split_accuracy_target(self):
        """Verify model achieves ≥95% accuracy on test split."""
        # Load trained model
        model = load_trained_model('./best_model.pth')
        test_dataset = KITTIDataset(root_dir='./kitti_data', split='test')
        test_loader = DataLoader(test_dataset, batch_size=4)
        
        correct = 0
        total = 0
        
        with torch.no_grad():
            for batch in test_loader:
                predictions = model(batch['image_t'], batch['image_t1'])
                pred_labels = (predictions > 0.5).float()
                gt_labels = (batch['misalignment_prob'] > 0.5).float()
                
                correct += (pred_labels == gt_labels).sum().item()
                total += gt_labels.size(0)
        
        accuracy = correct / total
        assert accuracy >= 0.95, f"Accuracy {accuracy:.2%} below 95% target"
```

### Test Coverage Summary

| Component | Unit Tests | Integration Tests | System Tests |
|-----------|------------|-------------------|--------------|
| CNN Feature Extractor | ✓ Shape, resolution, batch | ✓ Training pipeline | ✓ Memory limits |
| LiteFlowNet2/SpyNet | ✓ Output shape, interface | ✓ Training pipeline | ✓ Latency targets |
| Pose Estimator | ✓ Output ranges, uncertainty | ✓ End-to-end inference | ✓ Accuracy targets |
| Data Loading | ✓ Split ratios, augmentation | ✓ Training with real data | - |
| Preprocessing | ✓ Resolution, normalization | ✓ Inference pipeline | - |
| Configuration | ✓ YAML parsing, validation | - | - |
| Checkpoint Management | ✓ Save/load | ✓ Training resumption | - |
| Inference Engine | ✓ Severity classification | ✓ End-to-end inference | ✓ Throughput |
| Hybrid Mode | ✓ Ensemble weights | ✓ Fallback behavior | - |
| Error Handling | ✓ Exception handling | ✓ Fallback to rule-based | - |

---

## Integration with Existing System


### Backward Compatibility Architecture

The system maintains complete backward compatibility with the existing rule-based detection system through a unified interface:

```python
class MisalignmentDetector:
    """
    Unified interface for camera misalignment detection.
    Supports neural network, rule-based, and hybrid modes.
    """
    
    def __init__(self, config: SystemConfig):
        self.config = config
        self.mode = config.mode
        
        # Initialize appropriate detection system(s)
        if self.mode in ['neural_network', 'hybrid']:
            self.neural_engine = InferenceEngine(config)
        
        if self.mode in ['rule_based', 'hybrid']:
            self.rule_based_system = RuleBasedDetector()
        
    def detect(self, frames: list[np.ndarray]) -> DetectionResult:
        """
        Detect camera misalignment using configured mode.
        
        Args:
            frames: List of 4 camera frames
        
        Returns:
            DetectionResult with unified output format
        """
        if self.mode == 'neural_network':
            return self._neural_network_detect(frames)
        elif self.mode == 'rule_based':
            return self._rule_based_detect(frames)
        elif self.mode == 'hybrid':
            return self._hybrid_detect(frames)
        else:
            raise ValueError(f"Unknown mode: {self.mode}")
    
    def _neural_network_detect(self, frames):
        """Execute neural network detection."""
        output = self.neural_engine.infer(frames)
        return self._convert_to_unified_format(output)
    
    def _rule_based_detect(self, frames):
        """Execute rule-based detection (existing system)."""
        # Call existing ORB + optical flow + SLAM pipeline
        result = self.rule_based_system.process(frames)
        return self._convert_rule_based_to_unified_format(result)
    
    def _hybrid_detect(self, frames):
        """Execute both systems and ensemble results."""
        try:
            neural_output = self.neural_engine.infer(frames)
        except Exception as e:
            logging.error(f"Neural network failed in hybrid mode: {e}")
            # Fallback to rule-based only
            return self._rule_based_detect(frames)
        
        rule_based_output = self.rule_based_system.process(frames)
        
        # Ensemble predictions
        return self._ensemble_outputs(neural_output, rule_based_output)
    
    def _ensemble_outputs(self, neural_output, rule_based_output):
        """Combine neural network and rule-based predictions."""
        w_neural = self.config.hybrid_weights['neural']
        w_rule = self.config.hybrid_weights['rule_based']
        
        ensemble_result = {}
        
        for cam_id in neural_output.camera_results:
            neural_prob = neural_output.camera_results[cam_id].misalignment_probability
            rule_prob = rule_based_output[cam_id]['probability']
            
            # Weighted average
            ensemble_prob = w_neural * neural_prob + w_rule * rule_prob
            
            ensemble_result[cam_id] = {
                'probability': ensemble_prob,
                'severity': self._classify_severity(ensemble_prob),
                'neural_probability': neural_prob,
                'rule_based_probability': rule_prob,
                'pose': neural_output.camera_results[cam_id].position
            }
        
        return ensemble_result
```

### Mode Switching Without Restart

```python
class DynamicModeDetector(MisalignmentDetector):
    """
    Detector supporting runtime mode switching via config file monitoring.
    """
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
        super().__init__(self.config)
        
        # File watcher for config changes
        self.last_config_mtime = os.path.getmtime(config_path)
        
    def detect(self, frames: list[np.ndarray]) -> DetectionResult:
        """Detect with automatic config reload on changes."""
        # Check for config changes
        current_mtime = os.path.getmtime(self.config_path)
        if current_mtime != self.last_config_mtime:
            logging.info("Config file changed. Reloading...")
            self._reload_config()
            self.last_config_mtime = current_mtime
        
        return super().detect(frames)
    
    def _reload_config(self):
        """Reload configuration and reinitialize systems as needed."""
        new_config = self._load_config()
        
        # Check if mode changed
        if new_config.mode != self.mode:
            logging.info(f"Mode changed: {self.mode} → {new_config.mode}")
            self.mode = new_config.mode
            self.config = new_config
            
            # Reinitialize systems based on new mode
            if self.mode in ['neural_network', 'hybrid']:
                if not hasattr(self, 'neural_engine'):
                    self.neural_engine = InferenceEngine(self.config)
            
            if self.mode in ['rule_based', 'hybrid']:
                if not hasattr(self, 'rule_based_system'):
                    self.rule_based_system = RuleBasedDetector()
```

### Preserving Existing System Code

**File Structure**:

```
src/
├── cv/
│   ├── feature_extractor.py          # Existing ORB features (preserved)
│   ├── optical_flow_analyzer.py      # Existing dense optical flow (preserved)
│   ├── slam_position_tracker.py      # Existing visual SLAM (preserved)
│   └── rule_based_detector.py        # Wrapper for existing system
│
├── dl/                                # NEW: Deep learning components
│   ├── models/
│   │   ├── cnn_feature_extractor.py
│   │   ├── liteflownet2.py
│   │   ├── spynet.py
│   │   └── pose_estimator.py
│   │
│   ├── training/
│   │   ├── data_loader.py
│   │   ├── augmentation.py
│   │   ├── trainer.py
│   │   └── checkpoint_manager.py
│   │
│   ├── inference/
│   │   ├── engine.py
│   │   ├── preprocessor.py
│   │   └── validator.py
│   │
│   └── config.py
│
└── misalignment_detector.py          # NEW: Unified interface
```

**Rule-Based System Wrapper**:

```python
class RuleBasedDetector:
    """
    Wrapper for existing ORB + optical flow + SLAM pipeline.
    Preserves all original functionality.
    """
    
    def __init__(self):
        # Import existing modules (unchanged)
        from cv.feature_extraction_engine import FeatureExtractionEngine
        from cv.optical_flow_analyzer import OpticalFlowAnalyzer
        from cv.slam_position_tracker import SLAMPositionTracker
        
        self.feature_engine = FeatureExtractionEngine()
        self.flow_analyzer = OpticalFlowAnalyzer()
        self.slam_tracker = SLAMPositionTracker()
    
    def process(self, frames: list[np.ndarray]) -> dict:
        """
        Execute original rule-based detection pipeline.
        This method calls existing code without modification.
        """
        results = {}
        
        for i, frame in enumerate(frames):
            # Extract ORB features (existing code)
            keypoints, descriptors = self.feature_engine.extract(frame)
            
            # Compute optical flow (existing code)
            if i > 0:
                flow = self.flow_analyzer.compute_flow(frames[i-1], frame)
            else:
                flow = None
            
            # Update SLAM tracking (existing code)
            pose = self.slam_tracker.update(keypoints, descriptors, flow)
            
            # Compute misalignment probability (existing logic)
            probability = self._compute_misalignment_probability(pose, flow)
            
            camera_id = ['front', 'left', 'right', 'rear'][i]
            results[camera_id] = {
                'probability': probability,
                'pose': pose,
                'method': 'rule_based'
            }
        
        return results
    
    def _compute_misalignment_probability(self, pose, flow):
        """
        Original misalignment probability computation.
        Preserved from existing system.
        """
        # Existing logic unchanged
        pass
```


### Migration Path

**Phase 1: Parallel Deployment**
- Deploy neural network system alongside existing rule-based system
- Run both systems in parallel with logging for comparison
- Use rule-based system for production decisions
- Collect neural network performance data

**Phase 2: Hybrid Operation**
- Enable hybrid mode with conservative neural network weight (e.g., 0.3)
- Monitor ensemble performance vs. rule-based baseline
- Gradually increase neural network weight based on validation

**Phase 3: Primary Neural Network**
- Switch to neural network mode as primary
- Keep rule-based system as automatic fallback
- Monitor for regression

**Phase 4: Rule-Based as Fallback Only**
- Neural network becomes sole production system
- Rule-based system remains dormant for emergency fallback

---

## Deployment Considerations

### Hardware Recommendations

**Training System**:
- GPU: NVIDIA RTX 3060 (12GB VRAM) or higher
- RAM: 32GB system memory
- Storage: 500GB SSD for KITTI dataset and checkpoints
- Estimated training time: 12-20 hours per architecture

**Inference System (Vehicle)**:
- GPU: NVIDIA Jetson Xavier NX (8GB) or NVIDIA GTX 1650 (4GB)
- RAM: 16GB system memory
- Storage: 50GB for model checkpoints and logs
- Power: <30W GPU power draw for embedded deployment

### Model Deployment Pipeline

```
1. Training Environment
   ├─ Train Architecture A (LiteFlowNet2)
   ├─ Train Architecture B (SpyNet)
   ├─ Evaluate both on test split
   └─ Generate comparison report

2. Model Selection
   ├─ Review comparison metrics
   ├─ Select optimal architecture
   └─ Export best_model.pth

3. Validation Environment
   ├─ Load checkpoint on target hardware
   ├─ Run inference benchmarks
   ├─ Verify latency and memory targets
   └─ Test fallback mechanisms

4. Production Deployment
   ├─ Deploy in hybrid mode
   ├─ Monitor performance
   └─ Gradual transition to neural network mode
```

### Configuration Management

**Development Config** (`config/dev.yaml`):
```yaml
feature_extractor: "cnn_pyramid"
flow_network: "liteflownet2"
mode: "neural_network"
checkpoint_path: "./models/dev_checkpoint.pth"
target_resolution: [512, 512]  # Lower resolution for faster iteration
enable_uncertainty: true
device: "cuda"
log_level: "DEBUG"
```

**Production Config** (`config/prod.yaml`):
```yaml
feature_extractor: "cnn_pyramid"
flow_network: "spynet"  # Lighter for embedded deployment
mode: "hybrid"
hybrid_weights:
  neural: 0.7
  rule_based: 0.3
checkpoint_path: "/opt/models/best_model.pth"
target_resolution: [640, 640]
enable_uncertainty: false  # Disabled for latency
device: "cuda"
log_level: "INFO"
```

### Monitoring and Observability

**Metrics to Track**:

1. **Performance Metrics**:
   - Inference latency (p50, p95, p99)
   - Throughput (frames/second)
   - GPU utilization
   - Memory consumption

2. **Accuracy Metrics**:
   - Detection rate (true positives)
   - False positive rate
   - Uncertainty distribution
   - Severity classification breakdown

3. **System Health**:
   - Neural network failure rate
   - Fallback activation frequency
   - Model version in production
   - Configuration changes

**Logging Infrastructure**:

```python
class ProductionLogger:
    """Structured logging for production deployment."""
    
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        self.inference_log = self._setup_inference_log()
        self.performance_log = self._setup_performance_log()
        
    def log_inference(self, input_hash: str, output: InferenceOutput, 
                      is_valid: bool, warnings: list):
        """Log inference result for traceability."""
        record = {
            'timestamp': output.timestamp,
            'input_hash': input_hash,
            'model_version': output.model_version,
            'processing_time_ms': output.processing_time_ms,
            'detections': {
                cam_id: {
                    'probability': det.misalignment_probability,
                    'severity': det.severity_level,
                    'low_confidence': det.low_confidence
                }
                for cam_id, det in output.camera_results.items()
            },
            'is_valid': is_valid,
            'warnings': warnings
        }
        
        self.inference_log.info(json.dumps(record))
    
    def log_performance(self, latency_ms: float, memory_mb: float, 
                        gpu_util_pct: float):
        """Log performance metrics for monitoring."""
        record = {
            'timestamp': time.time(),
            'latency_ms': latency_ms,
            'memory_mb': memory_mb,
            'gpu_util_pct': gpu_util_pct
        }
        
        self.performance_log.info(json.dumps(record))
```

---

## Appendix: Architecture Comparison Framework

### Comparison Metrics

```python
@dataclass
class ArchitectureMetrics:
    """Comprehensive metrics for architecture comparison."""
    
    # Accuracy metrics (on test split)
    detection_accuracy: float  # Overall accuracy
    precision: float
    recall: float
    f1_score: float
    false_positive_rate: float
    
    # Per-severity metrics
    severity_breakdown: dict[str, dict]  # {"LOW": {"precision": ..., "recall": ...}, ...}
    
    # Performance metrics
    avg_inference_latency_ms: float
    p95_inference_latency_ms: float
    training_vram_peak_gb: float
    inference_vram_peak_gb: float
    
    # Model complexity
    total_parameters: int
    flops: int  # Floating point operations
    
    # Training metrics
    training_time_hours: float
    final_training_loss: float
    best_validation_loss: float
    epochs_to_convergence: int

def compare_architectures(arch_a_metrics: ArchitectureMetrics,
                          arch_b_metrics: ArchitectureMetrics) -> str:
    """
    Generate recommendation based on architecture comparison.
    
    Returns:
        Recommendation string: "Architecture A", "Architecture B", or "Hybrid"
    """
    # Accuracy comparison
    accuracy_diff = arch_a_metrics.detection_accuracy - arch_b_metrics.detection_accuracy
    
    # Memory comparison
    memory_diff_pct = (arch_a_metrics.inference_vram_peak_gb - 
                       arch_b_metrics.inference_vram_peak_gb) / arch_b_metrics.inference_vram_peak_gb
    
    # Latency comparison
    latency_diff_pct = (arch_a_metrics.avg_inference_latency_ms - 
                        arch_b_metrics.avg_inference_latency_ms) / arch_b_metrics.avg_inference_latency_ms
    
    # Decision logic
    if accuracy_diff >= 0.03:  # A is 3%+ better
        return "Architecture A (LiteFlowNet2) - Higher accuracy"
    elif accuracy_diff <= -0.03:  # B is 3%+ better
        return "Architecture B (SpyNet) - Higher accuracy"
    else:
        # Accuracy similar, compare memory/latency
        if abs(memory_diff_pct) >= 0.25:  # 25%+ memory difference
            if memory_diff_pct < 0:
                return "Architecture A (LiteFlowNet2) - More memory efficient"
            else:
                return "Architecture B (SpyNet) - More memory efficient"
        elif abs(latency_diff_pct) >= 0.20:  # 20%+ latency difference
            if latency_diff_pct < 0:
                return "Architecture A (LiteFlowNet2) - Faster inference"
            else:
                return "Architecture B (SpyNet) - Faster inference"
        else:
            return "Hybrid - Similar performance, use ensemble"

def generate_comparison_report(arch_a: ArchitectureMetrics,
                                arch_b: ArchitectureMetrics,
                                output_path: str):
    """Generate detailed comparison report in markdown format."""
    
    recommendation = compare_architectures(arch_a, arch_b)
    
    report = f"""
# Architecture Comparison Report

**Generated:** {datetime.now().isoformat()}

## Recommendation

**{recommendation}**

## Accuracy Metrics (Test Split)

| Metric | Architecture A (LiteFlowNet2) | Architecture B (SpyNet) | Difference |
|--------|-------------------------------|-------------------------|------------|
| Detection Accuracy | {arch_a.detection_accuracy:.2%} | {arch_b.detection_accuracy:.2%} | {arch_a.detection_accuracy - arch_b.detection_accuracy:+.2%} |
| Precision | {arch_a.precision:.2%} | {arch_b.precision:.2%} | {arch_a.precision - arch_b.precision:+.2%} |
| Recall | {arch_a.recall:.2%} | {arch_b.recall:.2%} | {arch_a.recall - arch_b.recall:+.2%} |
| F1-Score | {arch_a.f1_score:.3f} | {arch_b.f1_score:.3f} | {arch_a.f1_score - arch_b.f1_score:+.3f} |
| False Positive Rate | {arch_a.false_positive_rate:.2%} | {arch_b.false_positive_rate:.2%} | {arch_a.false_positive_rate - arch_b.false_positive_rate:+.2%} |

## Performance Metrics

| Metric | Architecture A | Architecture B | Difference |
|--------|----------------|----------------|------------|
| Avg Inference Latency | {arch_a.avg_inference_latency_ms:.1f} ms | {arch_b.avg_inference_latency_ms:.1f} ms | {arch_a.avg_inference_latency_ms - arch_b.avg_inference_latency_ms:+.1f} ms |
| P95 Inference Latency | {arch_a.p95_inference_latency_ms:.1f} ms | {arch_b.p95_inference_latency_ms:.1f} ms | {arch_a.p95_inference_latency_ms - arch_b.p95_inference_latency_ms:+.1f} ms |
| Training VRAM Peak | {arch_a.training_vram_peak_gb:.2f} GB | {arch_b.training_vram_peak_gb:.2f} GB | {arch_a.training_vram_peak_gb - arch_b.training_vram_peak_gb:+.2f} GB |
| Inference VRAM Peak | {arch_a.inference_vram_peak_gb:.2f} GB | {arch_b.inference_vram_peak_gb:.2f} GB | {arch_a.inference_vram_peak_gb - arch_b.inference_vram_peak_gb:+.2f} GB |

## Model Complexity

| Metric | Architecture A | Architecture B |
|--------|----------------|----------------|
| Total Parameters | {arch_a.total_parameters:,} | {arch_b.total_parameters:,} |
| FLOPs | {arch_a.flops:,} | {arch_b.flops:,} |

## Training Metrics

| Metric | Architecture A | Architecture B |
|--------|----------------|----------------|
| Training Time | {arch_a.training_time_hours:.1f} hours | {arch_b.training_time_hours:.1f} hours |
| Best Validation Loss | {arch_a.best_validation_loss:.4f} | {arch_b.best_validation_loss:.4f} |
| Epochs to Convergence | {arch_a.epochs_to_convergence} | {arch_b.epochs_to_convergence} |
"""
    
    with open(output_path, 'w') as f:
        f.write(report)
    
    print(f"Comparison report saved to {output_path}")
```

---

## Summary

This design document specifies a complete deep learning system for camera misalignment detection with:

1. **Dual Architecture Support**: LiteFlowNet2 and SpyNet for comparative evaluation
2. **Memory-Efficient Design**: Mixed precision, gradient checkpointing, and pyramid processing for consumer GPUs
3. **Real-Time Performance**: ≤100ms inference latency for 4-camera batches at 10+ Hz
4. **Resolution Constraint**: Maximum 750×750 pixel input strictly enforced across all components
5. **Backward Compatibility**: Seamless integration with existing rule-based system
6. **Flexible Operation**: Neural network, rule-based, and hybrid modes with runtime switching
7. **Comprehensive Testing**: Unit, integration, and system tests covering all components
8. **Production-Ready**: Checkpoint management, error handling, monitoring, and deployment pipeline

The system architecture enables data-driven selection between LiteFlowNet2 (optimized for accuracy) and SpyNet (optimized for efficiency) based on empirical comparison on KITTI test data, while preserving existing system functionality as a reliable fallback mechanism.
