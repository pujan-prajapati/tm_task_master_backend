from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped, relationship

from src.modules.core.db import Base

if TYPE_CHECKING:
    from src.modules.tasks.models import TaskModel


class CategoryModel(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))

    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    tasks: Mapped[list["TaskModel"]] = relationship(back_populates="category")

    __table_args__ = (UniqueConstraint("user_id", "name"),)
