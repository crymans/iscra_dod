# bot/services/task_service.py
from typing import Optional, List
from bot.models.database import DatabaseManager
from bot.models.models import Task
import logging

logger = logging.getLogger(__name__)

class TaskService:
    def __init__(self, db: DatabaseManager):
        self.db = db

    async def create_task(self, title: str, description: str, image_url: Optional[str], 
                         correct_answer: str, points: int) -> Task:
        return await self.db.create_task(
            title, description, image_url, correct_answer, points
        )

    async def get_random_task_for_user(self, telegram_id: int) -> Optional[Task]:
        user = await self.db.get_user_by_telegram_id(telegram_id)
        if not user or not user.can_get_task:
            return None
        
        return await self.db.get_random_task_for_user(user.id)

    async def check_answer(self, task_id: int, user_answer: str) -> bool:
        task = await self.db.get_task_by_id(task_id)
        if not task:
            return False
        
        # Улучшенная проверка ответа
        correct = task.correct_answer.lower().strip()
        user_ans = user_answer.lower().strip()
        
        logger.info(f"Checking answer - Correct: '{correct}', User: '{user_ans}'")
        
        # Сравниваем ответы
        return correct == user_ans

    async def get_all_tasks(self) -> List[Task]:
        return await self.db.get_all_tasks()

    async def get_task_by_id(self, task_id: int) -> Optional[Task]:
        return await self.db.get_task_by_id(task_id)

    async def update_task(self, task_id: int, **kwargs) -> Optional[Task]:
        return await self.db.update_task(task_id, **kwargs)