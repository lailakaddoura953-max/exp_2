"""
Unit tests for Strad Monitoring System Configuration

Tests the SystemConfig dataclass and ConfigurationManager for the strad monitoring system.
Validates:
- Loading from JSON configuration files
- Validation of configuration parameters including classifier_type
- Error handling for invalid configurations
"""

import pytest
import json
import tempfile
import os
from pathlib import Path

from src.strad_monitoring.config.system_config import (
    SystemConfig,
    ConfigurationManager
)


class TestClassifierTypeConfiguration:
    """Test classifier_type configuration field"""
    
    @pytest.fixture
    def valid_base_config(self, tmp_path):
        """Create a valid base configuration dictionary"""
        return {
            "database_connection_string": "DSN=TestDB;UID=test;PWD=test",
            "ip_addresses_json_path": str(tmp_path / "ip_addresses.json"),
            "model_checkpoint_path": str(tmp_path / "model.pth"),
            "temp_snapshot_path": str(tmp_path / "temp"),
            "permanent_snapshot_path": str(tmp_path / "snapshots"),
            "log_file_path": str(tmp_path / "logs" / "app.log"),
            "web_viewer_username": "test_user",
            "web_viewer_password": "test_pass",
            "cycle_schedule_cron": "0 * * * *",
            "strad_selection_count": 10,
            "cooldown_hours": 2,
            "classification_timeout_seconds": 30,
            "snapshot_min_width": 640,
            "snapshot_min_height": 480,
            "snapshot_retention_days": 30,
            "log_retention_days": 30,
            "enable_local_testing_mode": True
        }
    
    def _touch_ip_addresses_file(self, tmp_path):
        """Create a placeholder ip_addresses.json so path-existence checks pass"""
        ip_path = tmp_path / "ip_addresses.json"
        ip_path.write_text("SC#\tIP_Address\n001\t192.168.1.100\n")
        return ip_path
    
    def test_default_classifier_type_is_inference_engine(self, tmp_path, valid_base_config):
        """Test that classifier_type defaults to 'inference_engine'"""
        self._touch_ip_addresses_file(tmp_path)
        
        # Save config file
        config_file = tmp_path / "config.json"
        with open(config_file, 'w') as f:
            json.dump(valid_base_config, f)
        
        # Load configuration
        config = ConfigurationManager.load_config(str(config_file))
        
        # Verify default value
        assert config.classifier_type == 'inference_engine'
    
    def test_valid_classifier_type_simple_classifier(self, tmp_path, valid_base_config):
        """Test that 'simple_classifier' is accepted as valid"""
        self._touch_ip_addresses_file(tmp_path)
        
        # Add classifier_type
        valid_base_config['classifier_type'] = 'simple_classifier'
        
        # Save config file
        config_file = tmp_path / "config.json"
        with open(config_file, 'w') as f:
            json.dump(valid_base_config, f)
        
        # Load configuration
        config = ConfigurationManager.load_config(str(config_file))
        
        # Verify value
        assert config.classifier_type == 'simple_classifier'
    
    def test_valid_classifier_type_inference_engine(self, tmp_path, valid_base_config):
        """Test that 'inference_engine' is accepted as valid"""
        self._touch_ip_addresses_file(tmp_path)
        
        # Add classifier_type
        valid_base_config['classifier_type'] = 'inference_engine'
        
        # Save config file
        config_file = tmp_path / "config.json"
        with open(config_file, 'w') as f:
            json.dump(valid_base_config, f)
        
        # Load configuration
        config = ConfigurationManager.load_config(str(config_file))
        
        # Verify value
        assert config.classifier_type == 'inference_engine'
    
    def test_invalid_classifier_type_rejected(self, tmp_path, valid_base_config):
        """Test that invalid classifier_type values are rejected"""
        self._touch_ip_addresses_file(tmp_path)
        
        # Add invalid classifier_type
        valid_base_config['classifier_type'] = 'invalid_classifier'
        
        # Save config file
        config_file = tmp_path / "config.json"
        with open(config_file, 'w') as f:
            json.dump(valid_base_config, f)
        
        # Verify that loading fails with clear error
        with pytest.raises(ValueError) as exc_info:
            ConfigurationManager.load_config(str(config_file))
        
        # Check error message mentions valid values
        error_msg = str(exc_info.value)
        assert "classifier_type must be one of" in error_msg
        assert "simple_classifier" in error_msg
        assert "inference_engine" in error_msg
        assert "invalid_classifier" in error_msg
    
    def test_invalid_classifier_type_empty_string(self, tmp_path, valid_base_config):
        """Test that empty string classifier_type is rejected"""
        self._touch_ip_addresses_file(tmp_path)
        
        # Add empty classifier_type
        valid_base_config['classifier_type'] = ''
        
        # Save config file
        config_file = tmp_path / "config.json"
        with open(config_file, 'w') as f:
            json.dump(valid_base_config, f)
        
        # Verify that loading fails
        with pytest.raises(ValueError) as exc_info:
            ConfigurationManager.load_config(str(config_file))
        
        error_msg = str(exc_info.value)
        assert "classifier_type must be one of" in error_msg
    
    def test_invalid_classifier_type_misspelled(self, tmp_path, valid_base_config):
        """Test that misspelled classifier_type values are rejected"""
        self._touch_ip_addresses_file(tmp_path)
        
        invalid_values = [
            'SimpleClassifier',  # Wrong capitalization
            'simple-classifier',  # Wrong separator
            'inference_Engine',  # Wrong capitalization
            'inference-engine',  # Wrong separator
            'simple_clasifier',  # Typo
            'infrence_engine'   # Typo
        ]
        
        for invalid_value in invalid_values:
            valid_base_config['classifier_type'] = invalid_value
            
            # Save config file
            config_file = tmp_path / f"config_{invalid_value}.json"
            with open(config_file, 'w') as f:
                json.dump(valid_base_config, f)
            
            # Verify that loading fails
            with pytest.raises(ValueError) as exc_info:
                ConfigurationManager.load_config(str(config_file))
            
            error_msg = str(exc_info.value)
            assert "classifier_type must be one of" in error_msg, \
                f"Failed to reject invalid value: {invalid_value}"


class TestSystemConfigDataclass:
    """Test SystemConfig dataclass directly"""
    
    def test_classifier_type_field_exists(self):
        """Test that classifier_type field exists in SystemConfig"""
        # Create minimal config
        config = SystemConfig(
            database_connection_string="DSN=TestDB",
            ip_addresses_json_path="ip_addresses.json",
            model_checkpoint_path="model.pth",
            temp_snapshot_path="temp",
            permanent_snapshot_path="snapshots",
            log_file_path="logs/app.log",
            web_viewer_username="test_user",
            web_viewer_password="test_pass",
            cycle_schedule_cron="0 * * * *",
            strad_selection_count=10,
            cooldown_hours=2,
            classification_timeout_seconds=30,
            snapshot_min_width=640,
            snapshot_min_height=480,
            snapshot_retention_days=30,
            log_retention_days=30
        )
        
        # Verify field exists with default value
        assert hasattr(config, 'classifier_type')
        assert config.classifier_type == 'inference_engine'
    
    def test_classifier_type_can_be_set(self):
        """Test that classifier_type can be set to valid values"""
        config = SystemConfig(
            database_connection_string="DSN=TestDB",
            ip_addresses_json_path="ip_addresses.json",
            model_checkpoint_path="model.pth",
            temp_snapshot_path="temp",
            permanent_snapshot_path="snapshots",
            log_file_path="logs/app.log",
            web_viewer_username="test_user",
            web_viewer_password="test_pass",
            cycle_schedule_cron="0 * * * *",
            strad_selection_count=10,
            cooldown_hours=2,
            classification_timeout_seconds=30,
            snapshot_min_width=640,
            snapshot_min_height=480,
            snapshot_retention_days=30,
            log_retention_days=30,
            classifier_type='simple_classifier'
        )
        
        assert config.classifier_type == 'simple_classifier'


class TestConfigurationValidation:
    """Test validation logic for configuration"""
    
    def test_validate_config_checks_classifier_type(self):
        """Test that validate_config checks classifier_type"""
        config = SystemConfig(
            database_connection_string="DSN=TestDB",
            ip_addresses_json_path="ip_addresses.json",
            model_checkpoint_path="model.pth",
            temp_snapshot_path="temp",
            permanent_snapshot_path="snapshots",
            log_file_path="logs/app.log",
            web_viewer_username="test_user",
            web_viewer_password="test_pass",
            cycle_schedule_cron="0 * * * *",
            strad_selection_count=10,
            cooldown_hours=2,
            classification_timeout_seconds=30,
            snapshot_min_width=640,
            snapshot_min_height=480,
            snapshot_retention_days=30,
            log_retention_days=30,
            classifier_type='invalid_type'
        )
        
        errors = ConfigurationManager.validate_config(config)
        
        # Should have at least one error about classifier_type
        assert len(errors) > 0
        classifier_errors = [e for e in errors if 'classifier_type' in e]
        assert len(classifier_errors) > 0
        
        # Check error message content
        error_msg = classifier_errors[0]
        assert 'simple_classifier' in error_msg
        assert 'inference_engine' in error_msg
    
    def test_validate_config_accepts_valid_classifier_types(self):
        """Test that validate_config accepts valid classifier_type values"""
        for valid_type in ['simple_classifier', 'inference_engine']:
            config = SystemConfig(
                database_connection_string="DSN=TestDB",
                ip_addresses_json_path="ip_addresses.json",
                model_checkpoint_path="model.pth",
                temp_snapshot_path="temp",
                permanent_snapshot_path="snapshots",
                log_file_path="logs/app.log",
                web_viewer_username="test_user",
                web_viewer_password="test_pass",
                cycle_schedule_cron="0 * * * *",
                strad_selection_count=10,
                cooldown_hours=2,
                classification_timeout_seconds=30,
                snapshot_min_width=640,
                snapshot_min_height=480,
                snapshot_retention_days=30,
                log_retention_days=30,
                classifier_type=valid_type,
                enable_local_testing_mode=True  # Skip file path checks
            )
            
            errors = ConfigurationManager.validate_config(config)
            
            # Should not have errors about classifier_type
            classifier_errors = [e for e in errors if 'classifier_type' in e]
            assert len(classifier_errors) == 0, \
                f"Got unexpected classifier_type error for '{valid_type}': {classifier_errors}"
