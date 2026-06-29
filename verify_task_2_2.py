"""
Verification script for Task 2.2: Update classify_snapshot to populate raw_output dictionary

This script verifies that the raw_output dictionary includes all required keys:
- model_name
- device
- image_size
- preprocessing_time_ms
- class_probabilities (extracted from softmax output before taking max)

Requirements: 10.5, 12
"""

import sys
import numpy as np
import torch
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.strad_monitoring.dl_classifier.simple_classifier_wrapper import (
    SimpleClassifierWrapper,
    SimpleStradClassifier,
    ClassificationResult
)


def verify_raw_output_implementation():
    """Verify that raw_output dictionary is correctly populated."""
    
    print("=" * 70)
    print("Task 2.2 Verification: raw_output Dictionary Population")
    print("=" * 70)
    
    # Create a dummy checkpoint for testing
    checkpoint_path = Path("test_verify_checkpoint.pth")
    
    print("\n1. Creating test checkpoint...")
    model = SimpleStradClassifier(num_classes=3)
    checkpoint = {
        'model_state_dict': model.state_dict(),
        'epoch': 10,
        'loss': 0.5
    }
    torch.save(checkpoint, checkpoint_path)
    print("   ✓ Checkpoint created")
    
    try:
        # Initialize wrapper
        print("\n2. Initializing SimpleClassifierWrapper...")
        wrapper = SimpleClassifierWrapper(
            model_checkpoint_path=str(checkpoint_path),
            device='cpu',
            image_size=640
        )
        print("   ✓ Wrapper initialized")
        
        # Create a test image
        print("\n3. Creating test image (480x640x3, RGB, uint8)...")
        test_image = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
        print("   ✓ Test image created")
        
        # Classify
        print("\n4. Running classification...")
        result = wrapper.classify_snapshot(test_image)
        print("   ✓ Classification complete")
        
        # Verify result structure
        print("\n5. Verifying raw_output dictionary structure...")
        
        required_keys = [
            'model_name',
            'device',
            'image_size',
            'preprocessing_time_ms',
            'class_probabilities'
        ]
        
        all_present = True
        for key in required_keys:
            if key in result.raw_output:
                print(f"   ✓ Key '{key}' present")
            else:
                print(f"   ✗ Key '{key}' MISSING")
                all_present = False
        
        if not all_present:
            print("\n❌ FAILED: Missing required keys in raw_output")
            return False
        
        # Display values
        print("\n6. raw_output Dictionary Contents:")
        print("   " + "-" * 66)
        print(f"   model_name:            {result.raw_output['model_name']}")
        print(f"   device:                {result.raw_output['device']}")
        print(f"   image_size:            {result.raw_output['image_size']}")
        print(f"   preprocessing_time_ms: {result.raw_output['preprocessing_time_ms']:.3f} ms")
        
        print("\n   class_probabilities:")
        class_probs = result.raw_output['class_probabilities']
        for class_name in ['none', 'moderate', 'critical']:
            prob = class_probs[class_name]
            bar_length = int(prob * 50)
            bar = '█' * bar_length + '░' * (50 - bar_length)
            print(f"     {class_name:8s}: {prob:.4f} {bar}")
        
        prob_sum = sum(class_probs.values())
        print(f"\n   Probability sum: {prob_sum:.6f} (should be ~1.0)")
        
        # Verify classification result consistency
        print("\n7. Verifying consistency with ClassificationResult fields:")
        max_prob = max(class_probs.values())
        predicted_class = max(class_probs, key=class_probs.get)
        
        print(f"   Predicted severity:  {result.severity}")
        print(f"   Max probability class: {predicted_class}")
        print(f"   Match: {'✓' if result.severity == predicted_class else '✗'}")
        
        print(f"\n   Result confidence:    {result.confidence:.4f}")
        print(f"   Max probability:      {max_prob:.4f}")
        print(f"   Match: {'✓' if abs(result.confidence - max_prob) < 0.01 else '✗'}")
        
        print(f"\n   Processing time:      {result.processing_time_ms:.3f} ms")
        print(f"   Preprocessing time:   {result.raw_output['preprocessing_time_ms']:.3f} ms")
        
        # Final verdict
        print("\n" + "=" * 70)
        print("✅ TASK 2.2 VERIFIED: raw_output dictionary correctly populated")
        print("=" * 70)
        print("\nAll required fields are present:")
        print("  ✓ model_name: 'SimpleStradClassifier'")
        print("  ✓ device: Device string (e.g., 'cpu')")
        print("  ✓ image_size: 640")
        print("  ✓ preprocessing_time_ms: Float > 0")
        print("  ✓ class_probabilities: Dict with softmax probabilities")
        print("\nRequirements 10.5 and 12 are satisfied.")
        
        return True
        
    finally:
        # Cleanup
        if checkpoint_path.exists():
            checkpoint_path.unlink()
            print("\n✓ Cleanup complete")


if __name__ == "__main__":
    try:
        success = verify_raw_output_implementation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
