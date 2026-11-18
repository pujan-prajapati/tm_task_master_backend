import math

from fastapi import HTTPException, status

from sqlalchemy import insert, delete, or_, asc, desc, select, func
from sqlalchemy.orm import Session, selectinload

from src.modules.tags.models import TagModel
from src.modules.categories.models import CategoryModel
from src.modules.tasks.models import TaskModel

from src.associations_table.associations import task_assignment

from src.modules.tasks.dtos import (
    TaskSchema,
    AddTagSchema,
    TaskStatus,
    TaskPriority,
    AssignTaskSchema,
    TaskResponseSchema,
)

from src.modules.notifications.controllers import create_notification
from src.modules.tasks.helpers import check_task_access
from src.utils.helpers import success_response
from src.utils.mail import send_email

from src.modules.auth_service import auth_client

from src.websocket.manager import manager

from src.utils.redis import get_cache, set_cache, delete_user_task_cache
from src.jobs.email_jobs import send_email_job
from src.jobs.queue import email_queue, email_retry


# =========== CREATE TASK =======================
def create_task(body: TaskSchema, db: Session, user_id: int):
    if body.category_id is not None:
        category = db.get(CategoryModel, body.category_id)

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category Id {body.category_id} not found",
            )

        if category.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to use this category",
            )

    new_task = TaskModel(
        title=body.title,
        description=body.description,
        priority=body.priority,
        status=body.status,
        user_id=user_id,
        category_id=body.category_id,
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    delete_user_task_cache(user_id)

    return success_response(new_task, "Task Created Successfully")


# ============== GET ALL TASKS =============================
def get_all_tasks(
    db: Session,
    user_id: int,
    search: str | None = None,
    sort_by: str = "id",
    order: str = "asc",
    page: int = 1,
    limit: int = 10,
    tag_ids: list[int] | None = None,
    priority: TaskPriority | None = None,
    status: TaskStatus | None = None,
    category_id: int | None = None,
):
    can_cache = not any([search, tag_ids, priority, status, category_id])

    cache_key = (
        f"tasks:user:{user_id}:"
        f"page:{page}:limit:{limit}:"
        f"sort:{sort_by}:order{order}"
    )

    if can_cache:
        cached_data = get_cache(cache_key)

        if cached_data is not None:
            return success_response(cached_data, "Tasks fetched successfully")

    query = (
        select(TaskModel)
        .options(selectinload(TaskModel.tags))
        .where(
            or_(
                TaskModel.user_id == user_id,
                TaskModel.id.in_(
                    select(task_assignment.c.task_id).where(
                        task_assignment.c.user_id == user_id
                    )
                ),
            )
        )
    )

    # search --------------
    if search:
        query = query.where(
            or_(
                TaskModel.title.ilike(f"%{search}%"),
                TaskModel.description.ilike(f"%{search}%"),
            )
        )

    # status --------------
    if status:
        query = query.where(TaskModel.status == status)

    # priority --------------
    if priority:
        query = query.where(TaskModel.priority == priority)

    # category id --------------
    if category_id:
        query = query.where(TaskModel.category_id == category_id)

    # tag id ------------------
    if tag_ids:
        query = (
            query.join(TaskModel.tags)
            .where(TagModel.id.in_(tag_ids))
            .group_by(TaskModel.id)
            .having(func.count(TagModel.id) == len(tag_ids))
        )

    # total tasks
    total = db.scalar(select(func.count()).select_from(query.subquery()))

    # sorting and ordering --------------
    allowed_sort_fields = {
        "id": TaskModel.id,
        "title": TaskModel.title,
        "priority": TaskModel.priority,
        "status": TaskModel.status,
    }

    sort_column = allowed_sort_fields.get(sort_by, TaskModel.id)

    if order.lower() == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # pagination ---------------
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    tasks = db.scalars(query).all()

    task_items = [
        TaskResponseSchema.model_validate(task).model_dump() for task in tasks
    ]

    # Total pages -----------------
    total_pages = math.ceil(total / limit)

    response_data = {
        "items": task_items,
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
    }

    if can_cache:
        set_cache(cache_key, response_data, expire=60)

    return success_response(
        response_data,
        "Tasks Fetched Successfully",
    )


# ============== GET ONE TASK ===============================
def get_one_task(task_id: int, db: Session, user_id: int):
    task = db.get(TaskModel, task_id)

    if not task:
        raise HTTPException(404, detail="Task not found")

    check_task_access(task, user_id, db)

    return success_response(task, "Task fetched successfully")


# ============== UPDATE TASK ============================
def update_task(body: TaskSchema, task_id: int, db: Session, user_id: int):
    task = db.get(TaskModel, task_id)

    if not task:
        raise HTTPException(404, detail="Task not found")

    check_task_access(task, user_id, db)

    if body.category_id is not None:
        category = db.get(CategoryModel, body.category_id)

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category Id {body.category_id} not found",
            )

        if category.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to use this category",
            )

    task.title = body.title
    task.description = body.description
    task.priority = body.priority
    task.status = body.status
    task.category_id = body.category_id

    db.commit()
    db.refresh(task)

    delete_user_task_cache(user_id)

    return success_response(task, "Task updated successfully")


# ====================== DELETE TASK ================================
def delete_task(task_id: int, db: Session, user_id: int):
    task = db.get(TaskModel, task_id)

    if not task:
        raise HTTPException(404, detail=f"Task Id {task_id} not found")

    if task.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized"
        )

    db.delete(task)
    db.commit()

    delete_user_task_cache(user_id)

    return success_response(None, "Task Deleted Successfully")


# ====================== ADD TAGS TO TASK ==========================
def add_tags_to_task(task_id: int, body: AddTagSchema, db: Session, user_id: int):
    task = db.get(TaskModel, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task Id {task_id} not found"
        )

    check_task_access(task, user_id, db)

    for tag_id in body.tag_ids:
        tag = db.get(TagModel, tag_id)

        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tag Id {tag_id} not found",
            )

        if tag in task.tags:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Tag Already Exists"
            )

        task.tags.append(tag)

    db.commit()

    db.refresh(task)

    return success_response(task, "Tags added successfully")


# ================ DELETE TAG FROM TASK ================================
def delete_tag_from_task(task_id: int, tag_id: int, db: Session, user_id: int):
    task = db.get(TaskModel, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task Not Found"
        )

    check_task_access(task, user_id, db)

    tag = db.get(TagModel, tag_id)

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task Not Found"
        )

    if tag not in task.tags:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag is not attached to this task",
        )

    task.tags.remove(tag)

    db.commit()

    return success_response(None, "Tag removed successfully")


# ======================= ASSIGN TASKS ===================================
async def assign_task(
    task_id: int,
    body: AssignTaskSchema,
    db: Session,
    user_id: int,
):
    task = db.get(TaskModel, task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task Not Found"
        )

    if task.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only The Task Owner Can Assign Users",
        )

    user_response = await auth_client.get_user_by_id(body.user_id)
    assigned_user = user_response["data"]

    if not assigned_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User Id Not Found"
        )

    if assigned_user["id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You Cannot Assign Youself To Your Own Task",
        )

    existing_assignment = db.execute(
        select(task_assignment.c.user_id).where(
            task_assignment.c.task_id == task.id,
            task_assignment.c.user_id == assigned_user["id"],
        )
    ).first()

    if existing_assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User Is Already Assigned To This Task",
        )

    db.execute(
        insert(task_assignment).values(
            task_id=task.id,
            user_id=assigned_user["id"],
        )
    )

    # Database notification
    create_notification(
        message=f"You were assigned to task: {task.title}",
        user_id=assigned_user["id"],
        db=db,
    )

    db.commit()

    # websocket notification
    await manager.send_to_user(
        user_id=assigned_user["id"],
        message={
            "type": "task_assigned",
            "message": f"You were assigned to task: {task.title}",
            "task_id": task.id,
        },
    )

    # Email notification
    email_queue.enqueue(
        send_email_job,
        emails=[assigned_user["email"]],
        subject="You Were Assigned To A Task",
        html=f"""
            <h2>Task Assigned</h2>
            <p>Hi {assigned_user["name"]},</p>
            <p><strong>{task.title}</strong></p>
            <p>Please login to TaskMaster to view the task.</p>
        """,
        retry=email_retry,
    )

    delete_user_task_cache(task.user_id)
    delete_user_task_cache(assigned_user["id"])

    return success_response(None, "Task assigned successfully")


# ============================ GET TASK ASSIGNEES ==========================
async def get_task_assignees(task_id: int, db: Session, user_id: int):
    task = db.get(TaskModel, task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task Id Not Found",
        )

    if task.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You Are Not Authorized",
        )

    assigned_user_ids = db.scalars(
        select(task_assignment.c.user_id).where(task_assignment.c.task_id == task.id)
    ).all()

    assignees = []

    for assigned_user_id in assigned_user_ids:
        user_response = await auth_client.get_user_by_id(assigned_user_id)
        assignees.append(user_response["data"])

    return success_response(
        assignees,
        "Task Assignees Fetched Successfully",
    )


# ================== REMOVE TASK ASSIGNEE =============================
def remove_task_assignee(
    task_id: int,
    user_id: int,
    db: Session,
    current_user_id: int,
):
    task = db.get(TaskModel, task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task Id Not Found",
        )

    if task.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only The Task Owner Can Remove Users",
        )

    existing_assignment = db.execute(
        select(task_assignment.c.user_id).where(
            task_assignment.c.task_id == task.id,
            task_assignment.c.user_id == user_id,
        )
    ).first()

    if not existing_assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User Is Not Assigned To This Task",
        )

    db.execute(
        delete(task_assignment).where(
            task_assignment.c.task_id == task.id,
            task_assignment.c.user_id == user_id,
        )
    )

    db.commit()

    delete_user_task_cache(task.user_id)
    delete_user_task_cache(user_id)

    return success_response(None, "User Removed From Task Successfully")
