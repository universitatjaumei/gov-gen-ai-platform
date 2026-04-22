"""
Servicio central para herramientas PDF.
Orquesta operaciones y gestiona carpetas de entrada/salida.
"""
import os
import subprocess
import platform
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from client_app.app.modules.utilities.pdf_tools import (
    merge_pdfs,
    split_by_ranges,
    split_specific_pages,
    split_all_pages,
    optimize_pdf,
    get_pdf_info,
    validate_pdf
)


class PDFToolsService:
    """
    Servicio para operaciones con PDFs.
    Singleton pattern para uso consistente en toda la app.
    """
    _instance = None

    # Carpetas fijas de utilidades
    INPUT_DIR = Path("data/utilities/input")
    OUTPUT_DIR = Path("data/utilities/output")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_directories()
        return cls._instance

    def _init_directories(self):
        """Crea las carpetas de entrada/salida si no existen."""
        self.INPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def _create_output_subdir(self, operation: str) -> Path:
        """
        Crea subdirectorio de salida con timestamp.
        Ej: data/utilities/output/pdf_merge/2024-01-15_14-30-25/
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        subdir = self.OUTPUT_DIR / f"pdf_{operation}" / timestamp
        subdir.mkdir(parents=True, exist_ok=True)
        return subdir

    def list_input_files(self, extension: str = ".pdf") -> List[Dict]:
        """
        Lista archivos PDF en la carpeta de entrada.

        Args:
            extension: Extensión de archivos a listar

        Returns:
            Lista de dicts con información de cada archivo
        """
        files = []
        for f in self.INPUT_DIR.glob(f"*{extension}"):
            try:
                files.append(get_pdf_info(str(f)))
            except Exception:
                # Ignorar archivos que no se pueden leer
                pass
        return sorted(files, key=lambda x: x["name"].lower())

    def get_input_dir_path(self) -> str:
        """Retorna ruta absoluta de carpeta de entrada."""
        return str(self.INPUT_DIR.absolute())

    def get_output_dir_path(self) -> str:
        """Retorna ruta absoluta de carpeta de salida."""
        return str(self.OUTPUT_DIR.absolute())

    def open_folder(self, path: str) -> bool:
        """
        Abre una carpeta en el explorador de archivos del sistema.

        Args:
            path: Ruta de la carpeta a abrir

        Returns:
            True si se abrió correctamente
        """
        try:
            path = str(Path(path).absolute())
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", path], check=True)
            else:  # Linux
                subprocess.run(["xdg-open", path], check=True)
            return True
        except Exception as e:
            print(f"[PDFToolsService] Error opening folder: {e}")
            return False

    def validate_files(self, files: List[str]) -> Tuple[List[str], List[Dict]]:
        """
        Valida una lista de archivos PDF.

        Args:
            files: Lista de rutas de archivos

        Returns:
            Tupla (archivos_validos, errores)
        """
        valid_files = []
        errors = []

        for file_path in files:
            is_valid, message = validate_pdf(file_path)
            if is_valid:
                valid_files.append(file_path)
            else:
                errors.append({
                    "file": Path(file_path).name,
                    "error": message
                })

        return valid_files, errors

    # --- Operaciones principales ---

    async def merge(
        self,
        files: List[str],
        output_name: str = "merged.pdf",
        optimize: bool = True
    ) -> Dict:
        """
        Une múltiples PDFs en uno solo.

        Args:
            files: Lista de rutas de archivos en orden deseado
            output_name: Nombre del archivo de salida
            optimize: Aplicar optimización nivel 3

        Returns:
            Dict con resultado y estadísticas
        """
        # Validar archivos
        valid_files, errors = self.validate_files(files)
        if not valid_files:
            return {
                "success": False,
                "error": "No hay archivos válidos para procesar",
                "validation_errors": errors
            }

        # Asegurar extensión .pdf
        if not output_name.lower().endswith('.pdf'):
            output_name += '.pdf'

        output_dir = self._create_output_subdir("merge")
        output_path = str(output_dir / output_name)

        try:
            result = merge_pdfs(valid_files, output_path, optimize)
            result["success"] = True
            result["output_dir"] = str(output_dir)
            result["files_merged"] = len(valid_files)
            if errors:
                result["validation_errors"] = errors
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output_dir": str(output_dir)
            }

    async def split(
        self,
        file: str,
        mode: str,
        ranges: Optional[List[Tuple[int, int]]] = None,
        pages: Optional[List[int]] = None,
        optimize: bool = True
    ) -> Dict:
        """
        Divide un PDF según el modo especificado.

        Args:
            file: Ruta del PDF a dividir
            mode: 'ranges', 'pages', 'all'
            ranges: Para mode='ranges', lista de (inicio, fin)
            pages: Para mode='pages', lista de números de página
            optimize: Aplicar optimización nivel 3

        Returns:
            Dict con resultado y lista de archivos generados
        """
        # Validar archivo
        is_valid, message = validate_pdf(file)
        if not is_valid:
            return {
                "success": False,
                "error": message
            }

        output_dir = self._create_output_subdir("split")

        try:
            if mode == "ranges" and ranges:
                results = split_by_ranges(file, ranges, str(output_dir), optimize)
            elif mode == "pages" and pages:
                result = split_specific_pages(file, pages, str(output_dir), optimize)
                results = [result]
            elif mode == "all":
                results = split_all_pages(file, str(output_dir), optimize)
            else:
                return {
                    "success": False,
                    "error": f"Modo inválido o parámetros faltantes: {mode}"
                }

            return {
                "success": True,
                "output_dir": str(output_dir),
                "files_generated": len(results),
                "results": results
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output_dir": str(output_dir)
            }

    async def optimize(
        self,
        files: List[str],
        level: int = 3
    ) -> Dict:
        """
        Optimiza uno o más PDFs.

        Args:
            files: Lista de rutas de archivos
            level: Nivel de optimización (1-4)

        Returns:
            Dict con resultados por archivo y totales
        """
        # Validar archivos
        valid_files, errors = self.validate_files(files)
        if not valid_files:
            return {
                "success": False,
                "error": "No hay archivos válidos para procesar",
                "validation_errors": errors
            }

        output_dir = self._create_output_subdir("optimize")
        results = []
        total_saved = 0
        total_original = 0

        try:
            for file_path in valid_files:
                filename = Path(file_path).name
                output_path = str(output_dir / f"optimized_{filename}")

                result = optimize_pdf(file_path, output_path, level)
                result["original_name"] = filename
                results.append(result)

                total_saved += result["saved_mb"]
                total_original += result["original_mb"]

            return {
                "success": True,
                "output_dir": str(output_dir),
                "files_processed": len(results),
                "total_original_mb": round(total_original, 2),
                "total_saved_mb": round(total_saved, 2),
                "total_percentage": round((total_saved / total_original * 100) if total_original > 0 else 0, 1),
                "results": results,
                "validation_errors": errors if errors else None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output_dir": str(output_dir)
            }

    def get_file_info(self, file_path: str) -> Optional[Dict]:
        """
        Obtiene información de un archivo PDF.

        Args:
            file_path: Ruta al archivo

        Returns:
            Dict con información o None si no es válido
        """
        is_valid, _ = validate_pdf(file_path)
        if not is_valid:
            return None
        return get_pdf_info(file_path)


# Instancia global singleton
pdf_tools_service = PDFToolsService()
