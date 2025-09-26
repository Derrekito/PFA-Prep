#!/usr/bin/env python3
"""Shared time utilities for the PFA planning system."""

from datetime import datetime, time
from typing import Tuple


def parse_time_string(time_str: str) -> time:
    """Parse time string in HH:MM format to time object."""
    return datetime.strptime(time_str, "%H:%M").time()


def time_to_minutes(t: time) -> int:
    """Convert time object to total minutes since midnight."""
    return t.hour * 60 + t.minute


def minutes_to_time(minutes: int) -> time:
    """Convert total minutes since midnight to time object."""
    # Handle day overflow
    minutes = minutes % (24 * 60)
    return time(minutes // 60, minutes % 60)


def parse_time_to_seconds(time_str: str) -> int:
    """Convert MM:SS format to total seconds."""
    if ":" in time_str:
        minutes, seconds = map(int, time_str.split(":"))
        return minutes * 60 + seconds
    return int(time_str)


def seconds_to_time_string(total_seconds: int) -> str:
    """Convert total seconds to MM:SS format."""
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02d}"


def calculate_eating_duration(start_time: time, end_time: time) -> int:
    """Calculate eating window duration in minutes, handling midnight crossover."""
    start_minutes = time_to_minutes(start_time)
    end_minutes = time_to_minutes(end_time)

    # If end time is before start time, it crosses midnight
    if end_minutes <= start_minutes:
        end_minutes += 24 * 60

    return end_minutes - start_minutes


def add_minutes_to_time(t: time, minutes_offset: int) -> time:
    """Add minutes offset to a time object (can be negative)."""
    total_minutes = time_to_minutes(t) + minutes_offset
    return minutes_to_time(total_minutes)


def is_time_in_window(check_time: time, start_time: time, end_time: time) -> bool:
    """Check if a time falls within a time window, handling midnight crossover."""
    check_minutes = time_to_minutes(check_time)
    start_minutes = time_to_minutes(start_time)
    end_minutes = time_to_minutes(end_time)

    # Handle midnight crossover
    if end_minutes <= start_minutes:
        end_minutes += 24 * 60
        if check_minutes < start_minutes:
            check_minutes += 24 * 60

    return start_minutes <= check_minutes <= end_minutes