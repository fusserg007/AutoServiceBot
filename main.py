"""
Основной файл для запуска Telegram-бота автосервиса
"""
import logging
import os
import signal
import sys
from bott import start_bot, stop_bot
from database import init_db

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальная переменная для отслеживания статуса бота
import threading
bot_thread = None

def run_bot_thread():
    """Запуск Telegram-бота в отдельном потоке"""
    logger.info("Запуск Telegram-бота для автосервиса...")
    start_bot()

# Функция для гарантии, что бот запущен только один раз
def ensure_bot_running():
    global bot_thread
    
    # Если поток с ботом не существует или завершился
    if bot_thread is None or not bot_thread.is_alive():
        logger.info("Запуск бота в новом потоке...")
        bot_thread = threading.Thread(target=run_bot_thread)
        bot_thread.daemon = True  # Поток демон будет завершен при завершении основного потока
        bot_thread.start()
        return True
    else:
        logger.info("Бот уже запущен")
        return False

# Обработчик сигнала для корректного завершения
def signal_handler(sig, frame):
    logger.info("Получен сигнал прерывания, останавливаем бота...")
    stop_bot()
    logger.info("Завершение работы...")
    sys.exit(0)

def check_and_migrate():
    """
    Проверка необходимости миграции данных из JSON в SQL
    """
    # Если база данных не существует, но есть JSON файлы - запускаем миграцию
    if not os.path.exists('autoservice.db') and (os.path.exists('users.json') or os.path.exists('requests.json')):
        logger.info("Обнаружены JSON файлы, но база данных не найдена. Запуск миграции...")
        from migrate_to_sql import main as migrate_main
        migrate_main()
    else:
        # Инициализируем базу данных (создаем таблицы, если их нет)
        init_db()

if __name__ == "__main__":
    # Регистрируем обработчик сигнала прерывания (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Инициализируем базу данных и запускаем миграцию если необходимо
    init_db()
    
    # Запускаем бота и блокируем основной поток
    ensure_bot_running()
    
    try:
        # Блокируем основной поток, но с возможностью корректного завершения
        logger.info("Бот запущен. Нажмите Ctrl+C для остановки.")
        # Бесконечный цикл для поддержания работы основного потока
        while True:
            try:
                # Спим небольшими интервалами, чтобы была возможность обработать сигналы
                threading.Event().wait(1.0)
            except KeyboardInterrupt:
                # Обрабатываем Ctrl+C
                signal_handler(signal.SIGINT, None)
                break
    except Exception as e:
        logger.error(f"Ошибка в основном потоке: {e}")
    finally:
        # Гарантируем остановку бота при завершении программы
        logger.info("Завершение работы бота...")
        stop_bot()