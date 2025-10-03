from aiogram import Bot
from bot.utils.config import load_config

config = load_config()
bot = Bot(token=config.BOT_TOKEN)