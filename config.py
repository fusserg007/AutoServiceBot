import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

# Telegram Bot configuration
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
if not TELEGRAM_TOKEN:
    logging.error("No TELEGRAM_BOT_TOKEN found in environment variables")

# Admin IDs - Telegram user IDs that have admin privileges
ADMIN_IDS = []
admin_ids_str = os.environ.get("ADMIN_IDS", "")
if admin_ids_str:
    try:
        ADMIN_IDS = [int(id) for id in admin_ids_str.split(",") if id.strip()]
    except ValueError:
        logging.error("Invalid ADMIN_IDS format. Expected comma-separated integers.")

# Специальный администратор для заявок по пробегу предыдущего ТО
MILEAGE_ADMIN_ID = None
mileage_admin_id_str = os.environ.get("MILEAGE_ADMIN_ID", "")
if mileage_admin_id_str:
    try:
        MILEAGE_ADMIN_ID = int(mileage_admin_id_str)
    except ValueError:
        logging.error("Invalid MILEAGE_ADMIN_ID format. Expected integer.")
