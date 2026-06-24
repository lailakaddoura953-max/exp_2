"""
Training Pipeline

This module contains:
- Memory-efficient training configuration (mixed precision, gradient checkpointing)
- Loss functions (binary cross-entropy + smooth L1)
- Checkpoint management system
- Training loop with validation and early stopping
- TensorBoard logging integration

Task 9: Training Pipeline Implementation
"""

from .trainer import (
    Trainer,
    MisalignmentLoss,
    CheckpointManager,
    ModelCheckpoint
)

__all__ = [
    'Trainer',
    'MisalignmentLoss',
    'CheckpointManager',
    'ModelCheckpoint'
]
