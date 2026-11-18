from sqlalchemy import Table, Column, ForeignKey, Integer
from src.modules.core.db import Base

# task and tag association table
task_tags = Table(
    "task_tags",
    Base.metadata,
    Column(
        "task_id", ForeignKey("user_tasks.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


# external user and task assignment table
task_assignment = Table(
    "task_assignments",
    Base.metadata,
    Column(
        "task_id", ForeignKey("user_tasks.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("user_id", Integer, primary_key=True),
)
