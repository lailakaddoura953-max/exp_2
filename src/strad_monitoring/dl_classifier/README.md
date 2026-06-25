# DL Classifier Wrapper

This module provides a simplified interface to the existing deep learning misalignment detection system for integration with the Strad Carrier monitoring automation.

## Components

### `ClassificationResult`

Dataclass representing the result of a camera misalignment classification:

- `severity`: str - Classification level ('none', 'moderate', 'critical')
- `confidence`: float - Confidence score from 0.0 to 1.0
- `processing_time_ms`: float - Time taken for classification in milliseconds
- `raw_output`: Dict - Model-specific diagnostic data

### `DLClassifierWrapper`

Main wrapper class that integrates the InferenceEngine for single-snapshot classification:

**Initialization:**
```python
wrapper = DLClassifierWrapper(
    model_checkpoint_path='path/to/checkpoint.pth',
    config={
        'target_resolution': [640, 640],
        'flow_network': 'liteflownet2',
        'confidence_threshold': 0.5,
        'enable_uncertainty': False,
        'none_threshold': 0.3,
        'moderate_threshold': 0.7
    },
    device='cuda'  # or 'cpu'
)
```

**Classification:**
```python
import numpy as np

# Snapshot from VLC capture (RGB numpy array)
snapshot = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

# Classify
result = wrapper.classify_snapshot(snapshot)

print(f"Severity: {result.severity}")
print(f"Confidence: {result.confidence:.3f}")
print(f"Processing time: {result.processing_time_ms:.1f}ms")
```

## Severity Mapping

The wrapper maps model probability outputs to severity levels:

| Probability Range | Severity | Description |
|------------------|----------|-------------|
| < 0.3 | `none` | Properly aligned |
| 0.3 - 0.7 | `moderate` | Minor misalignment |
| ≥ 0.7 | `critical` | Severe misalignment |

## Processing Pipeline

1. **Validate Input**: Check snapshot is RGB numpy array with shape (H, W, 3)
2. **Preprocess**: 
   - Convert to PIL Image
   - Resize to 640x640
   - Normalize using ImageNet statistics
   - Convert to PyTorch tensor
3. **Inference**: Run through neural network model via InferenceEngine
4. **Map Output**: Convert probability to severity level
5. **Return Result**: Classification with confidence and timing

## Integration with Existing Code

This wrapper integrates with:

- `InferenceEngine` from `src/dl_misalignment/inference/inference_engine.py`
- `ImagePreprocessor` from `src/dl_misalignment/inference/preprocessing.py`

The wrapper simplifies the 4-camera batch processing interface of InferenceEngine to a single-snapshot interface suitable for the monitoring system.

## Requirements Satisfied

- **Requirement 4.1**: Load snapshot and process through DL model
- **Requirement 4.2**: Assign classification result (none/moderate/critical)

## Usage Example

```python
from src.strad_monitoring.dl_classifier import (
    DLClassifierWrapper,
    create_default_config
)

# Load with default configuration
config = create_default_config()
wrapper = DLClassifierWrapper(
    model_checkpoint_path='models/misalignment_detector.pth',
    config=config,
    device='cuda'
)

# Classify a snapshot
import numpy as np
snapshot = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
result = wrapper.classify_snapshot(snapshot)

# Get statistics
stats = wrapper.get_statistics()
print(f"Classifications performed: {stats['classification_count']}")
print(f"Average processing time: {stats['average_processing_time_ms']:.1f}ms")
```

## Performance

- **Target latency**: ≤10 seconds per classification (Requirement 4.6)
- **Input resolution**: 640x640 pixels (configurable)
- **Device support**: CUDA GPU (recommended) or CPU

## Notes

- The wrapper validates snapshot dimensions (minimum 640x480 per Requirement 3.5)
- Preprocessing handles various input formats (numpy array, PIL Image, torch Tensor)
- Statistics tracking provides performance monitoring
- Model checkpoint loading includes validation and error handling
