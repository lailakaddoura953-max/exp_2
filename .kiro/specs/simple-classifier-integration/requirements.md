# Requirements Document

## Introduction

The strad monitoring system currently uses `DLClassifierWrapper` with `InferenceEngine` to classify camera misalignment. However, models trained with `train_strad_classifier.py` save checkpoints in a different format (`model_state_dict`) than what `InferenceEngine` expects (`feature_extractor_state`). Additionally, `InferenceEngine` fails on CPU-only devices because it doesn't properly handle CUDA tensor deserialization.

This feature integrates `SimpleClassifierWrapper` as an alternative loading path that:
- Loads checkpoints saved by `train_strad_classifier.py` (with `model_state_dict` key)
- Works on both CPU and GPU devices using proper `map_location` handling
- Maintains the same `classify_snapshot()` interface as `DLClassifierWrapper`
- Returns compatible `ClassificationResult` objects for the orchestrator

The integration affects two components:
1. **Monitoring Orchestrator** (`src/strad_monitoring/orchestration/orchestrator.py`) - Uses classifier for hourly monitoring cycles
2. **Web Application Backend** (`docs/backend/app.py`) - Uses classifier for live inference API

## Glossary

- **Monitoring_System**: The strad carrier monitoring automation system that performs hourly checks
- **Web_App**: The Flask-based web application providing live inference API
- **SimpleClassifierWrapper**: Lightweight wrapper class for models trained with `train_strad_classifier.py`
- **DLClassifierWrapper**: Existing wrapper class that uses InferenceEngine (expects different checkpoint format)
- **InferenceEngine**: Complex inference system expecting `feature_extractor_state` checkpoint format
- **SimpleStradClassifier**: CNN model architecture for strad misalignment classification
- **Checkpoint**: Model weights file saved during training (`.pth` file)
- **ClassificationResult**: Data structure containing severity, confidence, and timing information
- **Orchestrator**: Main coordination component that runs hourly monitoring cycles
- **Device**: Computing device for inference (either 'cpu' or 'cuda')

## Requirements

### Requirement 1: Configuration-Based Classifier Selection

**User Story:** As a system administrator, I want to configure which classifier wrapper to use via system configuration, so that I can switch between InferenceEngine and SimpleClassifierWrapper without code changes

#### Acceptance Criteria

1. THE System_Config SHALL include a field `classifier_type` with allowed values `'inference_engine'` or `'simple_classifier'`
2. THE System_Config SHALL include a field `model_checkpoint_path` specifying the path to the model checkpoint file
3. WHEN `classifier_type` is `'simple_classifier'`, THE Orchestrator SHALL instantiate SimpleClassifierWrapper
4. WHEN `classifier_type` is `'inference_engine'`, THE Orchestrator SHALL instantiate DLClassifierWrapper with InferenceEngine
5. THE Web_App SHALL use the same `classifier_type` configuration to determine which wrapper to load

### Requirement 2: SimpleClassifierWrapper Initialization

**User Story:** As a developer, I want SimpleClassifierWrapper to load checkpoints saved by `train_strad_classifier.py`, so that trained models can be deployed without conversion

#### Acceptance Criteria

1. THE SimpleClassifierWrapper SHALL accept a `model_checkpoint_path` parameter pointing to a `.pth` checkpoint file
2. THE SimpleClassifierWrapper SHALL accept a `device` parameter with values `'cpu'` or `'cuda'`
3. WHEN loading a checkpoint, THE SimpleClassifierWrapper SHALL use `map_location=self.device` to handle CPU/GPU conversion
4. THE SimpleClassifierWrapper SHALL load model weights from the `'model_state_dict'` key in the checkpoint
5. IF the checkpoint does not contain `'model_state_dict'` key, THEN THE SimpleClassifierWrapper SHALL raise a descriptive error indicating the expected checkpoint format

### Requirement 3: Device Compatibility

**User Story:** As a deployment engineer, I want the classifier to work on CPU-only devices, so that I can deploy to laptops without CUDA support

#### Acceptance Criteria

1. WHEN `device='cpu'` is specified, THE SimpleClassifierWrapper SHALL load CUDA-trained checkpoints successfully using `map_location`
2. WHEN `device='cuda'` is specified AND CUDA is available, THE SimpleClassifierWrapper SHALL use GPU acceleration
3. WHEN `device='cuda'` is specified AND CUDA is unavailable, THEN THE SimpleClassifierWrapper SHALL raise an error indicating CUDA is not available
4. THE Orchestrator SHALL auto-detect device availability using `torch.cuda.is_available()` and default to CPU if CUDA is unavailable
5. THE Web_App SHALL auto-detect device availability using `torch.cuda.is_available()` and default to CPU if CUDA is unavailable

### Requirement 4: Classification Interface Compatibility

**User Story:** As a system integrator, I want SimpleClassifierWrapper to provide the same interface as DLClassifierWrapper, so that existing code requires minimal changes

#### Acceptance Criteria

1. THE SimpleClassifierWrapper SHALL provide a `classify_snapshot(image: np.ndarray)` method
2. THE `classify_snapshot()` method SHALL accept RGB numpy arrays with shape `(H, W, 3)` and dtype `uint8`
3. THE `classify_snapshot()` method SHALL return a ClassificationResult object with fields: `severity`, `confidence`, `processing_time_ms`, and `raw_output`
4. THE ClassificationResult.severity field SHALL contain one of: `'none'`, `'moderate'`, or `'critical'`
5. THE ClassificationResult.confidence field SHALL be a float between 0.0 and 1.0
6. THE ClassificationResult.processing_time_ms field SHALL contain the inference time in milliseconds
7. THE ClassificationResult.raw_output field SHALL be a dictionary containing diagnostic information

### Requirement 5: Image Preprocessing

**User Story:** As a machine learning engineer, I want images preprocessed consistently with training, so that inference accuracy matches validation performance

#### Acceptance Criteria

1. WHEN preprocessing an image, THE SimpleClassifierWrapper SHALL resize it to 640x640 pixels
2. WHEN preprocessing an image, THE SimpleClassifierWrapper SHALL normalize pixel values to the range [0, 1] by dividing by 255
3. WHEN preprocessing an image, THE SimpleClassifierWrapper SHALL apply ImageNet normalization with mean=[0.485, 0.456, 0.406] and std=[0.229, 0.224, 0.225]
4. WHEN preprocessing an image, THE SimpleClassifierWrapper SHALL convert from (H, W, C) numpy format to (1, C, H, W) PyTorch tensor format
5. THE SimpleClassifierWrapper SHALL move the preprocessed tensor to the configured device (CPU or GPU)

### Requirement 6: Orchestrator Integration

**User Story:** As a system operator, I want the orchestrator to use SimpleClassifierWrapper when configured, so that I can deploy models trained with the simple training script

#### Acceptance Criteria

1. WHEN initializing components, THE Orchestrator SHALL read the `classifier_type` field from configuration
2. IF `classifier_type` is `'simple_classifier'`, THEN THE Orchestrator SHALL create a SimpleClassifierWrapper instance
3. IF `classifier_type` is `'inference_engine'`, THEN THE Orchestrator SHALL create a DLClassifierWrapper instance (existing behavior)
4. THE Orchestrator SHALL pass the classifier instance to `process_single_strad()` for snapshot classification
5. THE Orchestrator SHALL handle SimpleClassifierWrapper errors the same way as DLClassifierWrapper errors (log and continue with remaining strads)

### Requirement 7: Web Application Integration

**User Story:** As a web application user, I want to run inference using SimpleClassifierWrapper through the API, so that I can test models in real-time

#### Acceptance Criteria

1. WHEN initializing the Flask app, THE Web_App SHALL read the `classifier_type` field from system configuration
2. IF `classifier_type` is `'simple_classifier'`, THEN THE Web_App SHALL create a SimpleClassifierWrapper instance
3. IF `classifier_type` is `'inference_engine'`, THEN THE Web_App SHALL create a DLClassifierWrapper instance (existing behavior)
4. THE `/api/inference` endpoint SHALL use the configured classifier wrapper for single-image inference
5. THE `/api/model/status` endpoint SHALL report which classifier type is loaded (`'simple_classifier'` or `'inference_engine'`)

### Requirement 8: Fallback Behavior for Missing Models

**User Story:** As a developer, I want the system to handle missing model files gracefully in testing mode, so that I can test other components without a trained model

#### Acceptance Criteria

1. WHEN `enable_local_testing_mode` is true AND the model checkpoint file does not exist, THE Orchestrator SHALL log a warning and set the classifier to None
2. WHEN the classifier is None AND a snapshot needs classification, THE Orchestrator SHALL return a mock ClassificationResult with severity='none' and confidence=0.5
3. WHEN `enable_local_testing_mode` is false AND the model checkpoint file does not exist, THEN THE Orchestrator SHALL raise an error during initialization
4. THE Web_App SHALL use the same fallback behavior: None classifier returns mock results in testing mode
5. THE `/api/model/status` endpoint SHALL indicate when mock mode is active

### Requirement 9: Error Handling and Validation

**User Story:** As a system administrator, I want clear error messages when configuration is invalid, so that I can quickly diagnose deployment issues

#### Acceptance Criteria

1. IF `classifier_type` has an invalid value (not `'simple_classifier'` or `'inference_engine'`), THEN THE System SHALL raise a ValueError with a descriptive message
2. IF `model_checkpoint_path` is not provided in configuration, THEN THE System SHALL raise a ValueError indicating the missing field
3. IF the checkpoint file does not exist at the specified path, THEN THE System SHALL raise a FileNotFoundError with the full path
4. IF checkpoint loading fails due to format mismatch, THEN THE SimpleClassifierWrapper SHALL raise an error indicating expected format (`model_state_dict` key)
5. WHEN preprocessing fails due to invalid image format, THE SimpleClassifierWrapper SHALL raise a ValueError with details about the expected format

### Requirement 10: Logging and Diagnostics

**User Story:** As a system operator, I want detailed logging of classifier initialization and usage, so that I can monitor system health and troubleshoot issues

#### Acceptance Criteria

1. WHEN SimpleClassifierWrapper is initialized, THE System SHALL log the classifier type, checkpoint path, and device being used
2. WHEN a checkpoint is loaded successfully, THE System SHALL log confirmation with the model architecture name
3. WHEN classification is performed, THE System SHALL log the severity, confidence, and processing time
4. IF classification processing time exceeds 10 seconds, THEN THE System SHALL log a warning
5. THE ClassificationResult.raw_output dictionary SHALL include fields: `model_name='SimpleStradClassifier'`, `device`, `image_size`, and `preprocessing_time_ms`

### Requirement 11: Backward Compatibility

**User Story:** As a system maintainer, I want existing InferenceEngine-based deployments to continue working, so that the integration doesn't break production systems

#### Acceptance Criteria

1. WHEN `classifier_type` is not specified in configuration, THE System SHALL default to `'inference_engine'` for backward compatibility
2. THE DLClassifierWrapper and InferenceEngine SHALL remain unchanged and functional
3. THE System SHALL support both checkpoint formats simultaneously in different deployments
4. IF a checkpoint fails to load with SimpleClassifierWrapper, THE error message SHALL suggest trying `classifier_type='inference_engine'` if it's an InferenceEngine checkpoint
5. THE System SHALL not remove or deprecate any existing DLClassifierWrapper functionality

### Requirement 12: Configuration File Updates

**User Story:** As a deployment engineer, I want example configuration showing how to enable SimpleClassifierWrapper, so that I can easily configure new deployments

#### Acceptance Criteria

1. THE `system_config.json` example file SHALL include a `classifier_type` field with value `'simple_classifier'`
2. THE `system_config.json` example file SHALL include comments explaining the difference between `'simple_classifier'` and `'inference_engine'`
3. THE configuration documentation SHALL explain when to use SimpleClassifierWrapper vs InferenceEngine
4. THE configuration SHALL note that SimpleClassifierWrapper requires checkpoints from `train_strad_classifier.py`
5. THE configuration SHALL note that InferenceEngine requires checkpoints from the multi-camera misalignment detector project
