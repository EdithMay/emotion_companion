# backend/app/models/db_models.py

from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class Conversation(Base):
    """会话表"""
    __tablename__ = "conversations"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    title:      Mapped[str]      = mapped_column(String(200), default="新对话")
    persona:    Mapped[str]      = mapped_column(String(50),  default="gentle")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联消息（一对多）
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    summaries: Mapped[list["MemorySummary"]] = relationship("MemorySummary", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """消息表"""
    __tablename__ = "messages"

    id:                Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    conversation_id:   Mapped[int]      = mapped_column(Integer, ForeignKey("conversations.id"), index=True)
    role:              Mapped[str]      = mapped_column(String(20))   # "user" 或 "assistant"
    content:           Mapped[str]      = mapped_column(Text)
    created_at:        Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    images: Mapped[list["MessageImage"]] = relationship("MessageImage", back_populates="message", cascade="all, delete-orphan")


class MessageImage(Base):
    """用户消息图片表"""
    __tablename__ = "message_images"

    id:              Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int]      = mapped_column(Integer, ForeignKey("conversations.id"), index=True)
    message_id:      Mapped[int]      = mapped_column(Integer, ForeignKey("messages.id"), index=True)
    file_path:       Mapped[str]      = mapped_column(Text)
    public_url:      Mapped[str]      = mapped_column(Text)
    mime_type:       Mapped[str]      = mapped_column(String(80))
    file_size:       Mapped[int]      = mapped_column(Integer, default=0)
    width:           Mapped[int]      = mapped_column(Integer, default=0)
    height:          Mapped[int]      = mapped_column(Integer, default=0)
    created_at:      Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    message: Mapped["Message"] = relationship("Message", back_populates="images")


class MemorySummary(Base):
    """记忆摘要表（中期记忆）"""
    __tablename__ = "memory_summaries"

    id:                Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    conversation_id:   Mapped[int]      = mapped_column(Integer, ForeignKey("conversations.id"), index=True)
    summary_text:      Mapped[str]      = mapped_column(Text)
    message_count:     Mapped[int]      = mapped_column(Integer, default=0)
    created_at:        Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="summaries")


class MoodEntry(Base):
    """心情小记表"""
    __tablename__ = "mood_entries"

    id:               Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    date:             Mapped[str]      = mapped_column(String(10), unique=True, index=True)  # YYYY-MM-DD
    score:            Mapped[int]      = mapped_column(Integer)          # 1-10
    summary_text:     Mapped[str]      = mapped_column(Text, default="")
    keywords:         Mapped[str]      = mapped_column(Text, default="[]")   # JSON 数组字符串
    conversation_ids: Mapped[str]      = mapped_column(Text, default="[]")   # JSON 数组字符串
    updated_at:       Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class PersonaConfig(Base):
    """人设配置表"""
    __tablename__ = "persona_config"

    id:            Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name:          Mapped[str] = mapped_column(String(50),  unique=True)   # gentle / rational / humorous
    display_name:  Mapped[str] = mapped_column(String(50))
    avatar_emoji:  Mapped[str] = mapped_column(String(10))
    system_prompt: Mapped[str] = mapped_column(Text)
