"""
Synthetic Data Generation Script

This script generates augmented copies of your training data to balance classes
and increase dataset size. Uses realistic augmentations for strad imagery.

Usage:
    python generate_synthetic_data.py --input SCFootage --output SCFootage_augmented --target_per_class 100

Features:
- Balances classes to equal counts
- Applies realistic augmentations (rotation, flip, brightness, noise)
- Preserves original data alongside synthetic copies
- Handles both images and video frames
"""

import argparse
import sys
from pathlib import Path
import shutil
import cv2
import numpy as np
from PIL import Image, ImageEnhance
import random
from tqdm import tqdm


class DataAugmenter:
    """
    Realistic data augmentation for strad imagery.
    """
    
    @staticmethod
    def random_rotation(image, max_angle=15):
        """Rotate image by random angle."""
        angle = random.uniform(-max_angle, max_angle)
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, matrix, (w, h), 
                                 borderMode=cv2.BORDER_REFLECT)
        return rotated
    
    @staticmethod
    def random_flip(image):
        """Randomly flip image horizontally."""
        if random.random() > 0.5:
            return cv2.flip(image, 1)
        return image
    
    @staticmethod
    def random_brightness(image, factor_range=(0.7, 1.3)):
        """Adjust brightness randomly."""
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        enhancer = ImageEnhance.Brightness(pil_image)
        factor = random.uniform(*factor_range)
        enhanced = enhancer.enhance(factor)
        return cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)
    
    @staticmethod
    def random_contrast(image, factor_range=(0.8, 1.2)):
        """Adjust contrast randomly."""
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        enhancer = ImageEnhance.Contrast(pil_image)
        factor = random.uniform(*factor_range)
        enhanced = enhancer.enhance(factor)
        return cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2BGR)
    
    @staticmethod
    def add_gaussian_noise(image, sigma_range=(5, 15)):
        """Add Gaussian noise."""
        sigma = random.uniform(*sigma_range)
        noise = np.random.normal(0, sigma, image.shape).astype(np.float32)
        noisy = image.astype(np.float32) + noise
        noisy = np.clip(noisy, 0, 255).astype(np.uint8)
        return noisy
    
    @staticmethod
    def random_translation(image, max_shift=0.1):
        """Randomly translate image."""
        h, w = image.shape[:2]
        tx = int(random.uniform(-max_shift, max_shift) * w)
        ty = int(random.uniform(-max_shift, max_shift) * h)
        matrix = np.float32([[1, 0, tx], [0, 1, ty]])
        translated = cv2.warpAffine(image, matrix, (w, h),
                                    borderMode=cv2.BORDER_REFLECT)
        return translated
    
    @staticmethod
    def random_blur(image, kernel_size_range=(3, 7)):
        """Apply random Gaussian blur."""
        if random.random() > 0.5:
            kernel_size = random.choice(range(kernel_size_range[0], 
                                             kernel_size_range[1] + 1, 2))
            return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
        return image
    
    def augment(self, image, num_augmentations=3):
        """
        Apply random augmentations to image.
        
        Args:
            image: Input image (BGR format)
            num_augmentations: Number of augmentations to apply
            
        Returns:
            Augmented image
        """
        augmentations = [
            self.random_rotation,
            self.random_flip,
            self.random_brightness,
            self.random_contrast,
            self.add_gaussian_noise,
            self.random_translation,
            self.random_blur
        ]
        
        # Randomly select augmentations
        selected = random.sample(augmentations, 
                                min(num_augmentations, len(augmentations)))
        
        augmented = image.copy()
        for aug_func in selected:
            augmented = aug_func(augmented)
        
        return augmented


def extract_video_frame(video_path, frame_index=-1):
    """Extract frame from video."""
    cap = cv2.VideoCapture(str(video_path))
    
    try:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if frame_index < 0:
            frame_index = total_frames // 2
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = cap.read()
        
        if not ret:
            raise ValueError(f"Failed to read frame from {video_path}")
        
        return frame
    
    finally:
        cap.release()


def scan_dataset(input_dir):
    """
    Scan dataset and count samples per class.
    
    Returns:
        dict: {class_name: [file_paths]}
    """
    input_dir = Path(input_dir)
    class_mapping = {
        'misaligned - none': 'none',
        'misaligned - moderate': 'moderate',
        'misaligned - critical': 'critical',
        'none': 'none',
        'moderate': 'moderate',
        'critical': 'critical'
    }
    
    dataset = {'none': [], 'moderate': [], 'critical': []}
    
    print(f"Scanning dataset: {input_dir}")
    
    for class_folder in input_dir.iterdir():
        if not class_folder.is_dir():
            continue
        
        class_key = class_folder.name.lower()
        if class_key not in class_mapping:
            print(f"  Warning: Unknown class folder '{class_folder.name}' - skipping")
            continue
        
        class_name = class_mapping[class_key]
        
        # Scan all strad folders
        for strad_folder in class_folder.iterdir():
            if not strad_folder.is_dir():
                continue
            
            # Find all images and videos
            for file_path in strad_folder.iterdir():
                if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.mp4', '.avi', '.mov']:
                    dataset[class_name].append(file_path)
    
    # Print statistics
    print(f"\nDataset statistics:")
    for class_name, files in dataset.items():
        print(f"  {class_name}: {len(files)} files")
    
    return dataset


def generate_synthetic_data(input_dir, output_dir, target_per_class=100):
    """
    Generate synthetic data by augmenting existing samples.
    
    Args:
        input_dir: Source data directory
        output_dir: Output directory for augmented data
        target_per_class: Target number of images per class
    """
    output_dir = Path(output_dir)
    augmenter = DataAugmenter()
    
    # Scan dataset
    dataset = scan_dataset(input_dir)
    
    # Create output directory structure
    output_dir.mkdir(exist_ok=True)
    
    class_output_dirs = {}
    for class_name in ['none', 'moderate', 'critical']:
        class_dir = output_dir / f'misaligned - {class_name}'
        class_dir.mkdir(exist_ok=True)
        class_output_dirs[class_name] = class_dir
    
    print(f"\n{'='*80}")
    print("GENERATING SYNTHETIC DATA")
    print("="*80)
    
    total_generated = 0
    
    for class_name, files in dataset.items():
        print(f"\nProcessing class: {class_name}")
        
        current_count = len(files)
        needed = target_per_class - current_count
        
        if needed <= 0:
            print(f"  Class already has {current_count} samples (target: {target_per_class})")
            print(f"  Copying original files...")
            
            # Just copy original files
            for i, file_path in enumerate(tqdm(files, desc=f"  Copying {class_name}")):
                # Load image/video
                if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                    image = cv2.imread(str(file_path))
                else:
                    image = extract_video_frame(str(file_path))
                
                # Save
                output_path = class_output_dirs[class_name] / f'{class_name}_{i:04d}_original.png'
                cv2.imwrite(str(output_path), image)
            
            continue
        
        print(f"  Current: {current_count}, Target: {target_per_class}, Generating: {needed}")
        
        # Calculate how many augmentations needed per original image
        augmentations_per_image = (needed + current_count - 1) // current_count
        
        print(f"  Augmentations per image: {augmentations_per_image}")
        
        sample_idx = 0
        
        # Process each original file
        for file_path in tqdm(files, desc=f"  Generating {class_name}"):
            # Load image/video
            if file_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                original_image = cv2.imread(str(file_path))
            else:
                original_image = extract_video_frame(str(file_path))
            
            # Save original
            output_path = class_output_dirs[class_name] / f'{class_name}_{sample_idx:04d}_original.png'
            cv2.imwrite(str(output_path), original_image)
            sample_idx += 1
            total_generated += 1
            
            # Generate augmented copies
            for aug_idx in range(augmentations_per_image):
                if sample_idx >= target_per_class:
                    break
                
                # Apply random augmentations
                augmented = augmenter.augment(original_image, 
                                             num_augmentations=random.randint(2, 4))
                
                # Save augmented
                output_path = class_output_dirs[class_name] / f'{class_name}_{sample_idx:04d}_aug{aug_idx}.png'
                cv2.imwrite(str(output_path), augmented)
                sample_idx += 1
                total_generated += 1
        
        print(f"  ✓ Generated {sample_idx} total samples for {class_name}")
    
    print(f"\n{'='*80}")
    print("GENERATION COMPLETE")
    print("="*80)
    print(f"\nTotal images generated: {total_generated}")
    print(f"Output directory: {output_dir}")
    print(f"\nFinal distribution:")
    for class_name in ['none', 'moderate', 'critical']:
        count = len(list(class_output_dirs[class_name].glob('*.png')))
        print(f"  {class_name}: {count} images")
    
    print(f"\nYou can now train with:")
    print(f"  python train_strad_classifier.py --data_dir {output_dir} --epochs 50")


def main():
    parser = argparse.ArgumentParser(
        description='Generate synthetic training data through augmentation'
    )
    parser.add_argument('--input', type=str, default='SCFootage',
                        help='Input directory with original data')
    parser.add_argument('--output', type=str, default='SCFootage_augmented',
                        help='Output directory for augmented data')
    parser.add_argument('--target_per_class', type=int, default=100,
                        help='Target number of images per class')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("SYNTHETIC DATA GENERATION")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Input directory: {args.input}")
    print(f"  Output directory: {args.output}")
    print(f"  Target per class: {args.target_per_class}")
    print(f"  Total target: {args.target_per_class * 3} images")
    
    # Check input exists
    if not Path(args.input).exists():
        print(f"\n✗ ERROR: Input directory not found: {args.input}")
        return 1
    
    # Generate synthetic data
    generate_synthetic_data(args.input, args.output, args.target_per_class)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
