"""Unit tests for Commentary Style Manager.

Tests excitement level mapping, perspective selection, variety enforcement,
and style orchestration for organic F1 commentary generation.
"""

import pytest
from collections import deque

from reachy_f1_commentator.src.commentary_style_manager import CommentaryStyleManager
from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.enhanced_models import (
    CommentaryPerspective,
    CommentaryStyle,
    ContextData,
    ExcitementLevel,
    SignificanceScore,
)
from reachy_f1_commentator.src.models import RaceEvent, RacePhase, RaceState


@pytest.fixture
def config():
    """Create test configuration."""
    return Config(
        excitement_threshold_calm=30,
        excitement_threshold_moderate=50,
        excitement_threshold_engaged=70,
        excitement_threshold_excited=85,
        perspective_weight_technical=0.25,
        perspective_weight_strategic=0.25,
        perspective_weight_dramatic=0.25,
        perspective_weight_positional=0.15,
        perspective_weight_historical=0.10,
    )


@pytest.fixture
def style_manager(config):
    """Create Commentary Style Manager instance."""
    return CommentaryStyleManager(config)


@pytest.fixture
def base_race_state():
    """Create base race state."""
    return RaceState(
        current_lap=10,
        total_laps=50,
        race_phase=RacePhase.MID_RACE,
    )


@pytest.fixture
def base_event():
    """Create base race event."""
    from datetime import datetime
    from src.models import EventType
    return RaceEvent(
        event_type=EventType.OVERTAKE,
        timestamp=datetime.fromisoformat("2024-01-01T12:00:00"),
        data={
            "driver": "Hamilton",
            "position": 3,
            "lap_number": 10,
        }
    )


@pytest.fixture
def base_context(base_event, base_race_state):
    """Create base context data."""
    return ContextData(
        event=base_event,
        race_state=base_race_state,
    )


class TestExcitementLevelMapping:
    """Test excitement level determination from significance scores."""
    
    def test_calm_excitement_low_score(self, style_manager, base_context):
        """Test CALM excitement for low significance scores (0-30)."""
        significance = SignificanceScore(base_score=20, context_bonus=0, total_score=20)
        excitement = style_manager._determine_excitement(significance, base_context)
        assert excitement == ExcitementLevel.CALM
    
    def test_calm_excitement_threshold(self, style_manager, base_context):
        """Test CALM excitement at threshold (30)."""
        significance = SignificanceScore(base_score=30, context_bonus=0, total_score=30)
        excitement = style_manager._determine_excitement(significance, base_context)
        assert excitement == ExcitementLevel.CALM
    
    def test_moderate_excitement(self, style_manager, base_context):
        """Test MODERATE excitement for scores 31-50."""
        significance = SignificanceScore(base_score=40, context_bonus=0, total_score=40)
        excitement = style_manager._determine_excitement(significance, base_context)
        assert excitement == ExcitementLevel.MODERATE
    
    def test_engaged_excitement(self, style_manager, base_context):
        """Test ENGAGED excitement for scores 51-70."""
        significance = SignificanceScore(base_score=60, context_bonus=0, total_score=60)
        excitement = style_manager._determine_excitement(significance, base_context)
        assert excitement == ExcitementLevel.ENGAGED
    
    def test_excited_excitement(self, style_manager, base_context):
        """Test EXCITED excitement for scores 71-85."""
        significance = SignificanceScore(base_score=80, context_bonus=0, total_score=80)
        excitement = style_manager._determine_excitement(significance, base_context)
        assert excitement == ExcitementLevel.EXCITED
    
    def test_dramatic_excitement(self, style_manager, base_context):
        """Test DRAMATIC excitement for scores 86-100."""
        significance = SignificanceScore(base_score=90, context_bonus=0, total_score=90)
        excitement = style_manager._determine_excitement(significance, base_context)
        assert excitement == ExcitementLevel.DRAMATIC
    
    def test_excitement_boost_in_final_laps(self, style_manager, base_context):
        """Test excitement boost during finish phase."""
        # Score of 75 would normally be EXCITED, but with finish boost becomes DRAMATIC
        base_context.race_state.race_phase = RacePhase.FINISH
        significance = SignificanceScore(base_score=75, context_bonus=0, total_score=75)
        excitement = style_manager._determine_excitement(significance, base_context)
        # 75 + 10 (finish boost) = 85, which is still EXCITED (threshold is 85)
        assert excitement == ExcitementLevel.EXCITED
        
        # Score of 76 with boost becomes 86, which is DRAMATIC
        significance = SignificanceScore(base_score=76, context_bonus=0, total_score=76)
        excitement = style_manager._determine_excitement(significance, base_context)
        assert excitement == ExcitementLevel.DRAMATIC
    
    def test_excitement_boost_capped_at_100(self, style_manager, base_context):
        """Test that excitement boost doesn't exceed 100."""
        base_context.race_state.race_phase = RacePhase.FINISH
        significance = SignificanceScore(base_score=95, context_bonus=0, total_score=95)
        excitement = style_manager._determine_excitement(significance, base_context)
        # Should still be DRAMATIC, not overflow
        assert excitement == ExcitementLevel.DRAMATIC


class TestPerspectiveSelection:
    """Test perspective selection with context preferences."""
    
    def test_technical_perspective_with_purple_sector(
        self, style_manager, base_event, base_context, base_race_state
    ):
        """Test technical perspective preferred when purple sector available."""
        base_context.sector_1_status = "purple"
        significance = SignificanceScore(base_score=60, context_bonus=0, total_score=60)
        
        # Run multiple times to check preference (not guaranteed due to randomness)
        technical_count = 0
        for _ in range(20):
            # Reset manager state for each iteration
            manager = CommentaryStyleManager(style_manager.config)
            perspective = manager._select_perspective(base_event, base_context, significance)
            if perspective == CommentaryPerspective.TECHNICAL:
                technical_count += 1
        
        # Technical should be selected more often (at least 20% of the time with 2x weight)
        assert technical_count >= 4, f"Technical selected {technical_count}/20 times"
    
    def test_technical_perspective_with_speed_trap(
        self, style_manager, base_event, base_context, base_race_state
    ):
        """Test technical perspective preferred when speed trap data available."""
        base_context.speed_trap = 320.5
        significance = SignificanceScore(base_score=60, context_bonus=0, total_score=60)
        
        technical_count = 0
        for _ in range(20):
            manager = CommentaryStyleManager(style_manager.config)
            perspective = manager._select_perspective(base_event, base_context, significance)
            if perspective == CommentaryPerspective.TECHNICAL:
                technical_count += 1
        
        assert technical_count >= 6
    
    def test_strategic_perspective_for_pit_stop(
        self, style_manager, base_race_state
    ):
        """Test strategic perspective preferred for pit stops."""
        from datetime import datetime
        from src.models import EventType
        
        # Create pit stop event
        pit_event = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.fromisoformat("2024-01-01T12:00:00"),
            data={"driver": "Hamilton", "position": 3, "lap_number": 10}
        )
        
        # Create context for pit stop
        pit_context = ContextData(
            event=pit_event,
            race_state=base_race_state,
        )
        
        significance = SignificanceScore(base_score=60, context_bonus=0, total_score=60)
        
        strategic_count = 0
        for _ in range(20):
            manager = CommentaryStyleManager(style_manager.config)
            perspective = manager._select_perspective(pit_event, pit_context, significance)
            if perspective == CommentaryPerspective.STRATEGIC:
                strategic_count += 1
        
        assert strategic_count >= 6
    
    def test_strategic_perspective_for_tire_differential(
        self, style_manager, base_event, base_context, base_race_state
    ):
        """Test strategic perspective preferred for significant tire age differential."""
        base_context.tire_age_differential = 8  # > 5 laps
        significance = SignificanceScore(base_score=60, context_bonus=0, total_score=60)
        
        strategic_count = 0
        for _ in range(20):
            manager = CommentaryStyleManager(style_manager.config)
            perspective = manager._select_perspective(base_event, base_context, significance)
            if perspective == CommentaryPerspective.STRATEGIC:
                strategic_count += 1
        
        assert strategic_count >= 6
    
    def test_dramatic_perspective_for_high_significance(
        self, style_manager, base_event, base_context, base_race_state
    ):
        """Test dramatic perspective preferred for high significance events (>80)."""
        significance = SignificanceScore(base_score=85, context_bonus=0, total_score=85)
        
        dramatic_count = 0
        for _ in range(20):
            manager = CommentaryStyleManager(style_manager.config)
            perspective = manager._select_perspective(base_event, base_context, significance)
            if perspective == CommentaryPerspective.DRAMATIC:
                dramatic_count += 1
        
        assert dramatic_count >= 6
    
    def test_dramatic_perspective_boost_in_final_laps(
        self, style_manager, base_event, base_context, base_race_state
    ):
        """Test dramatic perspective gets additional boost in final laps."""
        base_context.race_state.race_phase = RacePhase.FINISH
        significance = SignificanceScore(base_score=60, context_bonus=0, total_score=60)
        
        dramatic_count = 0
        for _ in range(20):
            manager = CommentaryStyleManager(style_manager.config)
            perspective = manager._select_perspective(base_event, base_context, significance)
            if perspective == CommentaryPerspective.DRAMATIC:
                dramatic_count += 1
        
        # Should be selected more often in final laps (at least 20% of the time)
        assert dramatic_count >= 4
    
    def test_positional_perspective_for_championship_contender(
        self, style_manager, base_event, base_context, base_race_state
    ):
        """Test positional perspective preferred for championship contenders."""
        base_context.is_championship_contender = True
        significance = SignificanceScore(base_score=60, context_bonus=0, total_score=60)
        
        positional_count = 0
        for _ in range(20):
            manager = CommentaryStyleManager(style_manager.config)
            perspective = manager._select_perspective(base_event, base_context, significance)
            if perspective == CommentaryPerspective.POSITIONAL:
                positional_count += 1
        
        # Lower threshold due to lower base weight (15% vs 25% for others)
        assert positional_count >= 3


class TestVarietyEnforcement:
    """Test perspective variety enforcement rules."""
    
    def test_avoid_consecutive_repetition(
        self, style_manager, base_event, base_context, base_race_state
    ):
        """Test that same perspective is strongly discouraged consecutively."""
        significance = SignificanceScore(base_score=60, context_bonus=0, total_score=60)
        
        # Generate 20 perspectives
        perspectives = []
        for _ in range(20):
            style = style_manager.select_style(base_event, base_context, significance)
            perspectives.append(style.perspective)
        
        # Count consecutive repetitions
        consecutive_count = 0
        for i in range(len(perspectives) - 1):
            if perspectives[i] == perspectives[i + 1]:
                consecutive_count += 1
        
        # With 10% weight for last perspective, consecutive repetitions should be rare
        # Allow up to 2 consecutive repetitions in 20 selections (10%)
        assert consecutive_count <= 2, \
            f"Too many consecutive repetitions: {consecutive_count}/19 (expected ≤2)"
    
    def test_perspective_usage_limit_in_window(
        self, style_manager, base_event, base_context, base_race_state
    ):
        """Test that no perspective exceeds 40% usage in 10-event window."""
        significance = SignificanceScore(base_score=60, context_bonus=0, total_score=60)
        
        # Generate 30 perspectives to test sliding window
        perspectives = []
        for _ in range(30):
            style = style_manager.select_style(base_event, base_context, significance)
            perspectives.append(style.perspective)
        
        # Check each 10-event window
        for i in range(len(perspectives) - 9):
            window = perspectives[i:i+10]
            perspective_counts = {}
            for p in window:
                perspective_counts[p] = perspective_counts.get(p, 0) + 1
            
            for perspective, count in perspective_counts.items():
                usage_percent = (count / 10) * 100
                assert usage_percent <= 40, \
                    f"Perspective {perspective.value} used {usage_percent}% in window {i}-{i+9}"
    
    def test_variety_enforcement_with_zero_weights(self, style_manager):
        """Test that variety enforcement handles zero weights gracefully."""
        # Manually set all weights to zero except one
        scores = {
            CommentaryPerspective.TECHNICAL: 0.0,
            CommentaryPerspective.STRATEGIC: 0.0,
            CommentaryPerspective.DRAMATIC: 0.0,
            CommentaryPerspective.POSITIONAL: 0.0,
            CommentaryPerspective.HISTORICAL: 1.0,
        }
        
        # Fill recent perspectives with historical to trigger blocking
        style_manager.perspective_window = deque(
            [CommentaryPerspective.HISTORICAL] * 10,
            maxlen=10
        )
        
        # Apply variety enforcement
        adjusted = style_manager._apply_variety_enforcement(scores)
        
        # Historical should be blocked (40% usage)
        assert adjusted[CommentaryPerspective.HISTORICAL] == 0.0


class TestStyleOrchestration:
    """Test complete style selection orchestration."""
    
    def test_select_style_returns_complete_style(
        self, style_manager, base_event, base_context, base_race_state
    ):
        """Test that select_style returns a complete CommentaryStyle."""
        significance = SignificanceScore(base_score=60, context_bonus=0, total_score=60)
        style = style_manager.select_style(base_event, base_context, significance)
        
        assert isinstance(style, CommentaryStyle)
        assert isinstance(style.excitement_level, ExcitementLevel)
        assert isinstance(style.perspective, CommentaryPerspective)
        assert isinstance(style.include_technical_detail, bool)
        assert isinstance(style.include_narrative_reference, bool)
        assert isinstance(style.include_championship_context, bool)
    
    def test_include_technical_flag_with_technical_data(
        self, style_manager, base_event, base_context, base_race_state
    ):
        """Test include_technical_detail flag set when technical data available."""
        base_context.sector_1_status = "purple"
        significance = SignificanceScore(base_score=60, context_bonus=0, total_score=60)
        style = style_manager.select_style(base_event, base_context, significance)
        
        assert style.include_technical_detail is True
    
    def test_include_technical_flag_without_technical_data(
        self, style_manager, base_event, base_context, base_race_state
    ):
        """Test include_technical_detail flag not set without technical data."""
        significance = SignificanceScore(base_score=60, context_bonus=0, total_score=60)
        style = style_manager.select_style(base_event, base_context, significance)
        
        assert style.include_technical_detail is False
    
    def test_include_narrative_flag_with_active_narratives(
        self, style_manager, base_event, base_context, base_race_state
    ):
        """Test include_narrative_reference flag set when narratives active."""
        base_context.active_narratives = ["battle_with_verstappen"]
        significance = SignificanceScore(base_score=60, context_bonus=0, total_score=60)
        style = style_manager.select_style(base_event, base_context, significance)
        
        assert style.include_narrative_reference is True
    
    def test_include_narrative_flag_without_narratives(
        self, style_manager, base_event, base_context, base_race_state
    ):
        """Test include_narrative_reference flag not set without narratives."""
        significance = SignificanceScore(base_score=60, context_bonus=0, total_score=60)
        style = style_manager.select_style(base_event, base_context, significance)
        
        assert style.include_narrative_reference is False
    
    def test_include_championship_flag_for_contender(
        self, style_manager, base_event, base_context, base_race_state
    ):
        """Test include_championship_context flag set for championship contenders."""
        base_context.is_championship_contender = True
        significance = SignificanceScore(base_score=60, context_bonus=0, total_score=60)
        style = style_manager.select_style(base_event, base_context, significance)
        
        assert style.include_championship_context is True
    
    def test_include_championship_flag_for_non_contender(
        self, style_manager, base_event, base_context, base_race_state
    ):
        """Test include_championship_context flag not set for non-contenders."""
        base_context.is_championship_contender = False
        significance = SignificanceScore(base_score=60, context_bonus=0, total_score=60)
        style = style_manager.select_style(base_event, base_context, significance)
        
        assert style.include_championship_context is False
    
    def test_perspective_tracking(
        self, style_manager, base_event, base_context, base_race_state
    ):
        """Test that perspectives are tracked in recent_perspectives deque."""
        significance = SignificanceScore(base_score=60, context_bonus=0, total_score=60)
        
        # Generate 3 styles
        styles = []
        for _ in range(3):
            style = style_manager.select_style(base_event, base_context, significance)
            styles.append(style)
        
        # Check that perspectives are tracked
        assert len(style_manager.recent_perspectives) == 3
        assert len(style_manager.perspective_window) == 3
        
        # Check that tracked perspectives match generated styles
        for i, style in enumerate(styles):
            assert style_manager.recent_perspectives[i] == style.perspective
            assert style_manager.perspective_window[i] == style.perspective


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_excitement_at_exact_thresholds(self, style_manager, base_context):
        """Test excitement level at exact threshold boundaries."""
        # Test each threshold boundary
        test_cases = [
            (30, ExcitementLevel.CALM),
            (31, ExcitementLevel.MODERATE),
            (50, ExcitementLevel.MODERATE),
            (51, ExcitementLevel.ENGAGED),
            (70, ExcitementLevel.ENGAGED),
            (71, ExcitementLevel.EXCITED),
            (85, ExcitementLevel.EXCITED),
            (86, ExcitementLevel.DRAMATIC),
        ]
        
        for score, expected_level in test_cases:
            significance = SignificanceScore(
                base_score=score, context_bonus=0, total_score=score
            )
            excitement = style_manager._determine_excitement(significance, base_context)
            assert excitement == expected_level, \
                f"Score {score} should map to {expected_level.name}, got {excitement.name}"
    
    def test_perspective_selection_with_empty_window(
        self, style_manager, base_event, base_context, base_race_state
    ):
        """Test perspective selection works with empty tracking window."""
        significance = SignificanceScore(base_score=60, context_bonus=0, total_score=60)
        
        # Should not raise error with empty window
        perspective = style_manager._select_perspective(
            base_event, base_context, significance
        )
        assert isinstance(perspective, CommentaryPerspective)
    
    def test_multiple_context_preferences(
        self, style_manager, base_event, base_context, base_race_state
    ):
        """Test perspective selection with multiple competing preferences."""
        from src.models import EventType
        # Set up context with multiple preferences
        base_context.sector_1_status = "purple"  # Technical preference
        base_event.event_type = EventType.PIT_STOP  # Strategic preference
        base_context.is_championship_contender = True  # Positional preference
        significance = SignificanceScore(base_score=85, context_bonus=0, total_score=85)  # Dramatic preference
        
        # Should still select a valid perspective
        perspective = style_manager._select_perspective(
            base_event, base_context, significance
        )
        assert isinstance(perspective, CommentaryPerspective)


class TestConfigurationIntegration:
    """Test integration with configuration parameters."""
    
    def test_custom_excitement_thresholds(self, base_context):
        """Test that custom excitement thresholds are respected."""
        custom_config = Config(
            excitement_threshold_calm=20,
            excitement_threshold_moderate=40,
            excitement_threshold_engaged=60,
            excitement_threshold_excited=80,
        )
        manager = CommentaryStyleManager(custom_config)
        
        # Test with score that would be MODERATE with default config
        significance = SignificanceScore(base_score=35, context_bonus=0, total_score=35)
        excitement = manager._determine_excitement(significance, base_context)
        
        # With custom thresholds, 35 should be MODERATE (20 < 35 <= 40)
        assert excitement == ExcitementLevel.MODERATE
    
    def test_custom_perspective_weights(self, base_event, base_context, base_race_state):
        """Test that custom perspective weights affect selection."""
        # Create config with heavy technical weight
        custom_config = Config(
            perspective_weight_technical=0.70,
            perspective_weight_strategic=0.10,
            perspective_weight_dramatic=0.10,
            perspective_weight_positional=0.05,
            perspective_weight_historical=0.05,
        )
        manager = CommentaryStyleManager(custom_config)
        
        significance = SignificanceScore(base_score=60, context_bonus=0, total_score=60)
        
        # Generate multiple perspectives
        technical_count = 0
        for _ in range(20):
            # Create new manager for each iteration to reset state
            fresh_manager = CommentaryStyleManager(custom_config)
            perspective = fresh_manager._select_perspective(
                base_event, base_context, significance
            )
            if perspective == CommentaryPerspective.TECHNICAL:
                technical_count += 1
        
        # Technical should be selected more often with higher weight
        assert technical_count >= 10, f"Technical selected {technical_count}/20 times"
