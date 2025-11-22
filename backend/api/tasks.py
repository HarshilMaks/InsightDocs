"""API endpoints for task management."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import logging
from backend.api.schemas import TaskStatusResponse
from backend.models import get_db, Task
from backend.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Get task status.
    
    Args:
        task_id: Task ID
        db: Database session
        
    Returns:
        Task status information
    """
    try:
        # Check Celery task status
        celery_task = celery_app.AsyncResult(task_id)
        
        # Check database for task details
        task = db.query(Task).filter(Task.id == task_id).first()
        
        if task:
            return TaskStatusResponse(
                task_id=task_id,
                status=task.status,
                progress=task.progress,
                result=task.result,
                error=task.error            )
        else:
            # Use Celery state if not in database
            return TaskStatusResponse(
                task_id=task_id,
                status=celery_task.state.lower(),
                progress=0.0,
                result=None,
                error=None
            )
        
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all tasks.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List of tasks
    """
    try:
        tasks = db.query(Task).offset(skip).limit(limit).all()
        
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
            "total": db.query(Task).count()
        }
        
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))
