"""
Test for SimpleClassifierWrapper raw_output field (Task 2.2)

This test verifies that the raw_output dictionary contains all required fields
as specified in Requirements 10.5 and 12.
"""

import pytest
import numpy as np
import torch
from pathlib import Path


def test_classify_snapshot_raw_output_structure():
    """
    Test that classify_snapshot populates raw_output with all required fields.
    
    Validates Requirements 10.5, 12:
    - model_name
    - device
    - image_size
    - preprocessing_time_ms
    - class_probabilities (extracted from softmax before max)
    """
    from src.strad_monitoring.dl_classifier.simple_classifier_wrapper import (
        SimpleClassifierWrapper,
        ClassificationResult
    )
    
    # Create a dummy checkpoint for testing
    checkpoint_path = Path("test_checkpoint.pth")
    
    # Create a simple model and save it
    from src.strad_monitoring.dl_classifier.simple_classifier_wrapper import SimpleStradClassifier
    model = SimpleStradClassifier(num_classes=3)
    
    checkpoint = {
        'model_state_dict': model.state_dict(),
        'epoch': 10,
        'loss': 0.5
    }
    
    torch.save(checkpoint, checkpoint_path)
    
    try:
        # Initialize wrapper
        wrapper = SimpleClassifierWrapper(
            model_checkpoint_path=str(checkpoint_path),
            device='cpu',
            image_size=640
        )
        
        # Create a test image (RGB, uint8)
        test_image = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
        
        # Classify
        result = wrapper.classify_snapshot(test_image)
        
        # Verify result structure
        assert isinstance(result, ClassificationResult)
        assert hasattr(result, 'raw_output')
        assert isinstance(result.raw_output, dict)
        
        # Verify required keys exist in raw_output
        required_keys = [
            'model_name',
            'device',
            'image_size',
            'preprocessing_time_ms',
            'class_probabilities'
        ]
        
        for key in required_keys:
            assert key in result.raw_output, f"Missing required key: {key}"
        
        # Verify field types and values
        assert result.raw_output['model_name'] == 'SimpleStradClassifier'
        assert isinstance(result.raw_output['device'], str)
        assert 'cpu' in result.raw_output['device'].lower()
        assert result.raw_output['image_size'] == 640
        assert isinstance(result.raw_output['preprocessing_time_ms'], float)
        assert result.raw_output['preprocessing_time_ms'] > 0
        
        # Verify class_probabilities structure
        class_probs = result.raw_output['class_probabilities']
        assert isinstance(class_probs, dict)
        assert len(class_probs) == 3  # none, moderate, critical
        assert 'none' in class_probs
        assert 'moderate' in class_probs
        assert 'critical' in class_probs
        
        # Verify probabilities are valid floats that sum to ~1.0
        for class_name, prob in class_probs.items():
            assert isinstance(prob, float)
            assert 0.0 <= prob <= 1.0
        
        prob_sum = sum(class_probs.values())
        assert abs(prob_sum - 1.0) < 0.01, f"Probabilities should sum to 1.0, got {prob_sum}"
        
        # Verify the confidence matches the max probability
        max_prob = max(class_probs.values())
        assert abs(result.confidence - max_prob) < 0.01, \
            f"Confidence {result.confidence} should match max probability {max_prob}"
        
        # Verify severity matches the class with max probability
        predicted_class = max(class_probs, key=class_probs.get)
        assert result.severity == predicted_class, \
            f"Severity {result.severity} should match class with max prob {predicted_class}"
        
        print("✓ All raw_output fields verified successfully")
        print(f"  - model_name: {result.raw_output['model_name']}")
        print(f"  - device: {result.raw_output['device']}")
        print(f"  - image_size: {result.raw_output['image_size']}")
        print(f"  - preprocessing_time_ms: {result.raw_output['preprocessing_time_ms']:.2f}")
        print(f"  - class_probabilities: {result.raw_output['class_probabilities']}")
        
    finally:
        # Cleanup
        if checkpoint_path.exists():
            checkpoint_path.unlink()


if __name__ == "__main__":
    test_classify_snapshot_raw_output_structure()
