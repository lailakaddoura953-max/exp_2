"""
Test for Orchestrator error handling (Task 3.2)

This test verifies error handling for:
- Invalid classifier_type values
- Missing checkpoint files in testing mode
- Missing checkpoint files in production mode

Validates Requirements 8.1, 8.3, 8.4, 9.1, 9.3
"""

import pytest
import tempfile
import torch
from pathlib import Path
from unittest.mock import Mock, patch


def test_invalid_classifier_type_production_mode():
    """
    Test that invalid classifier_type raises ValueError in production mode.
    
    Validates Requirements 9.1: Invalid classifier_type must raise ValueError
    """
    from src.strad_monitoring.config.system_config import SystemConfig
    from src.strad_monitoring.orchestration.orchestrator import MonitoringOrchestrator
    
    # Create config with invalid classifier_type
    config = SystemConfig(
        database_connection_string="Driver={SQL Server};Server=test;Database=test;Trusted_Connection=yes;",
        ip_addresses_json_path="test_ip_addresses.json",
        model_checkpoint_path="test_model.pth",
        temp_snapshot_path="temp",
        permanent_snapshot_path="permanent",
        log_file_path="test.log",
        web_viewer_username="test_user",
        web_viewer_password="test_pass",
        cycle_schedule_cron="0 * * * *",
        strad_selection_count=10,
        cooldown_hours=24,
        classification_timeout_seconds=60,
        snapshot_min_width=320,
        snapshot_min_height=240,
        snapshot_retention_days=30,
        log_retention_days=90,
        enable_local_testing_mode=False,  # Production mode
        classifier_type='invalid_type',  # Invalid value
        fallback_data_path='test_fallback.xlsx',
        fallback_data_source='random',
        dl_model_config={}
    )
    
    # Mock all component initializations to isolate classifier initialization
    with patch('src.strad_monitoring.orchestration.orchestrator.DatabaseInterface'), \
         patch('src.strad_monitoring.orchestration.orchestrator.IPAddressLoader'), \
         patch('src.strad_monitoring.orchestration.orchestrator.WebCapture'), \
         patch('src.strad_monitoring.orchestration.orchestrator.StorageManager'), \
         patch('src.strad_monitoring.orchestration.orchestrator.ModerateClassificationTracker'), \
         patch('src.strad_monitoring.orchestration.orchestrator.ConfirmationHandler'):
        
        # Attempt to initialize orchestrator - should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            orchestrator = MonitoringOrchestrator(config)
        
        # Verify error message mentions valid types
        error_msg = str(exc_info.value)
        assert 'invalid_type' in error_msg.lower() or 'Invalid classifier_type' in error_msg
        assert 'simple_classifier' in error_msg or 'inference_engine' in error_msg
    
    print("✓ Invalid classifier_type correctly raises ValueError in production mode")


def test_invalid_classifier_type_testing_mode():
    """
    Test that invalid classifier_type is handled gracefully in testing mode.
    
    Validates Requirements 8.1: Testing mode should set classifier to None and log warning
    """
    from src.strad_monitoring.config.system_config import SystemConfig
    from src.strad_monitoring.orchestration.orchestrator import MonitoringOrchestrator
    
    # Create config with invalid classifier_type but testing mode enabled
    config = SystemConfig(
        database_connection_string="Driver={SQL Server};Server=test;Database=test;Trusted_Connection=yes;",
        ip_addresses_json_path="test_ip_addresses.json",
        model_checkpoint_path="test_model.pth",
        temp_snapshot_path="temp",
        permanent_snapshot_path="permanent",
        log_file_path="test.log",
        web_viewer_username="test_user",
        web_viewer_password="test_pass",
        cycle_schedule_cron="0 * * * *",
        strad_selection_count=10,
        cooldown_hours=24,
        classification_timeout_seconds=60,
        snapshot_min_width=320,
        snapshot_min_height=240,
        snapshot_retention_days=30,
        log_retention_days=90,
        enable_local_testing_mode=True,  # Testing mode
        classifier_type='invalid_type',  # Invalid value
        fallback_data_path='test_fallback.xlsx',
        fallback_data_source='random',
        dl_model_config={}
    )
    
    # Mock all component initializations except classifier
    with patch('src.strad_monitoring.orchestration.orchestrator.DatabaseInterface'), \
         patch('src.strad_monitoring.orchestration.orchestrator.IPAddressLoader'), \
         patch('src.strad_monitoring.orchestration.orchestrator.WebCapture'), \
         patch('src.strad_monitoring.orchestration.orchestrator.StorageManager'), \
         patch('src.strad_monitoring.orchestration.orchestrator.ModerateClassificationTracker'), \
         patch('src.strad_monitoring.orchestration.orchestrator.ConfirmationHandler'):
        
        # Should not raise an error in testing mode
        orchestrator = MonitoringOrchestrator(config)
        
        # Verify classifier is None
        assert orchestrator.dl_classifier is None
    
    print("✓ Invalid classifier_type handled gracefully in testing mode (classifier=None)")


def test_missing_checkpoint_production_mode():
    """
    Test that missing checkpoint raises FileNotFoundError in production mode.
    
    Validates Requirements 9.3: Production mode must raise FileNotFoundError for missing checkpoint
    """
    from src.strad_monitoring.config.system_config import SystemConfig
    from src.strad_monitoring.orchestration.orchestrator import MonitoringOrchestrator
    
    # Create config pointing to non-existent checkpoint file
    config = SystemConfig(
        database_connection_string="Driver={SQL Server};Server=test;Database=test;Trusted_Connection=yes;",
        ip_addresses_json_path="test_ip_addresses.json",
        model_checkpoint_path="nonexistent_model.pth",  # File doesn't exist
        temp_snapshot_path="temp",
        permanent_snapshot_path="permanent",
        log_file_path="test.log",
        web_viewer_username="test_user",
        web_viewer_password="test_pass",
        cycle_schedule_cron="0 * * * *",
        strad_selection_count=10,
        cooldown_hours=24,
        classification_timeout_seconds=60,
        snapshot_min_width=320,
        snapshot_min_height=240,
        snapshot_retention_days=30,
        log_retention_days=90,
        enable_local_testing_mode=False,  # Production mode
        classifier_type='simple_classifier',
        fallback_data_path='test_fallback.xlsx',
        fallback_data_source='random',
        dl_model_config={}
    )
    
    # Mock all component initializations to isolate classifier initialization
    with patch('src.strad_monitoring.orchestration.orchestrator.DatabaseInterface'), \
         patch('src.strad_monitoring.orchestration.orchestrator.IPAddressLoader'), \
         patch('src.strad_monitoring.orchestration.orchestrator.WebCapture'), \
         patch('src.strad_monitoring.orchestration.orchestrator.StorageManager'), \
         patch('src.strad_monitoring.orchestration.orchestrator.ModerateClassificationTracker'), \
         patch('src.strad_monitoring.orchestration.orchestrator.ConfirmationHandler'):
        
        # Attempt to initialize orchestrator - should raise FileNotFoundError
        with pytest.raises(FileNotFoundError) as exc_info:
            orchestrator = MonitoringOrchestrator(config)
        
        # Verify error message mentions the checkpoint path
        error_msg = str(exc_info.value)
        assert 'nonexistent_model.pth' in error_msg or 'checkpoint' in error_msg.lower()
    
    print("✓ Missing checkpoint correctly raises FileNotFoundError in production mode")


def test_missing_checkpoint_testing_mode():
    """
    Test that missing checkpoint sets classifier to None in testing mode.
    
    Validates Requirements 8.1, 8.4: Testing mode should set classifier to None and log warning
    """
    from src.strad_monitoring.config.system_config import SystemConfig
    from src.strad_monitoring.orchestration.orchestrator import MonitoringOrchestrator
    
    # Create config pointing to non-existent checkpoint file
    config = SystemConfig(
        database_connection_string="Driver={SQL Server};Server=test;Database=test;Trusted_Connection=yes;",
        ip_addresses_json_path="test_ip_addresses.json",
        model_checkpoint_path="nonexistent_model.pth",  # File doesn't exist
        temp_snapshot_path="temp",
        permanent_snapshot_path="permanent",
        log_file_path="test.log",
        web_viewer_username="test_user",
        web_viewer_password="test_pass",
        cycle_schedule_cron="0 * * * *",
        strad_selection_count=10,
        cooldown_hours=24,
        classification_timeout_seconds=60,
        snapshot_min_width=320,
        snapshot_min_height=240,
        snapshot_retention_days=30,
        log_retention_days=90,
        enable_local_testing_mode=True,  # Testing mode
        classifier_type='simple_classifier',
        fallback_data_path='test_fallback.xlsx',
        fallback_data_source='random',
        dl_model_config={}
    )
    
    # Mock all component initializations except classifier
    with patch('src.strad_monitoring.orchestration.orchestrator.DatabaseInterface'), \
         patch('src.strad_monitoring.orchestration.orchestrator.IPAddressLoader'), \
         patch('src.strad_monitoring.orchestration.orchestrator.WebCapture'), \
         patch('src.strad_monitoring.orchestration.orchestrator.StorageManager'), \
         patch('src.strad_monitoring.orchestration.orchestrator.ModerateClassificationTracker'), \
         patch('src.strad_monitoring.orchestration.orchestrator.ConfirmationHandler'):
        
        # Should not raise an error in testing mode
        orchestrator = MonitoringOrchestrator(config)
        
        # Verify classifier is None
        assert orchestrator.dl_classifier is None
    
    print("✓ Missing checkpoint handled gracefully in testing mode (classifier=None)")


def test_valid_classifier_type_with_checkpoint():
    """
    Test that valid classifier_type with existing checkpoint initializes successfully.
    
    Validates Requirements 8.3: Valid configuration should initialize properly
    """
    from src.strad_monitoring.config.system_config import SystemConfig
    from src.strad_monitoring.orchestration.orchestrator import MonitoringOrchestrator
    from src.strad_monitoring.dl_classifier.simple_classifier_wrapper import SimpleStradClassifier
    
    # Create a temporary checkpoint file
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pth', delete=False) as tmp_checkpoint:
        checkpoint_path = Path(tmp_checkpoint.name)
        
        # Create and save a valid checkpoint
        model = SimpleStradClassifier(num_classes=3)
        checkpoint = {
            'model_state_dict': model.state_dict(),
            'epoch': 10,
            'loss': 0.5
        }
        torch.save(checkpoint, checkpoint_path)
    
    try:
        # Create config with valid classifier_type and existing checkpoint
        config = SystemConfig(
            database_connection_string="Driver={SQL Server};Server=test;Database=test;Trusted_Connection=yes;",
            ip_addresses_json_path="test_ip_addresses.json",
            model_checkpoint_path=str(checkpoint_path),
            temp_snapshot_path="temp",
            permanent_snapshot_path="permanent",
            log_file_path="test.log",
            web_viewer_username="test_user",
            web_viewer_password="test_pass",
            cycle_schedule_cron="0 * * * *",
            strad_selection_count=10,
            cooldown_hours=24,
            classification_timeout_seconds=60,
            snapshot_min_width=320,
            snapshot_min_height=240,
            snapshot_retention_days=30,
            log_retention_days=90,
            enable_local_testing_mode=True,  # Testing mode to avoid other dependencies
            classifier_type='simple_classifier',
            fallback_data_path='test_fallback.xlsx',
            fallback_data_source='random',
            dl_model_config={}
        )
        
        # Mock all component initializations except classifier
        with patch('src.strad_monitoring.orchestration.orchestrator.DatabaseInterface'), \
             patch('src.strad_monitoring.orchestration.orchestrator.IPAddressLoader'), \
             patch('src.strad_monitoring.orchestration.orchestrator.WebCapture'), \
             patch('src.strad_monitoring.orchestration.orchestrator.StorageManager'), \
             patch('src.strad_monitoring.orchestration.orchestrator.ModerateClassificationTracker'), \
             patch('src.strad_monitoring.orchestration.orchestrator.ConfirmationHandler'):
            
            # Should initialize successfully
            orchestrator = MonitoringOrchestrator(config)
            
            # Verify classifier was initialized (not None)
            assert orchestrator.dl_classifier is not None
            
            # Verify it's the right type
            from src.strad_monitoring.dl_classifier.simple_classifier_wrapper import SimpleClassifierWrapper
            assert isinstance(orchestrator.dl_classifier, SimpleClassifierWrapper)
        
        print("✓ Valid classifier_type with existing checkpoint initializes successfully")
        
    finally:
        # Cleanup temporary checkpoint
        if checkpoint_path.exists():
            checkpoint_path.unlink()


if __name__ == "__main__":
    print("Running orchestrator error handling tests...")
    print("=" * 80)
    
    try:
        test_invalid_classifier_type_production_mode()
    except Exception as e:
        print(f"✗ test_invalid_classifier_type_production_mode failed: {e}")
    
    try:
        test_invalid_classifier_type_testing_mode()
    except Exception as e:
        print(f"✗ test_invalid_classifier_type_testing_mode failed: {e}")
    
    try:
        test_missing_checkpoint_production_mode()
    except Exception as e:
        print(f"✗ test_missing_checkpoint_production_mode failed: {e}")
    
    try:
        test_missing_checkpoint_testing_mode()
    except Exception as e:
        print(f"✗ test_missing_checkpoint_testing_mode failed: {e}")
    
    try:
        test_valid_classifier_type_with_checkpoint()
    except Exception as e:
        print(f"✗ test_valid_classifier_type_with_checkpoint failed: {e}")
    
    print("=" * 80)
    print("All tests completed!")
