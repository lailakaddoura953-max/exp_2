"""
Training Visualization Utilities

Comprehensive visualization tools for training analysis and architecture comparison.
Uses seaborn and pandas for publication-quality plots.

Visualization Types:
1. Loss curves and training progress
2. Prediction histograms and distributions
3. Confusion matrices with metrics (precision, recall, F1)
4. Pose error heatmaps
5. Architecture comparison dashboards

Requirements: Visualization for Task 9 training pipeline
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    import pandas as pd
    from sklearn.metrics import confusion_matrix, classification_report, roc_curve, auc
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    plt = None
    sns = None
    pd = None

logger = logging.getLogger(__name__)

# Set seaborn style for beautiful plots
if VISUALIZATION_AVAILABLE:
    sns.set_style("whitegrid")
    sns.set_palette("husl")


class TrainingVisualizer:
    """
    Comprehensive visualization for training analysis.
    
    Creates:
    - Loss curves (training/validation)
    - Prediction distributions
    - Confusion matrices with metrics
    - Architecture comparisons
    - Pose error analysis
    """
    
    def __init__(self, output_dir: str = "results"):
        """
        Initialize visualizer.
        
        Args:
            output_dir: Directory to save plots
        """
        if not VISUALIZATION_AVAILABLE:
            raise ImportError("Visualization dependencies not available. "
                            "Install: pip install matplotlib seaborn pandas scikit-learn")
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"TrainingVisualizer initialized. Output: {self.output_dir}")
    
    # ==========================================================================
    # 1. Loss Curves and Training Progress
    # ==========================================================================
    
    def plot_loss_curves(
        self,
        train_losses: Dict[str, List[float]],
        val_losses: Dict[str, List[float]],
        architecture_name: str = "Architecture"
    ) -> plt.Figure:
        """
        Plot training and validation loss curves.
        
        Args:
            train_losses: {'total': [...], 'classification': [...], 'regression': [...]}
            val_losses: Same structure as train_losses
            architecture_name: "Architecture A" or "Architecture B"
        
        Returns:
            matplotlib Figure
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'{architecture_name} - Training Progress', fontsize=16, weight='bold')
        
        # Total loss
        axes[0, 0].plot(train_losses['total'], label='Train', linewidth=2)
        axes[0, 0].plot(val_losses['total'], label='Validation', linewidth=2)
        axes[0, 0].set_title('Total Loss', fontsize=12, weight='bold')
        axes[0, 0].set_xlabel('Epoch')
        axes[0, 0].set_ylabel('Loss')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # Classification loss (BCE)
        axes[0, 1].plot(train_losses['classification'], label='Train', linewidth=2)
        axes[0, 1].plot(val_losses['classification'], label='Validation', linewidth=2)
        axes[0, 1].set_title('Classification Loss (BCE)', fontsize=12, weight='bold')
        axes[0, 1].set_xlabel('Epoch')
        axes[0, 1].set_ylabel('Loss')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # Regression loss (Smooth L1)
        axes[1, 0].plot(train_losses['regression'], label='Train', linewidth=2)
        axes[1, 0].plot(val_losses['regression'], label='Validation', linewidth=2)
        axes[1, 0].set_title('Regression Loss (Smooth L1)', fontsize=12, weight='bold')
        axes[1, 0].set_xlabel('Epoch')
        axes[1, 0].set_ylabel('Loss')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # Loss components breakdown
        epochs = len(train_losses['total'])
        x = np.arange(epochs)
        axes[1, 1].bar(x - 0.2, train_losses['classification'], width=0.4, label='Classification', alpha=0.7)
        axes[1, 1].bar(x + 0.2, train_losses['regression'], width=0.4, label='Regression', alpha=0.7)
        axes[1, 1].set_title('Loss Component Breakdown (Train)', fontsize=12, weight='bold')
        axes[1, 1].set_xlabel('Epoch')
        axes[1, 1].set_ylabel('Loss')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        # Save
        save_path = self.output_dir / f"{architecture_name.lower().replace(' ', '_')}_loss_curves.png"
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Loss curves saved: {save_path}")
        
        return fig
    
    # ==========================================================================
    # 2. Prediction Distributions
    # ==========================================================================
    
    def plot_prediction_distributions(
        self,
        predictions: np.ndarray,
        ground_truth: np.ndarray,
        architecture_name: str = "Architecture"
    ) -> plt.Figure:
        """
        Plot histogram of prediction distributions.
        
        Args:
            predictions: Predicted probabilities [N]
            ground_truth: True labels [N] (0 or 1)
            architecture_name: Model name
        
        Returns:
            matplotlib Figure
        """
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle(f'{architecture_name} - Prediction Distributions', fontsize=16, weight='bold')
        
        # Histogram by class
        aligned = predictions[ground_truth == 0]
        misaligned = predictions[ground_truth == 1]
        
        axes[0].hist(aligned, bins=30, alpha=0.6, label='Aligned (GT=0)', color='green', edgecolor='black')
        axes[0].hist(misaligned, bins=30, alpha=0.6, label='Misaligned (GT=1)', color='red', edgecolor='black')
        axes[0].axvline(0.5, color='black', linestyle='--', linewidth=2, label='Threshold=0.5')
        axes[0].set_xlabel('Predicted Probability', fontsize=12)
        axes[0].set_ylabel('Frequency', fontsize=12)
        axes[0].set_title('Prediction Histogram by Ground Truth', fontsize=12, weight='bold')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3, axis='y')
        
        # KDE plot
        sns.kdeplot(data=aligned, ax=axes[1], label='Aligned (GT=0)', fill=True, alpha=0.5, color='green')
        sns.kdeplot(data=misaligned, ax=axes[1], label='Misaligned (GT=1)', fill=True, alpha=0.5, color='red')
        axes[1].axvline(0.5, color='black', linestyle='--', linewidth=2, label='Threshold=0.5')
        axes[1].set_xlabel('Predicted Probability', fontsize=12)
        axes[1].set_ylabel('Density', fontsize=12)
        axes[1].set_title('Probability Density Estimation', fontsize=12, weight='bold')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        # Save
        save_path = self.output_dir / f"{architecture_name.lower().replace(' ', '_')}_distributions.png"
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Distributions saved: {save_path}")
        
        return fig
    
    # ==========================================================================
    # 3. Confusion Matrix with Metrics
    # ==========================================================================
    
    def plot_confusion_matrix(
        self,
        predictions: np.ndarray,
        ground_truth: np.ndarray,
        threshold: float = 0.5,
        architecture_name: str = "Architecture"
    ) -> Tuple[plt.Figure, Dict]:
        """
        Plot confusion matrix with precision, recall, F1 scores.
        
        Args:
            predictions: Predicted probabilities [N]
            ground_truth: True labels [N] (0 or 1)
            threshold: Classification threshold
            architecture_name: Model name
        
        Returns:
            Tuple of (Figure, metrics_dict)
        """
        # Convert probabilities to binary predictions
        pred_binary = (predictions >= threshold).astype(int)
        
        # Compute confusion matrix
        cm = confusion_matrix(ground_truth, pred_binary)
        
        # Compute metrics
        from sklearn.metrics import precision_recall_fscore_support, accuracy_score
        precision, recall, f1, support = precision_recall_fscore_support(
            ground_truth, pred_binary, average=None, zero_division=0
        )
        accuracy = accuracy_score(ground_truth, pred_binary)
        
        # Create figure
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle(f'{architecture_name} - Classification Performance', fontsize=16, weight='bold')
        
        # Plot confusion matrix
        sns.heatmap(
            cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=['Aligned', 'Misaligned'],
            yticklabels=['Aligned', 'Misaligned'],
            ax=axes[0],
            cbar_kws={'label': 'Count'}
        )
        axes[0].set_title('Confusion Matrix', fontsize=12, weight='bold')
        axes[0].set_ylabel('True Label', fontsize=12)
        axes[0].set_xlabel('Predicted Label', fontsize=12)
        
        # Plot metrics
        metrics_df = pd.DataFrame({
            'Class': ['Aligned', 'Misaligned'],
            'Precision': precision,
            'Recall': recall,
            'F1-Score': f1,
            'Support': support
        })
        
        x = np.arange(len(metrics_df))
        width = 0.25
        
        axes[1].bar(x - width, metrics_df['Precision'], width, label='Precision', alpha=0.8)
        axes[1].bar(x, metrics_df['Recall'], width, label='Recall', alpha=0.8)
        axes[1].bar(x + width, metrics_df['F1-Score'], width, label='F1-Score', alpha=0.8)
        
        axes[1].set_xlabel('Class', fontsize=12)
        axes[1].set_ylabel('Score', fontsize=12)
        axes[1].set_title(f'Metrics (Accuracy: {accuracy:.3f})', fontsize=12, weight='bold')
        axes[1].set_xticks(x)
        axes[1].set_xticklabels(metrics_df['Class'])
        axes[1].legend()
        axes[1].grid(True, alpha=0.3, axis='y')
        axes[1].set_ylim([0, 1.0])
        
        plt.tight_layout()
        
        # Save
        save_path = self.output_dir / f"{architecture_name.lower().replace(' ', '_')}_confusion_matrix.png"
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Confusion matrix saved: {save_path}")
        
        # Return metrics dict
        metrics = {
            'accuracy': accuracy,
            'precision_aligned': precision[0],
            'precision_misaligned': precision[1],
            'recall_aligned': recall[0],
            'recall_misaligned': recall[1],
            'f1_aligned': f1[0],
            'f1_misaligned': f1[1],
            'confusion_matrix': cm
        }
        
        return fig, metrics
    
    # ==========================================================================
    # 4. Pose Error Heatmap
    # ==========================================================================
    
    def plot_pose_error_heatmap(
        self,
        predicted_pose: np.ndarray,
        true_pose: np.ndarray,
        architecture_name: str = "Architecture"
    ) -> plt.Figure:
        """
        Plot heatmap of pose prediction errors.
        
        Args:
            predicted_pose: Predicted poses [N, 6]
            true_pose: True poses [N, 6]
            architecture_name: Model name
        
        Returns:
            matplotlib Figure
        """
        # Compute errors
        errors = np.abs(predicted_pose - true_pose)
        
        # Create dataframe
        df = pd.DataFrame(
            errors,
            columns=['X (m)', 'Y (m)', 'Z (m)', 'Roll (°)', 'Pitch (°)', 'Yaw (°)']
        )
        
        fig, axes = plt.subplots(2, 1, figsize=(12, 10))
        fig.suptitle(f'{architecture_name} - Pose Estimation Error Analysis', fontsize=16, weight='bold')
        
        # Correlation heatmap of errors
        correlation = df.corr()
        sns.heatmap(
            correlation, annot=True, fmt='.2f', cmap='coolwarm',
            center=0, square=True, linewidths=1,
            cbar_kws={'label': 'Correlation'},
            ax=axes[0]
        )
        axes[0].set_title('Error Correlation Matrix', fontsize=12, weight='bold')
        
        # Box plot of errors by axis
        df_melted = df.melt(var_name='Axis', value_name='Absolute Error')
        sns.boxplot(data=df_melted, x='Axis', y='Absolute Error', ax=axes[1])
        axes[1].set_title('Error Distribution per Axis', fontsize=12, weight='bold')
        axes[1].set_xlabel('Pose Component', fontsize=12)
        axes[1].set_ylabel('Absolute Error', fontsize=12)
        axes[1].grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        # Save
        save_path = self.output_dir / f"{architecture_name.lower().replace(' ', '_')}_pose_errors.png"
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Pose error heatmap saved: {save_path}")
        
        return fig
    
    # ==========================================================================
    # 5. Architecture Comparison
    # ==========================================================================
    
    def plot_architecture_comparison(
        self,
        metrics_a: Dict,
        metrics_b: Dict
    ) -> plt.Figure:
        """
        Compare Architecture A vs Architecture B.
        
        Args:
            metrics_a: Metrics for Architecture A
            metrics_b: Metrics for Architecture B
        
        Returns:
            matplotlib Figure
        """
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Architecture Comparison: A vs B', fontsize=16, weight='bold')
        
        # Accuracy metrics
        metrics = ['accuracy', 'precision_misaligned', 'recall_misaligned', 'f1_misaligned']
        labels = ['Accuracy', 'Precision', 'Recall', 'F1-Score']
        
        values_a = [metrics_a.get(m, 0) for m in metrics]
        values_b = [metrics_b.get(m, 0) for m in metrics]
        
        x = np.arange(len(labels))
        width = 0.35
        
        axes[0, 0].bar(x - width/2, values_a, width, label='Architecture A (LiteFlowNet2)', alpha=0.8)
        axes[0, 0].bar(x + width/2, values_b, width, label='Architecture B (SpyNet)', alpha=0.8)
        axes[0, 0].set_xlabel('Metric', fontsize=12)
        axes[0, 0].set_ylabel('Score', fontsize=12)
        axes[0, 0].set_title('Classification Metrics', fontsize=12, weight='bold')
        axes[0, 0].set_xticks(x)
        axes[0, 0].set_xticklabels(labels, rotation=15)
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3, axis='y')
        axes[0, 0].set_ylim([0, 1.0])
        
        # Memory usage
        memory_a = metrics_a.get('memory_gb', 0)
        memory_b = metrics_b.get('memory_gb', 0)
        
        axes[0, 1].bar(['Arch A', 'Arch B'], [memory_a, memory_b], color=['#1f77b4', '#ff7f0e'], alpha=0.8)
        axes[0, 1].axhline(4.0, color='red', linestyle='--', label='Target: 4GB (A), 3GB (B)')
        axes[0, 1].axhline(3.0, color='orange', linestyle='--')
        axes[0, 1].set_ylabel('Memory (GB)', fontsize=12)
        axes[0, 1].set_title('VRAM Usage', fontsize=12, weight='bold')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3, axis='y')
        
        # Inference latency
        latency_a = metrics_a.get('latency_ms', 0)
        latency_b = metrics_b.get('latency_ms', 0)
        
        axes[1, 0].bar(['Arch A', 'Arch B'], [latency_a, latency_b], color=['#1f77b4', '#ff7f0e'], alpha=0.8)
        axes[1, 0].axhline(50, color='red', linestyle='--', label='Target: 50ms (A)')
        axes[1, 0].axhline(30, color='orange', linestyle='--', label='Target: 30ms (B)')
        axes[1, 0].set_ylabel('Latency (ms)', fontsize=12)
        axes[1, 0].set_title('Inference Latency (4-camera batch)', fontsize=12, weight='bold')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3, axis='y')
        
        # Accuracy vs Speed trade-off
        axes[1, 1].scatter(latency_a, values_a[0], s=200, alpha=0.6, label='Architecture A', color='#1f77b4')
        axes[1, 1].scatter(latency_b, values_b[0], s=200, alpha=0.6, label='Architecture B', color='#ff7f0e')
        axes[1, 1].annotate('Arch A', (latency_a, values_a[0]), xytext=(5, 5), textcoords='offset points')
        axes[1, 1].annotate('Arch B', (latency_b, values_b[0]), xytext=(5, 5), textcoords='offset points')
        axes[1, 1].set_xlabel('Inference Latency (ms)', fontsize=12)
        axes[1, 1].set_ylabel('Accuracy', fontsize=12)
        axes[1, 1].set_title('Accuracy vs Speed Trade-off', fontsize=12, weight='bold')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save
        save_path = self.output_dir / "architecture_comparison.png"
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Architecture comparison saved: {save_path}")
        
        return fig
    
    # ==========================================================================
    # 6. ROC Curve
    # ==========================================================================
    
    def plot_roc_curve(
        self,
        predictions: np.ndarray,
        ground_truth: np.ndarray,
        architecture_name: str = "Architecture"
    ) -> Tuple[plt.Figure, float]:
        """
        Plot ROC curve and compute AUC.
        
        Args:
            predictions: Predicted probabilities [N]
            ground_truth: True labels [N] (0 or 1)
            architecture_name: Model name
        
        Returns:
            Tuple of (Figure, AUC score)
        """
        # Compute ROC curve
        fpr, tpr, thresholds = roc_curve(ground_truth, predictions)
        roc_auc = auc(fpr, tpr)
        
        # Plot
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.plot(fpr, tpr, linewidth=2, label=f'ROC (AUC = {roc_auc:.3f})')
        ax.plot([0, 1], [0, 1], 'k--', linewidth=2, label='Random Classifier')
        ax.set_xlabel('False Positive Rate', fontsize=12)
        ax.set_ylabel('True Positive Rate', fontsize=12)
        ax.set_title(f'{architecture_name} - ROC Curve', fontsize=14, weight='bold')
        ax.legend(loc='lower right', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1])
        
        plt.tight_layout()
        
        # Save
        save_path = self.output_dir / f"{architecture_name.lower().replace(' ', '_')}_roc_curve.png"
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"ROC curve saved: {save_path}")
        
        return fig, roc_auc
    
    # ==========================================================================
    # 7. Sample Prediction Visualization (for TensorBoard)
    # ==========================================================================
    
    def create_sample_prediction_grid(
        self,
        images: np.ndarray,
        predictions: np.ndarray,
        ground_truth: np.ndarray,
        num_samples: int = 4
    ) -> plt.Figure:
        """
        Create grid visualization of sample predictions for TensorBoard logging.
        
        Args:
            images: Input images [N, C, H, W] or [N, H, W, C]
            predictions: Predicted probabilities [N]
            ground_truth: True labels [N]
            num_samples: Number of samples to visualize
        
        Returns:
            matplotlib Figure
        """
        num_samples = min(num_samples, len(images))
        
        fig, axes = plt.subplots(1, num_samples, figsize=(4*num_samples, 4))
        if num_samples == 1:
            axes = [axes]
        
        for idx in range(num_samples):
            # Get image (handle both CHW and HWC formats)
            img = images[idx]
            if img.shape[0] == 3:  # CHW format
                img = np.transpose(img, (1, 2, 0))  # Convert to HWC
            
            # Normalize to [0, 1] if needed
            if img.min() < 0 or img.max() > 1:
                img = (img - img.min()) / (img.max() - img.min() + 1e-8)
            
            # Plot image
            axes[idx].imshow(img)
            
            # Add prediction overlay
            pred = predictions[idx]
            gt = ground_truth[idx]
            correct = (pred > 0.5) == (gt > 0.5)
            
            color = 'green' if correct else 'red'
            axes[idx].set_title(
                f'Pred: {pred:.3f}\nGT: {gt:.1f}',
                color=color,
                fontsize=10,
                weight='bold'
            )
            axes[idx].axis('off')
        
        plt.tight_layout()
        return fig
