#!/usr/bin/env python3
"""Nutrition planning system with calorie/macro calculations and meal scheduling."""

from datetime import datetime, time, timedelta
from typing import Dict, Any, List, Tuple, Optional
import random


class NutritionPlanner:
    """Handles meal planning, macro distribution, and eating window management."""

    def __init__(self, nutrition_config: Dict[str, Any]):
        self.config = nutrition_config
        self.target_calories = nutrition_config['calorie_goals']['target']
        self.macros = nutrition_config['macros']
        self.eating_window = nutrition_config['eating_window']
        self.meal_timing = nutrition_config['meal_timing']
        self.dietary_preferences = nutrition_config['dietary_preferences']

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
            start_time = datetime.strptime(self.eating_window['start_time'], "%H:%M").time()
            end_time = datetime.strptime(self.eating_window['end_time'], "%H:%M").time()
            return start_time, end_time
        else:
            # Default to full day if not time restricted
            return time(6, 0), time(22, 0)

    def calculate_meal_times(self, workout_time: Optional[time] = None) -> Dict[str, time]:
        """Calculate optimal meal times based on eating window and workout schedule."""
        start_time, end_time = self.get_eating_window()

        # Convert times to minutes for easier calculation
        start_minutes = start_time.hour * 60 + start_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute

        # If end time is before start time, it crosses midnight
        if end_minutes <= start_minutes:
            end_minutes += 24 * 60

        eating_duration = end_minutes - start_minutes
        meals_per_day = self.meal_timing['meals_per_day']
        snacks_per_day = self.meal_timing['snacks_per_day']
        total_eating_events = meals_per_day + snacks_per_day

        meal_times = {}

        if workout_time:
            workout_minutes = workout_time.hour * 60 + workout_time.minute
            pre_workout_offset = self.meal_timing['pre_workout']
            post_workout_offset = self.meal_timing['post_workout']

            # Schedule pre-workout meal/snack
            pre_workout_minutes = workout_minutes + pre_workout_offset
            if start_minutes <= pre_workout_minutes <= end_minutes:
                meal_times['pre_workout'] = time(pre_workout_minutes // 60, pre_workout_minutes % 60)

            # Schedule post-workout meal/snack
            post_workout_minutes = workout_minutes + post_workout_offset
            if start_minutes <= post_workout_minutes <= end_minutes:
                meal_times['post_workout'] = time(post_workout_minutes // 60, post_workout_minutes % 60)

        # Schedule main meals evenly within eating window
        meal_interval = eating_duration // (meals_per_day + 1)

        for i in range(meals_per_day):
            meal_minutes = start_minutes + meal_interval * (i + 1)
            meal_minutes = meal_minutes % (24 * 60)  # Handle day overflow
            meal_name = ['breakfast', 'lunch', 'dinner'][i] if i < 3 else f'meal_{i+1}'
            meal_times[meal_name] = time(meal_minutes // 60, meal_minutes % 60)

        # Schedule snacks between meals
        if snacks_per_day > 0:
            snack_interval = eating_duration // (snacks_per_day + 1)
            for i in range(snacks_per_day):
                snack_minutes = start_minutes + meal_interval // 2 + snack_interval * i
                snack_minutes = snack_minutes % (24 * 60)
                meal_times[f'snack_{i+1}'] = time(snack_minutes // 60, snack_minutes % 60)

        return meal_times

    def generate_meal_options(self) -> Dict[str, List[str]]:
        """Generate meal options based on dietary preferences."""
        restrictions = self.dietary_preferences['restrictions']
        allergies = self.dietary_preferences['allergies']
        dislikes = self.dietary_preferences['dislikes']

        # Base meal options - would be expanded with more variety
        meal_options = {
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
        }

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

    def calculate_meal_macros(self, meal_type: str) -> Dict[str, int]:
        """Calculate macro distribution for a specific meal type."""
        total_macros = self.calculate_macro_grams()
        meals_per_day = self.meal_timing['meals_per_day']
        snacks_per_day = self.meal_timing['snacks_per_day']

        # Distribution strategy: meals get more calories than snacks
        if meal_type in ['breakfast', 'lunch', 'dinner']:
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

        # Calculate default meal times (without workout consideration)
        meal_times = self.calculate_meal_times()

        weekly_plan = {
            'week': week_number,
            'total_daily_calories': self.target_calories,
            'daily_macro_targets': macro_grams,
            'meal_times': {k: v.strftime('%H:%M') for k, v in meal_times.items()},
            'daily_meals': {}
        }

        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        for day in days:
            daily_meals = {}

            # Select meals with some variety (avoid same meal 2 days in a row)
            for meal_type in ['breakfast', 'lunch', 'dinner']:
                if meal_type in meal_options:
                    options = meal_options[meal_type]
                    if options:
                        daily_meals[meal_type] = random.choice(options)
                        daily_meals[f'{meal_type}_macros'] = self.calculate_meal_macros(meal_type)

            # Add snacks
            for i in range(self.meal_timing['snacks_per_day']):
                snack_name = f'snack_{i+1}'
                if 'snacks' in meal_options and meal_options['snacks']:
                    daily_meals[snack_name] = random.choice(meal_options['snacks'])
                    daily_meals[f'{snack_name}_macros'] = self.calculate_meal_macros('snack')

            weekly_plan['daily_meals'][day] = daily_meals

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