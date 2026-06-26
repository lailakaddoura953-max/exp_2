# Strad Classifier Training Guide

## Overview

This guide explains how to train a deep learning model for strad misalignment classification using your labeled footage.

## Prerequisites

- Labeled training data in `SCFootage/` folder
- Python environment with PyTorch installed
- GPU recommended (but CPU works too)

## Training Data Structure

Your data should be organized as:
```
SCFootage/
    misaligned - critical/
        STRAD_001/
            image1.png
            video1.mp4
        STRAD_002/
            ...
    misaligned - moderate/
        STRAD_003/
            ...
    misaligned - none/
        STRAD_004/
            ...
```

The training script automatically:
- Maps folder names to class labels (critical=2, moderate=1, none=0)
- Loads PNG/JPG images directly
- Extracts frames from MP4 videos
- Handles class imbalance with weights

## Quick Start

### 1. Prepare Data
Ensure your `SCFootage` folder is in the project root with labeled data.

### 2. Start Training

**Basic training (50 epochs):**
```bash
python train_strad_classifier.py --data_dir SCFootage --epochs 50
```

**With custom settings:**
```bash
python train_strad_classifier.py \
    --data_dir SCFootage \
    --epochs 100 \
    --batch_size 16 \
    --lr 0.001 \
    --image_size 640
```

### 3. Monitor Training

The script will display:
- Dataset statistics (class distribution)
- Training progress per epoch
- Validation accuracy per class
- Best model checkpoint saved

Example output:
```
Epoch [1/50]
  Batch [10/45] Loss: 1.0234 Acc: 45.67%
  
  Training:   Loss: 1.0123  Acc: 48.50%
  
  Validation Results:
    Overall Accuracy: 52.30%
    Per-class Accuracy:
      none: 65.20% (32/49)
      moderate: 48.10% (25/52)
      critical: 43.50% (20/46)
```

### 4. Use Trained Model

After training completes, update `system_config.json`:

```json
{
  "model_checkpoint_path": "trained_models/strad_classifier_acc85.3_20260626_120000.pth"
}
```

Then restart:
- Monitoring system: `python -m src.strad_monitoring.main`
- Web app: `start_web_app.bat`

The system will now use your trained model for real inference!

## Training Options

| Option | Default | Description |
|--------|---------|-------------|
| `--data_dir` | `SCFootage` | Path to training data folder |
| `--epochs` | `50` | Number of training epochs |
| `--batch_size` | `16` | Batch size (reduce if GPU OOM) |
| `--lr` | `0.001` | Learning rate |
| `--image_size` | `640` | Image size for training |
| `--output_dir` | `trained_models` | Where to save models |
| `--device` | `auto` | Use `cuda`, `cpu`, or `auto` |

## Model Architecture

The script uses a lightweight CNN:
- 4 convolutional blocks with batch normalization
- Global average pooling
- 2 fully connected layers
- ~3M parameters

This is a simple baseline. For better accuracy, you can:
- Use pre-trained ResNet/EfficientNet backbones
- Add attention mechanisms
- Increase training data
- Tune hyperparameters

## Training Tips

### If GPU runs out of memory:
```bash
python train_strad_classifier.py --batch_size 8 --image_size 512
```

### For quick testing:
```bash
python train_strad_classifier.py --epochs 10 --batch_size 8
```

### For best accuracy:
```bash
python train_strad_classifier.py --epochs 200 --batch_size 32 --lr 0.0001
```

## Troubleshooting

### Error: "No valid samples found"
- Check that `SCFootage/` folder exists
- Verify class folders match expected names:
  - "misaligned - critical"
  - "misaligned - moderate"
  - "misaligned - none"

### Error: CUDA out of memory
- Reduce batch size: `--batch_size 8` or `--batch_size 4`
- Reduce image size: `--image_size 512` or `--image_size 384`

### Low accuracy
- Collect more training data
- Train for more epochs: `--epochs 100`
- Balance class distribution
- Try different learning rates

### Training is slow
- Use GPU if available
- Increase batch size: `--batch_size 32`
- Reduce image size: `--image_size 512`

## Next Steps

1. **Collect more data**: More labeled examples = better accuracy
2. **Evaluate on test set**: Hold out some data for final evaluation
3. **Tune hyperparameters**: Try different learning rates, batch sizes
4. **Advanced models**: Experiment with ResNet, EfficientNet backbones
5. **Data augmentation**: Add more augmentations for robustness

## Files Created

- `train_strad_classifier.py` - Main training script
- `src/dl_misalignment/data/strad_footage_dataset.py` - Dataset loader
- `trained_models/` - Saved model checkpoints (created during training)

## Questions?

Check the code comments in:
- `train_strad_classifier.py` - Training loop and model definition
- `strad_footage_dataset.py` - Data loading logic
