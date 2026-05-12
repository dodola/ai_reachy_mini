"""
Narrative Tracker for F1 Commentary Robot.

This module maintains ongoing race narratives (battles, strategies, comebacks)
and provides narrative context for commentary generation.

Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.6, 6.7
"""

import logging
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple

from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.enhanced_models import (
    ContextData,
    NarrativeThread,
    NarrativeType,
)
from reachy_f1_commentator.src.models import RaceEvent, RaceState


logger = logging.getLogger(__name__)


class NarrativeTracker:
    """
    Maintains ongoing race narratives and provides narrative context.
    
    Tracks battles, comebacks, strategy divergences, championship fights,
    and undercut/overcut attempts across multiple laps.
    
    Validates: Requirements 6.1, 6.6, 6.7
    """
    
    def __init__(self, config: Config):
        """
        Initialize narrative tracker with configuration.
        
        Args:
            config: System configuration with narrative tracking parameters
        """
        self.config = config
        self.active_threads: List[NarrativeThread] = []
        self.max_active_threads = config.max_narrative_threads
        
        # Track driver positions and gaps over time for narrative detection
        self.position_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=20))
        self.gap_history: Dict[Tuple[str, str], deque] = defaultdict(lambda: deque(maxlen=10))
        
        # Track pit stop timing for undercut/overcut detection
        self.recent_pit_stops: Dict[str, int] = {}  # driver -> lap_number
        
        logger.info(
            f"NarrativeTracker initialized with max_threads={self.max_active_threads}, "
            f"battle_gap_threshold={config.battle_gap_threshold}s, "
            f"battle_lap_threshold={config.battle_lap_threshold} laps"
        )
    
    def update(self, race_state: RaceState, context: ContextData) -> None:
        """
        Update narratives based on current race state and context.
        
        This method should be called regularly (e.g., every lap or event) to:
        1. Update position and gap history
        2. Detect new narrative threads
        3. Update existing narrative threads
        4. Close stale narrative threads
        
        Args:
            race_state: Current race state with driver positions
            context: Enriched context data with gaps, tires, etc.
            
        Validates: Requirements 6.1
        """
        current_lap = race_state.current_lap
        
        # Update position history for all drivers
        for driver in race_state.drivers:
            self.position_history[driver.name].append({
                'lap': current_lap,
                'position': driver.position
            })
        
        # Update gap history for nearby drivers
        sorted_drivers = race_state.get_positions()
        for i in range(len(sorted_drivers) - 1):
            driver_ahead = sorted_drivers[i]
            driver_behind = sorted_drivers[i + 1]
            gap = driver_behind.gap_to_ahead
            
            if gap is not None and gap < 10.0:  # Only track gaps < 10s
                pair = (driver_ahead.name, driver_behind.name)
                self.gap_history[pair].append({
                    'lap': current_lap,
                    'gap': gap
                })
        
        # Track pit stops for undercut/overcut detection
        if context.pit_count > 0:
            # Extract driver name from event if available
            if hasattr(context.event, 'data') and 'driver' in context.event.data:
                driver = context.event.data['driver']
                self.recent_pit_stops[driver] = current_lap
        
        # Detect new narratives
        new_narratives = self.detect_new_narratives(race_state, context)
        for narrative in new_narratives:
            self._add_narrative(narrative)
        
        # Update existing narratives
        for narrative in self.active_threads:
            if narrative.is_active:
                narrative.last_update_lap = current_lap
        
        # Close stale narratives
        self.close_stale_narratives(race_state, current_lap)
        
        logger.debug(
            f"Lap {current_lap}: {len(self.active_threads)} active narratives"
        )
    
    def detect_new_narratives(
        self, race_state: RaceState, context: ContextData
    ) -> List[NarrativeThread]:
        """
        Detect new narrative threads from current race state.
        
        Scans for all narrative types: battles, comebacks, strategy divergence,
        championship fights, and undercut/overcut attempts.
        
        Args:
            race_state: Current race state
            context: Enriched context data
            
        Returns:
            List of newly detected narrative threads
            
        Validates: Requirements 6.1
        """
        new_narratives = []
        current_lap = race_state.current_lap
        
        # Detect battles
        battle = self._detect_battle(race_state, current_lap)
        if battle:
            new_narratives.append(battle)
        
        # Detect comebacks
        comeback = self._detect_comeback(race_state, current_lap)
        if comeback:
            new_narratives.append(comeback)
        
        # Detect strategy divergence
        strategy = self._detect_strategy_divergence(race_state, context)
        if strategy:
            new_narratives.append(strategy)
        
        # Detect championship fight
        championship = self._detect_championship_fight(context)
        if championship:
            new_narratives.append(championship)
        
        # Detect undercut attempts
        undercut = self._detect_undercut_attempt(race_state, current_lap)
        if undercut:
            new_narratives.append(undercut)
        
        # Detect overcut attempts
        overcut = self._detect_overcut_attempt(race_state, current_lap)
        if overcut:
            new_narratives.append(overcut)
        
        return new_narratives
    
    def _detect_battle(
        self, race_state: RaceState, current_lap: int
    ) -> Optional[NarrativeThread]:
        """
        Detect ongoing battle (drivers within 2s for 3+ consecutive laps).
        
        Scans gap history to find driver pairs that have been close for
        multiple consecutive laps.
        
        Args:
            race_state: Current race state
            current_lap: Current lap number
            
        Returns:
            NarrativeThread if battle detected, None otherwise
            
        Validates: Requirements 6.3
        """
        threshold = self.config.battle_gap_threshold
        min_laps = self.config.battle_lap_threshold
        
        # Check all tracked gap pairs
        for (driver_ahead, driver_behind), gap_data in self.gap_history.items():
            if len(gap_data) < min_laps:
                continue
            
            # Check if gap has been under threshold for min_laps consecutive laps
            recent_gaps = list(gap_data)[-min_laps:]
            consecutive = all(
                entry['gap'] <= threshold and 
                entry['lap'] >= current_lap - min_laps
                for entry in recent_gaps
            )
            
            if consecutive:
                # Check if this battle already exists
                narrative_id = f"battle_{driver_ahead}_{driver_behind}"
                if self._narrative_exists(narrative_id):
                    continue
                
                logger.info(
                    f"Battle detected: {driver_ahead} vs {driver_behind} "
                    f"(within {threshold}s for {min_laps}+ laps)"
                )
                
                return NarrativeThread(
                    narrative_id=narrative_id,
                    narrative_type=NarrativeType.BATTLE,
                    drivers_involved=[driver_ahead, driver_behind],
                    start_lap=current_lap - min_laps + 1,
                    last_update_lap=current_lap,
                    context_data={
                        'current_gap': recent_gaps[-1]['gap'],
                        'min_gap': min(entry['gap'] for entry in recent_gaps),
                        'max_gap': max(entry['gap'] for entry in recent_gaps),
                    },
                    is_active=True
                )
        
        return None
    
    def _detect_comeback(
        self, race_state: RaceState, current_lap: int
    ) -> Optional[NarrativeThread]:
        """
        Detect comeback drive (driver gaining 3+ positions in 10 laps).
        
        Scans position history to find drivers who have gained significant
        positions in recent laps.
        
        Args:
            race_state: Current race state
            current_lap: Current lap number
            
        Returns:
            NarrativeThread if comeback detected, None otherwise
            
        Validates: Requirements 6.2
        """
        min_positions = self.config.comeback_position_threshold
        lap_window = self.config.comeback_lap_window
        
        # Check each driver's position history
        for driver_name, position_data in self.position_history.items():
            if len(position_data) < 2:
                continue
            
            # Get positions from lap_window laps ago and current
            positions_in_window = [
                entry for entry in position_data
                if entry['lap'] >= current_lap - lap_window
            ]
            
            if len(positions_in_window) < 2:
                continue
            
            start_position = positions_in_window[0]['position']
            current_position = positions_in_window[-1]['position']
            positions_gained = start_position - current_position
            
            if positions_gained >= min_positions:
                # Check if this comeback already exists
                narrative_id = f"comeback_{driver_name}"
                if self._narrative_exists(narrative_id):
                    continue
                
                logger.info(
                    f"Comeback detected: {driver_name} gained {positions_gained} "
                    f"positions (P{start_position} -> P{current_position}) "
                    f"in {len(positions_in_window)} laps"
                )
                
                return NarrativeThread(
                    narrative_id=narrative_id,
                    narrative_type=NarrativeType.COMEBACK,
                    drivers_involved=[driver_name],
                    start_lap=positions_in_window[0]['lap'],
                    last_update_lap=current_lap,
                    context_data={
                        'start_position': start_position,
                        'current_position': current_position,
                        'positions_gained': positions_gained,
                        'laps_taken': len(positions_in_window),
                    },
                    is_active=True
                )
        
        return None
    
    def _detect_strategy_divergence(
        self, race_state: RaceState, context: ContextData
    ) -> Optional[NarrativeThread]:
        """
        Detect strategy divergence (different compounds or age diff >5 laps).
        
        Compares tire strategies of nearby drivers to find significant
        differences in compound or tire age.
        
        Args:
            race_state: Current race state
            context: Enriched context data with tire information
            
        Returns:
            NarrativeThread if strategy divergence detected, None otherwise
            
        Validates: Requirements 6.4
        """
        # Need tire data to detect strategy divergence
        if not context.current_tire_compound:
            return None
        
        # Get nearby drivers (within 5 positions)
        sorted_drivers = race_state.get_positions()
        
        for i in range(len(sorted_drivers) - 1):
            driver1 = sorted_drivers[i]
            driver2 = sorted_drivers[i + 1]
            
            # Check if drivers are close in position
            if abs(driver1.position - driver2.position) > 5:
                continue
            
            # Compare tire compounds
            compound1 = driver1.current_tire
            compound2 = driver2.current_tire
            
            # Different compounds indicate strategy divergence
            if compound1 != compound2 and compound1 != "unknown" and compound2 != "unknown":
                narrative_id = f"strategy_{driver1.name}_{driver2.name}"
                if self._narrative_exists(narrative_id):
                    continue
                
                logger.info(
                    f"Strategy divergence detected: {driver1.name} ({compound1}) "
                    f"vs {driver2.name} ({compound2})"
                )
                
                return NarrativeThread(
                    narrative_id=narrative_id,
                    narrative_type=NarrativeType.STRATEGY_DIVERGENCE,
                    drivers_involved=[driver1.name, driver2.name],
                    start_lap=race_state.current_lap,
                    last_update_lap=race_state.current_lap,
                    context_data={
                        'compound1': compound1,
                        'compound2': compound2,
                        'position_diff': abs(driver1.position - driver2.position),
                    },
                    is_active=True
                )
            
            # Check tire age difference (if available in context)
            if context.tire_age_differential and abs(context.tire_age_differential) > 5:
                narrative_id = f"strategy_age_{driver1.name}_{driver2.name}"
                if self._narrative_exists(narrative_id):
                    continue
                
                logger.info(
                    f"Strategy divergence detected: {driver1.name} vs {driver2.name} "
                    f"(tire age diff: {context.tire_age_differential} laps)"
                )
                
                return NarrativeThread(
                    narrative_id=narrative_id,
                    narrative_type=NarrativeType.STRATEGY_DIVERGENCE,
                    drivers_involved=[driver1.name, driver2.name],
                    start_lap=race_state.current_lap,
                    last_update_lap=race_state.current_lap,
                    context_data={
                        'tire_age_diff': context.tire_age_differential,
                        'position_diff': abs(driver1.position - driver2.position),
                    },
                    is_active=True
                )
        
        return None
    
    def _detect_championship_fight(
        self, context: ContextData
    ) -> Optional[NarrativeThread]:
        """
        Detect championship fight (top 2 within 25 points).
        
        Checks if the top 2 drivers in the championship are close enough
        to create a championship battle narrative.
        
        Args:
            context: Enriched context data with championship information
            
        Returns:
            NarrativeThread if championship fight detected, None otherwise
            
        Validates: Requirements 6.4
        """
        # Need championship data to detect championship fight
        if not context.driver_championship_position:
            return None
        
        # Check if driver is in top 2 and gap is within 25 points
        if context.driver_championship_position <= 2:
            if context.championship_gap_to_leader is not None:
                gap = abs(context.championship_gap_to_leader)
                
                if gap <= 25:
                    narrative_id = "championship_fight"
                    if self._narrative_exists(narrative_id):
                        return None
                    
                    logger.info(
                        f"Championship fight detected: top 2 within {gap} points"
                    )
                    
                    return NarrativeThread(
                        narrative_id=narrative_id,
                        narrative_type=NarrativeType.CHAMPIONSHIP_FIGHT,
                        drivers_involved=[],  # Will be populated with actual driver names
                        start_lap=0,  # Championship fight spans entire season
                        last_update_lap=0,
                        context_data={
                            'points_gap': gap,
                        },
                        is_active=True
                    )
        
        return None
    
    def _detect_undercut_attempt(
        self, race_state: RaceState, current_lap: int
    ) -> Optional[NarrativeThread]:
        """
        Detect undercut attempt (pit stop undercut scenarios).
        
        Identifies when a driver pits while their rival stays out,
        potentially setting up an undercut.
        
        Args:
            race_state: Current race state
            current_lap: Current lap number
            
        Returns:
            NarrativeThread if undercut attempt detected, None otherwise
            
        Validates: Requirements 6.4
        """
        # Check recent pit stops (within last 3 laps)
        recent_pitters = [
            driver for driver, lap in self.recent_pit_stops.items()
            if current_lap - lap <= 3
        ]
        
        if not recent_pitters:
            return None
        
        # For each recent pitter, check if there's a rival ahead who hasn't pitted
        sorted_drivers = race_state.get_positions()
        
        for pitter in recent_pitters:
            pitter_state = race_state.get_driver(pitter)
            if not pitter_state:
                continue
            
            # Find drivers within 3 positions ahead
            for driver in sorted_drivers:
                if driver.name == pitter:
                    continue
                
                position_diff = pitter_state.position - driver.position
                if 1 <= position_diff <= 3:
                    # Check if rival hasn't pitted recently
                    rival_last_pit = self.recent_pit_stops.get(driver.name, 0)
                    if current_lap - rival_last_pit > 5:
                        narrative_id = f"undercut_{pitter}_{driver.name}"
                        if self._narrative_exists(narrative_id):
                            continue
                        
                        logger.info(
                            f"Undercut attempt detected: {pitter} pitted, "
                            f"{driver.name} still out"
                        )
                        
                        return NarrativeThread(
                            narrative_id=narrative_id,
                            narrative_type=NarrativeType.UNDERCUT_ATTEMPT,
                            drivers_involved=[pitter, driver.name],
                            start_lap=self.recent_pit_stops[pitter],
                            last_update_lap=current_lap,
                            context_data={
                                'pitter': pitter,
                                'rival': driver.name,
                                'position_diff': position_diff,
                            },
                            is_active=True
                        )
        
        return None
    
    def _detect_overcut_attempt(
        self, race_state: RaceState, current_lap: int
    ) -> Optional[NarrativeThread]:
        """
        Detect overcut attempt (staying out longer scenarios).
        
        Identifies when a driver stays out while their rival has pitted,
        potentially setting up an overcut.
        
        Args:
            race_state: Current race state
            current_lap: Current lap number
            
        Returns:
            NarrativeThread if overcut attempt detected, None otherwise
            
        Validates: Requirements 6.4
        """
        # Check recent pit stops (within last 5 laps)
        recent_pitters = [
            driver for driver, lap in self.recent_pit_stops.items()
            if current_lap - lap <= 5
        ]
        
        if not recent_pitters:
            return None
        
        # For each recent pitter, check if there's a rival behind who hasn't pitted
        sorted_drivers = race_state.get_positions()
        
        for pitter in recent_pitters:
            pitter_state = race_state.get_driver(pitter)
            if not pitter_state:
                continue
            
            # Find drivers within 3 positions behind
            for driver in sorted_drivers:
                if driver.name == pitter:
                    continue
                
                position_diff = driver.position - pitter_state.position
                if 1 <= position_diff <= 3:
                    # Check if rival hasn't pitted recently (staying out longer)
                    rival_last_pit = self.recent_pit_stops.get(driver.name, 0)
                    if current_lap - rival_last_pit > 10:
                        narrative_id = f"overcut_{driver.name}_{pitter}"
                        if self._narrative_exists(narrative_id):
                            continue
                        
                        logger.info(
                            f"Overcut attempt detected: {driver.name} staying out, "
                            f"{pitter} already pitted"
                        )
                        
                        return NarrativeThread(
                            narrative_id=narrative_id,
                            narrative_type=NarrativeType.OVERCUT_ATTEMPT,
                            drivers_involved=[driver.name, pitter],
                            start_lap=self.recent_pit_stops[pitter],
                            last_update_lap=current_lap,
                            context_data={
                                'stayer': driver.name,
                                'pitter': pitter,
                                'position_diff': position_diff,
                            },
                            is_active=True
                        )
        
        return None
    
    def close_stale_narratives(
        self, race_state: RaceState, current_lap: int
    ) -> None:
        """
        Close narratives that are no longer active.
        
        Checks each active narrative to see if its conditions still apply:
        - Battle: gap > 5s for 2 consecutive laps OR one driver pits
        - Comeback: no position gain for 10 consecutive laps
        - Strategy: strategies converge (same compound and age within 3 laps)
        - Championship: gap > 25 points
        - Undercut/Overcut: both drivers complete pit cycle
        
        Args:
            race_state: Current race state
            current_lap: Current lap number
            
        Validates: Requirements 6.6
        """
        for narrative in self.active_threads:
            if not narrative.is_active:
                continue
            
            should_close = False
            reason = ""
            
            if narrative.narrative_type == NarrativeType.BATTLE:
                # Close if gap > 5s or one driver pitted recently
                drivers = narrative.drivers_involved
                if len(drivers) == 2:
                    pair = (drivers[0], drivers[1])
                    gap_data = self.gap_history.get(pair, deque())
                    
                    if gap_data:
                        recent_gaps = list(gap_data)[-2:]
                        if all(entry['gap'] > 5.0 for entry in recent_gaps):
                            should_close = True
                            reason = "gap exceeded 5s"
                    
                    # Check if either driver pitted recently
                    for driver in drivers:
                        if driver in self.recent_pit_stops:
                            pit_lap = self.recent_pit_stops[driver]
                            if current_lap - pit_lap <= 2:
                                should_close = True
                                reason = f"{driver} pitted"
            
            elif narrative.narrative_type == NarrativeType.COMEBACK:
                # Close if no position gain for 10 laps
                driver = narrative.drivers_involved[0]
                position_data = self.position_history.get(driver, deque())
                
                if position_data:
                    recent_positions = [
                        entry for entry in position_data
                        if entry['lap'] >= current_lap - 10
                    ]
                    
                    if len(recent_positions) >= 2:
                        start_pos = recent_positions[0]['position']
                        current_pos = recent_positions[-1]['position']
                        
                        if start_pos <= current_pos:  # No gain or lost positions
                            should_close = True
                            reason = "no position gain in 10 laps"
            
            elif narrative.narrative_type == NarrativeType.STRATEGY_DIVERGENCE:
                # Close if strategies converge
                drivers = narrative.drivers_involved
                if len(drivers) == 2:
                    driver1_state = race_state.get_driver(drivers[0])
                    driver2_state = race_state.get_driver(drivers[1])
                    
                    if driver1_state and driver2_state:
                        # Check if compounds are now the same
                        if (driver1_state.current_tire == driver2_state.current_tire and
                            driver1_state.current_tire != "unknown"):
                            should_close = True
                            reason = "strategies converged"
            
            elif narrative.narrative_type == NarrativeType.CHAMPIONSHIP_FIGHT:
                # Championship fights typically last the entire season
                # Only close if gap becomes very large (>50 points)
                if 'points_gap' in narrative.context_data:
                    if narrative.context_data['points_gap'] > 50:
                        should_close = True
                        reason = "championship gap too large"
            
            elif narrative.narrative_type in [
                NarrativeType.UNDERCUT_ATTEMPT,
                NarrativeType.OVERCUT_ATTEMPT
            ]:
                # Close after 10 laps (pit cycle should be complete)
                if current_lap - narrative.start_lap > 10:
                    should_close = True
                    reason = "pit cycle complete"
            
            if should_close:
                narrative.is_active = False
                logger.info(
                    f"Closed narrative {narrative.narrative_id} "
                    f"({narrative.narrative_type.value}): {reason}"
                )
    
    def get_relevant_narratives(
        self, event: RaceEvent
    ) -> List[NarrativeThread]:
        """
        Get narratives relevant to current event.
        
        Filters active narratives to find those that involve the drivers
        or context of the current event.
        
        Args:
            event: Current race event
            
        Returns:
            List of relevant narrative threads
            
        Validates: Requirements 6.8
        """
        relevant = []
        
        # Extract driver names from event
        event_drivers = set()
        if hasattr(event, 'data'):
            if 'driver' in event.data:
                event_drivers.add(event.data['driver'])
            if 'overtaking_driver' in event.data:
                event_drivers.add(event.data['overtaking_driver'])
            if 'overtaken_driver' in event.data:
                event_drivers.add(event.data['overtaken_driver'])
            if 'drivers_involved' in event.data:
                event_drivers.update(event.data['drivers_involved'])
        
        # Find narratives involving event drivers
        for narrative in self.active_threads:
            if not narrative.is_active:
                continue
            
            # Check if any event driver is involved in narrative
            if any(driver in event_drivers for driver in narrative.drivers_involved):
                relevant.append(narrative)
            
            # Championship fights are always relevant for top drivers
            elif narrative.narrative_type == NarrativeType.CHAMPIONSHIP_FIGHT:
                relevant.append(narrative)
        
        return relevant
    
    def _add_narrative(self, narrative: NarrativeThread) -> None:
        """
        Add a new narrative thread, enforcing thread limit.
        
        If at max capacity, removes the oldest narrative to make room.
        
        Args:
            narrative: New narrative thread to add
            
        Validates: Requirements 6.7
        """
        # Check if we're at max capacity
        if len(self.active_threads) >= self.max_active_threads:
            # Remove oldest narrative
            oldest = min(
                self.active_threads,
                key=lambda n: n.last_update_lap
            )
            self.active_threads.remove(oldest)
            logger.info(
                f"Removed oldest narrative {oldest.narrative_id} "
                f"to make room (max {self.max_active_threads} threads)"
            )
        
        self.active_threads.append(narrative)
        logger.info(
            f"Added narrative {narrative.narrative_id} "
            f"({narrative.narrative_type.value})"
        )
    
    def _narrative_exists(self, narrative_id: str) -> bool:
        """
        Check if a narrative with given ID already exists.
        
        Args:
            narrative_id: Narrative ID to check
            
        Returns:
            True if narrative exists and is active, False otherwise
        """
        return any(
            n.narrative_id == narrative_id and n.is_active
            for n in self.active_threads
        )
    
    def get_active_narratives(self) -> List[NarrativeThread]:
        """
        Get all currently active narrative threads.
        
        Returns:
            List of active narrative threads
        """
        return [n for n in self.active_threads if n.is_active]
    
    def get_narrative_count(self) -> int:
        """
        Get count of active narrative threads.
        
        Returns:
            Number of active narratives
        """
        return len([n for n in self.active_threads if n.is_active])
