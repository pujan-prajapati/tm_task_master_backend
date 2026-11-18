from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from src.modules.comments.dtos import CommentSchema
from src.modules.comments.models import CommentModel
from src.modules.tasks.models import TaskModel

from src.associations_table.associations import task_assignment
from src.modules.auth_service import auth_client

from src.modules.notifications.controllers import create_notification
from src.utils.helpers import success_response
from src.modules.tasks.helpers import check_task_access

from src.websocket.manager import manager

from src.jobs.queue import email_queue, email_retry
from src.jobs.email_jobs import send_email_job


# =================== CREATE COMMENT =========================
async def create_comment(
    body: CommentSchema,
    task_id: int,
    db: Session,
    user_id: int,
):
    task = db.get(TaskModel, task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    check_task_access(task, user_id, db)

    new_comment = CommentModel(
        content=body.content,
        task_id=task_id,
        user_id=user_id,
    )

    db.add(new_comment)

    # Collect notification recipients
    recipients = set()

    # Add task owner
    if task.user_id != user_id:
        recipients.add(task.user_id)

    # Get assigned user IDs from the association table
    assigned_user_ids = db.scalars(
        select(task_assignment.c.user_id).where(task_assignment.c.task_id == task.id)
    ).all()

    for assigned_user_id in assigned_user_ids:
        if assigned_user_id != user_id:
            recipients.add(assigned_user_id)

    # Fetch recipient details from Node.js Auth service
    recipient_profiles = []

    for recipient_id in recipients:
        user_response = await auth_client.get_user_by_id(recipient_id)
        recipient_profiles.append(user_response["data"])

        create_notification(
            message=f"New comment on task: {task.title}",
            user_id=recipient_id,
            db=db,
        )

    db.commit()
    db.refresh(new_comment)

    # Send external notifications after the database commit
    for recipient in recipient_profiles:
        await manager.send_to_user(
            user_id=recipient["id"],
            message={
                "type": "comment_added",
                "message": f"New comment on task: {task.title}",
                "task_id": task.id,
            },
        )

        email_queue.enqueue(
            send_email_job,
            emails=[recipient["email"]],
            subject="New Comment On Your Task",
            html=f"""
                <h2>New Comment</h2>
                <p>Hi {recipient["name"]},</p>
                <p><strong>{task.title}</strong></p>
                <p><strong>Comment:</strong></p>
                <p>{new_comment.content}</p>
                <p>Please login to TaskMaster to view the task.</p>
            """,
            retry=email_retry,
        )

    return success_response(
        data=new_comment,
        message="Comment Created Successfully",
    )


# ================ GET TASK COMMENTS ============================
def get_task_comments(task_id: int, db: Session, user_id: int):
    task = db.get(TaskModel, task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task Not Found"
        )

    check_task_access(task, user_id, db)

    query = (
        select(CommentModel)
        .where(CommentModel.task_id == task_id)
        .order_by(CommentModel.id.asc())
    )
    comments = db.scalars(query).all()

    return success_response(data=comments, message="Comments Fetched Successfully")


# ================ UPDATE COMMENTS ============================
def update_comment(
    task_id: int, comment_id: int, body: CommentSchema, db: Session, user_id: int
):
    task = db.get(TaskModel, task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tas Not Found"
        )

    check_task_access(task, user_id, db)

    comment = db.get(CommentModel, comment_id)

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Comment Not Found"
        )

    if comment.task_id != task.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment Does Not Belog To This Task",
        )

    if comment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You Can Only Update Your Own Comment",
        )

    comment.content = body.content

    db.commit()
    db.refresh(comment)

    return success_response(data=comment, message="Comment Updated Successfully")


# ================ DELETE COMMENTS ============================
def delete_comment(task_id: int, comment_id: int, db: Session, user_id: int):
    task = db.get(TaskModel, task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tas Not Found"
        )

    check_task_access(task, user_id, db)

    comment = db.get(CommentModel, comment_id)

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Comment Not Found"
        )

    if comment.task_id != task.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment Does Not Belog To This Task",
        )

    if comment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You Can Only Delete Your Own Comment",
        )

    db.delete(comment)
    db.commit()

    return success_response(data=None, message="Comment Deleted Successfully")
