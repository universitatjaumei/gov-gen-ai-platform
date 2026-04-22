"""
Local Knowledge Service - Prompt #9 Implementation
Motor de RAG Local para el Copiloto.

Proporciona busqueda contextual en la documentacion local (README.md de atomos)
para alimentar las consultas del Copiloto, respetando la privacidad Zero-Knowledge.

Features:
- Busqueda semantica simple basada en palabras clave
- Coincidencia de nombres de archivos/atomos
- Cache en memoria para consultas repetidas
- Privacidad: limpia rutas absolutas antes de enviar contexto
"""
import re
import unicodedata
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import logging

logger = logging.getLogger(__name__)

# Stop words en espanol para mejorar la busqueda
STOP_WORDS_ES = {
    'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
    'de', 'del', 'al', 'a', 'en', 'con', 'por', 'para',
    'que', 'como', 'cual', 'cuales', 'quien', 'quienes',
    'este', 'esta', 'estos', 'estas', 'ese', 'esa', 'esos', 'esas',
    'y', 'o', 'pero', 'si', 'no', 'es', 'son', 'hay',
    'ser', 'estar', 'tener', 'hacer', 'poder', 'ir',
    'muy', 'mas', 'menos', 'ya', 'todo', 'todos', 'toda', 'todas',
    'mi', 'tu', 'su', 'mis', 'tus', 'sus', 'nuestro', 'nuestra',
}


def normalize_text(text: str) -> str:
    """
    Normaliza texto para busqueda: quita acentos, pasa a minusculas.

    Args:
        text: Texto a normalizar

    Returns:
        Texto normalizado sin acentos y en minusculas
    """
    # Quitar acentos
    nfkd = unicodedata.normalize('NFKD', text)
    without_accents = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return without_accents.lower()


def extract_keywords(query: str, min_length: int = 2) -> List[str]:
    """
    Extrae palabras clave de una consulta, eliminando stop words.

    Args:
        query: Consulta del usuario
        min_length: Longitud minima de palabra para considerarla

    Returns:
        Lista de palabras clave relevantes
    """
    # Normalizar
    normalized = normalize_text(query)

    # Extraer palabras (alfanumericas y guiones bajos)
    words = re.findall(r'[a-z0-9_]+', normalized)

    # Filtrar stop words y palabras muy cortas
    keywords = [
        w for w in words
        if w not in STOP_WORDS_ES and len(w) >= min_length
    ]

    return keywords


def calculate_relevance_score(content: str, keywords: List[str], filename: str) -> float:
    """
    Calcula puntuacion de relevancia de un documento para las keywords.

    Args:
        content: Contenido del documento
        keywords: Palabras clave a buscar
        filename: Nombre del archivo (se da peso extra si coincide)

    Returns:
        Puntuacion de relevancia (mayor es mejor)
    """
    if not keywords:
        return 0.0

    normalized_content = normalize_text(content)
    normalized_filename = normalize_text(filename)

    score = 0.0

    for keyword in keywords:
        # Coincidencia en nombre de archivo (peso alto)
        if keyword in normalized_filename:
            score += 5.0

        # Contar ocurrencias en contenido
        occurrences = normalized_content.count(keyword)
        if occurrences > 0:
            # Log scale para no sobrevalorar muchas repeticiones
            score += 1.0 + min(occurrences * 0.1, 2.0)

        # Bonus si aparece en titulos (lineas que empiezan con #)
        for line in content.split('\n'):
            if line.strip().startswith('#') and keyword in normalize_text(line):
                score += 2.0
                break

    return score


class LocalKnowledgeService:
    """
    Servicio de RAG local para el Copiloto.

    Busca en la carpeta de documentacion (README.md de atomos) para
    encontrar informacion relevante a las consultas del usuario.

    Attributes:
        docs_path: Ruta a la carpeta de documentacion
        src_path: Ruta a la carpeta de scripts fuente
        max_context_chars: Limite de caracteres para el contexto
        max_files: Maximo de archivos a incluir en el contexto
        _cache: Cache de consultas recientes
    """

    def __init__(
        self,
        docs_path: Optional[Path] = None,
        src_path: Optional[Path] = None,
        native_docs_path: Optional[Path] = None,
        max_context_chars: int = 3000,
        max_files: int = 3
    ):
        """
        Inicializa el servicio de conocimiento local.

        Args:
            docs_path: Ruta a la carpeta de documentacion (scripts dinamicos).
                       Si no se especifica, usa DOCS_DIR de custom_script_service.
            src_path: Ruta a la carpeta de scripts fuente.
            native_docs_path: Ruta a la documentacion nativa de la aplicacion e integraciones.
            max_context_chars: Maximo de caracteres en el contexto generado
            max_files: Maximo de archivos a incluir en el contexto
        """
        if docs_path is None:
            try:
                from client_app.app.services.custom_script_service import DOCS_DIR
                self.docs_path = DOCS_DIR
            except ImportError:
                # Fallback si no se puede importar
                self.docs_path = Path("data/storage/scripts/docs")
        else:
            self.docs_path = Path(docs_path)

        if src_path is None:
            self.src_path = Path("data/storage/scripts/src")
        else:
            self.src_path = Path(src_path)

        if native_docs_path is None:
            # client_app/app/services/local_knowledge_service.py -> client_app/app/docs
            self.native_docs_path = Path(__file__).parent.parent / "docs"
        else:
            self.native_docs_path = Path(native_docs_path)

        self.max_context_chars = max_context_chars
        self.max_files = max_files
        self._cache: Dict[str, str] = {}
        self._file_cache: Dict[str, str] = {}  # Cache de contenido de archivos

    def get_context_for_query(self, query: str) -> str:
        """
        Busca documentacion relevante para la consulta.

        Escanea la carpeta de documentacion, filtra los archivos .md
        cuyo nombre o contenido tenga coincidencia con la query,
        y devuelve un contexto formateado.

        Args:
            query: Consulta del usuario en lenguaje natural

        Returns:
            String formateado con el contexto local relevante,
            o string vacio si no se encuentra nada.
        """
        # Verificar cache
        cache_key = normalize_text(query)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Verificar que el directorio existe
        if not self.docs_path.exists():
            logger.warning(f"Directorio de documentacion no existe: {self.docs_path}")
            return ""

        # Extraer keywords de la query
        keywords = extract_keywords(query)
        if not keywords:
            return ""

        # Escanear archivos .md
        md_files = list(self.docs_path.glob("*.md"))
        if not md_files:
            return ""

        # Calcular relevancia para cada archivo
        scored_files: List[Tuple[float, Path, str]] = []

        for md_file in md_files:
            try:
                # Usar cache de archivos si existe
                if str(md_file) in self._file_cache:
                    content = self._file_cache[str(md_file)]
                else:
                    content = md_file.read_text(encoding='utf-8')
                    self._file_cache[str(md_file)] = content

                score = calculate_relevance_score(
                    content=content,
                    keywords=keywords,
                    filename=md_file.stem
                )

                if score > 0:
                    scored_files.append((score, md_file, content))

            except Exception as e:
                logger.warning(f"Error leyendo archivo {md_file}: {e}")
                continue

        # Ordenar por relevancia y tomar los mejores
        scored_files.sort(key=lambda x: x[0], reverse=True)
        top_files = scored_files[:self.max_files]

        if not top_files:
            self._cache[cache_key] = ""
            return ""

        # Construir contexto
        context = self._build_context(top_files, keywords)

        # Guardar en cache
        self._cache[cache_key] = context

        return context

    def _build_context(
        self,
        scored_files: List[Tuple[float, Path, str]],
        keywords: List[str]
    ) -> str:
        """
        Construye el string de contexto a partir de los archivos relevantes.

        Args:
            scored_files: Lista de (score, path, content)
            keywords: Keywords para resaltar secciones relevantes

        Returns:
            String formateado con el contexto
        """
        context_parts = []
        remaining_chars = self.max_context_chars

        for score, file_path, content in scored_files:
            if remaining_chars <= 0:
                break

            # Extraer fragmentos relevantes del contenido
            fragment = self._extract_relevant_fragment(content, keywords, remaining_chars)

            if fragment:
                # Limpiar rutas absolutas por privacidad
                fragment = self._sanitize_paths(fragment)

                # Agregar con referencia al atomo
                atom_name = file_path.stem.replace('_', ' ').title()
                context_parts.append(f"[Atomo: {atom_name}]\n{fragment}")
                remaining_chars -= len(fragment) + len(atom_name) + 20

        if not context_parts:
            return ""

        # Formato final
        header = "--- CONTEXTO LOCAL ---"
        footer = "---"
        body = "\n\n".join(context_parts)

        return f"{header}\n{body}\n{footer}"

    def _extract_relevant_fragment(
        self,
        content: str,
        keywords: List[str],
        max_chars: int
    ) -> str:
        """
        Extrae las secciones mas relevantes del contenido.

        Args:
            content: Contenido completo del archivo
            keywords: Keywords para priorizar secciones
            max_chars: Maximo de caracteres a extraer

        Returns:
            Fragmento relevante del contenido
        """
        # Dividir en secciones por headers markdown
        sections = re.split(r'\n(?=##?\s)', content)

        # Puntuar cada seccion
        scored_sections: List[Tuple[float, str]] = []
        for section in sections:
            section_score = 0.0
            normalized = normalize_text(section)

            for keyword in keywords:
                if keyword in normalized:
                    section_score += normalized.count(keyword)

            if section_score > 0:
                scored_sections.append((section_score, section.strip()))

        # Ordenar por puntuacion
        scored_sections.sort(key=lambda x: x[0], reverse=True)

        # Tomar secciones hasta llenar el limite
        fragment_parts = []
        current_length = 0

        for score, section in scored_sections:
            if current_length + len(section) > max_chars:
                # Truncar la seccion si es necesario
                remaining = max_chars - current_length
                if remaining > 100:  # Solo agregar si queda espacio significativo
                    fragment_parts.append(section[:remaining] + "...")
                break
            fragment_parts.append(section)
            current_length += len(section) + 2  # +2 por newlines

        return "\n\n".join(fragment_parts)

    def _sanitize_paths(self, text: str) -> str:
        """
        Elimina rutas absolutas del texto por privacidad.

        Args:
            text: Texto que puede contener rutas

        Returns:
            Texto con rutas limpiadas
        """
        # Patrones de rutas a limpiar
        patterns = [
            r'C:\\[^\s\n"\']+',  # Windows paths
            r'/Users/[^\s\n"\']+',  # macOS user paths
            r'/home/[^\s\n"\']+',  # Linux user paths
            r'/var/[^\s\n"\']+',  # Linux var paths
            r'/tmp/[^\s\n"\']+',  # Temp paths
        ]

        result = text
        for pattern in patterns:
            result = re.sub(pattern, '[ruta-local]', result)

        return result

    def clear_cache(self) -> None:
        """Limpia las caches de consultas y archivos."""
        self._cache.clear()
        self._file_cache.clear()

    def refresh_file_cache(self) -> None:
        """Recarga el cache de archivos desde disco."""
        self._file_cache.clear()
        # El cache se rellenara en la proxima consulta

    def get_all_atom_names(self) -> List[str]:
        """
        Obtiene los nombres de todos los atomos documentados.

        Returns:
            Lista de nombres de atomos (sin extension .md)
        """
        if not self.docs_path.exists():
            return []

        return [f.stem for f in self.docs_path.glob("*.md")]

    def get_atom_readme(self, atom_name: str) -> Optional[str]:
        """
        Obtiene el README completo de un atomo especifico.

        Args:
            atom_name: Nombre del atomo (sin extension)

        Returns:
            Contenido del README o None si no existe
        """
        file_path = self.docs_path / f"{atom_name}.md"
        if not file_path.exists():
            # Intentar con variaciones del nombre
            normalized_name = atom_name.lower().replace(' ', '_')
            file_path = self.docs_path / f"{normalized_name}.md"

        if not file_path.exists():
            return None

        try:
            content = file_path.read_text(encoding='utf-8')
            return self._sanitize_paths(content)
        except Exception as e:
            logger.error(f"Error leyendo README de {atom_name}: {e}")
            return None

    def get_native_documentation(self, topic: str, subfolder: str = "actions") -> Optional[str]:
        """
        Busca documentacion estatica nativa de la aplicacion (ej. modulos core, acciones nativas).

        Args:
            topic: Nombre del topico o StepType (ej. 'etl_transform', 'flow_designer')
            subfolder: Subcarpeta donde buscar ('actions', 'core', etc.)

        Returns:
            Contenido de la documentacion nativa o None si no existe
        """
        if not self.native_docs_path.exists():
            return None

        # Normalizar a lowercase
        topic_normalized = topic.lower()

        # Buscar topic exacto
        file_path = self.native_docs_path / subfolder / f"{topic_normalized}.md"
        if not file_path.exists():
            # Intentar sin la terminacion '_op' o similar o mapeos comunes
            if topic_normalized == 'etl': file_path = self.native_docs_path / subfolder / "etl_transform.md"
            elif topic_normalized == 'api_get': file_path = self.native_docs_path / subfolder / "api_fetch.md"
            elif topic_normalized == 'smtp_send': file_path = self.native_docs_path / subfolder / "smtp.md"

        if not file_path.exists():
            return None

        try:
            content = file_path.read_text(encoding='utf-8')
            return content
        except Exception as e:
            logger.error(f"Error leyendo documentacion nativa para {topic}: {e}")
            return None

    def get_context_for_atom(
        self,
        atom_id: Optional[int] = None,
        atom_name: Optional[str] = None,
        doc_path: Optional[str] = None,
        atom_code: Optional[str] = None,
        atom_schema: Optional[Dict] = None,
        step_type: Optional[str] = None
    ) -> str:
        """
        Genera contexto RAG para un atomo especifico.

        Prioridad de fuentes:
        0. step_type (Documentacion nativa)
        1. doc_path (README.md especifico del modulo guardado)
        2. atom_code (codigo fuente pasado directamente)
        3. Buscar archivo .py en src_path por atom_id
        4. atom_schema (schema JSON como fallback)

        Args:
            atom_id: ID del atomo en la base de datos
            atom_name: Nombre del atomo (para el header)
            doc_path: Ruta al archivo de documentacion
            atom_code: Codigo fuente del atomo (si ya se tiene)
            atom_schema: Schema JSON del atomo (fallback)
            step_type: Enum StepType correspondiente al atomo para buscar doc nativa

        Returns:
            String formateado con contexto del atomo
        """
        context_parts = []
        header_name = atom_name or f"Atomo_{atom_id}" if atom_id else "Atomo"

        # 0. Intentar buscar documentacion nativa estatica primero (Mejor calidad)
        if step_type:
            tipo = str(step_type).split('.')[-1] if '.' in str(step_type) else str(step_type)
            native_doc = self.get_native_documentation(tipo, subfolder="actions")
            if native_doc:
                # Truncate if insanely large to prevent overwhelming context
                if len(native_doc) > self.max_context_chars:
                    native_doc = native_doc[:self.max_context_chars] + "\n... (truncado por longitud)"
                context_parts.append(f"## Documentacion Principal\n{native_doc}")

        # 1. Intentar leer documentacion especifica del script (README.md custom)
        if doc_path:
            doc_content = self._read_doc_file(doc_path)
            if doc_content:
                # Si tambien hay nativa, lo mostramos como Documentacion Extendida/Especifica
                prefix = "## Documentacion Especifica del Script" if context_parts else "## Documentacion"
                context_parts.append(f"{prefix}\n{doc_content}")

        # 2. Usar codigo fuente si se proporciona directamente
        if atom_code and not context_parts:
            sanitized_code = self._sanitize_paths(atom_code)
            # Limitar longitud del codigo
            if len(sanitized_code) > self.max_context_chars:
                sanitized_code = sanitized_code[:self.max_context_chars] + "\n# ... (truncado)"
            context_parts.append(f"## Codigo Fuente\n```python\n{sanitized_code}\n```")

        # 3. Buscar archivo .py por atom_id si no hay codigo
        if atom_id and not context_parts:
            code_content = self._find_and_read_source(atom_id)
            if code_content:
                context_parts.append(f"## Codigo Fuente\n```python\n{code_content}\n```")

        # 4. Usar schema como fallback
        if atom_schema and not context_parts:
            import json
            schema_str = json.dumps(atom_schema, indent=2, ensure_ascii=False)
            if len(schema_str) > 1000:
                schema_str = schema_str[:1000] + "\n... (truncado)"
            context_parts.append(f"## Schema de Configuracion\n```json\n{schema_str}\n```")

        if not context_parts:
            return ""

        # Formatear contexto final
        body = "\n\n".join(context_parts)
        return f"--- CONTEXTO ATOMO: {header_name} ---\n{body}\n---"

    def _read_doc_file(self, doc_path: str) -> Optional[str]:
        """Lee un archivo de documentacion."""
        try:
            path = Path(doc_path)
            if path.exists():
                content = path.read_text(encoding='utf-8')
                return self._sanitize_paths(content[:self.max_context_chars])
        except Exception as e:
            logger.warning(f"Error leyendo documentacion {doc_path}: {e}")
        return None

    def _find_and_read_source(self, atom_id: int) -> Optional[str]:
        """
        Busca y lee el archivo fuente de un atomo por su ID.

        Busca patrones como:
        - lib_{id}_*.py
        - {id}_*.py
        """
        if not self.src_path.exists():
            return None

        # Patrones a buscar
        patterns = [
            f"lib_{atom_id}_*.py",
            f"{atom_id}_*.py"
        ]

        for pattern in patterns:
            matches = list(self.src_path.glob(pattern))
            if matches:
                try:
                    content = matches[0].read_text(encoding='utf-8')
                    sanitized = self._sanitize_paths(content)
                    # Limitar longitud
                    if len(sanitized) > self.max_context_chars:
                        sanitized = sanitized[:self.max_context_chars] + "\n# ... (truncado)"
                    return sanitized
                except Exception as e:
                    logger.warning(f"Error leyendo fuente {matches[0]}: {e}")

        return None


# Singleton instance
local_knowledge_service = LocalKnowledgeService()
