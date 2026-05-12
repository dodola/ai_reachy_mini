"""
Template Library for Enhanced F1 Commentary.

This module provides the TemplateLibrary class for loading, validating, and
organizing commentary templates from JSON files.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from reachy_f1_commentator.src.enhanced_models import ExcitementLevel, CommentaryPerspective, Template

logger = logging.getLogger(__name__)


class TemplateLibrary:
    """
    Manages the template library for enhanced commentary generation.
    
    Loads templates from JSON file, validates them, and provides methods
    to retrieve templates by event type, excitement level, and perspective.
    """
    
    # Supported placeholder types
    SUPPORTED_PLACEHOLDERS = {
        # Driver placeholders
        'driver', 'driver1', 'driver2', 'pronoun', 'pronoun2', 'rival',
        # Position placeholders
        'position', 'position_before', 'positions_gained',
        # Time/Gap placeholders
        'gap', 'gap_to_leader', 'gap_trend', 'lap_time', 'time_delta',
        'sector_1_time', 'sector_2_time', 'sector_3_time',
        # Tire placeholders
        'tire_compound', 'tire_age', 'tire_age_diff', 'old_tire_compound',
        'new_tire_compound',
        # Technical placeholders
        'speed', 'speed_diff', 'speed_trap', 'drs_status', 'sector_status',
        # Pit placeholders
        'pit_duration', 'pit_lane_time',
        # Narrative placeholders
        'battle_laps', 'positions_gained_total', 'narrative_reference',
        'overtake_count',
        # Championship placeholders
        'championship_position', 'championship_gap', 'championship_context',
        # Weather placeholders
        'track_temp', 'air_temp', 'weather_condition',
        # Other
        'corner', 'team1', 'team2'
    }
    
    def __init__(self):
        """Initialize empty template library."""
        self.templates: Dict[str, List[Template]] = {}
        self.metadata: Dict = {}
        self._template_count = 0
        
    def load_templates(self, template_file: str) -> None:
        """
        Load templates from JSON file.
        
        Args:
            template_file: Path to template JSON file
            
        Raises:
            FileNotFoundError: If template file doesn't exist
            ValueError: If template file is invalid JSON
        """
        template_path = Path(template_file)
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_file}")
        
        try:
            with open(template_path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in template file: {e}")
        
        # Load metadata
        self.metadata = data.get('metadata', {})
        
        # Load templates
        template_list = data.get('templates', [])
        
        for template_data in template_list:
            try:
                template = self._parse_template(template_data)
                self._add_template(template)
            except Exception as e:
                logger.warning(f"Failed to parse template {template_data.get('template_id', 'unknown')}: {e}")
                continue
        
        self._template_count = len(template_list)
        logger.info(f"Loaded {self._template_count} templates from {template_file}")
        
    def _parse_template(self, template_data: Dict) -> Template:
        """
        Parse template data into Template object.
        
        Args:
            template_data: Dictionary containing template data
            
        Returns:
            Template object
            
        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ['template_id', 'event_type', 'excitement_level', 
                          'perspective', 'template_text']
        
        for field in required_fields:
            if field not in template_data:
                raise ValueError(f"Missing required field: {field}")
        
        return Template(
            template_id=template_data['template_id'],
            event_type=template_data['event_type'],
            excitement_level=template_data['excitement_level'],
            perspective=template_data['perspective'],
            template_text=template_data['template_text'],
            required_placeholders=template_data.get('required_placeholders', []),
            optional_placeholders=template_data.get('optional_placeholders', []),
            context_requirements=template_data.get('context_requirements', {})
        )
    
    def _add_template(self, template: Template) -> None:
        """
        Add template to library organized by key.
        
        Args:
            template: Template to add
        """
        # Create key from event_type, excitement_level, perspective
        key = f"{template.event_type}_{template.excitement_level}_{template.perspective}"
        
        if key not in self.templates:
            self.templates[key] = []
        
        self.templates[key].append(template)
    
    def get_templates(
        self,
        event_type: str,
        excitement: ExcitementLevel,
        perspective: CommentaryPerspective
    ) -> List[Template]:
        """
        Get templates matching criteria.
        
        Args:
            event_type: Type of event (overtake, pit_stop, etc.)
            excitement: Excitement level enum
            perspective: Commentary perspective enum
            
        Returns:
            List of matching templates (empty if none found)
        """
        # Convert enums to strings for key lookup
        excitement_str = excitement.name.lower()
        perspective_str = perspective.value
        
        key = f"{event_type}_{excitement_str}_{perspective_str}"
        
        return self.templates.get(key, [])
    
    def validate_templates(self) -> List[str]:
        """
        Validate all templates have valid placeholders.
        
        Returns:
            List of validation error messages (empty if all valid)
        """
        errors = []
        
        for key, template_list in self.templates.items():
            for template in template_list:
                # Extract placeholders from template text
                placeholders = self._extract_placeholders(template.template_text)
                
                # Check for unsupported placeholders
                for placeholder in placeholders:
                    if placeholder not in self.SUPPORTED_PLACEHOLDERS:
                        errors.append(
                            f"Template {template.template_id}: "
                            f"Unsupported placeholder '{placeholder}'"
                        )
                
                # Check required placeholders are in template
                for req_placeholder in template.required_placeholders:
                    if req_placeholder not in placeholders:
                        errors.append(
                            f"Template {template.template_id}: "
                            f"Required placeholder '{req_placeholder}' not in template text"
                        )
                
                # Check optional placeholders are in template
                for opt_placeholder in template.optional_placeholders:
                    if opt_placeholder not in placeholders:
                        errors.append(
                            f"Template {template.template_id}: "
                            f"Optional placeholder '{opt_placeholder}' not in template text"
                        )
        
        if errors:
            logger.warning(f"Template validation found {len(errors)} errors")
            for error in errors[:10]:  # Log first 10 errors
                logger.warning(error)
        else:
            logger.info("All templates validated successfully")
        
        return errors
    
    def _extract_placeholders(self, template_text: str) -> set:
        """
        Extract placeholder names from template text.
        
        Args:
            template_text: Template text with {placeholder} syntax
            
        Returns:
            Set of placeholder names
        """
        pattern = r'\{(\w+)\}'
        matches = re.findall(pattern, template_text)
        return set(matches)
    
    def get_template_count(self) -> int:
        """Get total number of templates loaded."""
        return self._template_count
    
    def get_template_by_id(self, template_id: str) -> Optional[Template]:
        """
        Get template by ID.
        
        Args:
            template_id: Template ID to find
            
        Returns:
            Template if found, None otherwise
        """
        for template_list in self.templates.values():
            for template in template_list:
                if template.template_id == template_id:
                    return template
        return None
    
    def get_available_combinations(self) -> List[tuple]:
        """
        Get list of available (event_type, excitement, perspective) combinations.
        
        Returns:
            List of tuples (event_type, excitement, perspective)
        """
        combinations = []
        for key in self.templates.keys():
            # Key format: {event_type}_{excitement}_{perspective}
            # Need to handle event types with underscores (e.g., pit_stop)
            # Strategy: excitement levels are known (calm, moderate, engaged, excited, dramatic)
            # Find the excitement level in the key and split there
            excitement_levels = ['calm', 'moderate', 'engaged', 'excited', 'dramatic']
            
            for excitement in excitement_levels:
                if f'_{excitement}_' in key:
                    parts = key.split(f'_{excitement}_', 1)
                    event_type = parts[0]
                    perspective = parts[1]
                    combinations.append((event_type, excitement, perspective))
                    break
        return combinations
    
    def get_statistics(self) -> Dict:
        """
        Get statistics about template library.
        
        Returns:
            Dictionary with statistics
        """
        from collections import defaultdict
        
        by_event = defaultdict(int)
        by_excitement = defaultdict(int)
        by_perspective = defaultdict(int)
        
        excitement_levels = ['calm', 'moderate', 'engaged', 'excited', 'dramatic']
        
        for key, template_list in self.templates.items():
            count = len(template_list)
            
            # Parse key by finding excitement level
            for excitement in excitement_levels:
                if f'_{excitement}_' in key:
                    parts = key.split(f'_{excitement}_', 1)
                    event_type = parts[0]
                    perspective = parts[1]
                    
                    by_event[event_type] += count
                    by_excitement[excitement] += count
                    by_perspective[perspective] += count
                    break
        
        return {
            'total_templates': self._template_count,
            'by_event_type': dict(by_event),
            'by_excitement_level': dict(by_excitement),
            'by_perspective': dict(by_perspective),
            'combinations': len(self.templates)
        }
