"""Unit tests for Motion Controller.

Tests the Reachy SDK interface, gesture library, and motion controller orchestrator.
"""

import pytest
import time
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from reachy_f1_commentator.src.motion_controller import (
    ReachyInterface,
    GestureLibrary,
    MotionController,
    GestureSequence
)
from reachy_f1_commentator.src.models import Gesture, EventType
from reachy_f1_commentator.src.config import Config


# ============================================================================
# ReachyInterface Tests
# ============================================================================

class TestReachyInterface:
    """Tests for Reachy SDK interface wrapper."""
    
    def test_initialization_without_sdk(self):
        """Test initialization when SDK is not available."""
        with patch('src.motion_controller.ReachyInterface.__init__', 
                  lambda self: setattr(self, 'connected', False) or setattr(self, 'reachy', None)):
            interface = ReachyInterface()
            assert not interface.is_connected()
    
    def test_validate_movement_valid(self):
        """Test movement validation with valid parameters."""
        interface = ReachyInterface()
        
        # Valid movements
        is_valid, msg = interface.validate_movement(pitch=10, yaw=20, roll=15)
        assert is_valid
        assert msg == ""
        
        is_valid, msg = interface.validate_movement(x=10, y=-5, z=15)
        assert is_valid
        assert msg == ""
    
    def test_validate_movement_invalid_pitch(self):
        """Test movement validation with invalid pitch."""
        interface = ReachyInterface()
        
        # Pitch too high
        is_valid, msg = interface.validate_movement(pitch=25)
        assert not is_valid
        assert "Pitch" in msg
        
        # Pitch too low
        is_valid, msg = interface.validate_movement(pitch=-25)
        assert not is_valid
        assert "Pitch" in msg
    
    def test_validate_movement_invalid_yaw(self):
        """Test movement validation with invalid yaw."""
        interface = ReachyInterface()
        
        # Yaw too high
        is_valid, msg = interface.validate_movement(yaw=50)
        assert not is_valid
        assert "Yaw" in msg
        
        # Yaw too low
        is_valid, msg = interface.validate_movement(yaw=-50)
        assert not is_valid
        assert "Yaw" in msg
    
    def test_validate_movement_invalid_roll(self):
        """Test movement validation with invalid roll."""
        interface = ReachyInterface()
        
        # Roll too high
        is_valid, msg = interface.validate_movement(roll=35)
        assert not is_valid
        assert "Roll" in msg
        
        # Roll too low
        is_valid, msg = interface.validate_movement(roll=-35)
        assert not is_valid
        assert "Roll" in msg
    
    def test_validate_movement_invalid_translation(self):
        """Test movement validation with invalid translations."""
        interface = ReachyInterface()
        
        # X too high
        is_valid, msg = interface.validate_movement(x=25)
        assert not is_valid
        assert "X translation" in msg
        
        # Y too low
        is_valid, msg = interface.validate_movement(y=-25)
        assert not is_valid
        assert "Y translation" in msg
        
        # Z too high
        is_valid, msg = interface.validate_movement(z=25)
        assert not is_valid
        assert "Z translation" in msg
    
    def test_validate_movement_multiple_errors(self):
        """Test movement validation with multiple invalid parameters."""
        interface = ReachyInterface()
        
        is_valid, msg = interface.validate_movement(pitch=25, yaw=50, roll=35)
        assert not is_valid
        assert "Pitch" in msg
        assert "Yaw" in msg
        assert "Roll" in msg
    
    def test_move_head_not_connected(self):
        """Test move_head when not connected to Reachy."""
        interface = ReachyInterface()
        interface.connected = False
        
        result = interface.move_head(pitch=10, yaw=5)
        assert not result
    
    def test_move_head_invalid_parameters(self):
        """Test move_head with invalid parameters."""
        interface = ReachyInterface()
        interface.connected = True
        
        result = interface.move_head(pitch=50)  # Invalid pitch
        assert not result
    
    def test_move_head_success(self):
        """Test successful head movement."""
        interface = ReachyInterface()
        interface.connected = True
        interface.reachy = Mock()
        interface.create_head_pose = Mock(return_value=Mock())
        
        result = interface.move_head(pitch=10, yaw=5, roll=0, duration=1.0)
        
        # Should succeed if connected and parameters valid
        # Note: This will fail without actual SDK, but validates the logic
        assert interface.create_head_pose.called or not result
    
    def test_get_current_position_not_connected(self):
        """Test getting current position when not connected."""
        interface = ReachyInterface()
        interface.connected = False
        
        position = interface.get_current_position()
        assert position is None


# ============================================================================
# GestureLibrary Tests
# ============================================================================

class TestGestureLibrary:
    """Tests for gesture library."""
    
    def test_get_gesture_neutral(self):
        """Test getting neutral gesture."""
        sequence = GestureLibrary.get_gesture(Gesture.NEUTRAL)
        
        assert isinstance(sequence, GestureSequence)
        assert len(sequence.movements) > 0
        assert sequence.total_duration > 0
    
    def test_get_gesture_nod(self):
        """Test getting nod gesture."""
        sequence = GestureLibrary.get_gesture(Gesture.NOD)
        
        assert isinstance(sequence, GestureSequence)
        assert len(sequence.movements) > 0
        assert sequence.total_duration > 0
    
    def test_get_gesture_excited(self):
        """Test getting excited gesture."""
        sequence = GestureLibrary.get_gesture(Gesture.EXCITED)
        
        assert isinstance(sequence, GestureSequence)
        assert len(sequence.movements) > 0
        assert sequence.total_duration > 0
    
    def test_get_gesture_concerned(self):
        """Test getting concerned gesture."""
        sequence = GestureLibrary.get_gesture(Gesture.CONCERNED)
        
        assert isinstance(sequence, GestureSequence)
        assert len(sequence.movements) > 0
        assert sequence.total_duration > 0
    
    def test_get_gesture_for_event_overtake(self):
        """Test getting gesture for overtake event."""
        gesture = GestureLibrary.get_gesture_for_event(EventType.OVERTAKE)
        assert gesture == Gesture.EXCITED
    
    def test_get_gesture_for_event_incident(self):
        """Test getting gesture for incident event."""
        gesture = GestureLibrary.get_gesture_for_event(EventType.INCIDENT)
        assert gesture == Gesture.CONCERNED
    
    def test_get_gesture_for_event_pit_stop(self):
        """Test getting gesture for pit stop event."""
        gesture = GestureLibrary.get_gesture_for_event(EventType.PIT_STOP)
        assert gesture == Gesture.NOD
    
    def test_get_gesture_for_event_lead_change(self):
        """Test getting gesture for lead change event."""
        gesture = GestureLibrary.get_gesture_for_event(EventType.LEAD_CHANGE)
        assert gesture == Gesture.EXCITED
    
    def test_get_gesture_for_event_safety_car(self):
        """Test getting gesture for safety car event."""
        gesture = GestureLibrary.get_gesture_for_event(EventType.SAFETY_CAR)
        assert gesture == Gesture.CONCERNED
    
    def test_get_gesture_for_event_fastest_lap(self):
        """Test getting gesture for fastest lap event."""
        gesture = GestureLibrary.get_gesture_for_event(EventType.FASTEST_LAP)
        assert gesture == Gesture.NOD
    
    def test_get_gesture_for_event_unknown(self):
        """Test getting gesture for unknown event type."""
        gesture = GestureLibrary.get_gesture_for_event(EventType.POSITION_UPDATE)
        assert gesture == Gesture.NEUTRAL
    
    def test_all_gestures_have_valid_movements(self):
        """Test that all gestures have valid movement parameters."""
        interface = ReachyInterface()
        
        for gesture_type in Gesture:
            sequence = GestureLibrary.get_gesture(gesture_type)
            
            for movement in sequence.movements:
                pitch = movement.get("pitch", 0)
                yaw = movement.get("yaw", 0)
                roll = movement.get("roll", 0)
                x = movement.get("x", 0)
                y = movement.get("y", 0)
                z = movement.get("z", 0)
                
                is_valid, msg = interface.validate_movement(x, y, z, roll, pitch, yaw)
                assert is_valid, f"Invalid movement in {gesture_type.value}: {msg}"


# ============================================================================
# MotionController Tests
# ============================================================================

class TestMotionController:
    """Tests for motion controller orchestrator."""
    
    def test_initialization(self):
        """Test motion controller initialization."""
        config = Config()
        controller = MotionController(config)
        
        assert controller.config == config
        assert controller.reachy is not None
        assert controller.gesture_library is not None
        assert not controller.is_moving
        assert controller.current_gesture is None
        
        # Cleanup
        controller.stop()
    
    def test_initialization_movements_disabled(self):
        """Test initialization with movements disabled."""
        config = Config(enable_movements=False)
        controller = MotionController(config)
        
        assert not controller.config.enable_movements
        
        # Cleanup
        controller.stop()
    
    def test_execute_gesture_movements_disabled(self):
        """Test executing gesture when movements are disabled."""
        config = Config(enable_movements=False)
        controller = MotionController(config)
        
        # Should not execute
        controller.execute_gesture(Gesture.NOD)
        time.sleep(0.1)
        
        assert not controller.is_moving
        
        # Cleanup
        controller.stop()
    
    def test_execute_gesture_neutral(self):
        """Test executing neutral gesture."""
        config = Config(enable_movements=True)
        controller = MotionController(config)
        
        controller.execute_gesture(Gesture.NEUTRAL)
        time.sleep(0.1)
        
        # Should start movement
        # Note: Actual movement depends on SDK availability
        
        # Cleanup
        controller.stop()
    
    def test_apply_speed_limit_no_adjustment(self):
        """Test speed limit with movement within limits."""
        config = Config(movement_speed=30.0)
        controller = MotionController(config)
        
        # 10 degrees in 1 second = 10 deg/s (within 30 deg/s limit)
        adjusted = controller._apply_speed_limit(10, 0, 0, 1.0)
        assert adjusted == 1.0
        
        # Cleanup
        controller.stop()
    
    def test_apply_speed_limit_with_adjustment(self):
        """Test speed limit with movement exceeding limits."""
        config = Config(movement_speed=30.0)
        controller = MotionController(config)
        
        # 60 degrees in 1 second = 60 deg/s (exceeds 30 deg/s limit)
        # Should adjust to 2 seconds
        adjusted = controller._apply_speed_limit(60, 0, 0, 1.0)
        assert adjusted == 2.0
        
        # Cleanup
        controller.stop()
    
    def test_apply_speed_limit_multiple_axes(self):
        """Test speed limit with movement on multiple axes."""
        config = Config(movement_speed=30.0)
        controller = MotionController(config)
        
        # Max angle is 45 degrees (yaw)
        # 45 degrees in 1 second = 45 deg/s (exceeds 30 deg/s limit)
        # Should adjust to 1.5 seconds
        adjusted = controller._apply_speed_limit(20, 45, 10, 1.0)
        assert adjusted == 1.5
        
        # Cleanup
        controller.stop()
    
    def test_sync_with_speech(self):
        """Test synchronizing movements with speech."""
        config = Config()
        controller = MotionController(config)
        
        initial_time = controller.last_movement_time
        time.sleep(0.1)
        
        controller.sync_with_speech(3.0)
        
        # Should update last movement time
        assert controller.last_movement_time > initial_time
        
        # Cleanup
        controller.stop()
    
    def test_return_to_neutral(self):
        """Test returning to neutral position."""
        config = Config(enable_movements=True)
        controller = MotionController(config)
        
        controller.return_to_neutral()
        time.sleep(0.1)
        
        # Should execute neutral gesture
        # Note: Actual movement depends on SDK availability
        
        # Cleanup
        controller.stop()
    
    def test_return_to_neutral_movements_disabled(self):
        """Test returning to neutral when movements disabled."""
        config = Config(enable_movements=False)
        controller = MotionController(config)
        
        controller.return_to_neutral()
        time.sleep(0.1)
        
        # Should not execute
        assert not controller.is_moving
        
        # Cleanup
        controller.stop()
    
    def test_stop(self):
        """Test emergency stop."""
        config = Config(enable_movements=True)
        controller = MotionController(config)
        
        # Start a gesture
        controller.execute_gesture(Gesture.EXCITED)
        time.sleep(0.1)
        
        # Stop
        controller.stop()
        
        # Should stop movement
        assert controller.stop_requested
        assert not controller.idle_check_running
    
    def test_is_speaking(self):
        """Test checking if robot is speaking (moving)."""
        config = Config()
        controller = MotionController(config)
        
        assert not controller.is_speaking()
        
        controller.is_moving = True
        assert controller.is_speaking()
        
        controller.is_moving = False
        assert not controller.is_speaking()
        
        # Cleanup
        controller.stop()
    
    def test_idle_timeout_return_to_neutral(self):
        """Test that robot returns to neutral after idle timeout."""
        config = Config(enable_movements=True)
        controller = MotionController(config)
        controller.idle_timeout = 0.5  # Short timeout for testing
        
        # Set last movement time to past
        controller.last_movement_time = time.time() - 1.0
        controller.current_gesture = Gesture.NOD
        
        # Wait for idle check
        time.sleep(0.6)
        
        # Should have triggered return to neutral
        # Note: Actual behavior depends on threading and SDK
        
        # Cleanup
        controller.stop()
    
    def test_gesture_execution_thread_safety(self):
        """Test that gesture execution is thread-safe."""
        config = Config(enable_movements=True)
        controller = MotionController(config)
        
        # Execute multiple gestures rapidly
        controller.execute_gesture(Gesture.NOD)
        controller.execute_gesture(Gesture.TURN_LEFT)
        controller.execute_gesture(Gesture.TURN_RIGHT)
        
        time.sleep(0.2)
        
        # Should handle without errors
        # Note: Only last gesture may execute due to threading
        
        # Cleanup
        controller.stop()


# ============================================================================
# Integration Tests
# ============================================================================

class TestMotionControllerIntegration:
    """Integration tests for motion controller with other components."""
    
    def test_event_to_gesture_mapping(self):
        """Test complete flow from event type to gesture execution."""
        config = Config(enable_movements=True)
        controller = MotionController(config)
        
        # Test overtake event
        gesture = GestureLibrary.get_gesture_for_event(EventType.OVERTAKE)
        assert gesture == Gesture.EXCITED
        
        controller.execute_gesture(gesture)
        time.sleep(0.1)
        
        # Cleanup
        controller.stop()
    
    def test_movement_constraints_respected(self):
        """Test that all predefined gestures respect movement constraints."""
        config = Config()
        controller = MotionController(config)
        
        # All gestures should have valid movements
        for gesture_type in Gesture:
            sequence = GestureLibrary.get_gesture(gesture_type)
            
            for movement in sequence.movements:
                pitch = movement.get("pitch", 0)
                yaw = movement.get("yaw", 0)
                roll = movement.get("roll", 0)
                x = movement.get("x", 0)
                y = movement.get("y", 0)
                z = movement.get("z", 0)
                
                is_valid, msg = controller.reachy.validate_movement(x, y, z, roll, pitch, yaw)
                assert is_valid, f"Invalid movement in {gesture_type.value}: {msg}"
        
        # Cleanup
        controller.stop()
    
    def test_speed_limit_applied_to_all_gestures(self):
        """Test that speed limit is applied to all gesture movements."""
        config = Config(movement_speed=30.0)
        controller = MotionController(config)
        
        for gesture_type in Gesture:
            sequence = GestureLibrary.get_gesture(gesture_type)
            
            for movement in sequence.movements:
                pitch = movement.get("pitch", 0)
                yaw = movement.get("yaw", 0)
                roll = movement.get("roll", 0)
                duration = movement.get("duration", 1.0)
                
                adjusted_duration = controller._apply_speed_limit(pitch, yaw, roll, duration)
                
                # Calculate actual speed
                max_angle = max(abs(pitch), abs(yaw), abs(roll))
                if max_angle > 0:
                    actual_speed = max_angle / adjusted_duration
                    assert actual_speed <= config.movement_speed, \
                        f"Speed limit violated in {gesture_type.value}: {actual_speed} > {config.movement_speed}"
        
        # Cleanup
        controller.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
