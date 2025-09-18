from sqlalchemy import ForeignKey, String, BigInteger, Text, DateTime
from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from datetime import datetime
from typing import List


engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3', echo=True)

async_session = async_sessionmaker(bind=engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id = mapped_column(BigInteger, unique=True)
    first_name: Mapped[str] = mapped_column(String(64), nullable=True)
    username: Mapped[str] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связь с продуктами пользователя
    user_products: Mapped[List["UserProduct"]] = relationship("UserProduct", back_populates="user")


class Product(Base):
    __tablename__ = 'products'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    qr_code: Mapped[str] = mapped_column(String(64), unique=True)
    image_url: Mapped[str] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связи
    training_programs: Mapped[List["TrainingProgram"]] = relationship("TrainingProgram", back_populates="product")
    user_products: Mapped[List["UserProduct"]] = relationship("UserProduct", back_populates="product")


class UserProduct(Base):
    """Связь пользователя с продуктом (когда он отсканировал QR)"""
    __tablename__ = 'user_products'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id', ondelete='CASCADE'))
    activated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Связи
    user: Mapped["User"] = relationship("User", back_populates="user_products")
    product: Mapped["Product"] = relationship("Product", back_populates="user_products")


class TrainingProgram(Base):
    __tablename__ = 'training_programs'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id', ondelete='CASCADE'))
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(default=0)
    
    # Связи
    product: Mapped["Product"] = relationship("Product", back_populates="training_programs")
    videos: Mapped[List["TrainingVideo"]] = relationship("TrainingVideo", back_populates="program")


class TrainingVideo(Base):
    __tablename__ = 'training_videos'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey('training_programs.id', ondelete='CASCADE'))
    title: Mapped[str] = mapped_column(String(128))
    youtube_url: Mapped[str] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(default=0)
    duration_seconds: Mapped[int] = mapped_column(nullable=True)
    
    # Связи
    program: Mapped["TrainingProgram"] = relationship("TrainingProgram", back_populates="videos")


class SupportRequest(Base):
    """Обращения к консультанту"""
    __tablename__ = 'support_requests'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    product_id: Mapped[int] = mapped_column(ForeignKey('products.id', ondelete='CASCADE'), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default='new')  # new, in_progress, resolved
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)