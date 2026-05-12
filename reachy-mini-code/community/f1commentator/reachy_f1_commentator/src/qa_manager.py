"""
Q&A Manager module for the F1 Commentary Robot.

This module handles viewer questions about race state, parsing questions
to identify intent, generating natural language responses, and managing
event queue pausing during Q&A interactions.
"""

import logging
import re
import threading
import time
from enum import Enum
from dataclasses import dataclass
from typing import Optional

from reachy_f1_commentator.src.models import RaceState
from reachy_f1_commentator.src.race_state_tracker import RaceStateTracker
from reachy_f1_commentator.src.event_queue import PriorityEventQueue


logger = logging.getLogger(__name__)


# ============================================================================
# Query Intent Models
# ============================================================================

class IntentType(Enum):
    """Types of questions that can be asked."""
    POSITION = "position"        # "Where is Hamilton?"
    PIT_STATUS = "pit_status"    # "Has Verstappen pitted?"
    GAP = "gap"                  # "What's the gap to the leader?"
    FASTEST_LAP = "fastest_lap"  # "Who has the fastest lap?"
    LEADER = "leader"            # "Who's leading?"
    UNKNOWN = "unknown"          # Unrecognized question


@dataclass
class QueryIntent:
    """Parsed question intent with extracted information."""
    intent_type: IntentType
    driver_name: Optional[str] = None


# ============================================================================
# Question Parser
# ============================================================================

class QuestionParser:
    """
    Parses user questions to identify query intent and extract driver names.
    
    Uses keyword-based parsing to determine what the user is asking about
    and extracts relevant driver names from the question text.
    """
    
    # Common F1 driver names for extraction (can be expanded)
    DRIVER_NAMES = [
        "verstappen", "hamilton", "leclerc", "sainz", "perez", "russell",
        "norris", "piastri", "alonso", "stroll", "ocon", "gasly",
        "bottas", "zhou", "magnussen", "hulkenberg", "tsunoda", "ricciardo",
        "albon", "sargeant", "max", "lewis", "charles", "carlos", "sergio",
        "george", "lando", "oscar", "fernando", "lance", "esteban", "pierre",
        "valtteri", "guanyu", "kevin", "nico", "yuki", "daniel", "alex", "logan"
    ]
    
    def parse_intent(self, question: str) -> QueryIntent:
        """
        Parse question to identify query type.
        
        Args:
            question: User's question text
            
        Returns:
            QueryIntent with identified intent type and driver name (if applicable)
        """
        question_lower = question.lower().strip()
        
        # Extract driver name first
        driver_name = self.extract_driver_name(question_lower)
        
        # Determine intent based on keywords
        # Check leader query first (before position) to handle "P1" and "first" correctly
        if self._is_leader_query(question_lower):
            return QueryIntent(IntentType.LEADER, None)
        elif self._is_position_query(question_lower):
            return QueryIntent(IntentType.POSITION, driver_name)
        elif self._is_pit_status_query(question_lower):
            return QueryIntent(IntentType.PIT_STATUS, driver_name)
        elif self._is_gap_query(question_lower):
            return QueryIntent(IntentType.GAP, driver_name)
        elif self._is_fastest_lap_query(question_lower):
            return QueryIntent(IntentType.FASTEST_LAP, None)
        else:
            return QueryIntent(IntentType.UNKNOWN, None)
    
    def extract_driver_name(self, question: str) -> Optional[str]:
        """
        Extract driver name from question using keyword matching.
        
        Args:
            question: Question text (should be lowercase)
            
        Returns:
            Driver name if found, None otherwise
        """
        question_lower = question.lower()
        
        # Look for driver names in the question
        for name in self.DRIVER_NAMES:
            if name in question_lower:
                # Return capitalized version
                return name.capitalize()
        
        return None
    
    def _is_position_query(self, question: str) -> bool:
        """Check if question is asking about driver position."""
        position_keywords = [
            "position", "where is", "where's", "what position",
            "p1", "p2", "p3", "place", "standing"
        ]
        return any(keyword in question for keyword in position_keywords)
    
    def _is_pit_status_query(self, question: str) -> bool:
        """Check if question is asking about pit stop status."""
        pit_keywords = [
            "pit", "pitted", "pit stop", "tire", "tyre",
            "compound", "stop"
        ]
        return any(keyword in question for keyword in pit_keywords)
    
    def _is_gap_query(self, question: str) -> bool:
        """Check if question is asking about time gap."""
        gap_keywords = [
            "gap", "behind", "ahead", "time difference",
            "how far", "distance"
        ]
        return any(keyword in question for keyword in gap_keywords)
    
    def _is_fastest_lap_query(self, question: str) -> bool:
        """Check if question is asking about fastest lap."""
        fastest_lap_keywords = [
            "fastest lap", "quickest lap", "best lap",
            "fastest time", "lap record"
        ]
        return any(keyword in question for keyword in fastest_lap_keywords)
    
    def _is_leader_query(self, question: str) -> bool:
        """Check if question is asking about race leader."""
        # Check for leader-specific patterns first
        leader_patterns = [
            "who's leading", "who is leading",
            "who's winning", "who is winning",
            "who is in first", "who's in first"
        ]
        
        # Check exact patterns first
        for pattern in leader_patterns:
            if pattern in question:
                return True
        
        # Check for standalone "lead" or "first" without driver context
        leader_keywords = ["lead", "first", "in front"]
        
        # Only match if it's a "who" question about leading/first
        if "who" in question:
            return any(keyword in question for keyword in leader_keywords)
        
        return False


# ============================================================================
# Response Generator
# ============================================================================

class ResponseGenerator:
    """
    Generates natural language responses to user questions.
    
    Creates responses based on parsed intent and current race state data,
    using templates populated with real-time information.
    """
    
    def generate_response(self, intent: QueryIntent, state_tracker: RaceStateTracker) -> str:
        """
        Generate natural language response based on intent and race state.
        
        Args:
            intent: Parsed query intent
            state_tracker: Race state tracker for current data
            
        Returns:
            Natural language response string
        """
        if intent.intent_type == IntentType.POSITION:
            return self._generate_position_response(intent.driver_name, state_tracker)
        elif intent.intent_type == IntentType.PIT_STATUS:
            return self._generate_pit_status_response(intent.driver_name, state_tracker)
        elif intent.intent_type == IntentType.GAP:
            return self._generate_gap_response(intent.driver_name, state_tracker)
        elif intent.intent_type == IntentType.FASTEST_LAP:
            return self._generate_fastest_lap_response(state_tracker)
        elif intent.intent_type == IntentType.LEADER:
            return self._generate_leader_response(state_tracker)
        else:
            return "I don't have that information right now"
    
    def _generate_position_response(self, driver_name: Optional[str], 
                                   state_tracker: RaceStateTracker) -> str:
        """Generate response for position query."""
        if not driver_name:
            return "I don't have that information right now"
        
        driver = state_tracker.get_driver(driver_name)
        if not driver:
            return f"I don't have information about {driver_name} right now"
        
        gap_text = ""
        if driver.position > 1:
            gap_text = f", {driver.gap_to_leader:.1f} seconds behind the leader"
        
        return f"{driver.name} is currently in P{driver.position}{gap_text}."
    
    def _generate_pit_status_response(self, driver_name: Optional[str],
                                      state_tracker: RaceStateTracker) -> str:
        """Generate response for pit status query."""
        if not driver_name:
            return "I don't have that information right now"
        
        driver = state_tracker.get_driver(driver_name)
        if not driver:
            return f"I don't have information about {driver_name} right now"
        
        if driver.pit_count == 0:
            return f"{driver.name} has not pitted yet."
        else:
            tire_info = ""
            if driver.current_tire and driver.current_tire != "unknown":
                tire_info = f", currently on {driver.current_tire} tires"
            
            stop_text = "stop" if driver.pit_count == 1 else "stops"
            return f"{driver.name} has made {driver.pit_count} pit {stop_text}{tire_info}."
    
    def _generate_gap_response(self, driver_name: Optional[str],
                               state_tracker: RaceStateTracker) -> str:
        """Generate response for gap query."""
        if not driver_name:
            # If no driver specified, give gap between leader and P2
            leader = state_tracker.get_leader()
            positions = state_tracker.get_positions()
            
            if not leader or len(positions) < 2:
                return "I don't have that information right now"
            
            second_place = positions[1]
            return f"The gap between {leader.name} and {second_place.name} is {second_place.gap_to_leader:.1f} seconds."
        
        driver = state_tracker.get_driver(driver_name)
        if not driver:
            return f"I don't have information about {driver_name} right now"
        
        if driver.position == 1:
            return f"{driver.name} is leading the race."
        
        return f"{driver.name} is {driver.gap_to_leader:.1f} seconds behind the leader."
    
    def _generate_fastest_lap_response(self, state_tracker: RaceStateTracker) -> str:
        """Generate response for fastest lap query."""
        positions = state_tracker.get_positions()
        if not positions:
            return "I don't have that information right now"
        
        # Get fastest lap from race state
        fastest_driver = None
        fastest_time = float('inf')
        
        for driver in positions:
            if driver.last_lap_time > 0 and driver.last_lap_time < fastest_time:
                fastest_time = driver.last_lap_time
                fastest_driver = driver
        
        if not fastest_driver:
            return "I don't have that information right now"
        
        return f"{fastest_driver.name} has the fastest lap with a time of {fastest_time:.3f} seconds."
    
    def _generate_leader_response(self, state_tracker: RaceStateTracker) -> str:
        """Generate response for leader query."""
        leader = state_tracker.get_leader()
        if not leader:
            return "I don't have that information right now"
        
        positions = state_tracker.get_positions()
        if len(positions) > 1:
            second_place = positions[1]
            gap_text = f", {second_place.gap_to_leader:.1f} seconds ahead of {second_place.name}"
        else:
            gap_text = ""
        
        return f"{leader.name} is currently leading the race{gap_text}."


# ============================================================================
# Q&A Manager Orchestrator
# ============================================================================

class QAManager:
    """
    Main Q&A orchestrator that handles viewer questions.
    
    Manages the complete Q&A flow: parsing questions, pausing event queue,
    generating responses, routing to speech synthesizer, and resuming
    event processing. Runs in a separate thread for asynchronous operation.
    """
    
    def __init__(self, state_tracker: RaceStateTracker, event_queue: PriorityEventQueue):
        """
        Initialize Q&A Manager.
        
        Args:
            state_tracker: Race state tracker for current data
            event_queue: Event queue to pause/resume during Q&A
        """
        self._state_tracker = state_tracker
        self._event_queue = event_queue
        self._parser = QuestionParser()
        self._response_generator = ResponseGenerator()
        self._timeout = 3.0  # 3 second timeout for response generation
    
    def process_question(self, question: str) -> str:
        """
        Process user question and generate response.
        
        This method:
        1. Pauses the event queue (if available)
        2. Parses the question to identify intent
        3. Queries race state for data
        4. Generates natural language response
        5. Returns response (caller should route to speech synthesizer)
        6. Resumes event queue (caller's responsibility after audio completes)
        
        Args:
            question: User's question text
            
        Returns:
            Natural language response string
        """
        start_time = time.time()
        
        try:
            # Pause event queue during Q&A (if available)
            if self._event_queue is not None:
                self._event_queue.pause()
            
            # Parse question to identify intent
            intent = self._parser.parse_intent(question)
            
            # Generate response based on intent and current state
            response = self._response_generator.generate_response(intent, self._state_tracker)
            
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > self._timeout:
                return "I don't have that information right now"
            
            return response
            
        except Exception as e:
            # Log error and return default response
            logger.error(f"[QAManager] Error processing question: {e}", exc_info=True)
            return "I don't have that information right now"
    
    def resume_event_queue(self) -> None:
        """
        Resume event queue after Q&A response is complete.
        
        Should be called after the response audio has finished playing.
        """
        if self._event_queue is not None:
            self._event_queue.resume()
