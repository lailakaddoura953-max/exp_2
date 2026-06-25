"""
Database Interface for Strad Monitoring System with Local Testing Fallback

This module provides SQL Server database connectivity with automatic fallback
to local test data when the database is unavailable. This enables full system
testing without requiring production database access.

FALLBACK MECHANISM:
==================
The database interface tries production SQL Server first, then automatically
falls back to local test data if the connection fails. This allows developers
to test the complete workflow (Excel → VLC → Classification) locally.

PRIMARY PATH: Production SQL Server
- Calls stored procedure: strad_action_check_by_id_and_timestamp
- Requires active SQL Server connection with user's Windows credentials
- Returns real strad IDs from production database

FALLBACK PATH: Local Testing Mode
- FALLBACK OPTION 0: SQLite test database (tests/test.db) - MOST REALISTIC
- FALLBACK OPTION 1: Load from KITTI dataset (kitti_data/ folder)
- FALLBACK OPTION 2: Load from local CSV/JSON file (custom test scenarios)
- FALLBACK OPTION 3: Generate random test strad IDs (quick testing)

Configuration in system_config.json:
    "enable_local_testing_mode": true,
    "use_sqlite_fallback": true,
    "sqlite_db_path": "tests/test.db",
    "fallback_data_source": "sqlite"  # or "kitti", "local_folder", "random"
    "fallback_data_path": "C:/test_data/strad_list.csv"  # for local_folder option

SQLite Test Database:
- Location: tests/test.db
- Table: container_demo
- Contains 20 realistic test records with CHE values (SC001-SC127)
- Mimics production database structure for most realistic local testing
- Created via test_table_create.sql and populate_test.sql

See LOCAL_TESTING_GUIDE.md for detailed fallback documentation.
"""

import csv
import json
import logging
import os
import random
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False
    logging.warning("pyodbc not available - SQL Server functionality disabled")

try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False
    logging.warning("sqlite3 not available - SQLite fallback disabled")

from ..utils.exceptions import DatabaseError, CriticalError
from ..utils.retry import retry


class DatabaseInterface:
    """
    Database interface with SQL Server connectivity and local testing fallback.
    
    This class manages all database operations including:
    - Strad selection with cooldown and exclusion filtering
    - Classification result storage
    - Check history tracking
    - Critical strad exclusion management
    
    The interface automatically falls back to local test data when SQL Server
    is unavailable, allowing full system testing without database access.
    """
    
    def __init__(
        self,
        connection_string: str,
        enable_fallback: bool = True,
        fallback_data_path: Optional[str] = None,
        fallback_data_source: str = "random",
        use_sqlite_fallback: bool = False,
        sqlite_db_path: Optional[str] = None
    ):
        """
        Initialize database interface with fallback support.
        
        Args:
            connection_string: SQL Server connection string
            enable_fallback: Enable local testing mode when database unavailable
            fallback_data_path: Path to local test data (KITTI dataset or local folder)
            fallback_data_source: Fallback method - "kitti", "local_folder", "sqlite", or "random"
            use_sqlite_fallback: Use SQLite database for local testing (NEW!)
            sqlite_db_path: Path to SQLite test database (default: "tests/test.db")
        """
        self.connection_string = connection_string
        self.enable_fallback = enable_fallback
        self.fallback_data_path = fallback_data_path
        self.fallback_data_source = fallback_data_source
        self.use_sqlite_fallback = use_sqlite_fallback
        self.sqlite_db_path = sqlite_db_path or "tests/test.db"
        
        self.connection = None
        self.sqlite_connection = None
        self.logger = logging.getLogger("DatabaseInterface")
        
        # Check if we can establish database connection
        self._is_database_available = self._test_connection()
    
    def _test_connection(self) -> bool:
        """
        Test if SQL Server database is available.
        
        Returns:
            True if database is accessible, False otherwise
        """
        if not PYODBC_AVAILABLE:
            self.logger.warning("pyodbc not installed - database unavailable")
            return False
        
        try:
            conn = pyodbc.connect(self.connection_string, timeout=5)
            conn.close()
            self.logger.info("Database connection successful")
            return True
        except Exception as e:
            self.logger.warning(f"Database connection failed: {e}")
            if not self.enable_fallback:
                raise CriticalError(
                    "Database unavailable and fallback disabled",
                    component="DatabaseInterface",
                    original_error=e
                )
            return False
    
    @retry(max_attempts=3, backoff_factor=1.0, exceptions=(Exception,))
    def _get_connection(self):
        """
        Get database connection with connection pooling.
        
        Uses retry decorator for transient connection errors.
        
        Returns:
            pyodbc.Connection object
            
        Raises:
            DatabaseError: If connection fails after retries
        """
        if not PYODBC_AVAILABLE:
            raise DatabaseError("pyodbc not available", component="DatabaseInterface")
        
        try:
            if self.connection is None or not self._connection_alive():
                self.connection = pyodbc.connect(
                    self.connection_string,
                    timeout=30
                )
            return self.connection
        except Exception as e:
            raise DatabaseError(
                "Failed to establish database connection",
                component="DatabaseInterface",
                original_error=e
            )
    
    def _connection_alive(self) -> bool:
        """Check if current connection is still alive."""
        if self.connection is None:
            return False
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
        except:
            return False
    
    def get_eligible_strads(self, count: int = 10) -> List[str]:
        """
        Query eligible strads with automatic fallback support.
        
        FALLBACK MECHANISM:
        This method tries production SQL Server first, then falls back to
        local test data if the connection fails.
        
        Args:
            count: Number of strads to select (default: 10)
            
        Returns:
            List of strad IDs in format SCXXX (e.g., ["SC042", "SC078", ...])
            
        Raises:
            DatabaseError: If query fails and fallback is disabled
            
        Example:
            >>> strads = db.get_eligible_strads(10)
            >>> print(strads)
            ['SC042', 'SC078', 'SC115', ...]
        """
        
        # ========================================
        # PRIMARY PATH: Production SQL Server
        # ========================================
        # Calls stored procedure: strad_action_check_by_id_and_timestamp
        # Requires active SQL Server connection with user's Windows credentials
        
        if self._is_database_available:
            try:
                self.logger.info(f"Querying SQL Server for {count} eligible strads")
                return self._query_production_server(count)
            except Exception as e:
                self.logger.error(f"Production query failed: {e}")
                if not self.enable_fallback:
                    raise DatabaseError(
                        "Failed to query eligible strads",
                        component="DatabaseInterface",
                        original_error=e
                    )
                # If query fails, mark database as unavailable and use fallback
                self._is_database_available = False
        
        # ========================================
        # FALLBACK PATH: Local Testing Mode
        # ========================================
        # Used when SQL Server is unavailable (local testing, network issues, etc.)
        
        self.logger.warning(
            f"SQL Server unavailable. Using local testing fallback: {self.fallback_data_source}"
        )
        
        if not self.enable_fallback:
            raise DatabaseError(
                "SQL Server unavailable and fallback disabled",
                component="DatabaseInterface"
            )
        
        return self._get_fallback_strads(count)
    
    def _query_production_server(self, count: int) -> List[str]:
        """
        Query production SQL Server for eligible strads.
        
        Calls the stored procedure 'strad_action_check_by_id_and_timestamp' which:
        - Filters strads checked within last 1 hour (cooldown)
        - Excludes strads in critical_strad_exclusions table
        - Returns up to 'count' random strad IDs
        
        Args:
            count: Number of strads to select
            
        Returns:
            List of strad IDs
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Call stored procedure with count parameter
            cursor.execute("EXEC strad_action_check_by_id_and_timestamp @count=?", (count,))
            results = cursor.fetchall()
            
            # Extract strad IDs from results
            strad_ids = [row[0] for row in results]
            
            self.logger.info(f"Retrieved {len(strad_ids)} eligible strads from SQL Server: {strad_ids[:5]}...")
            return strad_ids
            
        except Exception as e:
            raise DatabaseError(
                "Failed to execute stored procedure",
                component="DatabaseInterface",
                original_error=e
            )
        finally:
            cursor.close()
    
    def _get_fallback_strads(self, count: int) -> List[str]:
        """
        Get strad IDs using fallback method.
        
        Routes to appropriate fallback based on fallback_data_source configuration.
        
        Args:
            count: Number of strads to select
            
        Returns:
            List of strad IDs
        """
        # FALLBACK OPTION 0: SQLite test database (NEW!)
        if self.use_sqlite_fallback or self.fallback_data_source == "sqlite":
            return self._load_strads_from_sqlite(count)
        
        # FALLBACK OPTION 1: Load from KITTI dataset
        elif self.fallback_data_source == "kitti":
            return self._load_strads_from_kitti(count)
        
        # FALLBACK OPTION 2: Load from local CSV/JSON file
        elif self.fallback_data_source == "local_folder" and self.fallback_data_path:
            return self._load_strads_from_local_folder(count)
        
        # FALLBACK OPTION 3: Generate random test strad IDs
        else:
            return self._generate_random_test_strads(count)
    
    def _load_strads_from_kitti(self, count: int) -> List[str]:
        """
        FALLBACK OPTION 1: Load strad IDs from KITTI dataset
        
        This reads from the existing KITTI dataset structure and maps
        KITTI sequences to strad IDs for realistic testing.
        
        Path: kitti_data/ or configured fallback_data_path
        
        Args:
            count: Number of strads to select
            
        Returns:
            List of strad IDs mapped from KITTI sequences
        """
        self.logger.info(f"Loading strads from KITTI dataset: {self.fallback_data_path}")
        
        # Look for KITTI data directory
        kitti_path = self.fallback_data_path or "kitti_data"
        
        if not os.path.exists(kitti_path):
            self.logger.warning(f"KITTI path not found: {kitti_path}, using random fallback")
            return self._generate_random_test_strads(count)
        
        try:
            # Scan KITTI directory for sequences
            # KITTI structure: kitti_data/2011_09_26/2011_09_26_drive_0001_sync/...
            kitti_strads = []
            
            for root, dirs, files in os.walk(kitti_path):
                # Look for drive sequences
                for dir_name in dirs:
                    if 'drive' in dir_name:
                        # Extract sequence number and map to strad ID
                        try:
                            # Example: 2011_09_26_drive_0001_sync → SC001
                            seq_num = int(dir_name.split('_')[4])  # Extract 0001
                            if 1 <= seq_num <= 135:
                                strad_id = f"SC{str(seq_num).zfill(3)}"
                                if strad_id not in kitti_strads:
                                    kitti_strads.append(strad_id)
                        except (IndexError, ValueError):
                            continue
            
            if not kitti_strads:
                self.logger.warning("No KITTI sequences found, using random fallback")
                return self._generate_random_test_strads(count)
            
            # Randomly select from available KITTI strads
            selected = random.sample(kitti_strads, min(count, len(kitti_strads)))
            self.logger.info(f"Selected {len(selected)} strads from KITTI: {selected}")
            return selected
            
        except Exception as e:
            self.logger.error(f"Failed to load KITTI data: {e}, using random fallback")
            return self._generate_random_test_strads(count)
    
    def _load_strads_from_local_folder(self, count: int) -> List[str]:
        """
        FALLBACK OPTION 2: Load strad IDs from local CSV/JSON file
        
        Reads from a local file containing test strad IDs with timestamps
        and check history for realistic testing scenarios.
        
        Expected CSV format:
            strad_id,last_check_timestamp,is_critical
            SC001,2024-01-15 10:00:00,false
            SC042,2024-01-15 11:00:00,true
            ...
        
        Expected JSON format:
            {
              "strads": [
                {"strad_id": "SC001", "last_check_timestamp": "2024-01-15 10:00:00", "is_critical": false},
                ...
              ]
            }
        
        Path: Configured in fallback_data_path (e.g., 'C:/test_data/strad_list.csv')
        
        Args:
            count: Number of strads to select
            
        Returns:
            List of strad IDs with same filtering logic as production
        """
        self.logger.info(f"Loading strads from local file: {self.fallback_data_path}")
        
        if not self.fallback_data_path or not os.path.exists(self.fallback_data_path):
            self.logger.warning(f"Fallback data file not found: {self.fallback_data_path}, using random")
            return self._generate_random_test_strads(count)
        
        try:
            # Determine file type
            file_ext = os.path.splitext(self.fallback_data_path)[1].lower()
            
            if file_ext == '.csv':
                return self._load_from_csv(count)
            elif file_ext == '.json':
                return self._load_from_json(count)
            else:
                self.logger.warning(f"Unsupported file type: {file_ext}, using random")
                return self._generate_random_test_strads(count)
                
        except Exception as e:
            self.logger.error(f"Failed to load local data file: {e}, using random fallback")
            return self._generate_random_test_strads(count)
    
    def _load_from_csv(self, count: int) -> List[str]:
        """Load strads from CSV file and apply filtering logic."""
        eligible_strads = []
        current_time = datetime.now()
        cooldown_threshold = current_time - timedelta(hours=1)
        
        with open(self.fallback_data_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                strad_id = row['strad_id']
                last_check_str = row.get('last_check_timestamp', '')
                is_critical = row.get('is_critical', 'false').lower() == 'true'
                
                # Apply same filtering as production
                # 1. Exclude critical strads
                if is_critical:
                    continue
                
                # 2. Exclude strads in cooldown period
                if last_check_str:
                    try:
                        last_check = datetime.strptime(last_check_str, "%Y-%m-%d %H:%M:%S")
                        if last_check > cooldown_threshold:
                            continue  # In cooldown
                    except ValueError:
                        pass  # Invalid timestamp, include strad
                
                eligible_strads.append(strad_id)
        
        # Randomly select from eligible strads
        selected = random.sample(eligible_strads, min(count, len(eligible_strads)))
        self.logger.info(f"Selected {len(selected)} eligible strads from CSV: {selected}")
        return selected
    
    def _load_from_json(self, count: int) -> List[str]:
        """Load strads from JSON file and apply filtering logic."""
        with open(self.fallback_data_path, 'r') as f:
            data = json.load(f)
        
        eligible_strads = []
        current_time = datetime.now()
        cooldown_threshold = current_time - timedelta(hours=1)
        
        for strad in data.get('strads', []):
            strad_id = strad['strad_id']
            last_check_str = strad.get('last_check_timestamp', '')
            is_critical = strad.get('is_critical', False)
            
            # Apply same filtering as production
            if is_critical:
                continue
            
            if last_check_str:
                try:
                    last_check = datetime.strptime(last_check_str, "%Y-%m-%d %H:%M:%S")
                    if last_check > cooldown_threshold:
                        continue
                except ValueError:
                    pass
            
            eligible_strads.append(strad_id)
        
        selected = random.sample(eligible_strads, min(count, len(eligible_strads)))
        self.logger.info(f"Selected {len(selected)} eligible strads from JSON: {selected}")
        return selected
    
    def _generate_random_test_strads(self, count: int) -> List[str]:
        """
        FALLBACK OPTION 3: Generate random test strad IDs
        
        Creates realistic strad IDs (SC001-SC135) for basic testing
        when no local test data is available.
        
        Args:
            count: Number of strads to generate
            
        Returns:
            List of randomly generated strad IDs
        """
        all_strads = [f"SC{str(i).zfill(3)}" for i in range(1, 136)]
        selected = random.sample(all_strads, min(count, len(all_strads)))
        self.logger.info(f"Generated {len(selected)} random test strads: {selected}")
        return selected
    
    def _load_strads_from_sqlite(self, count: int) -> List[str]:
        """
        FALLBACK OPTION 0: Load strad IDs from SQLite test database
        
        This reads from a local SQLite database (tests/test.db) containing
        realistic test records from container_demo table. This is the most
        realistic fallback option as it mimics production database structure.
        
        Expected SQLite schema:
            CREATE TABLE container_demo (
                CONT_ID INTEGER,
                TIME_STAMP TEXT NOT NULL,
                CONT_ACTION TEXT NOT NULL,
                CONT_NAME TEXT NOT NULL,
                CHE TEXT NOT NULL,
                ...
                PRIMARY KEY (CONT_ID, CHE)
            );
        
        The database should contain 20+ test records with CHE values like:
        SC001, SC006, SC012, SC027, SC028, SC031, SC039, SC049, SC052, SC062,
        SC063, SC083, SC085, SC095, SC110, SC111, SC115, SC127
        
        Path: tests/test.db (or configured sqlite_db_path)
        
        Args:
            count: Number of strads to select
            
        Returns:
            List of strad IDs from SQLite database
        """
        self.logger.info(f"Loading strads from SQLite database: {self.sqlite_db_path}")
        
        if not SQLITE_AVAILABLE:
            self.logger.warning("sqlite3 not available, using random fallback")
            return self._generate_random_test_strads(count)
        
        if not os.path.exists(self.sqlite_db_path):
            self.logger.warning(f"SQLite database not found: {self.sqlite_db_path}, using random fallback")
            return self._generate_random_test_strads(count)
        
        try:
            # Connect to SQLite database
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            
            # Query distinct CHE values from container_demo table
            # In production, we'd filter by timestamp/cooldown, but for testing
            # we just get random unique CHE values
            query = """
                SELECT DISTINCT CHE
                FROM container_demo
                ORDER BY RANDOM()
                LIMIT ?
            """
            
            cursor.execute(query, (count,))
            results = cursor.fetchall()
            
            # Extract CHE values (strad IDs)
            strad_ids = [row[0] for row in results]
            
            cursor.close()
            conn.close()
            
            if not strad_ids:
                self.logger.warning("No records found in SQLite database, using random fallback")
                return self._generate_random_test_strads(count)
            
            self.logger.info(f"Selected {len(strad_ids)} strads from SQLite: {strad_ids}")
            return strad_ids
            
        except Exception as e:
            self.logger.error(f"Failed to load from SQLite: {e}, using random fallback")
            return self._generate_random_test_strads(count)
    
    def store_classification_result(
        self,
        strad_id: str,
        classification: str,
        confidence: float,
        snapshot_path: Optional[str] = None
    ) -> bool:
        """
        Store classification result in database.
        
        Inserts classification result into classification_results table with:
        - strad_id: CHE number (SCXXX format)
        - classification: 'none', 'moderate', or 'critical'
        - confidence: Confidence score (0.0 to 1.0)
        - snapshot_path: File path for critical snapshots (nullable)
        - timestamp: Current timestamp
        
        Args:
            strad_id: Strad CHE number
            classification: Classification level ('none', 'moderate', 'critical')
            confidence: Confidence score (0.0-1.0)
            snapshot_path: Path to snapshot file (only for critical classifications)
            
        Returns:
            True if storage successful, False otherwise
            
        Raises:
            DatabaseError: If insertion fails after retries
        """
        # FALLBACK PATH: Skip database storage if unavailable
        if not self._is_database_available:
            self.logger.warning(
                f"Database unavailable - classification result not stored: "
                f"{strad_id} = {classification} ({confidence:.2f})"
            )
            return False
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Use parameterized query to prevent SQL injection
            query = """
                INSERT INTO classification_results 
                (strad_id, classification, confidence, snapshot_path, timestamp)
                VALUES (?, ?, ?, ?, GETDATE())
            """
            
            cursor.execute(query, (strad_id, classification, confidence, snapshot_path))
            conn.commit()
            cursor.close()
            
            self.logger.info(
                f"Stored classification result: {strad_id} = {classification} "
                f"(confidence: {confidence:.2f})"
            )
            return True
            
        except Exception as e:
            raise DatabaseError(
                f"Failed to store classification result for {strad_id}",
                component="DatabaseInterface",
                original_error=e
            )
    
    def update_check_history(self, strad_id: str) -> bool:
        """
        Update check history timestamp for a strad.
        
        Inserts or updates the last_check_timestamp in strad_action_check_by_id_and_timestamp
        table to record when a strad was last processed. This enables cooldown filtering
        (1 hour between checks).
        
        Uses MERGE statement for idempotent behavior (handles both insert and update).
        
        Args:
            strad_id: Strad CHE number to update
            
        Returns:
            True if update successful, False otherwise
            
        Raises:
            DatabaseError: If update fails after retries
        """
        # FALLBACK PATH: Skip database update if unavailable
        if not self._is_database_available:
            self.logger.warning(
                f"Database unavailable - check history not updated for {strad_id}"
            )
            return False
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Use MERGE for idempotent insert/update behavior
            query = """
                MERGE strad_action_check_by_id_and_timestamp AS target
                USING (SELECT ? AS strad_id) AS source
                ON target.strad_id = source.strad_id
                WHEN MATCHED THEN
                    UPDATE SET last_check_timestamp = GETDATE()
                WHEN NOT MATCHED THEN
                    INSERT (strad_id, last_check_timestamp)
                    VALUES (source.strad_id, GETDATE());
            """
            
            cursor.execute(query, (strad_id,))
            conn.commit()
            cursor.close()
            
            self.logger.info(f"Updated check history for {strad_id}")
            return True
            
        except Exception as e:
            raise DatabaseError(
                f"Failed to update check history for {strad_id}",
                component="DatabaseInterface",
                original_error=e
            )
    
    def add_to_critical_exclusion(self, strad_id: str, reason: str = "Critical misalignment") -> bool:
        """
        Add strad to critical exclusion list.
        
        Inserts strad into critical_strad_exclusions table. Excluded strads are
        not returned by get_eligible_strads() until they are removed via
        remove_from_critical_exclusion().
        
        Uses serializable isolation level to prevent race conditions.
        
        Args:
            strad_id: Strad CHE number to exclude
            reason: Reason for exclusion (default: "Critical misalignment")
            
        Returns:
            True if addition successful, False if already excluded
            
        Raises:
            DatabaseError: If insertion fails after retries
        """
        # FALLBACK PATH: Skip database operation if unavailable
        if not self._is_database_available:
            self.logger.warning(
                f"Database unavailable - critical exclusion not added for {strad_id}"
            )
            return False
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if already excluded
            cursor.execute(
                "SELECT COUNT(*) FROM critical_strad_exclusions WHERE strad_id = ?",
                (strad_id,)
            )
            if cursor.fetchone()[0] > 0:
                self.logger.info(f"{strad_id} already in critical exclusion list")
                cursor.close()
                return False
            
            # Insert into exclusion list with serializable isolation
            cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
            cursor.execute("BEGIN TRANSACTION")
            
            query = """
                INSERT INTO critical_strad_exclusions 
                (strad_id, exclusion_timestamp, reason)
                VALUES (?, GETDATE(), ?)
            """
            
            cursor.execute(query, (strad_id, reason))
            cursor.execute("COMMIT TRANSACTION")
            conn.commit()
            cursor.close()
            
            self.logger.info(
                f"Added {strad_id} to critical exclusion list (reason: {reason})"
            )
            return True
            
        except Exception as e:
            raise DatabaseError(
                f"Failed to add {strad_id} to critical exclusion list",
                component="DatabaseInterface",
                original_error=e
            )
    
    def remove_from_critical_exclusion(self, strad_id: str) -> bool:
        """
        Remove strad from critical exclusion list.
        
        Deletes strad from critical_strad_exclusions table, allowing it to be
        returned by get_eligible_strads() again. Called after adjustment confirmation.
        
        Args:
            strad_id: Strad CHE number to remove from exclusion
            
        Returns:
            True if removal successful, False if not in exclusion list
            
        Raises:
            DatabaseError: If deletion fails after retries
        """
        # FALLBACK PATH: Skip database operation if unavailable
        if not self._is_database_available:
            self.logger.warning(
                f"Database unavailable - critical exclusion not removed for {strad_id}"
            )
            return False
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Delete from exclusion list
            query = "DELETE FROM critical_strad_exclusions WHERE strad_id = ?"
            cursor.execute(query, (strad_id,))
            rows_affected = cursor.rowcount
            conn.commit()
            cursor.close()
            
            if rows_affected > 0:
                self.logger.info(f"Removed {strad_id} from critical exclusion list")
                return True
            else:
                self.logger.info(f"{strad_id} was not in critical exclusion list")
                return False
            
        except Exception as e:
            raise DatabaseError(
                f"Failed to remove {strad_id} from critical exclusion list",
                component="DatabaseInterface",
                original_error=e
            )
    
    def cleanup_old_history(self, retention_days: int = 7) -> int:
        """
        Clean up old check history records.
        
        Removes records from Check_History table older than retention_days.
        This maintains database size and query performance.
        
        Args:
            retention_days: Number of days to retain history (default: 7)
            
        Returns:
            Number of records deleted
            
        Raises:
            DatabaseError: If cleanup fails
        """
        # FALLBACK PATH: Skip cleanup if database unavailable
        if not self._is_database_available:
            self.logger.warning("Database unavailable - history cleanup skipped")
            return 0
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = """
                DELETE FROM Check_History
                WHERE last_check_timestamp < DATEADD(day, -?, GETDATE())
            """
            
            cursor.execute(query, (retention_days,))
            rows_deleted = cursor.rowcount
            conn.commit()
            cursor.close()
            
            self.logger.info(
                f"Cleaned up {rows_deleted} check history records older than {retention_days} days"
            )
            return rows_deleted
            
        except Exception as e:
            raise DatabaseError(
                "Failed to cleanup old check history",
                component="DatabaseInterface",
                original_error=e
            )
    
    def health_check(self) -> bool:
        """
        Verify database connectivity.
        
        Returns:
            True if database is accessible, False otherwise
        """
        return self._test_connection()
    
    def close(self):
        """Close database connection."""
        if self.connection:
            try:
                self.connection.close()
                self.logger.info("Database connection closed")
            except Exception as e:
                self.logger.warning(f"Error closing connection: {e}")
            finally:
                self.connection = None
