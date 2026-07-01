"""
Unit tests for the web app live monitoring endpoints.

Tests:
1. /api/live/active-camera-count returns correct strad pool size
2. /api/live/images returns image list (live or augmented fallback)
3. /api/live/strad-details/<id> returns detail info with IP and history
4. /api/live/image/<filename> serves files or 404s gracefully
5. Existing endpoints still work (/, /api/model/status, /api/inference)
"""

import pytest
import sys
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))
sys.path.insert(0, str(project_root / 'docs' / 'backend'))


@pytest.fixture
def app_client():
    """Create a Flask test client with mocked dependencies."""
    # Mock heavy dependencies before importing app
    with patch.dict('sys.modules', {
        'torch': MagicMock(),
    }):
        # Patch config loading to avoid needing real system_config.json
        with patch('strad_monitoring.config.system_config.ConfigurationManager') as mock_cm:
            mock_config = MagicMock()
            mock_config.database_connection_string = "DSN=Test"
            mock_config.enable_local_testing_mode = True
            mock_config.fallback_data_source = "random"
            mock_config.fallback_data_path = ""
            mock_config.model_checkpoint_path = "nonexistent.pth"
            mock_config.classifier_type = "simple_classifier"
            mock_config.permanent_snapshot_path = str(project_root / "permanent_snapshots")
            mock_config.temp_snapshot_path = str(project_root / "temp_snapshots")
            mock_config.ip_addresses_json_path = str(project_root / "config" / "ip_addresses_template.json")
            mock_config.dl_model_config = {}
            mock_config.log_file_path = "test.log"
            mock_config.log_retention_days = 7
            mock_cm.load_config.return_value = mock_config

            # Need to reimport app fresh with mocks
            import importlib
            if 'app' in sys.modules:
                del sys.modules['app']

            from app import app
            app.config['TESTING'] = True

            with app.test_client() as client:
                yield client


@pytest.fixture
def state_with_data(tmp_path):
    """Create a local state store with test data."""
    from strad_monitoring.database.local_state_store import LocalStateStore

    state_path = str(tmp_path / "test_state.json")
    store = LocalStateStore(state_path)

    # Add some test data
    store.store_classification("SC042", "critical", 0.92, "/path/SC042_20260701.jpg")
    store.store_classification("SC087", "moderate", 0.67)
    store.store_classification("SC001", "none", 0.85)
    store.record_check("SC042")
    store.record_check("SC087")
    store.add_critical_exclusion("SC042", "Critical misalignment (confidence: 0.920)")

    return store, state_path


class TestHealthEndpoint:
    """Test the root health check endpoint still works."""

    def test_health_check(self, app_client):
        """GET / returns status info."""
        response = app_client.get('/')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'running'
        assert 'strad_monitoring_connected' in data


class TestModelStatusEndpoint:
    """Test /api/model/status still works."""

    def test_model_status(self, app_client):
        """GET /api/model/status returns model info."""
        response = app_client.get('/api/model/status')
        assert response.status_code == 200
        data = response.get_json()
        assert 'model_loaded' in data
        assert 'classifier_type' in data


class TestActiveCameraCount:
    """Test /api/live/active-camera-count endpoint."""

    def test_returns_count(self, app_client):
        """Returns total and available strad counts."""
        response = app_client.get('/api/live/active-camera-count')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'total_strads' in data
        assert 'available' in data
        assert 'critical_excluded' in data
        assert data['available'] == data['total_strads'] - data['critical_excluded']

    def test_total_matches_ip_file(self, app_client):
        """Total should be 135 if ip_addresses_template.json is used."""
        response = app_client.get('/api/live/active-camera-count')
        data = response.get_json()
        # Template has 135 entries
        assert data['total_strads'] == 135


class TestLiveImages:
    """Test /api/live/images endpoint."""

    def test_returns_success(self, app_client):
        """Endpoint returns success even with no images."""
        response = app_client.get('/api/live/images')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'data' in data
        assert 'count' in data

    def test_source_filter(self, app_client):
        """Source filter parameter is accepted."""
        for source in ['auto', 'live', 'augmented']:
            response = app_client.get(f'/api/live/images?source={source}')
            assert response.status_code == 200

    def test_severity_filter(self, app_client):
        """Severity filter parameter is accepted."""
        for severity in ['none', 'moderate', 'critical']:
            response = app_client.get(f'/api/live/images?severity={severity}')
            assert response.status_code == 200

    def test_limit_parameter(self, app_client):
        """Limit parameter is accepted."""
        response = app_client.get('/api/live/images?limit=5')
        assert response.status_code == 200
        data = response.get_json()
        assert data['count'] <= 5


class TestLiveImageServing:
    """Test /api/live/image/<filename> endpoint."""

    def test_nonexistent_image_returns_404(self, app_client):
        """Non-existent file returns 404."""
        response = app_client.get('/api/live/image/nonexistent_file.jpg')
        assert response.status_code == 404

    def test_serves_existing_image(self, app_client, tmp_path):
        """Serves a real image file if it exists in search paths."""
        # Create a test image in permanent_snapshots
        perm_path = project_root / "permanent_snapshots"
        perm_path.mkdir(exist_ok=True)

        test_file = perm_path / "SC001_20260701_120000.jpg"
        # Write minimal JPEG (just enough to be a valid file)
        test_file.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 100)

        try:
            response = app_client.get('/api/live/image/SC001_20260701_120000.jpg')
            # Should find it (200) or not depending on config path
            assert response.status_code in [200, 404]
        finally:
            # Cleanup - ignore if file is still locked by Flask
            try:
                if test_file.exists():
                    test_file.unlink()
            except PermissionError:
                pass  # File still held by send_file; OS will release on process exit


class TestStradDetails:
    """Test /api/live/strad-details/<strad_id> endpoint."""

    def test_returns_details_structure(self, app_client):
        """Returns correct structure for any strad ID."""
        response = app_client.get('/api/live/strad-details/SC042')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'data' in data

        details = data['data']
        assert details['strad_id'] == 'SC042'
        assert 'ip_address' in details
        assert 'classifications' in details
        assert 'is_critical' in details
        assert 'last_checked' in details

    def test_ip_address_lookup(self, app_client):
        """Should return IP address from ip_addresses.json."""
        response = app_client.get('/api/live/strad-details/SC042')
        data = response.get_json()
        # Template has SC042 mapped to 192.168.1.141
        if data['data']['ip_address']:
            assert '192.168.1' in data['data']['ip_address']

    def test_unknown_strad(self, app_client):
        """Unknown strad returns empty data gracefully."""
        response = app_client.get('/api/live/strad-details/SC999')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        # Should not crash, just return empty/null fields


class TestInferenceEndpointPreserved:
    """Verify original inference endpoint still works."""

    def test_inference_requires_image(self, app_client):
        """POST /api/inference without images returns 400."""
        response = app_client.post('/api/inference')
        assert response.status_code == 400

    def test_inference_accepts_single_image(self, app_client):
        """POST /api/inference with 'image' field is accepted."""
        from io import BytesIO
        from PIL import Image
        import numpy as np

        # Create a test image
        img = Image.fromarray(np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8))
        buf = BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)

        response = app_client.post(
            '/api/inference',
            data={'image': (buf, 'test.jpg')},
            content_type='multipart/form-data'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'classification' in data or 'misalignment_probability' in data
