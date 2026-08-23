"""Owner-scoped Evidence Workspace APIs.

A workspace is an explicit private corpus. It never grants document access: every
membership write verifies that the current user already owns the selected document.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from backend.api.schemas import (
    EvidenceWorkspaceCreate,
    EvidenceWorkspaceListItem,
    EvidenceWorkspaceListResponse,
    EvidenceWorkspaceResponse,
    EvidenceWorkspaceUpdate,
)
from backend.core.security import get_current_user
from backend.models import (
    Document,
    EvidenceWorkspace,
    EvidenceWorkspaceDocument,
    User,
    get_db,
)

router = APIRouter(prefix="/workspaces", tags=["Evidence Workspaces"])


def _workspace_query(db: Session):
    return db.query(EvidenceWorkspace).options(
        selectinload(EvidenceWorkspace.document_memberships).selectinload(
            EvidenceWorkspaceDocument.document
        )
    )


def _owned_workspace(db: Session, workspace_id: str, user_id: str) -> EvidenceWorkspace:
    workspace = (
        _workspace_query(db)
        .filter(EvidenceWorkspace.id == workspace_id, EvidenceWorkspace.user_id == user_id)
        .one_or_none()
    )
    if workspace is None:
        raise HTTPException(status_code=404, detail="Evidence Workspace not found.")
    return workspace


def _normalize_document_ids(document_ids: list[str]) -> list[str]:
    ordered: list[str] = []
    for document_id in document_ids:
        value = document_id.strip()
        if value and value not in ordered:
            ordered.append(value)
    return ordered


def _owned_documents(db: Session, document_ids: list[str], user_id: str) -> list[Document]:
    if not document_ids:
        return []
    documents = (
        db.query(Document)
        .filter(Document.user_id == user_id, Document.id.in_(document_ids))
        .all()
    )
    found = {document.id for document in documents}
    if found != set(document_ids):
        # Do not reveal whether a non-owned identifier exists.
        raise HTTPException(status_code=404, detail="One or more selected documents were not found.")
    return documents


def _list_item(workspace: EvidenceWorkspace) -> EvidenceWorkspaceListItem:
    return EvidenceWorkspaceListItem(
        id=workspace.id,
        name=workspace.name,
        description=workspace.description,
        document_count=len(workspace.document_memberships),
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )


def _detail(workspace: EvidenceWorkspace) -> EvidenceWorkspaceResponse:
    item = _list_item(workspace)
    documents = [
        membership.document
        for membership in sorted(workspace.document_memberships, key=lambda item: item.created_at)
        if membership.document is not None
    ]
    return EvidenceWorkspaceResponse(
        **item.model_dump(),
        documents=documents,
    )


@router.get("", response_model=EvidenceWorkspaceListResponse)
def list_workspaces(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base = _workspace_query(db).filter(EvidenceWorkspace.user_id == current_user.id)
    total = base.count()
    workspaces = (
        base.order_by(EvidenceWorkspace.updated_at.desc(), EvidenceWorkspace.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return EvidenceWorkspaceListResponse(
        workspaces=[_list_item(workspace) for workspace in workspaces], total=total
    )


@router.post("", response_model=EvidenceWorkspaceResponse, status_code=201)
def create_workspace(
    payload: EvidenceWorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Workspace name cannot be blank.")
    document_ids = _normalize_document_ids(payload.document_ids)
    documents = _owned_documents(db, document_ids, current_user.id)

    workspace = EvidenceWorkspace(
        name=name,
        description=payload.description.strip() if payload.description and payload.description.strip() else None,
        user_id=current_user.id,
    )
    db.add(workspace)
    db.flush()
    for document in documents:
        db.add(EvidenceWorkspaceDocument(workspace_id=workspace.id, document_id=document.id))
    db.commit()
    return _detail(_owned_workspace(db, workspace.id, current_user.id))


@router.get("/{workspace_id}", response_model=EvidenceWorkspaceResponse)
def get_workspace(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _detail(_owned_workspace(db, workspace_id, current_user.id))


@router.patch("/{workspace_id}", response_model=EvidenceWorkspaceResponse)
def update_workspace(
    workspace_id: str,
    payload: EvidenceWorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = _owned_workspace(db, workspace_id, current_user.id)
    if "name" in payload.model_fields_set:
        name = (payload.name or "").strip()
        if not name:
            raise HTTPException(status_code=422, detail="Workspace name cannot be blank.")
        workspace.name = name
    if "description" in payload.model_fields_set:
        workspace.description = payload.description.strip() if payload.description and payload.description.strip() else None
    db.commit()
    return _detail(_owned_workspace(db, workspace_id, current_user.id))


@router.delete("/{workspace_id}")
def delete_workspace(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = _owned_workspace(db, workspace_id, current_user.id)
    db.delete(workspace)
    db.commit()
    return {"success": True, "message": "Evidence Workspace deleted."}


@router.put("/{workspace_id}/documents/{document_id}", response_model=EvidenceWorkspaceResponse)
def add_workspace_document(
    workspace_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = _owned_workspace(db, workspace_id, current_user.id)
    _owned_documents(db, [document_id], current_user.id)
    if not any(membership.document_id == document_id for membership in workspace.document_memberships):
        db.add(EvidenceWorkspaceDocument(workspace_id=workspace.id, document_id=document_id))
        workspace.updated_at = datetime.now(timezone.utc)
        db.commit()
    return _detail(_owned_workspace(db, workspace_id, current_user.id))


@router.delete("/{workspace_id}/documents/{document_id}", response_model=EvidenceWorkspaceResponse)
def remove_workspace_document(
    workspace_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = _owned_workspace(db, workspace_id, current_user.id)
    membership = next(
        (item for item in workspace.document_memberships if item.document_id == document_id), None
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Document is not selected in this Evidence Workspace.")
    db.delete(membership)
    workspace.updated_at = datetime.now(timezone.utc)
    db.commit()
    return _detail(_owned_workspace(db, workspace_id, current_user.id))
