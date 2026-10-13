from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from app.models.base import Base


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    template_key = Column(String(100), unique=True, index=True, nullable=False)
    content = Column(Text, nullable=False)
    meta_template_name = Column(String(255), nullable=True)
    language = Column(String(10), default="en", nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<MessageTemplate(id={self.id}, key='{self.template_key}', name='{self.name}')>"
