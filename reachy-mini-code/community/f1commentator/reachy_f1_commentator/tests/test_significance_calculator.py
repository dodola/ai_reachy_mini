"""
Unit tests for the SignificanceCalculator class.

Tests the base scoring rules and context bonus application for event prioritization.
"""

import pytest
from datetime import datetime

from reachy_f1_commentator.src.event_prioritizer import SignificanceCalculator
from reachy_f1_commentator.src.enhanced_models import ContextData
from reachy_f1_commentator.src.models import EventType, RaceEvent, RaceState


@pytest.fixture
def calculator():
    """Create a SignificanceCalculator instance."""
    return SignificanceCalculator()


@pytest.fixture
def base_context():
    """Create a base ContextData with minimal information."""
    return ContextData(
        event=RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        ),
        race_state=RaceState()
    )


class TestBaseScoring:
    """Test base score calculation for different event types."""
    
    def test_lead_change_score(self, calculator, base_context):
        """Lead change should score 100."""
        event = RaceEvent(
            event_type=EventType.LEAD_CHANGE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        
        score = calculator.calculate_significance(event, base_context)
        assert score.base_score == 100
    
    def test_safety_car_score(self, calculator, base_context):
        """Safety car should score 100."""
        event = RaceEvent(
            event_type=EventType.SAFETY_CAR,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        
        score = calculator.calculate_significance(event, base_context)
        assert score.base_score == 100
    
    def test_incident_score(self, calculator, base_context):
        """Incident should score 95."""
        event = RaceEvent(
            event_type=EventType.INCIDENT,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        
        score = calculator.calculate_significance(event, base_context)
        assert score.base_score == 95
    
    def test_overtake_p1_p3_score(self, calculator, base_context):
        """Overtake in P1-P3 should score 90."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 2
        
        score = calculator.calculate_significance(event, base_context)
        assert score.base_score == 90
    
    def test_overtake_p4_p6_score(self, calculator, base_context):
        """Overtake in P4-P6 should score 70."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 5
        
        score = calculator.calculate_significance(event, base_context)
        assert score.base_score == 70
    
    def test_overtake_p7_p10_score(self, calculator, base_context):
        """Overtake in P7-P10 should score 50."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 8
        
        score = calculator.calculate_significance(event, base_context)
        assert score.base_score == 50
    
    def test_overtake_p11_plus_score(self, calculator, base_context):
        """Overtake in P11+ should score 30."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 15
        
        score = calculator.calculate_significance(event, base_context)
        assert score.base_score == 30
    
    def test_pit_stop_leader_score(self, calculator, base_context):
        """Pit stop by leader should score 80."""
        event = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_before = 1
        
        score = calculator.calculate_significance(event, base_context)
        assert score.base_score == 80
    
    def test_pit_stop_p2_p5_score(self, calculator, base_context):
        """Pit stop by P2-P5 should score 60."""
        event = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_before = 3
        
        score = calculator.calculate_significance(event, base_context)
        assert score.base_score == 60
    
    def test_pit_stop_p6_p10_score(self, calculator, base_context):
        """Pit stop by P6-P10 should score 40."""
        event = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_before = 7
        
        score = calculator.calculate_significance(event, base_context)
        assert score.base_score == 40
    
    def test_pit_stop_p11_plus_score(self, calculator, base_context):
        """Pit stop by P11+ should score 20."""
        event = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_before = 12
        
        score = calculator.calculate_significance(event, base_context)
        assert score.base_score == 20
    
    def test_fastest_lap_leader_score(self, calculator, base_context):
        """Fastest lap by leader should score 70."""
        event = RaceEvent(
            event_type=EventType.FASTEST_LAP,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 1
        
        score = calculator.calculate_significance(event, base_context)
        assert score.base_score == 70
    
    def test_fastest_lap_other_score(self, calculator, base_context):
        """Fastest lap by non-leader should score 50."""
        event = RaceEvent(
            event_type=EventType.FASTEST_LAP,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 5
        
        score = calculator.calculate_significance(event, base_context)
        assert score.base_score == 50


class TestContextBonuses:
    """Test context bonus application."""
    
    def test_championship_contender_bonus(self, calculator, base_context):
        """Championship contender should add +20 bonus."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 5
        base_context.is_championship_contender = True
        
        score = calculator.calculate_significance(event, base_context)
        assert score.context_bonus >= 20
        assert any("Championship contender" in reason for reason in score.reasons)
    
    def test_battle_narrative_bonus(self, calculator, base_context):
        """Battle narrative should add +15 bonus."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 5
        base_context.active_narratives = ["battle_with_hamilton"]
        
        score = calculator.calculate_significance(event, base_context)
        assert score.context_bonus >= 15
        assert any("Battle narrative" in reason for reason in score.reasons)
    
    def test_comeback_narrative_bonus(self, calculator, base_context):
        """Comeback narrative should add +15 bonus."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 5
        base_context.active_narratives = ["comeback_drive"]
        
        score = calculator.calculate_significance(event, base_context)
        assert score.context_bonus >= 15
        assert any("Comeback narrative" in reason for reason in score.reasons)
    
    def test_close_gap_bonus(self, calculator, base_context):
        """Gap < 1s should add +10 bonus."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 5
        base_context.gap_to_ahead = 0.8
        
        score = calculator.calculate_significance(event, base_context)
        assert score.context_bonus >= 10
        assert any("Gap < 1s" in reason for reason in score.reasons)
    
    def test_tire_age_differential_bonus(self, calculator, base_context):
        """Tire age diff > 5 laps should add +10 bonus."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 5
        base_context.tire_age_differential = 8
        
        score = calculator.calculate_significance(event, base_context)
        assert score.context_bonus >= 10
        assert any("Tire age diff" in reason for reason in score.reasons)
    
    def test_drs_bonus(self, calculator, base_context):
        """DRS active should add +5 bonus."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 5
        base_context.drs_active = True
        
        score = calculator.calculate_significance(event, base_context)
        assert score.context_bonus >= 5
        assert any("DRS active" in reason for reason in score.reasons)
    
    def test_purple_sector_bonus(self, calculator, base_context):
        """Purple sector should add +10 bonus."""
        event = RaceEvent(
            event_type=EventType.FASTEST_LAP,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 5
        base_context.sector_1_status = "purple"
        
        score = calculator.calculate_significance(event, base_context)
        assert score.context_bonus >= 10
        assert any("Purple sector" in reason for reason in score.reasons)
    
    def test_weather_impact_bonus_rainfall(self, calculator, base_context):
        """Rainfall should add +5 weather bonus."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 5
        base_context.rainfall = 1.5
        
        score = calculator.calculate_significance(event, base_context)
        assert score.context_bonus >= 5
        assert any("Weather impact" in reason for reason in score.reasons)
    
    def test_weather_impact_bonus_wind(self, calculator, base_context):
        """High wind should add +5 weather bonus."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 5
        base_context.wind_speed = 25
        
        score = calculator.calculate_significance(event, base_context)
        assert score.context_bonus >= 5
        assert any("Weather impact" in reason for reason in score.reasons)
    
    def test_first_pit_stop_bonus(self, calculator, base_context):
        """First pit stop should add +10 bonus."""
        event = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_before = 3
        base_context.pit_count = 1
        
        score = calculator.calculate_significance(event, base_context)
        assert score.context_bonus >= 10
        assert any("First pit stop" in reason for reason in score.reasons)
    
    def test_multiple_bonuses_cumulative(self, calculator, base_context):
        """Multiple bonuses should be cumulative."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 2
        base_context.is_championship_contender = True  # +20
        base_context.active_narratives = ["battle_with_Hamilton"]  # +15
        base_context.gap_to_ahead = 0.5  # +10
        base_context.drs_active = True  # +5
        
        score = calculator.calculate_significance(event, base_context)
        # Should have at least 50 bonus (20+15+10+5)
        assert score.context_bonus >= 50
        assert len([r for r in score.reasons if "+" in r]) >= 4


class TestTotalScore:
    """Test total score calculation and capping."""
    
    def test_total_score_calculation(self, calculator, base_context):
        """Total score should be base + bonus."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 5  # Base 70
        base_context.is_championship_contender = True  # +20
        
        score = calculator.calculate_significance(event, base_context)
        assert score.total_score == score.base_score + score.context_bonus
    
    def test_total_score_capped_at_100(self, calculator, base_context):
        """Total score should be capped at 100."""
        event = RaceEvent(
            event_type=EventType.LEAD_CHANGE,  # Base 100
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.is_championship_contender = True  # +20
        base_context.active_narratives = ["battle_with_Hamilton"]  # +15
        
        score = calculator.calculate_significance(event, base_context)
        assert score.total_score == 100
        assert score.base_score + score.context_bonus > 100
    
    def test_reasons_include_base_score(self, calculator, base_context):
        """Reasons should include base score explanation."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 5
        
        score = calculator.calculate_significance(event, base_context)
        assert any("Base score" in reason for reason in score.reasons)


class TestEdgeCases:
    """Test edge cases and missing data handling."""
    
    def test_overtake_without_position(self, calculator, base_context):
        """Overtake without position should use fallback score."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = None
        
        score = calculator.calculate_significance(event, base_context)
        assert score.base_score == 50  # Fallback score
    
    def test_pit_stop_without_position(self, calculator, base_context):
        """Pit stop without position should use fallback score."""
        event = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_before = None
        
        score = calculator.calculate_significance(event, base_context)
        assert score.base_score == 40  # Fallback score
    
    def test_no_context_bonuses(self, calculator, base_context):
        """Event with no context bonuses should have zero bonus."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 5
        
        score = calculator.calculate_significance(event, base_context)
        assert score.context_bonus == 0
        assert len(score.reasons) == 1  # Only base score reason
    
    def test_gap_exactly_1_second(self, calculator, base_context):
        """Gap of exactly 1.0s should not trigger bonus."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 5
        base_context.gap_to_ahead = 1.0
        
        score = calculator.calculate_significance(event, base_context)
        assert not any("Gap < 1s" in reason for reason in score.reasons)
    
    def test_tire_age_diff_exactly_5_laps(self, calculator, base_context):
        """Tire age diff of exactly 5 laps should not trigger bonus."""
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={}
        )
        base_context.event = event
        base_context.position_after = 5
        base_context.tire_age_differential = 5
        
        score = calculator.calculate_significance(event, base_context)
        assert not any("Tire age diff" in reason for reason in score.reasons)
