"""
Unit tests for ContextFetcher async methods.

Tests the async context fetching methods for telemetry, gaps, lap data,
tire data, weather, and pit data with timeout and error handling.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from reachy_f1_commentator.src.context_fetcher import ContextFetcher
from reachy_f1_commentator.src.data_ingestion import OpenF1Client


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_openf1_client():
    """Create a mock OpenF1 client."""
    client = Mock(spec=OpenF1Client)
    client.base_url = "https://api.openf1.org/v1"
    return client


@pytest.fixture
def context_fetcher(mock_openf1_client):
    """Create a ContextFetcher instance."""
    return ContextFetcher(mock_openf1_client, timeout_ms=500)


def create_mock_response(status, json_data):
    """Helper to create a properly mocked aiohttp response."""
    mock_response = AsyncMock()
    mock_response.status = status
    mock_response.json = AsyncMock(return_value=json_data)
    
    mock_cm = Mock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    
    return mock_cm


# ============================================================================
# Telemetry Tests
# ============================================================================

@pytest.mark.asyncio
async def test_fetch_telemetry_success(context_fetcher):
    """Test successful telemetry fetch."""
    mock_response_data = [{
        "speed": 315,
        "throttle": 100,
        "brake": 0,
        "drs": 12,  # DRS open
        "rpm": 11000,
        "n_gear": 8
    }]
    
    with patch.object(context_fetcher, '_ensure_session') as mock_ensure_session:
        mock_cm = create_mock_response(200, mock_response_data)
        
        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_cm)
        
        mock_ensure_session.return_value = mock_session
        
        result = await context_fetcher.fetch_telemetry(
            driver_number=44,
            session_key=9197
        )
        
        assert result["speed"] == 315
        assert result["throttle"] == 100
        assert result["brake"] == 0
        assert result["drs_active"] is True
        assert result["rpm"] == 11000
        assert result["gear"] == 8


@pytest.mark.asyncio
async def test_fetch_telemetry_timeout(context_fetcher):
    """Test telemetry fetch with timeout."""
    with patch.object(context_fetcher, '_ensure_session') as mock_ensure_session:
        mock_session = Mock()
        mock_session.get.side_effect = asyncio.TimeoutError()
        
        mock_ensure_session.return_value = mock_session
        
        result = await context_fetcher.fetch_telemetry(
            driver_number=44,
            session_key=9197
        )
        
        assert result == {}


@pytest.mark.asyncio
async def test_fetch_telemetry_http_error(context_fetcher):
    """Test telemetry fetch with HTTP error."""
    with patch.object(context_fetcher, '_ensure_session') as mock_ensure_session:
        mock_cm = create_mock_response(500, {})
        
        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_cm)
        
        mock_ensure_session.return_value = mock_session
        
        result = await context_fetcher.fetch_telemetry(
            driver_number=44,
            session_key=9197
        )
        
        assert result == {}


# ============================================================================
# Gap Tests
# ============================================================================

@pytest.mark.asyncio
async def test_fetch_gaps_success(context_fetcher):
    """Test successful gap fetch."""
    mock_response_data = [{
        "gap_to_leader": "+5.234",
        "interval": "+1.234"
    }]
    
    with patch.object(context_fetcher, '_ensure_session') as mock_ensure_session:
        mock_cm = create_mock_response(200, mock_response_data)
        
        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_cm)
        
        mock_ensure_session.return_value = mock_session
        
        result = await context_fetcher.fetch_gaps(
            driver_number=44,
            session_key=9197
        )
        
        assert result["gap_to_leader"] == 5.234
        assert result["gap_to_ahead"] == 1.234


@pytest.mark.asyncio
async def test_fetch_gaps_timeout(context_fetcher):
    """Test gap fetch with timeout."""
    with patch.object(context_fetcher, '_ensure_session') as mock_ensure_session:
        mock_session = Mock()
        mock_session.get.side_effect = asyncio.TimeoutError()
        
        mock_ensure_session.return_value = mock_session
        
        result = await context_fetcher.fetch_gaps(
            driver_number=44,
            session_key=9197
        )
        
        assert result == {}


# ============================================================================
# Lap Data Tests
# ============================================================================

@pytest.mark.asyncio
async def test_fetch_lap_data_success(context_fetcher):
    """Test successful lap data fetch."""
    mock_response_data = [{
        "duration_sector_1": 25.123,
        "duration_sector_2": 38.456,
        "duration_sector_3": 28.789,
        "segments_sector_1": 2051,  # purple
        "segments_sector_2": 2049,  # green
        "segments_sector_3": 2048,  # yellow
        "st_speed": 315.5
    }]
    
    with patch.object(context_fetcher, '_ensure_session') as mock_ensure_session:
        mock_cm = create_mock_response(200, mock_response_data)
        
        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_cm)
        
        mock_ensure_session.return_value = mock_session
        
        result = await context_fetcher.fetch_lap_data(
            driver_number=44,
            session_key=9197
        )
        
        assert result["sector_1_time"] == 25.123
        assert result["sector_2_time"] == 38.456
        assert result["sector_3_time"] == 28.789
        assert result["sector_1_status"] == "purple"
        assert result["sector_2_status"] == "green"
        assert result["sector_3_status"] == "yellow"
        assert result["speed_trap"] == 315.5


# ============================================================================
# Tire Data Tests
# ============================================================================

@pytest.mark.asyncio
async def test_fetch_tire_data_success(context_fetcher):
    """Test successful tire data fetch."""
    mock_response_data = [
        {
            "stint_number": 1,
            "compound": "MEDIUM",
            "tyre_age_at_start": 0
        },
        {
            "stint_number": 2,
            "compound": "HARD",
            "tyre_age_at_start": 0
        }
    ]
    
    with patch.object(context_fetcher, '_ensure_session') as mock_ensure_session:
        mock_cm = create_mock_response(200, mock_response_data)
        
        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_cm)
        
        mock_ensure_session.return_value = mock_session
        
        result = await context_fetcher.fetch_tire_data(
            driver_number=44,
            session_key=9197
        )
        
        assert result["current_tire_compound"] == "HARD"
        assert result["previous_tire_compound"] == "MEDIUM"


# ============================================================================
# Weather Tests
# ============================================================================

@pytest.mark.asyncio
async def test_fetch_weather_success(context_fetcher):
    """Test successful weather fetch."""
    mock_response_data = [{
        "air_temperature": 28.5,
        "track_temperature": 42.3,
        "humidity": 65,
        "rainfall": 0,
        "wind_speed": 15,
        "wind_direction": 180
    }]
    
    with patch.object(context_fetcher, '_ensure_session') as mock_ensure_session:
        mock_cm = create_mock_response(200, mock_response_data)
        
        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_cm)
        
        mock_ensure_session.return_value = mock_session
        
        result = await context_fetcher.fetch_weather(
            session_key=9197
        )
        
        assert result["air_temp"] == 28.5
        assert result["track_temp"] == 42.3
        assert result["humidity"] == 65
        assert result["rainfall"] == 0
        assert result["wind_speed"] == 15
        assert result["wind_direction"] == 180


# ============================================================================
# Pit Data Tests
# ============================================================================

@pytest.mark.asyncio
async def test_fetch_pit_data_success(context_fetcher):
    """Test successful pit data fetch."""
    mock_response_data = [
        {
            "pit_duration": 2.3,
            "lap_time": 25.6
        },
        {
            "pit_duration": 2.5,
            "lap_time": 26.1
        }
    ]
    
    with patch.object(context_fetcher, '_ensure_session') as mock_ensure_session:
        mock_cm = create_mock_response(200, mock_response_data)
        
        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_cm)
        
        mock_ensure_session.return_value = mock_session
        
        result = await context_fetcher.fetch_pit_data(
            driver_number=44,
            session_key=9197
        )
        
        assert result["pit_duration"] == 2.5  # Latest pit stop
        assert result["pit_lane_time"] == 26.1
        assert result["pit_count"] == 2


# ============================================================================
# Session Management Tests
# ============================================================================

@pytest.mark.asyncio
async def test_session_creation(context_fetcher):
    """Test that session is created on first use."""
    assert context_fetcher._session is None
    
    session = await context_fetcher._ensure_session()
    
    assert session is not None
    assert context_fetcher._session is not None
    
    await context_fetcher.close()


@pytest.mark.asyncio
async def test_session_reuse(context_fetcher):
    """Test that session is reused across calls."""
    session1 = await context_fetcher._ensure_session()
    session2 = await context_fetcher._ensure_session()
    
    assert session1 is session2
    
    await context_fetcher.close()


@pytest.mark.asyncio
async def test_close_session(context_fetcher):
    """Test session closure."""
    await context_fetcher._ensure_session()
    assert context_fetcher._session is not None
    
    await context_fetcher.close()
    
    # Session should be closed but still exist
    assert context_fetcher._session is not None
