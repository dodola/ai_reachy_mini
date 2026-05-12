"""
Unit tests for ContextEnricher orchestrator.

Tests the context enrichment orchestration, concurrent fetching,
gap trend calculation, and timeout handling.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from reachy_f1_commentator.src.context_enricher import ContextEnricher
from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.enhanced_models import ContextData
from reachy_f1_commentator.src.models import OvertakeEvent, PitStopEvent, RaceState


@pytest.fixture
def config():
    """Create test configuration."""
    config = Config()
    config.context_enrichment_timeout_ms = 500
    config.enable_telemetry = True
    config.enable_weather = True
    config.enable_championship = True
    return config


@pytest.fixture
def mock_openf1_client():
    """Create mock OpenF1 client."""
    client = Mock()
    client.base_url = "https://api.openf1.org/v1"
    return client


@pytest.fixture
def mock_race_state_tracker():
    """Create mock race state tracker."""
    from src.models import RacePhase, DriverState
    
    tracker = Mock()
    tracker.get_state.return_value = RaceState(
        current_lap=10,
        total_laps=50,
        race_phase=RacePhase.MID_RACE,
        drivers=[
            DriverState(name="Hamilton", position=1),
            DriverState(name="Verstappen", position=2),
            DriverState(name="Leclerc", position=3)
        ]
    )
    return tracker


@pytest.fixture
def context_enricher(config, mock_openf1_client, mock_race_state_tracker):
    """Create ContextEnricher instance."""
    enricher = ContextEnricher(config, mock_openf1_client, mock_race_state_tracker)
    enricher.set_session_key(9197)
    return enricher


@pytest.fixture
def sample_overtake_event():
    """Create sample overtake event."""
    return OvertakeEvent(
        timestamp=datetime.now(),
        lap_number=10,
        overtaking_driver="Hamilton",
        overtaken_driver="Verstappen",
        new_position=1
    )


@pytest.fixture
def sample_pit_event():
    """Create sample pit stop event."""
    return PitStopEvent(
        timestamp=datetime.now(),
        lap_number=15,
        driver="Hamilton",
        pit_count=1,
        pit_duration=2.3,
        tire_compound="soft"
    )


class TestContextEnricherInitialization:
    """Test ContextEnricher initialization."""
    
    def test_initialization(self, config, mock_openf1_client, mock_race_state_tracker):
        """Test that ContextEnricher initializes correctly."""
        enricher = ContextEnricher(config, mock_openf1_client, mock_race_state_tracker)
        
        assert enricher.config == config
        assert enricher.openf1_client == mock_openf1_client
        assert enricher.race_state_tracker == mock_race_state_tracker
        assert enricher.timeout_ms == 500
        assert enricher.timeout_seconds == 0.5
        assert enricher.cache is not None
        assert enricher.fetcher is not None
    
    def test_set_session_key(self, context_enricher):
        """Test setting session key."""
        context_enricher.set_session_key(9999)
        assert context_enricher._session_key == 9999
        assert context_enricher.cache._session_key == 9999


class TestContextEnrichment:
    """Test context enrichment functionality."""
    
    @pytest.mark.asyncio
    async def test_enrich_context_without_session_key(
        self,
        config,
        mock_openf1_client,
        mock_race_state_tracker,
        sample_overtake_event
    ):
        """Test that enrichment fails gracefully without session key."""
        enricher = ContextEnricher(config, mock_openf1_client, mock_race_state_tracker)
        # Don't set session key
        
        context = await enricher.enrich_context(sample_overtake_event)
        
        assert isinstance(context, ContextData)
        assert context.event == sample_overtake_event
        assert "all - no session key" in context.missing_data_sources
        assert context.enrichment_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_enrich_context_with_mock_data(
        self,
        context_enricher,
        sample_overtake_event
    ):
        """Test context enrichment with mocked fetch methods."""
        # Mock the cache to return driver info
        context_enricher.cache.get_driver_info = Mock(return_value=Mock(driver_number=44))
        
        # Mock the fetch methods
        context_enricher._fetch_telemetry_safe = AsyncMock(return_value={
            "speed": 315.5,
            "drs_active": True,
            "throttle": 100,
            "brake": 0,
            "rpm": 12000,
            "gear": 8
        })
        
        context_enricher._fetch_gaps_safe = AsyncMock(return_value={
            "gap_to_leader": 0.0,
            "gap_to_ahead": None,
            "gap_to_behind": 1.2
        })
        
        context_enricher._fetch_lap_data_safe = AsyncMock(return_value={
            "sector_1_time": 25.123,
            "sector_2_time": 28.456,
            "sector_3_time": 22.789,
            "sector_1_status": "purple",
            "sector_2_status": "green",
            "sector_3_status": "yellow",
            "speed_trap": 330.5
        })
        
        context_enricher._fetch_tire_data_safe = AsyncMock(return_value={
            "current_tire_compound": "soft",
            "current_tire_age": 5,
            "previous_tire_compound": "medium",
            "previous_tire_age": 18
        })
        
        context_enricher._fetch_weather_safe = AsyncMock(return_value={
            "air_temp": 28.5,
            "track_temp": 42.3,
            "humidity": 65,
            "rainfall": 0,
            "wind_speed": 15,
            "wind_direction": 180
        })
        
        context_enricher._fetch_pit_data_safe = AsyncMock(return_value={
            "pit_duration": 2.3,
            "pit_lane_time": 18.5,
            "pit_count": 1
        })
        
        # Enrich context
        context = await context_enricher.enrich_context(sample_overtake_event)
        
        # Verify context data
        assert isinstance(context, ContextData)
        assert context.event == sample_overtake_event
        assert context.speed == 315.5
        assert context.drs_active is True
        assert context.throttle == 100
        assert context.gap_to_leader == 0.0
        assert context.gap_to_behind == 1.2
        assert context.sector_1_time == 25.123
        assert context.sector_1_status == "purple"
        assert context.current_tire_compound == "soft"
        assert context.current_tire_age == 5
        assert context.air_temp == 28.5
        assert context.track_temp == 42.3
        assert context.pit_duration == 2.3
        assert context.enrichment_time_ms > 0
        assert context.enrichment_time_ms < 500  # Should be well under timeout
    
    @pytest.mark.asyncio
    async def test_enrich_context_with_missing_data(
        self,
        context_enricher,
        sample_overtake_event
    ):
        """Test context enrichment with some missing data sources."""
        # Mock the cache to return driver info
        context_enricher.cache.get_driver_info = Mock(return_value=Mock(driver_number=44))
        
        # Mock some fetch methods to return empty data
        context_enricher._fetch_telemetry_safe = AsyncMock(return_value={})
        context_enricher._fetch_gaps_safe = AsyncMock(return_value={
            "gap_to_leader": 1.5,
            "gap_to_ahead": 1.5
        })
        context_enricher._fetch_lap_data_safe = AsyncMock(return_value={})
        context_enricher._fetch_tire_data_safe = AsyncMock(return_value={
            "current_tire_compound": "medium",
            "current_tire_age": 12
        })
        context_enricher._fetch_weather_safe = AsyncMock(return_value={})
        context_enricher._fetch_pit_data_safe = AsyncMock(return_value={})
        
        # Enrich context
        context = await context_enricher.enrich_context(sample_overtake_event)
        
        # Verify context data
        assert isinstance(context, ContextData)
        assert context.gap_to_leader == 1.5
        assert context.current_tire_compound == "medium"
        
        # Verify missing sources are tracked
        assert "telemetry" in context.missing_data_sources
        assert "lap_data" in context.missing_data_sources
        assert "weather" in context.missing_data_sources
        assert "pit_data" in context.missing_data_sources
    
    @pytest.mark.asyncio
    async def test_enrich_context_timeout(
        self,
        config,
        mock_openf1_client,
        mock_race_state_tracker,
        sample_overtake_event
    ):
        """Test that context enrichment respects timeout."""
        # Create enricher with very short timeout
        config.context_enrichment_timeout_ms = 10
        enricher = ContextEnricher(config, mock_openf1_client, mock_race_state_tracker)
        enricher.set_session_key(9197)
        
        # Mock the cache to return driver info
        enricher.cache.get_driver_info = Mock(return_value=Mock(driver_number=44))
        
        # Mock fetch methods to take longer than timeout
        async def slow_fetch():
            await asyncio.sleep(1.0)  # 1 second - much longer than 10ms timeout
            return {}
        
        enricher._fetch_telemetry_safe = slow_fetch
        enricher._fetch_gaps_safe = slow_fetch
        enricher._fetch_lap_data_safe = slow_fetch
        enricher._fetch_tire_data_safe = slow_fetch
        enricher._fetch_weather_safe = slow_fetch
        enricher._fetch_pit_data_safe = slow_fetch
        
        # Enrich context
        context = await enricher.enrich_context(sample_overtake_event)
        
        # Verify timeout was hit
        assert isinstance(context, ContextData)
        assert any("timeout" in source for source in context.missing_data_sources)
        assert context.enrichment_time_ms < 100  # Should timeout quickly


class TestGapTrendCalculation:
    """Test gap trend calculation."""
    
    @pytest.mark.asyncio
    async def test_gap_trend_closing(self, context_enricher, sample_overtake_event):
        """Test gap trend calculation for closing gap."""
        # Mock driver info
        context_enricher.cache.get_driver_info = Mock(return_value=Mock(driver_number=44))
        
        # Simulate gap history: gap decreasing over laps
        context_enricher._gap_history[44] = asyncio.Queue()
        
        # Mock fetch methods
        async def mock_gaps_closing(lap):
            gaps = [5.0, 4.0, 3.0]  # Gap closing
            return {"gap_to_leader": gaps[min(lap, len(gaps)-1)]}
        
        # Manually populate gap history
        from collections import deque
        context_enricher._gap_history[44] = deque(maxlen=3)
        context_enricher._gap_history[44].append((8, 5.0))
        context_enricher._gap_history[44].append((9, 4.0))
        context_enricher._gap_history[44].append((10, 3.0))
        
        # Create context and calculate trend
        context = ContextData(event=sample_overtake_event, race_state=Mock())
        context.gap_to_leader = 3.0
        context_enricher._calculate_gap_trend(context, 44)
        
        # Verify trend
        assert context.gap_trend == "closing"
    
    @pytest.mark.asyncio
    async def test_gap_trend_increasing(self, context_enricher, sample_overtake_event):
        """Test gap trend calculation for increasing gap."""
        # Mock driver info
        context_enricher.cache.get_driver_info = Mock(return_value=Mock(driver_number=44))
        
        # Manually populate gap history: gap increasing
        from collections import deque
        context_enricher._gap_history[44] = deque(maxlen=3)
        context_enricher._gap_history[44].append((8, 3.0))
        context_enricher._gap_history[44].append((9, 4.0))
        context_enricher._gap_history[44].append((10, 5.0))
        
        # Create context and calculate trend
        context = ContextData(event=sample_overtake_event, race_state=Mock())
        context.gap_to_leader = 5.0
        context_enricher._calculate_gap_trend(context, 44)
        
        # Verify trend
        assert context.gap_trend == "increasing"
    
    @pytest.mark.asyncio
    async def test_gap_trend_stable(self, context_enricher, sample_overtake_event):
        """Test gap trend calculation for stable gap."""
        # Mock driver info
        context_enricher.cache.get_driver_info = Mock(return_value=Mock(driver_number=44))
        
        # Manually populate gap history: gap stable
        from collections import deque
        context_enricher._gap_history[44] = deque(maxlen=3)
        context_enricher._gap_history[44].append((8, 3.0))
        context_enricher._gap_history[44].append((9, 3.1))
        context_enricher._gap_history[44].append((10, 3.2))
        
        # Create context and calculate trend
        context = ContextData(event=sample_overtake_event, race_state=Mock())
        context.gap_to_leader = 3.2
        context_enricher._calculate_gap_trend(context, 44)
        
        # Verify trend
        assert context.gap_trend == "stable"


class TestDriverNumberExtraction:
    """Test driver number extraction from events."""
    
    def test_get_driver_number_from_overtake_event(
        self,
        context_enricher,
        sample_overtake_event
    ):
        """Test extracting driver number from overtake event."""
        # Mock cache to return driver info
        context_enricher.cache.get_driver_info = Mock(return_value=Mock(driver_number=44))
        
        driver_number = context_enricher._get_driver_number_from_event(sample_overtake_event)
        
        assert driver_number == 44
        context_enricher.cache.get_driver_info.assert_called_once_with("Hamilton")
    
    def test_get_driver_number_from_pit_event(
        self,
        context_enricher,
        sample_pit_event
    ):
        """Test extracting driver number from pit stop event."""
        # Mock cache to return driver info
        context_enricher.cache.get_driver_info = Mock(return_value=Mock(driver_number=44))
        
        driver_number = context_enricher._get_driver_number_from_event(sample_pit_event)
        
        assert driver_number == 44
        context_enricher.cache.get_driver_info.assert_called_once_with("Hamilton")
    
    def test_get_driver_number_unknown_driver(
        self,
        context_enricher,
        sample_overtake_event
    ):
        """Test extracting driver number for unknown driver."""
        # Mock cache to return None
        context_enricher.cache.get_driver_info = Mock(return_value=None)
        
        driver_number = context_enricher._get_driver_number_from_event(sample_overtake_event)
        
        assert driver_number is None


class TestConcurrentFetching:
    """Test concurrent data fetching."""
    
    @pytest.mark.asyncio
    async def test_concurrent_fetching_performance(
        self,
        context_enricher,
        sample_overtake_event
    ):
        """Test that concurrent fetching is faster than sequential."""
        # Mock driver info
        context_enricher.cache.get_driver_info = Mock(return_value=Mock(driver_number=44))
        
        # Mock fetch methods with delays
        async def slow_fetch(delay=0.05):
            await asyncio.sleep(delay)
            return {"data": "value"}
        
        context_enricher._fetch_telemetry_safe = AsyncMock(side_effect=lambda *args: slow_fetch())
        context_enricher._fetch_gaps_safe = AsyncMock(side_effect=lambda *args: slow_fetch())
        context_enricher._fetch_lap_data_safe = AsyncMock(side_effect=lambda *args: slow_fetch())
        context_enricher._fetch_tire_data_safe = AsyncMock(side_effect=lambda *args: slow_fetch())
        context_enricher._fetch_weather_safe = AsyncMock(side_effect=lambda *args: slow_fetch())
        context_enricher._fetch_pit_data_safe = AsyncMock(side_effect=lambda *args: slow_fetch())
        
        # Enrich context
        import time
        start = time.time()
        context = await context_enricher.enrich_context(sample_overtake_event)
        elapsed = time.time() - start
        
        # With 6 fetches at 50ms each:
        # - Sequential would take ~300ms
        # - Concurrent should take ~50ms (plus overhead)
        # We'll check it's significantly faster than sequential
        assert elapsed < 0.15  # Should be much less than 300ms
        assert context.enrichment_time_ms < 150


class TestCleanup:
    """Test cleanup methods."""
    
    @pytest.mark.asyncio
    async def test_close(self, context_enricher):
        """Test closing the context enricher."""
        # Mock the fetcher close method
        context_enricher.fetcher.close = AsyncMock()
        
        await context_enricher.close()
        
        context_enricher.fetcher.close.assert_called_once()
    
    def test_clear_gap_history(self, context_enricher):
        """Test clearing gap history."""
        # Add some gap history
        from collections import deque
        context_enricher._gap_history[44] = deque([(1, 5.0), (2, 4.5)])
        context_enricher._gap_history[33] = deque([(1, 3.0), (2, 3.2)])
        
        # Clear history
        context_enricher.clear_gap_history()
        
        # Verify cleared
        assert len(context_enricher._gap_history) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
