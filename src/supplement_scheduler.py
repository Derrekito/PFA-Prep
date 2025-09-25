#!/usr/bin/env python3
"""Supplement scheduling system with timing optimization and interaction awareness."""

from datetime import datetime, time, timedelta
from typing import Dict, Any, List, Tuple, Optional


class SupplementScheduler:
    """Handles supplement scheduling, timing optimization, and interaction management."""

    def __init__(self, supplement_config: Dict[str, Any]):
        self.config = supplement_config
        self.daily_stack = supplement_config['daily_stack']
        self.pre_workout = supplement_config['pre_workout']
        self.post_workout = supplement_config['post_workout']

        # Common supplement interactions to avoid
        self.interactions = {
            'caffeine': {
                'avoid_with': ['magnesium', 'calcium'],
                'min_separation_hours': 2
            },
            'iron': {
                'avoid_with': ['calcium', 'zinc', 'magnesium'],
                'min_separation_hours': 2
            },
            'calcium': {
                'avoid_with': ['iron', 'zinc', 'magnesium'],
                'min_separation_hours': 2
            },
            'zinc': {
                'avoid_with': ['calcium', 'iron', 'copper'],
                'min_separation_hours': 2
            }
        }

    def parse_time_string(self, time_str: str) -> time:
        """Parse time string in HH:MM format."""
        return datetime.strptime(time_str, "%H:%M").time()

    def time_to_minutes(self, t: time) -> int:
        """Convert time object to minutes since midnight."""
        return t.hour * 60 + t.minute

    def minutes_to_time(self, minutes: int) -> time:
        """Convert minutes since midnight to time object."""
        hours = (minutes // 60) % 24
        mins = minutes % 60
        return time(hours, mins)

    def get_daily_schedule(self, day_of_week: str = None) -> List[Dict[str, Any]]:
        """Get daily supplement schedule for a specific day."""
        schedule = []

        # Add daily stack supplements
        for stack_entry in self.daily_stack:
            schedule_time = self.parse_time_string(stack_entry['time'])
            for item in stack_entry['items']:
                schedule.append({
                    'time': schedule_time,
                    'name': item['name'],
                    'dose': item['dose'],
                    'type': 'daily',
                    'category': 'maintenance'
                })

        return sorted(schedule, key=lambda x: self.time_to_minutes(x['time']))

    def get_workout_supplements(self, workout_time: time, day_of_week: str) -> List[Dict[str, Any]]:
        """Get workout-specific supplements for a given workout time and day."""
        workout_supplements = []

        # Pre-workout supplements
        if self.pre_workout['enabled']:
            pre_timing = self.pre_workout['timing']  # negative minutes
            pre_time_minutes = self.time_to_minutes(workout_time) + pre_timing
            pre_time = self.minutes_to_time(pre_time_minutes)

            for item in self.pre_workout['items']:
                # Check if this supplement applies to the specific day
                if 'days' in item:
                    day_short = day_of_week[:3]  # Convert to 3-letter format
                    if day_short not in item['days']:
                        continue

                workout_supplements.append({
                    'time': pre_time,
                    'name': item['name'],
                    'dose': item['dose'],
                    'type': 'pre_workout',
                    'category': 'performance'
                })

        # Post-workout supplements
        if self.post_workout['enabled']:
            post_timing = self.post_workout['timing']  # positive minutes
            post_time_minutes = self.time_to_minutes(workout_time) + post_timing
            post_time = self.minutes_to_time(post_time_minutes)

            for item in self.post_workout['items']:
                supplement_entry = {
                    'time': post_time,
                    'name': item['name'],
                    'dose': item['dose'],
                    'type': 'post_workout',
                    'category': 'recovery'
                }

                # Handle conditional supplements
                if 'condition' in item:
                    supplement_entry['condition'] = item['condition']

                workout_supplements.append(supplement_entry)

        return workout_supplements

    def check_interactions(self, supplements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check for supplement interactions and flag potential issues."""
        interaction_warnings = []

        for i, supp1 in enumerate(supplements):
            for j, supp2 in enumerate(supplements[i+1:], i+1):
                supp1_name = supp1['name'].lower()
                supp2_name = supp2['name'].lower()

                # Check if there are known interactions
                for interaction_supp, rules in self.interactions.items():
                    if interaction_supp in supp1_name:
                        for avoid_supp in rules['avoid_with']:
                            if avoid_supp in supp2_name:
                                time_diff = abs(self.time_to_minutes(supp1['time']) -
                                              self.time_to_minutes(supp2['time']))
                                min_separation = rules['min_separation_hours'] * 60

                                if time_diff < min_separation:
                                    interaction_warnings.append({
                                        'supplement1': supp1['name'],
                                        'supplement2': supp2['name'],
                                        'time1': supp1['time'].strftime('%H:%M'),
                                        'time2': supp2['time'].strftime('%H:%M'),
                                        'issue': f"Should be separated by at least {rules['min_separation_hours']} hours",
                                        'current_separation': f"{time_diff // 60}h {time_diff % 60}m"
                                    })

        return interaction_warnings

    def optimize_timing(self, supplements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optimize supplement timing to minimize interactions."""
        optimized_supplements = supplements.copy()

        # Get interaction warnings
        warnings = self.check_interactions(optimized_supplements)

        # Simple optimization: adjust times to resolve conflicts
        for warning in warnings:
            # Find the supplements involved in the conflict
            for i, supp in enumerate(optimized_supplements):
                if supp['name'] == warning['supplement1'] and supp['type'] == 'daily':
                    # Adjust daily supplement timing (easier to move than workout-related)
                    current_minutes = self.time_to_minutes(supp['time'])
                    # Move 2 hours later
                    new_minutes = (current_minutes + 120) % (24 * 60)
                    optimized_supplements[i]['time'] = self.minutes_to_time(new_minutes)
                    break

        return optimized_supplements

    def generate_weekly_schedule(self, workout_schedule: Dict[str, time]) -> Dict[str, Any]:
        """Generate complete weekly supplement schedule."""
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekly_schedule = {}

        for day in days:
            # Get daily supplements
            daily_supplements = self.get_daily_schedule(day)

            # Add workout supplements if there's a workout this day
            if day in workout_schedule:
                workout_time = workout_schedule[day]
                workout_supplements = self.get_workout_supplements(workout_time, day)
                daily_supplements.extend(workout_supplements)

            # Optimize timing to avoid interactions
            optimized_supplements = self.optimize_timing(daily_supplements)

            # Sort by time
            optimized_supplements = sorted(optimized_supplements,
                                         key=lambda x: self.time_to_minutes(x['time']))

            # Check for any remaining interactions
            interaction_warnings = self.check_interactions(optimized_supplements)

            weekly_schedule[day] = {
                'supplements': optimized_supplements,
                'interaction_warnings': interaction_warnings,
                'total_supplements': len(optimized_supplements)
            }

        return weekly_schedule

    def get_supplement_timing_guidelines(self) -> Dict[str, str]:
        """Get general timing guidelines for supplements."""
        return {
            'fat_soluble_vitamins': 'Take with meals containing fat (A, D, E, K)',
            'water_soluble_vitamins': 'Take on empty stomach or with water (B, C)',
            'minerals': 'Take between meals when possible',
            'probiotics': 'Take on empty stomach, 30-60 minutes before meals',
            'omega_3': 'Take with meals to improve absorption and reduce fishy taste',
            'creatine': 'Timing not critical, but consistency is important',
            'caffeine': 'Avoid within 6-8 hours of bedtime',
            'magnesium': 'Take in evening as it can promote relaxation',
            'iron': 'Take on empty stomach, avoid with dairy or caffeine',
            'calcium': 'Split doses throughout day, max 500mg at a time'
        }

    def get_hydration_recommendations(self) -> Dict[str, str]:
        """Get hydration recommendations for supplement intake."""
        return {
            'general': 'Take supplements with at least 8oz of water',
            'creatine': 'Increase water intake by 16-24oz daily',
            'fiber': 'Take with extra water to prevent digestive issues',
            'electrolytes': 'Can count toward daily fluid intake',
            'timing': 'Spread supplement water intake throughout the day'
        }

    def calculate_monthly_costs(self, supplement_prices: Dict[str, float] = None) -> Dict[str, float]:
        """Calculate estimated monthly costs for supplement regimen."""
        if not supplement_prices:
            # Default price estimates (could be updated with real data)
            supplement_prices = {
                'creatine': 20.0,
                'vitamin d3': 15.0,
                'omega-3': 25.0,
                'magnesium': 18.0,
                'caffeine': 30.0,
                'protein powder': 40.0,
                'multivitamin': 25.0,
                'cordyceps': 35.0,
                'lion\'s mane': 30.0,
                'collagen': 35.0,
                'vitamin c': 12.0
            }

        monthly_costs = {}
        total_cost = 0

        # Calculate costs for daily supplements
        for stack_entry in self.daily_stack:
            for item in stack_entry['items']:
                name = item['name'].lower()
                for price_key, price in supplement_prices.items():
                    if price_key in name:
                        monthly_costs[item['name']] = price
                        total_cost += price
                        break

        # Add workout supplement costs
        if self.pre_workout['enabled']:
            for item in self.pre_workout['items']:
                name = item['name'].lower()
                for price_key, price in supplement_prices.items():
                    if price_key in name and item['name'] not in monthly_costs:
                        monthly_costs[item['name']] = price * 0.5  # Less frequent use
                        total_cost += price * 0.5
                        break

        if self.post_workout['enabled']:
            for item in self.post_workout['items']:
                name = item['name'].lower()
                for price_key, price in supplement_prices.items():
                    if price_key in name and item['name'] not in monthly_costs:
                        monthly_costs[item['name']] = price * 0.7  # Workout days only
                        total_cost += price * 0.7
                        break

        monthly_costs['total'] = total_cost
        return monthly_costs