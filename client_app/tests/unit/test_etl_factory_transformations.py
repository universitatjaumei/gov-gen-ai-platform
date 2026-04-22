"""
Tests para verificar que el ETLScriptFactory genera scripts válidos
que realizan las transformaciones solicitadas correctamente.

Estos tests verifican:
1. Scripts sintácticamente válidos y ejecutables
2. Scripts con función transform() correctamente definida
3. Transformaciones comunes funcionan según lo esperado
4. Manejo de casos edge (nulls, tipos mixtos, etc.)
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, patch
from datetime import datetime, date

from client_app.app.modules.factory.etl_factory import ETLScriptFactory


# =============================================================================
# HELPERS
# =============================================================================

def execute_transform_script(script: str, source_df: pd.DataFrame) -> pd.DataFrame:
    """
    Ejecuta un script de transformación y retorna el DataFrame resultante.

    Args:
        script: Código Python con función transform(df)
        source_df: DataFrame de entrada

    Returns:
        DataFrame transformado

    Raises:
        Exception si el script no es válido o falla la ejecución
    """
    namespace = {'pd': pd, 'np': np, 'datetime': datetime, 'date': date}
    exec(script, namespace)

    if 'transform' not in namespace:
        raise ValueError("El script no define la función 'transform'")

    transform_func = namespace['transform']
    return transform_func(source_df.copy())


def validate_script_syntax(script: str) -> bool:
    """Valida que el script sea sintácticamente correcto."""
    try:
        compile(script, '<string>', 'exec')
        return True
    except SyntaxError:
        return False


# =============================================================================
# FIXTURES - DataFrames de prueba
# =============================================================================

@pytest.fixture
def employees_df():
    """DataFrame de empleados para pruebas."""
    return pd.DataFrame({
        'nombre': ['Juan García', 'María López', 'Carlos Ruiz'],
        'apellido': ['García', 'López', 'Ruiz'],
        'salario': [35000, 42000, 28000],
        'departamento': ['Ventas', 'Marketing', 'IT'],
        'fecha_contrato': ['2020-01-15', '2019-06-20', '2021-03-10'],
        'activo': [True, True, False]
    })


@pytest.fixture
def sales_df():
    """DataFrame de ventas para pruebas."""
    return pd.DataFrame({
        'producto': ['A', 'B', 'A', 'C', 'B'],
        'cantidad': [10, 5, 8, 3, 12],
        'precio_unitario': [100.0, 200.0, 100.0, 150.0, 200.0],
        'fecha': ['2024-01-01', '2024-01-02', '2024-01-02', '2024-01-03', '2024-01-03'],
        'cliente': ['C1', 'C2', 'C1', 'C3', 'C2']
    })


@pytest.fixture
def messy_df():
    """DataFrame con datos sucios (nulls, espacios, etc.)."""
    return pd.DataFrame({
        'nombre': ['  Juan  ', 'María', None, 'Carlos  '],
        'edad': [30, None, 25, 40],
        'email': ['juan@test.com', 'MARIA@TEST.COM', 'pedro@test.com', None],
        'score': ['100', '85.5', 'N/A', '90']
    })


# =============================================================================
# FIXTURES - Mocks de IA
# =============================================================================

def create_mock_brain(script_code: str, model: str = 'test-model'):
    """Crea un mock del brain que retorna el script especificado."""
    brain = AsyncMock()
    brain.generate_code = AsyncMock(return_value={
        'code': script_code,
        'model': model,
        'tokens': len(script_code) // 4
    })
    return brain


# =============================================================================
# TESTS - Validación de estructura del script
# =============================================================================

class TestScriptStructureValidation:
    """Tests para validar que los scripts tienen la estructura correcta."""

    @pytest.mark.asyncio
    async def test_script_has_transform_function(self, employees_df):
        """El script debe definir una función llamada 'transform'."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    return df
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Retornar datos sin cambios",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        assert 'def transform' in result['script']
        assert validate_script_syntax(result['script'])

    @pytest.mark.asyncio
    async def test_script_is_executable(self, employees_df):
        """El script debe ser ejecutable sin errores."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Transforma el DataFrame."""
    df['salario_anual'] = df['salario'] * 12
    return df
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Calcular salario anual",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        # Debe ejecutar sin errores
        transformed = execute_transform_script(result['script'], employees_df)
        assert transformed is not None
        assert isinstance(transformed, pd.DataFrame)

    @pytest.mark.asyncio
    async def test_script_returns_dataframe(self, employees_df):
        """El script debe retornar un DataFrame."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    return df.copy()
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Copiar datos",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], employees_df)
        assert isinstance(transformed, pd.DataFrame)


# =============================================================================
# TESTS - Transformaciones de columnas
# =============================================================================

class TestColumnTransformations:
    """Tests para transformaciones que afectan columnas."""

    @pytest.mark.asyncio
    async def test_rename_columns(self, employees_df):
        """Renombrar columnas correctamente."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Renombra columnas al inglés."""
    return df.rename(columns={
        'nombre': 'first_name',
        'apellido': 'last_name',
        'salario': 'salary',
        'departamento': 'department'
    })
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Renombrar columnas al inglés",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], employees_df)

        assert 'first_name' in transformed.columns
        assert 'last_name' in transformed.columns
        assert 'salary' in transformed.columns
        assert 'nombre' not in transformed.columns

    @pytest.mark.asyncio
    async def test_select_columns(self, employees_df):
        """Seleccionar solo algunas columnas."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Selecciona solo nombre y salario."""
    return df[['nombre', 'salario']]
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Seleccionar solo nombre y salario",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], employees_df)

        assert list(transformed.columns) == ['nombre', 'salario']
        assert len(transformed) == len(employees_df)

    @pytest.mark.asyncio
    async def test_drop_columns(self, employees_df):
        """Eliminar columnas específicas."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Elimina la columna activo."""
    return df.drop(columns=['activo', 'fecha_contrato'])
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Eliminar columnas activo y fecha_contrato",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], employees_df)

        assert 'activo' not in transformed.columns
        assert 'fecha_contrato' not in transformed.columns
        assert 'nombre' in transformed.columns

    @pytest.mark.asyncio
    async def test_add_calculated_column(self, employees_df):
        """Añadir columna calculada."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Añade columna de salario mensual."""
    df['salario_mensual'] = df['salario'] / 12
    return df
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Calcular salario mensual",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], employees_df)

        assert 'salario_mensual' in transformed.columns
        # Verificar cálculo correcto
        expected = employees_df['salario'] / 12
        pd.testing.assert_series_equal(
            transformed['salario_mensual'],
            expected,
            check_names=False
        )


# =============================================================================
# TESTS - Transformaciones de filas
# =============================================================================

class TestRowTransformations:
    """Tests para transformaciones que afectan filas."""

    @pytest.mark.asyncio
    async def test_filter_rows(self, employees_df):
        """Filtrar filas por condición."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Filtra solo empleados activos."""
    return df[df['activo'] == True]
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Filtrar solo empleados activos",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], employees_df)

        assert len(transformed) == 2  # Solo Juan y María están activos
        assert all(transformed['activo'] == True)

    @pytest.mark.asyncio
    async def test_filter_by_value(self, employees_df):
        """Filtrar filas por valor específico."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Filtra empleados del departamento de Ventas."""
    return df[df['departamento'] == 'Ventas']
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Filtrar departamento Ventas",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], employees_df)

        assert len(transformed) == 1
        assert transformed.iloc[0]['nombre'] == 'Juan García'

    @pytest.mark.asyncio
    async def test_filter_numeric_range(self, employees_df):
        """Filtrar por rango numérico."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Filtra empleados con salario > 30000."""
    return df[df['salario'] > 30000]
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Filtrar salario mayor a 30000",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], employees_df)

        assert len(transformed) == 2  # Juan (35000) y María (42000)
        assert all(transformed['salario'] > 30000)


# =============================================================================
# TESTS - Transformaciones de valores
# =============================================================================

class TestValueTransformations:
    """Tests para transformaciones de valores en celdas."""

    @pytest.mark.asyncio
    async def test_uppercase_strings(self, employees_df):
        """Convertir strings a mayúsculas."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte nombres a mayúsculas."""
    df['nombre'] = df['nombre'].str.upper()
    return df
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Convertir nombres a mayúsculas",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], employees_df)

        assert transformed.iloc[0]['nombre'] == 'JUAN GARCÍA'
        assert transformed.iloc[1]['nombre'] == 'MARÍA LÓPEZ'

    @pytest.mark.asyncio
    async def test_clean_whitespace(self, messy_df):
        """Limpiar espacios en blanco."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Limpia espacios en nombres."""
    df['nombre'] = df['nombre'].str.strip()
    return df
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=messy_df,
            target_spec="Limpiar espacios en nombres",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], messy_df)

        # Verificar que se limpiaron los espacios (excepto None)
        assert transformed.iloc[0]['nombre'] == 'Juan'
        assert transformed.iloc[3]['nombre'] == 'Carlos'

    @pytest.mark.asyncio
    async def test_replace_values(self, employees_df):
        """Reemplazar valores específicos."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Reemplaza departamentos."""
    df['departamento'] = df['departamento'].replace({
        'IT': 'Tecnología',
        'Marketing': 'Mercadotecnia'
    })
    return df
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Renombrar departamentos",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], employees_df)

        assert 'Tecnología' in transformed['departamento'].values
        assert 'Mercadotecnia' in transformed['departamento'].values
        assert 'IT' not in transformed['departamento'].values


# =============================================================================
# TESTS - Agregaciones
# =============================================================================

class TestAggregations:
    """Tests para operaciones de agregación."""

    @pytest.mark.asyncio
    async def test_group_and_sum(self, sales_df):
        """Agrupar y sumar valores."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Suma cantidad por producto."""
    return df.groupby('producto', as_index=False).agg({
        'cantidad': 'sum'
    })
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=sales_df,
            target_spec="Sumar cantidad por producto",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], sales_df)

        assert len(transformed) == 3  # A, B, C
        # Producto A: 10 + 8 = 18
        assert transformed[transformed['producto'] == 'A']['cantidad'].values[0] == 18

    @pytest.mark.asyncio
    async def test_group_and_average(self, employees_df):
        """Calcular promedio por grupo."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Promedio de salario por departamento."""
    return df.groupby('departamento', as_index=False).agg({
        'salario': 'mean'
    }).rename(columns={'salario': 'salario_promedio'})
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Promedio de salario por departamento",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], employees_df)

        assert 'salario_promedio' in transformed.columns
        assert len(transformed) == 3  # IT, Marketing, Ventas

    @pytest.mark.asyncio
    async def test_calculate_totals(self, sales_df):
        """Calcular total (precio * cantidad)."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula el total de cada venta."""
    df['total'] = df['cantidad'] * df['precio_unitario']
    return df
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=sales_df,
            target_spec="Calcular total de cada venta",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], sales_df)

        assert 'total' in transformed.columns
        # Primera venta: 10 * 100 = 1000
        assert transformed.iloc[0]['total'] == 1000.0


# =============================================================================
# TESTS - Manejo de datos faltantes
# =============================================================================

class TestMissingDataHandling:
    """Tests para manejo de valores nulos/faltantes."""

    @pytest.mark.asyncio
    async def test_fill_na_with_value(self, messy_df):
        """Rellenar valores nulos con un valor específico."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Rellena valores nulos en edad con 0."""
    df['edad'] = df['edad'].fillna(0)
    return df
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=messy_df,
            target_spec="Rellenar edad nula con 0",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], messy_df)

        assert transformed['edad'].isna().sum() == 0
        assert transformed.iloc[1]['edad'] == 0  # Era None

    @pytest.mark.asyncio
    async def test_drop_na_rows(self, messy_df):
        """Eliminar filas con valores nulos."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Elimina filas con valores nulos."""
    return df.dropna()
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=messy_df,
            target_spec="Eliminar filas con valores nulos",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], messy_df)

        # Solo la fila de María tiene todos los valores (excepto edad)
        # En realidad, ninguna fila tiene todos los valores
        assert transformed.isna().sum().sum() == 0


# =============================================================================
# TESTS - Conversión de tipos
# =============================================================================

class TestTypeConversions:
    """Tests para conversiones de tipos de datos."""

    @pytest.mark.asyncio
    async def test_convert_to_datetime(self, employees_df):
        """Convertir string a datetime."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte fecha_contrato a datetime."""
    df['fecha_contrato'] = pd.to_datetime(df['fecha_contrato'])
    return df
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Convertir fecha_contrato a datetime",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], employees_df)

        assert pd.api.types.is_datetime64_any_dtype(transformed['fecha_contrato'])

    @pytest.mark.asyncio
    async def test_convert_to_numeric(self, messy_df):
        """Convertir string a numérico con manejo de errores."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte score a numérico."""
    df['score'] = pd.to_numeric(df['score'], errors='coerce')
    return df
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=messy_df,
            target_spec="Convertir score a numérico",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], messy_df)

        assert pd.api.types.is_numeric_dtype(transformed['score'])
        assert transformed.iloc[0]['score'] == 100.0
        assert transformed.iloc[1]['score'] == 85.5
        assert pd.isna(transformed.iloc[2]['score'])  # 'N/A' -> NaN


# =============================================================================
# TESTS - Transformaciones complejas
# =============================================================================

class TestComplexTransformations:
    """Tests para transformaciones que combinan varias operaciones."""

    @pytest.mark.asyncio
    async def test_etl_pipeline_complete(self, employees_df):
        """Pipeline ETL completo: filtrar, transformar, agregar columnas."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Pipeline ETL completo."""
    # 1. Filtrar empleados activos
    df = df[df['activo'] == True]

    # 2. Añadir columna de nombre completo
    df['nombre_completo'] = df['nombre'] + ' ' + df['apellido']

    # 3. Calcular salario anual con bonus
    df['salario_total'] = df['salario'] * 1.1

    # 4. Seleccionar columnas finales
    return df[['nombre_completo', 'departamento', 'salario_total']]
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Pipeline completo: filtrar activos, calcular salario con bonus",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], employees_df)

        # Verificar estructura
        assert list(transformed.columns) == ['nombre_completo', 'departamento', 'salario_total']

        # Verificar filtrado (solo activos)
        assert len(transformed) == 2

        # Verificar cálculo
        assert transformed.iloc[0]['salario_total'] == 35000 * 1.1

    @pytest.mark.asyncio
    async def test_sales_report_generation(self, sales_df):
        """Generar reporte de ventas agregado."""
        script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Genera reporte de ventas."""
    # Calcular total por venta
    df['total'] = df['cantidad'] * df['precio_unitario']

    # Agrupar por producto
    report = df.groupby('producto', as_index=False).agg({
        'cantidad': 'sum',
        'total': 'sum'
    })

    # Renombrar columnas
    report = report.rename(columns={
        'cantidad': 'unidades_vendidas',
        'total': 'ingresos_totales'
    })

    # Ordenar por ingresos
    return report.sort_values('ingresos_totales', ascending=False)
'''
        mock_brain = create_mock_brain(script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=sales_df,
            target_spec="Reporte de ventas por producto",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        transformed = execute_transform_script(result['script'], sales_df)

        assert 'unidades_vendidas' in transformed.columns
        assert 'ingresos_totales' in transformed.columns
        assert len(transformed) == 3  # 3 productos


# =============================================================================
# TESTS - Validación del prompt
# =============================================================================

class TestPromptGeneration:
    """Tests para verificar que el prompt se genera correctamente."""

    @pytest.mark.asyncio
    async def test_prompt_includes_source_columns(self, employees_df):
        """El prompt incluye información de columnas origen."""
        mock_brain = create_mock_brain('def transform(df): return df')
        factory = ETLScriptFactory()

        await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Transformar datos",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        call_args = mock_brain.generate_code.call_args
        prompt = call_args[1]['prompt']

        # Verificar que las columnas están en el prompt
        for col in employees_df.columns:
            assert col in prompt

    @pytest.mark.asyncio
    async def test_prompt_includes_sample_data(self, employees_df):
        """El prompt incluye datos de ejemplo."""
        mock_brain = create_mock_brain('def transform(df): return df')
        factory = ETLScriptFactory()

        await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Transformar datos",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        call_args = mock_brain.generate_code.call_args
        prompt = call_args[1]['prompt']

        # Verificar que hay datos de muestra (valores del DataFrame)
        assert 'Ventas' in prompt or 'Marketing' in prompt

    @pytest.mark.asyncio
    async def test_prompt_includes_user_instructions(self, employees_df):
        """El prompt incluye las instrucciones del usuario."""
        mock_brain = create_mock_brain('def transform(df): return df')
        factory = ETLScriptFactory()

        user_instructions = "Filtrar solo empleados del departamento IT"

        await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Filtrar datos",
            output_format='csv',
            user_instructions=user_instructions,
            client=mock_brain,
            license_key="TEST"
        )

        call_args = mock_brain.generate_code.call_args
        prompt = call_args[1]['prompt']

        assert user_instructions in prompt

    @pytest.mark.asyncio
    async def test_prompt_includes_output_format(self, employees_df):
        """El prompt incluye el formato de salida."""
        mock_brain = create_mock_brain('def transform(df): return df')
        factory = ETLScriptFactory()

        await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Transformar datos",
            output_format='parquet',
            client=mock_brain,
            license_key="TEST"
        )

        call_args = mock_brain.generate_code.call_args
        prompt = call_args[1]['prompt']

        assert 'parquet' in prompt.lower()


# =============================================================================
# TESTS - Extracción de código de respuesta
# =============================================================================

class TestCodeExtraction:
    """Tests para la extracción de código de diferentes formatos de respuesta."""

    @pytest.mark.asyncio
    async def test_extract_from_plain_code(self, employees_df):
        """Extrae código sin wrappers."""
        plain_script = '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    return df
'''
        mock_brain = create_mock_brain(plain_script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Test",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        assert 'def transform' in result['script']
        assert '```' not in result['script']

    @pytest.mark.asyncio
    async def test_extract_from_markdown_python_block(self, employees_df):
        """Extrae código de bloque markdown ```python."""
        markdown_script = '''```python
def transform(df: pd.DataFrame) -> pd.DataFrame:
    return df
```'''
        mock_brain = create_mock_brain(markdown_script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Test",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        assert 'def transform' in result['script']
        assert '```' not in result['script']

    @pytest.mark.asyncio
    async def test_extract_from_generic_markdown_block(self, employees_df):
        """Extrae código de bloque markdown genérico ```."""
        markdown_script = '''```
def transform(df: pd.DataFrame) -> pd.DataFrame:
    return df
```'''
        mock_brain = create_mock_brain(markdown_script)
        factory = ETLScriptFactory()

        result = await factory.generate_transformation_script(
            source_sample=employees_df,
            target_spec="Test",
            output_format='csv',
            client=mock_brain,
            license_key="TEST"
        )

        assert 'def transform' in result['script']
        assert '```' not in result['script']
