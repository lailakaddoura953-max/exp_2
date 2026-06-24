# Deep Learning System: Cleanup & Action Plan

**Date:** June 23, 2026  
**Focus:** Simplify and continue implementing DL misalignment detection  
**Status:** Early implementation phase - foundational work done, core models needed

---

## 📊 Current Status Analysis

### ✅ What's Implemented (Tasks 1-3: ~15% Complete)

**Project Setup (Task 1):**
- ✅ Directory structure created
- ✅ Config system implemented (`src/dl_misalignment/utils/config.py`)
- ✅ Hardware detection (`src/dl_misalignment/utils/hardware.py`)
- ✅ YAML configs for both architectures
- ⚠️ Missing: Unit tests for config system (optional)

**Data Pipeline (Task 2):**
- ✅ KITTI dataset loader (`src/dl_misalignment/data/kitti_dataset.py`)
- ✅ Data augmentation engine (`src/dl_misalignment/data/augmentation.py`)
- ✅ Train/val/test splitting logic
- ⚠️ Missing: Unit tests for data pipeline (optional)

**CNN Feature Extractor (Task 3):**
- ✅ Basic implementation (`src/dl_misalignment/models/cnn_feature_extractor.py`)
- ⚠️ Missing: Unit tests (optional)

### ❌ What's Not Implemented (Tasks 5-20: ~85% Remaining)

**Critical Missing Components:**
- ❌ LiteFlowNet2 optical flow network (Task 5)
- ❌ SpyNet optical flow network (Task 6)
- ❌ Pose Estimator module (Task 7)
- ❌ Training pipeline (Task 9)
- ❌ Inference engine (Task 11)
- ❌ Hybrid mode integration (Task 12)
- ❌ Model training execution (Task 14)
- ❌ Evaluation & comparison (Task 15)

---

## 🗑️ Files to Remove (Old/Unnecessary)

### 1. **Duplicate/Legacy Rule-Based System**
```
❌ src/camera_misalignment/
   ├── alert_system.py
   ├── database_logger.py
   ├── data_models.py
   ├── frame_acquisition.py
   ├── misalignment_detector.py
   └── __init__.py
```
**Why:** This appears to be a duplicate of the modular system in `src/acquisition/`, `src/alerting/`, `src/cv/`, etc. The DL system should integrate with the modular version, not this monolithic one.

### 2. **Webapp Files (Not Related to DL)**
```
Keep but ignore for DL work:
- docs/ (GitHub Pages webapp - separate project)
- demo_videos/ (for webapp demos)
- specs/github-pages-webapp/ (webapp spec)
```
**Why:** Webapp is complete and separate from DL system. Keep it but don't focus on it.

### 3. **Old Test Files (Pre-June 23)**
Check file dates and remove tests for components that have been refactored or are no longer relevant. Keep:
- `tests/test_dl_kitti_dataset.py` (for DL data pipeline)
- `tests/test_models.py` (for DL models)
- `tests/test_augmentation.py` (for DL augmentation)

Remove tests for:
- Old rule-based system versions
- Deprecated checkpoint tests
- Redundant integration tests

### 4. **Empty/Placeholder Directories**
```
❌ video_data/ (empty)
⚠️ kitti_data/ (empty - will be populated when you download KITTI dataset)
```

### 5. **Python Bindings (Not Needed Yet)**
```
❌ python_bindings/ (C++ bindings)
   ├── bindings.cpp
   └── CMakeLists.txt
```
**Why:** The DL system is pure Python/PyTorch. C++ bindings can be added later for optimization if needed.

---

## 🎯 Immediate Action Plan (Next Steps)

### Phase 1: Clean Up (30 min)
1. **Remove duplicate camera_misalignment directory**
   ```bash
   rm -rf src/camera_misalignment/
   ```

2. **Remove Python bindings** (can restore later if needed)
   ```bash
   rm -rf python_bindings/
   ```

3. **Remove old cleanup summary** (no longer relevant)
   ```bash
   rm PROJECT_CLEANUP_SUMMARY.md
   ```

4. **Update `.gitignore`** to exclude:
   - `__pycache__/` directories
   - `.venv/` virtual environment
   - `kitti_data/` (large dataset files)
   - `*.pyc` compiled Python files
   - `runs/` (TensorBoard logs)
   - `checkpoints/` (model checkpoints)

### Phase 2: Simplify & Modernize Code (1-2 hours)

1. **Review and refactor existing code:**
   - Check `src/dl_misalignment/data/kitti_dataset.py` for modern PyTorch patterns
   - Verify `cnn_feature_extractor.py` follows current best practices
   - Update to use latest PyTorch 2.0+ features if needed

2. **Update dependencies in `requirements.txt`:**
   ```
   # Core DL
   torch>=2.2.0
   torchvision>=0.17.0
   
   # Data & Config
   pyyaml>=6.0
   numpy>=1.24.0
   opencv-python>=4.8.0
   Pillow>=10.0.0
   
   # Training
   tensorboard>=2.15.0
   tqdm>=4.66.0
   
   # Testing (optional)
   pytest>=7.4.0
   pytest-cov>=4.1.0
   ```

3. **Consolidate config files:**
   - Keep: `config/architecture_a.yaml`, `config/architecture_b.yaml`
   - Remove: Old system configs not related to DL

### Phase 3: Continue Implementation (Next 2-4 Weeks)

**Priority Order:**

#### Week 1: Core Models
- **Task 5:** Implement LiteFlowNet2 (5.1-5.4)
- **Task 6:** Implement SpyNet (6.1-6.2)
- **Task 7:** Implement Pose Estimator (7.1-7.3)
- **Checkpoint 8:** Verify all models work end-to-end

#### Week 2: Training Pipeline
- **Task 9:** Implement training pipeline (9.1-9.6)
  - Memory-efficient training config
  - Loss functions
  - Checkpoint management
  - Training loop with early stopping
  - TensorBoard logging
  - Training scripts for both architectures

#### Week 3: Inference & Integration
- **Task 11:** Implement inference engine (11.1-11.7)
- **Task 12:** Implement hybrid mode (12.1-12.4)
- **Checkpoint 13:** Verify inference and hybrid mode

#### Week 4: Training & Evaluation
- **Task 14:** Train both architectures
- **Task 15:** Evaluate and compare models
- **Task 16:** Optimize VRAM and performance
- **Checkpoint 17:** Final verification

---

## 📁 Simplified Directory Structure (After Cleanup)

```
exp_2/
├── config/                      # DL configs only
│   ├── architecture_a.yaml     # LiteFlowNet2 config
│   └── architecture_b.yaml     # SpyNet config
├── src/
│   ├── acquisition/            # Frame acquisition (rule-based system)
│   ├── alerting/               # Alert system (rule-based system)
│   ├── cv/                     # CV utilities (rule-based system)
│   ├── data/                   # Data loaders (rule-based system)
│   ├── dl_misalignment/        # 🎯 DL SYSTEM (FOCUS HERE)
│   │   ├── data/
│   │   │   ├── kitti_dataset.py      ✅ Done
│   │   │   └── augmentation.py       ✅ Done
│   │   ├── models/
│   │   │   ├── cnn_feature_extractor.py  ✅ Done
│   │   │   ├── liteflownet2.py          ❌ TODO (Task 5)
│   │   │   ├── spynet.py                ❌ TODO (Task 6)
│   │   │   └── pose_estimator.py        ❌ TODO (Task 7)
│   │   ├── training/
│   │   │   ├── trainer.py               ❌ TODO (Task 9)
│   │   │   ├── loss_functions.py        ❌ TODO (Task 9)
│   │   │   └── checkpoint.py            ❌ TODO (Task 9)
│   │   ├── inference/
│   │   │   └── inference_engine.py      ❌ TODO (Task 11)
│   │   └── utils/
│   │       ├── config.py         ✅ Done
│   │       ├── hardware.py       ✅ Done
│   │       ├── metrics.py        ✅ Done
│   │       └── visualization.py  ✅ Done
│   └── pipeline/               # Integration pipeline
├── tests/                      # Tests for DL system
│   ├── test_dl_kitti_dataset.py
│   ├── test_models.py
│   └── test_augmentation.py
├── scripts/                    # Training/eval scripts
│   ├── train_architecture_a.py  ❌ TODO (Task 9)
│   └── train_architecture_b.py  ❌ TODO (Task 9)
├── specs/
│   └── deep-learning-misalignment-detection/  # DL spec
│       ├── requirements.md (28 requirements)
│       ├── design.md
│       └── tasks.md (20 tasks, 3 done)
├── kitti_data/                 # KITTI dataset (download needed)
├── checkpoints/                # Model checkpoints (generated)
├── runs/                       # TensorBoard logs (generated)
├── requirements.txt            # Python dependencies
└── .gitignore                  # Git ignore patterns
```

---

## 🔧 Modernization Opportunities

### 1. **Use Modern PyTorch Features**
- Use `torch.compile()` for faster inference (PyTorch 2.0+)
- Use native AMP (Automatic Mixed Precision) instead of manual FP16/FP32
- Use `torch.utils.checkpoint` for gradient checkpointing

### 2. **Simplify Model Architecture**
- Consider using pre-trained backbones (ResNet, EfficientNet) instead of custom CNN
- Use modern optical flow models (RAFT, GMA) instead of LiteFlowNet2/SpyNet
- Explore transformer-based architectures for better accuracy

### 3. **Improve Data Pipeline**
- Use `webdataset` for efficient large-scale dataset loading
- Implement on-the-fly augmentation with `albumentations`
- Add data caching for faster training

### 4. **Better Training Infrastructure**
- Use Weights & Biases (wandb) or MLflow instead of TensorBoard
- Add distributed training support for multi-GPU
- Implement learning rate finder (fastai style)
- Add gradient accumulation for larger effective batch sizes

### 5. **Code Quality**
- Add type hints throughout
- Use `dataclasses` for configuration
- Add docstrings with examples
- Set up pre-commit hooks (black, flake8, mypy)

---

## ✅ Requirements Checklist (28 Total)

### Completed (3/28):
- ✅ Requirement 1: CNN Feature Extractor (partial)
- ✅ Requirement 5: KITTI Dataset Integration (partial)
- ✅ Requirement 6: Data Augmentation (partial)

### In Progress (0/28):
- (None currently)

### Not Started (25/28):
- ❌ Requirements 2-4: LiteFlowNet2, SpyNet, Architecture Comparison
- ❌ Requirements 7-9: Training Configuration, Convergence, Inference
- ❌ Requirements 10-13: Outputs (Probability, Severity, Pose, Uncertainty)
- ❌ Requirements 14-16: Backward Compatibility, Hybrid Mode, Config System
- ❌ Requirements 17-20: Accuracy Targets, Hardware Constraints, Checkpoints
- ❌ Requirements 21-28: Advanced features (Augmentation Diversity, Batch Processing, Loss Design, Pyramid, Comparison, Fallback, TensorBoard, Output Structures)

---

## 🚀 Quick Start Guide (After Cleanup)

### 1. Set Up Environment
```bash
cd c:\Users\Miles\Desktop\exp_2

# Create/activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Verify CUDA
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### 2. Download KITTI Dataset
```bash
# Download from: http://www.cvlibs.net/datasets/kitti/
# Extract to: kitti_data/
```

### 3. Test Current Implementation
```bash
# Test data loading
python -m pytest tests/test_dl_kitti_dataset.py

# Test CNN Feature Extractor
python -m pytest tests/test_models.py

# Test augmentation
python -m pytest tests/test_augmentation.py
```

### 4. Continue Implementation
Follow the task order in `deep-learning-misalignment-detection/tasks.md`:
- Start with Task 5 (LiteFlowNet2)
- Then Task 6 (SpyNet)
- Then Task 7 (Pose Estimator)
- Verify with Checkpoint 8

---

## 📝 Notes

### Keep for Reference:
- `DATABASE_INTEGRATION_PLAN.md` - Future database work (not DL-related)
- `docs/` - Completed webapp (separate project)
- Rule-based CV system (`src/acquisition/`, `src/cv/`, etc.) - Needed for hybrid mode

### Can Remove:
- `src/camera_misalignment/` - Duplicate monolithic implementation
- `python_bindings/` - Not needed for pure PyTorch implementation
- `PROJECT_CLEANUP_SUMMARY.md` - Outdated after restore

### Will Be Generated:
- `checkpoints/` - Model checkpoints from training
- `runs/` - TensorBoard logs
- `kitti_data/` - Downloaded KITTI dataset

---

## 🎯 Success Criteria

**Short Term (2 weeks):**
- ✅ Cleanup complete
- ✅ LiteFlowNet2 and SpyNet implemented and tested
- ✅ Pose Estimator implemented and tested
- ✅ End-to-end forward pass working

**Medium Term (4 weeks):**
- ✅ Training pipeline complete and tested
- ✅ Both architectures trained on KITTI
- ✅ Inference engine working with <100ms latency
- ✅ Hybrid mode integrated with rule-based system

**Long Term (6 weeks):**
- ✅ All 28 requirements met
- ✅ Evaluation complete with comparison report
- ✅ Documentation complete
- ✅ System deployed and tested

---

**Ready to start? First, let's clean up the duplicate files, then move on to implementing Task 5 (LiteFlowNet2)!**
