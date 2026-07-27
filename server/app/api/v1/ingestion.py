"""Endpoint de ingestión de documentos de usuario.

Deploy: edge
"""

import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user
from server.app.core.auth import UserInfo
from server.app.core.uploads import UploadKind, validate_upload
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
    # Validación compartida (SEC.6): extensión + magic bytes + corte por tamaño
    # durante la lectura. No se mira content_type: lo fija el cliente.
    validado = await validate_upload(file, kind=UploadKind.PDF)

    import shutil
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        shutil.copyfileobj(validado, tmp)
        tmp_path = tmp.name
    validado.close()

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
