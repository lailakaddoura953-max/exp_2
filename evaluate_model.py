"""
Model Evaluation Script with Visualizations

This script evaluates a trained strad classifier and generates comprehensive
visualizations including:
- Confusion matrix
- Precision, Recall, F1-score per class
- Class distribution analysis
- Sample predictions with confidence scores
- ROC curves (for multi-class)

Usage:
    python evaluate_model.py --model trained_models/strad_classifier_acc85.3.pth --data_dir SCFootage
"""

import argparse
import sys
from pathlib import Path
import torch
import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, classification_report, roc_curve, auc
from sklearn.preprocessing import label_binarize
from tqdm import tqdm
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from dl_misalignment.data.strad_footage_dataset import create_strad_dataloaders
from torchvision import transforms


class SimpleStradClassifier(nn.Module):
    """Same architecture as training script."""
    def __init__(self, num_classes=3):
        super(SimpleStradClassifier, self).__init__()
        
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            
            nn.AdaptiveAvgPool2d((4, 4))
        )
        
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


def evaluate_model(model, dataloader, device):
    """
    Evaluate model and collect predictions.
    
    Returns:
        y_true: Ground truth labels
        y_pred: Predicted labels
        y_probs: Prediction probabilities
    """
    model.eval()
    
    y_true = []
    y_pred = []
    y_probs = []
    
    with torch.no_grad():
        for inputs, labels in tqdm(dataloader, desc="Evaluating"):
            inputs, labels = inputs.to(device), labels.to(device)
            
            outputs = model(inputs)
            probs = torch.softmax(outputs, dim=1)
            _, predicted = outputs.max(1)
            
            y_true.extend(labels.cpu().numpy())
            y_pred.extend(predicted.cpu().numpy())
            y_probs.extend(probs.cpu().numpy())
    
    return np.array(y_true), np.array(y_pred), np.array(y_probs)


def plot_confusion_matrix(y_true, y_pred, class_names, output_path):
    """Generate and save confusion matrix heatmap."""
    cm = confusion_matrix(y_true, y_pred)
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=class_names, yticklabels=class_names,
                cbar_kws={'label': 'Count'})
    plt.title('Confusion Matrix', fontsize=16, fontweight='bold')
    plt.ylabel('True Label', fontsize=12)
    plt.xlabel('Predicted Label', fontsize=12)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Confusion matrix saved: {output_path}")


def plot_classification_report(y_true, y_pred, class_names, output_path):
    """Generate and save classification metrics bar chart."""
    from sklearn.metrics import precision_recall_fscore_support
    
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=[0, 1, 2]
    )
    
    x = np.arange(len(class_names))
    width = 0.25
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.bar(x - width, precision, width, label='Precision', color='#3498db')
    ax.bar(x, recall, width, label='Recall', color='#2ecc71')
    ax.bar(x + width, f1, width, label='F1-Score', color='#e74c3c')
    
    ax.set_xlabel('Class', fontsize=12)
    ax.set_ylabel('Score', fontsize=12)
    ax.set_title('Classification Metrics by Class', fontsize=16, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(class_names)
    ax.legend()
    ax.set_ylim([0, 1.1])
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for i, (p, r, f) in enumerate(zip(precision, recall, f1)):
        ax.text(i - width, p + 0.02, f'{p:.3f}', ha='center', fontsize=9)
        ax.text(i, r + 0.02, f'{r:.3f}', ha='center', fontsize=9)
        ax.text(i + width, f + 0.02, f'{f:.3f}', ha='center', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Classification metrics saved: {output_path}")
    
    # Print detailed report
    print("\n" + "="*60)
    print("CLASSIFICATION REPORT")
    print("="*60)
    print(classification_report(y_true, y_pred, target_names=class_names, digits=4))


def plot_class_distribution(y_true, y_pred, class_names, output_path):
    """Generate class distribution comparison."""
    true_counts = np.bincount(y_true, minlength=3)
    pred_counts = np.bincount(y_pred, minlength=3)
    
    x = np.arange(len(class_names))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bars1 = ax.bar(x - width/2, true_counts, width, label='Ground Truth', 
                   color='#3498db', alpha=0.8)
    bars2 = ax.bar(x + width/2, pred_counts, width, label='Predictions', 
                   color='#2ecc71', alpha=0.8)
    
    ax.set_xlabel('Class', fontsize=12)
    ax.set_ylabel('Count', fontsize=12)
    ax.set_title('Class Distribution: Ground Truth vs Predictions', 
                 fontsize=16, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(class_names)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}', ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Class distribution saved: {output_path}")


def plot_roc_curves(y_true, y_probs, class_names, output_path):
    """Generate ROC curves for multi-class classification."""
    y_true_bin = label_binarize(y_true, classes=[0, 1, 2])
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    colors = ['#3498db', '#2ecc71', '#e74c3c']
    
    for i, (class_name, color) in enumerate(zip(class_names, colors)):
        fpr, tpr, _ = roc_curve(y_true_bin[:, i], y_probs[:, i])
        roc_auc = auc(fpr, tpr)
        
        ax.plot(fpr, tpr, color=color, lw=2,
               label=f'{class_name} (AUC = {roc_auc:.3f})')
    
    ax.plot([0, 1], [0, 1], 'k--', lw=2, label='Random Classifier')
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel('False Positive Rate', fontsize=12)
    ax.set_ylabel('True Positive Rate', fontsize=12)
    ax.set_title('ROC Curves by Class', fontsize=16, fontweight='bold')
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ ROC curves saved: {output_path}")


def plot_confidence_distribution(y_true, y_pred, y_probs, class_names, output_path):
    """Plot confidence score distributions for correct vs incorrect predictions."""
    correct_mask = (y_true == y_pred)
    incorrect_mask = ~correct_mask
    
    correct_conf = np.max(y_probs[correct_mask], axis=1)
    incorrect_conf = np.max(y_probs[incorrect_mask], axis=1)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.hist(correct_conf, bins=30, alpha=0.7, label='Correct Predictions', 
            color='#2ecc71', edgecolor='black')
    ax.hist(incorrect_conf, bins=30, alpha=0.7, label='Incorrect Predictions', 
            color='#e74c3c', edgecolor='black')
    
    ax.set_xlabel('Confidence Score', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title('Confidence Distribution: Correct vs Incorrect Predictions', 
                 fontsize=16, fontweight='bold')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    # Add mean lines
    ax.axvline(np.mean(correct_conf), color='#2ecc71', linestyle='--', linewidth=2,
              label=f'Mean Correct: {np.mean(correct_conf):.3f}')
    ax.axvline(np.mean(incorrect_conf), color='#e74c3c', linestyle='--', linewidth=2,
              label=f'Mean Incorrect: {np.mean(incorrect_conf):.3f}')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Confidence distribution saved: {output_path}")


def save_evaluation_summary(y_true, y_pred, y_probs, class_names, output_path):
    """Save evaluation summary as JSON."""
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support
    
    accuracy = accuracy_score(y_true, y_pred)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=[0, 1, 2]
    )
    
    summary = {
        'overall_accuracy': float(accuracy),
        'per_class_metrics': {}
    }
    
    for i, class_name in enumerate(class_names):
        summary['per_class_metrics'][class_name] = {
            'precision': float(precision[i]),
            'recall': float(recall[i]),
            'f1_score': float(f1[i]),
            'support': int(support[i])
        }
    
    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"✓ Evaluation summary saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Evaluate Strad Classifier')
    parser.add_argument('--model', type=str, required=True,
                        help='Path to trained model checkpoint')
    parser.add_argument('--data_dir', type=str, default='SCFootage',
                        help='Path to validation data')
    parser.add_argument('--batch_size', type=int, default=16,
                        help='Batch size for evaluation')
    parser.add_argument('--output_dir', type=str, default='evaluation_results',
                        help='Directory to save evaluation results')
    parser.add_argument('--device', type=str, default='auto',
                        help='Device (cuda/cpu/auto)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("STRAD CLASSIFIER - MODEL EVALUATION")
    print("=" * 80)
    
    # Setup device
    if args.device == 'auto':
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    else:
        device = torch.device(args.device)
    
    print(f"\nDevice: {device}")
    print(f"Model: {args.model}")
    print(f"Data: {args.data_dir}")
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Load model
    print(f"\nLoading model...")
    checkpoint = torch.load(args.model, map_location=device)
    
    model = SimpleStradClassifier(num_classes=3).to(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    
    print(f"✓ Model loaded (epoch {checkpoint['epoch']})")
    
    # Prepare data
    print(f"\nLoading validation data...")
    
    transform_val = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    _, val_loader, dataset_info = create_strad_dataloaders(
        root_dir=args.data_dir,
        batch_size=args.batch_size,
        train_split=0.8,
        num_workers=4,
        transform_train=None,
        transform_val=transform_val,
        image_size=(640, 640)
    )
    
    print(f"✓ Validation samples: {dataset_info['val_samples']}")
    
    # Evaluate
    print(f"\n{'=' * 80}")
    print("RUNNING EVALUATION")
    print("=" * 80)
    
    y_true, y_pred, y_probs = evaluate_model(model, val_loader, device)
    
    class_names = ['None', 'Moderate', 'Critical']
    
    print(f"\n✓ Evaluation complete: {len(y_true)} samples")
    
    # Generate visualizations
    print(f"\n{'=' * 80}")
    print("GENERATING VISUALIZATIONS")
    print("=" * 80)
    
    plot_confusion_matrix(y_true, y_pred, class_names, 
                          output_dir / 'confusion_matrix.png')
    
    plot_classification_report(y_true, y_pred, class_names,
                               output_dir / 'classification_metrics.png')
    
    plot_class_distribution(y_true, y_pred, class_names,
                           output_dir / 'class_distribution.png')
    
    plot_roc_curves(y_true, y_probs, class_names,
                    output_dir / 'roc_curves.png')
    
    plot_confidence_distribution(y_true, y_pred, y_probs, class_names,
                                 output_dir / 'confidence_distribution.png')
    
    save_evaluation_summary(y_true, y_pred, y_probs, class_names,
                            output_dir / 'evaluation_summary.json')
    
    print(f"\n{'=' * 80}")
    print("EVALUATION COMPLETE")
    print("=" * 80)
    print(f"\nAll results saved to: {output_dir}/")
    print(f"\nGenerated files:")
    print(f"  - confusion_matrix.png")
    print(f"  - classification_metrics.png")
    print(f"  - class_distribution.png")
    print(f"  - roc_curves.png")
    print(f"  - confidence_distribution.png")
    print(f"  - evaluation_summary.json")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
