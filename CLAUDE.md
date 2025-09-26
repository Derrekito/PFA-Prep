# PFA Planning System

## Overview
This system generates a comprehensive Physical Fitness Assessment (PFA) training plan using configurable parameters to create calendar entries for workouts, meals, and supplements. The system supports progressive training, flexible meal planning, and customizable eating windows.

## Configuration Format
**Recommendation: Migrate from JSON to YAML** for better readability and comments support.

## Core Parameters


### Timeline & Goals
```yaml
timeline:
  start_date: "2025-01-15"
  weeks: 16                  # Total training weeks
  buffer_weeks:              # How many weeks before PFA test to hit goals
    run: 4                   # Be at goal run time 4 weeks early
    pushups: 2               # Be at goal pushups 2 weeks early
    situps: 2                # Be at goal situps 2 weeks early
```

### Fitness Baselines & Goals
```yaml
fitness:
  baseline:
    run_time: "15:30"        # Current 1.5 mile run time (MM:SS)
    pushups: 20              # Current max pushups in 1 minute
    situps: 35               # Current max situps in 1 minute

  goals:
    run_time: "12:45"        # Target 1.5 mile run time
    pushups: 50              # Target max pushups
    situps: 55               # Target max situps

  pfa_standards:             # Age/gender specific minimums
    run_time: "13:36"        # Minimum passing time
    pushups: 33              # Minimum passing pushups
    situps: 42               # Minimum passing situps
```

### Nutrition Parameters
```yaml
nutrition:
  eating_window:
    type: "time_restricted"   # "normal" or "time_restricted"
    start_time: "08:00"       # First meal time
    end_time: "20:00"         # Last meal time

  calorie_goals:
    target: 2000              # Daily calorie target (manually set)

  macros:                     # Percentages (should sum to 100)
    protein: 30
    carbs: 40
    fat: 30

  meal_timing:
    pre_workout: "-30"        # Minutes before workout
    post_workout: "+45"       # Minutes after workout

    # Day-specific meal configuration
    weekdays:
      meals_per_day: 2        # 2 meals on weekdays
      snacks_per_day: 1       # 1 snack on weekdays
    weekends:
      meals_per_day: 3        # 3 meals on weekends
      snacks_per_day: 1       # 1 snack on weekends

    # Manual meal schedule using breakfast/lunch/dinner nomenclature
    manual_schedule:
      # Weekday meals (2 meals: breakfast + dinner)
      - name: "breakfast"
        time: "11:30"
        days: ["Mon", "Tue", "Wed", "Thu", "Fri"]
      - name: "dinner"
        time: "18:00"
        days: ["Mon", "Tue", "Wed", "Thu", "Fri"]

      # Weekend meals (3 meals: breakfast + lunch + dinner)
      - name: "breakfast"
        time: "09:00"
        days: ["Sat", "Sun"]
      - name: "lunch"
        time: "13:00"
        days: ["Sat", "Sun"]
      - name: "dinner"
        time: "18:00"
        days: ["Sat", "Sun"]

      # Snacks for all days
      - name: "snack"
        time: "14:30"
        days: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

  dietary_preferences:
    restrictions: ["none"]    # "vegetarian", "vegan", "keto", "paleo", etc.
    allergies: []             # Food allergies/intolerances
    dislikes: []              # Foods to avoid

```

### Supplement Protocol
```yaml
supplements:
  daily_stack:
    - time: "06:30"
      items:
        - name: "Creatine"
          dose: "5g"
        - name: "Vitamin D3"
          dose: "2000 IU"
    - time: "18:00"
      items:
        - name: "Omega-3"
          dose: "1g EPA+DHA"
        - name: "Magnesium"
          dose: "400mg"

  pre_workout:
    enabled: true
    timing: "-15"             # Minutes before workout
    items:
      - name: "Caffeine"
        dose: "150mg"
        days: ["Mon", "Wed", "Fri"]  # Training days only

  post_workout:
    enabled: true
    timing: "+30"             # Minutes after workout
    items:
      - name: "Protein Powder"
        dose: "25g"
        condition: "if_no_meal_within_hour"
```

### Training Schedule
```yaml
training:
  schedule:
    workout_days: ["Mon", "Wed", "Fri"]  # Primary training days
    strength_days: ["Tue", "Thu"]        # Strength/accessory days
    rest_days: ["Sat", "Sun"]            # Complete rest or active recovery

  workout_types:
    run_focused:
      frequency: 3             # Times per week
      progression_type: "time_based"  # "time_based", "distance_based", "pace_based"
      intensity_distribution:  # Percentage of workouts at each intensity
        easy: 60
        moderate: 30
        hard: 10

    strength_focused:
      frequency: 2
      progression_type: "linear"  # "linear", "periodized", "undulating"
      focus: ["pushups", "core", "functional"]
```

### Progression Algorithms
```yaml
progression:
  run_improvement:
    method: "linear_weekly"    # "linear_weekly", "step_function", "exponential"
    weekly_improvement: "0:05" # Seconds per week improvement
    plateau_handling: "deload" # "deload", "maintain", "intensity_focus"

  strength_improvement:
    method: "linear_sets_reps"
    weekly_increase:
      pushups: 2               # Reps per week
      situps: 3                # Reps per week
    max_weekly_increase: 5     # Cap on weekly increases

  adaptation_periods:          # Planned easier weeks
    frequency: 4               # Every 4th week
    reduction: 0.7             # 70% of normal volume
```

### Calendar Generation
```yaml
calendar:
  timezone: "America/Denver"
  output_dir: "./outputs/calendars/"  # Where to save calendar files

  separate_calendars:        # Generate separate calendar files
    workout:
      name: "PFA_Workouts"
      color: "blue"
      location: "Base Gym"
      default_duration: 60
      reminders: ["-15", "-5"]  # Minutes before

    meals:
      name: "PFA_Meals"
      color: "green"
      default_duration: 30
      reminders: ["-10"]

    supplements:
      name: "PFA_Supplements"
      color: "orange"
      default_duration: 5
      reminders: ["-5"]

  export_formats: ["ics"]  # Supported output formats
```

## System Functions

### 1. Fitness Progression Calculator
- **Linear Progression**: Calculates weekly improvements based on baseline→goal over specified weeks
- **Buffer Integration**: Adjusts timeline to meet goals X weeks before test date
- **Plateau Detection**: Identifies when progress stalls and suggests modifications
- **Standards Validation**: Ensures goals meet or exceed PFA minimums

### 2. Calorie & Macro Calculator
- **Manual Calorie Setting**: Uses user-specified daily calorie target
- **Macro Distribution**: Converts percentages to gram targets based on calorie goal

### 3. Advanced Meal Plan Generator
- **Structured Meal Database**: Uses separate YAML database (`configs/meal_database.yml`) with detailed food metadata
- **Intelligent Meal Combinations**: Combines proteins, carbs, vegetables, and fruits based on meal type requirements
- **Multiple Options Per Meal**: Generates 3 distinct meal options per meal type per day (9+ options daily)
- **Time-Restricted Eating**: Respects eating windows (e.g., 11am-7pm) with override capability
- **Day-Specific Configuration**: Different meal counts for weekdays (2 meals) vs weekends (3 meals)
- **Weekend Preferences**: Enhanced breakfast options for weekend meals when more time is available
- **Macro Precision**: Each meal option includes detailed macronutrient breakdown and calorie counts
- **Exclusion Rules**: Prevents conflicting food combinations (e.g., eggs vs boiled eggs)
- **Portion Control**: Precise portion sizes for accurate macro calculations

### 4. Supplement Scheduler
- **Timing Optimization**: Schedules supplements for maximum efficacy
- **Interaction Awareness**: Prevents conflicting supplement timing
- **Training Day Logic**: Different stacks for training vs. rest days
- **Reminder Integration**: Calendar alerts for supplement times

### 5. Workout Progression Engine
- **Auto-Scaling**: Adjusts workout intensity based on progress
- **Periodization**: Incorporates easy/hard week cycles
- **Component Balancing**: Ensures all PFA elements get adequate attention
- **Recovery Integration**: Schedules rest days and deload weeks

### 6. Advanced Calendar Integration
- **ICS Export**: Generates .ics calendar files compatible with all major calendar applications
- **Separate Calendar Files**: Generates distinct .ics files for workouts, meals, and supplements
- **Multiple Meal Options**: Creates separate calendar events for each meal option (3 per meal type)
- **Time Staggering**: Meal options are staggered by 5-minute intervals for easy selection
- **Detailed Event Descriptions**: Each event includes full ingredient lists, portions, and macro breakdowns
- **Smart Reminders**: Configurable reminder timing with string-to-integer parsing
- **Progress Tracking**: Includes fields for logging actual performance
- **Flexibility**: Easy to modify individual events without rebuilding

## Usage Examples

### Basic Usage
```bash
# Generate your plan (auto-setup on first run)
./run_pfa_plan.sh my_plan.yml
```

All configuration options (start date, weeks, formats, output directory, etc.) are specified in the YAML config file itself. The shell script handles virtual environment setup and activation automatically.

## Shell Scripts

### run_pfa_plan.sh
All-in-one script that handles environment setup and plan generation:
```bash
./run_pfa_plan.sh [options] config_file.yml
```
- **First run**: Creates `venvs/main/` virtual environment and installs dependencies
- **Subsequent runs**: Activates existing virtual environment
- Calls `python generate_pfa_plan.py` with all passed arguments
- Provides colored output and error handling
- No separate setup step required

## Development Workflow

The project includes a knowledge graph system to help with development and code understanding:

### 1. Graph Service Setup
```bash
# Ensure Neo4j is running on bolt://localhost:7687
# Default credentials: neo4j/password

# Start the graph API service (creates lightweight venv under venvs/graph/)
./scripts/run-graph.sh
```

### 2. Populate Knowledge Graph
```bash
# Extract project structure and relationships into Neo4j
python extract_graph.py
```
This script analyzes the codebase and creates nodes for:
- Python modules and their relationships
- Function definitions and dependencies
- Configuration files and parameters

### 3. Query Development Context
```bash
# Query the graph via REST API
curl -X POST http://127.0.0.1:8000/graph/query \
  -H 'Content-Type: application/json' \
  -d '{"cypher":"MATCH (f:Function)-[:DEFINED_IN]->(m:Module) RETURN f.fqname, m.path LIMIT 5"}'
```

This development approach keeps investigations grounded in the current repository state and helps agents understand code relationships without loading unrelated files.

## Meal Database System

The system uses a separate structured meal database (`configs/meal_database.yml`) with detailed food metadata:

### Database Structure
```yaml
proteins:
  - name: "Grilled chicken breast"
    portion: "4oz (115g)"
    calories: 185
    protein: 35
    carbs: 0
    fat: 4
    meal_types: ["lunch", "dinner"]
    tags: ["lean", "versatile"]
    exclusions: ["fried_chicken"]
    prep_time: 15

carbs:
  - name: "Brown rice"
    portion: "1/2 cup cooked"
    calories: 110
    protein: 3
    carbs: 22
    fat: 1
    meal_types: ["lunch", "dinner"]
    tags: ["fiber", "whole_grain"]
    exclusions: ["white_rice", "quinoa"]
    prep_time: 25

meal_generation:
  options_per_meal: 3
  combination_rules:
    breakfast:
      required_components: ["proteins"]
      optional_components: ["carbs", "fruits"]
      min_protein: 15
      target_calories: [300, 450]
```

### Meal Generation Features
- **Component-Based Assembly**: Intelligently combines proteins + vegetables + carbs + fruits
- **Meal Type Appropriateness**: Each food item specifies which meals it's suitable for
- **Nutritional Requirements**: Minimum protein and calorie ranges per meal type
- **Exclusion Logic**: Prevents conflicting combinations (e.g., brown rice + white rice)
- **Weekend Preferences**: Special handling for weekend meals with more elaborate options

## File Structure
```
PFA_plan/
├── configs/
│   ├── meal_database.yml       # Structured meal database with metadata
│   ├── templates/
│   │   ├── beginner.yml
│   │   ├── intermediate.yml
│   │   └── advanced.yml
│   └── personal/
│       └── my_plan.yml
├── src/
│   ├── config_loader.py         # YAML configuration handling
│   ├── fitness_calculator.py    # Progression calculations
│   ├── nutrition_planner.py     # Meal planning and macros
│   ├── meal_generator.py        # Advanced meal combination engine
│   ├── supplement_scheduler.py  # Supplement timing optimization
│   ├── calendar_generator.py    # ICS file generation
│   └── progression_engine.py    # Workout programming
├── scripts/
│   └── run-graph.sh            # Graph service launcher
├── outputs/
│   └── calendars/
│       ├── PFA_Workouts.ics
│       ├── PFA_Meals.ics       # Contains 3 options per meal (9+ daily)
│       └── PFA_Supplements.ics
├── venvs/
│   ├── main/                   # Main Python virtual environment
│   └── graph/                  # Graph service virtual environment
├── generate_pfa_plan.py        # Main Python script
├── run_pfa_plan.sh            # All-in-one execution script
├── extract_graph.py           # Knowledge graph extraction
├── graph_api.py               # FastAPI graph service wrapper
├── requirements.txt           # Python dependencies
├── README.md                  # User documentation
└── CLAUDE.md                  # Project specifications
```
