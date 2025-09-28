#!/usr/bin/env python3
"""
PFA Planning System - Main CLI Interface
Generates comprehensive Physical Fitness Assessment training plans.
"""

import sys
import argparse
import yaml
import signal
import os
from pathlib import Path
from datetime import datetime

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Fallback: manually load .env file
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

# Add src directory to path for imports
sys.path.append(str(Path(__file__).parent / 'src'))

from config_loader import load_config, create_default_config
from fitness_calculator import FitnessProgressionCalculator
from nutrition_planner import NutritionPlanner
from supplement_scheduler import SupplementScheduler
from progression_engine import WorkoutProgressionEngine
from calendar_generator import CalendarGenerator
from progress_utils import get_progress_tracker, reset_progress_tracker

# Import meal generator (now unified with recipe support)
try:
    from meal_generator import MealGenerator
    from logging_config import setup_logger, set_global_logging_level, get_logging_level_from_env
    RECIPE_SUPPORT_AVAILABLE = True
except ImportError as e:
    print(f"Meal generator not available: {e}")
    RECIPE_SUPPORT_AVAILABLE = False


def create_default_template(output_path: str):
    """Create a default YAML configuration template."""
    default_config = create_default_config()

    with open(output_path, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False, indent=2)

    print(f"Default configuration template created: {output_path}")
    print("Edit this file with your personal parameters and run:")
    print(f"python generate_pfa_plan.py {output_path}")


def validate_configuration(config):
    """Validate configuration parameters."""
    issues = []

    # Validate timeline
    if config.timeline.weeks < 4:
        issues.append("Timeline should be at least 4 weeks for meaningful progression")

    # Validate fitness goals
    try:
        calculator = FitnessProgressionCalculator(
            config.fitness.__dict__,
            config.timeline.weeks,
            config.timeline.buffer_weeks
        )
        validation = calculator.validate_goals()

        if not validation.get('run_meets_standard', True):
            issues.append("Run time goal does not meet PFA standards")
        if not validation.get('pushups_meets_standard', True):
            issues.append("Pushups goal does not meet PFA standards")
        if not validation.get('situps_meets_standard', True):
            issues.append("Situps goal does not meet PFA standards")

    except Exception as e:
        issues.append(f"Fitness progression validation error: {str(e)}")

    # Validate nutrition macros
    macro_sum = sum(config.nutrition.macros.values())
    if macro_sum != 100:
        issues.append(f"Macro percentages sum to {macro_sum}%, should be 100%")

    if config.nutrition.calorie_goals['target'] < 1200:
        issues.append("Daily calorie target seems too low (minimum 1200 recommended)")

    return issues


def generate_plan(config_path: str):
    """Generate complete PFA plan from configuration."""
    # Set up main system logger
    if RECIPE_SUPPORT_AVAILABLE:
        logger = setup_logger('pfa_system')
        logger.info(f"Loading configuration from: {config_path}")
    else:
        logger = None
        print(f"Loading configuration from: {config_path}")

    try:
        config = load_config(config_path)
    except Exception as e:
        if logger:
            logger.error(f"Error loading configuration: {str(e)}")
        else:
            print(f"Error loading configuration: {str(e)}")
        return False

    if logger:
        logger.info("Validating configuration...")
    else:
        print("Validating configuration...")
    issues = validate_configuration(config)

    if issues:
        print("\nConfiguration Issues:")
        for issue in issues:
            print(f"  - {issue}")

        response = input("\nProceed anyway? (y/N): ")
        if response.lower() != 'y':
            return False

    if logger:
        logger.info("Generating PFA plan...")
    else:
        print("\nGenerating PFA plan...")

    # Initialize components
    fitness_calculator = FitnessProgressionCalculator(
        config.fitness.__dict__,
        config.timeline.weeks,
        config.timeline.buffer_weeks
    )

    # Load meal database for advanced meal planning
    meal_database_path = Path(__file__).parent / 'configs' / 'meal_database.yml'
    if meal_database_path.exists():
        with open(meal_database_path, 'r') as f:
            meal_database_config = yaml.safe_load(f)

        # Add meal database to nutrition config
        nutrition_config = config.nutrition.__dict__.copy()
        nutrition_config['meal_database'] = meal_database_config
        nutrition_config['meal_generation'] = meal_database_config.get('meal_generation', {})
    else:
        nutrition_config = config.nutrition.__dict__

    # Load recipe configuration if available
    recipe_config = None
    recipe_config_path = getattr(config, 'recipe_config', None)
    if recipe_config_path:
        recipe_path = Path(recipe_config_path)
        if not recipe_path.is_absolute():
            recipe_path = Path(__file__).parent / recipe_path

        if logger:
            logger.debug(f"Looking for recipe config at: {recipe_path}")
        else:
            print(f"  - Looking for recipe config at: {recipe_path}")

        if recipe_path.exists():
            with open(recipe_path, 'r') as f:
                recipe_config = yaml.safe_load(f)
            # Substitute environment variables
            from src.config_loader import substitute_env_vars
            recipe_config = substitute_env_vars(recipe_config)

            if logger:
                logger.info(f"Recipe integration enabled (using {recipe_path})")
            else:
                print(f"  - Recipe integration enabled (using {recipe_path})")
        else:
            print(f"  - Recipe config not found at {recipe_path}, using component-based meals only")

    # Use meal generator with recipe support if available and configured
    if meal_database_path.exists() and recipe_config and RECIPE_SUPPORT_AVAILABLE:
        try:
            if logger:
                logger.info("Using meal generator with recipe integration")
            else:
                print(f"  - Using meal generator with recipe integration")
            # Merge meal generation rules with nutrition config (for tag filtering)
            meal_generation_rules = meal_database_config.get('meal_generation', {})
            if 'recipe_tags' in nutrition_config:
                meal_generation_rules['recipe_tags'] = nutrition_config['recipe_tags']

            meal_generator = MealGenerator(
                meal_database_config,
                meal_generation_rules,
                recipe_config.get('recipe_integration', {})
            )
            nutrition_planner = NutritionPlanner(nutrition_config, meal_generator)
        except Exception as e:
            print(f"  - Recipe meal generator failed, falling back to component meals: {e}")
            nutrition_planner = NutritionPlanner(nutrition_config)
    else:
        if not recipe_config:
            print(f"  - No recipe config specified, using component meals only")
        elif not RECIPE_SUPPORT_AVAILABLE:
            print(f"  - Recipe support not available, using component meals only")
        elif not meal_database_path.exists():
            print(f"  - No meal database found, using component meals only")
        nutrition_planner = NutritionPlanner(nutrition_config)
    supplement_scheduler = SupplementScheduler(config.supplements.__dict__)
    progression_engine = WorkoutProgressionEngine(
        config.training.__dict__,
        config.progression.__dict__,
        fitness_calculator
    )
    calendar_config = {
        'separate_calendars': config.calendar.separate_calendars,
        'output_dir': config.calendar.output_dir,
        'export_formats': config.calendar.export_formats
    }
    calendar_generator = CalendarGenerator(
        calendar_config,
        config.calendar.timezone
    )

    # Generate all components
    if logger:
        logger.info("Creating workout programs...")
    else:
        print("  - Creating workout programs...")
    workout_program = progression_engine.generate_full_program(config.timeline.weeks)

    if logger:
        logger.info("Planning meals...")
    else:
        print("  - Planning meals...")

    # Initialize progress tracker
    progress = get_progress_tracker()
    progress.start(config.timeline.weeks)

    if recipe_config:
        progress.log_message("Fetching recipes from APIs...")

    # Generate meal plans for each week
    meal_plans = {}
    try:
        for week in range(config.timeline.weeks):
            progress.update_status(f"Starting week {week + 1} of {config.timeline.weeks}...")
            weekly_meals = nutrition_planner.generate_advanced_meal_plan(week + 1)
            meal_plans[f'week_{week + 1}'] = weekly_meals
    except ValueError as e:
        progress.finish()
        if "Meal planning cancelled" in str(e):
            print(f"\n❌ Meal planning cancelled. Please fix the configuration conflicts and try again.")
            return False
        else:
            raise

    progress.update_status("Scheduling supplements...")
    # Create workout schedule for supplement timing
    workout_schedule = {}
    workout_times = getattr(config.training, 'workout_times', {})

    for day in config.training.schedule['workout_days']:
        time_str = workout_times.get('workout_days', '07:00')
        workout_schedule[day] = datetime.strptime(time_str, '%H:%M').time()
    for day in config.training.schedule['strength_days']:
        time_str = workout_times.get('strength_days', '18:00')
        workout_schedule[day] = datetime.strptime(time_str, '%H:%M').time()

    supplement_schedule = supplement_scheduler.generate_weekly_schedule(workout_schedule)
    progress.advance(1)

    progress.update_status("Generating calendars...")
    all_data = {
        'workouts': workout_program['weekly_workouts'],
        'meals': meal_plans,
        'supplements': supplement_schedule
    }

    calendar_files = calendar_generator.export_calendar_data(
        all_data,
        config.timeline.start_date,
        config.timeline.weeks
    )

    # Everything goes into the calendar files - no separate meal plan files needed

    # Print summary
    print(f"\n✅ PFA Plan Generated Successfully!")
    print(f"\nTimeline: {config.timeline.weeks} weeks starting {config.timeline.start_date}")
    print(f"Fitness Goals:")
    print(f"  Run time: {config.fitness.baseline['run_time']} → {config.fitness.goals['run_time']}")
    print(f"  Push-ups: {config.fitness.baseline['pushups']} → {config.fitness.goals['pushups']}")
    print(f"  Sit-ups: {config.fitness.baseline['situps']} → {config.fitness.goals['situps']}")

    print(f"\nNutrition:")
    print(f"  Daily calories: {config.nutrition.calorie_goals['target']}")
    macros = nutrition_planner.calculate_macro_grams()
    print(f"  Macros: {macros['protein']}g protein, {macros['carbs']}g carbs, {macros['fat']}g fat")

    print(f"\nCalendar Files Generated:")
    for calendar_type, file_path in calendar_files.items():
        print(f"  📅 {calendar_type.title()}: {file_path}")

    # Finish progress tracking
    progress.finish()

    print(f"\n🎯 Next Steps:")
    print(f"  1. Import calendar files into your calendar app")
    print(f"  2. Follow meal plans from calendar events")
    print(f"  3. Set up supplement schedule")
    print(f"  4. Track progress weekly")

    return True


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PFA Planning System - Generate comprehensive fitness training plans",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create default template
  python generate_pfa_plan.py --template my_config.yml

  # Generate plan from config
  python generate_pfa_plan.py my_config.yml

  # Use built-in template
  python generate_pfa_plan.py configs/templates/intermediate.yml
        """
    )

    parser.add_argument(
        "config_file",
        nargs="?",
        help="YAML configuration file path"
    )

    parser.add_argument(
        "--template",
        help="Create a default configuration template at specified path"
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate configuration without generating plan"
    )

    args = parser.parse_args()

    if args.template:
        create_default_template(args.template)
        return

    if not args.config_file:
        parser.print_help()
        print("\nError: Configuration file required")
        return

    config_path = Path(args.config_file)
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        return

    if args.validate_only:
        try:
            config = load_config(str(config_path))
            issues = validate_configuration(config)

            if issues:
                print("Configuration Issues:")
                for issue in issues:
                    print(f"  - {issue}")
            else:
                print("✅ Configuration is valid")
        except Exception as e:
            print(f"❌ Configuration error: {str(e)}")
        return

    success = generate_plan(str(config_path))
    sys.exit(0 if success else 1)


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    print("\n\n🛑 Operation cancelled by user")
    import os
    os._exit(1)  # Force immediate exit without cleanup

if __name__ == "__main__":
    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Set up logging based on environment variable
    if RECIPE_SUPPORT_AVAILABLE:
        log_level = get_logging_level_from_env()
        set_global_logging_level(log_level)
        if log_level == 'DEBUG':
            print(f"🔧 Logging level set to: {log_level}")

    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)