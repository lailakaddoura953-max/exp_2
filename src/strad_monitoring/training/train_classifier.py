"""
Lightweight Training Script for Strad Misalignment Classification

This script trains a simple CNN classifier on strad footage data.
Uses transfer learning with a pre-trained ResNet18 for fast training.
"""

import argparse
import os
from pathlib import Path
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models
from tqdm import tqdm
import json
from datetime import datetime

from .strad_dataset import create_strad_dataloaders


class StradClassifier(nn.Module):
    """
    Simple CNN classifier using transfer learning.
    Based on ResNet18 pre-trained on ImageNet.
    """
    
    def __init__(self, num_classes=3, pretrained=True):
        super().__init__()
        
        # Load pre-trained ResNet18
        self.backbone = models.resnet18(pretrained=pretrained)
        
        # Replace final layer for 3-class classification
        num_features = self.backbone.fc.in_features
        self.backbone.fc = nn.Linear(num_features, num_classes)
    
    def forward(self, x):
        return self.backbone(x)


def train_epoch(model, train_loader, criterion, optimizer, device):
    """Train for one epoch."""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    
    pbar = tqdm(train_loader, desc="Training")
    for images, labels, _ in pbar:
        images = images.to(device)
        labels = labels.to(device)
        
        # Forward pass
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        
        # Backward pass
        loss.backward()
        optimizer.step()
        
        # Statistics
        running_loss += loss.item()
        _, predicted = torch.max(outputs, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()
        
        # Update progress bar
        pbar.set_postfix({
            'loss': f'{running_loss/len(pbar):.4f}',
            'acc': f'{100*correct/total:.2f}%'
        })
    
    epoch_loss = running_loss / len(train_loader)
    epoch_acc = 100 * correct / total
    
    return epoch_loss, epoch_acc


def validate(model, val_loader, criterion, device):
    """Validate the model."""
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    
    with torch.no_grad():
        pbar = tqdm(val_loader, desc="Validation")
        for images, labels, _ in pbar:
            images = images.to(device)
            labels = labels.to(device)
            
            outputs = model(images)
            loss = criterion(outputs, labels)
            
            running_loss += loss.item()
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
            pbar.set_postfix({
                'loss': f'{running_loss/len(pbar):.4f}',
                'acc': f'{100*correct/total:.2f}%'
            })
    
    val_loss = running_loss / len(val_loader)
    val_acc = 100 * correct / total
    
    return val_loss, val_acc


def save_checkpoint(model, optimizer, epoch, train_loss, val_loss, val_acc, save_path):
    """Save model checkpoint."""
    checkpoint = {
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'train_loss': train_loss,
        'val_loss': val_loss,
        'val_acc': val_acc,
        'timestamp': datetime.now().isoformat()
    }
    
    torch.save(checkpoint, save_path)
    print(f"Checkpoint saved to {save_path}")


def main():
    parser = argparse.ArgumentParser(description='Train Strad Misalignment Classifier')
    parser.add_argument('--data_dir', type=str, required=True,
                        help='Path to SCFootage directory')
    parser.add_argument('--output_dir', type=str, default='checkpoints',
                        help='Directory to save checkpoints')
    parser.add_argument('--epochs', type=int, default=20,
                        help='Number of training epochs')
    parser.add_argument('--batch_size', type=int, default=16,
                        help='Batch size')
    parser.add_argument('--lr', type=float, default=0.001,
                        help='Learning rate')
    parser.add_argument('--device', type=str, default='cuda',
                        help='Device (cuda or cpu)')
    parser.add_argument('--num_workers', type=int, default=4,
                        help='Number of data loader workers')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Set device
    device = torch.device(args.device if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # Create dataloaders
    print("\nLoading dataset...")
    train_loader, val_loader, test_loader = create_strad_dataloaders(
        data_dir=args.data_dir,
        batch_size=args.batch_size,
        num_workers=args.num_workers
    )
    
    # Create model
    print("\nCreating model...")
    model = StradClassifier(num_classes=3, pretrained=True)
    model = model.to(device)
    
    # Get class weights for imbalanced data
    class_weights = train_loader.dataset.dataset.get_class_weights()
    class_weights = class_weights.to(device)
    
    # Loss and optimizer
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = optim.Adam(model.parameters(), lr=args.lr)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=3, verbose=True
    )
    
    # Training loop
    print(f"\nStarting training for {args.epochs} epochs...")
    print("=" * 60)
    
    best_val_acc = 0.0
    training_history = []
    
    for epoch in range(args.epochs):
        print(f"\nEpoch {epoch+1}/{args.epochs}")
        print("-" * 60)
        
        # Train
        train_loss, train_acc = train_epoch(
            model, train_loader, criterion, optimizer, device
        )
        
        # Validate
        val_loss, val_acc = validate(
            model, val_loader, criterion, device
        )
        
        # Adjust learning rate
        scheduler.step(val_loss)
        
        # Print epoch summary
        print(f"\nEpoch {epoch+1} Summary:")
        print(f"  Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.2f}%")
        print(f"  Val Loss:   {val_loss:.4f} | Val Acc:   {val_acc:.2f}%")
        
        # Save training history
        training_history.append({
            'epoch': epoch + 1,
            'train_loss': train_loss,
            'train_acc': train_acc,
            'val_loss': val_loss,
            'val_acc': val_acc
        })
        
        # Save checkpoint if best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            checkpoint_path = output_dir / 'best_model.pth'
            save_checkpoint(
                model, optimizer, epoch, train_loss, val_loss, val_acc,
                checkpoint_path
            )
            print(f"  ✓ New best model! Val Acc: {val_acc:.2f}%")
    
    # Save final model
    final_checkpoint_path = output_dir / 'final_model.pth'
    save_checkpoint(
        model, optimizer, args.epochs, train_loss, val_loss, val_acc,
        final_checkpoint_path
    )
    
    # Save training history
    history_path = output_dir / 'training_history.json'
    with open(history_path, 'w') as f:
        json.dump(training_history, f, indent=2)
    print(f"\nTraining history saved to {history_path}")
    
    # Test on test set
    print("\n" + "=" * 60)
    print("Evaluating on test set...")
    test_loss, test_acc = validate(model, test_loader, criterion, device)
    print(f"Test Loss: {test_loss:.4f} | Test Acc: {test_acc:.2f}%")
    
    print("\n" + "=" * 60)
    print("Training complete!")
    print(f"Best validation accuracy: {best_val_acc:.2f}%")
    print(f"Final test accuracy: {test_acc:.2f}%")
    print(f"Checkpoints saved to: {output_dir}")
    print("=" * 60)


if __name__ == '__main__':
    main()
