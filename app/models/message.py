from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON, func
from sqlalchemy.orm import relationship
from app.models.base import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    whatsapp_message_id = Column(String(128), unique=True, index=True, nullable=True)  # Used for Idempotency
    direction = Column(String(16), nullable=False)  # INBOUND, OUTBOUND
    message_type = Column(String(32), default="text", nullable=False)  # text, interactive_button, interactive_list, location, image, template
    message_text = Column(Text, nullable=True)
    media_url = Column(String(512), nullable=True)
    status = Column(String(32), default="SENT", nullable=False)  # RECEIVED, SENT, DELIVERED, READ, FAILED
    raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, conv_id={self.conversation_id}, dir='{self.direction}', type='{self.message_type}')>"
