"""API endpoints for task management."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import logging
from backend.api.schemas import TaskStatusResponse
from backend.models import get_db, Task
from backend.models.schemas import User
from backend.core.security import get_current_user
from backend.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/")
async def list_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List user's tasks (filtered by owner)."""
    try:
        tasks = db.query(Task).filter(
            Task.user_id == current_user.id
        ).order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
        
        task_list = [
            {
                "id": t.id,
                "task_type": t.task_type,
                "status": t.status.value,
                "progress": t.progress,
                "created_at": t.created_at.isoformat()
            }
            for t in tasks
        ]
        
        return {
            "tasks": task_list,
            "total": db.query(Task).filter(Task.user_id == current_user.id).count()
        }
        
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get task status (user must own the task)."""
    try:
        # Check database for task details and ownership
        task = db.query(Task).filter(
            Task.id == task_id,
            Task.user_id == current_user.id
        ).first()
        
        if task:
            # Check Celery task status just in case DB is stale (optional optimization)
            # celery_task = celery_app.AsyncResult(task_id) 
            
            return TaskStatusResponse(
                task_id=task_id,
                status=task.status,
                progress=task.progress,
                result=task.result,
                error=task.error
            )
        else:
            # Task not found or doesn't belong to user
            raise HTTPException(status_code=404, detail="Task not found")
         
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
