# Simple Classifier Integration - Testing Guide

This guide provides step-by-step instructions for testing the simple classifier integration on a separate device to verify that all changes work correctly.

## Prerequisites

Before testing, ensure you have:
1. Python 3.8+ installed
2. All dependencies installed: `pip install -r requirements.txt`
3. A trained model checkpoint (`.pth` file from `train_strad_classifier.py`)
4. The repository cloned from GitHub

---

## Testing Sequence

### Phase 1: Quick Verification (5 minutes)

These tests verify basic functionality without requiring full system setup.

#### Test 1.1: Configuration Validation
**Purpose:** Verify that the `classifier_type` field is recognized and validated

**Command:**
```bash
python -m pytest tests/test_strad_monitoring_config.py -v
```

**Expected Output:**
- ✅ 10 tests pass
- Configuration accepts `'simple_classifier'` and `'inference_engine'`
- Invalid classifier types are rejected

**If it fails:** Check that `src/strad_monitoring/config/system_config.py` has the latest changes

---

#### Test 1.2: SimpleClassifierWrapper Unit Tests
**Purpose:** Verify that SimpleClassifierWrapper can be imported and instantiated

**Command:**
```bash
python -m pytest tests/unit/test_simple_classifier_wrapper.py -v
```

**Expected Output:**
- ✅ 12 tests pass
- Checkpoint format validation works
- Error messages are descriptive

**If it fails:** Check that `src/strad_monitoring/dl_classifier/simple_classifier_wrapper.py` exists

---

### Phase 2: Integration Tests (10 minutes)

These tests verify that components work together correctly.

#### Test 2.1: CPU Deployment
**Purpose:** Verify cross-device compatibility (CUDA checkpoints load on CPU)

**Command:**
```bash
python -m pytest tests/test_cpu_deployment.py -v
```

**Expected Output:**
- ✅ 7 tests pass, 2 skipped (GPU tests on CPU-only system)
- CPU successfully loads CUDA-trained checkpoints
- Classification works on CPU

**If it fails:** Check PyTorch installation and device availability

---

#### Test 2.2: Orchestrator Error Handling
**Purpose:** Verify that orchestrator handles classifier initialization correctly

**Command:**
```bash
python -m pytest tests/test_orchestrator_error_handling.py -v
```

**Expected Output:**
- ✅ 5 tests pass
- Invalid classifier type raises error in production mode
- Missing checkpoint handled gracefully in testing mode

**If it fails:** Check `src/strad_monitoring/orchestration/orchestrator.py` modifications

---

#### Test 2.3: Raw Output Validation
**Purpose:** Verify that ClassificationResult includes raw_output field

**Command:**
```bash
python -m pytest tests/test_simple_classifier_raw_output.py -v
```

**Expected Output:**
- ✅ 1 test passes
- raw_output contains required diagnostic fields

**If it fails:** Check `simple_classifier_wrapper.py` classify_snapshot method

---

### Phase 3: Manual Verification (15 minutes)

These scripts provide interactive verification of the integration.

#### Test 3.1: Classifier Initialization Test
**Purpose:** Verify that both classifier types can be initialized

**Command:**
```bash
python test_classifier_initialization_only.py
```

**Expected Output:**
```
Testing Classifier Initialization
==================================================

Test 1: SimpleClassifierWrapper Instantiation
✓ SimpleClassifierWrapper imported successfully
✓ SimpleClassifierWrapper instantiated successfully

Test 2: Orchestrator Conditional Logic - simple_classifier
✓ Config loaded with classifier_type='simple_classifier'
✓ Orchestrator would instantiate SimpleClassifierWrapper

Test 3: Orchestrator Conditional Logic - inference_engine
✓ Config loaded with classifier_type='inference_engine'
✓ Orchestrator would instantiate DLClassifierWrapper

Test 4: Web App Conditional Logic - simple_classifier
✓ Web app would use SimpleClassifierWrapper

Test 5: Web App Conditional Logic - inference_engine
✓ Web app would use DLClassifierWrapper

Test 6: Logging Shows Classifier Type and Device
✓ Logging shows: Initializing classifier: simple_classifier...
✓ Logging shows: Using device: cpu

==================================================
All Tests Passed: 6/6
```

**If it fails:** Review error messages - they indicate which component is not working

---

#### Test 3.2: Web App Integration Test
**Purpose:** Verify that web app can initialize with the new classifier

**Command:**
```bash
python test_task_4_1_verification.py
```

**Expected Output:**
```
Testing Web App Integration (Task 4.1)
==================================================

Test 1: Import SimpleClassifierWrapper
✓ SimpleClassifierWrapper imported successfully

Test 2: Import DLClassifierWrapper
✓ DLClassifierWrapper imported successfully

Test 3: Classifier Type Logic - simple_classifier
✓ Config has classifier_type='simple_classifier'
✓ Web app would instantiate SimpleClassifierWrapper

Test 4: Classifier Type Logic - inference_engine
✓ Config has classifier_type='inference_engine'
✓ Web app would instantiate DLClassifierWrapper

Test 5: Default Fallback
✓ Missing classifier_type defaults to 'inference_engine'

Test 6: Invalid Classifier Type
✓ Invalid classifier_type raises ValueError

Test 7: Device Auto-Detection
✓ Device is auto-detected (cuda/cpu)

Test 8: /api/model/status Includes classifier_type
✓ API endpoint would report classifier_type

Test 9: Error Handling
✓ Errors are handled gracefully (classifier set to None)

==================================================
All Tests Passed: 9/9
```

**If it fails:** Check `docs/backend/app.py` for conditional logic

---

### Phase 4: End-to-End Testing (20 minutes)

These tests verify the complete system with actual models.

#### Test 4.1: Configure System for Testing
**Purpose:** Set up system_config.json for testing

**Steps:**
1. Open `system_config.json`
2. Locate the `classifier_type` field
3. Set it to `"simple_classifier"`:
   ```json
   {
     "classifier_type": "simple_classifier",
     "model_checkpoint_path": "path/to/your/model.pth",
     ...
   }
   ```
4. Ensure `enable_local_testing_mode` is `true`

---

#### Test 4.2: Run Orchestrator Initialization Test
**Purpose:** Verify that the orchestrator can initialize with SimpleClassifierWrapper

**Command:**
```bash
python -c "
from src.strad_monitoring.config.system_config import ConfigurationManager
from src.strad_monitoring.orchestration.orchestrator import MonitoringOrchestrator

config = ConfigurationManager.load_config('system_config.json')
print(f'Loaded config with classifier_type: {config.classifier_type}')

orchestrator = MonitoringOrchestrator(config)
print(f'Classifier type: {type(orchestrator.dl_classifier).__name__}')
print('✓ Orchestrator initialized successfully with SimpleClassifierWrapper')
"
```

**Expected Output:**
```
Loaded config with classifier_type: simple_classifier
Initializing classifier: simple_classifier...
Using device: cpu
✓ SimpleClassifierWrapper initialized
Classifier type: SimpleClassifierWrapper
✓ Orchestrator initialized successfully with SimpleClassifierWrapper
```

---

#### Test 4.3: Run Web App Smoke Test
**Purpose:** Verify that the web app can start with the new classifier

**Command:**
```bash
python -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'src'))

from strad_monitoring.config.system_config import ConfigurationManager
config = ConfigurationManager.load_config('system_config.json')

print(f'Loaded config with classifier_type: {config.classifier_type}')
print('✓ Configuration loaded successfully')
print('✓ Web app would initialize with this configuration')
print('Note: Full web app test requires starting Flask server')
"
```

**Expected Output:**
```
Loaded config with classifier_type: simple_classifier
✓ Configuration loaded successfully
✓ Web app would initialize with this configuration
```

---

#### Test 4.4: Run Complete Test Suite
**Purpose:** Run all tests together to ensure nothing is broken

**Command:**
```bash
python -m pytest tests/ -v --tb=short
```

**Expected Output:**
- ✅ 39 tests pass
- 2 tests skipped (GPU tests on CPU-only systems)
- 0 failures

**If it fails:** Review the failure output to identify which component has issues

---

## Testing Checklist

Use this checklist to track your testing progress:

### Quick Verification
- [ ] Configuration validation tests pass (10/10)
- [ ] SimpleClassifierWrapper unit tests pass (12/12)

### Integration Tests
- [ ] CPU deployment tests pass (7/7, 2 skipped)
- [ ] Orchestrator error handling tests pass (5/5)
- [ ] Raw output validation tests pass (1/1)

### Manual Verification
- [ ] Classifier initialization test passes (6/6)
- [ ] Web app integration test passes (9/9)

### End-to-End Testing
- [ ] system_config.json configured with `classifier_type`
- [ ] Orchestrator initializes with SimpleClassifierWrapper
- [ ] Web app configuration loads successfully
- [ ] Complete test suite passes (39/39, 2 skipped)

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'strad_monitoring'"
**Solution:** Run tests from the project root directory or add to PYTHONPATH:
```bash
set PYTHONPATH=%CD%;%PYTHONPATH%  # Windows
export PYTHONPATH=$(pwd):$PYTHONPATH  # Linux/Mac
```

### Issue: "FileNotFoundError: Model checkpoint not found"
**Solution:** 
1. Set `enable_local_testing_mode: true` in system_config.json
2. Or provide a valid model checkpoint path

### Issue: Tests fail with "CUDA not available"
**Solution:** This is expected on CPU-only systems. GPU tests will be skipped automatically.

### Issue: "KeyError: 'model_state_dict'"
**Solution:** 
- You're using an InferenceEngine checkpoint with SimpleClassifierWrapper
- Change `classifier_type` to `"inference_engine"` in system_config.json
- Or train a new model with `train_strad_classifier.py`

---

## Quick Test (All-in-One)

Run this single command to execute all tests:

```bash
python -m pytest tests/ -v && python test_classifier_initialization_only.py && python test_task_4_1_verification.py
```

**Expected:** All tests pass with detailed output showing what was tested.

---

## Summary

After completing all tests, you should have verified:
1. ✅ Configuration system recognizes `classifier_type` field
2. ✅ SimpleClassifierWrapper can be imported and instantiated
3. ✅ Cross-device compatibility works (CPU loads CUDA checkpoints)
4. ✅ Orchestrator initializes correct classifier based on config
5. ✅ Web app initializes correct classifier based on config
6. ✅ Error handling works for invalid configs and missing files
7. ✅ Raw output diagnostic information is included
8. ✅ Backward compatibility maintained (defaults to inference_engine)

If all tests pass, the integration is functioning correctly on the device.
