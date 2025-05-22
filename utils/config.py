"""
Config

This module provides functionality to load configuration from config.yaml file.
"""

import os
import yaml
from typing import Dict, Any
from utils.prompt_loader import get_prompt
from dotenv import load_dotenv

load_dotenv()

def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml file with structured format."""
    try:
        with open('config.yaml', 'r') as file:
            return yaml.safe_load(file) or {}
    except FileNotFoundError:
        print("Warning: config.yaml file not found. Using default values.")
        return {}
    except yaml.YAMLError as e:
        print(f"Error parsing config.yaml: {e}. Using default values.")
        return {}

# Load the configuration
CONFIG = load_config()
# Telegram API credentials from environment variables
try:
    TELEGRAM_API_ID = int(os.getenv('TELEGRAM_API_ID', '0'))
    if TELEGRAM_API_ID == 0:
        print("Warning: TELEGRAM_API_ID not set in environment variables")
except (TypeError, ValueError):
    print("Error: TELEGRAM_API_ID must be an integer")
    TELEGRAM_API_ID = 0

TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
if not TELEGRAM_API_HASH:
    print("Warning: TELEGRAM_API_HASH not set in environment variables")

# Get Telegram-related configs
TELEGRAM_STRING_SESSION = os.getenv('TELEGRAM_STRING_SESSION')
TELEGRAM_CHANNEL_ID = os.getenv('DEFAULT_TELEGRAM_CHANNEL_ID')

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
if not OPENROUTER_API_KEY:
    print("Warning: OPENROUTER_API_KEY not set in environment variables")
    

# OpenRouter models
DEFAULT_MODEL = CONFIG.get('openrouter', {}).get('models', {}).get('openai-o4-mini', 'openai/o4-mini-high')
ANTHROPIC_MODEL = CONFIG.get('openrouter', {}).get('models', {}).get('anthropic-3.7-sonnet', 'anthropic/claude-3.7-sonnet')
GEMINI_MODEL = CONFIG.get('openrouter', {}).get('models', {}).get('gemini-2.5-flash-preview-05-20', 'google/gemini-2.5-flash-preview-05-20')

# Get message fetching settings
DEFAULT_MESSAGE_LIMIT = CONFIG.get('message_fetching', {}).get('default_limit', 100)

# Define default prompts in case files are not found
DEFAULT_PROMPT = CONFIG.get('default_prompt', {}).get('system', {}).get('prompt', [])
PROMPT_TEMPLATE_NAME = CONFIG.get('default_prompt', {}).get('prompt_template_name', 'summary_prompt')

# Load prompt templates from markdown files
SUMMARY_PROMPT_TEMPLATE = get_prompt("summary_prompt", DEFAULT_PROMPT)
OVERALL_PROMPT_TEMPLATE = get_prompt("overall_prompt", DEFAULT_PROMPT)
PARTICIPANT_PROMPT_TEMPLATE = get_prompt("participant_prompt", DEFAULT_PROMPT)
UNIFIED_PROMPT_TEMPLATE = get_prompt("unified_prompt", DEFAULT_PROMPT)
ADDITIONAL_PROMPT_TEMPLATE = get_prompt("additional_prompt", DEFAULT_PROMPT)

PROMPT_TEMPLATE = get_prompt(PROMPT_TEMPLATE_NAME, DEFAULT_PROMPT)

# Telegram client configuration
def get_telegram_client_config() -> Dict[str, str]:
    """Get Telegram client configuration from config file"""
    return CONFIG.get('telegram_client', {})
