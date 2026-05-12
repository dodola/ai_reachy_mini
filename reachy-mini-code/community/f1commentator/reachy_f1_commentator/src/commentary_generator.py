"""
Commentary Generator module for the F1 Commentary Robot.

This module generates professional F1 commentary text from race events using
template-based and optionally AI-enhanced approaches.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.7, 5.8
"""

import random
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
from reachy_f1_commentator.src.models import RaceEvent, EventType, RacePhase
from reachy_f1_commentator.src.race_state_tracker import RaceStateTracker
from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.graceful_degradation import degradation_manager


logger = logging.getLogger(__name__)


# ============================================================================
# Commentary Templates with ElevenLabs Emotion Tags
# ============================================================================

OVERTAKE_TEMPLATES = [
    "[excited] {driver1} makes a brilliant move on {driver2} for P{position}!",
    "[excited] And {driver1} is through! That's P{position} now for {driver1}!",
    "[excited] {driver1} overtakes {driver2} - what a move!",
    "[excited] Fantastic overtake by {driver1} on {driver2}, now in P{position}!",
    "[excited] {driver1} gets past {driver2}! Up to P{position}!",
    "[excited] There it is! {driver1} takes P{position} from {driver2}!",
]

PIT_STOP_TEMPLATES = [
    "{driver} comes into the pits - that's pit stop number {pit_count}",
    "{driver} pitting now, going for {tire_compound} tires",
    "And {driver} is in the pit lane for stop number {pit_count}",
    "{driver} makes their pit stop, that's number {pit_count} for them",
    "Pit stop for {driver}, switching to {tire_compound} compound",
    "{driver} boxes! Stop number {pit_count}, approximately {pit_duration:.1f} seconds",
]

LEAD_CHANGE_TEMPLATES = [
    "[excited] {new_leader} takes the lead! {old_leader} drops to P2!",
    "[excited] We have a new race leader - it's {new_leader}!",
    "[excited] {new_leader} is now leading the race ahead of {old_leader}!",
    "[excited] Change at the front! {new_leader} leads from {old_leader}!",
    "[excited] {new_leader} moves into the lead, {old_leader} now second!",
    "[excited] And {new_leader} takes P1! {old_leader} slips to second place!",
]

FASTEST_LAP_TEMPLATES = [
    "[excited] {driver} sets the fastest lap! {lap_time:.3f} seconds!",
    "[excited] Fastest lap of the race goes to {driver} - {lap_time:.3f}!",
    "[excited] {driver} with a blistering lap time of {lap_time:.3f}!",
    "[excited] New fastest lap! {driver} with {lap_time:.3f} seconds!",
    "[excited] {driver} goes purple! Fastest lap at {lap_time:.3f}!",
]

INCIDENT_TEMPLATES = [
    "[surprised] Incident reported! {description}",
    "[surprised] We have an incident on track - {description}",
    "[surprised] Trouble on track! {description}",
    "Race control reports an incident: {description}",
    "[surprised] Drama! {description}",
]

SAFETY_CAR_TEMPLATES = [
    "[serious] Safety car deployed! {reason}",
    "[serious] The safety car is out on track - {reason}",
    "[serious] Safety car! Race neutralized due to {reason}",
    "[serious] Yellow flags and safety car - {reason}",
    "[serious] Safety car period begins - {reason}",
]

FLAG_TEMPLATES = [
    "{flag_type} flag is out!",
    "We have a {flag_type} flag condition",
    "{flag_type} flag waving!",
    "Race control shows {flag_type} flag",
]

RACE_START_TEMPLATE = "[excited] And it's lights out, and away they go!"

STARTING_GRID_TEMPLATES = [
    "After qualification, the grid looks as follows: {grid_list} [excited] And on pole position, {pole_driver}!",
]

POSITION_UPDATE_TEMPLATES = [
    "Current positions: {positions}",
    "The order is: {positions}",
    "Running order: {positions}",
]


# ============================================================================
# Commentary Style System
# ============================================================================

@dataclass
class CommentaryStyle:
    """
    Commentary style configuration based on race phase.
    
    Attributes:
        excitement_level: 0.0 to 1.0, affects template selection and tone
        detail_level: "brief", "moderate", or "detailed"
    """
    excitement_level: float  # 0.0 to 1.0
    detail_level: str  # "brief", "moderate", "detailed"


def get_style_for_phase(phase: RacePhase) -> CommentaryStyle:
    """
    Get commentary style based on race phase.
    
    Args:
        phase: Current race phase (START, MID_RACE, FINISH)
        
    Returns:
        CommentaryStyle appropriate for the phase
        
    Validates: Requirement 5.5
    """
    if phase == RacePhase.START:
        return CommentaryStyle(excitement_level=0.9, detail_level="detailed")
    elif phase == RacePhase.FINISH:
        return CommentaryStyle(excitement_level=1.0, detail_level="detailed")
    else:  # MID_RACE
        return CommentaryStyle(excitement_level=0.6, detail_level="moderate")


# ============================================================================
# Template Engine
# ============================================================================

class TemplateEngine:
    """
    Rule-based template system for generating commentary.
    
    Selects appropriate templates based on event type and populates them
    with race data and current state information.
    """
    
    def __init__(self):
        """Initialize template engine with template dictionaries."""
        self.templates = {
            EventType.OVERTAKE: OVERTAKE_TEMPLATES,
            EventType.PIT_STOP: PIT_STOP_TEMPLATES,
            EventType.LEAD_CHANGE: LEAD_CHANGE_TEMPLATES,
            EventType.FASTEST_LAP: FASTEST_LAP_TEMPLATES,
            EventType.INCIDENT: INCIDENT_TEMPLATES,
            EventType.SAFETY_CAR: SAFETY_CAR_TEMPLATES,
            EventType.FLAG: FLAG_TEMPLATES,
            EventType.POSITION_UPDATE: POSITION_UPDATE_TEMPLATES,
        }
    
    def select_template(self, event_type: EventType, style: CommentaryStyle) -> str:
        """
        Select a random template for the given event type.
        
        Args:
            event_type: Type of race event
            style: Commentary style (affects selection in future enhancements)
            
        Returns:
            Template string with placeholders
        """
        templates = self.templates.get(event_type, [])
        if not templates:
            return "Something is happening on track!"
        
        # Random selection for variety
        return random.choice(templates)
    
    def populate_template(
        self,
        template: str,
        event_data: Dict[str, Any],
        state_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Populate template with event and state data.
        
        Args:
            template: Template string with {placeholder} variables
            event_data: Data from the race event
            state_data: Additional data from race state (optional)
            
        Returns:
            Populated commentary text
        """
        # Combine event and state data
        data = {**event_data}
        if state_data:
            data.update(state_data)
        
        # Handle missing data gracefully
        try:
            return template.format(**data)
        except KeyError as e:
            logger.warning(f"[CommentaryGenerator] Missing template variable: {e}", exc_info=True)
            # Return template with available data
            return self._safe_format(template, data)
    
    def _safe_format(self, template: str, data: Dict[str, Any]) -> str:
        """
        Safely format template, replacing missing variables with placeholders.
        
        Args:
            template: Template string
            data: Available data
            
        Returns:
            Formatted string with missing variables replaced
        """
        result = template
        for key, value in data.items():
            placeholder = "{" + key + "}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        
        # Replace any remaining placeholders with generic text
        import re
        result = re.sub(r'\{[^}]+\}', '[data unavailable]', result)
        
        return result


# ============================================================================
# AI Enhancement (Optional)
# ============================================================================

class AIEnhancer:
    """
    Optional AI enhancement for commentary using language models.
    
    Enhances template-based commentary with varied phrasing while
    maintaining factual accuracy.
    """
    
    def __init__(self, config: Config):
        """
        Initialize AI enhancer with configuration.
        
        Args:
            config: System configuration with AI settings
        """
        self.config = config
        self.enabled = config.ai_enabled
        self.provider = config.ai_provider
        self.api_key = config.ai_api_key
        self.model = config.ai_model
        
        # Initialize API client based on provider
        self.client = None
        if self.enabled and self.provider != "none":
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize API client based on provider."""
        try:
            if self.provider == "openai":
                import openai
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized for AI enhancement")
            elif self.provider == "huggingface":
                # Placeholder for Hugging Face integration
                logger.warning("Hugging Face provider not yet implemented")
                self.enabled = False
        except ImportError as e:
            logger.error(f"[CommentaryGenerator] Failed to import AI provider library: {e}", exc_info=True)
            self.enabled = False
        except Exception as e:
            logger.error(f"[CommentaryGenerator] Failed to initialize AI client: {e}", exc_info=True)
            self.enabled = False
    
    def enhance(self, template_text: str, event: RaceEvent, timeout: float = 1.5) -> str:
        """
        Enhance template text with AI model.
        
        Args:
            template_text: Original template-based commentary
            event: Race event being commented on
            timeout: Maximum time to wait for AI response (seconds)
            
        Returns:
            Enhanced commentary text, or original if enhancement fails
            
        Validates: Requirement 5.3
        """
        # Check if AI is available (graceful degradation)
        if not degradation_manager.is_ai_enhancement_available():
            logger.debug("[CommentaryGenerator] AI enhancement unavailable, using template")
            return template_text
        
        if not self.enabled or not self.client:
            return template_text
        
        try:
            # Create enhancement prompt
            prompt = self._create_prompt(template_text, event)
            
            # Call AI API with timeout
            if self.provider == "openai":
                response = self._call_openai(prompt, timeout)
                if response:
                    logger.debug(f"AI enhanced commentary: {response}")
                    degradation_manager.record_ai_success()
                    return response
            
            # Fallback to template if AI fails
            logger.debug("AI enhancement failed or timed out, using template")
            degradation_manager.record_ai_failure()
            return template_text
            
        except Exception as e:
            logger.warning(f"[CommentaryGenerator] AI enhancement error: {e}", exc_info=True)
            degradation_manager.record_ai_failure()
            return template_text
    
    def _create_prompt(self, template_text: str, event: RaceEvent) -> str:
        """
        Create prompt for AI enhancement.
        
        Args:
            template_text: Original commentary
            event: Race event
            
        Returns:
            Prompt string for AI model
        """
        return f"""You are a professional F1 commentator. Enhance this commentary while keeping it factually accurate:
"{template_text}"

Make it more engaging and varied, but do not change any facts (driver names, positions, numbers, times).
Keep the response concise and suitable for live commentary.
Response:"""
    
    def _call_openai(self, prompt: str, timeout: float) -> Optional[str]:
        """
        Call OpenAI API for enhancement.
        
        Args:
            prompt: Enhancement prompt
            timeout: Request timeout in seconds
            
        Returns:
            Enhanced text or None if failed
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional F1 race commentator."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.7,
                timeout=timeout
            )
            
            if response.choices:
                return response.choices[0].message.content.strip()
            
            return None
            
        except Exception as e:
            logger.debug(f"OpenAI API call failed: {e}")
            return None


# ============================================================================
# Commentary Generator
# ============================================================================

class CommentaryGenerator:
    """
    Main commentary generator orchestrator.
    
    Generates professional F1 commentary text from race events using
    template-based approach with optional AI enhancement.
    """
    
    def __init__(self, config: Config, state_tracker: RaceStateTracker):
        """
        Initialize commentary generator.
        
        Args:
            config: System configuration
            state_tracker: Race state tracker for current state data
        """
        self.config = config
        self.state_tracker = state_tracker
        self.template_engine = TemplateEngine()
        self.ai_enhancer = AIEnhancer(config)
        
        logger.info("Commentary Generator initialized")
    
    def generate(self, event: RaceEvent) -> str:
        """
        Generate commentary text for a race event.
        
        Args:
            event: Race event to generate commentary for
            
        Returns:
            Commentary text string
            
        Validates: Requirements 5.1, 5.4
        """
        try:
            # Get current race phase and style
            race_phase = self.state_tracker.get_race_phase()
            style = get_style_for_phase(race_phase)
            
            # Apply template to generate base commentary
            commentary = self.apply_template(event, style)
            
            # Optionally enhance with AI
            if self.config.ai_enabled:
                commentary = self.ai_enhancer.enhance(commentary, event)
            
            logger.info(f"Generated commentary for {event.event_type.value}: {commentary}")
            return commentary
            
        except Exception as e:
            logger.error(f"Error generating commentary: {e}", exc_info=True)
            return "Something interesting is happening on track!"
    
    def apply_template(self, event: RaceEvent, style: CommentaryStyle) -> str:
        """
        Apply template system to generate commentary.
        
        Args:
            event: Race event
            style: Commentary style
            
        Returns:
            Template-based commentary text (empty string if event should be skipped)
            
        Validates: Requirement 5.2
        """
        # Handle race start specially
        if event.event_type == EventType.FLAG and event.data.get('is_race_start'):
            return RACE_START_TEMPLATE
        
        # Handle starting grid specially
        if event.event_type == EventType.POSITION_UPDATE and event.data.get('is_starting_grid'):
            template = random.choice(STARTING_GRID_TEMPLATES)
        else:
            # Select appropriate template
            template = self.template_engine.select_template(event.event_type, style)
        
        # Normalize event data for template compatibility
        normalized_data = self._normalize_event_data(event)
        
        # If normalization returns empty dict, skip this event
        if not normalized_data:
            logger.debug(f"Skipping event {event.event_type.value} - no data after normalization")
            return ""
        
        # Get additional state data if needed
        state_data = self._get_state_data(event)
        
        # Populate template with event and state data
        commentary = self.template_engine.populate_template(
            template,
            normalized_data,
            state_data
        )
        
        return commentary
    
    def _get_state_data(self, event: RaceEvent) -> Dict[str, Any]:
        """
        Get additional state data for commentary enhancement.
        
        Args:
            event: Race event
            
        Returns:
            Dictionary of state data
        """
        state_data = {}
        
        # Add leader information
        leader = self.state_tracker.get_leader()
        if leader:
            state_data['leader'] = leader.name
            state_data['leader_position'] = leader.position
        
        # Add race phase
        state_data['race_phase'] = self.state_tracker.get_race_phase().value
        
        # Add event-specific state data
        if event.event_type == EventType.OVERTAKE:
            # Get position information
            driver = event.data.get('overtaking_driver')
            if driver:
                driver_state = self.state_tracker.get_driver(driver)
                if driver_state:
                    state_data['gap_to_leader'] = driver_state.gap_to_leader
        
        return state_data
    
    def _normalize_event_data(self, event: RaceEvent) -> Dict[str, Any]:
        """
        Normalize event data to match template variable names.
        
        Args:
            event: Race event
            
        Returns:
            Normalized data dictionary
        """
        data = event.data.copy()
        
        # Normalize overtake event data
        if event.event_type == EventType.OVERTAKE:
            if 'overtaking_driver' in data:
                data['driver1'] = data['overtaking_driver']
            if 'overtaken_driver' in data:
                data['driver2'] = data['overtaken_driver']
            if 'new_position' in data:
                data['position'] = data['new_position']
        
        # Normalize pit stop event data
        elif event.event_type == EventType.PIT_STOP:
            # Already uses 'driver', 'pit_count', 'tire_compound', 'pit_duration'
            pass
        
        # Normalize lead change event data
        elif event.event_type == EventType.LEAD_CHANGE:
            # Already uses 'new_leader', 'old_leader'
            pass
        
        # Normalize fastest lap event data
        elif event.event_type == EventType.FASTEST_LAP:
            # Already uses 'driver', 'lap_time'
            pass
        
        # Normalize incident event data
        elif event.event_type == EventType.INCIDENT:
            # Already uses 'description'
            pass
        
        # Normalize safety car event data
        elif event.event_type == EventType.SAFETY_CAR:
            # Already uses 'reason'
            pass
        
        # Normalize flag event data
        elif event.event_type == EventType.FLAG:
            # Already uses 'flag_type'
            pass
        
        # Normalize starting grid data
        elif event.event_type == EventType.POSITION_UPDATE and data.get('is_starting_grid'):
            # Format starting grid as a countdown from back to front (P20 to P1)
            # Grid positions are side-by-side: P2/P1 (front row), P4/P3 (row 2), etc.
            grid = data.get('starting_grid', [])
            if grid:
                grid_announcements = []
                
                # Count down from back to front in pairs
                # Grid is P1, P2, P3, P4... so we go backwards
                total_drivers = len(grid)
                
                # Process in pairs from back to front
                # Start from the last pair and work forward
                i = total_drivers - 1
                while i >= 2:  # Stop before the front row (P1 and P2)
                    # Get pair (odd position on left, even on right in F1 grid)
                    driver_odd = grid[i] if i < total_drivers else None
                    driver_even = grid[i-1] if i-1 < total_drivers else None
                    
                    if driver_odd and driver_even:
                        name_odd = driver_odd.get('full_name', 'Unknown')
                        name_even = driver_even.get('full_name', 'Unknown')
                        
                        # Calculate row number from back
                        row_num = (i + 1) // 2
                        
                        grid_announcements.append(
                            f"On row {row_num}, {name_odd} and {name_even}"
                        )
                    
                    i -= 2  # Move to next pair
                
                # Handle front row specially (P2 and P1)
                if total_drivers >= 2:
                    p2_driver = grid[1].get('full_name', 'Unknown')
                    grid_announcements.append(f"On the front row, {p2_driver}")
                
                # Join all announcements
                if grid_announcements:
                    data['grid_list'] = '. '.join(grid_announcements)
                else:
                    data['grid_list'] = ""
                
                # Add pole position driver separately
                if grid:
                    data['pole_driver'] = grid[0].get('full_name', 'Unknown')
        
        # Normalize regular position update data (during race)
        elif event.event_type == EventType.POSITION_UPDATE:
            # Position updates are frequent but not very interesting
            # We'll skip most of them but show occasional updates
            # For now, skip all non-starting-grid position updates
            # TODO: Implement logic to show periodic position updates (every 5 laps?)
            logger.debug("Skipping regular position update (not starting grid)")
            return {}  # Return empty dict to skip this event
        
        return data
