from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import TaskStatus


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus = TaskStatus.pending


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus | None = None


class TaskOut(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    attachment_key: str | None = None
    created_at: datetime
    updated_at: datetime


class HealthOut(BaseModel):
    status: str
    db: str


class AttachmentOut(BaseModel):
    task_id: str
    attachment_key: str
