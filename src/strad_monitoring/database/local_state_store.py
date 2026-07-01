"""
Local State Store - JSON-based fallback for tracking monitoring state

When the remote database lacks write permissions (tables don't exist),
this module provides a local JSON file that tracks:
- Recently checked strads (cooldown filtering)
- Classification results (history)
- Critical strad exclusions

The orchestrator's database_interface tries the DB first; if the write
fails, this local store is used as fallback so the system still has
cooldown awareness and result history.

File: data/monitoring_state.json (auto-created in project root)
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_STATE_PATH = "data/monitoring_state.json"


class LocalStateStore:
    """
    JSON-based local state store for monitoring results and cooldown tracking.

    Persists to a JSON file after each write. Thread-safe for single-process
    usage (the orchestrator is single-threaded within each cycle).
    """

    def __init__(self, state_path: str = DEFAULT_STATE_PATH):
        """
        Initialize local state store.

        Args:
            state_path: Path to JSON state file (created if missing)
        """
        self.state_path = state_path
        self._state = {
            "check_history": {},        # {strad_id: last_check_iso_timestamp}
            "classification_results": [],  # [{strad_id, classification, confidence, timestamp}, ...]
            "critical_exclusions": {}   # {strad_id: {timestamp, reason}}
        }

        Path(os.path.dirname(state_path) or ".").mkdir(parents=True, exist_ok=True)
        self._load()
        logger.info(f"LocalStateStore initialized: {state_path}")

    def _load(self) -> None:
        """Load state from JSON file if it exists."""
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, 'r') as f:
                    loaded = json.load(f)
                # Merge with defaults to handle missing keys from older files
                for key in self._state:
                    if key in loaded:
                        self._state[key] = loaded[key]
                logger.debug(f"Loaded state: {len(self._state['check_history'])} check records")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load state file, starting fresh: {e}")
        else:
            logger.debug("No existing state file, starting fresh")

    def _save(self) -> None:
        """Persist current state to JSON file."""
        try:
            with open(self.state_path, 'w') as f:
                json.dump(self._state, f, indent=2, default=str)
        except IOError as e:
            logger.error(f"Failed to save state: {e}")

    # -------------------------------------------------------------------------
    # Check History (cooldown tracking)
    # -------------------------------------------------------------------------

    def record_check(self, strad_id: str) -> None:
        """Record that a strad was just checked (updates cooldown timestamp)."""
        self._state["check_history"][strad_id] = datetime.now().isoformat()
        self._save()

    def get_recently_checked(self, cooldown_hours: int = 1) -> List[str]:
        """
        Get list of strad IDs checked within the cooldown window.

        Args:
            cooldown_hours: Hours to look back (default 1)

        Returns:
            List of strad IDs that should be excluded from next selection
        """
        cutoff = datetime.now() - timedelta(hours=cooldown_hours)
        recently_checked = []

        for strad_id, timestamp_str in self._state["check_history"].items():
            try:
                check_time = datetime.fromisoformat(timestamp_str)
                if check_time > cutoff:
                    recently_checked.append(strad_id)
            except (ValueError, TypeError):
                continue

        return recently_checked

    # -------------------------------------------------------------------------
    # Classification Results
    # -------------------------------------------------------------------------

    def store_classification(
        self,
        strad_id: str,
        classification: str,
        confidence: float,
        snapshot_path: Optional[str] = None
    ) -> None:
        """Store a classification result."""
        self._state["classification_results"].append({
            "strad_id": strad_id,
            "classification": classification,
            "confidence": confidence,
            "snapshot_path": snapshot_path,
            "timestamp": datetime.now().isoformat()
        })
        self._save()

    def get_results(self, limit: int = 50) -> List[Dict]:
        """Get most recent classification results."""
        return self._state["classification_results"][-limit:]

    # -------------------------------------------------------------------------
    # Critical Exclusions
    # -------------------------------------------------------------------------

    def add_critical_exclusion(self, strad_id: str, reason: str = "") -> None:
        """Add strad to critical exclusion list."""
        self._state["critical_exclusions"][strad_id] = {
            "timestamp": datetime.now().isoformat(),
            "reason": reason
        }
        self._save()

    def get_critical_exclusions(self) -> List[str]:
        """Get list of all critically-excluded strad IDs."""
        return list(self._state["critical_exclusions"].keys())

    def remove_critical_exclusion(self, strad_id: str) -> bool:
        """Remove strad from critical exclusion list. Returns True if found."""
        if strad_id in self._state["critical_exclusions"]:
            del self._state["critical_exclusions"][strad_id]
            self._save()
            return True
        return False

    def clear_all(self) -> None:
        """Reset all state (for testing/debugging)."""
        self._state = {
            "check_history": {},
            "classification_results": [],
            "critical_exclusions": {}
        }
        self._save()
        logger.info("Local state cleared")

    # -------------------------------------------------------------------------
    # Filtering helper
    # -------------------------------------------------------------------------

    def filter_eligible_strads(
        self,
        strad_list: List[str],
        cooldown_hours: int = 1
    ) -> List[str]:
        """
        Filter a strad list by removing recently-checked and critical strads.

        Use this after getting strads from the remote DB to apply local
        cooldown and exclusion state.

        Args:
            strad_list: Raw strad list from remote DB query
            cooldown_hours: Cooldown window in hours

        Returns:
            Filtered list with recently-checked and critical strads removed
        """
        recently_checked = set(self.get_recently_checked(cooldown_hours))
        critical = set(self.get_critical_exclusions())
        excluded = recently_checked | critical

        filtered = [s for s in strad_list if s not in excluded]

        if excluded:
            removed = set(strad_list) - set(filtered)
            if removed:
                logger.info(
                    f"Local state filtered out {len(removed)} strads: "
                    f"{list(removed)[:5]}{'...' if len(removed) > 5 else ''}"
                )

        return filtered

    def summary(self) -> str:
        """Get a summary of local state."""
        return (
            f"Local State Store:\n"
            f"  File: {self.state_path}\n"
            f"  Check history records: {len(self._state['check_history'])}\n"
            f"  Classification results: {len(self._state['classification_results'])}\n"
            f"  Critical exclusions: {len(self._state['critical_exclusions'])}"
        )
