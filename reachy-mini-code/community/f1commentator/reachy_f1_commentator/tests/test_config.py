"""Tests for configuration management."""

import pytest
import json
import tempfile
import os
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import Config, validate_config, load_config, save_config


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_valid_config(self):
        """Test that a valid configuration passes validation."""
        config = Config(
            openf1_api_key="test_key",
            elevenlabs_api_key="test_key",
            elevenlabs_voice_id="test_voice"
        )
        errors = validate_config(config)
        assert len(errors) == 0
    
    def test_missing_required_fields_live_mode(self):
        """Test that missing required fields are caught in live mode."""
        config = Config(replay_mode=False)
        errors = validate_config(config)
        assert len(errors) > 0
        # OpenF1 API key is optional (historical data doesn't need authentication)
        # But ElevenLabs credentials are required
        assert any("elevenlabs_api_key" in error for error in errors)
        assert any("elevenlabs_voice_id" in error for error in errors)
    
    def test_invalid_polling_interval(self):
        """Test that invalid polling intervals are caught."""
        config = Config(
            openf1_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
            position_poll_interval=-1.0
        )
        errors = validate_config(config)
        assert any("position_poll_interval" in error for error in errors)
    
    def test_invalid_audio_volume(self):
        """Test that invalid audio volume is caught."""
        config = Config(
            openf1_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
            audio_volume=1.5
        )
        errors = validate_config(config)
        assert any("audio_volume" in error for error in errors)
    
    def test_invalid_movement_speed(self):
        """Test that invalid movement speed is caught."""
        config = Config(
            openf1_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
            movement_speed=50.0
        )
        errors = validate_config(config)
        assert any("movement_speed" in error for error in errors)
    
    def test_replay_mode_validation(self):
        """Test that replay mode requires race_id."""
        config = Config(
            replay_mode=True,
            replay_race_id=None
        )
        errors = validate_config(config)
        assert any("replay_race_id" in error for error in errors)
    
    # Enhanced configuration validation tests
    
    def test_valid_enhanced_config(self):
        """Test that a valid enhanced configuration passes validation."""
        config = Config(
            openf1_api_key="test_key",
            elevenlabs_api_key="test_key",
            elevenlabs_voice_id="test_voice",
            enhanced_mode=True
        )
        errors = validate_config(config)
        assert len(errors) == 0
    
    def test_invalid_context_enrichment_timeout(self):
        """Test that invalid context enrichment timeout is caught."""
        config = Config(
            openf1_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
            enhanced_mode=True,
            context_enrichment_timeout_ms=-100
        )
        errors = validate_config(config)
        assert any("context_enrichment_timeout_ms" in error for error in errors)
    
    def test_context_enrichment_timeout_too_high(self):
        """Test that context enrichment timeout exceeding 5000ms is caught."""
        config = Config(
            openf1_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
            enhanced_mode=True,
            context_enrichment_timeout_ms=6000
        )
        errors = validate_config(config)
        assert any("context_enrichment_timeout_ms" in error for error in errors)
    
    def test_invalid_cache_duration(self):
        """Test that invalid cache durations are caught."""
        config = Config(
            openf1_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
            enhanced_mode=True,
            cache_duration_weather=-10
        )
        errors = validate_config(config)
        assert any("cache_duration_weather" in error for error in errors)
    
    def test_invalid_significance_threshold(self):
        """Test that invalid significance threshold is caught."""
        config = Config(
            openf1_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
            enhanced_mode=True,
            min_significance_threshold=150
        )
        errors = validate_config(config)
        assert any("min_significance_threshold" in error for error in errors)
    
    def test_negative_bonus_values(self):
        """Test that negative bonus values are caught."""
        config = Config(
            openf1_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
            enhanced_mode=True,
            championship_contender_bonus=-5
        )
        errors = validate_config(config)
        assert any("championship_contender_bonus" in error for error in errors)
    
    def test_invalid_excitement_thresholds(self):
        """Test that invalid excitement thresholds are caught."""
        config = Config(
            openf1_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
            enhanced_mode=True,
            excitement_threshold_calm=150
        )
        errors = validate_config(config)
        assert any("excitement_threshold_calm" in error for error in errors)
    
    def test_excitement_thresholds_not_ascending(self):
        """Test that excitement thresholds must be in ascending order."""
        config = Config(
            openf1_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
            enhanced_mode=True,
            excitement_threshold_calm=50,
            excitement_threshold_moderate=30  # Lower than calm
        )
        errors = validate_config(config)
        assert any("ascending order" in error for error in errors)
    
    def test_negative_perspective_weights(self):
        """Test that negative perspective weights are caught."""
        config = Config(
            openf1_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
            enhanced_mode=True,
            perspective_weight_technical=-0.1
        )
        errors = validate_config(config)
        assert any("perspective_weight_technical" in error for error in errors)
    
    def test_perspective_weights_sum_validation(self):
        """Test that perspective weights must sum to approximately 1.0."""
        config = Config(
            openf1_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
            enhanced_mode=True,
            perspective_weight_technical=0.5,
            perspective_weight_strategic=0.5,
            perspective_weight_dramatic=0.5,
            perspective_weight_positional=0.5,
            perspective_weight_historical=0.5
        )
        errors = validate_config(config)
        assert any("sum to approximately 1.0" in error for error in errors)
    
    def test_invalid_template_repetition_window(self):
        """Test that invalid template repetition window is caught."""
        config = Config(
            openf1_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
            enhanced_mode=True,
            template_repetition_window=0
        )
        errors = validate_config(config)
        assert any("template_repetition_window" in error for error in errors)
    
    def test_invalid_max_sentence_length(self):
        """Test that invalid max sentence length is caught."""
        config = Config(
            openf1_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
            enhanced_mode=True,
            max_sentence_length=5  # Too short
        )
        errors = validate_config(config)
        assert any("max_sentence_length" in error for error in errors)
    
    def test_invalid_narrative_tracking_settings(self):
        """Test that invalid narrative tracking settings are caught."""
        config = Config(
            openf1_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
            enhanced_mode=True,
            max_narrative_threads=0
        )
        errors = validate_config(config)
        assert any("max_narrative_threads" in error for error in errors)
    
    def test_invalid_battle_gap_threshold(self):
        """Test that invalid battle gap threshold is caught."""
        config = Config(
            openf1_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
            enhanced_mode=True,
            battle_gap_threshold=-1.0
        )
        errors = validate_config(config)
        assert any("battle_gap_threshold" in error for error in errors)
    
    def test_invalid_performance_settings(self):
        """Test that invalid performance settings are caught."""
        config = Config(
            openf1_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
            enhanced_mode=True,
            max_cpu_percent=150.0
        )
        errors = validate_config(config)
        assert any("max_cpu_percent" in error for error in errors)
    
    def test_enhanced_mode_disabled_skips_validation(self):
        """Test that enhanced mode validation is skipped when disabled."""
        config = Config(
            openf1_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
            enhanced_mode=False,
            context_enrichment_timeout_ms=-100  # Invalid but should be ignored
        )
        errors = validate_config(config)
        # Should not have errors about enhanced config
        assert not any("context_enrichment_timeout_ms" in error for error in errors)


class TestConfigLoading:
    """Test configuration loading and saving."""
    
    def test_load_default_config(self):
        """Test loading default configuration when file doesn't exist."""
        config = load_config("nonexistent_config.json")
        assert isinstance(config, Config)
        assert config.openf1_base_url == "https://api.openf1.org/v1"
    
    def test_save_and_load_config(self):
        """Test saving and loading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "test_config.json")
            
            # Create and save config
            original_config = Config(
                openf1_api_key="test_key",
                elevenlabs_api_key="test_key",
                elevenlabs_voice_id="test_voice",
                audio_volume=0.5
            )
            save_config(original_config, config_path)
            
            # Load config
            loaded_config = load_config(config_path)
            
            assert loaded_config.openf1_api_key == "test_key"
            assert loaded_config.audio_volume == 0.5
    
    def test_load_invalid_json(self):
        """Test loading invalid JSON falls back to defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "invalid.json")
            
            # Write invalid JSON
            with open(config_path, 'w') as f:
                f.write("{ invalid json }")
            
            # Should not crash, should use defaults
            config = load_config(config_path)
            assert isinstance(config, Config)
    
    def test_environment_variable_override(self):
        """Test that environment variables override file config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "test_config.json")
            
            # Save config with one value
            original_config = Config(openf1_api_key="file_key")
            save_config(original_config, config_path)
            
            # Set environment variable
            os.environ['OPENF1_API_KEY'] = "env_key"
            
            try:
                # Load config - should use env var
                loaded_config = load_config(config_path)
                assert loaded_config.openf1_api_key == "env_key"
            finally:
                # Clean up
                del os.environ['OPENF1_API_KEY']
    
    def test_save_and_load_enhanced_config(self):
        """Test saving and loading enhanced configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "test_config.json")
            
            # Create and save enhanced config
            original_config = Config(
                openf1_api_key="test_key",
                elevenlabs_api_key="test_key",
                elevenlabs_voice_id="test_voice",
                enhanced_mode=True,
                context_enrichment_timeout_ms=600,
                min_significance_threshold=60,
                max_sentence_length=50
            )
            save_config(original_config, config_path)
            
            # Load config
            loaded_config = load_config(config_path)
            
            assert loaded_config.enhanced_mode is True
            assert loaded_config.context_enrichment_timeout_ms == 600
            assert loaded_config.min_significance_threshold == 60
            assert loaded_config.max_sentence_length == 50
    
    def test_invalid_enhanced_config_uses_defaults(self):
        """Test that invalid enhanced config values fall back to defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "test_config.json")
            
            # Create config with invalid values
            config_data = {
                "openf1_api_key": "test",
                "elevenlabs_api_key": "test",
                "elevenlabs_voice_id": "test",
                "enhanced_mode": True,
                "context_enrichment_timeout_ms": -100,  # Invalid
                "min_significance_threshold": 150,  # Invalid
                "max_sentence_length": 5  # Invalid
            }
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f)
            
            # Load config - should use defaults for invalid values
            loaded_config = load_config(config_path)
            
            assert loaded_config.context_enrichment_timeout_ms == 500  # Default
            assert loaded_config.min_significance_threshold == 50  # Default
            assert loaded_config.max_sentence_length == 40  # Default
