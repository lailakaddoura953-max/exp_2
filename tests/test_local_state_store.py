"""
Unit tests for LocalStateStore - JSON-based fallback for monitoring state.

Tests:
1. Check history recording and cooldown filtering
2. Classification result storage
3. Critical exclusion tracking and persistence across cycles
4. filter_eligible_strads correctly removes recently-checked and critical strads
5. State persists to file and loads back correctly
6. clear_all resets everything
"""

import pytest
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.strad_monitoring.database.local_state_store import LocalStateStore


@pytest.fixture
def state_file(tmp_path):
    """Create a temporary state file path."""
    return str(tmp_path / "test_state.json")


@pytest.fixture
def store(state_file):
    """Create a fresh LocalStateStore instance."""
    return LocalStateStore(state_file)


class TestCheckHistory:
    """Tests for cooldown/check history tracking."""

    def test_record_check_creates_entry(self, store):
        """Recording a check creates a timestamp entry."""
        store.record_check("SC042")
        recently = store.get_recently_checked(cooldown_hours=1)
        assert "SC042" in recently

    def test_recently_checked_respects_cooldown(self, store, state_file):
        """Strads checked outside the cooldown window are not returned."""
        # Manually inject a stale timestamp (2 hours ago)
        store._state["check_history"]["SC001"] = (
            datetime.now() - timedelta(hours=2)
        ).isoformat()
        store._save()

        recently = store.get_recently_checked(cooldown_hours=1)
        assert "SC001" not in recently

    def test_recently_checked_includes_fresh(self, store):
        """Strads checked within cooldown window are returned."""
        store.record_check("SC010")
        recently = store.get_recently_checked(cooldown_hours=1)
        assert "SC010" in recently

    def test_multiple_checks_tracked(self, store):
        """Multiple strads can be tracked independently."""
        store.record_check("SC001")
        store.record_check("SC002")
        store.record_check("SC003")
        recently = store.get_recently_checked(cooldown_hours=1)
        assert set(recently) == {"SC001", "SC002", "SC003"}


class TestClassificationResults:
    """Tests for classification result storage."""

    def test_store_classification(self, store):
        """Classification results are stored with correct fields."""
        store.store_classification("SC042", "critical", 0.92, "/path/snap.jpg")
        results = store.get_results()
        assert len(results) == 1
        assert results[0]["strad_id"] == "SC042"
        assert results[0]["classification"] == "critical"
        assert results[0]["confidence"] == 0.92
        assert results[0]["snapshot_path"] == "/path/snap.jpg"

    def test_multiple_results(self, store):
        """Multiple results accumulate in order."""
        store.store_classification("SC001", "none", 0.85)
        store.store_classification("SC002", "moderate", 0.67)
        store.store_classification("SC003", "critical", 0.95)
        results = store.get_results()
        assert len(results) == 3
        assert results[0]["strad_id"] == "SC001"
        assert results[2]["strad_id"] == "SC003"

    def test_get_results_limit(self, store):
        """get_results respects the limit parameter."""
        for i in range(20):
            store.store_classification(f"SC{i:03d}", "none", 0.5)
        results = store.get_results(limit=5)
        assert len(results) == 5


class TestCriticalExclusions:
    """Tests for critical strad exclusion management."""

    def test_add_critical_exclusion(self, store):
        """Critical exclusion is recorded."""
        store.add_critical_exclusion("SC087", "Critical misalignment")
        exclusions = store.get_critical_exclusions()
        assert "SC087" in exclusions

    def test_critical_persists_across_instances(self, state_file):
        """Critical exclusions persist to file and survive re-instantiation."""
        store1 = LocalStateStore(state_file)
        store1.add_critical_exclusion("SC050", "Test reason")
        del store1

        # New instance loads from same file
        store2 = LocalStateStore(state_file)
        assert "SC050" in store2.get_critical_exclusions()

    def test_remove_critical_exclusion(self, store):
        """Removing a critical exclusion works."""
        store.add_critical_exclusion("SC099", "Testing")
        assert "SC099" in store.get_critical_exclusions()

        result = store.remove_critical_exclusion("SC099")
        assert result is True
        assert "SC099" not in store.get_critical_exclusions()

    def test_remove_nonexistent_returns_false(self, store):
        """Removing a non-existent exclusion returns False."""
        result = store.remove_critical_exclusion("SC999")
        assert result is False

    def test_critical_exclusion_not_auto_cleared(self, store):
        """Critical exclusions stay until manually removed (not time-based)."""
        # Inject a critical exclusion from 48 hours ago
        store._state["critical_exclusions"]["SC010"] = {
            "timestamp": (datetime.now() - timedelta(hours=48)).isoformat(),
            "reason": "Old critical"
        }
        store._save()

        # Should still be excluded (no auto-expiry)
        assert "SC010" in store.get_critical_exclusions()


class TestFilterEligibleStrads:
    """Tests for the combined filtering logic."""

    def test_filters_recently_checked(self, store):
        """Recently checked strads are removed from eligible list."""
        store.record_check("SC002")
        store.record_check("SC005")

        input_list = ["SC001", "SC002", "SC003", "SC004", "SC005"]
        filtered = store.filter_eligible_strads(input_list, cooldown_hours=1)

        assert "SC002" not in filtered
        assert "SC005" not in filtered
        assert "SC001" in filtered
        assert "SC003" in filtered
        assert "SC004" in filtered

    def test_filters_critical_exclusions(self, store):
        """Critical strads are removed from eligible list."""
        store.add_critical_exclusion("SC003", "Critical")

        input_list = ["SC001", "SC002", "SC003", "SC004", "SC005"]
        filtered = store.filter_eligible_strads(input_list, cooldown_hours=1)

        assert "SC003" not in filtered
        assert len(filtered) == 4

    def test_filters_both_cooldown_and_critical(self, store):
        """Both cooldown and critical filtering applied together."""
        store.record_check("SC001")  # cooldown
        store.add_critical_exclusion("SC004", "Critical")  # critical

        input_list = ["SC001", "SC002", "SC003", "SC004", "SC005"]
        filtered = store.filter_eligible_strads(input_list, cooldown_hours=1)

        assert "SC001" not in filtered  # cooldown
        assert "SC004" not in filtered  # critical
        assert set(filtered) == {"SC002", "SC003", "SC005"}

    def test_expired_cooldown_not_filtered(self, store):
        """Strads past cooldown window are NOT filtered out."""
        # Inject stale check (2 hours ago)
        store._state["check_history"]["SC001"] = (
            datetime.now() - timedelta(hours=2)
        ).isoformat()
        store._save()

        input_list = ["SC001", "SC002"]
        filtered = store.filter_eligible_strads(input_list, cooldown_hours=1)

        assert "SC001" in filtered  # cooldown expired, should be eligible again


class TestPersistence:
    """Tests for file persistence."""

    def test_state_persists_to_file(self, store, state_file):
        """State is written to JSON file after each operation."""
        store.record_check("SC042")
        store.store_classification("SC042", "moderate", 0.7)

        assert os.path.exists(state_file)
        with open(state_file, 'r') as f:
            data = json.load(f)

        assert "SC042" in data["check_history"]
        assert len(data["classification_results"]) == 1

    def test_state_loads_on_init(self, state_file):
        """State is loaded from file when a new instance is created."""
        # Write some state
        store1 = LocalStateStore(state_file)
        store1.record_check("SC010")
        store1.store_classification("SC010", "none", 0.8)
        store1.add_critical_exclusion("SC099", "Test")
        del store1

        # New instance should have all that state
        store2 = LocalStateStore(state_file)
        assert "SC010" in store2.get_recently_checked(cooldown_hours=1)
        assert len(store2.get_results()) == 1
        assert "SC099" in store2.get_critical_exclusions()


class TestClearAll:
    """Tests for the clear_all reset."""

    def test_clear_all_resets_everything(self, store):
        """clear_all removes all state."""
        store.record_check("SC001")
        store.store_classification("SC001", "critical", 0.9)
        store.add_critical_exclusion("SC001", "Test")

        store.clear_all()

        assert store.get_recently_checked(cooldown_hours=24) == []
        assert store.get_results() == []
        assert store.get_critical_exclusions() == []
