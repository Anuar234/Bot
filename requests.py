from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from models import async_session, User, Product, UserProduct, TrainingProgram, TrainingVideo, SupportRequest
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime


# Схемы данных
class UserSchema(BaseModel):
    id: int
    tg_id: int
    first_name: Optional[str]
    username: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)


class ProductSchema(BaseModel):
    id: int
    name: str
    description: Optional[str]
    image_url: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)


class TrainingVideoSchema(BaseModel):
    id: int
    title: str
    youtube_url: str
    description: Optional[str]
    order_index: int
    duration_seconds: Optional[int]
    
    model_config = ConfigDict(from_attributes=True)


class TrainingProgramSchema(BaseModel):
    id: int
    title: str
    description: Optional[str]
    order_index: int
    videos: List[TrainingVideoSchema] = []
    
    model_config = ConfigDict(from_attributes=True)


class SupportRequestSchema(BaseModel):
    id: int
    message: str
    status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Функции для работы с пользователями
async def add_or_get_user(tg_id: int, first_name: str = None, username: str = None):
    """Добавляет нового пользователя или возвращает существующего"""
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            # Обновляем данные пользователя если они изменились
            if first_name and user.first_name != first_name:
                user.first_name = first_name
            if username and user.username != username:
                user.username = username
            await session.commit()
            return user
        
        new_user = User(tg_id=tg_id, first_name=first_name, username=username)
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return new_user


# Функции для работы с продуктами
async def get_product_by_qr(qr_code: str):
    """Получает продукт по QR коду"""
    async with async_session() as session:
        return await session.scalar(select(Product).where(Product.qr_code == qr_code))


async def activate_product_for_user(user_id: int, qr_code: str):
    """Активирует продукт для пользователя по QR коду"""
    async with async_session() as session:
        product = await session.scalar(select(Product).where(Product.qr_code == qr_code))
        if not product:
            return None
            
        # Проверяем, не активирован ли уже этот продукт для пользователя
        existing = await session.scalar(
            select(UserProduct).where(
                UserProduct.user_id == user_id,
                UserProduct.product_id == product.id
            )
        )
        
        if existing:
            return product
            
        user_product = UserProduct(user_id=user_id, product_id=product.id)
        session.add(user_product)
        await session.commit()
        return product


async def get_user_products(user_id: int):
    """Получает все продукты пользователя"""
    async with async_session() as session:
        result = await session.execute(
            select(UserProduct)
            .options(selectinload(UserProduct.product))
            .where(UserProduct.user_id == user_id)
        )
        user_products = result.scalars().all()
        
        products = [
            ProductSchema.model_validate(up.product).model_dump() 
            for up in user_products
        ]
        
        return products


# Функции для работы с тренировочными программами
async def get_training_programs(product_id: int):
    """Получает тренировочные программы для продукта"""
    async with async_session() as session:
        result = await session.execute(
            select(TrainingProgram)
            .options(selectinload(TrainingProgram.videos))
            .where(TrainingProgram.product_id == product_id)
            .order_by(TrainingProgram.order_index)
        )
        programs = result.scalars().all()
        
        serialized_programs = []
        for program in programs:
            program_data = TrainingProgramSchema.model_validate(program).model_dump()
            # Сортируем видео по порядку
            program_data['videos'] = sorted(program_data['videos'], key=lambda x: x['order_index'])
            serialized_programs.append(program_data)
        
        return serialized_programs


async def get_program_videos(program_id: int):
    """Получает видео конкретной программы"""
    async with async_session() as session:
        videos = await session.scalars(
            select(TrainingVideo)
            .where(TrainingVideo.program_id == program_id)
            .order_by(TrainingVideo.order_index)
        )
        
        return [
            TrainingVideoSchema.model_validate(video).model_dump() 
            for video in videos
        ]


# Функции для работы с поддержкой
async def create_support_request(user_id: int, message: str, product_id: int = None):
    """Создает обращение в поддержку"""
    async with async_session() as session:
        support_request = SupportRequest(
            user_id=user_id,
            product_id=product_id,
            message=message
        )
        session.add(support_request)
        await session.commit()
        await session.refresh(support_request)
        return support_request


async def get_user_support_requests(user_id: int):
    """Получает обращения пользователя в поддержку"""
    async with async_session() as session:
        requests = await session.scalars(
            select(SupportRequest)
            .where(SupportRequest.user_id == user_id)
            .order_by(SupportRequest.created_at.desc())
        )
        
        return [
            SupportRequestSchema.model_validate(req).model_dump() 
            for req in requests
        ]


# Административные функции
async def add_product(name: str, qr_code: str, description: str = None, image_url: str = None):
    """Добавляет новый продукт"""
    async with async_session() as session:
        product = Product(
            name=name,
            qr_code=qr_code,
            description=description,
            image_url=image_url
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)
        return product


async def add_training_program(product_id: int, title: str, description: str = None, order_index: int = 0):
    """Добавляет тренировочную программу"""
    async with async_session() as session:
        program = TrainingProgram(
            product_id=product_id,
            title=title,
            description=description,
            order_index=order_index
        )
        session.add(program)
        await session.commit()
        await session.refresh(program)
        return program


async def add_training_video(program_id: int, title: str, youtube_url: str, 
                           description: str = None, order_index: int = 0, duration_seconds: int = None):
    """Добавляет видео к тренировочной программе"""
    async with async_session() as session:
        video = TrainingVideo(
            program_id=program_id,
            title=title,
            youtube_url=youtube_url,
            description=description,
            order_index=order_index,
            duration_seconds=duration_seconds
        )
        session.add(video)
        await session.commit()
        await session.refresh(video)
        return video