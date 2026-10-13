from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    phone_number = Column(String(32), unique=True, index=True, nullable=False)
    whatsapp_user_id = Column(String(64), unique=True, index=True, nullable=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, phone='{self.phone_number}', name='{self.name}')>"
