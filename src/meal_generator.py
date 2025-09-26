#!/usr/bin/env python3
"""Advanced meal generation using structured meal database with metadata."""

import random
from typing import Dict, Any, List, Tuple, Optional, Set
from itertools import combinations


class MealGenerator:
    """Generates meal combinations from structured meal database."""

    def __init__(self, meal_database: Dict[str, Any], generation_rules: Dict[str, Any]):
        self.meal_database = meal_database
        self.generation_rules = generation_rules
        self.options_per_meal = generation_rules.get('options_per_meal', 3)
        self.combination_rules = generation_rules.get('combination_rules', {})
        self.variety_rules = generation_rules.get('variety_rules', {})

        # Track recent combinations for variety
        self.recent_combinations = {}

    def _get_items_by_component(self, component: str, meal_type: str) -> List[Dict[str, Any]]:
        """Get all items of a specific component type that are appropriate for meal type."""
        if component not in self.meal_database:
            return []

        items = []
        for item in self.meal_database[component]:
            if meal_type in item.get('meal_types', []):
                items.append(item)

        return items

    def _check_exclusions(self, selected_items: List[Dict[str, Any]]) -> bool:
        """Check if any selected items have mutual exclusions."""
        item_names = {item['name'].lower().replace(' ', '_').replace('(', '').replace(')', '')
                     for item in selected_items}

        for item in selected_items:
            exclusions = set(item.get('exclusions', []))
            if exclusions.intersection(item_names):
                return False

        return True

    def _calculate_totals(self, selected_items: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate total macros and calories for selected items."""
        totals = {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0}

        for item in selected_items:
            totals['calories'] += item.get('calories', 0)
            totals['protein'] += item.get('protein', 0)
            totals['carbs'] += item.get('carbs', 0)
            totals['fat'] += item.get('fat', 0)

        return totals

    def _meets_requirements(self, selected_items: List[Dict[str, Any]], meal_type: str) -> bool:
        """Check if combination meets meal type requirements."""
        if meal_type not in self.combination_rules:
            return True

        rules = self.combination_rules[meal_type]
        totals = self._calculate_totals(selected_items)

        # Check protein minimum
        min_protein = rules.get('min_protein', 0)
        if totals['protein'] < min_protein:
            return False

        # Check calorie range
        target_calories = rules.get('target_calories', [0, 10000])
        if not (target_calories[0] <= totals['calories'] <= target_calories[1]):
            return False

        return True

    def _format_meal_description(self, selected_items: List[Dict[str, Any]]) -> str:
        """Format selected items into a readable meal description."""
        descriptions = []
        for item in selected_items:
            name = item['name']
            portion = item.get('portion', '')
            if portion:
                descriptions.append(f"{name} ({portion})")
            else:
                descriptions.append(name)

        return " + ".join(descriptions)

    def _apply_weekend_preferences(self, items: List[Dict[str, Any]], meal_type: str,
                                  is_weekend: bool) -> List[Dict[str, Any]]:
        """Apply weekend preferences for meal selection."""
        if not is_weekend or meal_type not in self.combination_rules:
            return items

        rules = self.combination_rules[meal_type]
        weekend_prefs = rules.get('weekend_preference', [])

        if not weekend_prefs:
            return items

        # Boost priority of weekend-preferred items
        preferred_items = []
        regular_items = []

        for item in items:
            item_name_key = item['name'].lower().replace(' ', '_').replace('(', '').replace(')', '')
            if any(pref in item_name_key or pref in item.get('tags', []) for pref in weekend_prefs):
                preferred_items.append(item)
            else:
                regular_items.append(item)

        # Return preferred items first, then regular items
        return preferred_items + regular_items

    def generate_meal_options(self, meal_type: str, day: str = 'Monday',
                            num_options: Optional[int] = None) -> List[Dict[str, Any]]:
        """Generate multiple meal options for a specific meal type and day."""
        if num_options is None:
            num_options = self.options_per_meal

        is_weekend = day in ['Saturday', 'Sunday']

        if meal_type not in self.combination_rules:
            return []

        rules = self.combination_rules[meal_type]
        required_components = rules.get('required_components', [])
        optional_components = rules.get('optional_components', [])

        meal_options = []
        attempts = 0
        max_attempts = 100  # Prevent infinite loops

        while len(meal_options) < num_options and attempts < max_attempts:
            attempts += 1

            # Start with required components
            selected_items = []
            used_components = set()

            # Select required components
            for component in required_components:
                available_items = self._get_items_by_component(component, meal_type)
                available_items = self._apply_weekend_preferences(available_items, meal_type, is_weekend)

                if available_items:
                    # Filter out items that would cause exclusions
                    valid_items = []
                    for item in available_items:
                        test_items = selected_items + [item]
                        if self._check_exclusions(test_items):
                            valid_items.append(item)

                    if valid_items:
                        selected_items.append(random.choice(valid_items))
                        used_components.add(component)

            # Add some optional components (randomly choose 1-2)
            available_optional = [comp for comp in optional_components if comp not in used_components]
            num_optional = min(random.randint(1, 2), len(available_optional))

            if available_optional and num_optional > 0:
                chosen_optional = random.sample(available_optional, num_optional)

                for component in chosen_optional:
                    available_items = self._get_items_by_component(component, meal_type)
                    available_items = self._apply_weekend_preferences(available_items, meal_type, is_weekend)

                    if available_items:
                        # Filter out items that would cause exclusions
                        valid_items = []
                        for item in available_items:
                            test_items = selected_items + [item]
                            if self._check_exclusions(test_items):
                                valid_items.append(item)

                        if valid_items:
                            selected_items.append(random.choice(valid_items))

            # Check if combination meets requirements
            if selected_items and self._meets_requirements(selected_items, meal_type):
                # Create meal option
                totals = self._calculate_totals(selected_items)
                meal_description = self._format_meal_description(selected_items)

                meal_option = {
                    'description': meal_description,
                    'items': selected_items,
                    'totals': totals,
                    'prep_time': sum(item.get('prep_time', 0) for item in selected_items)
                }

                # Check if this combination is too similar to existing options
                is_duplicate = False
                for existing_option in meal_options:
                    existing_items = {item['name'] for item in existing_option['items']}
                    current_items = {item['name'] for item in selected_items}

                    # If more than 50% overlap, consider it duplicate
                    overlap = len(existing_items.intersection(current_items))
                    if overlap / max(len(existing_items), len(current_items)) > 0.5:
                        is_duplicate = True
                        break

                if not is_duplicate:
                    meal_options.append(meal_option)

        return meal_options

    def generate_daily_meal_plan(self, day: str, meal_types: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Generate complete daily meal plan with multiple options per meal."""
        daily_plan = {}

        for meal_type in meal_types:
            daily_plan[meal_type] = self.generate_meal_options(meal_type, day)

        return daily_plan

    def generate_weekly_meal_plan(self, week_number: int = 1) -> Dict[str, Any]:
        """Generate a complete weekly meal plan with multiple options."""
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekly_plan = {
            'week': week_number,
            'daily_plans': {}
        }

        for day in days:
            # Determine meal types for this day (2 meals weekdays, 3 meals weekends)
            if day in ['Saturday', 'Sunday']:
                meal_types = ['breakfast', 'lunch', 'dinner', 'snack']
            else:
                meal_types = ['breakfast', 'dinner', 'snack']

            weekly_plan['daily_plans'][day] = self.generate_daily_meal_plan(day, meal_types)

        return weekly_plan