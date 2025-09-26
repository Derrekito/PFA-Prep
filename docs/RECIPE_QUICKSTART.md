# 🍳 Quick Recipe Integration Guide

Your PFA meal planning system now supports real recipes from multiple APIs! Here's how to add recipe integration to your existing configuration.

## 🚀 Quick Start (2 minutes setup)

### Step 1: Add recipe config to your existing file
Add this single line to your existing config file (e.g., `configs/personal/female_38.yml`):

```yaml
# Add this line anywhere in your config file
recipe_config: "./configs/recipe_config.yml"
```

### Step 2: Test with recipes enabled
```bash
./run_pfa_plan.sh configs/personal/female_38.yml
```

That's it! The system will now include actual recipes alongside your component-based meals.

## 🎯 What You Get

### Before (Component meals only):
```
🥗 Breakfast - Option 1
Components: Greek yogurt (1 cup) + Blueberries (1/2 cup)
Nutrition: Calories: 185 | Protein: 20g | Carbs: 15g | Fat: 0g
```

### After (Mix of components + real recipes):
```
🍳 Breakfast - Protein Berry Pancakes (Recipe)
Ingredients: Greek yogurt (1 cup), Oats (1/2 cup), Eggs (1), Blueberries (1/2 cup), Vanilla (1 tsp)
Instructions: Blend oats into flour. Mix with yogurt and eggs. Cook pancakes in non-stick pan... (full recipe)
Time: Prep: 5min | Cook: 10min | Serves: 2
Nutrition: Calories: 320 | Protein: 28g | Carbs: 35g | Fat: 8g
Recipe URL: https://www.themealdb.com/meal/52785
```

## 📝 Current Configuration

The recipe system is already configured with:
- **TheMealDB**: Free API (no setup required) - 1000+ recipes
- **High-protein focus**: Perfect for fitness goals
- **30% recipe ratio**: 3 out of 10 meal options will be recipes
- **Smart ingredient matching**: Uses your existing meal database

## 🔧 Customize Your Recipes

Edit `configs/recipe_config.yml` to:
- Change recipe percentage (currently 30%)
- Add dietary filters (vegetarian, low-carb, etc.)
- Add more API keys for additional recipes
- Adjust difficulty and cooking time preferences

## 📊 API Status

- ✅ **TheMealDB**: Ready (free, no API key needed)
- ⏳ **Edamam**: Optional (free tier available at developer.edamam.com)
- ⏳ **Spoonacular**: Optional (free tier available at spoonacular.com/food-api)

## 🏃‍♂️ Test Your Enhanced System

```bash
# Test with your existing config (now enhanced with recipes)
./run_pfa_plan.sh configs/personal/female_38.yml

# Or try the full example with all features
./run_pfa_plan.sh configs/templates/enhanced_with_recipes.yml
```

## 🛠 Troubleshooting

**"No recipes found"**: Working normally - TheMealDB provides recipes for common ingredients
**"API errors"**: System falls back to your existing component meals
**"Too many recipes"**: Lower the `recipe_ratio` in `configs/recipe_config.yml`

Your existing meal plans continue to work exactly as before - recipes are just an enhancement!