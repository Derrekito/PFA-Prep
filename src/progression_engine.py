#!/usr/bin/env python3
"""Workout progression engine with periodization and adaptive scaling."""

from datetime import datetime, time
from typing import Dict, Any, List, Tuple, Optional
import math


class WorkoutProgressionEngine:
    """Generates progressive workout plans with periodization and adaptive scaling."""

    def __init__(self, training_config: Dict[str, Any], progression_config: Dict[str, Any], fitness_calculator):
        self.training_config = training_config
        self.progression_config = progression_config
        self.fitness_calculator = fitness_calculator

        self.workout_types = {
            'run_intervals': self._generate_run_intervals,
            'tempo_run': self._generate_tempo_run,
            'pfa_circuit': self._generate_pfa_circuit,
            'strength_core': self._generate_strength_core,
            'easy_run': self._generate_easy_run,
            'long_run': self._generate_long_run
        }

    def _parse_time_to_seconds(self, time_str: str) -> int:
        """Convert MM:SS format to total seconds."""
        if ":" in time_str:
            minutes, seconds = map(int, time_str.split(":"))
            return minutes * 60 + seconds
        return int(time_str)

    def _seconds_to_pace(self, total_seconds: int) -> str:
        """Convert total seconds to MM:SS pace format."""
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"

    def _normalize_day_name(self, day: str) -> str:
        """Convert full day names to abbreviated format for schedule matching."""
        day_mapping = {
            'Monday': 'Mon',
            'Tuesday': 'Tue',
            'Wednesday': 'Wed',
            'Thursday': 'Thu',
            'Friday': 'Fri',
            'Saturday': 'Sat',
            'Sunday': 'Sun'
        }
        return day_mapping.get(day, day)

    def _calculate_training_pace(self, week: int, intensity: str) -> str:
        """Calculate training pace based on week and intensity."""
        weekly_targets = self.fitness_calculator.get_weekly_targets(week)
        goal_pace_seconds = self._parse_time_to_seconds(weekly_targets['run_time'])
        mile_pace_seconds = int(goal_pace_seconds / 1.5)  # Convert 1.5 mile time to per-mile pace

        # Adjust pace based on intensity
        intensity_multipliers = {
            'easy': 1.15,      # 15% slower than goal pace
            'moderate': 1.05,   # 5% slower than goal pace
            'tempo': 0.98,     # 2% faster than goal pace
            'hard': 0.90,      # 10% faster than goal pace
            'interval': 0.85   # 15% faster than goal pace
        }

        multiplier = intensity_multipliers.get(intensity, 1.0)
        training_pace_seconds = int(mile_pace_seconds * multiplier)
        return self._seconds_to_pace(training_pace_seconds)

    def _generate_run_intervals(self, week: int, volume_multiplier: float = 1.0) -> Dict[str, Any]:
        """Generate interval run workout."""
        base_intervals = 6
        interval_distance = 200  # meters
        rest_duration = "2:00"

        # Progress intervals over time
        total_intervals = int(base_intervals + (week // 2) * 2)
        total_intervals = int(total_intervals * volume_multiplier)

        # Adjust pace based on week
        interval_pace = self._calculate_training_pace(week, 'interval')

        workout = {
            'type': 'run_intervals',
            'warm_up': '10 min easy jog + dynamic warm-up',
            'main_set': f'{total_intervals}×{interval_distance}m @ {interval_pace}/mi pace, {rest_duration} rest',
            'cool_down': '10 min easy jog + stretching',
            'total_duration': 45,
            'intensity': 'hard',
            'focus': 'speed_endurance'
        }

        # Add strength component
        weekly_targets = self.fitness_calculator.get_weekly_targets(week)
        pushup_target = max(int(weekly_targets['pushups'] * 0.7), 5)

        workout['strength_component'] = f'Push-ups: 4×{pushup_target}'

        return workout

    def _generate_tempo_run(self, week: int, volume_multiplier: float = 1.0) -> Dict[str, Any]:
        """Generate tempo run workout."""
        base_distance = 1.5  # miles
        progression_distance = base_distance + (week * 0.25)
        total_distance = progression_distance * volume_multiplier

        tempo_pace = self._calculate_training_pace(week, 'tempo')

        # Determine run/walk pattern based on progression
        if week < 4:
            pattern = "jog/walk intervals (3:1 ratio)"
        elif week < 8:
            pattern = "continuous jog (easy pace)"
        else:
            pattern = f"tempo run @ {tempo_pace}/mi"

        workout = {
            'type': 'tempo_run',
            'warm_up': '5 min walk + 5 min easy jog',
            'main_set': f'{total_distance:.1f} mi {pattern}',
            'cool_down': '5 min walk + stretching',
            'total_duration': 40,
            'intensity': 'moderate',
            'focus': 'aerobic_endurance'
        }

        # Add core component
        weekly_targets = self.fitness_calculator.get_weekly_targets(week)
        situp_target = max(int(weekly_targets['situps'] * 0.6), 10)

        workout['core_component'] = f'Core: {situp_target} sit-ups, dead bug 2×10/side, side planks 2×30s'

        return workout

    def _generate_pfa_circuit(self, week: int, volume_multiplier: float = 1.0) -> Dict[str, Any]:
        """Generate PFA-specific circuit workout."""
        weekly_targets = self.fitness_calculator.get_weekly_targets(week)

        # Circuit parameters based on week
        base_rounds = 3
        total_rounds = int((base_rounds + week // 4) * volume_multiplier)

        circuit_pace = self._calculate_training_pace(week, 'moderate')
        pushup_reps = max(int(weekly_targets['pushups'] * 0.6), 8)
        situp_reps = max(int(weekly_targets['situps'] * 0.5), 12)

        workout = {
            'type': 'pfa_circuit',
            'warm_up': '10 min dynamic warm-up',
            'main_set': f'{total_rounds} rounds: 400m jog @ {circuit_pace}/mi + '
                       f'{pushup_reps} push-ups + {situp_reps} sit-ups + 90s rest',
            'cool_down': '5 min walk + stretching',
            'total_duration': 50,
            'intensity': 'moderate',
            'focus': 'pfa_simulation'
        }

        return workout

    def _generate_strength_core(self, week: int, volume_multiplier: float = 1.0) -> Dict[str, Any]:
        """Generate strength and core workout."""
        weekly_targets = self.fitness_calculator.get_weekly_targets(week)

        # Progressive loading
        pushup_target = int(weekly_targets['pushups'] * volume_multiplier)
        situp_target = int(weekly_targets['situps'] * volume_multiplier)

        # Determine set/rep scheme based on progression
        if week < 4:
            pushup_sets = f"4×{max(int(pushup_target * 0.6), 5)}"
        elif week < 8:
            pushup_sets = f"5×{max(int(pushup_target * 0.7), 8)}"
        else:
            pushup_sets = f"6×{max(int(pushup_target * 0.8), 10)}"

        workout = {
            'type': 'strength_core',
            'warm_up': '10 min general warm-up',
            'main_set': {
                'push_ups': pushup_sets,
                'sit_ups': f'4×{max(int(situp_target * 0.7), 15)}',
                'dead_bugs': '3×10/side',
                'squats': '3×15-20',
                'lunges': '3×10/leg',
                'pull_ups': '3×max reps or assisted',
                'dips': '3×8-12'
            },
            'cool_down': '10 min stretching',
            'total_duration': 60,
            'intensity': 'moderate',
            'focus': 'strength_endurance'
        }

        return workout

    def _generate_easy_run(self, week: int, volume_multiplier: float = 1.0) -> Dict[str, Any]:
        """Generate easy recovery run."""
        base_distance = 2.0
        total_distance = (base_distance + week * 0.1) * volume_multiplier

        easy_pace = self._calculate_training_pace(week, 'easy')

        # Determine run type based on fitness level
        if week < 3:
            run_type = "brisk walk"
        elif week < 6:
            run_type = "jog/walk"
        else:
            run_type = f"easy jog @ {easy_pace}/mi"

        workout = {
            'type': 'easy_run',
            'warm_up': '5 min walk',
            'main_set': f'{total_distance:.1f} mi {run_type}',
            'cool_down': '5 min walk + light stretching',
            'total_duration': 30,
            'intensity': 'easy',
            'focus': 'recovery'
        }

        return workout

    def _generate_long_run(self, week: int, volume_multiplier: float = 1.0) -> Dict[str, Any]:
        """Generate long run for aerobic base building."""
        base_distance = 3.0
        total_distance = (base_distance + week * 0.2) * volume_multiplier

        easy_pace = self._calculate_training_pace(week, 'easy')

        workout = {
            'type': 'long_run',
            'warm_up': '10 min walk + 5 min easy jog',
            'main_set': f'{total_distance:.1f} mi @ {easy_pace}/mi (conversational pace)',
            'cool_down': '10 min walk + full stretching routine',
            'total_duration': int(45 + total_distance * 5),  # Estimate based on distance
            'intensity': 'easy',
            'focus': 'aerobic_base'
        }

        return workout

    def get_workout_for_day(self, day: str, week: int, workout_type: str = None) -> Dict[str, Any]:
        """Get specific workout for a given day and week."""
        # Get volume multiplier for adaptation weeks
        adaptation_frequency = self.progression_config['adaptation_periods']['frequency']
        reduction_factor = self.progression_config['adaptation_periods']['reduction']
        volume_multiplier = self.fitness_calculator.get_weekly_volume_multiplier(
            week, adaptation_frequency, reduction_factor
        )

        # Determine workout type based on day if not specified
        if not workout_type:
            schedule = self.training_config['schedule']
            normalized_day = self._normalize_day_name(day)

            if normalized_day in schedule['workout_days']:
                # Rotate workout types for main training days
                day_index = schedule['workout_days'].index(normalized_day)
                workout_types = ['run_intervals', 'tempo_run', 'pfa_circuit']
                workout_type = workout_types[day_index % len(workout_types)]
            elif normalized_day in schedule['strength_days']:
                workout_type = 'strength_core'
            elif normalized_day in schedule['rest_days']:
                # Optional easy activity on rest days
                if normalized_day == 'Sat':
                    workout_type = 'easy_run'
                else:
                    return {'type': 'rest', 'activity': 'Complete rest or light stretching'}
            else:
                workout_type = 'easy_run'

        # Generate workout using appropriate method
        if workout_type in self.workout_types:
            workout = self.workout_types[workout_type](week, volume_multiplier)
            workout['week'] = week + 1
            workout['day'] = day
            workout['volume_multiplier'] = volume_multiplier

            # Add workout time based on day type
            if 'workout_times' not in self.training_config:
                raise ValueError("Missing 'workout_times' configuration")

            workout_times = self.training_config['workout_times']

            if normalized_day in self.training_config['schedule']['workout_days']:
                if 'workout_days' not in workout_times:
                    raise ValueError("Missing 'workout_days' time in workout_times config")
                workout['time'] = workout_times['workout_days']
            elif normalized_day in self.training_config['schedule']['strength_days']:
                if 'strength_days' not in workout_times:
                    raise ValueError("Missing 'strength_days' time in workout_times config")
                workout['time'] = workout_times['strength_days']
            elif normalized_day in ['Sat']:
                if 'easy_days' not in workout_times:
                    raise ValueError("Missing 'easy_days' time in workout_times config")
                workout['time'] = workout_times['easy_days']
            else:
                raise ValueError(f"No workout time configured for day: {normalized_day}")

            return workout
        else:
            raise ValueError(f"Unknown workout type: {workout_type}")

    def generate_weekly_workouts(self, week: int) -> Dict[str, Dict[str, Any]]:
        """Generate complete weekly workout plan."""
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekly_workouts = {}

        for day in days:
            workout = self.get_workout_for_day(day, week)
            weekly_workouts[day] = workout

        return weekly_workouts

    def generate_full_program(self, weeks: int) -> Dict[str, Any]:
        """Generate complete multi-week training program."""
        program = {
            'total_weeks': weeks,
            'program_type': 'PFA_Preparation',
            'weekly_workouts': {}
        }

        for week in range(weeks):
            weekly_plan = self.generate_weekly_workouts(week)
            program['weekly_workouts'][f'week_{week + 1}'] = weekly_plan

        return program

    def get_intensity_distribution(self, week: int) -> Dict[str, float]:
        """Calculate weekly intensity distribution."""
        weekly_workouts = self.generate_weekly_workouts(week)
        intensity_counts = {'easy': 0, 'moderate': 0, 'hard': 0, 'rest': 0}
        total_workouts = 0

        for day, workout in weekly_workouts.items():
            if workout.get('intensity'):
                intensity_counts[workout['intensity']] += 1
                total_workouts += 1
            elif workout.get('type') == 'rest':
                intensity_counts['rest'] += 1

        # Convert to percentages
        intensity_distribution = {}
        for intensity, count in intensity_counts.items():
            intensity_distribution[intensity] = (count / 7) * 100  # 7 days in week

        return intensity_distribution

    def validate_program_balance(self, weeks: int) -> Dict[str, Any]:
        """Validate program has appropriate balance of intensities and recovery."""
        validation_report = {
            'program_weeks': weeks,
            'weekly_intensity_distribution': {},
            'adaptation_weeks': [],
            'recommendations': []
        }

        adaptation_frequency = self.progression_config['adaptation_periods']['frequency']
        adaptation_weeks = self.fitness_calculator.calculate_adaptation_weeks(adaptation_frequency)
        validation_report['adaptation_weeks'] = adaptation_weeks

        # Check intensity distribution for each week
        for week in range(weeks):
            distribution = self.get_intensity_distribution(week)
            validation_report['weekly_intensity_distribution'][f'week_{week + 1}'] = distribution

            # Validate 80/20 rule (80% easy-moderate, 20% hard)
            easy_moderate = distribution.get('easy', 0) + distribution.get('moderate', 0)
            hard = distribution.get('hard', 0)

            if hard > 30:  # More than 30% hard
                validation_report['recommendations'].append(
                    f"Week {week + 1}: Consider reducing high-intensity workouts ({hard:.1f}% hard)"
                )

            if easy_moderate < 50:  # Less than 50% easy-moderate
                validation_report['recommendations'].append(
                    f"Week {week + 1}: Consider adding more easy/moderate workouts ({easy_moderate:.1f}% easy-moderate)"
                )

        return validation_report