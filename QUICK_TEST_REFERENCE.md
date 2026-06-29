# Quick Test Reference - Simple Classifier Integration

## Fast Testing Sequence (Recommended Order)

Copy and paste these commands in order to test the integration:

---

## 1. Run All Unit Tests (2 minutes)
```bash
python -m pytest tests/test_strad_monitoring_config.py tests/unit/test_simple_classifier_wrapper.py -v
```
**Expected:** 22 tests pass (10 config + 12 wrapper)

---

## 2. Run All Integration Tests (3 minutes)
```bash
python -m pytest tests/test_cpu_deployment.py tests/test_orchestrator_error_handling.py tests/test_simple_classifier_raw_output.py -v
```
**Expected:** 13 tests pass, 2 skipped

---

## 3. Run Manual Verification Scripts (2 minutes)
```bash
python test_classifier_initialization_only.py
```
**Expected:** "All Tests Passed: 6/6"

```bash
python test_task_4_1_verification.py
```
**Expected:** "All Tests Passed: 9/9"

---

## 4. Run Complete Test Suite (5 minutes)
```bash
python -m pytest tests/ -v
```
**Expected:** 39 tests pass, 2 skipped, 0 failures

---

## One-Line Test (All Tests)
```bash
python -m pytest tests/ -v && python test_classifier_initialization_only.py && python test_task_4_1_verification.py
```

---

## Test What Changed

### Test Configuration Changes
```bash
python -m pytest tests/test_strad_monitoring_config.py::test_classifier_type_field_exists -v
python -m pytest tests/test_strad_monitoring_config.py::test_valid_classifier_types -v
```

### Test SimpleClassifierWrapper
```bash
python -m pytest tests/unit/test_simple_classifier_wrapper.py::test_valid_checkpoint_loads -v
python -m pytest tests/unit/test_simple_classifier_wrapper.py::test_checkpoint_format_validation -v
```

### Test Orchestrator Integration
```bash
python -m pytest tests/test_orchestrator_error_handling.py::test_invalid_classifier_type_production -v
python -m pytest tests/test_orchestrator_error_handling.py::test_valid_classifier_type_with_checkpoint -v
```

### Test Web App Integration
```bash
python test_task_4_1_verification.py
```

### Test CPU Deployment
```bash
python -m pytest tests/test_cpu_deployment.py::test_cpu_loads_cuda_checkpoint -v
python -m pytest tests/test_cpu_deployment.py::test_cpu_classification_succeeds -v
```

---

## Quick Smoke Test (30 seconds)

Test if the integration is working without running full suite:

```bash
python -c "from src.strad_monitoring.dl_classifier.simple_classifier_wrapper import SimpleClassifierWrapper; print('✓ SimpleClassifierWrapper imported')"
```

```bash
python -c "from src.strad_monitoring.config.system_config import ConfigurationManager, SystemConfig; c = SystemConfig(database_connection_string='test', excel_file_path='test', model_checkpoint_path='test', temp_snapshot_path='test', permanent_snapshot_path='test', log_file_path='test', cycle_schedule_cron='0 * * * *', strad_selection_count=10, cooldown_hours=1, classification_timeout_seconds=60, snapshot_min_width=640, snapshot_min_height=480, snapshot_retention_days=30, log_retention_days=7, classifier_type='simple_classifier'); print(f'✓ Config accepts classifier_type: {c.classifier_type}')"
```

---

## Check What's Installed

```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA Available: {torch.cuda.is_available()}')"
```

```bash
python -c "import sys; from pathlib import Path; sys.path.insert(0, 'src'); from strad_monitoring.dl_classifier import simple_classifier_wrapper; print('✓ All imports work')"
```

---

## Test Specific Features

### Feature: Classifier Type Selection
```bash
python -m pytest tests/test_strad_monitoring_config.py::test_valid_simple_classifier_type -v
python -m pytest tests/test_strad_monitoring_config.py::test_valid_inference_engine_type -v
python -m pytest tests/test_strad_monitoring_config.py::test_invalid_classifier_type_rejected -v
```

### Feature: Cross-Device Compatibility
```bash
python -m pytest tests/test_cpu_deployment.py::test_cpu_loads_cuda_checkpoint -v
python -m pytest tests/test_cpu_deployment.py::test_cpu_classification_succeeds -v
```

### Feature: Error Handling
```bash
python -m pytest tests/test_orchestrator_error_handling.py -v
```

### Feature: Raw Output
```bash
python -m pytest tests/test_simple_classifier_raw_output.py -v
```

---

## Verify Files Exist

```bash
python -c "from pathlib import Path; files = ['src/strad_monitoring/dl_classifier/simple_classifier_wrapper.py', 'tests/test_cpu_deployment.py', 'tests/test_orchestrator_error_handling.py', 'tests/test_strad_monitoring_config.py', 'tests/unit/test_simple_classifier_wrapper.py']; missing = [f for f in files if not Path(f).exists()]; print('✓ All files exist' if not missing else f'✗ Missing: {missing}')"
```

---

## Troubleshooting Quick Checks

### If tests fail to find modules:
```bash
set PYTHONPATH=%CD%;%PYTHONPATH%
python -m pytest tests/ -v
```

### If checkpoint errors occur:
Check your system_config.json:
```bash
python -c "import json; config = json.load(open('system_config.json')); print(f\"classifier_type: {config.get('classifier_type', 'NOT SET')}\"); print(f\"testing_mode: {config.get('enable_local_testing_mode', 'NOT SET')}\")"
```

### If import errors occur:
```bash
python -c "import sys; print('Python paths:'); [print(p) for p in sys.path]"
```

---

## Expected Test Counts

| Test File | Expected Pass | Expected Skip | Expected Fail |
|-----------|---------------|---------------|---------------|
| test_strad_monitoring_config.py | 10 | 0 | 0 |
| test_simple_classifier_wrapper.py | 12 | 0 | 0 |
| test_cpu_deployment.py | 7 | 2 | 0 |
| test_orchestrator_error_handling.py | 5 | 0 | 0 |
| test_simple_classifier_raw_output.py | 1 | 0 | 0 |
| test_classifier_initialization_only.py | 6 | 0 | 0 |
| test_task_4_1_verification.py | 9 | 0 | 0 |
| **TOTAL** | **50** | **2** | **0** |

---

## Success Criteria

✅ All 5 pytest test files pass  
✅ Both manual verification scripts pass  
✅ No unexpected failures or errors  
✅ Skipped tests are GPU-related only (on CPU systems)  
✅ All imports work without errors  

If all criteria are met, the integration is working correctly on the device.
