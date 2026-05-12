"""
Unit tests for PlaceholderResolver.

Tests placeholder resolution for all placeholder types including driver names,
positions, times, gaps, tire data, weather, speeds, and narrative references.
"""

import pytest
from unittest.mock import Mock, MagicMock

from reachy_f1_commentator.src.placeholder_resolver import PlaceholderResolver
from reachy_f1_commentator.src.enhanced_models import ContextData
from reachy_f1_commentator.src.openf1_data_cache import OpenF1DataCache, DriverInfo
from reachy_f1_commentator.src.models import RaceEvent, RaceState, EventType


@pytest.fixture
def mock_data_cache():
    """Create a mock OpenF1DataCache."""
    cache = Mock(spec=OpenF1DataCache)
    
    # Mock driver info
    hamilton_info = DriverInfo(
        driver_number=44,
        broadcast_name="L HAMILTON",
        full_name="Lewis HAMILTON",
        name_acronym="HAM",
        team_name="Mercedes",
        team_colour="00D2BE",
        first_name="Lewis",
        last_name="Hamilton"
    )
    
    verstappen_info = DriverInfo(
        driver_number=1,
        broadcast_name="M VERSTAPPEN",
        full_name="Max VERSTAPPEN",
        name_acronym="VER",
        team_name="Red Bull Racing",
        team_colour="0600EF",
        first_name="Max",
        last_name="Verstappen"
    )
    
    def get_driver_info(identifier):
        if identifier in [44, "Hamilton", "HAMILTON", "HAM"]:
            return hamilton_info
        elif identifier in [1, "Verstappen", "VERSTAPPEN", "VER"]:
            return verstappen_info
        return None
    
    cache.get_driver_info = Mock(side_effect=get_driver_info)
    
    return cache


@pytest.fixture
def resolver(mock_data_cache):
    """Create a PlaceholderResolver instance."""
    return PlaceholderResolver(mock_data_cache)


@pytest.fixture
def basic_context():
    """Create a basic ContextData for testing."""
    # Create a mock event with necessary attributes
    event = Mock(spec=['event_type', 'timestamp', 'driver', 'lap_number'])
    event.event_type = EventType.OVERTAKE
    event.timestamp = 0.0
    event.driver = "Hamilton"
    event.lap_number = 10
    
    # Create a mock race state
    race_state = Mock(spec=['current_lap', 'total_laps', 'session_status'])
    race_state.current_lap = 10
    race_state.total_laps = 50
    race_state.session_status = "Started"
    
    return ContextData(
        event=event,
        race_state=race_state
    )


class TestDriverPlaceholders:
    """Test driver-related placeholder resolution."""
    
    def test_resolve_driver1(self, resolver, basic_context):
        """Test resolving driver1 placeholder."""
        result = resolver.resolve("driver1", basic_context)
        assert result == "Hamilton"
    
    def test_resolve_driver_without_number(self, resolver, basic_context):
        """Test resolving driver placeholder."""
        result = resolver.resolve("driver", basic_context)
        assert result == "Hamilton"
    
    def test_resolve_driver2_overtake(self, resolver, basic_context):
        """Test resolving driver2 placeholder for overtake event."""
        basic_context.event.overtaken_driver = "Verstappen"
        result = resolver.resolve("driver2", basic_context)
        assert result == "Verstappen"
    
    def test_resolve_driver2_no_overtaken(self, resolver, basic_context):
        """Test resolving driver2 when no overtaken driver exists."""
        result = resolver.resolve("driver2", basic_context)
        assert result is None
    
    def test_resolve_unknown_driver(self, resolver, basic_context):
        """Test resolving unknown driver returns identifier."""
        basic_context.event.driver = "UnknownDriver"
        result = resolver.resolve("driver", basic_context)
        assert result == "UnknownDriver"


class TestPronounPlaceholders:
    """Test pronoun placeholder resolution."""
    
    def test_resolve_pronoun(self, resolver, basic_context):
        """Test resolving pronoun placeholder."""
        result = resolver.resolve("pronoun", basic_context)
        assert result == "he"
    
    def test_resolve_pronoun1(self, resolver, basic_context):
        """Test resolving pronoun1 placeholder."""
        result = resolver.resolve("pronoun1", basic_context)
        assert result == "he"
    
    def test_resolve_pronoun2(self, resolver, basic_context):
        """Test resolving pronoun2 placeholder."""
        basic_context.event.overtaken_driver = "Verstappen"
        result = resolver.resolve("pronoun2", basic_context)
        assert result == "he"


class TestTeamPlaceholders:
    """Test team-related placeholder resolution."""
    
    def test_resolve_team1(self, resolver, basic_context):
        """Test resolving team1 placeholder."""
        result = resolver.resolve("team1", basic_context)
        assert result == "Mercedes"
    
    def test_resolve_team(self, resolver, basic_context):
        """Test resolving team placeholder."""
        result = resolver.resolve("team", basic_context)
        assert result == "Mercedes"
    
    def test_resolve_team2(self, resolver, basic_context):
        """Test resolving team2 placeholder."""
        basic_context.event.overtaken_driver = "Verstappen"
        result = resolver.resolve("team2", basic_context)
        assert result == "Red Bull Racing"


class TestPositionPlaceholders:
    """Test position-related placeholder resolution."""
    
    def test_resolve_position(self, resolver, basic_context):
        """Test resolving position placeholder."""
        basic_context.position_after = 1
        result = resolver.resolve("position", basic_context)
        assert result == "P1"
    
    def test_resolve_position_before(self, resolver, basic_context):
        """Test resolving position_before placeholder."""
        basic_context.position_before = 3
        result = resolver.resolve("position_before", basic_context)
        assert result == "P3"
    
    def test_resolve_positions_gained(self, resolver, basic_context):
        """Test resolving positions_gained placeholder."""
        basic_context.positions_gained = 2
        result = resolver.resolve("positions_gained", basic_context)
        assert result == "2"
    
    def test_resolve_position_none(self, resolver, basic_context):
        """Test resolving position when not available."""
        result = resolver.resolve("position", basic_context)
        assert result is None


class TestGapPlaceholders:
    """Test gap-related placeholder resolution."""
    
    def test_resolve_gap_under_1s(self, resolver, basic_context):
        """Test resolving gap under 1 second."""
        basic_context.gap_to_leader = 0.8
        result = resolver.resolve("gap", basic_context)
        assert result == "0.8 seconds"
    
    def test_resolve_gap_1_to_10s(self, resolver, basic_context):
        """Test resolving gap between 1 and 10 seconds."""
        basic_context.gap_to_leader = 2.3
        result = resolver.resolve("gap", basic_context)
        assert result == "2.3 seconds"
    
    def test_resolve_gap_over_10s(self, resolver, basic_context):
        """Test resolving gap over 10 seconds."""
        basic_context.gap_to_leader = 15.7
        result = resolver.resolve("gap", basic_context)
        assert result == "16 seconds"
    
    def test_resolve_gap_to_leader(self, resolver, basic_context):
        """Test resolving gap_to_leader placeholder."""
        basic_context.gap_to_leader = 3.5
        result = resolver.resolve("gap_to_leader", basic_context)
        assert result == "3.5 seconds"
    
    def test_resolve_gap_to_ahead(self, resolver, basic_context):
        """Test resolving gap_to_ahead placeholder."""
        basic_context.gap_to_ahead = 1.2
        result = resolver.resolve("gap_to_ahead", basic_context)
        assert result == "1.2 seconds"
    
    def test_resolve_gap_trend(self, resolver, basic_context):
        """Test resolving gap_trend placeholder."""
        basic_context.gap_trend = "closing"
        result = resolver.resolve("gap_trend", basic_context)
        assert result == "closing"
    
    def test_resolve_gap_fallback_to_ahead(self, resolver, basic_context):
        """Test gap falls back to gap_to_ahead when gap_to_leader unavailable."""
        basic_context.gap_to_ahead = 0.5
        result = resolver.resolve("gap", basic_context)
        assert result == "0.5 seconds"


class TestTimePlaceholders:
    """Test time-related placeholder resolution."""
    
    def test_resolve_lap_time(self, resolver, basic_context):
        """Test resolving lap_time placeholder."""
        basic_context.event.lap_time = 83.456
        result = resolver.resolve("lap_time", basic_context)
        assert result == "1:23.456"
    
    def test_resolve_sector_1_time(self, resolver, basic_context):
        """Test resolving sector_1_time placeholder."""
        basic_context.sector_1_time = 23.456
        result = resolver.resolve("sector_1_time", basic_context)
        assert result == "23.456"
    
    def test_resolve_sector_2_time(self, resolver, basic_context):
        """Test resolving sector_2_time placeholder."""
        basic_context.sector_2_time = 34.567
        result = resolver.resolve("sector_2_time", basic_context)
        assert result == "34.567"
    
    def test_resolve_sector_3_time(self, resolver, basic_context):
        """Test resolving sector_3_time placeholder."""
        basic_context.sector_3_time = 25.789
        result = resolver.resolve("sector_3_time", basic_context)
        assert result == "25.789"


class TestSectorStatusPlaceholders:
    """Test sector status placeholder resolution."""
    
    def test_resolve_sector_status_purple_s1(self, resolver, basic_context):
        """Test resolving sector_status with purple sector 1."""
        basic_context.sector_1_status = "purple"
        result = resolver.resolve("sector_status", basic_context)
        assert result == "purple sector in sector 1"
    
    def test_resolve_sector_status_purple_s2(self, resolver, basic_context):
        """Test resolving sector_status with purple sector 2."""
        basic_context.sector_2_status = "purple"
        result = resolver.resolve("sector_status", basic_context)
        assert result == "purple sector in sector 2"
    
    def test_resolve_sector_status_purple_s3(self, resolver, basic_context):
        """Test resolving sector_status with purple sector 3."""
        basic_context.sector_3_status = "purple"
        result = resolver.resolve("sector_status", basic_context)
        assert result == "purple sector in sector 3"
    
    def test_resolve_sector_status_no_purple(self, resolver, basic_context):
        """Test resolving sector_status with no purple sectors."""
        basic_context.sector_1_status = "green"
        result = resolver.resolve("sector_status", basic_context)
        assert result is None


class TestTirePlaceholders:
    """Test tire-related placeholder resolution."""
    
    def test_resolve_tire_compound(self, resolver, basic_context):
        """Test resolving tire_compound placeholder."""
        basic_context.current_tire_compound = "SOFT"
        result = resolver.resolve("tire_compound", basic_context)
        assert result == "soft"
    
    def test_resolve_tire_compound_variations(self, resolver, basic_context):
        """Test resolving tire compound with various inputs."""
        test_cases = [
            ("SOFT", "soft"),
            ("MEDIUM", "medium"),
            ("HARD", "hard"),
            ("INTERMEDIATE", "intermediate"),
            ("INTER", "intermediate"),
            ("WET", "wet"),
            ("WETS", "wet")
        ]
        
        for input_compound, expected in test_cases:
            basic_context.current_tire_compound = input_compound
            result = resolver.resolve("tire_compound", basic_context)
            assert result == expected, f"Failed for {input_compound}"
    
    def test_resolve_tire_age(self, resolver, basic_context):
        """Test resolving tire_age placeholder."""
        basic_context.current_tire_age = 18
        result = resolver.resolve("tire_age", basic_context)
        assert result == "18 laps old"
    
    def test_resolve_tire_age_diff(self, resolver, basic_context):
        """Test resolving tire_age_diff placeholder."""
        basic_context.tire_age_differential = -5
        result = resolver.resolve("tire_age_diff", basic_context)
        assert result == "5"
    
    def test_resolve_new_tire_compound(self, resolver, basic_context):
        """Test resolving new_tire_compound placeholder."""
        basic_context.current_tire_compound = "MEDIUM"
        result = resolver.resolve("new_tire_compound", basic_context)
        assert result == "medium"
    
    def test_resolve_old_tire_compound(self, resolver, basic_context):
        """Test resolving old_tire_compound placeholder."""
        basic_context.previous_tire_compound = "SOFT"
        result = resolver.resolve("old_tire_compound", basic_context)
        assert result == "soft"
    
    def test_resolve_old_tire_age(self, resolver, basic_context):
        """Test resolving old_tire_age placeholder."""
        basic_context.previous_tire_age = 25
        result = resolver.resolve("old_tire_age", basic_context)
        assert result == "25 laps"


class TestSpeedPlaceholders:
    """Test speed-related placeholder resolution."""
    
    def test_resolve_speed(self, resolver, basic_context):
        """Test resolving speed placeholder."""
        basic_context.speed = 315.7
        result = resolver.resolve("speed", basic_context)
        assert result == "316 kilometers per hour"
    
    def test_resolve_speed_trap(self, resolver, basic_context):
        """Test resolving speed_trap placeholder."""
        basic_context.speed_trap = 342.3
        result = resolver.resolve("speed_trap", basic_context)
        assert result == "342 kilometers per hour"


class TestDRSPlaceholder:
    """Test DRS placeholder resolution."""
    
    def test_resolve_drs_active(self, resolver, basic_context):
        """Test resolving drs_status when DRS is active."""
        basic_context.drs_active = True
        result = resolver.resolve("drs_status", basic_context)
        assert result == "with DRS"
    
    def test_resolve_drs_inactive(self, resolver, basic_context):
        """Test resolving drs_status when DRS is inactive."""
        basic_context.drs_active = False
        result = resolver.resolve("drs_status", basic_context)
        assert result == ""
    
    def test_resolve_drs_none(self, resolver, basic_context):
        """Test resolving drs_status when DRS data unavailable."""
        result = resolver.resolve("drs_status", basic_context)
        assert result == ""


class TestWeatherPlaceholders:
    """Test weather-related placeholder resolution."""
    
    def test_resolve_track_temp(self, resolver, basic_context):
        """Test resolving track_temp placeholder."""
        basic_context.track_temp = 45.5
        result = resolver.resolve("track_temp", basic_context)
        assert result == "45.5°C"
    
    def test_resolve_air_temp(self, resolver, basic_context):
        """Test resolving air_temp placeholder."""
        basic_context.air_temp = 28.3
        result = resolver.resolve("air_temp", basic_context)
        assert result == "28.3°C"
    
    def test_resolve_weather_condition_rain(self, resolver, basic_context):
        """Test resolving weather_condition with rain."""
        basic_context.rainfall = 1.5
        result = resolver.resolve("weather_condition", basic_context)
        assert result == "in the wet conditions"
    
    def test_resolve_weather_condition_wind(self, resolver, basic_context):
        """Test resolving weather_condition with high wind."""
        basic_context.wind_speed = 25.0
        result = resolver.resolve("weather_condition", basic_context)
        assert result == "with the wind picking up"
    
    def test_resolve_weather_condition_hot_track(self, resolver, basic_context):
        """Test resolving weather_condition with hot track."""
        basic_context.track_temp = 50.0
        result = resolver.resolve("weather_condition", basic_context)
        assert result == "as the track heats up"
    
    def test_resolve_weather_condition_high_humidity(self, resolver, basic_context):
        """Test resolving weather_condition with high humidity."""
        basic_context.humidity = 75.0
        result = resolver.resolve("weather_condition", basic_context)
        assert result == "in these challenging conditions"
    
    def test_resolve_weather_condition_normal(self, resolver, basic_context):
        """Test resolving weather_condition with normal conditions."""
        basic_context.track_temp = 35.0
        basic_context.wind_speed = 10.0
        result = resolver.resolve("weather_condition", basic_context)
        assert result == "in these conditions"
    
    def test_resolve_weather_condition_no_data(self, resolver, basic_context):
        """Test resolving weather_condition with no weather data."""
        result = resolver.resolve("weather_condition", basic_context)
        assert result is None


class TestPitStopPlaceholders:
    """Test pit stop placeholder resolution."""
    
    def test_resolve_pit_duration(self, resolver, basic_context):
        """Test resolving pit_duration placeholder."""
        basic_context.pit_duration = 2.3
        result = resolver.resolve("pit_duration", basic_context)
        assert result == "2.3 seconds"
    
    def test_resolve_pit_count(self, resolver, basic_context):
        """Test resolving pit_count placeholder."""
        basic_context.pit_count = 2
        result = resolver.resolve("pit_count", basic_context)
        assert result == "2"


class TestNarrativePlaceholders:
    """Test narrative-related placeholder resolution."""
    
    def test_resolve_narrative_reference_battle(self, resolver, basic_context):
        """Test resolving narrative_reference for battle."""
        basic_context.active_narratives = ["battle_hamilton_verstappen"]
        result = resolver.resolve("narrative_reference", basic_context)
        assert result == "continuing their battle"
    
    def test_resolve_narrative_reference_comeback(self, resolver, basic_context):
        """Test resolving narrative_reference for comeback."""
        basic_context.active_narratives = ["comeback_hamilton"]
        result = resolver.resolve("narrative_reference", basic_context)
        assert result == "on his comeback drive"
    
    def test_resolve_narrative_reference_strategy(self, resolver, basic_context):
        """Test resolving narrative_reference for strategy."""
        basic_context.active_narratives = ["strategy_divergence"]
        result = resolver.resolve("narrative_reference", basic_context)
        assert result == "with the different tire strategies"
    
    def test_resolve_narrative_reference_undercut(self, resolver, basic_context):
        """Test resolving narrative_reference for undercut."""
        basic_context.active_narratives = ["undercut_attempt"]
        result = resolver.resolve("narrative_reference", basic_context)
        assert result == "attempting the undercut"
    
    def test_resolve_narrative_reference_overcut(self, resolver, basic_context):
        """Test resolving narrative_reference for overcut."""
        basic_context.active_narratives = ["overcut_attempt"]
        result = resolver.resolve("narrative_reference", basic_context)
        assert result == "going for the overcut"
    
    def test_resolve_narrative_reference_championship(self, resolver, basic_context):
        """Test resolving narrative_reference for championship."""
        basic_context.active_narratives = ["championship_fight"]
        result = resolver.resolve("narrative_reference", basic_context)
        assert result == "in the championship fight"
    
    def test_resolve_narrative_reference_none(self, resolver, basic_context):
        """Test resolving narrative_reference with no narratives."""
        result = resolver.resolve("narrative_reference", basic_context)
        assert result is None
    
    def test_resolve_battle_laps(self, resolver, basic_context):
        """Test resolving battle_laps placeholder."""
        basic_context.active_narratives = ["battle_hamilton_verstappen"]
        result = resolver.resolve("battle_laps", basic_context)
        assert result == "several"


class TestChampionshipPlaceholders:
    """Test championship-related placeholder resolution."""
    
    def test_resolve_championship_position(self, resolver, basic_context):
        """Test resolving championship_position placeholder."""
        basic_context.driver_championship_position = 1
        result = resolver.resolve("championship_position", basic_context)
        assert result == "1st"
    
    def test_resolve_championship_gap(self, resolver, basic_context):
        """Test resolving championship_gap placeholder."""
        basic_context.championship_gap_to_leader = 25
        result = resolver.resolve("championship_gap", basic_context)
        assert result == "25 points"
    
    def test_resolve_championship_context_leader(self, resolver, basic_context):
        """Test resolving championship_context for leader."""
        basic_context.driver_championship_position = 1
        result = resolver.resolve("championship_context", basic_context)
        assert result == "the championship leader"
    
    def test_resolve_championship_context_second(self, resolver, basic_context):
        """Test resolving championship_context for second place."""
        basic_context.driver_championship_position = 2
        result = resolver.resolve("championship_context", basic_context)
        assert result == "second in the standings"
    
    def test_resolve_championship_context_third(self, resolver, basic_context):
        """Test resolving championship_context for third place."""
        basic_context.driver_championship_position = 3
        result = resolver.resolve("championship_context", basic_context)
        assert result == "third in the championship"
    
    def test_resolve_championship_context_top5(self, resolver, basic_context):
        """Test resolving championship_context for top 5."""
        basic_context.driver_championship_position = 4
        result = resolver.resolve("championship_context", basic_context)
        assert result == "4th in the championship"
    
    def test_resolve_championship_context_top10(self, resolver, basic_context):
        """Test resolving championship_context for top 10."""
        basic_context.driver_championship_position = 7
        result = resolver.resolve("championship_context", basic_context)
        assert result == "fighting for 7th in the championship"
    
    def test_resolve_championship_context_outside_top10(self, resolver, basic_context):
        """Test resolving championship_context outside top 10."""
        basic_context.driver_championship_position = 15
        result = resolver.resolve("championship_context", basic_context)
        assert result is None


class TestOrdinalHelper:
    """Test ordinal number formatting."""
    
    def test_ordinal_numbers(self, resolver):
        """Test ordinal formatting for various numbers."""
        test_cases = [
            (1, "1st"),
            (2, "2nd"),
            (3, "3rd"),
            (4, "4th"),
            (10, "10th"),
            (11, "11th"),
            (12, "12th"),
            (13, "13th"),
            (21, "21st"),
            (22, "22nd"),
            (23, "23rd"),
            (24, "24th")
        ]
        
        for number, expected in test_cases:
            result = resolver._ordinal(number)
            assert result == expected, f"Failed for {number}"


class TestUnknownPlaceholder:
    """Test handling of unknown placeholders."""
    
    def test_unknown_placeholder(self, resolver, basic_context):
        """Test resolving unknown placeholder returns None."""
        result = resolver.resolve("unknown_placeholder", basic_context)
        assert result is None
    
    def test_placeholder_with_braces(self, resolver, basic_context):
        """Test resolving placeholder with curly braces."""
        basic_context.position_after = 1
        result = resolver.resolve("{position}", basic_context)
        assert result == "P1"


class TestErrorHandling:
    """Test error handling in placeholder resolution."""
    
    def test_resolve_with_exception(self, resolver, basic_context):
        """Test that exceptions are caught and None is returned."""
        # Create a context that will cause an error
        basic_context.event = None
        result = resolver.resolve("driver", basic_context)
        assert result is None
