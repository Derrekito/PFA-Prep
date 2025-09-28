#!/usr/bin/env python3
"""Nutrition planning system with calorie/macro calculations and meal scheduling."""

from datetime import datetime, time, timedelta
from typing import Dict, Any, List, Tuple, Optional
import random
from time_utils import (
    parse_time_string, time_to_minutes, minutes_to_time,
    calculate_eating_duration, add_minutes_to_time, is_time_in_window
)
from meal_generator import MealGenerator
from logging_config import setup_logger


class NutritionPlanner:
    """Handles meal planning, macro distribution, and eating window management."""

    def __init__(self, nutrition_config, meal_generator=None):
        # Handle both dict and dataclass inputs
        if hasattr(nutrition_config, '__dict__'):
            # It's a dataclass, convert to dict
            self.config = nutrition_config.__dict__
        else:
            # It's already a dict
            self.config = nutrition_config

        self.target_calories = self.config['calorie_goals']['target']
        self.macros = self.config['macros']
        self.eating_window = self.config['eating_window']
        self.meal_timing = self.config['meal_timing']
        self.dietary_preferences = self.config['dietary_preferences']
        self._warned_meal_times = set()  # Track which meal times we've warned about

        # Use provided meal generator or create default one if meal database is available
        if meal_generator:
            self.meal_generator = meal_generator
        elif (self.config.get('meal_database') is not None and
              self.config.get('meal_generation') is not None):
            self.meal_generator = MealGenerator(
                self.config['meal_database'],
                self.config['meal_generation']
            )
        else:
            self.meal_generator = None

        # Set up logging
        self.logger = setup_logger('nutrition_planner')

    def calculate_macro_grams(self) -> Dict[str, int]:
        """Convert macro percentages to gram targets based on calorie goal."""
        # Calories per gram: Protein=4, Carbs=4, Fat=9
        calories_per_gram = {'protein': 4, 'carbs': 4, 'fat': 9}

        macro_grams = {}
        for macro, percentage in self.macros.items():
            macro_calories = (percentage / 100) * self.target_calories
            macro_grams[macro] = int(round(macro_calories / calories_per_gram[macro]))

        return macro_grams

    def get_eating_window(self) -> Tuple[time, time]:
        """Get the eating window start and end times."""
        if self.eating_window['type'] == 'time_restricted':
            start_time = parse_time_string(self.eating_window['start_time'])
            end_time = parse_time_string(self.eating_window['end_time'])
            return start_time, end_time
        else:
            # Default to full day if not time restricted
            return time(6, 0), time(22, 0)

    def calculate_meal_times(self, workout_time: Optional[time] = None, day_name: Optional[str] = None) -> Dict[str, time]:
        """Calculate optimal meal times based on eating window and workout schedule."""
        # Check if manual scheduling is configured
        if 'manual_schedule' in self.meal_timing:
            return self._get_manual_meal_times(day_name, workout_time)

        # Fall back to automatic calculation
        start_time, end_time = self.get_eating_window()

        start_minutes = time_to_minutes(start_time)
        eating_duration = calculate_eating_duration(start_time, end_time)
        meals_per_day = self.meal_timing['meals_per_day']
        snacks_per_day = self.meal_timing['snacks_per_day']

        meal_times = {}

        if workout_time:
            pre_workout_offset = int(self.meal_timing['pre_workout'])  # Should be negative
            post_workout_offset = int(self.meal_timing['post_workout'])  # Should be positive

            # Schedule pre-workout meal/snack
            pre_workout_time = add_minutes_to_time(workout_time, pre_workout_offset)
            if is_time_in_window(pre_workout_time, start_time, end_time):
                meal_times['pre_workout'] = pre_workout_time

            # Schedule post-workout meal/snack
            post_workout_time = add_minutes_to_time(workout_time, post_workout_offset)
            if is_time_in_window(post_workout_time, start_time, end_time):
                meal_times['post_workout'] = post_workout_time

        # Schedule main meals evenly within eating window
        meal_interval = eating_duration // (meals_per_day + 1)

        for i in range(meals_per_day):
            meal_minutes = start_minutes + meal_interval * (i + 1)
            meal_name = f'meal_{i+1}'
            meal_times[meal_name] = minutes_to_time(meal_minutes)

        # Schedule snacks between meals
        if snacks_per_day > 0:
            snack_interval = eating_duration // (snacks_per_day + 1)
            for i in range(snacks_per_day):
                snack_minutes = start_minutes + meal_interval // 2 + snack_interval * i
                meal_times[f'snack_{i+1}'] = minutes_to_time(snack_minutes)

        return meal_times

    def _get_manual_meal_times(self, day_name: Optional[str], workout_time: Optional[time] = None) -> Dict[str, time]:
        """Get meal times from manual schedule configuration."""
        manual_schedule = self.meal_timing['manual_schedule']
        normalized_day = self._normalize_day_name(day_name) if day_name else None
        meal_times = {}

        # Process each meal schedule entry
        for meal_entry in manual_schedule:
            meal_name = meal_entry['name']
            meal_time_str = meal_entry['time']
            meal_days = meal_entry.get('days', [])

            # Check if this meal applies to the current day
            if not normalized_day or normalized_day in meal_days:
                meal_times[meal_name] = parse_time_string(meal_time_str)

        # Validate meal times are within eating window
        self._validate_meal_times_in_window(meal_times, day_name)

        # Add workout-based meals if needed
        if workout_time:
            start_time, end_time = self.get_eating_window()
            pre_workout_offset = int(self.meal_timing['pre_workout'])  # Should be negative
            post_workout_offset = int(self.meal_timing['post_workout'])  # Should be positive

            # Schedule pre-workout meal/snack
            pre_workout_time = add_minutes_to_time(workout_time, pre_workout_offset)
            if is_time_in_window(pre_workout_time, start_time, end_time):
                meal_times['pre_workout'] = pre_workout_time

            # Schedule post-workout meal/snack
            post_workout_time = add_minutes_to_time(workout_time, post_workout_offset)
            if is_time_in_window(post_workout_time, start_time, end_time):
                meal_times['post_workout'] = post_workout_time

        return meal_times

    def _get_meals_per_day(self, day: str) -> int:
        """Get the number of meals for a specific day based on weekday/weekend configuration."""
        # Check if we have day-specific configuration
        if 'weekdays' in self.meal_timing and 'weekends' in self.meal_timing:
            if day in ['Saturday', 'Sunday']:
                return self.meal_timing['weekends']['meals_per_day']
            else:
                return self.meal_timing['weekdays']['meals_per_day']

        # Fallback to general configuration
        return self.meal_timing.get('meals_per_day', 2)

    def _get_snacks_per_day(self, day: str) -> int:
        """Get the number of snacks for a specific day based on weekday/weekend configuration."""
        # Check if we have day-specific configuration
        if 'weekdays' in self.meal_timing and 'weekends' in self.meal_timing:
            if day in ['Saturday', 'Sunday']:
                return self.meal_timing['weekends']['snacks_per_day']
            else:
                return self.meal_timing['weekdays']['snacks_per_day']

        # Fallback to general configuration
        return self.meal_timing.get('snacks_per_day', 1)

    def _normalize_day_name(self, day: str) -> str:
        """Convert full day names to abbreviated format for config consistency."""
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

    def _validate_meal_times_in_window(self, meal_times: Dict[str, time], day_name: Optional[str] = None):
        """Validate that all meal times fall within the eating window."""
        start_time, end_time = self.get_eating_window()
        day_context = f" for {day_name}" if day_name else ""
        violations = []

        for meal_type, meal_time in meal_times.items():
            if not is_time_in_window(meal_time, start_time, end_time):
                warning_key = f"{meal_type}_{meal_time.strftime('%H:%M')}"
                if warning_key not in self._warned_meal_times:
                    violation_msg = f"{meal_type} at {meal_time.strftime('%H:%M')} is outside eating window ({start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}){day_context}"
                    violations.append(violation_msg)
                    self._warned_meal_times.add(warning_key)

        if violations:
            self.logger.warning("Meal timing issues detected:")
            for violation in violations:
                self.logger.warning(f"  {violation}")
            self.logger.info("Proceeding with meal plan despite timing violations")

    def generate_meal_options(self) -> Dict[str, List[str]]:
        """Generate meal options based on dietary preferences."""
        restrictions = self.dietary_preferences['restrictions']
        allergies = self.dietary_preferences['allergies']
        dislikes = self.dietary_preferences['dislikes']

        # Get meal options from config, with fallback to defaults if not configured
        meal_options = self.config.get('meal_options', {
            'breakfast': [
                'Oats + berries + protein powder',
                'Scrambled eggs + spinach + toast',
                'Greek yogurt + granola + fruit',
                'Omelet with vegetables',
                'Protein smoothie + banana',
                'Avocado toast + eggs',
                'Overnight oats + nuts'
            ],
            'lunch': [
                'Chicken + rice bowl + vegetables',
                'Turkey sandwich (whole grain)',
                'Turkey lettuce wraps + vegetables',
                'Chicken + quinoa + salad',
                'Beef + sweet potato + broccoli',
                'Tuna salad + whole grain crackers',
                'Grilled chicken + pasta + vegetables'
            ],
            'dinner': [
                'Grilled chicken + sweet potato + asparagus',
                'Ground beef stir-fry + rice + vegetables',
                'Salmon + quinoa + steamed vegetables',
                'Turkey burger + roasted vegetables',
                'Beef + cauliflower rice + green beans',
                'Chicken thighs + brown rice + Brussels sprouts',
                'Pork tenderloin + roasted sweet potatoes + salad'
            ],
            'snacks': [
                'Protein shake (20-30g)',
                'Greek yogurt + fruit',
                'Nuts + apple slices',
                'Hard-boiled eggs',
                'String cheese + vegetables',
                'Protein bar + water',
                'Cottage cheese + berries'
            ]
        })

        # Filter out options based on dietary restrictions
        filtered_options = {}
        for meal_type, options in meal_options.items():
            filtered_options[meal_type] = []
            for option in options:
                include_option = True

                # Check restrictions
                if 'vegetarian' in restrictions:
                    meat_keywords = ['chicken', 'beef', 'turkey', 'pork', 'tuna', 'salmon']
                    if any(keyword in option.lower() for keyword in meat_keywords):
                        include_option = False

                if 'vegan' in restrictions:
                    animal_keywords = ['chicken', 'beef', 'turkey', 'pork', 'tuna', 'salmon',
                                     'eggs', 'yogurt', 'cheese', 'milk']
                    if any(keyword in option.lower() for keyword in animal_keywords):
                        include_option = False

                # Check allergies and dislikes
                for allergen in allergies + dislikes:
                    if allergen.lower() in option.lower():
                        include_option = False

                if include_option:
                    filtered_options[meal_type].append(option)

        return filtered_options

    def calculate_meal_macros(self, meal_type: str, day: str = 'Monday') -> Dict[str, int]:
        """Calculate macro distribution for a specific meal type and day."""
        total_macros = self.calculate_macro_grams()
        meals_per_day = self._get_meals_per_day(day)
        snacks_per_day = self._get_snacks_per_day(day)

        # Distribution strategy: meals get more calories than snacks
        if meal_type in ['breakfast', 'lunch', 'dinner'] or meal_type.startswith('meal_'):
            meal_multiplier = 0.8 / meals_per_day  # 80% of calories in main meals
        else:  # snacks
            meal_multiplier = 0.2 / snacks_per_day  # 20% of calories in snacks

        meal_macros = {}
        for macro, total_grams in total_macros.items():
            meal_macros[macro] = int(round(total_grams * meal_multiplier))

        return meal_macros

    def generate_weekly_meal_plan(self, week_number: int = 1) -> Dict[str, Any]:
        """Generate a complete weekly meal plan."""
        meal_options = self.generate_meal_options()
        macro_grams = self.calculate_macro_grams()

        weekly_plan = {
            'week': week_number,
            'total_daily_calories': self.target_calories,
            'daily_macro_targets': macro_grams,
            'meal_times': {},  # Will be populated per day
            'daily_meals': {}
        }

        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        for day in days:
            # Calculate day-specific meal times
            day_meal_times = self.calculate_meal_times(day_name=day)
            weekly_plan['meal_times'][day] = {k: v.strftime('%H:%M') for k, v in day_meal_times.items()}
            daily_meals = {}

            # Get day-specific meal count and determine meal types for the day
            meals_per_day = self._get_meals_per_day(day)

            # Define meal types based on number of meals
            if meals_per_day == 2:
                meal_types = ['breakfast', 'dinner']
            elif meals_per_day == 3:
                meal_types = ['breakfast', 'lunch', 'dinner']
            else:
                # Fallback for other configurations
                meal_types = ['breakfast'] + [f'meal_{i+1}' for i in range(1, meals_per_day)]

            # Generate meals using proper nomenclature
            for meal_type in meal_types:
                # Determine meal category for food selection
                if meal_type == 'breakfast':
                    # Use weekend breakfast options on Saturday and Sunday
                    if day in ['Saturday', 'Sunday'] and 'breakfast_weekend' in meal_options:
                        meal_category = 'breakfast_weekend'
                    else:
                        meal_category = 'breakfast'
                else:
                    # Use meal_type as category (lunch, dinner, etc.)
                    meal_category = meal_type

                # Select meal from appropriate category
                if meal_category in meal_options and meal_options[meal_category]:
                    daily_meals[meal_type] = random.choice(meal_options[meal_category])
                    daily_meals[f'{meal_type}_macros'] = self.calculate_meal_macros(meal_type, day)
                elif 'breakfast' in meal_options and meal_options['breakfast']:
                    # Fallback to breakfast options if category not available
                    daily_meals[meal_type] = random.choice(meal_options['breakfast'])
                    daily_meals[f'{meal_type}_macros'] = self.calculate_meal_macros(meal_type, day)

            # Get day-specific snack count and add snacks
            snacks_per_day = self._get_snacks_per_day(day)
            if snacks_per_day == 1:
                snack_names = ['snack']
            else:
                snack_names = [f'snack_{i+1}' for i in range(snacks_per_day)]

            for snack_name in snack_names:
                if 'snacks' in meal_options and meal_options['snacks']:
                    daily_meals[snack_name] = random.choice(meal_options['snacks'])
                    daily_meals[f'{snack_name}_macros'] = self.calculate_meal_macros('snack', day)

            weekly_plan['daily_meals'][day] = daily_meals

        return weekly_plan

    def generate_advanced_meal_plan(self, week_number: int = 1) -> Dict[str, Any]:
        """Generate meal plan using the advanced meal database system."""
        if not self.meal_generator:
            # Fallback to legacy system
            return self.generate_weekly_meal_plan(week_number)

        # Use the new meal generator
        weekly_plan = self.meal_generator.generate_weekly_meal_plan(week_number)

        # Add meal timing information
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day in days:
            if day in weekly_plan['daily_plans']:
                # Calculate day-specific meal times
                day_meal_times = self.calculate_meal_times(day_name=day)
                weekly_plan['daily_plans'][day]['meal_times'] = {
                    k: v.strftime('%H:%M') for k, v in day_meal_times.items()
                }

        # Add daily targets
        macro_grams = self.calculate_macro_grams()
        weekly_plan['total_daily_calories'] = self.target_calories
        weekly_plan['daily_macro_targets'] = macro_grams

        return weekly_plan

    def adjust_meal_timing_for_workout(self, workout_time: time, workout_day: str) -> Dict[str, time]:
        """Adjust meal timing for a specific workout day."""
        return self.calculate_meal_times(workout_time)

    def get_hydration_recommendations(self) -> Dict[str, str]:
        """Get daily hydration recommendations."""
        return {
            'daily_water': '3-4 liters',
            'pre_workout': '500ml 2 hours before, 200ml 15 minutes before',
            'during_workout': '150-250ml every 15-20 minutes',
            'post_workout': '150% of fluid lost during exercise',
            'morning': 'Start day with 500ml water',
            'with_meals': 'Limit fluids during meals to aid digestion'
        }