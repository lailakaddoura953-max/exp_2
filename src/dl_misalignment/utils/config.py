"""
Configuration System for Deep Learning Misalignment Detection

This module provides a robust configuration system using YAML files and Pydantic
for validation. It ensures that all configuration parameters are valid before
training or inference begins, preventing runtime errors from invalid settings.

Key Concepts for Developers New to CNNs:
- YAML files provide human-readable configuration
- Pydantic validates types and ranges automatically
- Configuration is immutable after loading (prevents accidental changes)
- Default values are provided for most parameters

Example configuration file (config/architecture_a.yaml):
```yaml
feature_extractor: "cnn_pyramid"
flow_network: "liteflownet2"  # or "spynet" for Architecture B
mode: "neural_network"  # or "rule_based" or "hybrid"

checkpoint_path: "./checkpoints/best_model.pth"
confidence_threshold: 0.5
batch_size: 4
target_resolution: [640, 640]  # Maximum 750×750

device: "cuda"
mixed_precision: true
```
"""

import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Literal
from dataclasses import dataclass, field

import yaml
from pydantic import BaseModel, Field, validator, root_validator

logger = logging.getLogger(__name__)


# ==============================================================================
# Configuration Data Models
# ==============================================================================
# These define the structure and validation rules for all configuration
# parameters. Pydantic automatically validates types, ranges, and constraints.


class HybridWeightsConfig(BaseModel):
    """
    Configuration for hybrid mode weights.
    
    In hybrid mode, the system runs both neural network and rule-based detection
    in parallel, then combines their predictions using weighted averaging.
    
    Example:
        neural: 0.7  means neural network contributes 70% to final prediction
        rule_based: 0.3  means rule-based system contributes 30%
    
    The weights must sum to 1.0 (validated automatically).
    """
    neural: float = Field(
        default=0.7,
        ge=0.0,  # Greater than or equal to 0
        le=1.0,  # Less than or equal to 1
        description="Weight for neural network predictions (0.0 to 1.0)"
    )
    rule_based: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weight for rule-based predictions (0.0 to 1.0)"
    )
    
    @root_validator(skip_on_failure=True)
    def weights_must_sum_to_one(cls, values):
        """
        Validate that weights sum to exactly 1.0.
        
        This ensures the combined prediction is a proper weighted average.
        For example, if neural=0.7 and rule_based=0.3, sum=1.0 (valid).
        If neural=0.6 and rule_based=0.6, sum=1.2 (invalid - will raise error).
        """
        neural = values.get('neural', 0.7)
        rule_based = values.get('rule_based', 0.3)
        total = neural + rule_based
        
        if abs(total - 1.0) > 1e-6:  # Allow tiny floating-point errors
            raise ValueError(
                f"Hybrid weights must sum to 1.0, got {total:.6f} "
                f"(neural={neural}, rule_based={rule_based})"
            )
        
        return values


class SystemConfig(BaseModel):
    """
    Complete system configuration with validation.
    
    This is the main configuration class that defines all parameters needed
    for training and inference. Each field has:
    - Type checking (automatically validated by Pydantic)
    - Range validation (e.g., resolution must be ≤750×750)
    - Default values (so users only need to specify what they want to change)
    - Documentation strings (shown in this docstring and in YAML comments)
    
    Configuration Modes:
    - "neural_network": Use only neural network detection
    - "rule_based": Use only traditional rule-based detection
    - "hybrid": Use both and combine predictions with weighted averaging
    
    Architecture Selection:
    - "liteflownet2": Architecture A (higher accuracy, more memory)
    - "spynet": Architecture B (faster, less memory)
    """
    
    # --------------------------------------------------------------------------
    # Architecture Selection
    # --------------------------------------------------------------------------
    # These determine which neural network components to load
    
    feature_extractor: Literal["cnn_pyramid"] = Field(
        default="cnn_pyramid",
        description="Feature extractor architecture (currently only 'cnn_pyramid' supported)"
    )
    
    flow_network: Literal["liteflownet2", "spynet"] = Field(
        ...,  # ... means required field (no default)
        description="Optical flow network: 'liteflownet2' (Architecture A) or 'spynet' (Architecture B)"
    )
    
    # --------------------------------------------------------------------------
    # Operational Mode
    # --------------------------------------------------------------------------
    # Determines whether to use neural network, rule-based, or hybrid detection
    
    mode: Literal["neural_network", "rule_based", "hybrid"] = Field(
        default="neural_network",
        description="Detection mode: 'neural_network', 'rule_based', or 'hybrid'"
    )
    
    hybrid_weights: HybridWeightsConfig = Field(
        default_factory=HybridWeightsConfig,
        description="Weights for hybrid mode (only used if mode='hybrid')"
    )
    
    # --------------------------------------------------------------------------
    # Model Checkpoint
    # --------------------------------------------------------------------------
    # Path to the trained model weights (.pth file)
    
    checkpoint_path: str = Field(
        ...,  # Required field
        description="Path to trained model checkpoint (.pth file)"
    )
    
    # --------------------------------------------------------------------------
    # Inference Settings
    # --------------------------------------------------------------------------
    # Parameters that control how inference is performed
    
    confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Threshold for binary classification (0.0 to 1.0). "
                    "Predictions above this are classified as 'misaligned'"
    )
    
    enable_uncertainty: bool = Field(
        default=False,
        description="Enable Monte Carlo Dropout for uncertainty estimation. "
                    "This makes inference slower but provides confidence estimates."
    )
    
    uncertainty_samples: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Number of Monte Carlo samples for uncertainty estimation. "
                    "More samples = more accurate uncertainty but slower."
    )
    
    batch_size: int = Field(
        default=4,
        ge=1,
        le=8,
        description="Number of images to process in parallel. "
                    "Typically 4 for four-camera batches. Larger values use more VRAM."
    )
    
    # --------------------------------------------------------------------------
    # Image Preprocessing
    # --------------------------------------------------------------------------
    # How input images are prepared before being fed to the neural network
    
    target_resolution: Tuple[int, int] = Field(
        default=(640, 640),
        description="Target image resolution as [height, width]. "
                    "Images are resized to this before processing. Maximum 750×750."
    )
    
    normalization_mean: List[float] = Field(
        default=[0.485, 0.456, 0.406],
        description="Mean values for image normalization (RGB channels). "
                    "These are ImageNet statistics, standard for most CNNs."
    )
    
    normalization_std: List[float] = Field(
        default=[0.229, 0.224, 0.225],
        description="Standard deviation for image normalization (RGB channels). "
                    "These are ImageNet statistics, standard for most CNNs."
    )
    
    # --------------------------------------------------------------------------
    # Performance Settings
    # --------------------------------------------------------------------------
    # Hardware and optimization settings
    
    device: Literal["cuda", "cpu"] = Field(
        default="cuda",
        description="Device for computation: 'cuda' (GPU) or 'cpu'. "
                    "GPU is strongly recommended for acceptable performance."
    )
    
    mixed_precision: bool = Field(
        default=True,
        description="Use FP16 mixed precision for memory efficiency. "
                    "Reduces VRAM usage by ~30-40% with minimal accuracy impact."
    )
    
    # --------------------------------------------------------------------------
    # Logging and Monitoring
    # --------------------------------------------------------------------------
    # Where to save logs and how verbose to be
    
    tensorboard_dir: str = Field(
        default="./runs",
        description="Directory for TensorBoard logs during training"
    )
    
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging verbosity level"
    )
    
    # --------------------------------------------------------------------------
    # Validators
    # --------------------------------------------------------------------------
    # Custom validation logic for complex constraints
    
    @validator('target_resolution')
    def validate_resolution(cls, v):
        """
        Validate that target resolution respects the 750×750 maximum constraint.
        
        Why 750×750 maximum?
        - Larger images consume more VRAM (quadratically: 2× resolution = 4× memory)
        - 750×750 ensures we stay within 8GB VRAM budget for training
        - This is the key constraint that makes the system work on consumer GPUs
        
        The pyramid architecture processes multiple scales:
        - Level 0: 750×750 (full resolution)
        - Level 1: 375×375 (1/2 scale)
        - Level 2: 188×188 (1/4 scale)  
        - Level 3: 94×94 (1/8 scale)
        
        Each level has different channel counts (64, 128, 256, 512), and all
        must fit in memory simultaneously.
        """
        height, width = v
        
        # Check minimum resolution (too small images lose too much detail)
        if height < 256 or width < 256:
            raise ValueError(
                f"Resolution {height}×{width} is too small. "
                f"Minimum 256×256 required for meaningful feature extraction."
            )
        
        # Check maximum resolution (memory constraint)
        if height > 750 or width > 750:
            raise ValueError(
                f"Resolution {height}×{width} exceeds maximum 750×750. "
                f"This constraint ensures the system runs on consumer GPUs (8-16GB VRAM). "
                f"For larger images, resize them before processing."
            )
        
        return v
    
    @validator('normalization_mean', 'normalization_std')
    def validate_normalization_stats(cls, v, values, **kwargs):
        """
        Validate normalization statistics are RGB triplets.
        
        Normalization is crucial for neural networks:
        - Raw pixel values are 0-255 (uint8)
        - Neural networks work better with normalized inputs around 0 with std ≈1
        - We subtract mean and divide by std for each color channel
        
        ImageNet statistics (default) work well because:
        - Most CNNs are pre-trained on ImageNet
        - These values represent "typical" natural image statistics
        - Using them makes transfer learning more effective
        """
        if len(v) != 3:
            raise ValueError(
                f"Normalization stats must have exactly 3 values (RGB channels), got {len(v)}"
            )
        
        # Check reasonable range (mean should be 0-1 after uint8 scaling, std ~0.1-0.5)
        # We check if v contains values typical of mean (0-1) or std (0.01-1)
        if all(0.0 <= val <= 1.0 for val in v):
            # Could be either mean or std, both are valid in this range
            if all(val >= 0.01 for val in v) or all(val < 0.01 for val in v):
                return v
            # If some values are very small (< 0.01), probably std with invalid values
            if any(val < 0.01 for val in v):
                raise ValueError(
                    f"normalization_std values should be >= 0.01, got {v}"
                )
        else:
            raise ValueError(
                f"Normalization values should be in range [0, 1], got {v}"
            )
        
        return v
    
    @validator('checkpoint_path')
    def validate_checkpoint_exists(cls, v):
        """
        Validate that checkpoint file exists if specified.
        
        Note: This validation is only performed when loading a config for
        inference. During training, the checkpoint doesn't exist yet (we'll
        create it). So we only warn, not error.
        """
        if v and v != "":
            checkpoint = Path(v)
            if not checkpoint.exists():
                logger.warning(
                    f"Checkpoint file not found: {v}. "
                    f"This is normal during training (checkpoint will be created). "
                    f"For inference, make sure the path is correct."
                )
        
        return v
    
    class Config:
        """Pydantic configuration for this model."""
        # Allow extra fields (for forward compatibility)
        extra = "forbid"  # Actually, forbid extra fields to catch typos
        # Use enum values instead of names
        use_enum_values = True


# ==============================================================================
# Configuration Loading Functions
# ==============================================================================


def load_config_from_yaml(yaml_path: str) -> SystemConfig:
    """
    Load and validate configuration from a YAML file.
    
    This is the main function users call to load configuration. It:
    1. Reads the YAML file
    2. Parses it into a Python dictionary
    3. Validates all fields using Pydantic
    4. Returns a SystemConfig object with all parameters validated
    
    Args:
        yaml_path: Path to YAML configuration file
    
    Returns:
        SystemConfig: Validated configuration object
    
    Raises:
        FileNotFoundError: If YAML file doesn't exist
        yaml.YAMLError: If YAML file is malformed
        pydantic.ValidationError: If configuration values are invalid
    
    Example:
        >>> config = load_config_from_yaml("config/architecture_a.yaml")
        >>> print(config.flow_network)  # "liteflownet2"
        >>> print(config.target_resolution)  # (640, 640)
    """
    yaml_path = Path(yaml_path)
    
    # Check if file exists
    if not yaml_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {yaml_path}\n"
            f"Make sure the path is correct. Available example configs:\n"
            f"  - config/architecture_a.yaml (LiteFlowNet2)\n"
            f"  - config/architecture_b.yaml (SpyNet)"
        )
    
    # Read and parse YAML
    try:
        with open(yaml_path, 'r') as f:
            config_dict = yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML file: {yaml_path}")
        logger.error(f"YAML error: {e}")
        raise ValueError(
            f"Malformed YAML configuration file: {yaml_path}\n"
            f"Error: {e}\n"
            f"Make sure the file uses valid YAML syntax:\n"
            f"  - Use spaces for indentation (not tabs)\n"
            f"  - Use : after key names\n"
            f"  - Check for matching quotes and brackets"
        )
    
    if config_dict is None:
        raise ValueError(
            f"Configuration file is empty: {yaml_path}\n"
            f"The file must contain valid configuration parameters."
        )
    
    # Validate and create config object
    try:
        config = SystemConfig(**config_dict)
    except Exception as e:
        logger.error(f"Configuration validation failed for: {yaml_path}")
        logger.error(f"Validation error: {e}")
        raise ValueError(
            f"Invalid configuration in {yaml_path}\n"
            f"Error: {e}\n\n"
            f"Common issues:\n"
            f"  - flow_network must be 'liteflownet2' or 'spynet'\n"
            f"  - mode must be 'neural_network', 'rule_based', or 'hybrid'\n"
            f"  - target_resolution must be ≤750×750\n"
            f"  - confidence_threshold must be between 0.0 and 1.0\n"
            f"  - checkpoint_path must point to a .pth file\n"
            f"\nSee config/ directory for example configurations."
        )
    
    logger.info(f"✓ Configuration loaded successfully from {yaml_path}")
    logger.info(f"  Mode: {config.mode}")
    logger.info(f"  Flow Network: {config.flow_network}")
    logger.info(f"  Target Resolution: {config.target_resolution}")
    logger.info(f"  Device: {config.device}")
    
    return config


def save_config_to_yaml(config: SystemConfig, yaml_path: str) -> None:
    """
    Save configuration to a YAML file.
    
    This is useful for:
    - Saving the exact configuration used during training
    - Creating checkpoint metadata
    - Reproducing experiments
    
    Args:
        config: SystemConfig object to save
        yaml_path: Where to save the YAML file
    
    Example:
        >>> config = SystemConfig(flow_network="liteflownet2")
        >>> save_config_to_yaml(config, "experiments/run_001/config.yaml")
    """
    yaml_path = Path(yaml_path)
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert config to dictionary
    config_dict = config.dict()
    
    # Write to YAML with nice formatting
    with open(yaml_path, 'w') as f:
        yaml.dump(
            config_dict,
            f,
            default_flow_style=False,  # Use block style (more readable)
            sort_keys=False,  # Keep original order
            indent=2
        )
    
    logger.info(f"✓ Configuration saved to {yaml_path}")


def create_default_config(
    flow_network: Literal["liteflownet2", "spynet"],
    checkpoint_path: str,
    mode: Literal["neural_network", "rule_based", "hybrid"] = "neural_network"
) -> SystemConfig:
    """
    Create a configuration with default values.
    
    This is useful for programmatic configuration or quick testing without
    needing a YAML file.
    
    Args:
        flow_network: Which optical flow network to use
        checkpoint_path: Path to model checkpoint
        mode: Detection mode (default: "neural_network")
    
    Returns:
        SystemConfig: Configuration with default values
    
    Example:
        >>> config = create_default_config(
        ...     flow_network="liteflownet2",
        ...     checkpoint_path="models/best_model.pth"
        ... )
        >>> print(config.batch_size)  # 4 (default)
        >>> print(config.target_resolution)  # (640, 640) (default)
    """
    return SystemConfig(
        flow_network=flow_network,
        checkpoint_path=checkpoint_path,
        mode=mode
        # All other fields use their defaults
    )


# ==============================================================================
# Main Entry Point for Testing
# ==============================================================================


def main():
    """
    Command-line interface for testing configuration loading.
    
    Usage:
        python -m dl_misalignment.utils.config config/architecture_a.yaml
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m dl_misalignment.utils.config <config.yaml>")
        print("\nExample:")
        print("  python -m dl_misalignment.utils.config config/architecture_a.yaml")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    print(f"\nLoading configuration from: {config_path}")
    print("=" * 80)
    
    try:
        config = load_config_from_yaml(config_path)
        
        print("\n✓ Configuration loaded and validated successfully!")
        print("\nConfiguration Summary:")
        print("-" * 80)
        print(f"Mode: {config.mode}")
        print(f"Flow Network: {config.flow_network}")
        print(f"Checkpoint: {config.checkpoint_path}")
        print(f"Target Resolution: {config.target_resolution}")
        print(f"Batch Size: {config.batch_size}")
        print(f"Device: {config.device}")
        print(f"Mixed Precision: {config.mixed_precision}")
        print(f"Confidence Threshold: {config.confidence_threshold}")
        
        if config.mode == "hybrid":
            print("\nHybrid Mode Weights:")
            print(f"  Neural: {config.hybrid_weights.neural}")
            print(f"  Rule-based: {config.hybrid_weights.rule_based}")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\n❌ Configuration loading failed:")
        print(f"{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
