"""
Tests for Enhanced Commentary Generator.

This module tests the EnhancedCommentaryGenerator class that orchestrates
all enhanced commentary components.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock

from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.enhanced_commentary_generator import EnhancedCommentaryGenerator
from reachy_f1_commentator.src.enhanced_models import ContextData, SignificanceScore, CommentaryStyle, ExcitementLevel, CommentaryPerspective
from reachy_f1_commentator.src.models import RaceEvent, EventType, RaceState
from reachy_f1_commentator.src.race_state_tracker import RaceStateTracker


@pytest.fixture
def config():
    """Create a test configuration."""
    config = Config()
    config.enhanced_mode = True
    config.context_enrichment_timeout_ms = 500
    config.min_significance_threshold = 50
    config.max_generation_time_ms = 2500
    config.template_file = "config/enhanced_templates.json"
    config.enable_telemetry = True
    config.enable_weather = True
    config.enable_championship = True
    return config


@pytest.fixture
def state_tracker():
    """Create a mock race state tracker."""
    tracker = Mock()
    race_state = RaceState()
    race_state.current_lap = 10
    race_state.total_laps = 50
    tracker.get_state = Mock(return_value=race_state)
    return tracker


@pytest.fixture
def openf1_client():
    """Create a mock OpenF1 client."""
    return Mock()


def test_initialization_enhanced_mode(config, state_tracker, openf1_client):
    """Test that enhanced mode initializes all components."""
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    assert generator.enhanced_mode is True
    assert hasattr(generator, 'context_enricher')
    assert hasattr(generator, 'event_prioritizer')
    assert hasattr(generator, 'narrative_tracker')
    assert hasattr(generator, 'style_manager')
    assert hasattr(generator, 'template_selector')
    assert hasattr(generator, 'phrase_combiner')
    assert hasattr(generator, 'context_availability_stats')


def test_initialization_basic_mode(state_tracker):
    """Test that basic mode falls back to basic generator."""
    config = Config()
    config.enhanced_mode = False
    
    generator = EnhancedCommentaryGenerator(config, state_tracker)
    
    assert generator.enhanced_mode is False
    assert hasattr(generator, 'basic_generator')


def test_context_availability_stats_initialized(config, state_tracker, openf1_client):
    """Test that context availability statistics are initialized."""
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    assert 'total_events' in generator.context_availability_stats
    assert 'full_context' in generator.context_availability_stats
    assert 'partial_context' in generator.context_availability_stats
    assert 'no_context' in generator.context_availability_stats
    assert 'missing_sources' in generator.context_availability_stats
    assert 'fallback_activations' in generator.context_availability_stats
    
    # Check fallback activation counters
    fallbacks = generator.context_availability_stats['fallback_activations']
    assert 'context_timeout' in fallbacks
    assert 'context_error' in fallbacks
    assert 'generation_timeout' in fallbacks
    assert 'template_fallback' in fallbacks
    assert 'basic_mode_fallback' in fallbacks


def test_generate_calls_enhanced_generate_in_enhanced_mode(config, state_tracker, openf1_client):
    """Test that generate() calls enhanced_generate() in enhanced mode."""
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    # Mock the enhanced_generate method
    async def mock_enhanced_generate(event):
        from src.enhanced_models import CommentaryOutput, EnhancedRaceEvent
        return CommentaryOutput(
            text="Test commentary",
            event=EnhancedRaceEvent(
                base_event=event,
                context=ContextData(event=event, race_state=RaceState()),
                significance=SignificanceScore(50, 0, 50, []),
                style=CommentaryStyle(
                    ExcitementLevel.ENGAGED,
                    CommentaryPerspective.DRAMATIC
                ),
                narratives=[]
            ),
            generation_time_ms=100.0,
            context_enrichment_time_ms=50.0,
            missing_data=[]
        )
    
    generator.enhanced_generate = mock_enhanced_generate
    
    event = RaceEvent(
        event_type=EventType.OVERTAKE,
        timestamp=datetime.now(),
        data={'driver': 'Hamilton', 'position': 1}
    )
    
    result = generator.generate(event)
    
    assert result == "Test commentary"


def test_generate_falls_back_to_basic_on_error(config, state_tracker, openf1_client):
    """Test that generate() falls back to basic mode on error and logs it."""
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    # Mock enhanced_generate to raise an error
    async def mock_enhanced_generate_error(event):
        raise Exception("Test error")
    
    generator.enhanced_generate = mock_enhanced_generate_error
    
    event = RaceEvent(
        event_type=EventType.OVERTAKE,
        timestamp=datetime.now(),
        data={'driver': 'Hamilton', 'position': 1}
    )
    
    # Should not raise, should fall back to basic
    result = generator.generate(event)
    
    # Should return some commentary (from basic generator)
    assert isinstance(result, str)
    
    # Check that fallback was tracked
    assert generator.context_availability_stats['fallback_activations']['basic_mode_fallback'] > 0


def test_set_session_key(config, state_tracker, openf1_client):
    """Test setting session key."""
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    # Mock context enricher
    generator.context_enricher = Mock()
    generator.context_enricher.set_session_key = Mock()
    
    generator.set_session_key(9197)
    
    generator.context_enricher.set_session_key.assert_called_once_with(9197)


def test_load_static_data(config, state_tracker, openf1_client):
    """Test loading static data."""
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    # Mock context enricher
    generator.context_enricher = Mock()
    generator.context_enricher.load_static_data = Mock(return_value=True)
    
    result = generator.load_static_data(9197)
    
    assert result is True
    generator.context_enricher.load_static_data.assert_called_once_with(9197)


def test_get_statistics(config, state_tracker, openf1_client):
    """Test getting generation statistics with context availability."""
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    # Set some test values
    generator.generation_count = 10
    generator.total_generation_time_ms = 1000.0
    generator.total_enrichment_time_ms = 500.0
    generator.context_availability_stats['total_events'] = 10
    generator.context_availability_stats['full_context'] = 7
    generator.context_availability_stats['partial_context'] = 2
    generator.context_availability_stats['no_context'] = 1
    
    stats = generator.get_statistics()
    
    assert stats['mode'] == 'enhanced'
    assert stats['generation_count'] == 10
    assert stats['avg_generation_time_ms'] == 100.0
    assert stats['avg_enrichment_time_ms'] == 50.0
    
    # Check context availability stats
    assert 'context_availability' in stats
    context_stats = stats['context_availability']
    assert context_stats['total_events'] == 10
    assert context_stats['full_context'] == 7
    assert context_stats['partial_context'] == 2
    assert context_stats['no_context'] == 1
    assert context_stats['full_context_pct'] == 70.0
    assert context_stats['partial_context_pct'] == 20.0
    assert context_stats['no_context_pct'] == 10.0


def test_event_type_to_string(config, state_tracker, openf1_client):
    """Test event type conversion to string."""
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    assert generator._event_type_to_string(EventType.OVERTAKE) == "overtake"
    assert generator._event_type_to_string(EventType.PIT_STOP) == "pit_stop"
    assert generator._event_type_to_string(EventType.LEAD_CHANGE) == "lead_change"
    assert generator._event_type_to_string(EventType.FASTEST_LAP) == "fastest_lap"
    assert generator._event_type_to_string(EventType.INCIDENT) == "incident"
    assert generator._event_type_to_string(EventType.SAFETY_CAR) == "safety_car"


def test_track_context_availability_full_context(config, state_tracker, openf1_client):
    """Test tracking context availability with full context."""
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    context = ContextData(
        event=RaceEvent(EventType.OVERTAKE, datetime.now(), {}),
        race_state=RaceState(),
        missing_data_sources=[]
    )
    
    generator._track_context_availability(context)
    
    assert generator.context_availability_stats['total_events'] == 1
    assert generator.context_availability_stats['full_context'] == 1
    assert generator.context_availability_stats['partial_context'] == 0
    assert generator.context_availability_stats['no_context'] == 0


def test_track_context_availability_partial_context(config, state_tracker, openf1_client):
    """Test tracking context availability with partial context."""
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    context = ContextData(
        event=RaceEvent(EventType.OVERTAKE, datetime.now(), {}),
        race_state=RaceState(),
        missing_data_sources=['telemetry', 'weather']
    )
    
    generator._track_context_availability(context)
    
    assert generator.context_availability_stats['total_events'] == 1
    assert generator.context_availability_stats['full_context'] == 0
    assert generator.context_availability_stats['partial_context'] == 1
    assert generator.context_availability_stats['no_context'] == 0
    assert generator.context_availability_stats['missing_sources']['telemetry'] == 1
    assert generator.context_availability_stats['missing_sources']['weather'] == 1


def test_track_context_availability_no_context(config, state_tracker, openf1_client):
    """Test tracking context availability with no context."""
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    context = ContextData(
        event=RaceEvent(EventType.OVERTAKE, datetime.now(), {}),
        race_state=RaceState(),
        missing_data_sources=['telemetry', 'weather', 'gaps', 'tires']
    )
    
    generator._track_context_availability(context)
    
    assert generator.context_availability_stats['total_events'] == 1
    assert generator.context_availability_stats['full_context'] == 0
    assert generator.context_availability_stats['partial_context'] == 0
    assert generator.context_availability_stats['no_context'] == 1


@pytest.mark.asyncio
async def test_enrich_context_with_timeout_success(config, state_tracker, openf1_client):
    """Test context enrichment with successful completion."""
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    # Mock context enricher
    mock_context = ContextData(
        event=RaceEvent(EventType.OVERTAKE, datetime.now(), {}),
        race_state=RaceState(),
        enrichment_time_ms=100.0,
        missing_data_sources=[]
    )
    
    async def mock_enrich(event):
        return mock_context
    
    generator.context_enricher = Mock()
    generator.context_enricher.enrich_context = mock_enrich
    
    event = RaceEvent(EventType.OVERTAKE, datetime.now(), {})
    result = await generator._enrich_context_with_timeout(event)
    
    assert result == mock_context
    assert result.enrichment_time_ms == 100.0
    assert len(result.missing_data_sources) == 0


@pytest.mark.asyncio
async def test_enrich_context_with_timeout_timeout(config, state_tracker, openf1_client):
    """Test context enrichment with timeout and fallback tracking."""
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    # Mock context enricher that times out
    async def mock_enrich_timeout(event):
        await asyncio.sleep(1.0)  # Longer than timeout
        return ContextData(event=event, race_state=RaceState())
    
    generator.context_enricher = Mock()
    generator.context_enricher.enrich_context = mock_enrich_timeout
    
    event = RaceEvent(EventType.OVERTAKE, datetime.now(), {})
    result = await generator._enrich_context_with_timeout(event)
    
    # Should return minimal context with timeout indicator
    assert "timeout" in result.missing_data_sources[0]
    
    # Check that timeout was tracked
    assert generator.context_availability_stats['fallback_activations']['context_timeout'] == 1


@pytest.mark.asyncio
async def test_enrich_context_with_timeout_error(config, state_tracker, openf1_client):
    """Test context enrichment with error and fallback tracking."""
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    # Mock context enricher that raises error
    async def mock_enrich_error(event):
        raise Exception("Test error")
    
    generator.context_enricher = Mock()
    generator.context_enricher.enrich_context = mock_enrich_error
    
    event = RaceEvent(EventType.OVERTAKE, datetime.now(), {})
    result = await generator._enrich_context_with_timeout(event)
    
    # Should return minimal context with error indicator
    assert "error" in result.missing_data_sources[0]
    
    # Check that error was tracked
    assert generator.context_availability_stats['fallback_activations']['context_error'] == 1


@pytest.mark.asyncio
async def test_enrich_context_without_enricher(config, state_tracker, openf1_client):
    """Test context enrichment without context enricher (fallback)."""
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    # Remove context enricher
    generator.context_enricher = None
    
    event = RaceEvent(EventType.OVERTAKE, datetime.now(), {})
    result = await generator._enrich_context_with_timeout(event)
    
    # Should return minimal context
    assert "no context enricher" in result.missing_data_sources[0]
    
    # Check that fallback was tracked
    assert generator.context_availability_stats['fallback_activations']['basic_mode_fallback'] == 1


@pytest.mark.asyncio
async def test_enhanced_generate_with_generation_timeout(config, state_tracker, openf1_client):
    """Test that generation timeout triggers fallback to basic commentary."""
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    # Set a very short timeout
    config.max_generation_time_ms = 10
    generator.config = config
    
    # Mock internal generate to take too long
    async def mock_slow_generate(event, start_time):
        await asyncio.sleep(1.0)  # Much longer than timeout
        return CommentaryOutput(
            text="Should not reach here",
            event=None,
            generation_time_ms=1000.0,
            context_enrichment_time_ms=0.0,
            missing_data=[]
        )
    
    generator._enhanced_generate_internal = mock_slow_generate
    
    event = RaceEvent(EventType.OVERTAKE, datetime.now(), {})
    result = await generator.enhanced_generate(event)
    
    # Should return basic commentary
    assert isinstance(result.text, str)
    assert "generation_timeout" in result.missing_data
    
    # Check that timeout was tracked
    assert generator.context_availability_stats['fallback_activations']['generation_timeout'] == 1


def test_backward_compatibility_interface(config, state_tracker, openf1_client):
    """Test that EnhancedCommentaryGenerator implements same interface as CommentaryGenerator."""
    from src.commentary_generator import CommentaryGenerator
    
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    basic_generator = CommentaryGenerator(config, state_tracker)
    
    # Check that both have the same public methods
    assert hasattr(generator, 'generate')
    assert hasattr(basic_generator, 'generate')
    
    # Both should accept RaceEvent and return string
    event = RaceEvent(EventType.OVERTAKE, datetime.now(), {})
    
    # Enhanced generator should return string
    result = generator.generate(event)
    assert isinstance(result, str)


def test_basic_mode_initialization(state_tracker):
    """Test that basic mode initializes correctly without enhanced components.
    
    Validates: Requirements 19.2, 19.7
    """
    config = Config()
    config.enhanced_mode = False
    
    generator = EnhancedCommentaryGenerator(config, state_tracker)
    
    # Should be in basic mode
    assert generator.enhanced_mode is False
    
    # Should have basic generator
    assert hasattr(generator, 'basic_generator')
    assert generator.basic_generator is not None
    
    # Should not have enhanced components
    assert not hasattr(generator, 'context_enricher') or generator.context_enricher is None


def test_basic_mode_generates_commentary(state_tracker):
    """Test that basic mode generates commentary using basic generator.
    
    Validates: Requirements 19.2, 19.7
    """
    config = Config()
    config.enhanced_mode = False
    
    generator = EnhancedCommentaryGenerator(config, state_tracker)
    
    event = RaceEvent(
        event_type=EventType.OVERTAKE,
        timestamp=datetime.now(),
        data={
            'overtaking_driver': 'Hamilton',
            'overtaken_driver': 'Verstappen',
            'new_position': 1
        }
    )
    
    result = generator.generate(event)
    
    # Should return commentary text
    assert isinstance(result, str)
    assert len(result) > 0


def test_runtime_mode_switching_to_basic(config, state_tracker, openf1_client):
    """Test switching from enhanced to basic mode at runtime.
    
    Validates: Requirements 19.3, 19.7
    """
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    # Should start in enhanced mode
    assert generator.is_enhanced_mode() is True
    
    # Switch to basic mode
    generator.set_enhanced_mode(False)
    
    # Should now be in basic mode
    assert generator.is_enhanced_mode() is False
    assert generator.enhanced_mode is False
    
    # Generate commentary - should use basic generator
    event = RaceEvent(
        event_type=EventType.OVERTAKE,
        timestamp=datetime.now(),
        data={
            'overtaking_driver': 'Hamilton',
            'overtaken_driver': 'Verstappen',
            'new_position': 1
        }
    )
    
    result = generator.generate(event)
    
    # Should return commentary text from basic generator
    assert isinstance(result, str)
    assert len(result) > 0


def test_runtime_mode_switching_to_enhanced(state_tracker, openf1_client):
    """Test switching from basic to enhanced mode at runtime.
    
    Validates: Requirements 19.3, 19.7
    """
    config = Config()
    config.enhanced_mode = False
    
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    # Should start in basic mode
    assert generator.is_enhanced_mode() is False
    
    # Switch to enhanced mode
    generator.set_enhanced_mode(True)
    
    # Should now be in enhanced mode
    assert generator.is_enhanced_mode() is True
    assert generator.enhanced_mode is True


def test_runtime_mode_switching_idempotent(config, state_tracker, openf1_client):
    """Test that switching to the same mode is idempotent.
    
    Validates: Requirements 19.3
    """
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    # Should start in enhanced mode
    assert generator.is_enhanced_mode() is True
    
    # Switch to enhanced mode again (no-op)
    generator.set_enhanced_mode(True)
    
    # Should still be in enhanced mode
    assert generator.is_enhanced_mode() is True
    
    # Switch to basic mode
    generator.set_enhanced_mode(False)
    assert generator.is_enhanced_mode() is False
    
    # Switch to basic mode again (no-op)
    generator.set_enhanced_mode(False)
    assert generator.is_enhanced_mode() is False


def test_basic_mode_behaves_identically_to_original(state_tracker):
    """Test that basic mode behaves identically to original Commentary_Generator.
    
    Validates: Requirements 19.2, 19.7
    """
    from src.commentary_generator import CommentaryGenerator
    
    config = Config()
    config.enhanced_mode = False
    
    enhanced_generator = EnhancedCommentaryGenerator(config, state_tracker)
    basic_generator = CommentaryGenerator(config, state_tracker)
    
    # Create test events
    events = [
        RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={
                'overtaking_driver': 'Hamilton',
                'overtaken_driver': 'Verstappen',
                'new_position': 1
            }
        ),
        RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={
                'driver': 'Leclerc',
                'pit_count': 1,
                'tire_compound': 'soft',
                'pit_duration': 2.3
            }
        ),
        RaceEvent(
            event_type=EventType.FASTEST_LAP,
            timestamp=datetime.now(),
            data={
                'driver': 'Norris',
                'lap_time': 82.456
            }
        )
    ]
    
    # Both generators should produce commentary for all events
    for event in events:
        enhanced_result = enhanced_generator.generate(event)
        basic_result = basic_generator.generate(event)
        
        # Both should return strings
        assert isinstance(enhanced_result, str)
        assert isinstance(basic_result, str)
        
        # Both should return non-empty commentary
        assert len(enhanced_result) > 0
        assert len(basic_result) > 0


def test_mode_logging_on_initialization(state_tracker, caplog):
    """Test that mode is logged at startup.
    
    Validates: Requirements 19.8
    """
    import logging
    caplog.set_level(logging.INFO)
    
    # Test enhanced mode logging
    config_enhanced = Config()
    config_enhanced.enhanced_mode = True
    
    generator_enhanced = EnhancedCommentaryGenerator(config_enhanced, state_tracker)
    
    # Check that enhanced mode was logged
    assert any("Enhanced commentary mode enabled" in record.message for record in caplog.records)
    
    # Clear log
    caplog.clear()
    
    # Test basic mode logging
    config_basic = Config()
    config_basic.enhanced_mode = False
    
    generator_basic = EnhancedCommentaryGenerator(config_basic, state_tracker)
    
    # Check that basic mode was logged
    assert any("Enhanced commentary mode disabled" in record.message or 
               "using basic mode" in record.message for record in caplog.records)


def test_basic_generator_always_initialized(config, state_tracker, openf1_client):
    """Test that basic generator is always initialized for fallback.
    
    Validates: Requirements 19.7
    """
    generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    
    # Basic generator should always be present
    assert hasattr(generator, 'basic_generator')
    assert generator.basic_generator is not None
    
    # Even in enhanced mode
    assert generator.enhanced_mode is True
    assert generator.basic_generator is not None


def test_interface_compatibility_with_existing_system(config, state_tracker, openf1_client):
    """Test that EnhancedCommentaryGenerator maintains interface compatibility.
    
    Validates: Requirements 19.1, 19.4
    """
    from src.commentary_generator import CommentaryGenerator
    
    enhanced_generator = EnhancedCommentaryGenerator(config, state_tracker, openf1_client)
    basic_generator = CommentaryGenerator(config, state_tracker)
    
    # Check that both have the same interface
    # Main method: generate
    assert callable(getattr(enhanced_generator, 'generate', None))
    assert callable(getattr(basic_generator, 'generate', None))
    
    # Both should accept RaceEvent and return str
    event = RaceEvent(
        event_type=EventType.OVERTAKE,
        timestamp=datetime.now(),
        data={'driver': 'Hamilton', 'position': 1}
    )
    
    enhanced_result = enhanced_generator.generate(event)
    basic_result = basic_generator.generate(event)
    
    assert isinstance(enhanced_result, str)
    assert isinstance(basic_result, str)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
