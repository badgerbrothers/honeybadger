"""Project to global RAG binding APIs."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import Project
from app.models.rag_collection import RagCollection
from app.schemas.project_rag import ProjectRagBindingResponse, ProjectRagBindingUpdate
from app.security.auth import CurrentUser, get_current_user

router = APIRouter(prefix="/api/projects", tags=["project_rag"])


async def _get_owned_project_or_404(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession,
) -> Project:
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_user_id == user.id,
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_id}/rag", response_model=ProjectRagBindingResponse)
async def get_project_rag(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    project = await _get_owned_project_or_404(project_id=project_id, user=user, db=db)
    return ProjectRagBindingResponse(
        project_id=project.id,
        rag_collection_id=project.active_rag_collection_id,
        updated_at=project.updated_at,
    )


@router.put("/{project_id}/rag", response_model=ProjectRagBindingResponse)
async def put_project_rag(
    project_id: uuid.UUID,
    payload: ProjectRagBindingUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    project = await _get_owned_project_or_404(project_id=project_id, user=user, db=db)

    rag_id = payload.rag_collection_id
    if rag_id is not None:
        rag_result = await db.execute(
            select(RagCollection).where(
                RagCollection.id == rag_id,
                RagCollection.owner_user_id == user.id,
            )
        )
        if rag_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="RAG collection not found")

    project.active_rag_collection_id = rag_id
    await db.commit()
    await db.refresh(project)

    return ProjectRagBindingResponse(
        project_id=project.id,
        rag_collection_id=project.active_rag_collection_id,
        updated_at=project.updated_at,
    )
