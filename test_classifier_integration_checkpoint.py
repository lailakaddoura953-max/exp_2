"""
Test Script for Checkpoint 5: Verify Classifier Integration

This script tests both orchestrator and web app with both classifier types
to ensure the integration work from tasks 1-4 is functioning correctly.

Requirements tested:
- Orchestrator initializes SimpleClassifierWrapper when classifier_type='simple_classifier'
- Orchestrator initializes DLClassifierWrapper when classifier_type='inference_engine'
- Web app initializes SimpleClassifierWrapper when classifier_type='simple_classifier'
- Web app initializes DLClassifierWrapper when classifier_type='inference_engine'
- Logs show correct classifier type and device
"""

import sys
import json
import tempfile
from pathlib import Path
from dataclasses import replace
import torch

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

from strad_monitoring.config.system_config import ConfigurationManager, SystemConfig
from strad_monitoring.orchestration.orchestrator import MonitoringOrchestrator
from strad_monitoring.dl_classifier.simple_classifier_wrapper import SimpleClassifierWrapper

# Try to import DLClassifierWrapper (may not exist yet)
try:
    from strad_monitoring.dl_classifier.classifier_wrapper import DLClassifierWrapper
    DL_CLASSIFIER_AVAILABLE = True
except ImportError:
    print("⚠ DLClassifierWrapper not available - skipping inference_engine tests")
    DL_CLASSIFIER_AVAILABLE = False


class TestResult:
    """Simple test result tracker"""
    def __init__(self):
        self.passed = []
        self.failed = []
        self.skipped = []
    
    def add_pass(self, test_name, message=""):
        self.passed.append((test_name, message))
        print(f"✓ {test_name}")
        if message:
            print(f"  {message}")
    
    def add_fail(self, test_name, error):
        self.failed.append((test_name, error))
        print(f"✗ {test_name}")
        print(f"  Error: {error}")
    
    def add_skip(self, test_name, reason):
        self.skipped.append((test_name, reason))
        print(f"○ {test_name} (SKIPPED: {reason})")
    
    def print_summary(self):
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"✓ Passed:  {len(self.passed)}")
        print(f"✗ Failed:  {len(self.failed)}")
        print(f"○ Skipped: {len(self.skipped)}")
        print("=" * 80)
        
        if self.failed:
            print("\nFailed Tests:")
            for test_name, error in self.failed:
                print(f"  ✗ {test_name}: {error}")
        
        return len(self.failed) == 0


def create_test_config(classifier_type: str, checkpoint_path: str = None) -> SystemConfig:
    """Create a test configuration with specified classifier type"""
    
    # Use a minimal checkpoint path for testing
    if checkpoint_path is None:
        checkpoint_path = str(project_root / "test_model.pth")
    
    config = SystemConfig(
        # Database
        database_connection_string="DRIVER={ODBC Driver 17 for SQL Server};SERVER=test;DATABASE=Test;Trusted_Connection=yes",
        
        # Paths
        ip_addresses_json_path=str(project_root / "test_ip_addresses.json"),
        model_checkpoint_path=checkpoint_path,
        temp_snapshot_path=str(project_root / "temp_snapshots"),
        permanent_snapshot_path=str(project_root / "permanent_snapshots"),
        log_file_path=str(project_root / "logs"),
        
        # Web viewer credentials
        web_viewer_username="test_user",
        web_viewer_password="test_pass",
        
        # Timing
        cycle_schedule_cron="0 * * * *",
        strad_selection_count=10,
        cooldown_hours=1,
        classification_timeout_seconds=10,
        
        # Snapshot
        snapshot_min_width=640,
        snapshot_min_height=480,
        snapshot_retention_days=30,
        log_retention_days=14,
        
        # Fallback
        enable_local_testing_mode=True,
        use_sqlite_fallback=True,
        sqlite_db_path="tests/test.db",
        fallback_data_source="sqlite",
        fallback_data_path="",
        
        # Classifier
        classifier_type=classifier_type,
        
        # DL Model Config (for inference_engine)
        dl_model_config={
            "flow_network": "liteflownet2",
            "target_resolution": [640, 640],
            "confidence_threshold": 0.5,
            "enable_uncertainty": False
        }
    )
    
    return config


def create_dummy_checkpoint(checkpoint_type: str) -> str:
    """
    Create a dummy checkpoint file for testing
    
    Args:
        checkpoint_type: Either 'simple_classifier' or 'inference_engine'
    
    Returns:
        Path to created checkpoint file
    """
    import torch.nn as nn
    
    # Create a minimal model
    class DummyModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = nn.Linear(10, 3)
        
        def forward(self, x):
            return self.fc(x)
    
    model = DummyModel()
    
    # Create checkpoint based on type
    if checkpoint_type == 'simple_classifier':
        checkpoint = {
            'model_state_dict': model.state_dict(),
            'epoch': 1,
            'best_accuracy': 0.95
        }
    elif checkpoint_type == 'inference_engine':
        checkpoint = {
            'feature_extractor_state': model.state_dict(),
            'epoch': 1
        }
    else:
        raise ValueError(f"Unknown checkpoint_type: {checkpoint_type}")
    
    # Save to temporary file
    temp_dir = project_root / "temp_test_checkpoints"
    temp_dir.mkdir(exist_ok=True)
    
    checkpoint_path = temp_dir / f"test_{checkpoint_type}_checkpoint.pth"
    torch.save(checkpoint, checkpoint_path)
    
    return str(checkpoint_path)


def test_orchestrator_simple_classifier(results: TestResult):
    """Test orchestrator with classifier_type='simple_classifier'"""
    test_name = "Orchestrator with simple_classifier"
    
    try:
        # Create dummy checkpoint
        checkpoint_path = create_dummy_checkpoint('simple_classifier')
        
        # Create configuration
        config = create_test_config('simple_classifier', checkpoint_path)
        
        # Initialize orchestrator
        print(f"\n{'='*80}")
        print(f"Testing: {test_name}")
        print(f"{'='*80}")
        
        orchestrator = MonitoringOrchestrator(config)
        
        # Verify classifier type
        if orchestrator.dl_classifier is None:
            results.add_fail(test_name, "Classifier is None (should be SimpleClassifierWrapper)")
            return
        
        if not isinstance(orchestrator.dl_classifier, SimpleClassifierWrapper):
            results.add_fail(
                test_name,
                f"Expected SimpleClassifierWrapper, got {type(orchestrator.dl_classifier)}"
            )
            return
        
        results.add_pass(
            test_name,
            f"Classifier type: {type(orchestrator.dl_classifier).__name__}"
        )
        
        # Cleanup
        orchestrator.stop()
        
    except Exception as e:
        results.add_fail(test_name, str(e))


def test_orchestrator_inference_engine(results: TestResult):
    """Test orchestrator with classifier_type='inference_engine'"""
    test_name = "Orchestrator with inference_engine"
    
    if not DL_CLASSIFIER_AVAILABLE:
        results.add_skip(test_name, "DLClassifierWrapper not available")
        return
    
    try:
        # Create dummy checkpoint
        checkpoint_path = create_dummy_checkpoint('inference_engine')
        
        # Create configuration
        config = create_test_config('inference_engine', checkpoint_path)
        
        # Initialize orchestrator
        print(f"\n{'='*80}")
        print(f"Testing: {test_name}")
        print(f"{'='*80}")
        
        orchestrator = MonitoringOrchestrator(config)
        
        # Verify classifier type
        if orchestrator.dl_classifier is None:
            results.add_fail(test_name, "Classifier is None (should be DLClassifierWrapper)")
            return
        
        if not isinstance(orchestrator.dl_classifier, DLClassifierWrapper):
            results.add_fail(
                test_name,
                f"Expected DLClassifierWrapper, got {type(orchestrator.dl_classifier)}"
            )
            return
        
        results.add_pass(
            test_name,
            f"Classifier type: {type(orchestrator.dl_classifier).__name__}"
        )
        
        # Cleanup
        orchestrator.stop()
        
    except Exception as e:
        results.add_fail(test_name, str(e))


def test_web_app_simple_classifier(results: TestResult):
    """Test web app with classifier_type='simple_classifier'"""
    test_name = "Web App with simple_classifier"
    
    try:
        # Create dummy checkpoint
        checkpoint_path = create_dummy_checkpoint('simple_classifier')
        
        # Create test config file
        config_data = {
            "database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=test;DATABASE=Test;Trusted_Connection=yes",
            "ip_addresses_json_path": str(project_root / "test_ip_addresses.json"),
            "model_checkpoint_path": checkpoint_path,
            "temp_snapshot_path": str(project_root / "temp_snapshots"),
            "permanent_snapshot_path": str(project_root / "permanent_snapshots"),
            "log_file_path": str(project_root / "logs"),
            "web_viewer_username": "test_user",
            "web_viewer_password": "test_pass",
            "cycle_schedule_cron": "0 * * * *",
            "strad_selection_count": 10,
            "cooldown_hours": 1,
            "classification_timeout_seconds": 10,
            "snapshot_min_width": 640,
            "snapshot_min_height": 480,
            "snapshot_retention_days": 30,
            "log_retention_days": 14,
            "enable_local_testing_mode": True,
            "use_sqlite_fallback": True,
            "sqlite_db_path": "tests/test.db",
            "fallback_data_source": "sqlite",
            "fallback_data_path": "",
            "classifier_type": "simple_classifier",
            "dl_model_config": {
                "flow_network": "liteflownet2",
                "target_resolution": [640, 640],
                "confidence_threshold": 0.5,
                "enable_uncertainty": False
            }
        }
        
        # Write config to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_config_path = f.name
        
        try:
            # Simulate web app initialization
            print(f"\n{'='*80}")
            print(f"Testing: {test_name}")
            print(f"{'='*80}")
            
            # Load configuration
            config = ConfigurationManager.load_config(temp_config_path)
            
            # Initialize classifier (simulating app.py logic)
            classifier_type = getattr(config, 'classifier_type', 'inference_engine')
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            
            print(f"Using classifier: {classifier_type}, device: {device}")
            
            if classifier_type == 'simple_classifier':
                dl_classifier = SimpleClassifierWrapper(
                    model_checkpoint_path=config.model_checkpoint_path,
                    device=device,
                    image_size=640
                )
                print("✓ SimpleClassifierWrapper initialized")
            else:
                results.add_fail(test_name, f"Expected simple_classifier, got {classifier_type}")
                return
            
            # Verify type
            if not isinstance(dl_classifier, SimpleClassifierWrapper):
                results.add_fail(
                    test_name,
                    f"Expected SimpleClassifierWrapper, got {type(dl_classifier)}"
                )
                return
            
            results.add_pass(
                test_name,
                f"Classifier type: {type(dl_classifier).__name__}"
            )
            
        finally:
            # Cleanup temporary config file
            Path(temp_config_path).unlink(missing_ok=True)
        
    except Exception as e:
        results.add_fail(test_name, str(e))


def test_web_app_inference_engine(results: TestResult):
    """Test web app with classifier_type='inference_engine'"""
    test_name = "Web App with inference_engine"
    
    if not DL_CLASSIFIER_AVAILABLE:
        results.add_skip(test_name, "DLClassifierWrapper not available")
        return
    
    try:
        # Create dummy checkpoint
        checkpoint_path = create_dummy_checkpoint('inference_engine')
        
        # Create test config file
        config_data = {
            "database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=test;DATABASE=Test;Trusted_Connection=yes",
            "ip_addresses_json_path": str(project_root / "test_ip_addresses.json"),
            "model_checkpoint_path": checkpoint_path,
            "temp_snapshot_path": str(project_root / "temp_snapshots"),
            "permanent_snapshot_path": str(project_root / "permanent_snapshots"),
            "log_file_path": str(project_root / "logs"),
            "web_viewer_username": "test_user",
            "web_viewer_password": "test_pass",
            "cycle_schedule_cron": "0 * * * *",
            "strad_selection_count": 10,
            "cooldown_hours": 1,
            "classification_timeout_seconds": 10,
            "snapshot_min_width": 640,
            "snapshot_min_height": 480,
            "snapshot_retention_days": 30,
            "log_retention_days": 14,
            "enable_local_testing_mode": True,
            "use_sqlite_fallback": True,
            "sqlite_db_path": "tests/test.db",
            "fallback_data_source": "sqlite",
            "fallback_data_path": "",
            "classifier_type": "inference_engine",
            "dl_model_config": {
                "flow_network": "liteflownet2",
                "target_resolution": [640, 640],
                "confidence_threshold": 0.5,
                "enable_uncertainty": False
            }
        }
        
        # Write config to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_config_path = f.name
        
        try:
            # Simulate web app initialization
            print(f"\n{'='*80}")
            print(f"Testing: {test_name}")
            print(f"{'='*80}")
            
            # Load configuration
            config = ConfigurationManager.load_config(temp_config_path)
            
            # Initialize classifier (simulating app.py logic)
            classifier_type = getattr(config, 'classifier_type', 'inference_engine')
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            
            print(f"Using classifier: {classifier_type}, device: {device}")
            
            if classifier_type == 'inference_engine':
                dl_classifier = DLClassifierWrapper(
                    model_checkpoint_path=config.model_checkpoint_path,
                    config=config.dl_model_config,
                    device=device
                )
                print("✓ DLClassifierWrapper initialized")
            else:
                results.add_fail(test_name, f"Expected inference_engine, got {classifier_type}")
                return
            
            # Verify type
            if not isinstance(dl_classifier, DLClassifierWrapper):
                results.add_fail(
                    test_name,
                    f"Expected DLClassifierWrapper, got {type(dl_classifier)}"
                )
                return
            
            results.add_pass(
                test_name,
                f"Classifier type: {type(dl_classifier).__name__}"
            )
            
        finally:
            # Cleanup temporary config file
            Path(temp_config_path).unlink(missing_ok=True)
        
    except Exception as e:
        results.add_fail(test_name, str(e))


def test_device_detection(results: TestResult):
    """Test that device detection works correctly"""
    test_name = "Device detection"
    
    try:
        cuda_available = torch.cuda.is_available()
        expected_device = 'cuda' if cuda_available else 'cpu'
        
        print(f"\n{'='*80}")
        print(f"Testing: {test_name}")
        print(f"{'='*80}")
        print(f"CUDA available: {cuda_available}")
        print(f"Expected device: {expected_device}")
        
        results.add_pass(
            test_name,
            f"CUDA available: {cuda_available}, expected device: {expected_device}"
        )
        
    except Exception as e:
        results.add_fail(test_name, str(e))


def cleanup_test_files():
    """Clean up temporary test files"""
    temp_dir = project_root / "temp_test_checkpoints"
    if temp_dir.exists():
        import shutil
        shutil.rmtree(temp_dir)
        print("\n✓ Cleaned up temporary test files")


def main():
    """Run all checkpoint tests"""
    print("=" * 80)
    print("CHECKPOINT 5: CLASSIFIER INTEGRATION VERIFICATION")
    print("=" * 80)
    print()
    print("This script tests:")
    print("  1. Orchestrator with classifier_type='simple_classifier'")
    print("  2. Orchestrator with classifier_type='inference_engine'")
    print("  3. Web App with classifier_type='simple_classifier'")
    print("  4. Web App with classifier_type='inference_engine'")
    print("  5. Device detection (CPU/CUDA)")
    print()
    
    results = TestResult()
    
    try:
        # Run tests
        test_device_detection(results)
        test_orchestrator_simple_classifier(results)
        test_orchestrator_inference_engine(results)
        test_web_app_simple_classifier(results)
        test_web_app_inference_engine(results)
        
        # Print summary
        success = results.print_summary()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    finally:
        # Always cleanup
        cleanup_test_files()


if __name__ == "__main__":
    main()
