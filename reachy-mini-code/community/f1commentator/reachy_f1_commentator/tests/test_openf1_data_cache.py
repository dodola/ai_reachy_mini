"""
Unit tests for OpenF1 Data Cache.

Tests caching functionality, data loading, session records tracking,
and cache expiration logic.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from reachy_f1_commentator.src.openf1_data_cache import (
    OpenF1DataCache, DriverInfo, ChampionshipEntry, SessionRecords, CacheEntry
)
from reachy_f1_commentator.src.models import OvertakeEvent, PitStopEvent, FastestLapEvent


class TestDriverInfo:
    """Test DriverInfo dataclass."""
    
    def test_driver_info_creation(self):
        """Test creating a DriverInfo object."""
        driver = DriverInfo(
            driver_number=44,
            broadcast_name="L HAMILTON",
            full_name="Lewis HAMILTON",
            name_acronym="HAM",
            team_name="Mercedes",
            team_colour="00D2BE",
            first_name="Lewis",
            last_name="Hamilton"
        )
        
        assert driver.driver_number == 44
        assert driver.last_name == "Hamilton"
        assert driver.team_name == "Mercedes"


class TestChampionshipEntry:
    """Test ChampionshipEntry dataclass."""
    
    def test_championship_entry_creation(self):
        """Test creating a ChampionshipEntry object."""
        entry = ChampionshipEntry(
            driver_number=1,
            position=1,
            points=575.0,
            driver_name="Verstappen"
        )
        
        assert entry.driver_number == 1
        assert entry.position == 1
        assert entry.points == 575.0


class TestSessionRecords:
    """Test SessionRecords tracking."""
    
    def test_update_fastest_lap_new_record(self):
        """Test updating fastest lap with a new record."""
        records = SessionRecords()
        
        is_record = records.update_fastest_lap("Hamilton", 90.5)
        
        assert is_record is True
        assert records.fastest_lap_driver == "Hamilton"
        assert records.fastest_lap_time == 90.5
    
    def test_update_fastest_lap_not_faster(self):
        """Test updating fastest lap with a slower time."""
        records = SessionRecords()
        records.update_fastest_lap("Hamilton", 90.5)
        
        is_record = records.update_fastest_lap("Verstappen", 91.0)
        
        assert is_record is False
        assert records.fastest_lap_driver == "Hamilton"
        assert records.fastest_lap_time == 90.5
    
    def test_update_fastest_lap_faster(self):
        """Test updating fastest lap with a faster time."""
        records = SessionRecords()
        records.update_fastest_lap("Hamilton", 90.5)
        
        is_record = records.update_fastest_lap("Verstappen", 90.2)
        
        assert is_record is True
        assert records.fastest_lap_driver == "Verstappen"
        assert records.fastest_lap_time == 90.2
    
    def test_increment_overtake_count(self):
        """Test incrementing overtake count."""
        records = SessionRecords()
        
        count1 = records.increment_overtake_count("Hamilton")
        count2 = records.increment_overtake_count("Hamilton")
        count3 = records.increment_overtake_count("Verstappen")
        
        assert count1 == 1
        assert count2 == 2
        assert count3 == 1
        assert records.overtake_counts["Hamilton"] == 2
        assert records.overtake_counts["Verstappen"] == 1
        assert records.most_overtakes_driver == "Hamilton"
        assert records.most_overtakes_count == 2
    
    def test_update_stint_length(self):
        """Test updating stint length."""
        records = SessionRecords()
        
        is_record1 = records.update_stint_length("Hamilton", 15)
        is_record2 = records.update_stint_length("Verstappen", 20)
        is_record3 = records.update_stint_length("Hamilton", 18)
        
        assert is_record1 is True
        assert is_record2 is True
        assert is_record3 is False  # Not longer than 20
        assert records.longest_stint_driver == "Verstappen"
        assert records.longest_stint_laps == 20
    
    def test_reset_stint_length(self):
        """Test resetting stint length after pit stop."""
        records = SessionRecords()
        records.update_stint_length("Hamilton", 15)
        
        records.reset_stint_length("Hamilton")
        
        assert records.stint_lengths["Hamilton"] == 0
    
    def test_update_fastest_pit(self):
        """Test updating fastest pit stop."""
        records = SessionRecords()
        
        is_record1 = records.update_fastest_pit("Hamilton", 2.5)
        is_record2 = records.update_fastest_pit("Verstappen", 2.3)
        is_record3 = records.update_fastest_pit("Leclerc", 2.8)
        
        assert is_record1 is True
        assert is_record2 is True
        assert is_record3 is False
        assert records.fastest_pit_driver == "Verstappen"
        assert records.fastest_pit_duration == 2.3


class TestCacheEntry:
    """Test CacheEntry expiration logic."""
    
    def test_cache_entry_not_expired(self):
        """Test cache entry that has not expired."""
        entry = CacheEntry(
            data={"test": "data"},
            timestamp=datetime.now(),
            ttl_seconds=60
        )
        
        assert entry.is_expired() is False
    
    def test_cache_entry_expired(self):
        """Test cache entry that has expired."""
        entry = CacheEntry(
            data={"test": "data"},
            timestamp=datetime.now() - timedelta(seconds=120),
            ttl_seconds=60
        )
        
        assert entry.is_expired() is True
    
    def test_cache_entry_just_expired(self):
        """Test cache entry that just expired."""
        entry = CacheEntry(
            data={"test": "data"},
            timestamp=datetime.now() - timedelta(seconds=61),
            ttl_seconds=60
        )
        
        assert entry.is_expired() is True


class TestOpenF1DataCache:
    """Test OpenF1DataCache functionality."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock OpenF1 client."""
        client = Mock()
        return client
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock()
        config.cache_duration_driver_info = 3600
        config.cache_duration_championship = 3600
        return config
    
    @pytest.fixture
    def cache(self, mock_client, mock_config):
        """Create an OpenF1DataCache instance."""
        return OpenF1DataCache(mock_client, mock_config)
    
    def test_initialization(self, cache):
        """Test cache initialization."""
        assert cache.driver_info == {}
        assert cache.driver_info_by_name == {}
        assert cache.team_colors == {}
        assert cache.championship_standings == []
        assert cache.session_records is not None
    
    def test_set_session_key(self, cache):
        """Test setting session key."""
        cache.set_session_key(9197)
        
        assert cache._session_key == 9197
    
    def test_load_static_data_success(self, cache, mock_client):
        """Test successful loading of static data."""
        cache.set_session_key(9197)
        
        # Mock API response
        mock_client.poll_endpoint.return_value = [
            {
                "driver_number": 44,
                "broadcast_name": "L HAMILTON",
                "full_name": "Lewis HAMILTON",
                "name_acronym": "HAM",
                "team_name": "Mercedes",
                "team_colour": "00D2BE",
                "first_name": "Lewis",
                "last_name": "Hamilton"
            },
            {
                "driver_number": 1,
                "broadcast_name": "M VERSTAPPEN",
                "full_name": "Max VERSTAPPEN",
                "name_acronym": "VER",
                "team_name": "Red Bull Racing",
                "team_colour": "0600EF",
                "first_name": "Max",
                "last_name": "Verstappen"
            }
        ]
        
        result = cache.load_static_data()
        
        assert result is True
        assert len(cache.driver_info) == 2
        assert 44 in cache.driver_info
        assert 1 in cache.driver_info
        assert cache.driver_info[44].last_name == "Hamilton"
        assert cache.driver_info[1].last_name == "Verstappen"
        assert "HAMILTON" in cache.driver_info_by_name
        assert "HAM" in cache.driver_info_by_name
        assert len(cache.team_colors) == 2
        assert cache.team_colors["Mercedes"] == "00D2BE"
    
    def test_load_static_data_no_session_key(self, cache, mock_client):
        """Test loading static data without session key."""
        result = cache.load_static_data()
        
        assert result is False
        mock_client.poll_endpoint.assert_not_called()
    
    def test_load_static_data_api_failure(self, cache, mock_client):
        """Test loading static data when API fails."""
        cache.set_session_key(9197)
        mock_client.poll_endpoint.return_value = None
        
        result = cache.load_static_data()
        
        assert result is False
    
    def test_load_static_data_uses_cache(self, cache, mock_client):
        """Test that static data uses cache and doesn't reload unnecessarily."""
        cache.set_session_key(9197)
        
        # Mock API response
        mock_client.poll_endpoint.return_value = [
            {
                "driver_number": 44,
                "broadcast_name": "L HAMILTON",
                "full_name": "Lewis HAMILTON",
                "name_acronym": "HAM",
                "team_name": "Mercedes",
                "team_colour": "00D2BE",
                "first_name": "Lewis",
                "last_name": "Hamilton"
            }
        ]
        
        # First load
        result1 = cache.load_static_data()
        assert result1 is True
        assert mock_client.poll_endpoint.call_count == 1
        
        # Second load should use cache
        result2 = cache.load_static_data()
        assert result2 is True
        assert mock_client.poll_endpoint.call_count == 1  # Not called again
    
    def test_get_driver_info_by_number(self, cache):
        """Test getting driver info by number."""
        cache.driver_info[44] = DriverInfo(
            driver_number=44,
            broadcast_name="L HAMILTON",
            full_name="Lewis HAMILTON",
            name_acronym="HAM",
            team_name="Mercedes",
            team_colour="00D2BE",
            first_name="Lewis",
            last_name="Hamilton"
        )
        
        driver = cache.get_driver_info(44)
        
        assert driver is not None
        assert driver.last_name == "Hamilton"
    
    def test_get_driver_info_by_name(self, cache):
        """Test getting driver info by name."""
        driver_info = DriverInfo(
            driver_number=44,
            broadcast_name="L HAMILTON",
            full_name="Lewis HAMILTON",
            name_acronym="HAM",
            team_name="Mercedes",
            team_colour="00D2BE",
            first_name="Lewis",
            last_name="Hamilton"
        )
        cache.driver_info[44] = driver_info
        cache.driver_info_by_name["HAMILTON"] = driver_info
        
        driver = cache.get_driver_info("Hamilton")
        
        assert driver is not None
        assert driver.driver_number == 44
    
    def test_get_team_color(self, cache):
        """Test getting team color."""
        cache.team_colors["Mercedes"] = "00D2BE"
        
        color = cache.get_team_color("Mercedes")
        
        assert color == "00D2BE"
    
    def test_get_championship_position(self, cache):
        """Test getting championship position."""
        cache.championship_standings = [
            ChampionshipEntry(1, 1, 575.0, "Verstappen"),
            ChampionshipEntry(44, 2, 450.0, "Hamilton")
        ]
        
        position = cache.get_championship_position(44)
        
        assert position == 2
    
    def test_get_championship_points(self, cache):
        """Test getting championship points."""
        cache.championship_standings = [
            ChampionshipEntry(1, 1, 575.0, "Verstappen"),
            ChampionshipEntry(44, 2, 450.0, "Hamilton")
        ]
        
        points = cache.get_championship_points(44)
        
        assert points == 450.0
    
    def test_is_championship_contender(self, cache):
        """Test checking if driver is championship contender."""
        cache.championship_standings = [
            ChampionshipEntry(1, 1, 575.0, "Verstappen"),
            ChampionshipEntry(44, 2, 450.0, "Hamilton"),
            ChampionshipEntry(16, 6, 200.0, "Leclerc")
        ]
        
        assert cache.is_championship_contender(1) is True
        assert cache.is_championship_contender(44) is True
        assert cache.is_championship_contender(16) is False
    
    def test_update_session_records_fastest_lap(self, cache):
        """Test updating session records with fastest lap event."""
        event = FastestLapEvent(
            driver="Hamilton",
            lap_time=90.5,
            lap_number=10,
            timestamp=datetime.now()
        )
        
        cache.update_session_records(event)
        
        assert cache.session_records.fastest_lap_driver == "Hamilton"
        assert cache.session_records.fastest_lap_time == 90.5
    
    def test_update_session_records_overtake(self, cache):
        """Test updating session records with overtake event."""
        event = OvertakeEvent(
            overtaking_driver="Hamilton",
            overtaken_driver="Verstappen",
            new_position=1,
            lap_number=10,
            timestamp=datetime.now()
        )
        
        cache.update_session_records(event)
        
        assert cache.session_records.overtake_counts["Hamilton"] == 1
    
    def test_update_session_records_pit_stop(self, cache):
        """Test updating session records with pit stop event."""
        event = PitStopEvent(
            driver="Hamilton",
            pit_count=1,
            pit_duration=2.5,
            tire_compound="soft",
            lap_number=10,
            timestamp=datetime.now()
        )
        
        cache.update_session_records(event)
        
        assert cache.session_records.fastest_pit_driver == "Hamilton"
        assert cache.session_records.fastest_pit_duration == 2.5
        assert cache.session_records.stint_lengths["Hamilton"] == 0  # Reset after pit
    
    def test_update_stint_lengths(self, cache):
        """Test updating stint lengths for all drivers."""
        driver_tire_ages = {
            "Hamilton": 15,
            "Verstappen": 20,
            "Leclerc": 10
        }
        
        cache.update_stint_lengths(driver_tire_ages)
        
        assert cache.session_records.stint_lengths["Hamilton"] == 15
        assert cache.session_records.stint_lengths["Verstappen"] == 20
        assert cache.session_records.longest_stint_driver == "Verstappen"
        assert cache.session_records.longest_stint_laps == 20
    
    def test_clear_session_records(self, cache):
        """Test clearing session records."""
        # Add some records
        cache.session_records.update_fastest_lap("Hamilton", 90.5)
        cache.session_records.increment_overtake_count("Hamilton")
        
        # Clear
        cache.clear_session_records()
        
        assert cache.session_records.fastest_lap_driver is None
        assert cache.session_records.fastest_lap_time is None
        assert len(cache.session_records.overtake_counts) == 0
    
    def test_invalidate_cache_driver_info(self, cache):
        """Test invalidating driver info cache."""
        cache._driver_info_cache = CacheEntry(
            data=True,
            timestamp=datetime.now(),
            ttl_seconds=3600
        )
        
        cache.invalidate_cache("driver_info")
        
        assert cache._driver_info_cache is None
    
    def test_invalidate_cache_all(self, cache):
        """Test invalidating all caches."""
        cache._driver_info_cache = CacheEntry(
            data=True,
            timestamp=datetime.now(),
            ttl_seconds=3600
        )
        cache._championship_cache = CacheEntry(
            data=True,
            timestamp=datetime.now(),
            ttl_seconds=3600
        )
        
        cache.invalidate_cache("all")
        
        assert cache._driver_info_cache is None
        assert cache._championship_cache is None
