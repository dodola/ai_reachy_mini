"""
Data models for Reachy F1 Commentator app.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class WebUIConfiguration:
    """Configuration from web UI."""
    mode: str  # 'quick_demo' or 'full_race'
    session_key: Optional[int] = None
    commentary_mode: str = 'enhanced'  # 'basic' or 'enhanced'
    playback_speed: int = 10  # 1, 5, 10, or 20
    elevenlabs_api_key: str = ''
    elevenlabs_voice_id: str = 'HSSEHuB5EziJgTfCVmC6'
    
    def validate(self) -> tuple[bool, str]:
        """Validate configuration."""
        if self.mode not in ['quick_demo', 'full_race']:
            return False, "Invalid mode"
        
        if self.mode == 'full_race' and not self.session_key:
            return False, "Session key required for full race mode"
        
        if self.commentary_mode not in ['basic', 'enhanced']:
            return False, "Invalid commentary mode"
        
        if self.playback_speed not in [1, 5, 10, 20]:
            return False, "Invalid playback speed"
        
        return True, ""


@dataclass
class RaceMetadata:
    """Metadata for a race session."""
    session_key: int
    year: int
    date: str  # ISO format
    country: str
    circuit: str
    name: str  # e.g., "Bahrain Grand Prix"
    
    @classmethod
    def from_openf1_session(cls, session: dict) -> 'RaceMetadata':
        """Create from OpenF1 API session data."""
        return cls(
            session_key=session['session_key'],
            year=session.get('year', 0),
            date=session.get('date_start', ''),
            country=session.get('country_name', ''),
            circuit=session.get('circuit_short_name', ''),
            name=f"{session.get('country_name', '')} Grand Prix"
        )


@dataclass
class PlaybackStatus:
    """Current playback status."""
    state: str  # 'idle', 'loading', 'playing', 'stopped'
    current_lap: int = 0
    total_laps: int = 0
    elapsed_time: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            'state': self.state,
            'current_lap': self.current_lap,
            'total_laps': self.total_laps,
            'elapsed_time': self._format_time(self.elapsed_time)
        }
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
