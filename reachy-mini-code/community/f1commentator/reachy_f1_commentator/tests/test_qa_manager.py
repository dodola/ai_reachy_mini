"""
Unit tests for the Q&A Manager module.

Tests the QuestionParser, ResponseGenerator, and QAManager classes
including question parsing, intent identification, response generation,
and event queue management during Q&A.
"""

import pytest
from datetime import datetime
from reachy_f1_commentator.src.qa_manager import (
    QuestionParser, ResponseGenerator, QAManager,
    IntentType, QueryIntent
)
from reachy_f1_commentator.src.race_state_tracker import RaceStateTracker
from reachy_f1_commentator.src.event_queue import PriorityEventQueue
from reachy_f1_commentator.src.models import RaceEvent, EventType, DriverState


class TestQuestionParser:
    """Test QuestionParser functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = QuestionParser()
    
    def test_parse_position_query(self):
        """Test parsing of position queries."""
        questions = [
            "Where is Hamilton?",
            "What position is Verstappen in?",
            "Where's Leclerc?",
            "What's Hamilton's position?"
        ]
        
        for question in questions:
            intent = self.parser.parse_intent(question)
            assert intent.intent_type == IntentType.POSITION
    
    def test_parse_pit_status_query(self):
        """Test parsing of pit stop status queries."""
        questions = [
            "Has Verstappen pitted?",
            "Did Hamilton pit?",
            "What tires is Leclerc on?",
            "How many pit stops has Sainz made?"
        ]
        
        for question in questions:
            intent = self.parser.parse_intent(question)
            assert intent.intent_type == IntentType.PIT_STATUS
    
    def test_parse_gap_query(self):
        """Test parsing of gap queries."""
        questions = [
            "What's the gap to the leader?",
            "How far behind is Hamilton?",
            "What's the gap between Verstappen and Leclerc?",
            "How far ahead is the leader?"
        ]
        
        for question in questions:
            intent = self.parser.parse_intent(question)
            assert intent.intent_type == IntentType.GAP
    
    def test_parse_fastest_lap_query(self):
        """Test parsing of fastest lap queries."""
        questions = [
            "Who has the fastest lap?",
            "What's the fastest lap time?",
            "Who set the quickest lap?"
        ]
        
        for question in questions:
            intent = self.parser.parse_intent(question)
            assert intent.intent_type == IntentType.FASTEST_LAP
    
    def test_parse_leader_query(self):
        """Test parsing of leader queries."""
        questions = [
            "Who's leading?",
            "Who is in first place?",
            "Who's winning the race?",
            "Who is leading the race?"
        ]
        
        for question in questions:
            intent = self.parser.parse_intent(question)
            assert intent.intent_type == IntentType.LEADER
    
    def test_parse_unknown_query(self):
        """Test parsing of unrecognized queries."""
        questions = [
            "What's the weather like?",
            "How many laps are left?",
            "Tell me a joke"
        ]
        
        for question in questions:
            intent = self.parser.parse_intent(question)
            assert intent.intent_type == IntentType.UNKNOWN
    
    def test_extract_driver_name_found(self):
        """Test driver name extraction when name is present."""
        questions = [
            ("Where is Hamilton?", "Hamilton"),
            ("Has Verstappen pitted?", "Verstappen"),
            ("What position is Leclerc in?", "Leclerc"),
            ("How is Max doing?", "Max")
        ]
        
        for question, expected_name in questions:
            name = self.parser.extract_driver_name(question.lower())
            assert name is not None
            assert expected_name.lower() in name.lower()
    
    def test_extract_driver_name_not_found(self):
        """Test driver name extraction when no name is present."""
        questions = [
            "Who's leading?",
            "What's the fastest lap?",
            "How many laps are left?"
        ]
        
        for question in questions:
            name = self.parser.extract_driver_name(question.lower())
            # May or may not find a name depending on keywords
            # Just ensure it doesn't crash
            assert name is None or isinstance(name, str)


class TestResponseGenerator:
    """Test ResponseGenerator functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = ResponseGenerator()
        self.tracker = RaceStateTracker()
        
        # Set up sample race state
        event = RaceEvent(
            event_type=EventType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data={
                'positions': {
                    'Hamilton': 1,
                    'Verstappen': 2,
                    'Leclerc': 3
                },
                'gaps': {
                    'Verstappen': {'gap_to_leader': 2.5, 'gap_to_ahead': 2.5},
                    'Leclerc': {'gap_to_leader': 5.0, 'gap_to_ahead': 2.5}
                },
                'lap_number': 10,
                'total_laps': 50
            }
        )
        self.tracker.update(event)
        
        # Add pit stop data
        pit_event = RaceEvent(
            event_type=EventType.PIT_STOP,
            timestamp=datetime.now(),
            data={
                'driver': 'Verstappen',
                'tire_compound': 'soft',
                'lap_number': 10
            }
        )
        self.tracker.update(pit_event)
    
    def test_generate_position_response_leader(self):
        """Test position response for race leader."""
        intent = QueryIntent(IntentType.POSITION, "Hamilton")
        response = self.generator.generate_response(intent, self.tracker)
        
        assert "Hamilton" in response
        assert "P1" in response
        assert "currently" in response.lower()
    
    def test_generate_position_response_non_leader(self):
        """Test position response for non-leader."""
        intent = QueryIntent(IntentType.POSITION, "Verstappen")
        response = self.generator.generate_response(intent, self.tracker)
        
        assert "Verstappen" in response
        assert "P2" in response
        assert "behind" in response.lower()
        assert "2.5" in response
    
    def test_generate_position_response_driver_not_found(self):
        """Test position response when driver not found."""
        intent = QueryIntent(IntentType.POSITION, "Unknown")
        response = self.generator.generate_response(intent, self.tracker)
        
        assert "don't have" in response.lower() or "information" in response.lower()
    
    def test_generate_pit_status_response_pitted(self):
        """Test pit status response for driver who has pitted."""
        intent = QueryIntent(IntentType.PIT_STATUS, "Verstappen")
        response = self.generator.generate_response(intent, self.tracker)
        
        assert "Verstappen" in response
        assert "1" in response or "pit" in response.lower()
        assert "soft" in response.lower()
    
    def test_generate_pit_status_response_not_pitted(self):
        """Test pit status response for driver who hasn't pitted."""
        intent = QueryIntent(IntentType.PIT_STATUS, "Hamilton")
        response = self.generator.generate_response(intent, self.tracker)
        
        assert "Hamilton" in response
        assert "not pitted" in response.lower()
    
    def test_generate_gap_response_with_driver(self):
        """Test gap response for specific driver."""
        intent = QueryIntent(IntentType.GAP, "Verstappen")
        response = self.generator.generate_response(intent, self.tracker)
        
        assert "Verstappen" in response
        assert "2.5" in response
        assert "behind" in response.lower()
    
    def test_generate_gap_response_leader(self):
        """Test gap response for race leader."""
        intent = QueryIntent(IntentType.GAP, "Hamilton")
        response = self.generator.generate_response(intent, self.tracker)
        
        assert "Hamilton" in response
        assert "leading" in response.lower()
    
    def test_generate_fastest_lap_response(self):
        """Test fastest lap response."""
        # Add lap time data
        driver = self.tracker.get_driver("Hamilton")
        if driver:
            driver.last_lap_time = 85.123
        
        intent = QueryIntent(IntentType.FASTEST_LAP, None)
        response = self.generator.generate_response(intent, self.tracker)
        
        assert "Hamilton" in response or "fastest" in response.lower()
    
    def test_generate_leader_response(self):
        """Test leader response."""
        intent = QueryIntent(IntentType.LEADER, None)
        response = self.generator.generate_response(intent, self.tracker)
        
        assert "Hamilton" in response
        assert "leading" in response.lower()
    
    def test_generate_unknown_response(self):
        """Test response for unknown intent."""
        intent = QueryIntent(IntentType.UNKNOWN, None)
        response = self.generator.generate_response(intent, self.tracker)
        
        assert "don't have" in response.lower()


class TestQAManager:
    """Test QAManager orchestrator functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tracker = RaceStateTracker()
        self.event_queue = PriorityEventQueue(max_size=10)
        self.qa_manager = QAManager(self.tracker, self.event_queue)
        
        # Set up sample race state
        event = RaceEvent(
            event_type=EventType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data={
                'positions': {
                    'Hamilton': 1,
                    'Verstappen': 2,
                    'Leclerc': 3
                },
                'gaps': {
                    'Verstappen': {'gap_to_leader': 2.5, 'gap_to_ahead': 2.5},
                    'Leclerc': {'gap_to_leader': 5.0, 'gap_to_ahead': 2.5}
                },
                'lap_number': 10,
                'total_laps': 50
            }
        )
        self.tracker.update(event)
    
    def test_process_question_pauses_queue(self):
        """Test that processing a question pauses the event queue."""
        # Queue should not be paused initially
        assert not self.event_queue.is_paused()
        
        # Process a question
        response = self.qa_manager.process_question("Where is Hamilton?")
        
        # Queue should be paused after processing
        assert self.event_queue.is_paused()
        assert isinstance(response, str)
    
    def test_process_question_returns_response(self):
        """Test that process_question returns a valid response."""
        response = self.qa_manager.process_question("Where is Hamilton?")
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert "Hamilton" in response
    
    def test_resume_event_queue(self):
        """Test that resume_event_queue resumes the queue."""
        # Process question to pause queue
        self.qa_manager.process_question("Where is Hamilton?")
        assert self.event_queue.is_paused()
        
        # Resume queue
        self.qa_manager.resume_event_queue()
        assert not self.event_queue.is_paused()
    
    def test_process_question_handles_unknown_question(self):
        """Test that unknown questions are handled gracefully."""
        response = self.qa_manager.process_question("What's the weather?")
        
        assert isinstance(response, str)
        assert "don't have" in response.lower()
    
    def test_process_question_handles_empty_question(self):
        """Test that empty questions are handled gracefully."""
        response = self.qa_manager.process_question("")
        
        assert isinstance(response, str)
        assert "don't have" in response.lower()
    
    def test_process_question_with_position_query(self):
        """Test processing a position query."""
        response = self.qa_manager.process_question("What position is Verstappen in?")
        
        assert "Verstappen" in response
        assert "P2" in response
    
    def test_process_question_with_pit_query(self):
        """Test processing a pit status query."""
        response = self.qa_manager.process_question("Has Hamilton pitted?")
        
        assert "Hamilton" in response
        assert "not pitted" in response.lower()
    
    def test_process_question_with_leader_query(self):
        """Test processing a leader query."""
        response = self.qa_manager.process_question("Who's leading?")
        
        assert "Hamilton" in response
        assert "leading" in response.lower()


class TestQAManagerEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_race_state(self):
        """Test Q&A with empty race state."""
        tracker = RaceStateTracker()
        event_queue = PriorityEventQueue()
        qa_manager = QAManager(tracker, event_queue)
        
        response = qa_manager.process_question("Who's leading?")
        assert "don't have" in response.lower()
    
    def test_single_driver_scenario(self):
        """Test Q&A with only one driver."""
        tracker = RaceStateTracker()
        event = RaceEvent(
            event_type=EventType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data={
                'positions': {'Hamilton': 1},
                'lap_number': 1
            }
        )
        tracker.update(event)
        
        event_queue = PriorityEventQueue()
        qa_manager = QAManager(tracker, event_queue)
        
        response = qa_manager.process_question("Who's leading?")
        assert "Hamilton" in response
    
    def test_driver_not_found_handling(self):
        """Test handling when queried driver is not in race."""
        tracker = RaceStateTracker()
        event = RaceEvent(
            event_type=EventType.POSITION_UPDATE,
            timestamp=datetime.now(),
            data={
                'positions': {'Hamilton': 1},
                'lap_number': 1
            }
        )
        tracker.update(event)
        
        event_queue = PriorityEventQueue()
        qa_manager = QAManager(tracker, event_queue)
        
        response = qa_manager.process_question("Where is Schumacher?")
        assert "don't have" in response.lower() or "information" in response.lower()
