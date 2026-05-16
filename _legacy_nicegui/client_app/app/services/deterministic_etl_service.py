"""
Deterministic ETL Service - Executes predefined transformations without AI.

This service handles simple, deterministic data transformations that don't require
AI-generated code. Operations are executed directly using pandas.
"""

import pandas as pd
import re
from typing import List, Union
from datetime import datetime

from client_app.app.models.transform_operations import (
    TransformOperation,
    DropColumnsOperation,
    RenameColumnsOperation,
    MergeColumnsOperation,
    FormatDatesOperation,
    FilterRowsOperation,
    ReplaceValuesOperation,
    NormalizeTextOperation,
    FillNullsOperation,
    RemoveDuplicatesOperation,
    RemoveNullRowsOperation,
    ReorderColumnsOperation
)


class DeterministicETLService:
    """Executes deterministic transformations without AI intervention."""
    
    async def execute_transformation(
        self,
        source_df: pd.DataFrame,
        operations: List[TransformOperation]
    ) -> pd.DataFrame:
        """
        Apply a list of deterministic operations to a DataFrame.
        
        Args:
            source_df: Source DataFrame
            operations: List of operations to apply in order
            
        Returns:
            Transformed DataFrame
        """
        result_df = source_df.copy()
        
        for op in operations:
            if isinstance(op, DropColumnsOperation):
                result_df = self._drop_columns(result_df, op)
            elif isinstance(op, RenameColumnsOperation):
                result_df = self._rename_columns(result_df, op)
            elif isinstance(op, MergeColumnsOperation):
                result_df = self._merge_columns(result_df, op)
            elif isinstance(op, FormatDatesOperation):
                result_df = self._format_dates(result_df, op)
            elif isinstance(op, FilterRowsOperation):
                result_df = self._filter_rows(result_df, op)
            elif isinstance(op, ReplaceValuesOperation):
                result_df = self._replace_values(result_df, op)
            elif isinstance(op, NormalizeTextOperation):
                result_df = self._normalize_text(result_df, op)
            elif isinstance(op, FillNullsOperation):
                result_df = self._fill_nulls(result_df, op)
            elif isinstance(op, RemoveDuplicatesOperation):
                result_df = self._remove_duplicates(result_df, op)
            elif isinstance(op, RemoveNullRowsOperation):
                result_df = self._remove_null_rows(result_df, op)
            elif isinstance(op, ReorderColumnsOperation):
                result_df = self._reorder_columns(result_df, op)
            else:
                raise ValueError(f"Unknown operation type: {type(op)}")
        
        return result_df
    
    def _drop_columns(self, df: pd.DataFrame, op: DropColumnsOperation) -> pd.DataFrame:
        """Drop specified columns."""
        existing_cols = [col for col in op.columns if col in df.columns]
        if not existing_cols:
            return df
        return df.drop(columns=existing_cols)
    
    def _rename_columns(self, df: pd.DataFrame, op: RenameColumnsOperation) -> pd.DataFrame:
        """Rename columns according to mapping."""
        # Only rename columns that exist
        valid_mapping = {old: new for old, new in op.mapping.items() if old in df.columns}
        if not valid_mapping:
            return df
        return df.rename(columns=valid_mapping)
    
    def _merge_columns(self, df: pd.DataFrame, op: MergeColumnsOperation) -> pd.DataFrame:
        """Merge multiple columns into one."""
        # Check if all source columns exist
        existing_cols = [col for col in op.source_columns if col in df.columns]
        if not existing_cols:
            return df
        
        # Merge columns
        new_values = df[existing_cols].apply(
            lambda row: op.separator.join(row.astype(str)), axis=1
        )
        
        # [NEW] Preserve position logic
        if op.drop_source:
             # Find index of the first column being merged
             all_cols = list(df.columns)
             first_idx = min(all_cols.index(c) for c in existing_cols)
             
             # Calculate columns to drop
             df = df.drop(columns=existing_cols)
             
             # Insert at the same position
             df.insert(first_idx, op.target_column, new_values)
        else:
             # Just add as new column at the end
             df[op.target_column] = new_values
        
        return df

    def _reorder_columns(self, df: pd.DataFrame, op: ReorderColumnsOperation) -> pd.DataFrame:
        """Reorder columns."""
        # Only include columns that actually exist in the DF
        valid_cols = [c for c in op.columns if c in df.columns]
        # Add any columns that were in the DF but not in the requested list (at the end)
        remaining_cols = [c for c in df.columns if c not in valid_cols]
        return df[valid_cols + remaining_cols]
    
    def _format_dates(self, df: pd.DataFrame, op: FormatDatesOperation) -> pd.DataFrame:
        """Convert date format in a column."""
        if op.column not in df.columns:
            return df
        
        try:
            # Parse dates (auto-detect if source_format is None)
            if op.source_format:
                date_series = pd.to_datetime(df[op.column], format=op.source_format, errors='coerce')
            else:
                date_series = pd.to_datetime(df[op.column], errors='coerce')
            
            # Format dates
            if op.target_format.upper() == 'ISO8601':
                df[op.column] = date_series.dt.strftime('%Y-%m-%d')
            else:
                df[op.column] = date_series.dt.strftime(op.target_format)
        except Exception as e:
            # If conversion fails, leave column unchanged
            print(f"Warning: Date formatting failed for column '{op.column}': {e}")
        
        return df
    
    def _filter_rows(self, df: pd.DataFrame, op: FilterRowsOperation) -> pd.DataFrame:
        """Filter rows based on condition."""
        if op.column not in df.columns:
            return df
        
        if op.operator == '==':
            return df[df[op.column] == op.value]
        elif op.operator == '!=':
            return df[df[op.column] != op.value]
        elif op.operator == '>':
            return df[df[op.column] > op.value]
        elif op.operator == '<':
            return df[df[op.column] < op.value]
        elif op.operator == '>=':
            return df[df[op.column] >= op.value]
        elif op.operator == '<=':
            return df[df[op.column] <= op.value]
        elif op.operator == 'contains':
            return df[df[op.column].astype(str).str.contains(str(op.value), na=False)]
        elif op.operator == 'not_contains':
            return df[~df[op.column].astype(str).str.contains(str(op.value), na=False)]
        else:
            return df
    
    def _replace_values(self, df: pd.DataFrame, op: ReplaceValuesOperation) -> pd.DataFrame:
        """Replace values in a column."""
        if op.column not in df.columns:
            return df
        
        df[op.column] = df[op.column].replace(op.replacements)
        return df
    
    def _normalize_text(self, df: pd.DataFrame, op: NormalizeTextOperation) -> pd.DataFrame:
        """Normalize text in columns."""
        existing_cols = [col for col in op.columns if col in df.columns]
        if not existing_cols:
            return df
        
        for col in existing_cols:
            if op.mode == 'upper':
                df[col] = df[col].astype(str).str.upper()
            elif op.mode == 'lower':
                df[col] = df[col].astype(str).str.lower()
            elif op.mode == 'title':
                df[col] = df[col].astype(str).str.title()
            elif op.mode == 'strip':
                df[col] = df[col].astype(str).str.strip()
            elif op.mode == 'snake_case':
                df[col] = df[col].astype(str).apply(self._to_snake_case)
        
        return df
    
    def _to_snake_case(self, text: str) -> str:
        """Convert text to snake_case."""
        # Replace spaces and hyphens with underscores
        text = re.sub(r'[\s\-]+', '_', text)
        # Insert underscore before uppercase letters
        text = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', text)
        # Convert to lowercase
        return text.lower()
    
    def _fill_nulls(self, df: pd.DataFrame, op: FillNullsOperation) -> pd.DataFrame:
        """Fill null values in columns."""
        existing_cols = [col for col in op.columns if col in df.columns]
        if not existing_cols:
            return df
        
        df[existing_cols] = df[existing_cols].fillna(op.value)
        return df
    
    def _remove_duplicates(self, df: pd.DataFrame, op: RemoveDuplicatesOperation) -> pd.DataFrame:
        """Remove duplicate rows."""
        # Validate subset columns if provided
        subset = None
        if op.subset:
            subset = [col for col in op.subset if col in df.columns]
            if not subset:
                subset = None
        
        return df.drop_duplicates(subset=subset, keep=op.keep)
    
    def _remove_null_rows(self, df: pd.DataFrame, op: RemoveNullRowsOperation) -> pd.DataFrame:
        """Remove rows with null values."""
        # Validate subset columns if provided
        subset = None
        if op.subset:
            subset = [col for col in op.subset if col in df.columns]
            if not subset:
                subset = None
        
        how_val = op.how if op.how in ['any', 'all'] else 'any'
        return df.dropna(subset=subset, how=how_val)

    def generate_script(self, operations: List[TransformOperation]) -> str:
        """Generate a Python script for the transformations."""
        lines = [
            "import pandas as pd",
            "import numpy as np",
            "import re",
            "",
            "def to_snake_case(text):",
            "    if not isinstance(text, str): return str(text)",
            "    text = re.sub(r'[\\s\\-]+', '_', text)",
            "    text = re.sub(r'([a-z0-9])([A-Z])', r'\\1_\\2', text)",
            "    return text.lower()",
            "",
            "def transform(df: pd.DataFrame) -> pd.DataFrame:",
            "    # Deterministic Transformation Script",
            "    df = df.copy()",
            ""
        ]
        
        for i, op in enumerate(operations):
            lines.append(f"    # Operation {i+1}: {type(op).__name__}")
            
            if isinstance(op, DropColumnsOperation):
                lines.append(f"    existing_cols = [c for c in {op.columns} if c in df.columns]")
                lines.append(f"    if existing_cols: df = df.drop(columns=existing_cols)")
            
            elif isinstance(op, RenameColumnsOperation):
                lines.append(f"    df = df.rename(columns={op.mapping})")
            
            elif isinstance(op, MergeColumnsOperation):
                lines.append(f"    cols_to_merge = [c for c in {op.source_columns} if c in df.columns]")
                lines.append(f"    if cols_to_merge:")
                if op.drop_source:
                    lines.append(f"            first_idx = min(list(df.columns).index(c) for c in cols_to_merge)")
                    lines.append(f"            new_col = df[cols_to_merge].apply(lambda x: '{op.separator}'.join(x.astype(str)), axis=1)")
                    lines.append(f"            df = df.drop(columns=cols_to_merge)")
                    lines.append(f"            df.insert(first_idx, '{op.target_column}', new_col)")
                else:
                    lines.append(f"            df['{op.target_column}'] = df[cols_to_merge].apply(lambda x: '{op.separator}'.join(x.astype(str)), axis=1)")

            elif isinstance(op, FormatDatesOperation):
                if op.source_format:
                    lines.append(f"    if '{op.column}' in df.columns:")
                    lines.append(f"        df['{op.column}'] = pd.to_datetime(df['{op.column}'], format='{op.source_format}', errors='coerce')")
                else:
                    lines.append(f"    if '{op.column}' in df.columns:")
                    lines.append(f"        df['{op.column}'] = pd.to_datetime(df['{op.column}'], errors='coerce')")
                
                if op.target_format:
                     lines.append(f"        df['{op.column}'] = df['{op.column}'].dt.strftime('{op.target_format}')")

            elif isinstance(op, FilterRowsOperation):
                val = f"'{op.value}'" if isinstance(op.value, str) else op.value
                if op.operator == '==':
                    lines.append(f"    if '{op.column}' in df.columns: df = df[df['{op.column}'] == {val}]")
                elif op.operator == '!=':
                    lines.append(f"    if '{op.column}' in df.columns: df = df[df['{op.column}'] != {val}]")
                elif op.operator == '>':
                    lines.append(f"    if '{op.column}' in df.columns: df = df[df['{op.column}'] > {val}]")
                elif op.operator == '<':
                    lines.append(f"    if '{op.column}' in df.columns: df = df[df['{op.column}'] < {val}]")
                elif op.operator == 'contains':
                    # Ensure val is string for contains
                    val_str = str(op.value)
                    lines.append(f"    if '{op.column}' in df.columns: df = df[df['{op.column}'].astype(str).str.contains('{val_str}', na=False)]")

            elif isinstance(op, ReplaceValuesOperation):
                 lines.append(f"    if '{op.column}' in df.columns: df['{op.column}'] = df['{op.column}'].replace({op.replacements})")

            elif isinstance(op, NormalizeTextOperation):
                lines.append(f"    target_cols = [c for c in {op.columns} if c in df.columns]")
                lines.append(f"    for col in target_cols:")
                if op.mode == 'upper':
                    lines.append(f"        df[col] = df[col].astype(str).str.upper()")
                elif op.mode == 'lower':
                    lines.append(f"        df[col] = df[col].astype(str).str.lower()")
                elif op.mode == 'title':
                    lines.append(f"        df[col] = df[col].astype(str).str.title()")
                elif op.mode == 'strip':
                    lines.append(f"        df[col] = df[col].astype(str).str.strip()")
                elif op.mode == 'snake_case':
                    lines.append(f"        df[col] = df[col].astype(str).apply(to_snake_case)")

            elif isinstance(op, FillNullsOperation):
                lines.append(f"    target_cols = [c for c in {op.columns} if c in df.columns]")
                val = f"'{op.value}'" if isinstance(op.value, str) else op.value
                lines.append(f"    if target_cols: df[target_cols] = df[target_cols].fillna({val})")

            elif isinstance(op, RemoveDuplicatesOperation):
                subset_str = f"{op.subset}" if op.subset else "None"
                lines.append(f"    df = df.drop_duplicates(subset={subset_str}, keep='{op.keep}')")

            elif isinstance(op, RemoveNullRowsOperation):
                subset_str = f"{op.subset}" if op.subset else "None"
                how_val = 'any' if op.how not in ['any', 'all'] else op.how
                lines.append(f"    df = df.dropna(subset={subset_str}, how='{how_val}')")

            elif isinstance(op, ReorderColumnsOperation):
                lines.append(f"    valid_cols = [c for c in {op.columns} if c in df.columns]")
                lines.append(f"    remaining = [c for c in df.columns if c not in valid_cols]")
                lines.append(f"    df = df[valid_cols + remaining]")
            
            lines.append("")
            
        lines.append("    return df")
        return "\n".join(lines)
