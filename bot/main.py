# bot/main.py
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from typing import Any, Awaitable, Callable, Dict

from bot.utils.config import load_config
from bot.models.database import DatabaseManager
from bot.services.task_service import TaskService
from bot.services.user_service import UserService
from bot.handlers.user_handlers import user_router
from bot.handlers.admin_handlers import admin_router
from .create_bot import bot

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServiceMiddleware(BaseMiddleware):
    def __init__(self, task_service: TaskService, user_service: UserService, admin_ids: list):
        self.task_service = task_service
        self.user_service = user_service
        self.admin_ids = admin_ids

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        data['task_service'] = self.task_service
        data['user_service'] = self.user_service
        data['admin_ids'] = self.admin_ids
        return await handler(event, data)

async def main():
    try:
        # Загрузка конфигурации
        config = load_config()
        logger.info("Configuration loaded successfully")
        
        # Инициализация бота
        logger.info("Initializing bot...")
        
        
        # Проверка токена через получение информации о боте
        try:
            bot_info = await bot.get_me()
            logger.info(f"Bot initialized successfully: @{bot_info.username}")
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise
        
        # Инициализация диспетчера
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        
        # Инициализация базы данных
        logger.info("Initializing database...")
        db = DatabaseManager(config.DATABASE_URL)
        await db.create_tables()
        logger.info("Database initialized successfully")
        
        # Инициализация сервисов
        task_service = TaskService(db)
        user_service = UserService(db)
        
        # Создание middleware с передачей admin_ids
        service_middleware = ServiceMiddleware(task_service, user_service, config.ADMIN_IDS)
        
        # Регистрация middleware для всех роутеров
        user_router.message.middleware(service_middleware)
        user_router.callback_query.middleware(service_middleware)
        admin_router.message.middleware(service_middleware)
        admin_router.callback_query.middleware(service_middleware)
        
        # Регистрация роутеров
        dp.include_router(user_router)
        dp.include_router(admin_router)
        
        logger.info(f"Bot started with admin IDs: {config.ADMIN_IDS}")
        logger.info("Bot is ready to receive messages")
        
        # Запуск бота
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)
        
    finally:
        if 'bot' in locals():
            await bot.session.close()
            logger.info("Bot session closed")

if __name__ == "__main__":
    asyncio.run(main())