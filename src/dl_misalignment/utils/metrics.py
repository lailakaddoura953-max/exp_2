"""
Metrics Calculation for Model Evaluation

This module calculates all performance metrics needed to evaluate the
deep learning misalignment detection system:

1. Classification Metrics:
   - Accuracy: Overall correctness
   - Precision: How many predicted positives are actually positive
   - Recall: How many actual positives we detected
   - F1 Score: Harmonic mean of precision and recall
   
2. Detection Metrics:
   - mAP (Mean Average Precision): Standard metric for detection tasks
   - Confusion Matrix: True/False Positives/Negatives

3. Performance Metrics:
   - Inference latency
   - Memory usage (VRAM)
   - Throughput (images per second)

For developers new to ML metrics:
- Precision answers: "When the model says misaligned, is it usually right?"
- Recall answers: "Of all the actual misalignments, how many did we catch?"
- F1 balances precision and recall (useful when both matter equally)
- mAP is the standard way to compare detection models
"""

import logging
from typing import Dict, List, Tuple, Optional
import numpy as np

# Try to import sklearn (might not be installed yet)
try:
    from sklearn.metrics import (
        accuracy_score,
        precision_score,
        recall_score,
        f1_score,
        confusion_matrix,
        classification_report,
        average_precision_score,
        roc_auc_score,
        roc_curve
    )
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)


# ==============================================================================
# Classification Metrics
# ==============================================================================


def calculate_classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: Optional[np.ndarray] = None,
    class_names: List[str] = None
) -> Dict[str, any]:
    """
    Calculate comprehensive classification metrics.
    
    This is the main function for evaluating model performance.
    Call this after running inference on the test set.
    
    Args:
        y_true: True labels (0 = aligned, 1 = misaligned)
        y_pred: Predicted labels (0 or 1)
        y_prob: Predicted probabilities (0.0 to 1.0), optional
        class_names: Names for classes (default: ["Aligned", "Misaligned"])
    
    Returns:
        Dictionary containing:
        - accuracy: Overall correctness (0 to 1)
        - precision: Positive predictive value (0 to 1)
        - recall: True positive rate / sensitivity (0 to 1)
        - f1_score: Harmonic mean of precision and recall (0 to 1)
        - confusion_matrix: 2×2 matrix [[TN, FP], [FN, TP]]
        - false_positive_rate: FP / (FP + TN) (0 to 1)
        - false_negative_rate: FN / (FN + TP) (0 to 1)
        - classification_report: Detailed per-class metrics
        - mAP: Mean average precision (if y_prob provided)
        - auc: Area under ROC curve (if y_prob provided)
    
    Example:
        >>> y_true = np.array([0, 1, 0, 1, 1, 0])
        >>> y_pred = np.array([0, 1, 1, 1, 0, 0])
        >>> y_prob = np.array([0.1, 0.9, 0.6, 0.85, 0.4, 0.2])
        >>> metrics = calculate_classification_metrics(y_true, y_pred, y_prob)
        >>> print(f"Accuracy: {metrics['accuracy']:.3f}")
        >>> print(f"F1 Score: {metrics['f1_score']:.3f}")
    """
    if not SKLEARN_AVAILABLE:
        raise ImportError(
            "scikit-learn is required for metrics calculation. "
            "Install it with: pip install scikit-learn"
        )
    
    if class_names is None:
        class_names = ["Aligned", "Misaligned"]
    
    metrics = {}
    
    # Basic classification metrics
    metrics['accuracy'] = accuracy_score(y_true, y_pred)
    metrics['precision'] = precision_score(y_true, y_pred, zero_division=0)
    metrics['recall'] = recall_score(y_true, y_pred, zero_division=0)
    metrics['f1_score'] = f1_score(y_true, y_pred, zero_division=0)
    
    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    metrics['confusion_matrix'] = cm
    
    # Extract TP, TN, FP, FN from confusion matrix
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
        metrics['true_positives'] = int(tp)
        metrics['true_negatives'] = int(tn)
        metrics['false_positives'] = int(fp)
        metrics['false_negatives'] = int(fn)
        
        # Calculate error rates
        metrics['false_positive_rate'] = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        metrics['false_negative_rate'] = fn / (fn + tp) if (fn + tp) > 0 else 0.0
        
        # Specificity (True Negative Rate)
        metrics['specificity'] = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    
    # Detailed classification report
    report = classification_report(
        y_true,
        y_pred,
        target_names=class_names,
        output_dict=True,
        zero_division=0
    )
    metrics['classification_report'] = report
    metrics['per_class_metrics'] = {
        class_names[i]: report[class_names[i]]
        for i in range(len(class_names))
        if class_names[i] in report
    }
    
    # Probability-based metrics (if probabilities provided)
    if y_prob is not None:
        # Mean Average Precision
        metrics['mAP'] = average_precision_score(y_true, y_prob)
        
        # ROC AUC
        metrics['auc'] = roc_auc_score(y_true, y_prob)
        
        # ROC curve data (for plotting)
        fpr, tpr, thresholds = roc_curve(y_true, y_prob)
        metrics['roc_curve'] = {
            'fpr': fpr,
            'tpr': tpr,
            'thresholds': thresholds
        }
    
    # Log summary
    logger.info("=" * 60)
    logger.info("Classification Metrics Summary")
    logger.info("=" * 60)
    logger.info(f"Accuracy:  {metrics['accuracy']:.4f} ({metrics['accuracy']*100:.2f}%)")
    logger.info(f"Precision: {metrics['precision']:.4f}")
    logger.info(f"Recall:    {metrics['recall']:.4f}")
    logger.info(f"F1 Score:  {metrics['f1_score']:.4f}")
    if 'mAP' in metrics:
        logger.info(f"mAP:       {metrics['mAP']:.4f}")
    logger.info(f"FP Rate:   {metrics.get('false_positive_rate', 0):.4f}")
    logger.info(f"FN Rate:   {metrics.get('false_negative_rate', 0):.4f}")
    logger.info("=" * 60)
    
    # Check if meets requirements (≥95% accuracy, ≤5% FPR)
    meets_accuracy = metrics['accuracy'] >= 0.95
    meets_fpr = metrics.get('false_positive_rate', 1.0) <= 0.05
    metrics['meets_requirements'] = meets_accuracy and meets_fpr
    
    if not meets_accuracy:
        logger.warning(f"⚠ Accuracy {metrics['accuracy']:.2%} below target (95%)")
    if not meets_fpr:
        logger.warning(f"⚠ False positive rate {metrics.get('false_positive_rate', 0):.2%} above target (5%)")
    
    if metrics['meets_requirements']:
        logger.info("✓ Model meets all accuracy requirements!")
    
    return metrics


def calculate_severity_metrics(
    y_true_severity: np.ndarray,
    y_pred_severity: np.ndarray,
    severity_levels: List[str] = None
) -> Dict[str, any]:
    """
    Calculate metrics for severity level classification.
    
    Severity levels: LOW, MEDIUM, HIGH, CRITICAL
    This is a multi-class problem (4 classes instead of binary).
    
    Args:
        y_true_severity: True severity levels (0-3)
        y_pred_severity: Predicted severity levels (0-3)
        severity_levels: Names for severity levels
    
    Returns:
        Dictionary with per-severity metrics
    
    Example:
        >>> y_true = np.array([0, 1, 2, 3, 1, 2])  # LOW, MEDIUM, HIGH, CRITICAL, ...
        >>> y_pred = np.array([0, 1, 2, 2, 1, 2])  # Predicted severities
        >>> metrics = calculate_severity_metrics(y_true, y_pred)
        >>> print(metrics['accuracy'])
    """
    if not SKLEARN_AVAILABLE:
        raise ImportError("scikit-learn required for metrics")
    
    if severity_levels is None:
        severity_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    
    metrics = {}
    
    # Overall accuracy
    metrics['accuracy'] = accuracy_score(y_true_severity, y_pred_severity)
    
    # Per-class metrics (macro average treats all classes equally)
    metrics['precision_macro'] = precision_score(
        y_true_severity, y_pred_severity, average='macro', zero_division=0
    )
    metrics['recall_macro'] = recall_score(
        y_true_severity, y_pred_severity, average='macro', zero_division=0
    )
    metrics['f1_macro'] = f1_score(
        y_true_severity, y_pred_severity, average='macro', zero_division=0
    )
    
    # Weighted average (accounts for class imbalance)
    metrics['precision_weighted'] = precision_score(
        y_true_severity, y_pred_severity, average='weighted', zero_division=0
    )
    metrics['recall_weighted'] = recall_score(
        y_true_severity, y_pred_severity, average='weighted', zero_division=0
    )
    metrics['f1_weighted'] = f1_score(
        y_true_severity, y_pred_severity, average='weighted', zero_division=0
    )
    
    # Confusion matrix
    metrics['confusion_matrix'] = confusion_matrix(y_true_severity, y_pred_severity)
    
    # Detailed report
    report = classification_report(
        y_true_severity,
        y_pred_severity,
        target_names=severity_levels,
        output_dict=True,
        zero_division=0
    )
    metrics['classification_report'] = report
    
    logger.info("Severity Classification Metrics:")
    logger.info(f"  Accuracy: {metrics['accuracy']:.4f}")
    logger.info(f"  F1 (macro): {metrics['f1_macro']:.4f}")
    logger.info(f"  F1 (weighted): {metrics['f1_weighted']:.4f}")
    
    return metrics


# ==============================================================================
# Performance Metrics
# ==============================================================================


def calculate_performance_metrics(
    inference_times: List[float],
    memory_usage: Dict[str, float],
    batch_size: int = 4
) -> Dict[str, float]:
    """
    Calculate system performance metrics.
    
    Args:
        inference_times: List of inference times in milliseconds
        memory_usage: Dictionary with VRAM usage stats
        batch_size: Number of images per batch
    
    Returns:
        Dictionary with performance metrics:
        - mean_latency_ms: Average inference time
        - std_latency_ms: Standard deviation of latency
        - min_latency_ms: Fastest inference
        - max_latency_ms: Slowest inference
        - throughput_hz: Images processed per second
        - throughput_fps: Frames per second (same as Hz)
        - meets_latency_requirement: True if <100ms
        - memory_usage_gb: Peak VRAM usage
    
    Example:
        >>> times = [78.5, 82.1, 79.3, 81.7, 80.2]  # milliseconds
        >>> memory = {'peak_vram_gb': 4.2}
        >>> metrics = calculate_performance_metrics(times, memory, batch_size=4)
        >>> print(f"Average latency: {metrics['mean_latency_ms']:.1f} ms")
        >>> print(f"Throughput: {metrics['throughput_hz']:.1f} Hz")
    """
    metrics = {}
    
    # Latency statistics
    inference_times = np.array(inference_times)
    metrics['mean_latency_ms'] = float(np.mean(inference_times))
    metrics['std_latency_ms'] = float(np.std(inference_times))
    metrics['min_latency_ms'] = float(np.min(inference_times))
    metrics['max_latency_ms'] = float(np.max(inference_times))
    metrics['median_latency_ms'] = float(np.median(inference_times))
    
    # Percentiles (useful for understanding distribution)
    metrics['p95_latency_ms'] = float(np.percentile(inference_times, 95))
    metrics['p99_latency_ms'] = float(np.percentile(inference_times, 99))
    
    # Throughput (images per second)
    # If batch_size=4 and latency=80ms, throughput = 4/(0.080s) = 50 images/sec
    mean_latency_sec = metrics['mean_latency_ms'] / 1000.0
    metrics['throughput_hz'] = batch_size / mean_latency_sec if mean_latency_sec > 0 else 0
    metrics['throughput_fps'] = metrics['throughput_hz']  # Same thing, different name
    
    # Check if meets real-time requirement (≤100ms for 4-camera batch, ≥10Hz)
    metrics['meets_latency_requirement'] = metrics['mean_latency_ms'] <= 100.0
    metrics['meets_throughput_requirement'] = metrics['throughput_hz'] >= 10.0
    
    # Memory usage
    if memory_usage:
        metrics.update(memory_usage)
    
    logger.info("Performance Metrics:")
    logger.info(f"  Mean Latency: {metrics['mean_latency_ms']:.2f} ms (±{metrics['std_latency_ms']:.2f})")
    logger.info(f"  P95 Latency: {metrics['p95_latency_ms']:.2f} ms")
    logger.info(f"  Throughput: {metrics['throughput_hz']:.1f} Hz ({batch_size} cameras)")
    logger.info(f"  Latency OK: {metrics['meets_latency_requirement']} (<100ms target)")
    logger.info(f"  Throughput OK: {metrics['meets_throughput_requirement']} (≥10Hz target)")
    
    if 'peak_vram_gb' in metrics:
        logger.info(f"  Peak VRAM: {metrics['peak_vram_gb']:.2f} GB")
    
    return metrics


# ==============================================================================
# Architecture Comparison
# ==============================================================================


def compare_model_performance(
    model_a_metrics: Dict[str, float],
    model_b_metrics: Dict[str, float],
    model_a_name: str = "Architecture A",
    model_b_name: str = "Architecture B"
) -> Dict[str, any]:
    """
    Compare two models and determine which is better.
    
    Comparison criteria from requirements.md:
    1. If accuracy difference ≥3%: Choose more accurate model
    2. Else if VRAM difference ≥25%: Choose more memory-efficient model
    3. Else: Choose model with lower latency
    
    Args:
        model_a_metrics: Metrics for Architecture A (LiteFlowNet2)
        model_b_metrics: Metrics for Architecture B (SpyNet)
        model_a_name: Display name for model A
        model_b_name: Display name for model B
    
    Returns:
        Dictionary with comparison results and recommendation
    
    Example:
        >>> arch_a = {'accuracy': 0.96, 'inference_vram_gb': 4.2, 'mean_latency_ms': 80}
        >>> arch_b = {'accuracy': 0.95, 'inference_vram_gb': 3.1, 'mean_latency_ms': 60}
        >>> comparison = compare_model_performance(arch_a, arch_b)
        >>> print(comparison['recommendation'])  # "Architecture A" or "Architecture B"
        >>> print(comparison['reason'])
    """
    comparison = {
        'model_a_name': model_a_name,
        'model_b_name': model_b_name,
        'model_a_metrics': model_a_metrics,
        'model_b_metrics': model_b_metrics
    }
    
    # Extract key metrics
    acc_a = model_a_metrics.get('accuracy', 0)
    acc_b = model_b_metrics.get('accuracy', 0)
    
    vram_a = model_a_metrics.get('inference_vram_gb', 0)
    vram_b = model_b_metrics.get('inference_vram_gb', 0)
    
    latency_a = model_a_metrics.get('mean_latency_ms', float('inf'))
    latency_b = model_b_metrics.get('mean_latency_ms', float('inf'))
    
    # Calculate differences
    acc_diff = abs(acc_a - acc_b)
    vram_diff_pct = abs(vram_a - vram_b) / max(vram_a, vram_b) if max(vram_a, vram_b) > 0 else 0
    latency_diff = abs(latency_a - latency_b)
    
    comparison['accuracy_difference'] = acc_diff
    comparison['vram_difference_percent'] = vram_diff_pct * 100
    comparison['latency_difference_ms'] = latency_diff
    
    # Decision logic (from requirements.md Requirement 25)
    if acc_diff >= 0.03:  # 3% accuracy difference
        # Choose more accurate model
        if acc_a > acc_b:
            comparison['recommendation'] = model_a_name
            comparison['reason'] = (
                f"Accuracy advantage: {model_a_name} achieves {acc_a:.1%} vs "
                f"{model_b_name} {acc_b:.1%} (difference: {acc_diff:.1%} ≥ 3%)"
            )
        else:
            comparison['recommendation'] = model_b_name
            comparison['reason'] = (
                f"Accuracy advantage: {model_b_name} achieves {acc_b:.1%} vs "
                f"{model_a_name} {acc_a:.1%} (difference: {acc_diff:.1%} ≥ 3%)"
            )
    
    elif vram_diff_pct >= 0.25:  # 25% VRAM difference
        # Choose more memory-efficient model
        if vram_a < vram_b:
            comparison['recommendation'] = model_a_name
            comparison['reason'] = (
                f"Memory efficiency: {model_a_name} uses {vram_a:.1f} GB vs "
                f"{model_b_name} {vram_b:.1f} GB (difference: {vram_diff_pct*100:.1f}% ≥ 25%)"
            )
        else:
            comparison['recommendation'] = model_b_name
            comparison['reason'] = (
                f"Memory efficiency: {model_b_name} uses {vram_b:.1f} GB vs "
                f"{model_a_name} {vram_a:.1f} GB (difference: {vram_diff_pct*100:.1f}% ≥ 25%)"
            )
    
    else:
        # Choose model with lower latency
        if latency_a < latency_b:
            comparison['recommendation'] = model_a_name
            comparison['reason'] = (
                f"Lower latency: {model_a_name} {latency_a:.1f} ms vs "
                f"{model_b_name} {latency_b:.1f} ms (difference: {latency_diff:.1f} ms)"
            )
        else:
            comparison['recommendation'] = model_b_name
            comparison['reason'] = (
                f"Lower latency: {model_b_name} {latency_b:.1f} ms vs "
                f"{model_a_name} {latency_a:.1f} ms (difference: {latency_diff:.1f} ms)"
            )
    
    # Log recommendation
    logger.info("=" * 60)
    logger.info("Architecture Comparison Results")
    logger.info("=" * 60)
    logger.info(f"Recommendation: {comparison['recommendation']}")
    logger.info(f"Reason: {comparison['reason']}")
    logger.info("")
    logger.info("Detailed Comparison:")
    logger.info(f"  Accuracy: {model_a_name}={acc_a:.1%}, {model_b_name}={acc_b:.1%} (diff={acc_diff:.1%})")
    logger.info(f"  VRAM: {model_a_name}={vram_a:.1f}GB, {model_b_name}={vram_b:.1f}GB (diff={vram_diff_pct*100:.1f}%)")
    logger.info(f"  Latency: {model_a_name}={latency_a:.1f}ms, {model_b_name}={latency_b:.1f}ms (diff={latency_diff:.1f}ms)")
    logger.info("=" * 60)
    
    return comparison


def main():
    """
    Demo metrics calculation with example data.
    
    Run with: python -m dl_misalignment.utils.metrics
    """
    print("=" * 60)
    print("Metrics Calculation Demo")
    print("=" * 60)
    
    # Example data
    y_true = np.array([0, 1, 0, 1, 1, 0, 1, 0, 1, 1])
    y_pred = np.array([0, 1, 1, 1, 0, 0, 1, 0, 1, 1])
    y_prob = np.array([0.1, 0.9, 0.6, 0.85, 0.4, 0.2, 0.95, 0.15, 0.88, 0.92])
    
    # Calculate metrics
    metrics = calculate_classification_metrics(y_true, y_pred, y_prob)
    
    print("\n✓ Metrics calculation demo complete!")
    print("See output above for detailed metrics")


if __name__ == "__main__":
    main()
