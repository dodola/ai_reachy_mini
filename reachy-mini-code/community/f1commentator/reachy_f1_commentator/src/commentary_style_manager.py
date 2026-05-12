"""Commentary Style Manager for organic F1 commentary generation.

This module determines the appropriate excitement level and perspective for
commentary based on event significance and context. It ensures variety in
commentary style by tracking recent perspectives and adapting to race phase.

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 9.5, 9.6, 9.7, 9.8
"""

import logging
import random
from collections import Counter, deque
from typing import Optional

from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.enhanced_models import (
    CommentaryPerspective,
    CommentaryStyle,
    ContextData,
    ExcitementLevel,
    SignificanceScore,
)
from reachy_f1_commentator.src.models import RaceEvent, RacePhase

logger = logging.getLogger(__name__)


class CommentaryStyleManager:
    """
    Manages commentary style selection including excitement level and perspective.
    
    This class determines the appropriate tone and perspective for commentary
    based on event significance, context, and race phase. It enforces variety
    by tracking recent perspectives and avoiding repetition.
    
    Validates: Requirements 2.1, 2.6, 2.7, 2.8, 9.4, 9.5, 9.6, 9.7, 9.8
    """
    
    def __init__(self, config: Config):
        """Initialize Commentary Style Manager with configuration.
        
        Args:
            config: System configuration with style management parameters
        """
        self.config = config
        
        # Track last 5 perspectives used for variety enforcement
        self.recent_perspectives: deque = deque(maxlen=5)
        
        # Track perspectives in 10-event window for distribution enforcement
        self.perspective_window: deque = deque(maxlen=10)
        
        # Perspective weights from configuration
        self.perspective_weights = {
            CommentaryPerspective.TECHNICAL: config.perspective_weight_technical,
            CommentaryPerspective.STRATEGIC: config.perspective_weight_strategic,
            CommentaryPerspective.DRAMATIC: config.perspective_weight_dramatic,
            CommentaryPerspective.POSITIONAL: config.perspective_weight_positional,
            CommentaryPerspective.HISTORICAL: config.perspective_weight_historical,
        }
        
        logger.info("Commentary Style Manager initialized")
        logger.debug(f"Perspective weights: {self.perspective_weights}")
    
    def select_style(
        self,
        event: RaceEvent,
        context: ContextData,
        significance: SignificanceScore
    ) -> CommentaryStyle:
        """Select appropriate commentary style based on event and context.
        
        This is the main orchestrator method that combines excitement level
        determination and perspective selection to create a complete
        commentary style.
        
        Args:
            event: The race event to generate commentary for
            context: Enriched context data for the event
            significance: Significance score for the event
            
        Returns:
            CommentaryStyle with excitement level, perspective, and flags
            
        Validates: Requirements 2.1, 2.6
        """
        # Determine excitement level based on significance score
        excitement_level = self._determine_excitement(significance, context)
        
        # Select perspective ensuring variety
        perspective = self._select_perspective(event, context, significance)
        
        # Determine flags for optional content inclusion
        include_technical = self._should_include_technical(context)
        include_narrative = self._should_include_narrative(context)
        include_championship = self._should_include_championship(context)
        
        # Create and return commentary style
        style = CommentaryStyle(
            excitement_level=excitement_level,
            perspective=perspective,
            include_technical_detail=include_technical,
            include_narrative_reference=include_narrative,
            include_championship_context=include_championship,
        )
        
        # Track perspective for variety enforcement
        self.recent_perspectives.append(perspective)
        self.perspective_window.append(perspective)
        
        logger.debug(
            f"Selected style: excitement={excitement_level.name}, "
            f"perspective={perspective.value}, "
            f"technical={include_technical}, narrative={include_narrative}, "
            f"championship={include_championship}"
        )
        
        return style
    
    def _determine_excitement(
        self,
        significance: SignificanceScore,
        context: ContextData
    ) -> ExcitementLevel:
        """Map significance score to excitement level.
        
        Maps significance scores to excitement levels using configured thresholds:
        - 0-30: CALM (routine events, stable racing)
        - 31-50: MODERATE (minor position changes, routine pits)
        - 51-70: ENGAGED (interesting overtakes, strategy plays)
        - 71-85: EXCITED (top-5 battles, lead challenges)
        - 86-100: DRAMATIC (lead changes, incidents, championship moments)
        
        Adjusts excitement based on race phase (boost in final laps).
        
        Args:
            significance: Significance score for the event
            context: Enriched context data (used for race phase)
            
        Returns:
            Appropriate ExcitementLevel enum value
            
        Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5
        """
        score = significance.total_score
        
        # Apply race phase boost for final laps
        if context.race_state.race_phase == RacePhase.FINISH:
            # Boost excitement by 10 points in final laps (capped at 100)
            score = min(100, score + 10)
            logger.debug(f"Applied finish phase boost: {significance.total_score} -> {score}")
        
        # Map score to excitement level using configured thresholds
        if score <= self.config.excitement_threshold_calm:
            return ExcitementLevel.CALM
        elif score <= self.config.excitement_threshold_moderate:
            return ExcitementLevel.MODERATE
        elif score <= self.config.excitement_threshold_engaged:
            return ExcitementLevel.ENGAGED
        elif score <= self.config.excitement_threshold_excited:
            return ExcitementLevel.EXCITED
        else:
            return ExcitementLevel.DRAMATIC
    
    def _select_perspective(
        self,
        event: RaceEvent,
        context: ContextData,
        significance: SignificanceScore
    ) -> CommentaryPerspective:
        """Select perspective with variety enforcement and context preferences.
        
        Selects the most appropriate perspective based on:
        - Available context data (technical data, narratives, championship)
        - Event significance (prefer dramatic for high significance)
        - Race phase (more dramatic in final laps)
        - Variety enforcement (avoid repetition, limit usage to 40% in 10-event window)
        
        Preference rules:
        - Technical: When purple sectors or speed trap data available
        - Strategic: For pit stops and tire differentials
        - Dramatic: For high significance (>80) events
        - Positional: For championship contenders
        
        Args:
            event: The race event
            context: Enriched context data
            significance: Significance score
            
        Returns:
            Selected CommentaryPerspective enum value
            
        Validates: Requirements 2.6, 2.7, 2.8, 9.5, 9.6, 9.7, 9.8
        """
        # Calculate preference scores for each perspective
        scores = {}
        
        # Technical perspective: prefer when technical data available
        technical_score = self.perspective_weights[CommentaryPerspective.TECHNICAL]
        if self._has_technical_interest(context):
            technical_score *= 2.0  # Double weight when technical data available
        scores[CommentaryPerspective.TECHNICAL] = technical_score
        
        # Strategic perspective: prefer for pit stops and tire differentials
        strategic_score = self.perspective_weights[CommentaryPerspective.STRATEGIC]
        if self._has_strategic_interest(event, context):
            strategic_score *= 2.0  # Double weight for strategic events
        scores[CommentaryPerspective.STRATEGIC] = strategic_score
        
        # Dramatic perspective: prefer for high significance events
        dramatic_score = self.perspective_weights[CommentaryPerspective.DRAMATIC]
        if significance.total_score > 80:
            dramatic_score *= 2.0  # Double weight for high significance
        # Additional boost in final laps (Requirement 9.8)
        if context.race_state.race_phase == RacePhase.FINISH:
            dramatic_score *= 1.5  # 50% boost in final laps
        scores[CommentaryPerspective.DRAMATIC] = dramatic_score
        
        # Positional perspective: prefer for championship contenders
        positional_score = self.perspective_weights[CommentaryPerspective.POSITIONAL]
        if context.is_championship_contender:
            positional_score *= 2.0  # Double weight for championship contenders
        scores[CommentaryPerspective.POSITIONAL] = positional_score
        
        # Historical perspective: base weight only
        scores[CommentaryPerspective.HISTORICAL] = self.perspective_weights[
            CommentaryPerspective.HISTORICAL
        ]
        
        # Apply variety enforcement
        scores = self._apply_variety_enforcement(scores)
        
        # Select perspective using weighted random choice
        perspectives = list(scores.keys())
        weights = list(scores.values())
        
        # Ensure at least one perspective has non-zero weight
        if sum(weights) == 0:
            logger.warning("All perspective weights are zero, using equal distribution")
            weights = [1.0] * len(perspectives)
        
        selected = random.choices(perspectives, weights=weights, k=1)[0]
        
        logger.debug(f"Perspective scores: {scores}")
        logger.debug(f"Selected perspective: {selected.value}")
        
        return selected
    
    def _apply_variety_enforcement(
        self,
        scores: dict[CommentaryPerspective, float]
    ) -> dict[CommentaryPerspective, float]:
        """Apply variety enforcement rules to perspective scores.
        
        Enforces:
        - No consecutive repetition of same perspective
        - No perspective exceeds 40% usage in 10-event window
        
        Args:
            scores: Current perspective scores
            
        Returns:
            Adjusted scores with variety enforcement applied
            
        Validates: Requirements 2.7, 2.8, 9.7
        """
        adjusted_scores = scores.copy()
        
        # Rule 1: Avoid consecutive repetition (Requirement 2.8)
        if len(self.recent_perspectives) > 0:
            last_perspective = self.recent_perspectives[-1]
            if last_perspective in adjusted_scores:
                # Reduce weight to 10% for last used perspective
                adjusted_scores[last_perspective] *= 0.1
                logger.debug(f"Reduced weight for last perspective: {last_perspective.value}")
        
        # Rule 2: Limit usage to 40% in 10-event window (Requirement 9.7)
        if len(self.perspective_window) >= 10:
            perspective_counts = Counter(self.perspective_window)
            for perspective, count in perspective_counts.items():
                usage_percent = (count / len(self.perspective_window)) * 100
                if usage_percent >= 40:
                    # Zero out weight for perspectives at or above 40% usage
                    adjusted_scores[perspective] = 0.0
                    logger.debug(
                        f"Blocked perspective {perspective.value} "
                        f"(usage: {usage_percent:.1f}%)"
                    )
        
        return adjusted_scores
    
    def _has_technical_interest(self, context: ContextData) -> bool:
        """Check if context has technical interest (purple sectors, speed trap).
        
        Args:
            context: Enriched context data
            
        Returns:
            True if technical data is available
            
        Validates: Requirement 9.6
        """
        # Check for purple sectors
        has_purple_sector = (
            context.sector_1_status == "purple" or
            context.sector_2_status == "purple" or
            context.sector_3_status == "purple"
        )
        
        # Check for speed trap data
        has_speed_trap = context.speed_trap is not None
        
        # Check for telemetry data
        has_telemetry = context.speed is not None or context.drs_active is not None
        
        return has_purple_sector or has_speed_trap or has_telemetry
    
    def _has_strategic_interest(self, event: RaceEvent, context: ContextData) -> bool:
        """Check if event has strategic interest (pit stops, tire differentials).
        
        Args:
            event: The race event
            context: Enriched context data
            
        Returns:
            True if event has strategic interest
            
        Validates: Requirement 9.6
        """
        from src.models import EventType
        
        # Check if it's a pit stop event
        is_pit_stop = event.event_type == EventType.PIT_STOP
        
        # Check for significant tire age differential
        has_tire_differential = (
            context.tire_age_differential is not None and
            abs(context.tire_age_differential) > 5
        )
        
        # Check for different tire compounds
        has_compound_difference = (
            context.current_tire_compound is not None and
            context.tire_age_differential is not None  # Implies overtake with tire data
        )
        
        return is_pit_stop or has_tire_differential or has_compound_difference
    
    def _should_include_technical(self, context: ContextData) -> bool:
        """Determine if technical details should be included.
        
        Args:
            context: Enriched context data
            
        Returns:
            True if technical details should be included
        """
        return self._has_technical_interest(context)
    
    def _should_include_narrative(self, context: ContextData) -> bool:
        """Determine if narrative reference should be included.
        
        Args:
            context: Enriched context data
            
        Returns:
            True if narrative reference should be included
        """
        return len(context.active_narratives) > 0
    
    def _should_include_championship(self, context: ContextData) -> bool:
        """Determine if championship context should be included.
        
        Args:
            context: Enriched context data
            
        Returns:
            True if championship context should be included
        """
        return context.is_championship_contender
