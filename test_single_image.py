"""
Quick Test: Classify a Single Image

This script allows you to test the DL classifier on any image right now.
Works with local images, demo videos (frame extraction), or synthetic test data.

Usage:
    # Test with a local image file
    python test_single_image.py --image path/to/image.jpg
    
    # Test with first frame from demo video
    python test_single_image.py --demo
    
    # Test with synthetic random image
    python test_single_image.py --synthetic
"""

import argparse
import sys
from pathlib import Path
import numpy as np

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))


def load_image_from_file(image_path: str) -> np.ndarray:
    """Load image from file path."""
    from PIL import Image
    
    img = Image.open(image_path)
    
    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Resize to 640x640 if needed
    if img.size != (640, 640):
        print(f"Resizing image from {img.size} to (640, 640)")
        img = img.resize((640, 640))
    
    # Convert to numpy array
    return np.array(img)


def extract_frame_from_video(video_path: str, frame_number: int = 0) -> np.ndarray:
    """Extract a frame from video file."""
    import cv2
    
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")
    
    # Set frame position
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    
    # Read frame
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise ValueError(f"Cannot read frame {frame_number} from video")
    
    # Convert BGR to RGB
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Resize to 640x640
    if frame.shape[:2] != (640, 640):
        frame = cv2.resize(frame, (640, 640))
    
    return frame


def create_synthetic_image() -> np.ndarray:
    """Create synthetic test image."""
    # Create a gradient pattern for visual interest
    x = np.linspace(0, 255, 640)
    y = np.linspace(0, 255, 640)
    X, Y = np.meshgrid(x, y)
    
    # Create RGB channels with different patterns
    r = ((X + Y) / 2).astype(np.uint8)
    g = (X).astype(np.uint8)
    b = (Y).astype(np.uint8)
    
    return np.stack([r, g, b], axis=-1)


def main():
    parser = argparse.ArgumentParser(
        description='Test DL classifier on a single image',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--image', type=str, help='Path to image file')
    parser.add_argument('--demo', action='store_true', help='Use frame from demo video')
    parser.add_argument('--synthetic', action='store_true', help='Use synthetic test image')
    parser.add_argument('--config', type=str, default='config/architecture_a.yaml',
                       help='Path to model config (default: config/architecture_a.yaml)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("SINGLE IMAGE CLASSIFICATION TEST")
    print("=" * 80)
    
    # Determine image source
    if args.image:
        print(f"\nLoading image from: {args.image}")
        try:
            image = load_image_from_file(args.image)
            source_name = Path(args.image).name
        except Exception as e:
            print(f"✗ Failed to load image: {e}")
            return 1
    
    elif args.demo:
        print("\nExtracting frame from demo video...")
        demo_video = project_root / 'demo_videos' / '01_normal_operation.mp4'
        
        if not demo_video.exists():
            print(f"✗ Demo video not found: {demo_video}")
            print("Available demo videos should be in demo_videos/ folder")
            return 1
        
        try:
            image = extract_frame_from_video(str(demo_video), frame_number=30)
            source_name = "demo_video_frame_30"
        except Exception as e:
            print(f"✗ Failed to extract frame: {e}")
            print("Note: Requires opencv-python (pip install opencv-python)")
            return 1
    
    elif args.synthetic:
        print("\nGenerating synthetic test image...")
        image = create_synthetic_image()
        source_name = "synthetic_gradient"
    
    else:
        print("✗ Please specify image source:")
        print("  --image PATH     : Use local image file")
        print("  --demo           : Use frame from demo video")
        print("  --synthetic      : Use synthetic test image")
        return 1
    
    print(f"✓ Image loaded: {image.shape} (H×W×C)")
    
    # Load DL classifier wrapper
    print("\n" + "-" * 80)
    print("Initializing DL Classifier...")
    print("-" * 80)
    
    try:
        from strad_monitoring.dl_classifier.classifier_wrapper import DLClassifierWrapper
        from strad_monitoring.config.system_config import ConfigurationManager
        import torch
        
        # Load configuration to get model path
        try:
            config = ConfigurationManager.load_config('system_config.json')
            model_checkpoint_path = config.model_checkpoint_path
            dl_config = config.dl_model_config
        except Exception as e:
            print(f"⚠ Could not load system_config.json: {e}")
            print("Using default model path from config YAML")
            model_checkpoint_path = None
            dl_config = args.config
        
        # Initialize classifier
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Using device: {device}")
        
        if model_checkpoint_path:
            print(f"Model checkpoint: {model_checkpoint_path}")
        print(f"Model config: {dl_config}")
        
        classifier = DLClassifierWrapper(
            model_checkpoint_path=model_checkpoint_path,
            config=dl_config,
            device=device
        )
        
        print("✓ DL Classifier initialized")
        
    except FileNotFoundError as e:
        print(f"\n✗ Model checkpoint not found: {e}")
        print("\nTo use the classifier, you need a trained model checkpoint.")
        print("Options:")
        print("  1. Train a model using: python scripts/train_architecture_a.py")
        print("  2. Download a pre-trained checkpoint")
        print("  3. Update model_checkpoint_path in system_config.json")
        return 1
    
    except Exception as e:
        print(f"✗ Failed to initialize classifier: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Classify image
    print("\n" + "-" * 80)
    print("Classifying image...")
    print("-" * 80)
    
    try:
        result = classifier.classify_snapshot(image)
        
        print("\n" + "=" * 80)
        print("CLASSIFICATION RESULTS")
        print("=" * 80)
        print(f"\nImage source: {source_name}")
        print(f"Image shape: {image.shape}")
        print()
        print(f"Classification: {result.severity.upper()}")
        print(f"Confidence: {result.confidence:.3f}")
        print(f"Processing time: {result.processing_time_ms:.1f} ms")
        print()
        
        # Interpret results
        print("-" * 80)
        print("INTERPRETATION")
        print("-" * 80)
        
        if result.severity == 'critical':
            print("🔴 CRITICAL MISALIGNMENT DETECTED")
            print("   Action: Camera requires immediate adjustment")
            print("   System: Will exclude from monitoring rotation until confirmed")
            print("   Snapshot: Will be saved to permanent storage")
        
        elif result.severity == 'moderate':
            print("🟡 MODERATE MISALIGNMENT DETECTED")
            print("   Action: Continue monitoring in regular rotation")
            print("   System: Will track consecutive occurrences")
            print("   Warning: Notification after 3 consecutive moderate results")
        
        else:  # 'none'
            print("🟢 NO MISALIGNMENT DETECTED")
            print("   Action: Camera is properly aligned")
            print("   System: Continue normal monitoring")
        
        print()
        
        # Additional notes
        if result.confidence < 0.6:
            print("⚠ LOW CONFIDENCE WARNING")
            print(f"   Confidence ({result.confidence:.3f}) is below 0.6 threshold")
            print("   System assigns 'moderate' classification as conservative default")
            print()
        
        if result.confidence == 0.0:
            print("⚠ ZERO CONFIDENCE ALERT")
            print("   This triggers an alert to operations technology developers")
            print()
        
        print("=" * 80)
        print("✓ Classification completed successfully")
        print("=" * 80)
        
        return 0
    
    except Exception as e:
        print(f"\n✗ Classification failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
