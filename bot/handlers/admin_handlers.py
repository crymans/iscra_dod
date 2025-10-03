# bot/handlers/admin_handlers.py
from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
import logging
from ..create_bot import bot

from bot.services.task_service import TaskService
from bot.services.user_service import UserService

logger = logging.getLogger(__name__)
admin_router = Router()

def get_admin_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="📝 Добавить задание"))
    builder.add(types.KeyboardButton(text="📋 Управление заданиями"))
    builder.add(types.KeyboardButton(text="👥 Управление пользователями"))
    builder.add(types.KeyboardButton(text="❌ Удалить задание"))
    builder.add(types.KeyboardButton(text="🚫 Отмена действия"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

class CreateTask(StatesGroup):
    title = State()
    description = State()
    image_url = State()
    correct_answer = State()
    points = State()

class EditTask(StatesGroup):
    task_id = State()
    field = State()
    value = State()

# Функция для проверки админских прав
def check_admin(telegram_id: int, admin_ids: list) -> bool:
    return telegram_id in admin_ids

@admin_router.message(Command("admin"))
async def cmd_admin(message: types.Message, admin_ids: list):
    if not check_admin(message.from_user.id, admin_ids):
        await message.answer("❌ У вас нет прав для доступа к админ панели.")
        return
    
    admin_text = (
        "👨‍💻 <b>Панель администратора</b>\n\n"
        "Управление заданиями и пользователями:"
    )
    
    await message.answer(
        admin_text,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

@admin_router.message(F.text == "📝 Добавить задание")
@admin_router.message(Command("add_task"))
async def cmd_add_task(message: types.Message, state: FSMContext, admin_ids: list):
    if not check_admin(message.from_user.id, admin_ids):
        return
        
    await state.set_state(CreateTask.title)
    await message.answer("📝 Введите название задания:\n"
    "для отмены нажмите <code>/cancel</code>", parse_mode='html')

@admin_router.message(CreateTask.title)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(CreateTask.description)
    await message.answer("📖 Введите описание задания:")

@admin_router.message(CreateTask.description)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(CreateTask.image_url)
    await message.answer("🖼️ Введите URL картинки (или 'нет' если картинки нет):")

@admin_router.message(CreateTask.image_url)
async def process_image_url(message: types.Message, state: FSMContext):
    image_url = None if message.text.lower() == 'нет' else message.text
    await state.update_data(image_url=image_url)
    await state.set_state(CreateTask.correct_answer)
    await message.answer("✅ Введите правильный ответ:")

@admin_router.message(CreateTask.correct_answer)
async def process_correct_answer(message: types.Message, state: FSMContext):
    await state.update_data(correct_answer=message.text)
    await state.set_state(CreateTask.points)
    await message.answer("🏆 Введите количество баллов (по умолчанию 10):")

@admin_router.message(CreateTask.points)
async def process_points(message: types.Message, state: FSMContext, task_service: TaskService):
    try:
        points = int(message.text) if message.text.isdigit() else 10
    except ValueError:
        points = 10
    
    data = await state.get_data()
    
    task = await task_service.create_task(
        title=data['title'],
        description=data['description'],
        image_url=data['image_url'],
        correct_answer=data['correct_answer'],
        points=points
    )
    
    await state.clear()
    await message.answer(f"✅ Задание успешно создано! ID: {task.id}")

@admin_router.message(F.text == "📋 Управление заданиями")
@admin_router.message(Command("list_tasks"))
async def cmd_list_tasks(message: types.Message, task_service: TaskService, admin_ids: list):
    if not check_admin(message.from_user.id, admin_ids):
        return
        
    tasks = await task_service.get_all_tasks()
    
    if not tasks:
        await message.answer("📭 Нет созданных заданий.")
        return
    
    tasks_text = "📋 <b>Список заданий:</b>\n\n"
    for task in tasks:
        status = "✅" if task.is_active else "❌"
        # Показываем ответ только админам
        tasks_text += (
            f"🆔 ID: {task.id}\n"
            f"📚 Название: {task.title}\n"
            f"📖 Описание: {task.description[:50]}...\n"
            f"✅ Ответ: <code>{task.correct_answer}</code>\n"  # Добавляем ответ
            f"🏆 Баллы: {task.points}\n"
            f"📊 Статус: {status}\n"
            f"📋 Редактировать: <code>/edit_task {task.id}</code>\n"
            f"❌ Удалить: <code>/delete_task {task.id}</code>\n"
            f"{'─' * 30}\n"
        )
    
    await message.answer(tasks_text, parse_mode="HTML")

@admin_router.message(F.text == "👥 Управление пользователями")
@admin_router.message(Command("list_users"))
async def cmd_list_users(message: types.Message, user_service: UserService, admin_ids: list):
    if not check_admin(message.from_user.id, admin_ids):
        return
        
    users = await user_service.get_all_users()
    
    if not users:
        await message.answer("👥 Нет зарегистрированных пользователей.")
        return
    
    users_text = "👥 <b>Список пользователей:</b>\n\n"
    for user in users:
        status = "✅ Может получить" if user.can_get_task else "❌ Решил задание"
        current_task = await user_service.get_user_current_task(user.telegram_id)
        current_task_info = f" (задание: {current_task.title})" if current_task else ""
        
        users_text += (
            f"👤 {user.full_name} (@{user.username or 'нет'})\n"
            f"🏆 Баллы: {user.score}\n"
            f"📝 Статус: {status}{current_task_info}\n"
            f"📋 Выдать еще задание: <code>/allow_task {user.username}</code>\n"
            f"🔄 Поменять задание: <code>/assign_task {user.username} task_id</code>\n"
            f"{'─' * 30}\n"
        )
    
    await message.answer(users_text, parse_mode="HTML")

@admin_router.message(Command("allow_task"))
async def cmd_allow_task(message: types.Message, command: CommandObject, user_service: UserService, admin_ids: list):
    if not check_admin(message.from_user.id, admin_ids):
        return
        
    if not command.args:
        await message.answer(
            "❌ <b>Использование:</b> /allow_task @username\n\n"
            "Например:\n"
            "<code>/allow_task @username</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        username = command.args.replace('@', '').strip()
        
        # Получаем пользователя по username
        user = await user_service.get_user_by_username(username)
        
        if not user:
            await message.answer(f"❌ Пользователь @{username} не найден.")
            return
        
        # Разрешаем получать задания и очищаем текущее задание
        await user_service.update_user_task_permission(user.telegram_id, True)
        await user_service.set_user_current_task(user.telegram_id, None)
        await bot.send_message(
            f"✅ <b>Вам разрешено получить новое задание!</b>\n\n"
            f"Теперь вы можете использовать команду /task для получения следущего задания.",
            parse_mode="HTML"
        )
        await message.answer(
            f"✅ <b>Пользователю @{username} разрешено получить новое задание!</b>\n\n"
            f"Теперь пользователь может использовать команду /task для получения задания.",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in allow_task: {e}")
        await message.answer(f"❌ Ошибка: {e}")

@admin_router.message(Command("edit_task"))
async def cmd_edit_task(message: types.Message, command: CommandObject, task_service: TaskService, admin_ids: list):
    if not check_admin(message.from_user.id, admin_ids):
        return
        
    if not command.args:
        await message.answer("❌ Использование: /edit_task task_id")
        return
    
    try:
        task_id = int(command.args)
        task = await task_service.get_task_by_id(task_id)
        
        if not task:
            await message.answer(f"❌ Задание с ID {task_id} не найдено.")
            return
        
        # Показываем информацию о задании и кнопки для редактирования
        task_info = (
            f"📝 <b>Редактирование задания</b>\n\n"
            f"🆔 ID: {task.id}\n"
            f"📚 Название: {task.title}\n"
            f"📖 Описание: {task.description}\n"
            f"🖼️ Картинка: {task.image_url or 'нет'}\n"
            f"✅ Ответ: <code>{task.correct_answer}</code>\n"
            f"🏆 Баллы: {task.points}\n"
            f"📊 Статус: {'✅ Активно' if task.is_active else '❌ Неактивно'}\n\n"
            f"Выберите что редактировать:"
        )
        
        builder = InlineKeyboardBuilder()
        builder.add(
            types.InlineKeyboardButton(text="📚 Название", callback_data=f"edit_title_{task.id}"),
            types.InlineKeyboardButton(text="📖 Описание", callback_data=f"edit_desc_{task.id}"),
        )
        builder.add(
            types.InlineKeyboardButton(text="🖼️ Картинка", callback_data=f"edit_image_{task.id}"),
            types.InlineKeyboardButton(text="✅ Ответ", callback_data=f"edit_answer_{task.id}"),
        )
        builder.add(
            types.InlineKeyboardButton(text="🏆 Баллы", callback_data=f"edit_points_{task.id}"),
            types.InlineKeyboardButton(text="📊 Статус", callback_data=f"edit_status_{task.id}"),
        )
        
        await message.answer(task_info, reply_markup=builder.as_markup(), parse_mode="HTML")
        
    except ValueError:
        await message.answer("❌ Неверный формат ID задания")

@admin_router.callback_query(F.data.startswith("edit_"))
async def edit_task_callback(callback: types.CallbackQuery, state: FSMContext):
    data_parts = callback.data.split('_')
    field = data_parts[1]
    task_id = int(data_parts[2])
    
    field_names = {
        'title': 'название',
        'desc': 'описание', 
        'image': 'URL картинки',
        'answer': 'правильный ответ',
        'points': 'количество баллов',
        'status': 'статус активности'
    }
    
    await state.update_data(edit_task_id=task_id, edit_field=field)
    
    if field == 'status':
        # Для статуса предлагаем выбор
        builder = InlineKeyboardBuilder()
        builder.add(
            types.InlineKeyboardButton(text="✅ Активно", callback_data=f"set_active_{task_id}"),
            types.InlineKeyboardButton(text="❌ Неактивно", callback_data=f"set_inactive_{task_id}"),
        )
        await callback.message.answer(
            f"Выберите статус для задания ID {task_id}:",
            reply_markup=builder.as_markup()
        )
    else:
        await callback.message.answer(f"Введите новое значение для {field_names[field]}:")
    
    await callback.answer()

@admin_router.callback_query(F.data.startswith("set_"))
async def set_status_callback(callback: types.CallbackQuery, task_service: TaskService):
    data_parts = callback.data.split('_')
    status = data_parts[1]
    task_id = int(data_parts[2])
    
    is_active = status == 'active'
    
    task = await task_service.update_task(task_id, is_active=is_active)
    
    if task:
        status_text = "активно" if task.is_active else "неактивно"
        await callback.message.answer(f"✅ Статус задания ID {task_id} изменен на: {status_text}")
    else:
        await callback.message.answer("❌ Ошибка при обновлении задания")
    
    await callback.answer()


@admin_router.message(Command("assign_task"))
async def cmd_assign_task(message: types.Message, command: CommandObject, task_service: TaskService, user_service: UserService, admin_ids: list):
    """Назначить конкретное задание пользователю"""
    if not check_admin(message.from_user.id, admin_ids):
        return
        
    if not command.args:
        await message.answer(
            "❌ <b>Использование:</b> /assign_task @username task_id\n\n"
            "Например:\n"
            "<code>/assign_task @username 5</code>\n\n"
            "Чтобы посмотреть список заданий:\n"
            "<code>/list_tasks</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        args = command.args.split()
        if len(args) != 2:
            raise ValueError("Неверное количество аргументов")
        
        username = args[0].replace('@', '').strip()
        task_id = int(args[1])
        
        # Получаем пользователя по username
        user = await user_service.get_user_by_username(username)
        if not user:
            await message.answer(f"❌ Пользователь @{username} не найден.")
            return
        
        # Получаем задание по ID
        task = await task_service.get_task_by_id(task_id)
        if not task:
            await message.answer(f"❌ Задание с ID {task_id} не найдено.")
            return
        
        if not task.is_active:
            await message.answer(f"❌ Задание с ID {task_id} неактивно.")
            return
        
        # Проверяем, не решил ли пользователь уже это задание
        if await task_service.db.has_user_solved_task(user.id, task_id):
            await message.answer(
                f"❌ Пользователь @{username} уже решил задание '{task.title}'.\n\n"
                f"Используйте /allow_task @{username} чтобы разрешить новое задание."
            )
            return
        
        # Назначаем задание пользователю
        await user_service.set_user_current_task(user.telegram_id, task_id)
        await user_service.update_user_task_permission(user.telegram_id, True)
    

        await message.answer(
            f"✅ <b>Задание назначено!</b>\n\n"
            f"👤 Пользователь: @{username}\n"
            f"📚 Задание: {task.title} (ID: {task.id})\n"
            f"🏆 Баллы: {task.points}\n\n"
            f"Пользователь получит это задание при следующем использовании /task",
            parse_mode="HTML"
        )
    
        await bot.send_message(
            user.telegram_id,
            f"🎯 <b>Вам назначено новое задание!</b>\n\n"
            f"📚 {task.title}\n"
            f"🏆 Баллов за решение: {task.points}\n\n"
            f"Используйте /task чтобы посмотреть задание",
            parse_mode="HTML"
        )
    except ValueError as e:
        if "Неверное количество аргументов" in str(e):
            await message.answer(
                "❌ <b>Неверный формат команды</b>\n\n"
                "Использование: /assign_task @username task_id\n\n"
                "Например:\n"
                "<code>/assign_task @username 5</code>",
                parse_mode="HTML"
            )
        else:
            await message.answer("❌ Неверный формат ID задания")
    except Exception as e:
        logger.error(f"Error in assign_task: {e}")
        await message.answer(f"❌ Ошибка: {e}")

@admin_router.message(Command("user_tasks"))
async def cmd_user_tasks(message: types.Message, command: CommandObject, user_service: UserService, task_service: TaskService, admin_ids: list):
    """Посмотреть текущие задания пользователей"""
    if not check_admin(message.from_user.id, admin_ids):
        return
        
    users = await user_service.get_all_users()
    
    users_with_tasks = []
    for user in users:
        current_task = await user_service.get_user_current_task(user.telegram_id)
        if current_task:
            users_with_tasks.append((user, current_task))
    
    if not users_with_tasks:
        await message.answer("📭 Нет пользователей с активными заданиями.")
        return
    
    tasks_text = "👥 <b>Пользователи с активными заданиями:</b>\n\n"
    for user, task in users_with_tasks:
        tasks_text += (
            f"👤 @{user.username or 'без username'} ({user.full_name})\n"
            f"📚 Задание: {task.title} (ID: {task.id})\n"
            f"✅ Ответ: <code>{task.correct_answer}</code>\n"
            f"🏆 Баллы: {task.points}\n"
            f"{'─' * 30}\n"
        )
    
    await message.answer(tasks_text, parse_mode="HTML")

@admin_router.message(F.text == "❌ Удалить задание")
async def delete_task_button(message: types.Message):
    """Обработчик кнопки удаления задания"""
    await message.answer(
        "❌ <b>Удалить задание</b>\n\n"
        "Используйте команду:\n"
        "<code>/delete_task task_id</code>\n\n"
        "Например:\n"
        "<code>/delete_task 5</code>\n\n"
        "Чтобы посмотреть список заданий:\n"
        "<code>/list_tasks</code>\n\n"
        "<i>Внимание: удаление задания необратимо!</i>",
        parse_mode="HTML"
    )

@admin_router.message(F.text == "🚫 Отмена действия")
async def cancel_action_button(message: types.Message, state: FSMContext):
    """Обработчик кнопки отмены действия"""
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer(
            "✅ Текущее действие отменено.",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer(
            "ℹ️ <b>Отмена действия</b>\n\n"
            "Используйте эту кнопку чтобы отменить:\n"
            "• Создание задания\n"
            "• Редактирование задания\n"
            "• Или используйте команду /cancel",
            parse_mode="HTML"
        )

@admin_router.message(CreateTask.title, F.text.in_(["отмена", "cancel", "стоп", "stop", "/cancel"]))
@admin_router.message(CreateTask.description, F.text.in_(["отмена", "cancel", "стоп", "stop", "/cancel"]))
@admin_router.message(CreateTask.image_url, F.text.in_(["отмена", "cancel", "стоп", "stop", "/cancel"]))
@admin_router.message(CreateTask.correct_answer, F.text.in_(["отмена", "cancel", "стоп", "stop", "/cancel"]))
@admin_router.message(CreateTask.points, F.text.in_(["отмена", "cancel", "стоп", "stop", "/cancel"]))

@admin_router.message()
async def handle_edit_value(message: types.Message, state: FSMContext, task_service: TaskService):
    data = await state.get_data()
    
    if 'edit_task_id' not in data or 'edit_field' not in data:
        return
    
    task_id = data['edit_task_id']
    field = data['edit_field']
    value = message.text
    
    update_data = {}
    
    if field == 'title':
        update_data['title'] = value
    elif field == 'desc':
        update_data['description'] = value
    elif field == 'image':
        update_data['image_url'] = value if value.lower() != 'нет' else None
    elif field == 'answer':
        update_data['correct_answer'] = value
    elif field == 'points':
        try:
            update_data['points'] = int(value)
        except ValueError:
            await message.answer("❌ Неверный формат баллов")
            return
    
    task = await task_service.update_task(task_id, **update_data)
    
    if task:
        await message.answer(f"✅ Задание ID {task_id} успешно обновлено!")
    else:
        await message.answer("❌ Ошибка при обновлении задания")
    
    await state.clear()

