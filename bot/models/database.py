# bot/models/database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, and_, not_, func
from typing import List, Optional
from .models import Base, User, Task, UserAttempt
import logging

class DatabaseManager:
    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url)
        self.async_session = async_sessionmaker(
            self.engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )

    async def create_tables(self):
        """Создание таблиц"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # User methods
    async def get_or_create_user(self, telegram_id: int, username: str, full_name: str) -> User:
        """Получить или создать пользователя"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if user is None:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    full_name=full_name
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
            
            return user

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя по telegram_id"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()

    async def update_user_score(self, telegram_id: int, points: int) -> None:
        """Обновить счет пользователя"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                user.score += points
                await session.commit()

    async def update_user_task_permission(self, telegram_id: int, can_get_task: bool) -> None:
        """Обновить разрешение на получение заданий"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                user.can_get_task = can_get_task
                await session.commit()

    async def get_all_users(self) -> List[User]:
        """Получить всех пользователей"""
        async with self.async_session() as session:
            result = await session.execute(select(User))
            return result.scalars().all()

    # Task methods
    async def create_task(self, title: str, description: str, image_url: Optional[str], 
                         correct_answer: str, points: int) -> Task:
        """Создать новое задание"""
        async with self.async_session() as session:
            task = Task(
                title=title,
                description=description,
                image_url=image_url,
                correct_answer=correct_answer,
                points=points
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)
            return task

    async def get_random_task_for_user(self, user_id: int) -> Optional[Task]:
        """Получить случайное задание для пользователя (исключая решенные)"""
        async with self.async_session() as session:
            # Получаем ID заданий, которые пользователь уже решал
            solved_tasks_subquery = select(UserAttempt.task_id).where(
                UserAttempt.user_id == user_id
            ).scalar_subquery()

            # Получаем случайное активное задание, которое пользователь еще не решал
            result = await session.execute(
                select(Task).where(
                    and_(
                        Task.is_active == True,
                        not_(Task.id.in_(solved_tasks_subquery))
                    )
                ).order_by(func.random()).limit(1)
            )
            return result.scalar_one_or_none()

    async def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """Получить задание по ID"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            return result.scalar_one_or_none()

    async def get_all_tasks(self) -> List[Task]:
        """Получить все задания"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Task).order_by(Task.id)
            )
            return result.scalars().all()

    async def update_task(self, task_id: int, **kwargs) -> Optional[Task]:
        """Обновить задание"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if task:
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                await session.commit()
                await session.refresh(task)
            
            return task

    # Attempt methods
    async def create_attempt(self, user_id: int, task_id: int, user_answer: str, is_correct: bool) -> UserAttempt:
        """Создать запись о попытке"""
        async with self.async_session() as session:
            attempt = UserAttempt(
                user_id=user_id,
                task_id=task_id,
                user_answer=user_answer,
                is_correct=is_correct
            )
            session.add(attempt)
            await session.commit()
            await session.refresh(attempt)
            return attempt

    async def get_user_attempts(self, user_id: int) -> List[UserAttempt]:
        """Получить все попытки пользователя"""
        async with self.async_session() as session:
            result = await session.execute(
                select(UserAttempt).where(UserAttempt.user_id == user_id)
            )
            return result.scalars().all()

    async def has_user_solved_task(self, user_id: int, task_id: int) -> bool:
        """Проверить, решил ли пользователь задание"""
        async with self.async_session() as session:
            result = await session.execute(
                select(UserAttempt).where(
                    and_(
                        UserAttempt.user_id == user_id,
                        UserAttempt.task_id == task_id,
                        UserAttempt.is_correct == True
                    )
                )
            )
            return result.scalar_one_or_none() is not None

    async def debug_user_state(self, telegram_id: int):
        """Отладочная информация о состоянии пользователя"""
        async with self.async_session() as session:
            user_result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                return "User not found"
            
            attempts_result = await session.execute(
                select(UserAttempt).where(UserAttempt.user_id == user.id)
            )
            attempts = attempts_result.scalars().all()
            
            debug_info = {
                'user_id': user.id,
                'telegram_id': user.telegram_id,
                'can_get_task': user.can_get_task,
                'score': user.score,
                'attempts_count': len(attempts),
                'last_attempt': None,
                'solved_tasks': []
            }
            
            if attempts:
                last_attempt = attempts[-1]
                debug_info['last_attempt'] = {
                    'task_id': last_attempt.task_id,
                    'user_answer': last_attempt.user_answer,
                    'is_correct': last_attempt.is_correct,
                    'attempted_at': last_attempt.attempted_at
                }
                
                for attempt in attempts:
                    if attempt.is_correct:
                        debug_info['solved_tasks'].append(attempt.task_id)
            
            return debug_info

    async def set_user_current_task(self, telegram_id: int, task_id: Optional[int]) -> None:
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                user = result.scalar_one_or_none()
                
                if user:
                    user.current_task_id = task_id
                    await session.commit()
                    if task_id:
                        logging.info(f"Set current task {task_id} for user {telegram_id}")
                    else:
                        logging.info(f"Cleared current task for user {telegram_id}")
            except Exception as e:
                await session.rollback()
                logging.error(f"Error setting user current task: {e}")
                raise

    async def get_user_current_task(self, telegram_id: int) -> Optional[Task]:
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if user and user.current_task_id:
                task_result = await session.execute(
                    select(Task).where(Task.id == user.current_task_id)
                )
                return task_result.scalar_one_or_none()
            return None

    async def get_random_task_for_user(self, user_id: int) -> Optional[Task]:
        async with self.async_session() as session:
            try:
                # Получаем пользователя
                user_result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    return None

                # Получаем ID заданий, которые пользователь уже решал правильно
                solved_tasks_subquery = select(UserAttempt.task_id).where(
                    and_(
                        UserAttempt.user_id == user_id,
                        UserAttempt.is_correct == True
                    )
                ).scalar_subquery()

                # Получаем случайное активное задание, которое пользователь еще не решал
                result = await session.execute(
                    select(Task).where(
                        and_(
                            Task.is_active == True,
                            not_(Task.id.in_(solved_tasks_subquery))
                        )
                    ).order_by(func.random()).limit(1)
                )
                task = result.scalar_one_or_none()
                
                if task:
                    logging.info(f"Found random task for user {user_id}: {task.title}")
                else:
                    logging.info(f"No available tasks for user {user_id}")
                
                return task
            except Exception as e:
                logging.error(f"Error getting random task for user: {e}")
                return None
            
    async def has_user_solved_task(self, user_id: int, task_id: int) -> bool:
        """Проверить, решил ли пользователь задание"""
        async with self.async_session() as session:
            result = await session.execute(
                select(UserAttempt).where(
                    and_(
                        UserAttempt.user_id == user_id,
                        UserAttempt.task_id == task_id,
                        UserAttempt.is_correct == True
                    )
                )
            )
            return result.scalar_one_or_none() is not None
