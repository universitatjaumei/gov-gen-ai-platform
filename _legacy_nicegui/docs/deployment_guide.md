# Guía de Despliegue e Instalación

Esta guía detalla los pasos para poner en marcha la infraestructura de AutomatIA. Se recomienda el uso de `uv` para la gestión de dependencias y entornos virtuales.

## 1. Requisitos del Sistema
- **Python**: 3.11 o superior.
- **Gestor de paquetes**: `uv` (recomendado) o `pip`.
- **Navegador**: Google Chrome o Microsoft Edge (para RPA/Playwright).
- **Recursos**: Mínimo 8GB RAM para el Brain, 4GB RAM para el Client Node.

## 2. Instalación de Dependencias

1.  **Clonar el repositorio**:
    ```bash
    git clone https://github.com/tu-organizacion/automatia.git
    cd automatia
    ```

2.  **Crear entorno e instalar dependencias**:
    ```bash
    uv sync
    ```

3.  **Instalar modelos NLP (para el Anonymizer)**:
    ```bash
    uv run python -m spacy download es_core_news_sm
    ```

4.  **Instalar binarios de Playwright (para RPA)**:
    ```bash
    uv run playwright install chromium
    ```

## 3. Configuración de Variables de Entorno (.env)
Crea un archivo `.env` en la raíz con las siguientes claves:

```env
# Seguridad
AUTOMATIA_SECRET_KEY=tu_clave_fernet_generada

# AI Providers (solo en el Brain)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=x-...
GOOGLE_API_KEY=...

# Configuración de Entorno
AUTOMATIA_MODE=native  # 'native' para escritorio, 'web' para servidor
AUTOMATIA_ENV=production

# Privacidad Visual (ScreenshotGuard) - V4.0
SCREENSHOT_POLICY=REVIEW  # BLOCK | REVIEW | TRUSTED

# ClarificationService - V4.0
CLARIFICATION_ENABLED=true

# ValidationLoopManager - V4.0
MAX_VALIDATION_RETRIES=3
```

## 4. Dependencias Adicionales para Características V4.0

### GraphicsFactory (Generación de Gráficos)
Las dependencias para matplotlib y seaborn ya están incluidas en `pyproject.toml`. Si necesitas instalarlas manualmente:
```bash
uv add matplotlib seaborn
```

### ReportFactory (Generación de Informes)
ReportLab ya está incluido en las dependencias. Para el backend HTML opcional:
```bash
# Playwright ya instalado para RPA, no se requiere instalación adicional
```

## 5. Inicialización de Bases de Datos
El sistema inicializa las bases de datos SQLite automáticamente en el primer arranque si no existen.
- Para forzar la creación y población de datos iniciales manualmente:
    ```bash
    uv run python scripts/init_and_seed.py
    ```

## 6. Ejecución

### Modo Cliente (On-Premise)
```bash
uv run main.py
```

### Modo Servidor (Brain Cloud)
Para desplegar en un servidor Linux:
```bash
uv run gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```
(Asegúrate de configurar `AUTOMATIA_MODE=web` en el servidor).

## 7. Verificación de la Instalación

Tras la instalación, verifica que todos los componentes funcionan correctamente:

```bash
# Verificar modelos NLP
uv run python -c "import spacy; nlp = spacy.load('es_core_news_sm'); print('✓ spaCy OK')"

# Verificar Playwright
uv run python -c "from playwright.sync_api import sync_playwright; print('✓ Playwright OK')"

# Verificar GraphicsFactory
uv run python -c "import matplotlib; import seaborn; print('✓ Graphics OK')"

# Verificar ReportLab
uv run python -c "from reportlab.pdfgen import canvas; print('✓ ReportLab OK')"
```

## 8. Próximos Pasos

- Consulta la [Guía de Inicio Rápido](quick_start.md) para crear tu primera automatización
- Revisa el [Manual de Usuario](functional/user_manual_client.md) para conocer todas las funcionalidades
- Para problemas, consulta [Troubleshooting](troubleshooting.md)
