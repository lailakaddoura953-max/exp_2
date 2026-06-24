"""
Hardware Validation and GPU Monitoring Utilities

This module provides functions for:
1. Verifying GPU availability and CUDA/ROCm compatibility
2. Logging GPU specifications (VRAM, compute capability, driver version)
3. Monitoring GPU memory usage during training and inference
4. Validating minimum hardware requirements

These utilities help ensure the system runs on appropriate hardware and
provide early warnings when hardware constraints are not met.
"""

import logging
from typing import Dict, Optional, Tuple
import sys

# Try to import PyTorch - this script can run even if PyTorch isn't installed yet
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None  # type: ignore

# Set up logging
logger = logging.getLogger(__name__)


def check_pytorch_installation() -> bool:
    """
    Check if PyTorch is installed and importable.
    
    Returns:
        bool: True if PyTorch is available, False otherwise
    """
    if not TORCH_AVAILABLE:
        logger.error("PyTorch is not installed. Please install it first:")
        logger.error("  pip install -r requirements.txt")
        logger.error("Or visit https://pytorch.org/get-started/locally/")
        return False
    
    logger.info(f"PyTorch version: {torch.__version__}")
    return True


def get_cuda_info() -> Dict[str, any]:
    """
    Get detailed CUDA information including version, device count, and capabilities.
    
    Returns:
        dict: Dictionary containing CUDA information:
            - 'available': Whether CUDA is available
            - 'version': CUDA version string
            - 'device_count': Number of CUDA devices
            - 'current_device': Index of current device
            - 'devices': List of device information dicts
    """
    if not TORCH_AVAILABLE:
        return {'available': False, 'reason': 'PyTorch not installed'}
    
    cuda_info = {
        'available': torch.cuda.is_available(),
        'version': None,
        'device_count': 0,
        'current_device': None,
        'devices': []
    }
    
    if not cuda_info['available']:
        logger.warning("CUDA is not available. Possible reasons:")
        logger.warning("  1. No NVIDIA GPU detected")
        logger.warning("  2. CUDA drivers not installed")
        logger.warning("  3. PyTorch installed without CUDA support")
        logger.warning("  4. Using AMD GPU (requires ROCm-enabled PyTorch)")
        return cuda_info
    
    # Get CUDA version
    cuda_info['version'] = torch.version.cuda
    cuda_info['device_count'] = torch.cuda.device_count()
    cuda_info['current_device'] = torch.cuda.current_device()
    
    # Get information for each GPU
    for i in range(cuda_info['device_count']):
        device_props = torch.cuda.get_device_properties(i)
        
        # Compute capability determines which CUDA features are supported
        # Pascal (6.1) is minimum for this system
        compute_capability = f"{device_props.major}.{device_props.minor}"
        
        device_info = {
            'index': i,
            'name': device_props.name,
            'compute_capability': compute_capability,
            'total_memory_gb': device_props.total_memory / (1024**3),  # Convert bytes to GB
            'multi_processor_count': device_props.multi_processor_count,
        }
        
        cuda_info['devices'].append(device_info)
    
    return cuda_info


def log_gpu_specifications(verbose: bool = True) -> None:
    """
    Log detailed GPU specifications to help with debugging and performance tuning.
    
    This function prints comprehensive GPU information including:
    - GPU model name
    - Total VRAM (important for batch size selection)
    - Compute capability (determines supported CUDA features)
    - Number of streaming multiprocessors (affects parallelism)
    - CUDA version
    
    Args:
        verbose: If True, prints detailed information. If False, only critical info.
    """
    if not check_pytorch_installation():
        return
    
    cuda_info = get_cuda_info()
    
    if not cuda_info['available']:
        logger.error("=" * 80)
        logger.error("GPU NOT AVAILABLE")
        logger.error("=" * 80)
        logger.error("This system requires a CUDA-capable GPU for efficient operation.")
        logger.error("Training and inference will be extremely slow on CPU.")
        logger.error("")
        logger.error("Minimum requirements:")
        logger.error("  - Training: NVIDIA GPU with 8GB+ VRAM (CUDA 6.1+)")
        logger.error("  - Inference: NVIDIA GPU with 4GB+ VRAM")
        logger.error("=" * 80)
        return
    
    # Print GPU information
    logger.info("=" * 80)
    logger.info("GPU HARDWARE DETECTED")
    logger.info("=" * 80)
    logger.info(f"CUDA Version: {cuda_info['version']}")
    logger.info(f"Number of GPUs: {cuda_info['device_count']}")
    logger.info(f"Current Device: GPU {cuda_info['current_device']}")
    logger.info("")
    
    for device in cuda_info['devices']:
        logger.info(f"GPU {device['index']}: {device['name']}")
        logger.info(f"  Total VRAM: {device['total_memory_gb']:.2f} GB")
        logger.info(f"  Compute Capability: {device['compute_capability']}")
        
        if verbose:
            logger.info(f"  Multiprocessors: {device['multi_processor_count']}")
        
        # Check if compute capability meets minimum requirements
        major, minor = map(int, device['compute_capability'].split('.'))
        compute_value = major * 10 + minor
        
        if compute_value < 61:  # Pascal (6.1) is minimum
            logger.warning(f"  ⚠️  WARNING: Compute capability {device['compute_capability']} is below minimum (6.1)")
            logger.warning(f"  This GPU may not support required CUDA features.")
        else:
            logger.info(f"  ✓ Compute capability meets minimum requirements (6.1+)")
        
        logger.info("")
    
    logger.info("=" * 80)


def validate_training_hardware() -> Tuple[bool, str]:
    """
    Validate that the system meets minimum hardware requirements for training.
    
    Training Requirements (from requirements.md):
    - NVIDIA GPU with 8GB+ VRAM
    - CUDA compute capability 6.1+ (Pascal architecture or newer)
    - CUDA Toolkit 11.7+
    
    Returns:
        tuple: (is_valid, message)
            - is_valid: True if hardware meets requirements
            - message: Explanation of validation result
    """
    if not TORCH_AVAILABLE:
        return False, "PyTorch is not installed. Cannot validate hardware."
    
    cuda_info = get_cuda_info()
    
    if not cuda_info['available']:
        return False, (
            "No CUDA-capable GPU detected. Training requires NVIDIA GPU with 8GB+ VRAM. "
            "For AMD GPUs, install PyTorch with ROCm support."
        )
    
    # Check if at least one GPU meets requirements
    for device in cuda_info['devices']:
        # Check VRAM (minimum 8GB for training)
        if device['total_memory_gb'] < 8.0:
            logger.warning(
                f"GPU {device['index']} ({device['name']}) has {device['total_memory_gb']:.2f} GB VRAM. "
                f"Minimum 8GB recommended for training."
            )
            continue
        
        # Check compute capability (minimum 6.1 for Pascal features)
        major, minor = map(int, device['compute_capability'].split('.'))
        compute_value = major * 10 + minor
        
        if compute_value < 61:
            logger.warning(
                f"GPU {device['index']} has compute capability {device['compute_capability']}. "
                f"Minimum 6.1 required (Pascal architecture or newer)."
            )
            continue
        
        # Found a GPU that meets requirements
        return True, (
            f"Hardware validated: GPU {device['index']} ({device['name']}) meets training requirements. "
            f"VRAM: {device['total_memory_gb']:.2f} GB, Compute: {device['compute_capability']}"
        )
    
    # No GPU met the requirements
    return False, (
        "No GPU meets training requirements. Need: 8GB+ VRAM, compute capability 6.1+. "
        "Training may fail or be very slow with insufficient VRAM."
    )


def validate_inference_hardware() -> Tuple[bool, str]:
    """
    Validate that the system meets minimum hardware requirements for inference.
    
    Inference Requirements (from requirements.md):
    - NVIDIA GPU with 4GB+ VRAM
    - CUDA compute capability 6.1+ (Pascal or newer)
    - Also supports NVIDIA Jetson platforms (Xavier, Orin)
    
    Returns:
        tuple: (is_valid, message)
            - is_valid: True if hardware meets requirements
            - message: Explanation of validation result
    """
    if not TORCH_AVAILABLE:
        return False, "PyTorch is not installed. Cannot validate hardware."
    
    cuda_info = get_cuda_info()
    
    if not cuda_info['available']:
        return False, (
            "No CUDA-capable GPU detected. Inference requires NVIDIA GPU with 4GB+ VRAM."
        )
    
    # Check if at least one GPU meets requirements
    for device in cuda_info['devices']:
        # Check VRAM (minimum 4GB for inference)
        if device['total_memory_gb'] < 4.0:
            logger.warning(
                f"GPU {device['index']} ({device['name']}) has {device['total_memory_gb']:.2f} GB VRAM. "
                f"Minimum 4GB recommended for inference."
            )
            continue
        
        # Check compute capability
        major, minor = map(int, device['compute_capability'].split('.'))
        compute_value = major * 10 + minor
        
        if compute_value < 61:
            logger.warning(
                f"GPU {device['index']} has compute capability {device['compute_capability']}. "
                f"Minimum 6.1 recommended."
            )
            continue
        
        # Found a GPU that meets requirements
        return True, (
            f"Hardware validated: GPU {device['index']} ({device['name']}) meets inference requirements. "
            f"VRAM: {device['total_memory_gb']:.2f} GB, Compute: {device['compute_capability']}"
        )
    
    # No GPU met the requirements
    return False, (
        "No GPU meets inference requirements. Need: 4GB+ VRAM, compute capability 6.1+. "
        "Inference may fail or be very slow."
    )


def get_gpu_memory_usage(device: Optional[int] = None) -> Dict[str, float]:
    """
    Get current GPU memory usage statistics.
    
    This is useful for monitoring memory consumption during training and inference
    to ensure we stay within VRAM limits.
    
    Args:
        device: GPU device index. If None, uses current device.
    
    Returns:
        dict: Dictionary with memory statistics in GB:
            - 'allocated': Currently allocated memory
            - 'reserved': Memory reserved by caching allocator
            - 'total': Total GPU memory
            - 'free': Available memory
            - 'utilization_percent': Percentage of memory in use
    """
    if not TORCH_AVAILABLE or not torch.cuda.is_available():
        return {}
    
    if device is None:
        device = torch.cuda.current_device()
    
    # Get memory statistics (all values in bytes)
    allocated = torch.cuda.memory_allocated(device)
    reserved = torch.cuda.memory_reserved(device)
    total = torch.cuda.get_device_properties(device).total_memory
    free = total - reserved
    
    # Convert to GB for readability
    GB = 1024 ** 3
    
    return {
        'allocated_gb': allocated / GB,
        'reserved_gb': reserved / GB,
        'total_gb': total / GB,
        'free_gb': free / GB,
        'utilization_percent': (reserved / total) * 100
    }


def log_memory_usage(device: Optional[int] = None, prefix: str = "") -> None:
    """
    Log current GPU memory usage in a readable format.
    
    This function is typically called periodically during training (e.g., every
    100 steps) to monitor memory consumption and detect memory leaks.
    
    Args:
        device: GPU device index. If None, uses current device.
        prefix: Optional prefix for the log message (e.g., "Step 1000")
    """
    memory = get_gpu_memory_usage(device)
    
    if not memory:
        logger.debug(f"{prefix} GPU memory monitoring not available (no CUDA)")
        return
    
    logger.info(
        f"{prefix} GPU Memory: "
        f"Allocated={memory['allocated_gb']:.2f}GB, "
        f"Reserved={memory['reserved_gb']:.2f}GB, "
        f"Total={memory['total_gb']:.2f}GB, "
        f"Free={memory['free_gb']:.2f}GB "
        f"({memory['utilization_percent']:.1f}% utilized)"
    )


def main():
    """
    Command-line interface for hardware validation.
    
    This can be run as a standalone script to check hardware compatibility:
        python -m dl_misalignment.utils.hardware
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    print("\n" + "=" * 80)
    print("Deep Learning Misalignment Detection System")
    print("Hardware Validation Script")
    print("=" * 80 + "\n")
    
    # Check PyTorch installation
    if not check_pytorch_installation():
        sys.exit(1)
    
    # Log GPU specifications
    log_gpu_specifications(verbose=True)
    
    # Validate training hardware
    print("\nTraining Hardware Validation:")
    print("-" * 80)
    is_valid, message = validate_training_hardware()
    if is_valid:
        print(f"✓ {message}")
    else:
        print(f"✗ {message}")
    
    # Validate inference hardware
    print("\nInference Hardware Validation:")
    print("-" * 80)
    is_valid, message = validate_inference_hardware()
    if is_valid:
        print(f"✓ {message}")
    else:
        print(f"✗ {message}")
    
    # Show current memory usage
    print("\nCurrent GPU Memory Usage:")
    print("-" * 80)
    log_memory_usage()
    
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
