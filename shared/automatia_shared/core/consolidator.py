from typing import Dict, Any, List, Optional
import json

class DataConsolidator:
    """
    Módulo puro para la limpieza, filtrado y consolidación de datos de extracción.
    Centraliza la lógica de negocio para asegurar que los outputs sean consistentes
    independientemente del motor de IA o estrategia utilizada.
    """

    @staticmethod
    def filter_by_schema(raw_data: Dict[str, Any], schema_keys: List[str]) -> Dict[str, Any]:
        """
        Filtra un diccionario de datos crudos (raw_data), manteniendo solo
        las claves definidas en el esquema de negocio (schema_keys).
        
        Args:
            raw_data (Dict): Datos crudos extraídos (potencialmente con alucinaciones).
            schema_keys (List[str]): Lista de claves permitidas/esperadas.
            
        Returns:
            Dict: Diccionario limpio con solo las claves válidas encontradas.
        """
        if not raw_data or not schema_keys:
            return {}

        clean_data = {}
        # Normalizar claves de esquema para comparación insensible a mayúsculas si es necesario
        # Por ahora asumimos exact match para ser estrictos con los esquemas definidos
        
        for key in schema_keys:
            if key in raw_data:
                clean_data[key] = raw_data[key]
            
        return clean_data

    @staticmethod
    def validate_against_schema(raw_data: Dict[str, Any], schema: Any) -> Dict[str, Any]:
        """
        Valida y limpia los datos contra un OutputSchema.
        
        Args:
            raw_data: Datos crudos (diccionario).
            schema: Instancia de OutputSchema (o compatible con campos con tipo).
            
        Returns:
            Dict: Datos limpios y tipados.
        """
        if not raw_data:
            return {}
            
        if not schema:
            # Si no hay esquema (ej: ejecución ad-hoc genérica sin tipos definidos),
            # confiamos en la IA y devolvemos todo (Pass-through).
            # Esto responde a la duda del usuario sobre ejecuciones sin OutputSchema previo.
            return raw_data

        clean_data = {}
        
        # Como OutputSchema no tiene lógica de validación interna per se (la tiene UIContract),
        # replicamos una lógica simplificada de coerción basada en el prompt.
        # Lo ideal sería mover la lógica de UIContract a un helper compartido, 
        # pero para cumplir prompt 2 sin refactor masivo:
        
        from automatia_shared.contracts.ui_contract import InputType

        for field in schema.fields:
            if field.name not in raw_data:
                continue
                
            val = raw_data[field.name]
            
            # Coerción básica
            try:
                if field.type == InputType.INT:
                    val = int(val)
                elif field.type == InputType.FLOAT:
                    val = float(val)
                elif field.type == InputType.BOOL:
                    if isinstance(val, str):
                        val = val.lower() in ('true', '1', 'yes', 'on')
                    else:
                        val = bool(val)
                # Strings y otros se mantienen
            except (ValueError, TypeError):
                # Si falla la coerción, decidimos si descartar o mantener null.
                # Mantener original o None? El prompt dice "asegurar que los tipos coinciden".
                # Si no coincide, mejor descartar o None.
                continue 
                
            clean_data[field.name] = val
            
        return clean_data

    @staticmethod
    def consolidate_result(
        clean_data: Dict[str, Any], 
        source_engine: str = "unknown", 
        confidence_score: float = 1.0, 
        processing_metadata: Optional[Dict] = None,
        schema: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Empaqueta los datos limpios en una estructura estandarizada para consumo de UI/API.
        Añade metadatos de estado y procedencia.
        
        Args:
            clean_data (Dict): Datos de negocio.
            source_engine (str): Identificador del motor.
            confidence_score (float): Nivel de confianza.
            processing_metadata (Dict): Metadatos técnicos.
            schema (Optional[OutputSchema]): Esquema para validar/filtrar (Runtime safety).
            
        Returns:
            Dict: Estructura consolidada {'status': 'ok', 'data': {...}, 'meta': {...}}
        """
        
        # Runtime Validation (Si se provee esquema)
        final_data = clean_data
        if schema:
            final_data = DataConsolidator.validate_against_schema(clean_data, schema)

        # Validación básica de datos vacíos
        status = "ok" if final_data else "empty"
        
        consolidated = {
            "status": status,
            "data": final_data,
            "meta": {
                "engine": source_engine,
                "confidence": confidence_score,
                "timestamp": None,
            }
        }
        
        if processing_metadata:
            consolidated["meta"].update(processing_metadata)
            
        return consolidated

    @staticmethod
    def merge_multiple_sources(sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Prepara la estructura para unificar resultados de múltiples motores.
        Por ahora implementa una estrategia de "Last Write Wins" o fusión simple.
        
        Args:
            sources (List[Dict]): Lista de diccionarios de datos consolidados o crudos.
            
        Returns:
            Dict: Un único diccionario con los datos fusionados.
        """
        merged_data = {}
        merged_data = {}
        # Lógica simplificada: Sandwich / Last Write Wins
        
        for source in sources:
            # Si la fuente tiene la estructura consolidada, extraemos 'data'
            data_to_merge = source.get('data', source) if 'data' in source and 'meta' in source else source
            
            if isinstance(data_to_merge, dict):
                merged_data.update(data_to_merge)
                
        return merged_data

    @staticmethod
    def merge_discovery_fields(discovery_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extrae lista estructurada de campos desde Fase 0.
        Soporta formato nuevo {fields: [...]} y legado {campos_a...}.
        Returns: List[Dict] sorted by score.
        """
        items = []
        # New Format
        if 'fields' in discovery_data:
             items = discovery_data['fields']
        # Legacy Format (Adapter)
        elif 'campos_a' in discovery_data or 'campos_b' in discovery_data:
             for x in discovery_data.get('campos_a', []) + discovery_data.get('campos_b', []):
                 if isinstance(x, dict) and 'campo' in x: 
                     items.append({'name': x['campo'], 'score': 0.5})

        seen = set()
        out = []
        for it in items:
            if not isinstance(it, dict): continue
            name = str(it.get("name", "")).strip()
            if not name: continue
            key = name.lower()
            if key in seen: continue
            seen.add(key)
            
            out.append({
                "name": name,
                "score": float(it.get("score", 0.0)),
                "page_hint": it.get("page_hint")
            })
            
        out.sort(key=lambda x: x["score"], reverse=True)
        return out
