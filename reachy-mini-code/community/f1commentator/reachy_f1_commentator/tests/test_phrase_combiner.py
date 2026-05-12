"""
Unit tests for PhraseCombiner.

Tests phrase combination, placeholder resolution, validation, and truncation.
"""

import pytest
from unittest.mock import Mock, MagicMock

from reachy_f1_commentator.src.phrase_combiner import PhraseCombiner
from reachy_f1_commentator.src.placeholder_resolver import PlaceholderResolver
from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.enhanced_models import (
    ContextData, Template, RaceState, ExcitementLevel,
    CommentaryPerspective
)
from reachy_f1_commentator.src.models import EventType
from datetime import datetime
from unittest.mock import Mock


@pytest.fixture
def config():
    """Create test configuration."""
    return Config(
        openf1_api_key="test",
        elevenlabs_api_key="test",
        elevenlabs_voice_id="test",
        max_sentence_length=40
    )


@pytest.fixture
def mock_resolver():
    """Create mock placeholder resolver."""
    resolver = Mock(spec=PlaceholderResolver)
    
    # Default resolution behavior
    def resolve_side_effect(placeholder, context):
        resolutions = {
            "driver1": "Hamilton",
            "driver2": "Verstappen",
            "position": "P1",
            "gap": "0.8 seconds",
            "tire_compound": "soft",
            "tire_age": "15 laps old",
            "drs_status": "with DRS",
            "speed": "315 kilometers per hour",
            "pronoun": "he",
            "team1": "Mercedes",
            "gap_trend": "closing in"
        }
        return resolutions.get(placeholder)
    
    resolver.resolve.side_effect = resolve_side_effect
    return resolver


@pytest.fixture
def phrase_combiner(config, mock_resolver):
    """Create PhraseCombiner instance."""
    return PhraseCombiner(config, mock_resolver)


@pytest.fixture
def sample_event():
    """Create sample race event."""
    event = Mock()
    event.driver = "Hamilton"
    event.overtaken_driver = "Verstappen"
    event.lap_number = 25
    event.timestamp = datetime.now()
    return event


@pytest.fixture
def sample_context(sample_event):
    """Create sample context data."""
    return ContextData(
        event=sample_event,
        race_state=RaceState(),
        gap_to_leader=0.8,
        drs_active=True,
        current_tire_compound="soft",
        current_tire_age=15,
        position_after=1
    )


@pytest.fixture
def sample_template():
    """Create sample template."""
    return Template(
        template_id="test_001",
        event_type="overtake",
        excitement_level="excited",
        perspective="dramatic",
        template_text="{driver1} makes the move on {driver2} into {position}!",
        required_placeholders=["driver1", "driver2", "position"],
        optional_placeholders=[]
    )


class TestPhraseCombinerInitialization:
    """Test PhraseCombiner initialization."""
    
    def test_initialization(self, config, mock_resolver):
        """Test that PhraseCombiner initializes correctly."""
        combiner = PhraseCombiner(config, mock_resolver)
        
        assert combiner.config == config
        assert combiner.placeholder_resolver == mock_resolver
        assert combiner.max_sentence_length == 40
    
    def test_initialization_with_custom_max_length(self, mock_resolver):
        """Test initialization with custom max sentence length."""
        config = Config(
            openf1_api_key="test",
            elevenlabs_api_key="test",
            elevenlabs_voice_id="test",
            max_sentence_length=30
        )
        combiner = PhraseCombiner(config, mock_resolver)
        
        assert combiner.max_sentence_length == 30


class TestGenerateCommentary:
    """Test generate_commentary method."""
    
    def test_generate_simple_commentary(self, phrase_combiner, sample_template, sample_context):
        """Test generating simple commentary with all placeholders resolved."""
        result = phrase_combiner.generate_commentary(sample_template, sample_context)
        
        assert result == "Hamilton makes the move on Verstappen into P1!"
        assert "{" not in result
        assert "}" not in result
    
    def test_generate_commentary_with_optional_placeholders(self, phrase_combiner, mock_resolver, sample_context):
        """Test generating commentary with optional placeholders."""
        template = Template(
            template_id="test_002",
            event_type="overtake",
            excitement_level="excited",
            perspective="technical",
            template_text="{driver1} overtakes {driver2} {drs_status}, moving into {position}.",
            required_placeholders=["driver1", "driver2", "position"],
            optional_placeholders=["drs_status"]
        )
        
        result = phrase_combiner.generate_commentary(template, sample_context)
        
        assert "Hamilton" in result
        assert "Verstappen" in result
        assert "with DRS" in result
        assert "P1" in result
    
    def test_generate_commentary_with_missing_optional_placeholder(self, phrase_combiner, sample_context):
        """Test that missing optional placeholders are handled gracefully."""
        # Create a new mock resolver for this test
        resolver = Mock(spec=PlaceholderResolver)
        
        def resolve_with_none(placeholder, context):
            resolutions = {
                "driver1": "Hamilton",
                "driver2": "Verstappen",
                "tire_age": None  # This one is missing
            }
            return resolutions.get(placeholder)
        
        resolver.resolve.side_effect = resolve_with_none
        
        # Create a new phrase combiner with this resolver
        combiner = PhraseCombiner(phrase_combiner.config, resolver)
        
        template = Template(
            template_id="test_003",
            event_type="overtake",
            excitement_level="engaged",
            perspective="strategic",
            template_text="{driver1} overtakes {driver2} on tires that are {tire_age}.",
            required_placeholders=["driver1", "driver2"],
            optional_placeholders=["tire_age"]
        )
        
        result = combiner.generate_commentary(template, sample_context)
        
        # Should still generate commentary, just without the tire age
        assert "Hamilton" in result
        assert "Verstappen" in result
        # The unresolved placeholder should be removed
        assert "{tire_age}" not in result


class TestResolvePlaceholders:
    """Test _resolve_placeholders method."""
    
    def test_resolve_all_placeholders(self, phrase_combiner, sample_context):
        """Test resolving all placeholders in a template."""
        template_text = "{driver1} overtakes {driver2} into {position}"
        
        result = phrase_combiner._resolve_placeholders(template_text, sample_context)
        
        assert result == "Hamilton overtakes Verstappen into P1"
    
    def test_resolve_with_unresolvable_placeholder(self, phrase_combiner, sample_context):
        """Test that unresolvable placeholders are left in place."""
        template_text = "{driver1} overtakes {unknown_placeholder}"
        
        result = phrase_combiner._resolve_placeholders(template_text, sample_context)
        
        assert "Hamilton" in result
        assert "{unknown_placeholder}" in result
    
    def test_resolve_multiple_same_placeholder(self, phrase_combiner, sample_context):
        """Test resolving the same placeholder multiple times."""
        template_text = "{driver1} and {driver1} again"
        
        result = phrase_combiner._resolve_placeholders(template_text, sample_context)
        
        assert result == "Hamilton and Hamilton again"


class TestValidateOutput:
    """Test _validate_output method."""
    
    def test_validate_valid_output(self, phrase_combiner):
        """Test that valid output passes validation."""
        text = "Hamilton overtakes Verstappen into P1."
        
        assert phrase_combiner._validate_output(text) is True
    
    def test_validate_empty_text(self, phrase_combiner):
        """Test that empty text fails validation."""
        assert phrase_combiner._validate_output("") is False
        assert phrase_combiner._validate_output("   ") is False
    
    def test_validate_with_unresolved_placeholders(self, phrase_combiner):
        """Test that text with unresolved placeholders fails validation."""
        text = "Hamilton overtakes {driver2} into P1."
        
        assert phrase_combiner._validate_output(text) is False
    
    def test_validate_without_capital_start(self, phrase_combiner):
        """Test that text without capital start still passes (warning only)."""
        text = "hamilton overtakes Verstappen."
        
        # Should still pass, just logs a warning
        assert phrase_combiner._validate_output(text) is True
    
    def test_validate_without_punctuation_end(self, phrase_combiner):
        """Test that text without punctuation still passes (warning only)."""
        text = "Hamilton overtakes Verstappen"
        
        # Should still pass, just logs a warning
        assert phrase_combiner._validate_output(text) is True


class TestTruncateIfNeeded:
    """Test _truncate_if_needed method."""
    
    def test_no_truncation_needed(self, phrase_combiner):
        """Test that short text is not truncated."""
        text = "Hamilton overtakes Verstappen into P1."
        
        result = phrase_combiner._truncate_if_needed(text)
        
        assert result == text
    
    def test_truncate_long_text(self, phrase_combiner):
        """Test that text exceeding max length is truncated."""
        # Create text with more than 40 words
        words = ["word"] * 50
        text = " ".join(words)
        
        result = phrase_combiner._truncate_if_needed(text)
        
        result_words = result.split()
        assert len(result_words) <= 40
    
    def test_truncate_at_natural_boundary(self, phrase_combiner):
        """Test that truncation prefers natural boundaries."""
        # Create text with comma at word 35
        words = ["word"] * 35 + [","] + ["word"] * 20
        text = " ".join(words)
        
        result = phrase_combiner._truncate_if_needed(text)
        
        # Should truncate at the comma
        assert result.endswith(",") or result.endswith(".")
    
    def test_truncate_adds_period(self, phrase_combiner):
        """Test that truncation adds period if needed."""
        # Create text without punctuation
        words = ["word"] * 50
        text = " ".join(words)
        
        result = phrase_combiner._truncate_if_needed(text)
        
        # Should end with period
        assert result.endswith(".")
    
    def test_truncate_exact_max_length(self, phrase_combiner):
        """Test text at exactly max length is not truncated."""
        words = ["word"] * 40
        text = " ".join(words)
        
        result = phrase_combiner._truncate_if_needed(text)
        
        assert len(result.split()) == 40


class TestCleanText:
    """Test _clean_text method."""
    
    def test_clean_multiple_spaces(self, phrase_combiner):
        """Test removing multiple consecutive spaces."""
        text = "Hamilton  overtakes   Verstappen"
        
        result = phrase_combiner._clean_text(text)
        
        assert result == "Hamilton overtakes Verstappen"
    
    def test_clean_spaces_before_punctuation(self, phrase_combiner):
        """Test removing spaces before punctuation."""
        text = "Hamilton overtakes Verstappen ."
        
        result = phrase_combiner._clean_text(text)
        
        assert result == "Hamilton overtakes Verstappen."
    
    def test_clean_missing_space_after_punctuation(self, phrase_combiner):
        """Test adding space after punctuation."""
        text = "Hamilton overtakes.Verstappen follows."
        
        result = phrase_combiner._clean_text(text)
        
        assert result == "Hamilton overtakes. Verstappen follows."
    
    def test_clean_orphaned_commas(self, phrase_combiner):
        """Test cleaning up orphaned commas from unresolved placeholders."""
        text = "Hamilton overtakes , and moves into P1"
        
        result = phrase_combiner._clean_text(text)
        
        assert result == "Hamilton overtakes and moves into P1"
    
    def test_clean_double_commas(self, phrase_combiner):
        """Test cleaning up double commas."""
        text = "Hamilton overtakes,, and moves into P1"
        
        result = phrase_combiner._clean_text(text)
        
        # Double commas get cleaned to single comma, then comma before 'and' gets removed
        assert result == "Hamilton overtakes and moves into P1"


class TestRemoveUnresolvedPlaceholders:
    """Test _remove_unresolved_placeholders method."""
    
    def test_remove_single_placeholder(self, phrase_combiner):
        """Test removing a single unresolved placeholder."""
        text = "Hamilton overtakes {unknown} into P1."
        
        result = phrase_combiner._remove_unresolved_placeholders(text)
        
        assert "{unknown}" not in result
        assert "Hamilton overtakes into P1." == result
    
    def test_remove_multiple_placeholders(self, phrase_combiner):
        """Test removing multiple unresolved placeholders."""
        text = "Hamilton {unknown1} overtakes {unknown2} into P1."
        
        result = phrase_combiner._remove_unresolved_placeholders(text)
        
        assert "{" not in result
        assert "}" not in result
        assert "Hamilton overtakes into P1." == result
    
    def test_remove_placeholders_and_clean(self, phrase_combiner):
        """Test that removing placeholders also cleans up formatting."""
        text = "Hamilton overtakes {unknown} , and moves into P1."
        
        result = phrase_combiner._remove_unresolved_placeholders(text)
        
        assert "{unknown}" not in result
        assert "Hamilton overtakes and moves into P1." == result


class TestCompoundSentences:
    """Test generation of compound sentences with multiple data points."""
    
    def test_compound_sentence_with_transitional_phrases(self, phrase_combiner, mock_resolver, sample_context):
        """Test that compound sentences preserve transitional phrases."""
        template = Template(
            template_id="test_compound",
            event_type="overtake",
            excitement_level="excited",
            perspective="dramatic",
            template_text="{driver1} overtakes {driver2} with {drs_status}, and moves into {position} while {gap_trend}.",
            required_placeholders=["driver1", "driver2", "position"],
            optional_placeholders=["drs_status", "gap_trend"]
        )
        
        result = phrase_combiner.generate_commentary(template, sample_context)
        
        # Check that transitional phrases are preserved
        assert "with" in result or "and" in result or "while" in result
        # Check that multiple data points are included
        assert "Hamilton" in result
        assert "Verstappen" in result
        assert "P1" in result
    
    def test_compound_sentence_with_multiple_data_points(self, phrase_combiner, mock_resolver, sample_context):
        """Test that compound sentences combine multiple data points."""
        template = Template(
            template_id="test_multi_data",
            event_type="overtake",
            excitement_level="engaged",
            perspective="technical",
            template_text="{driver1} on {tire_compound} tires overtakes {driver2} at {speed} {drs_status}.",
            required_placeholders=["driver1", "driver2"],
            optional_placeholders=["tire_compound", "speed", "drs_status"]
        )
        
        result = phrase_combiner.generate_commentary(template, sample_context)
        
        # Should contain at least 3-4 data points
        data_points = 0
        if "Hamilton" in result:
            data_points += 1
        if "Verstappen" in result:
            data_points += 1
        if "soft" in result:
            data_points += 1
        if "315" in result or "kilometers" in result:
            data_points += 1
        if "DRS" in result:
            data_points += 1
        
        assert data_points >= 3


class TestIntegrationScenarios:
    """Test complete integration scenarios."""
    
    def test_pit_stop_commentary(self, phrase_combiner, mock_resolver):
        """Test generating pit stop commentary."""
        # Set up pit stop specific resolutions
        def pit_resolve(placeholder, context):
            resolutions = {
                "driver": "Hamilton",
                "position": "P2",
                "old_tire_compound": "medium",
                "old_tire_age": "25 laps",
                "new_tire_compound": "soft",
                "pit_duration": "2.3 seconds"
            }
            return resolutions.get(placeholder)
        
        mock_resolver.resolve.side_effect = pit_resolve
        
        event = Mock()
        event.driver = "Hamilton"
        event.lap_number = 30
        event.timestamp = datetime.now()
        
        context = ContextData(
            event=event,
            race_state=RaceState(),
            previous_tire_compound="medium",
            previous_tire_age=25,
            current_tire_compound="soft",
            pit_duration=2.3,
            position_after=2
        )
        
        template = Template(
            template_id="pit_001",
            event_type="pit_stop",
            excitement_level="moderate",
            perspective="strategic",
            template_text="{driver} pits from {position}, switching from {old_tire_compound} tires with {old_tire_age} to fresh {new_tire_compound} in {pit_duration}.",
            required_placeholders=["driver", "position"],
            optional_placeholders=["old_tire_compound", "old_tire_age", "new_tire_compound", "pit_duration"]
        )
        
        result = phrase_combiner.generate_commentary(template, context)
        
        assert "Hamilton" in result
        assert "P2" in result
        assert "medium" in result
        assert "soft" in result
        assert "2.3 seconds" in result
    
    def test_fastest_lap_commentary(self, phrase_combiner, mock_resolver):
        """Test generating fastest lap commentary."""
        def fastest_lap_resolve(placeholder, context):
            resolutions = {
                "driver": "Verstappen",
                "lap_time": "1:23.456",
                "sector_1_time": "23.123",
                "sector_2_time": "35.456",
                "sector_3_time": "24.877",
                "tire_compound": "soft"
            }
            return resolutions.get(placeholder)
        
        mock_resolver.resolve.side_effect = fastest_lap_resolve
        
        event = Mock()
        event.driver = "Verstappen"
        event.lap_number = 45
        event.lap_time = 83.456
        event.timestamp = datetime.now()
        
        context = ContextData(
            event=event,
            race_state=RaceState(),
            sector_1_time=23.123,
            sector_2_time=35.456,
            sector_3_time=24.877,
            current_tire_compound="soft"
        )
        
        template = Template(
            template_id="fastest_001",
            event_type="fastest_lap",
            excitement_level="engaged",
            perspective="technical",
            template_text="{driver} sets the fastest lap with a {lap_time} on {tire_compound} tires.",
            required_placeholders=["driver", "lap_time"],
            optional_placeholders=["tire_compound"]
        )
        
        result = phrase_combiner.generate_commentary(template, context)
        
        assert "Verstappen" in result
        assert "1:23.456" in result
        assert "soft" in result

