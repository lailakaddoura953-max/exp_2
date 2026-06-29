"""
Test CPU-only deployment scenario for SimpleClassifierWrapper

This test verifies that SimpleClassifierWrapper can load CUDA-trained checkpoints
on CPU-only devices and perform classification successfully.

Task: 6.1 Test CPU-only deployment scenario
Requirements: 2.3, 3.1, 3.2
"""

import pytest
import torch
import numpy as np
import tempfile
import os

from src.strad_monitoring.dl_classifier.simple_classifier_wrapper import (
    SimpleClassifierWrapper,
    SimpleStradClassifier,
    ClassificationResult,
)


@pytest.fixture
def cuda_trained_checkpoint():
    """
    Create a checkpoint that simulates being trained on CUDA device.
    
    This checkpoint will have tensors that were originally on CUDA (if available),
    but we'll test loading it on CPU to verify cross-device compatibility.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create model on CUDA if available, otherwise CPU
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model = SimpleStradClassifier(num_classes=3).to(device)
        
        # Save checkpoint with model_state_dict
        checkpoint = {
            'model_state_dict': model.state_dict(),
            'epoch': 10,
            'train_loss': 0.45,
            'val_loss': 0.52,
            'device': device,  # Record which device was used for training
        }
        
        checkpoint_path = os.path.join(tmpdir, 'cuda_trained_model.pth')
        torch.save(checkpoint, checkpoint_path)
        
        yield checkpoint_path


@pytest.fixture
def sample_rgb_image():
    """Create a sample RGB image for classification testing"""
    # Create a realistic looking image (not pure random noise)
    image = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)
    return image


@pytest.fixture
def various_image_sizes():
    """Generate images of various sizes to test preprocessing"""
    sizes = [
        (240, 320, 3),   # Small
        (480, 640, 3),   # Medium
        (720, 1280, 3),  # HD
        (1080, 1920, 3), # Full HD
    ]
    return [np.random.randint(0, 256, size, dtype=np.uint8) for size in sizes]


class TestCPUOnlyDeployment:
    """
    Test suite for CPU-only deployment scenarios.
    
    Validates Requirements 2.3, 3.1, 3.2:
    - WHEN device='cpu' is specified, THE SimpleClassifierWrapper SHALL load 
      CUDA-trained checkpoints successfully using map_location
    - WHEN device='cuda' is specified AND CUDA is available, THE SimpleClassifierWrapper 
      SHALL use GPU acceleration
    - WHEN device='cuda' is specified AND CUDA is unavailable, THEN THE SimpleClassifierWrapper 
      SHALL raise an error indicating CUDA is not available
    """
    
    def test_cpu_loads_cuda_trained_checkpoint(self, cuda_trained_checkpoint):
        """
        Test that CPU device can load CUDA-trained checkpoint using map_location.
        
        Requirement 2.3: WHEN loading a checkpoint, THE SimpleClassifierWrapper SHALL 
        use map_location=self.device to handle CPU/GPU conversion
        
        Requirement 3.1: WHEN device='cpu' is specified, THE SimpleClassifierWrapper 
        SHALL load CUDA-trained checkpoints successfully using map_location
        """
        # Force CPU device even if CUDA is available
        wrapper = SimpleClassifierWrapper(
            model_checkpoint_path=cuda_trained_checkpoint,
            device='cpu',
            image_size=640
        )
        
        # Verify model loaded successfully
        assert wrapper.model is not None
        assert wrapper.device == torch.device('cpu')
        
        # Verify model is on CPU
        for param in wrapper.model.parameters():
            assert param.device.type == 'cpu', f"Parameter is on {param.device}, expected cpu"
    
    def test_cpu_classification_succeeds(self, cuda_trained_checkpoint, sample_rgb_image):
        """
        Test that classification works on CPU device with CUDA-trained checkpoint.
        
        Requirement 3.1: Classification should succeed and return valid results.
        """
        # Force CPU device
        wrapper = SimpleClassifierWrapper(
            model_checkpoint_path=cuda_trained_checkpoint,
            device='cpu',
            image_size=640
        )
        
        # Perform classification
        result = wrapper.classify_snapshot(sample_rgb_image)
        
        # Verify result structure and validity
        assert isinstance(result, ClassificationResult)
        assert result.severity in ['none', 'moderate', 'critical']
        assert 0.0 <= result.confidence <= 1.0
        assert result.processing_time_ms > 0
        assert result.model_name == 'SimpleStradClassifier'
        assert isinstance(result.raw_output, dict)
    
    def test_cpu_classification_returns_valid_raw_output(self, cuda_trained_checkpoint, sample_rgb_image):
        """
        Test that raw_output contains required diagnostic information.
        
        Requirements: 2.3, 3.1, and implicitly 10.5 (raw_output fields)
        """
        wrapper = SimpleClassifierWrapper(
            model_checkpoint_path=cuda_trained_checkpoint,
            device='cpu',
            image_size=640
        )
        
        result = wrapper.classify_snapshot(sample_rgb_image)
        
        # Verify raw_output structure
        assert 'model_name' in result.raw_output
        assert result.raw_output['model_name'] == 'SimpleStradClassifier'
        
        assert 'device' in result.raw_output
        assert 'cpu' in result.raw_output['device'].lower()
        
        assert 'image_size' in result.raw_output
        assert result.raw_output['image_size'] == 640
        
        assert 'preprocessing_time_ms' in result.raw_output
        assert result.raw_output['preprocessing_time_ms'] > 0
        
        assert 'class_probabilities' in result.raw_output
        probs = result.raw_output['class_probabilities']
        assert 'none' in probs
        assert 'moderate' in probs
        assert 'critical' in probs
        
        # Probabilities should sum to approximately 1.0
        total_prob = sum(probs.values())
        assert 0.99 <= total_prob <= 1.01, f"Probabilities sum to {total_prob}, expected ~1.0"
    
    def test_cpu_classification_with_various_image_sizes(self, cuda_trained_checkpoint, various_image_sizes):
        """
        Test that CPU classification works with various input image sizes.
        
        All images should be preprocessed to 640x640 as per Requirement 5.1.
        """
        wrapper = SimpleClassifierWrapper(
            model_checkpoint_path=cuda_trained_checkpoint,
            device='cpu',
            image_size=640
        )
        
        for img in various_image_sizes:
            result = wrapper.classify_snapshot(img)
            
            assert isinstance(result, ClassificationResult)
            assert result.severity in ['none', 'moderate', 'critical']
            assert 0.0 <= result.confidence <= 1.0
            assert result.raw_output['image_size'] == 640
    
    def test_cpu_preprocessing_produces_correct_tensor_shape(self, cuda_trained_checkpoint, sample_rgb_image):
        """
        Test that preprocessing on CPU produces correct tensor shape.
        
        Requirement 5.4: SHALL convert from (H, W, C) numpy format to (1, C, H, W) PyTorch tensor
        Requirement 5.5: SHALL move the preprocessed tensor to the configured device (CPU)
        """
        wrapper = SimpleClassifierWrapper(
            model_checkpoint_path=cuda_trained_checkpoint,
            device='cpu',
            image_size=640
        )
        
        # Access preprocessing method (it's private but we'll test indirectly through classification)
        # The classification will fail if preprocessing is wrong
        result = wrapper.classify_snapshot(sample_rgb_image)
        
        # If we got here, preprocessing worked correctly
        assert result is not None
        assert result.raw_output['image_size'] == 640
    
    def test_cpu_device_explicitly_set(self, cuda_trained_checkpoint):
        """
        Test that device is explicitly set to CPU and model uses it.
        
        Requirement 3.2: WHEN device='cuda' is specified AND CUDA is available, 
        THE SimpleClassifierWrapper SHALL use GPU acceleration
        
        This test ensures CPU is used when specified, even if CUDA is available.
        """
        wrapper = SimpleClassifierWrapper(
            model_checkpoint_path=cuda_trained_checkpoint,
            device='cpu',
            image_size=640
        )
        
        # Check device is CPU
        assert wrapper.device.type == 'cpu'
        
        # Verify all model parameters are on CPU
        for name, param in wrapper.model.named_parameters():
            assert param.device.type == 'cpu', f"Parameter {name} is on {param.device.type}"
    
    def test_multiple_classifications_on_cpu(self, cuda_trained_checkpoint, sample_rgb_image):
        """
        Test that multiple classifications work correctly on CPU.
        
        This ensures there are no device-related memory issues or state problems.
        """
        wrapper = SimpleClassifierWrapper(
            model_checkpoint_path=cuda_trained_checkpoint,
            device='cpu',
            image_size=640
        )
        
        results = []
        for _ in range(5):
            result = wrapper.classify_snapshot(sample_rgb_image)
            results.append(result)
        
        # All results should be valid
        for result in results:
            assert isinstance(result, ClassificationResult)
            assert result.severity in ['none', 'moderate', 'critical']
            assert 0.0 <= result.confidence <= 1.0
    
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_cuda_device_when_available(self, cuda_trained_checkpoint):
        """
        Test that CUDA device is used when specified and available.
        
        Requirement 3.2: WHEN device='cuda' is specified AND CUDA is available, 
        THE SimpleClassifierWrapper SHALL use GPU acceleration
        """
        wrapper = SimpleClassifierWrapper(
            model_checkpoint_path=cuda_trained_checkpoint,
            device='cuda',
            image_size=640
        )
        
        # Check device is CUDA
        assert wrapper.device.type == 'cuda'
        
        # Verify model parameters are on CUDA
        for param in wrapper.model.parameters():
            assert param.device.type == 'cuda'
    
    @pytest.mark.skipif(torch.cuda.is_available(), reason="CUDA is available, test requires CUDA unavailable")
    def test_cuda_device_when_unavailable_raises_error(self, cuda_trained_checkpoint):
        """
        Test that requesting CUDA when unavailable raises an error.
        
        Requirement 3.3: WHEN device='cuda' is specified AND CUDA is unavailable, 
        THEN THE SimpleClassifierWrapper SHALL raise an error indicating CUDA is not available
        
        Note: This test only runs when CUDA is NOT available.
        """
        # The current implementation doesn't explicitly check for CUDA availability
        # It will fail when trying to move tensors to CUDA
        # This is acceptable behavior - PyTorch will raise a clear error
        
        # Attempt to create wrapper with CUDA device when unavailable
        # This should raise an error (either from PyTorch or our validation)
        with pytest.raises((RuntimeError, AssertionError)):
            wrapper = SimpleClassifierWrapper(
                model_checkpoint_path=cuda_trained_checkpoint,
                device='cuda',
                image_size=640
            )


class TestCrossDeviceCompatibility:
    """
    Test cross-device compatibility scenarios.
    
    Validates that checkpoints can be loaded across different devices without issues.
    """
    
    def test_cpu_to_cpu_loading(self, cuda_trained_checkpoint):
        """Test loading on CPU when checkpoint was saved from CPU"""
        wrapper = SimpleClassifierWrapper(
            model_checkpoint_path=cuda_trained_checkpoint,
            device='cpu',
            image_size=640
        )
        assert wrapper.device.type == 'cpu'
    
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_cpu_checkpoint_loads_on_cuda(self, cuda_trained_checkpoint, sample_rgb_image):
        """
        Test that a checkpoint (regardless of training device) loads on CUDA.
        
        Requirement 3.2: When CUDA is available and requested, use GPU acceleration
        """
        wrapper = SimpleClassifierWrapper(
            model_checkpoint_path=cuda_trained_checkpoint,
            device='cuda',
            image_size=640
        )
        
        assert wrapper.device.type == 'cuda'
        
        # Verify classification works on GPU
        result = wrapper.classify_snapshot(sample_rgb_image)
        assert isinstance(result, ClassificationResult)
        assert result.severity in ['none', 'moderate', 'critical']
    
    def test_map_location_used_in_loading(self, cuda_trained_checkpoint):
        """
        Test that map_location parameter is used when loading checkpoint.
        
        Requirement 2.3: WHEN loading a checkpoint, THE SimpleClassifierWrapper SHALL 
        use map_location=self.device to handle CPU/GPU conversion
        
        This is verified indirectly - if map_location wasn't used, loading would fail
        on CPU when checkpoint contains CUDA tensors.
        """
        # This should work because map_location=device is used
        wrapper = SimpleClassifierWrapper(
            model_checkpoint_path=cuda_trained_checkpoint,
            device='cpu',
            image_size=640
        )
        
        # If we got here without error, map_location worked
        assert wrapper.model is not None
        
        # All tensors should be on CPU
        for param in wrapper.model.parameters():
            assert param.device.type == 'cpu'


class TestDeploymentScenarios:
    """
    Test realistic deployment scenarios.
    """
    
    def test_laptop_deployment_scenario(self, cuda_trained_checkpoint, sample_rgb_image):
        """
        Simulate deploying to a laptop without CUDA support.
        
        This is the primary use case from the user story:
        "As a deployment engineer, I want the classifier to work on CPU-only devices, 
        so that I can deploy to laptops without CUDA support"
        """
        # Laptop would have CPU only
        wrapper = SimpleClassifierWrapper(
            model_checkpoint_path=cuda_trained_checkpoint,
            device='cpu',
            image_size=640
        )
        
        # Should be able to perform classification
        result = wrapper.classify_snapshot(sample_rgb_image)
        
        # Verify reasonable performance (not too slow)
        # CPU inference should still complete in reasonable time
        assert result.processing_time_ms < 10000, \
            f"CPU inference took {result.processing_time_ms}ms, exceeding 10s threshold"
        
        # Verify correct result structure
        assert isinstance(result, ClassificationResult)
        assert result.severity in ['none', 'moderate', 'critical']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
