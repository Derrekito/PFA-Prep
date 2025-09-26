#!/usr/bin/env python3
"""Unified logging configuration for PFA Planning System."""

import logging
import sys
import os


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and emojis for different log levels."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[0;36m',    # Cyan
        'INFO': '\033[0;32m',     # Green
        'WARNING': '\033[1;33m',  # Yellow
        'ERROR': '\033[0;31m',    # Red
        'CRITICAL': '\033[1;31m', # Bright Red
        'RESET': '\033[0m'        # Reset
    }

    # Emojis for each level
    EMOJIS = {
        'DEBUG': '🔍',
        'INFO': 'ℹ️',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '💥'
    }

    def format(self, record):
        # Get color and emoji for this level
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        emoji = self.EMOJIS.get(record.levelname, '📝')
        reset_color = self.COLORS['RESET']

        # Format: EMOJI message (no level text)
        colored_message = f"{level_color}{emoji}{reset_color} {record.getMessage()}"

        return colored_message


def setup_logger(name: str, default_level: str = 'INFO'):
    """Set up a logger with consistent formatting.

    Args:
        name: Logger name (e.g., 'recipe_fetcher', 'meal_generator')
        default_level: Default logging level

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Check if already configured
    if logger.handlers:
        return logger

    # Set default level
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    logger.setLevel(level_map.get(default_level.upper(), logging.INFO))

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    # Use custom colored formatter
    formatter = ColoredFormatter()
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False  # Don't propagate to root logger

    return logger


def set_logging_level(logger_name: str, level_name: str):
    """Set the logging level for a specific logger.

    Args:
        logger_name: Name of the logger to configure
        level_name: 'DEBUG', 'INFO', 'WARNING', 'ERROR', or 'CRITICAL'
    """
    logger = logging.getLogger(logger_name)
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    logger.setLevel(level_map.get(level_name.upper(), logging.INFO))


def set_global_logging_level(level_name: str):
    """Set logging level for all PFA system loggers.

    Args:
        level_name: 'DEBUG', 'INFO', 'WARNING', 'ERROR', or 'CRITICAL'
    """
    loggers = ['recipe_fetcher', 'meal_generator', 'pfa_system']
    for logger_name in loggers:
        set_logging_level(logger_name, level_name)


def get_logging_level_from_env():
    """Get logging level from environment variable PFA_LOG_LEVEL."""
    return os.getenv('PFA_LOG_LEVEL', 'INFO').upper()