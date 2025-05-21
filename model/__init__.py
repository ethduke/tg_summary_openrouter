"""
Model package for Telegram Message Analyzer.
Contains the TelegramMessageAnalyzer class for message analysis.
"""

from model.message_analyzer import TelegramMessageAnalyzer


from model.openrouter import (
    generate_summary_with_ai
)

__all__ = ['TelegramMessageAnalyzer', 'generate_summary_with_ai'] 
