from fastapi import HTTPException, status
from sqlalchemy import select, exists
from sqlalchemy.orm import Session

from src.modules.tasks.models import TaskModel
from src.associations_table.associations import task_assignment


def check_task_access(task: TaskModel, user_id: int, db: Session):
    # Task owner
    if task.user_id == user_id:
        return

    # Check whether the user is assigned to this task
    assigned = db.scalar(
        select(
            exists().where(
                task_assignment.c.task_id == task.id,
                task_assignment.c.user_id == user_id,
            )
        )
    )

    if assigned:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You Are Not Authorized To Access This Task",
    )
