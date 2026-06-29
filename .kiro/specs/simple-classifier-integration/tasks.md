# Implementation Plan: Simple Classifier Integration

## Overview

This implementation integrates `SimpleClassifierWrapper` as an alternative classifier loading mechanism for the strad monitoring system. The system currently uses `DLClassifierWrapper` with `InferenceEngine`, which has limitations with checkpoint formats and CPU-only devices. This integration provides:

- Configuration-based classifier selection between `simple_classifier` and `inference_engine`
- Support for models trained with `train_strad_classifier.py` (using `model_state_dict` format)
- Cross-device compatibility (CPU/GPU) using PyTorch's `map_location` parameter
- Interface compatibility with existing `DLClassifierWrapper` API

The implementation involves modifying two main components:
1. **Orchestrator** (`src/strad_monitoring/orchestration/orchestrator.py`) - Monitoring system
2. **Web Application** (`docs/backend/app.py`) - Live inference API

And enhancing one component:
3. **SimpleClassifierWrapper** (`src/strad_monitoring/dl_classifier/simple_classifier_wrapper.py`) - Add `raw_output` field

## Tasks

- [x] 1. Extend SystemConfig with classifier_type field
  - Add `classifier_type` field to SystemConfig dataclass with default value `'inference_engine'`
  - Add validation logic in `ConfigurationManager.validate_config()` to check valid values
  - Field should accept: `'simple_classifier'` or `'inference_engine'`
  - _Requirements: 1.1, 1.2, 9.1, 11.1_

- [x] 2. Enhance SimpleClassifierWrapper interface
  - [x] 2.1 Add raw_output field to ClassificationResult dataclass
    - Modify ClassificationResult to include `raw_output: Dict` field
    - Ensure field is populated with diagnostic information
    - _Requirements: 4.7, 10.5, 12_

  - [x] 2.2 Update classify_snapshot to populate raw_output dictionary
    - Include keys: `model_name`, `device`, `image_size`, `preprocessing_time_ms`, `class_probabilities`
    - Extract class probabilities from softmax output before taking max
    - _Requirements: 10.5, 12_

  - [x] 2.3 Add checkpoint format validation
    - Validate checkpoint contains `'model_state_dict'` key before loading
    - Raise descriptive KeyError if key is missing
    - Error message should suggest using `classifier_type='inference_engine'` for InferenceEngine checkpoints
    - _Requirements: 2.4, 2.5, 9.4_

  - [ ]* 2.4 Write property tests for SimpleClassifierWrapper enhancements
    - **Property 3: Checkpoint Format Validation**
    - **Property 6: Classification Result Structure Completeness**
    - **Property 12: Raw Output Contains Required Diagnostic Fields**
    - **Validates: Requirements 2.4, 2.5, 4.3, 4.4, 4.5, 4.6, 4.7, 10.5, 9.4**

- [x] 3. Modify Orchestrator classifier initialization
  - [x] 3.1 Add conditional classifier instantiation logic
    - Read `classifier_type` from config with default to `'inference_engine'`
    - Import SimpleClassifierWrapper when `classifier_type='simple_classifier'`
    - Import DLClassifierWrapper when `classifier_type='inference_engine'`
    - Auto-detect device using `torch.cuda.is_available()`
    - Log classifier type and device being used
    - _Requirements: 1.3, 1.4, 3.4, 6.2, 6.3_

  - [x] 3.2 Add error handling for invalid classifier_type
    - Validate classifier_type is one of the two allowed values
    - Raise ValueError with descriptive message if invalid
    - Handle missing checkpoint in testing mode (set classifier to None, log warning)
    - Raise FileNotFoundError in production mode when checkpoint missing
    - _Requirements: 8.1, 8.3, 8.4, 9.1, 9.3_

  - [ ]* 3.3 Write property tests for orchestrator integration
    - **Property 1: Classifier Type Determines Wrapper Instance**
    - **Property 13: Missing Checkpoint Handling in Testing Mode**
    - **Property 14: File Not Found Error in Production Mode**
    - **Property 15: Backward Compatibility Default**
    - **Validates: Requirements 1.3, 1.4, 6.2, 6.3, 8.1, 8.3, 8.4, 9.3, 11.1**

- [x] 4. Modify Web App classifier initialization
  - [x] 4.1 Add conditional classifier instantiation logic in app.py
    - Read `classifier_type` from config with default to `'inference_engine'`
    - Import and instantiate SimpleClassifierWrapper when `classifier_type='simple_classifier'`
    - Import and instantiate DLClassifierWrapper when `classifier_type='inference_engine'`
    - Auto-detect device using `torch.cuda.is_available()`
    - Handle initialization errors gracefully (set classifier to None)
    - _Requirements: 1.5, 7.2, 7.3, 3.5_

  - [x] 4.2 Update /api/model/status endpoint
    - Add `classifier_type` field to JSON response
    - Read value from config object
    - Return `'unknown'` if config not available
    - _Requirements: 7.5, 11_

  - [ ]* 4.3 Write property tests for web app integration
    - **Property 2: Web App Uses Same Classifier Selection Logic**
    - **Property 11: API Endpoint Reports Correct Classifier Type**
    - **Validates: Requirements 1.5, 7.2, 7.3, 7.5**

- [x] 5. Checkpoint - Verify classifier initialization works
  - Test both orchestrator and web app with `classifier_type='simple_classifier'`
  - Test both orchestrator and web app with `classifier_type='inference_engine'`
  - Verify appropriate classifier is instantiated in each case
  - Verify logs show correct classifier type and device
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Add cross-device compatibility tests
  - [x] 6.1 Test CPU-only deployment scenario
    - Create test that forces CPU device even on GPU machines
    - Verify SimpleClassifierWrapper loads CUDA-trained checkpoints on CPU
    - Verify classification succeeds and returns valid results
    - _Requirements: 2.3, 3.1, 3.2_

  - [ ]* 6.2 Write property test for cross-device loading
    - **Property 4: Cross-Device Checkpoint Loading**
    - **Validates: Requirements 2.3, 3.1, 3.2**

- [ ] 7. Add comprehensive input validation tests
  - [ ]* 7.1 Write property tests for image validation
    - **Property 8: Valid Image Acceptance**
    - **Property 9: Invalid Image Rejection**
    - **Validates: Requirements 4.2, 9.5**

  - [ ]* 7.2 Write property test for configuration validation
    - **Property 5: Configuration Validation Rejects Invalid Types**
    - **Validates: Requirements 1.1, 9.1**

- [x] 8. Update configuration example and documentation
  - [x] 8.1 Update system_config.json example
    - Add `classifier_type` field with example value `'simple_classifier'`
    - Add comments explaining difference between classifier types
    - Note that SimpleClassifierWrapper requires checkpoints from `train_strad_classifier.py`
    - Note that InferenceEngine requires checkpoints from multi-camera misalignment detector
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [x] 8.2 Add inline code documentation
    - Document new conditional logic in orchestrator.py
    - Document new conditional logic in app.py
    - Document enhanced SimpleClassifierWrapper methods
    - Document SystemConfig classifier_type field

- [ ] 9. Integration testing across components
  - [ ]* 9.1 Write integration test: End-to-end orchestrator with SimpleClassifierWrapper
    - Create test configuration with `classifier_type='simple_classifier'`
    - Initialize orchestrator and verify classifier type
    - Run `process_single_strad()` and verify classification result structure
    - _Requirements: 6.2, 6.3, 6.4, 6.5_

  - [ ]* 9.2 Write integration test: Web app API with SimpleClassifierWrapper
    - Start app with `classifier_type='simple_classifier'` configuration
    - Test `/api/model/status` endpoint returns correct classifier_type
    - Test `/api/inference` endpoint uses SimpleClassifierWrapper
    - Verify response structure matches expected format
    - _Requirements: 7.2, 7.3, 7.4, 7.5_

  - [ ]* 9.3 Write integration test: Classifier switching
    - Test system with both `simple_classifier` and `inference_engine` configurations
    - Verify both produce valid ClassificationResult objects
    - Verify orchestrator handles both classifiers identically
    - **Property 10: Error Handling Consistency Between Wrappers**
    - **Validates: Requirements 6.5, 11.2, 11.3**

- [x] 10. Final checkpoint - Ensure all tests pass
  - Run full test suite including all property tests
  - Verify no regressions in existing DLClassifierWrapper functionality
  - Test both classifier types in testing mode and production mode
  - Verify logging output is clear and actionable
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional test tasks and can be skipped for faster MVP
- Property tests validate universal correctness properties defined in the design
- Integration tests verify end-to-end workflows across components
- Configuration changes are backward compatible (default to `inference_engine`)
- SimpleClassifierWrapper enhancements maintain compatibility with existing usage

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["2.2", "2.3"] },
    { "id": 2, "tasks": ["2.4", "3.1"] },
    { "id": 3, "tasks": ["3.2", "4.1"] },
    { "id": 4, "tasks": ["3.3", "4.2"] },
    { "id": 5, "tasks": ["4.3", "6.1", "8.1"] },
    { "id": 6, "tasks": ["6.2", "7.1", "7.2", "8.2"] },
    { "id": 7, "tasks": ["9.1", "9.2", "9.3"] }
  ]
}
```
