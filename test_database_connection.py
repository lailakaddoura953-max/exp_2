"""
Test SQL Server database connection

This script verifies that the database connection string in system_config.json
is correct and the database is accessible.

Usage:
    python test_database_connection.py
"""

import sys
import json
from pathlib import Path


def print_header(message):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(message)
    print("=" * 70)


def print_success(message):
    """Print success message"""
    print(f"✓ {message}")


def print_error(message):
    """Print error message"""
    print(f"✗ {message}")


def print_info(message):
    """Print info message"""
    print(f"  {message}")


def main():
    print_header("SQL SERVER CONNECTION TEST")
    
    # Load configuration
    config_path = "system_config.json"
    
    if not Path(config_path).exists():
        print_error(f"Configuration file not found: {config_path}")
        print_info("The configuration should be in the root directory")
        return 1
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print_error(f"Failed to load configuration: {e}")
        return 1
    
    # Check for database configuration
    if 'database_connection_string' not in config:
        print_error("'database_connection_string' not found in config")
        print_info("Add 'database_connection_string' to system_config.json")
        print_info("See: SQL_SERVER_SETUP_GUIDE.md for instructions")
        return 1
    
    connection_string = config['database_connection_string']
    
    print_info(f"Connection string: {connection_string}")
    print()
    
    # Try to import pyodbc
    try:
        import pyodbc
    except ImportError:
        print_error("pyodbc not installed")
        print_info("Install with: pip install pyodbc")
        return 1
    
    # Attempt connection
    print("Attempting to connect...")
    
    try:
        conn = pyodbc.connect(connection_string, timeout=10)
        print_success("Connection successful!")
        
        # Get SQL Server version
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION AS version, @@SERVERNAME AS server, DB_NAME() AS db_name")
        row = cursor.fetchone()
        
        print()
        print_info("SQL Server Information:")
        print(f"    Server: {row[1]}")
        print(f"    Database: {row[2]}")
        print(f"    Version: {row[0][:60]}...")
        
        # List tables
        print()
        print_info("Checking for required tables...")
        
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        
        if tables:
            print_info(f"Found {len(tables)} table(s):")
            for table in tables:
                print(f"      - {table}")
        else:
            print_info("No tables found (database is empty)")
        
        # Check for required tables
        required_tables = [
            'classification_results',
            'moderate_tracking',
            'critical_exclusion_list'
        ]
        
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            print()
            print_info("⚠ Missing required tables:")
            for table in missing_tables:
                print(f"      - {table}")
            print_info("Run database setup script to create these tables")
            print_info("See: SQL_SERVER_SETUP_GUIDE.md")
        else:
            print()
            print_success("All required tables found!")
        
        # Check for stored procedure
        print()
        print_info("Checking for stored procedure...")
        
        cursor.execute("""
            SELECT ROUTINE_NAME 
            FROM INFORMATION_SCHEMA.ROUTINES 
            WHERE ROUTINE_TYPE = 'PROCEDURE'
            AND ROUTINE_NAME = 'strad_action_check_by_id_and_timestamp'
        """)
        
        if cursor.fetchone():
            print_success("Stored procedure 'strad_action_check_by_id_and_timestamp' found!")
        else:
            print_info("⚠ Stored procedure 'strad_action_check_by_id_and_timestamp' not found")
            print_info("This procedure is required for strad selection")
            print_info("See: SQL_SERVER_SETUP_GUIDE.md")
        
        # Test query
        print()
        print_info("Testing simple query...")
        cursor.execute("SELECT GETDATE() AS server_time")
        row = cursor.fetchone()
        print_success(f"Query successful! Server time: {row[0]}")
        
        cursor.close()
        conn.close()
        
        print()
        print_header("✓ CONNECTION TEST PASSED")
        print()
        print_info("Next steps:")
        print_info("  1. If tables are missing, run database setup script")
        print_info("  2. If stored procedure is missing, create it")
        print_info("  3. Test with: python -m src.strad_monitoring.main")
        print()
        
        return 0
        
    except pyodbc.Error as e:
        print_error("Connection failed!")
        print()
        print_info(f"Error: {e}")
        print()
        print_info("Troubleshooting steps:")
        print_info("  1. Check server name is correct")
        print_info("  2. Check database name exists")
        print_info("  3. Verify ODBC driver is installed")
        print_info("  4. Check SQL Server is running")
        print_info("  5. Verify firewall allows connection")
        print_info("  6. Check user has permissions")
        print()
        print_info("For detailed help, see: SQL_SERVER_SETUP_GUIDE.md")
        print()
        print_header("✗ CONNECTION TEST FAILED")
        return 1
    
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
