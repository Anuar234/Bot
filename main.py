from contextlib import asynccontextmanager
from typing import Optional

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import init_db
import requests as rq


# Модели запросов
class ScanQRRequest(BaseModel):
    tg_id: int
    qr_code: str
    first_name: Optional[str] = None
    username: Optional[str] = None


class SupportRequest(BaseModel):
    tg_id: int
    message: str
    product_id: Optional[int] = None


@asynccontextmanager
async def lifespan(app_: FastAPI):
    await init_db()
    print('Trainer Bot API is ready')
    yield


app = FastAPI(title="Trainer Mini App API", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Trainer Mini App API"}


# Эндпоинты для главного меню
@app.get("/api/user/{tg_id}")
async def get_user_info(tg_id: int):
    """Получает информацию о пользователе и его продуктах"""
    user = await rq.add_or_get_user(tg_id)
    products = await rq.get_user_products(user.id)
    
    return {
        'user': {
            'id': user.id,
            'tg_id': user.tg_id,
            'first_name': user.first_name,
            'username': user.username
        },
        'products': products
    }


@app.post("/api/scan-qr")
async def scan_qr_code(request: ScanQRRequest):
    """Сканирует QR код и активирует продукт для пользователя"""
    user = await rq.add_or_get_user(request.tg_id, request.first_name, request.username)
    
    product = await rq.activate_product_for_user(user.id, request.qr_code)
    
    if not product:
        raise HTTPException(status_code=404, detail="QR код не найден")
    
    return {
        'status': 'success',
        'product': {
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'image_url': product.image_url
        }
    }


# Эндпоинты для работы с продуктами
@app.get("/api/product/{product_id}")
async def get_product_details(product_id: int, tg_id: int):
    """Получает детальную информацию о продукте"""
    user = await rq.add_or_get_user(tg_id)
    
    # Проверяем, есть ли у пользователя доступ к этому продукту
    user_products = await rq.get_user_products(user.id)
    product_ids = [p['id'] for p in user_products]
    
    if product_id not in product_ids:
        raise HTTPException(status_code=403, detail="Нет доступа к этому продукту")
    
    product = next((p for p in user_products if p['id'] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Продукт не найден")
    
    return product


# Эндпоинты для тренировочных программ
@app.get("/api/training-programs/{product_id}")
async def get_training_programs(product_id: int, tg_id: int):
    """Получает тренировочные программы для продукта"""
    user = await rq.add_or_get_user(tg_id)
    
    # Проверяем доступ к продукту
    user_products = await rq.get_user_products(user.id)
    product_ids = [p['id'] for p in user_products]
    
    if product_id not in product_ids:
        raise HTTPException(status_code=403, detail="Нет доступа к этому продукту")
    
    programs = await rq.get_training_programs(product_id)
    
    return {
        'product_id': product_id,
        'programs': programs
    }


@app.get("/api/training-videos/{program_id}")
async def get_training_videos(program_id: int, tg_id: int):
    """Получает видео тренировочной программы"""
    # Здесь можно добавить дополнительную проверку доступа через связи
    videos = await rq.get_program_videos(program_id)
    
    return {
        'program_id': program_id,
        'videos': videos
    }


# Эндпоинты для поддержки
@app.post("/api/support")
async def create_support_request(request: SupportRequest):
    """Создает обращение в поддержку"""
    user = await rq.add_or_get_user(request.tg_id)
    
    support_request = await rq.create_support_request(
        user.id, 
        request.message, 
        request.product_id
    )
    
    return {
        'status': 'success',
        'request_id': support_request.id,
        'message': 'Ваше обращение принято. Консультант свяжется с вами в ближайшее время.'
    }


@app.get("/api/support/{tg_id}")
async def get_support_requests(tg_id: int):
    """Получает историю обращений пользователя"""
    user = await rq.add_or_get_user(tg_id)
    requests = await rq.get_user_support_requests(user.id)
    
    return {
        'requests': requests
    }


# Административные эндпоинты (для управления контентом)
@app.post("/api/admin/product")
async def admin_add_product(name: str, qr_code: str, description: str = None, image_url: str = None):
    """Добавляет новый продукт (админка)"""
    product = await rq.add_product(name, qr_code, description, image_url)
    return {'status': 'success', 'product_id': product.id}


@app.post("/api/admin/training-program")
async def admin_add_program(product_id: int, title: str, description: str = None, order_index: int = 0):
    """Добавляет тренировочную программу (админка)"""
    program = await rq.add_training_program(product_id, title, description, order_index)
    return {'status': 'success', 'program_id': program.id}


@app.post("/api/admin/training-video")
async def admin_add_video(program_id: int, title: str, youtube_url: str, 
                         description: str = None, order_index: int = 0, 
                         duration_seconds: int = None):
    """Добавляет видео к программе (админка)"""
    video = await rq.add_training_video(
        program_id, title, youtube_url, description, order_index, duration_seconds
    )
    return {'status': 'success', 'video_id': video.id}