from sqlalchemy import Boolean, Column, DateTime, Integer, String, JSON, func
from app.models.base import Base


class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    trigger_type = Column(String(64), nullable=False)  # KEYWORD, STATUS_CHANGE, TIME_INACTIVITY
    trigger_value = Column(String(255), nullable=False)
    action_type = Column(String(64), nullable=False)  # SEND_MESSAGE, NOTIFY_ADMIN, CHANGE_STATE
    action_config = Column(JSON, default=dict, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<AutomationRule(id={self.id}, name='{self.name}', trigger='{self.trigger_type}')>"
