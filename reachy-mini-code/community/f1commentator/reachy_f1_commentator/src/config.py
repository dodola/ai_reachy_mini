"""Configuration management for F1 Commentary Robot.

This module provides configuration schema, validation, and loading functionality.
Validates: Requirements 13.1, 13.2, 13.3, 13.4
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import json


logger = logging.getLogger(__name__)


@dataclass
class Config:
    """System configuration schema."""
    
    # OpenF1 API
    openf1_api_key: str = ""
    openf1_base_url: str = "https://api.openf1.org/v1"
    
    # ElevenLabs
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    
    # AI Enhancement (optional)
    ai_enabled: bool = False
    ai_provider: str = "openai"  # "openai", "huggingface", "none"
    ai_api_key: Optional[str] = None
    ai_model: str = "gpt-3.5-turbo"
    
    # Polling intervals (seconds)
    position_poll_interval: float = 1.0
    laps_poll_interval: float = 2.0
    pit_poll_interval: float = 1.0
    race_control_poll_interval: float = 1.0
    
    # Event queue
    max_queue_size: int = 10
    
    # Audio
    audio_volume: float = 0.8
    
    # Motion
    movement_speed: float = 30.0  # degrees/second
    enable_movements: bool = True
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/f1_commentary.log"
    
    # Mode
    replay_mode: bool = False
    replay_race_id: Optional[int] = None  # Numeric session_key (e.g., 9197 for 2023 Abu Dhabi GP)
    replay_speed: float = 1.0
    replay_skip_large_gaps: bool = True  # Skip time gaps > 60s in replay (set False for real-time)
    
    # Enhanced Commentary Mode (Requirement 17.1)
    enhanced_mode: bool = True  # Enable enhanced organic commentary features
    
    # Context Enrichment Configuration (Requirement 17.3)
    context_enrichment_timeout_ms: int = 500
    enable_telemetry: bool = True
    enable_weather: bool = True
    enable_championship: bool = True
    cache_duration_driver_info: int = 3600  # seconds (1 hour)
    cache_duration_championship: int = 3600  # seconds (1 hour)
    cache_duration_weather: int = 30  # seconds
    cache_duration_gaps: int = 4  # seconds
    cache_duration_tires: int = 10  # seconds
    
    # Event Prioritization Configuration (Requirement 17.1)
    min_significance_threshold: int = 50
    championship_contender_bonus: int = 20
    narrative_bonus: int = 15
    close_gap_bonus: int = 10
    fresh_tires_bonus: int = 10
    drs_available_bonus: int = 5
    
    # Style Management Configuration (Requirement 17.1)
    excitement_threshold_calm: int = 30
    excitement_threshold_moderate: int = 50
    excitement_threshold_engaged: int = 70
    excitement_threshold_excited: int = 85
    perspective_weight_technical: float = 0.25
    perspective_weight_strategic: float = 0.25
    perspective_weight_dramatic: float = 0.25
    perspective_weight_positional: float = 0.15
    perspective_weight_historical: float = 0.10
    
    # Template Selection Configuration (Requirement 17.2, 17.5)
    template_file: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        "config", 
        "enhanced_templates.json"
    ))
    template_repetition_window: int = 10
    max_sentence_length: int = 40
    
    # Narrative Tracking Configuration (Requirement 17.4)
    max_narrative_threads: int = 5
    battle_gap_threshold: float = 2.0
    battle_lap_threshold: int = 3
    comeback_position_threshold: int = 3
    comeback_lap_window: int = 10
    
    # Performance Configuration (Requirement 17.3, 17.6)
    max_generation_time_ms: int = 2500
    max_cpu_percent: float = 75.0
    max_memory_increase_mb: int = 500


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


def validate_config(config: Config) -> list[str]:
    """Validate configuration values.
    
    Args:
        config: Configuration object to validate
        
    Returns:
        List of validation error messages (empty if valid)
        
    Validates: Requirements 13.3, 17.7
    """
    errors = []
    
    # Validate required fields for live mode
    # Note: OpenF1 API key is NOT required for historical data (replay mode)
    # It's only needed for real-time data access (paid account)
    if not config.replay_mode:
        # OpenF1 API key is optional - historical data doesn't need authentication
        if config.openf1_api_key:
            logger.info("OpenF1 API key provided - can be used for real-time data")
        else:
            logger.info("No OpenF1 API key - using historical data only (no authentication required)")
        
        if not config.elevenlabs_api_key:
            errors.append("elevenlabs_api_key is required")
        if not config.elevenlabs_voice_id:
            errors.append("elevenlabs_voice_id is required")
    
    # Validate AI configuration
    if config.ai_enabled:
        if config.ai_provider not in ["openai", "huggingface", "none"]:
            errors.append(f"ai_provider must be 'openai', 'huggingface', or 'none', got '{config.ai_provider}'")
        if config.ai_provider != "none" and not config.ai_api_key:
            errors.append(f"ai_api_key is required when ai_provider is '{config.ai_provider}'")
    
    # Validate polling intervals
    if config.position_poll_interval <= 0:
        errors.append(f"position_poll_interval must be positive, got {config.position_poll_interval}")
    if config.laps_poll_interval <= 0:
        errors.append(f"laps_poll_interval must be positive, got {config.laps_poll_interval}")
    if config.pit_poll_interval <= 0:
        errors.append(f"pit_poll_interval must be positive, got {config.pit_poll_interval}")
    if config.race_control_poll_interval <= 0:
        errors.append(f"race_control_poll_interval must be positive, got {config.race_control_poll_interval}")
    
    # Validate queue size
    if config.max_queue_size <= 0:
        errors.append(f"max_queue_size must be positive, got {config.max_queue_size}")
    
    # Validate audio volume
    if not 0.0 <= config.audio_volume <= 1.0:
        errors.append(f"audio_volume must be between 0.0 and 1.0, got {config.audio_volume}")
    
    # Validate movement speed
    if config.movement_speed <= 0:
        errors.append(f"movement_speed must be positive, got {config.movement_speed}")
    if config.movement_speed > 30.0:
        errors.append(f"movement_speed must not exceed 30.0 degrees/second, got {config.movement_speed}")
    
    # Validate log level
    valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if config.log_level.upper() not in valid_log_levels:
        errors.append(f"log_level must be one of {valid_log_levels}, got '{config.log_level}'")
    
    # Validate replay mode settings
    if config.replay_mode:
        if not config.replay_race_id:
            errors.append("replay_race_id is required when replay_mode is enabled")
        if config.replay_speed <= 0:
            errors.append(f"replay_speed must be positive, got {config.replay_speed}")
    
    # Validate enhanced commentary configuration (Requirement 17.7)
    if config.enhanced_mode:
        # Validate context enrichment settings
        if config.context_enrichment_timeout_ms <= 0:
            errors.append(f"context_enrichment_timeout_ms must be positive, got {config.context_enrichment_timeout_ms}")
        if config.context_enrichment_timeout_ms > 5000:
            errors.append(f"context_enrichment_timeout_ms should not exceed 5000ms, got {config.context_enrichment_timeout_ms}")
        
        # Validate cache durations
        if config.cache_duration_driver_info <= 0:
            errors.append(f"cache_duration_driver_info must be positive, got {config.cache_duration_driver_info}")
        if config.cache_duration_championship <= 0:
            errors.append(f"cache_duration_championship must be positive, got {config.cache_duration_championship}")
        if config.cache_duration_weather <= 0:
            errors.append(f"cache_duration_weather must be positive, got {config.cache_duration_weather}")
        if config.cache_duration_gaps <= 0:
            errors.append(f"cache_duration_gaps must be positive, got {config.cache_duration_gaps}")
        if config.cache_duration_tires <= 0:
            errors.append(f"cache_duration_tires must be positive, got {config.cache_duration_tires}")
        
        # Validate event prioritization settings
        if not 0 <= config.min_significance_threshold <= 100:
            errors.append(f"min_significance_threshold must be between 0 and 100, got {config.min_significance_threshold}")
        if config.championship_contender_bonus < 0:
            errors.append(f"championship_contender_bonus must be non-negative, got {config.championship_contender_bonus}")
        if config.narrative_bonus < 0:
            errors.append(f"narrative_bonus must be non-negative, got {config.narrative_bonus}")
        if config.close_gap_bonus < 0:
            errors.append(f"close_gap_bonus must be non-negative, got {config.close_gap_bonus}")
        if config.fresh_tires_bonus < 0:
            errors.append(f"fresh_tires_bonus must be non-negative, got {config.fresh_tires_bonus}")
        if config.drs_available_bonus < 0:
            errors.append(f"drs_available_bonus must be non-negative, got {config.drs_available_bonus}")
        
        # Validate style management settings
        if not 0 <= config.excitement_threshold_calm <= 100:
            errors.append(f"excitement_threshold_calm must be between 0 and 100, got {config.excitement_threshold_calm}")
        if not 0 <= config.excitement_threshold_moderate <= 100:
            errors.append(f"excitement_threshold_moderate must be between 0 and 100, got {config.excitement_threshold_moderate}")
        if not 0 <= config.excitement_threshold_engaged <= 100:
            errors.append(f"excitement_threshold_engaged must be between 0 and 100, got {config.excitement_threshold_engaged}")
        if not 0 <= config.excitement_threshold_excited <= 100:
            errors.append(f"excitement_threshold_excited must be between 0 and 100, got {config.excitement_threshold_excited}")
        
        # Validate excitement thresholds are in ascending order
        if not (config.excitement_threshold_calm < config.excitement_threshold_moderate < 
                config.excitement_threshold_engaged < config.excitement_threshold_excited):
            errors.append("excitement thresholds must be in ascending order: calm < moderate < engaged < excited")
        
        # Validate perspective weights
        if config.perspective_weight_technical < 0:
            errors.append(f"perspective_weight_technical must be non-negative, got {config.perspective_weight_technical}")
        if config.perspective_weight_strategic < 0:
            errors.append(f"perspective_weight_strategic must be non-negative, got {config.perspective_weight_strategic}")
        if config.perspective_weight_dramatic < 0:
            errors.append(f"perspective_weight_dramatic must be non-negative, got {config.perspective_weight_dramatic}")
        if config.perspective_weight_positional < 0:
            errors.append(f"perspective_weight_positional must be non-negative, got {config.perspective_weight_positional}")
        if config.perspective_weight_historical < 0:
            errors.append(f"perspective_weight_historical must be non-negative, got {config.perspective_weight_historical}")
        
        # Validate perspective weights sum to approximately 1.0
        total_weight = (config.perspective_weight_technical + config.perspective_weight_strategic + 
                       config.perspective_weight_dramatic + config.perspective_weight_positional + 
                       config.perspective_weight_historical)
        if not 0.95 <= total_weight <= 1.05:
            errors.append(f"perspective weights should sum to approximately 1.0, got {total_weight:.2f}")
        
        # Validate template selection settings
        if config.template_repetition_window <= 0:
            errors.append(f"template_repetition_window must be positive, got {config.template_repetition_window}")
        if config.max_sentence_length <= 0:
            errors.append(f"max_sentence_length must be positive, got {config.max_sentence_length}")
        if config.max_sentence_length < 10:
            errors.append(f"max_sentence_length should be at least 10 words, got {config.max_sentence_length}")
        
        # Validate narrative tracking settings
        if config.max_narrative_threads <= 0:
            errors.append(f"max_narrative_threads must be positive, got {config.max_narrative_threads}")
        if config.battle_gap_threshold <= 0:
            errors.append(f"battle_gap_threshold must be positive, got {config.battle_gap_threshold}")
        if config.battle_lap_threshold <= 0:
            errors.append(f"battle_lap_threshold must be positive, got {config.battle_lap_threshold}")
        if config.comeback_position_threshold <= 0:
            errors.append(f"comeback_position_threshold must be positive, got {config.comeback_position_threshold}")
        if config.comeback_lap_window <= 0:
            errors.append(f"comeback_lap_window must be positive, got {config.comeback_lap_window}")
        
        # Validate performance settings
        if config.max_generation_time_ms <= 0:
            errors.append(f"max_generation_time_ms must be positive, got {config.max_generation_time_ms}")
        if config.max_cpu_percent <= 0 or config.max_cpu_percent > 100:
            errors.append(f"max_cpu_percent must be between 0 and 100, got {config.max_cpu_percent}")
        if config.max_memory_increase_mb <= 0:
            errors.append(f"max_memory_increase_mb must be positive, got {config.max_memory_increase_mb}")
    
    return errors


def load_config(config_path: str = "config/config.json") -> Config:
    """Load configuration from file with validation and error handling.
    
    Args:
        config_path: Path to configuration JSON file
        
    Returns:
        Validated Config object
        
    Validates: Requirements 13.1, 13.2, 13.4
    """
    config = Config()
    
    # Try to load from file
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
                
            # Update config with loaded values
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                else:
                    logger.warning(f"Unknown configuration key: {key}")
                    
            logger.info(f"Configuration loaded from {config_path}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse configuration file {config_path}: {e}")
            logger.warning("Using default configuration values")
        except Exception as e:
            logger.error(f"Failed to load configuration file {config_path}: {e}")
            logger.warning("Using default configuration values")
    else:
        logger.warning(f"Configuration file {config_path} not found, using defaults")
    
    # Load from environment variables (override file config)
    env_mappings = {
        'OPENF1_API_KEY': 'openf1_api_key',
        'ELEVENLABS_API_KEY': 'elevenlabs_api_key',
        'ELEVENLABS_VOICE_ID': 'elevenlabs_voice_id',
        'AI_API_KEY': 'ai_api_key',
    }
    
    for env_var, config_key in env_mappings.items():
        value = os.getenv(env_var)
        if value:
            setattr(config, config_key, value)
            logger.debug(f"Loaded {config_key} from environment variable {env_var}")
    
    # Validate configuration
    validation_errors = validate_config(config)
    
    if validation_errors:
        # Log all validation errors
        for error in validation_errors:
            logger.error(f"Configuration validation error: {error}")
        
        # Use defaults for invalid values (Requirements 13.4, 17.8)
        logger.warning("Some configuration values are invalid, using defaults where applicable")
        
        # Apply safe defaults for critical invalid values
        if config.audio_volume < 0.0 or config.audio_volume > 1.0:
            config.audio_volume = 0.8
            logger.info("Reset audio_volume to default: 0.8")
        
        if config.movement_speed <= 0 or config.movement_speed > 30.0:
            config.movement_speed = 30.0
            logger.info("Reset movement_speed to default: 30.0")
        
        if config.max_queue_size <= 0:
            config.max_queue_size = 10
            logger.info("Reset max_queue_size to default: 10")
        
        # Apply safe defaults for enhanced commentary configuration
        if config.enhanced_mode:
            if config.context_enrichment_timeout_ms <= 0 or config.context_enrichment_timeout_ms > 5000:
                config.context_enrichment_timeout_ms = 500
                logger.info("Reset context_enrichment_timeout_ms to default: 500")
            
            if not 0 <= config.min_significance_threshold <= 100:
                config.min_significance_threshold = 50
                logger.info("Reset min_significance_threshold to default: 50")
            
            if config.max_sentence_length <= 0 or config.max_sentence_length < 10:
                config.max_sentence_length = 40
                logger.info("Reset max_sentence_length to default: 40")
            
            if config.template_repetition_window <= 0:
                config.template_repetition_window = 10
                logger.info("Reset template_repetition_window to default: 10")
            
            if config.max_narrative_threads <= 0:
                config.max_narrative_threads = 5
                logger.info("Reset max_narrative_threads to default: 5")
            
            if config.max_generation_time_ms <= 0:
                config.max_generation_time_ms = 2500
                logger.info("Reset max_generation_time_ms to default: 2500")
            
            if config.max_cpu_percent <= 0 or config.max_cpu_percent > 100:
                config.max_cpu_percent = 75.0
                logger.info("Reset max_cpu_percent to default: 75.0")
            
            if config.max_memory_increase_mb <= 0:
                config.max_memory_increase_mb = 500
                logger.info("Reset max_memory_increase_mb to default: 500")
    
    return config


def save_config(config: Config, config_path: str = "config/config.json") -> None:
    """Save configuration to file.
    
    Args:
        config: Configuration object to save
        config_path: Path to save configuration JSON file
    """
    # Ensure config directory exists
    Path(config_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Convert config to dict
    config_dict = {
        key: value for key, value in config.__dict__.items()
        if not key.startswith('_')
    }
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
        logger.info(f"Configuration saved to {config_path}")
    except Exception as e:
        logger.error(f"Failed to save configuration to {config_path}: {e}")
