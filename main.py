from fastapi import FastAPI
from fastapi.exceptions import HTTPException

from src.modules.core.db import Base, engine
from src.modules.tasks.routers import task_routes
from src.modules.tags.routers import tag_routes
from src.modules.categories.routers import category_routes
from src.modules.comments.routers import comment_routes
from src.modules.notifications.routers import notification_routes
from src.modules.auth_service.routers import router as auth_router

from src.websocket.routers import websocket_routes
from src.utils.exceptions import http_exception_handler

# Base.metadata.create_all(engine)

app = FastAPI(title="This is my Task Management Application")

# custom exception handler
app.add_exception_handler(HTTPException, http_exception_handler)

# routers -----------------------------------
app.include_router(task_routes)
app.include_router(tag_routes)
app.include_router(category_routes)
app.include_router(comment_routes)
app.include_router(notification_routes)
app.include_router(websocket_routes)
app.include_router(auth_router)
