"""
Visualization Utilities for Deep Learning Misalignment Detection

This module provides comprehensive visualization tools for understanding:
1. Dataset distribution and augmentation effects
2. CNN architecture and feature maps
3. Optical flow fields and quality
4. Training metrics and model performance
5. Architecture comparison charts

All visualizations are designed to be:
- Notebook-friendly (Jupyter/IPython display)
- Saveable as high-quality images
- Dashboard-ready (can be embedded in UI later)
- Educational (helps understand what CNNs are learning)

For developers new to deep learning:
- Visualizations show what the network "sees" at each layer
- Helps debug when things go wrong
- Makes abstract concepts concrete and understandable
"""

import logging
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Union
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.gridspec import GridSpec
import seaborn as sns

# Try to import torch (might not be installed yet)
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None

logger = logging.getLogger(__name__)

# Set style for all plots
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10


# ==============================================================================
# Data Visualization
# ==============================================================================


def visualize_dataset_split(
    train_count: int,
    val_count: int,
    test_count: int,
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Visualize the train/validation/test split as a pie chart.
    
    This helps verify that the 70/15/15 split is correct and visually
    shows the distribution of data across splits.
    
    Args:
        train_count: Number of training samples
        val_count: Number of validation samples
        test_count: Number of test samples
        save_path: Optional path to save the figure
    
    Returns:
        matplotlib Figure object
    
    Example:
        >>> fig = visualize_dataset_split(7000, 1500, 1500)
        >>> plt.show()  # Display in notebook
        >>> # or save_path="reports/data_split.png" to save
    """
    total = train_count + val_count + test_count
    percentages = [
        (train_count / total) * 100,
        (val_count / total) * 100,
        (test_count / total) * 100
    ]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Pie chart
    colors = ['#3498db', '#e74c3c', '#2ecc71']
    labels = [
        f'Train\n{train_count:,} samples\n({percentages[0]:.1f}%)',
        f'Validation\n{val_count:,} samples\n({percentages[1]:.1f}%)',
        f'Test\n{test_count:,} samples\n({percentages[2]:.1f}%)'
    ]
    
    ax1.pie(
        [train_count, val_count, test_count],
        labels=labels,
        colors=colors,
        autopct='',
        startangle=90,
        textprops={'fontsize': 11, 'weight': 'bold'}
    )
    ax1.set_title('Dataset Split Distribution', fontsize=14, weight='bold', pad=20)
    
    # Bar chart
    splits = ['Train', 'Validation', 'Test']
    counts = [train_count, val_count, test_count]
    bars = ax2.bar(splits, counts, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    
    # Add count labels on bars
    for bar, count, pct in zip(bars, counts, percentages):
        height = bar.get_height()
        ax2.text(
            bar.get_x() + bar.get_width() / 2.,
            height,
            f'{count:,}\n({pct:.1f}%)',
            ha='center',
            va='bottom',
            fontsize=11,
            weight='bold'
        )
    
    ax2.set_ylabel('Number of Samples', fontsize=12, weight='bold')
    ax2.set_title('Sample Counts by Split', fontsize=14, weight='bold', pad=20)
    ax2.set_ylim(0, max(counts) * 1.15)
    ax2.grid(axis='y', alpha=0.3)
    
    # Overall title
    fig.suptitle(
        f'KITTI Dataset Split: {total:,} Total Samples',
        fontsize=16,
        weight='bold',
        y=0.98
    )
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Dataset split visualization saved to {save_path}")
    
    return fig


def visualize_sample_grid(
    images: Union[np.ndarray, torch.Tensor],
    labels: Optional[List[str]] = None,
    titles: Optional[List[str]] = None,
    rows: int = 2,
    cols: int = 4,
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Display a grid of sample images from the dataset.
    
    This is useful for:
    - Checking that images loaded correctly
    - Visualizing augmentation effects
    - Understanding what the network will see as input
    
    Args:
        images: Batch of images [N, C, H, W] or [N, H, W, C]
        labels: Optional labels for each image (e.g., "aligned", "misaligned")
        titles: Optional titles for each subplot
        rows: Number of rows in grid
        cols: Number of columns in grid
        save_path: Optional path to save the figure
    
    Returns:
        matplotlib Figure object
    
    Example:
        >>> # Show 8 random samples
        >>> sample_images = dataset[0:8]  # Get 8 images
        >>> fig = visualize_sample_grid(sample_images, rows=2, cols=4)
        >>> plt.show()
    """
    # Convert torch tensor to numpy if needed
    if TORCH_AVAILABLE and isinstance(images, torch.Tensor):
        images = images.cpu().numpy()
    
    # Handle different input formats
    if images.ndim == 4:
        if images.shape[1] in [1, 3]:  # [N, C, H, W] format
            images = np.transpose(images, (0, 2, 3, 1))  # Convert to [N, H, W, C]
    
    n_images = min(len(images), rows * cols)
    
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3, rows * 3))
    axes = axes.flatten() if rows * cols > 1 else [axes]
    
    for idx in range(n_images):
        img = images[idx]
        
        # Normalize to [0, 1] if needed
        if img.max() > 1.0:
            img = img / 255.0
        
        # Handle grayscale
        if img.shape[-1] == 1:
            img = img.squeeze()
            axes[idx].imshow(img, cmap='gray')
        else:
            axes[idx].imshow(img)
        
        # Add title
        title_parts = []
        if titles and idx < len(titles):
            title_parts.append(titles[idx])
        if labels and idx < len(labels):
            title_parts.append(f"[{labels[idx]}]")
        
        if title_parts:
            axes[idx].set_title(' '.join(title_parts), fontsize=10)
        
        axes[idx].axis('off')
    
    # Hide unused subplots
    for idx in range(n_images, len(axes)):
        axes[idx].axis('off')
    
    plt.suptitle('Dataset Samples', fontsize=14, weight='bold', y=0.98)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Sample grid saved to {save_path}")
    
    return fig


def visualize_augmentation_comparison(
    original_images: Union[np.ndarray, torch.Tensor],
    augmented_images: Union[np.ndarray, torch.Tensor],
    augmentation_params: Optional[List[Dict]] = None,
    n_samples: int = 4,
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Show before/after comparison of data augmentation.
    
    This helps understand what transformations are being applied and
    ensures augmentation is working correctly without being too aggressive.
    
    Args:
        original_images: Original images before augmentation
        augmented_images: Same images after augmentation
        augmentation_params: Optional list of augmentation parameters used
        n_samples: Number of image pairs to show
        save_path: Optional path to save the figure
    
    Returns:
        matplotlib Figure object
    
    Example:
        >>> original = dataset.get_raw_images(indices=[0, 1, 2, 3])
        >>> augmented = dataset.get_augmented_images(indices=[0, 1, 2, 3])
        >>> fig = visualize_augmentation_comparison(original, augmented)
        >>> plt.show()
    """
    # Convert torch tensors if needed
    if TORCH_AVAILABLE and isinstance(original_images, torch.Tensor):
        original_images = original_images.cpu().numpy()
        augmented_images = augmented_images.cpu().numpy()
    
    # Handle channel-first format [N, C, H, W] -> [N, H, W, C]
    if original_images.shape[1] in [1, 3]:
        original_images = np.transpose(original_images, (0, 2, 3, 1))
        augmented_images = np.transpose(augmented_images, (0, 2, 3, 1))
    
    n_samples = min(n_samples, len(original_images))
    
    fig, axes = plt.subplots(n_samples, 2, figsize=(10, n_samples * 3))
    if n_samples == 1:
        axes = axes.reshape(1, -1)
    
    for idx in range(n_samples):
        # Original image
        orig = original_images[idx]
        if orig.max() > 1.0:
            orig = orig / 255.0
        
        axes[idx, 0].imshow(orig if orig.shape[-1] == 3 else orig.squeeze(), 
                           cmap=None if orig.shape[-1] == 3 else 'gray')
        axes[idx, 0].set_title('Original', fontsize=11, weight='bold')
        axes[idx, 0].axis('off')
        
        # Augmented image
        aug = augmented_images[idx]
        if aug.max() > 1.0:
            aug = aug / 255.0
        
        axes[idx, 1].imshow(aug if aug.shape[-1] == 3 else aug.squeeze(),
                           cmap=None if aug.shape[-1] == 3 else 'gray')
        
        # Add augmentation params to title if available
        title = 'Augmented'
        if augmentation_params and idx < len(augmentation_params):
            params = augmentation_params[idx]
            param_str = ', '.join([f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}" 
                                   for k, v in params.items()])
            title += f"\n({param_str})"
        
        axes[idx, 1].set_title(title, fontsize=11, weight='bold')
        axes[idx, 1].axis('off')
    
    plt.suptitle('Data Augmentation: Before & After', fontsize=14, weight='bold', y=0.995)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Augmentation comparison saved to {save_path}")
    
    return fig


def plot_data_distribution(
    labels: np.ndarray,
    class_names: List[str] = None,
    split_name: str = "Dataset",
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Plot the distribution of classes in the dataset.
    
    For binary classification (aligned vs misaligned), this shows class balance.
    Important to check for class imbalance which can bias the model.
    
    Args:
        labels: Array of labels (0 = aligned, 1 = misaligned)
        class_names: Names for each class (default: ["Aligned", "Misaligned"])
        split_name: Name of the split (e.g., "Training", "Validation")
        save_path: Optional path to save the figure
    
    Returns:
        matplotlib Figure object
    
    Example:
        >>> train_labels = np.array([0, 1, 1, 0, 1, ...])  # 0=aligned, 1=misaligned
        >>> fig = plot_data_distribution(train_labels, split_name="Training")
        >>> plt.show()
    """
    if class_names is None:
        class_names = ["Aligned", "Misaligned"]
    
    unique, counts = np.unique(labels, return_counts=True)
    percentages = (counts / counts.sum()) * 100
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Bar chart
    colors = ['#2ecc71', '#e74c3c']  # Green for aligned, red for misaligned
    bars = ax1.bar(range(len(unique)), counts, color=colors, alpha=0.8, 
                   edgecolor='black', linewidth=1.5)
    
    # Add count and percentage labels
    for bar, count, pct in zip(bars, counts, percentages):
        height = bar.get_height()
        ax1.text(
            bar.get_x() + bar.get_width() / 2.,
            height,
            f'{count:,}\n({pct:.1f}%)',
            ha='center',
            va='bottom',
            fontsize=11,
            weight='bold'
        )
    
    ax1.set_xticks(range(len(unique)))
    ax1.set_xticklabels([class_names[i] for i in unique], fontsize=11)
    ax1.set_ylabel('Number of Samples', fontsize=12, weight='bold')
    ax1.set_title(f'{split_name} Class Distribution', fontsize=13, weight='bold')
    ax1.grid(axis='y', alpha=0.3)
    
    # Pie chart
    ax2.pie(
        counts,
        labels=[f'{class_names[i]}\n{counts[i]:,} ({percentages[i]:.1f}%)' 
                for i in range(len(unique))],
        colors=colors,
        autopct='',
        startangle=90,
        textprops={'fontsize': 11, 'weight': 'bold'}
    )
    ax2.set_title(f'{split_name} Class Balance', fontsize=13, weight='bold')
    
    # Overall title with balance warning
    balance_ratio = min(counts) / max(counts)
    if balance_ratio < 0.7:
        warning = f"\n⚠️ Class imbalance detected (ratio: {balance_ratio:.2f})"
        fig.suptitle(
            f'{split_name} Label Distribution{warning}',
            fontsize=14,
            weight='bold',
            y=0.98
        )
    else:
        fig.suptitle(
            f'{split_name} Label Distribution - Well Balanced',
            fontsize=14,
            weight='bold',
            y=0.98
        )
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Data distribution plot saved to {save_path}")
    
    return fig


# ==============================================================================
# CNN Architecture Visualization
# ==============================================================================


def visualize_cnn_architecture(
    model,
    input_size: Tuple[int, int] = (640, 640),
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Visualize the CNN Feature Extractor architecture showing all layers.
    
    This creates a diagram showing:
    - Input dimensions
    - Each convolutional layer with kernel sizes
    - Feature map dimensions at each level
    - Pooling operations
    - Output pyramid levels
    
    Helps understand how the 4-level pyramid processes images from
    640×640 down to 80×80 (1/8 scale) with increasing channels.
    
    Args:
        model: CNN Feature Extractor model
        input_size: Input image size (H, W)
        save_path: Optional path to save the figure
    
    Returns:
        matplotlib Figure object
    
    Example:
        >>> from dl_misalignment.models import CNNFeatureExtractor
        >>> model = CNNFeatureExtractor()
        >>> fig = visualize_cnn_architecture(model, input_size=(640, 640))
        >>> plt.show()
    """
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.axis('off')
    
    # Define architecture structure (will be populated by reading model)
    # For now, use the known structure from design.md
    layers = [
        {"name": "Input", "channels": 3, "size": input_size, "type": "input"},
        {"name": "Conv1_1", "channels": 64, "size": input_size, "kernel": "3×3", "type": "conv"},
        {"name": "Conv1_2", "channels": 64, "size": input_size, "kernel": "3×3", "type": "conv"},
        {"name": "Pool1", "channels": 64, "size": (input_size[0]//2, input_size[1]//2), "type": "pool"},
        {"name": "Conv2_1", "channels": 128, "size": (input_size[0]//2, input_size[1]//2), "kernel": "3×3", "type": "conv"},
        {"name": "Conv2_2", "channels": 128, "size": (input_size[0]//2, input_size[1]//2), "kernel": "3×3", "type": "conv"},
        {"name": "Pool2", "channels": 128, "size": (input_size[0]//4, input_size[1]//4), "type": "pool"},
        {"name": "Conv3_1", "channels": 256, "size": (input_size[0]//4, input_size[1]//4), "kernel": "3×3", "type": "conv"},
        {"name": "Conv3_2", "channels": 256, "size": (input_size[0]//4, input_size[1]//4), "kernel": "3×3", "type": "conv"},
        {"name": "Conv3_3", "channels": 256, "size": (input_size[0]//4, input_size[1]//4), "kernel": "3×3", "type": "conv"},
        {"name": "Pool3", "channels": 256, "size": (input_size[0]//8, input_size[1]//8), "type": "pool"},
        {"name": "Conv4_1", "channels": 512, "size": (input_size[0]//8, input_size[1]//8), "kernel": "3×3", "type": "conv"},
        {"name": "Conv4_2", "channels": 512, "size": (input_size[0]//8, input_size[1]//8), "kernel": "3×3", "type": "conv"},
        {"name": "Conv4_3", "channels": 512, "size": (input_size[0]//8, input_size[1]//8), "kernel": "3×3", "type": "conv"},
    ]
    
    # Colors for different layer types
    colors = {
        "input": "#3498db",
        "conv": "#2ecc71",
        "pool": "#e74c3c",
        "output": "#9b59b6"
    }
    
    # Draw layers
    y_pos = 0.9
    x_spacing = 0.06
    box_width = 0.08
    box_height = 0.08
    
    for idx, layer in enumerate(layers):
        x_pos = 0.1 + idx * x_spacing
        
        # Draw box
        color = colors.get(layer["type"], "#95a5a6")
        rect = patches.FancyBboxPatch(
            (x_pos, y_pos - box_height/2),
            box_width,
            box_height,
            boxstyle="round,pad=0.01",
            linewidth=2,
            edgecolor='black',
            facecolor=color,
            alpha=0.7,
            transform=ax.transAxes
        )
        ax.add_patch(rect)
        
        # Add text
        text_y = y_pos + box_height/2 + 0.02
        ax.text(
            x_pos + box_width/2,
            text_y,
            layer["name"],
            ha='center',
            va='bottom',
            fontsize=8,
            weight='bold',
            transform=ax.transAxes
        )
        
        # Add dimensions
        dim_text = f"{layer['channels']}×{layer['size'][0]}×{layer['size'][1]}"
        if "kernel" in layer:
            dim_text += f"\n{layer['kernel']}"
        
        ax.text(
            x_pos + box_width/2,
            y_pos,
            dim_text,
            ha='center',
            va='center',
            fontsize=7,
            transform=ax.transAxes
        )
        
        # Draw arrow to next layer
        if idx < len(layers) - 1:
            arrow = patches.FancyArrowPatch(
                (x_pos + box_width, y_pos),
                (x_pos + box_width + x_spacing, y_pos),
                arrowstyle='->',
                linewidth=2,
                color='black',
                transform=ax.transAxes
            )
            ax.add_patch(arrow)
    
    # Add pyramid level markers
    pyramid_levels = [
        (2, "Level 0 (1×)"),
        (5, "Level 1 (1/2×)"),
        (9, "Level 2 (1/4×)"),
        (13, "Level 3 (1/8×)")
    ]
    
    for layer_idx, level_name in pyramid_levels:
        x_pos = 0.1 + layer_idx * x_spacing + box_width/2
        ax.text(
            x_pos,
            0.15,
            level_name,
            ha='center',
            va='center',
            fontsize=10,
            weight='bold',
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.3),
            transform=ax.transAxes
        )
    
    # Title
    ax.text(
        0.5,
        0.95,
        'CNN Feature Extractor Architecture (4-Level Pyramid)',
        ha='center',
        va='top',
        fontsize=16,
        weight='bold',
        transform=ax.transAxes
    )
    
    # Legend
    legend_elements = [
        patches.Patch(facecolor=colors["input"], label='Input'),
        patches.Patch(facecolor=colors["conv"], label='Convolution'),
        patches.Patch(facecolor=colors["pool"], label='Max Pooling'),
    ]
    ax.legend(handles=legend_elements, loc='lower left', fontsize=10)
    
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"CNN architecture visualization saved to {save_path}")
    
    return fig


# ==============================================================================
# More visualization functions continued in next part...
# ==============================================================================


def main():
    """
    Demo visualization functions with example data.
    
    Run with: python -m dl_misalignment.utils.visualization
    """
    print("=" * 80)
    print("Visualization Demo")
    print("=" * 80)
    
    # Demo 1: Dataset split
    print("\n1. Dataset Split Visualization")
    fig1 = visualize_dataset_split(7000, 1500, 1500)
    plt.show()
    
    # Demo 2: Data distribution
    print("\n2. Data Distribution (example with imbalanced data)")
    labels = np.array([0] * 6000 + [1] * 4000)  # Imbalanced example
    fig2 = plot_data_distribution(labels, split_name="Training")
    plt.show()
    
    print("\n✓ Visualization demo complete!")
    print("See TASK_COMPLETION_LOG.md for more examples")


if __name__ == "__main__":
    main()
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Plot 1: Dataset split distribution (pie chart)
    split_data = {
        'Train (70%)': dataset_info.get('train_count', 0),
        'Validation (15%)': dataset_info.get('val_count', 0),
        'Test (15%)': dataset_info.get('test_count', 0)
    }
    
    colors = ['#4CAF50', '#2196F3', '#FF9800']
    axes[0].pie(
        split_data.values(),
        labels=split_data.keys(),
        autopct='%1.1f%%',
        colors=colors,
        startangle=90
    )
    axes[0].set_title('Dataset Split Distribution\n(Target: 70/15/15)', fontsize=12, fontweight='bold')
    
    # Plot 2: Resolution distribution (histogram)
    if 'resolutions' in dataset_info and dataset_info['resolutions']:
        resolutions = dataset_info['resolutions']
        widths = [w for h, w in resolutions]
        heights = [h for h, w in resolutions]
        
        axes[1].hist2d(widths, heights, bins=20, cmap='YlOrRd')
        axes[1].axhline(y=750, color='r', linestyle='--', linewidth=2, label='750px limit')
        axes[1].axvline(x=750, color='r', linestyle='--', linewidth=2)
        axes[1].set_xlabel('Width (pixels)', fontsize=10)
        axes[1].set_ylabel('Height (pixels)', fontsize=10)
        axes[1].set_title('Image Resolution Distribution\n(Red line = 750×750 max)', fontsize=12, fontweight='bold')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Dataset statistics saved to {save_path}")
    
    if show:
        plt.show()
    else:
        plt.close()


def plot_sample_images(
    images: List[np.ndarray],
    titles: Optional[List[str]] = None,
    save_path: Optional[str] = None,
    show: bool = True
) -> None:
    """
    Display sample images in a grid.
    
    Args:
        images: List of images (H, W, 3) RGB
        titles: Optional titles
        save_path: Save location
        show: Display plot
    """
    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    axes = axes.flatten()
    
    for idx, (ax, img) in enumerate(zip(axes, images[:8])):
        ax.imshow(img)
        ax.axis('off')
        if titles and idx < len(titles):
            ax.set_title(titles[idx], fontsize=10)
    
    plt.suptitle('Dataset Samples', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    if show:
        plt.show()
    else:
        plt.close()


# Placeholder for network architecture visualization
# Will be implemented with actual network modules
def visualize_network_architecture(model, input_shape=(3, 640, 640)):
    """Visualize CNN architecture - to be implemented with torch"""
    logger.info("Network visualization will be available after model implementation")
    pass



# ==============================================================================
# Optical Flow Visualization
# ==============================================================================


def visualize_optical_flow(
    flow: Union[np.ndarray, torch.Tensor],
    image: Optional[Union[np.ndarray, torch.Tensor]] = None,
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Visualize optical flow field as color-coded arrows.
    
    Optical flow represents motion between two consecutive frames.
    Each pixel has a 2D vector (u, v) indicating where it moved.
    
    Visualization uses HSV color space:
    - Hue (color) = direction of motion
    - Saturation = magnitude of motion (brighter = faster)
    - Value = fixed at maximum
    
    Args:
        flow: Optical flow field [2, H, W] or [H, W, 2] (u, v components)
        image: Optional background image to overlay flow on
        save_path: Optional path to save the figure
    
    Returns:
        matplotlib Figure object
    
    Example:
        >>> flow = model.compute_optical_flow(frame1, frame2)
        >>> fig = visualize_optical_flow(flow, image=frame1)
        >>> plt.show()
    """
    # Convert torch tensor if needed
    if TORCH_AVAILABLE and isinstance(flow, torch.Tensor):
        flow = flow.cpu().numpy()
    
    # Handle different input formats
    if flow.shape[0] == 2:  # [2, H, W] format
        flow = np.transpose(flow, (1, 2, 0))  # Convert to [H, W, 2]
    
    h, w = flow.shape[:2]
    
    # Compute flow magnitude and angle
    u = flow[:, :, 0]  # Horizontal component
    v = flow[:, :, 1]  # Vertical component
    magnitude = np.sqrt(u**2 + v**2)
    angle = np.arctan2(v, u)
    
    # Create HSV image
    # Hue = angle (direction), Saturation = magnitude (speed), Value = 1
    hsv = np.zeros((h, w, 3), dtype=np.uint8)
    hsv[:, :, 0] = ((angle + np.pi) / (2 * np.pi) * 179).astype(np.uint8)  # Hue (0-179)
    hsv[:, :, 1] = np.clip(magnitude / magnitude.max() * 255, 0, 255).astype(np.uint8)  # Saturation
    hsv[:, :, 2] = 255  # Value (brightness)
    
    # Convert HSV to RGB
    import cv2
    flow_rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    
    # Create figure
    if image is not None:
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))
        
        # Original image
        if TORCH_AVAILABLE and isinstance(image, torch.Tensor):
            image = image.cpu().numpy()
        if image.shape[0] in [1, 3]:  # [C, H, W]
            image = np.transpose(image, (1, 2, 0))
        if image.max() > 1.0:
            image = image / 255.0
        
        ax1.imshow(image if image.shape[-1] == 3 else image.squeeze(), cmap='gray' if image.shape[-1] != 3 else None)
        ax1.set_title('Input Image', fontsize=12, weight='bold')
        ax1.axis('off')
        
        # Flow visualization
        ax2.imshow(flow_rgb)
        ax2.set_title('Optical Flow (Color = Direction, Brightness = Speed)', fontsize=12, weight='bold')
        ax2.axis('off')
        
        # Flow magnitude
        mag_plot = ax3.imshow(magnitude, cmap='hot')
        ax3.set_title('Flow Magnitude (Speed)', fontsize=12, weight='bold')
        ax3.axis('off')
        plt.colorbar(mag_plot, ax=ax3, fraction=0.046, pad=0.04)
        
    else:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Flow visualization
        ax1.imshow(flow_rgb)
        ax1.set_title('Optical Flow (Color = Direction, Brightness = Speed)', fontsize=12, weight='bold')
        ax1.axis('off')
        
        # Flow magnitude
        mag_plot = ax2.imshow(magnitude, cmap='hot')
        ax2.set_title('Flow Magnitude (Speed)', fontsize=12, weight='bold')
        ax2.axis('off')
        plt.colorbar(mag_plot, ax=ax2, fraction=0.046, pad=0.04)
    
    plt.suptitle('Optical Flow Visualization', fontsize=14, weight='bold')
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Optical flow visualization saved to {save_path}")
    
    return fig


def visualize_feature_maps(
    feature_maps: Union[np.ndarray, torch.Tensor],
    layer_name: str = "Feature Maps",
    n_features: int = 16,
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Visualize feature maps from a CNN layer.
    
    Feature maps show what patterns the network detects at each layer.
    Early layers detect edges and simple patterns.
    Deeper layers detect complex shapes and object parts.
    
    This helps understand what the CNN is "learning" and debugging
    if something goes wrong.
    
    Args:
        feature_maps: Feature tensor [C, H, W] or [B, C, H, W]
        layer_name: Name of the layer for the title
        n_features: Number of feature maps to display
        save_path: Optional path to save the figure
    
    Returns:
        matplotlib Figure object
    
    Example:
        >>> # Get feature maps from CNN layer
        >>> features = model.extract_features(image)
        >>> fig = visualize_feature_maps(features[0], layer_name="Conv1_1")
        >>> plt.show()
    """
    # Convert torch tensor if needed
    if TORCH_AVAILABLE and isinstance(feature_maps, torch.Tensor):
        feature_maps = feature_maps.detach().cpu().numpy()
    
    # Handle batch dimension
    if feature_maps.ndim == 4:
        feature_maps = feature_maps[0]  # Take first image in batch
    
    n_channels = feature_maps.shape[0]
    n_features = min(n_features, n_channels)
    
    # Determine grid size
    cols = 4
    rows = (n_features + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(12, rows * 3))
    axes = axes.flatten() if rows * cols > 1 else [axes]
    
    for idx in range(n_features):
        feature_map = feature_maps[idx]
        
        # Normalize to [0, 1] for display
        feature_map = (feature_map - feature_map.min()) / (feature_map.max() - feature_map.min() + 1e-8)
        
        axes[idx].imshow(feature_map, cmap='viridis')
        axes[idx].set_title(f'Channel {idx}', fontsize=10)
        axes[idx].axis('off')
    
    # Hide unused subplots
    for idx in range(n_features, len(axes)):
        axes[idx].axis('off')
    
    plt.suptitle(f'{layer_name} - Feature Maps ({n_channels} total channels)', 
                 fontsize=14, weight='bold')
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Feature maps visualization saved to {save_path}")
    
    return fig



# ==============================================================================
# Training Metrics Visualization
# ==============================================================================


def plot_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: List[str] = None,
    normalize: bool = False,
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Plot confusion matrix for binary classification.
    
    Confusion Matrix shows:
    - True Positives (TP): Correctly predicted misaligned
    - True Negatives (TN): Correctly predicted aligned
    - False Positives (FP): Incorrectly predicted misaligned (Type I error)
    - False Negatives (FN): Incorrectly predicted aligned (Type II error)
    
    This is crucial for understanding model errors:
    - High FP = too many false alarms
    - High FN = missing real misalignments (dangerous!)
    
    Args:
        y_true: True labels (0 or 1)
        y_pred: Predicted labels (0 or 1)
        class_names: Names for classes (default: ["Aligned", "Misaligned"])
        normalize: If True, show percentages instead of counts
        save_path: Optional path to save the figure
    
    Returns:
        matplotlib Figure object
    
    Example:
        >>> y_true = np.array([0, 1, 0, 1, 1, 0])
        >>> y_pred = np.array([0, 1, 1, 1, 0, 0])
        >>> fig = plot_confusion_matrix(y_true, y_pred)
        >>> plt.show()
    """
    from sklearn.metrics import confusion_matrix
    
    if class_names is None:
        class_names = ["Aligned", "Misaligned"]
    
    # Compute confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        fmt = '.2%'
        title_suffix = '(Normalized)'
    else:
        fmt = 'd'
        title_suffix = '(Counts)'
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Plot heatmap
    sns.heatmap(
        cm,
        annot=True,
        fmt=fmt,
        cmap='Blues',
        square=True,
        cbar_kws={'label': 'Percentage' if normalize else 'Count'},
        xticklabels=class_names,
        yticklabels=class_names,
        ax=ax,
        annot_kws={'size': 14, 'weight': 'bold'}
    )
    
    # Labels
    ax.set_ylabel('True Label', fontsize=13, weight='bold')
    ax.set_xlabel('Predicted Label', fontsize=13, weight='bold')
    ax.set_title(f'Confusion Matrix {title_suffix}', fontsize=15, weight='bold', pad=20)
    
    # Add text annotations for interpretation
    if not normalize:
        tn, fp, fn, tp = cm.ravel()
        interpretation = (
            f"True Positives (TP): {tp} | True Negatives (TN): {tn}\n"
            f"False Positives (FP): {fp} | False Negatives (FN): {fn}"
        )
        ax.text(
            0.5, -0.15, interpretation,
            ha='center', va='top',
            fontsize=11, weight='bold',
            transform=ax.transAxes,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3)
        )
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Confusion matrix saved to {save_path}")
    
    return fig


def plot_metrics_report(
    metrics: Dict[str, float],
    model_name: str = "Model",
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Plot comprehensive metrics report.
    
    Displays all key metrics in an easy-to-read format:
    - Accuracy: Overall correctness (TP + TN) / Total
    - Precision: When model predicts misaligned, how often is it correct? TP / (TP + FP)
    - Recall: Of all actual misalignments, how many did we catch? TP / (TP + FN)
    - F1 Score: Harmonic mean of precision and recall (balance between them)
    - mAP: Mean Average Precision (for detection tasks)
    
    Args:
        metrics: Dictionary with metric names and values
        model_name: Name of the model for the title
        save_path: Optional path to save the figure
    
    Returns:
        matplotlib Figure object
    
    Example:
        >>> metrics = {
        ...     'accuracy': 0.95,
        ...     'precision': 0.93,
        ...     'recall': 0.96,
        ...     'f1_score': 0.945,
        ...     'mAP': 0.92
        ... }
        >>> fig = plot_metrics_report(metrics, model_name="LiteFlowNet2")
        >>> plt.show()
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Bar chart of metrics
    metric_names = list(metrics.keys())
    metric_values = list(metrics.values())
    
    colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(metric_names)))
    bars = ax1.barh(metric_names, metric_values, color=colors, edgecolor='black', linewidth=1.5)
    
    # Add value labels on bars
    for bar, value in zip(bars, metric_values):
        width = bar.get_width()
        ax1.text(
            width,
            bar.get_y() + bar.get_height() / 2,
            f'  {value:.3f}',
            ha='left',
            va='center',
            fontsize=12,
            weight='bold'
        )
    
    ax1.set_xlabel('Score', fontsize=13, weight='bold')
    ax1.set_title(f'{model_name} - Performance Metrics', fontsize=14, weight='bold')
    ax1.set_xlim(0, 1.05)
    ax1.grid(axis='x', alpha=0.3)
    ax1.axvline(x=0.95, color='red', linestyle='--', linewidth=2, alpha=0.5, label='Target (95%)')
    ax1.legend()
    
    # Radar chart
    angles = np.linspace(0, 2 * np.pi, len(metric_names), endpoint=False).tolist()
    values = metric_values + [metric_values[0]]  # Close the circle
    angles += angles[:1]
    
    ax2 = plt.subplot(122, projection='polar')
    ax2.plot(angles, values, 'o-', linewidth=2, color='#2ecc71')
    ax2.fill(angles, values, alpha=0.25, color='#2ecc71')
    ax2.set_xticks(angles[:-1])
    ax2.set_xticklabels(metric_names, size=11)
    ax2.set_ylim(0, 1)
    ax2.set_title(f'{model_name} - Performance Radar', fontsize=14, weight='bold', pad=20)
    ax2.grid(True)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Metrics report saved to {save_path}")
    
    return fig


def plot_training_history(
    history: Dict[str, List[float]],
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Plot training and validation loss/accuracy curves.
    
    Shows how the model improved during training:
    - Training loss should decrease over time
    - Validation loss should also decrease
    - If validation loss increases while training loss decreases: OVERFITTING!
    - Gap between training and validation: model memorizing vs generalizing
    
    Args:
        history: Dictionary with keys like 'train_loss', 'val_loss', 'train_acc', 'val_acc'
        save_path: Optional path to save the figure
    
    Returns:
        matplotlib Figure object
    
    Example:
        >>> history = {
        ...     'train_loss': [0.5, 0.4, 0.3, 0.25, 0.2],
        ...     'val_loss': [0.55, 0.45, 0.35, 0.32, 0.3],
        ...     'train_acc': [0.80, 0.85, 0.90, 0.92, 0.94],
        ...     'val_acc': [0.78, 0.83, 0.88, 0.89, 0.90]
        ... }
        >>> fig = plot_training_history(history)
        >>> plt.show()
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Loss curves
    if 'train_loss' in history:
        epochs = range(1, len(history['train_loss']) + 1)
        ax1.plot(epochs, history['train_loss'], 'b-o', label='Training Loss', linewidth=2, markersize=6)
    if 'val_loss' in history:
        epochs = range(1, len(history['val_loss']) + 1)
        ax1.plot(epochs, history['val_loss'], 'r-s', label='Validation Loss', linewidth=2, markersize=6)
    
    ax1.set_xlabel('Epoch', fontsize=12, weight='bold')
    ax1.set_ylabel('Loss', fontsize=12, weight='bold')
    ax1.set_title('Training and Validation Loss', fontsize=14, weight='bold')
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)
    
    # Accuracy curves
    if 'train_acc' in history:
        epochs = range(1, len(history['train_acc']) + 1)
        ax2.plot(epochs, history['train_acc'], 'b-o', label='Training Accuracy', linewidth=2, markersize=6)
    if 'val_acc' in history:
        epochs = range(1, len(history['val_acc']) + 1)
        ax2.plot(epochs, history['val_acc'], 'r-s', label='Validation Accuracy', linewidth=2, markersize=6)
    
    ax2.axhline(y=0.95, color='green', linestyle='--', linewidth=2, alpha=0.5, label='Target (95%)')
    ax2.set_xlabel('Epoch', fontsize=12, weight='bold')
    ax2.set_ylabel('Accuracy', fontsize=12, weight='bold')
    ax2.set_title('Training and Validation Accuracy', fontsize=14, weight='bold')
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, 1.05)
    
    plt.suptitle('Training History', fontsize=16, weight='bold', y=1.02)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Training history plot saved to {save_path}")
    
    return fig



# ==============================================================================
# Architecture Comparison Visualization
# ==============================================================================


def compare_architectures(
    arch_a_metrics: Dict[str, float],
    arch_b_metrics: Dict[str, float],
    metric_names: List[str] = None,
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Compare two architectures (LiteFlowNet2 vs SpyNet) side-by-side.
    
    Shows which architecture performs better on different metrics:
    - Accuracy, Precision, Recall, F1, mAP
    - Training/Inference VRAM usage
    - Inference latency
    
    Helps decide which architecture to deploy based on priorities:
    - Maximum accuracy → choose the more accurate one
    - Memory constrained → choose lower VRAM
    - Real-time critical → choose lower latency
    
    Args:
        arch_a_metrics: Metrics for Architecture A (LiteFlowNet2)
        arch_b_metrics: Metrics for Architecture B (SpyNet)
        metric_names: List of metric names to compare
        save_path: Optional path to save the figure
    
    Returns:
        matplotlib Figure object
    
    Example:
        >>> arch_a = {
        ...     'accuracy': 0.96, 'precision': 0.94, 'recall': 0.97,
        ...     'f1_score': 0.955, 'inference_latency_ms': 80,
        ...     'inference_vram_gb': 4.2, 'training_vram_gb': 7.8
        ... }
        >>> arch_b = {
        ...     'accuracy': 0.95, 'precision': 0.93, 'recall': 0.96,
        ...     'f1_score': 0.945, 'inference_latency_ms': 60,
        ...     'inference_vram_gb': 3.1, 'training_vram_gb': 5.9
        ... }
        >>> fig = compare_architectures(arch_a, arch_b)
        >>> plt.show()
    """
    if metric_names is None:
        metric_names = ['accuracy', 'precision', 'recall', 'f1_score', 'mAP']
    
    fig = plt.figure(figsize=(18, 10))
    gs = GridSpec(2, 3, figure=fig)
    
    # 1. Grouped bar chart for main metrics
    ax1 = fig.add_subplot(gs[0, :2])
    
    available_metrics = [m for m in metric_names if m in arch_a_metrics and m in arch_b_metrics]
    x = np.arange(len(available_metrics))
    width = 0.35
    
    values_a = [arch_a_metrics[m] for m in available_metrics]
    values_b = [arch_b_metrics[m] for m in available_metrics]
    
    bars1 = ax1.bar(x - width/2, values_a, width, label='Architecture A (LiteFlowNet2)', 
                    color='#3498db', edgecolor='black', linewidth=1.5)
    bars2 = ax1.bar(x + width/2, values_b, width, label='Architecture B (SpyNet)', 
                    color='#e74c3c', edgecolor='black', linewidth=1.5)
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.3f}',
                    ha='center', va='bottom', fontsize=10, weight='bold')
    
    ax1.set_ylabel('Score', fontsize=12, weight='bold')
    ax1.set_title('Performance Metrics Comparison', fontsize=14, weight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels([m.replace('_', ' ').title() for m in available_metrics])
    ax1.legend(fontsize=11)
    ax1.axhline(y=0.95, color='green', linestyle='--', linewidth=2, alpha=0.3, label='Target')
    ax1.set_ylim(0, 1.05)
    ax1.grid(axis='y', alpha=0.3)
    
    # 2. Memory usage comparison
    ax2 = fig.add_subplot(gs[0, 2])
    
    memory_metrics = ['training_vram_gb', 'inference_vram_gb']
    memory_labels = ['Training\nVRAM (GB)', 'Inference\nVRAM (GB)']
    
    if all(m in arch_a_metrics for m in memory_metrics):
        x_mem = np.arange(len(memory_metrics))
        mem_a = [arch_a_metrics[m] for m in memory_metrics]
        mem_b = [arch_b_metrics[m] for m in memory_metrics]
        
        bars1 = ax2.bar(x_mem - width/2, mem_a, width, label='Arch A', color='#3498db', 
                       edgecolor='black', linewidth=1.5)
        bars2 = ax2.bar(x_mem + width/2, mem_b, width, label='Arch B', color='#e74c3c', 
                       edgecolor='black', linewidth=1.5)
        
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}',
                        ha='center', va='bottom', fontsize=10, weight='bold')
        
        ax2.set_ylabel('VRAM (GB)', fontsize=12, weight='bold')
        ax2.set_title('Memory Usage', fontsize=14, weight='bold')
        ax2.set_xticks(x_mem)
        ax2.set_xticklabels(memory_labels)
        ax2.legend(fontsize=10)
        ax2.grid(axis='y', alpha=0.3)
    
    # 3. Latency comparison
    ax3 = fig.add_subplot(gs[1, 0])
    
    if 'inference_latency_ms' in arch_a_metrics:
        latencies = [arch_a_metrics['inference_latency_ms'], arch_b_metrics['inference_latency_ms']]
        colors = ['#3498db', '#e74c3c']
        labels = ['Arch A\n(LiteFlowNet2)', 'Arch B\n(SpyNet)']
        
        bars = ax3.bar(range(2), latencies, color=colors, edgecolor='black', linewidth=1.5)
        
        for bar, latency in zip(bars, latencies):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{latency:.1f} ms',
                    ha='center', va='bottom', fontsize=11, weight='bold')
        
        ax3.set_ylabel('Latency (ms)', fontsize=12, weight='bold')
        ax3.set_title('Inference Latency (4-Camera Batch)', fontsize=14, weight='bold')
        ax3.set_xticks(range(2))
        ax3.set_xticklabels(labels)
        ax3.axhline(y=100, color='red', linestyle='--', linewidth=2, alpha=0.5, label='Target (<100ms)')
        ax3.legend(fontsize=10)
        ax3.grid(axis='y', alpha=0.3)
    
    # 4. Radar chart comparison
    ax4 = fig.add_subplot(gs[1, 1:], projection='polar')
    
    radar_metrics = ['accuracy', 'precision', 'recall', 'f1_score']
    radar_metrics = [m for m in radar_metrics if m in arch_a_metrics]
    
    angles = np.linspace(0, 2 * np.pi, len(radar_metrics), endpoint=False).tolist()
    values_a = [arch_a_metrics[m] for m in radar_metrics]
    values_b = [arch_b_metrics[m] for m in radar_metrics]
    
    # Close the circle
    values_a += values_a[:1]
    values_b += values_b[:1]
    angles += angles[:1]
    
    ax4.plot(angles, values_a, 'o-', linewidth=2, color='#3498db', label='Architecture A')
    ax4.fill(angles, values_a, alpha=0.15, color='#3498db')
    ax4.plot(angles, values_b, 's-', linewidth=2, color='#e74c3c', label='Architecture B')
    ax4.fill(angles, values_b, alpha=0.15, color='#e74c3c')
    
    ax4.set_xticks(angles[:-1])
    ax4.set_xticklabels([m.replace('_', ' ').title() for m in radar_metrics], size=11)
    ax4.set_ylim(0, 1)
    ax4.set_title('Performance Comparison Radar', fontsize=14, weight='bold', pad=20)
    ax4.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0), fontsize=11)
    ax4.grid(True)
    
    plt.suptitle('Architecture Comparison: LiteFlowNet2 vs SpyNet', 
                 fontsize=16, weight='bold', y=0.98)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Architecture comparison saved to {save_path}")
    
    return fig


def create_dashboard_summary(
    metrics: Dict[str, any],
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Create a comprehensive dashboard summarizing all key information.
    
    This is the "master view" that shows everything at a glance:
    - Model performance (confusion matrix, metrics)
    - Training progress (loss curves)
    - Memory usage
    - Latency
    
    Perfect for presentations or quick status checks.
    
    Args:
        metrics: Dictionary containing all metrics, history, etc.
        save_path: Optional path to save the figure
    
    Returns:
        matplotlib Figure object
    
    Example:
        >>> metrics = {
        ...     'model_name': 'LiteFlowNet2',
        ...     'accuracy': 0.96,
        ...     'confusion_matrix': np.array([[850, 50], [30, 870]]),
        ...     'history': {...},
        ...     'inference_latency_ms': 80,
        ...     ...
        ... }
        >>> fig = create_dashboard_summary(metrics)
        >>> plt.show()
    """
    fig = plt.figure(figsize=(20, 12))
    gs = GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)
    
    model_name = metrics.get('model_name', 'Model')
    
    # Title
    fig.suptitle(
        f'{model_name} - Performance Dashboard',
        fontsize=18,
        weight='bold',
        y=0.98
    )
    
    # 1. Confusion Matrix (top left)
    if 'confusion_matrix' in metrics:
        ax1 = fig.add_subplot(gs[0, 0])
        cm = metrics['confusion_matrix']
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', square=True, ax=ax1,
                   cbar_kws={'label': 'Count'})
        ax1.set_title('Confusion Matrix', fontsize=13, weight='bold')
        ax1.set_ylabel('True Label')
        ax1.set_xlabel('Predicted Label')
    
    # 2. Metrics bars (top middle)
    ax2 = fig.add_subplot(gs[0, 1])
    metric_keys = ['accuracy', 'precision', 'recall', 'f1_score']
    metric_values = [metrics.get(k, 0) for k in metric_keys]
    colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(metric_keys)))
    bars = ax2.barh(metric_keys, metric_values, color=colors, edgecolor='black')
    for bar, val in zip(bars, metric_values):
        ax2.text(val, bar.get_y() + bar.get_height()/2, f' {val:.3f}',
                va='center', fontsize=10, weight='bold')
    ax2.set_xlim(0, 1.05)
    ax2.set_title('Performance Metrics', fontsize=13, weight='bold')
    ax2.grid(axis='x', alpha=0.3)
    
    # 3. System specs (top right)
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.axis('off')
    specs_text = f"""
    Model: {model_name}
    
    Performance:
    • Accuracy: {metrics.get('accuracy', 0):.1%}
    • Latency: {metrics.get('inference_latency_ms', 0):.1f} ms
    
    Memory:
    • Training: {metrics.get('training_vram_gb', 0):.1f} GB
    • Inference: {metrics.get('inference_vram_gb', 0):.1f} GB
    
    Dataset:
    • Train: {metrics.get('train_samples', 0):,}
    • Val: {metrics.get('val_samples', 0):,}
    • Test: {metrics.get('test_samples', 0):,}
    
    Status: {'✓ Meets Requirements' if metrics.get('accuracy', 0) >= 0.95 else '⚠ Below Target'}
    """
    ax3.text(0.1, 0.5, specs_text, fontsize=11, family='monospace',
            verticalalignment='center', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    ax3.set_title('System Specifications', fontsize=13, weight='bold')
    
    # 4-5. Training history (middle row)
    if 'history' in metrics:
        history = metrics['history']
        
        # Loss curves
        ax4 = fig.add_subplot(gs[1, :2])
        if 'train_loss' in history:
            epochs = range(1, len(history['train_loss']) + 1)
            ax4.plot(epochs, history['train_loss'], 'b-o', label='Training Loss', linewidth=2)
        if 'val_loss' in history:
            epochs = range(1, len(history['val_loss']) + 1)
            ax4.plot(epochs, history['val_loss'], 'r-s', label='Validation Loss', linewidth=2)
        ax4.set_xlabel('Epoch')
        ax4.set_ylabel('Loss')
        ax4.set_title('Training History - Loss', fontsize=13, weight='bold')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        # Accuracy curves
        ax5 = fig.add_subplot(gs[1, 2])
        if 'val_acc' in history:
            epochs = range(1, len(history['val_acc']) + 1)
            ax5.plot(epochs, history['val_acc'], 'g-^', label='Validation Accuracy', linewidth=2)
        ax5.axhline(y=0.95, color='red', linestyle='--', alpha=0.5, label='Target')
        ax5.set_xlabel('Epoch')
        ax5.set_ylabel('Accuracy')
        ax5.set_title('Validation Accuracy', fontsize=13, weight='bold')
        ax5.legend()
        ax5.grid(True, alpha=0.3)
        ax5.set_ylim(0, 1.05)
    
    # 6. Per-class metrics (bottom)
    ax6 = fig.add_subplot(gs[2, :])
    if 'per_class_metrics' in metrics:
        pcm = metrics['per_class_metrics']
        classes = list(pcm.keys())
        metrics_types = ['precision', 'recall', 'f1-score']
        
        x = np.arange(len(classes))
        width = 0.25
        
        for idx, metric in enumerate(metrics_types):
            values = [pcm[c].get(metric, 0) for c in classes]
            ax6.bar(x + idx*width, values, width, label=metric.capitalize())
        
        ax6.set_ylabel('Score')
        ax6.set_title('Per-Class Performance Metrics', fontsize=13, weight='bold')
        ax6.set_xticks(x + width)
        ax6.set_xticklabels(classes)
        ax6.legend()
        ax6.grid(axis='y', alpha=0.3)
        ax6.set_ylim(0, 1.05)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"Dashboard summary saved to {save_path}")
    
    return fig
