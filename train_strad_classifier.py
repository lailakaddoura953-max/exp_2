"""
Simple Training Script for Strad Misalignment Classifier

This script trains a lightweight CNN classifier for strad misalignment detection
using your labeled SCFootage dataset.

Usage:
    python train_strad_classifier.py --data_dir SCFootage --epochs 50

Requirements:
    - PyTorch, torchvision installed
    - Labeled data in SCFootage folder
    - CUDA-capable GPU (recommended) or CPU
"""

import argparse
import sys
from pathlib import Path
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import transforms
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dl_misalignment.data.strad_footage_dataset import create_strad_dataloaders


class SimpleStradClassifier(nn.Module):
    """
    Lightweight CNN for strad misalignment classification.
    
    Architecture:
    - 4 convolutional blocks with batch norm and max pooling
    - 2 fully connected layers
    - 3-class output (none, moderate, critical)
    
    This is a simple baseline model. For better performance, you can:
    - Use a pre-trained ResNet/EfficientNet backbone
    - Add attention mechanisms
    - Increase model capacity
    """
    
    def __init__(self, num_classes=3):
        super(SimpleStradClassifier, self).__init__()
        
        # Convolutional feature extractor
        self.features = nn.Sequential(
            # Block 1: 3 -> 32
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),  # 640x640 -> 320x320
            
            # Block 2: 32 -> 64
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),  # 320x320 -> 160x160
            
            # Block 3: 64 -> 128
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),  # 160x160 -> 80x80
            
            # Block 4: 128 -> 256
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),  # 80x80 -> 40x40
            
            # Global average pooling
            nn.AdaptiveAvgPool2d((4, 4))  # 40x40 -> 4x4
        )
        
        # Classifier head
        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(256 * 4 * 4, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes)
        )
    
    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return x


def train_one_epoch(model, train_loader, criterion, optimizer, device, epoch):
    """Train for one epoch."""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    
    for batch_idx, (inputs, labels) in enumerate(train_loader):
        inputs, labels = inputs.to(device), labels.to(device)
        
        # Zero gradients
        optimizer.zero_grad()
        
        # Forward pass
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        
        # Backward pass
        loss.backward()
        optimizer.step()
        
        # Statistics
        running_loss += loss.item()
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += predicted.eq(labels).sum().item()
        
        if (batch_idx + 1) % 10 == 0:
            print(f'  Batch [{batch_idx + 1}/{len(train_loader)}] '
                  f'Loss: {running_loss / (batch_idx + 1):.4f} '
                  f'Acc: {100. * correct / total:.2f}%')
    
    epoch_loss = running_loss / len(train_loader)
    epoch_acc = 100. * correct / total
    
    return epoch_loss, epoch_acc


def validate(model, val_loader, criterion, device):
    """Validate the model."""
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    
    # Per-class accuracy
    class_correct = [0, 0, 0]
    class_total = [0, 0, 0]
    
    with torch.no_grad():
        for inputs, labels in val_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            
            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()
            
            # Per-class stats
            for i in range(len(labels)):
                label = labels[i].item()
                class_total[label] += 1
                if predicted[i] == label:
                    class_correct[label] += 1
    
    val_loss = running_loss / len(val_loader)
    val_acc = 100. * correct / total
    
    print(f'\n  Validation Results:')
    print(f'    Overall Accuracy: {val_acc:.2f}%')
    print(f'    Per-class Accuracy:')
    class_names = ['none', 'moderate', 'critical']
    for i in range(3):
        if class_total[i] > 0:
            acc = 100. * class_correct[i] / class_total[i]
            print(f'      {class_names[i]}: {acc:.2f}% ({class_correct[i]}/{class_total[i]})')
    
    return val_loss, val_acc


def main():
    parser = argparse.ArgumentParser(description='Train Strad Misalignment Classifier')
    parser.add_argument('--data_dir', type=str, default='SCFootage',
                        help='Path to training data folder')
    parser.add_argument('--epochs', type=int, default=50,
                        help='Number of training epochs')
    parser.add_argument('--batch_size', type=int, default=16,
                        help='Batch size for training')
    parser.add_argument('--lr', type=float, default=0.001,
                        help='Learning rate')
    parser.add_argument('--image_size', type=int, default=640,
                        help='Image size (will be resized to size x size)')
    parser.add_argument('--output_dir', type=str, default='trained_models',
                        help='Directory to save trained models')
    parser.add_argument('--device', type=str, default='auto',
                        help='Device to use (cuda/cpu/auto)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("STRAD MISALIGNMENT CLASSIFIER - TRAINING")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Data directory: {args.data_dir}")
    print(f"  Epochs: {args.epochs}")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Learning rate: {args.lr}")
    print(f"  Image size: {args.image_size}x{args.image_size}")
    
    # Setup device
    if args.device == 'auto':
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    else:
        device = torch.device(args.device)
    
    print(f"  Device: {device}")
    
    # Check if data directory exists
    data_path = Path(args.data_dir)
    if not data_path.exists():
        print(f"\n✗ ERROR: Data directory not found: {args.data_dir}")
        print(f"  Please ensure the SCFootage folder exists in the project root")
        return 1
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    print(f"\n{'=' * 80}")
    print("LOADING DATASET")
    print("=" * 80)
    
    # Data transforms
    transform_train = transforms.Compose([
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(10),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    transform_val = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    # Create dataloaders
    try:
        train_loader, val_loader, dataset_info = create_strad_dataloaders(
            root_dir=str(data_path),
            batch_size=args.batch_size,
            train_split=0.8,
            num_workers=4,
            transform_train=transform_train,
            transform_val=transform_val,
            image_size=(args.image_size, args.image_size)
        )
        
        print(f"\n✓ Dataset loaded successfully:")
        print(f"  Total samples: {dataset_info['total_samples']}")
        print(f"  Training samples: {dataset_info['train_samples']}")
        print(f"  Validation samples: {dataset_info['val_samples']}")
        print(f"  Class distribution:")
        for class_idx, count in dataset_info['class_counts'].items():
            class_names = {0: 'none', 1: 'moderate', 2: 'critical'}
            print(f"    {class_names[class_idx]}: {count} samples")
        
    except Exception as e:
        print(f"\n✗ ERROR loading dataset: {e}")
        return 1
    
    print(f"\n{'=' * 80}")
    print("INITIALIZING MODEL")
    print("=" * 80)
    
    # Create model
    model = SimpleStradClassifier(num_classes=3).to(device)
    
    # Loss function with class weights (for imbalanced dataset)
    class_weights = dataset_info['class_weights'].to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    
    # Optimizer
    optimizer = optim.Adam(model.parameters(), lr=args.lr)
    
    # Learning rate scheduler
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=5, verbose=True
    )
    
    print(f"✓ Model initialized")
    print(f"  Parameters: {sum(p.numel() for p in model.parameters()):,}")
    print(f"  Optimizer: Adam (lr={args.lr})")
    print(f"  Loss: CrossEntropyLoss with class weights")
    
    print(f"\n{'=' * 80}")
    print("TRAINING")
    print("=" * 80)
    
    best_val_acc = 0.0
    best_model_path = None
    
    for epoch in range(args.epochs):
        print(f"\nEpoch [{epoch + 1}/{args.epochs}]")
        
        # Train
        train_loss, train_acc = train_one_epoch(
            model, train_loader, criterion, optimizer, device, epoch
        )
        
        print(f'\n  Training:   Loss: {train_loss:.4f}  Acc: {train_acc:.2f}%')
        
        # Validate
        val_loss, val_acc = validate(model, val_loader, criterion, device)
        print(f'  Validation: Loss: {val_loss:.4f}  Acc: {val_acc:.2f}%')
        
        # Learning rate scheduler step
        scheduler.step(val_loss)
        
        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            best_model_path = output_dir / f'strad_classifier_acc{val_acc:.1f}_{timestamp}.pth'
            
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_acc': val_acc,
                'val_loss': val_loss,
                'dataset_info': dataset_info
            }, best_model_path)
            
            print(f'  ✓ New best model saved: {best_model_path.name}')
    
    print(f"\n{'=' * 80}")
    print("TRAINING COMPLETE")
    print("=" * 80)
    print(f"\nBest Validation Accuracy: {best_val_acc:.2f}%")
    print(f"Best Model Saved: {best_model_path}")
    print(f"\nTo use this model:")
    print(f"  1. Copy model path: {best_model_path}")
    print(f"  2. Update system_config.json:")
    print(f'     "model_checkpoint_path": "{best_model_path}"')
    print(f"  3. Restart the monitoring system and web app")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
