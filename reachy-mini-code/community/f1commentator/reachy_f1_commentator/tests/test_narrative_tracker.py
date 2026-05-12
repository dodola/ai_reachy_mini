"""
Unit tests for Narrative Tracker.

Tests narrative detection logic for battles, comebacks, strategy divergence,
championship fights, and undercut/overcut attempts.

Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.6, 6.7
"""

import pytest
from datetime import datetime
from collections import deque

from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.narrative_tracker import NarrativeTracker
from reachy_f1_commentator.src.enhanced_models import ContextData, NarrativeType
from reachy_f1_commentator.src.models import RaceEvent, RaceState, DriverState, EventType


@pytest.fixture
def config():
    """Create test configuration."""
    return Config(
        max_narrative_threads=5,
        battle_gap_threshold=2.0,
        battle_lap_threshold=3,
        comeback_position_threshold=3,
        comeback_lap_window=10,
    )


@pytest.fixture
def tracker(config):
    """Create narrative tracker instance."""
    return NarrativeTracker(config)


@pytest.fixture
def race_state():
    """Create basic race state."""
    return RaceState(
        drivers=[
            DriverState(name="Hamilton", position=1, gap_to_leader=0.0, gap_to_ahead=0.0),
            DriverState(name="Verstappen", position=2, gap_to_leader=1.5, gap_to_ahead=1.5),
            DriverState(name="Leclerc", position=3, gap_to_leader=3.0, gap_to_ahead=1.5),
            DriverState(name="Sainz", position=4, gap_to_leader=5.0, gap_to_ahead=2.0),
            DriverState(name="Norris", position=5, gap_to_leader=8.0, gap_to_ahead=3.0),
        ],
        current_lap=10,
        total_laps=50,
    )


@pytest.fixture
def context_data(race_state):
    """Create basic context data."""
    return ContextData(
        event=RaceEvent(
            event_type=EventType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data={}
        ),
        race_state=race_state,
    )


class TestBattleDetection:
    """Test battle narrative detection."""
    
    def test_detect_battle_within_threshold(self, tracker, race_state, context_data):
        """Test battle detection when drivers are within gap threshold for required laps."""
        # Simulate 3 laps of close racing between Hamilton and Verstappen
        # Manually add gap history without calling update() to avoid interference
        pair = ("Hamilton", "Verstappen")
        for lap in range(8, 11):
            tracker.gap_history[pair].append({
                'lap': lap,
                'gap': 1.5  # Within 2.0s threshold
            })
        
        race_state.current_lap = 10
        
        # Should detect battle after 3 consecutive laps
        battle = tracker._detect_battle(race_state, 10)
        assert battle is not None
        assert battle.narrative_type == NarrativeType.BATTLE
        assert "Hamilton" in battle.drivers_involved
        assert "Verstappen" in battle.drivers_involved
    
    def test_no_battle_when_gap_too_large(self, tracker, race_state, context_data):
        """Test that battle is not detected when gap exceeds threshold."""
        # Simulate 3 laps with gap > 2.0s
        # Manually add gap history without calling update() to avoid interference
        pair = ("Hamilton", "Verstappen")
        for lap in range(8, 11):
            tracker.gap_history[pair].append({
                'lap': lap,
                'gap': 3.0  # Above 2.0s threshold
            })
        
        race_state.current_lap = 10
        
        # Should not detect battle
        battle = tracker._detect_battle(race_state, 10)
        assert battle is None
    
    def test_no_battle_when_insufficient_laps(self, tracker, race_state, context_data):
        """Test that battle is not detected with insufficient consecutive laps."""
        # Simulate only 2 laps of close racing
        for lap in range(9, 11):
            race_state.current_lap = lap
            
            pair = ("Hamilton", "Verstappen")
            tracker.gap_history[pair].append({
                'lap': lap,
                'gap': 1.5
            })
            
            tracker.update(race_state, context_data)
        
        # Should not detect battle (need 3 laps)
        battle = tracker._detect_battle(race_state, 10)
        assert battle is None
    
    def test_battle_closure_when_gap_increases(self, tracker, race_state, context_data):
        """Test that battle narrative closes when gap exceeds 5s."""
        # Create an active battle
        pair = ("Hamilton", "Verstappen")
        for lap in range(8, 11):
            tracker.gap_history[pair].append({'lap': lap, 'gap': 1.5})
        
        battle = tracker._detect_battle(race_state, 10)
        tracker._add_narrative(battle)
        
        # Simulate gap increasing to > 5s
        tracker.gap_history[pair].append({'lap': 11, 'gap': 6.0})
        tracker.gap_history[pair].append({'lap': 12, 'gap': 6.5})
        
        race_state.current_lap = 12
        tracker.close_stale_narratives(race_state, 12)
        
        # Battle should be closed
        assert not battle.is_active


class TestComebackDetection:
    """Test comeback narrative detection."""
    
    def test_detect_comeback_with_position_gain(self, tracker, race_state, context_data):
        """Test comeback detection when driver gains required positions."""
        # Simulate Norris gaining positions from P8 to P5
        positions = [
            {'lap': 1, 'position': 8},
            {'lap': 3, 'position': 7},
            {'lap': 5, 'position': 6},
            {'lap': 7, 'position': 5},
        ]
        
        tracker.position_history["Norris"] = deque(positions, maxlen=20)
        race_state.current_lap = 7
        
        comeback = tracker._detect_comeback(race_state, 7)
        assert comeback is not None
        assert comeback.narrative_type == NarrativeType.COMEBACK
        assert "Norris" in comeback.drivers_involved
        assert comeback.context_data['positions_gained'] == 3
    
    def test_no_comeback_when_insufficient_gain(self, tracker, race_state, context_data):
        """Test that comeback is not detected with insufficient position gain."""
        # Simulate only 2 positions gained
        positions = [
            {'lap': 1, 'position': 7},
            {'lap': 5, 'position': 5},
        ]
        
        tracker.position_history["Norris"] = deque(positions, maxlen=20)
        race_state.current_lap = 5
        
        comeback = tracker._detect_comeback(race_state, 5)
        assert comeback is None
    
    def test_comeback_closure_when_stalled(self, tracker, race_state, context_data):
        """Test that comeback narrative closes when no position gain for 10 laps."""
        # Create an active comeback
        positions = [
            {'lap': 1, 'position': 8},
            {'lap': 5, 'position': 5},
        ]
        tracker.position_history["Norris"] = deque(positions, maxlen=20)
        
        comeback = tracker._detect_comeback(race_state, 5)
        tracker._add_narrative(comeback)
        
        # Simulate 10 laps with no position gain
        for lap in range(6, 16):
            tracker.position_history["Norris"].append({'lap': lap, 'position': 5})
        
        race_state.current_lap = 15
        tracker.close_stale_narratives(race_state, 15)
        
        # Comeback should be closed
        assert not comeback.is_active


class TestStrategyDivergence:
    """Test strategy divergence detection."""
    
    def test_detect_strategy_different_compounds(self, tracker, race_state, context_data):
        """Test strategy divergence detection with different tire compounds."""
        # Set different tire compounds for nearby drivers
        race_state.drivers[0].current_tire = "soft"
        race_state.drivers[1].current_tire = "medium"
        
        context_data.current_tire_compound = "soft"
        
        strategy = tracker._detect_strategy_divergence(race_state, context_data)
        assert strategy is not None
        assert strategy.narrative_type == NarrativeType.STRATEGY_DIVERGENCE
        assert len(strategy.drivers_involved) == 2
    
    def test_detect_strategy_tire_age_difference(self, tracker, race_state, context_data):
        """Test strategy divergence detection with significant tire age difference."""
        context_data.current_tire_compound = "soft"
        context_data.tire_age_differential = 8  # > 5 laps difference
        
        strategy = tracker._detect_strategy_divergence(race_state, context_data)
        assert strategy is not None
        assert strategy.narrative_type == NarrativeType.STRATEGY_DIVERGENCE
    
    def test_no_strategy_divergence_same_compound(self, tracker, race_state, context_data):
        """Test that strategy divergence is not detected with same compounds."""
        # Set same tire compound for all drivers
        for driver in race_state.drivers:
            driver.current_tire = "medium"
        
        context_data.current_tire_compound = "medium"
        context_data.tire_age_differential = 2  # Small difference
        
        strategy = tracker._detect_strategy_divergence(race_state, context_data)
        assert strategy is None


class TestChampionshipFight:
    """Test championship fight detection."""
    
    def test_detect_championship_fight_close_points(self, tracker, race_state, context_data):
        """Test championship fight detection when top 2 are within 25 points."""
        context_data.driver_championship_position = 2
        context_data.championship_gap_to_leader = 15  # Within 25 points
        
        championship = tracker._detect_championship_fight(context_data)
        assert championship is not None
        assert championship.narrative_type == NarrativeType.CHAMPIONSHIP_FIGHT
        assert championship.context_data['points_gap'] == 15
    
    def test_no_championship_fight_large_gap(self, tracker, race_state, context_data):
        """Test that championship fight is not detected with large points gap."""
        context_data.driver_championship_position = 2
        context_data.championship_gap_to_leader = 50  # > 25 points
        
        championship = tracker._detect_championship_fight(context_data)
        assert championship is None
    
    def test_no_championship_fight_outside_top_2(self, tracker, race_state, context_data):
        """Test that championship fight is not detected for drivers outside top 2."""
        context_data.driver_championship_position = 5
        context_data.championship_gap_to_leader = 10
        
        championship = tracker._detect_championship_fight(context_data)
        assert championship is None


class TestUndercutDetection:
    """Test undercut attempt detection."""
    
    def test_detect_undercut_attempt(self, tracker, race_state, context_data):
        """Test undercut detection when driver pits while rival stays out."""
        race_state.current_lap = 20
        
        # Verstappen pits on lap 20
        tracker.recent_pit_stops["Verstappen"] = 20
        
        # Hamilton ahead hasn't pitted recently
        tracker.recent_pit_stops["Hamilton"] = 10
        
        undercut = tracker._detect_undercut_attempt(race_state, 20)
        assert undercut is not None
        assert undercut.narrative_type == NarrativeType.UNDERCUT_ATTEMPT
        assert "Verstappen" in undercut.drivers_involved
        assert "Hamilton" in undercut.drivers_involved
    
    def test_no_undercut_when_rival_also_pitted(self, tracker, race_state, context_data):
        """Test that undercut is not detected when rival also pitted recently."""
        race_state.current_lap = 20
        
        # Both drivers pitted recently
        tracker.recent_pit_stops["Verstappen"] = 20
        tracker.recent_pit_stops["Hamilton"] = 19
        
        undercut = tracker._detect_undercut_attempt(race_state, 20)
        assert undercut is None


class TestOvercutDetection:
    """Test overcut attempt detection."""
    
    def test_detect_overcut_attempt(self, tracker, race_state, context_data):
        """Test overcut detection when driver stays out while rival pits."""
        race_state.current_lap = 25
        
        # Hamilton pitted on lap 22
        tracker.recent_pit_stops["Hamilton"] = 22
        
        # Verstappen behind hasn't pitted in a long time
        tracker.recent_pit_stops["Verstappen"] = 10
        
        overcut = tracker._detect_overcut_attempt(race_state, 25)
        assert overcut is not None
        assert overcut.narrative_type == NarrativeType.OVERCUT_ATTEMPT
        assert "Verstappen" in overcut.drivers_involved
        assert "Hamilton" in overcut.drivers_involved


class TestNarrativeManagement:
    """Test narrative lifecycle management."""
    
    def test_narrative_thread_limit(self, tracker, race_state, context_data):
        """Test that narrative tracker enforces max thread limit."""
        # Create 6 narratives (exceeds limit of 5)
        for i in range(6):
            narrative = tracker._detect_battle(race_state, 10 + i)
            if narrative is None:
                # Create a dummy narrative for testing
                from src.enhanced_models import NarrativeThread
                narrative = NarrativeThread(
                    narrative_id=f"test_{i}",
                    narrative_type=NarrativeType.BATTLE,
                    drivers_involved=["Driver1", "Driver2"],
                    start_lap=10 + i,
                    last_update_lap=10 + i,
                    is_active=True
                )
            tracker._add_narrative(narrative)
        
        # Should only have 5 active narratives
        assert len(tracker.active_threads) == 5
    
    def test_get_relevant_narratives(self, tracker, race_state, context_data):
        """Test getting narratives relevant to an event."""
        from src.enhanced_models import NarrativeThread
        
        # Create battle narrative involving Hamilton
        battle = NarrativeThread(
            narrative_id="battle_hamilton_verstappen",
            narrative_type=NarrativeType.BATTLE,
            drivers_involved=["Hamilton", "Verstappen"],
            start_lap=5,
            last_update_lap=10,
            is_active=True
        )
        tracker.active_threads.append(battle)
        
        # Create event involving Hamilton
        event = RaceEvent(
            event_type=EventType.OVERTAKE,
            timestamp=datetime.now(),
            data={'overtaking_driver': 'Hamilton', 'overtaken_driver': 'Leclerc'}
        )
        
        relevant = tracker.get_relevant_narratives(event)
        assert len(relevant) == 1
        assert relevant[0].narrative_id == "battle_hamilton_verstappen"
    
    def test_narrative_exists_check(self, tracker):
        """Test checking if narrative already exists."""
        from src.enhanced_models import NarrativeThread
        
        narrative = NarrativeThread(
            narrative_id="test_narrative",
            narrative_type=NarrativeType.BATTLE,
            drivers_involved=["Driver1", "Driver2"],
            start_lap=5,
            last_update_lap=10,
            is_active=True
        )
        tracker.active_threads.append(narrative)
        
        assert tracker._narrative_exists("test_narrative") is True
        assert tracker._narrative_exists("nonexistent") is False
    
    def test_get_active_narratives(self, tracker):
        """Test getting only active narratives."""
        from src.enhanced_models import NarrativeThread
        
        # Create active and inactive narratives
        active = NarrativeThread(
            narrative_id="active",
            narrative_type=NarrativeType.BATTLE,
            drivers_involved=["Driver1", "Driver2"],
            start_lap=5,
            last_update_lap=10,
            is_active=True
        )
        
        inactive = NarrativeThread(
            narrative_id="inactive",
            narrative_type=NarrativeType.COMEBACK,
            drivers_involved=["Driver3"],
            start_lap=1,
            last_update_lap=5,
            is_active=False
        )
        
        tracker.active_threads.extend([active, inactive])
        
        active_narratives = tracker.get_active_narratives()
        assert len(active_narratives) == 1
        assert active_narratives[0].narrative_id == "active"


class TestNarrativeUpdate:
    """Test narrative update functionality."""
    
    def test_update_position_history(self, tracker, race_state, context_data):
        """Test that update() correctly tracks position history."""
        race_state.current_lap = 10
        tracker.update(race_state, context_data)
        
        # Check that position history was updated for all drivers
        assert len(tracker.position_history) == 5
        assert "Hamilton" in tracker.position_history
        assert tracker.position_history["Hamilton"][-1]['lap'] == 10
        assert tracker.position_history["Hamilton"][-1]['position'] == 1
    
    def test_update_gap_history(self, tracker, race_state, context_data):
        """Test that update() correctly tracks gap history."""
        race_state.current_lap = 10
        tracker.update(race_state, context_data)
        
        # Check that gap history was updated for nearby drivers
        pair = ("Hamilton", "Verstappen")
        assert pair in tracker.gap_history
        assert tracker.gap_history[pair][-1]['lap'] == 10
        assert tracker.gap_history[pair][-1]['gap'] == 1.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
