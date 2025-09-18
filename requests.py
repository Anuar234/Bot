from sqlachemy import select, update, delete, func
from models import async_session, User, tasks
from pydantic import BaseModel, ConfigDict
from typing import List

class TaskSchema(BaseModel):
    id: int
    title: str
    completed: bool
    user: int

    model_config = ConfigDict(from_attributes=True)


async def add_user(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).where(user.tg_id == tg_id))
        if user:
            return user
        
        new_user = User(th_id=tg_id)
        session.add(new_user)
        await session.commit()
        await session.refresh()
        return new_user
    
async def get_tasks(user_id):
    async with async_session() as session:
        tasks = await session.scalars(
        select(Task).where(Task.user == user_id, Task.completed == False)
        )

        serialized_tasks = [
            TaskSchema.model_validate(t).model_dump() for t in tasks
        ]

        return serialized_tasks
    
async def get_completed_tasks_count(user_id):
    async with async_session() as session:
        return await session.scalar(select(func.count(Task.id)).where(Task.completed==True))
    