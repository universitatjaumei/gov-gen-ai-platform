"""
Atom Service - Gestión de átomos reutilizables.
Prompt 1.3 del plan de refactorización del editor de flujos.

Proporciona operaciones CRUD para el catálogo de átomos (AtomRegistry).
"""
import json
from datetime import datetime
from typing import Optional, List

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from client_app.app.database.db import client_engine
from client_app.app.database.models import AtomRegistry
from automatia_shared.enums import StepType


class AtomService:
    """
    Servicio para gestión de átomos reutilizables.

    Implementa patrón Singleton para asegurar una única instancia.
    """
    _instance = None

    def __new__(cls):
        """
        Garantiza que solo exista una instancia de AtomService (Singleton).
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _validate_json(self, value: str, field_name: str) -> None:
        """Valida que un string sea JSON válido."""
        try:
            json.loads(value)
        except (json.JSONDecodeError, TypeError):
            raise ValueError(f"{field_name} debe ser JSON válido")

    async def create_atom(
        self,
        name: str,
        atom_type: StepType,
        config_schema: str,
        description: str = None,
        default_config: str = "{}",
        version: str = "1.0.0",
        subtype: str = None,
        input_contract: str = None,
        output_contract: str = None,
        dependencies: List[int] = None,
        has_stepper: bool = True,
        has_variables: bool = True,
        status: str = 'DRAFT'
    ) -> AtomRegistry:
        """
        Crea un nuevo átomo en el catálogo.

        Args:
            name: Nombre descriptivo del átomo
            atom_type: Tipo de paso (StepType enum)
            config_schema: JSON Schema que define los campos de configuración
            description: Descripción para el usuario (opcional)
            default_config: Configuración por defecto en JSON
            version: Versión semántica (default "1.0.0")
            subtype: Subtipo de conexión (EMAIL, API, DATABASE) - solo para CONNECTION
            input_contract: JSON Schema de datos de entrada (opcional)
            output_contract: JSON Schema de datos de salida (opcional)
            dependencies: Lista de IDs de átomos dependientes (ej: conexiones)
            has_stepper: Si el átomo usa el stepper de ajustes (default True)
            has_variables: Si el átomo expone variables de salida (default True)

        Returns:
            AtomRegistry: El átomo creado

        Raises:
            ValueError: Si config_schema no es JSON válido
        """
        # Validar que config_schema sea JSON válido
        self._validate_json(config_schema, "config_schema")

        # Validar default_config si se proporciona
        if default_config:
            self._validate_json(default_config, "default_config")

        # Validar contratos si se proporcionan
        if input_contract:
            self._validate_json(input_contract, "input_contract")
        if output_contract:
            self._validate_json(output_contract, "output_contract")

        atom = AtomRegistry(
            name=name,
            atom_type=atom_type,
            description=description,
            config_schema=config_schema,
            default_config=default_config,
            version=version,
            is_active=True,
            subtype=subtype,
            input_contract=input_contract,
            output_contract=output_contract,
            dependencies=json.dumps(dependencies) if dependencies else "[]",
            has_stepper=has_stepper,
            has_variables=has_variables,
            status=status
        )

        async with AsyncSession(client_engine) as session:
            session.add(atom)
            await session.commit()
            await session.refresh(atom)
            return atom

    async def list_atoms(
        self,
        atom_type: StepType = None,
        include_inactive: bool = False
    ) -> List[AtomRegistry]:
        """
        Lista átomos con filtros opcionales.

        Args:
            atom_type: Filtrar por tipo de átomo (opcional)
            include_inactive: Incluir átomos inactivos (default False)

        Returns:
            List[AtomRegistry]: Lista de átomos que coinciden con los filtros
        """
        async with AsyncSession(client_engine) as session:
            query = select(AtomRegistry)

            # Por defecto solo átomos activos
            if not include_inactive:
                query = query.where(AtomRegistry.is_active == True)

            # Filtrar por tipo
            if atom_type is not None:
                query = query.where(AtomRegistry.atom_type == atom_type)

            # Ordenar por nombre
            query = query.order_by(AtomRegistry.name)

            result = await session.execute(query)
            return result.scalars().all()

    async def get_atom(self, atom_id: int) -> Optional[AtomRegistry]:
        """
        Recupera un átomo específico del catálogo utilizando su identificador único.

        Args:
            atom_id: ID numérico del átomo en el registro.

        Returns:
            El objeto AtomRegistry si existe, o None en caso contrario.
        """
        async with AsyncSession(client_engine) as session:
            return await session.get(AtomRegistry, atom_id)

    async def update_atom(self, atom_id: int, **kwargs) -> AtomRegistry:
        """
        Actualiza los campos de un átomo.

        Args:
            atom_id: ID del átomo a actualizar
            **kwargs: Campos a actualizar (name, description, config_schema, etc.)

        Returns:
            AtomRegistry: El átomo actualizado

        Raises:
            ValueError: Si el átomo no existe o si los datos son inválidos
        """
        async with AsyncSession(client_engine) as session:
            atom = await session.get(AtomRegistry, atom_id)
            if not atom:
                raise ValueError(f"Atom {atom_id} not found")

            # Validar JSON si se actualiza config_schema
            if "config_schema" in kwargs:
                self._validate_json(kwargs["config_schema"], "config_schema")

            # Validar JSON si se actualiza default_config
            if "default_config" in kwargs:
                self._validate_json(kwargs["default_config"], "default_config")

            # Aplicar actualizaciones
            for key, value in kwargs.items():
                if hasattr(atom, key):
                    setattr(atom, key, value)

            # Actualizar timestamp
            atom.updated_at = datetime.utcnow()

            session.add(atom)
            await session.commit()
            await session.refresh(atom)
            return atom

    async def update_atom_sample_data(self, atom_id: int, data: any, source: str = "auto") -> bool:
        """
        Actualiza el campo `sample_data` de un átomo capturando una muestra de los datos proporcionados.
        Utiliza el PreviewDataService para normalizar la muestra a un formato tabular.
        
        Args:
            atom_id: El ID del átomo a actualizar.
            data: Los datos crudos (DataFrame, lista, dict) a parsear como muestra.
            source: Opcional, marca el origen (ej. 'auto', 'manual').
            
        Returns:
            bool: True si el átomo se actualizó correctamente, False si no se encontró.
        """
        try:
            from client_app.app.services.preview_data_service import preview_data_service
            
            # 1. Normalizar los datos (obtener PreviewResult con max_rows)
            preview_result = preview_data_service._normalize_output_to_preview(data, max_rows=10)
            
            # 2. Enriquecer con metadatos
            if not preview_result.metadata:
                preview_result.metadata = {}
            preview_result.metadata["generated_at"] = datetime.utcnow().isoformat()
            preview_result.source_type = source
            
            # 3. Serializar a JSON
            sample_json = json.dumps({
                "columns": preview_result.columns,
                "rows": preview_result.rows,
                "preview_rows": preview_result.preview_rows,
                "row_count": preview_result.row_count,
                "metadata": preview_result.metadata,
                "source_type": preview_result.source_type
            })
            
            # 4. Guardar en BD
            async with AsyncSession(client_engine) as session:
                atom = await session.get(AtomRegistry, atom_id)
                if not atom:
                    return False
                    
                atom.sample_data = sample_json
                atom.updated_at = datetime.utcnow()
                
                session.add(atom)
                await session.commit()
                return True
        except Exception as e:
            print(f"Error actualizando sample_data para atom {atom_id}: {e}")
            return False

    async def delete_atom(self, atom_id: int) -> bool:
        """
        Realiza un borrado lógico (soft delete) de un átomo, marcándolo como inactivo.

        Args:
            atom_id: Identificador del átomo a desactivar.

        Returns:
            True si el átomo fue encontrado y desactivado, False si no existía.
        """
        async with AsyncSession(client_engine) as session:
            atom = await session.get(AtomRegistry, atom_id)
            if not atom:
                return False

            atom.is_active = False
            atom.updated_at = datetime.utcnow()

            session.add(atom)
            await session.commit()
            return True

    async def create_new_version(self, atom_id: int) -> AtomRegistry:
        """
        Crea una nueva versión del átomo como borrador.
        Incrementa la versión menor (ej: 1.0.0 -> 1.1.0).
        """
        async with AsyncSession(client_engine) as session:
            original = await session.get(AtomRegistry, atom_id)
            if not original:
                raise ValueError(f"Atom {atom_id} not found")

            # Incrementar versión (X.Y.Z -> X.Y+1.0)
            try:
                parts = original.version.split('.')
                if len(parts) >= 2:
                    parts[1] = str(int(parts[1]) + 1)
                    if len(parts) >= 3:
                        parts[2] = "0"
                    new_version = '.'.join(parts)
                else:
                    new_version = f"{original.version}.1.0"
            except:
                new_version = f"{original.version}.1"

            new_atom = AtomRegistry(
                name=f"{original.name} v{new_version}",
                description=f"Nueva versión de: {original.name}",
                atom_type=original.atom_type,
                subtype=original.subtype,
                config_schema=original.config_schema,
                default_config=original.default_config,
                input_contract=original.input_contract,
                output_contract=original.output_contract,
                dependencies=original.dependencies,
                has_stepper=original.has_stepper,
                has_variables=original.has_variables,
                version=new_version,
                status='DRAFT',  # Siempre borrador
                is_active=True
            )

            session.add(new_atom)
            await session.commit()
            await session.refresh(new_atom)
            return new_atom

    async def duplicate_atom(self, atom_id: int, new_name: str) -> AtomRegistry:
        """
        Crea una copia de un átomo existente.

        Args:
            atom_id: ID del átomo a duplicar
            new_name: Nombre para la copia

        Returns:
            AtomRegistry: El nuevo átomo creado

        Raises:
            ValueError: Si el átomo original no existe
        """
        async with AsyncSession(client_engine) as session:
            original = await session.get(AtomRegistry, atom_id)
            if not original:
                raise ValueError(f"Atom {atom_id} not found")

            # Crear copia con nuevo nombre (incluyendo contratos)
            new_atom = AtomRegistry(
                name=new_name,
                atom_type=original.atom_type,
                subtype=original.subtype,
                description=f"Copia de {original.name}" if not original.description
                           else original.description,
                config_schema=original.config_schema,
                default_config=original.default_config,
                input_contract=original.input_contract,
                output_contract=original.output_contract,
                dependencies=original.dependencies,
                has_stepper=original.has_stepper,
                has_variables=original.has_variables,
                version="1.0.0",  # Reset version
                is_active=True
            )

            session.add(new_atom)
            await session.commit()
            await session.refresh(new_atom)
            return new_atom


# Singleton Instance
atom_service = AtomService()
