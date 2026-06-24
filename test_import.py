"""Quick import test"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

try:
    from dl_misalignment.training.trainer import Trainer, MisalignmentLoss, CheckpointManager
    print("✓ Training modules imported successfully")
    
    from dl_misalignment.models.cnn_feature_extractor import CNNFeatureExtractor
    from dl_misalignment.models.liteflownet2 import LiteFlowNet2
    from dl_misalignment.models.spynet import SpyNet
    from dl_misalignment.models.pose_estimator import PoseEstimator
    print("✓ All model modules imported successfully")
    
    print("\nAll imports successful! Training pipeline is ready.")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
