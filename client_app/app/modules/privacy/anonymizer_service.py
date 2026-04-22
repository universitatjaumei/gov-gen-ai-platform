# client_app/app/modules/privacy/anonymizer_service.py
"""
Servicio de alto nivel para aplicar politicas de anonimizacion a archivos.
"""
from pydantic import BaseModel
from typing import List, Literal, Optional
from pathlib import Path
import pandas as pd
from .anonymizer import AnonymizationContext
from client_app.app.modules.security.encryption_service import EncryptionService

Strategy = Literal[
    "NER_PERSON->INITIALS",
    "NER_PERSON->FAKE_NAME",
    "DNI->CODE",
    "DNI->MASK_LAST4",
    "EMAIL->TOKEN",
    "EMAIL->FAKE"
]


class AnonymizerPolicy(BaseModel):
    """Politica de anonimizacion aplicable a datasets."""
    strategies: List[Strategy]
    locale: str = "es_ES"


class AnonymizerService:
    """
    Servicio de alto nivel para anonimizacion de archivos estructurados.

    Features:
    - Aplica politicas granulares (INITIALS, MASK, TOKEN, FAKE)
    - Persiste mapa de anonimizacion cifrado
    - Soporta Excel (.xlsx) y CSV
    - Integracion con ValidationLoop para errores
    """

    def __init__(self, encryption_service: Optional[EncryptionService] = None):
        """
        Inicializa el servicio.

        Args:
            encryption_service: Servicio de cifrado (se crea uno por defecto)
        """
        self.encryption_service = encryption_service or EncryptionService()

    def apply(
        self,
        input_path: Path,
        output_path: Path,
        map_path: Path,
        policy: AnonymizerPolicy
    ):
        """
        Aplica politica de anonimizacion a un archivo.

        Args:
            input_path: Archivo original (.xlsx o .csv)
            output_path: Archivo anonimizado de salida
            map_path: Ruta para guardar el mapa cifrado
            policy: Politica de anonimizacion a aplicar
        """
        # Cargar datos
        if str(input_path).lower().endswith(".csv"):
            df = pd.read_csv(input_path)
        else:
            df = pd.read_excel(input_path, engine="openpyxl")

        # Crear contexto de anonimizacion
        ctx = AnonymizationContext(
            locale=policy.locale,
            encryption_service=self.encryption_service
        )

        # Intentar cargar mapa existente (para append)
        if map_path.exists():
            ctx.load_state(map_path)

        # Aplicar estrategias columna por columna
        for col in df.columns:
            # Convertir a string manejando NaN
            series = df[col].fillna('').astype(str)

            for strategy in policy.strategies:
                if strategy == "NER_PERSON->INITIALS":
                    series = series.apply(
                        lambda x: self._to_initials(x, ctx) if x.strip() else x
                    )

                elif strategy == "NER_PERSON->FAKE_NAME":
                    series = series.apply(
                        lambda x: ctx.anonymize(x) if x.strip() else x
                    )

                elif strategy == "EMAIL->TOKEN":
                    series = series.str.replace(
                        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
                        "EMAIL_TOKEN",
                        regex=True
                    )

                elif strategy == "EMAIL->FAKE":
                    series = series.apply(
                        lambda x: ctx.anonymize(x) if x.strip() and '@' in x else x
                    )

                elif strategy == "DNI->MASK_LAST4":
                    series = series.str.replace(
                        r"\b(\d{4})\d{4}([A-Z])\b",
                        r"\1****\2",
                        regex=True
                    )

                elif strategy == "DNI->CODE":
                    series = series.str.replace(
                        r"\b\d{8}[A-Z]\b",
                        "DNI_CODE",
                        regex=True
                    )

            df[col] = series

        # Guardar archivo anonimizado
        if str(output_path).lower().endswith(".csv"):
            df.to_csv(output_path, index=False)
        else:
            df.to_excel(output_path, index=False, engine="openpyxl")

        # Persistir mapa cifrado
        ctx.save_state(map_path)

    def deanonymize(
        self,
        anonymized_path: Path,
        output_path: Path,
        map_path: Path
    ):
        """
        Desanonimiza un archivo usando el mapa guardado.

        Args:
            anonymized_path: Archivo anonimizado
            output_path: Archivo con datos originales restaurados
            map_path: Ruta del mapa de anonimizacion cifrado
        """
        # Cargar contexto con mapa
        ctx = AnonymizationContext(encryption_service=self.encryption_service)
        ctx.load_state(map_path)

        # Cargar datos
        if str(anonymized_path).lower().endswith(".csv"):
            df = pd.read_csv(anonymized_path)
        else:
            df = pd.read_excel(anonymized_path, engine="openpyxl")

        # Desanonimizar todas las columnas
        for col in df.columns:
            df[col] = df[col].apply(
                lambda x: ctx.deanonymize(str(x)) if pd.notna(x) else x
            )

        # Guardar archivo restaurado
        if str(output_path).lower().endswith(".csv"):
            df.to_csv(output_path, index=False)
        else:
            df.to_excel(output_path, index=False, engine="openpyxl")

    @staticmethod
    def _to_initials(value: str, ctx: AnonymizationContext) -> str:
        """
        Convierte nombres a iniciales usando contexto NER.

        Ej: "Juan Perez Garcia" -> "J. P. G."

        Args:
            value: Texto a convertir
            ctx: Contexto de anonimizacion para deteccion NER

        Returns:
            Iniciales si es nombre, o valor original si no
        """
        if not value or not value.strip():
            return value

        # Detectar si es nombre propio con NER
        entities = ctx._detect_with_ner(value)
        person_entities = [e for e in entities if e.type == "PERSON_NAME"]

        if not person_entities:
            # Si no es nombre, retornar original
            return value

        # Extraer nombres y convertir a iniciales
        parts = [p.strip() for p in value.split() if p.strip()]

        if len(parts) >= 2:
            # Multiples palabras: tomar inicial de cada una
            initials = [f"{p[0]}." for p in parts]
            return " ".join(initials)
        else:
            # Una sola palabra: retornar primera letra + punto
            return f"{parts[0][0]}." if parts else value
