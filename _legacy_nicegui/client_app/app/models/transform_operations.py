"""
Transform Operation Models for Deterministic ETL.

Defines Pydantic models for each type of deterministic transformation operation.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Optional


class DropColumnsOperation(BaseModel):
    """Drop specified columns from DataFrame."""
    type: Literal['drop_columns'] = 'drop_columns'
    columns: List[str] = Field(..., description="List of column names to drop")


class RenameColumnsOperation(BaseModel):
    """Rename columns in DataFrame."""
    type: Literal['rename_columns'] = 'rename_columns'
    mapping: Dict[str, str] = Field(..., description="Mapping of old_name -> new_name")


class MergeColumnsOperation(BaseModel):
    """Merge multiple columns into a single column."""
    type: Literal['merge_columns'] = 'merge_columns'
    source_columns: List[str] = Field(..., description="Columns to merge")
    target_column: str = Field(..., description="Name of the new merged column")
    separator: str = Field(default=" ", description="Separator between values")
    drop_source: bool = Field(default=False, description="Drop source columns after merge")


class FormatDatesOperation(BaseModel):
    """Convert date format in a column."""
    type: Literal['format_dates'] = 'format_dates'
    column: str = Field(..., description="Column containing dates")
    source_format: Optional[str] = Field(default=None, description="Source date format (None for auto-detect)")
    target_format: str = Field(..., description="Target date format (e.g., '%Y-%m-%d', 'ISO8601')")


class FilterRowsOperation(BaseModel):
    """Filter rows based on simple conditions."""
    type: Literal['filter_rows'] = 'filter_rows'
    column: str = Field(..., description="Column to filter on")
    operator: Literal['==', '!=', '>', '<', '>=', '<=', 'contains', 'not_contains'] = Field(..., description="Comparison operator")
    value: Any = Field(..., description="Value to compare against")


class ReplaceValuesOperation(BaseModel):
    """Replace values in a column."""
    type: Literal['replace_values'] = 'replace_values'
    column: str = Field(..., description="Column to perform replacement in")
    replacements: Dict[str, str] = Field(..., description="Mapping of old_value -> new_value")


class NormalizeTextOperation(BaseModel):
    """Normalize text in columns."""
    type: Literal['normalize_text'] = 'normalize_text'
    columns: List[str] = Field(..., description="Columns to normalize")
    mode: Literal['upper', 'lower', 'title', 'strip', 'snake_case'] = Field(..., description="Normalization mode")


class FillNullsOperation(BaseModel):
    """Fill null values in columns."""
    type: Literal['fill_nulls'] = 'fill_nulls'
    columns: List[str] = Field(..., description="Columns to fill nulls in")
    value: Any = Field(..., description="Value to fill nulls with")


class RemoveDuplicatesOperation(BaseModel):
    """Remove duplicate rows."""
    type: Literal['remove_duplicates'] = 'remove_duplicates'
    subset: Optional[List[str]] = Field(default=None, description="Columns to consider for duplicates (None = all)")
    keep: Literal['first', 'last', False] = Field(default='first', description="Which duplicates to keep")


class RemoveNullRowsOperation(BaseModel):
    """Remove rows with null values."""
    type: Literal['remove_null_rows'] = 'remove_null_rows'
    subset: Optional[List[str]] = Field(default=None, description="Columns to check for nulls (None = any column)")
    how: Literal['any', 'all'] = Field(default='any', description="'any' = drop if any null, 'all' = drop if all null")


class ReorderColumnsOperation(BaseModel):
    """Reorder columns in DataFrame."""
    type: Literal['reorder_columns'] = 'reorder_columns'
    columns: List[str] = Field(..., description="Ordered list of column names")


# Union type for all operations
TransformOperation = (
    DropColumnsOperation |
    RenameColumnsOperation |
    MergeColumnsOperation |
    FormatDatesOperation |
    FilterRowsOperation |
    ReplaceValuesOperation |
    NormalizeTextOperation |
    FillNullsOperation |
    RemoveDuplicatesOperation |
    RemoveNullRowsOperation |
    ReorderColumnsOperation
)
