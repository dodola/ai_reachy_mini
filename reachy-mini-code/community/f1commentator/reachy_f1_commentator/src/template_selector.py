"""
Template Selector for Enhanced F1 Commentary.

This module provides the TemplateSelector class for choosing appropriate
commentary templates based on event type, style, and context variables.
"""

import logging
import random
from collections import deque
from typing import List, Optional

from reachy_f1_commentator.src.enhanced_models import (
    ContextData,
    CommentaryStyle,
    Template,
    ExcitementLevel,
    CommentaryPerspective
)
from reachy_f1_commentator.src.template_library import TemplateLibrary
from reachy_f1_commentator.src.config import Config

logger = logging.getLogger(__name__)


class TemplateSelector:
    """
    Selects appropriate commentary templates based on context.
    
    Filters templates by event type, excitement level, and perspective,
    then scores them based on context match quality. Avoids repetition
    by tracking recently used templates.
    """
    
    def __init__(self, config: Config, template_library: TemplateLibrary):
        """
        Initialize template selector.
        
        Args:
            config: Configuration object with template selection parameters
            template_library: Loaded template library
        """
        self.config = config
        self.template_library = template_library
        
        # Track recently used templates to avoid repetition
        repetition_window = getattr(
            config, 
            'template_repetition_window', 
            10
        )
        self.recent_templates: deque = deque(maxlen=repetition_window)
        
        logger.info(
            f"TemplateSelector initialized with repetition window of {repetition_window}"
        )
    
    def select_template(
        self,
        event_type: str,
        context: ContextData,
        style: CommentaryStyle
    ) -> Optional[Template]:
        """
        Select appropriate template based on all context.
        
        Args:
            event_type: Type of event (overtake, pit_stop, etc.)
            context: Enriched context data
            style: Commentary style (excitement, perspective)
            
        Returns:
            Selected template, or None if no suitable template found
        """
        # Get templates matching event type, excitement, and perspective
        templates = self.template_library.get_templates(
            event_type=event_type,
            excitement=style.excitement_level,
            perspective=style.perspective
        )
        
        if not templates:
            logger.warning(
                f"No templates found for {event_type}, "
                f"{style.excitement_level.name}, {style.perspective.value}"
            )
            return self._fallback_template(event_type, context, style)
        
        logger.debug(
            f"Found {len(templates)} templates for {event_type}, "
            f"{style.excitement_level.name}, {style.perspective.value}"
        )
        
        # Filter by context requirements
        filtered_templates = self._filter_by_context(templates, context)
        
        if not filtered_templates:
            logger.debug(
                f"No templates match context requirements, "
                f"falling back to simpler template"
            )
            return self._fallback_template(event_type, context, style)
        
        # Avoid recently used templates
        non_repeated_templates = self._avoid_repetition(filtered_templates)
        
        if not non_repeated_templates:
            logger.debug(
                f"All templates recently used, allowing repetition"
            )
            non_repeated_templates = filtered_templates
        
        # Score templates by context match quality
        scored_templates = [
            (template, self._score_template(template, context))
            for template in non_repeated_templates
        ]
        
        # Sort by score (descending)
        scored_templates.sort(key=lambda x: x[1], reverse=True)
        
        # Randomly select from top 3 scored templates
        top_templates = scored_templates[:3]
        selected_template = random.choice(top_templates)[0]
        
        # Track selected template
        self.recent_templates.append(selected_template.template_id)
        
        logger.debug(
            f"Selected template {selected_template.template_id} "
            f"(score: {scored_templates[0][1]:.2f})"
        )
        
        return selected_template
    
    def _filter_by_context(
        self,
        templates: List[Template],
        context: ContextData
    ) -> List[Template]:
        """
        Filter templates by available context data.
        
        Removes templates that require data not available in context.
        
        Args:
            templates: List of candidate templates
            context: Enriched context data
            
        Returns:
            List of templates with satisfied context requirements
        """
        filtered = []
        
        for template in templates:
            # Check if all context requirements are met
            requirements_met = True
            
            for req_key, req_value in template.context_requirements.items():
                # If requirement is False, it's optional (doesn't require the data)
                if not req_value:
                    continue
                
                # Check if required data is available
                if req_key == 'tire_data':
                    if context.current_tire_compound is None:
                        requirements_met = False
                        break
                elif req_key == 'gap_data':
                    if context.gap_to_leader is None and context.gap_to_ahead is None:
                        requirements_met = False
                        break
                elif req_key == 'telemetry_data':
                    if context.speed is None and context.drs_active is None:
                        requirements_met = False
                        break
                elif req_key == 'weather_data':
                    if context.track_temp is None and context.air_temp is None:
                        requirements_met = False
                        break
                elif req_key == 'championship_data':
                    if context.driver_championship_position is None:
                        requirements_met = False
                        break
                elif req_key == 'battle_narrative':
                    if not any('battle' in n.lower() for n in context.active_narratives):
                        requirements_met = False
                        break
                elif req_key == 'sector_data':
                    if (context.sector_1_time is None and 
                        context.sector_2_time is None and 
                        context.sector_3_time is None):
                        requirements_met = False
                        break
            
            if requirements_met:
                filtered.append(template)
        
        logger.debug(
            f"Filtered {len(templates)} templates to {len(filtered)} "
            f"based on context requirements"
        )
        
        return filtered
    
    def _score_template(
        self,
        template: Template,
        context: ContextData
    ) -> float:
        """
        Score template based on context match quality.
        
        Higher scores indicate better match with available context.
        
        Args:
            template: Template to score
            context: Enriched context data
            
        Returns:
            Score (0.0-10.0)
        """
        score = 5.0  # Base score
        
        # Bonus for optional placeholders that have data available
        for placeholder in template.optional_placeholders:
            if self._has_data_for_placeholder(placeholder, context):
                score += 0.5
        
        # Bonus for context-rich templates when data is available
        if len(template.optional_placeholders) > 3:
            # Complex template with many optional fields
            available_count = sum(
                1 for p in template.optional_placeholders
                if self._has_data_for_placeholder(p, context)
            )
            if available_count >= len(template.optional_placeholders) * 0.7:
                score += 2.0  # Most optional data available
        
        # Bonus for narrative references when narratives are active
        if 'narrative_reference' in template.optional_placeholders:
            if context.active_narratives:
                score += 1.5
        
        # Bonus for championship context when driver is contender
        if 'championship_context' in template.optional_placeholders:
            if context.is_championship_contender:
                score += 1.5
        
        # Bonus for tire data when significant tire age differential exists
        if 'tire_age_diff' in template.optional_placeholders:
            if context.tire_age_differential and context.tire_age_differential > 5:
                score += 1.0
        
        # Bonus for gap data when gap is close
        if 'gap' in template.optional_placeholders or 'gap_to_leader' in template.optional_placeholders:
            if context.gap_to_ahead and context.gap_to_ahead < 1.0:
                score += 1.0
        
        # Bonus for DRS when active
        if 'drs_status' in template.optional_placeholders:
            if context.drs_active:
                score += 0.5
        
        return score
    
    def _has_data_for_placeholder(
        self,
        placeholder: str,
        context: ContextData
    ) -> bool:
        """
        Check if context has data for a placeholder.
        
        Args:
            placeholder: Placeholder name
            context: Enriched context data
            
        Returns:
            True if data is available, False otherwise
        """
        # Map placeholders to context fields
        placeholder_map = {
            'speed': context.speed,
            'speed_diff': context.speed,
            'speed_trap': context.speed_trap,
            'drs_status': context.drs_active,
            'gap': context.gap_to_ahead,
            'gap_to_leader': context.gap_to_leader,
            'gap_trend': context.gap_trend,
            'tire_compound': context.current_tire_compound,
            'tire_age': context.current_tire_age,
            'tire_age_diff': context.tire_age_differential,
            'old_tire_compound': context.previous_tire_compound,
            'new_tire_compound': context.current_tire_compound,
            'sector_1_time': context.sector_1_time,
            'sector_2_time': context.sector_2_time,
            'sector_3_time': context.sector_3_time,
            'sector_status': context.sector_1_status,
            'pit_duration': context.pit_duration,
            'pit_lane_time': context.pit_lane_time,
            'track_temp': context.track_temp,
            'air_temp': context.air_temp,
            'weather_condition': context.track_temp or context.rainfall,
            'championship_position': context.driver_championship_position,
            'championship_gap': context.championship_gap_to_leader,
            'championship_context': context.driver_championship_position,
            'narrative_reference': len(context.active_narratives) > 0,
            'battle_laps': len(context.active_narratives) > 0,
            'positions_gained_total': context.positions_gained,
            'overtake_count': True,  # Tracked separately
        }
        
        return placeholder_map.get(placeholder, False) is not None and \
               placeholder_map.get(placeholder, False) is not False
    
    def _avoid_repetition(
        self,
        templates: List[Template]
    ) -> List[Template]:
        """
        Filter out recently used templates.
        
        Args:
            templates: List of candidate templates
            
        Returns:
            List of templates not recently used
        """
        return [
            template for template in templates
            if template.template_id not in self.recent_templates
        ]
    
    def _fallback_template(
        self,
        event_type: str,
        context: ContextData,
        style: CommentaryStyle
    ) -> Optional[Template]:
        """
        Find a simpler fallback template when no match found.
        
        Tries progressively simpler criteria:
        1. Same event type, any excitement, any perspective
        2. Same event type, calm excitement, any perspective
        3. None (will trigger basic commentary)
        
        Args:
            event_type: Type of event
            context: Enriched context data
            style: Commentary style
            
        Returns:
            Fallback template, or None if no fallback available
        """
        logger.debug(f"Attempting fallback for {event_type}")
        
        # Try all perspectives with same event type and excitement
        for perspective in CommentaryPerspective:
            templates = self.template_library.get_templates(
                event_type=event_type,
                excitement=style.excitement_level,
                perspective=perspective
            )
            
            if templates:
                # Filter by context and avoid repetition
                filtered = self._filter_by_context(templates, context)
                non_repeated = self._avoid_repetition(filtered) if filtered else []
                
                if non_repeated:
                    selected = random.choice(non_repeated)
                    self.recent_templates.append(selected.template_id)
                    logger.info(
                        f"Fallback: selected {selected.template_id} "
                        f"with different perspective"
                    )
                    return selected
        
        # Try calm excitement with any perspective
        for perspective in CommentaryPerspective:
            templates = self.template_library.get_templates(
                event_type=event_type,
                excitement=ExcitementLevel.CALM,
                perspective=perspective
            )
            
            if templates:
                # Filter by context and avoid repetition
                filtered = self._filter_by_context(templates, context)
                non_repeated = self._avoid_repetition(filtered) if filtered else []
                
                if non_repeated:
                    selected = random.choice(non_repeated)
                    self.recent_templates.append(selected.template_id)
                    logger.info(
                        f"Fallback: selected {selected.template_id} "
                        f"with calm excitement"
                    )
                    return selected
        
        logger.warning(f"No fallback template found for {event_type}")
        return None
    
    def reset_history(self):
        """Reset the recent templates history."""
        self.recent_templates.clear()
        logger.debug("Template selection history reset")
    
    def get_statistics(self) -> dict:
        """
        Get statistics about template selection.
        
        Returns:
            Dictionary with selection statistics
        """
        return {
            'recent_templates_count': len(self.recent_templates),
            'recent_templates': list(self.recent_templates),
            'repetition_window': self.recent_templates.maxlen
        }
