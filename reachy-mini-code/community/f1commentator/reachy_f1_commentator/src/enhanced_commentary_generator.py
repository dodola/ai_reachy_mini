"""
Enhanced Commentary Generator for Organic F1 Commentary.

This module provides the EnhancedCommentaryGenerator class that orchestrates
all enhanced commentary components to generate organic, context-rich commentary
that mimics real-life F1 commentators.

The generator maintains backward compatibility with the original Commentary_Generator
interface while adding rich context integration, varied commentary styles, dynamic
template selection, and compound sentence construction.

Validates: Requirements 19.1
"""

import asyncio
import logging
import time
from typing import Optional

from reachy_f1_commentator.src.commentary_generator import CommentaryGenerator
from reachy_f1_commentator.src.commentary_style_manager import CommentaryStyleManager
from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.context_enricher import ContextEnricher
from reachy_f1_commentator.src.data_ingestion import OpenF1Client
from reachy_f1_commentator.src.enhanced_models import CommentaryOutput, ContextData, EnhancedRaceEvent
from reachy_f1_commentator.src.event_prioritizer import EventPrioritizer
from reachy_f1_commentator.src.frequency_trackers import FrequencyTrackerManager
from reachy_f1_commentator.src.models import EventType, RaceEvent
from reachy_f1_commentator.src.narrative_tracker import NarrativeTracker
from reachy_f1_commentator.src.phrase_combiner import PhraseCombiner
from reachy_f1_commentator.src.placeholder_resolver import PlaceholderResolver
from reachy_f1_commentator.src.race_state_tracker import RaceStateTracker
from reachy_f1_commentator.src.template_library import TemplateLibrary
from reachy_f1_commentator.src.template_selector import TemplateSelector


logger = logging.getLogger(__name__)


class EnhancedCommentaryGenerator:
    """
    Enhanced commentary generator that orchestrates all components.
    
    This class implements the same interface as the original Commentary_Generator
    to maintain backward compatibility, while internally using the enhanced
    components to generate organic, context-rich commentary.
    
    The generation flow:
    1. Context Enricher gathers data from multiple OpenF1 endpoints
    2. Event Prioritizer calculates significance and filters events
    3. Narrative Tracker provides active story threads
    4. Commentary Style Manager selects excitement level and perspective
    5. Template Selector chooses appropriate template
    6. Phrase Combiner generates final text
    
    Validates: Requirements 19.1
    """
    
    def __init__(
        self,
        config: Config,
        state_tracker: RaceStateTracker,
        openf1_client: Optional[OpenF1Client] = None
    ):
        """
        Initialize enhanced commentary generator.
        
        Args:
            config: System configuration
            state_tracker: Race state tracker for current state data
            openf1_client: OpenF1 API client (optional, required for enhanced mode)
            
        Validates: Requirements 19.1, 19.2, 19.7, 19.8
        """
        self.config = config
        self.state_tracker = state_tracker
        self.openf1_client = openf1_client
        
        # Check if enhanced mode is enabled (Requirement 19.2)
        self.enhanced_mode = getattr(config, 'enhanced_mode', True)
        
        # Always initialize basic generator for fallback (Requirement 19.7)
        self.basic_generator = CommentaryGenerator(config, state_tracker)
        
        if self.enhanced_mode:
            logger.info("Enhanced commentary mode enabled")  # Requirement 19.8
            self._initialize_enhanced_components()
        else:
            logger.info("Enhanced commentary mode disabled, using basic mode")  # Requirement 19.8
        
        logger.info("Enhanced Commentary Generator initialized")
    
    def _initialize_enhanced_components(self):
        """
        Initialize all enhanced commentary components.
        
        If initialization fails, falls back to basic mode.
        
        Validates: Requirements 19.2, 19.7
        """
        try:
            # Initialize Context Enricher
            if self.openf1_client:
                self.context_enricher = ContextEnricher(
                    self.config,
                    self.openf1_client,
                    self.state_tracker
                )
            else:
                logger.warning(
                    "No OpenF1 client provided - context enrichment will be limited"
                )
                self.context_enricher = None
            
            # Initialize Event Prioritizer
            self.event_prioritizer = EventPrioritizer(
                self.config,
                self.state_tracker
            )
            
            # Initialize Narrative Tracker
            self.narrative_tracker = NarrativeTracker(self.config)
            
            # Initialize Commentary Style Manager
            self.style_manager = CommentaryStyleManager(self.config)
            
            # Initialize Frequency Tracker Manager
            self.frequency_trackers = FrequencyTrackerManager()
            
            # Initialize Template Library and Selector
            self.template_library = TemplateLibrary()
            template_file = getattr(self.config, 'template_file', 'config/enhanced_templates.json')
            try:
                self.template_library.load_templates(template_file)
                logger.info(f"Loaded templates from {template_file}")
            except Exception as e:
                logger.error(f"Failed to load templates from {template_file}: {e}")
                logger.warning("Enhanced commentary will fall back to basic mode")
                self.enhanced_mode = False
                return
            
            self.template_selector = TemplateSelector(
                self.config,
                self.template_library
            )
            
            # Initialize Placeholder Resolver and Phrase Combiner
            # Use the data cache from context enricher if available
            data_cache = self.context_enricher.cache if self.context_enricher else None
            if data_cache:
                self.placeholder_resolver = PlaceholderResolver(data_cache)
                self.phrase_combiner = PhraseCombiner(
                    self.config,
                    self.placeholder_resolver
                )
            else:
                logger.warning("No data cache available - placeholder resolution will be limited")
                # Create a minimal data cache
                from reachy_f1_commentator.src.openf1_data_cache import OpenF1DataCache
                minimal_cache = OpenF1DataCache(self.openf1_client, self.config) if self.openf1_client else None
                if minimal_cache:
                    self.placeholder_resolver = PlaceholderResolver(minimal_cache)
                    self.phrase_combiner = PhraseCombiner(
                        self.config,
                        self.placeholder_resolver
                    )
                else:
                    logger.error("Cannot initialize placeholder resolver without data cache")
                    self.enhanced_mode = False
                    return
            
            # Track generation metrics
            self.generation_count = 0
            self.total_generation_time_ms = 0.0
            self.total_enrichment_time_ms = 0.0
            
            # Track context data availability statistics (Requirement 16.7)
            self.context_availability_stats = {
                'total_events': 0,
                'full_context': 0,
                'partial_context': 0,
                'no_context': 0,
                'missing_sources': {},  # Track which sources are missing most often
                'fallback_activations': {
                    'context_timeout': 0,
                    'context_error': 0,
                    'generation_timeout': 0,
                    'template_fallback': 0,
                    'basic_mode_fallback': 0
                }
            }
            
            logger.info("All enhanced components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize enhanced components: {e}", exc_info=True)
            logger.warning("Falling back to basic mode")
            self.enhanced_mode = False
    
    def set_session_key(self, session_key: int) -> None:
        """
        Set the session key for data fetching.
        
        Args:
            session_key: OpenF1 session key (e.g., 9197 for 2023 Abu Dhabi GP)
        """
        if self.enhanced_mode and self.context_enricher:
            self.context_enricher.set_session_key(session_key)
            logger.info(f"Session key set to: {session_key}")
    
    def set_enhanced_mode(self, enabled: bool) -> None:
        """
        Enable or disable enhanced mode at runtime.
        
        This allows switching between enhanced and basic commentary modes
        without restarting the system.
        
        Args:
            enabled: True to enable enhanced mode, False for basic mode
            
        Validates: Requirements 19.3, 19.7
        """
        if enabled == self.enhanced_mode:
            logger.info(f"Enhanced mode already {'enabled' if enabled else 'disabled'}")
            return
        
        if enabled:
            # Switch to enhanced mode
            logger.info("Switching to enhanced commentary mode")
            self.enhanced_mode = True
            # Re-initialize enhanced components if not already done
            if not hasattr(self, 'context_enricher'):
                self._initialize_enhanced_components()
        else:
            # Switch to basic mode
            logger.info("Switching to basic commentary mode")
            self.enhanced_mode = False
        
        logger.info(f"Enhanced mode now: {'enabled' if self.enhanced_mode else 'disabled'}")
    
    def is_enhanced_mode(self) -> bool:
        """
        Check if enhanced mode is currently enabled.
        
        Returns:
            True if enhanced mode is enabled, False otherwise
            
        Validates: Requirements 19.3
        """
        return self.enhanced_mode
    
    def load_static_data(self, session_key: Optional[int] = None) -> bool:
        """
        Load static data (driver info, championship standings) at session start.
        
        Args:
            session_key: OpenF1 session key (optional)
            
        Returns:
            True if data loaded successfully, False otherwise
        """
        if self.enhanced_mode and self.context_enricher:
            return self.context_enricher.load_static_data(session_key)
        return True
    
    def generate(self, event: RaceEvent) -> str:
        """
        Generate commentary text for a race event.
        
        This is the main interface method that maintains compatibility with
        the original Commentary_Generator. It delegates to either enhanced
        or basic generation based on configuration.
        
        Args:
            event: Race event to generate commentary for
            
        Returns:
            Commentary text string
            
        Validates: Requirements 19.1, 19.2, 19.7, 16.5, 16.6
        """
        # When enhanced mode is disabled, delegate directly to basic generator (Requirement 19.7)
        if not self.enhanced_mode:
            logger.debug("Using basic commentary generator (enhanced mode disabled)")
            return self.basic_generator.generate(event)
        
        # Try enhanced generation
        try:
            # Use enhanced generation
            output = asyncio.run(self.enhanced_generate(event))
            return output.text
        except Exception as e:
            # Log fallback activation (Requirement 16.6)
            logger.error(
                f"Enhanced generation failed with error: {e} - "
                f"falling back to basic commentary",
                exc_info=True
            )
            self.context_availability_stats['fallback_activations']['basic_mode_fallback'] += 1
            
            # Fall back to basic generation (Requirement 16.5)
            return self.basic_generator.generate(event)
    
    async def enhanced_generate(self, event: RaceEvent) -> CommentaryOutput:
        """
        Generate enhanced commentary with full context enrichment.
        
        This is the main orchestration method that coordinates all enhanced
        components to generate organic, context-rich commentary.
        
        Flow:
        1. Enrich context from multiple OpenF1 endpoints (with timeout)
        2. Calculate significance and filter low-priority events
        3. Get relevant narrative threads
        4. Select commentary style (excitement and perspective)
        5. Select appropriate template
        6. Generate final commentary text
        7. Track performance metrics
        
        Args:
            event: Race event to generate commentary for
            
        Returns:
            CommentaryOutput with text and metadata
            
        Validates: Requirements 19.1, 16.5, 16.6, 16.7
        """
        start_time = time.time()
        
        # Wrap entire generation in timeout (Requirement 16.2)
        max_generation_time = getattr(self.config, 'max_generation_time_ms', 2500)
        try:
            return await asyncio.wait_for(
                self._enhanced_generate_internal(event, start_time),
                timeout=max_generation_time / 1000.0
            )
        except asyncio.TimeoutError:
            # Log fallback activation (Requirement 16.6)
            logger.warning(
                f"Commentary generation timeout after {max_generation_time}ms - "
                f"falling back to basic commentary"
            )
            self.context_availability_stats['fallback_activations']['generation_timeout'] += 1
            
            # Fall back to basic commentary (Requirement 16.5)
            basic_text = self.basic_generator.generate(event)
            generation_time_ms = (time.time() - start_time) * 1000
            
            return CommentaryOutput(
                text=basic_text,
                event=EnhancedRaceEvent(
                    base_event=event,
                    context=ContextData(
                        event=event,
                        race_state=self.state_tracker.get_state(),
                        missing_data_sources=["generation_timeout"]
                    ),
                    significance=None,
                    style=None,
                    narratives=[]
                ),
                template_used=None,
                generation_time_ms=generation_time_ms,
                context_enrichment_time_ms=0.0,
                missing_data=["generation_timeout"]
            )
    
    async def _enhanced_generate_internal(
        self,
        event: RaceEvent,
        start_time: float
    ) -> CommentaryOutput:
        """
        Internal enhanced generation method (without timeout wrapper).
        
        Args:
            event: Race event to generate commentary for
            start_time: Start time for performance tracking
            
        Returns:
            CommentaryOutput with text and metadata
        """
        
        # Step 1: Enrich context (with timeout)
        context = await self._enrich_context_with_timeout(event)
        enrichment_time_ms = context.enrichment_time_ms
        
        # Track context availability statistics (Requirement 16.7)
        self._track_context_availability(context)
        
        # Step 2: Calculate significance and filter
        significance = self.event_prioritizer.calculate_significance(event, context)
        
        # Check if event should be commentated
        if not self.event_prioritizer.should_commentate(significance):
            logger.debug(
                f"Event filtered out (significance {significance.total_score} "
                f"< threshold {self.event_prioritizer.min_threshold})"
            )
            # Return empty commentary
            generation_time_ms = (time.time() - start_time) * 1000
            return CommentaryOutput(
                text="",
                event=EnhancedRaceEvent(
                    base_event=event,
                    context=context,
                    significance=significance,
                    style=None,
                    narratives=[]
                ),
                template_used=None,
                generation_time_ms=generation_time_ms,
                context_enrichment_time_ms=enrichment_time_ms,
                missing_data=context.missing_data_sources
            )
        
        # Check for pit-cycle suppression
        if self.event_prioritizer.suppress_pit_cycle_changes(event, context):
            logger.debug("Event suppressed as pit-cycle position change")
            generation_time_ms = (time.time() - start_time) * 1000
            return CommentaryOutput(
                text="",
                event=EnhancedRaceEvent(
                    base_event=event,
                    context=context,
                    significance=significance,
                    style=None,
                    narratives=[]
                ),
                template_used=None,
                generation_time_ms=generation_time_ms,
                context_enrichment_time_ms=enrichment_time_ms,
                missing_data=context.missing_data_sources
            )
        
        # Track pit stops for pit-cycle detection
        if event.event_type == EventType.PIT_STOP:
            self.event_prioritizer.track_pit_stop(event, context)
        
        # Step 3: Get relevant narratives
        narratives = self.narrative_tracker.get_relevant_narratives(event)
        context.active_narratives = [n.narrative_id for n in narratives]
        
        # Update narrative tracker with current state
        self.narrative_tracker.update(context.race_state, context)
        
        # Step 4: Select commentary style
        style = self.style_manager.select_style(event, context, significance)
        
        # Step 4.5: Apply frequency controls to style flags
        style = self._apply_frequency_controls(style, context)
        
        # Step 5: Select template
        event_type_str = self._event_type_to_string(event.event_type)
        template = self.template_selector.select_template(
            event_type_str,
            context,
            style
        )
        
        # Step 6: Generate final text
        if template:
            commentary_text = self.phrase_combiner.generate_commentary(template, context)
        else:
            # Fallback to basic commentary if no template found (Requirement 16.5, 16.6)
            logger.warning(
                f"No template found for {event_type_str} - "
                f"falling back to basic commentary"
            )
            self.context_availability_stats['fallback_activations']['template_fallback'] += 1
            
            commentary_text = self.basic_generator.generate(event)
        
        # Step 7: Track performance metrics
        generation_time_ms = (time.time() - start_time) * 1000
        self.generation_count += 1
        self.total_generation_time_ms += generation_time_ms
        self.total_enrichment_time_ms += enrichment_time_ms
        
        # Step 8: Update frequency trackers
        self._update_frequency_trackers(style, context, template)
        
        # Log performance warning if generation took too long
        max_generation_time = getattr(self.config, 'max_generation_time_ms', 2500)
        if generation_time_ms > max_generation_time:
            logger.warning(
                f"Commentary generation exceeded target time: "
                f"{generation_time_ms:.1f}ms > {max_generation_time}ms"
            )
        
        logger.info(
            f"Generated commentary for {event.event_type.value}: {commentary_text} "
            f"(generation: {generation_time_ms:.1f}ms, enrichment: {enrichment_time_ms:.1f}ms, "
            f"significance: {significance.total_score})"
        )
        
        # Create and return output
        return CommentaryOutput(
            text=commentary_text,
            event=EnhancedRaceEvent(
                base_event=event,
                context=context,
                significance=significance,
                style=style,
                narratives=narratives
            ),
            template_used=template,
            generation_time_ms=generation_time_ms,
            context_enrichment_time_ms=enrichment_time_ms,
            missing_data=context.missing_data_sources
        )
    
    async def _enrich_context_with_timeout(self, event: RaceEvent):
        """
        Enrich context with timeout handling.
        
        Attempts to enrich context within the configured timeout. If timeout
        is exceeded, proceeds with available data.
        
        Args:
            event: Race event to enrich
            
        Returns:
            ContextData with available enrichment
            
        Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5, 16.6
        """
        if not self.context_enricher:
            # No context enricher available, create minimal context (Requirement 16.5)
            logger.warning("No context enricher available - falling back to basic mode")
            self.context_availability_stats['fallback_activations']['basic_mode_fallback'] += 1
            
            return ContextData(
                event=event,
                race_state=self.state_tracker.get_state(),
                missing_data_sources=["all - no context enricher"]
            )
        
        try:
            # Attempt context enrichment with timeout (Requirement 16.1)
            timeout_seconds = self.config.context_enrichment_timeout_ms / 1000.0
            context = await asyncio.wait_for(
                self.context_enricher.enrich_context(event),
                timeout=timeout_seconds
            )
            return context
        except asyncio.TimeoutError:
            # Log fallback activation (Requirement 16.6)
            logger.warning(
                f"Context enrichment timeout after "
                f"{self.config.context_enrichment_timeout_ms}ms - "
                f"proceeding with minimal context"
            )
            self.context_availability_stats['fallback_activations']['context_timeout'] += 1
            
            # Return minimal context (Requirement 16.5)
            return ContextData(
                event=event,
                race_state=self.state_tracker.get_state(),
                missing_data_sources=["timeout - no enrichment"],
                enrichment_time_ms=self.config.context_enrichment_timeout_ms
            )
        except Exception as e:
            # Log fallback activation (Requirement 16.6)
            logger.error(
                f"Context enrichment error: {e} - "
                f"proceeding with minimal context",
                exc_info=True
            )
            self.context_availability_stats['fallback_activations']['context_error'] += 1
            
            # Return minimal context (Requirement 16.5)
            return ContextData(
                event=event,
                race_state=self.state_tracker.get_state(),
                missing_data_sources=[f"error - {str(e)}"]
            )
    
    def _apply_frequency_controls(
        self,
        style: 'CommentaryStyle',
        context: ContextData
    ) -> 'CommentaryStyle':
        """
        Apply frequency controls to commentary style flags.
        
        Checks frequency trackers before including optional content types
        (historical, weather, championship, tire strategy). If frequency
        limit is reached, disables the corresponding flag in the style.
        
        Args:
            style: Commentary style with initial flags
            context: Enriched context data
            
        Returns:
            Modified commentary style with frequency controls applied
            
        Validates: Requirements 8.8, 11.7, 14.8, 13.8
        """
        from src.enhanced_models import CommentaryStyle
        
        # Check historical reference frequency (Requirement 8.8)
        # Historical references are included via templates, not style flags
        # But we track whether historical context is available
        include_historical = (
            self.frequency_trackers.should_include_historical() and
            self._has_historical_context(context)
        )
        
        # Check weather reference frequency (Requirement 11.7)
        include_weather = (
            style.include_technical_detail and  # Weather is part of technical detail
            self.frequency_trackers.should_include_weather() and
            self._has_weather_context(context)
        )
        
        # Check championship reference frequency (Requirement 14.8)
        include_championship = (
            style.include_championship_context and
            self.frequency_trackers.should_include_championship()
        )
        
        # Check tire strategy reference frequency (Requirement 13.8)
        # Tire strategy is included via templates for pit stops and overtakes
        # We track whether tire strategy context should be emphasized
        include_tire_strategy = (
            self.frequency_trackers.should_include_tire_strategy() and
            self._has_tire_strategy_context(context)
        )
        
        # Log frequency control decisions
        if style.include_championship_context and not include_championship:
            logger.debug(
                "Championship reference suppressed by frequency control "
                f"(current rate: {self.frequency_trackers.championship.get_current_rate():.1%})"
            )
        
        if self._has_weather_context(context) and not include_weather:
            logger.debug(
                "Weather reference suppressed by frequency control "
                f"(current rate: {self.frequency_trackers.weather.get_current_rate():.1%})"
            )
        
        # Create modified style with frequency controls applied
        modified_style = CommentaryStyle(
            excitement_level=style.excitement_level,
            perspective=style.perspective,
            include_technical_detail=include_weather if self._has_weather_context(context) else style.include_technical_detail,
            include_narrative_reference=style.include_narrative_reference,
            include_championship_context=include_championship,
        )
        
        # Store additional flags for template selection
        # These are not part of the CommentaryStyle dataclass but can be used
        # by template selector to filter templates
        modified_style._include_historical = include_historical
        modified_style._include_tire_strategy = include_tire_strategy
        
        return modified_style
    
    def _update_frequency_trackers(
        self,
        style: 'CommentaryStyle',
        context: ContextData,
        template: Optional['Template']
    ) -> None:
        """
        Update frequency trackers after generating commentary.
        
        Records whether each type of reference was included in the generated
        commentary based on the style flags and template used.
        
        Args:
            style: Commentary style used for generation
            context: Enriched context data
            template: Template used for generation (may be None for fallback)
            
        Validates: Requirements 8.8, 11.7, 14.8, 13.8
        """
        # Determine if historical reference was included
        # Historical references appear in templates with historical perspective
        # or templates with historical placeholders
        historical_included = False
        if template:
            historical_included = (
                style.perspective.value == 'historical' or
                any(p in template.optional_placeholders 
                    for p in ['first_time', 'session_record', 'overtake_count', 'back_in_position'])
            )
        
        # Determine if weather reference was included
        weather_included = False
        if template and self._has_weather_context(context):
            weather_included = (
                style.include_technical_detail and
                any(p in template.optional_placeholders 
                    for p in ['weather_condition', 'track_temp', 'air_temp'])
            )
        
        # Determine if championship reference was included
        championship_included = style.include_championship_context
        
        # Determine if tire strategy reference was included
        tire_strategy_included = False
        if template and self._has_tire_strategy_context(context):
            tire_strategy_included = any(
                p in template.optional_placeholders 
                for p in ['tire_compound', 'tire_age', 'tire_age_diff', 
                         'old_tire_compound', 'new_tire_compound']
            )
        
        # Update trackers
        self.frequency_trackers.record_historical(historical_included)
        self.frequency_trackers.record_weather(weather_included)
        self.frequency_trackers.record_championship(championship_included)
        self.frequency_trackers.record_tire_strategy(tire_strategy_included)
        
        # Log frequency statistics periodically
        if self.generation_count % 10 == 0:
            stats = self.frequency_trackers.get_statistics()
            logger.info(
                f"Frequency statistics after {self.generation_count} pieces: "
                f"historical={stats['historical']['overall_rate']:.1%}, "
                f"weather={stats['weather']['overall_rate']:.1%}, "
                f"championship={stats['championship']['overall_rate']:.1%}, "
                f"tire_strategy={stats['tire_strategy']['overall_rate']:.1%}"
            )
    
    def _has_historical_context(self, context: ContextData) -> bool:
        """
        Check if context has historical information available.
        
        Args:
            context: Enriched context data
            
        Returns:
            True if historical context is available
        """
        # Historical context is tracked in session records
        # For now, we assume it's available if we have context enricher
        return self.context_enricher is not None
    
    def _has_weather_context(self, context: ContextData) -> bool:
        """
        Check if context has weather information available.
        
        Args:
            context: Enriched context data
            
        Returns:
            True if weather context is available
        """
        return (
            context.track_temp is not None or
            context.air_temp is not None or
            context.rainfall is not None or
            context.wind_speed is not None
        )
    
    def _has_tire_strategy_context(self, context: ContextData) -> bool:
        """
        Check if context has tire strategy information available.
        
        Args:
            context: Enriched context data
            
        Returns:
            True if tire strategy context is available
        """
        return (
            context.current_tire_compound is not None or
            context.tire_age_differential is not None
        )
    
    def _event_type_to_string(self, event_type: EventType) -> str:
        """
        Convert EventType enum to string for template selection.
        
        Args:
            event_type: EventType enum value
            
        Returns:
            String representation for template lookup
        """
        # Map EventType to template event type strings
        mapping = {
            EventType.OVERTAKE: "overtake",
            EventType.PIT_STOP: "pit_stop",
            EventType.LEAD_CHANGE: "lead_change",
            EventType.FASTEST_LAP: "fastest_lap",
            EventType.INCIDENT: "incident",
            EventType.SAFETY_CAR: "safety_car",
            EventType.FLAG: "flag",
            EventType.POSITION_UPDATE: "position_update"
        }
        return mapping.get(event_type, event_type.value)
    
    def _track_context_availability(self, context: ContextData) -> None:
        """
        Track context data availability statistics.
        
        Tracks which data sources are available/missing for each event to
        provide statistics on context enrichment success rate.
        
        Args:
            context: Context data to analyze
            
        Validates: Requirements 16.7
        """
        self.context_availability_stats['total_events'] += 1
        
        # Categorize context availability
        missing_count = len(context.missing_data_sources)
        
        if missing_count == 0:
            self.context_availability_stats['full_context'] += 1
        elif missing_count < 3:  # Arbitrary threshold for "partial"
            self.context_availability_stats['partial_context'] += 1
        else:
            self.context_availability_stats['no_context'] += 1
        
        # Track which sources are missing most often
        for source in context.missing_data_sources:
            if source not in self.context_availability_stats['missing_sources']:
                self.context_availability_stats['missing_sources'][source] = 0
            self.context_availability_stats['missing_sources'][source] += 1
    
    def get_statistics(self) -> dict:
        """
        Get generation statistics for monitoring.
        
        Returns:
            Dictionary with generation metrics and context availability stats
            
        Validates: Requirements 16.7
        """
        if not self.enhanced_mode:
            return {"mode": "basic"}
        
        avg_generation_time = (
            self.total_generation_time_ms / self.generation_count
            if self.generation_count > 0 else 0
        )
        avg_enrichment_time = (
            self.total_enrichment_time_ms / self.generation_count
            if self.generation_count > 0 else 0
        )
        
        # Calculate context availability percentages (Requirement 16.7)
        total_events = self.context_availability_stats['total_events']
        context_percentages = {}
        if total_events > 0:
            context_percentages = {
                'full_context_pct': (
                    self.context_availability_stats['full_context'] / total_events * 100
                ),
                'partial_context_pct': (
                    self.context_availability_stats['partial_context'] / total_events * 100
                ),
                'no_context_pct': (
                    self.context_availability_stats['no_context'] / total_events * 100
                )
            }
        
        stats = {
            "mode": "enhanced",
            "generation_count": self.generation_count,
            "avg_generation_time_ms": avg_generation_time,
            "avg_enrichment_time_ms": avg_enrichment_time,
            "total_generation_time_ms": self.total_generation_time_ms,
            "total_enrichment_time_ms": self.total_enrichment_time_ms,
            "context_availability": {
                **self.context_availability_stats,
                **context_percentages
            }
        }
        
        # Add component statistics if available
        if hasattr(self, 'template_selector'):
            stats["template_selector"] = self.template_selector.get_statistics()
        
        if hasattr(self, 'frequency_trackers'):
            stats["frequency_trackers"] = self.frequency_trackers.get_statistics()
        
        return stats
    
    async def close(self) -> None:
        """Close all async resources."""
        if self.enhanced_mode and self.context_enricher:
            await self.context_enricher.close()
        logger.info("Enhanced Commentary Generator closed")
