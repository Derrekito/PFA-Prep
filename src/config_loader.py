#!/usr/bin/env python3
"""YAML configuration loader with validation for PFA planning system."""

import yaml
import os
import re
from datetime import datetime, date, time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def substitute_env_vars(obj):
    """Recursively substitute environment variables in strings."""
    if isinstance(obj, str):
        # Replace ${VAR_NAME} with environment variable value
        return re.sub(r'\$\{([^}]+)\}', lambda m: os.getenv(m.group(1), m.group(0)), obj)
    elif isinstance(obj, dict):
        return {k: substitute_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [substitute_env_vars(item) for item in obj]
    else:
        return obj


@dataclass
class TimelineConfig:
    start_date: date
    weeks: int
    buffer_weeks: Dict[str, int]


@dataclass
class FitnessConfig:
    baseline: Dict[str, Any]
    goals: Dict[str, Any]
    pfa_standards: Dict[str, Any]


@dataclass
class NutritionConfig:
    eating_window: Dict[str, Any]
    calorie_goals: Dict[str, int]
    macros: Dict[str, int]
    meal_timing: Dict[str, Any]
    dietary_preferences: Dict[str, List[str]]
    meal_database: Optional[Dict[str, Any]] = None
    meal_generation: Optional[Dict[str, Any]] = None


@dataclass
class SupplementConfig:
    daily_stack: List[Dict[str, Any]]
    pre_workout: Dict[str, Any]
    post_workout: Dict[str, Any]


@dataclass
class TrainingConfig:
    schedule: Dict[str, List[str]]
    workout_types: Dict[str, Any]
    workout_times: Dict[str, str]


@dataclass
class ProgressionConfig:
    adaptation_periods: Dict[str, Any]


@dataclass
class CalendarConfig:
    timezone: str
    output_dir: str
    separate_calendars: Dict[str, Dict[str, Any]]
    export_formats: List[str]


@dataclass
class PFAConfig:
    timeline: TimelineConfig
    fitness: FitnessConfig
    nutrition: NutritionConfig
    supplements: SupplementConfig
    training: TrainingConfig
    progression: ProgressionConfig
    calendar: CalendarConfig
    recipe_config: Optional[str] = None


def parse_time_string(time_str: str) -> time:
    """Parse time string in HH:MM format."""
    return datetime.strptime(time_str, "%H:%M").time()


def parse_duration_string(duration_str: str) -> int:
    """Parse duration string in MM:SS format to total seconds."""
    if ":" in duration_str:
        parts = duration_str.split(":")
        if len(parts) == 2:
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
    return int(duration_str)


def validate_percentages(macros: Dict[str, int]) -> bool:
    """Validate that macro percentages sum to 100."""
    return sum(macros.values()) == 100


def load_meal_database(base_config_path: str) -> Dict[str, Any]:
    """Load meal database from separate file."""
    config_path = Path(base_config_path)

    # Try multiple locations for the meal database
    possible_paths = [
        # Same directory as config
        config_path.parent / "meal_database.yml",
        # Up one level from personal/ to configs/
        config_path.parent.parent / "meal_database.yml",
        # Project root configs directory
        config_path.parent.parent.parent / "configs" / "meal_database.yml"
    ]

    for meal_db_path in possible_paths:
        if meal_db_path.exists():
            with open(meal_db_path, 'r') as f:
                return yaml.safe_load(f)

    return {}


def load_config(config_path: str) -> PFAConfig:
    """Load and validate YAML configuration."""
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)
        data = substitute_env_vars(data)

    # Load meal database if available
    meal_database = load_meal_database(str(config_path))
    if meal_database:
        # Merge meal database into nutrition config
        if 'nutrition' not in data:
            data['nutrition'] = {}
        data['nutrition']['meal_database'] = meal_database
        if 'meal_generation' in meal_database:
            data['nutrition']['meal_generation'] = meal_database['meal_generation']

    # Extract recipe_config if present
    recipe_config = data.get('recipe_config', None)

    # Parse timeline
    timeline_data = data['timeline']
    start_date = datetime.strptime(timeline_data['start_date'], "%Y-%m-%d").date()
    timeline = TimelineConfig(
        start_date=start_date,
        weeks=timeline_data['weeks'],
        buffer_weeks=timeline_data.get('buffer_weeks', {})
    )

    # Parse fitness configuration
    fitness = FitnessConfig(
        baseline=data['fitness']['baseline'],
        goals=data['fitness']['goals'],
        pfa_standards=data['fitness']['pfa_standards']
    )

    # Parse nutrition configuration
    nutrition_data = data['nutrition']
    nutrition = NutritionConfig(
        eating_window=nutrition_data['eating_window'],
        calorie_goals=nutrition_data['calorie_goals'],
        macros=nutrition_data['macros'],
        meal_timing=nutrition_data['meal_timing'],
        dietary_preferences=nutrition_data['dietary_preferences'],
        meal_database=nutrition_data.get('meal_database'),
        meal_generation=nutrition_data.get('meal_generation')
    )

    # Validate macros sum to 100%
    if not validate_percentages(nutrition.macros):
        raise ValueError("Macro percentages must sum to 100")

    # Parse supplements configuration
    supplements_data = data['supplements']
    supplements = SupplementConfig(
        daily_stack=supplements_data['daily_stack'],
        pre_workout=supplements_data['pre_workout'],
        post_workout=supplements_data['post_workout']
    )

    # Parse training configuration
    training = TrainingConfig(
        schedule=data['training']['schedule'],
        workout_types=data['training']['workout_types'],
        workout_times=data['training']['workout_times']
    )

    # Parse progression configuration
    progression = ProgressionConfig(
        adaptation_periods=data['progression']['adaptation_periods']
    )

    # Parse calendar configuration
    calendar_data = data['calendar']
    calendar = CalendarConfig(
        timezone=calendar_data['timezone'],
        output_dir=calendar_data['output_dir'],
        separate_calendars=calendar_data['separate_calendars'],
        export_formats=calendar_data['export_formats']
    )

    return PFAConfig(
        timeline=timeline,
        fitness=fitness,
        nutrition=nutrition,
        supplements=supplements,
        training=training,
        progression=progression,
        calendar=calendar,
        recipe_config=recipe_config
    )


def create_default_config() -> Dict[str, Any]:
    """Create a default configuration template."""
    return {
        'timeline': {
            'start_date': '2025-01-15',
            'weeks': 16,
            'buffer_weeks': {
                'run': 4,
                'pushups': 2,
                'situps': 2
            }
        },
        'fitness': {
            'baseline': {
                'run_time': '15:30',
                'pushups': 20,
                'situps': 35
            },
            'goals': {
                'run_time': '12:45',
                'pushups': 50,
                'situps': 55
            },
            'pfa_standards': {
                'run_time': '13:36',
                'pushups': 33,
                'situps': 42
            }
        },
        'nutrition': {
            'eating_window': {
                'type': 'time_restricted',
                'start_time': '08:00',
                'end_time': '20:00'
            },
            'calorie_goals': {
                'target': 2000
            },
            'macros': {
                'protein': 30,
                'carbs': 40,
                'fat': 30
            },
            'meal_timing': {
                'pre_workout': -30,
                'post_workout': 45,
                'meals_per_day': 3,
                'snacks_per_day': 2
            },
            'dietary_preferences': {
                'restrictions': ['none'],
                'allergies': [],
                'dislikes': []
            }
        },
        'supplements': {
            'daily_stack': [
                {
                    'time': '06:30',
                    'items': [
                        {'name': 'Creatine', 'dose': '5g'},
                        {'name': 'Vitamin D3', 'dose': '2000 IU'}
                    ]
                },
                {
                    'time': '18:00',
                    'items': [
                        {'name': 'Omega-3', 'dose': '1g EPA+DHA'},
                        {'name': 'Magnesium', 'dose': '400mg'}
                    ]
                }
            ],
            'pre_workout': {
                'enabled': True,
                'timing': -15,
                'items': [
                    {
                        'name': 'Caffeine',
                        'dose': '150mg',
                        'days': ['Mon', 'Wed', 'Fri']
                    }
                ]
            },
            'post_workout': {
                'enabled': True,
                'timing': 30,
                'items': [
                    {
                        'name': 'Protein Powder',
                        'dose': '25g',
                        'condition': 'if_no_meal_within_hour'
                    }
                ]
            }
        },
        'training': {
            'schedule': {
                'workout_days': ['Mon', 'Wed', 'Fri'],
                'strength_days': ['Tue', 'Thu'],
                'rest_days': ['Sat', 'Sun']
            },
            'workout_types': {
                'run_focused': {
                    'frequency': 3,
                    'progression_type': 'time_based',
                    'intensity_distribution': {
                        'easy': 60,
                        'moderate': 30,
                        'hard': 10
                    }
                },
                'strength_focused': {
                    'frequency': 2,
                    'progression_type': 'linear',
                    'focus': ['pushups', 'core', 'functional']
                }
            }
        },
        'progression': {
            'adaptation_periods': {
                'frequency': 4,
                'reduction': 0.7
            }
        },
        'calendar': {
            'timezone': 'America/Denver',
            'output_dir': './outputs/calendars/',
            'separate_calendars': {
                'workout': {
                    'name': 'PFA_Workouts',
                    'color': 'blue',
                    'location': 'Base Gym',
                    'default_duration': 60,
                    'reminders': [-15, -5]
                },
                'meals': {
                    'name': 'PFA_Meals',
                    'color': 'green',
                    'default_duration': 30,
                    'reminders': [-10]
                },
                'supplements': {
                    'name': 'PFA_Supplements',
                    'color': 'orange',
                    'default_duration': 5,
                    'reminders': [-5]
                }
            },
            'export_formats': ['ics']
        }
    }