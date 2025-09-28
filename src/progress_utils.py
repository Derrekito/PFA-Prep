#!/usr/bin/env python3
"""Progress bar utilities using rich library for TUI progress display."""

from rich.progress import Progress, TaskID, BarColumn, TextColumn, TimeRemainingColumn, SpinnerColumn
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from typing import Optional, List
import time
import sys
from logging_config import setup_logger

class ProgressTracker:
    """Centralized progress tracking for PFA plan generation."""

    def __init__(self):
        self.console = Console()
        self.progress: Optional[Progress] = None
        self.main_task: Optional[TaskID] = None
        self.total_steps = 0
        self.completed_steps = 0
        self.logger = setup_logger('progress_tracker')
        self._progress_visible = False

    def start(self, total_weeks: int):
        """Start the main progress tracking."""
        # Much more granular: track individual days and meals
        # Each week has 7 days, each day has ~3 meals = 21 meals per week
        # Plus workouts (3 per week) + supplements (7 per week) = 31 per week
        # Plus final calendars
        self.total_steps = (total_weeks * 31) + 3
        self.completed_steps = 0

        # Create progress bar - Rich handles keeping it at bottom automatically
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed:>3.0f}/{task.total:>3.0f})"),
            TimeRemainingColumn(),
            console=self.console
        )
        self.progress.start()
        self._progress_visible = True

        # Single main task tracks everything
        self.main_task = self.progress.add_task(
            f"[cyan]Generating {total_weeks}-week PFA plan...",
            total=self.total_steps
        )

    def log_message(self, message: str, level: str = "info"):
        """Log a message that will appear above the progress bar."""
        # Format message with appropriate emoji and color
        if level == "info":
            formatted_msg = f"ℹ️ {message}"
            style = "cyan"
        elif level == "warning":
            formatted_msg = f"⚠️ {message}"
            style = "yellow"
        elif level == "error":
            formatted_msg = f"❌ {message}"
            style = "red"
        elif level == "success":
            formatted_msg = f"✅ {message}"
            style = "green"
        else:
            formatted_msg = message
            style = None

        # Rich Progress should handle this automatically - just print to console
        if style:
            self.console.print(formatted_msg, style=style)
        else:
            self.console.print(formatted_msg)

    def update_status(self, description: str):
        """Update the status description."""
        if self.main_task is not None and self.progress:
            self.progress.update(self.main_task, description=f"[cyan]{description}")
        else:
            self.logger.debug(f"Status update skipped: {description}")

    def advance(self, steps: int = 1):
        """Advance progress by specified number of steps."""
        self.completed_steps += steps
        self.logger.debug(f"Advanced progress: {self.completed_steps}/{self.total_steps}")
        if self.main_task is not None and self.progress:
            self.progress.update(self.main_task, completed=self.completed_steps)
        else:
            self.logger.debug(f"Progress tracking skipped: main_task={self.main_task}, progress={self.progress}")

    def add_meal_progress(self, meal_type: str, day: str):
        """Show detailed meal generation progress."""
        self.logger.debug(f"Generating meal progress for {meal_type} on {day}")
        self.update_status(f"Generating {meal_type} for {day}...")
        self.advance(1)  # Advance 1 step per meal

    def add_recipe_progress(self, recipe_count: int, meal_type: str):
        """Show recipe fetching progress."""
        self.update_status(f"Found {recipe_count} recipes for {meal_type}...")

    def add_calendar_progress(self, calendar_type: str):
        """Show calendar generation progress."""
        self.update_status(f"Generating {calendar_type} calendar...")
        self.advance(1)  # Advance 1 step per calendar

    def finish(self):
        """Complete and clean up progress tracking."""
        if self.main_task and self.progress:
            self.progress.update(self.main_task, completed=self.total_steps)
            self.progress.update(self.main_task, description="[green]PFA Plan generation complete!")

        if self.progress and self._progress_visible:
            time.sleep(0.8)  # Brief pause to show completion
            self.progress.stop()
            self._progress_visible = False

        # Final success message
        self.console.print("\n✅ [bold green]PFA Plan generation complete![/bold green]")


# MealProgressTracker no longer needed - meal generator calls global tracker directly


# Global progress tracker instance
_global_tracker: Optional[ProgressTracker] = None

def get_progress_tracker() -> ProgressTracker:
    """Get the global progress tracker instance."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = ProgressTracker()
    return _global_tracker

def reset_progress_tracker():
    """Reset the global progress tracker."""
    global _global_tracker
    if _global_tracker:
        _global_tracker.finish()
    _global_tracker = None