"""Endpoint de ingestión de documentos de usuario.

Deploy: edge
"""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user
from server.app.core.auth import UserInfo
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher
from server.app.modules.agents_hub.services.embedding_service import get_embedding_service

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/user-upload", status_code=status.HTTP_201_CREATED)
async def user_upload(
    chatbot_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
) -> dict:
    """Procesa un PDF subido por el usuario y lo vectoriza como contexto temporal.

    Los chunks creados son visibles únicamente para el usuario que los subió.
    """
    if file.content_type not in ("application/pdf",):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Solo se admiten archivos PDF.",
        )

    import tempfile
    from pathlib import Path

    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        watcher = IngestionWatcher(
            session=session,
            embedding_service=get_embedding_service(),
        )
        chunks = await watcher.process_user_upload(
            source_url=tmp_path,
            chatbot_id=chatbot_id,
            owner_id=uuid.UUID(current_user.user_id),
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {"chunks_created": len(chunks)}
