#!/usr/bin/env python3
"""Advanced calendar generator with separate calendar support and enhanced features."""

import json
import uuid
import logging
from datetime import datetime, date, time, timedelta, UTC
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from time_utils import parse_time_string


class CalendarGenerator:
    """Generates ICS calendar files for workouts, meals, and supplements."""

    def __init__(self, calendar_config: Dict[str, Any], timezone: str = "UTC"):
        self.config = calendar_config
        try:
            self.timezone = ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            self.timezone = ZoneInfo("UTC")

        self.weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def _parse_time(self, time_str: str) -> time:
        """Parse time string in HH:MM format."""
        return parse_time_string(time_str)

    def _to_utc_strings(self, local_date: date, local_time: time, duration_minutes: int = 60, offset_minutes: int = 0) -> Tuple[str, str]:
        """Convert local datetime to UTC strings for ICS format."""
        start_local = datetime.combine(local_date, local_time).replace(tzinfo=self.timezone)
        # Apply time offset for staggered events
        start_local = start_local + timedelta(minutes=offset_minutes)
        end_local = start_local + timedelta(minutes=duration_minutes)
        start_utc = start_local.astimezone(ZoneInfo("UTC"))
        end_utc = end_local.astimezone(ZoneInfo("UTC"))
        return start_utc.strftime("%Y%m%dT%H%M%SZ"), end_utc.strftime("%Y%m%dT%H%M%SZ")

    def _fold_ics_text(self, text: str) -> str:
        """Fold ICS text to handle newlines properly."""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        return text.replace("\n", "\\n")

    def _add_event(self, lines: List[str], start_utc: str, end_utc: str, summary: str,
                   description: str = "", location: str = "", reminders: List[int] = None,
                   event_id: str = None):
        """Add a calendar event to the ICS lines."""
        if event_id:
            uid = f"{event_id}@pfa-plan"
        else:
            uid = f"{uuid.uuid4()}@pfa-plan"
        lines.append("BEGIN:VEVENT")
        lines.append(f"DTSTART:{start_utc}")
        lines.append(f"DTEND:{end_utc}")
        lines.append(f"DTSTAMP:{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}")
        lines.append(f"UID:{uid}")
        lines.append(f"SUMMARY:{self._fold_ics_text(summary)}")

        if location:
            lines.append(f"LOCATION:{self._fold_ics_text(location)}")

        if description:
            lines.append(f"DESCRIPTION:{self._fold_ics_text(description)}")

        # Add reminders/alarms
        if reminders:
            for reminder_minutes in reminders:
                # Convert string to int if needed
                if isinstance(reminder_minutes, str):
                    reminder_minutes = int(reminder_minutes)
                lines.append("BEGIN:VALARM")
                lines.append("ACTION:DISPLAY")
                lines.append(f"DESCRIPTION:Reminder: {summary}")
                lines.append(f"TRIGGER:-PT{abs(reminder_minutes)}M")
                lines.append("END:VALARM")

        lines.append("END:VEVENT")

    def _create_calendar_header(self, calendar_name: str, color: str = None) -> List[str]:
        """Create ICS calendar header."""
        lines = []
        lines.append("BEGIN:VCALENDAR")
        lines.append("VERSION:2.0")
        lines.append("PRODID:-//PFA Planning System//EN")
        lines.append(f"X-WR-CALNAME:{calendar_name}")
        lines.append(f"X-WR-TIMEZONE:{self.timezone}")

        if color:
            # Add calendar color (supported by some clients)
            lines.append(f"X-APPLE-CALENDAR-COLOR:{color}")
            lines.append(f"X-OUTLOOK-COLOR:{color}")

        return lines

    def _create_calendar_footer(self) -> List[str]:
        """Create ICS calendar footer."""
        return ["END:VCALENDAR"]

    def generate_workout_calendar(self, workout_data: Dict[str, Any], start_date: date, weeks: int) -> str:
        """Generate workout calendar."""
        calendar_config = self.config.get('workout', {})
        calendar_name = calendar_config.get('name', 'PFA_Workouts')
        color = calendar_config.get('color', 'blue')
        location = calendar_config.get('location', '')
        default_duration = calendar_config.get('default_duration', 60)
        reminders = calendar_config.get('reminders', [])

        lines = self._create_calendar_header(calendar_name, color)

        # Generate workout events for each week
        for week in range(weeks):
            weekly_workouts = workout_data.get(f'week_{week + 1}', {})

            for day_name, workout in weekly_workouts.items():
                if workout.get('type') == 'rest':
                    continue  # Skip rest days

                # Calculate event date
                day_index = self.weekdays.index(day_name)

                # Find the first occurrence of this weekday on or after start_date
                start_weekday = start_date.weekday()  # Monday = 0, Sunday = 6
                days_until_target = (day_index - start_weekday) % 7
                first_occurrence = start_date + timedelta(days=days_until_target)

                # Add weeks to get the correct occurrence
                event_date = first_occurrence + timedelta(days=week * 7)

                # Determine workout time (default to 07:00)
                workout_time = self._parse_time(workout.get('time', '07:00'))
                duration = workout.get('total_duration', default_duration)

                # Create event
                start_utc, end_utc = self._to_utc_strings(event_date, workout_time, duration)

                # Build description
                description_parts = [f"Week {week + 1} - {workout.get('focus', 'Training').title()}"]

                if 'warm_up' in workout:
                    description_parts.append(f"Warm-up: {workout['warm_up']}")

                if 'main_set' in workout:
                    if isinstance(workout['main_set'], dict):
                        description_parts.append("Main Set:")
                        for exercise, sets in workout['main_set'].items():
                            description_parts.append(f"  {exercise.replace('_', ' ').title()}: {sets}")
                    else:
                        description_parts.append(f"Main Set: {workout['main_set']}")

                if 'strength_component' in workout:
                    description_parts.append(f"Strength: {workout['strength_component']}")

                if 'core_component' in workout:
                    description_parts.append(f"Core: {workout['core_component']}")

                if 'cool_down' in workout:
                    description_parts.append(f"Cool-down: {workout['cool_down']}")

                if 'intensity' in workout:
                    description_parts.append(f"Intensity: {workout['intensity'].title()}")

                description = "\\n\\n".join(description_parts)

                summary = f"{workout.get('type', 'Workout').replace('_', ' ').title()}"
                event_id = f"workout-week{week+1}-{day_name.lower()}"
                self._add_event(lines, start_utc, end_utc, summary, description, location, reminders, event_id)

        lines.extend(self._create_calendar_footer())
        return "\n".join(lines)

    def generate_meals_calendar(self, meal_data: Dict[str, Any], start_date: date, weeks: int) -> str:
        """Generate meals calendar."""
        calendar_config = self.config.get('separate_calendars', {}).get('meals', {})
        calendar_name = calendar_config.get('name', 'PFA_Meals')
        color = calendar_config.get('color', 'green')
        default_duration = calendar_config.get('default_duration', 30)
        reminders = calendar_config.get('reminders', [])

        lines = self._create_calendar_header(calendar_name, color)

        # Generate meal events for each week
        for week in range(weeks):
            weekly_meals = meal_data.get(f'week_{week + 1}', {})
            # Support both old and new data structures
            if 'daily_plans' in weekly_meals:
                # New structure from meal generator
                weekly_meal_times = {}
                daily_meals_data = weekly_meals['daily_plans']

                # Extract meal times from each day's data
                for day in daily_meals_data:
                    if 'meal_times' in daily_meals_data[day]:
                        weekly_meal_times[day] = daily_meals_data[day]['meal_times']
            else:
                # Legacy structure
                weekly_meal_times = weekly_meals.get('meal_times', {})
                daily_meals_data = weekly_meals.get('daily_meals', {})

            for day_index in range(7):
                day_name = self.weekdays[day_index]
                event_date = start_date + timedelta(days=week * 7 + day_index)
                daily_meals = daily_meals_data.get(day_name, {})

                # Get meal times for this specific day
                day_meal_times = weekly_meal_times.get(day_name, {})

                # Create events for each meal type
                available_meals = [meal for meal in day_meal_times.keys() if meal in daily_meals]
                for meal_type in available_meals:
                    if meal_type in day_meal_times and meal_type in daily_meals:
                        meal_time = self._parse_time(day_meal_times[meal_type])

                        # Handle both old format (string) and new format (array of options)
                        meal_info = daily_meals[meal_type]
                        if isinstance(meal_info, list) and len(meal_info) > 0:
                            # New format: create single event with all options in description
                            start_utc, end_utc = self._to_utc_strings(event_date, meal_time, default_duration)

                            all_options_parts = []

                            for option_index, meal_option in enumerate(meal_info):
                                meal_description = meal_option['description']
                                macros = meal_option['totals']

                                option_parts = [f"Option {option_index + 1}: {meal_description}"]

                                # Handle recipe-specific information
                                if meal_option.get('type') in ['recipe', 'component_with_recipe', 'component_with_no_recipe']:
                                    recipe_info = meal_option.get('recipe', {})
                                    if recipe_info.get('ingredients'):
                                        ingredients_display = meal_option.get('ingredients_display', '')
                                        if ingredients_display:
                                            option_parts.append(f"Ingredients: {ingredients_display}")

                                    if recipe_info.get('instructions'):
                                        instructions_preview = meal_option.get('instructions_preview', '')
                                        if instructions_preview:
                                            option_parts.append(f"Instructions: {instructions_preview}")

                                    # Add cooking time information
                                    prep_time = recipe_info.get('prep_time', 0)
                                    cook_time = recipe_info.get('cook_time', 0)
                                    if prep_time or cook_time:
                                        time_info = []
                                        if prep_time:
                                            time_info.append(f"Prep: {prep_time}min")
                                        if cook_time:
                                            time_info.append(f"Cook: {cook_time}min")
                                        option_parts.append(f"Time: {' | '.join(time_info)}")

                                    # Add servings and source info
                                    servings = recipe_info.get('servings', 1)
                                    if servings > 1:
                                        option_parts.append(f"Serves: {servings}")

                                    source_url = recipe_info.get('source_url')
                                    if source_url:
                                        option_parts.append(f"Recipe URL: {source_url}")

                                    # Add difficulty if specified
                                    difficulty = recipe_info.get('difficulty', '')
                                    if difficulty and difficulty != 'medium':
                                        option_parts.append(f"Difficulty: {difficulty.title()}")

                                    # Add tags
                                    tags = recipe_info.get('tags', [])
                                    if tags:
                                        tag_text = ', '.join(tags[:5])  # Limit to first 5 tags
                                        option_parts.append(f"Tags: {tag_text}")

                                # Show component items for component-based meals
                                if meal_option.get('type') in ['component_only', 'component_with_recipe', 'component_with_no_recipe']:
                                    items = meal_option.get('items', [])
                                    if items:
                                        items_text = " + ".join([f"{item['name']} ({item.get('portion', '')})"
                                                                 for item in items])
                                        option_parts.append(f"Components: {items_text}")

                                # Add macro information
                                if macros:
                                    macro_text = " | ".join([f"{k.title()}: {v}g" if k != 'calories'
                                                             else f"{k.title()}: {v}"
                                                             for k, v in macros.items()])
                                    option_parts.append(f"Nutrition: {macro_text}")

                                all_options_parts.append("\\n".join(option_parts))

                            description = "\\n\\n".join(all_options_parts)
                            summary = f"{meal_type.title()}"
                            event_id = f"meal-week{week+1}-{day_name.lower()}-{meal_type}"

                            self._add_event(lines, start_utc, end_utc, summary, description, "", reminders, event_id)
                        else:
                            # Legacy format: simple string
                            start_utc, end_utc = self._to_utc_strings(event_date, meal_time, default_duration)
                            meal_option = meal_info
                            macros = daily_meals.get(f'{meal_type}_macros', {})

                            description_parts = [f"Meal Option: {meal_option}"]
                            if macros:
                                macro_text = " | ".join([f"{k.title()}: {v}g" for k, v in macros.items()])
                                description_parts.append(f"Macros: {macro_text}")

                            description = "\\n\\n".join(description_parts)
                            summary = meal_type.title()
                            event_id = f"meal-week{week+1}-{day_name.lower()}-{meal_type}"

                            self._add_event(lines, start_utc, end_utc, summary, description, "", reminders, event_id)

                # Create events for snacks
                for snack_key in daily_meals.keys():
                    if snack_key.startswith('snack_') and not snack_key.endswith('_macros'):
                        snack_number = snack_key.split('_')[1]
                        snack_time_key = f'snack_{snack_number}'

                        if snack_time_key in day_meal_times:
                            snack_time = self._parse_time(day_meal_times[snack_time_key])
                            start_utc, end_utc = self._to_utc_strings(event_date, snack_time, 15)

                            snack_option = daily_meals[snack_key]
                            macros = daily_meals.get(f'{snack_key}_macros', {})

                            description_parts = [f"Snack Option: {snack_option}"]
                            if macros:
                                macro_text = " | ".join([f"{k.title()}: {v}g" for k, v in macros.items()])
                                description_parts.append(f"Macros: {macro_text}")

                            description = "\\n\\n".join(description_parts)
                            summary = f"Snack {snack_number}"
                            event_id = f"snack-week{week+1}-{day_name.lower()}-{snack_number}"

                            self._add_event(lines, start_utc, end_utc, summary, description, "", reminders, event_id)

        lines.extend(self._create_calendar_footer())
        return "\n".join(lines)

    def generate_supplements_calendar(self, supplement_data: Dict[str, Any], start_date: date, weeks: int) -> str:
        """Generate supplements calendar."""
        calendar_config = self.config.get('supplements', {})
        calendar_name = calendar_config.get('name', 'PFA_Supplements')
        color = calendar_config.get('color', 'orange')
        default_duration = calendar_config.get('default_duration', 5)
        reminders = calendar_config.get('reminders', [])

        lines = self._create_calendar_header(calendar_name, color)

        # Generate supplement events for each week
        for week in range(weeks):
            for day_index in range(7):
                day_name = self.weekdays[day_index]
                event_date = start_date + timedelta(days=week * 7 + day_index)

                # Get supplements for this day
                daily_supplements = supplement_data.get(day_name, {}).get('supplements', [])

                for supplement in daily_supplements:
                    supp_time = supplement['time']
                    if isinstance(supp_time, str):
                        supp_time = self._parse_time(supp_time)

                    start_utc, end_utc = self._to_utc_strings(event_date, supp_time, default_duration)

                    # Build description
                    description_parts = [
                        f"Supplement: {supplement['name']}",
                        f"Dose: {supplement['dose']}",
                        f"Type: {supplement['type'].replace('_', ' ').title()}"
                    ]

                    if 'condition' in supplement:
                        description_parts.append(f"Note: {supplement['condition']}")

                    description = "\\n".join(description_parts)
                    summary = supplement['name']
                    # Create unique ID with supplement name (sanitized for ID)
                    supp_name_clean = supplement['name'].replace(' ', '').replace('-', '').lower()
                    event_id = f"supplement-week{week+1}-{day_name.lower()}-{supp_name_clean}"

                    self._add_event(lines, start_utc, end_utc, summary, description, "", reminders, event_id)

        lines.extend(self._create_calendar_footer())
        return "\n".join(lines)

    def save_calendars(self, workout_data: Dict[str, Any], meal_data: Dict[str, Any],
                      supplement_data: Dict[str, Any], start_date: date, weeks: int) -> Dict[str, str]:
        """Save all calendar files and return paths."""
        output_dir = Path(self.config['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)

        saved_files = {}

        # Generate and save workout calendar
        if 'workout' in self.config['separate_calendars']:
            workout_calendar = self.generate_workout_calendar(workout_data, start_date, weeks)
            workout_path = output_dir / f"{self.config['separate_calendars']['workout']['name']}.ics"
            with open(workout_path, 'w', encoding='utf-8') as f:
                f.write(workout_calendar)
            saved_files['workouts'] = str(workout_path)

        # Generate and save meals calendar
        if 'meals' in self.config['separate_calendars']:
            meals_calendar = self.generate_meals_calendar(meal_data, start_date, weeks)
            meals_path = output_dir / f"{self.config['separate_calendars']['meals']['name']}.ics"
            with open(meals_path, 'w', encoding='utf-8') as f:
                f.write(meals_calendar)
            saved_files['meals'] = str(meals_path)

        # Generate and save supplements calendar
        if 'supplements' in self.config['separate_calendars']:
            supplements_calendar = self.generate_supplements_calendar(supplement_data, start_date, weeks)
            supplements_path = output_dir / f"{self.config['separate_calendars']['supplements']['name']}.ics"
            with open(supplements_path, 'w', encoding='utf-8') as f:
                f.write(supplements_calendar)
            saved_files['supplements'] = str(supplements_path)

        return saved_files

    def generate_combined_calendar(self, workout_data: Dict[str, Any], meal_data: Dict[str, Any],
                                 supplement_data: Dict[str, Any], start_date: date, weeks: int,
                                 calendar_name: str = "PFA_Complete_Plan") -> str:
        """Generate a single combined calendar with all events."""
        lines = self._create_calendar_header(calendar_name)

        # Add workout events
        workout_cal = self.generate_workout_calendar(workout_data, start_date, weeks)
        workout_events = workout_cal.split('\n')[4:-1]  # Extract events (skip header/footer)
        lines.extend(workout_events)

        # Add meal events
        meals_cal = self.generate_meals_calendar(meal_data, start_date, weeks)
        meal_events = meals_cal.split('\n')[4:-1]
        lines.extend(meal_events)

        # Add supplement events
        supplements_cal = self.generate_supplements_calendar(supplement_data, start_date, weeks)
        supplement_events = supplements_cal.split('\n')[4:-1]
        lines.extend(supplement_events)

        lines.extend(self._create_calendar_footer())
        return "\n".join(lines)

    def export_calendar_data(self, all_data: Dict[str, Any], start_date: date, weeks: int) -> Dict[str, str]:
        """Export all calendar data based on configuration."""
        results = {}

        workout_data = all_data.get('workouts', {})
        meal_data = all_data.get('meals', {})
        supplement_data = all_data.get('supplements', {})

        # Save separate calendars
        if self.config.get('separate_calendars'):
            separate_files = self.save_calendars(workout_data, meal_data, supplement_data, start_date, weeks)
            results.update(separate_files)

        # Save combined calendar if requested
        output_dir = Path(self.config['output_dir'])
        combined_calendar = self.generate_combined_calendar(
            workout_data, meal_data, supplement_data, start_date, weeks
        )
        combined_path = output_dir / "PFA_Complete_Plan.ics"
        with open(combined_path, 'w', encoding='utf-8') as f:
            f.write(combined_calendar)
        results['combined'] = str(combined_path)

        return results