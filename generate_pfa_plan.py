#!/usr/bin/env python3
"""
PFA Planning System - Main CLI Interface
Generates comprehensive Physical Fitness Assessment training plans.
"""

import sys
import argparse
import yaml
from pathlib import Path
from datetime import datetime

# Add src directory to path for imports
sys.path.append(str(Path(__file__).parent / 'src'))

from config_loader import load_config, create_default_config
from fitness_calculator import FitnessProgressionCalculator
from nutrition_planner import NutritionPlanner
from supplement_scheduler import SupplementScheduler
from progression_engine import WorkoutProgressionEngine
from calendar_generator import CalendarGenerator


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
    print(f"Loading configuration from: {config_path}")

    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"Error loading configuration: {str(e)}")
        return False

    print("Validating configuration...")
    issues = validate_configuration(config)

    if issues:
        print("\nConfiguration Issues:")
        for issue in issues:
            print(f"  - {issue}")

        response = input("\nProceed anyway? (y/N): ")
        if response.lower() != 'y':
            return False

    print("\nGenerating PFA plan...")

    # Initialize components
    fitness_calculator = FitnessProgressionCalculator(
        config.fitness.__dict__,
        config.timeline.weeks,
        config.timeline.buffer_weeks
    )

    nutrition_planner = NutritionPlanner(config.nutrition.__dict__)
    supplement_scheduler = SupplementScheduler(config.supplements.__dict__)
    progression_engine = WorkoutProgressionEngine(
        config.training.__dict__,
        config.progression.__dict__,
        fitness_calculator
    )
    calendar_generator = CalendarGenerator(
        config.calendar.separate_calendars,
        config.calendar.timezone
    )

    # Generate all components
    print("  - Calculating fitness progressions...")
    fitness_report = fitness_calculator.generate_progression_report()

    print("  - Creating workout programs...")
    workout_program = progression_engine.generate_full_program(config.timeline.weeks)

    print("  - Planning meals...")
    # Generate meal plans for each week
    meal_plans = {}
    for week in range(config.timeline.weeks):
        weekly_meals = nutrition_planner.generate_weekly_meal_plan(week + 1)
        meal_plans[f'week_{week + 1}'] = weekly_meals

    print("  - Scheduling supplements...")
    # Create workout schedule for supplement timing
    workout_schedule = {}
    for day in config.training.schedule['workout_days']:
        workout_schedule[day] = datetime.strptime('07:00', '%H:%M').time()
    for day in config.training.schedule['strength_days']:
        workout_schedule[day] = datetime.strptime('18:00', '%H:%M').time()

    supplement_schedule = supplement_scheduler.generate_weekly_schedule(workout_schedule)

    print("  - Generating calendars...")
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

    # Save additional reports
    output_dir = Path(config.calendar.output_dir).parent
    reports_dir = output_dir / 'progress_reports'
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Save fitness progression report
    fitness_report_path = reports_dir / 'fitness_progression.yaml'
    with open(fitness_report_path, 'w') as f:
        yaml.dump(fitness_report, f, default_flow_style=False)

    # Save program validation report
    program_validation = progression_engine.validate_program_balance(config.timeline.weeks)
    validation_report_path = reports_dir / 'program_validation.yaml'
    with open(validation_report_path, 'w') as f:
        yaml.dump(program_validation, f, default_flow_style=False)

    # Save meal plans
    meal_plans_dir = output_dir / 'meal_plans'
    meal_plans_dir.mkdir(parents=True, exist_ok=True)
    meal_plans_path = meal_plans_dir / 'weekly_meal_plans.yaml'
    with open(meal_plans_path, 'w') as f:
        yaml.dump(meal_plans, f, default_flow_style=False)

    # Print summary
    print(f"\n✅ PFA Plan Generated Successfully!")
    print(f"\nTimeline: {config.timeline.weeks} weeks starting {config.timeline.start_date}")
    print(f"Fitness Goals:")
    print(f"  Run time: {config.fitness.baseline['run_time']} → {config.fitness.goals['run_time']}")
    print(f"  Push-ups: {config.fitness.baseline['pushups']} → {config.fitness.goals['pushups']}")
    print(f"  Sit-ups: {config.fitness.baseline['situps']} → {config.fitness.goals['situps']}")
    print(f"  Plank: {config.fitness.baseline['plank']} → {config.fitness.goals['plank']}")

    print(f"\nNutrition:")
    print(f"  Daily calories: {config.nutrition.calorie_goals['target']}")
    macros = nutrition_planner.calculate_macro_grams()
    print(f"  Macros: {macros['protein']}g protein, {macros['carbs']}g carbs, {macros['fat']}g fat")

    print(f"\nFiles Generated:")
    for calendar_type, file_path in calendar_files.items():
        print(f"  📅 {calendar_type.title()}: {file_path}")

    print(f"  📊 Fitness Report: {fitness_report_path}")
    print(f"  📊 Program Validation: {validation_report_path}")
    print(f"  🍽️ Meal Plans: {meal_plans_path}")

    print(f"\n🎯 Next Steps:")
    print(f"  1. Import calendar files into your calendar app")
    print(f"  2. Review meal plans and prep ingredients")
    print(f"  3. Set up supplement schedule")
    print(f"  4. Track progress weekly")

    if program_validation['recommendations']:
        print(f"\n⚠️ Program Recommendations:")
        for rec in program_validation['recommendations'][:3]:  # Show first 3
            print(f"  • {rec}")

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


if __name__ == "__main__":
    main()