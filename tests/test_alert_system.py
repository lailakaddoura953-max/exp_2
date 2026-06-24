"""
Unit tests for Alert System Module

Tests multi-channel alerting with:
- Property 14: Alert Delivery for High Severity Events
"""

import pytest
import time
from datetime import datetime

from src.alerting.alert_system import (
    AlertSystem,
    AlertRecord,
    MockAlertChannel
)
from src.models.core import (
    MisalignmentEvent,
    Severity,
    DisplacementMetrics
)
import numpy as np


class TestMockAlertChannel:
    """Test MockAlertChannel"""
    
    def test_create_mock_channel(self):
        """Test creating mock alert channel"""
        channel = MockAlertChannel("test-channel")
        
        assert channel.get_channel_name() == "test-channel"
        assert channel.get_alert_count() == 0
    
    def test_send_alert_success(self):
        """Test sending alert successfully"""
        channel = MockAlertChannel("test-channel")
        event = self.create_event(Severity.HIGH)
        
        success = channel.send_alert(event)
        
        assert success is True
        assert channel.get_alert_count() == 1
        assert channel.alerts_received[0] == event
    
    def test_send_alert_failure(self):
        """Test sending alert with failure"""
        channel = MockAlertChannel("test-channel", fail_on_send=True)
        event = self.create_event(Severity.HIGH)
        
        success = channel.send_alert(event)
        
        assert success is False
        assert channel.get_alert_count() == 0
    
    def test_clear_alerts(self):
        """Test clearing received alerts"""
        channel = MockAlertChannel("test-channel")
        
        channel.send_alert(self.create_event(Severity.HIGH))
        channel.send_alert(self.create_event(Severity.CRITICAL))
        assert channel.get_alert_count() == 2
        
        channel.clear_alerts()
        assert channel.get_alert_count() == 0
    
    def create_event(self, severity):
        """Helper to create misalignment event"""
        displacement = DisplacementMetrics(
            position_delta=np.array([0.1, 0, 0]),
            position_delta_magnitude=0.1,
            angle_delta=np.array([5, 0, 0]),
            angle_delta_magnitude=5.0,
            flow_inconsistency=0.2
        )
        
        return MisalignmentEvent(
            event_id="test-event",
            camera_id=0,
            timestamp=datetime.now(),
            severity=severity,
            displacement=displacement,
            confidence=0.9,
            diagnostic_data={}
        )



class TestAlertSystemInit:
    """Test AlertSystem initialization"""
    
    def test_init_valid(self):
        """Test valid initialization"""
        channels = [MockAlertChannel("ch1"), MockAlertChannel("ch2")]
        system = AlertSystem(channels)
        
        assert len(system.channels) == 2
        assert system.rate_limit_seconds == 60.0
        assert system.max_history_size == 1000
    
    def test_init_custom_params(self):
        """Test initialization with custom parameters"""
        channels = [MockAlertChannel("ch1")]
        system = AlertSystem(
            channels=channels,
            rate_limit_seconds=30.0,
            max_history_size=500
        )
        
        assert system.rate_limit_seconds == 30.0
        assert system.max_history_size == 500
    
    def test_init_invalid_rate_limit(self):
        """Test error when rate_limit_seconds is negative"""
        channels = [MockAlertChannel("ch1")]
        
        with pytest.raises(ValueError, match="rate_limit_seconds must be non-negative"):
            AlertSystem(channels, rate_limit_seconds=-10.0)
    
    def test_init_invalid_history_size(self):
        """Test error when max_history_size is non-positive"""
        channels = [MockAlertChannel("ch1")]
        
        with pytest.raises(ValueError, match="max_history_size must be positive"):
            AlertSystem(channels, max_history_size=0)


class TestProperty14AlertDelivery:
    """Test Property 14: Alert Delivery for High Severity Events"""
    
    @pytest.fixture
    def system(self):
        """Create alert system with mock channel"""
        channel = MockAlertChannel("test-channel")
        return AlertSystem([channel], rate_limit_seconds=0)  # No rate limiting for tests
    
    def create_event(self, severity, camera_id=0):
        """Helper to create event"""
        displacement = DisplacementMetrics(
            position_delta=np.array([0.1, 0, 0]),
            position_delta_magnitude=0.1,
            angle_delta=np.array([0, 0, 0]),
            angle_delta_magnitude=0.0,
            flow_inconsistency=0.0
        )
        
        return MisalignmentEvent(
            event_id=f"event-{severity.name}-{camera_id}",
            camera_id=camera_id,
            timestamp=datetime.now(),
            severity=severity,
            displacement=displacement,
            confidence=0.9,
            diagnostic_data={}
        )
    
    def test_property_14_high_severity_sends_alert(self, system):
        """Test Property 14: HIGH severity events trigger alerts"""
        event = self.create_event(Severity.HIGH)
        
        result = system.process_event(event)
        
        assert result is True
        assert system.channels[0].get_alert_count() == 1
        assert system.alerts_sent == 1
    
    def test_property_14_critical_severity_sends_alert(self, system):
        """Test Property 14: CRITICAL severity events trigger alerts"""
        event = self.create_event(Severity.CRITICAL)
        
        result = system.process_event(event)
        
        assert result is True
        assert system.channels[0].get_alert_count() == 1
        assert system.alerts_sent == 1
    
    def test_property_14_low_severity_filtered(self, system):
        """Test Property 14: LOW severity events are filtered"""
        event = self.create_event(Severity.LOW)
        
        result = system.process_event(event)
        
        assert result is False
        assert system.channels[0].get_alert_count() == 0
        assert system.alerts_filtered == 1
    
    def test_property_14_medium_severity_filtered(self, system):
        """Test Property 14: MEDIUM severity events are filtered"""
        event = self.create_event(Severity.MEDIUM)
        
        result = system.process_event(event)
        
        assert result is False
        assert system.channels[0].get_alert_count() == 0
        assert system.alerts_filtered == 1


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    @pytest.fixture
    def system(self):
        """Create system with 1 second rate limit"""
        channel = MockAlertChannel("test-channel")
        return AlertSystem([channel], rate_limit_seconds=1.0)
    
    def create_event(self, camera_id):
        """Helper"""
        displacement = DisplacementMetrics(
            position_delta=np.array([0.1, 0, 0]),
            position_delta_magnitude=0.1,
            angle_delta=np.array([0, 0, 0]),
            angle_delta_magnitude=0.0,
            flow_inconsistency=0.0
        )
        
        return MisalignmentEvent(
            event_id=f"event-{camera_id}",
            camera_id=camera_id,
            timestamp=datetime.now(),
            severity=Severity.HIGH,
            displacement=displacement,
            confidence=0.9,
            diagnostic_data={}
        )

    
    def test_first_alert_sent(self, system):
        """Test first alert is sent immediately"""
        event = self.create_event(camera_id=0)
        
        result = system.process_event(event)
        
        assert result is True
        assert system.channels[0].get_alert_count() == 1
        assert system.alerts_sent == 1
    
    def test_second_alert_rate_limited(self, system):
        """Test second alert within rate limit is blocked"""
        event1 = self.create_event(camera_id=0)
        event2 = self.create_event(camera_id=0)
        
        result1 = system.process_event(event1)
        result2 = system.process_event(event2)
        
        assert result1 is True
        assert result2 is False
        assert system.channels[0].get_alert_count() == 1
        assert system.alerts_rate_limited == 1
    
    def test_alert_sent_after_waiting(self, system):
        """Test alert sent after waiting for rate limit"""
        event1 = self.create_event(camera_id=0)
        event2 = self.create_event(camera_id=0)
        
        system.process_event(event1)
        time.sleep(1.1)  # Wait for rate limit to expire
        result = system.process_event(event2)
        
        assert result is True
        assert system.channels[0].get_alert_count() == 2
    
    def test_different_cameras_not_rate_limited(self, system):
        """Test different cameras have independent rate limits"""
        event_cam0 = self.create_event(camera_id=0)
        event_cam1 = self.create_event(camera_id=1)
        
        result1 = system.process_event(event_cam0)
        result2 = system.process_event(event_cam1)
        
        assert result1 is True
        assert result2 is True
        assert system.channels[0].get_alert_count() == 2
    
    def test_clear_rate_limit_single_camera(self, system):
        """Test clearing rate limit for single camera"""
        event = self.create_event(camera_id=0)
        
        system.process_event(event)
        system.clear_rate_limit(camera_id=0)
        result = system.process_event(event)
        
        assert result is True
        assert system.channels[0].get_alert_count() == 2
    
    def test_clear_rate_limit_all_cameras(self, system):
        """Test clearing rate limit for all cameras"""
        event0 = self.create_event(camera_id=0)
        event1 = self.create_event(camera_id=1)
        
        system.process_event(event0)
        system.process_event(event1)
        
        system.clear_rate_limit()  # Clear all
        
        result0 = system.process_event(event0)
        result1 = system.process_event(event1)
        
        assert result0 is True
        assert result1 is True
        assert system.channels[0].get_alert_count() == 4



class TestMultipleChannels:
    """Test alert distribution across multiple channels"""
    
    @pytest.fixture
    def system(self):
        """Create system with multiple channels"""
        ch1 = MockAlertChannel("channel-1")
        ch2 = MockAlertChannel("channel-2")
        ch3 = MockAlertChannel("channel-3")
        return AlertSystem([ch1, ch2, ch3], rate_limit_seconds=0)
    
    def create_event(self):
        """Helper to create event"""
        displacement = DisplacementMetrics(
            position_delta=np.array([0.1, 0, 0]),
            position_delta_magnitude=0.1,
            angle_delta=np.array([0, 0, 0]),
            angle_delta_magnitude=0.0,
            flow_inconsistency=0.0
        )
        
        return MisalignmentEvent(
            event_id="test-event",
            camera_id=0,
            timestamp=datetime.now(),
            severity=Severity.HIGH,
            displacement=displacement,
            confidence=0.9,
            diagnostic_data={}
        )
    
    def test_alert_sent_to_all_channels(self, system):
        """Test alert is sent to all channels"""
        event = self.create_event()
        
        result = system.process_event(event)
        
        assert result is True
        assert system.channels[0].get_alert_count() == 1
        assert system.channels[1].get_alert_count() == 1
        assert system.channels[2].get_alert_count() == 1
    
    def test_partial_channel_failure(self, system):
        """Test alert succeeds if at least one channel works"""
        # Make middle channel fail
        system.channels[1].fail_on_send = True
        
        event = self.create_event()
        result = system.process_event(event)
        
        assert result is True  # Still succeeds
        assert system.channels[0].get_alert_count() == 1
        assert system.channels[1].get_alert_count() == 0  # Failed
        assert system.channels[2].get_alert_count() == 1
    
    def test_empty_channels_list(self):
        """Test system with no channels"""
        system = AlertSystem([], rate_limit_seconds=0)
        event = self.create_event()
        
        result = system.process_event(event)
        
        assert result is False  # No channels to send to
    
    def test_all_channels_fail(self, system):
        """Test when all channels fail"""
        for channel in system.channels:
            channel.fail_on_send = True
        
        event = self.create_event()
        result = system.process_event(event)
        
        assert result is False
        assert system.alerts_sent == 0



class TestProcessEvents:
    """Test batch event processing"""
    
    @pytest.fixture
    def system(self):
        """Create system"""
        channel = MockAlertChannel("test-channel")
        return AlertSystem([channel], rate_limit_seconds=0)
    
    def create_event(self, severity, camera_id=0):
        """Helper to create event"""
        displacement = DisplacementMetrics(
            position_delta=np.array([0.1, 0, 0]),
            position_delta_magnitude=0.1,
            angle_delta=np.array([0, 0, 0]),
            angle_delta_magnitude=0.0,
            flow_inconsistency=0.0
        )
        
        return MisalignmentEvent(
            event_id=f"event-{severity.name}-{camera_id}",
            camera_id=camera_id,
            timestamp=datetime.now(),
            severity=severity,
            displacement=displacement,
            confidence=0.9,
            diagnostic_data={}
        )
    
    def test_process_multiple_events(self, system):
        """Test processing multiple events"""
        events = [
            self.create_event(Severity.HIGH, camera_id=0),
            self.create_event(Severity.CRITICAL, camera_id=1),
            self.create_event(Severity.HIGH, camera_id=2)
        ]
        
        count = system.process_events(events)
        
        assert count == 3
        assert system.channels[0].get_alert_count() == 3
    
    def test_mixed_severities(self, system):
        """Test processing events with mixed severities"""
        events = [
            self.create_event(Severity.LOW, camera_id=0),     # Filtered
            self.create_event(Severity.HIGH, camera_id=1),    # Sent
            self.create_event(Severity.MEDIUM, camera_id=2),  # Filtered
            self.create_event(Severity.CRITICAL, camera_id=3) # Sent
        ]
        
        count = system.process_events(events)
        
        assert count == 2  # Only HIGH and CRITICAL
        assert system.alerts_filtered == 2
        assert system.alerts_sent == 2
    
    def test_empty_events_list(self, system):
        """Test processing empty event list"""
        count = system.process_events([])
        
        assert count == 0
        assert system.channels[0].get_alert_count() == 0



class TestAlertHistory:
    """Test alert history tracking"""
    
    @pytest.fixture
    def system(self):
        """Create system with small history size"""
        channel = MockAlertChannel("test-channel")
        return AlertSystem([channel], rate_limit_seconds=0, max_history_size=10)
    
    def create_event(self, severity, camera_id):
        """Helper to create event"""
        displacement = DisplacementMetrics(
            position_delta=np.array([0.1, 0, 0]),
            position_delta_magnitude=0.1,
            angle_delta=np.array([0, 0, 0]),
            angle_delta_magnitude=0.0,
            flow_inconsistency=0.0
        )
        
        return MisalignmentEvent(
            event_id=f"event-{camera_id}-{severity.name}",
            camera_id=camera_id,
            timestamp=datetime.now(),
            severity=severity,
            displacement=displacement,
            confidence=0.9,
            diagnostic_data={}
        )
    
    def test_history_recording(self, system):
        """Test alert history is recorded"""
        event = self.create_event(Severity.HIGH, camera_id=0)
        
        system.process_event(event)
        
        history = system.get_alert_history()
        assert len(history) == 1
        assert history[0].event_id == event.event_id
        assert history[0].camera_id == 0
        assert history[0].severity == Severity.HIGH
        assert history[0].success is True
    
    def test_get_alert_history_no_filters(self, system):
        """Test retrieving all alert history"""
        system.process_event(self.create_event(Severity.HIGH, camera_id=0))
        system.process_event(self.create_event(Severity.CRITICAL, camera_id=1))
        system.process_event(self.create_event(Severity.HIGH, camera_id=2))
        
        history = system.get_alert_history()
        
        assert len(history) == 3
        # Most recent first
        assert history[0].camera_id == 2
        assert history[2].camera_id == 0
    
    def test_filter_by_camera_id(self, system):
        """Test filtering history by camera ID"""
        system.process_event(self.create_event(Severity.HIGH, camera_id=0))
        system.process_event(self.create_event(Severity.HIGH, camera_id=1))
        system.process_event(self.create_event(Severity.HIGH, camera_id=0))
        
        history = system.get_alert_history(camera_id=0)
        
        assert len(history) == 2
        assert all(r.camera_id == 0 for r in history)
    
    def test_filter_by_severity(self, system):
        """Test filtering history by severity"""
        system.process_event(self.create_event(Severity.HIGH, camera_id=0))
        system.process_event(self.create_event(Severity.CRITICAL, camera_id=1))
        system.process_event(self.create_event(Severity.HIGH, camera_id=2))
        
        history = system.get_alert_history(severity=Severity.HIGH)
        
        assert len(history) == 2
        assert all(r.severity == Severity.HIGH for r in history)
    
    def test_limit_parameter(self, system):
        """Test limiting number of results"""
        for i in range(5):
            system.process_event(self.create_event(Severity.HIGH, camera_id=i % 4))
        
        history = system.get_alert_history(limit=3)
        
        assert len(history) == 3
    
    def test_bounded_history(self, system):
        """Test history is bounded to max_history_size"""
        # max_history_size = 10 in fixture
        for i in range(15):
            system.process_event(self.create_event(Severity.HIGH, camera_id=i % 4))
        
        history = system.get_alert_history()
        
        # Only last 10 kept
        assert len(history) == 10



class TestStatistics:
    """Test statistics tracking"""
    
    @pytest.fixture
    def system(self):
        """Create system"""
        channel = MockAlertChannel("test-channel")
        return AlertSystem([channel], rate_limit_seconds=1.0)
    
    def create_event(self, severity, camera_id=0):
        """Helper to create event"""
        displacement = DisplacementMetrics(
            position_delta=np.array([0.1, 0, 0]),
            position_delta_magnitude=0.1,
            angle_delta=np.array([0, 0, 0]),
            angle_delta_magnitude=0.0,
            flow_inconsistency=0.0
        )
        
        return MisalignmentEvent(
            event_id=f"event-{camera_id}",
            camera_id=camera_id,
            timestamp=datetime.now(),
            severity=severity,
            displacement=displacement,
            confidence=0.9,
            diagnostic_data={}
        )
    
    def test_alerts_sent_counter(self, system):
        """Test alerts_sent counter increments"""
        system.process_event(self.create_event(Severity.HIGH, camera_id=0))
        system.process_event(self.create_event(Severity.CRITICAL, camera_id=1))
        
        assert system.alerts_sent == 2
    
    def test_alerts_rate_limited_counter(self, system):
        """Test alerts_rate_limited counter increments"""
        event = self.create_event(Severity.HIGH, camera_id=0)
        
        system.process_event(event)
        system.process_event(event)  # Rate limited
        system.process_event(event)  # Rate limited
        
        assert system.alerts_rate_limited == 2
    
    def test_alerts_filtered_counter(self, system):
        """Test alerts_filtered counter increments"""
        system.process_event(self.create_event(Severity.LOW, camera_id=0))
        system.process_event(self.create_event(Severity.MEDIUM, camera_id=1))
        
        assert system.alerts_filtered == 2
    
    def test_reset_statistics(self, system):
        """Test resetting statistics"""
        system.process_event(self.create_event(Severity.HIGH, camera_id=0))
        system.process_event(self.create_event(Severity.LOW, camera_id=1))
        system.process_event(self.create_event(Severity.HIGH, camera_id=0))  # Rate limited
        
        assert system.alerts_sent > 0
        assert system.alerts_filtered > 0
        assert system.alerts_rate_limited > 0
        
        system.reset_statistics()
        
        assert system.alerts_sent == 0
        assert system.alerts_filtered == 0
        assert system.alerts_rate_limited == 0
    
    def test_get_statistics(self, system):
        """Test get_statistics method"""
        system.process_event(self.create_event(Severity.HIGH, camera_id=0))
        system.process_event(self.create_event(Severity.LOW, camera_id=1))
        
        stats = system.get_statistics()
        
        assert 'alerts_sent' in stats
        assert 'alerts_rate_limited' in stats
        assert 'alerts_filtered' in stats
        assert 'history_size' in stats
        assert 'history_capacity' in stats
        
        assert stats['alerts_sent'] == 1
        assert stats['alerts_filtered'] == 1
        assert stats['history_size'] == 1
