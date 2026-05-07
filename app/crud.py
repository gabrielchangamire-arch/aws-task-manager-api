from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Task
from app.schemas import TaskCreate, TaskUpdate


def create_task(db: Session, payload: TaskCreate) -> Task:
    task = Task(title=payload.title, description=payload.description, status=payload.status)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_tasks(db: Session, limit: int = 100, offset: int = 0) -> list[Task]:
    stmt = select(Task).order_by(Task.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def get_task(db: Session, task_id: str) -> Task | None:
    return db.get(Task, task_id)


def update_task(db: Session, task: Task, payload: TaskUpdate) -> Task:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task: Task) -> None:
    db.delete(task)
    db.commit()


def set_attachment_key(db: Session, task: Task, key: str) -> Task:
    task.attachment_key = key
    db.commit()
    db.refresh(task)
    return task
