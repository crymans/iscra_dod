# bot/handlers/user_handlers.py
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import logging

from bot.services.task_service import TaskService
from bot.services.user_service import UserService
from bot.models.models import Task  # Добавьте этот импорт

logger = logging.getLogger(__name__)
user_router = Router()

def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="🎯 Получить задание"))
    builder.add(types.KeyboardButton(text="📊 Моя статистика"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_task_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="📊 Моя статистика"))
    builder.add(types.KeyboardButton(text="🏠 Главное меню"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

@user_router.message(Command("start"))
async def cmd_start(message: types.Message, user_service: UserService):
    user = await user_service.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )
    
    welcome_text = (
        "🎉 Добро пожаловать на День открытых дверей!\n\n"
        "🎯 Вы можете получить одно задание для решения - отправьте /task или воспользуйтесь кнопкой\n"
        "📝 За верный ответ вы получите баллы - пример ответа к заданию 'Ответ ...текст_ответа...'\n"
        "📊 Следите за своим прогрессом в статистике.\n\n"
        "Удачи! 🍀"
    )
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard()
    )

@user_router.message(Command("task"))
@user_router.message(F.text == "🎯 Получить задание")
async def cmd_task(message: types.Message, task_service: TaskService, user_service: UserService):
    user = await user_service.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )
    
    # Проверяем, может ли пользователь получить задание
    if not user.can_get_task:
        await message.answer(
            "⏳ Вы уже решили задание!\n\n"
            "Ожидайте, администратор может предоставить вам новое задание.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Проверяем, есть ли у пользователя уже текущее задание
    current_task = await user_service.get_user_current_task(message.from_user.id)
    if current_task:
        await show_current_task(message, current_task)
        return
    
    # Получаем новое задание
    task = await task_service.get_random_task_for_user(message.from_user.id)
    
    if not task:
        await message.answer(
            "🎉 Вы решили все доступные задания!\n\n"
            "Ожидайте, администратор может добавить новые задания.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Закрепляем задание за пользователем
    await user_service.set_user_current_task(message.from_user.id, task.id)
    
    # Показываем задание
    await show_current_task(message, task)

async def show_current_task(message: types.Message, task: Task):  # Исправлено: Task вместо types.Task
    """Показать текущее задание пользователю"""
    task_text = (
        f"📚 <b>{task.title}</b>\n\n"
        f"📖 {task.description}\n\n"
        f"🏆 Баллов за решение: {task.points}"
    )
    
    if task.image_url:
        await message.answer_photo(
            photo=task.image_url,
            caption=task_text,
            parse_mode="HTML"
        )
    else:
        await message.answer(task_text, parse_mode="HTML")
    
    await message.answer(
        "✍️ Напишите ваш ответ текстом:",
        reply_markup=get_task_keyboard()
    )

@user_router.message(Command("stats"))
@user_router.message(F.text == "📊 Моя статистика")
async def cmd_stats(message: types.Message, user_service: UserService):
    stats = await user_service.get_user_stats(message.from_user.id)
    if stats:
        status = "✅ Можете получить задание" if stats['can_get_task'] else "⏳ Ожидайте новое задание"
        current_task_info = f"📝 Текущее задание: {stats['current_task']}" if stats['current_task'] else "📝 Текущее задание: нет"
        
        stats_text = (
            f"📊 <b>Ваша статистика</b>\n\n"
            f"👤 Пользователь: @{stats['username'] or 'без username'}\n"
            f"🏆 Всего баллов: {stats['score']}\n"
            f"✅ Решено заданий: {stats['solved_count']}\n"
            f"📝 Статус: {status}\n"
            f"{current_task_info}"
        )
        
        await message.answer(stats_text, parse_mode="HTML")
    else:
        await message.answer("❌ Статистика не найдена. Используйте /start для начала работы.")

@user_router.message(F.text == "🏠 Главное меню")
async def cmd_main_menu(message: types.Message):
    await message.answer(
        "🏠 <b>Главное меню</b>\n\nВыберите действие:",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

@user_router.message(Command("debug"))
async def cmd_debug(message: types.Message, task_service: TaskService, user_service: UserService):
    """Команда для отладки - посмотреть состояние пользователя"""
    debug_info = await task_service.db.debug_user_state(message.from_user.id)
    
    debug_text = (
        f"🔧 <b>Отладочная информация</b>\n\n"
        f"👤 User ID: {debug_info['user_id']}\n"
        f"📱 Telegram ID: {debug_info['telegram_id']}\n"
        f"🎯 Может получать задания: {debug_info['can_get_task']}\n"
        f"🏆 Баллы: {debug_info['score']}\n"
        f"📝 Всего попыток: {debug_info['attempts_count']}\n"
        f"✅ Решенные задания: {debug_info['solved_tasks']}\n"
    )
    
    if debug_info['last_attempt']:
        last = debug_info['last_attempt']
        debug_text += (
            f"\n📋 <b>Последняя попытка:</b>\n"
            f"🆔 ID задания: {last['task_id']}\n"
            f"📝 Ответ: {last['user_answer']}\n"
            f"✅ Правильно: {last['is_correct']}\n"
            f"🕐 Время: {last['attempted_at']}"
        )
    
    await message.answer(debug_text, parse_mode="HTML")

@user_router.message(F.text.contains('Ответ'))
async def handle_answer(message: types.Message, task_service: TaskService, user_service: UserService):
    # Пропускаем команды и кнопки
    if (message.text.startswith('/') or 
        message.text in ["🎯 Получить задание", "📊 Моя статистика", "🏠 Главное меню"]):
        return
    
    user = await user_service.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )
    
    # Проверяем, может ли пользователь отвечать
    if not user.can_get_task:
        await message.answer(
            "⏳ Вы уже решили задание!\n\n"
            "Ожидайте, администратор может предоставить вам новое задание.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Получаем текущее задание пользователя
    current_task = await user_service.get_user_current_task(message.from_user.id)
    if not current_task:
        await message.answer(
            "❌ Сначала получите задание с помощью /task",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Проверяем ответ
    user_answer = message.text.lower().replace('ответ', '').strip()
    is_correct = await task_service.check_answer(current_task.id, user_answer)
    
    logger.info(f"Answer check - Task: {current_task.id}, User answer: '{user_answer}', Correct: '{current_task.correct_answer}', Is correct: {is_correct}")
    
    # Создаем попытку
    await task_service.db.create_attempt(user.id, current_task.id, user_answer, is_correct)
    
    if is_correct:
        # Начисляем баллы
        await user_service.update_user_score(message.from_user.id, current_task.points)
        # Запрещаем получать новые задания
        await user_service.update_user_task_permission(message.from_user.id, False)
        # Очищаем текущее задание
        await user_service.set_user_current_task(message.from_user.id, None)
        
        stats = await user_service.get_user_stats(message.from_user.id)
        
        await message.answer(
            f"✅ <b>Правильно!</b>\n\n"
            f"🎯 Вы заработали: {current_task.points} баллов\n"
            f"🏆 Ваш текущий счет: {stats['score']}\n\n"
            f"Вы решили задание! Администратор может предоставить вам новое задание.",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Неправильно</b>\n\n"
            "Попробуйте еще раз!",
            parse_mode="HTML"
        )