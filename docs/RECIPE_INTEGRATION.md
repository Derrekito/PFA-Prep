# Recipe Integration Guide

The PFA Planning System now includes powerful recipe integration that pulls real recipes from multiple APIs based on your meal database ingredients. This enhancement provides actual cooking instructions, complete ingredient lists, and nutritional information alongside your existing component-based meal planning.

## Overview

The enhanced system combines:
- **Component-based meals**: Your existing structured meal database with precise portions and macros
- **Real recipes**: Actual cooking instructions and ingredient lists from popular recipe APIs
- **Smart mixing**: Configurable ratio between recipes and components (default: 30% recipes, 70% components)

## Features

### 🍳 Multiple Recipe Sources
- **TheMealDB**: Completely free, no API key required (1000+ recipes)
- **Edamam**: Free tier available with nutrition data (2.3M+ recipes)
- **Spoonacular**: Free tier with detailed nutrition and meal planning features

### 🎯 Intelligent Recipe Matching
- Matches recipes to your meal database ingredients
- Filters recipes based on meal type (breakfast, lunch, dinner, snack)
- Applies dietary filters (high-protein, low-carb, vegetarian, etc.)
- Respects your macro and calorie requirements

### 📅 Enhanced Calendar Events
Recipe-based calendar events include:
- Complete ingredient lists with portions
- Step-by-step cooking instructions
- Prep time, cook time, and difficulty level
- Serving size and source URL
- Detailed nutritional breakdown

## Quick Start

### 1. Basic Setup (Free - No API Keys Required)

The system works immediately with TheMealDB (completely free):

```yaml
# In your main config file
recipe_config: "./configs/recipe_config.yml"
```

### 2. Enhanced Setup (Optional API Keys)

For access to more recipes and detailed nutrition data:

1. **Edamam (Free Tier)**:
   - Sign up at https://developer.edamam.com/
   - Get your App ID and App Key
   - Update `configs/recipe_config.yml`

2. **Spoonacular (Free Tier)**:
   - Sign up at https://spoonacular.com/food-api
   - Get your API key
   - Update `configs/recipe_config.yml`

## Configuration

### Main Configuration File

Add this line to your main PFA configuration:

```yaml
# Reference to recipe configuration
recipe_config: "./configs/recipe_config.yml"
```

### Recipe Configuration File

The `configs/recipe_config.yml` file controls all recipe integration:

```yaml
recipe_integration:
  enable_recipes: true
  recipe_ratio: 0.3  # 30% recipes, 70% components
  max_recipes_per_meal: 2

  recipe_apis:
    themealdb:
      enabled: true  # Free, no setup required

    edamam:
      enabled: true  # Set to false if no API key
      app_id: "your_app_id"
      app_key: "your_app_key"

    spoonacular:
      enabled: false
      api_key: "your_api_key"

  dietary_filters:
    - "high-protein"  # Focus on fitness-appropriate recipes
    # - "low-carb"    # Uncomment as needed
    # - "vegetarian"  # Uncomment as needed

  preferences:
    difficulty_preference: ["easy", "medium"]
    max_cook_time: 45
    min_rating: 3.5
```

## API Setup Instructions

### TheMealDB (Free - No Setup Required)
- Already enabled by default
- No API key needed
- 1000+ recipes with ingredients and instructions
- Perfect for getting started

### Edamam Recipe API (Free Tier Available)
1. Go to https://developer.edamam.com/
2. Click "Get Started For Free"
3. Create account and verify email
4. Go to Dashboard → Applications
5. Create new application (select "Recipe Search API")
6. Copy your Application ID and Application Key
7. Update your `recipe_config.yml`:
   ```yaml
   edamam:
     enabled: true
     app_id: "your_app_id_here"
     app_key: "your_app_key_here"
   ```

### Spoonacular API (Free Tier Available)
1. Go to https://spoonacular.com/food-api
2. Click "Get API Key"
3. Create account and verify email
4. Go to Console → My API Keys
5. Copy your API key
6. Update your `recipe_config.yml`:
   ```yaml
   spoonacular:
     enabled: true
     api_key: "your_api_key_here"
   ```

## Usage Examples

### Example 1: Basic Recipe Integration

```bash
# Use the enhanced template with recipes enabled
./run_pfa_plan.sh configs/templates/enhanced_with_recipes.yml
```

This generates meal plans with:
- 70% component-based meals (your existing database)
- 30% real recipes from TheMealDB
- All properly scheduled in your calendar

### Example 2: High-Protein Recipe Focus

Update your `recipe_config.yml`:
```yaml
dietary_filters:
  - "high-protein"
  - "balanced"

preferences:
  difficulty_preference: ["easy"]
  max_cook_time: 30
```

### Example 3: Vegetarian Recipe Integration

```yaml
dietary_filters:
  - "vegetarian"
  - "high-protein"

component_priority:
  proteins: 3    # Focus on plant proteins
  vegetables: 3  # High vegetable priority
  carbs: 2       # Include healthy carbs
```

## Calendar Integration

Recipe-enhanced calendar events contain:

### Component-Based Meal Event
```
🥗 Breakfast - Option 1
Components: Greek yogurt (1 cup) + Blueberries (1/2 cup) + Steel-cut oats (1/2 cup dry)
Nutrition: Calories: 385 | Protein: 30g | Carbs: 54g | Fat: 3g
```

### Recipe-Based Meal Event
```
🍳 Dinner - Grilled Chicken with Vegetables
Ingredients: Chicken breast (4oz), Bell peppers (1 cup), Olive oil (1 tbsp), Garlic (2 cloves), Broccoli (1 cup), Brown rice (1/2 cup)
Instructions: Season chicken with salt and pepper. Heat oil in pan... (3 more steps)
Time: Prep: 15min | Cook: 20min
Serves: 2
Nutrition: Calories: 450 | Protein: 38g | Carbs: 35g | Fat: 12g
Recipe URL: https://www.themealdb.com/meal/52785
```

## Troubleshooting

### Common Issues

**"No recipes found"**
- Check your internet connection
- Verify API keys are correct
- Try reducing dietary filters
- Increase `max_cook_time` setting

**"API rate limit exceeded"**
- The system has built-in rate limiting
- Free tiers have daily limits (usually 5000+ requests)
- Consider using multiple APIs for more quota

**"Recipes don't match my macros"**
- Adjust `target_calories` in meal rules
- The system auto-adjusts serving sizes
- Set appropriate `min_protein` levels

### Debugging

Enable verbose logging by adding to your main script:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Performance Tips

1. **Cache Efficiency**: Recipes are cached for 1 hour by default
2. **API Selection**: TheMealDB is fastest (no auth), Edamam has best nutrition data
3. **Ingredient Matching**: More specific ingredients get better recipe matches

## Advanced Features

### Custom Ingredient Matching

The system intelligently maps your meal database components to recipe searches:
- "Grilled chicken breast" → searches for "chicken" recipes
- "Steel-cut oats" → searches for "oats" recipes
- "Mixed vegetables" → searches for "vegetables" recipes

### Nutrition Validation

Recipes are automatically validated against your meal requirements:
- Minimum protein requirements per meal type
- Calorie range compliance
- Macro distribution preferences

### Portion Adjustment

The system automatically adjusts recipe portions to match your calorie targets:
- Scales serving sizes up/down as needed
- Maintains recipe integrity (won't scale beyond 0.3x to 3.0x)
- Updates nutrition information proportionally

## File Structure

```
PFA_plan/
├── configs/
│   ├── recipe_config.yml              # Main recipe configuration
│   ├── recipe_config_template.yml     # Template with all options
│   └── templates/
│       └── enhanced_with_recipes.yml  # Example main config with recipes
├── src/
│   ├── recipe_fetcher.py              # Recipe API integration
│   ├── enhanced_meal_generator.py     # Enhanced meal generator
│   └── calendar_generator.py          # Updated for recipe events
└── docs/
    └── RECIPE_INTEGRATION.md          # This file
```

## Next Steps

1. **Start Simple**: Use the free TheMealDB integration first
2. **Add API Keys**: Sign up for Edamam/Spoonacular for more variety
3. **Customize**: Adjust dietary filters and preferences
4. **Monitor**: Check your calendar for the mix of components vs recipes
5. **Iterate**: Fine-tune the `recipe_ratio` based on your preferences

The recipe integration transforms your meal planning from basic components to a comprehensive cooking guide while maintaining the precision and fitness focus of your original system.