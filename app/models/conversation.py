from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, JSON, func
from sqlalchemy.orm import relationship
from app.models.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    state = Column(String(64), default="MAIN_MENU", nullable=False, index=True)
    previous_state = Column(String(64), nullable=True)
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)  # ACTIVE, HUMAN_HANDOFF, CLOSED
    session_data = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    leads = relationship("Lead", back_populates="conversation")

    def __repr__(self):
        return f"<Conversation(id={self.id}, user_id={self.user_id}, state='{self.state}', status='{self.status}')>"
