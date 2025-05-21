import logging
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import utils.config as config
import asyncio
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)

# Time constants
SECONDS_PER_HOUR = 3600
SECONDS_PER_MINUTE = 60

# Load config values
CONFIG = config.CONFIG

# Telegram client configuration from consts.yaml
SYSTEM_VERSION = CONFIG.get('telegram_client', {}).get('system_version')
APP_VERSION = CONFIG.get('telegram_client', {}).get('app_version')
DEVICE_MODEL = CONFIG.get('telegram_client', {}).get('device_model')
SYSTEM_LANG_CODE = CONFIG.get('telegram_client', {}).get('system_lang_code')
LANG_CODE = CONFIG.get('telegram_client', {}).get('lang_code')

# Telegram API credentials from environment variables
API_ID = config.TELEGRAM_API_ID
API_HASH = config.TELEGRAM_API_HASH

async def generate_session():
    try:
        # Create client with StringSession
        client = TelegramClient(
            StringSession(), 
            API_ID, 
            API_HASH,
            system_version=SYSTEM_VERSION,
            app_version=APP_VERSION,
            device_model=DEVICE_MODEL,
            system_lang_code=SYSTEM_LANG_CODE,
            lang_code=LANG_CODE
        )

        # Start client
        await client.start()

        # Get the session string
        session_string = client.session.save()
        print("\nYour session string is:\n")
        print(session_string)
        print("\nStore this string safely!\n")

        await client.disconnect()
        return session_string

    except Exception as e:
        print(f"\nError: {str(e)}")
        if "FLOOD_WAIT" in str(e):
            wait_time = int(str(e).split('of ')[1].split(' seconds')[0])
            hours = wait_time // SECONDS_PER_HOUR
            minutes = (wait_time % SECONDS_PER_HOUR) // SECONDS_PER_MINUTE
            print(f"\nTelegram requires waiting {hours} hours and {minutes} minutes before requesting another code.")
            print("Please try again after this time period.")
        return None

if __name__ == "__main__":
    try:
        session_string = asyncio.run(generate_session())
        if session_string:
            # Save to .env file
            with open('.env', 'r') as f:
                env_lines = f.readlines()

            with open('.env', 'w') as f:
                for line in env_lines:
                    if not line.startswith('TELEGRAM_STRING_SESSION='):
                        f.write(line)
                f.write(f'\nTELEGRAM_STRING_SESSION="{session_string}"')

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"\nFatal error: {e}")
    sys.exit(0) 