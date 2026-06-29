"""
Simple Classifier Wrapper for Trained Strad Models

This is a lightweight wrapper for models trained with train_strad_classifier.py.
It bypasses the complex InferenceEngine and loads SimpleStradClassifier directly.

Use this when you've trained a model with the training script and want to use it
in the monitoring system or web app.

Key Features:
- Direct model loading without InferenceEngine overhead
- Compatible with checkpoints from train_strad_classifier.py
- Automatic device detection (CUDA/CPU)
- Returns ClassificationResult with raw_output for diagnostics
"""

import torch
import torch.nn as nn
import numpy as np
from typing import Optional, Dict
from dataclasses import dataclass
import time


@dataclass
class ClassificationResult:
    """
    Result from classification with diagnostic information.
    
    This data class contains all information about a classification result,
    including the prediction, confidence, timing, and raw model outputs.
    
    Attributes:
        severity: Classification result - 'none', 'moderate', or 'critical'
        confidence: Confidence score from 0.0 to 1.0 (probability of predicted class)
        processing_time_ms: Total processing time in milliseconds (preprocessing + inference)
        model_name: Name of the model used for classification
        threshold_used: Threshold value used for classification (currently fixed at 0.5)
        raw_output: Dictionary with diagnostic information including:
            - model_name: Model architecture name
            - device: Device used for inference (cuda/cpu)
            - image_size: Input image size
            - preprocessing_time_ms: Time spent preprocessing the image
            - class_probabilities: Dictionary of probabilities for each class
    """
    severity: str  # 'none', 'moderate', or 'critical'
    confidence: float  # 0.0 to 1.0
    processing_time_ms: float
    model_name: str
    threshold_used: float
    raw_output: Dict  # Diagnostic information


class SimpleStradClassifier(nn.Module):
    """
    Simple CNN classifier for strad misalignment detection.
    
    This is the same architecture used in train_strad_classifier.py.
    It uses a 4-layer convolutional feature extractor followed by
    a 2-layer fully connected classifier.
    
    Architecture:
        - Conv1: 3 -> 32 channels, 3x3 kernel, batch norm, ReLU, max pool
        - Conv2: 32 -> 64 channels, 3x3 kernel, batch norm, ReLU, max pool
        - Conv3: 64 -> 128 channels, 3x3 kernel, batch norm, ReLU, max pool
        - Conv4: 128 -> 256 channels, 3x3 kernel, batch norm, ReLU, max pool
        - Adaptive avg pool to 4x4
        - FC1: 256*4*4 -> 512, ReLU, dropout(0.5)
        - FC2: 512 -> num_classes, dropout(0.3)
    
    Args:
        num_classes: Number of output classes (default: 3 for none/moderate/critical)
    """
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


class SimpleClassifierWrapper:
    """
    Wrapper for SimpleStradClassifier trained models.
    
    This wrapper provides a simple interface for loading and running inference
    with models trained using train_strad_classifier.py. It is compatible with
    the monitoring system and web app.
    
    Key Features:
    - Direct model loading from .pth checkpoints
    - Automatic device selection (CUDA/CPU)
    - Image preprocessing with ImageNet normalization
    - Returns structured ClassificationResult with diagnostics
    
    Usage:
        >>> wrapper = SimpleClassifierWrapper(
        ...     model_checkpoint_path='model.pth',
        ...     device='cuda',
        ...     image_size=640
        ... )
        >>> result = wrapper.classify_snapshot(image_array)
        >>> print(f"{result.severity} ({result.confidence:.2f})")
    
    Attributes:
        device: torch.device for model inference (cuda/cpu)
        image_size: Input image size (square) for preprocessing
        model_checkpoint_path: Path to the .pth checkpoint file
        class_names: List of class labels ['none', 'moderate', 'critical']
        model: Loaded SimpleStradClassifier model in eval mode
    """
    
    def __init__(
        self,
        model_checkpoint_path: str,
        device: str = 'cpu',
        image_size: int = 640
    ):
        """
        Initialize classifier wrapper.
        
        Args:
            model_checkpoint_path: Path to .pth checkpoint file from train_strad_classifier.py
            device: Device for inference - 'cuda' for GPU or 'cpu' (default: 'cpu')
            image_size: Input image size in pixels (square images, default: 640)
        
        Raises:
            KeyError: If checkpoint doesn't contain 'model_state_dict' key
            FileNotFoundError: If checkpoint file doesn't exist
            RuntimeError: If model weights fail to load
        """
        self.device = torch.device(device)
        self.image_size = image_size
        self.model_checkpoint_path = model_checkpoint_path
        
        # Class mapping
        self.class_names = ['none', 'moderate', 'critical']
        
        # Load model
        self.model = self._load_model()
        self.model.eval()
    
    def _load_model(self):
        """
        Load trained model from checkpoint.
        
        This method loads the model state dict from a checkpoint file created
        by train_strad_classifier.py. It validates the checkpoint format and
        provides helpful error messages if the checkpoint is incompatible.
        
        Returns:
            SimpleStradClassifier model loaded with trained weights in eval mode
        
        Raises:
            KeyError: If checkpoint doesn't contain 'model_state_dict' key.
                     This happens when trying to use an InferenceEngine checkpoint
                     with SimpleClassifierWrapper. Use classifier_type='inference_engine' instead.
        """
        # Load checkpoint
        checkpoint = torch.load(
            self.model_checkpoint_path,
            map_location=self.device
        )
        
        # Validate checkpoint format
        if 'model_state_dict' not in checkpoint:
            raise KeyError(
                f"Checkpoint at '{self.model_checkpoint_path}' does not contain "
                f"'model_state_dict' key. This wrapper expects checkpoints from "
                f"train_strad_classifier.py. If this is an InferenceEngine checkpoint, "
                f"set classifier_type='inference_engine' in system_config.json"
            )
        
        # Create model
        model = SimpleStradClassifier(num_classes=3).to(self.device)
        
        # Load weights
        model.load_state_dict(checkpoint['model_state_dict'])
        
        return model
    
    def _preprocess_image(self, image: np.ndarray) -> torch.Tensor:
        """
        Preprocess image for model input.
        
        This method performs the following preprocessing steps:
        1. Resize image to target size (default: 640x640)
        2. Convert from uint8 [0, 255] to float32 [0.0, 1.0]
        3. Apply ImageNet normalization (mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        4. Convert from numpy (H, W, C) to torch tensor (C, H, W)
        5. Add batch dimension (1, C, H, W)
        6. Move to target device (CPU/CUDA)
        
        Args:
            image: Input image as numpy array (H, W, C) in RGB format, uint8 [0-255]
            
        Returns:
            Preprocessed tensor (1, 3, H, W) ready for model input, float32 on target device
        """
        import cv2
        
        # Resize
        image = cv2.resize(image, (self.image_size, self.image_size))
        
        # Convert to float and normalize to [0, 1]
        image = image.astype(np.float32) / 255.0
        
        # ImageNet normalization
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        
        image = (image - mean) / std
        
        # Convert to tensor (H, W, C) -> (C, H, W)
        image = torch.from_numpy(image).permute(2, 0, 1)
        
        # Add batch dimension (C, H, W) -> (1, C, H, W)
        image = image.unsqueeze(0)
        
        return image.to(self.device)
    
    def classify_snapshot(self, image: np.ndarray) -> ClassificationResult:
        """
        Classify a snapshot image for misalignment severity.
        
        This method performs the complete inference pipeline:
        1. Preprocess the input image (resize, normalize, tensorize)
        2. Run model inference to get class logits
        3. Apply softmax to get class probabilities
        4. Extract predicted class and confidence score
        5. Build ClassificationResult with timing and diagnostics
        
        The method tracks preprocessing and total processing time for
        performance monitoring.
        
        Args:
            image: Input image as numpy array (H, W, C) in RGB format, uint8 [0-255]
            
        Returns:
            ClassificationResult containing:
                - severity: Predicted class ('none', 'moderate', or 'critical')
                - confidence: Confidence score (0.0 to 1.0)
                - processing_time_ms: Total processing time in milliseconds
                - model_name: 'SimpleStradClassifier'
                - threshold_used: 0.5 (currently unused)
                - raw_output: Dictionary with diagnostic information:
                    - model_name: 'SimpleStradClassifier'
                    - device: Device used for inference
                    - image_size: Input image size
                    - preprocessing_time_ms: Preprocessing time
                    - class_probabilities: Dict of probabilities for each class
        """
        start_time = time.time()
        
        # Preprocess
        preprocess_start = time.time()
        input_tensor = self._preprocess_image(image)
        preprocess_time = (time.time() - preprocess_start) * 1000  # ms
        
        # Inference
        with torch.no_grad():
            outputs = self.model(input_tensor)
            probabilities = torch.softmax(outputs, dim=1)
            confidence, predicted = probabilities.max(1)
        
        # Get results
        severity = self.class_names[predicted.item()]
        confidence_score = confidence.item()
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000  # ms
        
        # Build raw output dictionary with diagnostic information
        raw_output = {
            'model_name': 'SimpleStradClassifier',
            'device': str(self.device),
            'image_size': self.image_size,
            'preprocessing_time_ms': preprocess_time,
            'class_probabilities': {
                self.class_names[i]: probabilities[0][i].item()
                for i in range(len(self.class_names))
            }
        }
        
        return ClassificationResult(
            severity=severity,
            confidence=confidence_score,
            processing_time_ms=processing_time,
            model_name='SimpleStradClassifier',
            threshold_used=0.5,
            raw_output=raw_output
        )
