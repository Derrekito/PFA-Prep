#!/usr/bin/env python3
"""Advanced meal generation using structured meal database with metadata."""

import random
from typing import Dict, Any, List, Tuple, Optional, Set
from itertools import combinations
from progress_utils import get_progress_tracker
from recipe_fetcher import RecipeFetcher, Recipe
from logging_config import setup_logger


class MealGenerator:
    """Generates meal combinations from structured meal database."""

    def __init__(self, meal_database: Dict[str, Any], generation_rules: Dict[str, Any],
                 recipe_config: Dict[str, Any] = None):
        self.meal_database = meal_database
        self.generation_rules = generation_rules
        self.options_per_meal = generation_rules.get('options_per_meal', 3)
        self.combination_rules = generation_rules.get('combination_rules', {})
        self.variety_rules = generation_rules.get('variety_rules', {})

        # Track recent combinations for variety
        self.recent_combinations = {}

        # Recipe integration setup
        self.logger = setup_logger('meal_generator')
        self.recipe_fetcher = RecipeFetcher(recipe_config or {}) if recipe_config else None
        self.recipe_config = recipe_config or {}

        # Recipe integration settings
        self.recipe_ratio = self.recipe_config.get('recipe_ratio', 0.3)  # 30% recipes, 70% components
        self.enable_recipes = self.recipe_config.get('enable_recipes', True)
        self.dietary_filters = self.recipe_config.get('dietary_filters', [])
        self.max_recipes_per_meal = self.recipe_config.get('max_recipes_per_meal', 2)

        # Tag filtering settings - get from nutrition config passed in generation_rules
        self.tag_filters = generation_rules.get('recipe_tags', {})

        # Cache for fetched recipes
        self._recipe_cache = {}

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

    def _generate_component_meal_options(self, meal_type: str, day: str = 'Monday',
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
                    'type': 'component_only',  # Mark as component-based meal
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

    def generate_meal_options(self, meal_type: str, day: str = 'Monday',
                             num_options: Optional[int] = None) -> List[Dict[str, Any]]:
        """Generate meal options, mixing component-based meals and recipes if available."""
        if self.recipe_fetcher and self.enable_recipes:
            # Use mixed approach with recipes
            return self.generate_mixed_meal_options(meal_type, day, num_options)
        else:
            # Use component-only approach
            return self._generate_component_meal_options(meal_type, day, num_options)

    def generate_daily_meal_plan(self, day: str, meal_types: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Generate complete daily meal plan with multiple options per meal."""
        progress = get_progress_tracker()
        progress.log_message(f"Generating daily meal plan for {day} with meals: {meal_types}")
        daily_plan = {}

        for meal_type in meal_types:
            self.logger.debug(f"Processing {meal_type} for {day}")
            progress.add_meal_progress(meal_type, day)
            daily_plan[meal_type] = self.generate_meal_options(meal_type, day)

        progress.log_message(f"Completed daily meal plan for {day}")
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

    # ===============================
    # RECIPE INTEGRATION METHODS
    # ===============================

    def _create_recipe_meal_option(self, recipe: Recipe, meal_type: str) -> Dict[str, Any]:
        """Convert a Recipe object to a meal option format."""
        # Format ingredients for display
        ingredients_text = "; ".join(recipe.ingredients[:8])  # Limit to first 8 ingredients
        if len(recipe.ingredients) > 8:
            ingredients_text += f" (and {len(recipe.ingredients) - 8} more)"

        # Format instructions for display (first 3 steps)
        instructions_text = ". ".join(recipe.instructions[:3])
        if len(recipe.instructions) > 3:
            instructions_text += f" (and {len(recipe.instructions) - 3} more steps)"

        description = f"{recipe.name} (Recipe)"
        if recipe.servings > 1:
            description += f" - Serves {recipe.servings}"

        meal_option = {
            'description': description,
            'type': 'recipe',
            'recipe_id': recipe.id,
            'recipe': {
                'name': recipe.name,
                'ingredients': recipe.ingredients,
                'instructions': recipe.instructions,
                'prep_time': recipe.prep_time,
                'cook_time': recipe.cook_time,
                'total_time': recipe.total_time,
                'servings': recipe.servings,
                'source_api': recipe.source_api,
                'source_url': recipe.source_url,
                'difficulty': recipe.difficulty,
                'tags': recipe.tags
            },
            'totals': recipe.nutrition,
            'prep_time': recipe.total_time,
            'ingredients_display': ingredients_text,
            'instructions_preview': instructions_text,
            'servings': recipe.servings,
            'source': f"Recipe from {recipe.source_api}",
            'items': []  # Empty for recipes since they're self-contained
        }

        return meal_option

    def _meets_recipe_requirements(self, recipe: Recipe, meal_type: str) -> bool:
        """Check if recipe meets meal type requirements."""
        if meal_type not in self.combination_rules:
            return True

        rules = self.combination_rules[meal_type]

        # Check protein minimum
        min_protein = rules.get('min_protein', 0)
        if recipe.nutrition.get('protein', 0) < min_protein:
            return False

        # Check calorie range
        target_calories = rules.get('target_calories', [0, 10000])
        recipe_calories = recipe.nutrition.get('calories', 0)
        if not (target_calories[0] <= recipe_calories <= target_calories[1]):
            return False

        return True

    def _meets_tag_requirements(self, recipe: Recipe) -> bool:
        """Check if recipe meets tag filtering requirements."""
        if not self.tag_filters:
            return True

        recipe_tags = recipe.tags or []

        # Check include tags - recipe must have at least one of these tags
        include_tags = self.tag_filters.get('include_tags', [])
        if include_tags:
            has_include_tag = any(tag in recipe_tags for tag in include_tags)
            if not has_include_tag:
                self.logger.debug(f"Recipe '{recipe.name}' excluded: missing required tags {include_tags} (has: {recipe_tags})")
                return False

        # Check exclude tags - recipe must not have any of these tags
        exclude_tags = self.tag_filters.get('exclude_tags', [])
        if exclude_tags:
            has_exclude_tag = any(tag in recipe_tags for tag in exclude_tags)
            if has_exclude_tag:
                self.logger.debug(f"Recipe '{recipe.name}' excluded: has forbidden tags {exclude_tags} (has: {recipe_tags})")
                return False

        return True

    def generate_mixed_meal_options(self, meal_type: str, day: str, num_options: int = None) -> List[Dict[str, Any]]:
        """Generate meal options mixing component-based meals and recipes."""
        if num_options is None:
            num_options = self.options_per_meal

        meal_options = []

        # Calculate split between component meals and recipes
        target_recipes = min(self.max_recipes_per_meal, max(1, int(num_options * self.recipe_ratio)))
        target_components = num_options - target_recipes

        # Generate component-based meals first
        component_meals = self._generate_component_meal_options(meal_type, day, target_components)
        meal_options.extend(component_meals)

        # Add recipes if enabled
        if self.recipe_fetcher and self.enable_recipes:
            try:
                # Get recipes for this meal type
                recipes = self._get_recipes_for_meal(meal_type)

                # Convert recipes to meal options
                recipes_added = 0
                for recipe in recipes[:target_recipes]:
                    recipe_option = self._create_recipe_meal_option(recipe, meal_type)
                    meal_options.append(recipe_option)
                    recipes_added += 1

                # Update progress with recipe info
                if recipes:
                    progress = get_progress_tracker()
                    progress.add_recipe_progress(len(recipes), meal_type)

                # If we didn't get enough recipes, fill with more component meals
                if recipes_added < target_recipes and len(component_meals) < num_options:
                    additional_components = self._generate_component_meal_options(
                        meal_type, day, num_options - len(meal_options)
                    )
                    meal_options.extend(additional_components)

            except Exception as e:
                self.logger.error(f"Error adding recipes to {meal_type}: {e}")
                # Fill with more component meals if recipes failed
                if len(meal_options) < num_options:
                    additional_components = self._generate_component_meal_options(
                        meal_type, day, num_options - len(meal_options)
                    )
                    meal_options.extend(additional_components)

        return meal_options[:num_options]

    def _get_recipes_for_meal(self, meal_type: str) -> List[Recipe]:
        """Get suitable recipes for a meal type."""
        if not self.recipe_fetcher:
            return []

        # Get sample components for this meal type to use for recipe search
        meal_components = []
        if meal_type in self.combination_rules:
            rules = self.combination_rules[meal_type]
            required_components = rules.get('required_components', [])

            # Get representative items from each required component
            for component in required_components[:2]:  # Limit to first 2 components
                items = self._get_items_by_component(component, meal_type)
                if items:
                    meal_components.append(items[0])  # Use first item as representative

        # Try to find recipes matching meal components
        recipes = self.recipe_fetcher.find_recipes_for_meal_components(
            meal_components, meal_type, self.dietary_filters
        )

        # Filter recipes that meet requirements
        suitable_recipes = []
        for recipe in recipes:
            if (self._meets_recipe_requirements(recipe, meal_type) and
                self._meets_tag_requirements(recipe)):
                suitable_recipes.append(recipe)

        return suitable_recipes[:self.max_recipes_per_meal]