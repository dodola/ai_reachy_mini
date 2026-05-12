"""
Unit tests for Template Selector.

Tests template selection logic including context filtering, scoring,
repetition avoidance, and fallback behavior.
"""

import pytest
from unittest.mock import Mock, MagicMock
from collections import deque

from reachy_f1_commentator.src.template_selector import TemplateSelector
from reachy_f1_commentator.src.template_library import TemplateLibrary
from reachy_f1_commentator.src.enhanced_models import (
    ContextData,
    CommentaryStyle,
    Template,
    ExcitementLevel,
    CommentaryPerspective,
    RaceEvent,
    RaceState
)
from reachy_f1_commentator.src.config import Config


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = Mock(spec=Config)
    config.template_repetition_window = 10
    return config


@pytest.fixture
def mock_template_library():
    """Create mock template library with sample templates."""
    library = Mock(spec=TemplateLibrary)
    
    # Create sample templates
    def create_template(template_id, event_type, excitement, perspective, 
                       optional_placeholders=None, context_requirements=None):
        return Template(
            template_id=template_id,
            event_type=event_type,
            excitement_level=excitement,
            perspective=perspective,
            template_text=f"Template {template_id}",
            required_placeholders=["driver1", "driver2", "position"],
            optional_placeholders=optional_placeholders or [],
            context_requirements=context_requirements or {}
        )
    
    # Mock get_templates to return different templates based on criteria
    def get_templates_side_effect(event_type, excitement, perspective):
        excitement_str = excitement.name.lower()
        perspective_str = perspective.value
        
        # Return templates for overtake events
        if event_type == "overtake":
            if excitement_str == "excited" and perspective_str == "dramatic":
                return [
                    create_template(
                        "overtake_excited_dramatic_001",
                        "overtake", "excited", "dramatic",
                        optional_placeholders=["pronoun", "drs_status"],
                        context_requirements={}
                    ),
                    create_template(
                        "overtake_excited_dramatic_002",
                        "overtake", "excited", "dramatic",
                        optional_placeholders=["tire_age_diff", "gap"],
                        context_requirements={"tire_data": True}
                    ),
                    create_template(
                        "overtake_excited_dramatic_003",
                        "overtake", "excited", "dramatic",
                        optional_placeholders=["narrative_reference"],
                        context_requirements={"battle_narrative": True}
                    )
                ]
            elif excitement_str == "calm" and perspective_str == "technical":
                return [
                    create_template(
                        "overtake_calm_technical_001",
                        "overtake", "calm", "technical",
                        optional_placeholders=["speed_diff"],
                        context_requirements={}
                    )
                ]
        
        return []
    
    library.get_templates.side_effect = get_templates_side_effect
    
    return library


@pytest.fixture
def mock_race_event():
    """Create mock race event."""
    event = Mock(spec=RaceEvent)
    event.event_type = "overtake"
    event.driver = "Hamilton"
    event.lap_number = 10
    return event


@pytest.fixture
def mock_race_state():
    """Create mock race state."""
    state = Mock(spec=RaceState)
    state.current_lap = 10
    return state


@pytest.fixture
def basic_context(mock_race_event, mock_race_state):
    """Create basic context data."""
    return ContextData(
        event=mock_race_event,
        race_state=mock_race_state,
        gap_to_ahead=1.5,
        current_tire_compound="soft",
        current_tire_age=10
    )


@pytest.fixture
def template_selector(mock_config, mock_template_library):
    """Create template selector instance."""
    return TemplateSelector(mock_config, mock_template_library)


class TestTemplateSelector:
    """Test suite for TemplateSelector class."""
    
    def test_initialization(self, mock_config, mock_template_library):
        """Test template selector initialization."""
        selector = TemplateSelector(mock_config, mock_template_library)
        
        assert selector.config == mock_config
        assert selector.template_library == mock_template_library
        assert isinstance(selector.recent_templates, deque)
        assert selector.recent_templates.maxlen == 10
    
    def test_select_template_basic(self, template_selector, basic_context):
        """Test basic template selection."""
        style = CommentaryStyle(
            excitement_level=ExcitementLevel.EXCITED,
            perspective=CommentaryPerspective.DRAMATIC
        )
        
        template = template_selector.select_template(
            event_type="overtake",
            context=basic_context,
            style=style
        )
        
        assert template is not None
        assert template.event_type == "overtake"
        assert template.template_id in template_selector.recent_templates
    
    def test_filter_by_context_tire_data_required(self, template_selector):
        """Test filtering templates that require tire data."""
        templates = [
            Template(
                template_id="with_tire_data",
                event_type="overtake",
                excitement_level="excited",
                perspective="dramatic",
                template_text="Template with tire data",
                required_placeholders=["driver1"],
                optional_placeholders=["tire_age_diff"],
                context_requirements={"tire_data": True}
            ),
            Template(
                template_id="without_tire_data",
                event_type="overtake",
                excitement_level="excited",
                perspective="dramatic",
                template_text="Template without tire data",
                required_placeholders=["driver1"],
                optional_placeholders=[],
                context_requirements={}
            )
        ]
        
        # Context without tire data
        context = ContextData(
            event=Mock(),
            race_state=Mock(),
            current_tire_compound=None
        )
        
        filtered = template_selector._filter_by_context(templates, context)
        
        assert len(filtered) == 1
        assert filtered[0].template_id == "without_tire_data"
    
    def test_filter_by_context_tire_data_available(self, template_selector, basic_context):
        """Test filtering when tire data is available."""
        templates = [
            Template(
                template_id="with_tire_data",
                event_type="overtake",
                excitement_level="excited",
                perspective="dramatic",
                template_text="Template with tire data",
                required_placeholders=["driver1"],
                optional_placeholders=["tire_age_diff"],
                context_requirements={"tire_data": True}
            )
        ]
        
        filtered = template_selector._filter_by_context(templates, basic_context)
        
        assert len(filtered) == 1
        assert filtered[0].template_id == "with_tire_data"
    
    def test_filter_by_context_battle_narrative(self, template_selector):
        """Test filtering templates that require battle narrative."""
        templates = [
            Template(
                template_id="with_battle",
                event_type="overtake",
                excitement_level="excited",
                perspective="dramatic",
                template_text="Template with battle",
                required_placeholders=["driver1"],
                optional_placeholders=["narrative_reference"],
                context_requirements={"battle_narrative": True}
            )
        ]
        
        # Context without battle narrative
        context = ContextData(
            event=Mock(),
            race_state=Mock(),
            active_narratives=[]
        )
        
        filtered = template_selector._filter_by_context(templates, context)
        assert len(filtered) == 0
        
        # Context with battle narrative
        context.active_narratives = ["battle_hamilton_verstappen"]
        filtered = template_selector._filter_by_context(templates, context)
        assert len(filtered) == 1
    
    def test_score_template_basic(self, template_selector, basic_context):
        """Test basic template scoring."""
        template = Template(
            template_id="basic",
            event_type="overtake",
            excitement_level="excited",
            perspective="dramatic",
            template_text="Basic template",
            required_placeholders=["driver1"],
            optional_placeholders=[],
            context_requirements={}
        )
        
        score = template_selector._score_template(template, basic_context)
        
        assert score == 5.0  # Base score
    
    def test_score_template_with_optional_data(self, template_selector, basic_context):
        """Test scoring with optional placeholders that have data."""
        template = Template(
            template_id="with_optional",
            event_type="overtake",
            excitement_level="excited",
            perspective="dramatic",
            template_text="Template with optional data",
            required_placeholders=["driver1"],
            optional_placeholders=["gap", "tire_compound"],
            context_requirements={}
        )
        
        score = template_selector._score_template(template, basic_context)
        
        # Base score (5.0) + 2 optional placeholders with data (0.5 each) = 6.0
        assert score == 6.0
    
    def test_score_template_with_narrative(self, template_selector, basic_context):
        """Test scoring bonus for narrative references."""
        template = Template(
            template_id="with_narrative",
            event_type="overtake",
            excitement_level="excited",
            perspective="dramatic",
            template_text="Template with narrative",
            required_placeholders=["driver1"],
            optional_placeholders=["narrative_reference"],
            context_requirements={}
        )
        
        basic_context.active_narratives = ["battle_hamilton_verstappen"]
        
        score = template_selector._score_template(template, basic_context)
        
        # Base score (5.0) + narrative bonus (1.5) + has data (0.5) = 7.0
        assert score == 7.0
    
    def test_score_template_with_championship_context(self, template_selector, basic_context):
        """Test scoring bonus for championship context."""
        template = Template(
            template_id="with_championship",
            event_type="overtake",
            excitement_level="excited",
            perspective="dramatic",
            template_text="Template with championship",
            required_placeholders=["driver1"],
            optional_placeholders=["championship_context"],
            context_requirements={}
        )
        
        basic_context.is_championship_contender = True
        basic_context.driver_championship_position = 2
        
        score = template_selector._score_template(template, basic_context)
        
        # Base score (5.0) + championship bonus (1.5) + has data (0.5) = 7.0
        assert score == 7.0
    
    def test_score_template_with_tire_age_differential(self, template_selector, basic_context):
        """Test scoring bonus for significant tire age differential."""
        template = Template(
            template_id="with_tire_diff",
            event_type="overtake",
            excitement_level="excited",
            perspective="dramatic",
            template_text="Template with tire diff",
            required_placeholders=["driver1"],
            optional_placeholders=["tire_age_diff"],
            context_requirements={}
        )
        
        basic_context.tire_age_differential = 8  # > 5 laps
        
        score = template_selector._score_template(template, basic_context)
        
        # Base score (5.0) + tire diff bonus (1.0) + has data (0.5) = 6.5
        assert score == 6.5
    
    def test_score_template_with_close_gap(self, template_selector, basic_context):
        """Test scoring bonus for close gap."""
        template = Template(
            template_id="with_gap",
            event_type="overtake",
            excitement_level="excited",
            perspective="dramatic",
            template_text="Template with gap",
            required_placeholders=["driver1"],
            optional_placeholders=["gap"],
            context_requirements={}
        )
        
        basic_context.gap_to_ahead = 0.8  # < 1.0 second
        
        score = template_selector._score_template(template, basic_context)
        
        # Base score (5.0) + close gap bonus (1.0) + has data (0.5) = 6.5
        assert score == 6.5
    
    def test_score_template_with_drs(self, template_selector, basic_context):
        """Test scoring bonus for DRS active."""
        template = Template(
            template_id="with_drs",
            event_type="overtake",
            excitement_level="excited",
            perspective="dramatic",
            template_text="Template with DRS",
            required_placeholders=["driver1"],
            optional_placeholders=["drs_status"],
            context_requirements={}
        )
        
        basic_context.drs_active = True
        
        score = template_selector._score_template(template, basic_context)
        
        # Base score (5.0) + DRS bonus (0.5) + has data (0.5) = 6.0
        assert score == 6.0
    
    def test_avoid_repetition(self, template_selector):
        """Test filtering out recently used templates."""
        templates = [
            Template(
                template_id="template_1",
                event_type="overtake",
                excitement_level="excited",
                perspective="dramatic",
                template_text="Template 1",
                required_placeholders=["driver1"],
                optional_placeholders=[],
                context_requirements={}
            ),
            Template(
                template_id="template_2",
                event_type="overtake",
                excitement_level="excited",
                perspective="dramatic",
                template_text="Template 2",
                required_placeholders=["driver1"],
                optional_placeholders=[],
                context_requirements={}
            ),
            Template(
                template_id="template_3",
                event_type="overtake",
                excitement_level="excited",
                perspective="dramatic",
                template_text="Template 3",
                required_placeholders=["driver1"],
                optional_placeholders=[],
                context_requirements={}
            )
        ]
        
        # Mark template_1 and template_2 as recently used
        template_selector.recent_templates.append("template_1")
        template_selector.recent_templates.append("template_2")
        
        filtered = template_selector._avoid_repetition(templates)
        
        assert len(filtered) == 1
        assert filtered[0].template_id == "template_3"
    
    def test_repetition_window_limit(self, template_selector):
        """Test that repetition window respects maxlen."""
        # Fill up the deque beyond its limit
        for i in range(15):
            template_selector.recent_templates.append(f"template_{i}")
        
        # Should only keep last 10
        assert len(template_selector.recent_templates) == 10
        assert "template_5" in template_selector.recent_templates
        assert "template_14" in template_selector.recent_templates
        assert "template_0" not in template_selector.recent_templates
    
    def test_select_template_tracks_usage(self, template_selector, basic_context):
        """Test that selected templates are tracked."""
        style = CommentaryStyle(
            excitement_level=ExcitementLevel.EXCITED,
            perspective=CommentaryPerspective.DRAMATIC
        )
        
        initial_count = len(template_selector.recent_templates)
        
        template = template_selector.select_template(
            event_type="overtake",
            context=basic_context,
            style=style
        )
        
        assert len(template_selector.recent_templates) == initial_count + 1
        assert template.template_id in template_selector.recent_templates
    
    def test_select_template_no_templates_found(self, template_selector, basic_context):
        """Test fallback when no templates match criteria."""
        style = CommentaryStyle(
            excitement_level=ExcitementLevel.EXCITED,
            perspective=CommentaryPerspective.DRAMATIC
        )
        
        # Request template for event type that doesn't exist
        template = template_selector.select_template(
            event_type="nonexistent_event",
            context=basic_context,
            style=style
        )
        
        # Should return None (fallback will be triggered)
        assert template is None
    
    def test_fallback_template_different_perspective(self, mock_config, mock_template_library, basic_context):
        """Test fallback tries different perspectives."""
        selector = TemplateSelector(mock_config, mock_template_library)
        
        style = CommentaryStyle(
            excitement_level=ExcitementLevel.EXCITED,
            perspective=CommentaryPerspective.DRAMATIC
        )
        
        # Mock get_templates to return empty for dramatic but templates for technical
        def fallback_side_effect(event_type, excitement, perspective):
            if perspective == CommentaryPerspective.TECHNICAL:
                return [
                    Template(
                        template_id="fallback_technical",
                        event_type="overtake",
                        excitement_level="excited",
                        perspective="technical",
                        template_text="Fallback template",
                        required_placeholders=["driver1"],
                        optional_placeholders=[],
                        context_requirements={}
                    )
                ]
            return []
        
        mock_template_library.get_templates.side_effect = fallback_side_effect
        
        template = selector._fallback_template("overtake", basic_context, style)
        
        assert template is not None
        assert template.template_id == "fallback_technical"
    
    def test_fallback_template_calm_excitement(self, mock_config, mock_template_library, basic_context):
        """Test fallback tries calm excitement level."""
        selector = TemplateSelector(mock_config, mock_template_library)
        
        style = CommentaryStyle(
            excitement_level=ExcitementLevel.EXCITED,
            perspective=CommentaryPerspective.DRAMATIC
        )
        
        # Mock get_templates to return templates only for calm excitement
        def fallback_side_effect(event_type, excitement, perspective):
            if excitement == ExcitementLevel.CALM:
                return [
                    Template(
                        template_id="fallback_calm",
                        event_type="overtake",
                        excitement_level="calm",
                        perspective="technical",
                        template_text="Fallback calm template",
                        required_placeholders=["driver1"],
                        optional_placeholders=[],
                        context_requirements={}
                    )
                ]
            return []
        
        mock_template_library.get_templates.side_effect = fallback_side_effect
        
        template = selector._fallback_template("overtake", basic_context, style)
        
        assert template is not None
        assert template.template_id == "fallback_calm"
    
    def test_reset_history(self, template_selector):
        """Test resetting template selection history."""
        template_selector.recent_templates.append("template_1")
        template_selector.recent_templates.append("template_2")
        
        assert len(template_selector.recent_templates) == 2
        
        template_selector.reset_history()
        
        assert len(template_selector.recent_templates) == 0
    
    def test_get_statistics(self, template_selector):
        """Test getting selection statistics."""
        template_selector.recent_templates.append("template_1")
        template_selector.recent_templates.append("template_2")
        
        stats = template_selector.get_statistics()
        
        assert stats['recent_templates_count'] == 2
        assert stats['recent_templates'] == ["template_1", "template_2"]
        assert stats['repetition_window'] == 10
    
    def test_has_data_for_placeholder(self, template_selector, basic_context):
        """Test checking if context has data for placeholders."""
        # Test placeholders with data
        assert template_selector._has_data_for_placeholder("gap", basic_context)
        assert template_selector._has_data_for_placeholder("tire_compound", basic_context)
        assert template_selector._has_data_for_placeholder("tire_age", basic_context)
        
        # Test placeholders without data
        assert not template_selector._has_data_for_placeholder("speed", basic_context)
        assert not template_selector._has_data_for_placeholder("drs_status", basic_context)
        assert not template_selector._has_data_for_placeholder("sector_1_time", basic_context)
    
    def test_select_from_top_3_scored(self, template_selector, basic_context):
        """Test that selection is from top 3 scored templates."""
        style = CommentaryStyle(
            excitement_level=ExcitementLevel.EXCITED,
            perspective=CommentaryPerspective.DRAMATIC
        )
        
        # Run selection multiple times
        selected_ids = set()
        for _ in range(20):
            template_selector.reset_history()  # Reset to allow repetition
            template = template_selector.select_template(
                event_type="overtake",
                context=basic_context,
                style=style
            )
            if template:
                selected_ids.add(template.template_id)
        
        # Should only select from available templates (max 3 in mock)
        assert len(selected_ids) <= 3
