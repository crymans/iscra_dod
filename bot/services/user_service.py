# bot/services/user_service.py
from bot.models.database import DatabaseManager
from bot.models.models import User, Task
from typing import Optional, List

class UserService:
    def __init__(self, db: DatabaseManager):
        self.db = db

    async def get_or_create_user(self, telegram_id: int, username: str, full_name: str) -> User:
        return await self.db.get_or_create_user(telegram_id, username, full_name)

    async def update_user_score(self, telegram_id: int, points: int) -> None:
        await self.db.update_user_score(telegram_id, points)

    async def update_user_task_permission(self, telegram_id: int, can_get_task: bool) -> None:
        await self.db.update_user_task_permission(telegram_id, can_get_task)

    async def set_user_current_task(self, telegram_id: int, task_id: Optional[int]) -> None:
        await self.db.set_user_current_task(telegram_id, task_id)

    async def get_user_current_task(self, telegram_id: int) -> Optional[Task]:
        return await self.db.get_user_current_task(telegram_id)

    async def get_user_stats(self, telegram_id: int) -> dict:
        user = await self.db.get_user_by_telegram_id(telegram_id)
        if not user:
            return None
        
        attempts = await self.db.get_user_attempts(user.id)
        solved_count = len([a for a in attempts if a.is_correct])
        current_task = await self.get_user_current_task(telegram_id)
        
        return {
            'score': user.score,
            'solved_count': solved_count,
            'can_get_task': user.can_get_task,
            'username': user.username,
            'current_task': current_task.title if current_task else None
        }

    async def get_all_users(self) -> List[User]:
        return await self.db.get_all_users()

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        return await self.db.get_user_by_telegram_id(telegram_id)
    
    async def get_user_by_username(self, username: str):
        users = await self.get_all_users()
        for user in users:
            if user.username == username:
                return user
        return None