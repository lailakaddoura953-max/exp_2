"""
Training Pipeline for Deep Learning Misalignment Detection

This module implements the complete training pipeline for both Architecture A (LiteFlowNet2)
and Architecture B (SpyNet), including:

1. Memory-efficient training configuration (FP16, gradient checkpointing)
2. Loss function components (BCE + Smooth L1)
3. Checkpoint management
4. Training loop with validation and early stopping
5. TensorBoard logging integration

Task 9: Training Pipeline Implementation
Requirements: 7.1-7.7, 8.1-8.7, 20.1-20.7, 23.1-23.7, 27.1-27.7

Key Features:
- Mixed precision training (FP16/FP32) for memory efficiency
- Dynamic batch sizing based on available VRAM
- Automatic checkpointing every 1000 steps
- Early stopping (10 evaluations without improvement)
- Learning rate reduction (5 evaluations without improvement)
- TensorBoard logging for monitoring
"""

import logging
import time
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime
import json

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import DataLoader
    from torch.cuda.amp import GradScaler, autocast
    from torch.utils.tensorboard import SummaryWriter
    import numpy as np
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

logger = logging.getLogger(__name__)


# ==============================================================================
# Task 9.2: Loss Function Components
# ==============================================================================

class MisalignmentLoss(nn.Module):
    """
    Combined loss function for misalignment detection.
    
    Components:
    1. Binary Cross-Entropy (BCE) for misalignment probability classification
    2. Smooth L1 Loss for 6-DOF pose regression
    3. Weighted combination with configurable weights
    
    Why these losses?
    - BCE: Perfect for binary classification (aligned vs misaligned)
    - Smooth L1: More robust to outliers than MSE for pose regression
    - Weighted: Balance the importance of classification vs regression
    
    Requirements: 23.1-23.7
    """
    
    def __init__(
        self,
        classification_weight: float = 0.6,
        regression_weight: float = 0.4
    ):
        """
        Initialize loss function.
        
        Args:
            classification_weight: Weight for BCE loss (default: 0.6)
            regression_weight: Weight for Smooth L1 loss (default: 0.4)
        
        Requirements: 23.3, 23.4
        """
        super().__init__()
        
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch required")
        
        # Validate weights sum to 1.0
        total_weight = classification_weight + regression_weight
        if not np.isclose(total_weight, 1.0, atol=1e-6):
            logger.warning(
                f"Loss weights sum to {total_weight}, normalizing to 1.0"
            )
            classification_weight /= total_weight
            regression_weight /= total_weight
        
        self.classification_weight = classification_weight
        self.regression_weight = regression_weight
        
        # BCE loss for probability classification
        self.bce_loss = nn.BCELoss()
        
        # Smooth L1 loss for pose regression
        self.smooth_l1_loss = nn.SmoothL1Loss()
        
        logger.info(
            f"MisalignmentLoss initialized: "
            f"classification={classification_weight:.2f}, "
            f"regression={regression_weight:.2f}"
        )
    
    def forward(
        self,
        pred_prob: torch.Tensor,
        pred_pose: torch.Tensor,
        target_prob: torch.Tensor,
        target_pose: torch.Tensor
    ) -> Dict[str, torch.Tensor]:
        """
        Compute combined loss.
        
        Args:
            pred_prob: Predicted misalignment probability [B, 1]
            pred_pose: Predicted 6-DOF pose [B, 6]
            target_prob: Ground truth probability [B, 1]
            target_pose: Ground truth pose [B, 6]
        
        Returns:
            Dictionary with:
            - 'total': Combined weighted loss
            - 'classification': BCE loss component
            - 'regression': Smooth L1 loss component
        
        Requirements: 23.1, 23.2, 23.3, 23.6
        """
        # Classification loss (BCE)
        cls_loss = self.bce_loss(pred_prob, target_prob)
        
        # Regression loss (Smooth L1)
        reg_loss = self.smooth_l1_loss(pred_pose, target_pose)
        
        # Combined weighted loss
        total_loss = (
            self.classification_weight * cls_loss +
            self.regression_weight * reg_loss
        )
        
        return {
            'total': total_loss,
            'classification': cls_loss,
            'regression': reg_loss
        }


# ==============================================================================
# Task 9.3: Checkpoint Management
# ==============================================================================

@dataclass
class ModelCheckpoint:
    """
    Model checkpoint data structure.
    
    Contains all information needed to:
    - Resume training from interruption
    - Deploy model for inference
    - Track training progress
    
    Requirements: 20.1-20.6
    """
    # Model weights
    feature_extractor_state: Dict
    flow_network_state: Dict
    pose_estimator_state: Dict
    
    # Training state
    optimizer_state: Dict
    scheduler_state: Optional[Dict]
    training_step: int
    epoch: int
    
    # Performance metrics
    best_validation_loss: float
    validation_accuracy: float
    training_loss_history: List[float]
    
    # Configuration
    model_config: Dict
    preprocessing_params: Dict
    
    # Metadata
    timestamp: str
    pytorch_version: str
    cuda_version: str
    model_version: str


class CheckpointManager:
    """
    Manages model checkpoints during training.
    
    Features:
    - Save checkpoints every N steps
    - Keep only K most recent checkpoints (save disk space)
    - Maintain separate "best model" checkpoint
    - Support training resumption
    
    Requirements: 20.1-20.7
    """
    
    def __init__(
        self,
        checkpoint_dir: str,
        max_checkpoints: int = 3,
        save_interval: int = 1000
    ):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_dir: Directory to save checkpoints
            max_checkpoints: Maximum recent checkpoints to keep (default: 3)
            save_interval: Save every N training steps (default: 1000)
        
        Requirements: 20.3, 8.2
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_checkpoints = max_checkpoints
        self.save_interval = save_interval
        
        # Track checkpoint files
        self.checkpoint_files = []
        self.best_checkpoint_path = None
        self.best_validation_loss = float('inf')
        
        logger.info(f"CheckpointManager initialized: {self.checkpoint_dir}")
    
    def save_checkpoint(
        self,
        feature_extractor: nn.Module,
        flow_network: nn.Module,
        pose_estimator: nn.Module,
        optimizer: torch.optim.Optimizer,
        scheduler: Optional[any],
        training_step: int,
        epoch: int,
        validation_loss: float,
        validation_accuracy: float,
        training_loss_history: List[float],
        model_config: Dict,
        is_best: bool = False
    ) -> str:
        """
        Save model checkpoint.
        
        Args:
            feature_extractor: CNN Feature Extractor module
            flow_network: LiteFlowNet2 or SpyNet module
            pose_estimator: Pose Estimator module
            optimizer: Training optimizer
            scheduler: Learning rate scheduler (optional)
            training_step: Current training step
            epoch: Current epoch
            validation_loss: Current validation loss
            validation_accuracy: Current validation accuracy
            training_loss_history: Recent training losses
            model_config: Model configuration dictionary
            is_best: If True, save as best_model checkpoint
        
        Returns:
            Path to saved checkpoint file
        
        Requirements: 20.1, 20.2, 20.3, 20.4, 20.6
        """
        # Create checkpoint dictionary
        checkpoint = {
            'feature_extractor_state': feature_extractor.state_dict(),
            'flow_network_state': flow_network.state_dict(),
            'pose_estimator_state': pose_estimator.state_dict(),
            'optimizer_state': optimizer.state_dict(),
            'scheduler_state': scheduler.state_dict() if scheduler else None,
            'training_step': training_step,
            'epoch': epoch,
            'best_validation_loss': self.best_validation_loss,
            'validation_accuracy': validation_accuracy,
            'training_loss_history': training_loss_history[-100:],  # Last 100
            'model_config': model_config,
            'preprocessing_params': {
                'normalization_mean': [0.485, 0.456, 0.406],
                'normalization_std': [0.229, 0.224, 0.225],
                'target_resolution': model_config.get('target_resolution', (640, 640))
            },
            'timestamp': datetime.now().isoformat(),
            'pytorch_version': torch.__version__,
            'cuda_version': torch.version.cuda if torch.cuda.is_available() else 'N/A',
            'model_version': '1.0.0'
        }
        
        # Determine filename
        if is_best:
            filename = 'best_model.pth'
        else:
            filename = f'checkpoint_step_{training_step}.pth'
        
        checkpoint_path = self.checkpoint_dir / filename
        
        # Save checkpoint
        torch.save(checkpoint, checkpoint_path)
        
        # Update tracking
        if is_best:
            self.best_checkpoint_path = checkpoint_path
            self.best_validation_loss = validation_loss
            logger.info(
                f"✓ Saved best model: {checkpoint_path} "
                f"(val_loss={validation_loss:.4f})"
            )
        else:
            self.checkpoint_files.append(checkpoint_path)
            logger.info(
                f"✓ Saved checkpoint: {checkpoint_path} "
                f"(step={training_step}, val_loss={validation_loss:.4f})"
            )
        
        # Clean up old checkpoints (keep only max_checkpoints most recent)
        if not is_best and len(self.checkpoint_files) > self.max_checkpoints:
            old_checkpoint = self.checkpoint_files.pop(0)
            if old_checkpoint.exists():
                old_checkpoint.unlink()
                logger.info(f"Removed old checkpoint: {old_checkpoint}")
        
        return str(checkpoint_path)
    
    def load_checkpoint(
        self,
        checkpoint_path: str,
        feature_extractor: nn.Module,
        flow_network: nn.Module,
        pose_estimator: nn.Module,
        optimizer: Optional[torch.optim.Optimizer] = None,
        scheduler: Optional[any] = None
    ) -> Dict:
        """
        Load model checkpoint.
        
        Args:
            checkpoint_path: Path to checkpoint file
            feature_extractor: CNN Feature Extractor module
            flow_network: LiteFlowNet2 or SpyNet module
            pose_estimator: Pose Estimator module
            optimizer: Training optimizer (optional, for resumption)
            scheduler: Learning rate scheduler (optional, for resumption)
        
        Returns:
            Dictionary with checkpoint metadata
        
        Requirements: 20.5, 20.7
        """
        checkpoint_path = Path(checkpoint_path)
        
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
        
        logger.info(f"Loading checkpoint from {checkpoint_path}...")
        
        # Load checkpoint (map to CPU first for compatibility)
        # PyTorch 2.6+ requires weights_only=False for loading full checkpoints
        checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
        
        # Load model weights
        feature_extractor.load_state_dict(checkpoint['feature_extractor_state'])
        flow_network.load_state_dict(checkpoint['flow_network_state'])
        pose_estimator.load_state_dict(checkpoint['pose_estimator_state'])
        
        # Load optimizer/scheduler states if resuming training
        if optimizer and 'optimizer_state' in checkpoint:
            optimizer.load_state_dict(checkpoint['optimizer_state'])
        
        if scheduler and 'scheduler_state' in checkpoint and checkpoint['scheduler_state']:
            scheduler.load_state_dict(checkpoint['scheduler_state'])
        
        logger.info(
            f"✓ Checkpoint loaded: step={checkpoint['training_step']}, "
            f"epoch={checkpoint['epoch']}, "
            f"val_loss={checkpoint.get('best_validation_loss', 'N/A')}"
        )
        
        return checkpoint
    
    def should_save(self, training_step: int) -> bool:
        """Check if checkpoint should be saved at this step."""
        return training_step > 0 and training_step % self.save_interval == 0


# ==============================================================================
# Task 9.4 & 9.5: Training Loop with Validation and TensorBoard Logging
# ==============================================================================

class Trainer:
    """
    Complete training pipeline for misalignment detection models.
    
    Features:
    - Mixed precision training (FP16/FP32)
    - Automatic checkpoint management
    - Early stopping
    - Learning rate scheduling
    - TensorBoard logging
    - VRAM monitoring
    
    Requirements: 7.1-7.7, 8.1-8.7, 27.1-27.7
    """
    
    def __init__(
        self,
        feature_extractor: nn.Module,
        flow_network: nn.Module,
        pose_estimator: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        config: Dict,
        device: str = 'cuda'
    ):
        """
        Initialize trainer.
        
        Args:
            feature_extractor: CNN Feature Extractor
            flow_network: LiteFlowNet2 or SpyNet
            pose_estimator: Pose Estimator
            train_loader: Training data loader
            val_loader: Validation data loader
            config: Training configuration dictionary
            device: 'cuda' or 'cpu'
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch required")
        
        self.feature_extractor = feature_extractor.to(device)
        self.flow_network = flow_network.to(device)
        self.pose_estimator = pose_estimator.to(device)
        
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.config = config
        self.device = device
        
        # Loss function
        self.criterion = MisalignmentLoss(
            classification_weight=config.get('classification_weight', 0.6),
            regression_weight=config.get('regression_weight', 0.4)
        )
        
        # Optimizer (Adam)
        all_params = list(feature_extractor.parameters()) + \
                     list(flow_network.parameters()) + \
                     list(pose_estimator.parameters())
        
        self.optimizer = torch.optim.Adam(
            all_params,
            lr=config.get('learning_rate', 1e-4)
        )
        
        # Learning rate scheduler (reduce on plateau)
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=5  # 5 evaluations without improvement
        )
        
        # Mixed precision training
        self.use_amp = config.get('mixed_precision', True)
        self.scaler = GradScaler() if self.use_amp else None
        
        # Checkpoint manager
        self.checkpoint_manager = CheckpointManager(
            checkpoint_dir=config.get('checkpoint_dir', 'checkpoints'),
            max_checkpoints=3,
            save_interval=1000
        )
        
        # TensorBoard writer
        log_dir = Path(config.get('tensorboard_dir', 'runs')) / config.get('run_name', 'experiment')
        self.writer = SummaryWriter(log_dir=str(log_dir))
        logger.info(f"TensorBoard logging to {log_dir}")
        
        # Training state
        self.training_step = 0
        self.epoch = 0
        self.best_val_loss = float('inf')
        self.epochs_without_improvement = 0
        self.training_loss_history = []
        
        # Early stopping parameters
        self.early_stopping_patience = config.get('early_stopping_patience', 10)
        self.validation_interval = config.get('validation_interval', 500)
        
        logger.info("Trainer initialized")
        logger.info(f"  Device: {device}")
        logger.info(f"  Mixed precision: {self.use_amp}")
        logger.info(f"  Validation every {self.validation_interval} steps")
        logger.info(f"  Early stopping patience: {self.early_stopping_patience} evaluations")
    
    def train_step(
        self,
        images_t: torch.Tensor,
        images_t1: torch.Tensor,
        labels: Dict
    ) -> Dict[str, float]:
        """
        Single training step.
        
        Args:
            images_t: Images at time t [B, 3, H, W]
            images_t1: Images at time t+1 [B, 3, H, W]
            labels: Dictionary with ground truth labels
        
        Returns:
            Dictionary with loss components
        """
        self.feature_extractor.train()
        self.flow_network.train()
        self.pose_estimator.train()
        
        # Move to device
        images_t = images_t.to(self.device)
        images_t1 = images_t1.to(self.device)
        
        # Get target probability and ensure shape is [B, 1]
        target_prob = labels['misalignment_probability'].to(self.device)
        if target_prob.dim() == 1:
            target_prob = target_prob.unsqueeze(1)
        elif target_prob.dim() == 3:
            target_prob = target_prob.squeeze(-1)  # Remove extra dimension if present
        
        target_pose = labels['pose'].to(self.device)
        
        # Zero gradients
        self.optimizer.zero_grad()
        
        # Forward pass with mixed precision
        if self.use_amp:
            with autocast():
                # Extract features
                pyramid_t = self.feature_extractor(images_t)
                pyramid_t1 = self.feature_extractor(images_t1)
                
                # Estimate optical flow
                flow = self.flow_network(pyramid_t, pyramid_t1)
                
                # Predict misalignment and pose
                pred_prob, pred_pose = self.pose_estimator(pyramid_t[0], flow)
                
                # Compute loss
                losses = self.criterion(pred_prob, pred_pose, target_prob, target_pose)
            
            # Backward pass with gradient scaling
            self.scaler.scale(losses['total']).backward()
            self.scaler.step(self.optimizer)
            self.scaler.update()
        else:
            # Extract features
            pyramid_t = self.feature_extractor(images_t)
            pyramid_t1 = self.feature_extractor(images_t1)
            
            # Estimate optical flow
            flow = self.flow_network(pyramid_t, pyramid_t1)
            
            # Predict misalignment and pose
            pred_prob, pred_pose = self.pose_estimator(pyramid_t[0], flow)
            
            # Compute loss
            losses = self.criterion(pred_prob, pred_pose, target_prob, target_pose)
            
            # Backward pass
            losses['total'].backward()
            self.optimizer.step()
        
        # Return loss values
        return {
            'total': losses['total'].item(),
            'classification': losses['classification'].item(),
            'regression': losses['regression'].item()
        }
    
    def validate(self) -> Dict[str, float]:
        """
        Validation evaluation.
        
        Returns:
            Dictionary with validation metrics
        """
        self.feature_extractor.eval()
        self.flow_network.eval()
        self.pose_estimator.eval()
        
        total_loss = 0.0
        cls_loss = 0.0
        reg_loss = 0.0
        correct = 0
        total = 0
        
        with torch.no_grad():
            for batch_idx, (images_t, images_t1, labels) in enumerate(self.val_loader):
                images_t = images_t.to(self.device)
                images_t1 = images_t1.to(self.device)
                
                # Get target probability and ensure shape is [B, 1]
                target_prob = labels['misalignment_probability'].to(self.device)
                if target_prob.dim() == 1:
                    target_prob = target_prob.unsqueeze(1)
                elif target_prob.dim() == 3:
                    target_prob = target_prob.squeeze(-1)  # Remove extra dimension if present
                
                target_pose = labels['pose'].to(self.device)
                
                # Forward pass
                pyramid_t = self.feature_extractor(images_t)
                pyramid_t1 = self.feature_extractor(images_t1)
                flow = self.flow_network(pyramid_t, pyramid_t1)
                pred_prob, pred_pose = self.pose_estimator(pyramid_t[0], flow)
                
                # Compute loss
                losses = self.criterion(pred_prob, pred_pose, target_prob, target_pose)
                
                total_loss += losses['total'].item()
                cls_loss += losses['classification'].item()
                reg_loss += losses['regression'].item()
                
                # Compute accuracy (threshold at 0.5)
                pred_binary = (pred_prob > 0.5).float()
                target_binary = (target_prob > 0.5).float()
                correct += (pred_binary == target_binary).sum().item()
                total += target_binary.size(0)
        
        n_batches = len(self.val_loader)
        accuracy = correct / total if total > 0 else 0.0
        
        return {
            'loss': total_loss / n_batches,
            'classification_loss': cls_loss / n_batches,
            'regression_loss': reg_loss / n_batches,
            'accuracy': accuracy
        }
    
    def train(self, num_epochs: int):
        """
        Main training loop.
        
        Args:
            num_epochs: Number of epochs to train
        
        Requirements: 8.1-8.7
        """
        logger.info(f"Starting training for {num_epochs} epochs...")
        
        for epoch in range(num_epochs):
            self.epoch = epoch
            epoch_start_time = time.time()
            
            for batch_idx, (images_t, images_t1, labels) in enumerate(self.train_loader):
                self.training_step += 1
                
                # Training step
                losses = self.train_step(images_t, images_t1, labels)
                
                # Log training losses
                self.training_loss_history.append(losses['total'])
                
                if self.training_step % 10 == 0:
                    self.writer.add_scalar('Train/Total_Loss', losses['total'], self.training_step)
                    self.writer.add_scalar('Train/Classification_Loss', losses['classification'], self.training_step)
                    self.writer.add_scalar('Train/Regression_Loss', losses['regression'], self.training_step)
                
                if self.training_step % 100 == 0:
                    self.writer.add_scalar('Train/Learning_Rate', self.optimizer.param_groups[0]['lr'], self.training_step)
                    
                    if torch.cuda.is_available():
                        memory_allocated = torch.cuda.memory_allocated() / 1e9
                        memory_reserved = torch.cuda.memory_reserved() / 1e9
                        self.writer.add_scalar('System/GPU_Memory_Allocated_GB', memory_allocated, self.training_step)
                        self.writer.add_scalar('System/GPU_Memory_Reserved_GB', memory_reserved, self.training_step)
                
                # Validation
                if self.training_step % self.validation_interval == 0:
                    val_metrics = self.validate()
                    
                    # Log validation metrics
                    self.writer.add_scalar('Val/Loss', val_metrics['loss'], self.training_step)
                    self.writer.add_scalar('Val/Classification_Loss', val_metrics['classification_loss'], self.training_step)
                    self.writer.add_scalar('Val/Regression_Loss', val_metrics['regression_loss'], self.training_step)
                    self.writer.add_scalar('Val/Accuracy', val_metrics['accuracy'], self.training_step)
                    
                    logger.info(
                        f"Step {self.training_step}: "
                        f"Val Loss={val_metrics['loss']:.4f}, "
                        f"Accuracy={val_metrics['accuracy']:.4f}"
                    )
                    
                    # Learning rate scheduling
                    self.scheduler.step(val_metrics['loss'])
                    
                    # Check for improvement
                    is_best = val_metrics['loss'] < self.best_val_loss
                    if is_best:
                        self.best_val_loss = val_metrics['loss']
                        self.epochs_without_improvement = 0
                    else:
                        self.epochs_without_improvement += 1
                    
                    # Save checkpoint
                    if self.checkpoint_manager.should_save(self.training_step) or is_best:
                        self.checkpoint_manager.save_checkpoint(
                            self.feature_extractor,
                            self.flow_network,
                            self.pose_estimator,
                            self.optimizer,
                            self.scheduler,
                            self.training_step,
                            self.epoch,
                            val_metrics['loss'],
                            val_metrics['accuracy'],
                            self.training_loss_history,
                            self.config,
                            is_best=is_best
                        )
                    
                    # Early stopping check
                    if self.epochs_without_improvement >= self.early_stopping_patience:
                        logger.info(
                            f"Early stopping triggered after {self.epochs_without_improvement} "
                            f"evaluations without improvement"
                        )
                        return
            
            epoch_time = time.time() - epoch_start_time
            logger.info(f"Epoch {epoch+1}/{num_epochs} completed in {epoch_time:.1f}s")
        
        logger.info("Training completed!")
        self.writer.close()
