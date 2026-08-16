"""Cola de validación de vigencia (A7).

El asistente ya **advierte** cuando cita un documento cuya vigencia nadie ha comprobado
(VIS.3). Advertir es lo correcto, pero no cierra nada: el aviso se repite indefinidamente
porque no hay ninguna pantalla donde ver *cuáles* son esos documentos ni cuántos quedan.

Este endpoint es esa lista. El criterio de quién entra en ella es exactamente el mismo que
usa la capa de recuperación para decidir el aviso —`vigencia_no_validada`—, y eso no es un
detalle: si la pantalla usara un criterio propio, el número de la pantalla y el número de
documentos que provocan aviso divergirían sin que se note.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import server.app.main  # noqa: F401  (fija el orden de carga; ver test_corpus_upload_contract)
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.routers.hub_ingestion_router import router as ingestion_router

ORG = "00000000-0000-0000-0000-00000000dead"
CHATBOT = str(uuid.uuid4())

_JWT_ENV = {
    "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-characters-long",
    "JWT_ALGORITHM": "HS256",
    "JWT_EXPIRATION_MINUTES": "60",
}


def _token() -> str:
    import os

    os.environ.update(_JWT_ENV)
    from server.app.core.auth import UserInfo, create_token

    return create_token(
        UserInfo(
            user_id="admin-1",
            email="admin@test.com",
            role="admin",
            organizacion_ids=(ORG,),
        )
    )


def _doc(**campos):
    base = dict(
        id=uuid.uuid4(),
        title="Reglament de prova",
        language="va",
        canonical_url="https://www.uji.es/reg.pdf",
        id_publicacio="REG-999",
        estat_vigencia="vigent",
        vigencia_validada_el=None,
        data_revisio_prevista=None,
        revisat_per=None,
    )
    base.update(campos)
    return SimpleNamespace(**base)


def _consultar(pendientes, total=297):
    """Monta la app con una sesión que devuelve `pendientes` y un total conocido."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    session = AsyncMock()
    chatbot = MagicMock()
    chatbot.organizacion_id = uuid.UUID(ORG)
    session.get = AsyncMock(return_value=chatbot)
    session.scalar = AsyncMock(return_value=total)

    resultado = MagicMock()
    resultado.scalars.return_value.all.return_value = pendientes
    session.execute = AsyncMock(return_value=resultado)

    async def _sesion():
        yield session

    app = FastAPI()
    app.dependency_overrides[get_async_session] = _sesion
    app.include_router(ingestion_router, prefix="/api/v1")

    with TestClient(app, raise_server_exceptions=False) as cliente:
        return cliente.get(
            f"/api/v1/hub/ingestion/{CHATBOT}/vigencia",
            headers={"Authorization": f"Bearer {_token()}"},
        )


class TestColaDeVigencia:

    def test_should_list_the_documents_whose_vigencia_is_not_validated(self):
        respuesta = _consultar([_doc(title="Reglament sense validar")])

        assert respuesta.status_code == 200, respuesta.text
        cuerpo = respuesta.json()
        assert [d["title"] for d in cuerpo["documents"]] == ["Reglament sense validar"]

    def test_should_report_how_many_are_pending_against_the_whole_corpus(self):
        """Sin el total, «50 pendientes» no dice si el corpus está bien o fatal."""
        respuesta = _consultar([_doc(), _doc(), _doc()], total=297)

        cuerpo = respuesta.json()
        assert cuerpo["pendents"] == 3
        assert cuerpo["total"] == 297

    def test_should_say_why_each_document_is_pending(self):
        """Los dos motivos piden trabajo distinto: uno es revisar, el otro es retirar o
        marcar. Calcularlo en el cliente sería duplicar la regla de `vigencia_no_validada`."""
        sin_validar, derogado = _consultar(
            [
                _doc(vigencia_validada_el=None, estat_vigencia="vigent"),
                _doc(
                    vigencia_validada_el=datetime(2026, 1, 1, tzinfo=timezone.utc),
                    estat_vigencia="derogat",
                ),
            ]
        ).json()["documents"]

        assert sin_validar["motiu"] == "sense_validar"
        assert derogado["motiu"] == "estat_no_vigent"

    def test_should_let_the_state_win_over_the_missing_validation(self):
        """Un documento derogado que además nadie validó pide **retirarlo**, no revisarlo.
        Si cayera en el montón de «sólo hay que mirarlo», es donde se queda sin hacer."""
        documento = _consultar(
            [_doc(vigencia_validada_el=None, estat_vigencia="derogat")]
        ).json()["documents"][0]

        assert documento["motiu"] == "estat_no_vigent"

    def test_should_carry_the_data_needed_to_go_and_check_it(self):
        """Quien valide necesita abrir la norma y saber cuándo tocaba revisarla."""
        respuesta = _consultar(
            [
                _doc(
                    id_publicacio="REG-042",
                    canonical_url="https://www.uji.es/reg-042.pdf",
                    data_revisio_prevista=date(2026, 3, 1),
                )
            ]
        )

        documento = respuesta.json()["documents"][0]
        assert documento["id_publicacio"] == "REG-042"
        assert documento["canonical_url"] == "https://www.uji.es/reg-042.pdf"
        assert documento["data_revisio_prevista"] == "2026-03-01"

    def test_should_return_an_empty_list_when_the_corpus_is_fully_validated(self):
        respuesta = _consultar([])

        cuerpo = respuesta.json()
        assert cuerpo["documents"] == []
        assert cuerpo["pendents"] == 0

    def test_should_refuse_a_chatbot_of_another_organization(self):
        """Los títulos del corpus de otra organización no son públicos."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        session = AsyncMock()
        ajeno = MagicMock()
        ajeno.organizacion_id = uuid.uuid4()
        session.get = AsyncMock(return_value=ajeno)

        async def _sesion():
            yield session

        app = FastAPI()
        app.dependency_overrides[get_async_session] = _sesion
        app.include_router(ingestion_router, prefix="/api/v1")

        with TestClient(app, raise_server_exceptions=False) as cliente:
            respuesta = cliente.get(
                f"/api/v1/hub/ingestion/{CHATBOT}/vigencia",
                headers={"Authorization": f"Bearer {_token()}"},
            )

        assert respuesta.status_code == 403, respuesta.text
