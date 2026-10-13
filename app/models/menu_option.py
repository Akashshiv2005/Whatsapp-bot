from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base


class MenuOption(Base):
    __tablename__ = "menu_options"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    parent_state = Column(String(64), nullable=False, index=True)
    label = Column(String(255), nullable=False)
    value = Column(String(100), nullable=False)  # identifier used in button/list ID or matched against text/number
    next_state = Column(String(64), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    active = Column(Boolean, default=True, nullable=False)

    # Relationships
    service = relationship("Service", back_populates="menu_options")

    def __repr__(self):
        return f"<MenuOption(id={self.id}, parent='{self.parent_state}', label='{self.label}', next='{self.next_state}')>"
