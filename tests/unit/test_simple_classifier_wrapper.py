"""
Unit tests for SimpleClassifierWrapper checkpoint format validation
"""

import pytest
import torch
import numpy as np
from pathlib import Path
import tempfile
import os

from src.strad_monitoring.dl_classifier.simple_classifier_wrapper import (
    SimpleClassifierWrapper,
    SimpleStradClassifier,
    ClassificationResult,
)


@pytest.fixture
def temp_checkpoint_dir():
    """Create a temporary directory for checkpoint files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def valid_checkpoint(temp_checkpoint_dir):
    """Create a valid checkpoint with model_state_dict key"""
    # Create a simple model to get state dict
    model = SimpleStradClassifier(num_classes=3)
    
    checkpoint = {
        'model_state_dict': model.state_dict(),
        'epoch': 10,
        'train_loss': 0.5,
        'val_loss': 0.6,
    }
    
    checkpoint_path = os.path.join(temp_checkpoint_dir, 'valid_checkpoint.pth')
    torch.save(checkpoint, checkpoint_path)
    
    return checkpoint_path


@pytest.fixture
def inference_engine_checkpoint(temp_checkpoint_dir):
    """Create an InferenceEngine-style checkpoint (missing model_state_dict key)"""
    model = SimpleStradClassifier(num_classes=3)
    
    checkpoint = {
        'feature_extractor_state': model.state_dict(),  # Wrong key for SimpleClassifierWrapper
        'epoch': 10,
        'train_loss': 0.5,
    }
    
    checkpoint_path = os.path.join(temp_checkpoint_dir, 'inference_engine_checkpoint.pth')
    torch.save(checkpoint, checkpoint_path)
    
    return checkpoint_path


@pytest.fixture
def empty_checkpoint(temp_checkpoint_dir):
    """Create an empty checkpoint with no keys"""
    checkpoint = {}
    
    checkpoint_path = os.path.join(temp_checkpoint_dir, 'empty_checkpoint.pth')
    torch.save(checkpoint, checkpoint_path)
    
    return checkpoint_path


@pytest.fixture
def sample_image():
    """Create a sample RGB image for testing classification"""
    return np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)


class TestCheckpointFormatValidation:
    """Test suite for checkpoint format validation (Requirements 2.4, 2.5, 9.4)"""
    
    def test_valid_checkpoint_loads_successfully(self, valid_checkpoint):
        """Test that a valid checkpoint with model_state_dict key loads successfully"""
        # Should not raise any exception
        wrapper = SimpleClassifierWrapper(
            model_checkpoint_path=valid_checkpoint,
            device='cpu',
            image_size=640
        )
        
        assert wrapper.model is not None
        assert wrapper.model_checkpoint_path == valid_checkpoint
    
    def test_missing_model_state_dict_raises_key_error(self, inference_engine_checkpoint):
        """Test that checkpoint without model_state_dict key raises KeyError (Requirement 2.5)"""
        with pytest.raises(KeyError) as exc_info:
            SimpleClassifierWrapper(
                model_checkpoint_path=inference_engine_checkpoint,
                device='cpu',
                image_size=640
            )
        
        # Verify the error message
        error_message = str(exc_info.value)
        assert 'model_state_dict' in error_message
        # Check that the checkpoint filename is in the message (account for path separators)
        assert 'inference_engine_checkpoint.pth' in error_message
    
    def test_error_message_suggests_inference_engine(self, inference_engine_checkpoint):
        """Test that error message suggests using classifier_type='inference_engine' (Requirement 9.4)"""
        with pytest.raises(KeyError) as exc_info:
            SimpleClassifierWrapper(
                model_checkpoint_path=inference_engine_checkpoint,
                device='cpu',
                image_size=640
            )
        
        error_message = str(exc_info.value)
        # Check that the error suggests the correct classifier type
        assert "classifier_type='inference_engine'" in error_message
        assert 'InferenceEngine' in error_message
    
    def test_error_message_mentions_training_script(self, inference_engine_checkpoint):
        """Test that error message mentions train_strad_classifier.py (Requirement 2.4)"""
        with pytest.raises(KeyError) as exc_info:
            SimpleClassifierWrapper(
                model_checkpoint_path=inference_engine_checkpoint,
                device='cpu',
                image_size=640
            )
        
        error_message = str(exc_info.value)
        assert 'train_strad_classifier.py' in error_message
    
    def test_empty_checkpoint_raises_key_error(self, empty_checkpoint):
        """Test that an empty checkpoint raises KeyError"""
        with pytest.raises(KeyError) as exc_info:
            SimpleClassifierWrapper(
                model_checkpoint_path=empty_checkpoint,
                device='cpu',
                image_size=640
            )
        
        error_message = str(exc_info.value)
        assert 'model_state_dict' in error_message
    
    def test_validation_happens_before_model_load(self, inference_engine_checkpoint):
        """Test that validation happens before attempting to load weights into model"""
        # This should fail at validation stage, not at model.load_state_dict()
        with pytest.raises(KeyError) as exc_info:
            SimpleClassifierWrapper(
                model_checkpoint_path=inference_engine_checkpoint,
                device='cpu',
                image_size=640
            )
        
        # KeyError from validation, not from load_state_dict
        assert 'model_state_dict' in str(exc_info.value)
    
    def test_valid_checkpoint_works_end_to_end(self, valid_checkpoint, sample_image):
        """Test that a valid checkpoint can be loaded and used for classification"""
        wrapper = SimpleClassifierWrapper(
            model_checkpoint_path=valid_checkpoint,
            device='cpu',
            image_size=640
        )
        
        # Should be able to classify an image
        result = wrapper.classify_snapshot(sample_image)
        
        assert isinstance(result, ClassificationResult)
        assert result.severity in ['none', 'moderate', 'critical']
        assert 0.0 <= result.confidence <= 1.0
        assert result.processing_time_ms > 0
    
    def test_checkpoint_path_included_in_error(self, inference_engine_checkpoint):
        """Test that the checkpoint path is included in error message for debugging"""
        with pytest.raises(KeyError) as exc_info:
            SimpleClassifierWrapper(
                model_checkpoint_path=inference_engine_checkpoint,
                device='cpu',
                image_size=640
            )
        
        # The checkpoint filename should be in the error message
        error_message = str(exc_info.value)
        assert 'inference_engine_checkpoint.pth' in error_message


class TestCheckpointCompatibility:
    """Test checkpoint compatibility across different scenarios"""
    
    def test_checkpoint_with_extra_keys_loads_successfully(self, temp_checkpoint_dir):
        """Test that checkpoint with additional metadata keys still loads"""
        model = SimpleStradClassifier(num_classes=3)
        
        checkpoint = {
            'model_state_dict': model.state_dict(),
            'epoch': 10,
            'optimizer_state_dict': {},  # Extra key
            'lr_scheduler_state_dict': {},  # Extra key
            'metrics': {'accuracy': 0.95},  # Extra key
            'config': {'batch_size': 32},  # Extra key
        }
        
        checkpoint_path = os.path.join(temp_checkpoint_dir, 'checkpoint_with_extras.pth')
        torch.save(checkpoint, checkpoint_path)
        
        # Should load successfully despite extra keys
        wrapper = SimpleClassifierWrapper(
            model_checkpoint_path=checkpoint_path,
            device='cpu',
            image_size=640
        )
        
        assert wrapper.model is not None
    
    def test_checkpoint_with_only_model_state_dict(self, temp_checkpoint_dir):
        """Test that checkpoint with only model_state_dict key (minimal) loads"""
        model = SimpleStradClassifier(num_classes=3)
        
        checkpoint = {
            'model_state_dict': model.state_dict(),
        }
        
        checkpoint_path = os.path.join(temp_checkpoint_dir, 'minimal_checkpoint.pth')
        torch.save(checkpoint, checkpoint_path)
        
        # Should load successfully
        wrapper = SimpleClassifierWrapper(
            model_checkpoint_path=checkpoint_path,
            device='cpu',
            image_size=640
        )
        
        assert wrapper.model is not None


class TestErrorMessageQuality:
    """Test that error messages are descriptive and helpful"""
    
    def test_error_message_is_descriptive(self, inference_engine_checkpoint):
        """Test that the error message provides clear guidance"""
        with pytest.raises(KeyError) as exc_info:
            SimpleClassifierWrapper(
                model_checkpoint_path=inference_engine_checkpoint,
                device='cpu',
                image_size=640
            )
        
        error_message = str(exc_info.value)
        
        # Check for key components of a helpful error message
        assert 'does not contain' in error_message
        assert 'model_state_dict' in error_message
        assert 'train_strad_classifier.py' in error_message
        assert "classifier_type='inference_engine'" in error_message
        assert 'system_config.json' in error_message
    
    def test_error_distinguishes_checkpoint_types(self, inference_engine_checkpoint):
        """Test that error clearly distinguishes between SimpleClassifier and InferenceEngine checkpoints"""
        with pytest.raises(KeyError) as exc_info:
            SimpleClassifierWrapper(
                model_checkpoint_path=inference_engine_checkpoint,
                device='cpu',
                image_size=640
            )
        
        error_message = str(exc_info.value)
        
        # Should mention both checkpoint types
        assert 'InferenceEngine' in error_message
        assert 'train_strad_classifier.py' in error_message


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
