from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship
from app.models.base import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone_number = Column(String(32), nullable=False, index=True)
    business_type = Column(String(255), nullable=True)
    requirement = Column(Text, nullable=True)
    budget = Column(String(100), nullable=True)
    timeline = Column(String(100), nullable=True)
    preferred_contact_time = Column(String(100), nullable=True)
    estimated_amount = Column(String(100), nullable=True)
    status = Column(String(32), default="NEW", nullable=False, index=True)  # NEW, CONTACTED, QUALIFIED, IN_PROGRESS, CONVERTED, LOST, CLOSED
    source = Column(String(64), default="WHATSAPP_BOT", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="leads")
    service = relationship("Service", back_populates="leads")
    conversation = relationship("Conversation", back_populates="leads")

    def __repr__(self):
        return f"<Lead(id={self.id}, name='{self.name}', phone='{self.phone_number}', status='{self.status}')>"
