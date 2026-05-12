"""
Unit tests for Template Library.

Tests template loading, validation, and retrieval functionality.
"""

import json
import pytest
import tempfile
from pathlib import Path

from reachy_f1_commentator.src.template_library import TemplateLibrary
from reachy_f1_commentator.src.enhanced_models import ExcitementLevel, CommentaryPerspective, Template


class TestTemplateLibrary:
    """Test suite for TemplateLibrary class."""
    
    @pytest.fixture
    def sample_templates(self):
        """Create sample template data for testing."""
        return {
            "metadata": {
                "version": "1.0",
                "description": "Test templates",
                "total_templates": 3
            },
            "templates": [
                {
                    "template_id": "overtake_calm_technical_001",
                    "event_type": "overtake",
                    "excitement_level": "calm",
                    "perspective": "technical",
                    "template_text": "{driver1} moves past {driver2} into {position}.",
                    "required_placeholders": ["driver1", "driver2", "position"],
                    "optional_placeholders": [],
                    "context_requirements": {}
                },
                {
                    "template_id": "overtake_calm_technical_002",
                    "event_type": "overtake",
                    "excitement_level": "calm",
                    "perspective": "technical",
                    "template_text": "{driver1} overtakes {driver2} for {position} with {drs_status}.",
                    "required_placeholders": ["driver1", "driver2", "position"],
                    "optional_placeholders": ["drs_status"],
                    "context_requirements": {"telemetry_data": False}
                },
                {
                    "template_id": "pit_stop_calm_strategic_001",
                    "event_type": "pit_stop",
                    "excitement_level": "calm",
                    "perspective": "strategic",
                    "template_text": "{driver} pits from {position} for {tire_compound} tires.",
                    "required_placeholders": ["driver", "position"],
                    "optional_placeholders": ["tire_compound"],
                    "context_requirements": {"tire_data": False}
                }
            ]
        }
    
    @pytest.fixture
    def template_file(self, sample_templates, tmp_path):
        """Create temporary template file for testing."""
        template_path = tmp_path / "test_templates.json"
        with open(template_path, 'w') as f:
            json.dump(sample_templates, f)
        return str(template_path)
    
    def test_init(self):
        """Test TemplateLibrary initialization."""
        library = TemplateLibrary()
        assert library.templates == {}
        assert library.metadata == {}
        assert library.get_template_count() == 0
    
    def test_load_templates_success(self, template_file):
        """Test successful template loading."""
        library = TemplateLibrary()
        library.load_templates(template_file)
        
        assert library.get_template_count() == 3
        assert len(library.metadata) > 0
        assert library.metadata['version'] == "1.0"
    
    def test_load_templates_file_not_found(self):
        """Test loading from non-existent file."""
        library = TemplateLibrary()
        
        with pytest.raises(FileNotFoundError):
            library.load_templates("nonexistent_file.json")
    
    def test_load_templates_invalid_json(self, tmp_path):
        """Test loading invalid JSON file."""
        invalid_file = tmp_path / "invalid.json"
        with open(invalid_file, 'w') as f:
            f.write("{ invalid json }")
        
        library = TemplateLibrary()
        
        with pytest.raises(ValueError):
            library.load_templates(str(invalid_file))
    
    def test_get_templates_found(self, template_file):
        """Test retrieving templates that exist."""
        library = TemplateLibrary()
        library.load_templates(template_file)
        
        templates = library.get_templates(
            "overtake",
            ExcitementLevel.CALM,
            CommentaryPerspective.TECHNICAL
        )
        
        assert len(templates) == 2
        assert all(t.event_type == "overtake" for t in templates)
        assert all(t.excitement_level == "calm" for t in templates)
        assert all(t.perspective == "technical" for t in templates)
    
    def test_get_templates_not_found(self, template_file):
        """Test retrieving templates that don't exist."""
        library = TemplateLibrary()
        library.load_templates(template_file)
        
        templates = library.get_templates(
            "fastest_lap",
            ExcitementLevel.DRAMATIC,
            CommentaryPerspective.HISTORICAL
        )
        
        assert templates == []
    
    def test_validate_templates_valid(self, template_file):
        """Test validation of valid templates."""
        library = TemplateLibrary()
        library.load_templates(template_file)
        
        errors = library.validate_templates()
        
        assert errors == []
    
    def test_validate_templates_unsupported_placeholder(self, tmp_path):
        """Test validation catches unsupported placeholders."""
        invalid_templates = {
            "templates": [
                {
                    "template_id": "test_001",
                    "event_type": "overtake",
                    "excitement_level": "calm",
                    "perspective": "technical",
                    "template_text": "{driver1} passes {driver2} with {unsupported_placeholder}.",
                    "required_placeholders": ["driver1", "driver2"],
                    "optional_placeholders": ["unsupported_placeholder"],
                    "context_requirements": {}
                }
            ]
        }
        
        template_path = tmp_path / "invalid_templates.json"
        with open(template_path, 'w') as f:
            json.dump(invalid_templates, f)
        
        library = TemplateLibrary()
        library.load_templates(str(template_path))
        
        errors = library.validate_templates()
        
        assert len(errors) > 0
        assert any("unsupported_placeholder" in error for error in errors)
    
    def test_validate_templates_missing_required_placeholder(self, tmp_path):
        """Test validation catches missing required placeholders."""
        invalid_templates = {
            "templates": [
                {
                    "template_id": "test_001",
                    "event_type": "overtake",
                    "excitement_level": "calm",
                    "perspective": "technical",
                    "template_text": "{driver1} passes {driver2}.",
                    "required_placeholders": ["driver1", "driver2", "position"],
                    "optional_placeholders": [],
                    "context_requirements": {}
                }
            ]
        }
        
        template_path = tmp_path / "invalid_templates.json"
        with open(template_path, 'w') as f:
            json.dump(invalid_templates, f)
        
        library = TemplateLibrary()
        library.load_templates(str(template_path))
        
        errors = library.validate_templates()
        
        assert len(errors) > 0
        assert any("position" in error and "not in template text" in error for error in errors)
    
    def test_get_template_by_id_found(self, template_file):
        """Test retrieving template by ID."""
        library = TemplateLibrary()
        library.load_templates(template_file)
        
        template = library.get_template_by_id("overtake_calm_technical_001")
        
        assert template is not None
        assert template.template_id == "overtake_calm_technical_001"
        assert template.event_type == "overtake"
    
    def test_get_template_by_id_not_found(self, template_file):
        """Test retrieving non-existent template by ID."""
        library = TemplateLibrary()
        library.load_templates(template_file)
        
        template = library.get_template_by_id("nonexistent_template")
        
        assert template is None
    
    def test_get_available_combinations(self, template_file):
        """Test getting available template combinations."""
        library = TemplateLibrary()
        library.load_templates(template_file)
        
        combinations = library.get_available_combinations()
        
        assert len(combinations) == 2  # overtake_calm_technical and pit_stop_calm_strategic
        assert ("overtake", "calm", "technical") in combinations
        assert ("pit_stop", "calm", "strategic") in combinations
    
    def test_get_statistics(self, template_file):
        """Test getting template statistics."""
        library = TemplateLibrary()
        library.load_templates(template_file)
        
        stats = library.get_statistics()
        
        assert stats['total_templates'] == 3
        assert stats['by_event_type']['overtake'] == 2
        assert stats['by_event_type']['pit_stop'] == 1
        assert stats['by_excitement_level']['calm'] == 3
        assert stats['by_perspective']['technical'] == 2
        assert stats['by_perspective']['strategic'] == 1
        assert stats['combinations'] == 2
    
    def test_extract_placeholders(self):
        """Test placeholder extraction from template text."""
        library = TemplateLibrary()
        
        text = "{driver1} overtakes {driver2} for {position} with {drs_status}."
        placeholders = library._extract_placeholders(text)
        
        assert placeholders == {'driver1', 'driver2', 'position', 'drs_status'}
    
    def test_extract_placeholders_no_placeholders(self):
        """Test placeholder extraction with no placeholders."""
        library = TemplateLibrary()
        
        text = "This is a template with no placeholders."
        placeholders = library._extract_placeholders(text)
        
        assert placeholders == set()
    
    def test_parse_template_missing_required_field(self):
        """Test parsing template with missing required field."""
        library = TemplateLibrary()
        
        invalid_template = {
            "template_id": "test_001",
            "event_type": "overtake",
            # Missing excitement_level, perspective, template_text
        }
        
        with pytest.raises(ValueError):
            library._parse_template(invalid_template)
    
    def test_load_real_template_file(self):
        """Test loading the actual enhanced_templates.json file."""
        library = TemplateLibrary()
        
        # Try to load the real template file
        template_path = "config/enhanced_templates.json"
        if Path(template_path).exists():
            library.load_templates(template_path)
            
            assert library.get_template_count() > 0
            
            # Validate all templates
            errors = library.validate_templates()
            assert errors == [], f"Template validation errors: {errors}"
            
            # Check statistics
            stats = library.get_statistics()
            assert stats['total_templates'] > 0
            assert len(stats['by_event_type']) > 0
            assert len(stats['by_excitement_level']) > 0
            assert len(stats['by_perspective']) > 0


class TestTemplateLibraryIntegration:
    """Integration tests for TemplateLibrary with real templates."""
    
    def test_load_and_retrieve_overtake_templates(self):
        """Test loading and retrieving overtake templates."""
        library = TemplateLibrary()
        template_path = "config/enhanced_templates.json"
        
        if not Path(template_path).exists():
            pytest.skip("Template file not found")
        
        library.load_templates(template_path)
        
        # Try to get overtake templates for different combinations
        for excitement in ExcitementLevel:
            for perspective in CommentaryPerspective:
                templates = library.get_templates("overtake", excitement, perspective)
                # Some combinations may not exist, that's okay
                if templates:
                    assert all(t.event_type == "overtake" for t in templates)
    
    def test_load_and_retrieve_pit_stop_templates(self):
        """Test loading and retrieving pit stop templates."""
        library = TemplateLibrary()
        template_path = "config/enhanced_templates.json"
        
        if not Path(template_path).exists():
            pytest.skip("Template file not found")
        
        library.load_templates(template_path)
        
        # Try to get pit stop templates
        templates = library.get_templates(
            "pit_stop",
            ExcitementLevel.CALM,
            CommentaryPerspective.TECHNICAL
        )
        
        if templates:
            assert all(t.event_type == "pit_stop" for t in templates)
            assert len(templates) > 0
