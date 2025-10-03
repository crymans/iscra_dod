# bot/utils/config.py
import os
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

@dataclass
class Config:
    BOT_TOKEN: str
    ADMIN_IDS: List[int]
    DATABASE_URL: str

def load_config() -> Config:
    # Получаем абсолютный путь к .env файлу
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent  # bot/utils/../../ = project root
    env_path = project_root / '.env'
    
    logger.info(f"Looking for .env file at: {env_path}")
    
    # Загружаем .env файл
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f".env file found and loaded from: {env_path}")
    else:
        logger.warning(f".env file not found at: {env_path}")
        # Пробуем загрузить из текущей директории
        load_dotenv()
    
    # Читаем переменные
    bot_token = os.getenv('BOT_TOKEN')
    logger.info(f"BOT_TOKEN from env: {'*' * 10 if bot_token else 'NOT FOUND'}")
    
    if not bot_token:
        # Выводим все переменные окружения для отладки
        all_env_vars = {k: v for k, v in os.environ.items() if 'TOKEN' in k or 'BOT' in k}
        logger.info(f"Relevant env vars: {all_env_vars}")
        raise ValueError("BOT_TOKEN not found in environment variables")
    
    admin_ids_str = os.getenv('ADMIN_IDS', '')
    admin_ids = []
    
    if admin_ids_str:
        try:
            admin_ids = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip()]
        except ValueError as e:
            logger.warning(f"Invalid admin IDs format: {e}")
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables")
    
    logger.info(f"Config loaded successfully")
    logger.info(f"Admin IDs: {admin_ids}")
    logger.info(f"Database URL: {database_url}")
    
    return Config(
        BOT_TOKEN=bot_token,
        ADMIN_IDS=admin_ids,
        DATABASE_URL=database_url
    )