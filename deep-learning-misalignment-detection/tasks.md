# Implementation Plan: Deep Learning Misalignment Detection System

## Overview

This implementation plan covers the complete development of a deep learning-based camera misalignment detection system using PyTorch. The system implements two neural network architectures (Architecture A with LiteFlowNet2 and Architecture B with SpyNet) trained on the KITTI dataset for comparative evaluation. The implementation follows a memory-efficient design targeting consumer GPUs (4-16GB VRAM) with real-time inference capabilities (<100ms for 4-camera batches).

The plan is structured to build incrementally from foundational components (project setup, data pipeline) through core neural network modules (CNN Feature Extractor, optical flow networks, pose estimator) to the complete training and inference systems, with comprehensive testing throughout.

## Tasks

- [x] 1. Project setup and infrastructure
  - [x] 1.1 Create project directory structure and Python package configuration
    - Create directory structure: `src/dl_misalignment/`, `src/dl_misalignment/models/`, `src/dl_misalignment/data/`, `src/dl_misalignment/training/`, `src/dl_misalignment/inference/`, `src/dl_misalignment/utils/`, `tests/`, `config/`, `scripts/`
    - Create `pyproject.toml` with project metadata and dependencies
    - Create `setup.py` for package installation
    - Create `.gitignore` for Python, PyTorch, and data files
    - _Requirements: 18.5, 19.4_

  - [x] 1.2 Install and configure core dependencies
    - Add PyTorch (>=2.0) with CUDA support to dependencies
    - Add torchvision for image preprocessing utilities
    - Add PyYAML for configuration file parsing
    - Add tensorboard for training visualization
    - Add pytest for testing framework
    - Add numpy, opencv-python, Pillow for data processing
    - Create `requirements.txt` and `requirements-dev.txt`
    - Verify CUDA availability and log GPU specifications
    - _Requirements: 18.1, 18.2, 18.3, 19.1, 19.2, 19.3_

  - [x] 1.3 Create system configuration schema and YAML loader
    - Implement `SystemConfig` dataclass matching design specification
    - Create YAML schema validator using Pydantic or dataclasses
    - Implement configuration loader with error handling for malformed files
    - Create example configuration files for both architectures (Architecture A with LiteFlowNet2, Architecture B with SpyNet)
    - Add validation for checkpoint path existence and mode selection
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7, 16.8_

  - [ ]* 1.4 Write unit tests for configuration system
    - Test valid YAML loading and parsing
    - Test malformed YAML error handling
    - Test nonexistent checkpoint path detection
    - Test default value assignment
    - _Requirements: 16.7, 16.8_

- [x] 2. KITTI dataset integration and preprocessing
  - [x] 2.1 Implement KITTI dataset loader
    - Create `KITTIDataset` class inheriting from `torch.utils.data.Dataset`
    - Load stereo image pairs from KITTI directory structure
    - Implement image preprocessing: resize to target resolution (≤750×750), normalize using ImageNet statistics
    - Preserve original resolution metadata and color channels
    - Create efficient batching with `DataLoader`
    - _Requirements: 5.1, 5.7, 1.1_

  - [x] 2.2 Implement dataset splitting strategy
    - Create train/validation/test split with 70/15/15 ratio (±2% tolerance)
    - Implement deterministic splitting using fixed random seed for reproducibility
    - Verify no sample overlap between splits
    - Log split statistics (sample counts, percentage verification)
    - Save split indices to disk for consistent evaluation
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 5.6_

  - [x] 2.3 Implement data augmentation engine
    - Create `AugmentationEngine` class with random transformations
    - Implement rotation augmentation (-10° to +10°)
    - Implement translation augmentation (-50 to +50 pixels in X and Y)
    - Implement brightness augmentation (0.7 to 1.3 multiplicative factor)
    - Implement contrast augmentation (0.8 to 1.2 multiplicative factor)
    - Implement Gaussian noise augmentation (σ=0.01)
    - Implement horizontal flip augmentation (50% probability)
    - Implement random cropping (90-100% scale)
    - Apply augmentations with 50% probability per sample
    - Apply to training and validation splits only (exclude test split)
    - Generate ground truth misalignment labels from applied transformations
    - Preserve image dimensions matching original KITTI samples
    - Log augmentation statistics every 1000 steps
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 21.1, 21.2, 21.3, 21.4, 21.5, 21.6, 21.7_

  - [ ]* 2.4 Write unit tests for data pipeline
    - Test dataset loading and sample retrieval
    - Test train/validation/test split ratios and non-overlap
    - Test augmentation transformations preserve image dimensions
    - Test augmentation ground truth label generation
    - Test preprocessing normalization and resizing
    - _Requirements: 5.6, 6.7, 21.7_

- [x] 3. CNN Feature Extractor implementation
  - [x] 3.1 Implement CNNFeatureExtractor module
    - Create `CNNFeatureExtractor` class inheriting from `nn.Module`
    - Implement 4-level pyramid architecture (1x, 1/2x, 1/4x, 1/8x resolutions)
    - Level 0: Conv layers 3→64→64 channels (1x resolution)
    - Level 1: Conv layers 64→128→128 channels (1/2x resolution with pooling)
    - Level 2: Conv layers 128→256→256→256 channels (1/4x resolution with pooling)
    - Level 3: Conv layers 256→512→512→512 channels (1/8x resolution with pooling)
    - Return list of 4 feature tensors as pyramid
    - Support input dimensions 256×256 to 1024×1024, enforce ≤750×750 maximum
    - Support batch processing up to batch_size=4
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 1.6, 24.1, 24.2, 24.3_

  - [ ]* 3.2 Write unit tests for CNN Feature Extractor
    - Test input dimension validation (256-1024 range, 750 max enforcement)
    - Test output pyramid structure (4 levels with correct shapes)
    - Test feature map spatial resolution (1/8 of input at coarsest level)
    - Test batch processing with batch_size=4
    - Test forward pass latency (target ≤30ms on GPU)
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.6_

- [x] 4. Checkpoint - Verify data pipeline and feature extractor
  - Ensure all tests pass for configuration, data loading, and CNN Feature Extractor
  - Run data loading with sample batch to verify preprocessing
  - Profile CNN Feature Extractor memory usage with batch_size=4
  - Ask the user if questions arise.

- [x] 5. LiteFlowNet2 implementation (Architecture A)
  - [~] 5.1 Implement FeatureWarping module
    - Create `FeatureWarping` class for warping frame t+1 features to frame t using optical flow
    - Generate sampling grid from flow vectors
    - Implement bilinear interpolation using `F.grid_sample`
    - Normalize grid coordinates to [-1, 1] range
    - _Requirements: 2.1, 2.2_

  - [~] 5.2 Implement FlowEstimator module
    - Create `FlowEstimator` class with 6 convolutional layers
    - Input: concatenated features (varies by pyramid level)
    - Output: 2-channel optical flow (u, v)
    - Use LeakyReLU activation with negative_slope=0.1
    - Progressive channel reduction: 128→128→96→64→32→2
    - _Requirements: 2.2, 2.3_

  - [~] 5.3 Implement FlowRefiner module
    - Create `FlowRefiner` class for residual flow refinement
    - Input: current flow estimate + features
    - Output: refined flow (original + residual)
    - 4 convolutional layers: 128→64→32→2 channels
    - _Requirements: 2.2, 2.3_

  - [~] 5.4 Implement complete LiteFlowNet2 architecture
    - Create `LiteFlowNet2` class with coarse-to-fine pyramid processing
    - Implement Level 3 (coarsest) flow estimation from concatenated features
    - Implement Level 2 refinement with warping and upsampling
    - Implement Level 1 refinement with warping and upsampling
    - Implement Level 0 (finest) refinement for final output
    - Upsample flow with bilinear interpolation and 2× scaling factor
    - Output optical flow field at full input resolution
    - _Requirements: 2.1, 2.2, 2.3, 24.4, 24.6, 24.7_

  - [ ]* 5.5 Write unit tests for LiteFlowNet2
    - Test flow field output dimensions match input resolution
    - Test 2D flow vector estimation per pixel
    - Test forward pass latency (target ≤50ms for batch_size=4)
    - Test coarse-to-fine processing order
    - _Requirements: 2.2, 2.3, 2.6_

- [x] 6. SpyNet implementation (Architecture B)
  - [~] 6.1 Implement BasicFlowModule
    - Create `BasicFlowModule` class with lightweight convolutional design
    - 4 convolutional layers with 7×7 kernels: input→32→16→8→2 channels
    - Use ReLU activation
    - Input: concatenated [feat1, feat2_warped, current_flow]
    - Output: flow residual
    - _Requirements: 3.1, 3.2, 3.6_

  - [~] 6.2 Implement complete SpyNet architecture
    - Create `SpyNet` class with pyramid processing from coarse to fine
    - Reuse `FeatureWarping` module from LiteFlowNet2
    - Create 4 `BasicFlowModule` instances (one per pyramid level)
    - Initialize flow at coarsest level (Level 3)
    - Iterate through levels 3→2→1→0 with upsampling and refinement
    - Output optical flow field at full input resolution
    - _Requirements: 3.1, 3.2, 24.5, 24.6, 24.7_

  - [ ]* 6.3 Write unit tests for SpyNet
    - Test flow field output dimensions match input resolution
    - Test forward pass latency (target ≤30ms for batch_size=4)
    - Test memory consumption lower than LiteFlowNet2
    - _Requirements: 3.2, 3.5, 3.6_

- [x] 7. Pose Estimator implementation
  - [~] 7.1 Implement PoseEstimator module
    - Create `PoseEstimator` class with multi-task head design
    - Implement global average pooling for spatial aggregation
    - Implement shared feature processing: FC layer 66→256 with dropout (p=0.3)
    - Implement misalignment probability branch: 256→128→1 with sigmoid activation
    - Implement 6-DOF pose regression branch: 256→128→6 (X, Y, Z, roll, pitch, yaw)
    - Accept Level 0 features (64 channels) and optical flow (2 channels) as input
    - Output misalignment probability in range [0, 1]
    - Output pose with position in meters and orientation in degrees
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 12.1, 12.2, 12.3, 12.4, 12.5_

  - [~] 7.2 Implement Monte Carlo Dropout for uncertainty estimation
    - Create `forward_with_uncertainty` method using MC Dropout
    - Run forward pass 10 times with dropout enabled during inference
    - Compute mean and standard deviation across samples
    - Return probability mean, pose mean, probability std, pose std
    - Flag predictions with uncertainty >0.2 as low confidence
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

  - [~] 7.3 Implement severity classification logic
    - Create helper function to map misalignment probability to severity levels
    - Probability [0.25, 0.50) → LOW
    - Probability [0.50, 0.75) → MEDIUM
    - Probability [0.75, 0.90) → HIGH
    - Probability [0.90, 1.00] → CRITICAL
    - Probability <0.25 → NONE (no actionable misalignment)
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [ ]* 7.4 Write unit tests for Pose Estimator
    - Test output shapes (misalignment probability: [B, 1], pose: [B, 6])
    - Test sigmoid output range [0, 1]
    - Test Monte Carlo uncertainty estimation (10 samples)
    - Test severity classification mapping
    - Test forward pass latency (≤10ms standard, ≤100ms with uncertainty)
    - _Requirements: 10.1, 10.4, 11.1, 13.2, 13.3_

- [x] 8. Checkpoint - Verify all neural network modules
  - Ensure all tests pass for CNN Feature Extractor, LiteFlowNet2, SpyNet, and Pose Estimator
  - Run end-to-end forward pass: input images → CNN → flow network → pose estimator
  - Profile memory usage for both architectures with batch_size=4
  - Ask the user if questions arise.

- [x] 9. Training pipeline implementation
  - [~] 9.1 Implement memory-efficient training configuration
    - Create training script with mixed precision (FP16 forward, FP32 gradients) using `torch.cuda.amp`
    - Implement gradient checkpointing to reduce activation memory
    - Implement dynamic batch size adjustment based on available VRAM
    - For VRAM ≤8GB: set batch_size ≤2
    - For VRAM >8GB and ≤16GB: set batch_size ≤4
    - Monitor GPU memory usage and log peak consumption every 100 steps
    - Implement VRAM allocation failure handling (reduce batch size by 50% and retry)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 18.1, 18.5_

  - [~] 9.2 Implement loss function components
    - Implement binary cross-entropy loss for misalignment probability classification
    - Implement smooth L1 loss for 6-DOF pose regression
    - Implement weighted combination with configurable weights (default: 0.6 classification, 0.4 regression)
    - Log separate classification loss, regression loss, and combined loss every 10 steps
    - Allow loss weight customization via configuration file
    - _Requirements: 23.1, 23.2, 23.3, 23.4, 23.5, 23.6, 23.7_

  - [~] 9.3 Implement checkpoint management system
    - Create `ModelCheckpoint` dataclass with model weights, optimizer state, training step, epoch
    - Save checkpoints every 1000 training steps in PyTorch .pth format
    - Include metadata: timestamp, PyTorch version, CUDA version, model version
    - Maintain 3 most recent checkpoints to conserve disk space
    - Save separate best_model checkpoint with lowest validation loss
    - Implement training resumption from checkpoint with optimizer state restoration
    - Log checkpoint file path and validation loss on save
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.6_

  - [~] 9.4 Implement training loop with validation and early stopping
    - Create main training loop with Adam optimizer
    - Evaluate on validation split every 500 training steps
    - Implement learning rate scheduler: reduce by 0.5× if validation loss doesn't improve for 5 evaluations
    - Implement early stopping: terminate if validation loss doesn't improve for 10 evaluations
    - Target training completion within 24 hours on single consumer GPU
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [~] 9.5 Implement TensorBoard logging integration
    - Log training loss every 10 steps
    - Log validation loss every 500 steps
    - Log learning rate every 100 steps
    - Log GPU memory utilization every 100 steps
    - Log sample predictions with ground truth overlays every 1000 steps
    - Organize logs with separate runs for Architecture A and Architecture B
    - Create event files in configurable output directory
    - _Requirements: 8.6, 27.1, 27.2, 27.3, 27.4, 27.5, 27.6, 27.7_

  - [~] 9.6 Create training scripts for both architectures
    - Create `train_architecture_a.py` for LiteFlowNet2 configuration
    - Create `train_architecture_b.py` for SpyNet configuration
    - Use identical hyperparameters and training split for fair comparison
    - Verify hardware requirements at initialization (8GB VRAM, 16GB RAM, CUDA 6.1+)
    - Log hardware specifications and terminate with guidance if requirements not met
    - _Requirements: 4.1, 18.1, 18.2, 18.3, 18.4, 18.5, 18.6_

  - [ ]* 9.7 Write integration tests for training pipeline
    - Test checkpoint saving and loading
    - Test training resumption from checkpoint
    - Test early stopping trigger
    - Test learning rate reduction
    - Test TensorBoard event file creation
    - _Requirements: 8.4, 8.5, 20.5, 27.6_

- [x] 10. Checkpoint - Verify training pipeline
  - Run short training session (10 steps) for Architecture A to verify all components
  - Check checkpoint files are created correctly
  - Verify TensorBoard logs are generated
  - Test training resumption from checkpoint
  - Ask the user if questions arise.

- [ ] 11. Inference engine implementation
  - [~] 11.1 Implement preprocessing and batch formation
    - Create image preprocessing pipeline: resize to target resolution (≤750×750), normalize
    - Implement four-camera batch formation into single tensor [4, 3, H, W]
    - Validate input dimensions and enforce 750×750 maximum resolution
    - Support both single-camera and four-camera batch modes
    - _Requirements: 9.1, 22.1_

  - [~] 11.2 Implement efficient batch inference engine
    - Create `InferenceEngine` class with model loading from checkpoint
    - Validate checkpoint compatibility with code version during loading
    - Load checkpoint within 5 seconds during initialization
    - Pre-allocate GPU memory buffers for four-camera batch processing
    - Use asynchronous GPU operations with CUDA streams for overlapping data transfer and computation
    - Process four-camera batch as single tensor operation (not 4 sequential operations)
    - Target GPU utilization ≥80% during processing
    - Measure and log per-camera inference time breakdown
    - _Requirements: 9.3, 9.4, 20.7, 22.1, 22.2, 22.3, 22.4, 22.5_

  - [~] 11.3 Implement real-time performance monitoring
    - Measure total processing time for four-camera batch (target ≤100ms)
    - Achieve processing rate ≥10 Hz for continuous stream monitoring
    - Log warning with timing breakdown if latency exceeds 100ms
    - Monitor VRAM consumption (target ≤8GB during operation)
    - _Requirements: 9.1, 9.2, 9.4, 9.5_

  - [~] 11.4 Implement output data structures and serialization
    - Create `CameraDetection` dataclass with misalignment probability, severity level, 6-DOF pose, uncertainty
    - Create `InferenceOutput` dataclass with per-camera results and metadata
    - Implement JSON serialization with `to_json()` method
    - Include timestamp, model version, processing time in output
    - Apply severity classification using thresholds from Pose Estimator
    - Include optional uncertainty estimates when enabled
    - _Requirements: 10.1, 10.6, 11.7, 12.4, 13.5, 28.1, 28.2, 28.3, 28.4, 28.5, 28.6, 28.7_

  - [~] 11.5 Implement confidence thresholding for binary classification
    - Apply configurable confidence threshold (default 0.5) to convert probability to binary detection
    - Support threshold customization via configuration file
    - _Requirements: 10.5, 10.6_

  - [~] 11.6 Implement optional uncertainty estimation mode
    - Add configuration flag to enable/disable uncertainty estimation
    - When enabled, use Monte Carlo Dropout with 10 samples
    - When disabled, skip uncertainty computation for lower latency
    - Flag low-confidence predictions (uncertainty >0.2)
    - _Requirements: 13.1, 13.4, 13.6_

  - [ ]* 11.7 Write integration tests for inference engine
    - Test four-camera batch processing latency (≤100ms)
    - Test checkpoint loading time (≤5 seconds)
    - Test output JSON serialization
    - Test uncertainty estimation toggle
    - Test confidence threshold application
    - _Requirements: 9.1, 9.3, 10.5, 13.6_

- [ ] 12. Hybrid mode and rule-based system integration
  - [~] 12.1 Preserve existing rule-based system codebase
    - Document existing rule-based system components (ORB features, optical flow, SLAM)
    - Ensure no modifications to existing source code
    - Verify rule-based system can run independently
    - _Requirements: 14.1, 14.3_

  - [~] 12.2 Implement mode selection system
    - Add mode configuration parameter: "neural_network", "rule_based", or "hybrid"
    - Implement mode switching logic in main system controller
    - Create unified interface for both detection approaches with identical input/output
    - Support mode switching via configuration file update without system restart
    - _Requirements: 14.2, 14.3, 14.4, 14.5, 14.6_

  - [~] 12.3 Implement hybrid ensemble prediction
    - Create hybrid mode that executes both neural network and rule-based pipelines in parallel
    - Compute ensemble misalignment probability as weighted average (configurable weights, default 0.7 neural + 0.3 rule-based)
    - Output both individual and ensemble predictions
    - Implement fallback to rule-based only if neural network inference fails
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6_

  - [~] 12.4 Implement automatic fallback on neural network failure
    - Wrap neural network inference in exception handling
    - On inference failure, automatically switch to rule-based mode and log error with exception details
    - Continue processing frames using rule-based system after fallback
    - Attempt neural network recovery after 60 seconds
    - After 3 consecutive recovery failures, remain in rule-based mode until manual intervention
    - Expose fallback status via monitoring API
    - _Requirements: 26.1, 26.2, 26.3, 26.4, 26.5, 26.6, 26.7_

  - [ ]* 12.5 Write integration tests for hybrid mode
    - Test mode switching between neural_network, rule_based, hybrid
    - Test ensemble prediction computation
    - Test automatic fallback on neural network exception
    - Test neural network recovery attempts
    - _Requirements: 14.6, 15.6, 26.1, 26.4_

- [~] 13. Checkpoint - Verify inference and hybrid mode
  - Run inference on sample images for all three modes
  - Verify output format consistency across modes
  - Test automatic fallback by simulating neural network failure
  - Profile latency and memory for four-camera batch
  - Ask the user if questions arise.

- [ ] 14. Model training execution
  - [~] 14.1 Train Architecture A (LiteFlowNet2) on KITTI dataset
    - Execute training script for Architecture A
    - Monitor training progress via TensorBoard
    - Verify training completes within 24 hours
    - Save best_model checkpoint based on validation loss
    - Record final training loss, validation loss, and training time
    - _Requirements: 4.1, 8.1, 8.7_

  - [~] 14.2 Train Architecture B (SpyNet) on KITTI dataset
    - Execute training script for Architecture B
    - Use identical hyperparameters and data split as Architecture A
    - Monitor training progress via TensorBoard
    - Verify training completes within 24 hours
    - Save best_model checkpoint based on validation loss
    - Record final training loss, validation loss, and training time
    - _Requirements: 4.1, 8.1, 8.7_

- [ ] 15. Model evaluation and comparison
  - [~] 15.1 Implement evaluation metrics computation
    - Create evaluation script that loads trained models and test split
    - Compute detection accuracy (correctly classified samples / total samples)
    - Compute precision, recall, F1-score for each severity level
    - Compute false positive rate (aligned samples classified as misaligned / total aligned)
    - Generate classification report with per-class metrics
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6_

  - [~] 15.2 Evaluate Architecture A on test split
    - Load best_model checkpoint for Architecture A
    - Run inference on entire test split
    - Compute all evaluation metrics (accuracy, precision, recall, F1, FPR)
    - Measure peak VRAM consumption during inference
    - Measure average inference latency per four-camera batch
    - Record all metrics to results file
    - Verify detection accuracy ≥95% and false positive rate ≤5%
    - _Requirements: 4.2, 4.3, 4.5, 4.6, 17.1, 17.4_

  - [~] 15.3 Evaluate Architecture B on test split
    - Load best_model checkpoint for Architecture B
    - Run inference on identical test split as Architecture A
    - Compute all evaluation metrics (accuracy, precision, recall, F1, FPR)
    - Measure peak VRAM consumption during inference
    - Measure average inference latency per four-camera batch
    - Record all metrics to results file
    - Verify detection accuracy ≥95% and false positive rate ≤5%
    - _Requirements: 4.2, 4.3, 4.5, 4.6, 17.2, 17.4_

  - [~] 15.4 Measure and record memory consumption
    - Record training peak VRAM for Architecture A (target ≤8GB)
    - Record inference peak VRAM for Architecture A (target ≤4GB)
    - Record training peak VRAM for Architecture B (target ≤6GB)
    - Record inference peak VRAM for Architecture B (target ≤3GB)
    - _Requirements: 2.4, 2.5, 3.3, 3.4, 4.4, 4.5_

  - [~] 15.5 Generate architecture comparison report
    - Create comparison report with side-by-side metrics table
    - Include accuracy, precision, recall, F1-score for both architectures
    - Include training VRAM, inference VRAM, inference latency for both architectures
    - Implement recommendation logic:
      - If accuracy difference ≥3%: recommend higher-accuracy architecture
      - Else if VRAM difference ≥25%: recommend memory-efficient architecture
      - Else: recommend architecture with lower latency
    - Generate final recommendation (Architecture A, Architecture B, or hybrid)
    - _Requirements: 4.7, 25.1, 25.2, 25.3, 25.4, 25.5, 25.6, 25.7_

  - [ ]* 15.6 Write system-level tests for evaluation pipeline
    - Test evaluation metrics computation (accuracy, precision, recall, F1, FPR)
    - Test comparison report generation
    - Test recommendation logic for different metric scenarios
    - _Requirements: 17.3, 17.5, 25.4_

- [ ] 16. VRAM optimization and performance tuning
  - [~] 16.1 Profile and optimize memory consumption
    - Profile VRAM usage during training for both architectures
    - Identify memory bottlenecks using PyTorch profiler
    - Tune gradient checkpointing parameters if needed
    - Verify batch size limits for different VRAM configurations (8GB, 16GB)
    - _Requirements: 2.4, 2.5, 3.3, 3.4, 7.4, 7.5_

  - [~] 16.2 Optimize inference latency
    - Profile inference pipeline using PyTorch profiler
    - Optimize CUDA stream usage for asynchronous operations
    - Verify batch processing efficiency (≤1.5× single-camera time for four-camera batch)
    - Tune memory pre-allocation for optimal GPU utilization
    - _Requirements: 9.1, 22.2, 22.6_

  - [ ]* 16.3 Write performance benchmarking tests
    - Test training VRAM consumption stays within limits
    - Test inference latency for four-camera batch (≤100ms)
    - Test batch processing efficiency ratio
    - _Requirements: 2.4, 2.5, 3.3, 3.4, 9.1, 22.6_

- [~] 17. Checkpoint - Final system integration verification
  - Verify both architectures are trained and evaluated
  - Review comparison report and deployment recommendation
  - Test all three operational modes (neural_network, rule_based, hybrid)
  - Verify all performance targets are met (accuracy ≥95%, latency ≤100ms, VRAM within limits)
  - Ask the user if questions arise.

- [ ] 18. Documentation and deployment preparation
  - [~] 18.1 Create system architecture documentation
    - Document overall system design with component diagrams
    - Document data flow for training and inference pipelines
    - Document neural network architectures with layer specifications
    - Document memory optimization techniques used
    - _Requirements: All requirements (comprehensive documentation)_

  - [~] 18.2 Create configuration guide
    - Document YAML configuration schema with all parameters
    - Provide example configurations for both architectures and all modes
    - Document hardware requirements for training and inference
    - Document troubleshooting guide for common issues
    - _Requirements: 16.1-16.8, 18.1-18.6, 19.1-19.6_

  - [~] 18.3 Create training guide
    - Document KITTI dataset setup and preprocessing
    - Document training script usage and hyperparameters
    - Document monitoring with TensorBoard
    - Document checkpoint management and training resumption
    - _Requirements: 5.1-5.7, 8.1-8.7, 20.1-20.7_

  - [~] 18.4 Create inference and deployment guide
    - Document inference engine initialization and usage
    - Document output format and JSON schema
    - Document integration with existing systems
    - Document performance expectations and monitoring
    - _Requirements: 9.1-9.6, 28.1-28.7, 29.1-29.6_

  - [~] 18.5 Create API reference documentation
    - Document all public classes and methods with docstrings
    - Generate API documentation using Sphinx or similar tool
    - Document data structures (TrainingSample, ModelCheckpoint, InferenceOutput, CameraDetection)
    - _Requirements: All requirements (complete API reference)_

  - [~] 18.6 Create deployment scripts
    - Create Docker container configuration for inference deployment
    - Create model packaging script for checkpoint distribution
    - Create validation script for deployment environment verification
    - Document hardware compatibility (NVIDIA GPUs, Jetson platforms, AMD ROCm)
    - _Requirements: 19.3, 19.4, 19.5_

- [ ] 19. Final validation and testing
  - [ ]* 19.1 Run complete end-to-end system test
    - Test complete workflow: data loading → training → evaluation → inference
    - Verify all 30 requirements are satisfied
    - Test on multiple GPU configurations (8GB, 16GB VRAM)
    - Test on NVIDIA Jetson platform if available
    - _Requirements: All 30 requirements_

  - [ ]* 19.2 Perform stress testing
    - Test continuous inference operation for extended duration (1 hour)
    - Monitor for memory leaks or performance degradation
    - Test automatic fallback recovery under simulated failures
    - _Requirements: 9.2, 26.1-26.7_

  - [ ]* 19.3 Validate hardware compatibility
    - Test on minimum hardware specification (8GB VRAM training, 4GB VRAM inference)
    - Verify AMD ROCm compatibility if applicable
    - Test CUDA compute capability 6.1+ (Pascal architecture or newer)
    - _Requirements: 18.1-18.6, 19.1-19.6_

- [~] 20. Final checkpoint - Deployment readiness
  - Review all documentation is complete and accurate
  - Verify trained models meet all performance targets
  - Confirm comparison report with deployment recommendation
  - Package models and documentation for deployment
  - Obtain final approval for production deployment

## Notes

- **Optional Tasks**: Tasks marked with `*` are optional testing and validation tasks that can be skipped for faster MVP delivery. However, completing these tasks significantly improves system reliability and confidence.

- **Architecture Comparison**: Tasks 14 and 15 train and evaluate both Architecture A (LiteFlowNet2) and Architecture B (SpyNet) using identical datasets and hyperparameters, enabling direct comparison for deployment decision.

- **Memory Constraints**: All implementation tasks respect the 750×750 maximum resolution constraint and target consumer GPU memory limits (4-16GB VRAM).

- **Incremental Validation**: Checkpoint tasks (4, 8, 10, 13, 17) ensure incremental validation and provide natural breaking points for user feedback.

- **Requirements Traceability**: Each task explicitly references the requirements it addresses, ensuring complete coverage of all 30 requirements from requirements.md.

- **Testing Strategy**: Unit tests validate individual components, integration tests verify component interactions, and system tests ensure end-to-end functionality. Optional test tasks are marked with `*` but provide significant confidence for production deployment.

- **Hardware Requirements**: Training requires minimum 8GB VRAM, inference requires minimum 4GB VRAM. System includes hardware verification at initialization with clear error messages if requirements are not met.

- **Hybrid Mode**: The system preserves the existing rule-based detection approach and provides three operational modes: pure neural network, pure rule-based, and hybrid ensemble. Automatic fallback ensures robustness.

- **Performance Targets**: 
  - Training: Complete within 24 hours on consumer GPU
  - Inference: ≤100ms for 4-camera batch (≥10 Hz throughput)
  - Accuracy: ≥95% detection accuracy, ≤5% false positive rate
  - Memory: Architecture A (8GB training/4GB inference), Architecture B (6GB training/3GB inference)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "1.4"] },
    { "id": 2, "tasks": ["2.1", "2.2"] },
    { "id": 3, "tasks": ["2.3", "2.4"] },
    { "id": 4, "tasks": ["3.1", "3.2"] },
    { "id": 5, "tasks": ["5.1", "5.2", "5.3", "6.1"] },
    { "id": 6, "tasks": ["5.4", "5.5", "6.2", "6.3"] },
    { "id": 7, "tasks": ["7.1"] },
    { "id": 8, "tasks": ["7.2", "7.3", "7.4"] },
    { "id": 9, "tasks": ["9.1", "9.2"] },
    { "id": 10, "tasks": ["9.3", "9.4"] },
    { "id": 11, "tasks": ["9.5", "9.6", "9.7"] },
    { "id": 12, "tasks": ["11.1"] },
    { "id": 13, "tasks": ["11.2", "11.3"] },
    { "id": 14, "tasks": ["11.4", "11.5", "11.6", "11.7"] },
    { "id": 15, "tasks": ["12.1", "12.2"] },
    { "id": 16, "tasks": ["12.3", "12.4", "12.5"] },
    { "id": 17, "tasks": ["14.1", "14.2"] },
    { "id": 18, "tasks": ["15.1"] },
    { "id": 19, "tasks": ["15.2", "15.3"] },
    { "id": 20, "tasks": ["15.4", "15.5", "15.6"] },
    { "id": 21, "tasks": ["16.1", "16.2", "16.3"] },
    { "id": 22, "tasks": ["18.1", "18.2", "18.3", "18.4", "18.5", "18.6"] },
    { "id": 23, "tasks": ["19.1", "19.2", "19.3"] }
  ]
}
```
