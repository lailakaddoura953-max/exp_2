"""
Adjustment Confirmation Handler for Strad Monitoring System

This module handles camera adjustment confirmations for strads that were previously
classified as critical and excluded from monitoring rotation. When a technician
confirms that camera adjustments have been made, this handler:

1. Validates the CHE_Number exists in the critical exclusion list
2. Records the confirmation timestamp and technician ID
3. Removes the CHE_Number from the critical exclusion list
4. Resets the Check_History timestamp to allow immediate re-checking

Requirements addressed:
- 14.1: Provide confirmation input accepting CHE_Number and timestamp
- 14.2: Record confirmation timestamp and technician_id when CHE_Number exists
- 14.3: Remove CHE_Number from exclusion list immediately upon confirmation
- 14.4: Reset Check_History timestamp to allow immediate re-checking
- 14.5: Return confirmation message on successful processing
- 14.6: Return informational message when no exclusion exists
"""

import logging
from datetime import datetime
from typing import Optional, Tuple

from ..database.database_interface import DatabaseInterface
from ..utils.exceptions import DatabaseError, ComponentError


class ConfirmationResult:
    """
    Result of a confirmation operation.
    
    Attributes:
        success: Whether the confirmation was processed successfully
        message: Human-readable result message
        was_excluded: Whether the strad was in the exclusion list
        strad_id: The CHE_Number that was processed
        technician_id: ID of technician who performed confirmation
        timestamp: When the confirmation was recorded
    """
    
    def __init__(
        self,
        success: bool,
        message: str,
        was_excluded: bool,
        strad_id: str,
        technician_id: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        self.success = success
        self.message = message
        self.was_excluded = was_excluded
        self.strad_id = strad_id
        self.technician_id = technician_id
        self.timestamp = timestamp
    
    def __str__(self) -> str:
        """Format result as string."""
        return f"ConfirmationResult(success={self.success}, strad={self.strad_id}, message='{self.message}')"
    
    def __repr__(self) -> str:
        return self.__str__()


class ConfirmationHandler:
    """
    Handles adjustment confirmations for critical strads.
    
    This handler processes technician reports that camera adjustments have been
    completed for strads that were previously classified as critical. It validates
    the strad is in the exclusion list, records the confirmation, removes the
    exclusion, and resets the check history to allow immediate re-checking.
    
    Usage:
        >>> handler = ConfirmationHandler(db_interface)
        >>> result = handler.confirm_adjustment('SC042', 'TECH123')
        >>> print(result.message)
        'Confirmation successful: SC042 removed from exclusion list and ready for re-checking'
    """
    
    def __init__(self, database_interface: DatabaseInterface):
        """
        Initialize confirmation handler.
        
        Args:
            database_interface: DatabaseInterface instance for database operations
        """
        self.db = database_interface
        self.logger = logging.getLogger("ConfirmationHandler")
    
    def confirm_adjustment(
        self,
        che_number: str,
        technician_id: str,
        confirmation_timestamp: Optional[datetime] = None
    ) -> ConfirmationResult:
        """
        Process adjustment confirmation for a critical strad.
        
        This method performs the following steps:
        1. Validates CHE_Number format (SCXXX)
        2. Checks if CHE_Number exists in critical_strad_exclusions table
        3. If exists:
            a. Records confirmation timestamp and technician_id
            b. Removes CHE_Number from exclusion list
            c. Resets Check_History timestamp to allow immediate re-checking
            d. Returns success confirmation message
        4. If not exists:
            a. Returns informational message (no error)
        
        Args:
            che_number: Strad ID in format SCXXX (e.g., 'SC042')
            technician_id: Identifier of technician who performed adjustment
            confirmation_timestamp: When confirmation occurred (default: current time)
        
        Returns:
            ConfirmationResult with operation details and message
        
        Raises:
            DatabaseError: If database operations fail
            ValueError: If CHE_Number format is invalid
        
        Examples:
            >>> # Successful confirmation of excluded strad
            >>> result = handler.confirm_adjustment('SC042', 'TECH123')
            >>> print(result.message)
            'Confirmation successful: SC042 removed from exclusion list and ready for re-checking'
            >>> assert result.success is True
            >>> assert result.was_excluded is True
            
            >>> # Confirmation for non-excluded strad (informational)
            >>> result = handler.confirm_adjustment('SC078', 'TECH456')
            >>> print(result.message)
            'No exclusion exists for SC078 - strad is not in critical exclusion list'
            >>> assert result.success is True
            >>> assert result.was_excluded is False
        """
        # Set default timestamp if not provided
        if confirmation_timestamp is None:
            confirmation_timestamp = datetime.now()
        
        # Validate CHE_Number format
        self._validate_che_number(che_number)
        
        self.logger.info(
            f"Processing adjustment confirmation for {che_number} by {technician_id}"
        )
        
        try:
            # Check if CHE_Number exists in critical exclusion list
            is_excluded = self._check_exclusion_exists(che_number)
            
            if not is_excluded:
                # Return informational message - not an error
                message = (
                    f"No exclusion exists for {che_number} - "
                    "strad is not in critical exclusion list"
                )
                self.logger.info(message)
                
                return ConfirmationResult(
                    success=True,
                    message=message,
                    was_excluded=False,
                    strad_id=che_number,
                    technician_id=technician_id,
                    timestamp=confirmation_timestamp
                )
            
            # CHE_Number is in exclusion list - process confirmation
            self._record_confirmation(
                che_number,
                technician_id,
                confirmation_timestamp
            )
            
            # Remove from critical exclusion list
            removed = self.db.remove_from_critical_exclusion(che_number)
            
            if not removed:
                # This shouldn't happen since we validated existence above
                # But handle gracefully just in case
                raise DatabaseError(
                    f"Failed to remove {che_number} from exclusion list",
                    component="ConfirmationHandler"
                )
            
            # Reset Check_History timestamp to allow immediate re-checking
            self._reset_check_history(che_number)
            
            # Success message
            message = (
                f"Confirmation successful: {che_number} removed from exclusion list "
                "and ready for re-checking"
            )
            self.logger.info(message)
            
            return ConfirmationResult(
                success=True,
                message=message,
                was_excluded=True,
                strad_id=che_number,
                technician_id=technician_id,
                timestamp=confirmation_timestamp
            )
            
        except DatabaseError:
            # Re-raise database errors as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise DatabaseError(
                f"Failed to process confirmation for {che_number}",
                component="ConfirmationHandler",
                original_error=e
            )
    
    def _validate_che_number(self, che_number: str) -> None:
        """
        Validate CHE_Number format.
        
        CHE_Number must be in format SCXXX where XXX is a number from 001 to 135.
        
        Args:
            che_number: Strad ID to validate
        
        Raises:
            ValueError: If CHE_Number format is invalid
        
        Examples:
            >>> handler._validate_che_number('SC042')  # Valid
            >>> handler._validate_che_number('SC001')  # Valid
            >>> handler._validate_che_number('SC135')  # Valid
            >>> handler._validate_che_number('SC200')  # Raises ValueError
            >>> handler._validate_che_number('XY042')  # Raises ValueError
        """
        if not che_number:
            raise ValueError("CHE_Number cannot be empty")
        
        # Check format: SCXXX
        if not che_number.startswith("SC") or len(che_number) != 5:
            raise ValueError(
                f"Invalid CHE_Number format: '{che_number}'. "
                "Expected format: SCXXX (e.g., SC042)"
            )
        
        # Extract and validate numeric part
        try:
            number = int(che_number[2:])
        except ValueError:
            raise ValueError(
                f"Invalid CHE_Number: '{che_number}'. "
                "Last 3 characters must be digits"
            )
        
        # Validate range: 001 to 135
        if number < 1 or number > 135:
            raise ValueError(
                f"Invalid CHE_Number: '{che_number}'. "
                "Number must be between 001 and 135"
            )
        
        self.logger.debug(f"CHE_Number validation passed: {che_number}")
    
    def _check_exclusion_exists(self, che_number: str) -> bool:
        """
        Check if CHE_Number exists in critical exclusion list.
        
        Args:
            che_number: Strad ID to check
        
        Returns:
            True if strad is in exclusion list, False otherwise
        
        Raises:
            DatabaseError: If database query fails
        """
        # FALLBACK PATH: If database unavailable, return False
        if not self.db._is_database_available:
            self.logger.warning(
                f"Database unavailable - cannot check exclusion for {che_number}"
            )
            return False
        
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT COUNT(*) 
                FROM critical_strad_exclusions 
                WHERE strad_id = ?
            """
            
            cursor.execute(query, (che_number,))
            count = cursor.fetchone()[0]
            cursor.close()
            
            exists = count > 0
            self.logger.debug(
                f"{che_number} {'exists' if exists else 'does not exist'} "
                "in critical exclusion list"
            )
            
            return exists
            
        except Exception as e:
            raise DatabaseError(
                f"Failed to check exclusion status for {che_number}",
                component="ConfirmationHandler",
                original_error=e
            )
    
    def _record_confirmation(
        self,
        che_number: str,
        technician_id: str,
        timestamp: datetime
    ) -> None:
        """
        Record confirmation timestamp and technician ID in database.
        
        Updates the critical_strad_exclusions record to include confirmation
        details before removal. This preserves audit trail.
        
        Args:
            che_number: Strad ID
            technician_id: Technician who performed adjustment
            timestamp: When confirmation occurred
        
        Raises:
            DatabaseError: If update fails
        """
        # FALLBACK PATH: Skip if database unavailable
        if not self.db._is_database_available:
            self.logger.warning(
                f"Database unavailable - confirmation not recorded for {che_number}"
            )
            return
        
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            query = """
                UPDATE critical_strad_exclusions
                SET adjustment_confirmed_at = ?,
                    technician_id = ?
                WHERE strad_id = ?
            """
            
            cursor.execute(query, (timestamp, technician_id, che_number))
            conn.commit()
            cursor.close()
            
            self.logger.info(
                f"Recorded confirmation for {che_number}: "
                f"technician={technician_id}, timestamp={timestamp}"
            )
            
        except Exception as e:
            raise DatabaseError(
                f"Failed to record confirmation for {che_number}",
                component="ConfirmationHandler",
                original_error=e
            )
    
    def _reset_check_history(self, che_number: str) -> None:
        """
        Reset Check_History timestamp to allow immediate re-checking.
        
        Deletes or updates the check history record so the strad can be
        selected in the next monitoring cycle without waiting for cooldown.
        
        Implementation: Deletes the check history record entirely. This is
        equivalent to the strad never having been checked, allowing it to be
        immediately eligible for selection.
        
        Alternative implementation could update timestamp to a past time
        (more than 1 hour ago), but deletion is simpler and achieves the
        same effect.
        
        Args:
            che_number: Strad ID
        
        Raises:
            DatabaseError: If reset fails
        """
        # FALLBACK PATH: Skip if database unavailable
        if not self.db._is_database_available:
            self.logger.warning(
                f"Database unavailable - check history not reset for {che_number}"
            )
            return
        
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # Delete check history record to allow immediate re-checking
            query = """
                DELETE FROM strad_action_check_by_id_and_timestamp
                WHERE strad_id = ?
            """
            
            cursor.execute(query, (che_number,))
            rows_affected = cursor.rowcount
            conn.commit()
            cursor.close()
            
            if rows_affected > 0:
                self.logger.info(
                    f"Reset check history for {che_number} - "
                    "strad is now eligible for immediate re-checking"
                )
            else:
                # No check history existed - that's fine, strad is still eligible
                self.logger.debug(
                    f"No check history found for {che_number} - "
                    "strad is eligible for immediate checking"
                )
            
        except Exception as e:
            raise DatabaseError(
                f"Failed to reset check history for {che_number}",
                component="ConfirmationHandler",
                original_error=e
            )
    
    def get_exclusion_details(self, che_number: str) -> Optional[dict]:
        """
        Get details about a strad's exclusion status.
        
        Retrieves information about when a strad was excluded, whether it has
        been confirmed for adjustment, and by whom.
        
        Args:
            che_number: Strad ID to query
        
        Returns:
            Dictionary with exclusion details if strad is excluded, None otherwise.
            Format: {
                'strad_id': str,
                'added_at': datetime,
                'adjustment_confirmed_at': datetime or None,
                'technician_id': str or None
            }
        
        Raises:
            DatabaseError: If query fails
        """
        # FALLBACK PATH: Return None if database unavailable
        if not self.db._is_database_available:
            self.logger.warning(
                f"Database unavailable - cannot get exclusion details for {che_number}"
            )
            return None
        
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            query = """
                SELECT strad_id, exclusion_timestamp, adjustment_confirmed_at, technician_id
                FROM critical_strad_exclusions
                WHERE strad_id = ?
            """
            
            cursor.execute(query, (che_number,))
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                return None
            
            return {
                'strad_id': row[0],
                'added_at': row[1],
                'adjustment_confirmed_at': row[2],
                'technician_id': row[3]
            }
            
        except Exception as e:
            raise DatabaseError(
                f"Failed to get exclusion details for {che_number}",
                component="ConfirmationHandler",
                original_error=e
            )
