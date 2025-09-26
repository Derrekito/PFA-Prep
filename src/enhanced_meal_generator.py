#!/usr/bin/env python3
"""Enhanced meal generator that integrates both component-based meals and full recipes."""

import random
from typing import Dict, Any, List, Tuple, Optional, Set
from dataclasses import asdict
import logging

from meal_generator import MealGenerator
from recipe_fetcher import RecipeFetcher, Recipe
from logging_config import setup_logger, set_logging_level


class EnhancedMealGenerator(MealGenerator):
    """Extended meal generator that can create both component-based meals and full recipes."""

    def __init__(self, meal_database: Dict[str, Any], generation_rules: Dict[str, Any],
                 recipe_config: Dict[str, Any] = None):
        super().__init__(meal_database, generation_rules)

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

    def _adjust_recipe_nutrition_for_portion(self, recipe: Recipe, target_calories: Tuple[int, int]) -> Recipe:
        """Adjust recipe nutrition and serving size to fit calorie targets."""
        current_calories = recipe.nutrition.get('calories', 0)
        if current_calories == 0:
            return recipe

        target_mid = (target_calories[0] + target_calories[1]) / 2
        portion_multiplier = target_mid / current_calories

        # Don't adjust if the multiplier is too extreme
        if portion_multiplier < 0.3 or portion_multiplier > 3.0:
            return recipe

        # Create adjusted recipe
        adjusted_recipe = Recipe(
            id=recipe.id,
            name=recipe.name,
            ingredients=recipe.ingredients,
            instructions=recipe.instructions,
            prep_time=recipe.prep_time,
            cook_time=recipe.cook_time,
            total_time=recipe.total_time,
            servings=max(1, int(recipe.servings * portion_multiplier)),
            nutrition={
                'calories': recipe.nutrition.get('calories', 0) * portion_multiplier,
                'protein': recipe.nutrition.get('protein', 0) * portion_multiplier,
                'carbs': recipe.nutrition.get('carbs', 0) * portion_multiplier,
                'fat': recipe.nutrition.get('fat', 0) * portion_multiplier
            },
            tags=recipe.tags,
            source_api=recipe.source_api,
            source_url=recipe.source_url,
            difficulty=recipe.difficulty,
            meal_types=recipe.meal_types
        )

        return adjusted_recipe

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

    def _fetch_recipes_for_meal(self, meal_type: str, selected_components: List[Dict[str, Any]] = None) -> List[Recipe]:
        """Fetch appropriate recipes for a meal type."""
        self.logger.debug(f"_fetch_recipes_for_meal called for {meal_type}")

        if not self.recipe_fetcher or not self.enable_recipes:
            self.logger.warning(f"Recipe fetcher not available or disabled")
            return []

        cache_key = f"{meal_type}_{hash(str(selected_components)) if selected_components else 'general'}"
        self.logger.debug(f"Cache key: {cache_key}")

        # Check cache first
        cached_recipes = self.recipe_fetcher.get_cached_recipes(cache_key)
        if cached_recipes:
            self.logger.info(f"Found {len(cached_recipes)} cached recipes")
            return cached_recipes
        else:
            self.logger.debug(f"No cached recipes, fetching fresh")

        # Get ingredients from selected components or use general meal type ingredients
        if selected_components:
            self.logger.debug(f"Using components: {[c['name'] for c in selected_components]}")
            recipes = self.recipe_fetcher.find_recipes_for_meal_components(
                selected_components, meal_type, self.dietary_filters
            )
        else:
            # Get popular ingredients for this meal type from our database
            popular_ingredients = self._get_popular_ingredients_for_meal_type(meal_type)
            print(f"      🌶️ Popular ingredients for {meal_type}: {popular_ingredients}")
            recipes = self.recipe_fetcher.fetch_recipes_for_ingredients(
                popular_ingredients, self.dietary_filters, max_recipes=10
            )

        self.logger.debug(f"Raw recipes found: {len(recipes)}")

        # Filter recipes that meet our requirements
        suitable_recipes = []
        for recipe in recipes:
            if self._meets_recipe_requirements(recipe, meal_type) and self._meets_tag_requirements(recipe):
                suitable_recipes.append(recipe)

        self.logger.info(f"Filtered {len(suitable_recipes)} suitable recipes from {len(recipes)} total for {meal_type}")

        # Adjust portions for calorie targets if needed
        rules = self.combination_rules.get(meal_type, {})
        target_calories = rules.get('target_calories', [0, 10000])
        adjusted_recipes = []

        for recipe in suitable_recipes:
            adjusted = self._adjust_recipe_nutrition_for_portion(recipe, target_calories)
            adjusted_recipes.append(adjusted)

        # Cache the results
        self.recipe_fetcher.cache_recipes(adjusted_recipes, cache_key)

        final_count = min(len(adjusted_recipes), self.max_recipes_per_meal)
        self.logger.info(f"Returning {final_count} recipes for {meal_type}")
        return adjusted_recipes[:self.max_recipes_per_meal]

    def _extract_main_ingredient(self, name: str) -> str:
        """Extract the main ingredient from a food name, identifying the key noun."""
        # Clean up the name by removing parenthetical info
        clean_name = name.lower().split('(')[0].strip()
        words = clean_name.split()

        # Remove modifiers but keep the core ingredient
        skip_modifiers = ['low', 'sodium', 'fresh', 'organic', 'lean', 'plain', 'cooked', 'dry', 'large', 'medium', 'small']
        filtered_words = [word for word in words if word not in skip_modifiers]

        if not filtered_words:
            return ""

        # Identify key ingredient patterns
        key_ingredients = {
            # Proteins
            'chicken', 'turkey', 'beef', 'pork', 'fish', 'eggs', 'yogurt', 'protein', 'bacon', 'jerky', 'nuts',
            # Carbs
            'oats', 'rice', 'potato', 'quinoa', 'toast', 'bread',
            # Vegetables
            'broccoli', 'spinach', 'peppers', 'asparagus', 'sprouts', 'mushrooms', 'cauliflower', 'greens', 'cabbage', 'avocado',
            # Fruits
            'blueberries', 'banana', 'apple', 'strawberries', 'grapes', 'orange', 'pineapple', 'mango', 'pear'
        }

        # Look for key ingredients in the words
        for word in filtered_words:
            if word in key_ingredients:
                # For compound names, include the modifier if it's meaningful
                word_index = filtered_words.index(word)
                if word_index > 0:
                    prev_word = filtered_words[word_index - 1]
                    # Keep meaningful modifiers
                    if prev_word in ['deli', 'ground', 'steel-cut', 'whole', 'sweet', 'mixed', 'rotisserie', 'bell']:
                        return f"{prev_word} {word}"
                return word

        # Fallback: if no key ingredient found, use first 2 words or handle special cases
        if len(filtered_words) >= 2:
            # Special handling for compound foods
            compound = ' '.join(filtered_words[:2])
            if any(x in compound for x in ['protein bar', 'fish sticks', 'steel cut', 'whole grain']):
                return compound

        return filtered_words[0] if filtered_words else ""

    def _get_popular_ingredients_for_meal_type(self, meal_type: str) -> List[str]:
        """Get popular ingredients for a meal type from our database."""
        ingredients = []

        # Get proteins appropriate for this meal type
        proteins = self._get_items_by_component('proteins', meal_type)
        if proteins:
            # Extract main ingredient names using proper logic
            for protein in proteins[:3]:  # Top 3 proteins
                main_ingredient = self._extract_main_ingredient(protein['name'])
                if main_ingredient:
                    ingredients.append(main_ingredient)

        # Add some popular carbs for lunch/dinner
        if meal_type in ['lunch', 'dinner']:
            carbs = self._get_items_by_component('carbs', meal_type)
            if carbs:
                carb_name = self._extract_main_ingredient(carbs[0]['name'])
                if carb_name:
                    ingredients.append(carb_name)

        # Add vegetables for lunch/dinner
        if meal_type in ['lunch', 'dinner']:
            vegetables = self._get_items_by_component('vegetables', meal_type)
            if vegetables:
                veg_name = self._extract_main_ingredient(vegetables[0]['name'])
                if veg_name:
                    ingredients.append(veg_name)

        return ingredients

    def generate_mixed_meal_options(self, meal_type: str, day: str = 'Monday',
                                   num_options: Optional[int] = None) -> List[Dict[str, Any]]:
        """Generate meal options mixing component-based meals and full recipes."""
        if num_options is None:
            num_options = self.options_per_meal

        meal_options = []

        # Generate component-based meals first (these are our base ingredients from meal_database.yml)
        component_meals = super().generate_meal_options(meal_type, day, num_options)

        # For each component meal, try to find a matching recipe
        for component_meal in component_meals:
            enhanced_option = component_meal.copy()

            # Try to find a recipe that matches/complements the components
            if self.recipe_fetcher and self.enable_recipes:
                try:
                    component_ingredients = [item['name'] for item in component_meal.get('items', [])]
                    recipes = self._fetch_recipes_for_meal(meal_type, component_meal.get('items', []))

                    if recipes:
                        # Use the first matching recipe
                        recipe = recipes[0]
                        print(f"    🍳 Enhanced {meal_type} with recipe: {recipe.name}")

                        # Add recipe information to the component meal
                        enhanced_option['type'] = 'component_with_recipe'
                        enhanced_option['recipe'] = {
                            'name': recipe.name,
                            'ingredients': recipe.ingredients,
                            'instructions': recipe.instructions,
                            'prep_time': recipe.prep_time,
                            'cook_time': recipe.cook_time,
                            'servings': recipe.servings,
                            'difficulty': getattr(recipe, 'difficulty', 'medium'),
                            'source_url': getattr(recipe, 'source_url', ''),
                            'tags': getattr(recipe, 'tags', [])
                        }

                        # Update description to include recipe
                        base_desc = enhanced_option.get('description', '')
                        enhanced_option['description'] = f"{base_desc} + {recipe.name} Recipe"

                        # Add recipe display info
                        ingredients_text = "; ".join(recipe.ingredients[:8])
                        if len(recipe.ingredients) > 8:
                            ingredients_text += f" (and {len(recipe.ingredients) - 8} more)"
                        enhanced_option['ingredients_display'] = ingredients_text

                        instructions_text = ". ".join(recipe.instructions[:3])
                        if len(recipe.instructions) > 3:
                            instructions_text += f" (and {len(recipe.instructions) - 3} more steps)"
                        enhanced_option['instructions_preview'] = instructions_text
                    else:
                        self.logger.warning(f"No matching recipe found for {meal_type} components")
                        enhanced_option['type'] = 'component_with_no_recipe'

                        # Add "No recipe found" placeholder
                        enhanced_option['recipe'] = {
                            'name': 'No recipe found',
                            'ingredients': [],
                            'instructions': ['No recipe available for this ingredient combination'],
                            'prep_time': 0,
                            'cook_time': 0,
                            'servings': 1,
                            'difficulty': '',
                            'source_url': '',
                            'tags': []
                        }

                        # Update description to show no recipe found
                        base_desc = enhanced_option.get('description', '')
                        enhanced_option['description'] = f"{base_desc} (No recipe found)"

                        # Add placeholder display info
                        enhanced_option['ingredients_display'] = 'No recipe available'
                        enhanced_option['instructions_preview'] = 'No recipe found for this ingredient combination'

                except Exception as e:
                    self.logger.error(f"Failed to enhance {meal_type} with recipe: {e}")
                    enhanced_option['type'] = 'component_only'
            else:
                enhanced_option['type'] = 'component_only'

            meal_options.append(enhanced_option)

        return meal_options[:num_options]

    def generate_daily_meal_plan(self, day: str, meal_types: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Generate complete daily meal plan with mixed component meals and recipes."""
        daily_plan = {}

        for meal_type in meal_types:
            daily_plan[meal_type] = self.generate_mixed_meal_options(meal_type, day)

        return daily_plan

    def generate_recipe_focused_meal_options(self, meal_type: str, ingredients: List[str],
                                           num_options: int = 3) -> List[Dict[str, Any]]:
        """Generate meal options focused entirely on recipes with specific ingredients."""
        if not self.recipe_fetcher or not self.enable_recipes:
            return self.generate_meal_options(meal_type, num_options=num_options)

        meal_options = []

        try:
            recipes = self.recipe_fetcher.fetch_recipes_for_ingredients(
                ingredients, self.dietary_filters, max_recipes=num_options * 2
            )

            # Filter for appropriate meal type and requirements
            suitable_recipes = []
            for recipe in recipes:
                if (meal_type in recipe.meal_types and
                    self._meets_recipe_requirements(recipe, meal_type)):
                    suitable_recipes.append(recipe)

            # Convert to meal options
            for recipe in suitable_recipes[:num_options]:
                recipe_option = self._create_recipe_meal_option(recipe, meal_type)
                meal_options.append(recipe_option)

        except Exception as e:
            self.logger.error(f"Error generating recipe-focused meals: {e}")
            # Fallback to component-based meals
            return self.generate_meal_options(meal_type, num_options=num_options)

        # Fill remaining slots with component meals if needed
        while len(meal_options) < num_options:
            component_meals = self.generate_meal_options(meal_type, num_options=1)
            if component_meals:
                meal_options.extend(component_meals)
            else:
                break

        return meal_options[:num_options]

    def get_meal_option_summary(self, meal_option: Dict[str, Any]) -> str:
        """Get a concise summary of a meal option for display."""
        if meal_option.get('type') == 'recipe':
            recipe_info = meal_option.get('recipe', {})
            summary = f"🍳 {recipe_info.get('name', 'Recipe')}"

            total_time = recipe_info.get('total_time', 0)
            if total_time > 0:
                summary += f" ({total_time}min)"

            difficulty = recipe_info.get('difficulty', 'medium')
            if difficulty != 'medium':
                summary += f" [{difficulty.title()}]"

            return summary
        else:
            # Component-based meal
            return f"🥗 {meal_option.get('description', 'Component Meal')}"

    def get_detailed_meal_info(self, meal_option: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a meal option."""
        base_info = {
            'type': meal_option.get('type', 'component'),
            'description': meal_option.get('description', ''),
            'nutrition': meal_option.get('totals', {}),
            'prep_time': meal_option.get('prep_time', 0)
        }

        if meal_option.get('type') == 'recipe':
            recipe_info = meal_option.get('recipe', {})
            base_info.update({
                'recipe_name': recipe_info.get('name', ''),
                'ingredients': recipe_info.get('ingredients', []),
                'instructions': recipe_info.get('instructions', []),
                'servings': recipe_info.get('servings', 1),
                'cook_time': recipe_info.get('cook_time', 0),
                'difficulty': recipe_info.get('difficulty', 'medium'),
                'source_url': recipe_info.get('source_url', ''),
                'tags': recipe_info.get('tags', [])
            })
        else:
            base_info.update({
                'components': meal_option.get('items', []),
                'component_details': [
                    {
                        'name': item.get('name', ''),
                        'portion': item.get('portion', ''),
                        'calories': item.get('calories', 0),
                        'protein': item.get('protein', 0)
                    }
                    for item in meal_option.get('items', [])
                ]
            })

        return base_info