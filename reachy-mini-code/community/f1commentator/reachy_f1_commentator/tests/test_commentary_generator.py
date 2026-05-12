"""
Tests for Commentary Generator module.

Tests template system, style adaptation, and commentary generation.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from reachy_f1_commentator.src.commentary_generator import (
    CommentaryGenerator,
    TemplateEngine,
    CommentaryStyle,
    get_style_for_phase,
    AIEnhancer,
    OVERTAKE_TEMPLATES,
    PIT_STOP_TEMPLATES,
    LEAD_CHANGE_TEMPLATES,
)
from reachy_f1_commentator.src.models import RaceEvent, EventType, RacePhase, DriverState
from reachy_f1_commentator.src.race_state_tracker import RaceStateTracker
from reachy_f1_commentator.src.config import Config


# ============================================================================
# Template Engine Tests
# ============================================================================

class TestTemplateEngine:
    """Test the template engine functionality."""
    
    def test_select_template_returns_valid_template(self):
        """Test that template selection returns a valid template string."""
        engine = TemplateEngine()
        style = CommentaryStyle(excitement_level=0.8, detail_level="moderate")
        
        template = engine.select_template(EventType.OVERTAKE, style)
        
        assert template in OVERTAKE_TEMPLATES
        assert isinstance(template, str)
        assert len(template) > 0
    
    def test_select_template_for_all_event_types(self):
        """Test template selection for all event types."""
        engine = TemplateEngine()
        style = CommentaryStyle(excitement_level=0.8, detail_level="moderate")
        
        event_types = [
            EventType.OVERTAKE,
            EventType.PIT_STOP,
            EventType.LEAD_CHANGE,
            EventType.FASTEST_LAP,
            EventType.INCIDENT,
            EventType.SAFETY_CAR,
            EventType.FLAG,
        ]
        
        for event_type in event_types:
            template = engine.select_template(event_type, style)
            assert isinstance(template, str)
            assert len(template) > 0
    
    def test_populate_template_with_complete_data(self):
        """Test template population with all required data."""
        engine = TemplateEngine()
        template = "{driver1} overtakes {driver2} for P{position}!"
        event_data = {
            "driver1": "Hamilton",
            "driver2": "Verstappen",
            "position": 1
        }
        
        result = engine.populate_template(template, event_data)
        
        assert result == "Hamilton overtakes Verstappen for P1!"
    
    def test_populate_template_with_missing_data(self):
        """Test template population handles missing data gracefully."""
        engine = TemplateEngine()
        template = "{driver1} overtakes {driver2} for P{position}!"
        event_data = {
            "driver1": "Hamilton",
            # Missing driver2 and position
        }
        
        result = engine.populate_template(template, event_data)
        
        # Should not crash and should contain available data
        assert "Hamilton" in result
        assert "[data unavailable]" in result or "driver2" not in result
    
    def test_populate_template_with_state_data(self):
        """Test template population with both event and state data."""
        engine = TemplateEngine()
        template = "{driver} in P{position}, gap to leader: {gap_to_leader:.1f}s"
        event_data = {"driver": "Leclerc", "position": 3}
        state_data = {"gap_to_leader": 5.234}
        
        result = engine.populate_template(template, event_data, state_data)
        
        assert "Leclerc" in result
        assert "P3" in result
        assert "5.2" in result


# ============================================================================
# Commentary Style Tests
# ============================================================================

class TestCommentaryStyle:
    """Test commentary style system."""
    
    def test_get_style_for_start_phase(self):
        """Test style for race start phase."""
        style = get_style_for_phase(RacePhase.START)
        
        assert style.excitement_level == 0.9
        assert style.detail_level == "detailed"
    
    def test_get_style_for_mid_race_phase(self):
        """Test style for mid-race phase."""
        style = get_style_for_phase(RacePhase.MID_RACE)
        
        assert style.excitement_level == 0.6
        assert style.detail_level == "moderate"
    
    def test_get_style_for_finish_phase(self):
        """Test style for finish phase."""
        style = get_style_for_phase(RacePhase.FINISH)
        
        assert style.excitement_level == 1.0
        assert style.detail_level == "detailed"


# ============================================================================
# AI Enhancer Tests
# ============================================================================

class TestAIEnhancer:
    """Test AI enhancement functionality."""
    
    def test_ai_enhancer_disabled_by_default(self):
        """Test that AI enhancer is disabled when not configured."""
        config = Config(ai_enabled=False)
        enhancer = AIEnhancer(config)
        
        assert not enhancer.enabled
        assert enhancer.client is None
    
    def test_ai_enhancer_returns_original_when_disabled(self):
        """Test that disabled enhancer returns original text."""
        config = Config(ai_enabled=False)
        enhancer = AIEnhancer(config)
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        
        original = "Hamilton overtakes Verstappen!"
        result = enhancer.enhance(original, event)
        
        assert result == original
    
    def test_ai_enhancer_fallback_on_error(self):
        """Test that enhancer falls back to template on error."""
        config = Config(
            ai_enabled=True,
            ai_provider="openai",
            ai_api_key="test_key"
        )
        enhancer = AIEnhancer(config)
        # Force client to None to simulate error
        enhancer.client = None
        
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        
        original = "Hamilton overtakes Verstappen!"
        result = enhancer.enhance(original, event)
        
        assert result == original


# ============================================================================
# Commentary Generator Tests
# ============================================================================

class TestCommentaryGenerator:
    """Test the main commentary generator."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return Config(ai_enabled=False)
    
    @pytest.fixture
    def state_tracker(self):
        """Create mock state tracker."""
        tracker = RaceStateTracker()
        # Add some test drivers
        tracker._state.drivers = [
            DriverState(name="Hamilton", position=1, gap_to_leader=0.0),
            DriverState(name="Verstappen", position=2, gap_to_leader=2.5),
            DriverState(name="Leclerc", position=3, gap_to_leader=5.0),
        ]
        tracker._state.current_lap = 10
        tracker._state.total_laps = 50
        return tracker
    
    @pytest.fixture
    def generator(self, config, state_tracker):
        """Create commentary generator."""
        return CommentaryGenerator(config, state_tracker)
    
    def test_generator_initialization(self, generator):
        """Test that generator initializes correctly."""
        assert generator.template_engine is not None
        assert generator.ai_enhancer is not None
        assert generator.state_tracker is not None
    
    def test_generate_overtake_commentary(self, generator):
        """Test generating commentary for overtake event."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={
                "overtaking_driver": "Hamilton",
                "overtaken_driver": "Verstappen",
                "new_position": 1,
                "lap_number": 10
            }
        )
        
        commentary = generator.generate(event)
        
        assert isinstance(commentary, str)
        assert len(commentary) > 0
        # Should contain driver names
        assert "Hamilton" in commentary or "Verstappen" in commentary
    
    def test_generate_pit_stop_commentary(self, generator):
        """Test generating commentary for pit stop event."""
        event = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={
                "driver": "Leclerc",
                "pit_count": 1,
                "tire_compound": "soft",
                "pit_duration": 2.3,
                "lap_number": 15
            }
        )
        
        commentary = generator.generate(event)
        
        assert isinstance(commentary, str)
        assert "Leclerc" in commentary
        # Should mention pit stop number or tire compound
        assert "1" in commentary or "soft" in commentary
    
    def test_generate_lead_change_commentary(self, generator):
        """Test generating commentary for lead change event."""
        event = RaceEvent(
            event_type=EventType.LEAD_CHANGE,
            timestamp=datetime.now(),
            data={
                "new_leader": "Verstappen",
                "old_leader": "Hamilton",
                "lap_number": 20
            }
        )
        
        commentary = generator.generate(event)
        
        assert isinstance(commentary, str)
        # Should mention at least one of the drivers involved
        assert "Verstappen" in commentary or "Hamilton" in commentary
    
    def test_generate_fastest_lap_commentary(self, generator):
        """Test generating commentary for fastest lap event."""
        event = RaceEvent(
            event_type=EventType.FASTEST_LAP,
            timestamp=datetime.now(),
            data={
                "driver": "Hamilton",
                "lap_time": 78.456,
                "lap_number": 25
            }
        )
        
        commentary = generator.generate(event)
        
        assert isinstance(commentary, str)
        assert "Hamilton" in commentary
        assert "78.456" in commentary or "78.5" in commentary
    
    def test_generate_handles_missing_data(self, generator):
        """Test that generator handles events with missing data."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}  # Missing required data
        )
        
        # Should not crash
        commentary = generator.generate(event)
        
        assert isinstance(commentary, str)
        assert len(commentary) > 0
    
    def test_generate_adapts_to_race_phase(self, generator, state_tracker):
        """Test that commentary style adapts to race phase."""
        # Set to finish phase
        state_tracker._state.current_lap = 48
        state_tracker._state.total_laps = 50
        
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={
                "overtaking_driver": "Hamilton",
                "overtaken_driver": "Verstappen",
                "new_position": 1
            }
        )
        
        commentary = generator.generate(event)
        
        # Should generate commentary (style adaptation is internal)
        assert isinstance(commentary, str)
        assert len(commentary) > 0
    
    def test_apply_template_uses_state_data(self, generator):
        """Test that apply_template incorporates state data."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={
                "overtaking_driver": "Hamilton",
                "overtaken_driver": "Verstappen",
                "new_position": 1
            }
        )
        style = CommentaryStyle(excitement_level=0.8, detail_level="moderate")
        
        commentary = generator.apply_template(event, style)
        
        assert isinstance(commentary, str)
        assert len(commentary) > 0
    
    def test_generate_error_handling(self, generator):
        """Test that generator handles errors gracefully."""
        # Create event with invalid type
        event = RaceEvent(
            event_type=EventType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data=None  # Invalid data
        )
        
        # Should not crash
        commentary = generator.generate(event)
        
        assert isinstance(commentary, str)
        assert len(commentary) > 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestCommentaryGeneratorIntegration:
    """Integration tests for commentary generator with real components."""
    
    def test_end_to_end_overtake_commentary(self):
        """Test complete overtake commentary generation flow."""
        config = Config(ai_enabled=False)
        tracker = RaceStateTracker()
        
        # Set up race state
        tracker._state.drivers = [
            DriverState(name="Hamilton", position=2, gap_to_leader=1.5),
            DriverState(name="Verstappen", position=1, gap_to_leader=0.0),
        ]
        tracker._state.current_lap = 15
        tracker._state.total_laps = 50
        
        generator = CommentaryGenerator(config, tracker)
        
        # Create overtake event
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={
                "overtaking_driver": "Hamilton",
                "overtaken_driver": "Verstappen",
                "new_position": 1,
                "lap_number": 15
            }
        )
        
        commentary = generator.generate(event)
        
        # Verify commentary quality
        assert isinstance(commentary, str)
        assert len(commentary) > 10  # Reasonable length
        assert "Hamilton" in commentary
        # Should mention overtake or position change
        assert "overtake" in commentary.lower() or "P1" in commentary or "lead" in commentary.lower()
    
    def test_multiple_events_generate_varied_commentary(self):
        """Test that multiple events generate different commentary."""
        config = Config(ai_enabled=False)
        tracker = RaceStateTracker()
        tracker._state.current_lap = 20
        tracker._state.total_laps = 50
        
        generator = CommentaryGenerator(config, tracker)
        
        # Generate commentary for same event type multiple times
        commentaries = []
        for i in range(5):
            event = RaceEvent(
                event_type=EventType.OVERTAKE,
                timestamp=datetime.now(),
                data={
                    "overtaking_driver": "Hamilton",
                    "overtaken_driver": "Verstappen",
                    "new_position": 1
                }
            )
            commentary = generator.generate(event)
            commentaries.append(commentary)
        
        # Should have some variety (random template selection)
        # At least 2 different commentaries in 5 attempts
        unique_commentaries = set(commentaries)
        assert len(unique_commentaries) >= 2
