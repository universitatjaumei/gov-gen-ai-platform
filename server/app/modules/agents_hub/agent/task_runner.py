"""Orquestador de tareas: triangulación RAG + Oracle + evidencias de usuario."""

from typing import Any


class MissingFieldError(Exception):
    """Se lanza cuando falta un campo obligatorio para generar el informe."""

    def __init__(self, missing_fields: list[str]) -> None:
        self.missing_fields = missing_fields
        super().__init__(f"Campos obligatorios faltantes: {', '.join(missing_fields)}")


class TaskRunner:
    """Orquesta la síntesis de datos para generación de informes estructurados."""

    def __init__(self, retriever, embedding_service) -> None:
        self.retriever = retriever
        self.embedding_service = embedding_service

    async def synthesize(
        self,
        oracle_data: dict[str, Any],
        user_evidence: str,
        normativa_context: str,
        required_fields: list[str] | None = None,
    ) -> str:
        """Genera un borrador combinando datos de Oracle, evidencias del usuario y normativa.

        Args:
            oracle_data: Datos numéricos/estructurados del sistema (ej: Oracle ERP)
            user_evidence: Texto justificativo extraído de documentos del usuario
            normativa_context: Contexto normativo recuperado via RAG
            required_fields: Campos obligatorios según la normativa (gap detection)

        Returns:
            Borrador del informe en Markdown

        Raises:
            MissingFieldError: Si faltan campos obligatorios en oracle_data
        """
        if required_fields:
            missing = [f for f in required_fields if f not in oracle_data]
            if missing:
                raise MissingFieldError(missing)

        return await self._generate_draft(
            oracle_data=oracle_data,
            user_evidence=user_evidence,
            normativa_context=normativa_context,
        )

    async def _generate_draft(
        self,
        oracle_data: dict[str, Any],
        user_evidence: str,
        normativa_context: str,
    ) -> str:
        """Genera el borrador del informe en Markdown."""
        data_section = "\n".join(f"- **{k}**: {v}" for k, v in oracle_data.items())

        return (
            "## Informe Generado\n\n"
            f"### Datos del Sistema\n\n{data_section}\n\n"
            f"### Justificación\n\n{user_evidence}\n\n"
            f"### Contexto Normativo\n\n{normativa_context}\n"
        )
