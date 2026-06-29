"""
Quick script to check checkpoint format and determine which classifier to use
"""
import torch
import sys

def check_checkpoint_format(checkpoint_path):
    """Check what keys are in the checkpoint"""
    try:
        print(f"Loading checkpoint: {checkpoint_path}")
        checkpoint = torch.load(checkpoint_path, map_location='cpu')
        
        print("\n" + "="*60)
        print("CHECKPOINT KEYS:")
        print("="*60)
        
        if isinstance(checkpoint, dict):
            for key in checkpoint.keys():
                print(f"  - {key}")
            
            print("\n" + "="*60)
            print("RECOMMENDATION:")
            print("="*60)
            
            if 'model_state_dict' in checkpoint:
                print("✓ This checkpoint has 'model_state_dict'")
                print("✓ Use: classifier_type = 'simple_classifier'")
                print("✓ This model was trained with train_strad_classifier.py")
                return 'simple_classifier'
            
            elif 'feature_extractor_state' in checkpoint or 'feature_extractor' in checkpoint:
                print("✓ This checkpoint has 'feature_extractor_state'")
                print("✓ Use: classifier_type = 'inference_engine'")
                print("✓ This model was trained with multi-camera detector")
                return 'inference_engine'
            
            else:
                print("⚠ Unknown checkpoint format")
                print("Keys found:", list(checkpoint.keys()))
                return 'unknown'
        else:
            print("⚠ Checkpoint is not a dictionary")
            print(f"Type: {type(checkpoint)}")
            return 'unknown'
            
    except Exception as e:
        print(f"✗ Error loading checkpoint: {e}")
        return 'error'

if __name__ == "__main__":
    if len(sys.argv) > 1:
        checkpoint_path = sys.argv[1]
    else:
        # Default path from system_config.json
        checkpoint_path = "C:\\Models\\misalignment_detector_v2.pth"
    
    classifier_type = check_checkpoint_format(checkpoint_path)
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    
    if classifier_type == 'simple_classifier':
        print("1. Update system_config.json:")
        print('   "classifier_type": "simple_classifier"')
        print("\n2. Run the strad monitoring script")
    
    elif classifier_type == 'inference_engine':
        print("1. Update system_config.json:")
        print('   "classifier_type": "inference_engine"')
        print("\n2. Run the strad monitoring script")
    
    else:
        print("1. Check if the checkpoint path is correct")
        print("2. Verify the model was trained successfully")
        print("3. Re-train the model if necessary")
