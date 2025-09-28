#!/usr/bin/env python3
"""Recipe fetcher that integrates multiple APIs to pull recipes based on meal database ingredients."""

import requests
import time
import json
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from urllib.parse import quote_plus

from logging_config import setup_logger, set_logging_level


@dataclass
class Recipe:
    """Standardized recipe data structure."""
    id: str
    name: str
    ingredients: List[str]
    instructions: List[str]
    prep_time: int  # minutes
    cook_time: int  # minutes
    total_time: int  # minutes
    servings: int
    nutrition: Dict[str, float]  # calories, protein, carbs, fat per serving
    tags: List[str]
    source_api: str
    source_url: Optional[str] = None
    difficulty: str = "medium"
    meal_types: List[str] = None

    def __post_init__(self):
        if self.meal_types is None:
            self.meal_types = []


class RecipeFetcher:
    """Fetches recipes from multiple APIs based on ingredients and dietary preferences."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_configs = config.get('recipe_apis', {})
        self.cache = {}
        self.logger = setup_logger('recipe_fetcher')

        # API rate limiting
        self.last_request_times = {}
        self.min_request_interval = 1.0  # seconds between requests

        # Circuit breaker to prevent hanging on failing APIs
        self.api_failure_counts = {}
        self.max_failures_per_api = 3

    def _rate_limit_wait(self, api_name: str):
        """Ensure we don't exceed API rate limits."""
        now = time.time()
        last_request = self.last_request_times.get(api_name, 0)

        time_since_last = now - last_request
        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            time.sleep(wait_time)

        self.last_request_times[api_name] = time.time()

    def _make_request(self, url: str, headers: Dict[str, str] = None, timeout: int = 5) -> Optional[Dict]:
        """Make HTTP request with error handling."""
        try:
            response = requests.get(url, headers=headers or {}, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Get API name for consistent logging
            api_name = "Unknown API"
            if "edamam.com" in url:
                api_name = "Edamam"
            elif "spoonacular.com" in url:
                api_name = "Spoonacular"
            elif "themealdb.com" in url:
                api_name = "TheMealDB"

            # Handle different status codes with logging
            if response.status_code == 400:
                self.logger.warning(f"{api_name} found no recipes for this search")
            elif response.status_code == 401:
                self.logger.error(f"{api_name} authentication failed - check API credentials")
            elif response.status_code == 402:
                self.logger.warning(f"{api_name} requires payment - consider upgrading or disable this API")
            elif response.status_code == 403:
                self.logger.error(f"{api_name} access forbidden - check API permissions")
            elif response.status_code == 429:
                self.logger.warning(f"{api_name} rate limit exceeded - requests throttled")
            else:
                self.logger.error(f"{api_name} request failed ({response.status_code})")
            return None
        except requests.exceptions.Timeout:
            self.logger.warning(f"API request timed out after {timeout}s")
            return None
        except requests.exceptions.ConnectionError:
            self.logger.warning(f"API connection failed - check network connectivity")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"API request failed - {str(e)[:50]}...")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected API error - {str(e)[:50]}...")
            return None

    def _normalize_nutrition(self, nutrition_data: Dict, servings: int = 1) -> Dict[str, float]:
        """Normalize nutrition data from different APIs."""
        # Default values
        normalized = {
            'calories': 0,
            'protein': 0,
            'carbs': 0,
            'fat': 0
        }

        if not nutrition_data:
            return normalized

        # Handle different API nutrition formats
        calories = nutrition_data.get('calories') or nutrition_data.get('energy') or 0
        protein = nutrition_data.get('protein') or nutrition_data.get('protien') or 0
        carbs = (nutrition_data.get('carbs') or
                nutrition_data.get('carbohydrates') or
                nutrition_data.get('totalCarbs') or 0)
        fat = nutrition_data.get('fat') or nutrition_data.get('totalFat') or 0

        # Convert to per-serving basis
        normalized['calories'] = float(calories) / max(servings, 1)
        normalized['protein'] = float(protein) / max(servings, 1)
        normalized['carbs'] = float(carbs) / max(servings, 1)
        normalized['fat'] = float(fat) / max(servings, 1)

        return normalized

    def fetch_themealdb_recipes(self, ingredients: List[str], dietary_filters: List[str] = None) -> List[Recipe]:
        """Fetch recipes from TheMealDB (completely free, no API key required)."""
        recipes = []
        api_name = "themealdb"

        for ingredient in ingredients[:3]:  # Limit to 3 ingredients to avoid too many requests
            self._rate_limit_wait(api_name)

            # Clean ingredient name for search
            clean_ingredient = ingredient.lower().replace('(', '').replace(')', '').split()[0]
            url = f"https://www.themealdb.com/api/json/v1/1/filter.php?i={quote_plus(clean_ingredient)}"

            data = self._make_request(url)
            if not data or 'meals' not in data or not data['meals']:
                continue

            # Get detailed info for each meal (limited to first 5 to avoid rate limits)
            for meal_summary in data['meals'][:5]:
                self._rate_limit_wait(api_name)

                detail_url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_summary['idMeal']}"
                detail_data = self._make_request(detail_url)

                if not detail_data or 'meals' not in detail_data or not detail_data['meals']:
                    continue

                meal = detail_data['meals'][0]

                # Parse ingredients (TheMealDB has up to 20 ingredient fields)
                ingredients_list = []
                for i in range(1, 21):
                    ingredient = meal.get(f'strIngredient{i}')
                    measure = meal.get(f'strMeasure{i}')
                    if ingredient and ingredient.strip():
                        if measure and measure.strip():
                            ingredients_list.append(f"{measure.strip()} {ingredient.strip()}")
                        else:
                            ingredients_list.append(ingredient.strip())

                # Parse instructions
                instructions = []
                if meal.get('strInstructions'):
                    # Split by sentences and clean up
                    raw_instructions = meal['strInstructions'].split('.')
                    instructions = [inst.strip() for inst in raw_instructions if inst.strip()]

                # Skip dessert/junk food recipes if dietary filters specified
                recipe_name = meal['strMeal'].lower()
                category = meal.get('strCategory', '').lower()

                if dietary_filters:
                    # Skip obvious desserts and junk food
                    junk_keywords = ['pancake', 'flapjack', 'cake', 'cookie', 'brownie', 'donut', 'pie',
                                   'tart', 'pudding', 'ice cream', 'candy', 'chocolate', 'dessert',
                                   'sweet', 'sugar', 'frosting', 'icing', 'syrup']
                    if any(keyword in recipe_name or keyword in category for keyword in junk_keywords):
                        continue

                # Determine meal types based on category
                meal_types = []
                if any(term in category for term in ['breakfast', 'dessert']):
                    meal_types.append('breakfast')
                if any(term in category for term in ['beef', 'chicken', 'pork', 'lamb', 'seafood']):
                    meal_types.extend(['lunch', 'dinner'])
                if not meal_types:
                    meal_types = ['lunch', 'dinner']  # Default

                # Create recipe object
                recipe = Recipe(
                    id=f"themealdb_{meal['idMeal']}",
                    name=meal['strMeal'],
                    ingredients=ingredients_list,
                    instructions=instructions,
                    prep_time=15,  # Estimated
                    cook_time=30,  # Estimated
                    total_time=45,
                    servings=4,  # Estimated
                    nutrition=self._estimate_nutrition_from_ingredients(ingredients_list),
                    tags=[meal.get('strCategory', ''), meal.get('strArea', '')],
                    source_api="themealdb",
                    source_url=f"https://www.themealdb.com/meal/{meal['idMeal']}",
                    meal_types=meal_types
                )

                recipes.append(recipe)

        return recipes

    def fetch_edamam_recipes(self, ingredients: List[str], dietary_filters: List[str] = None) -> List[Recipe]:
        """Fetch recipes from Edamam Recipe Search API (requires free API key).

        Available filtering options from Edamam API documentation:

        Health Labels: Alcohol-Free, Dairy-Free, Egg-Free, Gluten-Free, Keto-Friendly,
          Vegan, Vegetarian, Wheat-Free, Peanut-Free, Tree-Nut-Free, Soy-Free,
          Fish-Free, Shellfish-Free, Pork-Free, Red-Meat-Free, Crustacean-Free

        Diet Labels: Balanced, High-Fiber, High-Protein, Low-Carb, Low-Fat, Low-Sodium

        Cuisine Types: American, Asian, British, Chinese, French, Greek, Indian,
          Italian, Japanese, Mediterranean, Mexican, Middle Eastern

        Dish Types: Bread, Desserts, Main Course, Pasta, Pizza, Salad, Sandwiches,
          Soup, Starter

        Meal Types: Breakfast, Brunch, Lunch/Dinner, Snack, Teatime
        """
        api_config = self.api_configs.get('edamam', {})
        app_id = api_config.get('app_id')
        app_key = api_config.get('app_key')

        if not app_id or not app_key:
            self.logger.error("Edamam API credentials not configured")
            return []

        self.logger.debug(f"Using Edamam credentials: ID={app_id[:4]}..., Key={app_key[:4]}...")

        recipes = []
        api_name = "edamam"

        # Build query from ingredients
        query = " ".join(ingredients[:3])  # Combine first 3 ingredients

        params = {
            'type': 'public',
            'q': query,
            'app_id': app_id,
            'app_key': app_key,
            'to': 20  # Limit results
        }

        # Add health/diet filters - but don't be too restrictive
        if dietary_filters:
            for filter_type in dietary_filters:
                if filter_type in ['high-protein']:
                    params['health'] = filter_type
                    break  # Only use one health filter to avoid being too restrictive
                elif filter_type in ['keto', 'paleo', 'vegetarian', 'vegan']:
                    params['diet'] = filter_type
                    break  # Only use one diet filter

        self.logger.debug(f"Edamam query: '{query}' with params: {params}")

        self._rate_limit_wait(api_name)

        url = "https://api.edamam.com/api/recipes/v2"
        full_url = url + "?" + "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
        self.logger.debug(f"Edamam URL: {full_url}")
        data = self._make_request(full_url)

        if not data or 'hits' not in data:
            return recipes

        for hit in data['hits'][:10]:  # Limit to 10 recipes
            recipe_data = hit['recipe']

            # Parse nutrition
            nutrition = self._normalize_nutrition(recipe_data.get('totalNutrients', {}),
                                                recipe_data.get('yield', 1))

            # Determine meal types from labels
            meal_types = []
            labels = recipe_data.get('mealType', [])
            for label in labels:
                if label.lower() in ['breakfast', 'lunch', 'dinner', 'snack']:
                    meal_types.append(label.lower())
            if not meal_types:
                meal_types = ['lunch', 'dinner']  # Default

            recipe = Recipe(
                id=f"edamam_{recipe_data['uri'].split('#')[-1]}",
                name=recipe_data['label'],
                ingredients=recipe_data.get('ingredientLines', []),
                instructions=["See source URL for detailed instructions"],
                prep_time=int(recipe_data.get('totalTime', 30)),
                cook_time=0,
                total_time=int(recipe_data.get('totalTime', 30)),
                servings=int(recipe_data.get('yield', 4)),
                nutrition=nutrition,
                tags=(recipe_data.get('healthLabels', []) +
                      recipe_data.get('dietLabels', []) +
                      recipe_data.get('cuisineType', []) +
                      recipe_data.get('dishType', []))[:10],  # Multiple tag sources
                source_api="edamam",
                source_url=recipe_data.get('url'),
                meal_types=meal_types
            )

            recipes.append(recipe)

        return recipes

    def fetch_spoonacular_recipes(self, ingredients: List[str], dietary_filters: List[str] = None) -> List[Recipe]:
        """Fetch recipes from Spoonacular API (requires free API key)."""
        api_config = self.api_configs.get('spoonacular', {})
        api_key = api_config.get('api_key')

        if not api_key:
            self.logger.warning("Spoonacular API key not configured")
            return []

        recipes = []
        api_name = "spoonacular"

        params = {
            'apiKey': api_key,
            'includeIngredients': ",".join(ingredients[:3]),
            'number': 10,
            'addRecipeNutrition': 'true',
            'addRecipeInstructions': 'true'
        }

        # Add dietary filters
        if dietary_filters:
            for diet_filter in dietary_filters:
                if diet_filter in ['ketogenic', 'vegetarian', 'vegan', 'gluten free', 'dairy free']:
                    params['diet'] = diet_filter
                elif diet_filter == 'high-protein':
                    params['minProtein'] = 20
                elif diet_filter == 'low-carb':
                    params['maxCarbs'] = 50

        self._rate_limit_wait(api_name)

        url = "https://api.spoonacular.com/recipes/complexSearch"
        data = self._make_request(url + "?" + "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items()))

        if not data or 'results' not in data:
            return recipes

        for recipe_data in data['results']:
            # Parse nutrition
            nutrition_data = recipe_data.get('nutrition', {})
            nutrients_list = nutrition_data.get('nutrients', [])

            # Convert Spoonacular nutrients list to dict format
            nutrients_dict = {}
            if isinstance(nutrients_list, list):
                for nutrient in nutrients_list:
                    name = nutrient.get('name', '').lower()
                    amount = nutrient.get('amount', 0)
                    if 'calorie' in name:
                        nutrients_dict['calories'] = amount
                    elif 'protein' in name:
                        nutrients_dict['protein'] = amount
                    elif 'carbohydrate' in name or 'carb' in name:
                        nutrients_dict['carbs'] = amount
                    elif 'fat' in name and 'saturated' not in name:
                        nutrients_dict['fat'] = amount

            nutrition = self._normalize_nutrition(nutrients_dict, 1)

            # Parse instructions
            instructions = []
            if 'analyzedInstructions' in recipe_data:
                for instruction_group in recipe_data['analyzedInstructions']:
                    steps = instruction_group.get('steps', [])
                    for step in steps:
                        instructions.append(step.get('step', ''))

            # Determine meal types
            dish_types = recipe_data.get('dishTypes', [])
            meal_types = []
            for dish_type in dish_types:
                if 'breakfast' in dish_type.lower():
                    meal_types.append('breakfast')
                elif any(term in dish_type.lower() for term in ['lunch', 'main', 'dinner']):
                    meal_types.extend(['lunch', 'dinner'])
                elif 'snack' in dish_type.lower():
                    meal_types.append('snack')
            if not meal_types:
                meal_types = ['lunch', 'dinner']

            recipe = Recipe(
                id=f"spoonacular_{recipe_data['id']}",
                name=recipe_data['title'],
                ingredients=recipe_data.get('extendedIngredients', []),  # This would need parsing
                instructions=instructions,
                prep_time=recipe_data.get('preparationMinutes', 15),
                cook_time=recipe_data.get('cookingMinutes', 15),
                total_time=recipe_data.get('readyInMinutes', 30),
                servings=recipe_data.get('servings', 4),
                nutrition=nutrition,
                tags=recipe_data.get('dishTypes', [])[:5],
                source_api="spoonacular",
                source_url=recipe_data.get('sourceUrl'),
                meal_types=meal_types
            )

            recipes.append(recipe)

        return recipes

    def _estimate_nutrition_from_ingredients(self, ingredients: List[str]) -> Dict[str, float]:
        """Estimate basic nutrition when API doesn't provide it."""
        # Very basic estimation based on ingredient count and common foods
        base_calories = 50 * len(ingredients)  # Rough estimate

        protein_keywords = ['chicken', 'beef', 'fish', 'egg', 'protein', 'tofu', 'beans']
        carb_keywords = ['rice', 'pasta', 'bread', 'potato', 'oats']

        protein_boost = sum(1 for ingredient in ingredients
                          if any(keyword in ingredient.lower() for keyword in protein_keywords))
        carb_boost = sum(1 for ingredient in ingredients
                        if any(keyword in ingredient.lower() for keyword in carb_keywords))

        return {
            'calories': base_calories + (protein_boost * 100) + (carb_boost * 80),
            'protein': max(5, protein_boost * 25),
            'carbs': max(10, carb_boost * 30),
            'fat': max(5, len(ingredients) * 3)
        }

    def fetch_recipes_for_ingredients(self, ingredients: List[str],
                                    dietary_filters: List[str] = None,
                                    max_recipes: int = 30) -> List[Recipe]:
        """Fetch recipes from all available APIs based on ingredients."""
        all_recipes = []

        # Try each API in order of preference
        apis_to_try = [
            ('themealdb', self.fetch_themealdb_recipes),
            ('edamam', self.fetch_edamam_recipes),
            ('spoonacular', self.fetch_spoonacular_recipes)
        ]

        for api_name, fetch_func in apis_to_try:
            # Check if this API is enabled in config
            api_config = self.api_configs.get(api_name, {})
            if not api_config.get('enabled', False):
                self.logger.debug(f"Skipping {api_name} API: disabled in config")
                continue

            # Circuit breaker: Skip APIs that have failed too many times
            if self.api_failure_counts.get(api_name, 0) >= self.max_failures_per_api:
                self.logger.debug(f"Skipping {api_name} API: too many recent failures")
                continue

            try:
                recipes = fetch_func(ingredients, dietary_filters or [])
                all_recipes.extend(recipes)
                # Use progress tracker for user-visible messages
                from progress_utils import get_progress_tracker
                progress = get_progress_tracker()
                progress.log_message(f"({api_name.title()}) Fetched {len(recipes)} recipes")

                # Reset failure count on success
                self.api_failure_counts[api_name] = 0

                if len(all_recipes) >= max_recipes:
                    break

            except Exception as e:
                self.logger.error(f"Error fetching from {api_name}: {e}")
                # Increment failure count
                self.api_failure_counts[api_name] = self.api_failure_counts.get(api_name, 0) + 1
                continue

        # Remove duplicates based on similar names
        unique_recipes = []
        seen_names = set()

        for recipe in all_recipes:
            normalized_name = recipe.name.lower().strip()
            if normalized_name not in seen_names:
                unique_recipes.append(recipe)
                seen_names.add(normalized_name)

        return unique_recipes[:max_recipes]

    def _extract_main_ingredient(self, name: str) -> str:
        """Extract the main ingredient from a food name - use key ingredient for API search."""
        # Clean up the name
        clean_name = name.lower().split('(')[0].strip()

        # Extract the key searchable ingredient
        key_ingredients = {
            'eggs': ['eggs', 'boiled eggs', 'scrambled eggs'],
            'toast': ['toast', 'bread'],
            'oats': ['oats', 'steel-cut oats', 'quick oats'],
            'chicken': ['chicken', 'grilled chicken'],
            'beef': ['beef', 'ground beef'],
            'rice': ['rice', 'brown rice'],
            'yogurt': ['yogurt', 'greek yogurt'],
            'cheese': ['cheese', 'cottage cheese'],
            'sweet potato': ['sweet potato'],
            'avocado': ['avocado'],
            'spinach': ['spinach'],
            'broccoli': ['broccoli']
        }

        # Find matching key ingredient
        for key, variants in key_ingredients.items():
            if any(variant in clean_name for variant in variants):
                return key

        # Fallback: use first meaningful word
        words = clean_name.split()
        skip_words = ['whole', 'grain', 'steel-cut', 'boiled', 'grilled', 'lean']
        for word in words:
            if word not in skip_words:
                return word

        return clean_name

    def find_recipes_for_meal_components(self, meal_components: List[Dict[str, Any]],
                                       meal_type: str,
                                       dietary_filters: List[str] = None) -> List[Recipe]:
        """Find recipes using intelligent fallback logic."""
        # Extract and categorize ingredient names
        ingredient_names = []
        fruits = []

        for component in meal_components:
            main_ingredient = self._extract_main_ingredient(component['name'])

            if main_ingredient:
                # Check if it's a fruit (side ingredient)
                if any(fruit in main_ingredient for fruit in ['apple', 'banana', 'orange', 'berry', 'berries', 'grape', 'pear', 'mango', 'pineapple', 'strawberries', 'blueberries']):
                    fruits.append(main_ingredient)
                else:
                    ingredient_names.append(main_ingredient)

        # Fallback strategy
        search_attempts = [
            ingredient_names + fruits,  # Try all ingredients first
            ingredient_names,           # Remove fruits (sides)
        ]

        # If still have multiple main ingredients, try removing one by one
        if len(ingredient_names) > 1:
            for i in range(len(ingredient_names)):
                reduced_list = ingredient_names[:i] + ingredient_names[i+1:]
                if reduced_list:  # Don't add empty lists
                    search_attempts.append(reduced_list)

        # Try each search attempt
        for attempt_num, ingredients in enumerate(search_attempts):
            if not ingredients:
                continue

            self.logger.debug(f"Search attempt {attempt_num + 1}: {ingredients}")
            recipes = self.fetch_recipes_for_ingredients(ingredients, dietary_filters)

            if recipes:
                from progress_utils import get_progress_tracker
                progress = get_progress_tracker()
                progress.log_message(f"Found {len(recipes)} recipes with: {', '.join(ingredients)}")
                self.logger.debug(f"Raw recipes found: {len(recipes)}")

                # Debug: Show what meal types we got
                for i, recipe in enumerate(recipes[:3]):
                    self.logger.debug(f"Recipe {i+1} '{recipe.name}' has meal_types: {recipe.meal_types}")

                # Filter recipes appropriate for meal type
                self.logger.debug(f"Filtering for meal_type: '{meal_type}'")
                filtered_recipes = [r for r in recipes if meal_type in r.meal_types]
                progress.log_message(f"Returning {len(filtered_recipes)} recipes for {meal_type}")

                if filtered_recipes:
                    return filtered_recipes
                else:
                    # Return unfiltered if no meal-type specific recipes
                    progress.log_message(f"No meal-type specific recipes, returning first 3 unfiltered", "warning")
                    return recipes[:3]  # Limit to 3 best matches

        self.logger.warning(f"No recipes found after all fallback attempts")
        return []

    def cache_recipes(self, recipes: List[Recipe], cache_key: str):
        """Cache recipes for later use."""
        self.cache[cache_key] = {
            'recipes': recipes,
            'timestamp': time.time()
        }

    def get_cached_recipes(self, cache_key: str, max_age: int = 3600) -> Optional[List[Recipe]]:
        """Get cached recipes if they're still fresh."""
        if cache_key not in self.cache:
            return None

        cached_data = self.cache[cache_key]
        age = time.time() - cached_data['timestamp']

        if age > max_age:
            del self.cache[cache_key]
            return None

        return cached_data['recipes']