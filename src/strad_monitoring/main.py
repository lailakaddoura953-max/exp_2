"""
Main entry point for Strad Carrier Monitoring Automation

This module provides the main() function that serves as the entry point for the
monitoring system. It handles:
- Configuration loading and validation
- Logging system setup
- Database connectivity verification
- Orchestrator initialization and startup
- Signal handling for graceful shutdown

Usage:
    python -m src.strad_monitoring.main [--config PATH]

Requirements addressed:
- 12.1: Load configuration from system_config.json at startup
- 12.4: Refuse to start if configuration validation fails
- 12.6: Verify database connectivity during initialization
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .config.system_config import ConfigurationManager, SystemConfig
from .logging.logging_system import LoggingSystem
from .orchestration.orchestrator import MonitoringOrchestrator


def validate_database_connectivity(config: SystemConfig) -> bool:
    """
    Verify database connectivity during initialization.
    
    Args:
        config: SystemConfig with database connection string
        
    Returns:
        True if database is reachable, False otherwise
        
    Requirements: 12.6 (verify database connectivity during initialization)
    """
    from .database.database_interface import DatabaseInterface
    
    try:
        print("Verifying database connectivity...")
        db_interface = DatabaseInterface(
            connection_string=config.database_connection_string,
            enable_fallback=config.enable_local_testing_mode,
            fallback_data_path=config.fallback_data_path,
            fallback_data_source=config.fallback_data_source,
            use_sqlite_fallback=getattr(config, 'use_sqlite_fallback', False),
            sqlite_db_path=getattr(config, 'sqlite_db_path', 'tests/test.db')
        )
        
        is_connected = db_interface.health_check()
        
        if is_connected:
            print("✓ Database connectivity verified")
        else:
            if config.enable_local_testing_mode:
                print("⚠ Database unavailable - using local testing mode with fallback")
            else:
                print("✗ Database connectivity check failed")
                return False
        
        # Cleanup
        if hasattr(db_interface, 'connection') and db_interface.connection:
            db_interface.connection.close()
        
        return True
        
    except Exception as e:
        if config.enable_local_testing_mode:
            print(f"⚠ Database unavailable: {e}")
            print("⚠ Proceeding with local testing mode (fallback enabled)")
            return True
        else:
            print(f"✗ Database connectivity check failed: {e}")
            return False


def main(config_path: Optional[str] = None) -> int:
    """
    Main entry point for the Strad Carrier Monitoring Automation system.
    
    This function:
    1. Loads configuration from system_config.json (or specified path)
    2. Validates configuration parameters
    3. Sets up logging system
    4. Verifies database connectivity
    5. Creates and starts MonitoringOrchestrator
    6. Handles exceptions with proper error messages
    
    Args:
        config_path: Optional path to configuration file. If not specified,
                    defaults to "system_config.json" in current directory
                    
    Returns:
        Exit code: 0 for success, 1 for error
        
    Requirements:
        - 12.1: Load configuration from system_config.json at startup
        - 12.4: Refuse to start if configuration validation fails
        - 12.6: Verify database connectivity during initialization
        
    Example:
        >>> main()  # Uses default system_config.json
        >>> main("custom_config.json")  # Uses custom config
    """
    print("=" * 80)
    print("STRAD CARRIER MONITORING AUTOMATION - STARTING")
    print("=" * 80)
    
    # =================================================================
    # Step 1: Load configuration
    # =================================================================
    # Requirements: 12.1 (load configuration from system_config.json)
    try:
        if config_path is None:
            config_path = "system_config.json"
        
        print(f"Loading configuration from: {config_path}")
        config = ConfigurationManager.load_config(config_path)
        print("✓ Configuration loaded successfully")
        
    except FileNotFoundError:
        print(f"✗ Configuration file not found: {config_path}")
        print("Please create a system_config.json file with required parameters")
        return 1
        
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return 1
    
    # =================================================================
    # Step 2: Validate configuration
    # =================================================================
    # Requirements: 12.4 (refuse to start if validation fails)
    try:
        print("Validating configuration...")
        errors = ConfigurationManager.validate_config(config)
        
        if errors:
            print("✗ Configuration validation failed:")
            for error in errors:
                print(f"  - {error}")
            print("\nRefusing to start due to configuration errors")
            return 1
        
        print("✓ Configuration validated successfully")
        
    except Exception as e:
        print(f"✗ Configuration validation error: {e}")
        return 1
    
    # =================================================================
    # Step 3: Setup logging system
    # =================================================================
    # Requirements: 12.1 (initialize logging)
    try:
        print("Setting up logging system...")
        LoggingSystem.setup_logging(
            log_file_path=config.log_file_path,
            log_level="INFO",
            retention_days=config.log_retention_days,
            enable_console=True  # Enable console output for main process
        )
        
        logger = LoggingSystem.get_logger("Main")
        logger.info("=" * 80)
        logger.info("STRAD CARRIER MONITORING AUTOMATION - INITIALIZATION")
        logger.info("=" * 80)
        logger.info(f"Configuration file: {config_path}")
        logger.info(f"Log file path: {config.log_file_path}")
        logger.info("✓ Logging system initialized")
        
        print("✓ Logging system initialized")
        
    except Exception as e:
        print(f"✗ Failed to setup logging: {e}")
        return 1
    
    # =================================================================
    # Step 4: Verify database connectivity
    # =================================================================
    # Requirements: 12.6 (verify database connectivity during initialization)
    try:
        if not validate_database_connectivity(config):
            logger.error("Database connectivity verification failed")
            print("✗ Database connectivity verification failed")
            print("Cannot start monitoring system without database access")
            LoggingSystem.shutdown()
            return 1
        
        logger.info("✓ Database connectivity verified")
        
    except Exception as e:
        logger.error(f"Database connectivity check error: {e}")
        print(f"✗ Database connectivity check error: {e}")
        LoggingSystem.shutdown()
        return 1
    
    # =================================================================
    # Step 5: Create and start MonitoringOrchestrator
    # =================================================================
    # Requirements: 12.1 (create orchestrator and start scheduler)
    try:
        logger.info("Creating MonitoringOrchestrator...")
        print("Creating MonitoringOrchestrator...")
        
        orchestrator = MonitoringOrchestrator(config)
        
        logger.info("✓ MonitoringOrchestrator created successfully")
        print("✓ MonitoringOrchestrator created successfully")
        
        logger.info("Starting monitoring scheduler...")
        print("Starting monitoring scheduler...")
        print("System will execute monitoring cycles at XX:00:00 every hour")
        print("Press Ctrl+C to stop")
        print("=" * 80)
        
        # Start orchestrator (blocking call)
        orchestrator.start()
        
        # This line is reached only after orchestrator.stop() is called
        logger.info("Orchestrator stopped - exiting")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt - shutting down")
        print("\nReceived keyboard interrupt - shutting down")
        return 0
        
    except Exception as e:
        logger.error(f"Failed to start orchestrator: {e}", exc_info=True)
        print(f"✗ Failed to start orchestrator: {e}")
        LoggingSystem.shutdown()
        return 1


def cli_main() -> None:
    """
    Command-line interface entry point.
    
    Parses command-line arguments and calls main().
    """
    parser = argparse.ArgumentParser(
        description="Strad Carrier Monitoring Automation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default configuration file (system_config.json)
  python -m src.strad_monitoring.main
  
  # Use custom configuration file
  python -m src.strad_monitoring.main --config custom_config.json
  
  # Use demo configuration for testing
  python -m src.strad_monitoring.main --config demo_config/system_config.json
        """
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to configuration file (default: system_config.json)"
    )
    
    args = parser.parse_args()
    
    # Call main with parsed arguments
    exit_code = main(config_path=args.config)
    sys.exit(exit_code)


if __name__ == "__main__":
    cli_main()
