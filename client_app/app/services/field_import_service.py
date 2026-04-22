# client_app/app/services/field_import_service.py
"""
Field Import Service - Bulk import of field definitions from Excel/CSV.

Prompt #4 BIS: Importador Masivo de Campos desde Excel/CSV.

This service allows users to define extraction schemas by uploading
Excel or CSV files instead of manually entering each field.

Usage:
    service = FieldImportService()
    fields = service.parse_file(file_buffer, extension='.xlsx')
    # Returns list of {"name": str, "type": InputType, "description": str, "is_optional": bool}
"""
import re
import logging
from typing import List, Dict, Any, Tuple, Union, BinaryIO, TextIO

import pandas as pd

from automatia_shared.contracts.ui_contract import InputType

logger = logging.getLogger(__name__)


# Type mapping from user-friendly names to InputType enum
# Supports Spanish and English aliases
TYPE_MAP = {
    # String types
    'texto': InputType.STR,
    'text': InputType.STR,
    'string': InputType.STR,
    'str': InputType.STR,
    'cadena': InputType.STR,
    'varchar': InputType.STR,

    # Integer types
    'numero': InputType.INT,
    'number': InputType.INT,
    'int': InputType.INT,
    'integer': InputType.INT,
    'entero': InputType.INT,

    # Float types
    'decimal': InputType.FLOAT,
    'float': InputType.FLOAT,
    'double': InputType.FLOAT,
    'money': InputType.FLOAT,
    'dinero': InputType.FLOAT,
    'importe': InputType.FLOAT,
    'currency': InputType.FLOAT,

    # Date types
    'fecha': InputType.DATE,
    'date': InputType.DATE,

    # Datetime types
    'datetime': InputType.DATETIME,
    'fechahora': InputType.DATETIME,
    'timestamp': InputType.DATETIME,

    # Boolean types
    'bool': InputType.BOOL,
    'boolean': InputType.BOOL,
    'booleano': InputType.BOOL,
    'si/no': InputType.BOOL,
    'verdadero/falso': InputType.BOOL,
    'true/false': InputType.BOOL,

    # File types
    'file': InputType.FILE,
    'archivo': InputType.FILE,
    'files': InputType.FILES,
    'archivos': InputType.FILES,

    # JSON type
    'json': InputType.JSON,
    'objeto': InputType.JSON,
    'object': InputType.JSON,

    # Secret type
    'secret': InputType.SECRET,
    'password': InputType.SECRET,
    'contraseña': InputType.SECRET,

    # Select type
    'select': InputType.SELECT,
    'seleccion': InputType.SELECT,
    'dropdown': InputType.SELECT,
}

# Column name aliases (Spanish and English)
COLUMN_ALIASES = {
    'name': ['nombre', 'name', 'campo', 'field', 'columna', 'column'],
    'type': ['tipo', 'type', 'data_type', 'datatype', 'tipo_dato'],
    'description': ['descripcion', 'description', 'desc', 'comentario', 'comment', 'nota', 'note'],
    'is_optional': ['opcional', 'optional', 'is_optional', 'required', 'requerido', 'obligatorio'],
}


def _sanitize_field_name(name: str) -> str:
    """
    Sanitize a field name to be a valid Python identifier.

    - Converts to lowercase
    - Replaces spaces and special chars with underscores
    - Ensures it doesn't start with a number
    - Removes consecutive underscores

    Args:
        name: Original field name

    Returns:
        Sanitized field name (snake_case)
    """
    if not name:
        return "unnamed_field"

    # Trim whitespace
    name = str(name).strip()

    # Convert to lowercase
    name = name.lower()

    # Replace spaces and special characters with underscores
    name = re.sub(r'[^a-z0-9_]', '_', name)

    # Remove consecutive underscores
    name = re.sub(r'_+', '_', name)

    # Remove leading/trailing underscores
    name = name.strip('_')

    # Ensure doesn't start with a number
    if name and name[0].isdigit():
        name = f"field_{name}"

    # Fallback for empty result
    if not name:
        name = "unnamed_field"

    return name


def _normalize_type(type_str: str) -> InputType:
    """
    Normalize a type string to InputType enum.

    Args:
        type_str: User-provided type string

    Returns:
        InputType enum value (defaults to STR if unknown)
    """
    if not type_str:
        return InputType.STR

    type_lower = str(type_str).strip().lower()
    return TYPE_MAP.get(type_lower, InputType.STR)


def _find_column(df: pd.DataFrame, aliases: List[str]) -> str:
    """
    Find a column in DataFrame by checking multiple aliases.

    Args:
        df: DataFrame to search
        aliases: List of possible column names

    Returns:
        Actual column name found, or None
    """
    df_columns_lower = {col.lower().strip(): col for col in df.columns}

    for alias in aliases:
        if alias.lower() in df_columns_lower:
            return df_columns_lower[alias.lower()]

    return None


def _parse_boolean(value: Any) -> bool:
    """
    Parse various representations of boolean values.

    Args:
        value: Value to parse

    Returns:
        Boolean interpretation
    """
    if isinstance(value, bool):
        return value

    if pd.isna(value):
        return False

    str_val = str(value).strip().lower()

    # True values
    if str_val in ('true', 'yes', 'si', 'sí', '1', 'verdadero', 'opcional', 'optional'):
        return True

    # For 'required'/'requerido' columns, the logic is inverted
    # (required=True means optional=False)
    if str_val in ('false', 'no', '0', 'falso', 'requerido', 'required', 'obligatorio'):
        return False

    return False


class FieldImportService:
    """
    Service for importing field definitions from Excel/CSV files.

    Supports:
    - Excel (.xlsx, .xls) via pandas + openpyxl
    - CSV (.csv) via pandas

    Expected file format:
    - Required columns: nombre/name, tipo/type
    - Optional columns: descripcion/description, opcional/optional
    """

    def __init__(self):
        """Initialize the service."""
        self._warnings: List[str] = []

    def parse_file(
        self,
        file: Union[BinaryIO, TextIO, str],
        extension: str = '.xlsx'
    ) -> List[Dict[str, Any]]:
        """
        Parse a file and return field definitions.

        Args:
            file: File buffer or path to file
            extension: File extension (.xlsx, .xls, .csv)

        Returns:
            List of field definitions:
            [{"name": str, "type": InputType, "description": str, "is_optional": bool}]

        Raises:
            ValueError: If file format is invalid or required columns missing
        """
        fields, _ = self.parse_file_with_warnings(file, extension)
        return fields

    def parse_file_with_warnings(
        self,
        file: Union[BinaryIO, TextIO, str],
        extension: str = '.xlsx'
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Parse a file and return field definitions with any warnings.

        Args:
            file: File buffer or path to file
            extension: File extension (.xlsx, .xls, .csv)

        Returns:
            Tuple of (fields list, warnings list)

        Raises:
            ValueError: If file format is invalid or required columns missing
        """
        self._warnings = []

        # Read file into DataFrame
        df = self._read_file(file, extension)

        # Validate required columns exist
        self._validate_columns(df)

        # Parse fields
        fields = self._parse_fields(df)

        # Handle duplicates
        fields = self._handle_duplicates(fields)

        return fields, self._warnings

    def _read_file(
        self,
        file: Union[BinaryIO, TextIO, str],
        extension: str
    ) -> pd.DataFrame:
        """
        Read file into a DataFrame.

        Args:
            file: File buffer or path
            extension: File extension

        Returns:
            pandas DataFrame
        """
        ext = extension.lower().strip('.')

        try:
            if ext in ('xlsx', 'xls'):
                df = pd.read_excel(file, engine='openpyxl' if ext == 'xlsx' else None)
            elif ext == 'csv':
                df = pd.read_csv(file)
            else:
                raise ValueError(f"Extensión no soportada: {extension}")

            return df

        except Exception as e:
            raise ValueError(f"Error leyendo archivo: {str(e)}")

    def _validate_columns(self, df: pd.DataFrame) -> None:
        """
        Validate that required columns exist.

        Args:
            df: DataFrame to validate

        Raises:
            ValueError: If required columns missing or file is empty
        """
        # Find name column
        name_col = _find_column(df, COLUMN_ALIASES['name'])
        if not name_col:
            raise ValueError(
                "Columnas requeridas no encontradas: 'nombre' o 'name'. "
                f"Columnas encontradas: {list(df.columns)}"
            )

        # Find type column
        type_col = _find_column(df, COLUMN_ALIASES['type'])
        if not type_col:
            raise ValueError(
                "Columnas requeridas no encontradas: 'tipo' o 'type'. "
                f"Columnas encontradas: {list(df.columns)}"
            )

        # Check not empty
        if df.empty or len(df) == 0:
            raise ValueError("Archivo vacío: no se encontraron campos para importar")

    def _parse_fields(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Parse DataFrame rows into field definitions.

        Args:
            df: DataFrame with field data

        Returns:
            List of field definitions
        """
        fields = []

        # Find columns
        name_col = _find_column(df, COLUMN_ALIASES['name'])
        type_col = _find_column(df, COLUMN_ALIASES['type'])
        desc_col = _find_column(df, COLUMN_ALIASES['description'])
        opt_col = _find_column(df, COLUMN_ALIASES['is_optional'])

        for idx, row in df.iterrows():
            # Get and sanitize name
            raw_name = row.get(name_col, '')
            if pd.isna(raw_name) or str(raw_name).strip() == '':
                self._warnings.append(f"Fila {idx + 2}: nombre vacío, saltando")
                continue

            name = _sanitize_field_name(str(raw_name))

            # Get and normalize type
            raw_type = row.get(type_col, 'string')
            if pd.isna(raw_type):
                raw_type = 'string'

            field_type = _normalize_type(str(raw_type))

            # Check for unknown type
            type_lower = str(raw_type).strip().lower()
            if type_lower and type_lower not in TYPE_MAP:
                self._warnings.append(
                    f"Tipo desconocido '{raw_type}' para campo '{name}', "
                    f"usando STR por defecto"
                )

            # Get description
            description = ''
            if desc_col:
                desc_val = row.get(desc_col, '')
                if not pd.isna(desc_val):
                    description = str(desc_val).strip()

            # Get is_optional
            is_optional = False
            if opt_col:
                opt_val = row.get(opt_col, False)
                # Check if column name suggests it's 'required' (inverted logic)
                col_lower = opt_col.lower()
                if any(kw in col_lower for kw in ['required', 'requerido', 'obligatorio']):
                    is_optional = not _parse_boolean(opt_val)
                else:
                    is_optional = _parse_boolean(opt_val)

            fields.append({
                'name': name,
                'type': field_type,
                'description': description,
                'is_optional': is_optional
            })

        if not fields:
            raise ValueError("No se encontraron campos válidos para importar")

        return fields

    def _handle_duplicates(self, fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Handle duplicate field names by appending suffix.

        Args:
            fields: List of field definitions

        Returns:
            List with unique names
        """
        seen_names = {}
        result = []

        for field in fields:
            name = field['name']

            if name in seen_names:
                seen_names[name] += 1
                new_name = f"{name}_{seen_names[name]}"
                self._warnings.append(
                    f"Nombre duplicado '{name}' renombrado a '{new_name}'"
                )
                field = {**field, 'name': new_name}
            else:
                seen_names[name] = 0

            result.append(field)

        return result

    def get_template_dataframe(self) -> pd.DataFrame:
        """
        Get a template DataFrame that users can fill out.

        Returns:
            DataFrame with example structure
        """
        return pd.DataFrame({
            'nombre': ['ejemplo_campo1', 'ejemplo_campo2', 'ejemplo_campo3'],
            'tipo': ['texto', 'numero', 'fecha'],
            'descripcion': ['Descripción del campo 1', 'Descripción del campo 2', 'Descripción del campo 3'],
            'opcional': [False, False, True]
        })

    def save_template(self, path: str) -> None:
        """
        Save a template Excel file for users to fill out.

        Args:
            path: Path to save the template
        """
        df = self.get_template_dataframe()
        df.to_excel(path, index=False)
        logger.info(f"Template saved to: {path}")


# Singleton instance
field_import_service = FieldImportService()
