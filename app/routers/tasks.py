import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.schemas import AttachmentOut, TaskCreate, TaskOut, TaskUpdate
from app.storage.s3 import S3Disabled, get_s3_client, upload_attachment

router = APIRouter(prefix="/tasks", tags=["tasks"])
log = logging.getLogger(__name__)


def _get_task_or_404(db: Session, task_id: str):
    task = crud.get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    return task


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> TaskOut:
    task = crud.create_task(db, payload)
    log.info("task.created id=%s title=%s", task.id, task.title)
    return TaskOut.model_validate(task)


@router.get("", response_model=list[TaskOut])
def list_tasks(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[TaskOut]:
    return [TaskOut.model_validate(t) for t in crud.list_tasks(db, limit=limit, offset=offset)]


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)) -> TaskOut:
    task = _get_task_or_404(db, task_id)
    return TaskOut.model_validate(task)


@router.put("/{task_id}", response_model=TaskOut)
def update_task(task_id: str, payload: TaskUpdate, db: Session = Depends(get_db)) -> TaskOut:
    task = _get_task_or_404(db, task_id)
    updated = crud.update_task(db, task, payload)
    log.info("task.updated id=%s", updated.id)
    return TaskOut.model_validate(updated)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, db: Session = Depends(get_db)) -> None:
    task = _get_task_or_404(db, task_id)
    crud.delete_task(db, task)
    log.info("task.deleted id=%s", task_id)


@router.post("/{task_id}/attachment", response_model=AttachmentOut)
def upload_task_attachment(
    task_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> AttachmentOut:
    task = _get_task_or_404(db, task_id)
    try:
        client, bucket = get_s3_client()
    except S3Disabled as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

    key = upload_attachment(client, bucket, task_id, file.filename or "attachment", file.file)
    crud.set_attachment_key(db, task, key)
    log.info("task.attachment.uploaded id=%s key=%s", task_id, key)
    return AttachmentOut(task_id=task_id, attachment_key=key)
