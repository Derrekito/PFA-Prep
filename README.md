# PFA Planning System

A comprehensive Physical Fitness Assessment (PFA) training plan generator that creates calendar entries for workouts, meals, and supplements with progressive training, flexible meal planning, and customizable eating windows.

## 🚀 Quick Start

### 1. Setup
```bash
# Clone/download the project
cd PFA_plan

# Run setup (creates venv, installs dependencies)
./setup.sh
```

### 2. Generate Your Plan
```bash
# Create a personal config from template
./run_pfa_plan.sh --template configs/personal/my_plan.yml

# Edit the config with your parameters
nano configs/personal/my_plan.yml

# Generate your complete PFA plan
./run_pfa_plan.sh configs/personal/my_plan.yml
```

### 3. Use Pre-built Templates
```bash
# For beginners (20 weeks, conservative progression)
./run_pfa_plan.sh configs/templates/beginner.yml

# For intermediate (16 weeks, standard progression)
./run_pfa_plan.sh configs/templates/intermediate.yml

# For advanced athletes (12 weeks, aggressive goals)
./run_pfa_plan.sh configs/templates/advanced.yml
```

## 📋 What You Get

The system generates:

### 📅 Calendar Files (ICS format)
- **Workout Calendar**: Progressive training with detailed descriptions
- **Meals Calendar**: Time-optimized nutrition with macro targets
- **Supplements Calendar**: Timing-optimized supplement schedule
- **Combined Calendar**: All events in one file

### 📊 Progress Reports
- **Fitness Progression**: Week-by-week targets for run time, push-ups, sit-ups, plank
- **Program Validation**: Intensity distribution analysis and recommendations
- **Meal Plans**: Complete weekly meal plans with macro breakdowns

## 🎯 Features

### Fitness Progression Calculator
- **Smart Progressions**: Linear, step-function, or exponential improvement curves
- **Buffer Zones**: Reach goals X weeks before test date for confidence
- **Standards Validation**: Ensures goals meet PFA minimums
- **Adaptation Weeks**: Built-in deload/recovery periods

### Intelligent Nutrition Planning
- **Time-Restricted Eating**: Configurable eating windows (e.g., 8am-8pm)
- **Workout Timing**: Pre/post workout meal optimization
- **Macro Calculations**: Converts percentages to gram targets
- **Variety Engine**: Rotates meals to prevent monotony
- **Dietary Restrictions**: Supports vegetarian, vegan, allergies, etc.

### Advanced Supplement Scheduling
- **Interaction Awareness**: Prevents conflicting supplement timing
- **Training Day Logic**: Different stacks for workout vs. rest days
- **Timing Optimization**: Maximizes absorption and efficacy
- **Cost Tracking**: Estimates monthly supplement costs

### Progressive Workout Engine
- **Periodization**: Incorporates intensity cycling and recovery weeks
- **Auto-Scaling**: Adjusts based on weekly progression targets
- **PFA Simulation**: Includes practice tests and circuit training
- **Intensity Distribution**: Follows 80/20 rule (80% easy/moderate, 20% hard)

## ⚙️ Configuration

All settings are in YAML format for readability:

```yaml
timeline:
  start_date: "2025-01-15"
  weeks: 16
  buffer_weeks:
    run: 4      # Reach run goal 4 weeks early
    pushups: 2
    situps: 2

fitness:
  baseline:
    run_time: "15:30"    # Current 1.5 mile time
    pushups: 25
    situps: 35
    plank: "1:30"

  goals:
    run_time: "12:45"    # Target 1.5 mile time
    pushups: 55
    situps: 60
    plank: "3:00"

nutrition:
  eating_window:
    type: "time_restricted"
    start_time: "08:00"
    end_time: "20:00"

  calorie_goals:
    target: 2200

  macros:
    protein: 30  # Percentages (must sum to 100)
    carbs: 40
    fat: 30
```

## 📚 Usage Examples

### Validate Configuration Only
```bash
./run_pfa_plan.sh --validate-only configs/personal/my_plan.yml
```

### Different Templates
```bash
# Conservative 20-week plan
./run_pfa_plan.sh configs/templates/beginner.yml

# Balanced 16-week plan
./run_pfa_plan.sh configs/templates/intermediate.yml

# Aggressive 12-week plan
./run_pfa_plan.sh configs/templates/advanced.yml
```

### Custom Configuration
```bash
# Create template
./run_pfa_plan.sh --template my_custom_plan.yml

# Edit parameters
nano my_custom_plan.yml

# Generate plan
./run_pfa_plan.sh my_custom_plan.yml
```

## 📁 Generated Files

```
outputs/
├── calendars/
│   ├── PFA_Workouts.ics           # Import into calendar app
│   ├── PFA_Meals.ics              # Meal timing and options
│   ├── PFA_Supplements.ics        # Supplement schedule
│   └── PFA_Complete_Plan.ics      # All events combined
├── progress_reports/
│   ├── fitness_progression.yaml    # Weekly targets
│   └── program_validation.yaml    # Program analysis
└── meal_plans/
    └── weekly_meal_plans.yaml     # Detailed meal planning
```

## 🎛️ Customization Options

### Training Schedule
- **Workout Days**: Default Mon/Wed/Fri
- **Strength Days**: Default Tue/Thu
- **Rest Days**: Default Sat/Sun
- **Intensity Distribution**: Configurable easy/moderate/hard ratios

### Meal Planning
- **Eating Windows**: Normal or time-restricted
- **Meal Frequency**: 3-4 meals + 1-2 snacks
- **Pre/Post Workout**: Automatic timing optimization
- **Dietary Restrictions**: Vegetarian, vegan, allergies, dislikes

### Supplement Protocols
- **Daily Stack**: Morning and evening supplements
- **Pre-Workout**: Optional caffeine and performance boosters
- **Post-Workout**: Recovery supplements with conditions
- **Interaction Prevention**: Automatic timing adjustments

## 🔧 Technical Details

### Requirements
- Python 3.8+
- PyYAML 6.0+
- Virtual environment (automatically created)

### Architecture
```
src/
├── config_loader.py          # YAML configuration handling
├── fitness_calculator.py     # Progression calculations
├── nutrition_planner.py      # Meal planning and macros
├── supplement_scheduler.py   # Supplement timing optimization
├── progression_engine.py     # Workout programming
└── calendar_generator.py     # ICS file generation
```

### Calendar Integration
- **ICS Format**: Universal calendar standard
- **Separate Calendars**: Import only what you need
- **Rich Descriptions**: Detailed workout instructions
- **Reminders**: Configurable alerts
- **Timezone Support**: Automatic conversion

## 📱 Calendar App Import

### iPhone/iOS
1. Email yourself the .ics files
2. Tap to open in Calendar app
3. Choose calendar to import to

### Android/Google Calendar
1. Upload .ics files to Google Drive
2. Open in Google Calendar
3. Select import calendar

### Outlook
1. File → Open & Export → Import/Export
2. Select .ics file
3. Choose destination calendar

## 🎯 Training Philosophy

The system follows evidence-based training principles:

- **Progressive Overload**: Gradual increases in volume/intensity
- **Periodization**: Planned variation and recovery
- **Specificity**: PFA-focused exercises and energy systems
- **Recovery**: Built-in deload weeks and rest days
- **Sustainability**: Realistic progressions and lifestyle integration

## 🚨 Safety Notes

- Consult healthcare provider before starting any training program
- Start with beginner template if unsure of fitness level
- Listen to your body and adjust as needed
- The system provides guidance, not medical advice

## 🤝 Contributing

This system was built following the specifications in `CLAUDE.md`. To contribute:

1. Review the architecture documentation
2. Follow existing code patterns
3. Test with multiple configuration templates
4. Ensure calendar output is properly formatted

## 📄 License

Built for military/fitness community use. Modify and distribute as needed.

---

**🎖️ Train hard, test easy. Semper Fi!** 🦅