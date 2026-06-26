"""
System Configuration Management for Strad Monitoring System

This module provides configuration loading, validation, and access for the
Strad Carrier monitoring automation system.

Configuration is loaded from system_config.json and validated before the
system starts. Required fields are checked and file paths are verified.
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class SystemConfig:
    """
    System configuration for Strad Monitoring Automation.
    
    All configuration parameters loaded from system_config.json are stored
    in this dataclass for type-safe access throughout the system.
    """
    
    # Database configuration (required)
    database_connection_string: str
    
    # File paths (required)
    excel_file_path: str
    model_checkpoint_path: str
    temp_snapshot_path: str
    permanent_snapshot_path: str
    log_file_path: str
    
    # Timing configuration (required)
    cycle_schedule_cron: str
    strad_selection_count: int
    cooldown_hours: int
    classification_timeout_seconds: int
    
    # Snapshot configuration (required)
    snapshot_min_width: int
    snapshot_min_height: int
    snapshot_retention_days: int
    log_retention_days: int
    
    # Database configuration (optional - with defaults)
    strad_query_sql_file: str = "strad_query.sql"  # SQL query file for strad selection
    
    # RTSP authentication for VLC (optional - with defaults)
    rtsp_username: Optional[str] = None
    rtsp_password: Optional[str] = None
    
    # LOCAL TESTING FALLBACK CONFIGURATION (optional - with defaults)
    # See LOCAL_TESTING_GUIDE.md for details
    enable_local_testing_mode: bool = True
    fallback_data_path: Optional[str] = None
    fallback_data_source: str = "random"  # Options: "kitti", "local_folder", "random"
    
    # Deep learning model configuration (optional - with defaults)
    dl_model_config: Dict = field(default_factory=dict)


class ConfigurationManager:
    """
    Configuration Manager for loading and validating system configuration.
    
    This class implements singleton pattern to ensure only one configuration
    instance exists across the system.
    """
    
    _instance: Optional['ConfigurationManager'] = None
    _config: Optional[SystemConfig] = None
    
    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @staticmethod
    def load_config(config_path: str = "system_config.json") -> SystemConfig:
        """
        Load and validate configuration from JSON file.
        
        Args:
            config_path: Path to configuration JSON file (default: system_config.json)
            
        Returns:
            SystemConfig object with validated configuration
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config file has invalid JSON
            ValueError: If required fields are missing or invalid
            
        Example:
            >>> config = ConfigurationManager.load_config("system_config.json")
            >>> print(config.strad_selection_count)
            10
        """
        # Check if config file exists
        if not os.path.exists(config_path):
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}\n"
                f"Please create system_config.json from the template."
            )
        
        # Load JSON configuration
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        # Remove comment fields (fields starting with underscore)
        config_data = {k: v for k, v in config_data.items() if not k.startswith('_')}
        
        # Substitute environment variables (${ENV_VAR} syntax)
        config_data = ConfigurationManager._substitute_env_vars(config_data)
        
        # Create SystemConfig object
        try:
            config = SystemConfig(**config_data)
        except TypeError as e:
            raise ValueError(f"Invalid configuration structure: {e}")
        
        # Validate the configuration
        validation_errors = ConfigurationManager.validate_config(config)
        if validation_errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(validation_errors)
            raise ValueError(error_msg)
        
        # Store in singleton instance
        ConfigurationManager._config = config
        
        return config
    
    @staticmethod
    def _substitute_env_vars(config_data: dict) -> dict:
        """
        Substitute environment variables in configuration values.
        
        Supports ${ENV_VAR} syntax for environment variable substitution.
        
        Args:
            config_data: Configuration dictionary
            
        Returns:
            Configuration dictionary with environment variables substituted
            
        Example:
            Input: {"path": "${USER_HOME}/data"}
            Output: {"path": "C:/Users/Miles/data"}
        """
        env_var_pattern = re.compile(r'\$\{([^}]+)\}')
        
        def substitute_value(value):
            if isinstance(value, str):
                # Find all ${VAR} patterns
                matches = env_var_pattern.findall(value)
                for var_name in matches:
                    env_value = os.environ.get(var_name, '')
                    value = value.replace(f'${{{var_name}}}', env_value)
                return value
            elif isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(v) for v in value]
            else:
                return value
        
        return {k: substitute_value(v) for k, v in config_data.items()}
    
    @staticmethod
    def validate_config(config: SystemConfig) -> List[str]:
        """
        Validate configuration and return list of validation errors.
        
        Checks:
        - All required fields are present and non-empty
        - File paths exist and are accessible
        - Numeric values are within reasonable ranges
        - Database connection string has valid format
        
        Args:
            config: SystemConfig object to validate
            
        Returns:
            List of validation error messages (empty list if valid)
            
        Example:
            >>> errors = ConfigurationManager.validate_config(config)
            >>> if errors:
            ...     print("Validation failed:", errors)
        """
        errors = []
        
        # Validate required fields are non-empty
        required_fields = [
            'database_connection_string',
            'excel_file_path',
            'model_checkpoint_path',
            'temp_snapshot_path',
            'permanent_snapshot_path',
            'log_file_path'
        ]
        
        for field_name in required_fields:
            value = getattr(config, field_name)
            if not value or (isinstance(value, str) and not value.strip()):
                errors.append(f"Required field '{field_name}' is missing or empty")
        
        # Validate database connection string format
        # DSN-based connections (DSN=...) don't need DRIVER= or SERVER=
        if config.database_connection_string:
            is_dsn_connection = 'DSN=' in config.database_connection_string.upper()
            if not is_dsn_connection:
                # For non-DSN connections, require DRIVER= and SERVER=
                if 'DRIVER=' not in config.database_connection_string:
                    errors.append("database_connection_string must contain 'DRIVER=' clause (or use DSN=...)")
                if 'SERVER=' not in config.database_connection_string:
                    errors.append("database_connection_string must contain 'SERVER=' clause (or use DSN=...)")
        
        # Validate file paths exist (skip if using environment variables that aren't set yet)
        paths_to_check = {
            'excel_file_path': config.excel_file_path,
            'model_checkpoint_path': config.model_checkpoint_path
        }
        
        for path_name, path_value in paths_to_check.items():
            if path_value and not path_value.startswith('${') and not os.path.exists(path_value):
                errors.append(f"{path_name} does not exist: {path_value}")
        
        # Validate directories can be created
        directories_to_check = {
            'temp_snapshot_path': config.temp_snapshot_path,
            'permanent_snapshot_path': config.permanent_snapshot_path,
            'log_file_path': config.log_file_path
        }
        
        for dir_name, dir_path in directories_to_check.items():
            if dir_path and not dir_path.startswith('${'):
                parent_dir = os.path.dirname(dir_path) if os.path.splitext(dir_path)[1] else dir_path
                try:
                    os.makedirs(parent_dir, exist_ok=True)
                except Exception as e:
                    errors.append(f"Cannot create directory for {dir_name}: {e}")
        
        # Validate numeric ranges
        if config.strad_selection_count < 1 or config.strad_selection_count > 135:
            errors.append(f"strad_selection_count must be between 1 and 135, got {config.strad_selection_count}")
        
        if config.cooldown_hours < 0 or config.cooldown_hours > 24:
            errors.append(f"cooldown_hours must be between 0 and 24, got {config.cooldown_hours}")
        
        if config.classification_timeout_seconds < 1 or config.classification_timeout_seconds > 300:
            errors.append(f"classification_timeout_seconds must be between 1 and 300, got {config.classification_timeout_seconds}")
        
        if config.snapshot_min_width < 320 or config.snapshot_min_height < 240:
            errors.append(f"Snapshot dimensions too small: {config.snapshot_min_width}x{config.snapshot_min_height} (min: 320x240)")
        
        if config.snapshot_retention_days < 1 or config.snapshot_retention_days > 365:
            errors.append(f"snapshot_retention_days must be between 1 and 365, got {config.snapshot_retention_days}")
        
        if config.log_retention_days < 1 or config.log_retention_days > 90:
            errors.append(f"log_retention_days must be between 1 and 90, got {config.log_retention_days}")
        
        # Validate cron schedule format (basic validation)
        cron_parts = config.cycle_schedule_cron.split()
        if len(cron_parts) != 5:
            errors.append(f"cycle_schedule_cron must have 5 fields (minute hour day month weekday), got: {config.cycle_schedule_cron}")
        
        # Validate fallback configuration
        if config.enable_local_testing_mode:
            valid_sources = ['kitti', 'local_folder', 'random']
            if config.fallback_data_source not in valid_sources:
                errors.append(f"fallback_data_source must be one of {valid_sources}, got: {config.fallback_data_source}")
            
            # If using local_folder or kitti, fallback_data_path should be set
            if config.fallback_data_source in ['local_folder', 'kitti'] and not config.fallback_data_path:
                errors.append(f"fallback_data_path must be set when fallback_data_source is '{config.fallback_data_source}'")
        
        return errors
    
    @staticmethod
    def get_config() -> Optional[SystemConfig]:
        """
        Get the singleton configuration instance.
        
        Returns:
            SystemConfig object if loaded, None otherwise
            
        Example:
            >>> config = ConfigurationManager.get_config()
            >>> if config:
            ...     print(f"Checking {config.strad_selection_count} strads per cycle")
        """
        return ConfigurationManager._config
    
    @staticmethod
    def reload_config(config_path: str = "system_config.json") -> SystemConfig:
        """
        Reload configuration from file without restarting the system.
        
        Args:
            config_path: Path to configuration JSON file
            
        Returns:
            SystemConfig object with reloaded configuration
            
        Note:
            Some configuration changes may require system restart to take effect.
        """
        return ConfigurationManager.load_config(config_path)
