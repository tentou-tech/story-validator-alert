import os
import requests
import logging
from dotenv import load_dotenv
from telegram import Bot
from apscheduler.schedulers.blocking import BlockingScheduler
import pytz  # Import pytz to handle time zones

# Load environment variables
load_dotenv()
LCD_URL = os.getenv("LCD_URL")
VALIDATOR_ADDRESS = os.getenv("VALIDATOR_ADDRESS")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize Telegram bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Global variable to store last known tokens value
last_tokens = None

def get_validator_tokens():
    """Fetch validator staking data from LCD URL"""
    try:
        url = f"{LCD_URL}/staking/validators/{VALIDATOR_ADDRESS}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        tokens = int(data["msg"]["validator"]["tokens"]) // 10**9  # Convert and take whole number part
        moniker = data["msg"]["validator"]["description"]["moniker"]  # Get validator name
        return tokens, moniker
    except Exception as e:
        logging.error(f"Error fetching validator data: {e}")
        send_alert(f"⚠️ Error: {e}")  # Send error to Telegram
        return None, None

def send_alert(message):
    """Send a message to Telegram channel"""
    try:
        bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message)
        logging.info("Alert sent to Telegram channel.")
    except Exception as e:
        logging.error(f"Failed to send alert: {e}")

def check_validator_tokens():
    """Compare stored and new validator tokens value and send alert if changed."""
    global last_tokens
    new_tokens, moniker = get_validator_tokens()
    if new_tokens is None:
        return

    # Format tokens with comma separation using f'{value:,}'
    formatted_tokens = f'{new_tokens:,}'

    if last_tokens is None:
        logging.info("First time fetching tokens. Sending initial alert.")
        send_alert(f"🔔 Validator '{moniker}' tokens initial value: {formatted_tokens}")
    elif new_tokens != last_tokens:
        gap = new_tokens - last_tokens
        sign = "➕" if gap > 0 else "➖"
        message = f"🔔 Validator '{moniker}' tokens changed!\nPrevious: {f'{last_tokens:,}'}\nNew: {formatted_tokens}\nChange: {sign}{abs(gap)}"
        send_alert(message)
    else:
        logging.info("No change in validator tokens.")

    last_tokens = new_tokens

# Schedule daily task with a specific timezone (e.g., UTC)
scheduler = BlockingScheduler(timezone=pytz.UTC)
scheduler.add_job(check_validator_tokens, 'interval', days=1)

if __name__ == "__main__":
    logging.info("Starting Telegram bot scheduler...")
    check_validator_tokens()  # Run initially to fetch first value and send alert
    scheduler.start()
