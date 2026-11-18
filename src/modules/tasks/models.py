from sqlalchemy import String, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from src.modules.tags.models import TagModel

if TYPE_CHECKING:
    from src.modules.categories.models import CategoryModel

from src.modules.core.db import Base
from src.associations_table.associations import task_tags


class TaskModel(Base):
    __tablename__ = "user_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String)

    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)

    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )

    category: Mapped["CategoryModel | None"] = relationship(back_populates="tasks")

    tags: Mapped[list["TagModel"]] = relationship(
        secondary=task_tags, back_populates="tasks"
    )
