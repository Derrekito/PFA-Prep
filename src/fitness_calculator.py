#!/usr/bin/env python3
"""Fitness progression calculator for PFA training."""

from datetime import time, timedelta
from typing import Dict, Any, List, Tuple
import math
from time_utils import parse_time_to_seconds, seconds_to_time_string


def time_string_to_seconds(time_str: str) -> int:
    """Convert MM:SS format to total seconds."""
    return parse_time_to_seconds(time_str)


def seconds_to_time_string(total_seconds: int) -> str:
    """Convert total seconds to MM:SS format."""
    from time_utils import seconds_to_time_string as util_seconds_to_time_string
    return util_seconds_to_time_string(total_seconds)


class FitnessProgressionCalculator:
    """Calculates weekly fitness progressions based on baseline, goals, and timeline."""

    def __init__(self, fitness_config: Dict[str, Any], timeline_weeks: int, buffer_weeks: Dict[str, int]):
        self.fitness_config = fitness_config
        self.timeline_weeks = timeline_weeks
        self.buffer_weeks = buffer_weeks
        self._warned_run_goal = False

    def calculate_run_progression(self) -> List[str]:
        """Calculate weekly run time progression."""
        baseline_str = self.fitness_config['baseline']['run_time']
        goal_str = self.fitness_config['goals']['run_time']
        standard_str = self.fitness_config['pfa_standards']['run_time']

        baseline_seconds = time_string_to_seconds(baseline_str)
        goal_seconds = time_string_to_seconds(goal_str)
        standard_seconds = time_string_to_seconds(standard_str)

        # Ensure goal meets or exceeds standards (allow override for unrealistic but user-chosen goals)
        if goal_seconds > standard_seconds:
            if not self._warned_run_goal:
                print(f"WARNING: Goal run time ({goal_str}) does not meet PFA standard ({standard_str}). Using standard as calculation target.")
                self._warned_run_goal = True
            # Use the standard as the effective goal to prevent calculation errors
            goal_seconds = standard_seconds
            goal_str = standard_str

        # Calculate effective weeks (total weeks minus buffer)
        buffer = self.buffer_weeks.get('run', 0)
        effective_weeks = self.timeline_weeks - buffer

        if effective_weeks <= 0:
            raise ValueError("Buffer weeks exceed total timeline weeks")

        # Calculate weekly improvement needed
        total_improvement = baseline_seconds - goal_seconds  # Negative for faster times
        weekly_improvement = total_improvement / effective_weeks

        progression = []
        current_seconds = baseline_seconds

        for week in range(self.timeline_weeks):
            if week < effective_weeks:
                current_seconds -= weekly_improvement
            # Maintain goal time during buffer period

            progression.append(seconds_to_time_string(int(round(current_seconds))))

        return progression

    def calculate_strength_progression(self, exercise: str) -> List[int]:
        """Calculate weekly strength progression for pushups/situps."""
        baseline = self.fitness_config['baseline'][exercise]
        goal = self.fitness_config['goals'][exercise]
        standard = self.fitness_config['pfa_standards'][exercise]

        # Ensure goal meets or exceeds standards
        if goal < standard:
            raise ValueError(f"Goal {exercise} ({goal}) does not meet PFA standard ({standard})")

        # Calculate effective weeks (total weeks minus buffer)
        buffer = self.buffer_weeks.get(exercise, 0)
        effective_weeks = self.timeline_weeks - buffer

        if effective_weeks <= 0:
            raise ValueError("Buffer weeks exceed total timeline weeks")

        # Calculate weekly improvement needed
        total_improvement = goal - baseline
        weekly_improvement = total_improvement / effective_weeks

        progression = []
        current_value = baseline

        for week in range(self.timeline_weeks):
            if week < effective_weeks:
                current_value += weekly_improvement
            # Maintain goal during buffer period

            progression.append(int(round(current_value)))

        return progression


    def get_weekly_targets(self, week: int) -> Dict[str, Any]:
        """Get fitness targets for a specific week."""
        run_progression = self.calculate_run_progression()
        pushup_progression = self.calculate_strength_progression('pushups')
        situp_progression = self.calculate_strength_progression('situps')

        if week >= len(run_progression):
            week = len(run_progression) - 1

        return {
            'run_time': run_progression[week],
            'pushups': pushup_progression[week],
            'situps': situp_progression[week]
        }

    def validate_goals(self) -> Dict[str, bool]:
        """Validate that goals are achievable and meet standards."""
        validation = {}

        # Check run time goal
        goal_run = time_string_to_seconds(self.fitness_config['goals']['run_time'])
        standard_run = time_string_to_seconds(self.fitness_config['pfa_standards']['run_time'])
        validation['run_meets_standard'] = goal_run <= standard_run

        # Check pushup goal
        goal_pushups = self.fitness_config['goals']['pushups']
        standard_pushups = self.fitness_config['pfa_standards']['pushups']
        validation['pushups_meets_standard'] = goal_pushups >= standard_pushups

        # Check situp goal
        goal_situps = self.fitness_config['goals']['situps']
        standard_situps = self.fitness_config['pfa_standards']['situps']
        validation['situps_meets_standard'] = goal_situps >= standard_situps

        return validation

    def calculate_adaptation_weeks(self, adaptation_frequency: int) -> List[int]:
        """Calculate which weeks should be adaptation/deload weeks."""
        adaptation_weeks = []
        for week in range(adaptation_frequency - 1, self.timeline_weeks, adaptation_frequency):
            adaptation_weeks.append(week)
        return adaptation_weeks

    def get_weekly_volume_multiplier(self, week: int, adaptation_frequency: int, reduction_factor: float) -> float:
        """Get volume multiplier for a given week (1.0 for normal, reduced for adaptation weeks)."""
        adaptation_weeks = self.calculate_adaptation_weeks(adaptation_frequency)
        if week in adaptation_weeks:
            return reduction_factor
        return 1.0

    def generate_progression_report(self) -> Dict[str, Any]:
        """Generate a comprehensive progression report."""
        validation = self.validate_goals()

        report = {
            'validation': validation,
            'timeline_weeks': self.timeline_weeks,
            'buffer_weeks': self.buffer_weeks,
            'progressions': {
                'run_time': self.calculate_run_progression(),
                'pushups': self.calculate_strength_progression('pushups'),
                'situps': self.calculate_strength_progression('situps')
            }
        }

        return report