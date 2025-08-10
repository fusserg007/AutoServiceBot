import logging
import threading
from telegram.ext import Updater
from config import TELEGRAM_TOKEN
from telegram_handlers import register_handlers
from database import init_db

# Глобальная переменная для отслеживания экземпляра бота
_bot_instance = None
_bot_lock = threading.Lock()

def setup_bot():
    """Setup and return the telegram bot updater"""
    
    if not TELEGRAM_TOKEN:
        logging.error("Telegram token is missing. Please set the TELEGRAM_BOT_TOKEN environment variable.")
        return None
    
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    # Register all handlers
    register_handlers(dispatcher)
    
    logging.info("Bot is set up and handlers are registered")
    return updater

def start_bot():
    """Start the Telegram bot, обеспечивая, что только один экземпляр запущен"""
    global _bot_instance
    
    # Инициализируем базу данных перед запуском бота
    init_db()
    
    with _bot_lock:
        if _bot_instance is not None:
            logging.info("Bot instance already exists, reusing")
            return _bot_instance
        
        updater = setup_bot()
        if not updater:
            logging.error("Failed to set up bot updater")
            return None
        
        # Запускаем бота в режиме polling
        updater.start_polling()
        logging.info("Bot started in polling mode")
        
        # Сохраняем экземпляр бота
        _bot_instance = updater
        
        return updater

def stop_bot():
    """Остановить Telegram бота"""
    global _bot_instance
    
    with _bot_lock:
        if _bot_instance is not None:
            logging.info("Stopping bot...")
            _bot_instance.stop()
            _bot_instance = None
            logging.info("Bot stopped successfully")
        else:
            logging.info("No active bot instance to stop")
